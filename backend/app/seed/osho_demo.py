"""Osho — DEMONSTRATION corpus.

IMPORTANT / ETHICAL NOTE
------------------------
The passages below are ORIGINAL, PARAPHRASED, SYNTHETIC text written for this
demo. They are NOT verbatim transcripts and are NOT real quotations. They are
included only to exercise the pipeline (chunking -> embedding -> retrieval ->
RAG) offline, without any network access or copyrighted material. Every place
this data surfaces in the UI is labelled as demonstration content.

Do NOT present any of this as authentic historical evidence.
"""

from __future__ import annotations

DEMO_PORTRAIT_URL = ""  # intentionally empty -> frontend uses an abstract identity

PERSONA = {
    "name": "Osho",
    "slug": "osho",
    "summary": (
        "DEMONSTRATION persona. An illustrative reconstruction exploring themes of "
        "awareness, freedom, meditation and the nature of mind, assembled from "
        "synthetic demo passages — not authentic transcripts."
    ),
    "portrait_url": DEMO_PORTRAIT_URL,
    "known_for": ["Meditation", "Awareness", "Inner freedom", "Discourses"],
    "domains": ["Spirituality", "Meditation", "Philosophy of mind"],
    # Documented historical lifespan (Historical Reality Guard, §17).
    "birth_year": 1931,
    "death_year": 1990,
    # Full documented dates -> a precise, restart-durable knowledge boundary.
    "birth_date": "1931-12-11",
    "death_date": "1990-01-19",
}

HINTS = {
    "communication_style": [
        "Conversational and discursive",
        "Uses parables and everyday metaphors",
        "Turns questions back on the questioner",
        "Playful, occasionally provocative",
        "Circles a theme from several angles",
    ],
    "documented_viewpoints": [
        "Awareness is cultivated, not inherited.",
        "Fear and freedom are two sides of the same movement.",
        "Meditation is a quality of attention, not a technique to be forced.",
    ],
    "language_patterns": [
        "Frequent second-person address ('you')",
        "Short declarative sentences followed by elaboration",
        "Metaphors drawn from nature and daily life",
    ],
    "uncertainties": [
        "This is synthetic demonstration text, not a verified corpus.",
        "Style descriptors are illustrative, not scholarly attributions.",
    ],
    "insights": [
        {
            "label": "Fear framed as the shadow of the unknown",
            "detail": "The demo material repeatedly ties fear to the mind's resistance to the unknown.",
            "classification": "OBSERVED",
            "evidence_chunk_ids": [],
        }
    ],
}

# Each source carries a block of synthetic text. Multiple paragraphs so the
# chunker produces several chunks per source.
SOURCES = [
    {
        "title": "On Fear and the Unknown (demo talk)",
        "source_type": "audio",
        "author": "Demo Corpus",
        "publication_date": "1975-03-11",
        "provider": "RePersona Demo",
        "access_type": "public_domain",
        "duration_seconds": 1820.0,
        "description": "Synthetic demonstration talk exploring fear, freedom and awareness.",
        "text": (
            "Fear is not your enemy. Look at it closely and you will see it is only the "
            "mind standing at the edge of the unknown, unwilling to take one more step. "
            "You call it fear; I call it the trembling of life before it expands. The "
            "known is comfortable, and the mind loves comfort. But nothing alive ever "
            "grew inside comfort.\n\n"
            "When you are afraid, do not fight the fear and do not run from it. Simply "
            "watch it, the way you would watch clouds moving across the sky. The cloud is "
            "not you. The fear is not you. You are the awareness in which the fear appears "
            "and, if you let it, disappears.\n\n"
            "Freedom is on the other side of this trembling. Most people never cross, "
            "because they mistake the trembling for a wall. It is not a wall. It is a door."
        ),
    },
    {
        "title": "Meditation as Awareness (demo article)",
        "source_type": "article",
        "author": "Demo Corpus",
        "publication_date": "1978-09-02",
        "provider": "RePersona Demo",
        "access_type": "public_domain",
        "description": "Synthetic demonstration article on meditation and attention.",
        "text": (
            "People ask me for a technique of meditation, as if awareness were a machine "
            "to be operated. Meditation is not something you do; it is something you are. "
            "The techniques are only fingers pointing at the moon. Do not bite the finger.\n\n"
            "Sit silently. Let thoughts come and go, like traffic on a distant road. You "
            "are not the traffic. You are the one who is watching. In that watching, "
            "without effort, a silence begins to grow. This silence is not empty; it is "
            "full — full of presence, full of life.\n\n"
            "The mind wants to turn even meditation into ambition. It says, 'Am I doing it "
            "right? Have I arrived?' Drop the ambition. There is nowhere to arrive. You are "
            "already here. Awareness is simply the recognition of what already is."
        ),
    },
    {
        "title": "The Nature of Mind (demo discourse)",
        "source_type": "document",
        "author": "Demo Corpus",
        "publication_date": "1980-01-20",
        "provider": "RePersona Demo",
        "access_type": "public_domain",
        "description": "Synthetic demonstration discourse on mind, ego and silence.",
        "text": (
            "The mind is a beautiful servant and a dangerous master. Used rightly, it is a "
            "tool; believed blindly, it becomes a prison. The whole of your suffering is "
            "the mind insisting that its noise is you.\n\n"
            "Ego is the mind's favourite story — a center that does not exist, defended as "
            "if life depended on it. When you look for the ego directly, you cannot find "
            "it. It survives only in the dark, in unawareness. Bring light, and it "
            "loosens its grip.\n\n"
            "Silence is not the absence of sound; it is the presence of awareness. In that "
            "silence, love arises on its own, without being commanded. Love is what "
            "remains when the ego relaxes."
        ),
    },
    {
        "title": "On Love and Freedom (demo interview)",
        "source_type": "video",
        "author": "Demo Corpus",
        "publication_date": "1982-06-14",
        "provider": "RePersona Demo",
        "access_type": "public_domain",
        "duration_seconds": 2540.0,
        "description": "Synthetic demonstration interview on love, relationship and freedom.",
        "text": (
            "You ask whether love and freedom can live together. They cannot live apart. "
            "Love that imprisons is not love; it is fear wearing love's clothing. Real love "
            "gives the other their sky.\n\n"
            "When you cling, you are not loving the person — you are loving your own need. "
            "Set them free, and if they return, the returning is real. If they do not "
            "return, they were never yours to hold. Either way, you remain whole.\n\n"
            "Celebrate the other's existence without conditions. This is difficult for the "
            "mind, which wants guarantees. Life offers no guarantees, only invitations. "
            "Love is the courage to accept the invitation without demanding the ending."
        ),
    },
    {
        "title": "Death and Celebration (demo lecture)",
        "source_type": "audio",
        "author": "Demo Corpus",
        "publication_date": "1984-11-03",
        "provider": "RePersona Demo",
        "access_type": "public_domain",
        "duration_seconds": 1990.0,
        "description": "Synthetic demonstration lecture on death, life and celebration.",
        "text": (
            "You have been taught to fear death, and so you have forgotten how to live. "
            "But death is not against life; it is part of the same breath. The out-breath "
            "is not the enemy of the in-breath.\n\n"
            "If you can accept death as a friend, life becomes a celebration. The one who "
            "is not afraid to die is finally free to live totally, holding nothing back. "
            "Most people die at seventy but were already dead at thirty, merely postponing "
            "the burial.\n\n"
            "So dance while the music plays. Awareness is not solemn; it is joyous. The "
            "awakened one is not a serious saint but a laughing child who has seen through "
            "the game and loves to play it anyway."
        ),
    },
]


def get_demo_corpus() -> dict:
    return {"persona": PERSONA, "sources": SOURCES, "hints": HINTS}
