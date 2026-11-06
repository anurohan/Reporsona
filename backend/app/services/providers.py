"""Provider status registry (§27 API-key strategy).

Reports which optional integrations are configured, without ever exposing the
secret values themselves. The frontend renders this as:

    Web Search: Not configured
    YouTube:    Configured
    LLM:        Ollama
    Embeddings: Local

Every flag is derived from environment-driven ``settings`` — never hardcoded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.config import settings


@dataclass
class ProviderStatus:
    key: str
    label: str
    configured: bool
    mode: str                      # short status word shown in the UI
    detail: str = ""
    requires_key: bool = True
    docs: str = ""

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "configured": self.configured,
            "mode": self.mode,
            "detail": self.detail,
            "requires_key": self.requires_key,
            "docs": self.docs,
        }


def _llm_status() -> ProviderStatus:
    provider = (settings.llm_provider or "auto").lower()
    if provider == "demo":
        return ProviderStatus(
            key="llm", label="Language model", configured=True, mode="Demo composer",
            requires_key=False,
            detail="Offline deterministic composer (no external LLM).",
        )
    if provider in ("openai_compatible",):
        configured = bool(settings.llm_api_key) or bool(settings.llm_base_url)
        return ProviderStatus(
            key="llm", label="Language model",
            configured=configured, mode="OpenAI-compatible",
            requires_key=False,
            detail=f"Endpoint {settings.llm_base_url} · model {settings.llm_model}.",
        )
    # auto / ollama
    return ProviderStatus(
        key="llm", label="Language model", configured=True,
        mode="Ollama (local)" if provider != "auto" else "Auto (Ollama → demo)",
        requires_key=False,
        detail=(
            f"Uses local Ollama ({settings.llm_model}) when reachable at "
            f"{settings.llm_base_url}; falls back to the offline composer."
        ),
    )


def _web_search_status() -> ProviderStatus:
    prov = (settings.search_provider or "").strip().lower()
    configured = bool(settings.search_api_key) and bool(prov)
    label_map = {"tavily": "Tavily", "serpapi": "SerpAPI"}
    return ProviderStatus(
        key="web_search", label="Web search",
        configured=configured,
        mode=(label_map.get(prov, prov.title()) if configured else "Not configured"),
        detail=(
            f"Live web search via {label_map.get(prov, prov)}."
            if configured
            else "Set SEARCH_PROVIDER + SEARCH_API_KEY to enable live web search."
        ),
        docs="https://tavily.com  /  https://serpapi.com",
    )


def _youtube_status() -> ProviderStatus:
    key = getattr(settings, "youtube_api_key", "") or ""
    configured = bool(key.strip())
    return ProviderStatus(
        key="youtube", label="YouTube",
        configured=configured,
        mode="Configured" if configured else "Not configured",
        detail=(
            "YouTube Data API v3 discovery is enabled."
            if configured
            else "Set YOUTUBE_API_KEY to enable video/interview discovery."
        ),
        docs="https://developers.google.com/youtube/v3",
    )


def _sources_status() -> ProviderStatus:
    mode = (settings.source_mode or "auto").lower()
    live = mode in ("auto", "wikipedia")
    return ProviderStatus(
        key="sources", label="Reference sources",
        configured=True, requires_key=False,
        mode="Wikipedia / Wikiquote (live)" if live else "Demo corpus (offline)",
        detail=(
            "Live discovery from Wikipedia & Wikiquote public APIs."
            if live
            else "Offline bundled demonstration corpus only."
        ),
    )


def _embeddings_status() -> ProviderStatus:
    # Deferred import so this module stays import-light and testable.
    backend = "local"
    try:
        from app.services.embeddings import embedding_service

        backend = embedding_service.backend
    except Exception:  # noqa: BLE001
        backend = "unknown"
    nice = {
        "sentence-transformers": "Local (sentence-transformers)",
        "hashing": "Local (lexical fallback)",
        "unknown": "Local",
    }.get(backend, f"Local ({backend})")
    return ProviderStatus(
        key="embeddings", label="Embeddings",
        configured=True, requires_key=False, mode=nice,
        detail="All embedding + vector retrieval runs locally.",
    )


def provider_statuses() -> List[ProviderStatus]:
    return [
        _sources_status(),
        _web_search_status(),
        _youtube_status(),
        _llm_status(),
        _embeddings_status(),
    ]


def provider_status_dicts() -> List[dict]:
    return [p.as_dict() for p in provider_statuses()]
