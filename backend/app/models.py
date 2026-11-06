"""SQLAlchemy ORM models for RePersona.

The schema captures the full pipeline: personas -> sources -> media/documents ->
transcripts -> chunks (+ embeddings metadata) -> topics/insights/knowledge graph,
plus jobs (build pipeline) and chat sessions/messages with evidence provenance.

Generic ``JSON`` columns are used so the same models work on both SQLite (demo)
and PostgreSQL (production).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="")


class Persona(Base, TimestampMixin):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|building|ready|failed
    is_demo: Mapped[bool] = mapped_column(default=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    portrait_url: Mapped[str] = mapped_column(String(1024), default="")
    known_for: Mapped[list] = mapped_column(JSON, default=list)
    domains: Mapped[list] = mapped_column(JSON, default=list)
    # Temporal boundary (Historical Reality Guard). Nullable: unknown/living.
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    death_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Structured, restart-durable temporal boundary (§17). Full ISO dates when
    # known ("1990-01-19"); empty string when unknown. ``knowledge_cutoff`` is
    # the date past which the documented person could not have known events
    # (death date for the deceased), and ``knowledge_cutoff_reason`` records why
    # (e.g. "documented death date"). These are stored so the boundary survives
    # a backend restart without re-parsing prose.
    birth_date: Mapped[str] = mapped_column(String(32), default="")
    death_date: Mapped[str] = mapped_column(String(32), default="")
    knowledge_cutoff: Mapped[str] = mapped_column(String(32), default="")
    knowledge_cutoff_reason: Mapped[str] = mapped_column(String(255), default="")

    sources = relationship("Source", back_populates="persona", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="persona", cascade="all, delete-orphan")
    profile = relationship("PersonaProfile", back_populates="persona", uselist=False, cascade="all, delete-orphan")
    insights = relationship("PersonaInsight", back_populates="persona", cascade="all, delete-orphan")
    nodes = relationship("KnowledgeNode", back_populates="persona", cascade="all, delete-orphan")
    edges = relationship("KnowledgeEdge", back_populates="persona", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="persona", cascade="all, delete-orphan")


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), index=True)
    title: Mapped[str] = mapped_column(String(1024), default="")
    url: Mapped[str] = mapped_column(String(2048), default="")
    source_type: Mapped[str] = mapped_column(String(32), default="text")  # video|audio|article|document|image|text
    author: Mapped[str] = mapped_column(String(512), default="")
    publication_date: Mapped[str] = mapped_column(String(32), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    thumbnail: Mapped[str] = mapped_column(String(2048), default="")
    provider: Mapped[str] = mapped_column(String(128), default="")
    access_type: Mapped[str] = mapped_column(String(64), default="public")  # public|licensed|public_domain|user_provided
    discovery_method: Mapped[str] = mapped_column(String(64), default="demo")
    processing_status: Mapped[str] = mapped_column(String(32), default="pending")
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    persona = relationship("Persona", back_populates="sources")
    chunks = relationship("Chunk", back_populates="source", cascade="all, delete-orphan")


class Chunk(Base, TimestampMixin):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    start_time: Mapped[float] = mapped_column(Float, default=0.0)  # seconds (audio/video)
    end_time: Mapped[float] = mapped_column(Float, default=0.0)
    page: Mapped[int] = mapped_column(Integer, default=0)  # documents
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    vector_index: Mapped[int] = mapped_column(Integer, default=-1)  # position in the FAISS index

    persona = relationship("Persona", back_populates="chunks")
    source = relationship("Source", back_populates="chunks")


class Topic(Base, TimestampMixin):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), index=True)
    label: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    persona = relationship("Persona", back_populates="topics")


class PersonaProfile(Base, TimestampMixin):
    __tablename__ = "persona_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), index=True)
    communication_style: Mapped[list] = mapped_column(JSON, default=list)
    recurring_themes: Mapped[list] = mapped_column(JSON, default=list)
    documented_viewpoints: Mapped[list] = mapped_column(JSON, default=list)
    frequent_concepts: Mapped[list] = mapped_column(JSON, default=list)
    language_patterns: Mapped[list] = mapped_column(JSON, default=list)
    source_coverage: Mapped[dict] = mapped_column(JSON, default=dict)
    uncertainties: Mapped[list] = mapped_column(JSON, default=list)

    persona = relationship("Persona", back_populates="profile")


class PersonaInsight(Base, TimestampMixin):
    __tablename__ = "persona_insights"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), index=True)
    label: Mapped[str] = mapped_column(String(512))
    detail: Mapped[str] = mapped_column(Text, default="")
    # classification: DOCUMENTED | OBSERVED | INFERRED | UNKNOWN
    classification: Mapped[str] = mapped_column(String(32), default="OBSERVED")
    evidence_chunk_ids: Mapped[list] = mapped_column(JSON, default=list)

    persona = relationship("Persona", back_populates="insights")


class KnowledgeNode(Base, TimestampMixin):
    __tablename__ = "knowledge_nodes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), index=True)
    label: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    group: Mapped[str] = mapped_column(String(64), default="concept")

    persona = relationship("Persona", back_populates="nodes")


class KnowledgeEdge(Base, TimestampMixin):
    __tablename__ = "knowledge_edges"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), index=True)
    source_node_id: Mapped[str] = mapped_column(String(32), index=True)
    target_node_id: Mapped[str] = mapped_column(String(32), index=True)
    relation: Mapped[str] = mapped_column(String(128), default="related")
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    persona = relationship("Persona", back_populates="edges")


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), index=True)
    kind: Mapped[str] = mapped_column(String(64), default="persona_build")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|completed|failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    current_stage: Mapped[str] = mapped_column(String(64), default="")
    stages: Mapped[list] = mapped_column(JSON, default=list)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")


class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), index=True)
    title: Mapped[str] = mapped_column(String(512), default="New conversation")

    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    evidence_coverage: Mapped[str] = mapped_column(String(16), default="")  # HIGH|MEDIUM|LOW
    evidence: Mapped[list] = mapped_column(JSON, default=list)

    session = relationship("ChatSession", back_populates="messages")
