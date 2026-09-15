from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.orchestration.adaptive_replanner import AdaptiveReplanner


def _replanner() -> AdaptiveReplanner:
    replanner = object.__new__(AdaptiveReplanner)
    replanner.db = SimpleNamespace()
    return replanner


@pytest.mark.asyncio
async def test_check_proactive_intervention_below_threshold_returns_none(monkeypatch) -> None:
    replanner = _replanner()
    replanner._get_meta_value = AsyncMock()
    replanner._set_meta_value = AsyncMock()

    monkeypatch.setattr(
        "app.services.struggle_signal_aggregator.struggle_signal_aggregator.get_struggle_context",
        AsyncMock(return_value={"struggle_score": 0.59}),
    )

    result = await replanner.check_proactive_intervention(user_id=str(uuid4()), plan_id=str(uuid4()))

    assert result is None
    replanner._get_meta_value.assert_not_called()
    replanner._set_meta_value.assert_not_called()


@pytest.mark.asyncio
async def test_check_proactive_intervention_respects_8h_cooldown(monkeypatch) -> None:
    replanner = _replanner()
    replanner._get_meta_value = AsyncMock(return_value=datetime.now(timezone.utc) - timedelta(hours=2))
    replanner._set_meta_value = AsyncMock()

    monkeypatch.setattr(
        "app.services.struggle_signal_aggregator.struggle_signal_aggregator.get_struggle_context",
        AsyncMock(return_value={"struggle_score": 0.72, "stuck_concepts": []}),
    )

    result = await replanner.check_proactive_intervention(user_id=str(uuid4()), plan_id=str(uuid4()))

    assert result is None
    replanner._set_meta_value.assert_not_called()


@pytest.mark.asyncio
async def test_check_proactive_intervention_with_stuck_concepts_mentions_concept(monkeypatch) -> None:
    replanner = _replanner()
    replanner._get_meta_value = AsyncMock(return_value=None)
    replanner._set_meta_value = AsyncMock()

    monkeypatch.setattr(
        "app.services.struggle_signal_aggregator.struggle_signal_aggregator.get_struggle_context",
        AsyncMock(
            return_value={
                "struggle_score": 0.72,
                "stuck_concepts": ["热力学过程", "卡诺循环"],
                "days_behind": 2,
            }
        ),
    )

    result = await replanner.check_proactive_intervention(user_id=str(uuid4()), plan_id=str(uuid4()))

    assert result is not None
    assert result["action"] == "send_proactive_aurora_message"
    assert "热力学过程" in result["message_hint"]
    replanner._set_meta_value.assert_awaited_once()


@pytest.mark.asyncio
async def test_proactive_message_hint_is_non_judgmental(monkeypatch) -> None:
    replanner = _replanner()
    replanner._get_meta_value = AsyncMock(return_value=None)
    replanner._set_meta_value = AsyncMock()

    monkeypatch.setattr(
        "app.services.struggle_signal_aggregator.struggle_signal_aggregator.get_struggle_context",
        AsyncMock(return_value={"struggle_score": 0.7, "stuck_concepts": [], "days_behind": 0}),
    )

    result = await replanner.check_proactive_intervention(user_id=str(uuid4()), plan_id=str(uuid4()))

    assert result is not None
    message_hint = result["message_hint"]
    assert "失败" not in message_hint
    assert "没做到" not in message_hint
    assert "你又" not in message_hint
