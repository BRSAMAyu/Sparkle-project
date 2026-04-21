from __future__ import annotations

from typing import Any
from uuid import UUID

from loguru import logger

from app.core.event_bus import SRLPhaseTransitionEvent, event_bus
from app.core.metrics import SRL_EVENT_PUBLISHED_TOTAL
from app.services.aurora_stage29_srl_kill_switch_service import AuroraStage29SRLKillSwitchService


async def publish_srl_event(
    *,
    user_id: UUID | str,
    trigger_event_type: str,
    evidence_id: str,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    kill_switch = AuroraStage29SRLKillSwitchService()
    if await kill_switch.get_mode() == "off":
        return None
    bridge_mode = await kill_switch.get_bridge_mode()
    if bridge_mode == "off":
        return None

    event = SRLPhaseTransitionEvent(
        user_id=str(user_id),
        trigger_event_type=trigger_event_type,
        evidence_id=evidence_id,
        metadata=metadata or {},
    )
    try:
        SRL_EVENT_PUBLISHED_TOTAL.labels(trigger_event_type=trigger_event_type, mode=bridge_mode).inc()
        return await event_bus.publish("srl.phase.transition", event.to_dict())
    except Exception as exc:
        logger.warning("Failed to publish SRL transition event {}: {}", trigger_event_type, exc)
        return None
