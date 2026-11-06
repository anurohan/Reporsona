"""Modular external source providers (§5, §6, §7).

A small ``SourceProvider`` interface plus real, key-gated implementations:

    * ``TavilyProvider``   — live web search via the Tavily API
    * ``SerpApiProvider``  — live web search via SerpAPI (Google results)
    * ``YouTubeProvider``  — interview/talk discovery via YouTube Data API v3

ETHICAL / LEGAL contract (identical to source_discovery.py):
  * Providers only call *authorised* public APIs with the user's own key.
  * They never scrape, never bypass paywalls / robots / access controls.
  * When a provider is not configured (no key) it returns an empty list and a
    clear note — it NEVER fabricates results, snippets, or transcripts (§47).
  * YouTube transcripts are not fabricated: when a transcript cannot be
    retrieved the video is still recorded from its real API metadata, with a
    note that the transcript was not available (§7, §48).

Each provider degrades gracefully: any network / quota / auth error is logged
and turned into an empty result so a single failing provider never breaks a
persona build (§29).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.services.source_discovery import DiscoveredSource

logger = logging.getLogger("repersona.providers")

_UA = "RePersona/0.1 (educational persona-reconstruction; authorised-API client)"
_TIMEOUT = 15.0


@dataclass
class ProviderResult:
    """What a provider returned for one discovery call."""

    sources: List[DiscoveredSource] = field(default_factory=list)
    configured: bool = False
    ok: bool = False
    note: str = ""


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:  # noqa: BLE001
        return ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class SourceProvider(ABC):
    name = "base"
    label = "Source provider"

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def discover(self, personality: str, limit: int = 6) -> ProviderResult: ...


# --------------------------------------------------------------------------- #
# Web search
# --------------------------------------------------------------------------- #
class TavilyProvider(SourceProvider):
    name = "tavily"
    label = "Tavily web search"
    endpoint = "https://api.tavily.com/search"

    def is_configured(self) -> bool:
        return (settings.search_provider or "").lower() == "tavily" and bool(settings.search_api_key)

    def discover(self, personality: str, limit: int = 6) -> ProviderResult:
        if not self.is_configured():
            return ProviderResult(configured=False, note="Tavily not configured (SEARCH_PROVIDER=tavily + SEARCH_API_KEY).")
        payload = {
            "api_key": settings.search_api_key,
            "query": f"{personality} biography interview views quotes",
            "search_depth": "advanced",
            "include_answer": False,
            "max_results": max(1, min(limit, 10)),
        }
        try:
            with httpx.Client(timeout=_TIMEOUT, headers={"User-Agent": _UA}) as c:
                r = c.post(self.endpoint, json=payload)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Tavily discovery failed: %s", exc)
            return ProviderResult(configured=True, ok=False, note=f"Tavily request failed: {exc}")

        sources: List[DiscoveredSource] = []
        for item in data.get("results", []) or []:
            content = (item.get("content") or "").strip()
            url = item.get("url") or ""
            if not content or not url:
                continue
            sources.append(DiscoveredSource(
                title=item.get("title") or _domain(url) or "Web result",
                source_type="article",
                text=content,
                author=_domain(url),
                url=url,
                publication_date=item.get("published_date") or "",
                provider="Tavily",
                access_type="public_web",
                description=f"Live web result via Tavily ({_domain(url)}), retrieved {_now_iso()}.",
                discovery_method="web_search",
            ))
        return ProviderResult(sources=sources, configured=True, ok=True,
                              note=f"Tavily returned {len(sources)} web sources.")


class SerpApiProvider(SourceProvider):
    name = "serpapi"
    label = "SerpAPI web search"
    endpoint = "https://serpapi.com/search.json"

    def is_configured(self) -> bool:
        return (settings.search_provider or "").lower() == "serpapi" and bool(settings.search_api_key)

    def discover(self, personality: str, limit: int = 6) -> ProviderResult:
        if not self.is_configured():
            return ProviderResult(configured=False, note="SerpAPI not configured (SEARCH_PROVIDER=serpapi + SEARCH_API_KEY).")
        params = {
            "api_key": settings.search_api_key,
            "engine": "google",
            "q": f"{personality} biography interview views",
            "num": max(1, min(limit, 10)),
        }
        try:
            with httpx.Client(timeout=_TIMEOUT, headers={"User-Agent": _UA}) as c:
                r = c.get(self.endpoint, params=params)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("SerpAPI discovery failed: %s", exc)
            return ProviderResult(configured=True, ok=False, note=f"SerpAPI request failed: {exc}")

        sources: List[DiscoveredSource] = []
        for item in (data.get("organic_results") or []):
            snippet = (item.get("snippet") or "").strip()
            url = item.get("link") or ""
            if not snippet or not url:
                continue
            sources.append(DiscoveredSource(
                title=item.get("title") or _domain(url) or "Web result",
                source_type="article",
                text=snippet,
                author=_domain(url),
                url=url,
                publication_date=item.get("date") or "",
                provider="SerpAPI",
                access_type="public_web",
                description=f"Live web result via SerpAPI ({_domain(url)}), retrieved {_now_iso()}. "
                            f"Snippet only — full article not mirrored.",
                discovery_method="web_search",
            ))
        return ProviderResult(sources=sources, configured=True, ok=True,
                              note=f"SerpAPI returned {len(sources)} web sources.")


def web_search_provider() -> SourceProvider:
    """Return the configured web-search provider (Tavily by default)."""
    prov = (settings.search_provider or "").lower()
    if prov == "serpapi":
        return SerpApiProvider()
    return TavilyProvider()


# --------------------------------------------------------------------------- #
# YouTube
# --------------------------------------------------------------------------- #
class YouTubeProvider(SourceProvider):
    name = "youtube"
    label = "YouTube Data API"
    search_endpoint = "https://www.googleapis.com/youtube/v3/search"

    def is_configured(self) -> bool:
        return bool((getattr(settings, "youtube_api_key", "") or "").strip())

    def discover(self, personality: str, limit: int = 5) -> ProviderResult:
        if not self.is_configured():
            return ProviderResult(configured=False, note="YouTube not configured (YOUTUBE_API_KEY).")
        params = {
            "key": settings.youtube_api_key,
            "part": "snippet",
            "q": f"{personality} interview lecture speech talk",
            "type": "video",
            "maxResults": max(1, min(limit, 10)),
            "relevanceLanguage": "en",
            "safeSearch": "moderate",
        }
        try:
            with httpx.Client(timeout=_TIMEOUT, headers={"User-Agent": _UA}) as c:
                r = c.get(self.search_endpoint, params=params)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("YouTube discovery failed: %s", exc)
            return ProviderResult(configured=True, ok=False, note=f"YouTube request failed: {exc}")

        sources: List[DiscoveredSource] = []
        for item in (data.get("items") or []):
            vid = (item.get("id") or {}).get("videoId")
            snip = item.get("snippet") or {}
            if not vid:
                continue
            title = snip.get("title") or "YouTube video"
            channel = snip.get("channelTitle") or ""
            description = (snip.get("description") or "").strip()
            published = (snip.get("publishedAt") or "")[:10]
            url = f"https://www.youtube.com/watch?v={vid}"
            # We store the REAL API-provided title/description as text. We do NOT
            # fabricate a transcript or timestamps; if a transcript library is
            # later added it can enrich this source in place.
            body = (
                f"{title}\nChannel: {channel}\n\n{description}"
                if description else f"{title}\nChannel: {channel}"
            )
            sources.append(DiscoveredSource(
                title=f"{title} — YouTube",
                source_type="video",
                text=body,
                author=channel,
                url=url,
                publication_date=published,
                provider="YouTube",
                access_type="public_media",
                description=(
                    "Video discovered via YouTube Data API. Transcript not retrieved "
                    "(no authorised transcript source configured); metadata only."
                ),
                discovery_method="youtube",
            ))
        return ProviderResult(sources=sources, configured=True, ok=True,
                              note=f"YouTube returned {len(sources)} videos (metadata only).")


def youtube_provider() -> SourceProvider:
    return YouTubeProvider()


# --------------------------------------------------------------------------- #
# Composition
# --------------------------------------------------------------------------- #
def augment_sources(personality: str) -> tuple[List[DiscoveredSource], List[str]]:
    """Gather extra sources from every *configured* external provider.

    Returns ``(sources, notes)``. Unconfigured providers contribute nothing and
    no note (the provider-status endpoint already reports their state). Failures
    contribute a note but never raise.
    """
    extra: List[DiscoveredSource] = []
    notes: List[str] = []
    for provider in (web_search_provider(), youtube_provider()):
        try:
            if not provider.is_configured():
                continue
            res = provider.discover(personality)
            extra.extend(res.sources)
            if res.note:
                notes.append(res.note)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Provider %s failed: %s", provider.name, exc)
            notes.append(f"{provider.label} failed: {exc}")
    return extra, notes
