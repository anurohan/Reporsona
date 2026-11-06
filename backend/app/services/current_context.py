"""Live current-context retrieval (§18).

When a question is classified as requiring present-day knowledge (current
politics / news / society / events), the persona reasoner must obtain REAL,
freshly-retrieved facts from a configured live search provider — never from the
documented person's historical corpus, and never fabricated.

This module owns that boundary. Its single public entry point,
``retrieve_current_context(query, ...)``, returns a :class:`CurrentContextResult`
whose ``status`` is one of:

    * ``"ok"``          — live results retrieved (``items`` populated)
    * ``"empty"``       — provider configured & reachable but returned nothing
    * ``"unavailable"`` — no live search provider is configured
    * ``"error"``       — a configured provider failed (network/quota/auth)

Contract (mirrors the ethical rules in source_providers.py):
  * Only authorised public search APIs are called, using the user's own key.
  * Nothing is scraped and no snippet/date is invented.
  * On ``unavailable``/``error``/``empty`` the caller must NOT synthesise
    current facts from old persona documents — it surfaces the status instead.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger("repersona.current_context")

_UA = "RePersona/0.1 (educational persona-reconstruction; authorised-API client)"
_TIMEOUT = 15.0

UNAVAILABLE_MESSAGE = (
    "Current web context is unavailable because no live search provider is "
    "configured. Set SEARCH_PROVIDER (tavily or serpapi) and SEARCH_API_KEY to "
    "enable present-day retrieval."
)


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:  # noqa: BLE001
        return ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class CurrentContextItem:
    """One live-retrieved current fact. Sourced ONLY from live web search."""

    title: str = ""
    url: str = ""
    domain: str = ""
    source: str = ""
    publication_date: str = ""
    retrieved_at: str = ""
    snippet: str = ""
    relevance: float = 0.0

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "domain": self.domain,
            "source": self.source,
            "publication_date": self.publication_date,
            "retrieved_at": self.retrieved_at,
            "snippet": self.snippet,
            "relevance": round(self.relevance, 4),
        }


@dataclass
class CurrentContextResult:
    status: str = "unavailable"  # ok | empty | unavailable | error
    provider: str = ""
    items: List[CurrentContextItem] = field(default_factory=list)
    note: str = ""

    @property
    def used(self) -> bool:
        return self.status == "ok" and bool(self.items)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "provider": self.provider,
            "note": self.note,
            "items": [i.as_dict() for i in self.items],
        }


def _provider_name() -> str:
    return (settings.search_provider or "").lower()


def is_configured() -> bool:
    """True when a live web-search provider has both a provider name and key."""
    return _provider_name() in ("tavily", "serpapi") and bool(settings.search_api_key)


# --------------------------------------------------------------------------- #
# Provider calls (current-context flavour: raw query, recency-biased)
# --------------------------------------------------------------------------- #
def _tavily(query: str, limit: int) -> CurrentContextResult:
    payload = {
        "api_key": settings.search_api_key,
        "query": query,
        "search_depth": "advanced",
        "topic": "news",
        "days": 30,
        "include_answer": False,
        "max_results": max(1, min(limit, 10)),
    }
    try:
        with httpx.Client(timeout=_TIMEOUT, headers={"User-Agent": _UA}) as c:
            r = c.post("https://api.tavily.com/search", json=payload)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tavily current-context search failed: %s", exc)
        return CurrentContextResult(status="error", provider="tavily",
                                    note=f"Tavily request failed: {exc}")

    retrieved = _now_iso()
    items: List[CurrentContextItem] = []
    for it in (data.get("results") or []):
        url = it.get("url") or ""
        snippet = (it.get("content") or "").strip()
        if not url or not snippet:
            continue
        items.append(CurrentContextItem(
            title=it.get("title") or _domain(url) or "Web result",
            url=url,
            domain=_domain(url),
            source=_domain(url),
            publication_date=it.get("published_date") or "",
            retrieved_at=retrieved,
            snippet=snippet,
            relevance=float(it.get("score") or 0.0),
        ))
    status = "ok" if items else "empty"
    return CurrentContextResult(status=status, provider="tavily", items=items,
                                note=f"Tavily returned {len(items)} live results.")


def _serpapi(query: str, limit: int) -> CurrentContextResult:
    params = {
        "api_key": settings.search_api_key,
        "engine": "google",
        "q": query,
        "num": max(1, min(limit, 10)),
        "tbm": "nws",  # news results → recency-biased
    }
    try:
        with httpx.Client(timeout=_TIMEOUT, headers={"User-Agent": _UA}) as c:
            r = c.get("https://serpapi.com/search.json", params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("SerpAPI current-context search failed: %s", exc)
        return CurrentContextResult(status="error", provider="serpapi",
                                    note=f"SerpAPI request failed: {exc}")

    retrieved = _now_iso()
    items: List[CurrentContextItem] = []
    # News engine returns "news_results"; fall back to "organic_results".
    rows = data.get("news_results") or data.get("organic_results") or []
    for rank, it in enumerate(rows):
        url = it.get("link") or ""
        snippet = (it.get("snippet") or it.get("title") or "").strip()
        if not url or not snippet:
            continue
        items.append(CurrentContextItem(
            title=it.get("title") or _domain(url) or "Web result",
            url=url,
            domain=_domain(url),
            source=it.get("source") or _domain(url),
            publication_date=it.get("date") or "",
            retrieved_at=retrieved,
            snippet=snippet,
            relevance=round(1.0 - rank * 0.08, 4),
        ))
    status = "ok" if items else "empty"
    return CurrentContextResult(status=status, provider="serpapi", items=items,
                                note=f"SerpAPI returned {len(items)} live results.")


def retrieve_current_context(query: str, limit: int = 6) -> CurrentContextResult:
    """Retrieve present-day facts for ``query`` from the configured provider.

    Never raises; never fabricates. Returns ``status="unavailable"`` when no
    provider is configured so the caller can surface the honest failure mode
    instead of answering from the persona's historical corpus."""
    q = (query or "").strip()
    if not q:
        return CurrentContextResult(status="unavailable", note="Empty query.")
    if not is_configured():
        return CurrentContextResult(status="unavailable", note=UNAVAILABLE_MESSAGE)

    prov = _provider_name()
    if prov == "serpapi":
        return _serpapi(q, limit)
    return _tavily(q, limit)
