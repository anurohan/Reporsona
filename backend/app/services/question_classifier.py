"""Question classification for the persona reasoner.

Pure-stdlib (no third-party deps) so it is trivially testable and cannot break
the import graph. Its single public entry point is ``classify(question)``, which
returns a :class:`Classification` describing *what kind* of question was asked
and, crucially, whether answering it honestly *requires live current-world
context* the documented (possibly deceased) person could not have known.

This layer exists to stop the biography/persona composer from hijacking a
current-events question. For example the query

    "What are the most relevant current political developments in India today?"

must classify as ``current_politics`` with ``requires_current_context=True`` so
the reasoner performs a live retrieval instead of weaving old corpus snippets
into a first-person "biography".

Nothing here is person-specific and nothing fabricates content — it only labels
the question's *type* from surface cues, leaving retrieval/generation to callers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

# --------------------------------------------------------------------------- #
# Category constants
# --------------------------------------------------------------------------- #
CAT_HISTORICAL = "historical"
CAT_BIOGRAPHY = "biography"
CAT_FACTUAL_PERSON = "factual_person"
CAT_QUOTE = "quote"
CAT_OPINION_HISTORICAL = "opinion_about_historical_topic"
CAT_CURRENT_EVENT = "current_event"
CAT_CURRENT_POLITICS = "current_politics"
CAT_CURRENT_NEWS = "current_news"
CAT_CURRENT_SOCIETY = "current_society"
CAT_GENERAL = "general"
CAT_UNCLEAR = "unclear"

# Categories that demand live, present-day retrieval.
CURRENT_CATEGORIES = {
    CAT_CURRENT_EVENT,
    CAT_CURRENT_POLITICS,
    CAT_CURRENT_NEWS,
    CAT_CURRENT_SOCIETY,
}

# --------------------------------------------------------------------------- #
# Lexicons / regexes
# --------------------------------------------------------------------------- #
# Present-tense "what is happening now" markers (English + a little Hinglish).
_CURRENT_MARKERS = re.compile(
    r"\b(today|todays|nowadays|currently|current|right\s*now|these\s*days|"
    r"this\s*(?:year|month|week)|latest|recent(?:ly)?|modern|present[\s-]*day|"
    r"21st\s*century|at\s*the\s*moment|as\s*of\s*(?:now|today)|"
    r"going\s*on|happening|up[\s-]*to[\s-]*date|"
    r"aaj\s*kal|aajkal|abhi|is\s*waqt)\b",
    re.IGNORECASE,
)

# A near-present year (2020-2099) strongly implies current context.
_RECENT_YEAR = re.compile(r"\b(20[2-9][0-9])\b")

# Politics / governance stem — note "politic" covers political/politics/politician.
_POLITICS = re.compile(
    r"\b(politic\w*|govern(?:ment|ance|s|ing)?|election\w*|"
    r"parliament\w*|congress|senate|president\w*|prime\s*minister|\bpm\b|"
    r"minister\w*|policy|policies|legislation|geopolit\w*|"
    r"democracy|democratic|republican|voter\w*|voting|ballot|coalition|"
    r"cabinet|diplomat\w*|sanction\w*|referendum|bjp|modi|opposition\s*party)\b",
    re.IGNORECASE,
)

# News / breaking-events stem.
_NEWS = re.compile(
    r"\b(news|headline\w*|breaking|report\w*|update\w*|"
    r"press|media\s*coverage|announced|announcement)\b",
    re.IGNORECASE,
)

# Society / economy / culture "what's going on in the world" stem.
_SOCIETY = re.compile(
    r"\b(societ\w*|social\s*issue\w*|econom\w*|inflation|market\w*|"
    r"stock\w*|climate|pandemic|technolog\w*|\bai\b|"
    r"culture|cultural|trend\w*|world\s*affairs|current\s*affairs)\b",
    re.IGNORECASE,
)

# Quote / verbatim request.
_QUOTE = re.compile(
    r"\b(quote|quotation|exact\s*words|verbatim|say\s*exactly|"
    r"what\s*did\s*(?:you|he|she|they)\s*say|actual\s*words)\b",
    re.IGNORECASE,
)

# Biography / identity ("who are you", "tell me about yourself", "when were you born").
_IDENTITY = re.compile(
    r"\b(who\s*(?:are|were)\s*you|tell\s*me\s*about\s*(?:your|yourself|you)|"
    r"introduce\s*yourself|what(?:'s| is)\s*your\s*name|"
    r"when\s*(?:were|was)\s*you\s*born|where\s*(?:were|was)\s*you\s*born|"
    r"your\s*(?:life|biography|childhood|early\s*life)|"
    r"about\s*your\s*life)\b",
    re.IGNORECASE,
)

# Third-person biographical/factual-about-the-person cues.
_FACTUAL_PERSON = re.compile(
    r"\b(when\s*(?:were|was|did)\s*(?:he|she|they|\w+)\s*(?:born|die|found)|"
    r"where\s*(?:was|were|did)|"
    r"biograph\w*|born\s*in|died\s*in|date\s*of\s*(?:birth|death)|"
    r"how\s*old|his\s*life|her\s*life|their\s*life)\b",
    re.IGNORECASE,
)

# Opinion / projection ("what would you say about", "your view on").
_OPINION = re.compile(
    r"\b(what\s*(?:would|do)\s*you\s*(?:say|think|feel)|how\s*would\s*you|"
    r"your\s*(?:view|opinion|take|thoughts?|perspective)\s*(?:on|about)|"
    r"what\s*do\s*you\s*think\s*about|if\s*you\s*(?:were|saw)|"
    r"would\s*you\s*(?:say|think|feel|agree))\b",
    re.IGNORECASE,
)

# Smalltalk greetings (never a current-events question). Allows a couple of
# trailing filler words ("hello there", "hi everyone", "thanks a lot").
_SMALLTALK = re.compile(
    r"^\s*(hi|hii+|hey|hello|namaste|namaskar|yo|sup|"
    r"good\s*(?:morning|afternoon|evening|night)|"
    r"how\s*are\s*you|kaise\s*ho|thanks?|thank\s*you|thankyou|"
    r"ok(?:ay)?|cool|nice|great|bye|goodbye)\b(?:\s+\w+){0,2}[\s!.?]*$",
    re.IGNORECASE,
)

# Historical / past-tense markers.
_HISTORICAL = re.compile(
    r"\b(in\s*(?:1[0-9]{3}|20[01][0-9])|back\s*then|at\s*the\s*time|"
    r"during\s*your\s*(?:life|time)|in\s*those\s*days|historically|"
    r"in\s*the\s*(?:past|1[0-9]{2}0s|19[0-9]0s))\b",
    re.IGNORECASE,
)


@dataclass
class Classification:
    """The result of classifying a user question."""

    category: str = CAT_UNCLEAR
    requires_current_context: bool = False
    is_identity: bool = False
    is_smalltalk: bool = False
    is_quote_request: bool = False
    is_opinion: bool = False
    matched: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "requires_current_context": self.requires_current_context,
            "is_identity": self.is_identity,
            "is_smalltalk": self.is_smalltalk,
            "is_quote_request": self.is_quote_request,
            "is_opinion": self.is_opinion,
            "matched": self.matched,
            "confidence": round(self.confidence, 3),
        }


def _has_current_signal(q: str) -> bool:
    """Present-tense marker OR a near-present (>=2020) year."""
    return bool(_CURRENT_MARKERS.search(q) or _RECENT_YEAR.search(q))


def classify(question: str) -> Classification:
    """Classify ``question`` into one of the documented categories.

    Priority order matters: smalltalk and identity are resolved first (they must
    never be mistaken for current events); then quote/opinion flags are recorded;
    then — critically — the presence of a *current* signal routes politics/news/
    society/event questions into the current-context branch; historical and
    biographical questions fall through to their past-tense categories."""
    q = (question or "").strip()
    matched: List[str] = []

    if not q:
        return Classification(category=CAT_UNCLEAR, confidence=0.0)

    # 1) Pure smalltalk greeting (short, no substantive topic).
    if _SMALLTALK.match(q) and len(q.split()) <= 6:
        return Classification(
            category=CAT_GENERAL, is_smalltalk=True,
            matched=["smalltalk"], confidence=0.9,
        )

    current_signal = _has_current_signal(q)
    is_identity = bool(_IDENTITY.search(q))
    is_quote = bool(_QUOTE.search(q))
    is_opinion = bool(_OPINION.search(q))
    has_politics = bool(_POLITICS.search(q))
    has_news = bool(_NEWS.search(q))
    has_society = bool(_SOCIETY.search(q))

    # 2) Identity / "about yourself" — but only when NOT asking about current
    #    world affairs (e.g. "what's your view on today's politics" is not an
    #    identity question even though it says "you").
    if is_identity and not current_signal:
        return Classification(
            category=CAT_BIOGRAPHY, is_identity=True,
            matched=["identity"], confidence=0.85,
        )

    # 3) Current-context branch: a present-tense signal + a worldly topic.
    if current_signal:
        matched.append("current-signal")
        if has_politics:
            matched.append("politics")
            return Classification(
                category=CAT_CURRENT_POLITICS, requires_current_context=True,
                is_opinion=is_opinion, matched=matched, confidence=0.92,
            )
        if has_news:
            matched.append("news")
            return Classification(
                category=CAT_CURRENT_NEWS, requires_current_context=True,
                is_opinion=is_opinion, matched=matched, confidence=0.88,
            )
        if has_society:
            matched.append("society")
            return Classification(
                category=CAT_CURRENT_SOCIETY, requires_current_context=True,
                is_opinion=is_opinion, matched=matched, confidence=0.85,
            )
        # Generic "what's happening now / latest" with no specific topic.
        return Classification(
            category=CAT_CURRENT_EVENT, requires_current_context=True,
            is_opinion=is_opinion, matched=matched, confidence=0.75,
        )

    # 4) No current signal below this point → historical / persona-scoped.
    if is_quote:
        return Classification(
            category=CAT_QUOTE, is_quote_request=True,
            matched=["quote"], confidence=0.8,
        )

    # Opinion about a (historical / timeless) topic — persona worldview applies.
    if is_opinion:
        # A politics/society topic asked as an opinion but WITHOUT a current
        # signal is an opinion about a (documented-era) topic.
        cat = CAT_OPINION_HISTORICAL
        matched.append("opinion")
        if has_politics:
            matched.append("politics")
        return Classification(
            category=cat, is_opinion=True,
            matched=matched, confidence=0.7,
        )

    if _HISTORICAL.search(q):
        return Classification(
            category=CAT_HISTORICAL, matched=["historical"], confidence=0.75,
        )

    if _FACTUAL_PERSON.search(q):
        return Classification(
            category=CAT_FACTUAL_PERSON, matched=["factual-person"], confidence=0.7,
        )

    # A bare politics/news/society topic with no temporal marker: treat as a
    # documented-worldview opinion topic, not live current context.
    if has_politics or has_society or has_news:
        return Classification(
            category=CAT_OPINION_HISTORICAL,
            matched=["topic-no-temporal"], confidence=0.55,
        )

    # 5) Fallback.
    return Classification(category=CAT_GENERAL, matched=["general"], confidence=0.4)
