from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String

from app.aurora.runtime_v1.models import JSONBCompat
from app.models.base import GUID, BaseModel


class ResearchConsent(BaseModel):
    """Durable research consent state for one user and consent type."""

    __tablename__ = "research_consents"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String(64), nullable=False, index=True)
    granted = Column(Boolean, nullable=False, default=False, index=True)
    granted_at = Column(DateTime, nullable=True, index=True)
    revoked_at = Column(DateTime, nullable=True, index=True)
    version = Column(String(32), nullable=False, default="1.0")
    source = Column(String(64), nullable=False, default="api")
    runtime_metadata = Column("metadata", JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_research_consent_user_type", "user_id", "consent_type", unique=True),
        Index("idx_research_consent_granted_type", "granted", "consent_type"),
    )


class ResearchExportUsage(BaseModel):
    """Research export usage marker that can be revoked after consent changes."""

    __tablename__ = "research_export_usages"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String(64), nullable=False, index=True)
    export_id = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="active", index=True)
    exported_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True, index=True)
    runtime_metadata = Column("metadata", JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_research_export_user_status", "user_id", "status"),
        Index("idx_research_export_consent_status", "consent_type", "status"),
    )
