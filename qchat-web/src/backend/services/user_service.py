"""
User Service - Database Operations
Centralizing database code in one place and making changes easily
"""

from typing import Optional
from datetime import datetime
from bson import ObjectId
from pymongo.collection import Collection
import sys
import os

# For importing from the backend folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import UserCreate, UserInDB, UserUpdate, UserResponse


class UserService:
    """User database operations"""
    
    def __init__(self, users_collection: Collection):
        #Initialize with MongoDB collection
        self.users = users_collection
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        try:
            self.users.create_index("username", unique=True)
            self.users.create_index("UserId", sparse=True)
            self.users.create_index("authProvider", sparse=True)
        except Exception as e:
            print(f"Index creation: {e}")
    
    def create_user(self, user_data: UserCreate, password_hash: Optional[str] = None) -> UserInDB:
        user_dict = {
            "username": user_data.username,
            "name": user_data.name,
            "role": user_data.role,  # Default "student" from model
            "password": password_hash if password_hash else user_data.password,
            "UserId": user_data.UserId,
            "authProvider": user_data.authProvider,
            "createdAt": datetime.utcnow(),
            "lastLogin": datetime.utcnow()
        }
        
        result = self.users.insert_one(user_dict)
        user_dict["_id"] = result.inserted_id
        
        return UserInDB(**user_dict)
    
    def get_by_username(self, username: str) -> Optional[UserInDB]:
        user_doc = self.users.find_one({"username": username})
        return UserInDB(**user_doc) if user_doc else None
    
    def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        try:
            user_doc = self.users.find_one({"_id": ObjectId(user_id)})
            return UserInDB(**user_doc) if user_doc else None
        except Exception:
            return None
    
    def get_by_oauth(self, username: str, provider: str) -> Optional[UserInDB]:
        user_doc = self.users.find_one({
            "username": username,
            "authProvider": provider
        })
        return UserInDB(**user_doc) if user_doc else None
    
    def update_user(self, user_id: str, update_data: UserUpdate) -> bool:
        update_dict = update_data.model_dump(exclude_unset=True)  # Pydantic v2
        
        result = self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict}
        )
        return result.modified_count > 0
    
    def make_admin(self, user_id: str) -> bool:
        return self.update_user(user_id, UserUpdate(role="admin"))
    
    def make_student(self, user_id: str) -> bool:
        return self.update_user(user_id, UserUpdate(role="student"))
    
    def get_all_admins(self) -> list[UserInDB]:
        admin_docs = self.users.find({"role": "admin"})
        return [UserInDB(**doc) for doc in admin_docs]
    
    def user_exists(self, username: str) -> bool:
        return self.users.count_documents({"username": username}) > 0
    
    def update_last_login(self, user_id: str) -> bool:
        result = self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"lastLogin": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    def to_response(self, user: UserInDB) -> dict:
        response = UserResponse(
            _id=str(user.id),
            username=user.username,
            name=user.name,
            role=user.role,
            is_admin=user.is_admin(),
            createdAt=user.createdAt,
            lastLogin=user.lastLogin
        )
        return response.model_dump()  