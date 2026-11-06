from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ChatMessage, ChatSession, Persona
from app.schemas import (
    ChatRequest,
    ChatResponse,
    CurrentContextItem,
    EvidenceItem,
    TemporalContext,
)
from app.services import persona_reasoner

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    if len(payload.message) > settings.max_question_chars:
        raise HTTPException(status_code=422, detail="Question too long")

    persona = db.get(Persona, payload.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    if persona.status != "ready":
        raise HTTPException(status_code=409, detail="Persona is not ready yet")

    # session
    session = db.get(ChatSession, payload.session_id) if payload.session_id else None
    if session is None:
        session = ChatSession(persona_id=persona.id, title=payload.message[:60])
        db.add(session)
        db.flush()

    # persist user turn
    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message))
    db.commit()

    # -- persona reasoning pipeline (§16) --------------------------------- #
    result = await persona_reasoner.reason(
        db, persona, payload.message,
        history=payload.history, mode=payload.mode, language=payload.language,
    )

    evidence_items = result.evidence if payload.evidence_mode else []
    evidence = [e.model_dump() for e in evidence_items]

    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content=result.message,
            evidence_coverage=result.evidence_coverage,
            evidence=evidence,
        )
    )
    db.commit()

    return ChatResponse(
        session_id=session.id,
        message=result.message,
        evidence=[EvidenceItem(**e) for e in evidence],
        evidence_coverage=result.evidence_coverage,
        limitations=result.limitations,
        provider=result.provider,
        response_type=result.response_type,
        mode=result.mode,
        requested_mode=result.requested_mode,
        intent=result.intent,
        temporal=TemporalContext(**result.temporal) if result.temporal else None,
        worldview_concepts=result.worldview_concepts,
        reasoning=result.reasoning,
        category=result.category,
        requires_current_context=result.requires_current_context,
        current_context_used=result.current_context_used,
        current_context_status=result.current_context_status,
        current_context=[CurrentContextItem(**c) for c in result.current_context],
        citations=result.citations,
        warnings=result.warnings,
        knowledge_cutoff=result.knowledge_cutoff,
    )
