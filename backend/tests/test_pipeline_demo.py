"""Verifies the persona build pipeline produces real, linked artifacts."""

from __future__ import annotations

from sqlalchemy import select

from app.models import Chunk, KnowledgeNode, Source, Topic


def test_demo_persona_is_ready(demo_persona):
    assert demo_persona.status == "ready"
    assert demo_persona.is_demo is True
    assert demo_persona.name == "Osho"


def test_sources_and_chunks_created(db_session, demo_persona):
    sources = list(db_session.scalars(select(Source).where(Source.persona_id == demo_persona.id)))
    chunks = list(db_session.scalars(select(Chunk).where(Chunk.persona_id == demo_persona.id)))
    assert len(sources) >= 4
    assert len(chunks) >= len(sources)  # each source yields >= 1 chunk
    # audio/video sources carry timestamps on their chunks
    audio_ids = {s.id for s in sources if s.source_type in ("audio", "video")}
    audio_chunks = [c for c in chunks if c.source_id in audio_ids]
    assert any(c.end_time > 0 for c in audio_chunks)


def test_topics_and_graph_derived(db_session, demo_persona):
    topics = list(db_session.scalars(select(Topic).where(Topic.persona_id == demo_persona.id)))
    nodes = list(db_session.scalars(select(KnowledgeNode).where(KnowledgeNode.persona_id == demo_persona.id)))
    assert len(topics) > 0
    assert len(nodes) > 0
    assert demo_persona.profile is not None
    assert demo_persona.profile.source_coverage.get("total_chunks", 0) > 0
