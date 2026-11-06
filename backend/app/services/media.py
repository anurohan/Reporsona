"""Media processing: speech-to-text (Whisper) and OCR (computer vision).

Real integrations with graceful degradation. When the optional dependencies are
not installed (the default demo environment), these functions report that the
capability is unavailable rather than crashing — the demo pipeline supplies text
directly, so the neural models are only needed for real audio/scanned inputs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.config import settings

logger = logging.getLogger("repersona.media")


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float
    confidence: float = 1.0


@dataclass
class TranscriptResult:
    segments: List[TranscriptSegment] = field(default_factory=list)
    language: str = ""
    available: bool = True
    note: str = ""

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.segments)


def transcribe_audio(path: str) -> TranscriptResult:
    """Transcribe an audio file with Whisper (faster-whisper preferred).

    Pipeline: audio -> Whisper -> timestamped segments. Falls back cleanly when
    Whisper is not installed.
    """
    try:
        from faster_whisper import WhisperModel  # type: ignore

        model = WhisperModel(settings.whisper_model, device=settings.whisper_device)
        segments, info = model.transcribe(path, vad_filter=True)
        segs = [
            TranscriptSegment(
                text=s.text.strip(),
                start=float(s.start or 0.0),
                end=float(s.end or 0.0),
                confidence=float(getattr(s, "avg_logprob", 0.0)),
            )
            for s in segments
        ]
        return TranscriptResult(segments=segs, language=getattr(info, "language", ""))
    except Exception as exc:  # noqa: BLE001
        logger.info("Whisper unavailable (%s) — skipping transcription.", exc)
        return TranscriptResult(
            available=False,
            note="Whisper not installed; install faster-whisper to transcribe audio/video.",
        )


@dataclass
class OcrResult:
    text: str = ""
    available: bool = True
    note: str = ""


def ocr_image(path: str) -> OcrResult:
    """Extract text from an image / scanned page.

    Pipeline: image -> preprocessing -> OCR -> text. We do NOT infer any
    psychological traits from images — OCR is used purely to read documents.
    """
    try:
        import pytesseract  # type: ignore
        from PIL import Image, ImageFilter, ImageOps  # type: ignore

        img = Image.open(path)
        img = ImageOps.grayscale(img)
        img = ImageOps.autocontrast(img)
        img = img.filter(ImageFilter.SHARPEN)
        text = pytesseract.image_to_string(img)
        return OcrResult(text=text.strip())
    except Exception as exc:  # noqa: BLE001
        logger.info("OCR unavailable (%s) — skipping.", exc)
        return OcrResult(
            available=False,
            note="pytesseract/Pillow not installed (and Tesseract binary required) for OCR.",
        )


def extract_pdf_text(path: str) -> Optional[str]:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(path)
        return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception as exc:  # noqa: BLE001
        logger.info("PDF text extraction unavailable (%s).", exc)
        return None
