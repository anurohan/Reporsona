"""Transcript parser for Virtual Friend feature.

Supports:
  - WhatsApp TXT exports (multiple date formats)
  - JSON transcripts (various key conventions)
  - CSV transcripts
  - Plain-text conversations

Returns a ParseResult dataclass with structured messages, speakers, errors,
and detected format.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional
from html.parser import HTMLParser


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ParsedMessage:
    sender: str
    text: str
    timestamp: Optional[str]
    ordinal: int


@dataclass
class ParseResult:
    messages: list[ParsedMessage]
    speakers: list[str]
    parse_errors: list[str]
    format_detected: str


@dataclass
class NormalizedConversation:
    """Platform-neutral conversation representation used by the import flow."""

    platform: str
    conversation_id: str
    participants: list[str]
    messages: list[ParsedMessage]
    parse_errors: list[str]
    source_metadata: dict = field(default_factory=dict)


SUPPORTED_PLATFORMS = {"whatsapp", "instagram", "telegram", "messenger"}


# ---------------------------------------------------------------------------
# System-message noise filters
# ---------------------------------------------------------------------------

_SYSTEM_PATTERNS = [
    re.compile(r"messages and calls are end.to.end encrypted", re.I),
    re.compile(r"<media omitted>", re.I),
    re.compile(r"this message was deleted", re.I),
    re.compile(r"you deleted this message", re.I),
    re.compile(r"missed (voice|video) call", re.I),
    re.compile(r"changed the subject", re.I),
    re.compile(r"changed the group", re.I),
    re.compile(r"added you", re.I),
    re.compile(r"left$", re.I),
    re.compile(r"joined using this group's invite link", re.I),
    re.compile(r"changed their phone number", re.I),
    re.compile(r"security code changed", re.I),
    re.compile(r"tap to learn more", re.I),
    re.compile(r"^null$", re.I),
    re.compile(r"^\s*$"),
]


def _is_system_message(text: str) -> bool:
    t = text.strip()
    for pat in _SYSTEM_PATTERNS:
        if pat.search(t):
            return True
    return False


# ---------------------------------------------------------------------------
# WhatsApp format detection & parsing
# ---------------------------------------------------------------------------

# Pattern 1: [12/11/2024, 10:30:45 AM] Alice: Hello
_WA_BRACKET = re.compile(
    r"^\[(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\]\s+([^:]+?):\s+(.+)$"
)
# Pattern 2: 12/11/2024, 10:30 - Alice: Hello
_WA_DASH = re.compile(
    r"^(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\s*-\s+([^:]+?):\s+(.+)$"
)
# Continuation line (no timestamp, no "sender:" prefix)
_WA_CONTINUATION = re.compile(r"^(?!\d{1,2}[/.\-])(?!\[)(.+)$")


def _try_whatsapp(raw: str) -> Optional[ParseResult]:
    errors: list[str] = []
    messages: list[ParsedMessage] = []
    ordinal = 0
    last_msg: Optional[ParsedMessage] = None
    matched_lines = 0

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        m = _WA_BRACKET.match(line) or _WA_DASH.match(line)
        if m:
            matched_lines += 1
            ts, sender, text = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
            if _is_system_message(text) or _is_system_message(sender):
                last_msg = None
                continue
            last_msg = ParsedMessage(sender=sender, text=text, timestamp=ts, ordinal=ordinal)
            messages.append(last_msg)
            ordinal += 1
        elif last_msg is not None:
            # Could be a continuation of the previous message
            last_msg.text += "\n" + line

    if matched_lines < 2:
        return None

    return _build_result(messages, errors, "whatsapp")


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

_JSON_SENDER_KEYS = ("sender", "from", "author", "name", "user", "speaker")
_JSON_TEXT_KEYS = ("message", "text", "content", "body", "msg")
_JSON_TS_KEYS = ("timestamp", "date", "time", "created_at", "datetime", "sent_at")


def _extract_json_field(obj: dict, keys: tuple) -> str:
    for k in keys:
        if k in obj and obj[k] is not None:
            return str(obj[k]).strip()
    return ""


def _try_json(raw: str) -> Optional[ParseResult]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    # Support top-level list or {"messages": [...]}
    if isinstance(data, dict):
        for key in ("messages", "data", "conversation", "chat"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            return None

    if not isinstance(data, list) or len(data) == 0:
        return None

    errors: list[str] = []
    messages: list[ParsedMessage] = []
    ordinal = 0

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        sender = _extract_json_field(item, _JSON_SENDER_KEYS)
        text = _extract_json_field(item, _JSON_TEXT_KEYS)
        ts = _extract_json_field(item, _JSON_TS_KEYS)

        if not text:
            errors.append(f"Row {i}: no message text")
            continue
        if not sender:
            sender = "Unknown"

        if _is_system_message(text):
            continue

        messages.append(ParsedMessage(sender=sender, text=text, timestamp=ts or None, ordinal=ordinal))
        ordinal += 1

    if not messages:
        return None

    return _build_result(messages, errors, "json")


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

_CSV_SENDER_KEYS = {"sender", "from", "author", "name", "user", "speaker"}
_CSV_TEXT_KEYS = {"message", "text", "content", "body", "msg"}
_CSV_TS_KEYS = {"timestamp", "date", "time", "created_at", "datetime"}


def _try_csv(raw: str) -> Optional[ParseResult]:
    try:
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
    except Exception:
        return None

    if not rows:
        return None

    fieldnames = [f.lower().strip() for f in (reader.fieldnames or [])]

    sender_col = next((f for f in fieldnames if f in _CSV_SENDER_KEYS), None)
    text_col = next((f for f in fieldnames if f in _CSV_TEXT_KEYS), None)
    ts_col = next((f for f in fieldnames if f in _CSV_TS_KEYS), None)

    if not text_col:
        return None

    errors: list[str] = []
    messages: list[ParsedMessage] = []
    ordinal = 0

    # Build a mapping from lowercase field name to actual field name
    field_map: dict[str, str] = {}
    for f in (reader.fieldnames or []):
        field_map[f.lower().strip()] = f

    real_sender_col = field_map.get(sender_col) if sender_col else None
    real_text_col = field_map.get(text_col) if text_col else None
    real_ts_col = field_map.get(ts_col) if ts_col else None

    for i, row in enumerate(rows):
        text = (row.get(real_text_col) or "").strip() if real_text_col else ""
        sender = (row.get(real_sender_col) or "").strip() if real_sender_col else "Unknown"
        ts = (row.get(real_ts_col) or "").strip() if real_ts_col else None

        if not text:
            errors.append(f"Row {i+1}: empty message")
            continue
        if _is_system_message(text):
            continue

        messages.append(ParsedMessage(sender=sender or "Unknown", text=text, timestamp=ts or None, ordinal=ordinal))
        ordinal += 1

    if not messages:
        return None

    return _build_result(messages, errors, "csv")


# ---------------------------------------------------------------------------
# Plain-text fallback: "Name: message" lines
# ---------------------------------------------------------------------------

_PLAIN_LINE = re.compile(r"^([A-Za-z0-9 _\-]{1,50}):\s+(.+)$")


def _try_plain(raw: str) -> Optional[ParseResult]:
    errors: list[str] = []
    messages: list[ParsedMessage] = []
    ordinal = 0

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _PLAIN_LINE.match(line)
        if m:
            sender, text = m.group(1).strip(), m.group(2).strip()
            if _is_system_message(text):
                continue
            messages.append(ParsedMessage(sender=sender, text=text, timestamp=None, ordinal=ordinal))
            ordinal += 1

    if len(messages) < 2:
        return None

    return _build_result(messages, errors, "text")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _build_result(messages: list[ParsedMessage], errors: list[str], fmt: str) -> ParseResult:
    # Deduplicate consecutive identical messages from same sender
    deduped: list[ParsedMessage] = []
    for msg in messages:
        if deduped and deduped[-1].sender == msg.sender and deduped[-1].text == msg.text:
            continue
        deduped.append(msg)

    # Re-assign ordinals
    for i, m in enumerate(deduped):
        m.ordinal = i

    # Detect speakers sorted by frequency
    counts: Counter = Counter(m.sender for m in deduped)
    speakers = [s for s, _ in counts.most_common()]

    return ParseResult(messages=deduped, speakers=speakers, parse_errors=errors, format_detected=fmt)


def _decode_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "windows-1252", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_transcript(data: bytes | str, filename: str = "") -> ParseResult:
    """Parse a transcript from raw bytes or string.

    Tries formats in order: WhatsApp → JSON → CSV → plain text.
    Raises ValueError if nothing parseable is found.
    """
    if isinstance(data, bytes):
        raw = _decode_bytes(data)
    else:
        raw = data

    raw = raw.strip()
    if not raw:
        raise ValueError("Empty transcript — nothing to parse.")

    # Try each format
    ext = (filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    result: Optional[ParseResult] = None

    if ext == "json":
        result = _try_json(raw)
    elif ext == "csv":
        result = _try_csv(raw)
    elif ext in ("txt", ""):
        result = _try_whatsapp(raw) or _try_plain(raw)
    
    # If extension-hint didn't match, try all
    if result is None:
        result = (
            _try_whatsapp(raw)
            or _try_json(raw)
            or _try_csv(raw)
            or _try_plain(raw)
        )

    if result is None or not result.messages:
        raise ValueError(
            "Could not parse the transcript. Expected WhatsApp TXT export, "
            "JSON list, CSV with sender/message columns, or plain 'Speaker: message' lines."
        )

    return result


# ---------------------------------------------------------------------------
# Multi-platform export normalization
# ---------------------------------------------------------------------------

def detect_platform(filename: str, data: bytes | str = b"") -> str:
    name = (filename or "").lower()
    if name.endswith(".zip"):
        return "whatsapp" if "whatsapp" in name else "auto"
    if "whatsapp" in name:
        return "whatsapp"
    text = data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else data
    lowered = text.lower()
    if '"messages"' in lowered and ("sender_name" in lowered or "timestamp_ms" in lowered):
        return "messenger" if "messenger" in name or "facebook" in name else "instagram"
    if '"from_id"' in lowered or '"type":"personal_chat"' in lowered:
        return "telegram"
    return "auto"


def _message_text(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "".join(_message_text(v.get("text", "") if isinstance(v, dict) else v) for v in value).strip()
    if isinstance(value, dict):
        return _message_text(value.get("text", value.get("content", "")))
    return ""


def _dedupe_normalized(messages: list[ParsedMessage]) -> list[ParsedMessage]:
    seen: set[tuple[str, str, str]] = set()
    output: list[ParsedMessage] = []
    for message in messages:
        key = (message.sender.casefold(), message.timestamp or "", message.text.casefold())
        if not message.text or key in seen or _is_system_message(message.text):
            continue
        seen.add(key)
        output.append(message)
    for index, message in enumerate(output):
        message.ordinal = index
    return output


def _normalized(platform: str, messages: list[ParsedMessage], errors: list[str], conversation_id: str, metadata: dict | None = None) -> NormalizedConversation:
    messages = _dedupe_normalized(messages)
    participants = [name for name, _ in Counter(m.sender for m in messages).most_common()]
    return NormalizedConversation(platform, conversation_id, participants, messages, errors, metadata or {})


def _parse_social_json(raw: str, platform: str) -> NormalizedConversation:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed {platform} JSON export: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected a {platform} export object.")
    rows = data.get("messages")
    if not isinstance(rows, list):
        for key in ("data", "conversation", "chat"):
            if isinstance(data.get(key), list):
                rows = data[key]
                break
    if not isinstance(rows, list):
        raise ValueError(f"Could not find messages in the {platform} JSON export.")
    errors: list[str] = []
    messages: list[ParsedMessage] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"Message {index + 1}: unsupported record")
            continue
        sender = str(row.get("sender_name") or row.get("from") or row.get("sender") or row.get("author") or "Unknown").strip()
        text = _message_text(row.get("content", row.get("text", row.get("message", ""))))
        if not text:
            attachment = row.get("type") or row.get("media") or row.get("photos") or row.get("share")
            if attachment:
                text = f"[Attachment: {attachment if isinstance(attachment, str) else 'unsupported message type'}]"
            else:
                errors.append(f"Message {index + 1}: no text or supported attachment")
                continue
        timestamp = row.get("timestamp_ms") or row.get("timestamp") or row.get("date") or row.get("created_at")
        if isinstance(timestamp, (int, float)):
            from datetime import datetime, timezone
            timestamp = datetime.fromtimestamp(timestamp / 1000 if timestamp > 10_000_000_000 else timestamp, tz=timezone.utc).isoformat()
        messages.append(ParsedMessage(sender, text, str(timestamp) if timestamp else None, index))
    conversation_id = str(data.get("id") or data.get("thread_path") or data.get("name") or f"{platform}-import")
    participants = data.get("participants") or data.get("members") or []
    metadata = {"name": data.get("name", ""), "title": data.get("title", ""), "participants_raw": participants}
    return _normalized(platform, messages, errors, conversation_id, metadata)


class _SocialHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict] = []
        self.current: dict | None = None
        self.capture: str | None = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "")
        marker = f"{classes} {attrs_dict.get('id', '')}".lower()
        if self.current and self.capture == "timestamp" and attrs_dict.get("title"):
            self.current["timestamp"] = attrs_dict["title"]
        if any(key in marker for key in ("from_name", "sender", "a6-h")):
            if self.current and self.current.get("sender") and self.current.get("text"):
                self.blocks.append(self.current)
            self.current = {"sender": "", "text": "", "timestamp": attrs_dict.get("title", "")}
            self.capture = "sender"
        elif self.current and any(key in marker for key in ("text", "a6-i", "message")):
            self.capture = "text"
        elif self.current and "date" in marker:
            self.capture = "timestamp"

    def handle_data(self, data):
        if self.current and self.capture:
            self.current[self.capture] += data

    def handle_endtag(self, tag):
        # Social exports nest sender, text, and timestamp in one message
        # container. Do not finalize at an inner div: the timestamp often
        # follows the text block.
        if tag in {"body", "html"} and self.current and self.current.get("sender") and self.current.get("text"):
            self.blocks.append(self.current)
            self.current = None
            self.capture = None

    def close(self):
        super().close()
        if self.current and self.current.get("sender") and self.current.get("text"):
            self.blocks.append(self.current)
            self.current = None


def _parse_social_html(raw: str, platform: str) -> NormalizedConversation:
    parser = _SocialHTMLParser()
    try:
        parser.feed(raw)
        parser.close()
    except Exception as exc:
        raise ValueError(f"Malformed {platform} HTML export: {exc}") from exc
    messages = [ParsedMessage(str(row["sender"]).strip(), " ".join(row["text"].split()), row.get("timestamp") or None, index) for index, row in enumerate(parser.blocks)]
    if not messages:
        raise ValueError(f"Could not find sender/message blocks in the {platform} HTML export.")
    return _normalized(platform, messages, [], f"{platform}-html-import", {})


def _unzip_export(data: bytes, filename: str) -> tuple[bytes, str]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            files = [item for item in archive.infolist() if not item.is_dir() and item.file_size <= 50 * 1024 * 1024]
            candidates = [item for item in files if item.filename.lower().endswith((".txt", ".json", ".html", ".htm"))]
            if not candidates:
                raise ValueError("ZIP export contains no supported TXT, JSON, or HTML conversation file.")
            item = max(candidates, key=lambda entry: entry.file_size)
            return archive.read(item), item.filename
    except zipfile.BadZipFile as exc:
        raise ValueError("Malformed ZIP export.") from exc


def parse_platform_export(data: bytes | str, filename: str = "", platform: str = "auto") -> NormalizedConversation:
    """Parse an exported file into the common conversation schema.

    ZIP exports are unpacked in memory and only supported conversation content
    is read. No scraping or account access is performed.
    """
    if isinstance(data, str):
        raw_bytes = data.encode("utf-8")
    else:
        raw_bytes = data
    if not raw_bytes:
        raise ValueError("Empty export — nothing to parse.")
    if filename.lower().endswith(".zip"):
        raw_bytes, filename = _unzip_export(raw_bytes, filename)
    detected = platform.lower().strip() if platform else "auto"
    if detected == "auto":
        detected = detect_platform(filename, raw_bytes)
    if detected not in SUPPORTED_PLATFORMS:
        detected = "whatsapp" if filename.lower().endswith(".txt") else detected
    if detected == "whatsapp":
        parsed = parse_transcript(raw_bytes, filename)
        return _normalized("whatsapp", parsed.messages, parsed.parse_errors, f"whatsapp-{filename or 'import'}", {"filename": filename})
    raw = _decode_bytes(raw_bytes)
    if filename.lower().endswith((".html", ".htm")):
        return _parse_social_html(raw, detected)
    return _parse_social_json(raw, detected)
