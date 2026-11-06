# RePersona — Architecture

RePersona is a two-tier application (Next.js frontend + FastAPI backend) around a
multimodal AI pipeline that turns raw source material into an evidence-grounded,
queryable persona.

```
┌──────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Next.js 14)                          │
│  Landing / START · Search · Build (SSE) · Profile · Chat · Graph ·      │
│  Sources        Three.js/R3F 3D · Framer Motion · Tailwind              │
└───────────────▲───────────────────────────────────────────▲───────────┘
                │ REST (JSON)                                 │ SSE
┌───────────────┴───────────────────────────────────────────┴───────────┐
│                          BACKEND (FastAPI)                              │
│  routers: personas · jobs(stream) · chat · health                       │
│                                                                         │
│  Pipeline (job_manager, async 15 stages)                                │
│   discover → validate → collect → docs → audio → transcribe(Whisper)    │
│   → OCR → clean → NLP → embed → index(FAISS) → analyze → validate → ✔   │
│                                                                         │
│  services: source_discovery · media(Whisper/OCR/PDF) · nlp ·            │
│            embeddings · vector_store · persona_analysis · rag_engine ·  │
│            llm_provider · demo_builder                                   │
└───────┬───────────────┬───────────────┬───────────────┬────────────────┘
        │               │               │               │
   PostgreSQL       Vector store     LLM (Llama)     Object storage
   (SQLAlchemy)     FAISS/memory     Ollama/OpenAI-  local / S3
                    (→Qdrant/…)      compatible/demo
```

## Frontend

- **Next.js App Router** with routes: `/`, `/explore`, `/persona/build/[jobId]`,
  `/persona/[personaId]`, `/persona/[personaId]/{chat,knowledge,sources}`.
- **`src/lib/api.ts`** — a single typed fetch layer; **`src/lib/types.ts`**
  mirrors the backend Pydantic schemas (the API contract).
- **`useJobStream`** — subscribes to `GET /api/jobs/{id}/stream` via `EventSource`,
  handling every named event plus a `PING` keep-alive and a polling fallback.
- **3D** is isolated in `components/three/*`, dynamically imported (`ssr:false`),
  quality-scaled by device, and gated behind `prefers-reduced-motion`.

## Backend

### API surface
`POST /api/personas/create`, `GET /api/personas`, `GET /api/personas/{id}`,
`/sources`, `/topics`, `/insights`, `/knowledge-graph`,
`POST /api/personas/{id}/sources/text`, `POST /api/personas/{id}/sources/upload`,
`POST /api/chat`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/stream`,
`GET /api/health`, `GET /api/ethical-notice`.

### User-provided ingestion (`services/ingest.py`, `routers/uploads.py`)
Text is decoded directly; PDFs use pypdf extraction; images use OCR; audio/video
use Whisper (timestamped segments). Extracted text is chunked, the persona's
vector index is dropped so it lazily rebuilds with the new material, and persona
analysis re-runs (curated profile hints preserved). Content is de-duplicated by
SHA-256. Missing optional deps yield an honest 422, never a fake success.

### Live source discovery (`services/source_discovery.py`)
Adapter pattern. `WikipediaSourceAdapter` (default, `SOURCE_MODE=auto`) resolves
the page title via the action API, pulls the summary + portrait image (Wikimedia
REST), the full plain-text article (`prop=extracts`), and documented quotations
from Wikiquote — all via official public APIs with a descriptive User-Agent, no
scraping. It splits the article into section-sources for retrieval diversity and
sets the persona's portrait URL. On any failure it degrades to the bundled demo
adapter. `DemoSourceAdapter` (offline synthetic) and a `LiveSearchAdapter` stub
(bring-your-own authorised API) round out the options. The (possibly network-
bound) call runs off the event loop via `asyncio.to_thread`.

### LLM auto mode (`services/llm_provider.py`)
`LLM_PROVIDER=auto` does a fast (~2s) reachability probe of Ollama; if up it
generates with the local model, otherwise it uses the offline composer — so the
user never waits on a long timeout when no model server is present.

### Storage (`services/storage.py`)
`Storage` interface with `LocalStorage` and `S3Storage` (boto3, S3/MinIO/R2).
Uploaded blobs are saved via the interface; media/OCR tools resolve a local path
(downloading from object storage into a temp cache when needed).

### Rate limiting (`middleware.py`)
In-memory per-IP sliding window (`RATE_LIMIT_PER_MINUTE`), added inside CORS so
429 responses still carry CORS headers. Health and SSE endpoints are exempt.

### Persona build pipeline (`services/job_manager.py`)
An async task advances through 15 stages, doing real work each step (create
`Source` rows → chunk → embed → build vector index → run persona analysis) and
publishing progress to SSE subscribers while persisting state to the `jobs`
table (so late subscribers and pollers always see current state). For
horizontal scale, the same stage functions and event schema drop into
Celery/RQ workers backed by Redis.

### RAG engine (`services/rag_engine.py`)
`question → query embedding → vector retrieval (top-k) → diversity reranking →
evidence selection (with provenance) → persona-conditioned system prompt →
LLM → answer + evidence + coverage + limitations`. The system prompt enforces
the anti-fabrication / anti-impersonation rules and instructs the model to
distinguish documented facts from inference and to cite passages.

### Persona Reasoner (`services/persona_reasoner.py`) — core innovation
A dedicated reasoning service layered *on top of* plain RAG. Pipeline:
`question → intent detection → temporal analysis → persona-evidence retrieval →
current-context retrieval → worldview mapping → mode selection → generation →
quote-authenticity guard → reasoning trace`. It returns a labelled response
type — `SIMULATED_PERSONA_RESPONSE` vs `VERIFIED_HISTORICAL_QUOTE` (§18) — plus
the evidence, worldview concepts, sources, and temporal context that power the
"Why did the AI say this?" panel (§22). Response modes (§23): `evidence`,
`persona_simulation`, `historical`, `current_context`.

### Historical Reality Guard (`services/temporal.py`)
A deceased persona's `knowledge_cutoff` is its death year. Questions referencing
later events are detected, and the answer is generated as a clearly labelled
*simulated* perspective drawn from the documented worldview — never presented as
something the person directly knew (§17). Covered by `tests/test_temporal.py`.

### Identity resolution (`services/identity.py`)
Before deep ingestion, an ambiguous name is resolved to candidate identities
(name, profession, birth/death years, portrait, summary) so the correct person
is selected (§8). Exposed at `POST /api/personas/resolve`.

### Source providers (`services/source_providers.py`)
A modular `SourceProvider` system (Wikipedia/Wikiquote always on; Tavily/SerpAPI
web search and YouTube Data API key-gated). Each provider is enabled
independently via env vars; a missing key reports *not configured* (§27) and is
skipped rather than faked. `GET /api/providers` drives the Settings status UI.

### Timeline & coverage (`services/timeline.py`, `services/coverage.py`)
`build_timeline` derives a documented timeline from lifespan + dated sources
with documented/inferred confidence (§12). `estimate_coverage` returns per-facet
coverage estimates + suggested searches to fill gaps (§21) — labelled estimates,
not exact measurements.

### Pluggable AI layers
- **Embeddings** (`services/embeddings.py`): Sentence Transformers when present;
  otherwise a deterministic, offline hashing/TF vectoriser. Same `list[float]`
  L2-normalised output either way.
- **Vector store** (`services/vector_store.py`): `VectorStore` ABC with
  `FaissVectorStore` and pure-Python `MemoryVectorStore`. An `IndexRegistry`
  caches one index per persona and lazily rebuilds from DB chunks. Swapping in
  Qdrant/Chroma/Pinecone means implementing this one interface.
- **LLM** (`services/llm_provider.py`): `demo` (offline deterministic composer),
  `ollama`, `openai_compatible`. `complete()` never raises on provider failure —
  it degrades to the demo composer and reports which provider produced the text.
- **Media** (`services/media.py`): faster-whisper transcription (timestamped
  segments), pytesseract OCR with image preprocessing, pypdf text extraction —
  each degrades cleanly when its optional dependency is missing.

### Persona analysis (`services/persona_analysis.py`)
Derives topics, frequent concepts, a co-occurrence knowledge graph, source
coverage and a profile from the chunks; produces insights classified
`DOCUMENTED / OBSERVED / INFERRED / UNKNOWN`, each linked to the evidence chunks
that support it (a `DOCUMENTED` insight lacking evidence is downgraded during
the `validating_evidence` stage).

## Data model (`app/models.py`)
`users, personas, sources, chunks, topics, persona_profiles, persona_insights,
knowledge_nodes, knowledge_edges, jobs, chat_sessions, chat_messages`. Generic
`JSON` columns keep the schema portable across SQLite and PostgreSQL. Indexes on
foreign keys and `content_hash` (dedup/caching).

## Real-time processing
Server-Sent Events over `sse-starlette`. Event names mirror the pipeline:
`JOB_STARTED, SOURCE_DISCOVERY, SOURCE_VALIDATION, DOCUMENT_PROCESSING,
AUDIO_PROCESSING, TRANSCRIPTION, OCR_PROCESSING, NLP_ANALYSIS, EMBEDDING,
VECTOR_INDEXING, PERSONALITY_ANALYSIS, PERSONA_BUILDING, EVIDENCE_VALIDATION,
COMPLETED, FAILED` (+ `SNAPSHOT`, `PING`).

## Caching & storage
Sources are de-duplicated by SHA-256 `content_hash` so identical material is not
reprocessed. Large media belongs in object storage (local or S3-compatible
abstraction) rather than the relational DB.

## Security
Environment-driven configuration (no hard-coded secrets), input/length
validation, configurable CORS, error sanitisation, and a source-discovery layer
that refuses to bypass access controls. Secrets (LLM/API keys, DB credentials)
are never returned by the API. For production add authentication, per-IP rate
limiting, and request-size limits at the gateway.

## Observability
Structured logging under the `repersona.*` namespace (jobs, LLM, media). Jobs
persist `status`, `progress`, per-stage state, `stats`, and `error` for
inspection and failure triage.

## Deployment topology
Frontend → Vercel · Backend → container host · Workers → Celery/RQ + Redis ·
Database → managed PostgreSQL · Vector DB → FAISS→Qdrant/Pinecone · Storage →
S3-compatible object storage.
