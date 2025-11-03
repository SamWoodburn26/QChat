# Ollama-backed chat via LangChain
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

import azure.functions as func
import json, os, requests
import re
from pathlib import Path

# LangChain LLM configured to call local Ollama
llm = ChatOllama(
    model="mistral:latest",
    base_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
)


prompt_template = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are a helpful assistant for Quinnipiac University. "
            "Assume all user questions are about Quinnipiac University unless the user explicitly specifies otherwise. "
            "For ambiguous queries, interpret them in the Quinnipiac context (events, campuses, services). "
            "If you truly cannot answer with available knowledge, say 'I don't know.' Do not fabricate details."
        ),
    ),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])

# Build a simple LCEL chain: prompt -> model -> string parser
_parser = StrOutputParser()
chain = prompt_template | llm | _parser

def main(req: func.HttpRequest) -> func.HttpResponse:
    msg = (req.params.get("message") or "").strip()
    if not msg:
        try:
            body = req.get_json()
        except ValueError:
            body = {}
        msg = (body.get("message") or "").strip()
    
    if not msg:
        return func.HttpResponse('{"error":"missing message"}', status_code=400, mimetype="application/json")

    # Language filtering: load filtered words from a text file
    def load_profanity_list():
        path = Path(__file__).parent / "profanity_list.txt"
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]

    profanity_words = load_profanity_list()

    # Build a robust regex that handles leetspeak, repeated letters, and punctuation separators
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
        # Escape any non-alnum as literal
        return re.escape(ch)

    def _token_to_pattern(token: str) -> str:
        # For each character, allow 1-3 repeats and optional light separators between letters
        parts = []
        for c in token:
            if c.isspace():
                # Allow small non-alnum separators for spaces between words
                parts.append(r"\W{0,3}")
            else:
                parts.append(f"(?:{_char_class(c)}{{1,3}})" )
                # Optional small separator between letters to catch things like s*p*a*m
                parts.append(r"\W{0,2}")
        # Remove trailing optional separator if present
        if parts and parts[-1] == r"\W{0,2}":
            parts.pop()
        return ''.join(parts)

    def build_profanity_regex(words: list[str]):
        if not words:
            return None
        patterns = []
        for w in words:
            # Normalize multi-word phrases by splitting on whitespace; rebuild with separators allowed
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
            # Fallback to basic word-boundary matching if the advanced pattern fails
            basic = r"|".join([rf"\b{re.escape(w)}\b" for w in words])
            return re.compile(basic, re.IGNORECASE)

    _PROFANITY_REGEX = build_profanity_regex(profanity_words)

    def contains_profanity(text):
        if not _PROFANITY_REGEX:
            return False
        return bool(_PROFANITY_REGEX.search(text or ""))

    def sanitize_text(text):
        if not _PROFANITY_REGEX:
            return text
        return _PROFANITY_REGEX.sub("****", text or "")

    # Do not block or alter user messages. We'll only sanitize the bot's own reply.


    try:
        # We don't have a retrieval context wired here yet; default to empty context and let
        # the system prompt bias the interpretation toward Quinnipiac context.
        reply = chain.invoke({
            "context": "",
            "question": msg,
        }).strip()
        # Only sanitize the bot's reply, not the user's input.
        reply = sanitize_text(reply)
    except Exception as e:
        print("LLM error: ", repr(e))
        reply = "local model is unavailable"

    return func.HttpResponse(json.dumps({"reply": reply}), mimetype="application/json")