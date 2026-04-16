# ollama to make the gemma model
import azure.functions as func
import json, os, re
import sys
from datetime import datetime
from pymongo import MongoClient
import certifi

from env_loader import load_backend_env

load_backend_env()

# for llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
# Profile service import
from .profile_service import ensure_profile_exists, get_user_profile
# Smart profile extractor
from .smart_profile_extractor import extract_profile_info_from_conversation, apply_extracted_info_to_profile
# Unified response system (replaces tiered Personal→FAQ→RAG)
from .unified_response import get_unified_response
# FAQ matcher import
from .faq_matcher import check_faq_by_keywords
from .profanity_filter import sanitize_text
from .RAG import retrieve
from .livewhale import get_upcoming_events
from .qu_topic_redirects import get_topic_redirect, looks_like_idk_reply


def _configure_console_encoding() -> None:
    """Avoid Windows cp1252 crashes when logging non-ASCII retrieval text."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="backslashreplace")
            except Exception:
                # Best-effort only; fallback safe logging still handles failures.
                pass


def _safe_log(*parts) -> None:
    """Log without raising UnicodeEncodeError on Windows consoles."""
    text = " ".join(str(p) for p in parts)
    try:
        print(text)
    except UnicodeEncodeError:
        # Last-resort fallback if stream encoding cannot print certain characters.
        print(text.encode("ascii", "backslashreplace").decode("ascii"))


_configure_console_encoding()

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGODB_URI') or os.getenv('MONGODB_URI')
DATABASE_NAME = os.environ.get('DB_NAME', 'qchat')
CHAT_LOGS_COLLECTION = 'chatLogs'
# Allow turning off DB logging entirely via env
QCHAT_LOG_CHATS = (os.getenv('QCHAT_LOG_CHATS', 'true').lower() == 'true')

# MongoDB client (global)
mongo_client = None
db = None
# One-time DB check flags
_db_checked = False
_db_ready = False
_db_error = None

# Collections
CONVERSATIONS_COLLECTION = 'conversations'

# greetings to aviod rag answering
GREETINGS_LIST = re.compile(r"\b(hi|hello|hey|hii|sup|what'?s up)\b", re.IGNORECASE)

_THANKS_REPLY_TEXT = (
    "You're welcome! I'm glad I could help. Let me know if you need anything else."
)


def _is_thanks_only_message(msg: str) -> bool:
    """True for short gratitude-only messages (no real follow-up question)."""
    t = re.sub(r"[!?.,:;\"']+", "", (msg or "").strip().lower())
    t = re.sub(r"\s+", " ", t).strip()
    if not t or len(t) > 100:
        return False
    if re.search(
        r"\b(where|when|what|how|why|which|who|can you|could you|should i|is there)\b",
        t,
    ):
        return False
    thank_patterns = [
        r"^thank you(\s+(so|very)\s+much)?$",
        r"^thanks(\s+(so|a)\s+(much|lot))?$",
        r"^(ty|thx|tysm)$",
        r"^much appreciated$",
        r"^(i\s+)?(really\s+)?appreciate(\s+it)?$",
        r"^thank you again$",
        r"^thanks again$",
        r"^thanks for (the help|everything|that|your help)$",
        r"^thank you for (the help|everything|that|your help)$",
    ]
    return any(re.match(p, t) for p in thank_patterns)
# for events
EVENTS_TRIGGER = re.compile(
    r"\b(next|events|event|upcoming|today|todays|tomorrow|schedule|vs|versus|week|weekend|happening|going on)\b",
    re.I,
)
SPORT_WORDS = re.compile(r"\b(basketball|hockey|soccer|baseball|softball|volleyball|lacrosse)\b", re.I)
FINAL_EXAM_QUERY = re.compile(
    r"\b(final|finals|final exam|final exams|exam period|exam week)\b",
    re.I,
)


#Enable FAQ priority: check FAQs before calling RAG
QCHAT_FAQ_FIRST = (os.getenv('QCHAT_FAQ_FIRST', 'true').lower() == 'true')

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
     "- If the answer is NOT in the context and NOT a greeting → briefly say you do not have that in the provided Quinnipiac resources, then point the student to the most relevant campus area (dining, housing, athletics, MyQ, careers, events, health/wellness, etc.) in one short sentence. Do not invent facts or links.\n"
     "- NEVER make up information.\n"
     "- ALWAYS be helpful and positive.\n"
     "- NEVER make up or modify the links given, provide the exact link without any adjustments.\n"
     "- assume the student is an undergraduate living on Mount Carmel, unless otherwise told. \n"
     "- Use the conversation history to understand follow-up questions in context.\n"
     "Formatting rules:\n"
     "- Use short paragraphs\n"
     "- Use bullet points for lists\n"
     "- Use headings when appropriate\n"
     "- Do NOT return one long block of text\n"
     "- Preserve line breaks\n"
     "- When there is a numbered list seperate each number with a new line\n"
     "- Do not include empty parentheses\n"
     "- Do not include citations or URLs inside the answer. I will display sources separately."),
    ("human", "Context:\n{context}\n\nConversation history:\n{history}\n\nUser: {question}")
])

# prompt for ambiguity detection on short/vague queries
_ambiguity_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a query analyzer for a university chatbot. "
     "Your ONLY job is to determine if a student's question is ambiguous — "
     "meaning it could reasonably refer to multiple different topics at a university.\n\n"
     "Examples of ambiguous queries:\n"
     "- 'finals' → could mean final exams or sports finals/championships\n"
     "- 'registration' → could mean course registration, event registration, or orientation registration\n"
     "- 'drop' → could mean dropping a class, drop-in hours, or drop-off locations\n"
     "- 'application' → could mean college application, job application, or software application\n\n"
     "Examples of clear queries (NOT ambiguous):\n"
     "- 'when is the final exam for biology' → clearly about exams\n"
     "- 'what are the dining hall hours' → clearly about dining\n"
     "- 'basketball schedule' → clearly about sports\n"
     "- 'hi' or 'hello' → greetings are never ambiguous\n"
     "- 'thanks' → gratitude is never ambiguous\n\n"
     "Also consider the conversation history. If a previous message already "
     "clarified the topic, the follow-up is NOT ambiguous.\n\n"
     "If the query IS ambiguous, respond with ONLY a short, friendly clarifying question "
     "(e.g., 'Are you asking about final exams or sports finals/championships?').\n"
     "If the query is NOT ambiguous, respond with ONLY the word: CLEAR"),
    ("human", "Conversation history:\n{history}\n\nNew message: {message}")
])


def detect_ambiguity(message: str, history_text: str = "") -> str | None:
    """
    Returns a clarifying question if the message is ambiguous,
    or None if it's clear enough to answer directly.
    Only called for short queries (<=5 words) to avoid unnecessary LLM calls.
    """
    try:
        result = llm.invoke(
            _ambiguity_prompt.invoke({"message": message, "history": history_text})
        ).content.strip()
        if result.lower().startswith("ambiguous:"):
            result = result.split(":", 1)[1].strip()

        if result.upper().startswith("CLEAR"):
            return None
        return result
    except Exception as e:
        print(f"Ambiguity detection error: {repr(e)}")
        return None


def _format_history_text(history: list) -> str:
    """Format conversation history list into a readable string for LLM prompts."""
    if not history:
        return "(no prior messages)"
    lines = []
    for m in history[-6:]:
        role = "User" if m.get("role") == "user" else "QChat"
        lines.append(f"{role}: {m.get('text', '')}")
    return "\n".join(lines)


def _is_final_exam_query(question: str) -> bool:
    """Detect questions likely about undergraduate final-exam timing/schedule."""
    q = (question or "").lower()
    if not q:
        return False
    if not FINAL_EXAM_QUERY.search(q):
        return False
    if SPORT_WORDS.search(q):
        return False
    return True


def _mentions_law_or_medicine(question: str) -> bool:
    q = (question or "").lower()
    return any(term in q for term in ["law", "school of law", "medicine", "medical", "netter"])


def _build_final_exam_retrieval_query(question: str) -> str:
    """Bias retrieval toward the main QU academic calendar finals window."""
    return (
        f"{question} "
        "quinnipiac undergraduate academic calendar final exam period mount carmel "
        "spring semester finals dates"
    ).strip()


def _rerank_docs_for_final_exams(docs: list) -> list:
    """Prioritize academic-calendar pages and downrank medicine/law pages for finals-date questions."""
    def score_doc(d) -> int:
        source = (d.metadata.get("source") or "").lower()
        score = 0
        if "academic-calendar" in source:
            score += 100
        if "/academics/" in source:
            score += 15
        if "medicine.qu.edu" in source or "/admissions/medicine" in source:
            score -= 40
        if "law.qu.edu" in source:
            score -= 20
        return score

    return sorted(docs, key=score_doc, reverse=True)


def _latest_assistant_before_current_user(history: list) -> tuple[dict | None, int]:
    """
    Return the latest assistant message and index.
    If the current user message is already included at the end of history,
    search starting from the prior index.
    """
    if not history:
        return None, -1

    start = len(history) - 1
    if history[-1].get("role") == "user":
        start -= 1

    for i in range(start, -1, -1):
        if history[i].get("role") == "assistant":
            return history[i], i
    return None, -1


def _latest_user_before_index(history: list, index: int) -> dict | None:
    """Return the latest user message before a given history index."""
    for i in range(index - 1, -1, -1):
        if history[i].get("role") == "user":
            return history[i]
    return None

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
            "serverSelectionTimeoutMS": 30000,
            "connectTimeoutMS": 30000,
            "socketTimeoutMS": 30000,
        }
        if MONGO_URI.startswith("mongodb+srv") or "mongodb.net" in MONGO_URI:
            # Atlas requires TLS
            mongo_kwargs["tls"] = True
            mongo_kwargs["tlsCAFile"] = certifi.where()
            mongo_kwargs["retryWrites"] = True
        mc = MongoClient(MONGO_URI, **mongo_kwargs)
        # Ping to verify connectivity
        mc.admin.command("ping")
        mongo_client = mc
        db = mongo_client[DATABASE_NAME]
        _db_ready = True
    except Exception as e:
        _safe_log("Mongo one-time init failed:", repr(e))
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
def answer_with_rag(question: str, history_text: str = "", apply_final_exam_boost: bool = False) -> dict:
    # handle greeting
    if GREETINGS_LIST.search(question.strip()):
        return {"reply": "Hi! I'm QChat. Ask me anything about Quinnipiac!", "sources": []}

    if _is_thanks_only_message(question):
        return {"reply": _THANKS_REPLY_TEXT, "sources": []}

    use_final_exam_boost = apply_final_exam_boost or _is_final_exam_query(question)
    allow_professional_school_content = _mentions_law_or_medicine(question)
    retrieval_query = _build_final_exam_retrieval_query(question) if use_final_exam_boost else question
    docs = retrieve(retrieval_query, k=10 if use_final_exam_boost else 6)
    if use_final_exam_boost and docs:
        docs = _rerank_docs_for_final_exams(docs)[:6]
        if not allow_professional_school_content:
            docs = [
                d for d in docs
                if "law.qu.edu" not in (d.metadata.get("source") or "").lower()
                and "medicine.qu.edu" not in (d.metadata.get("source") or "").lower()
            ]
            # Keep a fallback in case filtering becomes too aggressive.
            if not docs:
                docs = retrieve(question, k=6)
    # failure to retrieve docs
    if not docs:
        redirect = get_topic_redirect(question)
        if redirect:
            return redirect
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
    llm_question = question
    if use_final_exam_boost and not allow_professional_school_content:
        llm_question = (
            f"{question}\n"
            "Important: The user did not ask about School of Law or School of Medicine. "
            "Prioritize undergraduate and graduate on-campus final exam dates from the main QU academic calendar."
        )

    reply_text = llm.invoke(
        prompt_template.invoke({"context": context, "question": llm_question, "history": history_text})
    ).content.strip()
    reply_text = sanitize_text(reply_text)
    reply_text = format_reply(reply_text)
    redirect = get_topic_redirect(question)
    if redirect and looks_like_idk_reply(reply_text):
        return {"reply": redirect["reply"], "sources": redirect["sources"]}
    # retrun reply
    return{"reply": reply_text, "sources": sources[:5]}

def _get_recent_conversation_history(username: str, limit: int = 10) -> list:
    """
    Get recent conversation history for context in profile extraction.
    
    Args:
        username: The username to get history for
        limit: Maximum number of recent messages to retrieve
        
    Returns:
        List of message dicts with 'role' and 'text' keys
    """
    if not _db_ready or db is None:
        return []
    
    try:
        # Get the most recent conversation for this user
        conversation = db[CONVERSATIONS_COLLECTION].find_one(
            {"username": username},
            sort=[("updated", -1)]  # Most recently updated
        )
        
        if not conversation or "messages" not in conversation:
            return []
        
        # Get the last N messages
        messages = conversation["messages"][-limit:] if len(conversation["messages"]) > limit else conversation["messages"]
        
        # Convert to expected format
        history = []
        for msg in messages:
            history.append({
                "role": msg.get("role", "user"),
                "text": msg.get("text", "")
            })
        
        return history
        
    except Exception as e:
        _safe_log(f"Error retrieving conversation history: {repr(e)}")
        return []


def _smart_extract_and_save_profile(username: str, user_message: str, bot_reply: str):
    """
    Use LLM to intelligently extract and save profile information.
    Analyzes conversation context to understand what should be remembered.
    """
    try:
        # Get conversation history for context
        conversation_history = _get_recent_conversation_history(username, limit=10)
        
        # Get current profile for context
        from . import profile_service
        current_profile = get_user_profile(username)
        
        # Use LLM to extract information
        extracted = extract_profile_info_from_conversation(
            user_message=user_message,
            bot_reply=bot_reply,
            conversation_history=conversation_history,
            current_profile=current_profile
        )
        
        # Apply extracted information to profile
        if extracted.get("extracted"):
            updated = apply_extracted_info_to_profile(username, extracted, profile_service)
            if updated:
                _safe_log(f"✓ Smart extraction updated profile for {username}")
            else:
                _safe_log(f"No new information to add for {username}")
        else:
            _safe_log(f"No profile information detected in conversation for {username}")
            
    except Exception as e:
        _safe_log(f"Error in smart profile extraction: {repr(e)}")
        import traceback
        traceback.print_exc()


def main(req: func.HttpRequest) -> func.HttpResponse:
    # MAINTENANCE MODE CHECK - BLOCKS EVERYONE
    maintenance_file = os.path.join(os.path.dirname(__file__), '..', 'maintenance_mode.json')
    try:
        if os.path.exists(maintenance_file):
            with open(maintenance_file, 'r') as f:
                maintenance_status = json.load(f)
                if maintenance_status.get('enabled', False):
                    _safe_log('Chat request BLOCKED - Maintenance mode enabled')
                    response = func.HttpResponse(
                        json.dumps({
                            "error": "maintenance_mode",
                            "message": maintenance_status.get('message', 'System under maintenance')
                        }),
                        status_code=503,
                        mimetype="application/json"
                    )
                    response.headers["Access-Control-Allow-Origin"] = "*"
                    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
                    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
                    return response
    except Exception as e:
        _safe_log(f'Error checking maintenance mode: {str(e)}')
    
    if req.method == "OPTIONS":
        response = func.HttpResponse("")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    _safe_log("main called")
    
    try:
        body = req.get_json()
    except ValueError:
        body = {}

    
    # Backward-compatible parameter parsing (supports body and querystring)
    action = body.get("action") or req.params.get("action") or "chat"
    user_id = body.get("userId") or req.params.get("userId") or "anonymous"
    username = body.get("username") or req.params.get("username") or user_id
    msg = ""
    
    # Ensure user profile exists for non-anonymous users
    if username and username != "anonymous":
        try:
            ensure_profile_exists(username)
        except Exception as e:
            _safe_log(f"Error ensuring profile exists for {username}: {repr(e)}")
    
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
            "responseSystem": "unified",  # Indicate using unified system
        }
        return func.HttpResponse(json.dumps(info), mimetype="application/json")
    elif action == "chat":
        msg = (body.get("message") or req.params.get("message") or "").strip()
    else:
        # Fall back to chat if unknown action provided
        msg = (body.get("message") or req.params.get("message") or "").strip()
    
    if not msg:
        return func.HttpResponse('{"error":"missing message"}', status_code=400, mimetype="application/json")

    # Extract conversation history sent from the frontend
    conversation_history = body.get("history", [])
    history_text = _format_history_text(conversation_history)

    # Detect whether this is a reply to a clarification question.
    latest_assistant, assistant_idx = _latest_assistant_before_current_user(conversation_history)
    _prev_was_clarification = bool(
        latest_assistant and latest_assistant.get("source") == "clarification"
    )

    # If user is replying to a clarification, merge topic + follow-up
    # e.g. "finals" + "exams" -> "finals exams"
    query_text = msg
    if _prev_was_clarification and assistant_idx > 0:
        previous_user = _latest_user_before_index(conversation_history, assistant_idx)
        if previous_user and previous_user.get("text"):
            query_text = f"{previous_user.get('text', '').strip()} {msg}".strip()
            print(f"Clarification follow-up detected. Expanded query: {query_text}")
    final_exam_intent = _is_final_exam_query(query_text)

    reply = None

    if (
        not _is_thanks_only_message(msg)
        and not GREETINGS_LIST.search(msg.strip())
        and len(msg.split()) <= 5
        and not _prev_was_clarification
    ):
        print(f"Short query detected ({len(msg.split())} words), checking ambiguity: {msg}")
        clarification = detect_ambiguity(msg, history_text)
        if clarification:
            print(f"Ambiguous query — asking for clarification")
            reply = {
                "reply": clarification,
                "sources": [],
                "source": "clarification",
            }

    # FAQ matcher logic + RAG fallback (skipped if ambiguity already produced a reply)
    if reply is None:
        try:
            if _is_thanks_only_message(msg):
                reply = {
                    "reply": _THANKS_REPLY_TEXT,
                    "sources": [],
                    "source": "thanks",
                }
            elif _prev_was_clarification:
                _safe_log("Clarification follow-up: bypassing FAQ/event routing and using RAG")
                rag_result = answer_with_rag(
                    query_text,
                    history_text,
                    apply_final_exam_boost=final_exam_intent,
                )
                reply = {
                    "reply": rag_result.get("reply", "I don't know."),
                    "sources": rag_result.get("sources", []),
                    "source": "rag",
                }
            elif final_exam_intent:
                _safe_log("Final-exam intent detected: bypassing FAQ/event routing and using boosted RAG")
                rag_result = answer_with_rag(
                    query_text,
                    history_text,
                    apply_final_exam_boost=True,
                )
                reply = {
                    "reply": rag_result.get("reply", "I don't know."),
                    "sources": rag_result.get("sources", []),
                    "source": "rag",
                }
            else:
                faq_result = None
                if QCHAT_FAQ_FIRST:
                    _safe_log(f"Checking FAQ for: {query_text}")
                    faq_result = check_faq_by_keywords(query_text)

                if faq_result:
                    _safe_log(
                        f"FAQ match found! Category: {faq_result.get('category')}, Score: {faq_result.get('faqScore')}"
                    )
                    reply = {
                        "reply": faq_result.get("reply"),
                        "sources": faq_result.get("sources", []),
                        "source": "faq",
                        "category": faq_result.get("category"),
                        "faqScore": faq_result.get("faqScore"),
                    }
                elif EVENTS_TRIGGER.search(query_text):
                    events = get_upcoming_events(limit=10, query=query_text)

                    if events:
                        reply_text = "Here are upcoming Quinnipiac events:\n\n"

                        for e in events:
                            reply_text += f"• {e['title']}\n  {e['link']}\n\n"
                        reply = {
                            "reply": reply_text,
                            "sources": [e["link"] for e in events],
                            "source": "livewhale",
                        }
                    else:
                        _safe_log("No livewhale match, using RAG...")
                        rag_result = answer_with_rag(query_text, history_text)
                        reply = {
                            "reply": rag_result.get("reply", "I don't know."),
                            "sources": rag_result.get("sources", []),
                            "source": "rag",
                        }
                else:
                    _safe_log("No FAQ match, using RAG...")
                    rag_result = answer_with_rag(query_text, history_text)
                    reply = {
                        "reply": rag_result.get("reply", "I don't know."),
                        "sources": rag_result.get("sources", []),
                        "source": "rag",
                    }
        except Exception as e:
            err_msg = repr(e)
            _safe_log(f"Error in FAQ/RAG processing: {err_msg}")
            reply = {
                "reply": f"I don't know. (Backend error: {err_msg})",
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
            
            db[CHAT_LOGS_COLLECTION].insert_one(log_doc)
            _safe_log("inserting to mongo")
        except Exception as e:
            _safe_log("Mongo insert error:", repr(e))

    return response