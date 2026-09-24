"""
Learning Assets Models (学习资产模型)
Represents user's vocabulary, sentences, and concepts collected from translation lookups.
"""
import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel, HardDeleteBaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AssetStatus(enum.StrEnum):
    """Asset lifecycle status (not including deleted - use deleted_at for soft delete)"""
    INBOX = "INBOX"       # Pending user review, auto-expires after 7 days
    ACTIVE = "ACTIVE"     # User confirmed, active for review scheduling
    ARCHIVED = "ARCHIVED"  # User archived or auto-archived from inbox expiry


class AssetKind(enum.StrEnum):
    """Type of learning asset"""
    WORD = "WORD"         # Single word or phrase
    SENTENCE = "SENTENCE"  # Full sentence
    CONCEPT = "CONCEPT"    # Abstract concept or term


class MatchStrength(enum.StrEnum):
    """Provenance match confidence"""
    STRONG = "STRONG"   # >= 0.85 similarity
    WEAK = "WEAK"       # 0.70 - 0.85 similarity
    ORPHAN = "ORPHAN"   # < 0.70 or no document context


class LearningAsset(BaseModel):
    """
    User's learning asset (word, sentence, concept).

    Key design principles:
    - snapshot_json is immutable (captures original context at creation)
    - provenance_json is mutable (can be recalculated for better matching)
    - Core searchable fields are relational, JSONB for extensions
    """
    __tablename__ = "learning_assets"

    # === Foreign Keys ===
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_file_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True, index=True)

    # === Status & Type ===
    status: Mapped[str] = mapped_column(String(20), default=AssetStatus.INBOX.value, nullable=False, index=True)
    asset_kind: Mapped[str] = mapped_column(String(20), default=AssetKind.WORD.value, nullable=False)

    # === Core Content (Relational for Search/Index) ===
    headword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # The primary word/term
    definition: Mapped[str] = mapped_column(Text, nullable=True)  # Definition or meaning
    translation: Mapped[str] = mapped_column(Text, nullable=True)  # Target language translation
    example: Mapped[str] = mapped_column(Text, nullable=True)  # Example sentence
    language_code: Mapped[str] = mapped_column(String(10), default="en", nullable=False)  # Source language

    # === Inbox Decay ===
    inbox_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)  # Auto-archive after this time

    # === Snapshot (Immutable) ===
    snapshot_json: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)  # Original context snapshot
    snapshot_schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # For future migrations

    # === Provenance (Mutable for recalculation) ===
    provenance_json: Mapped[Any] = mapped_column(JSONBCompat, nullable=True, default=dict)  # Match info, source location
    provenance_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # === Fingerprints for Deduplication & Tracing ===
    selection_fp: Mapped[str] = mapped_column(String(64), nullable=True, index=True)  # sha256(normalize(selected_text))
    anchor_fp: Mapped[str] = mapped_column(String(64), nullable=True, index=True)    # sha256(doc_fp + context + page)
    doc_fp: Mapped[str] = mapped_column(String(64), nullable=True)                   # sha256(selection_fp + doc_id)
    norm_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)  # Normalization version
    match_profile: Mapped[str] = mapped_column(String(50), nullable=True)            # Match algorithm used

    # === Review Scheduling (SRS) ===
    review_due_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0.0 - 1.0
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # === Statistics ===
    lookup_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # Times looked up
    star_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)    # User stars/favorites
    ignored_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Times dismissed

    # === Relationships ===
    user = relationship("User")
    source_file = relationship("StoredFile")

    __table_args__ = (
        # Composite index for user asset queries
        Index('idx_learning_assets_user_status', 'user_id', 'status'),
        # Partial index for inbox expiry scan
        Index('idx_learning_assets_inbox_expires', 'inbox_expires_at',
              postgresql_where="status = 'INBOX'"),
        # Partial index for review scheduling
        Index('idx_learning_assets_review_due', 'user_id', 'review_due_at',
              postgresql_where="status = 'ACTIVE' AND review_due_at IS NOT NULL"),
        # Fingerprint deduplication
        Index('idx_learning_assets_selection_fp', 'user_id', 'selection_fp'),
    )

    def is_inbox_expired(self) -> bool:
        """Check if inbox item has expired"""
        if self.status != AssetStatus.INBOX.value:
            return False
        if self.inbox_expires_at is None:
            return False
        return _utcnow() > self.inbox_expires_at

    def activate(self) -> None:
        """Move from INBOX to ACTIVE status"""
        self.status = AssetStatus.ACTIVE.value
        self.inbox_expires_at = None
        self.review_due_at = _utcnow()  # Start review scheduling

    def archive(self) -> None:
        """Archive the asset"""
        self.status = AssetStatus.ARCHIVED.value
        self.inbox_expires_at = None


class SuggestionDecision(enum.StrEnum):
    """Decision made by suggestion system"""
    SUGGESTED = "SUGGESTED"      # Suggestion shown to user
    NOT_SUGGESTED = "NOT_SUGGESTED"  # Suppressed (cooldown, quota, etc.)
    SKIPPED = "SKIPPED"          # Skipped due to conditions not met


class UserSuggestionResponse(enum.StrEnum):
    """User's response to a suggestion"""
    ACCEPT = "ACCEPT"     # User accepted and created asset
    DISMISS = "DISMISS"   # User explicitly dismissed
    IGNORE = "IGNORE"     # User ignored (no action)
    PENDING = "PENDING"   # Awaiting response


class AssetSuggestionLog(HardDeleteBaseModel):
    """
    Suggestion evidence chain and anti-harassment tracking.
    Uses HardDeleteBaseModel as these are append-only audit records.
    """
    __tablename__ = "asset_suggestion_logs"

    # === Context ===
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=True)  # Client session ID
    policy_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # e.g., "repeat_lookup_v1"
    trigger_event: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "translation_lookup"

    # === Evidence ===
    evidence_json: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    # Example: {"fingerprint": "...", "lookup_count": 3, "time_window_seconds": 3600}

    # === Decision ===
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # SUGGESTED / NOT_SUGGESTED / SKIPPED
    decision_reason: Mapped[str] = mapped_column(String(255), nullable=True)  # e.g., "cooldown_active"

    # === User Response ===
    user_response: Mapped[str] = mapped_column(String(20), default=UserSuggestionResponse.PENDING.value, nullable=True)
    response_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # === Cooldown ===
    cooldown_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # If dismissed, cooldown expiry

    # === Reference ===
    asset_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("learning_assets.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index('idx_suggestion_log_user_created', 'user_id', 'created_at'),
        Index('idx_suggestion_log_policy', 'policy_id'),
    )
