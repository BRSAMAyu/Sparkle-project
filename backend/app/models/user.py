"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

用户模型
User Model - 核心用户信息和个性化偏好
"""

from __future__ import annotations

import enum


# Python 3.9 compatible StrEnum
class StrEnum(enum.StrEnum):
    """String enum for Python 3.9 compatibility"""
    def __new__(cls, value):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj


from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

# 导出 SearchVisibility 供其他模块使用
__all__ = ['UserStatus', 'AvatarStatus', 'SearchVisibility', 'User', 'PushPreference', 'UserDevice', 'LoginAttempt']


class UserStatus(StrEnum):
    """用户在线状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    INVISIBLE = "invisible"


class AvatarStatus(StrEnum):
    """头像审核状态"""
    APPROVED = "approved"   # 审核通过
    PENDING = "pending"     # 待审核
    REJECTED = "rejected"   # 审核驳回


class SearchVisibility(StrEnum):
    """用户搜索可见性设置"""
    EVERYONE = "everyone"   # 所有人可搜索
    FRIENDS = "friends"     # 仅好友可搜索
    NOBODY = "nobody"       # 不可搜索


class User(BaseModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    password_login_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=True)
    nickname: Mapped[str] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)

    # 头像审核系统
    avatar_status: Mapped[AvatarStatus] = mapped_column(Enum(AvatarStatus), default=AvatarStatus.APPROVED, nullable=False)
    pending_avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)

    # 火花系统
    flame_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    flame_brightness: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    # 🆕 权益分层 (V3-FIX-02 / D17 冻结决策)：独立字段，'free' | 'pro'。
    # 禁止用 flame_level 派生权益 —— 权益唯一判据是本列。
    entitlement: Mapped[str] = mapped_column(String(32), default="free", nullable=False, server_default="free")

    # 🆕 权益到期时间 (D-REDEEM)：NULL = 永久（存量行/手工授予的既有语义，零变化）。
    # 非空且已过 → 有效判级降为 free（到期降级，宁降不升；判级真源
    # app/core/entitlement.entitlement_effective，网关同语义
    # IsProEntitlementEffective）。兑换码核销是唯一写本列的业务路径。
    entitlement_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 用户偏好
    depth_preference: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    curiosity_preference: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    # 🆕 碎片时间/日程偏好 {"commute_time": ["08:00", "09:00"], "lunch_break": ...}
    schedule_preferences: Mapped[Any] = mapped_column(JSON, nullable=True)  # Deprecated: Use PushPreference instead

    # 🆕 天气映射偏好 (v2.3)
    weather_preferences: Mapped[Any] = mapped_column(JSON, nullable=True)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.OFFLINE, nullable=False)

    # 🆕 社交登录 ID (encrypted at rest via pii_encryption_listeners)
    google_id: Mapped[str] = mapped_column(String(512), unique=True, nullable=True, index=True)
    google_id_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    apple_id: Mapped[str] = mapped_column(String(512), unique=True, nullable=True, index=True)
    apple_id_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    wechat_unionid: Mapped[str] = mapped_column(String(512), unique=True, nullable=True, index=True)
    wechat_unionid_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    # Hash columns for deterministic lookup (P1-1: field-level encryption)
    username_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    # 🆕 注册来源 (analytics)
    registration_source: Mapped[str] = mapped_column(String(50), default="email", nullable=False) # email, google, apple, wechat
    last_login_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    token_revoked_before: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    agreed_to_tos_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    agreed_to_privacy_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    tos_version: Mapped[str] = mapped_column(String(50), nullable=True)
    privacy_version: Mapped[str] = mapped_column(String(50), nullable=True)
    agreed_locale: Mapped[str] = mapped_column(String(20), nullable=True)

    # 🆕 年龄校验 (V3.1)
    is_minor: Mapped[bool] = mapped_column(Boolean, nullable=True)  # None = unknown, True/False = verified
    age_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    age_verification_source: Mapped[str] = mapped_column(String(50), nullable=True)  # registration, parent_consent, device_mode
    age_verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 🆕 光子积分系统 (V3.2)
    photon_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 光子积分余额
    photon_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # 光子积分最后更新时间

    # 🆕 商城装备系统 (V3.2)
    equipped_skin: Mapped[str] = mapped_column(String(50), nullable=True, index=True)  # 当前装备的皮肤ID（按来源命名空间解释）
    equipped_skin_source: Mapped[str] = mapped_column(String(20), nullable=True, index=True)  # achievement | shop
    equipped_title: Mapped[str] = mapped_column(String(50), nullable=True, index=True)  # 当前装备的称号ID（按来源命名空间解释）
    equipped_title_source: Mapped[str] = mapped_column(String(20), nullable=True, index=True)  # achievement | shop

    # 🆕 社群隐私设置 (V3.3)
    searchable_by: Mapped[SearchVisibility] = mapped_column(
        Enum(
            SearchVisibility,
            name="searchvisibility",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=SearchVisibility.EVERYONE,
        nullable=False,
    )

    # 关系定义
    push_preference = relationship(
        "PushPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined"
    )

    intervention_settings = relationship(
        "UserInterventionSettings",
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

    chat_sessions = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    intervention_requests = relationship(
        "InterventionRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    intervention_feedback = relationship(
        "InterventionFeedback",
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

    # 胶囊反馈关系
    capsule_feedbacks = relationship(
        "CapsuleFeedback",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # 任务反馈关系
    task_feedbacks = relationship(
        "TaskFeedback",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # 胶囊收藏关系
    capsule_favorites = relationship(
        "CapsuleFavorite",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # 胶囊生成任务关系
    capsule_generation_jobs = relationship(
        "CapsuleGenerationJob",
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

    # 🛒 商城系统关系 (v3.2)
    shop_purchases = relationship(
        "ShopPurchase",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    consumables = relationship(
        "UserConsumable",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    photon_transactions = relationship(
        "PhotonTransactionHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="desc(PhotonTransactionHistory.created_at)"
    )

    candidate_feedbacks = relationship(
        "CandidateActionFeedback",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<User(username={self.username}, email={self.email})>"


class PushPreference(BaseModel):
    """
    用户推送偏好设置 (v2.0)
    """
    __tablename__ = "push_preferences"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # 活跃时间段 [{"start": "08:00", "end": "09:00"}]
    active_slots: Mapped[Any] = mapped_column(JSON, nullable=True)

    # 时区
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai", nullable=False)

    # 开关和配置
    enable_curiosity: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    persona_type: Mapped[str] = mapped_column(String(50), default="coach", nullable=False) # coach, anime

    # 频控
    daily_cap: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    last_push_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    consecutive_ignores: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 关系
    user = relationship("User", back_populates="push_preference")

    def __repr__(self):
        return f"<PushPreference(user_id={self.user_id}, timezone={self.timezone})>"


class UserDevice(BaseModel):
    """
    用户设备令牌表 (v3.2)
    用于推送通知和离线消息推送
    """
    __tablename__ = "user_devices"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 设备标识
    device_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # 设备唯一标识
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # ios, android, web

    # 推送令牌 (encrypted at rest via pii_encryption_listeners)
    push_token: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)  # FCM/APNs token
    push_token_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    token_type: Mapped[str] = mapped_column(String(50), nullable=False)  # fcm, apns, huawei

    # 设备信息
    device_name: Mapped[str] = mapped_column(String(100), nullable=True)  # iPhone 14 Pro, Xiaomi 13, etc.
    app_version: Mapped[str] = mapped_column(String(50), nullable=True)  # 应用版本
    os_version: Mapped[str] = mapped_column(String(50), nullable=True)  # iOS 17.0, Android 14, etc.

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # 令牌是否有效
    last_used_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # 最后使用时间

    # 元数据 (使用 device_metadata 避免 SQLAlchemy 保留字冲突)
    device_metadata: Mapped[Any] = mapped_column(JSON, nullable=True)  # 额外设备信息

    def __repr__(self):
        return f"<UserDevice(user_id={self.user_id}, platform={self.platform}, is_active={self.is_active})>"


class LoginAttempt(BaseModel):
    """登录尝试记录表"""
    __tablename__ = "login_attempts"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # 尝试登录的用户名
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)  # 支持IPv6
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True)  # 用户代理
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)  # 是否登录成功
    attempted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # 关系
    user = relationship("User", back_populates="login_attempts")

    def __repr__(self):
        return f"<LoginAttempt username={self.username} success={self.success} at={self.attempted_at}>"


# 创建索引
Index("idx_users_username", User.username)
Index("idx_users_email", User.email)
