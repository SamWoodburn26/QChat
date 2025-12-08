import os
# Mitigate OpenMP runtime conflicts (faiss/LLVM vs Intel MKL)
# Must be set BEFORE importing libraries that may initialize OpenMP
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")   # allow duplicate OpenMP runtimes (unsafe but pragmatic)
os.environ.setdefault("OMP_NUM_THREADS", "1")            # keep threads low in constrained envs
os.environ.setdefault("MKL_THREADING_LAYER", "SEQUENTIAL")
 
# ollama to make the gemma model
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate

import azure.functions as func
import json, os

from .RAG import store_from_txt

import azure.functions as func
import json, os
from datetime import datetime
from pymongo import MongoClient
import certifi
import requests

# Ollama-backed chat via LangChain
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import re
from pathlib import Path

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGODB_URI') or os.getenv('MONGODB_URI')
DATABASE_NAME = os.environ.get('DB_NAME', 'qchat')
CHAT_LOGS_COLLECTION = 'chatLogs'
# Allow turning off DB logging entirely via env
QCHAT_LOG_CHATS = (os.getenv('QCHAT_LOG_CHATS', 'true').lower() == 'true')
# greetings to aviod rag answering
GREETINGS_LIST = re.compile(r"\b(hi|hello|hey|hii|sup|what'?s up)\b", re.IGNORECASE)

# MongoDB client (global)
mongo_client = None
db = None
# One-time DB check flags
_db_checked = False
_db_ready = False
_db_error = None

def _init_db_once():
    """Attempt to initialize Mongo only once per process.
    Sets _db_ready/_db_checked accordingly and avoids repeated slow failures.
    """
    global mongo_client, db, _db_checked, _db_ready, _db_error
    if _db_checked:
        return
    _db_checked = True
    _db_ready = False
    _db_error = None
    if not (QCHAT_LOG_CHATS and MONGO_URI):
        return
    try:
        mongo_kwargs = {
            "serverSelectionTimeoutMS": 3000,
            "connectTimeoutMS": 3000,
            "socketTimeoutMS": 3000,
        }
        if MONGO_URI.startswith("mongodb+srv") or "mongodb.net" in MONGO_URI:
            # Atlas requires TLS
            mongo_kwargs["tls"] = True
            mongo_kwargs["tlsCAFile"] = certifi.where()
        mc = MongoClient(MONGO_URI, **mongo_kwargs)
        # Ping to verify connectivity
        mc.admin.command("ping")
        mongo_client = mc
        db = mongo_client[DATABASE_NAME]
        _db_ready = True
    except Exception as e:
        print("Mongo one-time init failed:", repr(e))
        mongo_client = None
        db = None
        _db_ready = False
        _db_error = repr(e)


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "256"))

def _preload_model():
    try:
        # Preload and keep the model warm to reduce first-token latency
        requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": OLLAMA_MODEL, "messages": [], "keep_alive": -1},
            timeout=2,
        )
    except Exception:
        pass

_preload_model()

# LangChain LLM configured to call local Ollama (tuned for speed)
llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_URL,
    temperature=0.2,
    num_ctx=_NUM_CTX,
    model_kwargs={"num_predict": _NUM_PREDICT},
)

# for ollama llm model and embeddings
#llm = ChatOllama(model="mistral:latest", base_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
embeddings = OllamaEmbeddings(model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"));

# prompt to only use given context
prompt_template = ChatPromptTemplate.from_messages([
    ("system",
     "You are QChat, a helpful assistant for Quinnipiac University.\n"
     "Your job is to answer using ONLY the provided context.\n\n"
     "RULES:\n"
     "- If the answer is in the context → answer clearly and concisely.\n"
     "- If the question is a greeting (hi, hello, hey, etc.) → respond friendly and invite a real question.\n"
     "- If the answer is NOT in the context and NOT a greeting → say: 'I don't know. Try asking about dining, housing, athletics, or MyQ.'\n"
     "- NEVER make up information.\n"
     "- ALWAYS be helpful and positive.\n"),
    ("human", "Context:\n{context}\n\nUser: {question}")
])

_vector_store = None

# get vector store using RAG.py function and qu_docs txt files
def get_vector_store():
    global _vector_store
    if _vector_store is None:
        print("⚙️ Loading RAG vector store (first time)...")
        from .RAG import store_from_txt  
        _vector_store = store_from_txt("qu_docs.txt")
        print("RAG vector store loaded.")
    return _vector_store



# Build a simple LCEL chain: prompt -> model -> string parser
_parser = StrOutputParser()
chain = prompt_template | llm | _parser

# Profanity filtering utilities (applied to BOT replies only)
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

# New FAQ Functions

def search_faq(query):
    """Search FAQ database"""
    _init_db_once()
    if not _db_ready:
        return []
    
    try:
        all_faqs = list(db['universityInfo'].find())
        if not all_faqs:
            print("No FAQs in database")
            return []
        
        print(f"Found {len(all_faqs)} FAQs in database")
        
        query_lower = query.lower().strip()
        scored_faqs = []
        
        for faq in all_faqs:
            question = faq.get('question', '').lower()
            
            # Simple exact match check
            if query_lower == question:
                score = 1000
                scored_faqs.append((score, faq))
                print(f" EXACT MATCH: {faq.get('question')} → Score: {score}")
                break  # Found exact match, stop searching
            
            # Partial match
            if query_lower in question or question in query_lower:
                score = 500
                scored_faqs.append((score, faq))
                print(f" Partial match: {faq.get('question')[:50]}... → Score: {score}")
        
        if not scored_faqs:
            print(" No matches found")
            return []
        
        scored_faqs.sort(reverse=True, key=lambda x: x[0])
        best_score, best_faq = scored_faqs[0]
        
        print(f" Best match: {best_faq.get('question')} (Score: {best_score})")
        
        return [{'score': best_score, 'faq': best_faq}]
        
    except Exception as e:
        print(f" FAQ search error: {e}")
        import traceback
        traceback.print_exc()
        return []


# answer using rag
def answer_with_rag(question:str) -> dict:
     # manage answering hi
    if GREETINGS_LIST.search(question.strip()):
        return{
            "reply": "Hi! I'm QChat.  Ask me anything about Quinnipiac University!",
            "sources": []
        }
    # New try FAQ search first 
    print(f"🔍 Searching FAQ for: {question}")
    faq_results = search_faq(question)
    
    if faq_results and faq_results[0]['score'] >= 100:
        faq = faq_results[0]['faq']
        print(f"FAQ FOUND (score: {faq_results[0]['score']})")
        return {
            "reply": faq.get('answer', ''),
            "sources": [f"FAQ: {faq.get('question')}"]
        }
    
    print(" Using RAG...")
    vector_store = get_vector_store()
    docs = vector_store.similarity_search(question, k=4)
    ctx = "\n\n".join(d.page_content for d in docs)
    reply = llm.invoke(prompt_template.invoke({"context": ctx, "question": question})).content.strip()
    sources = [d.metadata.get("source") for d in docs if d.metadata.get("source")]
    print(f"Retrieved {len(docs)} docs from {len(sources)} sources")
    reply = sanitize_text(reply)
    return {"reply": reply, "sources": sources}

def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        response = func.HttpResponse("")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    print("=" * 50)
    print("main called")
    try:
        body = req.get_json()
    except ValueError:
        body = {}

    
    # Backward-compatible parameter parsing (supports body and querystring)
    action = body.get("action") or req.params.get("action") or "chat"
    user_id = body.get("userId") or req.params.get("userId") or "anonymous"
    msg = ""
    
    # For now, treat any action as 'chat' (backward compatibility)
    if action == "health":
        # Return health diagnostics for DB connectivity and model config
        _init_db_once()
        info = {
            "dbReady": _db_ready,
            "dbName": DATABASE_NAME,
            "loggingEnabled": QCHAT_LOG_CHATS,
            "hasMongoUri": bool(MONGO_URI),
            "error": _db_error,
        }
        return func.HttpResponse(json.dumps(info), mimetype="application/json")
    elif action == "chat":
        msg = (body.get("message") or req.params.get("message") or "").strip()
    else:
        # Fall back to chat if unknown action provided
        msg = (body.get("message") or req.params.get("message") or "").strip()
    
    if not msg:
        return func.HttpResponse('{"error":"missing message"}', status_code=400, mimetype="application/json")

    try:
        # Invoke via LCEL chain; no external context wired yet.
        rag_result = answer_with_rag(msg)
        reply_text = rag_result["reply"]
        sources = rag_result["sources"]

        reply  = {"reply": reply_text, "sources": sources}
    except Exception as e:
        print("RAG error: ", repr(e))
        reply = {"reply": "I don't know.", "sources":[]}

    response = func.HttpResponse(
        json.dumps(reply),
        mimetype="application/json"
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    # One-time DB connectivity check and optional logging
    _init_db_once()
    if _db_ready and db is not None:
        try:
            db[CHAT_LOGS_COLLECTION].insert_one({
                "userId": user_id,
                "action": action,
                "message": msg,
                "reply": reply,
                "ts": datetime.utcnow(),
            })
        except Exception as e:
            # Do not attempt to re-initialize; skip logging silently after first failure
            print("Mongo insert error:", repr(e))

    return response