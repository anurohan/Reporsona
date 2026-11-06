"""RAG retrieval + generation tests (demo generator, offline)."""

from __future__ import annotations

import asyncio

from app.services import rag_engine
from app.services.rag_engine import retrieve


def test_retrieval_finds_fear_passages(db_session, demo_persona):
    hits = retrieve(db_session, demo_persona.id, "What did he say about fear and the unknown?")
    assert hits, "expected at least one retrieved chunk"
    # 'fear' should surface among the top retrieved passages (lexical fallback
    # embedder does not guarantee an exact #1 ordering, so check the top few).
    top_texts = " ".join(chunk.text.lower() for chunk, _src, _score in hits[:3])
    assert "fear" in top_texts


def test_answer_is_grounded_and_labeled(db_session, demo_persona):
    result = asyncio.run(
        rag_engine.answer(db_session, demo_persona, "Tell me about fear.", history=[], evidence_mode=True)
    )
    assert result["provider"].startswith("demo")
    assert result["evidence_coverage"] in {"HIGH", "MEDIUM", "LOW"}
    assert isinstance(result["message"], str) and result["message"].strip()
    assert len(result["evidence"]) >= 1
    # The answer should read naturally, not with robotic meta-framing.
    low = result["message"].lower()
    assert "documented passages" not in low
    assert "sources panel" not in low
    # AI-simulation labelling now lives in the evidence panel / limitations, not
    # the message body.
    assert isinstance(result["limitations"], list)


def test_greeting_skips_retrieval(db_session, demo_persona):
    result = asyncio.run(
        rag_engine.answer(db_session, demo_persona, "hello", history=[], evidence_mode=True)
    )
    # a greeting must not drag in evidence or heavy retrieval limitations
    assert result["evidence"] == []
    assert result["limitations"] == []
    assert isinstance(result["message"], str) and result["message"].strip()


def test_unknown_question_degrades_gracefully(db_session, demo_persona):
    result = asyncio.run(
        rag_engine.answer(
            db_session, demo_persona,
            "zxqwv nonexistent gibberish token 999",
            history=[], evidence_mode=True,
        )
    )
    # should still return a string and honest limitations, never crash
    assert isinstance(result["message"], str)
    assert isinstance(result["limitations"], list)
