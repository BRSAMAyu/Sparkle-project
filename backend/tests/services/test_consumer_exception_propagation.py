"""Regression test for ISSUE-20260504-1700-F5.

Two contracts, split as the consumers diverged:
- TaskEventConsumer sub-handlers are isolated by _safe_run (log + contain);
  EventBus retry/DLQ deliberately never sees their exceptions.
- ProfileEventConsumer still re-raises, pinning the original F5 propagation
  contract for consumers without such isolation.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_task_completed_contains_sub_handler_failures():
    """Supersedes the F5 propagation expectation for TaskEventConsumer.

    The fan-out now wraps every sub-handler in _safe_run and keeps the
    plan_id lookup / adaptive replanner in their own try/except: a DB
    failure is logged and contained so one broken dependency can neither
    kill sibling sub-handlers nor the stream loop.
    """
    from app.services.task_event_consumer import TaskEventConsumer

    consumer = TaskEventConsumer.__new__(TaskEventConsumer)
    consumer.event_bus = MagicMock()
    consumer._running = False
    consumer._subscribed = False

    event = {
        "event_type": "task.completed",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "task_id": "00000000-0000-0000-0000-000000000002",
        "estimated_minutes": 10,
        "actual_minutes": 5,
        "completion_rate": 0.5,
    }

    # The consumer logs via loguru, so spy on the module logger instead of caplog.
    with patch("app.services.task_event_consumer.AsyncSessionLocal") as mock_session, patch(
        "app.services.task_event_consumer.logger"
    ) as mock_logger:
        mock_session.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("DB connection lost")
        )
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        # Containment contract: must not raise, and must log the failure.
        await consumer._handle_task_completed(event)

    logged = [str(call.args) for call in mock_logger.warning.call_args_list]
    assert any("DB connection lost" in args for args in logged)


@pytest.mark.asyncio
async def test_profile_preference_updated_propagates_exceptions():
    from app.services.profile_event_consumer import ProfileEventConsumer

    consumer = ProfileEventConsumer.__new__(ProfileEventConsumer)
    mock_redis = AsyncMock()
    consumer.redis = mock_redis
    consumer.event_bus = MagicMock()

    event = {
        "event_type": "profile.preference.updated",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "pref_keys": ["language"],
        "preference_version": 1,
        "source": "test",
    }

    with patch(
        "app.services.profile_event_consumer.invalidate_personalization_cache",
        side_effect=Exception("Cache layer down"),
    ):
        with pytest.raises(Exception, match="Cache layer down"):
            await consumer._handle_preference_updated(event)


@pytest.mark.asyncio
async def test_intervention_record_created_propagates_exceptions():
    from app.services.intervention_event_consumer import InterventionEventConsumer

    consumer = InterventionEventConsumer.__new__(InterventionEventConsumer)
    consumer.event_bus = MagicMock()

    event = {
        "event_type": "intervention_record.created",
        "record_id": "00000000-0000-0000-0000-000000000001",
    }

    with patch(
        "app.services.intervention_event_consumer.AsyncSessionLocal"
    ) as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("DB down")
        )
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(Exception, match="DB down"):
            await consumer._handle_record_created(event)
