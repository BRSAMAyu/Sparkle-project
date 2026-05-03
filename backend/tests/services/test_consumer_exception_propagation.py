"""Regression test for ISSUE-20260504-1700-F5.

Verifies that consumer sub-handlers re-raise exceptions so EventBus
retry/DLQ infrastructure is not bypassed.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_task_completed_propagates_exceptions():
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

    with patch("app.services.task_event_consumer.AsyncSessionLocal") as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("DB connection lost")
        )
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(Exception, match="DB connection lost"):
            await consumer._handle_task_completed(event)


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
