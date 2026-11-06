"""Unit tests for the Persona Reasoner's pure decision logic (§16, §18, §23).

These cover intent detection, response-mode selection (including the Historical
Reality Guard upgrade), and quote-authenticity classification. They avoid the
LLM/DB by testing the standalone helpers, so they run under the normal pytest
suite without a model server.
"""

from __future__ import annotations

from app.schemas import EvidenceItem
from app.services import persona_reasoner as pr
from app.services.temporal import analyze_question


# --------------------------------------------------------------------------- #
# Intent detection
# --------------------------------------------------------------------------- #
def test_intent_greeting():
    assert pr.detect_intent("Hello there!") == "greeting"


def test_intent_opinion():
    assert pr.detect_intent("What do you think about freedom?") == "opinion"


def test_intent_current_event():
    assert pr.detect_intent("How is the economy doing?") == "current_event"


def test_intent_biographical():
    assert pr.detect_intent("When were you born?") == "biographical"


def test_intent_general_fallback():
    assert pr.detect_intent("Describe a flower.") == "general"


# --------------------------------------------------------------------------- #
# Mode selection + Historical Reality Guard
# --------------------------------------------------------------------------- #
def _ta(question: str, cutoff):
    return analyze_question(question, cutoff_year=cutoff)


def test_mode_evidence_is_preserved():
    ta = _ta("What did you write?", 1990)
    assert pr._select_mode(pr.MODE_EVIDENCE, "general", ta) == pr.MODE_EVIDENCE


def test_mode_historical_ignores_current():
    # Even a "nowadays" question stays historical when historical mode requested.
    ta = _ta("How is politics nowadays?", 1990)
    assert pr._select_mode(pr.MODE_HISTORICAL, "current_event", ta) == pr.MODE_HISTORICAL


def test_persona_mode_upgraded_to_current_after_cutoff():
    ta = _ta("What about the 2024 election?", 1990)
    assert ta.needs_current_context is True
    assert pr._select_mode(pr.MODE_PERSONA, "current_event", ta) == pr.MODE_CURRENT


def test_persona_mode_stays_persona_within_lifetime():
    ta = _ta("What did meditation mean to you in 1975?", 1990)
    assert ta.needs_current_context is False
    assert pr._select_mode(pr.MODE_PERSONA, "opinion", ta) == pr.MODE_PERSONA


def test_living_persona_never_forced_to_current():
    ta = _ta("What about the 2024 election?", None)  # living persona, no cutoff
    assert pr._select_mode(pr.MODE_PERSONA, "current_event", ta) == pr.MODE_PERSONA


# --------------------------------------------------------------------------- #
# Quote authenticity (§18)
# --------------------------------------------------------------------------- #
def _ev(text: str, source_type: str = "article", source_title: str = "Article"):
    return EvidenceItem(
        chunk_id="c", source_id="s", source_title=source_title,
        source_type=source_type, relevance=0.5, text=text,
    )


def test_quote_detected_from_wikiquote_source():
    assert pr._looks_like_quote(_ev("Freedom is the ultimate value.", "quote")) is True


def test_quote_detected_from_quotation_marks():
    assert pr._looks_like_quote(_ev('He said, "Be yourself and life will follow."')) is True


def test_plain_prose_is_not_a_quote():
    assert pr._looks_like_quote(_ev("This is an encyclopedic paragraph about his life.")) is False


if __name__ == "__main__":
    import sys, traceback  # noqa: E401

    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
