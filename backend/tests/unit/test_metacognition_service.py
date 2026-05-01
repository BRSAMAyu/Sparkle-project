from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.services.metacognition_service import MetacognitionService


@pytest.mark.asyncio
async def test_build_aggregator_summary_filters_dimensions_below_sample_threshold(
    db_session,
    test_user,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "AURORA_METACOG_MIN_SAMPLE_SIZE", 20)
    service = MetacognitionService(db_session, redis=None)
    service.get_snapshot = AsyncMock(
        return_value={
            "mode": "live",
            "dimensions": [
                {
                    "dim": "completion_bias",
                    "sample_size": 19,
                    "bias_mean": 0.4,
                    "trend": "stable",
                },
                {
                    "dim": "time_estimation_bias",
                    "sample_size": 20,
                    "bias_mean": 0.31,
                    "trend": "improving",
                },
            ],
        }
    )

    summary = await service.build_aggregator_summary(test_user.id)

    assert len(summary.items) == 1
    assert summary.items[0].dim == "time_estimation_bias"
    assert summary.items[0].sample_size == 20


@pytest.mark.asyncio
async def test_dashboard_payload_turns_off_when_child_mode_off(
    db_session, test_user, monkeypatch
) -> None:
    service = MetacognitionService(db_session, redis=None)
    service.get_snapshot = AsyncMock(
        return_value={
            "mode": "live",
            "dimensions": [],
            "generated_at": "2026-04-22T10:00:00",
        }
    )
    monkeypatch.setattr(service, "_load_panel_hidden", AsyncMock(return_value=False))
    monkeypatch.setattr(
        service.kill_switch, "get_feature_mode", AsyncMock(return_value="off")
    )

    payload = await service.build_dashboard_payload(test_user.id)

    assert payload["available"] is False
    assert payload["cards"] == []


@pytest.mark.asyncio
async def test_dashboard_payload_uses_registered_templates_only(
    db_session, test_user, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "AURORA_METACOG_MIN_SAMPLE_SIZE", 20)
    service = MetacognitionService(db_session, redis=None)
    service.get_snapshot = AsyncMock(
        return_value={
            "mode": "live",
            "generated_at": "2026-04-22T10:00:00",
            "dimensions": [
                {
                    "dim": "time_estimation_bias",
                    "sample_size": 24,
                    "bias_mean": 0.42,
                    "display_mean": 2.3,
                    "trend": "stable",
                },
            ],
        }
    )
    monkeypatch.setattr(service, "_load_panel_hidden", AsyncMock(return_value=False))
    monkeypatch.setattr(
        service.kill_switch, "get_feature_mode", AsyncMock(return_value="live")
    )

    payload = await service.build_dashboard_payload(test_user.id)

    assert payload["available"] is True
    assert payload["cards"][0]["template_id"] == "mc_dashboard_time_more_support"
    assert "你过去 {sample_size} 次对完成时间估得偏乐观 {display_value} 小时。" == payload["cards"][0]["body"]
