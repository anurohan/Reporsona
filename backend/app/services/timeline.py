"""Timeline engine (§12) — derive a persona timeline from documented data.

Events come only from real, stored data: the persona's documented birth/death
years and the publication dates of its sources. Nothing is invented; sources
without a parseable date are omitted rather than guessed. Each event carries
its provenance (source id/title) and a confidence label.
"""

from __future__ import annotations

import re
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Persona, Source

_YEAR_RE = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")


def _year_of(date_str: str) -> Optional[int]:
    m = _YEAR_RE.search(date_str or "")
    return int(m.group(1)) if m else None


def build_timeline(db: Session, persona: Persona) -> List[dict]:
    """Return a chronological list of documented timeline events."""
    events: List[dict] = []

    if persona.birth_year:
        events.append({
            "year": persona.birth_year, "date": str(persona.birth_year),
            "title": "Born", "description": f"{persona.name} was born.",
            "category": "birth", "confidence": "documented",
        })
    if persona.death_year:
        events.append({
            "year": persona.death_year, "date": str(persona.death_year),
            "title": "Died", "description": f"End of {persona.name}'s documented lifetime.",
            "category": "death", "confidence": "documented",
        })

    sources = db.scalars(select(Source).where(Source.persona_id == persona.id))
    for s in sources:
        yr = _year_of(s.publication_date)
        if yr is None:
            continue
        events.append({
            "year": yr, "date": s.publication_date,
            "title": s.title,
            "description": s.description or f"{s.source_type.title()} source.",
            "category": "source", "source_id": s.id, "source_title": s.title,
            "confidence": "documented",
        })

    events.sort(key=lambda e: (e.get("year") or 0, e.get("category") != "birth"))
    return events
