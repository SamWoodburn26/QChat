"""
User Model for QChat
To use user data in MongoDB in a type-safe manner in Python
To add the role field (student/admin)
"""

from typing import Optional, Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_core import core_schema
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom type for MongoDB ObjectId - Pydantic v2 compatible"""
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler):
        """Pydantic v2 schema definition"""
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.validate),
            ])
        ],
        serialization=core_schema.plain_serializer_function_ser_schema(
            lambda x: str(x)
        ))
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class UserBase(BaseModel):
    """Common fields for all users"""
    username: str  # Email or name
    role: Literal["student", "admin"] = "student"  # Default: student


class UserCreate(UserBase):
    """Model used when creating a new user"""
    name: Optional[str] = None  # Full name
    password: Optional[str] = None  # Password for login
    UserId: Optional[str] = None  # Student ID number
    authProvider: Optional[Literal["google", "microsoft"]] = None  # OAuth provider


class UserInDB(UserBase):
    """
    The actual user document in MongoDB
    All your fields are here
    """
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    
    # Your current MongoDB fields:
    name: Optional[str] = None  # Full name
    password: Optional[str] = None  # Hashed password
    UserId: Optional[str] = None  # Student ID
    authProvider: Optional[str] = None  # OAuth provider
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    lastLogin: Optional[datetime] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }

    def is_admin(self) -> bool:
        """Admin control"""
        return self.role == "admin"


class UserResponse(BaseModel):
    """
    API response - To be sent to the frontend
    No sensitive data (no password)
    """
    id: str = Field(alias="_id")  # MongoDB _id as string
    username: str
    name: Optional[str] = None
    role: str
    is_admin: bool
    createdAt: datetime
    lastLogin: Optional[datetime] = None

    model_config = {
        "populate_by_name": True
    }


class UserUpdate(BaseModel):
    """Fields that can be updated"""
    role: Optional[Literal["student", "admin"]] = None
    lastLogin: Optional[datetime] = None