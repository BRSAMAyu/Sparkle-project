"""
Compliance Models
合规与审计相关模型 (V3.1)
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel, GUID


class LegalHold(BaseModel):
    """
    法律冻结标记
    """
    __tablename__ = "legal_holds"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    device_id = Column(String(128), nullable=True, index=True)
    case_ref = Column(String(120), nullable=False, index=True)
    reason = Column(Text, nullable=True)

    admin_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    released_at = Column(DateTime, nullable=True)
    released_by = Column(GUID(), ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    admin = relationship("User", foreign_keys=[admin_id])
    releaser = relationship("User", foreign_keys=[released_by])


class UserPersonaKey(BaseModel):
    """
    用户画像加密密钥表
    """
    __tablename__ = "user_persona_keys"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_id = Column(String(128), nullable=False, index=True)
    encrypted_key = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    destroyed_at = Column(DateTime, nullable=True)

    user = relationship("User")


class CryptoShreddingCertificate(BaseModel):
    """
    加密抹除存证
    """
    __tablename__ = "crypto_shredding_certificates"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_id = Column(String(128), nullable=False)
    destruction_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    cloud_provider_ack = Column(Text, nullable=True)
    certificate_data = Column(JSONB, nullable=True)

    user = relationship("User")


class DlqReplayAuditLog(BaseModel):
    """
    DLQ 重放审计日志 (双人复核)
    """
    __tablename__ = "dlq_replay_audit_logs"

    message_id = Column(String(128), nullable=False, index=True)
    admin_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    approver_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    reason_code = Column(String(64), nullable=False)
    payload_hash = Column(String(128), nullable=False)

    admin = relationship("User", foreign_keys=[admin_id])
    approver = relationship("User", foreign_keys=[approver_id])


class PersonaSnapshot(BaseModel):
    """
    画像快照 (用于回滚与审计)
    """
    __tablename__ = "persona_snapshots"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_version = Column(String(50), nullable=False, index=True)
    audit_token = Column(String(128), nullable=True, index=True)
    source_event_id = Column(String(64), nullable=True, index=True)
    snapshot_data = Column(JSONB, nullable=False)

    user = relationship("User")
