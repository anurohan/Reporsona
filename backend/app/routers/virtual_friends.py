"""Virtual Friends router.

Endpoints:
  POST   /virtual-friends/                          — create
  GET    /virtual-friends/                          — list
  GET    /virtual-friends/{friend_id}               — detail
  DELETE /virtual-friends/{friend_id}               — delete

  POST   /virtual-friends/{friend_id}/transcripts/upload    — upload file
  POST   /virtual-friends/{friend_id}/transcripts/text      — paste text
  GET    /virtual-friends/{friend_id}/transcripts           — list
  DELETE /virtual-friends/{friend_id}/transcripts/{tid}     — delete

  POST   /virtual-friends/{friend_id}/transcripts/{tid}/select-speaker

  POST   /virtual-friends/{friend_id}/chat                        — chat
  GET    /virtual-friends/{friend_id}/conversations               — list sessions
  GET    /virtual-friends/{friend_id}/conversations/{sid}         — session messages
  DELETE /virtual-friends/{friend_id}/conversations/{sid}         — delete session

  GET    /virtual-friends/{friend_id}/memories                    — list insights
  DELETE /virtual-friends/{friend_id}/memories/{iid}             — delete insight
"""

from __future__ import annotations

import os
import re
import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Chunk,
    Persona,
    PersonaInsight,
    PersonaProfile,
    Source,
    VFChatMessage,
    VFChatSession,
    VFTranscript,
    VFImport,
    VirtualFriend,
    User,
)
from app.schemas import (
    EvidenceItem,
    TranscriptUploadResult,
    VFChatRequest,
    VFChatResponse,
    VFConversationOut,
    VFMemoryOut,
    VFMessageOut,
    VFSpeakerSelectRequest,
    VirtualFriendCreate,
    VirtualFriendSummary,
    ImportPreviewOut,
    ImportConfirmRequest,
    ImportConfirmOut,
)
from app.services import virtual_friend_analysis
from app.services.llm_provider import llm_provider
from app.services.transcript_parser import NormalizedConversation, ParseResult, ParsedMessage, parse_platform_export, parse_transcript
from app.services.vector_store import index_registry
from app.services import rag_engine
from app.services.nlp import STOPWORDS, tokenize
from app.services.auth import get_current_user

router = APIRouter(prefix="/virtual-friends", tags=["virtual-friends"], dependencies=[Depends(get_current_user)])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
SUPPORTED_EXTENSIONS = {".txt", ".json", ".csv"}

# Messages-per-chunk grouping for transcript ingestion
MESSAGES_PER_CHUNK = 7


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")[:100]


def _get_friend(db: Session, friend_id: str, user: User | None = None) -> VirtualFriend:
    vf = db.get(VirtualFriend, friend_id)
    if not vf or (user and vf.owner_id != user.id):
        raise HTTPException(status_code=404, detail="Virtual friend not found")
    return vf


def _get_persona(db: Session, vf: VirtualFriend) -> Persona:
    if not vf.persona_id:
        raise HTTPException(status_code=409, detail="Virtual friend has no linked persona")
    p = db.get(Persona, vf.persona_id)
    if not p:
        raise HTTPException(status_code=404, detail="Linked persona not found")
    return p


def _chunk_count_for_source(db: Session, source_id: str) -> int:
    return db.query(Chunk).filter(Chunk.source_id == source_id).count()


def _ingest_transcript(
    db: Session,
    persona: Persona,
    parse_result: ParseResult,
    target_speaker: str,
    filename: str,
    conversation_aware: bool = False,
    source_metadata: dict | None = None,
) -> tuple[Source, list[str], int]:
    """Create Source + Chunks from parsed messages.

    Target speaker messages form the main corpus. Other speaker messages are
    ingested as chat_context sources so the RAG engine has conversation context.
    Returns (source, total_chunks_added).
    """
    from app.models import Chunk as ChunkModel, Source as SourceModel
    from app.services.vector_store import index_registry

    # --- Main source for target speaker ---
    target_msgs = [m for m in parse_result.messages if m.sender.lower() == target_speaker.lower()]
    all_msgs = parse_result.messages

    # Group messages into chunks of MESSAGES_PER_CHUNK lines
    def _group_chunks(msgs: list, label: str) -> list[str]:
        chunks: list[str] = []
        for i in range(0, len(msgs), MESSAGES_PER_CHUNK):
            group = msgs[i: i + MESSAGES_PER_CHUNK]
            lines = []
            for m in group:
                ts = f" [{m.timestamp}]" if m.timestamp else ""
                lines.append(f"{m.sender}{ts}: {m.text}")
            chunks.append("\n".join(lines))
        return chunks

    target_chunks_text = _group_chunks(all_msgs if conversation_aware else target_msgs, target_speaker)
    context_msgs = [m for m in all_msgs if m.sender.lower() != target_speaker.lower()]
    context_chunks_text = _group_chunks(context_msgs, "context")

    # Create main source
    import hashlib
    combined_text = "\n".join(target_chunks_text)
    h = hashlib.sha256(combined_text.encode("utf-8")).hexdigest()

    src = SourceModel(
        persona_id=persona.id,
        title=filename or "Chat transcript",
        source_type="chat_transcript",
        author=target_speaker,
        provider="user_upload",
        access_type="user_provided",
        discovery_method="user_upload",
        content_hash=h,
        description=json.dumps(source_metadata or {}, ensure_ascii=False),
        processing_status="processed",
    )
    db.add(src)
    db.flush()

    total_added = 0
    for ordinal, text in enumerate(target_chunks_text):
        if text.strip():
            db.add(ChunkModel(
                persona_id=persona.id,
                source_id=src.id,
                text=text,
                ordinal=ordinal,
            ))
            total_added += 1

    # Create context source (other speakers for RAG context)
    if context_chunks_text and not conversation_aware:
        ctx_text = "\n".join(context_chunks_text)
        ctx_h = hashlib.sha256(ctx_text.encode("utf-8")).hexdigest()
        ctx_src = SourceModel(
            persona_id=persona.id,
            title=f"{filename} (context)",
            source_type="chat_context",
            author="conversation_context",
            provider="user_upload",
            access_type="user_provided",
            discovery_method="user_upload",
            content_hash=ctx_h,
            processing_status="processed",
        )
        db.add(ctx_src)
        db.flush()
        for ordinal, text in enumerate(context_chunks_text):
            if text.strip():
                db.add(ChunkModel(
                    persona_id=persona.id,
                    source_id=ctx_src.id,
                    text=text,
                    ordinal=ordinal,
                ))

    db.commit()
    index_registry.drop(persona.id)
    source_ids = [src.id]
    if context_chunks_text and not conversation_aware:
        source_ids.append(ctx_src.id)
    return src, source_ids, total_added


def _run_analysis(db: Session, persona: Persona, vf: VirtualFriend, parse_result: ParseResult, target_speaker: str) -> None:
    """Run virtual friend analysis and persist profile + personality."""
    profile_data, personality_summary = virtual_friend_analysis.extract_profile(
        db=db,
        persona_id=persona.id,
        messages=parse_result.messages,
        target_speaker=target_speaker,
    )

    # Update or create PersonaProfile
    if persona.profile:
        profile = persona.profile
        # Merge new insights
        profile.communication_style = list(profile.communication_style or []) + profile_data.get("communication_style", [])
        profile.recurring_themes = profile_data.get("recurring_themes", [])
        profile.documented_viewpoints = profile_data.get("documented_viewpoints", [])
        profile.frequent_concepts = profile_data.get("frequent_concepts", [])
        profile.language_patterns = profile_data.get("language_patterns", [])
        profile.source_coverage = profile_data.get("source_coverage", {})
        profile.uncertainties = profile_data.get("uncertainties", [])
    else:
        db.add(PersonaProfile(
            persona_id=persona.id,
            **profile_data,
        ))

    # Update VirtualFriend.personality
    vf.personality = personality_summary
    db.commit()


# ---------------------------------------------------------------------------
# VirtualFriend CRUD
# ---------------------------------------------------------------------------

@router.post("/", response_model=VirtualFriendSummary, status_code=201)
def create_virtual_friend(payload: VirtualFriendCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    slug = _slug(payload.name)

    # Create underlying Persona for RAG reuse
    persona = Persona(
        owner_id=user.id,
        name=payload.name,
        slug=slug,
        status="ready",
        is_demo=False,
        summary=f"Virtual friend simulation for {payload.name}.",
    )
    db.add(persona)
    db.flush()

    vf = VirtualFriend(
        owner_id=user.id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        avatar_color=payload.avatar_color,
        status="ready",
        persona_id=persona.id,
    )
    db.add(vf)
    db.commit()
    db.refresh(vf)
    return VirtualFriendSummary.model_validate(vf)


@router.get("/", response_model=list[VirtualFriendSummary])
def list_virtual_friends(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vfs = db.query(VirtualFriend).filter(VirtualFriend.owner_id == user.id).order_by(VirtualFriend.created_at.desc()).all()
    return [VirtualFriendSummary.model_validate(v) for v in vfs]


# ---------------------------------------------------------------------------
# Staged multi-platform imports
# ---------------------------------------------------------------------------

@router.post("/imports/preview", response_model=ImportPreviewOut, status_code=201)
async def preview_import(
    file: UploadFile = File(...),
    platform: str = Form("auto"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty export.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Export too large (max 50 MB).")
    filename = file.filename or "conversation-export.txt"
    extension = os.path.splitext(filename)[1].lower()
    if extension not in {".txt", ".json", ".html", ".htm", ".zip"}:
        raise HTTPException(status_code=415, detail="Accepted export types: TXT, JSON, HTML, or ZIP.")
    try:
        parsed = parse_platform_export(data, filename, platform)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    staged = VFImport(
        owner_id=user.id,
        platform=parsed.platform,
        filename=filename,
        conversation_id=parsed.conversation_id,
        participants=parsed.participants,
        normalized_messages=[
            {"sender": m.sender, "text": m.text, "timestamp": m.timestamp, "ordinal": m.ordinal}
            for m in parsed.messages
        ],
        source_metadata=parsed.source_metadata,
        parse_errors=parsed.parse_errors,
        status="preview",
    )
    db.add(staged)
    db.commit()
    return ImportPreviewOut(
        import_id=staged.id,
        platform=staged.platform,
        filename=staged.filename,
        conversation_id=staged.conversation_id,
        participants=staged.participants,
        message_count=len(parsed.messages),
        sample_messages=staged.normalized_messages[:8],
        parse_errors=staged.parse_errors,
        source_metadata=staged.source_metadata,
        status=staged.status,
    )


@router.post("/imports/{import_id}/confirm", response_model=ImportConfirmOut, status_code=201)
def confirm_import(import_id: str, payload: ImportConfirmRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    staged = db.get(VFImport, import_id)
    if not staged or staged.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Import preview not found")
    if staged.status == "confirmed":
        raise HTTPException(status_code=409, detail="Import has already been confirmed")
    if payload.target_speaker not in (staged.participants or []):
        raise HTTPException(status_code=422, detail=f"Select one of the detected participants: {staged.participants}")

    if payload.friend_id:
        vf = _get_friend(db, payload.friend_id, user)
    else:
        if not payload.friend_name or not payload.friend_name.strip():
            raise HTTPException(status_code=422, detail="friend_name is required when creating a new Virtual Friend")
        name = payload.friend_name.strip()
        persona = Persona(name=name, slug=_slug(name), status="ready", is_demo=False, summary=f"Virtual friend simulation for {name}.")
        db.add(persona)
        db.flush()
        vf = VirtualFriend(name=name, slug=_slug(name), description=payload.description, status="processing", persona_id=persona.id, owner_id=user.id)
        db.add(vf)
        db.flush()

    persona = _get_persona(db, vf)
    parsed_messages = [
        ParsedMessage(
            sender=item.get("sender", "Unknown"), text=item.get("text", ""), timestamp=item.get("timestamp"), ordinal=item.get("ordinal", index)
        )
        for index, item in enumerate(staged.normalized_messages)
    ]
    parsed = ParseResult(parsed_messages, staged.participants or [], staged.parse_errors or [], staged.platform)
    _, source_ids, chunks_added = _ingest_transcript(
        db, persona, parsed, payload.target_speaker, staged.filename,
        conversation_aware=True, source_metadata={"platform": staged.platform, "conversation_id": staged.conversation_id, **(staged.source_metadata or {})},
    )
    target_count = sum(1 for message in parsed_messages if message.sender.casefold() == payload.target_speaker.casefold())
    transcript = VFTranscript(
        friend_id=vf.id, filename=staged.filename, format=staged.platform,
        speakers=staged.participants, target_speaker=payload.target_speaker,
        message_count=target_count, parse_errors=staged.parse_errors,
        source_ids=source_ids, raw_text=json.dumps(staged.normalized_messages, ensure_ascii=False),
    )
    db.add(transcript)
    vf.total_transcripts = (vf.total_transcripts or 0) + 1
    vf.total_messages = (vf.total_messages or 0) + target_count
    _run_analysis(db, persona, vf, parsed, payload.target_speaker)
    vf.status = "ready"
    staged.friend_id = vf.id
    staged.status = "confirmed"
    db.commit()
    return ImportConfirmOut(
        import_id=staged.id, friend_id=vf.id, transcript_id=transcript.id,
        target_speaker=payload.target_speaker, message_count=target_count,
        chunks_added=chunks_added, status="ready",
    )


@router.delete("/imports/{import_id}", status_code=204)
def delete_staged_import(import_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    staged = db.get(VFImport, import_id)
    if not staged or staged.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Import preview not found")
    if staged.status == "confirmed":
        raise HTTPException(status_code=409, detail="Confirmed imports must be deleted from the Virtual Friend profile")
    db.delete(staged)
    db.commit()


@router.get("/{friend_id}", response_model=VirtualFriendSummary)
def get_virtual_friend(friend_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vf = _get_friend(db, friend_id, user)
    return VirtualFriendSummary.model_validate(vf)


@router.delete("/{friend_id}", status_code=204)
def delete_virtual_friend(friend_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vf = _get_friend(db, friend_id, user)
    persona_id = vf.persona_id

    # Drop vector index
    if persona_id:
        index_registry.drop(persona_id)

    db.delete(vf)
    db.flush()

    # Delete linked persona (cascades sources, chunks, insights, etc.)
    if persona_id:
        p = db.get(Persona, persona_id)
        if p:
            db.delete(p)

    db.commit()


# ---------------------------------------------------------------------------
# Transcript ingestion — shared logic
# ---------------------------------------------------------------------------

def _process_transcript(
    db: Session,
    vf: VirtualFriend,
    raw_bytes: bytes,
    filename: str,
    target_speaker: Optional[str],
) -> TranscriptUploadResult:
    # Parse
    try:
        parse_result = parse_transcript(raw_bytes, filename=filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Determine target speaker
    if target_speaker and target_speaker not in parse_result.speakers:
        raise HTTPException(
            status_code=422,
            detail=f"Target speaker '{target_speaker}' was not found. Available speakers: {parse_result.speakers}",
        )
    if not target_speaker:
        # Default to most frequent speaker
        target_speaker = parse_result.speakers[0] if parse_result.speakers else "Unknown"

    persona = _get_persona(db, vf)

    # Ingest
    src, source_ids, chunks_added = _ingest_transcript(
        db=db,
        persona=persona,
        parse_result=parse_result,
        target_speaker=target_speaker,
        filename=filename,
    )

    # Store VFTranscript record
    transcript = VFTranscript(
        friend_id=vf.id,
        filename=filename,
        format=parse_result.format_detected,
        speakers=parse_result.speakers,
        target_speaker=target_speaker,
        message_count=len([m for m in parse_result.messages if m.sender.lower() == target_speaker.lower()]),
        parse_errors=parse_result.parse_errors,
        source_ids=source_ids,
        raw_text=raw_bytes.decode("utf-8", errors="replace"),
    )
    db.add(transcript)
    db.flush()

    # Update VirtualFriend stats
    vf.total_transcripts = (vf.total_transcripts or 0) + 1
    vf.total_messages = (vf.total_messages or 0) + transcript.message_count
    db.flush()

    # Run analysis (non-fatal if fails)
    try:
        _run_analysis(db, persona, vf, parse_result, target_speaker)
    except Exception:
        pass

    db.commit()

    note = ""
    if not target_speaker or target_speaker == "Unknown":
        note = f"Could not detect speakers. Using first speaker. Available: {', '.join(parse_result.speakers)}"

    return TranscriptUploadResult(
        transcript_id=transcript.id,
        friend_id=vf.id,
        filename=filename,
        format=parse_result.format_detected,
        speakers=parse_result.speakers,
        target_speaker=target_speaker,
        message_count=transcript.message_count,
        chunks_added=chunks_added,
        parse_errors=parse_result.parse_errors,
        note=note,
    )


@router.post("/{friend_id}/transcripts/upload", response_model=TranscriptUploadResult)
async def upload_transcript(
    friend_id: str,
    file: UploadFile = File(...),
    target_speaker: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    vf = _get_friend(db, friend_id, user)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty file.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB).")

    filename = file.filename or "transcript.txt"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {ext or 'unknown'}. Accepted: .txt, .json, .csv",
        )

    return _process_transcript(db, vf, data, filename, target_speaker or None)


class _TextTranscriptPayload:
    """Body schema for the /text endpoint (as a plain Pydantic model)."""


from pydantic import BaseModel as _BM


class TextTranscriptPayload(_BM):
    text: str
    title: str = ""
    target_speaker: str = ""


@router.post("/{friend_id}/transcripts/text", response_model=TranscriptUploadResult)
def add_text_transcript(
    friend_id: str,
    payload: TextTranscriptPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    vf = _get_friend(db, friend_id, user)
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail="Text is empty.")
    return _process_transcript(
        db, vf,
        payload.text.encode("utf-8"),
        payload.title or "pasted_transcript.txt",
        payload.target_speaker or None,
    )


@router.get("/{friend_id}/transcripts")
def list_transcripts(friend_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_friend(db, friend_id, user)
    transcripts = db.query(VFTranscript).filter(VFTranscript.friend_id == friend_id).all()
    return [
        {
            "id": t.id,
            "friend_id": t.friend_id,
            "filename": t.filename,
            "format": t.format,
            "speakers": t.speakers,
            "target_speaker": t.target_speaker,
            "message_count": t.message_count,
            "parse_errors": t.parse_errors,
            "created_at": t.created_at.isoformat() if t.created_at else "",
        }
        for t in transcripts
    ]


@router.delete("/{friend_id}/transcripts/{transcript_id}", status_code=204)
def delete_transcript(friend_id: str, transcript_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vf = _get_friend(db, friend_id, user)
    t = db.get(VFTranscript, transcript_id)
    if not t or t.friend_id != friend_id:
        raise HTTPException(status_code=404, detail="Transcript not found")

    # Delete linked chunks from the persona's corpus
    persona = _get_persona(db, vf)
    # Delete only the sources owned by this transcript. Filenames are not
    # unique, so matching on title could delete another import.
    sources = [db.get(Source, source_id) for source_id in (t.source_ids or [])]
    for src in sources:
        if not src:
            continue
        db.query(Chunk).filter(Chunk.source_id == src.id).delete()
        db.delete(src)

    db.delete(t)
    # Rebuild index on next retrieval
    index_registry.drop(persona.id)
    vf.total_transcripts = max(0, (vf.total_transcripts or 1) - 1)
    db.commit()


@router.post("/{friend_id}/transcripts/{transcript_id}/reprocess", response_model=TranscriptUploadResult)
def reprocess_transcript(friend_id: str, transcript_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Rebuild derived chunks and profile data from the user's stored upload."""
    vf = _get_friend(db, friend_id, user)
    transcript = db.get(VFTranscript, transcript_id)
    if not transcript or transcript.friend_id != friend_id:
        raise HTTPException(status_code=404, detail="Transcript not found")
    if not transcript.raw_text:
        raise HTTPException(status_code=409, detail="This transcript cannot be reprocessed because its source text is unavailable.")

    persona = _get_persona(db, vf)
    for source_id in (transcript.source_ids or []):
        source = db.get(Source, source_id)
        if source:
            db.query(Chunk).filter(Chunk.source_id == source.id).delete()
            db.delete(source)
    db.flush()
    parsed = parse_transcript(transcript.raw_text.encode("utf-8"), filename=transcript.filename)
    target = transcript.target_speaker if transcript.target_speaker in parsed.speakers else parsed.speakers[0]
    _src, source_ids, chunks_added = _ingest_transcript(db, persona, parsed, target, transcript.filename)
    transcript.source_ids = source_ids
    transcript.speakers = parsed.speakers
    transcript.target_speaker = target
    transcript.message_count = sum(1 for m in parsed.messages if m.sender.lower() == target.lower())
    transcript.parse_errors = parsed.parse_errors
    _run_analysis(db, persona, vf, parsed, target)
    db.commit()
    return TranscriptUploadResult(
        transcript_id=transcript.id, friend_id=vf.id, filename=transcript.filename,
        format=parsed.format_detected, speakers=parsed.speakers, target_speaker=target,
        message_count=transcript.message_count, chunks_added=chunks_added,
        parse_errors=parsed.parse_errors, note="Transcript reprocessed successfully.",
    )


@router.post("/{friend_id}/transcripts/{transcript_id}/select-speaker")
def select_speaker(
    friend_id: str,
    transcript_id: str,
    payload: VFSpeakerSelectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_friend(db, friend_id, user)
    t = db.get(VFTranscript, transcript_id)
    if not t or t.friend_id != friend_id:
        raise HTTPException(status_code=404, detail="Transcript not found")
    if payload.target_speaker not in (t.speakers or []):
        raise HTTPException(
            status_code=422,
            detail=f"Speaker '{payload.target_speaker}' not in this transcript. Available: {t.speakers}",
        )
    t.target_speaker = payload.target_speaker
    db.commit()
    return {"transcript_id": t.id, "target_speaker": t.target_speaker}


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

def _build_vf_system_prompt(vf: VirtualFriend, persona: Persona) -> str:
    name = vf.name
    personality = vf.personality or {}
    comm_styles = personality.get("communication_style", [])
    lang_patterns = personality.get("language_patterns", [])
    topics = personality.get("frequent_topics", [])

    style_text = ""
    if comm_styles:
        style_text = "Their observed communication style: " + "; ".join(comm_styles[:3]) + "."
    topics_text = ""
    if topics:
        topics_text = "Topics they frequently discuss: " + "; ".join(topics[:3]) + "."
    lang_text = ""
    if lang_patterns:
        lang_text = "Language patterns: " + "; ".join(lang_patterns[:3]) + "."

    return (
        f"You are simulating the conversational style of {name}, a real person, based solely on "
        f"messages they have written that were uploaded to this system.\n\n"
        f"IMPORTANT RULES:\n"
        f"- You are NOT {name}. You are an AI simulation of how {name} communicates, based only on "
        f"the documented messages.\n"
        f"- Never claim to be the actual person or imply you share their consciousness or identity.\n"
        f"- Base all responses on the reference notes below (the uploaded messages). "
        f"Do not fabricate opinions, memories, or facts.\n"
        f"- If the uploaded messages don't address a topic, say: "
        f"\"I couldn't find evidence of {name} discussing this in the uploaded conversations.\"\n"
        f"- Reflect the person's natural tone and style as observed in their messages.\n"
        f"- Clearly frame responses as a simulation: speak naturally in their voice, but do not "
        f"pretend to have knowledge beyond the uploaded messages.\n\n"
        + (f"{style_text}\n" if style_text else "")
        + (f"{topics_text}\n" if topics_text else "")
        + (f"{lang_text}\n" if lang_text else "")
    )


def _coverage_to_confidence(coverage: str, evidence_count: int) -> str:
    if evidence_count == 0:
        return "INSUFFICIENT"
    if coverage == "HIGH":
        return "HIGH"
    if coverage == "MEDIUM":
        return "MEDIUM"
    return "LOW"


@router.post("/chat", response_model=VFChatResponse)
async def vf_chat(payload: VFChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vf = _get_friend(db, payload.friend_id, user)

    persona = _get_persona(db, vf)

    # Session management
    session = db.get(VFChatSession, payload.session_id) if payload.session_id else None
    if session is None:
        session = VFChatSession(friend_id=vf.id, title=payload.message[:60])
        db.add(session)
        db.flush()

    # Persist user message
    db.add(VFChatMessage(session_id=session.id, role="user", content=payload.message))
    db.commit()

    # Retrieve evidence
    hits = rag_engine.retrieve(db, persona.id, payload.message)
    evidence: list[EvidenceItem] = []
    for chunk, source, score in hits:
        if score < rag_engine.MIN_SIMILARITY:
            continue
        evidence.append(EvidenceItem(
            chunk_id=chunk.id,
            source_id=chunk.source_id,
            source_title=source.title if source else "Chat transcript",
            source_type=source.source_type if source else "chat_transcript",
            publication_date=source.publication_date if source else "",
            url=source.url if source else "",
            timestamp=None,
            page=None,
            relevance=round(score, 4),
            text=chunk.text,
        ))

    # Similarity alone can return topical-but-wrong passages, especially for
    # short personal questions. Require a concrete lexical anchor before
    # treating a retrieved passage as evidence. This makes abstention
    # deterministic and prevents an embedding model from inventing coverage.
    if evidence:
        query_terms = {t for t in tokenize(payload.message) if t not in STOPWORDS and len(t) > 2}
        if query_terms and not any(
            query_terms & {t for t in tokenize(item.text) if t not in STOPWORDS and len(t) > 2}
            for item in evidence
        ):
            evidence = []

    coverage = rag_engine._coverage([e.relevance for e in evidence])
    confidence = _coverage_to_confidence(coverage, len(evidence))

    # Build specialized system prompt
    system = _build_vf_system_prompt(vf, persona)

    # Build context from evidence
    context_lines = [e.text for e in evidence[:6]]
    context = "\n\n".join(context_lines) if context_lines else "(no matching messages found)"

    # Build history
    hist_parts = []
    for turn in (payload.history or [])[-6:]:
        prefix = vf.name if turn.role == "assistant" else "User"
        hist_parts.append(f"{prefix}: {turn.content}")
    hist_text = "\n".join(hist_parts)

    if evidence:
        user_prompt = (
            f"{hist_text}\n\n" if hist_text else ""
        ) + (
            f"Reference — messages from {vf.name} in the uploaded chats "
            f"(use to stay accurate — do not quote directly):\n{context}\n\n"
            f"User says: \"{payload.message}\"\n\n"
            f"Reply in the voice and style of {vf.name}, based on the above messages."
        )
    else:
        user_prompt = (
            f"{hist_text}\n\n" if hist_text else ""
        ) + (
            f"User says: \"{payload.message}\"\n\n"
            f"No matching messages from {vf.name} were found in the uploaded transcripts for this topic. "
            f"Reply honestly that you couldn't find evidence of {vf.name} discussing this topic."
        )

    if not evidence:
        text = "I couldn't find enough evidence in the uploaded conversations to know what they would think about this."
        provider_used = "abstained"
    else:
        text, provider_used = await llm_provider.complete(
            system,
            user_prompt,
            demo_persona_name=vf.name,
            demo_question=payload.message,
            demo_evidence=[e.text for e in evidence],
            language=payload.language or "en",
        )

    limitations: list[str] = []
    if confidence == "INSUFFICIENT":
        limitations.append(f"No evidence found for this topic in {vf.name}'s uploaded conversations.")
    elif confidence == "LOW":
        limitations.append("Low evidence coverage — response may be generic.")
    limitations.append(f"This is a simulated response based on {vf.name}'s uploaded messages, not a real conversation.")

    evidence_out = evidence if payload.evidence_mode else []
    evidence_dicts = [e.model_dump() for e in evidence_out]

    # Persist assistant message
    db.add(VFChatMessage(
        session_id=session.id,
        role="assistant",
        content=text,
        evidence_coverage=coverage,
        evidence=evidence_dicts,
    ))
    db.commit()

    return VFChatResponse(
        session_id=session.id,
        message=text,
        evidence=evidence_out,
        evidence_coverage=coverage,
        limitations=limitations,
        provider=provider_used,
        confidence=confidence,
        reasoning_note=f"Based on {len(evidence)} retrieved message chunks from uploaded transcripts.",
    )


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

@router.get("/{friend_id}/conversations", response_model=list[VFConversationOut])
def list_conversations(friend_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_friend(db, friend_id, user)
    sessions = (
        db.query(VFChatSession)
        .filter(VFChatSession.friend_id == friend_id)
        .order_by(VFChatSession.created_at.desc())
        .all()
    )
    result = []
    for s in sessions:
        msg_count = db.query(VFChatMessage).filter(VFChatMessage.session_id == s.id).count()
        result.append(VFConversationOut(
            id=s.id,
            friend_id=s.friend_id,
            title=s.title,
            message_count=msg_count,
        ))
    return result


@router.get("/{friend_id}/conversations/{session_id}")
def get_conversation(friend_id: str, session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_friend(db, friend_id, user)
    session = db.get(VFChatSession, session_id)
    if not session or session.friend_id != friend_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = (
        db.query(VFChatMessage)
        .filter(VFChatMessage.session_id == session_id)
        .order_by(VFChatMessage.created_at)
        .all()
    )
    return {
        "id": session.id,
        "friend_id": session.friend_id,
        "title": session.title,
        "message_count": len(messages),
        "messages": [VFMessageOut.model_validate(m) for m in messages],
    }


@router.delete("/{friend_id}/conversations/{session_id}", status_code=204)
def delete_conversation(friend_id: str, session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_friend(db, friend_id, user)
    session = db.get(VFChatSession, session_id)
    if not session or session.friend_id != friend_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(session)
    db.commit()


# ---------------------------------------------------------------------------
# Memories (PersonaInsights of the linked persona)
# ---------------------------------------------------------------------------

@router.get("/{friend_id}/memories", response_model=list[VFMemoryOut])
def list_memories(friend_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vf = _get_friend(db, friend_id, user)
    if not vf.persona_id:
        return []
    insights = (
        db.query(PersonaInsight)
        .filter(PersonaInsight.persona_id == vf.persona_id)
        .all()
    )
    return [VFMemoryOut.model_validate(i) for i in insights]


@router.delete("/{friend_id}/memories/{insight_id}", status_code=204)
def delete_memory(friend_id: str, insight_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vf = _get_friend(db, friend_id, user)
    insight = db.get(PersonaInsight, insight_id)
    if not insight or insight.persona_id != vf.persona_id:
        raise HTTPException(status_code=404, detail="Memory not found")
    db.delete(insight)
    db.commit()
