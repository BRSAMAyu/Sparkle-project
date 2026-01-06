"""
用户模型
User Model - 核心用户信息和个性化偏好
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Index, JSON, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, GUID


class UserStatus(str, enum.Enum):
    """用户在线状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    INVISIBLE = "invisible"


class AvatarStatus(str, enum.Enum):
    """头像审核状态"""
    APPROVED = "approved"   # 审核通过
    PENDING = "pending"     # 待审核
    REJECTED = "rejected"   # 审核驳回


class User(BaseModel):
    __tablename__ = "users"

    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    nickname = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # 头像审核系统
    avatar_status = Column(Enum(AvatarStatus), default=AvatarStatus.APPROVED, nullable=False)
    pending_avatar_url = Column(String(500), nullable=True)

    # 火花系统
    flame_level = Column(Integer, default=1, nullable=False)
    flame_brightness = Column(Float, default=0.5, nullable=False)

    # 用户偏好
    depth_preference = Column(Float, default=0.5, nullable=False)
    curiosity_preference = Column(Float, default=0.5, nullable=False)
    
    # 🆕 碎片时间/日程偏好 {"commute_time": ["08:00", "09:00"], "lunch_break": ...}
    schedule_preferences = Column(JSON, nullable=True)  # Deprecated: Use PushPreference instead

    # 🆕 天气映射偏好 (v2.3)
    weather_preferences = Column(JSON, nullable=True)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.OFFLINE, nullable=False)

    # 🆕 社交登录 ID
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    apple_id = Column(String(255), unique=True, nullable=True, index=True)
    wechat_unionid = Column(String(255), unique=True, nullable=True, index=True)
    
    # 🆕 注册来源 (analytics)
    registration_source = Column(String(50), default="email", nullable=False) # email, google, apple, wechat
    last_login_at = Column(DateTime, nullable=True)

    # 🆕 年龄校验 (V3.1)
    is_minor = Column(Boolean, nullable=True)  # None = unknown, True/False = verified
    age_verified = Column(Boolean, default=False, nullable=False)
    age_verification_source = Column(String(50), nullable=True)  # registration, parent_consent, device_mode
    age_verified_at = Column(DateTime, nullable=True)

    # 关系定义
    push_preference = relationship(
        "PushPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined"
    )

    tasks = relationship(
        "Task",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    plans = relationship(
        "Plan",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    chat_messages = relationship(
        "ChatMessage",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    token_usage = relationship(
        "TokenUsage",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    error_records = relationship(
        "ErrorRecord",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    curiosity_capsules = relationship(
        "CuriosityCapsule",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # 安全审计日志关系
    security_audit_logs = relationship(
        "SecurityAuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    data_access_logs = relationship(
        "DataAccessLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    system_config_change_logs = relationship(
        "SystemConfigChangeLog",
        back_populates="changer",
        foreign_keys="[SystemConfigChangeLog.changed_by]",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    compliance_check_logs = relationship(
        "ComplianceCheckLog",
        back_populates="executor",
        foreign_keys="[ComplianceCheckLog.executed_by]",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    login_attempts = relationship(
        "LoginAttempt",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<User(username={self.username}, email={self.email})>"


class PushPreference(BaseModel):
    """
    用户推送偏好设置 (v2.0)
    """
    __tablename__ = "push_preferences"

    user_id = Column(GUID(), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # 活跃时间段 [{"start": "08:00", "end": "09:00"}]
    active_slots = Column(JSON, nullable=True)
    
    # 时区
    timezone = Column(String(50), default="Asia/Shanghai", nullable=False)
    
    # 开关和配置
    enable_curiosity = Column(Boolean, default=True, nullable=False)
    persona_type = Column(String(50), default="coach", nullable=False) # coach, anime
    
    # 频控
    daily_cap = Column(Integer, default=5, nullable=False)
    last_push_time = Column(DateTime, nullable=True)
    consecutive_ignores = Column(Integer, default=0, nullable=False)

    # 关系
    user = relationship("User", back_populates="push_preference")

    def __repr__(self):
        return f"<PushPreference(user_id={self.user_id}, timezone={self.timezone})>"


class LoginAttempt(BaseModel):
    """登录尝试记录表"""
    __tablename__ = "login_attempts"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    username = Column(String(100), nullable=False, index=True)  # 尝试登录的用户名
    ip_address = Column(String(45), nullable=False, index=True)  # 支持IPv6
    user_agent = Column(String(500), nullable=True)  # 用户代理
    success = Column(Boolean, nullable=False, index=True)  # 是否登录成功
    attempted_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # 关系
    user = relationship("User", back_populates="login_attempts")

    def __repr__(self):
        return f"<LoginAttempt username={self.username} success={self.success} at={self.attempted_at}>"


# 创建索引
Index("idx_users_username", User.username)
Index("idx_users_email", User.email)
