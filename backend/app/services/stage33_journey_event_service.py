from __future__ import annotations

from typing import Any

from loguru import logger

from app.config import settings
from app.core.event_bus import event_bus_reliable
from app.core.metrics import AURORA_STAGE33_FALLBACK_TOTAL
from app.services.aurora_stage33_kill_switch_service import AuroraStage33KillSwitchService


class Stage33JourneyEventService:
    @staticmethod
    async def publish(
        event_type: str,
        payload: dict[str, Any],
    ) -> str | None:
        try:
            events_mode = str((await AuroraStage33KillSwitchService().summary()).get("events") or "off").strip().lower()
        except Exception as exc:
            logger.warning("Stage33 events kill switch lookup failed: {}", exc)
            AURORA_STAGE33_FALLBACK_TOTAL.labels(feature="events", reason="mode_lookup_failed").inc()
            events_mode = str(getattr(settings, "AURORA_STAGE33_EVENTS_MODE", "off") or "off").strip().lower()

        if events_mode not in {"shadow", "live"}:
            AURORA_STAGE33_FALLBACK_TOTAL.labels(feature="events", reason="off").inc()
            return None

        message = dict(payload or {})
        message["event_type"] = event_type
        metadata = message.get("metadata")
        metadata = dict(metadata) if isinstance(metadata, dict) else {}
        metadata.setdefault("stage", "stage33")
        metadata.setdefault("stage33_mode", events_mode)
        message["metadata"] = metadata
        message["stage33_mode"] = events_mode
        return await event_bus_reliable.publish(event_type, message)
