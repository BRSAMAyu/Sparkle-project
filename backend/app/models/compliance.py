"""
Compliance Models
合规与审计相关模型 (V3.1)
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class LegalHold(BaseModel):
    """
    法律冻结标记
    """
    __tablename__ = "legal_holds"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    device_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    case_ref: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=True)

    admin_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    released_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    released_by: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    admin = relationship("User", foreign_keys=[admin_id])
    releaser = relationship("User", foreign_keys=[released_by])


class UserPersonaKey(BaseModel):
    """
    用户画像加密密钥表
    """
    __tablename__ = "user_persona_keys"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    destroyed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user = relationship("User")


class CryptoShreddingCertificate(BaseModel):
    """
    加密抹除存证
    """
    __tablename__ = "crypto_shredding_certificates"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_id: Mapped[str] = mapped_column(String(128), nullable=False)
    destruction_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    cloud_provider_ack: Mapped[str] = mapped_column(Text, nullable=True)
    certificate_data: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)

    user = relationship("User")


class DlqReplayAuditLog(BaseModel):
    """
    DLQ 重放审计日志 (双人复核)
    """
    __tablename__ = "dlq_replay_audit_logs"

    message_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    admin_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    approver_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    admin = relationship("User", foreign_keys=[admin_id])
    approver = relationship("User", foreign_keys=[approver_id])


class PersonaSnapshot(BaseModel):
    """
    画像快照 (用于回滚与审计)
    """
    __tablename__ = "persona_snapshots"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    audit_token: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    source_event_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    snapshot_data: Mapped[Any] = mapped_column(JSONBCompat, nullable=False)

    user = relationship("User")
