# Profanity filtering utilities (applied to BOT replies only)
from pathlib import Path
import re

# load profanity list from text file
def load_profanity_list():
    path = Path(__file__).parent / "profanity_list.txt"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

_PROFANITY_WORDS = load_profanity_list()

def _char_class(ch: str) -> str:
    m = {
        'a': ['a', '@', '4'],
        'b': ['b', '8'],
        'e': ['e', '3'],
        'g': ['g', '9'],
        'i': ['i', '1', '!', 'l'],
        'l': ['l', '1', 'i'],
        'o': ['o', '0'],
        's': ['s', '5', '$'],
        't': ['t', '7'],
        'z': ['z', '2'],
    }
    ch = ch.lower()
    if ch.isalpha() or ch.isdigit():
        if ch in m:
            chars = ''.join(sorted(set(m[ch])))
            return f"[{re.escape(chars)}]"
        return f"[{re.escape(ch)}]"
    return re.escape(ch)

def _token_to_pattern(token: str) -> str:
    parts = []
    for c in token:
        if c.isspace():
            parts.append(r"\W{0,3}")
        else:
            parts.append(f"(?:{_char_class(c)}{{1,3}})")
            parts.append(r"\W{0,2}")
    if parts and parts[-1] == r"\W{0,2}":
        parts.pop()
    return ''.join(parts)

def _build_profanity_regex(words: list[str]):
    if not words:
        return None
    patterns = []
    for w in words:
        tokens = w.split()
        if not tokens:
            continue
        token_patterns = [_token_to_pattern(t) for t in tokens]
        phrase_pat = r"\b" + r"\W{0,3}".join(token_patterns) + r"\b"
        patterns.append(phrase_pat)
    if not patterns:
        return None
    try:
        combined = "|".join(patterns)
        return re.compile(combined, re.IGNORECASE)
    except re.error:
        basic = r"|".join([rf"\b{re.escape(w)}\b" for w in words])
        return re.compile(basic, re.IGNORECASE)

_PROFANITY_REGEX = _build_profanity_regex(_PROFANITY_WORDS)

def sanitize_text(text: str) -> str:
    if not _PROFANITY_REGEX:
        return text
    return _PROFANITY_REGEX.sub("****", text or "")