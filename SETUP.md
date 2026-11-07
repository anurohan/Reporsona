# RePersona — Setup Guide

This guide covers local development, environment configuration, optional
providers, the database, and troubleshooting. For the system design see
[`ARCHITECTURE.md`](./ARCHITECTURE.md); for a feature overview see
[`README.md`](./README.md).

RePersona runs in two modes:

- **Local mode (default)** — no paid API. Wikipedia/Wikiquote discovery, the
  offline lexical embedder, an in-memory / FAISS vector store, and either Ollama
  or the offline composer. Everything works with zero keys.
- **Enhanced mode** — optional keys unlock live web search (Tavily/SerpAPI),
  YouTube discovery, hosted LLMs, and news enrichment. Missing keys are reported
  as *not configured* on Settings → Providers and are skipped, never faked.

---

## 1. Prerequisites

- Python 3.11+
- Node.js 18+ (npm)
- (optional) Ollama for local LLM generation — https://ollama.com
- (optional) `tesseract-ocr` + `ffmpeg` system packages for OCR / audio-video

## 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # demo-ready defaults
uvicorn app.main:app --reload        # http://localhost:8000  (docs at /docs)
```

On boot the backend creates the SQLite schema and seeds a ready **Osho** demo
persona.

## 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local           # NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev                          # http://localhost:3000
```

Production build: `npm run build && npm run start`.

## 4. One-click (Windows)

Double-click `START_REPERSONA.bat` in the project root. First run creates the
venv, installs backend + frontend deps, copies `.env` files, then opens Backend
and Frontend windows and launches the browser.

## 5. Environment variables

Full documented list lives in `backend/.env.example`. Highlights:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SOURCE_MODE` | `auto` | `auto`/`wikipedia` = live real data · `demo` = offline corpus |
| `WIKIPEDIA_LANG` | `en` | Wikipedia/Wikiquote language |
| `LLM_PROVIDER` | `auto` | `auto` \| `demo` \| `ollama` \| `openai_compatible` |
| `LLM_BASE_URL` | `http://127.0.0.1:11434` | Ollama / OpenAI-compatible endpoint |
| `LLM_MODEL` | `llama3.2:3b` | Generation model |
| `LLM_API_KEY` | _(empty)_ | Key for hosted OpenAI-compatible/Groq endpoints |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Neural embedder (falls back to lexical) |
| `VECTOR_DB` | `faiss` | `faiss` \| `memory` (auto-falls back to memory) |
| `DATABASE_URL` | `sqlite:///./repersona.db` | SQLite by default; PostgreSQL supported |
| `SEARCH_PROVIDER` | _(empty)_ | `""` \| `tavily` \| `serpapi` (live web search) |
| `SEARCH_API_KEY` | _(empty)_ | Tavily / SerpAPI key |
| `YOUTUBE_API_KEY` | _(empty)_ | YouTube Data API v3 (interview discovery) |
| `NEWS_API_KEY` | _(empty)_ | NewsAPI (current-context enrichment) |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |

Secrets live only in `.env` / `.env.local` (git-ignored). Never commit keys;
they are read server-side and never exposed to the frontend.

## 6. Optional API keys

| Provider | Required? | Get a key |
|----------|-----------|-----------|
| Wikipedia/Wikiquote | No key ever | built-in |
| Ollama (local LLM) | Optional | https://ollama.com |
| Tavily / SerpAPI (web search) | Optional | https://app.tavily.com · https://serpapi.com |
| YouTube Data API v3 | Optional | https://console.cloud.google.com/apis/credentials |
| NewsAPI | Optional | https://newsapi.org |
| OpenAI-compatible / Groq | Optional | provider dashboard → `LLM_API_KEY` |

No key is *required*: the app is fully functional in local/demo mode.

### Temporal guardrails and live current-context

RePersona now evaluates whether a question is asking for historical memory, present-day events, or a hypothetical projection. For deceased figures, the knowledge cutoff is bound to the documented lifespan, and any post-cutoff or current-event question is routed to the live web search path. This prevents the app from pretending a historical figure had knowledge they did not have.

If `SEARCH_PROVIDER` and `SEARCH_API_KEY` are configured, the app retrieves fresh current-context results through Tavily or SerpAPI (optionally cross-checked via NewsAPI). If they are not configured, the app surfaces the unavailable state and keeps the answer honest instead of fabricating missing current facts.

## 7. Database & migrations

Demo uses SQLite created on startup (`init_db()` → `create_all`). For PostgreSQL:

```bash
# set DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/repersona
cd backend
alembic revision --autogenerate -m "init"
alembic upgrade head
```

## 8. Enabling neural AI (optional)

Uncomment in `backend/requirements.txt` then reinstall:

```
sentence-transformers  faiss-cpu  numpy       # semantic embeddings + FAISS
faster-whisper                                # audio/video transcription
pytesseract  pillow  pypdf                     # OCR + PDF text
```

Install `tesseract-ocr` and `ffmpeg` at the OS level (see `backend/Dockerfile`).

## 9. Testing

```bash
cd backend
pytest                 # 42 tests: temporal guard, persona reasoner, discovery,
                       # pipeline, RAG, uploads, full API
cd ../frontend
npm run lint           # ESLint (Next.js)
npm run build          # type-check + production build
```

## 10. Troubleshooting

- **"Could not reach the RePersona service"** — the backend isn't running or
  `NEXT_PUBLIC_API_BASE` is wrong. Start uvicorn and confirm http://localhost:8000/api/health.
- **Provider shows "not configured"** — expected when its key is absent; add the
  key to `backend/.env` and restart. This is by design (§27), not an error.
- **No neural embeddings** — `sentence-transformers`/`faiss` not installed; the
  app auto-falls back to the offline lexical embedder + in-memory store.
- **Ollama not used** — ensure it is running at `LLM_BASE_URL`; with
  `LLM_PROVIDER=auto` the app falls back to the offline composer when unreachable.
- **CORS errors** — add your frontend origin to `CORS_ORIGINS`.
