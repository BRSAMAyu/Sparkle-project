"""
Tests for D-01: Notification interaction fatigue → Spine signal pipeline.
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.notification_center_service import NotificationCenterService
from app.services.spine_event_bridge import SpineEventBridge


def _utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


def _make_interaction(user_id, action_type, hours_ago=0):
    """Create a mock NotificationInteraction."""
    m = MagicMock()
    m.user_id = user_id
    m.action_type = action_type
    m.action_time = _utcnow() - timedelta(hours=hours_ago)
    return m


@pytest.mark.asyncio
async def test_spine_bridge_notification_fatigue_signal():
    """notification.fatigue_detected event produces correct ActionableSignal."""
    bridge = SpineEventBridge(MagicMock())
    signal = bridge.build_signal({
        "event_type": "notification.fatigue_detected",
        "user_id": str(uuid4()),
        "consecutive_dismissals": 4,
        "notification_type": "intervention",
    })
    assert signal is not None
    assert signal.state_key == "notification_fatigue"
    assert signal.claim == "consecutive_notification_dismissal"
    assert signal.confidence >= 0.8
    assert signal.priority == "high"


@pytest.mark.asyncio
async def test_spine_bridge_notification_fatigue_low_count():
    """Low consecutive count should still produce signal but medium priority."""
    bridge = SpineEventBridge(MagicMock())
    signal = bridge.build_signal({
        "event_type": "notification.fatigue_detected",
        "user_id": str(uuid4()),
        "consecutive_dismissals": 3,
        "notification_type": "system",
    })
    assert signal is not None
    assert signal.priority == "medium"
    assert signal.confidence >= 0.7


@pytest.mark.asyncio
async def test_fatigue_check_emits_event_on_consecutive_dismissals():
    """_check_and_emit_fatigue should publish EventBus event when 3+ consecutive dismissals."""
    user_id = uuid4()
    db = AsyncMock()
    mock_rows = [_make_interaction(user_id, "dismissed") for _ in range(3)]
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = mock_rows
    db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock)))
    db.flush = AsyncMock()

    svc = NotificationCenterService(db)

    mock_bus = AsyncMock()
    with patch("app.core.event_bus.EventBus", return_value=mock_bus):
        with patch("app.core.cache.cache_service") as mock_cache:
            mock_cache.redis = MagicMock()
            await svc._check_and_emit_fatigue(user_id, "intervention")
            mock_bus.publish.assert_called_once()
            call_kwargs = mock_bus.publish.call_args
            assert call_kwargs.kwargs["event_type"] == "notification.fatigue_detected"
            assert call_kwargs.kwargs["data"]["consecutive_dismissals"] == 3


@pytest.mark.asyncio
async def test_fatigue_check_no_event_below_threshold():
    """_check_and_emit_fatigue should NOT publish when dismissals < 3."""
    user_id = uuid4()
    db = AsyncMock()
    # 2 dismissals + 1 click
    mock_rows = [
        _make_interaction(user_id, "dismissed"),
        _make_interaction(user_id, "dismissed"),
        _make_interaction(user_id, "clicked"),
    ]
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = mock_rows
    db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock)))

    svc = NotificationCenterService(db)

    mock_bus = AsyncMock()
    with patch("app.core.event_bus.EventBus", return_value=mock_bus):
        with patch("app.core.cache.cache_service"):
            await svc._check_and_emit_fatigue(user_id, "system")
            mock_bus.publish.assert_not_called()


@pytest.mark.asyncio
async def test_non_dismissal_action_skips_fatigue_check():
    """Non-dismiss actions should not trigger fatigue check at all."""
    user_id = uuid4()
    db = AsyncMock()
    db.flush = AsyncMock()

    svc = NotificationCenterService(db)
    # _record_interaction with action_type="clicked" should not call _check_and_emit_fatigue
    with patch.object(svc, "_check_and_emit_fatigue", new_callable=AsyncMock) as mock_check:
        await svc._record_interaction(
            user_id=user_id,
            notification_type="system",
            notification_id=uuid4(),
            action_type="clicked",
            created_at=_utcnow(),
        )
        mock_check.assert_not_called()


@pytest.mark.asyncio
async def test_fatigue_check_graceful_on_db_error():
    """Fatigue check should not crash on DB errors."""
    user_id = uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=Exception("DB connection lost"))

    svc = NotificationCenterService(db)
    # Should not raise
    await svc._check_and_emit_fatigue(user_id, "intervention")
