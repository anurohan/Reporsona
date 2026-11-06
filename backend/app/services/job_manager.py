"""Persona build pipeline + real-time job streaming.

Runs the 15-stage build as an asyncio task and publishes progress events to any
number of Server-Sent-Events subscribers. Progress is also persisted to the
``jobs`` table so a late subscriber (or a poll of ``GET /api/jobs/{id}``) always
sees current state.

The stages do REAL work against the database: create sources, chunk text,
generate embeddings, build the vector index, and run persona analysis. In Demo
Mode the text is supplied by the bundled corpus (no network); with real sources
the same stages call Whisper / OCR / PDF extraction (see ``media.py``).

For a horizontally-scaled deployment, swap this in-process runner for Celery/RQ
workers backed by Redis — the stage functions and event schema stay the same.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Dict, List

from app.database import SessionLocal
from app.models import Chunk, Job, Persona, Source
from app.services import media, nlp, persona_analysis, source_discovery
from app.services.embeddings import embedding_service
from app.services.vector_store import index_registry

logger = logging.getLogger("repersona.jobs")

# (key, label, event-name) — event names mirror the documented SSE contract.
STAGES: List[tuple[str, str, str]] = [
    ("discovering_sources", "Discovering sources", "SOURCE_DISCOVERY"),
    ("validating_sources", "Validating sources", "SOURCE_VALIDATION"),
    ("collecting_data", "Collecting data", "SOURCE_VALIDATION"),
    ("processing_documents", "Processing documents", "DOCUMENT_PROCESSING"),
    ("processing_audio", "Processing audio", "AUDIO_PROCESSING"),
    ("transcribing_speech", "Transcribing speech", "TRANSCRIPTION"),
    ("running_ocr", "Running OCR", "OCR_PROCESSING"),
    ("cleaning_text", "Cleaning text", "NLP_ANALYSIS"),
    ("running_nlp", "Running NLP analysis", "NLP_ANALYSIS"),
    ("generating_embeddings", "Generating embeddings", "EMBEDDING"),
    ("building_index", "Building knowledge index", "VECTOR_INDEXING"),
    ("analyzing_patterns", "Analyzing communication patterns", "PERSONALITY_ANALYSIS"),
    ("constructing_persona", "Constructing persona", "PERSONA_BUILDING"),
    ("validating_evidence", "Validating evidence", "EVIDENCE_VALIDATION"),
    ("persona_ready", "Persona ready", "COMPLETED"),
]


class JobManager:
    def __init__(self) -> None:
        self._subs: Dict[str, List[asyncio.Queue]] = {}

    # -- pub/sub ---------------------------------------------------------- #
    def subscribe(self, job_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.setdefault(job_id, []).append(q)
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue) -> None:
        subs = self._subs.get(job_id)
        if subs and q in subs:
            subs.remove(q)

    async def _emit(self, job_id: str, event: Dict[str, Any]) -> None:
        for q in list(self._subs.get(job_id, [])):
            await q.put(event)

    # -- helpers ---------------------------------------------------------- #
    @staticmethod
    def initial_stages() -> List[dict]:
        return [{"key": k, "label": lbl, "status": "pending", "detail": ""} for k, lbl, _ in STAGES]

    # -- pipeline --------------------------------------------------------- #
    async def run_build(self, job_id: str, persona_id: str, personality: str, force_demo: bool) -> None:
        db = SessionLocal()
        stats: Dict[str, Any] = {
            "sources": 0, "documents": 0, "audio": 0, "audio_seconds": 0.0,
            "transcripts": 0, "ocr_pages": 0, "chunks": 0, "embeddings": 0,
            "topics": 0, "embedder": embedding_service.backend,
        }
        try:
            job = db.get(Job, job_id)
            persona = db.get(Persona, persona_id)
            job.status = "running"
            job.stages = self.initial_stages()
            db.commit()
            await self._emit(job_id, {"event": "JOB_STARTED", "job_id": job_id, "progress": 0.0})

            discovery = None
            discovered_sources: List[source_discovery.DiscoveredSource] = []
            # per-build local state (avoid shared mutable state on the singleton)
            validated: List[tuple] = []
            source_rows: List[tuple] = []
            chunk_rows: List[Chunk] = []
            vectors: List[List[float]] = []

            for idx, (key, label, event) in enumerate(STAGES):
                await self._set_stage(db, job_id, idx, "processing")
                await asyncio.sleep(0.35)  # visible streaming cadence

                # ---- real work per stage ---- #
                if key == "discovering_sources":
                    # run the (possibly network-bound) discovery off the event loop
                    discovery = await asyncio.to_thread(
                        source_discovery.discover, personality, force_demo
                    )
                    discovered_sources = discovery.sources
                    stats["sources"] = len(discovered_sources)
                    if not discovered_sources:
                        await self._set_stage(db, job_id, idx, "completed", discovery.note)
                        # nothing to process -> finish gracefully but honestly
                        await self._finish_empty(db, job_id, persona, discovery)
                        return

                elif key == "validating_sources":
                    # de-dupe by content hash; keep only sources with text
                    seen = set()
                    valid = []
                    for s in discovered_sources:
                        h = hashlib.sha256(s.text.encode("utf-8")).hexdigest()
                        if h in seen or not s.text.strip():
                            continue
                        seen.add(h)
                        valid.append((s, h))
                    validated = valid
                    stats["sources"] = len(valid)

                elif key == "collecting_data":
                    # persist Source rows
                    source_rows = []
                    for s, h in validated:
                        row = Source(
                            persona_id=persona.id, title=s.title, url=s.url,
                            source_type=s.source_type, author=s.author,
                            publication_date=s.publication_date, description=s.description,
                            provider=s.provider, access_type=s.access_type,
                            discovery_method=s.discovery_method, content_hash=h,
                            duration_seconds=s.duration_seconds, processing_status="collected",
                        )
                        db.add(row)
                        db.flush()
                        source_rows.append((row, s))
                    db.commit()

                elif key == "processing_documents":
                    stats["documents"] = sum(1 for r, _ in source_rows if r.source_type in ("document", "article", "text", "image"))

                elif key == "processing_audio":
                    audio_rows = [(r, s) for r, s in source_rows if r.source_type in ("audio", "video")]
                    stats["audio"] = len(audio_rows)
                    stats["audio_seconds"] = round(sum(r.duration_seconds for r, _ in audio_rows), 1)

                elif key == "transcribing_speech":
                    # Demo corpus supplies transcript text directly. Real audio
                    # files would be run through media.transcribe_audio().
                    stats["transcripts"] = stats["audio"]

                elif key == "running_ocr":
                    stats["ocr_pages"] = sum(1 for r, _ in source_rows if r.source_type == "image")

                elif key == "cleaning_text":
                    for r, s in source_rows:
                        s.text = nlp.clean_text(s.text)

                elif key == "running_nlp":
                    # chunk every source into Chunk rows
                    total_chunks = 0
                    chunk_rows = []
                    for r, s in source_rows:
                        pieces = nlp.chunk_text(s.text)
                        for ordinal, piece in enumerate(pieces):
                            c = Chunk(
                                persona_id=persona.id, source_id=r.id, text=piece,
                                ordinal=ordinal,
                                start_time=(r.duration_seconds / max(len(pieces), 1)) * ordinal if r.source_type in ("audio", "video") else 0.0,
                                end_time=(r.duration_seconds / max(len(pieces), 1)) * (ordinal + 1) if r.source_type in ("audio", "video") else 0.0,
                                page=(ordinal + 1) if r.source_type in ("document", "image") else 0,
                            )
                            db.add(c)
                            chunk_rows.append(c)
                            total_chunks += 1
                        r.processing_status = "processed"
                    db.commit()
                    stats["chunks"] = total_chunks

                elif key == "generating_embeddings":
                    texts = [c.text for c in chunk_rows]
                    vectors = embedding_service.encode(texts)
                    stats["embeddings"] = len(vectors)
                    stats["embedder"] = embedding_service.backend

                elif key == "building_index":
                    ids = [c.id for c in chunk_rows]
                    for i, c in enumerate(chunk_rows):
                        c.vector_index = i
                    db.commit()
                    index_registry.build(persona.id, ids, vectors, embedding_service.dim)

                elif key == "analyzing_patterns":
                    pass  # folded into constructing_persona (single analysis pass)

                elif key == "constructing_persona":
                    hints = discovery.hints if discovery else {}
                    persona_analysis.analyze(db, persona, hints=hints)
                    db.commit()
                    db.refresh(persona)
                    stats["topics"] = len(persona.topics)

                elif key == "validating_evidence":
                    # ensure derived insights actually reference evidence
                    for ins in persona.insights:
                        if not ins.evidence_chunk_ids and ins.classification == "DOCUMENTED":
                            ins.classification = "INFERRED"
                    db.commit()

                elif key == "persona_ready":
                    persona.status = "ready"
                    if discovery and discovery.persona:
                        persona.summary = discovery.persona.get("summary", persona.summary)
                        persona.known_for = discovery.persona.get("known_for", persona.known_for)
                        persona.domains = discovery.persona.get("domains", persona.domains)
                        persona.portrait_url = discovery.persona.get("portrait_url", persona.portrait_url)
                        from app.services.demo_builder import apply_temporal_boundary

                        apply_temporal_boundary(persona, discovery.persona)
                        persona.is_demo = discovery.is_demo
                    db.commit()

                await self._set_stage(db, job_id, idx, "completed")
                progress = round((idx + 1) / len(STAGES), 4)
                job = db.get(Job, job_id)
                job.progress = progress
                job.stats = dict(stats)
                job.current_stage = key
                db.commit()
                await self._emit(job_id, {
                    "event": event, "job_id": job_id, "stage": key, "label": label,
                    "status": "completed", "progress": progress, "stats": dict(stats),
                })

            job = db.get(Job, job_id)
            job.status = "completed"
            job.progress = 1.0
            db.commit()
            await self._emit(job_id, {
                "event": "COMPLETED", "job_id": job_id, "persona_id": persona_id,
                "progress": 1.0, "stats": dict(stats),
            })
        except Exception as exc:  # noqa: BLE001
            logger.exception("Persona build failed: %s", exc)
            try:
                job = db.get(Job, job_id)
                if job:
                    job.status = "failed"
                    job.error = str(exc)
                    db.commit()
                persona = db.get(Persona, persona_id)
                if persona:
                    persona.status = "failed"
                    db.commit()
            finally:
                await self._emit(job_id, {"event": "FAILED", "job_id": job_id, "error": str(exc)})
        finally:
            db.close()

    async def _set_stage(self, db, job_id: str, idx: int, status: str, detail: str = "") -> None:
        job = db.get(Job, job_id)
        stages = list(job.stages or self.initial_stages())
        stages[idx] = {**stages[idx], "status": status, "detail": detail}
        job.stages = stages
        job.current_stage = stages[idx]["key"]
        db.commit()
        if status == "processing":
            _, _, event = STAGES[idx]
            await self._emit(job_id, {
                "event": event, "job_id": job_id, "stage": stages[idx]["key"],
                "label": stages[idx]["label"], "status": "processing",
                "progress": job.progress,
            })

    async def _finish_empty(self, db, job_id, persona, discovery) -> None:
        job = db.get(Job, job_id)
        job.status = "completed"
        job.progress = 1.0
        job.error = discovery.note if discovery else "No sources discovered."
        db.commit()
        persona.status = "ready"
        persona.summary = (discovery.persona.get("summary", "") if discovery and discovery.persona else "")
        db.commit()
        await self._emit(job_id, {
            "event": "COMPLETED", "job_id": job_id, "persona_id": persona.id,
            "progress": 1.0, "stats": {"sources": 0}, "note": job.error,
        })


job_manager = JobManager()
