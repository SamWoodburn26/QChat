"""
User Profile Service - Manages student profiles and personalization data.

This module handles:
- Creating and retrieving user profiles
- Storing student information (schedule, classes, preferences)
- Privacy enforcement (profiles are tied to user accounts)
- Adaptive learning about students
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import certifi
import os

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGODB_URI') or os.getenv('MONGODB_URI')
DATABASE_NAME = os.environ.get('DB_NAME', 'qchat')
PROFILES_COLLECTION = 'user_profiles'

# Singleton DB connection
_mongo_client = None
_db = None


def _get_db():
    """Get or initialize MongoDB connection."""
    global _mongo_client, _db
    if _db is None and MONGO_URI:
        try:
            mongo_kwargs = {
                "serverSelectionTimeoutMS": 3000,
                "connectTimeoutMS": 3000,
                "socketTimeoutMS": 3000,
            }
            if MONGO_URI.startswith("mongodb+srv") or "mongodb.net" in MONGO_URI:
                mongo_kwargs["tls"] = True
                mongo_kwargs["tlsCAFile"] = certifi.where()
            _mongo_client = MongoClient(MONGO_URI, **mongo_kwargs)
            _mongo_client.admin.command("ping")
            _db = _mongo_client[DATABASE_NAME]
            
            # Ensure username index for fast lookups and uniqueness
            _db[PROFILES_COLLECTION].create_index("username", unique=True)
            print(f"Profile service connected to MongoDB: {DATABASE_NAME}")
        except Exception as e:
            print(f"Profile service MongoDB connection error: {repr(e)}")
            _mongo_client = None
            _db = None
    return _db


def get_user_profile(username: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user's profile by username.
    
    Args:
        username: The username to look up (case-sensitive)
        
    Returns:
        User profile dict if found, None if not found or on error
    """
    if not username:
        return None
        
    db = _get_db()
    if db is None:
        print("Cannot retrieve profile - DB not available")
        return None
        
    try:
        profile = db[PROFILES_COLLECTION].find_one({"username": username})
        if profile:
            # Remove MongoDB _id from returned data
            profile.pop('_id', None)
        return profile
    except Exception as e:
        print(f"Error retrieving profile for {username}: {repr(e)}")
        return None


def create_user_profile(username: str) -> Dict[str, Any]:
    """
    Create a new user profile with default structure.
    
    Args:
        username: The username for the new profile
        
    Returns:
        The created profile dict
        
    Raises:
        ValueError: If profile already exists
    """
    if not username:
        raise ValueError("Username is required")
        
    db = _get_db()
    if db is None:
        raise RuntimeError("Database not available")
        
    profile = {
        "username": username,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "personal_info": {
            "name": None,
            "year": None,  # freshman, sophomore, junior, senior, grad
            "major": None,
            "minor": None,
        },
        "schedule": {
            "classes": [],  # List of class objects
            "study_times": [],  # Preferred study times
            "extracurriculars": [],  # Clubs, sports, etc.
        },
        "preferences": {
            "favorite_dining_halls": [],
            "dietary_restrictions": [],
            "study_locations": [],
            "topics_of_interest": [],
        },
        "academic": {
            "advisor": None,
            "gpa": None,
            "dean_list": False,
        },
        "notes": [],  # Free-form notes the bot learns about the user
    }
    
    try:
        result = db[PROFILES_COLLECTION].insert_one(profile)
        profile['_id'] = result.inserted_id
        profile.pop('_id', None)  # Remove before returning
        print(f"Created profile for user: {username}")
        return profile
    except DuplicateKeyError:
        raise ValueError(f"Profile already exists for user: {username}")
    except Exception as e:
        print(f"Error creating profile for {username}: {repr(e)}")
        raise


def update_user_profile(username: str, updates: Dict[str, Any]) -> bool:
    """
    Update a user's profile with new information.
    
    Args:
        username: The username to update
        updates: Dict of fields to update (supports nested updates)
        
    Returns:
        True if updated successfully, False otherwise
    """
    if not username or not updates:
        return False
        
    db = _get_db()
    if db is None:
        print("Cannot update profile - DB not available")
        return False
        
    try:
        # Always update the timestamp
        updates['updated_at'] = datetime.utcnow()
        
        result = db[PROFILES_COLLECTION].update_one(
            {"username": username},
            {"$set": updates}
        )
        
        if result.matched_count > 0:
            print(f"Updated profile for {username}")
            return True
        else:
            print(f"No profile found for {username} to update")
            return False
    except Exception as e:
        print(f"Error updating profile for {username}: {repr(e)}")
        return False


def add_to_profile_array(username: str, field_path: str, value: Any) -> bool:
    """
    Add an item to an array field in the user's profile.
    
    Args:
        username: The username to update
        field_path: Dot-notation path to the array (e.g., 'schedule.classes')
        value: The value to append to the array
        
    Returns:
        True if added successfully, False otherwise
    """
    if not username or not field_path:
        return False
        
    db = _get_db()
    if db is None:
        return False
        
    try:
        result = db[PROFILES_COLLECTION].update_one(
            {"username": username},
            {
                "$addToSet": {field_path: value},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.matched_count > 0
    except Exception as e:
        print(f"Error adding to array for {username}: {repr(e)}")
        return False


def add_note_to_profile(username: str, note: str) -> bool:
    """
    Add a learning note about the user.
    
    Args:
        username: The username
        note: The note to add (what the bot learned)
        
    Returns:
        True if added successfully, False otherwise
    """
    if not username or not note:
        return False
        
    note_obj = {
        "text": note,
        "timestamp": datetime.utcnow()
    }
    
    return add_to_profile_array(username, "notes", note_obj)


def get_profile_context(username: str) -> str:
    """
    Generate a context string from user profile for RAG prompts.
    
    Args:
        username: The username to get context for
        
    Returns:
        Formatted string containing relevant user context
    """
    profile = get_user_profile(username)
    if not profile:
        return ""
    
    context_parts = []
    
    # Personal info
    personal = profile.get('personal_info', {})
    if personal.get('name'):
        context_parts.append(f"Student name: {personal['name']}")
    if personal.get('year'):
        context_parts.append(f"Year: {personal['year']}")
    if personal.get('major'):
        context_parts.append(f"Major: {personal['major']}")
    if personal.get('minor'):
        context_parts.append(f"Minor: {personal['minor']}")
    
    # Schedule and classes
    schedule = profile.get('schedule', {})
    classes = schedule.get('classes', [])
    if classes:
        class_list = ", ".join([c.get('name', '') for c in classes if c.get('name')])
        if class_list:
            context_parts.append(f"Current classes: {class_list}")
    
    extracurriculars = schedule.get('extracurriculars', [])
    if extracurriculars:
        context_parts.append(f"Activities: {', '.join(extracurriculars)}")
    
    # Preferences
    prefs = profile.get('preferences', {})
    if prefs.get('favorite_dining_halls'):
        context_parts.append(f"Favorite dining: {', '.join(prefs['favorite_dining_halls'])}")
    if prefs.get('dietary_restrictions'):
        context_parts.append(f"Dietary needs: {', '.join(prefs['dietary_restrictions'])}")
    
    # Recent notes (last 5)
    notes = profile.get('notes', [])
    if notes:
        recent_notes = sorted(notes, key=lambda x: x.get('timestamp', datetime.min), reverse=True)[:5]
        for note in recent_notes:
            context_parts.append(f"Note: {note.get('text', '')}")
    
    if context_parts:
        return "USER PROFILE INFORMATION:\n" + "\n".join(context_parts)
    return ""


def ensure_profile_exists(username: str) -> Dict[str, Any]:
    """
    Get or create a user profile.
    
    Args:
        username: The username
        
    Returns:
        The user's profile
    """
    profile = get_user_profile(username)
    if profile is None:
        try:
            profile = create_user_profile(username)
        except ValueError:
            # Race condition - profile was just created
            profile = get_user_profile(username)
    return profile
