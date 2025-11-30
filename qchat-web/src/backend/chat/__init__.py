# ollama to make the gemma model
import azure.functions as func
import json, os

from .RAG import answer_with_rag

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

# MongoDB client (global)
mongo_client = None
db = None
# One-time DB check flags
_db_checked = False
_db_ready = False
_db_error = None


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
        # send message to databse
        try:
            db[CHAT_LOGS_COLLECTION].insert_one({
                "userId": user_id,
                "action": action,
                "message": msg,
                "reply": reply,
                "ts": datetime.utcnow(),
            })
            print("inserting to mongo")
        except Exception as e:
            # connection to database error
            print("Mongo insert error:", repr(e))

    return response

