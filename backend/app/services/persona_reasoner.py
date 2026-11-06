"""Persona Reasoner — the core reasoning service (§16).

This sits *above* plain RAG. Where ``rag_engine`` answers "what do the documents
say", the reasoner orchestrates a persona-aware pipeline:

    QUESTION
      -> intent detection        (what kind of question is this?)
      -> temporal analysis       (could the documented person have known this?)
      -> persona evidence         (retrieve documented material)
      -> worldview mapping        (which recurring concepts are relevant?)
      -> response-mode selection  (evidence / persona / historical / current+persona)
      -> generation               (persona-conditioned, temporal-guarded prompt)
      -> quote-authenticity check (never dress a simulation up as a real quote)
      -> reasoning trace          (the "Why this response?" payload)

It is deliberately dependency-light: it reuses ``rag_engine`` for retrieval and
``llm_provider`` for generation, and ``temporal`` for the Historical Reality
Guard. All labelling (SIMULATED PERSONA RESPONSE vs VERIFIED HISTORICAL QUOTE)
is decided here so the API and UI stay consistent.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Persona
from app.schemas import ChatTurn, EvidenceItem
from app.services import current_context as cc
from app.services import question_classifier as qc
from app.services import rag_engine
from app.services.embeddings import embedding_service
from app.services.llm_provider import is_smalltalk, llm_provider
from app.services.temporal import (
    Lifespan,
    TemporalAnalysis,
    analyze_question,
    derive_cutoff,
    format_date_display,
    parse_lifespan,
    year_of,
)

# Response modes (§23).
MODE_EVIDENCE = "evidence"
MODE_PERSONA = "persona_simulation"
MODE_HISTORICAL = "historical"
MODE_CURRENT = "current_context"
VALID_MODES = {MODE_EVIDENCE, MODE_PERSONA, MODE_HISTORICAL, MODE_CURRENT}

# Response type labels (§18 quote-authenticity).
LABEL_SIMULATION = "SIMULATED_PERSONA_RESPONSE"
LABEL_QUOTE = "VERIFIED_HISTORICAL_QUOTE"

_INTENT_PATTERNS = [
    ("greeting", re.compile(r"\b(hi|hello|hey|namaste|namaskar)\b", re.I)),
    ("identity", re.compile(r"\b(who\s*are\s*you|your\s*name|about\s*yourself)\b", re.I)),
    ("opinion", re.compile(r"\b(what\s*do\s*you\s*think|your\s*(view|opinion|take)|"
                            r"how\s*do\s*you\s*(feel|see))\b", re.I)),
    ("advice", re.compile(r"\b(should\s*i|how\s*(do|can|should)\s*i|what\s*should|advice)\b", re.I)),
    ("current_event", re.compile(r"\b(politics|election|war|economy|news|world|society|"
                                 r"technology|ai|climate)\b", re.I)),
    ("biographical", re.compile(r"\b(when\s*were\s*you\s*born|where\s*did\s*you|your\s*life|"
                                r"your\s*(work|book|childhood|death))\b", re.I)),
]


def detect_intent(question: str) -> str:
    q = question or ""
    for label, rx in _INTENT_PATTERNS:
        if rx.search(q):
            return label
    return "general"


@dataclass
class ReasonResult:
    message: str
    response_type: str                       # LABEL_SIMULATION | LABEL_QUOTE
    mode: str                                # effective response mode
    requested_mode: str
    intent: str
    evidence: List[EvidenceItem] = field(default_factory=list)
    evidence_coverage: str = "LOW"
    limitations: List[str] = field(default_factory=list)
    provider: str = "demo"
    temporal: Optional[dict] = None
    worldview_concepts: List[str] = field(default_factory=list)
    reasoning: dict = field(default_factory=dict)   # the "Why this response?" payload
    # Classification + current-context (§18-19)
    category: str = "general"
    requires_current_context: bool = False
    current_context_used: bool = False
    current_context_status: str = "not_required"
    current_context: List[dict] = field(default_factory=list)
    citations: List[dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    knowledge_cutoff: str = ""

    def as_dict(self) -> dict:
        return {
            "message": self.message,
            "response_type": self.response_type,
            "mode": self.mode,
            "requested_mode": self.requested_mode,
            "intent": self.intent,
            "evidence": self.evidence,
            "evidence_coverage": self.evidence_coverage,
            "limitations": self.limitations,
            "provider": self.provider,
            "temporal": self.temporal,
            "worldview_concepts": self.worldview_concepts,
            "reasoning": self.reasoning,
            "category": self.category,
            "requires_current_context": self.requires_current_context,
            "current_context_used": self.current_context_used,
            "current_context_status": self.current_context_status,
            "current_context": self.current_context,
            "citations": self.citations,
            "warnings": self.warnings,
            "knowledge_cutoff": self.knowledge_cutoff,
        }


def _persona_lifespan(persona: Persona) -> Lifespan:
    """Prefer stored birth/death years; fall back to parsing the summary."""
    by = getattr(persona, "birth_year", None)
    dy = getattr(persona, "death_year", None)
    if by or dy:
        return Lifespan(birth_year=by, death_year=dy)
    return parse_lifespan(summary=persona.summary or "")


def _structured_cutoff(persona: Persona) -> tuple[str, str]:
    """Return the persona's durable ``(knowledge_cutoff, reason)``.

    Prefers the stored, restart-durable columns; if a legacy row never had them
    computed, derive on the fly from whatever lifespan data exists. Person-
    agnostic — no persona is special-cased here."""
    cutoff = (getattr(persona, "knowledge_cutoff", "") or "").strip()
    reason = (getattr(persona, "knowledge_cutoff_reason", "") or "").strip()
    if reason:  # already computed and stored
        return cutoff, reason
    return derive_cutoff(
        birth_date=(getattr(persona, "birth_date", "") or ""),
        death_date=(getattr(persona, "death_date", "") or ""),
        birth_year=getattr(persona, "birth_year", None),
        death_year=getattr(persona, "death_year", None),
    )


def _format_current_facts(result: "cc.CurrentContextResult") -> str:
    """Render the CURRENT FACTS section strictly from live-retrieved items.

    Never fabricates: when nothing was retrieved it states the honest status."""
    if result.status == "unavailable":
        return cc.UNAVAILABLE_MESSAGE
    if result.status == "error":
        return (
            "Current web context could not be retrieved due to a live search "
            f"provider error ({result.note}). No current facts are shown rather "
            "than guessing."
        )
    if result.status == "empty" or not result.items:
        return (
            "The live search provider returned no current results for this "
            "question, so no present-day facts are shown."
        )
    lines: List[str] = []
    for i, it in enumerate(result.items, start=1):
        date = it.publication_date or "date not stated"
        src = it.source or it.domain or "source"
        lines.append(
            f"{i}. {it.snippet.strip()}\n"
            f"   — {src} ({date}) · {it.url}"
        )
    return "\n".join(lines)


def _temporal_notice(boundary_display: str) -> str:
    where = f" ({boundary_display})" if boundary_display else ""
    return (
        "TEMPORAL NOTICE: This is a present-day simulated perspective generated "
        "from the person's documented worldview. The person could not have "
        f"directly known events after their documented knowledge boundary{where}. "
        "The current facts above come from live web sources, not from the person."
    )


def _assemble_current_message(
    *,
    persona_name: str,
    perspective: str,
    current_result: "cc.CurrentContextResult",
    evidence: List[EvidenceItem],
    boundary_display: str,
) -> str:
    """Compose the 4-section current-context answer (§19 response format)."""
    facts = _format_current_facts(current_result)

    used_ev = evidence[:4]
    if used_ev:
        ev_lines = "\n".join(
            f"- {e.source_title} ({e.source_type})" for e in used_ev
        )
    else:
        ev_lines = "- No documented persona passages matched this theme."

    return (
        "CURRENT FACTS\n"
        f"{facts}\n\n"
        f"SIMULATED PERSONA PERSPECTIVE — {persona_name} (simulated, not a real quote)\n"
        f"{perspective.strip()}\n\n"
        "EVIDENCE USED\n"
        f"{ev_lines}\n\n"
        f"{_temporal_notice(boundary_display)}"
    )


def _worldview_concepts(persona: Persona, question: str, evidence: List[EvidenceItem]) -> List[str]:
    """Which of the persona's documented recurring concepts are relevant here.

    Uses simple lexical overlap between the question + retrieved evidence and the
    persona's profile concepts/themes. Never invents concepts — only surfaces
    ones already documented on the profile."""
    pool: List[str] = []
    prof = persona.profile
    if prof:
        pool += list(prof.frequent_concepts or [])
        pool += list(prof.recurring_themes or [])
        pool += list(prof.documented_viewpoints or [])
    pool += list(getattr(persona, "known_for", []) or [])
    pool += list(getattr(persona, "domains", []) or [])

    haystack = (question + " " + " ".join(e.text for e in evidence)).lower()
    q_tokens = set(re.findall(r"[a-z]{4,}", haystack))

    scored: List[tuple[int, str]] = []
    seen = set()
    for concept in pool:
        c = (concept or "").strip()
        if not c or c.lower() in seen:
            continue
        seen.add(c.lower())
        c_tokens = set(re.findall(r"[a-z]{4,}", c.lower()))
        overlap = len(c_tokens & q_tokens)
        scored.append((overlap, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    # Prefer overlapping concepts, but always return a few so the panel isn't empty.
    relevant = [c for ov, c in scored if ov > 0][:6]
    if len(relevant) < 3:
        relevant += [c for ov, c in scored if c not in relevant][: 3 - len(relevant)]
    return relevant


# A chunk is treated as a genuine quotation only when the source itself is a
# quotation record (Wikiquote / quote) OR the text is wrapped in quotation marks.
_QUOTE_RX = re.compile(r"[\"“][^\"”]{15,}[\"”]")


def _looks_like_quote(ev: EvidenceItem) -> bool:
    st = (ev.source_type or "").lower()
    title = (ev.source_title or "").lower()
    if "quote" in st or "wikiquote" in title:
        return True
    return bool(_QUOTE_RX.search(ev.text or ""))


def _select_mode(requested: str, intent: str, temporal: TemporalAnalysis) -> str:
    """Resolve the effective response mode.

    The user's requested mode is respected, except the Historical Reality Guard
    can *upgrade* a persona-mode answer to current-context when the question is
    clearly about events after the persona's lifetime."""
    mode = requested if requested in VALID_MODES else MODE_PERSONA
    if mode == MODE_EVIDENCE:
        return MODE_EVIDENCE
    if mode == MODE_HISTORICAL:
        # Historical mode intentionally ignores post-cutoff info.
        return MODE_HISTORICAL
    # persona / current: let the temporal guard decide.
    if temporal.needs_current_context:
        return MODE_CURRENT
    return mode


def _build_reasoner_prompt(
    persona: Persona,
    question: str,
    evidence: List[EvidenceItem],
    history: List[ChatTurn],
    *,
    mode: str,
    temporal: TemporalAnalysis,
    concepts: List[str],
    language: str,
) -> tuple[str, str]:
    """Persona-conditioned, temporally-guarded prompt.

    Builds on rag_engine's persona system prompt, then layers the reasoner's
    extra rules: mode-specific behaviour and the Historical Reality Guard."""
    system, user = rag_engine._build_prompts(persona, question, evidence, history, language)

    guard_lines: List[str] = []
    if mode == MODE_EVIDENCE:
        guard_lines.append(
            "Answer strictly from the reference notes. If they do not cover the "
            "question, say so plainly rather than speculating."
        )
    elif mode == MODE_HISTORICAL:
        guard_lines.append(
            "Answer only from what you knew during your own lifetime. Do not "
            "reference anything that happened after your time."
        )
    elif mode == MODE_CURRENT:
        guard_lines.append(
            "This question is about events after your lifetime. Do not claim to "
            "have witnessed or known them. Instead, reflect on them the way your "
            "documented worldview would — speak in your own voice about the theme, "
            "while it stays clear this is your perspective applied to something new."
        )
    else:  # persona simulation
        guard_lines.append(
            "Respond in your own documented voice and worldview. Stay faithful to "
            "how you actually thought and spoke."
        )

    if concepts:
        guard_lines.append("Themes you naturally return to: " + ", ".join(concepts[:6]) + ".")

    if guard_lines:
        system = system + "\n" + "\n".join(f"- {g}" for g in guard_lines)

    return system, user


async def reason(
    db: Session,
    persona: Persona,
    question: str,
    *,
    history: Optional[List[ChatTurn]] = None,
    mode: str = MODE_PERSONA,
    language: str = "en",
    now_year: int = 2026,
) -> ReasonResult:
    """Full persona-reasoning pipeline. Returns a structured ``ReasonResult``.

    Pipeline: QUESTION -> CLASSIFICATION -> TEMPORAL -> (CURRENT CONTEXT if
    required) -> PERSONA EVIDENCE -> MODE -> GENERATION -> EVIDENCE/QUOTE CHECK.
    The persona is never allowed to answer current-world questions from its
    historical corpus: those are answered from live retrieval, with a clearly
    labelled simulated perspective layered on top."""
    history = history or []
    requested_mode = mode if mode in VALID_MODES else MODE_PERSONA
    intent = detect_intent(question)
    classification = qc.classify(question)

    # -- structured, restart-durable temporal boundary ------------------- #
    cutoff_date, cutoff_reason = _structured_cutoff(persona)
    lifespan = _persona_lifespan(persona)
    cutoff_year = year_of(cutoff_date) if cutoff_date else lifespan.knowledge_cutoff()
    temporal = analyze_question(
        question, cutoff_year, now_year=now_year,
        cutoff_date=cutoff_date, cutoff_reason=cutoff_reason,
    )
    boundary_display = temporal.boundary_display or (
        format_date_display(cutoff_date) if cutoff_date else ""
    )

    # -- small talk / greeting: persona voice, no heavy retrieval --------- #
    if classification.is_smalltalk or is_smalltalk(question):
        system, user = rag_engine._build_prompts(persona, question, [], history, language)
        text, provider_used = await llm_provider.complete(
            system, user, demo_persona_name=persona.name,
            demo_question=question, demo_evidence=[], language=language,
        )
        return ReasonResult(
            message=text, response_type=LABEL_SIMULATION, mode=MODE_PERSONA,
            requested_mode=requested_mode, intent=intent, evidence=[],
            evidence_coverage="LOW", limitations=[], provider=provider_used,
            temporal=temporal.as_dict(), worldview_concepts=[],
            category=classification.category, requires_current_context=False,
            current_context_status="not_required", knowledge_cutoff=cutoff_date,
            reasoning={
                "question": question,
                "intent": intent,
                "classification": classification.as_dict(),
                "temporal_context": temporal.note,
                "persona_evidence": [],
                "worldview_concepts": [],
                "conflicts": [],
                "note": "Greeting / small talk — answered directly in persona voice.",
            },
        )

    # -- does this question require live present-day context? ------------- #
    requires_current = bool(
        classification.requires_current_context or temporal.needs_current_context
    )
    # Identity / "about yourself" questions never require current context.
    if classification.is_identity and not classification.requires_current_context:
        requires_current = False

    # -- persona evidence retrieval (documented corpus only) -------------- #
    hits = rag_engine.retrieve(db, persona.id, question)
    evidence: List[EvidenceItem] = []
    for chunk, source, score in hits:
        if score < rag_engine.MIN_SIMILARITY:
            continue
        evidence.append(
            EvidenceItem(
                chunk_id=chunk.id, source_id=chunk.source_id,
                source_title=source.title if source else "Unknown source",
                source_type=source.source_type if source else "text",
                publication_date=source.publication_date if source else "",
                url=source.url if source else "",
                timestamp=chunk.start_time if (chunk.start_time or 0) > 0 else None,
                page=chunk.page if chunk.page else None,
                relevance=round(score, 4), text=chunk.text,
            )
        )

    coverage = rag_engine._coverage([e.relevance for e in evidence])
    concepts = _worldview_concepts(persona, question, evidence)

    current_items: List[dict] = []
    current_used = False
    current_status = "not_required"
    warnings: List[str] = []
    limitations: List[str] = []

    # ==================================================================== #
    # CURRENT-CONTEXT BRANCH — live retrieval, never persona corpus
    # ==================================================================== #
    if requires_current:
        effective_mode = MODE_CURRENT
        # Live retrieval, off the event loop (sync httpx client inside).
        current_result = await asyncio.to_thread(cc.retrieve_current_context, question)
        current_items = [i.as_dict() for i in current_result.items]
        current_used = current_result.used
        current_status = current_result.status

        # Persona PERSPECTIVE only — the LLM reflects the worldview on the theme
        # and must NOT assert current facts (those come from live items above).
        system, user = _build_reasoner_prompt(
            persona, question, evidence, history,
            mode=MODE_CURRENT, temporal=temporal, concepts=concepts, language=language,
        )
        perspective, provider_used = await llm_provider.complete(
            system, user, demo_persona_name=persona.name,
            demo_question=question, demo_evidence=[e.text for e in evidence],
            language=language,
        )

        message = _assemble_current_message(
            persona_name=persona.name, perspective=perspective,
            current_result=current_result, evidence=evidence,
            boundary_display=boundary_display,
        )

        if current_status == "unavailable":
            warnings.append(cc.UNAVAILABLE_MESSAGE)
            limitations.append(
                "No live search provider is configured, so no current facts could "
                "be retrieved. Only a simulated worldview perspective is shown."
            )
        elif current_status == "error":
            warnings.append("Live search provider error — current facts omitted (not fabricated).")
        elif current_status == "empty":
            warnings.append("Live search returned no current results for this question.")

        limitations.append(
            "This response applies the persona's documented worldview to events "
            "after their lifetime. It is a simulated perspective, not a record of "
            "anything the person actually said."
        )

    # ==================================================================== #
    # STANDARD BRANCH — evidence / persona / historical
    # ==================================================================== #
    else:
        effective_mode = _select_mode(requested_mode, intent, temporal)
        system, user = _build_reasoner_prompt(
            persona, question, evidence, history,
            mode=effective_mode, temporal=temporal, concepts=concepts, language=language,
        )
        message, provider_used = await llm_provider.complete(
            system, user, demo_persona_name=persona.name,
            demo_question=question, demo_evidence=[e.text for e in evidence],
            language=language,
        )
        if coverage == "LOW":
            limitations.append("Low evidence coverage — the response may be incomplete or generic.")
        if not evidence:
            limitations.append("No matching passages were retrieved for this question.")

    # -- shared limitations ---------------------------------------------- #
    if persona.is_demo:
        limitations.append(
            "Demo persona: the corpus is clearly-labelled demonstration data, not "
            "verified historical transcripts."
        )
    if embedding_service.backend == "hashing":
        limitations.append(
            "Retrieval is running on the offline lexical fallback embedder "
            "(install sentence-transformers for semantic retrieval)."
        )

    # -- quote authenticity (§18): a generated answer is NEVER a quote ---- #
    response_type = LABEL_SIMULATION
    quote_sources = [e.source_title for e in evidence if _looks_like_quote(e)]

    # -- citations: current-context and persona evidence, kept distinct --- #
    citations: List[dict] = []
    for it in current_items:
        citations.append({
            "type": "current_context",
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "source": it.get("source", ""),
            "publication_date": it.get("publication_date", ""),
            "retrieved_at": it.get("retrieved_at", ""),
        })
    for e in evidence[:6]:
        citations.append({
            "type": "persona_evidence",
            "title": e.source_title,
            "url": e.url,
            "source": e.source_type,
            "publication_date": e.publication_date,
            "is_quote": _looks_like_quote(e),
        })

    # -- reasoning trace (§22 "Why this response?") ----------------------- #
    reasoning = {
        "question": question,
        "intent": intent,
        "mode": effective_mode,
        "classification": classification.as_dict(),
        "temporal_context": temporal.note,
        "temporal_markers": temporal.markers,
        "knowledge_boundary": boundary_display or "unavailable",
        "current_context_status": current_status,
        "current_context": current_items,
        "persona_evidence": [
            {
                "source_title": e.source_title,
                "source_type": e.source_type,
                "relevance": e.relevance,
                "is_quote": _looks_like_quote(e),
                "excerpt": (e.text[:220] + "…") if len(e.text) > 220 else e.text,
            }
            for e in evidence[:6]
        ],
        "worldview_concepts": concepts,
        "verified_quote_sources": quote_sources,
        "conflicts": [],  # populated by the contradiction engine when available
        "coverage": coverage,
    }

    return ReasonResult(
        message=message, response_type=response_type, mode=effective_mode,
        requested_mode=requested_mode, intent=intent, evidence=evidence,
        evidence_coverage=coverage, limitations=limitations, provider=provider_used,
        temporal=temporal.as_dict(), worldview_concepts=concepts, reasoning=reasoning,
        category=classification.category, requires_current_context=requires_current,
        current_context_used=current_used, current_context_status=current_status,
        current_context=current_items, citations=citations, warnings=warnings,
        knowledge_cutoff=cutoff_date,
    )

