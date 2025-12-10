import azure.functions as func
import json
import os
from datetime import datetime
from pymongo import MongoClient
import certifi

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGODB_URI') or os.getenv('MONGODB_URI')
DATABASE_NAME = os.environ.get('DB_NAME', 'qchat')
CONVERSATIONS_COLLECTION = 'conversations'

# MongoDB client (global)
mongo_client = None
db = None


def _init_db():
    """Initialize MongoDB connection."""
    global mongo_client, db
    if mongo_client is None and MONGO_URI:
        try:
            mongo_kwargs = {
                "serverSelectionTimeoutMS": 3000,
                "connectTimeoutMS": 3000,
                "socketTimeoutMS": 3000,
            }
            if MONGO_URI.startswith("mongodb+srv") or "mongodb.net" in MONGO_URI:
                mongo_kwargs["tls"] = True
                mongo_kwargs["tlsCAFile"] = certifi.where()
            mongo_client = MongoClient(MONGO_URI, **mongo_kwargs)
            mongo_client.admin.command("ping")
            db = mongo_client[DATABASE_NAME]
            print(f"Connected to MongoDB: {DATABASE_NAME}")
        except Exception as e:
            print("MongoDB connection error:", repr(e))
            mongo_client = None
            db = None


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        response = func.HttpResponse("")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    _init_db()

    if db is None:
        response = func.HttpResponse(
            json.dumps({"error": "Database unavailable"}),
            status_code=500,
            mimetype="application/json"
        )
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    conversations_collection = db[CONVERSATIONS_COLLECTION]

    try:
        if req.method == "GET":
            # Get user's conversation history
            username = req.params.get("username")
            
            if not username:
                result = {"error": "Username required"}
            else:
                # Fetch all conversations for this user
                conversations = list(conversations_collection.find(
                    {"username": username},
                    {"_id": 0}  # Exclude MongoDB _id from response
                ).sort("created", -1).limit(50))
                
                result = {"conversations": conversations}

        elif req.method == "POST":
            body = req.get_json()
            action = body.get("action")
            username = body.get("username")

            if not username:
                result = {"error": "Username required"}
            elif action == "save":
                # Save or update a conversation
                conversation = body.get("conversation")
                
                if not conversation or not conversation.get("id"):
                    result = {"error": "Invalid conversation data"}
                else:
                    # Upsert conversation
                    conversations_collection.update_one(
                        {
                            "username": username,
                            "id": conversation["id"]
                        },
                        {
                            "$set": {
                                "username": username,
                                "id": conversation["id"],
                                "title": conversation.get("title", ""),
                                "messages": conversation.get("messages", []),
                                "created": conversation.get("created", datetime.utcnow().isoformat()),
                                "updated": datetime.utcnow().isoformat()
                            }
                        },
                        upsert=True
                    )
                    result = {"success": True}

            elif action == "delete":
                # Delete a conversation
                conversation_id = body.get("conversationId")
                
                if not conversation_id:
                    result = {"error": "Conversation ID required"}
                else:
                    conversations_collection.delete_one({
                        "username": username,
                        "id": conversation_id
                    })
                    result = {"success": True}
            else:
                result = {"error": "Invalid action"}
        else:
            result = {"error": "Method not allowed"}

    except Exception as e:
        print("History error:", repr(e))
        result = {"error": "Server error"}

    response = func.HttpResponse(
        json.dumps(result),
        mimetype="application/json"
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
