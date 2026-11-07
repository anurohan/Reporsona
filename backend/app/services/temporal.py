"""Historical Reality Guard — temporal awareness for persona simulation.

Pure-stdlib module (no third-party deps) so it is trivially testable and cannot
break the import graph. Two jobs:

1. ``parse_lifespan(text, summary)`` — extract birth / death years from
   biographical prose (Wikipedia summary, extract, etc). Deceased persons get a
   ``knowledge_cutoff`` equal to their death year; living persons have no cutoff.

2. ``analyze_question(question, cutoff_year, now_year)`` — classify a user
   question against the persona's knowledge boundary: does it reference a year
   after the cutoff? does it use present-tense "current events" markers? is it a
   hypothetical projection ("what would you say about ...")? The result drives
   the Current-Context + Persona response mode and the mandatory "this occurred
   after the person's lifetime" labelling.

Nothing here fabricates facts. It only *classifies* the temporal relationship so
the reasoner can be honest about what the documented person could have known.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

# --------------------------------------------------------------------------- #
# Regexes
# --------------------------------------------------------------------------- #
# A plausible historical/near-future year (1000–2099). Avoids matching "247" or
# random 5-digit numbers.
_YEAR_RE = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")

# "(born 11 December 1931)", "b. 1931", "born 1931"
# The gap allows day-numbers/month names ("11 December ") but NOT a period, so
# it never crosses a sentence boundary. The 4-digit capture group ensures a
# 2-digit day like "11" is skipped in favour of the real year.
_BORN_RE = re.compile(
    r"\b(?:born|b\.)\s*(?:[^.]{0,24}?)(1[0-9]{3}|20[0-9]{2})\b",
    re.IGNORECASE,
)
# "died 19 January 1990", "passed away in 1990".
#
# Do not match the terse ``d. 1990`` notation here. In unstructured article
# text it is too easy to confuse with a person's middle initial (for example
# "Narendra D. ... 1989"), which created false death dates for living people.
# Parenthesised lifespan ranges remain supported below and are much safer.
_DIED_RE = re.compile(
    r"\b(?:died|passed away)\s*(?:[^.]{0,24}?)(1[0-9]{3}|20[0-9]{2})\b",
    re.IGNORECASE,
)
# "(1931–1990)" / "(1931-1990)" / "1931 – 1990" — a birth–death range in parens
_RANGE_RE = re.compile(
    r"\(?\s*(1[0-9]{3}|20[0-9]{2})\s*[–\-—]\s*(1[0-9]{3}|20[0-9]{2})\s*\)?"
)

# Present-tense "what is happening now" markers.
_CURRENT_MARKERS = re.compile(
    r"\b(today|nowadays|currently|right\s*now|these\s*days|this\s*(year|month|week)|"
    r"latest|recent(?:ly)?|modern|present[\s-]*day|21st\s*century|"
    r"in\s*20[2-9][0-9]|going\s*on\s*(?:now|today)|at\s*the\s*moment|"
    r"aaj\s*kal|abhi|aajkal|is\s*waqt)\b",
    re.IGNORECASE,
)

# Hypothetical-projection markers ("what would X say about ...").
_PROJECTION_MARKERS = re.compile(
    r"\b(what\s*would\s*you|how\s*would\s*you|what\s*do\s*you\s*think\s*about|"
    r"your\s*(?:view|opinion|take)\s*on|if\s*you\s*(?:were|saw)|"
    r"would\s*you\s*(?:say|think|feel))\b",
    re.IGNORECASE,
)


@dataclass
class Lifespan:
    """A persona's documented temporal boundary."""

    birth_year: Optional[int] = None
    death_year: Optional[int] = None

    @property
    def is_deceased(self) -> bool:
        return self.death_year is not None

    def knowledge_cutoff(self) -> Optional[int]:
        """Year past which the documented person could not have known events.

        Deceased -> death year. Living -> ``None`` (no historical cutoff)."""
        return self.death_year

    def as_dict(self) -> dict:
        return {
            "birth_year": self.birth_year,
            "death_year": self.death_year,
            "is_deceased": self.is_deceased,
            "knowledge_cutoff": self.knowledge_cutoff(),
        }


@dataclass
class TemporalAnalysis:
    """Classification of a question against a persona's knowledge cutoff."""

    referenced_year: Optional[int] = None
    is_current_context: bool = False
    is_after_cutoff: bool = False
    is_projection: bool = False
    cutoff_year: Optional[int] = None
    note: str = ""
    markers: List[str] = field(default_factory=list)
    # Structured boundary for the UI (§17 display requirement).
    cutoff_date: str = ""            # ISO date or bare year, "" if unknown
    cutoff_reason: str = ""          # why this boundary exists
    boundary_display: str = ""       # e.g. "19 Jan 1990" or "" when unavailable

    @property
    def needs_current_context(self) -> bool:
        """True when the question concerns something the documented person could
        not have known, so the answer must be labelled as a present-day
        simulated perspective rather than a historical recollection."""
        return bool(self.is_after_cutoff or self.is_current_context)

    def as_dict(self) -> dict:
        return {
            "referenced_year": self.referenced_year,
            "is_current_context": self.is_current_context,
            "is_after_cutoff": self.is_after_cutoff,
            "is_projection": self.is_projection,
            "cutoff_year": self.cutoff_year,
            "needs_current_context": self.needs_current_context,
            "note": self.note,
            "markers": self.markers,
            "cutoff_date": self.cutoff_date,
            "cutoff_reason": self.cutoff_reason,
            "boundary_display": self.boundary_display,
        }


def _first_int(match: Optional[re.Match]) -> Optional[int]:
    return int(match.group(1)) if match else None


# --------------------------------------------------------------------------- #
# Date formatting / cutoff derivation (structured, restart-durable boundary)
# --------------------------------------------------------------------------- #
_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_ISO_RE = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})\s*$")
_YEAR_ONLY_RE = re.compile(r"^\s*(\d{3,4})\s*$")


def format_date_display(value: str) -> str:
    """Human-readable date, e.g. ``1990-01-19`` -> ``19 Jan 1990``.

    Accepts an ISO ``YYYY-MM-DD`` date or a bare year. Returns "" for anything
    unparseable so callers can decide on a fallback (never guesses a date)."""
    v = (value or "").strip()
    if not v:
        return ""
    m = _ISO_RE.match(v)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{d} {_MONTHS[mo - 1][:3]} {y}"
    m = _YEAR_ONLY_RE.match(v)
    if m:
        return m.group(1)
    return ""


def year_of(value: str) -> Optional[int]:
    """Extract the year from an ISO date or bare-year string."""
    v = (value or "").strip()
    m = _ISO_RE.match(v) or _YEAR_ONLY_RE.match(v)
    if m:
        return int(m.group(1))
    return None


def derive_cutoff(
    *,
    birth_date: str = "",
    death_date: str = "",
    birth_year: Optional[int] = None,
    death_year: Optional[int] = None,
) -> tuple[str, str]:
    """Compute ``(knowledge_cutoff, reason)`` for a persona from whatever is
    known. The rule is person-agnostic: a documented death bounds knowledge.

    * death date/year known -> cutoff = death date (full ISO if available, else
      the year as a string), reason "documented death date".
    * otherwise -> cutoff "" (living or unknown), reason explains which.
    """
    if death_date and _ISO_RE.match(death_date.strip()):
        return death_date.strip(), "documented death date"
    if death_year:
        return str(death_year), "documented death year"
    if birth_date or birth_year:
        return "", "no documented death date (living or unknown)"
    return "", "no documented lifespan"


# Full-date extraction: "11 December 1931" / "December 11, 1931".
_MONTH_ALT = "|".join(_MONTHS)
_DMY_RE = re.compile(rf"\b(\d{{1,2}})\s+({_MONTH_ALT})\s+(\d{{4}})\b", re.IGNORECASE)
_MDY_RE = re.compile(rf"\b({_MONTH_ALT})\s+(\d{{1,2}}),?\s+(\d{{4}})\b", re.IGNORECASE)


def _iso_from_match(m: Optional[re.Match], order: str) -> str:
    if not m:
        return ""
    if order == "dmy":
        d, mon, y = m.group(1), m.group(2), m.group(3)
    else:  # mdy
        mon, d, y = m.group(1), m.group(2), m.group(3)
    try:
        mo = next(i for i, name in enumerate(_MONTHS, start=1)
                  if name.lower() == mon.lower())
        return f"{int(y):04d}-{mo:02d}-{int(d):02d}"
    except Exception:  # noqa: BLE001
        return ""


def parse_full_dates(text: str = "", summary: str = "") -> tuple[str, str]:
    """Best-effort extraction of full ISO birth/death dates from biographical
    prose. Returns ``(birth_date, death_date)`` as ISO strings, "" when a
    confident date is not found (never guesses)."""
    blob = f"{summary}\n{text}".strip()
    if not blob:
        return "", ""

    def _find(keyword_re: re.Pattern) -> str:
        m = keyword_re.search(blob)
        if not m:
            return ""
        window = blob[m.start(): m.start() + 60]
        return _iso_from_match(_DMY_RE.search(window), "dmy") or \
            _iso_from_match(_MDY_RE.search(window), "mdy")

    born = _find(re.compile(r"\b(?:born|b\.)\b", re.IGNORECASE))
    died = _find(re.compile(r"\b(?:died|passed away|d\.)\b", re.IGNORECASE))
    return born, died


def parse_lifespan(text: str = "", summary: str = "") -> Lifespan:
    """Extract birth/death years from biographical prose.

    Strategy: try an explicit ``born ... died ...`` pair first, then a
    ``(1931–1990)`` parenthetical range, and finally leave fields ``None`` when
    nothing is confidently found (never guess)."""
    blob = f"{summary}\n{text}".strip()
    if not blob:
        return Lifespan()

    birth = _first_int(_BORN_RE.search(blob))
    death = _first_int(_DIED_RE.search(blob))

    if birth is None or death is None:
        # A Wikipedia article often contains many other people's lifespans
        # (parents, collaborators, historical figures). Only a lead summary,
        # or the opening of a source with no summary, is allowed to define the
        # subject's own parenthesised lifespan.
        lead = (summary or text[:500]).strip()
        m = _RANGE_RE.search(lead)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            # Only trust a range when it is plausible (b > a, spans < 130 yrs).
            if b > a and (b - a) < 130:
                birth = birth or a
                death = death or b

    # Sanity: reject impossible orderings.
    if birth is not None and death is not None and death < birth:
        birth, death = None, None

    return Lifespan(birth_year=birth, death_year=death)


def analyze_question(
    question: str,
    cutoff_year: Optional[int] = None,
    now_year: int = 2026,
    *,
    cutoff_date: str = "",
    cutoff_reason: str = "",
) -> TemporalAnalysis:
    """Classify ``question`` against the persona's ``cutoff_year``.

    ``cutoff_year`` is typically ``Lifespan.knowledge_cutoff()`` (death year) or
    ``None`` for a living persona / unknown boundary. ``cutoff_date`` /
    ``cutoff_reason`` carry the structured, restart-durable boundary for display
    (e.g. ``"1990-01-19"`` / ``"documented death date"``)."""
    q = (question or "").strip()
    markers: List[str] = []

    # If a full cutoff_date was supplied but no year, derive the year from it.
    if cutoff_year is None and cutoff_date:
        cutoff_year = year_of(cutoff_date)

    boundary_display = format_date_display(cutoff_date) if cutoff_date else (
        str(cutoff_year) if cutoff_year is not None else ""
    )

    # Largest referenced year in the question (e.g. "in 2024").
    years = [int(y) for y in _YEAR_RE.findall(q)]
    referenced_year = max(years) if years else None

    is_current = bool(_CURRENT_MARKERS.search(q))
    if is_current:
        markers.append("present-tense/current-events phrasing")

    is_projection = bool(_PROJECTION_MARKERS.search(q))
    if is_projection:
        markers.append("hypothetical projection phrasing")

    is_after_cutoff = False
    if cutoff_year is not None:
        if referenced_year is not None and referenced_year > cutoff_year:
            is_after_cutoff = True
            markers.append(f"references {referenced_year} (after cutoff {cutoff_year})")
        # "today/currently" for a deceased person is always after their lifetime.
        if is_current:
            is_after_cutoff = True

    # Build a human-readable note for the UI.
    if cutoff_year is None:
        note = (
            "No historical knowledge cutoff is recorded for this persona; "
            "answers draw on documented material without a temporal boundary."
        )
    elif is_after_cutoff:
        label = boundary_display or str(cutoff_year)
        note = (
            f"This question concerns events after the persona's documented "
            f"knowledge boundary ({label}). The response is a present-day "
            f"simulated perspective, not a historical recollection."
        )
    else:
        label = boundary_display or str(cutoff_year)
        note = (
            f"This question falls within the persona's documented period "
            f"(through {label})."
        )

    return TemporalAnalysis(
        referenced_year=referenced_year,
        is_current_context=is_current,
        is_after_cutoff=is_after_cutoff,
        is_projection=is_projection,
        cutoff_year=cutoff_year,
        note=note,
        markers=markers,
        cutoff_date=cutoff_date,
        cutoff_reason=cutoff_reason,
        boundary_display=boundary_display,
    )
