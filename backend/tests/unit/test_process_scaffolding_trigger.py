from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.services.metacognition_service import MetacognitionService


@pytest.mark.asyncio
async def test_process_scaffolding_triggers_for_eligible_dimension(
    db_session, test_user, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "AURORA_METACOG_MIN_SAMPLE_SIZE", 20)
    monkeypatch.setattr(settings, "AURORA_METACOG_PROCESS_TRIGGER_ABS_BIAS", 0.3)
    service = MetacognitionService(db_session, redis=None)
    monkeypatch.setattr(
        service.kill_switch, "get_feature_mode", AsyncMock(return_value="live")
    )
    monkeypatch.setattr(
        service,
        "get_snapshot",
        AsyncMock(
            return_value={
                "mode": "live",
                "dimensions": [
                    {
                        "dim": "time_estimation_bias",
                        "sample_size": 22,
                        "bias_mean": 0.4,
                        "mean_predicted": 2.0,
                        "mean_actual": 4.0,
                    }
                ],
            }
        ),
    )
    monkeypatch.setattr(service, "_is_in_cooldown", AsyncMock(return_value=False))
    monkeypatch.setattr(service, "_mark_cooldown", AsyncMock())

    scaffold = await service.build_prompt_process_scaffolding(test_user.id)

    assert scaffold is not None
    assert scaffold["template_id"] == "mc_process_time_more_support_factors"
    assert "你之前预估用 2.0 小时完成，实际用了 4.0 小时。" in scaffold["body"]


@pytest.mark.asyncio
async def test_process_scaffolding_skips_when_in_cooldown(
    db_session, test_user, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "AURORA_METACOG_MIN_SAMPLE_SIZE", 20)
    monkeypatch.setattr(settings, "AURORA_METACOG_PROCESS_TRIGGER_ABS_BIAS", 0.3)
    service = MetacognitionService(db_session, redis=None)
    monkeypatch.setattr(
        service.kill_switch, "get_feature_mode", AsyncMock(return_value="live")
    )
    monkeypatch.setattr(
        service,
        "get_snapshot",
        AsyncMock(
            return_value={
                "mode": "live",
                "dimensions": [
                    {
                        "dim": "time_estimation_bias",
                        "sample_size": 22,
                        "bias_mean": 0.4,
                        "mean_predicted": 2.0,
                        "mean_actual": 4.0,
                    }
                ],
            }
        ),
    )
    monkeypatch.setattr(service, "_is_in_cooldown", AsyncMock(return_value=True))

    scaffold = await service.build_prompt_process_scaffolding(test_user.id)

    assert scaffold is None
