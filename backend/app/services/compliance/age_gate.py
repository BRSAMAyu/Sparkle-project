from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.models.user import User


@dataclass
class AgeGateDecision:
    is_minor: bool | None
    should_collect_sensitive: bool
    source: str | None


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AgeGateService:
    """
    端侧年龄校验与最小化采集策略
    """

    @staticmethod
    def evaluate(user: User, payload: dict[str, Any]) -> AgeGateDecision:
        declared_age = payload.get("declared_age")
        parent_mode = payload.get("parental_control_enabled")
        registration_verified = payload.get("registration_age_verified")

        if registration_verified is True and declared_age is not None:
            is_minor = declared_age < 18
            return AgeGateDecision(
                is_minor=is_minor,
                should_collect_sensitive=not is_minor,
                source="registration"
            )

        if parent_mode is True:
            return AgeGateDecision(
                is_minor=True,
                should_collect_sensitive=False,
                source="device_mode"
            )

        return AgeGateDecision(
            is_minor=user.is_minor if user.is_minor is not None else None,
            should_collect_sensitive=False,
            source=None
        )

    @staticmethod
    def apply_to_user(user: User, decision: AgeGateDecision) -> None:
        if decision.is_minor is None:
            return
        user.is_minor = decision.is_minor
        user.age_verified = True
        user.age_verification_source = decision.source
        user.age_verified_at = _utcnow()



# ═══════════════════════════════════════════════════════════════════════
# GOV-006: Data Deletion Protocol + Legal Hold + Encrypted Erasure
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class DeletionRequest:
    """A user-initiated data deletion request."""
    request_id: str
    user_id: str
    scope: str                # "full" | "selective"
    selected_tables: list[str] | None = None
    reason: str = "user_request"
    legal_hold: bool = False
    status: str = "pending"   # pending | scheduled | processing | completed | blocked_legal_hold
    requested_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "scope": self.scope,
            "selected_tables": self.selected_tables,
            "reason": self.reason,
            "legal_hold": self.legal_hold,
            "status": self.status,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class DataDeletionService:
    """GOV-006: Data deletion, legal hold, and encrypted erasure.

    Protocol:
    1. User requests deletion → check legal hold
    2. If legal hold active → block and notify compliance
    3. Otherwise → schedule encrypted erasure
    4. Erasure: overwrite sensitive fields with hash, then delete rows
    """

    # Tables with user data that must be erased
    USER_DATA_TABLES = [
        "users",
        "user_preferences",
        "chat_messages",
        "plans",
        "tasks",
        "focus_sessions",
        "memory_entries",
        "achievement_progress",
        "galaxy_nodes",
        "user_node_status",
        "error_book_entries",
        "notifications",
    ]

    # Fields that require cryptographic erasure (overwrite before delete)
    SENSITIVE_FIELDS = {
        "users": ["email", "phone", "full_name", "nickname", "avatar_url"],
        "chat_messages": ["content", "metadata"],
    }

    # Minimum retention days for legal compliance
    LEGAL_RETENTION_DAYS = {
        "financial_transactions": 365 * 7,  # 7 years for financial
        "audit_logs": 365,                  # 1 year for audit
    }

    @classmethod
    def create_deletion_request(
        cls,
        *,
        user_id: str,
        scope: str = "full",
        selected_tables: list[str] | None = None,
        reason: str = "user_request",
        legal_hold_active: bool = False,
    ) -> DeletionRequest:
        """Create a data deletion request."""
        import uuid
        request = DeletionRequest(
            request_id=f"del_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            scope=scope,
            selected_tables=selected_tables,
            reason=reason,
            legal_hold=legal_hold_active,
            requested_at=_utcnow(),
        )

        if legal_hold_active:
            request.status = "blocked_legal_hold"
        else:
            request.status = "scheduled"

        return request

    @classmethod
    def get_erasure_tables(
        cls,
        request: DeletionRequest,
    ) -> list[str]:
        """Get the list of tables to erase for this request."""
        if request.scope == "selective" and request.selected_tables:
            return [t for t in request.selected_tables if t in cls.USER_DATA_TABLES]
        return list(cls.USER_DATA_TABLES)

    @classmethod
    def encrypted_erase_field(cls, value: str, *, user_id: str) -> str:
        """Cryptographic erasure: replace value with one-way hash.

        This ensures the original value is irrecoverable even if the
        deletion is interrupted mid-process.
        """
        import hashlib
        return f"ERASED:{hashlib.sha256(f'{user_id}:{value}'.encode()).hexdigest()[:16]}"

    @classmethod
    def check_legal_hold(
        cls,
        user_id: str,
        active_holds: list[str] | None = None,
    ) -> bool:
        """Check if user has an active legal hold blocking deletion."""
        return bool(active_holds and user_id in active_holds)
