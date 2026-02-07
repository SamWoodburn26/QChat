# for rag and filter
import re
from .RAG import build_index, retrieve
from .profanity_filter import sanitize_text
# for llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
# FAQ matcher import
from .faq_matcher import check_faq_by_keywords
# other imports
import azure.functions as func
import json, os
from datetime import datetime
from pymongo import MongoClient
import certifi

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGODB_URI') or os.getenv('MONGODB_URI')
DATABASE_NAME = os.environ.get('DB_NAME', 'qchat')
CHAT_LOGS_COLLECTION = 'chatLogs'
# Allow turning off DB logging entirely via env
QCHAT_LOG_CHATS = (os.getenv('QCHAT_LOG_CHATS', 'true').lower() == 'true')

# greetings to aviod rag answering
GREETINGS_LIST = re.compile(r"\b(hi|hello|hey|hii|sup|what'?s up)\b", re.IGNORECASE)


#Enable FAQ priority: check FAQs before calling RAG
QCHAT_FAQ_FIRST = (os.getenv('QCHAT_FAQ_FIRST', 'true').lower() == 'true')

# MongoDB client (global)
mongo_client = None
db = None
# One-time DB check flags
_db_checked = False
_db_ready = False
_db_error = None

# intialize llm model
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "256"))
llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_URL,
    temperature=0,
    num_ctx=_NUM_CTX,
    model_kwargs={"num_predict": _NUM_PREDICT},
)

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
     "- ALWAYS be helpful and positive.\n"
     "- NEVER make up or modify the links given, provide the exact link without any adjustments.\n"
     "- assume the student is an undergraduate living on Mount Carmel, unless otherwise told. \n"
     "Formatting rules:\n"
     "- Use short paragraphs\n"
     "- Use bullet points for lists\n"
     "- Use headings when appropriate\n"
     "- Do NOT return one long block of text\n"
     "- Preserve line breaks\n"
     "- When there is a numbered list seperate each number with a new line\n"
     "- Do not include empty parentheses\n"
     "- Do not include citations or URLs inside the answer. I will display sources separately."),
    ("human", "Context:\n{context}\n\nUser: {question}")
])


# intiialize database connnection
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

# to format the response to be more readable
def format_reply(text: str) -> str:
    if not text:
        return text
    t = text.strip().replace("\r\n", "\n").replace("\r", "\n")

    # ensure headings start on their own line
    t = re.sub(r"\s*(\*\*[^*\n]{2,80}\*\*:)\s*", r"\n\n\1\n", t)
    # put bullets on their own lines (handles "- ", "• ", "* ")
    t = re.sub(r"\s+(-\s+)", r"\n- ", t)
    t = re.sub(r"\s+(•\s+)", r"\n• ", t)
    t = re.sub(r"\s+(\*\s+)", r"\n* ", t)
    # if a bullet is glued to a heading like "**X:** - item", split it
    t = re.sub(r"(\*\*[^*\n]{2,80}\*\*:)\s*-\s*", r"\1\n- ", t)
    # keep numbered items clean 
    t = re.sub(r"\s+(\d+\.)\s+", r"\n\1 ", t)
    # collapse too many blank lines
    t = re.sub(r"\n{3,}", "\n\n", t)
    # return cleaned version
    return t.strip()

# to answer with rag
def answer_with_rag(question: str) -> dict:
    # handle greeting
    if GREETINGS_LIST.search(question.strip()):
        return {"reply": "Hi! I'm QChat. Ask me anything about Quinnipiac!", "sources": []}

    docs = retrieve(question, k=6)
    # failure to retrieve docs
    if not docs:
        return {
            "reply": "I don't know, not in the provided resources",
            "sources": [],
        }
    # build context
    context = "\n\n".join(f"[Source: {d.metadata.get('source','')}]\n{d.page_content}"
        for d in docs
    )
    # sources list, deduplicate and preserve order
    sources = []
    seen = set()
    for d in docs:
        s = d.metadata.get("source")
        if s and s not in seen:
            sources.append(s)
            seen.add(s)
    #get reply
    reply_text = llm.invoke(
        prompt_template.invoke({"context": context, "question": question})
    ).content.strip()
    reply_text = sanitize_text(reply_text)
    reply_text = format_reply(reply_text)
    # retrun reply
    return{"reply": reply_text, "sources": sources[:5]}


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        response = func.HttpResponse("")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response
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
            "faqEnabled": QCHAT_FAQ_FIRST,
        }
        return func.HttpResponse(json.dumps(info), mimetype="application/json")
    elif action == "chat":
        msg = (body.get("message") or req.params.get("message") or "").strip()
    else:
        # Fall back to chat if unknown action provided
        msg = (body.get("message") or req.params.get("message") or "").strip()
    
    if not msg:
        return func.HttpResponse('{"error":"missing message"}', status_code=400, mimetype="application/json")


    # FAQ matcher logic + RAG fallback
    try:
        # First control FAQ if enabled
        faq_result = None
        if QCHAT_FAQ_FIRST:
            print(f"Checking FAQ for: {msg}")
            faq_result = check_faq_by_keywords(msg)
        
        # if FAQ found use it , else use RAG
        if faq_result:
            print(f"FAQ match found! Category: {faq_result.get('category')}, Score: {faq_result.get('faqScore')}")
            reply = {
                "reply": faq_result.get("reply"),
                "sources": faq_result.get("sources", []),
                "source": "faq",
                "category": faq_result.get("category"),
                "faqScore": faq_result.get("faqScore"),
            }
        else:
            # Use RAG because no FAQ match
            print("No FAQ match, using RAG...")
            rag_result = answer_with_rag(msg)
            reply = {
                "reply": rag_result.get("reply", "I don't know."),
                "sources": rag_result.get("sources", []),
                "source": "rag",
            }
    except Exception as e:
        print(f"Error in FAQ/RAG processing: {repr(e)}")
        reply = {
            "reply": "I don't know.",
            "sources": [],
            "source": "error",
        }

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
            log_doc = {
                "userId": user_id,
                "action": action,
                "message": msg,
                "reply": reply.get("reply"),
                "source": reply.get("source", "unknown"),
                "ts": datetime.utcnow(),
            }
            
            # Add FAQ-specific analytics data
            if reply.get("source") == "faq":
                log_doc["faqCategory"] = reply.get("category")
                log_doc["faqScore"] = reply.get("faqScore")
            
            db[CHAT_LOGS_COLLECTION].insert_one(log_doc)
            print("inserting to mongo")
        except Exception as e:
            print("Mongo insert error:", repr(e))

    return response