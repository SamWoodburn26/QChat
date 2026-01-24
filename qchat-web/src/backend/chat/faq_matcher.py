# Checks the incoming message against static FAQ data using keyword matching.
import re
from .faq_data import FAQ_DATA


# scoring weights
CORE_WEIGHT = 3              # Core keywords (required, heavily weighted)
CONTEXT_WEIGHT = 2           # Context keywords (distinguishing)
OPTIONAL_WEIGHT = 1          # Optional keywords (bonus points)

STRONG_CONTEXT_BONUS = 2     # Bonus points for strong context match
STRONG_CONTEXT_COUNT = 2     # Number of context matches needed for bonus

# Minimum score: at least 1 core + 1 context (more robust)
MINIMUM_SCORE_THRESHOLD = 6
#CORE_WEIGHT + CONTEXT_WEIGHT  # = 5


def keyword_in_msg(keyword: str, message: str) -> bool:
    # Prevents partial matches (e.g., "aid" won't match "paid")
    # Use word boundaries (\b) to match whole words only
    pattern = rf"\b{re.escape(keyword)}\b"
    return re.search(pattern, message) is not None


def check_faq_by_keywords(message: str):
    
    ## Weighted keyword matching: core(3pts) + context(2pts) + optional(1pt), min threshold 6
    if not message:
        return None

    msg = message.lower()
    
    best_faq = None
    best_score = 0
    best_core_matches = 0  # For tie-breaking

    # Iterate through all FAQs to find the best match
    for faq in FAQ_DATA:
        score = 0
        context_match_count = 0
        core_matches = 0

        # Check core keywords with word boundaries
        for kw in faq.get("core", []):
            kw = kw.lower().strip()
            if kw and keyword_in_msg(kw, msg):
                core_matches += 1
                score += CORE_WEIGHT

        # If no core keyword matches, skip this FAQ entirely
        if core_matches == 0:
            continue

        # Check context keywords with word boundaries
        for kw in faq.get("context", []):
            kw = kw.lower().strip()
            if kw and keyword_in_msg(kw, msg):
                context_match_count += 1
                score += CONTEXT_WEIGHT

        # Apply bonus for strong context match (2+ context keywords)
        if context_match_count >= STRONG_CONTEXT_COUNT:
            score += STRONG_CONTEXT_BONUS

        
        # Check optional keywords with word boundaries
        for kw in faq.get("optional", []):
            kw = kw.lower().strip()
            if kw and keyword_in_msg(kw, msg):
                score += OPTIONAL_WEIGHT

        # Update best match logic
        # Primary: highest score
        # Tie-breaker: most core matches
        if score >= MINIMUM_SCORE_THRESHOLD and (
            score > best_score or
            (score == best_score and core_matches > best_core_matches)
        ):
            best_score = score
            best_faq = faq
            best_core_matches = core_matches

    # No suitable match found
    if best_faq is None:
        return None

    # Return the best matching FAQ
    return {
        "reply": best_faq.get("answer"),
        "sources": [],
        "source": "faq",
        "category": best_faq.get("category"),
        "question": best_faq.get("question"),
        "faqScore": best_score,
    }