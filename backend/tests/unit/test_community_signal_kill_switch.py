"""Regression test for ISSUE-20260504-1600-L5: CommunitySignalBridge Aurora tri-state kill switch."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage33_kill_switch_service import AuroraStage33KillSwitchService
from app.services.community_signal_bridge import CommunitySignalBridge


@pytest.mark.asyncio
async def test_community_bridge_initializes_kill_switch() -> None:
    bridge = CommunitySignalBridge(db=AsyncMock(), redis=None)
    assert isinstance(bridge.kill_switch, AuroraStage33KillSwitchService)


@pytest.mark.asyncio
async def test_community_mode_returns_feature_mode(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "live"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "shadow"

    bridge = CommunitySignalBridge(db=AsyncMock(), redis=None)
    mode = await bridge._community_mode()
    assert mode == "shadow"


@pytest.mark.asyncio
async def test_community_off_blocked_by_master_mode(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "off"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "live"

    bridge = CommunitySignalBridge(db=AsyncMock(), redis=None)
    mode = await bridge._community_mode()
    assert mode == "off"


# ── cohort signal ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cohort_signal_disabled_when_community_off(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "live"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "off"

    bridge = CommunitySignalBridge(db=AsyncMock(), redis=None)
    result = await bridge.build_privacy_preserving_cohort_signal(
        requester_user_id=uuid4(),
        cohort_criteria={"topic": "math"},
        stat_name="avg_progress",
        contributor_values=[0.5, 0.6, 0.7, 0.8, 0.9],
    )
    assert result == {"allowed": False, "reason": "community_bridge_disabled"}


@pytest.mark.asyncio
async def test_cohort_signal_disabled_when_community_shadow(monkeypatch) -> None:
    """Shadow mode must suppress writes same as off (tri-state)."""
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "live"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "shadow"

    bridge = CommunitySignalBridge(db=AsyncMock(), redis=None)
    result = await bridge.build_privacy_preserving_cohort_signal(
        requester_user_id=uuid4(),
        cohort_criteria={"topic": "math"},
        stat_name="avg_progress",
        contributor_values=[0.5, 0.6, 0.7, 0.8, 0.9],
    )
    assert result == {"allowed": False, "reason": "community_bridge_disabled"}


# ── broadcast achievement ──────────────────────────────────────


@pytest.mark.asyncio
async def test_broadcast_achievement_skipped_when_community_off(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "live"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "off"

    bridge = CommunitySignalBridge(db=AsyncMock(), redis=None)
    result = await bridge.broadcast_achievement_unlock(
        user_id=uuid4(),
        achievement_id="ach_001",
        achievement_title="Test Achievement",
    )
    assert result is None


@pytest.mark.asyncio
async def test_broadcast_achievement_skipped_when_community_shadow(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "live"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "shadow"

    bridge = CommunitySignalBridge(db=AsyncMock(), redis=None)
    result = await bridge.broadcast_achievement_unlock(
        user_id=uuid4(),
        achievement_id="ach_001",
        achievement_title="Test Achievement",
    )
    assert result is None


# ── handle_group_task_completed ────────────────────────────────


@pytest.mark.asyncio
async def test_handle_group_task_completed_skipped_when_community_off(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "live"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "off"

    db_mock = AsyncMock()
    bridge = CommunitySignalBridge(db=db_mock, redis=None)
    result = await bridge.handle_group_task_completed(
        {"source": "group", "task_id": str(uuid4()), "user_id": str(uuid4())}
    )
    assert result is None
    db_mock.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_group_task_completed_skipped_when_community_shadow(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "live"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "shadow"

    db_mock = AsyncMock()
    bridge = CommunitySignalBridge(db=db_mock, redis=None)
    result = await bridge.handle_group_task_completed(
        {"source": "group", "task_id": str(uuid4()), "user_id": str(uuid4())}
    )
    assert result is None
    db_mock.execute.assert_not_awaited()


# ── kill switch service ────────────────────────────────────────


@pytest.mark.asyncio
async def test_stage33_community_feature_binding_registered(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "live"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "shadow"

    service = AuroraStage33KillSwitchService()
    assert await service.get_feature_mode("community") == "shadow"


@pytest.mark.asyncio
async def test_stage33_summary_includes_community(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "shadow"
    settings.AURORA_STAGE33_SOCIAL_MODE = "live"
    settings.AURORA_STAGE33_SRL_MODE = "shadow"
    settings.AURORA_STAGE33_WM_PROMPT_MODE = "shadow"
    settings.AURORA_STAGE33_EVENTS_MODE = "shadow"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "live"

    summary = await AuroraStage33KillSwitchService().summary()
    assert set(summary.keys()) == {"mode", "social", "srl", "wm_prompt", "events", "community"}
    assert summary["community"] == "live"
