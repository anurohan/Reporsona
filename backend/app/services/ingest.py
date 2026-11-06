"""Ingest user-provided material into an existing persona.

This is the concrete, non-faked path for "user-provided content": given raw
text (or a file that Whisper/OCR/PDF extraction has turned into text +
timestamps), it creates a Source, chunks it, drops the persona's vector index so
it lazily rebuilds with the new material, and re-runs persona analysis.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Chunk, Persona, Source
from app.services import nlp, persona_analysis
from app.services.source_discovery import DiscoveryResult  # noqa: F401 (type doc)
from app.services.vector_store import index_registry


def add_text_source(
    db: Session,
    persona: Persona,
    *,
    title: str,
    text: str,
    source_type: str = "text",
    author: str = "User upload",
    url: str = "",
    publication_date: str = "",
    duration_seconds: float = 0.0,
    segments: Optional[list[dict]] = None,
    reanalyze: bool = True,
) -> Source:
    """Create a Source + Chunks from text. If ``segments`` (list of
    {text,start,end}) is given (e.g. Whisper output), chunks preserve timestamps;
    otherwise the text is semantically chunked."""
    text = nlp.clean_text(text)
    if not text:
        raise ValueError("No text content to ingest.")

    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    existing = db.query(Source).filter(
        Source.persona_id == persona.id, Source.content_hash == h
    ).first()
    if existing:
        return existing  # dedup: identical content already ingested

    src = Source(
        persona_id=persona.id, title=title or "Untitled source", url=url,
        source_type=source_type, author=author, publication_date=publication_date,
        provider="user_upload", access_type="user_provided",
        discovery_method="user_upload", content_hash=h,
        duration_seconds=duration_seconds, processing_status="processed",
    )
    db.add(src)
    db.flush()

    if segments:
        for ordinal, seg in enumerate(segments):
            t = nlp.clean_text(seg.get("text", ""))
            if not t:
                continue
            db.add(Chunk(
                persona_id=persona.id, source_id=src.id, text=t, ordinal=ordinal,
                start_time=float(seg.get("start", 0.0)), end_time=float(seg.get("end", 0.0)),
                confidence=float(seg.get("confidence", 1.0)),
            ))
    else:
        pieces = nlp.chunk_text(text)
        for ordinal, piece in enumerate(pieces):
            db.add(Chunk(
                persona_id=persona.id, source_id=src.id, text=piece, ordinal=ordinal,
                start_time=(duration_seconds / max(len(pieces), 1)) * ordinal if source_type in ("audio", "video") else 0.0,
                end_time=(duration_seconds / max(len(pieces), 1)) * (ordinal + 1) if source_type in ("audio", "video") else 0.0,
                page=(ordinal + 1) if source_type in ("document", "image") else 0,
            ))
    db.commit()

    # invalidate index so the next retrieval rebuilds with the new chunks
    index_registry.drop(persona.id)

    if reanalyze:
        # Preserve any curated profile fields (e.g. demo persona style hints)
        # so re-analysis over the enlarged corpus doesn't wipe them.
        hints: dict = {}
        if persona.profile:
            hints = {
                "communication_style": list(persona.profile.communication_style or []),
                "documented_viewpoints": list(persona.profile.documented_viewpoints or []),
                "language_patterns": list(persona.profile.language_patterns or []),
                "uncertainties": list(persona.profile.uncertainties or []),
            }
        persona_analysis.analyze(db, persona, hints=hints)
        db.commit()

    db.refresh(src)
    return src
