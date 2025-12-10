import azure.functions as func
import json
import os
from datetime import datetime
from pymongo import MongoClient
import certifi
import hashlib

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGODB_URI') or os.getenv('MONGODB_URI')
DATABASE_NAME = os.environ.get('DB_NAME', 'qchat')
USERS_COLLECTION = 'users'

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


def _hash_password(password: str) -> str:
    """Simple password hashing (use bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        response = func.HttpResponse("")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON"}),
            status_code=400,
            mimetype="application/json"
        )

    action = body.get("action")
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()

    if not username or not password:
        response = func.HttpResponse(
            json.dumps({"error": "Username and password required"}),
            status_code=400,
            mimetype="application/json"
        )
        response.headers["Access-Control-Allow-Origin"] = "*"
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

    users_collection = db[USERS_COLLECTION]

    try:
        if action == "login":
            # Find user
            user = users_collection.find_one({"username": username})
            
            if user and user.get("password") == _hash_password(password):
                # Successful login
                users_collection.update_one(
                    {"username": username},
                    {"$set": {"lastLogin": datetime.utcnow()}}
                )
                result = {
                    "success": True,
                    "username": username,
                    "message": "Login successful"
                }
            else:
                result = {
                    "success": False,
                    "error": "Invalid username or password"
                }

        elif action == "register":
            # Check if user exists
            existing = users_collection.find_one({"username": username})
            
            if existing:
                result = {
                    "success": False,
                    "error": "Username already exists"
                }
            else:
                # Create new user
                users_collection.insert_one({
                    "username": username,
                    "password": _hash_password(password),
                    "createdAt": datetime.utcnow(),
                    "lastLogin": datetime.utcnow()
                })
                result = {
                    "success": True,
                    "username": username,
                    "message": "Registration successful"
                }
        else:
            result = {
                "success": False,
                "error": "Invalid action. Use 'login' or 'register'"
            }

    except Exception as e:
        print("Auth error:", repr(e))
        result = {
            "success": False,
            "error": "Authentication error"
        }

    response = func.HttpResponse(
        json.dumps(result),
        mimetype="application/json"
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
