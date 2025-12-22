"""
用户模型
User Model - 核心用户信息和个性化偏好
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Index, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class User(BaseModel):
    """
    用户模型

    字段:
        username: 用户名
        email: 邮箱
        hashed_password: 加密密码
        nickname: 昵称
        avatar_url: 头像URL
        flame_level: 火花等级 (1-10)
        flame_brightness: 火花亮度 (0-1)
        depth_preference: 深度偏好 (0-1)
        curiosity_preference: 好奇偏好 (0-1)
        is_active: 是否激活

    关系:
        tasks: 用户的所有任务
        plans: 用户的所有计划
        chat_messages: 用户聊天消息
        error_records: 用户错题档案
    """

    __tablename__ = "users"

    # 基本信息
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    nickname = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # 火花系统
    flame_level = Column(Integer, default=1, nullable=False)
    flame_brightness = Column(Float, default=0.5, nullable=False)

    # 用户偏好
    depth_preference = Column(Float, default=0.5, nullable=False)
    curiosity_preference = Column(Float, default=0.5, nullable=False)
    
    # 🆕 碎片时间/日程偏好 {"commute_time": ["08:00", "09:00"], "lunch_break": ...}
    schedule_preferences = Column(JSON, nullable=True)  # Deprecated: Use PushPreference instead

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)

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


# 创建索引
Index("idx_users_username", User.username)
Index("idx_users_email", User.email)
