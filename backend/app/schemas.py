"""Pydantic v2 request/response schemas (the public API contract).

The frontend ``src/lib/types.ts`` mirrors these shapes.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")


# --------------------------------------------------------------------------- #
# Personas
# --------------------------------------------------------------------------- #
class PersonaCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    demo: bool = Field(default=False, description="Force use of the bundled demo corpus.")


class PersonaSummary(ORMModel):
    id: str
    name: str
    slug: str
    status: str
    is_demo: bool
    summary: str = ""
    portrait_url: str = ""
    known_for: list[str] = []
    domains: list[str] = []
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    birth_date: str = ""
    death_date: str = ""
    knowledge_cutoff: str = ""
    knowledge_cutoff_reason: str = ""


class SourceOut(ORMModel):
    id: str
    title: str
    url: str = ""
    source_type: str
    author: str = ""
    publication_date: str = ""
    description: str = ""
    thumbnail: str = ""
    provider: str = ""
    access_type: str = ""
    processing_status: str = ""
    duration_seconds: float = 0.0


class TopicOut(ORMModel):
    id: str
    label: str
    description: str = ""
    weight: float = 0.0
    keywords: list[str] = []


class InsightOut(ORMModel):
    id: str
    label: str
    detail: str = ""
    classification: str
    evidence_chunk_ids: list[str] = []


class ProfileOut(ORMModel):
    communication_style: list[str] = []
    recurring_themes: list[str] = []
    documented_viewpoints: list[str] = []
    frequent_concepts: list[str] = []
    language_patterns: list[str] = []
    source_coverage: dict[str, Any] = {}
    uncertainties: list[str] = []


class KnowledgeNodeOut(ORMModel):
    id: str
    label: str
    description: str = ""
    weight: float = 1.0
    group: str = "concept"


class KnowledgeEdgeOut(ORMModel):
    id: str
    source_node_id: str
    target_node_id: str
    relation: str = "related"
    weight: float = 1.0


class KnowledgeGraphOut(BaseModel):
    nodes: list[KnowledgeNodeOut]
    edges: list[KnowledgeEdgeOut]


class PersonaDetail(PersonaSummary):
    profile: Optional[ProfileOut] = None
    topics: list[TopicOut] = []
    source_count: int = 0


# --------------------------------------------------------------------------- #
# Jobs
# --------------------------------------------------------------------------- #
class StageOut(BaseModel):
    key: str
    label: str
    status: str  # pending | processing | completed | failed
    detail: str = ""


class JobOut(ORMModel):
    id: str
    persona_id: str
    kind: str
    status: str
    progress: float
    current_stage: str = ""
    stages: list[StageOut] = []
    stats: dict[str, Any] = {}
    error: str = ""


class PersonaCreateResponse(BaseModel):
    persona: PersonaSummary
    job: JobOut


# --------------------------------------------------------------------------- #
# Chat
# --------------------------------------------------------------------------- #
class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    persona_id: str
    message: str = Field(min_length=1)
    session_id: Optional[str] = None
    history: list[ChatTurn] = []
    evidence_mode: bool = True
    language: str = Field(default="en", description="Reply language: en | hi | hinglish")
    mode: str = Field(
        default="persona_simulation",
        description="Response mode: evidence | persona_simulation | historical | current_context",
    )


class EvidenceItem(BaseModel):
    chunk_id: str
    source_id: str
    source_title: str
    source_type: str
    publication_date: str = ""
    url: str = ""
    timestamp: Optional[float] = None
    page: Optional[int] = None
    relevance: float
    text: str


class TemporalContext(BaseModel):
    referenced_year: Optional[int] = None
    is_current_context: bool = False
    is_after_cutoff: bool = False
    is_projection: bool = False
    cutoff_year: Optional[int] = None
    needs_current_context: bool = False
    note: str = ""
    markers: list[str] = []
    # Structured, restart-durable boundary for display (§17).
    cutoff_date: str = ""            # ISO date or bare year, "" if unknown
    cutoff_reason: str = ""          # why this boundary exists
    boundary_display: str = ""       # e.g. "19 Jan 1990" or "" when unavailable


class CurrentContextItem(BaseModel):
    """A single live-retrieved current-context fact. NEVER sourced from the
    persona's historical corpus — only from a configured live search provider."""
    title: str = ""
    url: str = ""
    domain: str = ""
    source: str = ""
    publication_date: str = ""
    retrieved_at: str = ""
    snippet: str = ""
    relevance: float = 0.0


class ChatResponse(BaseModel):
    session_id: str
    message: str
    evidence: list[EvidenceItem] = []
    evidence_coverage: str = "LOW"  # HIGH | MEDIUM | LOW
    limitations: list[str] = []
    provider: str = "demo"
    # Persona-reasoner additions (§16-23)
    response_type: str = "SIMULATED_PERSONA_RESPONSE"  # or VERIFIED_HISTORICAL_QUOTE
    mode: str = "persona_simulation"                    # effective mode used
    requested_mode: str = "persona_simulation"
    intent: str = "general"
    temporal: Optional[TemporalContext] = None
    worldview_concepts: list[str] = []
    reasoning: dict[str, Any] = {}                      # "Why this response?" payload
    # Question classification + current-context (§18-19)
    category: str = "general"
    requires_current_context: bool = False
    current_context_used: bool = False
    current_context_status: str = "not_required"  # not_required|ok|unavailable|error|empty
    current_context: list[CurrentContextItem] = []
    citations: list[dict[str, Any]] = []
    warnings: list[str] = []
    knowledge_cutoff: str = ""


# --------------------------------------------------------------------------- #
# Provider status (§27)
# --------------------------------------------------------------------------- #
class ProviderStatusOut(BaseModel):
    key: str
    label: str
    configured: bool
    mode: str
    detail: str = ""
    requires_key: bool = True
    docs: str = ""


# --------------------------------------------------------------------------- #
# Conversations (§20 conversation memory)
# --------------------------------------------------------------------------- #
class MessageOut(ORMModel):
    id: str
    role: str
    content: str
    evidence_coverage: str = ""
    evidence: list[Any] = []


class ConversationOut(ORMModel):
    id: str
    persona_id: str
    title: str
    message_count: int = 0


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


# --------------------------------------------------------------------------- #
# Timeline (§12)
# --------------------------------------------------------------------------- #
class TimelineEventOut(BaseModel):
    year: Optional[int] = None
    date: str = ""
    title: str
    description: str = ""
    category: str = "event"        # birth | death | source | work | event
    source_id: str = ""
    source_title: str = ""
    confidence: str = "documented"  # documented | inferred


# --------------------------------------------------------------------------- #
# Identity resolution (§8)
# --------------------------------------------------------------------------- #
class IdentityCandidateOut(BaseModel):
    name: str
    description: str = ""
    summary: str = ""
    url: str = ""
    portrait_url: str = ""
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    source: str = "wikipedia"


class ResolutionOut(BaseModel):
    query: str
    candidates: list[IdentityCandidateOut] = []
    ambiguous: bool = False
    note: str = ""


class ResolveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=5, ge=1, le=10)


# --------------------------------------------------------------------------- #
# Knowledge coverage estimates (§21)
# --------------------------------------------------------------------------- #
class CoverageFacetOut(BaseModel):
    facet: str
    coverage: int


class CoverageOut(BaseModel):
    note: str = ""
    source_count: int = 0
    chunk_count: int = 0
    facets: list[CoverageFacetOut] = []
    suggested_searches: list[str] = []


# --------------------------------------------------------------------------- #
# User-provided source ingestion
# --------------------------------------------------------------------------- #
class SourceTextRequest(BaseModel):
    title: str = ""
    text: str = Field(min_length=1)
    source_type: str = "text"
    author: str = "User upload"
    url: str = ""
    publication_date: str = ""


class UploadResult(BaseModel):
    source: SourceOut
    chunks_added: int
    extraction: str  # text | pdf | ocr | whisper
    note: str = ""
