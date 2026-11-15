# RePersona Project Report

## 1. Executive summary

RePersona is an evidence-grounded AI research and conversation application. Its purpose is to let a user search for a public or historical person, build a documented profile from available source material, inspect the evidence and derived knowledge, and ask questions through a clearly labelled persona simulation.

The central idea is not to claim that the application recreates a real person's consciousness. Instead, it constructs a limited simulation from collected material. Every answer is intended to be traceable to retrieved evidence, and the system includes temporal safeguards so a deceased person is not presented as knowing events that happened after their lifetime.

The project is a two-tier application:

```text
Next.js frontend
        |
        | JSON REST + Server-Sent Events
        v
FastAPI backend
        |
        +-- SQL database (SQLite by default, PostgreSQL supported)
        +-- source discovery and ingestion
        +-- text/media processing
        +-- embeddings and vector retrieval
        +-- persona analysis
        +-- LLM or offline answer composer
```

## 2. Original product idea

The product idea was to create a research-oriented interface for exploring the documented mind of a historical or public figure. A user should be able to:

1. Search for a person and resolve ambiguous identities.
2. Gather public biographical information, articles, quotations, portraits, uploaded text, documents, images, audio, or video.
3. Transform those materials into a searchable knowledge base.
4. Derive a profile, topics, insights, timeline, source list, coverage estimate, and knowledge graph.
5. Ask questions in several modes: evidence, persona simulation, historical, or current-context plus persona.
6. See why an answer was produced, which evidence supported it, and what limitations apply.
7. Keep the distinction between a verified historical quotation and generated simulated text.

The application therefore combines a research dashboard, a document-ingestion pipeline, a retrieval-augmented generation system, and a conversational UI.

## 3. Main user journey

```text
Open app
  -> Search or select a person
  -> Resolve identity if the name is ambiguous
  -> Start persona build
  -> Watch 15-stage progress stream
  -> Open completed persona
  -> Review profile, timeline, sources, topics, insights, coverage, graph
  -> Ask a question
  -> Retrieve relevant evidence
  -> Classify intent and temporal context
  -> Generate a grounded response
  -> Display answer, evidence, citations, warnings, and reasoning
```

The bundled Osho persona is a synthetic demonstration corpus. It makes the main flow usable without external API keys, a hosted model, or network access. The demo text is deliberately labelled as synthetic and must not be treated as authentic transcripts.

## 4. Repository structure

Important project files and folders are:

| Location | Responsibility |
|---|---|
| [`README.md`](./README.md) | Product overview, quick start, configuration, ethics, and structure. |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | System design and implementation notes. |
| [`SETUP.md`](./SETUP.md) | Installation, environment variables, troubleshooting, and optional integrations. |
| [`backend/app/main.py`](./backend/app/main.py) | FastAPI application entrypoint, startup, middleware, and router registration. |
| [`backend/app/models.py`](./backend/app/models.py) | SQLAlchemy database models and relationships. |
| [`backend/app/schemas.py`](./backend/app/schemas.py) | Pydantic request and response contracts. |
| [`backend/app/routers/`](./backend/app/routers) | HTTP API route modules. |
| [`backend/app/services/`](./backend/app/services) | Business logic, AI pipeline, ingestion, retrieval, and analysis services. |
| [`backend/app/seed/osho_demo.py`](./backend/app/seed/osho_demo.py) | Bundled synthetic demonstration persona and source corpus. |
| [`backend/tests/`](./backend/tests) | Backend tests for API, pipeline, retrieval, temporal logic, uploads, and reasoning. |
| [`frontend/src/app/`](./frontend/src/app) | Next.js App Router pages. |
| [`frontend/src/components/`](./frontend/src/components) | Reusable UI, build-progress, chat, evidence, and Three.js components. |
| [`frontend/src/lib/api.ts`](./frontend/src/lib/api.ts) | Typed frontend-to-backend request layer. |
| [`frontend/src/lib/types.ts`](./frontend/src/lib/types.ts) | Frontend TypeScript representation of backend response types. |
| [`frontend/src/lib/useJobStream.ts`](./frontend/src/lib/useJobStream.ts) | SSE job-progress hook with polling fallback. |
| [`docker-compose.yml`](./docker-compose.yml) | Container topology for PostgreSQL, backend, and frontend. |
| [`START_REPERSONA.bat`](./START_REPERSONA.bat) | Windows one-click launcher. |
| [`docs/visual-technical-report/`](./docs/visual-technical-report) | Imported visual documentation package: 51-page PDF, interactive architecture HTML, 49 SVG diagrams, and diagram-generator source files. |

The imported visual package is documentation, not a second implementation of the backend or frontend. Its diagrams describe the same current architecture and label optional or future capabilities separately. The interactive HTML is self-contained and conceptual; it does not call the running backend.

## 5. Backend architecture

The backend is written in Python using FastAPI. It exposes JSON REST endpoints and an SSE endpoint for long-running persona builds.

### 5.1 Application startup

[`backend/app/main.py`](./backend/app/main.py) creates the FastAPI application. Startup initializes the database and prepares the configured services. The routers are mounted under `/api` and include personas, jobs, chat, conversations, uploads, providers, and health.

The backend uses environment-driven settings from [`backend/app/config.py`](./backend/app/config.py). SQLite is the default database for local development. PostgreSQL can be selected by changing `DATABASE_URL`.

### 5.2 API route groups

The main route modules are:

- [`backend/app/routers/personas.py`](./backend/app/routers/personas.py): create, list, inspect, delete, resolve identity, retrieve sources, topics, insights, timeline, coverage, and knowledge graph.
- [`backend/app/routers/jobs.py`](./backend/app/routers/jobs.py): inspect a build job and stream its progress through SSE.
- [`backend/app/routers/chat.py`](./backend/app/routers/chat.py): receive a question and return a structured persona answer.
- [`backend/app/routers/conversations.py`](./backend/app/routers/conversations.py): list, inspect, rename, and delete chat sessions.
- [`backend/app/routers/uploads.py`](./backend/app/routers/uploads.py): add pasted text or upload supported files.
- [`backend/app/routers/providers.py`](./backend/app/routers/providers.py): report which optional integrations are configured without exposing secrets.
- [`backend/app/routers/health.py`](./backend/app/routers/health.py): report application, LLM, embedding, and vector-store status.

### 5.3 Internal REST and SSE API reference

The frontend does not directly talk to Wikipedia, Ollama, or other providers. It talks to the RePersona FastAPI API. The backend then calls external providers only when the configured workflow requires them.

| Internal endpoint | Method | Why it exists |
|---|---:|---|
| `/api/personas/resolve` | POST | Find candidate identities before building the wrong person. |
| `/api/personas/create` | POST | Create a persona and start its asynchronous build job. |
| `/api/personas` | GET | List previously created personas. |
| `/api/personas/{id}` | GET | Load the completed profile and summary data. |
| `/api/personas/{id}/sources` | GET | Show source records and provenance. |
| `/api/personas/{id}/sources/text` | POST | Add user-pasted evidence. |
| `/api/personas/{id}/sources/upload` | POST | Add text, Markdown, PDF, image, audio, or video material. |
| `/api/personas/{id}/topics` | GET | Return extracted topics and weights. |
| `/api/personas/{id}/insights` | GET | Return evidence-linked observations and insights. |
| `/api/personas/{id}/knowledge-graph` | GET | Return nodes and relationships for the graph view. |
| `/api/personas/{id}/timeline` | GET | Return documented life and source events. |
| `/api/personas/{id}/coverage` | GET | Return coverage estimates and suggested gaps. |
| `/api/chat` | POST | Ask a question and receive answer, evidence, citations, warnings, and reasoning metadata. |
| `/api/conversations` | GET | List saved conversations for a persona. |
| `/api/conversations/{id}` | GET | Load one conversation and its messages. |
| `/api/conversations/{id}` | PATCH/DELETE | Rename or delete a conversation. |
| `/api/jobs/{id}` | GET | Poll the current build status. |
| `/api/jobs/{id}/stream` | GET/SSE | Stream build-stage events in real time. |
| `/api/providers` | GET | Show configured/not-configured provider status without exposing secrets. |
| `/api/health` | GET | Check backend, embedding backend, and vector-store state. |
| `/api/ethical-notice` | GET | Return the simulation and source-use notice. |

The internal API is the stable contract between the Next.js UI and Python services. This separation makes it possible to replace a provider or model without rewriting the frontend.

### 5.4 Database model

[`backend/app/models.py`](./backend/app/models.py) contains the SQLAlchemy model layer. The principal entities are:

- `Persona`: the selected person, profile metadata, dates, knowledge cutoff, status, and demo flag.
- `Source`: a collected or user-provided source, including title, type, URL, publication date, hash, and extraction metadata.
- `Chunk`: searchable text pieces derived from sources, including page and media timestamps where available.
- `Topic`: extracted or grouped topic information.
- `PersonaProfile`: communication style, known domains, concepts, viewpoints, uncertainties, and other profile material.
- `PersonaInsight`: a claim or observation classified as documented, observed, inferred, or unknown, with supporting chunk references.
- `KnowledgeNode` and `KnowledgeEdge`: the derived knowledge graph.
- `Job`: persistent progress for the persona-build pipeline.
- `ChatSession` and `ChatMessage`: conversation history and generated answer metadata.
- `User`: reserved for account-level expansion.

JSON columns are used for portable lists and structured metadata. Foreign-key indexes and source content hashes support lookup, deduplication, and caching.

### 5.5 Pydantic API contract

[`backend/app/schemas.py`](./backend/app/schemas.py) defines the request and response models. The frontend mirrors these structures in [`frontend/src/lib/types.ts`](./frontend/src/lib/types.ts), which keeps the REST contract explicit and typed.

## 6. Persona build pipeline

The build is coordinated by [`backend/app/services/job_manager.py`](./backend/app/services/job_manager.py). It runs as an asynchronous task and stores its state in the `jobs` table. Each stage emits a named SSE event and updates progress, current stage, statistics, and errors.

The 15 stages are:

1. Discover sources.
2. Validate source candidates.
3. Collect source data.
4. Process documents.
5. Process audio.
6. Transcribe speech.
7. Run OCR.
8. Clean text.
9. Run NLP analysis.
10. Generate embeddings.
11. Build the vector index.
12. Analyze communication and personality patterns.
13. Construct the persona profile.
14. Validate evidence.
15. Mark the persona ready.

The pipeline does actual work at each stage. It creates database source rows, chunks text, generates vectors, builds the per-persona index, and derives analysis outputs. In a future horizontally scaled deployment, the same stage functions and event contract can be moved to Celery or RQ workers backed by Redis.

## 7. Source discovery and identity resolution

### 7.1 Identity resolution

[`backend/app/services/identity.py`](./backend/app/services/identity.py) resolves an ambiguous name into candidate public figures before deep ingestion. Candidates may include name, profession, birth/death years, portrait, and summary. The user can use this step to avoid building a profile for the wrong person.

### 7.2 Source discovery

[`backend/app/services/source_discovery.py`](./backend/app/services/source_discovery.py) uses an adapter-style design. The default live adapter uses official public Wikipedia, Wikiquote, and Wikimedia APIs to collect:

- a summary;
- a portrait URL;
- plain article text;
- article sections as separate sources for retrieval diversity;
- documented quotations from Wikiquote.

The project does not bypass authentication, paywalls, robots restrictions, or platform protections. If live discovery fails, the application can fall back to the bundled demo adapter.

### 7.3 External APIs and why they are used

| External service/API | Configuration | What RePersona uses it for | Why it is used |
|---|---|---|---|
| Wikipedia Action API (`{lang}.wikipedia.org/w/api.php`) | No key | Resolve page titles, search names, and obtain article extracts. | Broad public biography and identity information through an official API. |
| Wikimedia REST summary API (`{lang}.wikipedia.org/api/rest_v1/page/summary/...`) | No key | Obtain a concise summary and portrait/thumbnail metadata. | A clean identity summary and public image URL for the UI. |
| Wikiquote Action API (`{lang}.wikiquote.org/w/api.php`) | No key | Collect documented quotation pages when available. | A separate quotation-oriented source for quote evidence. |
| Tavily Search API (`https://api.tavily.com/search`) | `SEARCH_PROVIDER=tavily` plus `SEARCH_API_KEY` | Discover supplementary authorised web sources and current-context results. | Focused web search for source expansion and present-day questions. |
| SerpAPI (`https://serpapi.com/search.json`) | `SEARCH_PROVIDER=serpapi` plus `SEARCH_API_KEY` | Alternative web/news search and current-context retrieval. | Google-style search results through an API. |
| YouTube Data API v3 (`https://www.googleapis.com/youtube/v3/search`) | `YOUTUBE_API_KEY` | Discover interviews, talks, and videos related to the person. | Expands collection beyond text pages; metadata is not treated as a transcript. |
| NewsAPI (`https://newsapi.org/v2/everything`) | `NEWS_API_KEY` | Add an independently indexed news view to current-context answers. | Supplements live links and publication dates for current questions. |
| Ollama (`LLM_BASE_URL`, normally `http://127.0.0.1:11434`) | Local model installation | Generate natural persona-conditioned answers with a local Llama model. | Keeps source material local and avoids hosted-model cost. |
| OpenAI-compatible `/v1/chat/completions` endpoint | `LLM_PROVIDER=openai_compatible` plus URL/key | Use a hosted or local compatible model. | Keeps the generation layer replaceable. |

All external providers are optional. When a provider is not configured, the application reports that fact and skips it instead of fabricating a successful result.

### 7.4 User-provided sources

[`backend/app/services/ingest.py`](./backend/app/services/ingest.py) and [`backend/app/routers/uploads.py`](./backend/app/routers/uploads.py) support:

- pasted text;
- plain text and Markdown files;
- PDF extraction through `pypdf`;
- image OCR through Tesseract and Pillow;
- audio/video transcription through Whisper-compatible packages and FFmpeg.

Uploaded material is stored through [`backend/app/services/storage.py`](./backend/app/services/storage.py), which supports local storage and S3-compatible storage. Content is deduplicated with SHA-256 hashes. If an optional dependency is missing, the API returns an explicit error instead of pretending that extraction succeeded.

## 8. Text processing and persona analysis

[`backend/app/services/nlp.py`](./backend/app/services/nlp.py) provides lightweight text cleaning, sentence splitting, chunking, tokenization, keyword extraction, and keyphrase grouping. Chunking keeps sentence boundaries and uses overlap so related context is not lost at chunk boundaries.

[`backend/app/services/persona_analysis.py`](./backend/app/services/persona_analysis.py) analyzes the collected chunks to derive:

- topics and frequent concepts;
- recurring themes and documented viewpoints;
- communication style and language patterns;
- source coverage;
- a co-occurrence knowledge graph;
- evidence-linked insights.

Insights are classified as `DOCUMENTED`, `OBSERVED`, `INFERRED`, or `UNKNOWN`. During evidence validation, a documented claim without supporting evidence can be downgraded. This helps separate source-backed claims from interpretation.

[`backend/app/services/timeline.py`](./backend/app/services/timeline.py) builds a documented timeline from lifespan data and dated sources. [`backend/app/services/coverage.py`](./backend/app/services/coverage.py) estimates which facets of the persona are well covered and suggests searches or sources that could fill gaps. Coverage is explicitly an estimate, not a scientific completeness score.

## 9. Embeddings, vector store, and retrieval

### 9.1 Embeddings

[`backend/app/services/embeddings.py`](./backend/app/services/embeddings.py) first attempts to use Sentence Transformers. If the package or model is unavailable, it uses a deterministic hashing/bag-of-words vectorizer. Both paths return normalized vectors with the same interface.

### 9.2 Vector storage

[`backend/app/services/vector_store.py`](./backend/app/services/vector_store.py) defines the vector-store interface and implementations. FAISS is preferred when installed; an in-memory pure-Python store is available as a fallback. [`index_registry`](./backend/app/services/vector_store.py) caches one index per persona and rebuilds lazily when needed.

### 9.3 Retrieval

[`backend/app/services/rag_engine.py`](./backend/app/services/rag_engine.py) follows this flow:

```text
Question
  -> question embedding
  -> top-k vector search
  -> lexical reranking for exact topic overlap
  -> source diversity preference
  -> EvidenceItem objects with provenance
  -> persona-conditioned prompt
  -> LLM/offline composer
  -> answer + coverage + limitations
```

The lexical reranking layer is important for short questions and for the offline hashing embedder. It reduces the chance that a vector collision or broadly related passage becomes the answer. The offline composer also selects sentences that match the actual question instead of blindly returning the first retrieved chunk.

## 10. Persona Reasoner and answer correctness

[`backend/app/services/persona_reasoner.py`](./backend/app/services/persona_reasoner.py) is the main reasoning layer above basic RAG. Its stages are:

1. Detect intent.
2. Classify the question.
3. Analyze temporal context.
4. Retrieve persona evidence.
5. Map relevant worldview concepts.
6. Choose an answer mode.
7. Retrieve current context when necessary.
8. Generate the answer.
9. Apply quotation and temporal safeguards.
10. Return a reasoning trace and citations.

The response contains more than a message. It may include evidence, coverage, limitations, provider, category, current-context status, citations, warnings, knowledge cutoff, worldview concepts, and a reasoning object for the UI.

### 10.1 Question classification

[`backend/app/services/question_classifier.py`](./backend/app/services/question_classifier.py) distinguishes:

- small talk;
- identity and biography;
- factual questions about a person;
- quotation requests;
- historical questions;
- opinion questions;
- current politics, news, society, and generic current events.

Current markers include terms such as “today,” “now,” “latest,” “currently,” “recent,” and near-present years. The classifier also handles several Hinglish markers such as “aaj kal” and “abhi.”

### 10.2 Historical Reality Guard

[`backend/app/services/temporal.py`](./backend/app/services/temporal.py) derives a knowledge boundary from the person's documented death date or year. If a question asks about an event after that boundary, the system cannot present the answer as historical memory. It switches to a current-context or simulated-perspective path and explicitly explains the limitation.

For example, a deceased persona can be asked how its documented worldview might apply to a present-day issue, but the output must say that this is a generated perspective and not something the person actually knew or said.

### 10.3 Response modes

- `evidence`: answer strictly from the retrieved material.
- `persona_simulation`: generate a first-person documented-perspective simulation.
- `historical`: stay inside the historical period and ignore post-cutoff information.
- `current_context`: combine fresh current facts with a clearly labelled simulated worldview perspective.

Generated text is labelled `SIMULATED_PERSONA_RESPONSE`. The system never marks generated text as a verified historical quotation. It only identifies evidence that appears to be from a quote source or is visibly quoted in source material.

## 11. Current-context retrieval

[`backend/app/services/current_context.py`](./backend/app/services/current_context.py) retrieves current facts from configured external providers such as Tavily, SerpAPI, and optionally NewsAPI. It is only used when classification or temporal analysis says that fresh context is needed.

The current-context path is intentionally conservative:

- no provider configured means current facts are unavailable;
- provider errors are surfaced as errors;
- empty search results remain empty;
- snippets retain source URLs, titles, domains, publication dates, and retrieval timestamps;
- historical persona evidence and live current facts are kept distinct in the response.

The system never fills missing current facts by guessing.

## 12. LLM and offline generation

[`backend/app/services/llm_provider.py`](./backend/app/services/llm_provider.py) supports:

- `demo`: deterministic local answer composer;
- `ollama`: local model generation;
- `openai_compatible`: compatible hosted or local endpoint;
- `auto`: probe Ollama quickly and fall back if it is unavailable.

The provider receives a persona-conditioned system prompt, recent conversation history, retrieved evidence, language instructions, and the selected response-mode guardrails.

### 12.1 Why Llama/Ollama is used

“Llama” is the language model family; “Ollama” is the local runtime that serves a Llama model through an HTTP API. The default model is configured as `llama3.2:3b`, although it can be changed through `LLM_MODEL`.

This combination is used because it can run locally, keeps source material on the developer's machine, avoids per-request hosted-model costs, and exposes a simple HTTP interface. It also produces more natural evidence-grounded language than a purely template-based answer composer.

Llama/Ollama is not required for the basic product. With `LLM_PROVIDER=demo`, the deterministic offline composer answers from retrieved evidence. With `LLM_PROVIDER=auto`, the system uses Ollama if reachable and otherwise returns a `demo(no-llm)` answer. This makes the project runnable on a fresh machine and prevents an unavailable model server from breaking chat.

The model is not treated as a source of facts. Retrieval supplies evidence, temporal guards restrict context, prompts prohibit invented quotations, and the response includes evidence and limitations. The LLM's role is mainly to interpret and express retrieved material naturally.

The prompt rules require the generator to:

- avoid claiming literal identity or consciousness;
- avoid inventing quotations, dates, and events;
- use evidence for factual accuracy;
- say when the evidence does not cover a question;
- use the requested English, Hindi, or Hinglish style;
- remain natural and conversational.

The public `complete()` function catches provider failures and returns a safe offline answer instead of crashing. The response identifies which provider actually produced the text.

## 13. Frontend architecture

The frontend uses Next.js 14 App Router, React 18, TypeScript, Tailwind CSS, Framer Motion, Lucide icons, Three.js, React Three Fiber, and Drei. Dependencies are defined in [`frontend/package.json`](./frontend/package.json).

### 13.1 Frontend pages

The main pages are:

- [`frontend/src/app/page.tsx`](./frontend/src/app/page.tsx): landing/start experience.
- [`frontend/src/app/explore/page.tsx`](./frontend/src/app/explore/page.tsx): browse and select personas.
- [`frontend/src/app/persona/build/[jobId]/page.tsx`](./frontend/src/app/persona/build/[jobId]/page.tsx): live build-progress screen.
- [`frontend/src/app/persona/[personaId]/page.tsx`](./frontend/src/app/persona/[personaId]/page.tsx): persona overview.
- [`frontend/src/app/persona/[personaId]/chat/page.tsx`](./frontend/src/app/persona/[personaId]/chat/page.tsx): conversation interface.
- [`frontend/src/app/persona/[personaId]/sources/page.tsx`](./frontend/src/app/persona/[personaId]/sources/page.tsx): source collection and uploads.
- [`frontend/src/app/persona/[personaId]/knowledge/page.tsx`](./frontend/src/app/persona/[personaId]/knowledge/page.tsx): knowledge graph, topics, or related analysis.
- [`frontend/src/app/persona/[personaId]/insights/page.tsx`](./frontend/src/app/persona/[personaId]/insights/page.tsx): derived insights and evidence context.
- [`frontend/src/app/settings/page.tsx`](./frontend/src/app/settings/page.tsx): provider and application settings.

### 13.2 Frontend API layer

[`frontend/src/lib/api.ts`](./frontend/src/lib/api.ts) is the single typed fetch layer. It handles:

- common JSON request headers;
- API base URL configuration through `NEXT_PUBLIC_API_BASE`;
- response parsing and `ApiError` conversion;
- persona creation and retrieval;
- chat requests;
- source text and file uploads;
- job retrieval and SSE URL construction;
- provider status;
- identity resolution;
- timeline, coverage, and conversation management.

The API layer keeps page components from duplicating URL construction and error handling.

### 13.3 Build-progress streaming

[`frontend/src/lib/useJobStream.ts`](./frontend/src/lib/useJobStream.ts) subscribes to `GET /api/jobs/{jobId}/stream` using `EventSource`. It understands the named pipeline events, snapshots, completion, failures, and PING keep-alives.

The hook also has a polling fallback. If SSE is unavailable or fails before completion, it calls `GET /api/jobs/{jobId}` periodically. It derives activity-feed entries only from actual backend stat changes and stage transitions, so the UI does not invent progress.

### 13.4 Main reusable components

Notable components include:

- [`frontend/src/components/ChatPanel.tsx`](./frontend/src/components/ChatPanel.tsx): chat interaction and response presentation.
- [`frontend/src/components/EvidencePanel.tsx`](./frontend/src/components/EvidencePanel.tsx): evidence, sources, provenance, and limitations.
- [`frontend/src/components/Timeline.tsx`](./frontend/src/components/Timeline.tsx): documented timeline display.
- [`frontend/src/components/Coverage.tsx`](./frontend/src/components/Coverage.tsx): coverage estimates and gaps.
- [`frontend/src/components/PipelineStages.tsx`](./frontend/src/components/PipelineStages.tsx): build-stage progress.
- [`frontend/src/components/build/ActivityFeed.tsx`](./frontend/src/components/build/ActivityFeed.tsx): source, document, embedding, and milestone activity.
- [`frontend/src/components/three/KnowledgeGraph3D.tsx`](./frontend/src/components/three/KnowledgeGraph3D.tsx): interactive knowledge graph.
- [`frontend/src/components/three/ReconstructionScene.tsx`](./frontend/src/components/three/ReconstructionScene.tsx): visual persona reconstruction scene.
- [`frontend/src/components/PersonaImage.tsx`](./frontend/src/components/PersonaImage.tsx): portrait or fallback identity presentation.
- [`frontend/src/components/EthicalNotice.tsx`](./frontend/src/components/EthicalNotice.tsx): simulation and source-use notice.

Three.js components are isolated under `components/three`, dynamically loaded where needed, quality-scaled for devices, and designed to respect reduced-motion preferences.

## 14. End-to-end chat flow

```text
User types question in ChatPanel
  -> frontend sendChat() in lib/api.ts
  -> POST /api/chat
  -> backend loads Persona and conversation session
  -> user message is persisted
  -> persona_reasoner.reason(...)
       -> classify question
       -> temporal analysis
       -> retrieve persona chunks
       -> rerank and build EvidenceItem list
       -> optionally retrieve current facts
       -> build guarded prompt
       -> call Ollama/OpenAI-compatible/demo provider
       -> assemble labels, citations, warnings, and reasoning
  -> assistant message is persisted
  -> typed ChatResponse returned
  -> ChatPanel renders answer
  -> EvidencePanel renders supporting material
```

## 15. Real-time build flow

```text
POST /api/personas/create
  -> create Persona(status=building)
  -> create Job(status=pending)
  -> start async JobManager task
  -> return persona summary + job

Frontend opens GET /api/jobs/{jobId}/stream
  -> receives SNAPSHOT
  -> receives named stage events
  -> updates progress and activity feed
  -> receives COMPLETED or FAILED
  -> navigates to the ready persona
```

The job state is persisted, so late subscribers and polling clients can recover the latest snapshot.

## 16. Storage and deployment

Local development uses SQLite and local filesystem storage. PostgreSQL and S3-compatible object storage are supported for production-style deployment.

The intended deployment topology is:

```text
Frontend: Vercel or another Node-compatible host
Backend: container or Python service host
Workers: Celery/RQ plus Redis if background scale is required
Database: managed PostgreSQL
Vector store: FAISS locally, or a scalable vector database later
Files: local storage for development, S3-compatible storage in production
```

[`docker-compose.yml`](./docker-compose.yml) provides a local container topology with PostgreSQL, the API, and frontend.

### 16.1 Docker and Docker Compose in this project

Docker is an optional reproducible deployment path. The normal local workflow can use a Python virtual environment and npm directly, while Docker packages the same application into isolated services.

[`docker-compose.yml`](./docker-compose.yml) defines:

| Compose service | Image/build | Port | Role |
|---|---|---:|---|
| `db` | `postgres:16-alpine` | 5432 | PostgreSQL database with a health check and named `pgdata` volume. |
| `backend` | [`backend/Dockerfile`](./backend/Dockerfile) | 8000 | Python 3.11 FastAPI service connected to PostgreSQL. |
| `frontend` | [`frontend/Dockerfile`](./frontend/Dockerfile) | 3000 | Multi-stage Next.js 14 production image served with Node. |
| `redis` | `redis:7-alpine` (commented) | 6379 | Optional future queue backend for Celery/RQ workers. |

The backend container waits for the PostgreSQL health check before starting. The Compose backend currently uses `LLM_PROVIDER=demo` and `VECTOR_DB=memory`, so the default stack is deterministic and does not require Ollama or heavy neural packages. Production can change these values and attach a model service or external provider.

The backend Docker image installs lightweight Python requirements. OCR and Whisper system dependencies are not installed by default; they must be added when those optional ingestion capabilities are enabled. The frontend image uses three stages: dependency installation, Next.js build, and a production runner image.

Useful Docker commands:

```bash
docker compose up --build       # build and start PostgreSQL, API, and frontend
docker compose down             # stop services and keep PostgreSQL data
docker compose down -v           # stop services and remove PostgreSQL data
```

### 16.2 Runtime choices by mode

| Mode | Database | Embeddings/vector store | Answer generation | External keys |
|---|---|---|---|---|
| Local zero-config | SQLite | Hashing lexical vectors + memory store | Demo composer, or Ollama if installed | None required |
| Local enhanced | SQLite/PostgreSQL | Sentence Transformers + FAISS | Ollama/Llama | Optional |
| Docker Compose default | PostgreSQL | Memory store | Demo composer | None required |
| Production-style | PostgreSQL | FAISS or external vector DB | Ollama, hosted compatible model, or another adapter | As required |

## 17. Configuration

Important backend settings are documented in [`backend/.env.example`](./backend/.env.example). The most important values are:

| Setting | Purpose |
|---|---|
| `SOURCE_MODE` | Select automatic/live discovery or the demo corpus. |
| `DEMO_MODE` | Enable the bundled demonstration persona at startup. |
| `DATABASE_URL` | Select SQLite or PostgreSQL. |
| `LLM_PROVIDER` | Select auto, demo, Ollama, or OpenAI-compatible generation. |
| `LLM_BASE_URL` | LLM endpoint URL. |
| `LLM_MODEL` | Model identifier. |
| `LLM_API_KEY` | Optional hosted-provider key, kept server-side. |
| `EMBEDDING_MODEL` | Sentence Transformer model when neural embeddings are installed. |
| `VECTOR_DB` | FAISS or in-memory vector store. |
| `SEARCH_PROVIDER` and `SEARCH_API_KEY` | Optional live current-context search. |
| `NEWS_API_KEY` | Optional news cross-check. |
| `YOUTUBE_API_KEY` | Optional interview discovery. |
| `CORS_ORIGINS` | Allowed frontend origins. |
| `NEXT_PUBLIC_API_BASE` | Frontend API base URL in `.env.local`. |

No key is required for the offline demo path. Missing optional providers are reported as not configured rather than simulated.

## 18. Safety and ethical design

The project intentionally includes several safeguards:

- It labels the product as an AI simulation.
- It avoids claiming consciousness, literal identity, or direct communication.
- It separates generated responses from verified historical quotations.
- It preserves source provenance and evidence metadata.
- It does not invent current facts when live retrieval is unavailable.
- It applies a knowledge cutoff for deceased people.
- It distinguishes documented claims, observations, inferences, and unknowns.
- It refuses to bypass access controls, authentication, paywalls, robots restrictions, or platform protections.
- It returns explicit errors when optional OCR, PDF, or transcription dependencies are unavailable.

The bundled demo corpus is synthetic paraphrased material. It exists to exercise the application flow, not to represent authentic historical speech.

## 19. Testing and validation

Backend tests are located in [`backend/tests/`](./backend/tests). They cover:

- API behavior;
- source discovery;
- demo pipeline construction;
- RAG retrieval and answer behavior;
- persona reasoning;
- question classification;
- historical and temporal guardrails;
- uploads and optional extraction paths.

The normal commands are:

```bash
cd backend
pytest

cd ../frontend
npm run lint
npm run build
```

The answer-correctness fix also added a regression test that verifies the offline composer selects a meditation sentence rather than returning an unrelated fear sentence when both are present in candidate evidence. The backend suite was run after that change and passed.

## 20. Current strengths

- Works offline in demo mode.
- Clear separation between frontend, API, services, and persistence.
- Evidence and provenance are first-class response data.
- Real-time build progress is persisted and streamed.
- Pluggable embeddings, vector stores, LLM providers, source providers, and storage.
- Historical reality and current-context guardrails are built into the reasoning layer.
- Supports text, documents, images, audio, and video ingestion paths.
- UI exposes sources, reasoning, coverage, timeline, graph, and ethical context instead of showing only an opaque chat answer.

## 21. Known limitations and future improvements

The current implementation is designed as a strong local/demo foundation. Important future improvements would be:

1. Add authentication and authorization before exposing it publicly.
2. Move long-running builds to a durable worker queue for horizontal scaling.
3. Add stronger hybrid retrieval with explicit BM25 or a production search engine.
4. Add reranking models and answer-level citation alignment.
5. Add contradiction detection across sources.
6. Add source-quality scoring and human review workflows.
7. Add multilingual source ingestion and multilingual semantic retrieval beyond the current language instructions.
8. Add production observability, tracing, metrics, and alerting.
9. Add rate limiting and request-size limits at the gateway in addition to the application middleware.
10. Add browser-level frontend tests and accessibility audits.
11. Add a secure secret manager and separate production configuration.
12. Improve current-context source verification and freshness policies.

## 22. Academic syllabus alignment: Computer Vision and NLP

The project was intended to combine topics from both Computer Vision and Deep Learning for Natural Language Processing. The current implementation has a strong NLP/RAG foundation and a practical multimedia-ingestion layer for Computer Vision. It is important to distinguish between topics that are already implemented, topics that are used through an optional dependency, and topics that are not yet part of the codebase.

### 22.1 Computer Vision syllabus mapping

| Computer Vision syllabus topic | Project connection | Current status |
|---|---|---|
| Role of computer vision in AI applications | The application can accept images and media as evidence for a persona and can extract information from them. | Implemented at the application level. |
| Image fundamentals, pixels, channels, color spaces | Image files are accepted as upload inputs and passed to the OCR pipeline. | Used indirectly by image/OCR libraries; no custom pixel-level model code. |
| Resizing, cropping, normalization | These are standard preprocessing operations for OCR/image processing. | Available through the Pillow/Tesseract integration when optional packages are installed; not a standalone experiment in the current UI. |
| Neural networks, perceptron, feedforward networks, activations, losses, optimization | These are theoretical foundations for deep vision models. | Not explicitly implemented as a training module in this project. |
| CNN convolution, filters, feature maps, padding, stride, pooling, receptive fields | CNNs are relevant to image understanding, but the current image path performs OCR rather than training a CNN. | Not currently implemented. |
| LeNet, AlexNet, VGG, ResNet, Inception | These architectures are not used by the current OCR or persona pipeline. | Not currently implemented. |
| Regularization, batch normalization, dropout, augmentation, scheduling, initialization, early stopping | These would be required for training a custom vision classifier. | Not currently implemented. |
| Transfer learning, ResNet, EfficientNet, MobileNet, feature extraction, fine-tuning | A future image-classification or portrait-classification module could use these models. | Not currently implemented. |
| Object detection, bounding boxes, IoU, NMS, R-CNN, YOLO, SSD, RetinaNet, mAP | The project does not currently detect objects or produce bounding boxes. | Not currently implemented. |
| Semantic and instance segmentation, U-Net, DeepLab, Mask R-CNN | The project does not create pixel masks or segmented regions. | Not currently implemented. |
| Vision Transformers, ViT, Swin Transformer | No transformer-based image encoder is currently used. | Not currently implemented. |
| VAEs, GANs, DCGAN, CycleGAN, StyleGAN, image generation, image-to-image translation, super-resolution | The project does not generate or transform images. | Not currently implemented. |
| CLIP image-text alignment | This would be useful for matching an uploaded image to persona topics, but it is not currently part of retrieval. | Not currently implemented. |
| Grad-CAM, saliency maps, interpretability | The current system provides text/source evidence explanations, not visual heatmaps. | Not currently implemented. |

#### Computer Vision capability that is currently present

The concrete Computer Vision-related feature is the optional OCR ingestion path in [`backend/app/services/media.py`](./backend/app/services/media.py). A user can upload an image, the backend stores it, applies OCR through Pillow/Tesseract, converts detected text into a source, chunks it, embeds it, and adds it to the persona's searchable evidence. The source then becomes available to the same RAG and citation pipeline as ordinary text.

The project also supports image/media metadata and portraits. Portraits are used for persona presentation, while uploaded images are evidence inputs. These are useful computer-vision-enabled product features, but they are not equivalent to training CNN, detection, segmentation, or generative-vision models.

#### Recommended Computer Vision extension for full syllabus coverage

To make the project a stronger Computer Vision practical project, add an `image_analysis` service with one or more of the following:

1. A pretrained ResNet/EfficientNet classifier for classifying uploaded source images.
2. Transfer learning with frozen and unfrozen layers, layer-wise learning rates, augmentation, dropout, batch normalization, and early stopping.
3. YOLO object detection that stores labels, confidence, bounding boxes, IoU, and mAP results as evidence metadata.
4. U-Net or DeepLab segmentation for document/portrait regions.
5. CLIP embeddings so image and text evidence can share a multimodal vector space.
6. Grad-CAM or saliency overlays shown in the Evidence panel for visual explainability.

Those additions would connect the project directly to CNNs, transfer learning, detection, segmentation, vision transformers, multimodal alignment, and visual interpretability from the syllabus.

### 22.2 NLP syllabus mapping

| NLP syllabus topic | Project connection | Current status |
|---|---|---|
| Origin, applications, language, grammar, morphology, syntax, semantics, NLP challenges | The project processes biography, articles, quotations, transcripts, and user text to create searchable persona knowledge. | Implemented as the product's NLP problem context; not a standalone linguistic research module. |
| Tokenization and normalization | [`backend/app/services/nlp.py`](./backend/app/services/nlp.py) tokenizes text, cleans whitespace, splits sentences, and normalizes content. | Implemented. |
| Stop-word removal | Shared stop-word lists are used by keyword extraction, lexical embeddings, and retrieval reranking. | Implemented. |
| Punctuation/noise handling | Text cleaning removes formatting noise, wiki markup, reference artifacts, and malformed fragments. | Implemented. |
| Stemming and lemmatization | The current lightweight NLP layer does not use a full stemmer or lemmatizer. | Partially implemented through normalization only. |
| Out-of-vocabulary handling | The hashing fallback can represent unseen tokens deterministically, while neural embeddings use a pretrained tokenizer/model. | Implemented through fallback design; not evaluated as a separate experiment. |
| Bag-of-Words and TF-IDF | The fallback embedding is a hashing/bag-of-words style vectorizer. | Bag-of-words style representation implemented; classic TF-IDF is not a separate stored feature. |
| Vector-space models and dense embeddings | Sentence Transformers can generate normalized dense vectors; the fallback produces normalized hashing vectors. | Implemented. |
| Word2Vec, CBOW, Skip-Gram, and GloVe | The current project does not train or load Word2Vec/GloVe specifically. | Not currently implemented. |
| PCA/t-SNE embedding visualization | The knowledge graph and topic views visualize derived knowledge, but there is no PCA/t-SNE word-embedding notebook or screen. | Not currently implemented. |
| RNN, LSTM, GRU, BiRNN sequence models | The project uses retrieval and transformer/LLM providers rather than training recurrent sequence models. | Not currently implemented. |
| Sentiment classification and text classification | The classifier detects question categories and intent, but it is a rule-based routing classifier, not an LSTM/GRU training experiment. | Rule-based intent classification implemented; deep sentiment model not implemented. |
| Teacher forcing and truncated BPTT | These are training methods for recurrent models and are not used by the current pipeline. | Not currently implemented. |
| Seq2seq encoder-decoder models | The project does not train a translation or summarization seq2seq model. | Not currently implemented. |
| Bahdanau and Luong attention | The prompt and LLM may internally use attention, but the project does not implement or train these mechanisms directly. | Not directly implemented. |
| BLEU and ROUGE evaluation | Chat responses are evaluated with evidence, coverage, limitations, and tests rather than BLEU/ROUGE. | Not currently implemented. |
| Transformer architecture and self-attention | Ollama/Llama and OpenAI-compatible providers are transformer-based language models; the project consumes them through APIs rather than implementing transformer blocks. | Used through external/pretrained model providers. |
| BPE and WordPiece tokenization | The selected LLM and Sentence Transformer internally tokenize text, but the project does not expose a custom tokenizer training pipeline. | Used internally by model libraries; not a standalone project module. |
| BERT, GPT, T5, masked language modeling, causal language modeling | Llama is used for causal generation when Ollama is available; compatible providers can expose other pretrained transformer models. | Llama/causal generation is supported; BERT/T5 training is not part of the current code. |
| Transfer learning and fine-tuning for NLP | The project uses pretrained embeddings and language models without fine-tuning them on the persona corpus. | Feature usage is implemented; fine-tuning is not. |
| Named Entity Recognition and question answering | Identity resolution and factual/person-question routing exist, but there is no dedicated BiLSTM/BERT NER trainer. | Application-level handling implemented; dedicated NER model not implemented. |
| Generative NLP, decoding, dialogue, reasoning, evaluation | Persona chat uses a generated response, conversation history, mode selection, temporal reasoning, and provider fallback. | Implemented through Llama/Ollama or compatible LLMs plus the reasoner. |
| Perplexity, human evaluation, explainability, hallucination analysis | The system exposes evidence, citations, limitations, reasoning traces, current-context status, and anti-fabrication rules. | Explainability and hallucination safeguards implemented; perplexity benchmark not implemented. |

#### NLP capability that is currently present

NLP is the strongest academic area in the current project. The complete implemented path is:

```text
Raw articles / quotations / transcripts / OCR text
  -> cleaning and sentence splitting
  -> tokenization and stop-word filtering
  -> chunking with overlap
  -> lexical or neural embeddings
  -> vector retrieval plus lexical reranking
  -> question classification and intent detection
  -> temporal analysis and current-context routing
  -> persona-conditioned generation
  -> evidence, citations, limitations, and reasoning trace
```

This directly demonstrates text preprocessing, numerical representation, embeddings, semantic retrieval, text classification, transformer/LLM usage, generative dialogue, hallucination mitigation, and explainability. The project does not currently demonstrate every classical NLP practical from the syllabus, such as training CBOW/Skip-Gram, BiLSTM NER, attention-based translation, ROUGE/BLEU benchmarking, or fine-tuning BERT.

### 22.3 Combined Computer Vision + NLP project story

The project can be presented as a multimodal evidence-grounded persona system:

```text
Text source        -> NLP cleaning/chunking/embeddings
PDF                -> PDF extraction -> NLP pipeline
Image              -> OCR -> NLP pipeline
Audio/video        -> Whisper transcription -> NLP pipeline
Portrait/media     -> visual UI and optional future CV analysis
All evidence       -> shared source database and RAG index
Question           -> NLP classification + temporal reasoning
Answer             -> LLM generation + evidence and citations
```

The current integration is therefore strongest where Computer Vision or speech converts unstructured media into text, after which the NLP/RAG system reasons over it. To claim full coverage of the Computer Vision syllabus, the project should additionally implement at least one trainable or pretrained vision task, such as transfer-learning image classification, YOLO detection, U-Net segmentation, CLIP image-text retrieval, or Grad-CAM explainability.

## 23. Final understanding of the project

RePersona is best understood as a source-aware persona research system, not a generic chatbot. Its value comes from the full chain:

```text
Public/user-provided material
  -> extraction and cleaning
  -> chunking and indexing
  -> profile and knowledge analysis
  -> question classification
  -> evidence retrieval
  -> temporal and ethical guardrails
  -> controlled generation
  -> answer with evidence, limits, and explanation
```

The frontend turns that chain into a visual product experience. The backend performs the source processing, database work, retrieval, reasoning, and generation. The database preserves the built persona and conversation history. The SSE layer makes the long-running build understandable to the user. Together these parts implement the original idea of exploring a documented historical or public figure through a transparent, evidence-grounded simulation.
