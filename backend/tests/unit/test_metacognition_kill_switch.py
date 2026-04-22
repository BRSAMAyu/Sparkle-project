from __future__ import annotations

import pytest

from app.config import settings
from app.services.aurora_stage30_metacognition_kill_switch_service import (
    AuroraStage30MetacognitionKillSwitchService,
)
from app.services.metacognition_service import MetacognitionService


@pytest.mark.asyncio
async def test_metacognition_kill_switch_defaults_to_settings(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_METACOG_MODE", "shadow")
    service = AuroraStage30MetacognitionKillSwitchService()
    assert await service.get_mode() == "shadow"


@pytest.mark.asyncio
async def test_metacognition_kill_switch_auto_disable_turns_everything_off(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "AURORA_METACOG_MODE", "live")
    monkeypatch.setattr(settings, "AURORA_METACOG_DASHBOARD_MODE", "live")
    monkeypatch.setattr(settings, "AURORA_METACOG_PROCESS_SCAFFOLDING_MODE", "live")
    monkeypatch.setattr(settings, "AURORA_METACOG_FSM_COMBINE_MODE", "live")
    service = AuroraStage30MetacognitionKillSwitchService()

    states = await service.auto_disable_on_diagnostic_hit(1)

    assert states == {
        "mode": "off",
        "dashboard": "off",
        "process_scaffolding": "off",
        "fsm_combine": "off",
    }


@pytest.mark.asyncio
async def test_language_contract_hit_disables_runtime_modes(
    db_session, test_user, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "AURORA_METACOG_MODE", "live")
    monkeypatch.setattr(settings, "AURORA_METACOG_DASHBOARD_MODE", "live")
    monkeypatch.setattr(settings, "AURORA_METACOG_PROCESS_SCAFFOLDING_MODE", "live")
    monkeypatch.setattr(settings, "AURORA_METACOG_FSM_COMBINE_MODE", "live")
    service = MetacognitionService(db_session, redis=None)

    allowed = await service._enforce_language_contract(
        ["你是拖延型。"], source="dashboard"
    )

    assert allowed is False
    assert await service.kill_switch.get_mode() == "off"
    assert await service.kill_switch.get_feature_mode("dashboard") == "off"
