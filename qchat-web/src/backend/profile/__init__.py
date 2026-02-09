import azure.functions as func
import json
import os
from datetime import datetime
import sys
import os.path

# Add parent directory to path to import profile_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from chat.profile_service import (
    get_user_profile,
    create_user_profile,
    update_user_profile,
    add_to_profile_array,
    ensure_profile_exists
)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Profile Management Endpoint
    
    GET /api/profile?username=<username> - Retrieve user profile
    POST /api/profile - Create or update profile
        Body: {
            "username": "user123",
            "action": "get" | "update" | "add_class" | "add_activity",
            "data": { ... profile fields to update ... }
        }
    """
    # Handle CORS preflight
    if req.method == "OPTIONS":
        response = func.HttpResponse("")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    try:
        # Handle GET requests
        if req.method == "GET":
            username = req.params.get("username")
            if not username:
                return _error_response("Missing username parameter", 400)
            
            profile = get_user_profile(username)
            if profile is None:
                # Create profile if it doesn't exist
                try:
                    profile = create_user_profile(username)
                except ValueError:
                    # Already exists (race condition)
                    profile = get_user_profile(username)
            
            return _success_response({"profile": profile})
        
        # Handle POST requests
        elif req.method == "POST":
            try:
                body = req.get_json()
            except ValueError:
                return _error_response("Invalid JSON in request body", 400)
            
            username = body.get("username")
            action = body.get("action", "update")
            
            if not username:
                return _error_response("Missing username in request", 400)
            
            # Ensure profile exists
            ensure_profile_exists(username)
            
            # Handle different actions
            if action == "get":
                profile = get_user_profile(username)
                return _success_response({"profile": profile})
            
            elif action == "update":
                data = body.get("data", {})
                if not data:
                    return _error_response("Missing data to update", 400)
                
                success = update_user_profile(username, data)
                if success:
                    updated_profile = get_user_profile(username)
                    return _success_response({
                        "message": "Profile updated successfully",
                        "profile": updated_profile
                    })
                else:
                    return _error_response("Failed to update profile", 500)
            
            elif action == "add_class":
                class_data = body.get("data", {})
                if not class_data.get("name"):
                    return _error_response("Missing class name", 400)
                
                # Structure class data
                class_obj = {
                    "name": class_data.get("name"),
                    "code": class_data.get("code"),
                    "professor": class_data.get("professor"),
                    "schedule": class_data.get("schedule"),  # e.g., "MWF 10:00-11:00"
                    "location": class_data.get("location"),
                    "added_at": datetime.utcnow()
                }
                
                success = add_to_profile_array(username, "schedule.classes", class_obj)
                if success:
                    return _success_response({
                        "message": "Class added successfully",
                        "class": class_obj
                    })
                else:
                    return _error_response("Failed to add class", 500)
            
            elif action == "add_activity":
                activity = body.get("data", {}).get("activity")
                if not activity:
                    return _error_response("Missing activity", 400)
                
                success = add_to_profile_array(username, "schedule.extracurriculars", activity)
                if success:
                    return _success_response({
                        "message": "Activity added successfully",
                        "activity": activity
                    })
                else:
                    return _error_response("Failed to add activity", 500)
            
            elif action == "set_preferences":
                prefs = body.get("data", {})
                updates = {}
                
                if "favorite_dining_halls" in prefs:
                    updates["preferences.favorite_dining_halls"] = prefs["favorite_dining_halls"]
                if "dietary_restrictions" in prefs:
                    updates["preferences.dietary_restrictions"] = prefs["dietary_restrictions"]
                if "study_locations" in prefs:
                    updates["preferences.study_locations"] = prefs["study_locations"]
                
                if updates:
                    success = update_user_profile(username, updates)
                    if success:
                        return _success_response({"message": "Preferences updated successfully"})
                    else:
                        return _error_response("Failed to update preferences", 500)
                else:
                    return _error_response("No valid preferences provided", 400)
            
            else:
                return _error_response(f"Unknown action: {action}", 400)
        
        else:
            return _error_response(f"Method {req.method} not allowed", 405)
    
    except Exception as e:
        print(f"Profile endpoint error: {repr(e)}")
        return _error_response(f"Internal server error: {str(e)}", 500)


def _success_response(data: dict, status_code: int = 200) -> func.HttpResponse:
    """Create a successful JSON response with CORS headers."""
    response = func.HttpResponse(
        json.dumps(data),
        status_code=status_code,
        mimetype="application/json"
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def _error_response(message: str, status_code: int = 400) -> func.HttpResponse:
    """Create an error JSON response with CORS headers."""
    response = func.HttpResponse(
        json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json"
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
