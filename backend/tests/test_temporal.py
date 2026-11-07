"""Unit tests for the Historical Reality Guard (temporal.py, §17).

Pure-stdlib module, so these run without any third-party dependencies.
"""

from __future__ import annotations

from app.services.temporal import (
    Lifespan,
    analyze_question,
    parse_lifespan,
)


# --------------------------------------------------------------------------- #
# Lifespan parsing
# --------------------------------------------------------------------------- #
def test_parse_born_died_prose():
    span = parse_lifespan(summary="Osho (born 11 December 1931 – died 19 January 1990) was a mystic.")
    assert span.birth_year == 1931
    assert span.death_year == 1990
    assert span.is_deceased is True
    assert span.knowledge_cutoff() == 1990


def test_parse_parenthetical_range():
    span = parse_lifespan(summary="Albert Einstein (1879–1955) was a physicist.")
    assert span.birth_year == 1879
    assert span.death_year == 1955


def test_parse_living_person_has_no_cutoff():
    span = parse_lifespan(summary="Jane Doe (born 1980) is an author.")
    assert span.birth_year == 1980
    assert span.death_year is None
    assert span.is_deceased is False
    assert span.knowledge_cutoff() is None


def test_initials_do_not_create_false_death_date():
    # Regression: a middle initial followed by a year must never be read as
    # the abbreviated "d. YEAR" death notation.
    span = parse_lifespan(
        summary="Narendra D. Modi was born in 1950 and entered public life in 1989."
    )
    assert span.birth_year == 1950
    assert span.death_year is None


def test_relative_lifespan_does_not_override_living_subject():
    span = parse_lifespan(
        summary="Narendra Modi is an Indian politician born in 1950.",
        text="His father Damodardas Modi (1915–1989) ran a tea stall.",
    )
    assert span.birth_year == 1950
    assert span.death_year is None


def test_parse_rejects_impossible_order():
    span = parse_lifespan(summary="born 1990 died 1931")
    assert span.birth_year is None and span.death_year is None


def test_parse_empty():
    span = parse_lifespan()
    assert span == Lifespan()


# --------------------------------------------------------------------------- #
# Question analysis
# --------------------------------------------------------------------------- #
def test_future_year_after_cutoff():
    a = analyze_question("What do you think about the 2024 election?", cutoff_year=1990)
    assert a.referenced_year == 2024
    assert a.is_after_cutoff is True
    assert a.needs_current_context is True


def test_current_marker_after_cutoff_for_deceased():
    a = analyze_question("How is politics going nowadays?", cutoff_year=1990)
    assert a.is_current_context is True
    assert a.is_after_cutoff is True
    assert a.needs_current_context is True


def test_within_lifetime_question():
    a = analyze_question("What did you feel about meditation in 1975?", cutoff_year=1990)
    assert a.is_after_cutoff is False
    assert a.needs_current_context is False


def test_projection_phrasing_detected():
    a = analyze_question("What would you say about modern technology?", cutoff_year=1990)
    assert a.is_projection is True
    # "modern" is a current marker -> current context for a deceased persona
    assert a.needs_current_context is True


def test_living_persona_no_boundary():
    a = analyze_question("What about the 2024 election?", cutoff_year=None)
    assert a.is_after_cutoff is False
    assert a.cutoff_year is None
    assert "no historical knowledge cutoff" in a.note.lower()


def test_hinglish_current_marker():
    a = analyze_question("Aaj kal duniya kaisi chal rahi hai?", cutoff_year=1990)
    assert a.is_current_context is True
    assert a.needs_current_context is True


if __name__ == "__main__":  # allow running as a plain stdlib script
    import sys
    import traceback

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
