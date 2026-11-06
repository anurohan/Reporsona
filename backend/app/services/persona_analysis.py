"""Persona Analysis Engine.

Derives a structured profile, topics, insights and a knowledge graph from the
persona's processed chunks. Everything that can be computed from the text is
computed (concepts, themes, co-occurrence graph, source coverage). Curated
hints (communication style / documented viewpoints) may be supplied by the
source adapter — these are stored verbatim and classified honestly.

Insights are classified as DOCUMENTED | OBSERVED | INFERRED | UNKNOWN and each
important one is linked to the evidence chunks that support it.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Chunk,
    KnowledgeEdge,
    KnowledgeNode,
    Persona,
    PersonaInsight,
    PersonaProfile,
    Source,
    Topic,
)
from app.services import nlp


def analyze(db: Session, persona: Persona, hints: Optional[dict] = None) -> None:
    """Populate topics, profile, insights and knowledge graph for the persona.

    Idempotent: clears any previously-derived analysis for the persona first.
    """
    hints = hints or {}
    chunks = list(db.scalars(select(Chunk).where(Chunk.persona_id == persona.id)))
    sources = list(db.scalars(select(Source).where(Source.persona_id == persona.id)))
    texts = [c.text for c in chunks]

    # --- clear prior derived rows ------------------------------------- #
    for model in (Topic, PersonaInsight, KnowledgeNode, KnowledgeEdge):
        for row in db.scalars(select(model).where(model.persona_id == persona.id)):
            db.delete(row)
    if persona.profile:
        db.delete(persona.profile)
    db.flush()

    # --- concepts / topics -------------------------------------------- #
    phrases = nlp.keyphrases(texts, top_n=24)
    # Prefer multi-word phrases and longer words as "concepts".
    concept_scores = [(p, c) for p, c in phrases if len(p) > 3]
    top_concepts = [p for p, _ in concept_scores[:12]]

    max_count = max((c for _, c in concept_scores), default=1)
    topic_rows: list[Topic] = []
    for label, count in concept_scores[:8]:
        t = Topic(
            persona_id=persona.id,
            label=label.title(),
            description=f"A recurring subject across {persona.name}'s processed material.",
            weight=round(count / max_count, 3),
            keywords=[label],
        )
        db.add(t)
        topic_rows.append(t)

    # --- knowledge graph (co-occurrence) ------------------------------ #
    node_ids: dict[str, str] = {}
    for label, count in concept_scores[:14]:
        node = KnowledgeNode(
            persona_id=persona.id,
            label=label.title(),
            description="Concept extracted from the processed corpus.",
            weight=round(count / max_count, 3),
            group="concept",
        )
        db.add(node)
        db.flush()
        node_ids[label] = node.id

    pair_weights: Counter = Counter()
    concept_set = set(node_ids)
    for text in texts:
        present = [c for c in concept_set if c in text.lower()]
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                a, b = sorted((present[i], present[j]))
                pair_weights[(a, b)] += 1
    for (a, b), w in pair_weights.most_common(24):
        db.add(
            KnowledgeEdge(
                persona_id=persona.id,
                source_node_id=node_ids[a],
                target_node_id=node_ids[b],
                relation="related",
                weight=float(w),
            )
        )

    # --- source coverage ---------------------------------------------- #
    coverage = defaultdict(int)
    for s in sources:
        coverage[s.source_type] += 1
    source_coverage = {
        "total_sources": len(sources),
        "total_chunks": len(chunks),
        "by_type": dict(coverage),
    }

    # --- profile ------------------------------------------------------- #
    profile = PersonaProfile(
        persona_id=persona.id,
        communication_style=hints.get("communication_style", []),
        recurring_themes=[t.label for t in topic_rows],
        documented_viewpoints=hints.get("documented_viewpoints", []),
        frequent_concepts=[c.title() for c in top_concepts],
        language_patterns=hints.get("language_patterns", []),
        source_coverage=source_coverage,
        uncertainties=hints.get(
            "uncertainties",
            [
                "Coverage is limited to the sources processed so far.",
                "Communication-style descriptors are observed patterns, not clinical assessments.",
            ],
        ),
    )
    db.add(profile)

    # --- insights (linked to evidence) -------------------------------- #
    # DOCUMENTED: a recurring theme backed by the chunks that mention it.
    for label in top_concepts[:4]:
        supporting = [c.id for c in chunks if label in c.text.lower()][:5]
        classification = "DOCUMENTED" if len(supporting) >= 3 else "OBSERVED"
        db.add(
            PersonaInsight(
                persona_id=persona.id,
                label=f"Recurring focus on “{label}”",
                detail=(
                    f"“{label}” appears repeatedly across the processed material, "
                    f"suggesting it is a central concern in the documented record."
                ),
                classification=classification,
                evidence_chunk_ids=supporting,
            )
        )
    for extra in hints.get("insights", []):
        db.add(
            PersonaInsight(
                persona_id=persona.id,
                label=extra.get("label", ""),
                detail=extra.get("detail", ""),
                classification=extra.get("classification", "OBSERVED"),
                evidence_chunk_ids=extra.get("evidence_chunk_ids", []),
            )
        )

    db.flush()
