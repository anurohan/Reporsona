"""Identity resolution (§8).

Given an ambiguous name, produce a short list of candidate public figures so the
user can pick the right one before deep ingestion begins. Uses only Wikipedia's
public search + summary APIs (no scraping, no bypassing). Falls back gracefully
to a single best-effort candidate when the network or an API is unavailable, so
the flow never hard-fails offline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

import httpx

from app.config import settings
from app.services.source_discovery import WIKI_UA, slugify
from app.services.temporal import parse_lifespan

logger = logging.getLogger("repersona.identity")


@dataclass
class IdentityCandidate:
    name: str
    description: str = ""
    summary: str = ""
    url: str = ""
    portrait_url: str = ""
    birth_year: int | None = None
    death_year: int | None = None
    source: str = "wikipedia"

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "summary": self.summary,
            "url": self.url,
            "portrait_url": self.portrait_url,
            "birth_year": self.birth_year,
            "death_year": self.death_year,
            "source": self.source,
        }


@dataclass
class ResolutionResult:
    query: str
    candidates: List[IdentityCandidate] = field(default_factory=list)
    ambiguous: bool = False
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "query": self.query,
            "candidates": [c.as_dict() for c in self.candidates],
            "ambiguous": self.ambiguous,
            "note": self.note,
        }


def resolve(name: str, limit: int = 5) -> ResolutionResult:
    query = (name or "").strip()
    if not query:
        return ResolutionResult(query=query, candidates=[], note="Empty query.")
    try:
        return _resolve_wikipedia(query, limit)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Identity resolution failed for %r (%s).", query, exc)
        return ResolutionResult(
            query=query,
            candidates=[IdentityCandidate(name=query.title(), description="", source="fallback")],
            ambiguous=False,
            note=f"Live identity lookup unavailable ({exc}); proceeding with the entered name.",
        )


def _resolve_wikipedia(query: str, limit: int) -> ResolutionResult:
    lang = settings.wikipedia_lang or "en"
    wiki_api = f"https://{lang}.wikipedia.org/w/api.php"
    headers = {"User-Agent": WIKI_UA, "Accept": "application/json"}

    with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
        r = client.get(wiki_api, params={
            "action": "query", "list": "search", "srsearch": query,
            "srlimit": limit, "format": "json",
        })
        r.raise_for_status()
        hits = r.json().get("query", {}).get("search", [])

        candidates: List[IdentityCandidate] = []
        for hit in hits:
            title = hit.get("title", "")
            if not title:
                continue
            cand = IdentityCandidate(name=title, url=(
                f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
            ))
            try:
                s = client.get(
                    f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
                )
                if s.status_code == 200:
                    sj = s.json()
                    cand.description = sj.get("description", "") or ""
                    cand.summary = sj.get("extract", "") or ""
                    cand.portrait_url = (
                        (sj.get("thumbnail") or {}).get("source") or ""
                    )
                    span = parse_lifespan(summary=cand.summary)
                    cand.birth_year = span.birth_year
                    cand.death_year = span.death_year
            except Exception:  # noqa: BLE001
                pass
            candidates.append(cand)

    if not candidates:
        return ResolutionResult(
            query=query, candidates=[], ambiguous=False,
            note="No matching public figures found. You can still build from an entered name or uploads.",
        )
    return ResolutionResult(
        query=query, candidates=candidates,
        ambiguous=len(candidates) > 1,
        note=f"Found {len(candidates)} candidate(s) via Wikipedia.",
    )
