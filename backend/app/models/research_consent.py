from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.models.base import BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class ResearchConsentRecord(BaseModel):
    """Durable consent ledger for P4 research data usage."""

    __tablename__ = "research_consent_records"

    user_id = Column(String(64), nullable=False, index=True)
    protocol_id = Column(String(64), nullable=False, index=True)
    granted_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True, index=True)
    scope = Column(JSONBCompat, nullable=False, default=list)
    evidence = Column(JSONBCompat, nullable=False, default=dict)
    version = Column(String(32), nullable=False, default="1.0")
    source = Column(String(64), nullable=False, default="api")

    grant_reason = Column(Text, nullable=True)
    grant_initiator = Column(String(16), nullable=False, default="user")
    grant_ip_hash = Column(String(64), nullable=True)
    revoke_reason = Column(Text, nullable=True)
    revoke_initiator = Column(String(16), nullable=True)
    revoke_ip_hash = Column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_research_consent_user_protocol", "user_id", "protocol_id"),
        Index("ix_research_consent_user_active", "user_id", "protocol_id", "revoked_at"),
        Index(
            "uq_research_consent_active_protocol",
            "user_id",
            "protocol_id",
            unique=True,
            postgresql_where=revoked_at.is_(None),
            sqlite_where=revoked_at.is_(None),
        ),
    )
