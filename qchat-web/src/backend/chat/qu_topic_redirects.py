"""
Topic-based Quinnipiac redirects when the bot cannot answer from FAQ/RAG context.
First matching rule wins; order matters (put more specific keyword groups first).
"""

import re
from typing import Any, Dict, List, Optional

# (keyword_substrings, reply, sources) — keywords normalized to lowercase word checks
_TOPIC_RULES: List[tuple] = [
    (
        ("cake", "cakes", "baking", "bake", "cooking", "cook", "recipe", "recipes", "culinary", "chef"),
        (
            "I do not have that specific detail in my Quinnipiac resources. "
            "For cooking-related opportunities on campus and through QU, browse the links below."
        ),
        [
            "https://lifelonglearning.qu.edu/",
            "https://www.qu.edu/student-life/dining/special-events/",
            "https://www.qu.edu/student-life/athletics-and-recreation/fitness-and-recreation/",
        ],
    ),
    (
        (
            "sport",
            "sports",
            "athletic",
            "athletics",
            "bobcat",
            "bobcats",
            "game",
            "games",
            "ncaa",
            "lacrosse",
            "hockey",
            "basketball",
            "soccer",
            "baseball",
            "softball",
            "volleyball",
            "tennis",
            "field hockey",
            "gobobcats",
        ),
        (
            "I do not have that answer in my indexed resources. "
            "For Quinnipiac athletics schedules and news, use the official athletics sites below."
        ),
        [
            "https://www.qu.edu/student-life/athletics-and-recreation/division-I-athletics/",
            "https://gobobcats.com/",
        ],
    ),
    (
        ("intramural", "intramurals"),
        (
            "I do not have that detail in my resources. "
            "Quinnipiac intramural sports are run through Recreation—see the link below."
        ),
        ["https://www.qu.edu/student-life/athletics-and-recreation/intramural-sports/"],
    ),
    (
        ("club sport", "club sports"),
        (
            "I do not have that detail in my resources. "
            "For club sports at QU, start with the club sports page below."
        ),
        ["https://www.qu.edu/student-life/athletics-and-recreation/club-sports/"],
    ),
    (
        ("music", "concert", "band", "choir", "theater", "theatre", "drama", "performance"),
        (
            "I do not have that in my current resources. "
            "For campus arts and performances, check the main events calendar and student life."
        ),
        [
            "https://www.qu.edu/events-calendar/",
            "https://www.qu.edu/student-life/events-activities-and-traditions/",
        ],
    ),
    (
        ("career", "internship", "internships", "job fair", "resume"),
        (
            "I do not have that specific answer in my resources. "
            "For careers and professional development, explore Quinnipiac's career resources."
        ),
        ["https://careers.qu.edu/"],
    ),
    (
        ("library", "libraries", "study room", "arnold bernhard"),
        (
            "I do not have that detail in my resources. "
            "For library hours, spaces, and research help, visit the libraries site."
        ),
        ["https://www.qu.edu/academics/university-library/"],
    ),
    (
        ("health", "wellness", "counseling", "counselling", "medical", "clinic"),
        (
            "I do not have that answer in my resources. "
            "For student health and counseling, see Student Health and Wellness."
        ),
        ["https://www.qu.edu/student-life/health-and-wellness/"],
    ),
]


_IDK_PATTERNS = [
    re.compile(r"i\s+don'?t\s+know", re.I),
    re.compile(r"not\s+in\s+the\s+(context|provided)", re.I),
    re.compile(r"cannot\s+find\s+(that|this|an?\s+answer)", re.I),
    re.compile(r"no\s+information\s+(in|about|on)\s+the\s+context", re.I),
    re.compile(r"is\s+not\s+in\s+the\s+context", re.I),
]


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def get_topic_redirect(question: str) -> Optional[Dict[str, Any]]:
    """
    If the question matches a topic rule, return reply + sources for a QU-specific redirect.
    Otherwise return None.
    """
    q = _normalize(question)
    if not q:
        return None

    for keywords, reply, sources in _TOPIC_RULES:
        for kw in keywords:
            if kw in q:
                return {"reply": reply, "sources": list(sources)}
    return None


def looks_like_idk_reply(text: str) -> bool:
    """True if the model reply is a generic 'cannot answer from context' style answer."""
    if not text or not text.strip():
        return True
    t = text.strip()
    for pat in _IDK_PATTERNS:
        if pat.search(t):
            return True
    # Short refusal without substance
    if len(t) < 160 and "context" in t.lower() and "don't" in t.lower():
        return True
    return False
