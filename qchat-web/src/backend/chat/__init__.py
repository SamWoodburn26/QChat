# ollama to make the gemma model
import azure.functions as func
import json, os

from .RAG import answer_with_rag
# FAQ matcher import
from .faq_matcher import check_faq_by_keywords
# Profile service import
from .profile_service import ensure_profile_exists, get_user_profile
# Smart profile extractor
from .smart_profile_extractor import extract_profile_info_from_conversation, apply_extracted_info_to_profile
# Personal question handler
from .personal_qa import try_answer_personal_question

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


#Enable FAQ priority: check FAQs before calling RAG
QCHAT_FAQ_FIRST = (os.getenv('QCHAT_FAQ_FIRST', 'true').lower() == 'true')

# MongoDB client (global)
mongo_client = None
db = None
# One-time DB check flags
_db_checked = False
_db_ready = False
_db_error = None

# Collections
CONVERSATIONS_COLLECTION = 'conversations'


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
        print(f"Error retrieving conversation history: {repr(e)}")
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
                print(f"✓ Smart extraction updated profile for {username}")
            else:
                print(f"No new information to add for {username}")
        else:
            print(f"No profile information detected in conversation for {username}")
            
    except Exception as e:
        print(f"Error in smart profile extraction: {repr(e)}")
        import traceback
        traceback.print_exc()


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
    username = body.get("username") or req.params.get("username") or user_id
    msg = ""
    
    # Ensure user profile exists for non-anonymous users
    if username and username != "anonymous":
        try:
            ensure_profile_exists(username)
        except Exception as e:
            print(f"Error ensuring profile exists for {username}: {repr(e)}")
    
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


    # Personal question → FAQ → RAG priority chain
    try:
        # FIRST: Check if it's a personal question about the user's profile
        personal_answer = None
        if username and username != "anonymous":
            personal_answer = try_answer_personal_question(msg, username)
        
        if personal_answer:
            print(f"Answered from profile for {username}")
            reply = personal_answer
        else:
            # SECOND: Check FAQ if enabled
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
                # THIRD: Use RAG because no FAQ match
                print("No FAQ match, using RAG...")
                rag_result = answer_with_rag(msg, username if username != "anonymous" else None)
                reply = {
                    "reply": rag_result.get("reply", "I don't know."),
                    "sources": rag_result.get("sources", []),
                    "source": "rag",
                }
        
        # Smart profile extraction using LLM for non-anonymous users
        if username and username != "anonymous":
            try:
                _smart_extract_and_save_profile(username, msg, reply.get("reply", ""))
            except Exception as e:
                print(f"Error in smart profile extraction: {repr(e)}")
                
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