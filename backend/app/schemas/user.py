"""User Schemas - Registration, login, profile, etc."""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID

from app.schemas.common import BaseSchema

# ========== Request Schemas ==========

class UserRegister(BaseModel):
    """User registration"""
    username: str = Field(min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(description="Email")
    password: str = Field(min_length=6, max_length=100, description="Password")
    nickname: Optional[str] = Field(default=None, max_length=100, description="Nickname")

class UserLogin(BaseModel):
    """User login"""
    username: str = Field(description="Username or email")
    password: str = Field(description="Password")

class UserUpdate(BaseModel):
    """User information update"""
    nickname: Optional[str] = Field(default=None, max_length=100, description="Nickname")
    avatar_url: Optional[str] = Field(default=None, max_length=500, description="Avatar URL")
    depth_preference: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Depth preference")
    curiosity_preference: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Curiosity preference")

class PasswordChange(BaseModel):
    """Password change"""
    old_password: str = Field(description="Old password")
    new_password: str = Field(min_length=6, max_length=100, description="New password")

class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(description="Refresh token")

class SocialLoginRequest(BaseModel):
    """Social login request"""
    provider: str = Field(description="Provider (google, apple, wechat)")
    token: str = Field(description="ID Token or Auth Code")
    email: Optional[EmailStr] = Field(default=None, description="Email (if available)")
    nickname: Optional[str] = Field(default=None, description="Nickname (if available)")
    avatar_url: Optional[str] = Field(default=None, description="Avatar URL (if available)")

# ========== Response Schemas ==========

class UserBase(BaseModel):
    """User basic information"""
    id: UUID = Field(description="User ID")
    username: str = Field(description="Username")
    email: str = Field(description="Email")
    nickname: Optional[str] = Field(description="Nickname")
    avatar_url: Optional[str] = Field(description="Avatar URL")

    class Config:
        from_attributes = True

class UserProfile(UserBase):
    """User detailed information"""
    flame_level: int = Field(description="Flame level")
    flame_brightness: float = Field(description="Flame brightness")
    depth_preference: float = Field(description="Depth preference")
    curiosity_preference: float = Field(description="Curiosity preference")
    is_active: bool = Field(description="Is active")
    created_at: str = Field(description="Registration time")

class UserFlameStatus(BaseModel):
    """User flame status"""
    user_id: UUID = Field(description="User ID")
    flame_level: int = Field(description="Flame level")
    flame_brightness: float = Field(description="Flame brightness")
    days_streak: int = Field(description="Consecutive days")
    total_completed_tasks: int = Field(description="Total completed tasks")

    class Config:
        from_attributes = True

class UserPreferences(BaseModel):
    """User preferences"""
    depth_preference: float = Field(description="Depth preference (0-1)")
    curiosity_preference: float = Field(description="Curiosity preference (0-1)")

    class Config:
        from_attributes = True
