"""Synchronous persona builder used for startup seeding and tests.

Runs the same real steps as the staged pipeline (discover -> chunk -> embed ->
index -> analyze) but without the streaming cadence, so a ready-to-use demo
persona exists the moment the API boots.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chunk, Persona, Source
from app.services import nlp, persona_analysis, source_discovery
from app.services.embeddings import embedding_service
from app.services.source_discovery import slugify
from app.services.temporal import derive_cutoff
from app.services.vector_store import index_registry


def apply_temporal_boundary(persona: Persona, data: dict) -> None:
    """Populate a persona's structured, restart-durable temporal boundary from a
    discovery/seed ``data`` dict. Person-agnostic: derives the knowledge cutoff
    from whatever birth/death info is available (never hardcodes a person)."""
    persona.birth_year = data.get("birth_year", persona.birth_year)
    persona.death_year = data.get("death_year", persona.death_year)
    persona.birth_date = data.get("birth_date", getattr(persona, "birth_date", "")) or ""
    persona.death_date = data.get("death_date", getattr(persona, "death_date", "")) or ""
    cutoff, reason = derive_cutoff(
        birth_date=persona.birth_date,
        death_date=persona.death_date,
        birth_year=persona.birth_year,
        death_year=persona.death_year,
    )
    persona.knowledge_cutoff = cutoff
    persona.knowledge_cutoff_reason = reason


def build_ready_persona(db: Session, name: str, force_demo: bool = True) -> Persona:
    existing = db.scalar(select(Persona).where(Persona.slug == slugify(name)))
    if existing and existing.status == "ready":
        # ensure the in-memory index exists for this process
        if not index_registry.has(existing.id):
            _reindex(db, existing.id)
        # Backfill lifespan on demo personas created before the temporal upgrade
        # so the Historical Reality Guard works without a full rebuild. This runs
        # for any persona whose structured cutoff has not been computed yet.
        if not getattr(existing, "knowledge_cutoff_reason", ""):
            if force_demo and existing.slug == "osho":
                from app.seed import osho_demo

                data = dict(osho_demo.PERSONA)
            else:
                data = {
                    "birth_year": existing.birth_year,
                    "death_year": existing.death_year,
                    "birth_date": getattr(existing, "birth_date", "") or "",
                    "death_date": getattr(existing, "death_date", "") or "",
                }
            apply_temporal_boundary(existing, data)
            db.commit()
            db.refresh(existing)
        return existing

    discovery = source_discovery.discover(name, force_demo=force_demo)
    persona = existing or Persona(name=name, slug=slugify(name))
    persona.status = "building"
    persona.is_demo = discovery.is_demo
    if discovery.persona:
        persona.summary = discovery.persona.get("summary", "")
        persona.known_for = discovery.persona.get("known_for", [])
        persona.domains = discovery.persona.get("domains", [])
        persona.portrait_url = discovery.persona.get("portrait_url", "")
        apply_temporal_boundary(persona, discovery.persona)
    db.add(persona)
    db.flush()

    chunk_rows: list[Chunk] = []
    for s in discovery.sources:
        if not s.text.strip():
            continue
        h = hashlib.sha256(s.text.encode("utf-8")).hexdigest()
        src = Source(
            persona_id=persona.id, title=s.title, url=s.url, source_type=s.source_type,
            author=s.author, publication_date=s.publication_date, description=s.description,
            provider=s.provider, access_type=s.access_type, discovery_method=s.discovery_method,
            content_hash=h, duration_seconds=s.duration_seconds, processing_status="processed",
        )
        db.add(src)
        db.flush()
        pieces = nlp.chunk_text(nlp.clean_text(s.text))
        for ordinal, piece in enumerate(pieces):
            c = Chunk(
                persona_id=persona.id, source_id=src.id, text=piece, ordinal=ordinal,
                start_time=(src.duration_seconds / max(len(pieces), 1)) * ordinal if src.source_type in ("audio", "video") else 0.0,
                end_time=(src.duration_seconds / max(len(pieces), 1)) * (ordinal + 1) if src.source_type in ("audio", "video") else 0.0,
                page=(ordinal + 1) if src.source_type in ("document", "image") else 0,
                vector_index=len(chunk_rows),
            )
            db.add(c)
            chunk_rows.append(c)
    db.flush()

    vectors = embedding_service.encode([c.text for c in chunk_rows])
    index_registry.build(persona.id, [c.id for c in chunk_rows], vectors, embedding_service.dim)

    persona_analysis.analyze(db, persona, hints=discovery.hints)
    persona.status = "ready"
    db.commit()
    db.refresh(persona)
    return persona


def _reindex(db: Session, persona_id: str) -> None:
    chunks = list(db.scalars(select(Chunk).where(Chunk.persona_id == persona_id)))
    vectors = embedding_service.encode([c.text for c in chunks]) if chunks else []
    index_registry.build(persona_id, [c.id for c in chunks], vectors, embedding_service.dim)
