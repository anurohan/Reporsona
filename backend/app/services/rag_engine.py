"""Retrieval-Augmented Generation engine.

Flow: question -> query embedding -> vector retrieval -> light reranking ->
evidence selection -> persona-conditioned prompt -> LLM -> answer + evidence +
evidence-coverage + limitations. Provenance (source + timestamp/page) is carried
through for every retrieved chunk.
"""

from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Chunk, Persona, Source
from app.schemas import ChatTurn, EvidenceItem
from app.services.embeddings import embedding_service
from app.services.llm_provider import is_smalltalk, llm_provider
from app.services.vector_store import index_registry

TOP_K = 6
MIN_SIMILARITY = 0.03  # lexical-fallback friendly; neural models score higher


def ensure_index(db: Session, persona_id: str) -> None:
    """Lazily build the persona's vector index from its chunks."""
    if index_registry.has(persona_id):
        return
    chunks = list(db.scalars(select(Chunk).where(Chunk.persona_id == persona_id)))
    ids = [c.id for c in chunks]
    vectors = embedding_service.encode([c.text for c in chunks]) if chunks else []
    index_registry.build(persona_id, ids, vectors, embedding_service.dim)


def _coverage(scores: List[float]) -> str:
    strong = [s for s in scores if s >= MIN_SIMILARITY]
    if not strong:
        return "LOW"
    mean = sum(strong) / len(strong)
    if len(strong) >= 4 and mean >= 0.18:
        return "HIGH"
    if len(strong) >= 2:
        return "MEDIUM"
    return "LOW"


def retrieve(db: Session, persona_id: str, question: str, top_k: int = TOP_K):
    ensure_index(db, persona_id)
    store = index_registry.get(persona_id)
    if store is None or len(store) == 0:
        return []
    qvec = embedding_service.encode_one(question)
    hits = store.search(qvec, top_k)
    results = []
    for chunk_id, score in hits:
        chunk = db.get(Chunk, chunk_id)
        if not chunk:
            continue
        source = db.get(Source, chunk.source_id)
        results.append((chunk, source, float(score)))
    # Light reranking: prefer diverse sources among near-ties.
    seen_sources: set[str] = set()
    reranked = []
    for chunk, source, score in results:
        bonus = 0.02 if (source and source.id not in seen_sources) else 0.0
        if source:
            seen_sources.add(source.id)
        reranked.append((chunk, source, score + bonus))
    reranked.sort(key=lambda x: x[2], reverse=True)
    return reranked


_LANG_INSTRUCTION = {
    "en": "Reply in natural English.",
    "hi": (
        "Reply in Hindi. Write it in the Latin/Roman script (Hinglish spelling of "
        "Hindi words), not Devanagari, so it's easy to read. Keep it warm and simple."
    ),
    "hinglish": (
        "Reply in Hinglish — a natural mix of Hindi and English the way friends "
        "chat in India (Roman script). Keep it warm, casual and simple."
    ),
}


def _lang_key(language: str) -> str:
    l = (language or "en").strip().lower()
    if l in ("hi", "hindi"):
        return "hi"
    if l in ("hinglish", "hi-en", "hien"):
        return "hinglish"
    return "en"


def _build_prompts(persona: Persona, question: str, evidence: List[EvidenceItem], history: List[ChatTurn], language: str = "en"):
    style = ""
    if persona.profile and persona.profile.communication_style:
        style = ", ".join(persona.profile.communication_style[:5])

    identity_bits = []
    if persona.summary:
        identity_bits.append(persona.summary)
    if getattr(persona, "known_for", None):
        identity_bits.append("You are known for: " + ", ".join(persona.known_for[:6]) + ".")
    if getattr(persona, "domains", None):
        identity_bits.append("Your world: " + ", ".join(persona.domains[:6]) + ".")
    identity = " ".join(identity_bits)

    system = (
        f"You are an evidence-grounded simulation of the documented views of {persona.name}. "
        f"Speak in a natural first-person style when simulation mode is requested, but never "
        f"claim to literally be {persona.name} or imply consciousness, identity, or direct contact. "
        f"Use a warm, natural, simple, conversational human voice — like a real "
        f"conversation, not an essay or a report.\n"
        f"How to reply:\n"
        f"- Do not present generated text as a verified historical quotation. Never invent quotes. "
        f"When asked for factual support, be transparent that the answer is based on documented material.\n"
        f"- Use the reference notes below only to stay accurate about your life, "
        f"views and way of speaking. Do not quote them or refer to them.\n"
        f"- Keep it clear and fairly short unless asked to go deeper.\n"
        + (f"- Your manner of speaking: {style}.\n" if style else "")
        + f"- If something is genuinely outside what you'd know, say so simply and "
        f"honestly, in your own voice.\n"
        f"- Never invent specific quotes, dates, or events you're not sure of.\n"
        f"- {_LANG_INSTRUCTION[_lang_key(language)]}\n"
        + (f"About you: {identity}" if identity else "")
    )

    context_lines = []
    for ev in evidence:
        context_lines.append(ev.text)
    context = "\n\n".join(context_lines) if context_lines else "(nothing in particular)"

    hist = ""
    if history:
        turns = [f"{'You' if t.role == 'assistant' else 'Them'}: {t.content}" for t in history[-6:]]
        hist = "Recent conversation:\n" + "\n".join(turns) + "\n\n"

    user = (
        f"{hist}Reference notes about you (for accuracy only — never mention these):\n"
        f"{context}\n\n"
        f"Someone says to you: \"{question}\"\n\n"
        f"Reply as a documented-perspective simulation of {persona.name}, in the first person, naturally."
    )
    return system, user


async def answer(
    db: Session,
    persona: Persona,
    question: str,
    history: List[ChatTurn] | None = None,
    evidence_mode: bool = True,
    language: str = "en",
):
    history = history or []

    # Greetings / small talk: reply naturally WITHOUT running heavy retrieval.
    if is_smalltalk(question):
        system, user = _build_prompts(persona, question, [], history, language)
        text, provider_used = await llm_provider.complete(
            system, user,
            demo_persona_name=persona.name,
            demo_question=question,
            demo_evidence=[],
            language=language,
        )
        return {
            "message": text,
            "evidence": [],
            "evidence_coverage": "LOW",
            "limitations": [],
            "provider": provider_used,
        }

    hits = retrieve(db, persona.id, question)

    evidence: List[EvidenceItem] = []
    for chunk, source, score in hits:
        if score < MIN_SIMILARITY:
            continue
        evidence.append(
            EvidenceItem(
                chunk_id=chunk.id,
                source_id=chunk.source_id,
                source_title=source.title if source else "Unknown source",
                source_type=source.source_type if source else "text",
                publication_date=source.publication_date if source else "",
                url=source.url if source else "",
                timestamp=chunk.start_time if (chunk.start_time or 0) > 0 else None,
                page=chunk.page if chunk.page else None,
                relevance=round(score, 4),
                text=chunk.text,
            )
        )

    coverage = _coverage([e.relevance for e in evidence])
    system, user = _build_prompts(persona, question, evidence, history, language)

    text, provider_used = await llm_provider.complete(
        system,
        user,
        demo_persona_name=persona.name,
        demo_question=question,
        demo_evidence=[e.text for e in evidence],
        language=language,
    )

    limitations: List[str] = []
    if coverage == "LOW":
        limitations.append("Low evidence coverage — the response may be incomplete or generic.")
    if not evidence:
        limitations.append("No matching passages were retrieved for this question.")
    if persona.is_demo:
        limitations.append("Demo persona: the corpus is clearly-labelled demonstration data, not verified historical transcripts.")
    if embedding_service.backend == "hashing":
        limitations.append("Retrieval is running on the offline lexical fallback embedder (install sentence-transformers for semantic retrieval).")

    return {
        "message": text,
        "evidence": evidence if evidence_mode else [],
        "evidence_coverage": coverage,
        "limitations": limitations,
        "provider": provider_used,
    }
