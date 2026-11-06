from __future__ import annotations

import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, KnowledgeEdge, KnowledgeNode, Persona, Source
from app.schemas import (
    InsightOut,
    JobOut,
    KnowledgeEdgeOut,
    KnowledgeGraphOut,
    KnowledgeNodeOut,
    PersonaCreateRequest,
    PersonaCreateResponse,
    PersonaDetail,
    PersonaSummary,
    ProfileOut,
    SourceOut,
    TopicOut,
    TimelineEventOut,
    CoverageOut,
    ResolveRequest,
    ResolutionOut,
)
from app.models import ChatMessage, ChatSession
from app.services import coverage as coverage_service
from app.services import identity as identity_service
from app.services import timeline as timeline_service
from app.services.job_manager import job_manager
from app.services.source_discovery import slugify
from app.services.vector_store import index_registry

router = APIRouter(prefix="/personas", tags=["personas"])

# hold references so background build tasks are not garbage-collected
_build_tasks: set[asyncio.Task] = set()


@router.post("/create", response_model=PersonaCreateResponse, status_code=201)
async def create_persona(payload: PersonaCreateRequest, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")

    # Only the explicit "Use Demo Persona" action forces the bundled corpus.
    # A normal search/create collects real data live (Wikipedia) via the adapter.
    force_demo = payload.demo
    persona = Persona(name=name, slug=slugify(name), status="building",
                      is_demo=force_demo)
    db.add(persona)
    db.flush()

    job = Job(persona_id=persona.id, kind="persona_build", status="pending",
              stages=job_manager.initial_stages())
    db.add(job)
    db.commit()
    db.refresh(persona)
    db.refresh(job)
    task = asyncio.create_task(
        job_manager.run_build(job.id, persona.id, name, force_demo)
    )
    _build_tasks.add(task)
    task.add_done_callback(_build_tasks.discard)

    return PersonaCreateResponse(
        persona=PersonaSummary.model_validate(persona),
        job=JobOut.model_validate(job),
    )


@router.post("/resolve", response_model=ResolutionOut)
async def resolve_identity(payload: ResolveRequest):
    """Identity resolution (§8): return candidate public figures for a name so
    the user can disambiguate before deep ingestion begins."""
    result = await asyncio.to_thread(identity_service.resolve, payload.name, payload.limit)
    return ResolutionOut(**result.as_dict())


@router.get("", response_model=List[PersonaSummary])
def list_personas(db: Session = Depends(get_db)):
    rows = db.scalars(select(Persona).order_by(Persona.created_at.desc()))
    return [PersonaSummary.model_validate(p) for p in rows]


@router.delete("/{persona_id}", status_code=204)
def delete_persona(persona_id: str, db: Session = Depends(get_db)):
    """Delete a persona and everything derived from it.

    Persona relationships (sources, chunks, topics, profile, insights,
    knowledge nodes/edges) cascade automatically. Jobs and chat sessions have
    no ORM cascade, so remove them explicitly. The in-memory FAISS index is
    dropped too so a re-created persona doesn't reuse stale vectors.
    """
    persona = db.get(Persona, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # chat sessions + their messages
    session_ids = list(
        db.scalars(select(ChatSession.id).where(ChatSession.persona_id == persona_id))
    )
    if session_ids:
        db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).delete(
            synchronize_session=False
        )
        db.query(ChatSession).filter(ChatSession.persona_id == persona_id).delete(
            synchronize_session=False
        )

    # build jobs
    db.query(Job).filter(Job.persona_id == persona_id).delete(synchronize_session=False)

    db.delete(persona)  # cascades the rest
    db.commit()

    try:
        index_registry.drop(persona_id)
    except Exception:  # noqa: BLE001 — index may not exist; deletion still succeeded
        pass
    return None


def _get_persona(db: Session, persona_id: str) -> Persona:
    persona = db.get(Persona, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.get("/{persona_id}", response_model=PersonaDetail)
def get_persona(persona_id: str, db: Session = Depends(get_db)):
    persona = _get_persona(db, persona_id)
    detail = PersonaDetail.model_validate(persona)
    detail.source_count = db.query(Source).filter(Source.persona_id == persona.id).count()
    if persona.profile:
        detail.profile = ProfileOut.model_validate(persona.profile)
    detail.topics = [TopicOut.model_validate(t) for t in persona.topics]
    return detail


@router.get("/{persona_id}/sources", response_model=List[SourceOut])
def get_sources(persona_id: str, source_type: str | None = None, db: Session = Depends(get_db)):
    _get_persona(db, persona_id)
    q = select(Source).where(Source.persona_id == persona_id)
    if source_type:
        q = q.where(Source.source_type == source_type)
    return [SourceOut.model_validate(s) for s in db.scalars(q)]


@router.get("/{persona_id}/topics", response_model=List[TopicOut])
def get_topics(persona_id: str, db: Session = Depends(get_db)):
    persona = _get_persona(db, persona_id)
    return [TopicOut.model_validate(t) for t in sorted(persona.topics, key=lambda t: t.weight, reverse=True)]


@router.get("/{persona_id}/insights", response_model=List[InsightOut])
def get_insights(persona_id: str, db: Session = Depends(get_db)):
    persona = _get_persona(db, persona_id)
    return [InsightOut.model_validate(i) for i in persona.insights]


@router.get("/{persona_id}/knowledge-graph", response_model=KnowledgeGraphOut)
def get_knowledge_graph(persona_id: str, db: Session = Depends(get_db)):
    _get_persona(db, persona_id)
    nodes = db.scalars(select(KnowledgeNode).where(KnowledgeNode.persona_id == persona_id))
    edges = db.scalars(select(KnowledgeEdge).where(KnowledgeEdge.persona_id == persona_id))
    return KnowledgeGraphOut(
        nodes=[KnowledgeNodeOut.model_validate(n) for n in nodes],
        edges=[KnowledgeEdgeOut.model_validate(e) for e in edges],
    )


@router.get("/{persona_id}/timeline", response_model=List[TimelineEventOut])
def get_timeline(persona_id: str, db: Session = Depends(get_db)):
    """Documented timeline (§12) derived from lifespan + source dates."""
    persona = _get_persona(db, persona_id)
    return [TimelineEventOut(**e) for e in timeline_service.build_timeline(db, persona)]


@router.get("/{persona_id}/coverage", response_model=CoverageOut)
def get_coverage(persona_id: str, db: Session = Depends(get_db)):
    """Knowledge coverage estimates + suggested next searches (§21)."""
    persona = _get_persona(db, persona_id)
    return CoverageOut(**coverage_service.estimate_coverage(db, persona))
