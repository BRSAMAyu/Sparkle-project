from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from app.services.scene_consolidation_service import SceneConsolidationService
from tests.unit.scene_test_helpers import make_memory


@pytest.mark.asyncio
async def test_scene_kill_switch_defaults_to_off() -> None:
    service = AuroraStage26SceneKillSwitchService()
    await service.reset_quality_streak()
    await service.set_mode("off")
    mode = await service.get_mode()
    assert mode == "off"


@pytest.mark.asyncio
async def test_scene_kill_switch_round_trips_modes() -> None:
    service = AuroraStage26SceneKillSwitchService()

    assert await service.set_mode("live") == "live"
    assert await service.get_mode() == "live"
    assert await service.set_mode("shadow") == "shadow"
    assert await service.set_mode("off") == "off"


@pytest.mark.asyncio
async def test_scene_consolidation_stops_when_mode_is_off(db_session) -> None:
    user_id = uuid4()
    memory = make_memory(
        user_id=user_id,
        summary="不开启 scene",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[0.8, 0.2],
    )
    db_session.add(memory)
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("off")

    result = await SceneConsolidationService(db_session).consolidate_memory(memory)

    assert result.action == "disabled"
    assert result.scene is None
