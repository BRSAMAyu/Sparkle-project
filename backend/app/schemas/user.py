"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

User Schemas - Registration, login, profile, etc.
"""

from __future__ import annotations
import enum


# Python 3.9 compatible StrEnum
class StrEnum(str, enum.Enum):
    """String enum for Python 3.9 compatibility"""
    def __new__(cls, value):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj


from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

# ========== Request Schemas ==========

class UserStatusEnum(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    INVISIBLE = "invisible"


class AvatarStatus(StrEnum):
    """头像审核状态"""
    APPROVED = "approved"   # 审核通过
    PENDING = "pending"     # 待审核
    REJECTED = "rejected"   # 审核驳回


class UserRegister(BaseModel):
    """User registration"""
    username: str = Field(min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(description="Email")
    password: str = Field(min_length=6, max_length=100, description="Password")
    nickname: str | None = Field(default=None, max_length=100, description="Nickname")
    accepted_tos: bool = Field(default=False, description="Accepted terms of service")
    accepted_privacy: bool = Field(default=False, description="Accepted privacy policy")
    tos_version: str | None = Field(default="v1", description="Terms version")
    privacy_version: str | None = Field(default="v1", description="Privacy version")
    agreed_locale: str | None = Field(default=None, description="Locale for agreement")

class UserLogin(BaseModel):
    """User login"""
    username: str | None = Field(default=None, description="Username")
    email: EmailStr | None = Field(default=None, description="Email")
    password: str = Field(description="Password")

    @model_validator(mode="after")
    def _validate_identifier(self):
        if not self.username and not self.email:
            raise ValueError("username or email is required")
        return self

class UserUpdate(BaseModel):
    """User information update"""
    nickname: str | None = Field(default=None, max_length=100, description="Nickname")
    email: EmailStr | None = Field(default=None, description="Email")
    avatar_url: str | None = Field(default=None, max_length=500, description="Avatar URL")
    avatar_status: AvatarStatus | None = Field(default=None, description="Avatar audit status")
    pending_avatar_url: str | None = Field(default=None, max_length=500, description="Pending Avatar URL")
    depth_preference: float | None = Field(default=None, ge=0.0, le=1.0, description="Depth preference")
    curiosity_preference: float | None = Field(default=None, ge=0.0, le=1.0, description="Curiosity preference")
    status: UserStatusEnum | None = Field(default=None, description="Status update") # Allow update here too?
    equipped_skin: str | None = Field(default=None, max_length=50, description="Equipped skin ID")
    equipped_title: str | None = Field(default=None, max_length=50, description="Equipped title ID")

class PasswordChange(BaseModel):
    """Password change"""
    old_password: str = Field(description="Old password")
    new_password: str = Field(min_length=6, max_length=100, description="New password")

class SetPasswordRequest(BaseModel):
    """Set password (no old password)"""
    new_password: str = Field(min_length=6, max_length=100, description="New password")


class DeleteAccountRequest(BaseModel):
    """Delete account request with re-authentication."""
    confirmation: str = Field(description="Type DELETE to confirm")
    password: str | None = Field(default=None, description="Current password")
    provider: str | None = Field(default=None, description="google|apple|wechat")
    provider_token: str | None = Field(default=None, description="Fresh social provider token")

class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(description="Refresh token")

class LogoutRequest(BaseModel):
    """Logout request (refresh token optional)"""
    refresh_token: str | None = Field(default=None, description="Refresh token")

class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""
    email: EmailStr = Field(description="Email")

class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    token: str = Field(description="Reset token")
    new_password: str = Field(min_length=6, max_length=100, description="New password")

class VerifyEmailRequest(BaseModel):
    """Verify email request"""
    token: str = Field(description="Verification token")


class LinkSocialRequest(BaseModel):
    """Link a social login provider."""
    provider: str = Field(description="Provider (google, apple, wechat)")
    token: str = Field(description="Provider token")
    openid: str | None = Field(default=None, description="WeChat OpenID")


class UnlinkSocialRequest(BaseModel):
    """Unlink a social provider."""
    provider: str = Field(description="Provider (google, apple, wechat)")


class UpgradeGuestRequest(BaseModel):
    """Upgrade guest to full email account."""
    username: str = Field(min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(description="Email")
    password: str = Field(min_length=6, max_length=100, description="Password")
    nickname: str | None = Field(default=None, max_length=100, description="Nickname")
    accepted_tos: bool = Field(default=False, description="Accepted terms of service")
    accepted_privacy: bool = Field(default=False, description="Accepted privacy policy")
    tos_version: str | None = Field(default="v1", description="Terms version")
    privacy_version: str | None = Field(default="v1", description="Privacy version")
    agreed_locale: str | None = Field(default=None, description="Locale for agreement")


class UpgradeGuestSocialRequest(BaseModel):
    """Upgrade guest via social provider."""
    provider: str = Field(description="Provider (google, apple, wechat)")
    token: str = Field(description="Provider token")
    openid: str | None = Field(default=None, description="WeChat OpenID")
    accepted_tos: bool = Field(default=False, description="Accepted terms of service")
    accepted_privacy: bool = Field(default=False, description="Accepted privacy policy")
    tos_version: str | None = Field(default="v1", description="Terms version")
    privacy_version: str | None = Field(default="v1", description="Privacy version")
    agreed_locale: str | None = Field(default=None, description="Locale for agreement")

class SocialLoginRequest(BaseModel):
    """Social login request"""
    provider: str = Field(description="Provider (google, apple, wechat)")
    token: str = Field(description="ID Token or Auth Code")
    openid: str | None = Field(default=None, description="WeChat OpenID")
    email: EmailStr | None = Field(default=None, description="Email (if available)")
    nickname: str | None = Field(default=None, description="Nickname (if available)")
    avatar_url: str | None = Field(default=None, description="Avatar URL (if available)")

# ========== Response Schemas ==========

class UserBase(BaseModel):
    """User basic information"""
    id: UUID = Field(description="User ID")
    username: str = Field(description="Username")
    email: str = Field(description="Email")
    email_verified: bool = Field(default=False, description="Email verified")
    password_login_enabled: bool = Field(default=True, description="Password login enabled")
    nickname: str | None = Field(description="Nickname")
    avatar_url: str | None = Field(description="Avatar URL")
    avatar_status: AvatarStatus = Field(default=AvatarStatus.APPROVED, description="Avatar status")
    pending_avatar_url: str | None = Field(default=None, description="Pending avatar URL")

    model_config = ConfigDict(from_attributes=True)

class UserProfile(UserBase):
    """User detailed information"""
    flame_level: int = Field(description="Flame level")
    flame_brightness: float = Field(description="Flame brightness")
    depth_preference: float = Field(description="Depth preference")
    curiosity_preference: float = Field(description="Curiosity preference")
    is_active: bool = Field(description="Is active")
    status: UserStatusEnum = Field(default=UserStatusEnum.OFFLINE, description="Status")
    created_at: datetime = Field(description="Registration time")
    updated_at: datetime = Field(description="Last update time")
    photon_balance: int = Field(default=0, description="Photon balance")
    equipped_skin: str | None = Field(default=None, description="Equipped skin ID")
    equipped_skin_source: str | None = Field(default=None, description="Equipped skin source")
    equipped_title: str | None = Field(default=None, description="Equipped title ID")
    equipped_title_source: str | None = Field(default=None, description="Equipped title source")
    push_preferences: Optional["PushPreferenceResponse"] = Field(default=None, description="Push notification preferences")
    registration_source: str | None = Field(default=None, description="Registration source")
    linked_providers: list[str] = Field(default_factory=list, description="Linked social providers")
    tos_version: str | None = Field(default=None, description="Accepted terms version")
    privacy_version: str | None = Field(default=None, description="Accepted privacy version")


class SocialAccountStatus(BaseModel):
    """Social provider linked status."""
    provider: str = Field(description="Provider")
    linked: bool = Field(description="Whether linked")


class UserSessionInfo(BaseModel):
    """Active login session info."""
    session_id: str = Field(description="Session ID")
    device_id: str | None = Field(default=None, description="Device ID")
    device_name: str | None = Field(default=None, description="Device name")
    device_type: str | None = Field(default=None, description="Device type")
    ip_address: str | None = Field(default=None, description="IP address")
    user_agent: str | None = Field(default=None, description="User agent")
    is_active: bool = Field(description="Whether session is active")
    is_current: bool = Field(default=False, description="Whether current session")
    created_at: datetime = Field(description="Created at")
    last_active_at: datetime = Field(description="Last active at")


class AuthAuditLogInfo(BaseModel):
    """Security log item for the current user."""
    action: str = Field(description="Action")
    ip_address: str | None = Field(default=None, description="IP address")
    user_agent: str | None = Field(default=None, description="User agent")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")
    occurred_at: datetime = Field(description="Occurred at")

class UserFlameStatus(BaseModel):
    """User flame status"""
    user_id: UUID = Field(description="User ID")
    flame_level: int = Field(description="Flame level")
    flame_brightness: float = Field(description="Flame brightness")
    days_streak: int = Field(description="Consecutive days")
    total_completed_tasks: int = Field(description="Total completed tasks")

    model_config = ConfigDict(from_attributes=True)

class UserPreferences(BaseModel):
    """User preferences"""
    learning_depth: float = Field(description="Learning depth preference (0-1)")
    curiosity_level: float = Field(description="Curiosity preference (0-1)")
    schedule_preferences: dict[str, Any] | None = Field(default=None, description="Active time slots")
    weather_preferences: dict[str, Any] | None = Field(default=None, description="Weather mapping preferences")
    notification_enabled: bool = Field(default=True, description="Whether notifications are enabled")
    persona_type: str = Field(default="coach", description="AI persona type (coach, anime, etc.)")
    daily_cap: int = Field(default=5, description="Daily interaction cap")

    model_config = ConfigDict(from_attributes=True)


class PushPreferenceUpdate(BaseModel):
    """Push preference update request"""
    enable_curiosity: bool | None = Field(default=None, description="Enable curiosity-based push notifications")
    persona_type: str | None = Field(default=None, description="AI persona type (coach, anime, mentor, friend)")
    daily_cap: int | None = Field(default=None, ge=1, le=20, description="Daily push notification cap")
    active_slots: list[dict[str, str]] | None = Field(default=None, description="Active time slots [{'start': '08:00', 'end': '09:00'}]")
    timezone: str | None = Field(default=None, description="User timezone")


class PushPreferenceResponse(BaseModel):
    """Push preference response"""
    enable_curiosity: bool = Field(description="Enable curiosity-based push notifications")
    persona_type: str = Field(description="AI persona type")
    daily_cap: int = Field(description="Daily push notification cap")
    active_slots: list[dict[str, str]] | None = Field(default=None, description="Active time slots")
    timezone: str = Field(description="User timezone")

    model_config = ConfigDict(from_attributes=True)


class UserContext(BaseModel):
    """User context for LLM prompts"""
    user_id: str = Field(description="User ID string")
    nickname: str = Field(description="User nickname")
    timezone: str = Field(default="Asia/Shanghai", description="User timezone")
    language: str = Field(default="zh-CN", description="User language")
    is_pro: bool = Field(default=False, description="Whether user is Pro")
    preferences: dict[str, Any] = Field(default_factory=dict, description="Core preferences")
    active_slots: dict[str, Any] | None = Field(default=None, description="Active time slots")
    daily_cap: int = Field(default=5, description="Daily interaction cap")
    persona_type: str = Field(default="coach", description="AI persona type")
    preference_version: int = Field(default=0, description="Preference version for cache validation")
    active_goals: list[dict[str, Any]] = Field(default_factory=list, description="Top-level active goals for prompt render")
    episodic_memories: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Top-level episodic memory summaries for prompt render",
    )

    model_config = ConfigDict(from_attributes=True)
