"""User-provided source ingestion endpoints.

Two real, non-faked paths to add material to an existing persona:

* ``POST /api/personas/{id}/sources/text``   — paste text (always works, offline).
* ``POST /api/personas/{id}/sources/upload`` — upload a file. Text/Markdown is
  decoded directly; PDFs go through text extraction; images through OCR; audio/
  video through Whisper. If the optional dependency for a given file type is not
  installed, the endpoint returns a clear 422 explaining what to install — it
  does NOT pretend to have processed the file.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chunk, Persona
from app.schemas import SourceOut, SourceTextRequest, UploadResult
from app.services import ingest, media
from app.services.storage import storage

router = APIRouter(prefix="/personas", tags=["uploads"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

TEXT_EXT = {".txt", ".md", ".markdown"}
PDF_EXT = {".pdf"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".webm", ".mov"}


def _persona(db: Session, persona_id: str) -> Persona:
    p = db.get(Persona, persona_id)
    if not p:
        raise HTTPException(status_code=404, detail="Persona not found")
    return p


def _chunk_count(db: Session, source_id: str) -> int:
    return db.query(Chunk).filter(Chunk.source_id == source_id).count()


@router.post("/{persona_id}/sources/text", response_model=UploadResult)
def add_text(persona_id: str, payload: SourceTextRequest, db: Session = Depends(get_db)):
    persona = _persona(db, persona_id)
    src = ingest.add_text_source(
        db, persona,
        title=payload.title or "Pasted text",
        text=payload.text,
        source_type=payload.source_type or "text",
        author=payload.author,
        url=payload.url,
        publication_date=payload.publication_date,
    )
    return UploadResult(
        source=SourceOut.model_validate(src),
        chunks_added=_chunk_count(db, src.id),
        extraction="text",
    )


@router.post("/{persona_id}/sources/upload", response_model=UploadResult)
async def upload_file(
    persona_id: str,
    file: UploadFile = File(...),
    title: str = Form(""),
    db: Session = Depends(get_db),
):
    persona = _persona(db, persona_id)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty file.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50MB).")

    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    display_title = title or filename

    text = ""
    segments = None
    duration = 0.0
    source_type = "document"
    extraction = "text"

    if ext in TEXT_EXT:
        text = data.decode("utf-8", errors="replace")
        source_type, extraction = "text", "text"

    elif ext in PDF_EXT:
        key = storage.save_bytes(data, filename, subdir=persona_id)
        text = media.extract_pdf_text(storage.local_path(key)) or ""
        source_type, extraction = "document", "pdf"
        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail="Could not extract text from the PDF (install 'pypdf', or the PDF may be scanned — upload as an image for OCR).",
            )

    elif ext in IMAGE_EXT:
        key = storage.save_bytes(data, filename, subdir=persona_id)
        result = media.ocr_image(storage.local_path(key))
        if not result.available:
            raise HTTPException(status_code=422, detail=result.note)
        text = result.text
        source_type, extraction = "image", "ocr"
        if not text.strip():
            raise HTTPException(status_code=422, detail="OCR found no readable text in the image.")

    elif ext in AUDIO_EXT:
        key = storage.save_bytes(data, filename, subdir=persona_id)
        result = media.transcribe_audio(storage.local_path(key))
        if not result.available:
            raise HTTPException(status_code=422, detail=result.note)
        segments = [{"text": s.text, "start": s.start, "end": s.end, "confidence": s.confidence} for s in result.segments]
        text = result.text
        duration = result.segments[-1].end if result.segments else 0.0
        source_type, extraction = "audio", "whisper"
        if not text.strip():
            raise HTTPException(status_code=422, detail="Transcription produced no text.")

    else:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {ext or 'unknown'}")

    src = ingest.add_text_source(
        db, persona,
        title=display_title, text=text, source_type=source_type,
        duration_seconds=duration, segments=segments,
    )
    return UploadResult(
        source=SourceOut.model_validate(src),
        chunks_added=_chunk_count(db, src.id),
        extraction=extraction,
    )
