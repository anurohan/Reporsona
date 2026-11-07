"""Source discovery engine.

Given only a personality name, produce a list of candidate sources. The engine
is adapter-based so real providers (authorised search APIs, public-domain
archives, user uploads) can be added without touching the pipeline.

ETHICAL / LEGAL: adapters must only surface public, licensed, public-domain,
authorised, or user-provided material. They must never bypass authentication,
paywalls, access controls, robots restrictions, or platform protections.

Demo Mode uses the bundled, clearly-labelled synthetic corpora so the whole
flow works offline with zero credentials.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

import httpx

logger = logging.getLogger("repersona.discovery")

# Wikimedia asks all API clients to send a descriptive User-Agent.
WIKI_UA = "RePersona/0.1 (educational persona-reconstruction demo; contact: local user)"

from app.config import settings
from app.seed import osho_demo


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


@dataclass
class DiscoveredSource:
    title: str
    source_type: str
    text: str
    author: str = ""
    url: str = ""
    publication_date: str = ""
    provider: str = ""
    access_type: str = "public"
    description: str = ""
    duration_seconds: float = 0.0
    discovery_method: str = "demo"


@dataclass
class DiscoveryResult:
    persona: dict
    sources: List[DiscoveredSource]
    hints: dict = field(default_factory=dict)
    is_demo: bool = True
    note: str = ""


class BaseSourceAdapter(ABC):
    name = "base"

    @abstractmethod
    def discover(self, personality: str) -> DiscoveryResult: ...


class DemoSourceAdapter(BaseSourceAdapter):
    """Serves bundled demo corpora. Osho has a curated set; any other name gets
    a small, explicitly generic illustrative corpus so the flow is exercisable
    without attributing invented quotes to a real person."""

    name = "demo"

    def discover(self, personality: str) -> DiscoveryResult:
        slug = slugify(personality)
        if slug == "osho":
            corpus = osho_demo.get_demo_corpus()
            sources = [
                DiscoveredSource(discovery_method="demo", **s) for s in corpus["sources"]
            ]
            return DiscoveryResult(
                persona=corpus["persona"],
                sources=sources,
                hints=corpus["hints"],
                is_demo=True,
                note="Bundled Osho demonstration corpus (synthetic, not real transcripts).",
            )
        return self._generic(personality)

    def _generic(self, personality: str) -> DiscoveryResult:
        name = personality.strip().title()
        generic_text = (
            f"[DEMONSTRATION PLACEHOLDER] This is generic, synthetic illustrative "
            f"text used to exercise the RePersona pipeline for “{name}”. It is not "
            f"attributed to the real person and contains no real quotations. In a "
            f"configured deployment, a real source-discovery adapter would gather "
            f"public, licensed, or user-provided material here. Themes such as "
            f"knowledge, work, ideas, curiosity and perseverance appear so retrieval "
            f"has something to match against.\n\n"
            f"Curiosity drives discovery. Ideas build on ideas. Perseverance turns "
            f"questions into understanding. This placeholder repeats a few themes so "
            f"the chunker, embedder and retriever have material to operate on."
        )
        sources = [
            DiscoveredSource(
                title=f"{name} — illustrative demo document",
                source_type="document",
                text=generic_text,
                author="Demo Corpus",
                provider="RePersona Demo",
                access_type="public_domain",
                publication_date="",
                description="Generic demonstration placeholder — not real content.",
                discovery_method="demo",
            )
        ]
        return DiscoveryResult(
            persona={
                "name": name,
                "slug": slugify(name),
                "summary": f"DEMONSTRATION persona for {name} built from generic placeholder text.",
                "portrait_url": "",
                "known_for": [],
                "domains": [],
            },
            sources=sources,
            hints={"uncertainties": ["Generic demo placeholder — no real corpus was gathered."]},
            is_demo=True,
            note="No curated corpus for this name; generated a generic demo placeholder.",
        )


class LiveSearchAdapter(BaseSourceAdapter):
    """Placeholder for a real, authorised search adapter.

    Intentionally does NOT scrape or bypass anything. It requires an explicit
    ``SEARCH_API_KEY`` / ``SEARCH_PROVIDER`` and would call an authorised API.
    Until configured, it returns nothing with a clear note.
    """

    name = "live_search"

    def discover(self, personality: str) -> DiscoveryResult:
        return DiscoveryResult(
            persona={"name": personality.strip(), "slug": slugify(personality)},
            sources=[],
            hints={},
            is_demo=False,
            note=(
                "Live source discovery is not configured. Set SEARCH_PROVIDER and "
                "SEARCH_API_KEY and implement the adapter call, or upload sources "
                "manually. RePersona never bypasses paywalls or access controls."
            ),
        )


class WikipediaSourceAdapter(BaseSourceAdapter):
    """Collects REAL, public data live from Wikipedia + Wikiquote + Wikimedia.

    Uses only official public APIs (no scraping, no bypassing anything):
      * action API `list=search` to resolve the best-matching page title
      * REST `page/summary` for the description + portrait image (Wikimedia)
      * action API `prop=extracts` for the full plain-text article
      * Wikiquote `prop=extracts` for documented quotations (best-effort)

    Falls back to the demo adapter if the network is unavailable or no page is
    found, so the app never hard-fails.
    """

    name = "wikipedia"
    MAX_CHARS = 16000
    SECTION_CHARS = 1800

    def discover(self, personality: str) -> DiscoveryResult:
        try:
            return self._discover(personality)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Wikipedia discovery failed for %r (%s) — using demo fallback.", personality, exc)
            fallback = DemoSourceAdapter().discover(personality)
            fallback.note = f"Live collection failed ({exc}); showing demo data instead."
            return fallback

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=15.0,
            headers={"User-Agent": WIKI_UA, "Accept": "application/json"},
            follow_redirects=True,
        )

    def _discover(self, personality: str) -> DiscoveryResult:
        lang = settings.wikipedia_lang or "en"
        wiki_api = f"https://{lang}.wikipedia.org/w/api.php"
        quote_api = f"https://{lang}.wikiquote.org/w/api.php"

        with self._client() as client:
            # 1) resolve the canonical page title
            r = client.get(wiki_api, params={
                "action": "query", "list": "search", "srsearch": personality,
                "srlimit": 1, "format": "json",
            })
            r.raise_for_status()
            hits = r.json().get("query", {}).get("search", [])
            if not hits:
                raise ValueError("No Wikipedia page found")
            title = hits[0]["title"]

            # 2) summary (description + portrait image)
            portrait = ""
            summary_text = ""
            page_url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
            try:
                s = client.get(
                    f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
                )
                if s.status_code == 200:
                    sj = s.json()
                    summary_text = sj.get("extract", "") or ""
                    portrait = (
                        (sj.get("originalimage") or {}).get("source")
                        or (sj.get("thumbnail") or {}).get("source")
                        or ""
                    )
                    page_url = (
                        ((sj.get("content_urls") or {}).get("desktop") or {}).get("page")
                        or page_url
                    )
            except Exception:  # noqa: BLE001
                pass

            # 3) full plain-text article
            e = client.get(wiki_api, params={
                "action": "query", "prop": "extracts", "explaintext": 1,
                "redirects": 1, "titles": title, "format": "json",
            })
            e.raise_for_status()
            pages = e.json().get("query", {}).get("pages", {})
            extract = ""
            for _pid, page in pages.items():
                extract = page.get("extract", "") or ""
                break
            extract = extract[: self.MAX_CHARS]

            # 4) Wikiquote quotations (best-effort)
            quotes_text = ""
            try:
                q = client.get(quote_api, params={
                    "action": "query", "prop": "extracts", "explaintext": 1,
                    "redirects": 1, "titles": title, "format": "json",
                })
                if q.status_code == 200:
                    qpages = q.json().get("query", {}).get("pages", {})
                    for _pid, page in qpages.items():
                        if "missing" not in page:
                            quotes_text = (page.get("extract", "") or "")[: self.MAX_CHARS]
                        break
            except Exception:  # noqa: BLE001
                pass

        # ---- build sources from the collected text ----
        sources: List[DiscoveredSource] = []
        base_text = extract or summary_text
        if not base_text.strip():
            raise ValueError("No usable article text")

        for i, section in enumerate(self._split_sections(base_text)):
            sources.append(DiscoveredSource(
                title=f"{title} — Wikipedia (part {i + 1})",
                source_type="article",
                text=section,
                author="Wikipedia contributors",
                url=page_url,
                provider="Wikipedia",
                access_type="cc-by-sa",
                description="Live-collected encyclopedic text.",
                discovery_method="wikipedia",
            ))
        if quotes_text.strip():
            sources.append(DiscoveredSource(
                title=f"{title} — Wikiquote (documented quotations)",
                source_type="document",
                text=quotes_text,
                author="Wikiquote contributors",
                url=f"https://{lang}.wikiquote.org/wiki/{title.replace(' ', '_')}",
                provider="Wikiquote",
                access_type="cc-by-sa",
                description="Documented quotations attributed to the subject.",
                discovery_method="wikiquote",
            ))

        persona = {
            "name": title,
            "slug": slugify(title),
            "summary": summary_text or f"Live-reconstructed profile of {title} from public sources.",
            "portrait_url": portrait,
            "known_for": [],
            "domains": [],
        }
        # Historical Reality Guard (§17): extract documented birth/death years
        # from the encyclopedic prose so the temporal boundary is honest.
        try:
            from app.services.temporal import parse_full_dates, parse_lifespan

            span = parse_lifespan(text=extract, summary=summary_text)
            if span.birth_year:
                persona["birth_year"] = span.birth_year
            if span.death_year:
                persona["death_year"] = span.death_year
            # Best-effort full ISO dates -> a precise, restart-durable boundary.
            birth_date, death_date = parse_full_dates(text=extract, summary=summary_text)
            if birth_date:
                persona["birth_date"] = birth_date
            if death_date:
                persona["death_date"] = death_date
        except Exception:  # noqa: BLE001 — never fail discovery on parsing
            pass
        hints = {
            "uncertainties": [
                "Profile auto-collected live from Wikipedia/Wikiquote (CC BY-SA); coverage is limited to those pages.",
                "This is an AI reconstruction from public text, not the real person.",
            ],
        }
        return DiscoveryResult(
            persona=persona, sources=sources, hints=hints, is_demo=False,
            note=f"Collected live from Wikipedia/Wikiquote: {len(sources)} sources.",
        )

    def _split_sections(self, text: str) -> List[str]:
        # group paragraphs into ~SECTION_CHARS-sized blocks
        paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip() and len(p.strip()) > 40]
        blocks: List[str] = []
        cur = ""
        for p in paras:
            if len(cur) + len(p) + 2 > self.SECTION_CHARS and cur:
                blocks.append(cur)
                cur = p
            else:
                cur = f"{cur}\n\n{p}" if cur else p
        if cur:
            blocks.append(cur)
        return blocks[:10] or [text[: self.SECTION_CHARS]]


def get_adapter() -> BaseSourceAdapter:
    if settings.source_mode == "demo":
        return DemoSourceAdapter()
    # Wikipedia provides the canonical identity, biography and lifespan data.
    # Configured web/video providers are appended by ``discover`` below; they
    # must never replace this baseline with an empty placeholder adapter.
    return WikipediaSourceAdapter()


def discover(personality: str, force_demo: bool = False) -> DiscoveryResult:
    if force_demo:
        return DemoSourceAdapter().discover(personality)
    result = get_adapter().discover(personality)
    # Augment with any *configured* external providers (web search, YouTube).
    # Deferred import avoids a circular dependency (source_providers imports
    # DiscoveredSource from this module). Never fails the build (§29).
    try:
        from app.services.source_providers import augment_sources

        extra, notes = augment_sources(personality)
        if extra:
            result.sources.extend(extra)
            result.is_demo = False
            joined = " ".join(notes)
            result.note = (f"{result.note} {joined}".strip() if result.note else joined)
    except Exception as exc:  # noqa: BLE001
        logger.warning("External provider augmentation skipped: %s", exc)
    return result
