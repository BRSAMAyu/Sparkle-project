from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.services.metacognition_service import MetacognitionService


def _rows(count: int) -> list[dict[str, object]]:
    return [
        {
            "bias": 0.35,
            "display_bias": 2.1,
            "predicted": 2.0,
            "actual": 4.1,
            "recorded_at": datetime(2026, 4, 22, 10, 0, 0),
        }
        for _ in range(count)
    ]


@pytest.mark.asyncio
async def test_cold_start_summary_excludes_sample_size_below_twenty(db_session, test_user, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_METACOG_MIN_SAMPLE_SIZE", 20)
    service = MetacognitionService(db_session, redis=None)
    snapshot = {
        "mode": "live",
        "dimensions": [
            service._aggregate_dimension_rows("time_estimation_bias", _rows(19), datetime(2026, 4, 22, 10, 0, 0)),
        ],
    }
    monkeypatch.setattr(service, "get_snapshot", AsyncMock(return_value=snapshot))

    summary = await service.build_aggregator_summary(test_user.id)

    assert summary.items == ()


@pytest.mark.asyncio
async def test_cold_start_summary_includes_sample_size_equal_twenty(db_session, test_user, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_METACOG_MIN_SAMPLE_SIZE", 20)
    service = MetacognitionService(db_session, redis=None)
    snapshot = {
        "mode": "live",
        "dimensions": [
            service._aggregate_dimension_rows("time_estimation_bias", _rows(20), datetime(2026, 4, 22, 10, 0, 0)),
        ],
    }
    monkeypatch.setattr(service, "get_snapshot", AsyncMock(return_value=snapshot))

    summary = await service.build_aggregator_summary(test_user.id)

    assert len(summary.items) == 1
    assert summary.items[0].sample_size == 20


@pytest.mark.asyncio
async def test_process_scaffolding_does_not_trigger_below_twenty(db_session, test_user, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_METACOG_MIN_SAMPLE_SIZE", 20)
    monkeypatch.setattr(settings, "AURORA_METACOG_PROCESS_TRIGGER_ABS_BIAS", 0.3)
    service = MetacognitionService(db_session, redis=None)
    monkeypatch.setattr(service.kill_switch, "get_feature_mode", AsyncMock(return_value="live"))
    monkeypatch.setattr(
        service,
        "get_snapshot",
        AsyncMock(
            return_value={
                "mode": "live",
                "dimensions": [
                    {
                        "dim": "time_estimation_bias",
                        "sample_size": 19,
                        "bias_mean": 0.45,
                        "mean_predicted": 2.0,
                        "mean_actual": 4.0,
                    }
                ],
            }
        ),
    )

    scaffold = await service.build_prompt_process_scaffolding(test_user.id)

    assert scaffold is None
