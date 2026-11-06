"""Knowledge coverage estimates (§21).

Produces *estimates* — never presented as exact science — of how well the
collected corpus covers a set of standard biographical facets, plus suggested
next searches for weak areas. Estimates are derived from real signals: the
number of sources/chunks per facet, keyword presence, and source-type mix.
"""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chunk, Persona, Source

# facet -> keywords that, if present in the corpus, indicate coverage
_FACETS: Dict[str, List[str]] = {
    "Biography": ["born", "life", "childhood", "family", "grew up", "early"],
    "Career": ["work", "career", "founded", "led", "role", "profession"],
    "Ideas & Views": ["believe", "view", "idea", "concept", "philosophy", "think"],
    "Interviews": ["interview", "conversation", "asked", "question", "talk"],
    "Works": ["book", "wrote", "published", "lecture", "discourse", "speech"],
    "Media Coverage": ["video", "audio", "recording", "documentary", "podcast"],
}

_SUGGESTIONS: Dict[str, str] = {
    "Biography": "early childhood and family background",
    "Career": "career milestones and major roles",
    "Ideas & Views": "documented positions and viewpoints",
    "Interviews": "long-form interviews",
    "Works": "published works and major lectures",
    "Media Coverage": "video/audio appearances",
}


def estimate_coverage(db: Session, persona: Persona) -> dict:
    sources = list(db.scalars(select(Source).where(Source.persona_id == persona.id)))
    chunks = list(db.scalars(select(Chunk).where(Chunk.persona_id == persona.id)))
    corpus = " ".join(c.text.lower() for c in chunks)
    source_types = {s.source_type for s in sources}

    facets: List[dict] = []
    gaps: List[str] = []
    for facet, keywords in _FACETS.items():
        hits = sum(1 for kw in keywords if kw in corpus)
        base = min(hits / max(len(keywords), 1), 1.0)
        # media facet also rewards having audio/video source types
        if facet == "Media Coverage" and ({"audio", "video"} & source_types):
            base = max(base, 0.6)
        # scale by overall corpus size so a tiny corpus never reads as "complete"
        volume = min(len(chunks) / 20.0, 1.0)
        score = round(min(base * 0.7 + volume * 0.3, 1.0) * 100)
        facets.append({"facet": facet, "coverage": score})
        if score < 55:
            gaps.append(_SUGGESTIONS[facet])

    facets.sort(key=lambda f: f["coverage"], reverse=True)
    return {
        "note": (
            "Knowledge coverage estimates based on collected sources and extracted "
            "evidence. These are heuristic indicators, not exact measurements."
        ),
        "source_count": len(sources),
        "chunk_count": len(chunks),
        "facets": facets,
        "suggested_searches": gaps,
    }
