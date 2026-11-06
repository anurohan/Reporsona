// Mirrors backend/app/schemas.py — the public API contract.

export type PersonaStatus =
  | "pending"
  | "building"
  | "ready"
  | "failed"
  | string;

export interface PersonaSummary {
  id: string;
  name: string;
  slug: string;
  status: PersonaStatus;
  is_demo: boolean;
  summary: string;
  portrait_url: string;
  known_for: string[];
  domains: string[];
  birth_year?: number | null;
  death_year?: number | null;
  birth_date?: string;
  death_date?: string;
  knowledge_cutoff?: string;
  knowledge_cutoff_reason?: string;
}

export interface Profile {
  communication_style: string[];
  recurring_themes: string[];
  documented_viewpoints: string[];
  frequent_concepts: string[];
  language_patterns: string[];
  source_coverage: Record<string, any>;
  uncertainties: string[];
}

export interface Topic {
  id: string;
  label: string;
  description: string;
  weight: number;
  keywords: string[];
}

export interface PersonaDetail extends PersonaSummary {
  profile?: Profile | null;
  topics: Topic[];
  source_count: number;
}

export type SourceType =
  | "video"
  | "audio"
  | "article"
  | "document"
  | "image"
  | string;

export interface SourceOut {
  id: string;
  title: string;
  url: string;
  source_type: SourceType;
  author: string;
  publication_date: string;
  description: string;
  thumbnail: string;
  provider: string;
  access_type: string;
  processing_status: string;
  duration_seconds: number;
}

export type InsightClassification =
  | "DOCUMENTED"
  | "OBSERVED"
  | "INFERRED"
  | "UNKNOWN";

export interface Insight {
  id: string;
  label: string;
  detail: string;
  classification: InsightClassification;
  evidence_chunk_ids: string[];
}

export interface KnowledgeNode {
  id: string;
  label: string;
  description: string;
  weight: number;
  group: string;
}

export interface KnowledgeEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  relation: string;
  weight: number;
}

export interface KnowledgeGraph {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

export type StageStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | string;

export interface JobStage {
  key: string;
  label: string;
  status: StageStatus;
  detail: string;
}

export type JobStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | string;

export interface Job {
  id: string;
  persona_id: string;
  kind: string;
  status: JobStatus;
  progress: number;
  current_stage: string;
  stages: JobStage[];
  stats: Record<string, any>;
  error: string;
}

export interface PersonaCreateResponse {
  persona: PersonaSummary;
  job: Job;
}

export interface ChatTurn {
  role: "user" | "assistant" | string;
  content: string;
}

export interface Evidence {
  chunk_id: string;
  source_id: string;
  source_title: string;
  source_type: SourceType;
  publication_date: string;
  url: string;
  timestamp?: number | null;
  page?: number | null;
  relevance: number;
  text: string;
}

export type EvidenceCoverage = "HIGH" | "MEDIUM" | "LOW";

// Response modes (§23) and quote-authenticity labels (§18).
export type ResponseMode =
  | "evidence"
  | "persona_simulation"
  | "historical"
  | "current_context";

export type ResponseType =
  | "SIMULATED_PERSONA_RESPONSE"
  | "VERIFIED_HISTORICAL_QUOTE";

// Historical Reality Guard (§17) classification of the question.
export interface TemporalContext {
  referenced_year?: number | null;
  is_current_context: boolean;
  is_after_cutoff: boolean;
  is_projection: boolean;
  cutoff_year?: number | null;
  needs_current_context: boolean;
  note: string;
  markers: string[];
  // Structured, restart-durable boundary for display (§17).
  cutoff_date?: string;
  cutoff_reason?: string;
  boundary_display?: string;
}

// A single live-retrieved current-context fact (§18). Never from persona corpus.
export interface CurrentContextItem {
  title: string;
  url: string;
  domain: string;
  source: string;
  publication_date: string;
  retrieved_at: string;
  snippet: string;
  relevance: number;
}

export type CurrentContextStatus =
  | "not_required"
  | "ok"
  | "empty"
  | "unavailable"
  | "error"
  | string;

export interface Citation {
  type: "current_context" | "persona_evidence" | string;
  title: string;
  url: string;
  source: string;
  publication_date?: string;
  retrieved_at?: string;
  is_quote?: boolean;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  evidence: Evidence[];
  evidence_coverage: EvidenceCoverage;
  limitations: string[];
  provider: string;
  // Persona-reasoner additions (§16–23)
  response_type: ResponseType;
  mode: ResponseMode | string;
  requested_mode: ResponseMode | string;
  intent: string;
  temporal?: TemporalContext | null;
  worldview_concepts: string[];
  reasoning: Record<string, any>;
  // Classification + current-context (§18–19)
  category: string;
  requires_current_context: boolean;
  current_context_used: boolean;
  current_context_status: CurrentContextStatus;
  current_context: CurrentContextItem[];
  citations: Citation[];
  warnings: string[];
  knowledge_cutoff: string;
}

// Provider status (§27).
export interface ProviderStatus {
  key: string;
  label: string;
  configured: boolean;
  mode: string;
  detail: string;
  requires_key: boolean;
  docs: string;
}

// Conversation memory (§20).
export interface MessageOut {
  id: string;
  role: string;
  content: string;
  evidence_coverage: string;
  evidence: any[];
}

export interface Conversation {
  id: string;
  persona_id: string;
  title: string;
  message_count: number;
}

export interface ConversationDetail extends Conversation {
  messages: MessageOut[];
}

// Timeline (§12).
export interface TimelineEvent {
  year?: number | null;
  date: string;
  title: string;
  description: string;
  category: "birth" | "death" | "source" | "work" | "event" | string;
  source_id: string;
  source_title: string;
  confidence: "documented" | "inferred" | string;
}

// Identity resolution (§8).
export interface IdentityCandidate {
  name: string;
  description: string;
  summary: string;
  url: string;
  portrait_url: string;
  birth_year?: number | null;
  death_year?: number | null;
  source: string;
}

export interface Resolution {
  query: string;
  candidates: IdentityCandidate[];
  ambiguous: boolean;
  note: string;
}

// Knowledge coverage estimates (§21).
export interface CoverageFacet {
  facet: string;
  coverage: number;
}

export interface Coverage {
  note: string;
  source_count: number;
  chunk_count: number;
  facets: CoverageFacet[];
  suggested_searches: string[];
}

export interface EthicalNotice {
  notice: string;
}

export interface UploadResult {
  source: SourceOut;
  chunks_added: number;
  extraction: string;
  note?: string;
}

// A single entry in the live reconstruction activity feed, derived from real
// SSE frames + stat deltas (never fabricated).
export type ActivityKind =
  | "stage"
  | "source"
  | "document"
  | "chunk"
  | "embedding"
  | "topic"
  | "evidence"
  | "milestone";

export interface JobActivityEvent {
  id: string;
  kind: ActivityKind;
  /** Short uppercase headline, e.g. "SOURCE DISCOVERED". */
  label: string;
  /** Real supporting detail, e.g. "6 sources found". */
  detail: string;
  /** Client receive time (ms epoch) for ordering/animation. */
  ts: number;
}

// Shape of a decoded SSE `data` payload from /api/jobs/{id}/stream.
export interface JobStreamEvent {
  event: string;
  job_id: string;
  stage?: string;
  label?: string;
  status?: string;
  progress: number;
  stats?: Record<string, any>;
  stages?: JobStage[];
  error?: string;
  persona_id?: string;
}
