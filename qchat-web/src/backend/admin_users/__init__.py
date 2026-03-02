"""
Admin Users API
GET /api/admin/users - List all users
PUT /api/admin/users/{id} - Update user role
"""

import azure.functions as func
import logging
import json
from datetime import datetime
from bson import ObjectId
import sys
import os

# Add backend to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_connection import user_service, users_collection


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Admin Users API
    
    GET /api/admin/users
    - Returns list of all users
    
    PUT /api/admin/users/{user_id}
    - Updates user role
    - Body: {"role": "admin" | "student"}
    """
    logging.info('Admin users API triggered')
    
    # Get HTTP method
    method = req.method
    
    try:
        if method == 'GET':
            return handle_get_users(req)
        elif method == 'PUT':
            return handle_update_user(req)
        else:
            return func.HttpResponse(
                json.dumps({"error": "Method not allowed"}),
                status_code=405,
                mimetype="application/json"
            )
    
    except Exception as e:
        logging.error(f"Admin users API error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def handle_get_users(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/admin/users
    
    Returns all users with their roles
    
    Response:
    {
        "users": [
            {
                "_id": "...",
                "username": "user@example.com",
                "name": "User Name",
                "role": "student",
                "createdAt": "2026-01-01T00:00:00Z",
                "lastLogin": "2026-01-02T00:00:00Z"
            }
        ]
    }
    """
    logging.info('Getting all users')
    
    try:
        # Get all users from MongoDB
        all_users = list(users_collection.find(
            {},
            {
                "_id": 1,
                "username": 1,
                "name": 1,
                "role": 1,
                "createdAt": 1,
                "lastLogin": 1,
                "authProvider": 1,
                "UserId": 1
            }
        ))
        
        # Convert ObjectId to string
        users_data = []
        for user in all_users:
            user_dict = {
                "_id": str(user["_id"]),
                "username": user.get("username", ""),
                "name": user.get("name"),
                "role": user.get("role", "student"),  # Default to student if not set
                "createdAt": user.get("createdAt", datetime.utcnow()).isoformat() if isinstance(user.get("createdAt"), datetime) else str(user.get("createdAt", "")),
                "lastLogin": user.get("lastLogin", "").isoformat() if isinstance(user.get("lastLogin"), datetime) else str(user.get("lastLogin", ""))
            }
            users_data.append(user_dict)
        
        logging.info(f"Found {len(users_data)} users")
        
        return func.HttpResponse(
            json.dumps({"users": users_data}),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logging.error(f"Error getting users: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Failed to get users: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )


def handle_update_user(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/admin/users/{user_id}
    
    Updates user role
    
    URL: /api/admin/users/65abc123...
    Body: {"role": "admin"} or {"role": "student"}
    
    Response:
    {
        "success": true,
        "user": {
            "_id": "...",
            "username": "user@example.com",
            "role": "admin"
        }
    }
    """
    logging.info('Updating user role')
    
    try:
        # Get user_id from route params
        user_id = req.route_params.get('id')
        
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "User ID is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get request body
        req_body = req.get_json()
        new_role = req_body.get('role')
        
        if not new_role or new_role not in ['admin', 'student']:
            return func.HttpResponse(
                json.dumps({"error": "Valid role is required (admin or student)"}),
                status_code=400,
                mimetype="application/json"
            )
        
        logging.info(f"Updating user {user_id} to role: {new_role}")
        
        # Update user role in MongoDB
        result = users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "role": new_role,
                    "updatedAt": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            # Check if user exists
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return func.HttpResponse(
                    json.dumps({"error": "User not found"}),
                    status_code=404,
                    mimetype="application/json"
                )
            # User exists but role wasn't changed (maybe already had that role)
            logging.info(f"User {user_id} already has role {new_role}")
        
        # Get updated user
        updated_user = users_collection.find_one({"_id": ObjectId(user_id)})
        
        user_response = {
            "_id": str(updated_user["_id"]),
            "username": updated_user.get("username", ""),
            "name": updated_user.get("name"),
            "role": updated_user.get("role", "student")
        }
        
        logging.info(f"Successfully updated user {user_id} to {new_role}")
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "user": user_response
            }),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logging.error(f"Error updating user: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Failed to update user: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )