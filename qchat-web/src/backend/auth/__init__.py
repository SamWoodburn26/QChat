import azure.functions as func
import json
import os
import base64
from datetime import datetime
from pymongo import MongoClient
import certifi
import hashlib
import requests

from env_loader import load_backend_env

load_backend_env()

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGODB_URI') or os.getenv('MONGODB_URI')
DATABASE_NAME = os.environ.get('DB_NAME', 'chatbot_db')
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
                "serverSelectionTimeoutMS": 30000,
                "connectTimeoutMS": 30000,
                "socketTimeoutMS": 30000,
            }
            if MONGO_URI.startswith("mongodb+srv") or "mongodb.net" in MONGO_URI:
                mongo_kwargs["tls"] = True
                mongo_kwargs["tlsCAFile"] = certifi.where()
                mongo_kwargs["retryWrites"] = True
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


def _decode_jwt_payload(id_token: str) -> dict:
    parts = id_token.split(".")
    if len(parts) != 3:
        raise RuntimeError("Invalid id_token format")
    payload_part = parts[1]
    padded = payload_part + "=" * ((4 - (len(payload_part) % 4)) % 4)
    decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
    return json.loads(decoded)


def _exchange_microsoft_code(code: str, code_verifier: str, redirect_uri: str) -> dict:
    tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common").strip() or "common"
    client_id = os.getenv("MICROSOFT_CLIENT_ID", "").strip()
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        raise RuntimeError("Microsoft code exchange is not configured. Set MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET.")

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_resp = requests.post(
        token_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "scope": "openid profile email",
        },
        timeout=20,
    )

    if not token_resp.ok:
        raise RuntimeError(f"Token exchange failed: {token_resp.text}")

    token_json = token_resp.json()
    id_token = token_json.get("id_token")
    if not id_token:
        raise RuntimeError("No id_token returned from Microsoft token endpoint")

    return _decode_jwt_payload(id_token)


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

    # Only require password for login/register actions, not OAuth
    if action in ["login", "register"]:
        if not username or not password:
            response = func.HttpResponse(
                json.dumps({"error": "Username and password required"}),
                status_code=400,
                mimetype="application/json"
            )
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
    elif action in ["microsoft_login", "google_login"]:
        if not username:
            response = func.HttpResponse(
                json.dumps({"error": "Username required"}),
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
                role = user.get("role", "student")
                name = user.get("name", username)
                result = {
                    "success": True,
                    "username": username,
                    "name": name,
                    "role": role,
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
                    "role": "student",
                    "createdAt": datetime.utcnow(),
                    "lastLogin": datetime.utcnow()
                })
                result = {
                    "success": True,
                    "username": username,
                    "role":"student",
                    "message": "Registration successful"
                }
        
        elif action == "microsoft_login":
            # Microsoft OAuth login - no password needed
            name = body.get("name", username)
            
            # Check if user exists
            existing = users_collection.find_one({"username": username})
            
            if existing:
                # Update last login
                users_collection.update_one(
                    {"username": username},
                    {"$set": {"lastLogin": datetime.utcnow()}}
                )
                role = existing.get("role", "student") 
            else:
                # Create new user for Microsoft account (no password)
                role="student"
                users_collection.insert_one({
                    "username": username,
                    "name": name,
                    "authProvider": "microsoft",
                    "role": role,
                    "createdAt": datetime.utcnow(),
                    "lastLogin": datetime.utcnow()
                })
            
            result = {
                "success": True,
                "username": username,
                "name": name,
                "role": role,
                "message": "Microsoft login successful"
            }

        elif action == "microsoft_exchange_code":
            code = body.get("code", "").strip()
            code_verifier = body.get("codeVerifier", "").strip()
            redirect_uri = body.get("redirectUri", "").strip()
            expected_nonce = body.get("expectedNonce", "").strip()

            if not code or not code_verifier or not redirect_uri:
                result = {
                    "success": False,
                    "error": "Missing code exchange parameters"
                }
            else:
                payload = _exchange_microsoft_code(code, code_verifier, redirect_uri)

                nonce = (payload.get("nonce") or "").strip()
                if expected_nonce and nonce != expected_nonce:
                    result = {
                        "success": False,
                        "error": "Nonce validation failed"
                    }
                else:
                    email = (payload.get("email") or payload.get("preferred_username") or "").strip().lower()
                    if not email:
                        result = {
                            "success": False,
                            "error": "No email/username returned from Microsoft token"
                        }
                    else:
                        name = (payload.get("name") or email).strip()
                        existing = users_collection.find_one({"username": email})

                        if existing:
                            users_collection.update_one(
                                {"username": email},
                                {"$set": {"lastLogin": datetime.utcnow()}}
                            )
                            role = existing.get("role", "student")
                        else:
                            role = "student"
                            users_collection.insert_one({
                                "username": email,
                                "name": name,
                                "authProvider": "microsoft",
                                "role": role,
                                "createdAt": datetime.utcnow(),
                                "lastLogin": datetime.utcnow()
                            })

                        result = {
                            "success": True,
                            "username": email,
                            "name": name,
                            "role": role,
                            "message": "Microsoft login successful"
                        }
        
        elif action == "google_login":
            # Google OAuth login - no password needed
            name = body.get("name", username)
            
            # Check if user exists
            existing = users_collection.find_one({"username": username})
            
            if existing:
                # Update last login
                users_collection.update_one(
                    {"username": username},
                    {"$set": {"lastLogin": datetime.utcnow()}}
                )
                role = existing.get("role", "student")
            else:
                # Create new user for Google account (no password)
                role="student"
                users_collection.insert_one({
                    "username": username,
                    "name": name,
                    "authProvider": "google",
                    "role": role,
                    "createdAt": datetime.utcnow(),
                    "lastLogin": datetime.utcnow()
                })
            
            result = {
                "success": True,
                "username": username,
                "name": name,
                "role": role,
                "message": "Google login successful"
            }
        
        else:
            result = {
                "success": False,
                "error": "Invalid action. Use 'login', 'register', 'microsoft_login', 'google_login', or 'microsoft_exchange_code'"
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
