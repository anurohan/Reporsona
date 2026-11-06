"""Tests for the question classifier (pure-stdlib, runnable standalone).

Run either with pytest or directly:  ``python tests/test_question_classifier.py``
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.question_classifier import (  # noqa: E402
    CAT_BIOGRAPHY,
    CAT_CURRENT_EVENT,
    CAT_CURRENT_NEWS,
    CAT_CURRENT_POLITICS,
    CAT_CURRENT_SOCIETY,
    CAT_FACTUAL_PERSON,
    CAT_GENERAL,
    CAT_HISTORICAL,
    CAT_OPINION_HISTORICAL,
    CAT_QUOTE,
    classify,
)


def test_current_politics_india_today():
    """The headline regression: must NOT be biography."""
    c = classify(
        "What are the most relevant current political developments in India today?"
    )
    assert c.category == CAT_CURRENT_POLITICS, c.category
    assert c.requires_current_context is True
    assert c.is_identity is False


def test_identity_who_are_you():
    c = classify("Who are you?")
    assert c.category == CAT_BIOGRAPHY
    assert c.is_identity is True
    assert c.requires_current_context is False


def test_identity_when_born():
    c = classify("When were you born?")
    assert c.category == CAT_BIOGRAPHY
    assert c.is_identity is True


def test_smalltalk_greeting():
    c = classify("hello there")
    assert c.is_smalltalk is True
    assert c.requires_current_context is False


def test_early_life_biography():
    c = classify("Tell me about your early life and childhood.")
    assert c.category == CAT_BIOGRAPHY
    assert c.is_identity is True


def test_historical_politics_1985():
    c = classify("What political events happened in 1985?")
    assert c.category == CAT_HISTORICAL, c.category
    assert c.requires_current_context is False


def test_what_did_you_say_about_politics_is_not_current():
    """Persona-evidence question, no current signal → not current context."""
    c = classify("What did you say about politics?")
    assert c.requires_current_context is False
    assert c.category in (CAT_OPINION_HISTORICAL, CAT_QUOTE)


def test_projection_today_politics_is_current():
    c = classify(
        "What would you say about today's Indian political environment?"
    )
    assert c.category == CAT_CURRENT_POLITICS, c.category
    assert c.requires_current_context is True
    assert c.is_opinion is True


def test_current_news():
    c = classify("What's the latest news right now?")
    assert c.category in (CAT_CURRENT_NEWS, CAT_CURRENT_EVENT), c.category
    assert c.requires_current_context is True


def test_current_society_economy():
    c = classify("How is the economy doing these days?")
    assert c.category in (CAT_CURRENT_SOCIETY, CAT_CURRENT_EVENT), c.category
    assert c.requires_current_context is True


def test_recent_year_triggers_current():
    c = classify("What happened in the 2024 election?")
    assert c.requires_current_context is True
    assert c.category == CAT_CURRENT_POLITICS, c.category


def test_quote_request():
    c = classify("Give me an exact quote about meditation.")
    assert c.category == CAT_QUOTE
    assert c.is_quote_request is True


def test_opinion_timeless_topic():
    c = classify("What is your view on love?")
    assert c.category == CAT_OPINION_HISTORICAL
    assert c.is_opinion is True
    assert c.requires_current_context is False


def test_factual_person_third_person():
    c = classify("When was he born and where did he die?")
    assert c.category == CAT_FACTUAL_PERSON, c.category


def test_empty_is_unclear():
    c = classify("   ")
    assert c.category == "unclear"


def test_general_fallback():
    c = classify("Do you like tea or coffee?")
    assert c.category == CAT_GENERAL


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            passed += 1
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {fn.__name__}: {e!r}")
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
