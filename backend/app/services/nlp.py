"""Lightweight NLP utilities (pure Python, no heavy deps).

Provides semantic-ish chunking, keyword extraction and simple topic grouping.
When spaCy / NLTK are available they could be slotted in behind these same
functions, but the defaults keep Demo Mode dependency-free.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import List

_SENT_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_WORD_RE = re.compile(r"[A-Za-zÀ-ɏऀ-ॿ']+")

STOPWORDS = set(
    """
    a an and are as at be but by for from has have he her his i in is it its of on or
    that the their them they this to was were will with you your we our us not no so if
    what which who whom whose when where why how do does did done can could would should
    may might must about into over under again then than too very just also more most
    such only own same s t don now these those there here up out off down all any each
    """.split()
)


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> List[str]:
    parts = _SENT_RE.split(clean_text(text))
    return [p.strip() for p in parts if p and p.strip()]


def chunk_text(
    text: str,
    chunk_size: int = 700,
    overlap: int = 150,
) -> List[str]:
    """Semantic-ish chunking: pack whole sentences up to ``chunk_size`` chars
    with a sliding ``overlap`` (in characters) between consecutive chunks."""
    text = clean_text(text)
    if not text:
        return []
    sentences = split_sentences(text)
    if not sentences:
        return [text]

    chunks: List[str] = []
    current: List[str] = []
    length = 0
    for sent in sentences:
        if length + len(sent) + 1 > chunk_size and current:
            chunk = " ".join(current).strip()
            chunks.append(chunk)
            # build overlap tail
            tail = chunk[-overlap:] if overlap > 0 else ""
            current = [tail, sent] if tail else [sent]
            length = len(tail) + len(sent)
        else:
            current.append(sent)
            length += len(sent) + 1
    if current:
        chunks.append(" ".join(current).strip())
    return [c for c in chunks if c]


def tokenize(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text or "")]


def keywords(text: str, top_n: int = 12) -> List[str]:
    counts = Counter(
        w for w in tokenize(text) if w not in STOPWORDS and len(w) > 2
    )
    return [w for w, _ in counts.most_common(top_n)]


def keyphrases(texts: List[str], top_n: int = 20) -> List[tuple[str, int]]:
    counter: Counter = Counter()
    for t in texts:
        toks = [w for w in tokenize(t) if w not in STOPWORDS and len(w) > 2]
        counter.update(toks)
        # simple bigrams
        for a, b in zip(toks, toks[1:]):
            counter[f"{a} {b}"] += 1
    return counter.most_common(top_n)
