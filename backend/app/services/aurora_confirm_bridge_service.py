"""
Core: bridge
Phase: relate
Stage: inbox

Aurora confirmation queue -> notification center bridge (B4-INBOX).

The Aurora confirmation queue that SURVIVES a session is the calibration
card lane: visible assumption claims (status=candidate / needs_confirmation)
persisted in the user preference store (``inferred.self_model``).  This
bridge projects those pending cards into the unified notification-center
list (``source_type='aurora_confirm'``) and exposes the unprocessed count
for the inbox badge.

Design constraints:
- Read-only projection: items carry no DB rows of their own; they leave the
  queue when the user responds through the EXISTING confirm API
  (``AuroraCalibrationCardService.respond`` via
  ``POST /aurora/calibration-cards/{card_id}/respond``).  No new write path.
- ``pending_count`` is a no-write lightweight read (skips due-trial
  promotion, which only mutates ``trial`` claims that are never visible in
  the queue anyway) so it is safe for the control-surface hot path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger

from app.schemas.unified_notification import UnifiedNotificationResponse
from app.services.aurora_calibration_card_service import (
    KNOWN_ASSUMPTIONS_KEY,
    SELF_MODEL_KEY,
    AuroraCalibrationCardService,
)

AURORA_CONFIRM_SOURCE_TYPE = "aurora_confirm"
AURORA_CONFIRM_NOTIFICATION_TYPE = "aurora_confirm"

_AURORA_CONFIRM_TITLE_FALLBACK = "Aurora 有一个判断需要你确认"
_AURORA_CONFIRM_CONTENT_FALLBACK = "确认或纠正后，Aurora 会更新对你的理解。"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


class AuroraConfirmBridgeService:
    """Read-only projection of the persisted Aurora confirmation queue."""

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis

    async def pending_cards(
        self,
        *,
        user_id: UUID,
        plan_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Pending confirmation cards, identical to the calibration sheet
        surface (reuses ``AuroraCalibrationCardService.list_cards`` verbatim)."""
        try:
            service = AuroraCalibrationCardService(self.db, self.redis)
            surface = await service.list_cards(user_id=user_id, plan_id=plan_id)
        except Exception as exc:
            logger.warning("Aurora confirm bridge: list_cards unavailable: {}", exc)
            return []
        items = surface.get("items") if isinstance(surface, dict) else None
        if not isinstance(items, list):
            return []
        return [dict(item) for item in items if isinstance(item, dict) and str(item.get("id") or "").strip()]

    async def pending_count(self, *, user_id: UUID) -> int:
        """Uncapped unprocessed-confirmation count (no-write read)."""
        try:
            inferred = await self._load_inferred(user_id)
            return self.count_visible_from_inferred(inferred)
        except Exception as exc:
            logger.warning("Aurora confirm bridge: pending_count unavailable: {}", exc)
            return 0

    async def _load_inferred(self, user_id: UUID) -> dict[str, Any]:
        from app.services.personalization.preference_service import PreferenceService

        prefs = await PreferenceService(self.db, self.redis).get_preferences(user_id)
        return dict(getattr(prefs, "inferred", None) or {})

    @staticmethod
    def count_visible_from_inferred(inferred: dict[str, Any]) -> int:
        """Count queue-visible assumptions straight from the preference payload.

        Mirrors ``AuroraCalibrationCardService._is_visible_assumption`` so the
        count matches the calibration sheet / notification-center items without
        the MAX_VISIBLE_CARDS display cap (badge shows the true backlog).
        """
        self_model = AuroraCalibrationCardService._get_self_model(dict(inferred or {}))
        assumptions = self_model.get(KNOWN_ASSUMPTIONS_KEY)
        if not isinstance(assumptions, list):
            return 0
        return sum(
            1
            for item in assumptions
            if isinstance(item, dict)
            and str(item.get("id") or "").strip()
            and AuroraCalibrationCardService._is_visible_assumption(item)
        )

    def to_unified(self, card: dict[str, Any]) -> UnifiedNotificationResponse:
        """Project one pending card into the unified notification format."""
        observed_at = _parse_iso(card.get("last_observed_at")) or _utcnow()
        needs_confirmation = bool(card.get("needs_confirmation"))
        return UnifiedNotificationResponse(
            id=str(card.get("id")),
            source_type=AURORA_CONFIRM_SOURCE_TYPE,
            title=str(card.get("title") or "").strip() or _AURORA_CONFIRM_TITLE_FALLBACK,
            content=str(card.get("statement") or "").strip() or _AURORA_CONFIRM_CONTENT_FALLBACK,
            type=AURORA_CONFIRM_NOTIFICATION_TYPE,
            priority="high" if needs_confirmation else "medium",
            is_read=False,
            created_at=observed_at,
            read_at=None,
            metadata={
                "kind": AURORA_CONFIRM_NOTIFICATION_TYPE,
                "needs_confirmation": needs_confirmation,
                "confidence": card.get("confidence"),
                "confidence_label": card.get("confidence_label"),
                "evidence_summary": card.get("evidence_summary"),
                "status": card.get("status"),
                "plan_id": card.get("plan_id"),
                "source": card.get("source"),
            },
        )
