"""Conversation memory endpoints (§20).

List, inspect, rename and delete chat conversations for a persona. Conversations
and their messages are already persisted by the /chat endpoint; this router lets
the UI manage them (sidebar, rename, delete, resume).
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatMessage, ChatSession, Persona
from app.schemas import (
    ConversationDetail,
    ConversationOut,
    ConversationRenameRequest,
    MessageOut,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _count(db: Session, session_id: str) -> int:
    return db.scalar(
        select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
    ) or 0


@router.get("", response_model=List[ConversationOut])
def list_conversations(persona_id: str, db: Session = Depends(get_db)):
    """List conversations for a persona, newest first."""
    if not db.get(Persona, persona_id):
        raise HTTPException(status_code=404, detail="Persona not found")
    rows = db.scalars(
        select(ChatSession)
        .where(ChatSession.persona_id == persona_id)
        .order_by(ChatSession.created_at.desc())
    )
    out: List[ConversationOut] = []
    for s in rows:
        item = ConversationOut.model_validate(s)
        item.message_count = _count(db, s.id)
        out.append(item)
    return out


@router.get("/{session_id}", response_model=ConversationDetail)
def get_conversation(session_id: str, db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")
    detail = ConversationDetail.model_validate(session)
    detail.messages = [MessageOut.model_validate(m) for m in session.messages]
    detail.message_count = len(detail.messages)
    return detail


@router.patch("/{session_id}", response_model=ConversationOut)
def rename_conversation(
    session_id: str, payload: ConversationRenameRequest, db: Session = Depends(get_db)
):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")
    session.title = payload.title.strip()
    db.commit()
    db.refresh(session)
    item = ConversationOut.model_validate(session)
    item.message_count = _count(db, session.id)
    return item


@router.delete("/{session_id}", status_code=204)
def delete_conversation(session_id: str, db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete(
        synchronize_session=False
    )
    db.delete(session)
    db.commit()
    return None
