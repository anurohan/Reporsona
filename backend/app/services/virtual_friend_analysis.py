"""Virtual Friend Analysis — extract a structured personality profile from chat transcripts.

Builds on persona_analysis.analyze() patterns but adapted for private chat data.
Extracts communication style, personality traits, preferences, language patterns,
and uncertainties from the uploaded messages of the target speaker.

Each insight is classified as:
  DOCUMENTED  — explicitly stated in a message
  OBSERVED    — a pattern seen across multiple messages
  INFERRED    — derived by the analysis engine (should be clearly labelled)
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Chunk,
    PersonaInsight,
    PersonaProfile,
    Source,
)
from app.services import nlp
from app.services.transcript_parser import ParsedMessage


# ---------------------------------------------------------------------------
# Emoji & language-pattern helpers
# ---------------------------------------------------------------------------

_EMOJI_RX = re.compile(
    "[\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251]+",
    flags=re.UNICODE,
)

_GREETING_RX = re.compile(r"\b(hi|hello|hey|hiya|sup|howdy|namaste|hola|yo)\b", re.I)
_POSITIVE_RX = re.compile(r"\b(love|like|enjoy|amazing|awesome|great|good|wonderful|fantastic|beautiful|nice|perfect|happy)\b", re.I)
_NEGATIVE_RX = re.compile(r"\b(hate|dislike|terrible|awful|bad|horrible|ugly|annoying|boring|stupid|worst|never)\b", re.I)
_QUESTION_RX = re.compile(r"\?")
_EXCLAIM_RX = re.compile(r"!")
_LOL_RX = re.compile(r"\b(lol|lmao|haha|hehe|😂|🤣)\b", re.I)


def _emoji_count(text: str) -> int:
    return sum(len(m.group()) for m in _EMOJI_RX.finditer(text))


def _has_emoji(text: str) -> bool:
    return bool(_EMOJI_RX.search(text))


# ---------------------------------------------------------------------------
# Communication-style extraction
# ---------------------------------------------------------------------------

def _extract_communication_style(messages: list[ParsedMessage]) -> list[str]:
    if not messages:
        return []

    total = len(messages)
    lengths = [len(m.text.split()) for m in messages]
    avg_words = sum(lengths) / total if total else 0

    emoji_msgs = sum(1 for m in messages if _has_emoji(m.text))
    lol_msgs = sum(1 for m in messages if _LOL_RX.search(m.text))
    question_msgs = sum(1 for m in messages if _QUESTION_RX.search(m.text))
    exclaim_msgs = sum(1 for m in messages if _EXCLAIM_RX.search(m.text))

    styles: list[str] = []

    # Message length
    if avg_words < 5:
        styles.append("OBSERVED: Sends very short, punchy messages (avg ~{:.0f} words)".format(avg_words))
    elif avg_words < 15:
        styles.append("OBSERVED: Prefers concise messages (avg ~{:.0f} words)".format(avg_words))
    else:
        styles.append("OBSERVED: Tends to write longer, more detailed messages (avg ~{:.0f} words)".format(avg_words))

    # Emoji use
    emoji_pct = emoji_msgs / total * 100
    if emoji_pct > 60:
        styles.append("OBSERVED: Heavy emoji user ({:.0f}% of messages contain emojis)".format(emoji_pct))
    elif emoji_pct > 20:
        styles.append("OBSERVED: Moderate emoji use ({:.0f}% of messages)".format(emoji_pct))
    else:
        styles.append("OBSERVED: Minimal emoji use")

    # Humor markers
    if lol_msgs / total > 0.15:
        styles.append("OBSERVED: Frequently uses humor markers (lol, haha, etc.)")

    # Question frequency
    if question_msgs / total > 0.3:
        styles.append("OBSERVED: Asks lots of questions — engaged and curious conversational style")

    # Exclamation use
    if exclaim_msgs / total > 0.4:
        styles.append("OBSERVED: Enthusiastic tone — frequent use of exclamation marks")

    return styles


# ---------------------------------------------------------------------------
# Personality traits
# ---------------------------------------------------------------------------

def _extract_personality_traits(messages: list[ParsedMessage]) -> list[str]:
    traits: list[str] = []
    total = len(messages)
    if not total:
        return traits

    positive_msgs = sum(1 for m in messages if _POSITIVE_RX.search(m.text))
    negative_msgs = sum(1 for m in messages if _NEGATIVE_RX.search(m.text))

    if positive_msgs / total > 0.25:
        traits.append("OBSERVED: Generally positive and optimistic in expressions")
    if negative_msgs / total > 0.2:
        traits.append("OBSERVED: Expresses criticisms or dislikes openly")

    # Sharing/helping signals
    help_rx = re.compile(r"\b(help|sure|of course|happy to|let me|i can|no problem)\b", re.I)
    help_msgs = sum(1 for m in messages if help_rx.search(m.text))
    if help_msgs / total > 0.1:
        traits.append("OBSERVED: Helpful and supportive — frequently offers assistance")

    # Storytelling
    story_rx = re.compile(r"\b(so|then|and then|after that|so like|anyway)\b", re.I)
    story_msgs = sum(1 for m in messages if story_rx.search(m.text))
    if story_msgs / total > 0.3:
        traits.append("OBSERVED: Conversational storyteller — frequently narrates events")

    return traits


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

def _extract_preferences(messages: list[ParsedMessage]) -> list[str]:
    """Extract things the person talks positively about."""
    preferences: list[str] = []
    all_text = " ".join(m.text for m in messages)
    words = nlp.keywords(all_text, top_n=30)

    # Find words that frequently appear alongside positive language
    positive_context: Counter = Counter()
    for m in messages:
        if _POSITIVE_RX.search(m.text):
            for w in nlp.tokenize(m.text):
                if w not in nlp.STOPWORDS and len(w) > 3:
                    positive_context[w] += 1

    for word, count in positive_context.most_common(5):
        if count >= 2:
            preferences.append(f"OBSERVED: Shows positive sentiment around '{word}' (mentioned {count}x in positive context)")

    return preferences


# ---------------------------------------------------------------------------
# Values & beliefs
# ---------------------------------------------------------------------------

def _extract_values(messages: list[ParsedMessage]) -> list[str]:
    values: list[str] = []
    value_patterns = [
        (re.compile(r"\b(family|friends|relationships|people|loved ones)\b", re.I), "Values relationships and people"),
        (re.compile(r"\b(work|career|job|professional|success|achieve)\b", re.I), "Career and achievement oriented"),
        (re.compile(r"\b(travel|adventure|explore|experience|journey)\b", re.I), "Values experiences and exploration"),
        (re.compile(r"\b(honest|truth|fair|right|wrong|ethical|moral)\b", re.I), "Expresses clear ethical standards"),
        (re.compile(r"\b(health|fitness|exercise|wellbeing|mental health)\b", re.I), "Health and wellbeing conscious"),
        (re.compile(r"\b(learn|knowledge|read|understand|curious|education)\b", re.I), "Values learning and knowledge"),
    ]

    for rx, label in value_patterns:
        count = sum(1 for m in messages if rx.search(m.text))
        if count >= 2:
            values.append(f"OBSERVED: {label} ({count} mentions)")

    return values


# ---------------------------------------------------------------------------
# Frequent topics
# ---------------------------------------------------------------------------

def _extract_frequent_topics(messages: list[ParsedMessage]) -> list[str]:
    all_text = " ".join(m.text for m in messages)
    phrases = nlp.keyphrases([m.text for m in messages], top_n=20)
    topics = []
    for phrase, count in phrases[:8]:
        if len(phrase) > 3 and count >= 2:
            topics.append(f"OBSERVED: Frequent topic: '{phrase.title()}' ({count} occurrences)")
    return topics


# ---------------------------------------------------------------------------
# Language patterns
# ---------------------------------------------------------------------------

def _extract_language_patterns(messages: list[ParsedMessage]) -> list[str]:
    patterns: list[str] = []

    # Common openers
    openers: Counter = Counter()
    for m in messages:
        words = m.text.strip().split()
        if words:
            openers[words[0].lower().rstrip("!?,.")] += 1

    for word, count in openers.most_common(3):
        if count >= 3 and len(word) > 1:
            patterns.append(f"OBSERVED: Frequently starts messages with '{word}' ({count}x)")

    # Catch-phrases: single words used very frequently
    all_words: Counter = Counter()
    for m in messages:
        for w in nlp.tokenize(m.text):
            if w not in nlp.STOPWORDS and len(w) > 3:
                all_words[w] += 1

    for word, count in all_words.most_common(5):
        if count >= 5:
            patterns.append(f"OBSERVED: Characteristic word '{word}' used {count}x")

    # Greeting style
    greeting_msgs = sum(1 for m in messages if _GREETING_RX.match(m.text.strip()))
    if greeting_msgs >= 2:
        patterns.append(f"OBSERVED: Uses informal greetings frequently ({greeting_msgs} greeting messages)")

    return patterns


# ---------------------------------------------------------------------------
# Uncertainties
# ---------------------------------------------------------------------------

def _build_uncertainties(messages: list[ParsedMessage], target_speaker: str) -> list[str]:
    total = len(messages)
    return [
        f"Coverage limited to {total} messages from {target_speaker} in uploaded transcripts.",
        "Communication style descriptors are observed patterns from chat context, not formal assessments.",
        "Personality traits are inferred from text patterns only — private beliefs or values may differ.",
        "Preferences and dislikes reflect chat discussion topics, not comprehensive life preferences.",
        "The simulation cannot reflect recent changes in the person's views or circumstances.",
    ]


# ---------------------------------------------------------------------------
# Main analysis entrypoint
# ---------------------------------------------------------------------------

def extract_profile(
    db: Session,
    persona_id: str,
    messages: list[ParsedMessage],
    target_speaker: str,
    *,
    hints: Optional[dict] = None,
) -> dict:
    """Extract a structured personality profile from parsed chat messages.

    Runs analysis on the target speaker's messages and stores PersonaInsights
    with appropriate DOCUMENTED/OBSERVED/INFERRED classifications.

    Returns a dict matching the PersonaProfile schema.
    """
    hints = hints or {}

    # Filter to target speaker
    speaker_msgs = [m for m in messages if m.sender.lower() == target_speaker.lower()]
    if not speaker_msgs:
        speaker_msgs = messages  # fallback: analyse all

    communication_style = _extract_communication_style(speaker_msgs)
    personality_traits = _extract_personality_traits(speaker_msgs)
    preferences = _extract_preferences(speaker_msgs)
    values_beliefs = _extract_values(speaker_msgs)
    frequent_topics = _extract_frequent_topics(speaker_msgs)
    language_patterns = _extract_language_patterns(speaker_msgs)
    uncertainties = _build_uncertainties(speaker_msgs, target_speaker)

    # Source coverage stats
    chunks = db.query(Chunk).filter(Chunk.persona_id == persona_id).all()
    sources = db.query(Source).filter(Source.persona_id == persona_id).all()
    source_coverage = {
        "total_sources": len(sources),
        "total_chunks": len(chunks),
        "total_messages_analyzed": len(speaker_msgs),
        "by_type": {"chat_transcript": len([s for s in sources if s.source_type == "chat_transcript"])},
    }

    # Build/update profile data dict
    profile_data = {
        "communication_style": hints.get("communication_style", []) + communication_style,
        "recurring_themes": frequent_topics,
        "documented_viewpoints": values_beliefs,
        "frequent_concepts": language_patterns,
        "language_patterns": language_patterns,
        "source_coverage": source_coverage,
        "uncertainties": uncertainties,
    }

    # Store insights in the database
    _store_insights(
        db=db,
        persona_id=persona_id,
        speaker_msgs=speaker_msgs,
        target_speaker=target_speaker,
        communication_style=communication_style,
        personality_traits=personality_traits,
        preferences=preferences,
        values_beliefs=values_beliefs,
        frequent_topics=frequent_topics,
        language_patterns=language_patterns,
    )

    # Personality summary dict (stored on VirtualFriend.personality)
    personality_summary = {
        "communication_style": communication_style,
        "personality_traits": personality_traits,
        "preferences": preferences,
        "values_beliefs": values_beliefs,
        "frequent_topics": frequent_topics,
        "language_patterns": language_patterns,
        "uncertainties": uncertainties,
        "message_count": len(speaker_msgs),
        "target_speaker": target_speaker,
    }

    return profile_data, personality_summary


def _store_insights(
    *,
    db: Session,
    persona_id: str,
    speaker_msgs: list[ParsedMessage],
    target_speaker: str,
    communication_style: list[str],
    personality_traits: list[str],
    preferences: list[str],
    values_beliefs: list[str],
    frequent_topics: list[str],
    language_patterns: list[str],
) -> None:
    """Write PersonaInsights for a virtual friend persona, with correct classification."""

    chunks = db.query(Chunk).filter(Chunk.persona_id == persona_id).all()
    chunk_ids = [c.id for c in chunks]

    def _add(label: str, detail: str, classification: str, evidence_ids: list[str] | None = None):
        db.add(PersonaInsight(
            persona_id=persona_id,
            label=label,
            detail=detail,
            classification=classification,
            evidence_chunk_ids=evidence_ids or [],
        ))

    # Communication style insights → OBSERVED
    for style in communication_style[:3]:
        _add(
            label=style,
            detail=f"Derived from analysis of {target_speaker}'s message patterns.",
            classification="OBSERVED",
            evidence_ids=chunk_ids[:5],
        )

    # Personality traits → OBSERVED
    for trait in personality_traits[:3]:
        _add(
            label=trait,
            detail=f"Pattern observed across {target_speaker}'s uploaded conversations.",
            classification="OBSERVED",
            evidence_ids=chunk_ids[:5],
        )

    # Values → OBSERVED or DOCUMENTED (depending on frequency)
    for val in values_beliefs[:3]:
        classification = "DOCUMENTED" if val.startswith("OBSERVED:") and "mentions" in val else "OBSERVED"
        _add(label=val, detail=f"Value/belief identified in {target_speaker}'s messages.", classification=classification)

    # Topics → DOCUMENTED (they explicitly appear in messages)
    for topic in frequent_topics[:3]:
        _add(label=topic, detail="Topic frequently discussed in uploaded chats.", classification="DOCUMENTED", evidence_ids=chunk_ids[:8])

    # Language patterns → OBSERVED
    for lp in language_patterns[:3]:
        _add(label=lp, detail=f"Language pattern observed in {target_speaker}'s messages.", classification="OBSERVED")
