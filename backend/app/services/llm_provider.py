"""LLM (Llama) provider abstraction.

Supported providers (``LLM_PROVIDER``):

* ``demo``              — deterministic local composer. No network. Weaves the
                          retrieved evidence into an answer written in the
                          persona's documented register, with explicit
                          anti-fabrication framing. Used by Demo Mode and as the
                          universal fallback when a real provider errors.
* ``ollama``            — local Ollama server (default ``llama3.2:3b``).
* ``openai_compatible`` — any OpenAI-compatible ``/v1/chat/completions`` endpoint
                          (vLLM, Together, Groq, LM Studio, etc).

The public entrypoint ``complete()`` never raises for provider/network issues —
it degrades to the demo composer and reports which provider actually produced
the text, so the UI can be transparent about it.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger("repersona.llm")


import re

_GREETING_RE = re.compile(
    r"^\s*(hi|hii+|hey+|hello+|helo|yo|namaste|namaskar|hola|"
    r"good\s*(morning|afternoon|evening)|how\s*are\s*you|"
    r"how'?s\s*it\s*going|what'?s\s*up|sup)\b",
    re.IGNORECASE,
)
_IDENTITY_RE = re.compile(
    r"\b(who\s*are\s*you|what'?s\s*your\s*name|what\s*is\s*your\s*(full\s*)?name|"
    r"your\s*(full\s*)?name|tell\s*me\s*your\s*name|introduce\s*yourself|"
    r"tell\s*me\s*about\s*yourself)\b",
    re.IGNORECASE,
)


def is_smalltalk(question: str) -> bool:
    """True for greetings / identity chit-chat that should NOT trigger heavy
    retrieval — a real person just replies, they don't 'search their sources'."""
    q = (question or "").strip()
    if _IDENTITY_RE.search(q):
        return True
    return bool(_GREETING_RE.search(q)) and len(q.split()) <= 6


def _to_first_person(text: str, persona_name: str) -> str:
    """Best-effort, conservative rewrite of biographical (3rd-person) text into
    the persona's first-person voice, so the offline composer reads like the
    person is speaking. Not perfect — the LLM path is far better — but it avoids
    an obviously robotic register."""
    if not text:
        return text
    parts = [p for p in persona_name.split() if len(p) > 1]
    variants = sorted(set([persona_name] + parts), key=len, reverse=True)
    for v in variants:
        text = re.sub(rf"\b{re.escape(v)}\b", "I", text)
    # collapse the common artefact "I 's" -> "my"
    text = text.replace("I 's", "my").replace("I's", "my")
    return text


def _clean_snippet(s: str) -> str:
    """Strip Wikiquote/wiki markup and dangling mid-sentence fragments so the
    offline composer never pastes raw junk like 't. I never talk about...'."""
    s = s or ""
    # drop wiki section headers (== Sourced ==), list bullets, attributions
    s = re.sub(r"={2,}[^=\n]+={2,}", " ", s)
    s = re.sub(r"^\s*[\*#:;\-]+\s*", " ", s, flags=re.MULTILINE)
    # remove bracketed refs / notes and stray quote marks
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = s.replace("“", '"').replace("”", '"').replace("’", "'")
    s = " ".join(s.split())
    # If the snippet starts mid-word/mid-sentence (lowercase or punctuation),
    # jump to the first real sentence start (a capital letter after a boundary).
    if s and not s[0].isupper():
        m = re.search(r"(?:^|[.!?]\s+)([A-Z].*)", s)
        if m:
            s = m.group(1)
    return s.strip()


def _first_sentences(s: str, max_sentences: int = 3, n: int = 480) -> str:
    """Return the first few *complete* sentences, capped at n chars."""
    s = _clean_snippet(s)
    if not s:
        return s
    sentences = re.split(r"(?<=[.!?])\s+", s)
    out = ""
    for sent in sentences[:max_sentences]:
        if len(out) + len(sent) + 1 > n and out:
            break
        out = f"{out} {sent}".strip()
    if not out:
        out = s
    # ensure it ends on a sentence boundary
    if out and out[-1] not in ".!?":
        cut = max(out.rfind("."), out.rfind("!"), out.rfind("?"))
        out = out[: cut + 1] if cut > 40 else out + "."
    return out.strip()


def _trim(s: str, n: int = 500) -> str:
    s = " ".join((s or "").split())
    if len(s) <= n:
        return s
    return s[: n - 1].rsplit(" ", 1)[0] + "…"


# Canned lines for the offline composer, per language. (The LLM path handles
# language far better; these keep the fallback coherent when Ollama is absent.)
_GREET_LINES = {
    "en": "Hello, good to meet you. I'm {name}. Ask me whatever you're curious about and I'll do my best to answer.",
    "hi": "Namaste, aapse milkar accha laga. Main {name} hoon. Jo bhi jaanna chahein, poochhiye — main poori koshish karunga batane ki.",
    "hinglish": "Hello ji, aapse milke accha laga! Main {name} hoon. Jo bhi puchhna hai bindaas puchho, main try karunga answer dene ki.",
}
_IDENTITY_LINES = {
    "en": "I'm {name}. Happy to talk — ask me about my work, my ideas, or anything you'd like to know.",
    "hi": "Main {name} hoon. Baat karke khushi hogi — mere kaam ke baare mein, mere vichaaron ke baare mein, jo chahein poochhein.",
    "hinglish": "Main {name} hoon. Baat karke acha lagega — mere work ke baare mein, meri ideas ke baare mein, kuch bhi pucho.",
}
_NO_ANSWER_LINES = {
    "en": "That's not something I can really speak to — I'd rather be honest than make something up. Ask me another way, or about something closer to what I'm known for.",
    "hi": "Iske baare mein main sach mein kuch keh nahi sakta — jhooth bolne se accha hai saaf kah doon. Kisi aur tareeke se poochhein, ya jis cheez ke liye main jaana jaata hoon uske baare mein.",
    "hinglish": "Iske baare mein main sahi se kuch nahi keh sakta — banane se accha hai honest rahoon. Thoda alag tareeke se pucho, ya jis cheez ke liye main famous hoon uske baare mein.",
}


def _lang_key(language: str) -> str:
    l = (language or "en").strip().lower()
    if l in ("hi", "hindi"):
        return "hi"
    if l in ("hinglish", "hi-en", "hien"):
        return "hinglish"
    return "en"


def compose_demo_answer(
    persona_name: str,
    question: str,
    evidence_texts: List[str],
    language: str = "en",
) -> str:
    """Offline, deterministic answer composer written in a natural, human,
    first-person voice. It never fabricates facts — it only speaks from the
    material that was retrieved — but it cleans wiki markup / fragments and
    drops robotic framing. (The ethical notice + Evidence panel keep the
    AI-simulation labelling.)"""
    name = persona_name.strip() or "me"
    q = question or ""
    lk = _lang_key(language)

    # Greetings / small talk -> warm, in-character hello (no evidence needed).
    if _GREETING_RE.search(q) and len(q.split()) <= 6:
        return _GREET_LINES[lk].format(name=name)
    if _IDENTITY_RE.search(q):
        return _IDENTITY_LINES[lk].format(name=name)

    snippets = [t.strip() for t in (evidence_texts or []) if t and t.strip()]
    # clean + keep only snippets that yield a real sentence
    cleaned = [c for c in (_first_sentences(s) for s in snippets[:3]) if c]
    if not cleaned:
        return _NO_ANSWER_LINES[lk]

    lead = _to_first_person(cleaned[0], name)
    answer = lead
    if len(cleaned) > 1:
        extra = _to_first_person(_first_sentences(snippets[1], max_sentences=2, n=300), name)
        if extra and extra != lead:
            answer = f"{lead} {extra}"
    return answer.strip()


class LLMProvider:
    def __init__(self) -> None:
        self.provider = settings.llm_provider

    async def complete(
        self,
        system: str,
        user: str,
        *,
        demo_persona_name: str = "",
        demo_question: str = "",
        demo_evidence: Optional[List[str]] = None,
        language: str = "en",
    ) -> Tuple[str, str]:
        """Return ``(text, provider_used)``. Never raises on provider failure."""
        demo_evidence = demo_evidence or []

        if self.provider == "demo":
            return (
                compose_demo_answer(demo_persona_name, demo_question, demo_evidence, language),
                "demo",
            )

        try:
            if self.provider in ("auto", "ollama"):
                # In auto mode, only use Ollama if it's actually reachable so we
                # don't make the user wait on a long timeout when it's absent.
                if self.provider == "auto" and not await self._ollama_reachable():
                    return (
                        compose_demo_answer(demo_persona_name, demo_question, demo_evidence, language),
                        "demo(no-llm)",
                    )
                text = await self._ollama(system, user)
                if text.strip():
                    return text, "ollama"
            elif self.provider == "openai_compatible":
                text = await self._openai_compatible(system, user)
                if text.strip():
                    return text, "openai_compatible"
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM provider '%s' failed: %s — falling back to demo", self.provider, exc)

        return (
            compose_demo_answer(demo_persona_name, demo_question, demo_evidence, language),
            "demo(fallback)",
        )

    # -- providers -------------------------------------------------------- #
    async def _ollama_reachable(self) -> bool:
        url = settings.llm_base_url.rstrip("/") + "/api/tags"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(url)
                return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    async def _ollama(self, system: str, user: str) -> str:
        url = settings.llm_base_url.rstrip("/") + "/api/chat"
        payload = {
            "model": settings.llm_model,
            "stream": False,
            "options": {"temperature": settings.llm_temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            return (data.get("message", {}) or {}).get("content", "").strip()

    async def _openai_compatible(self, system: str, user: str) -> str:
        url = settings.llm_base_url.rstrip("/") + "/v1/chat/completions"
        headers = {}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        payload = {
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()


llm_provider = LLMProvider()
