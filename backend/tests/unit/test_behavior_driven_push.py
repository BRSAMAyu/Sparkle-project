from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.signals.recall_opportunity import RecallOpportunityDetector, RecallTrigger
from app.services.push_scheduler import PushScheduler, _RECALL_QUEUE_PREFIX


def test_undigested_material_trigger() -> None:
    detector = RecallOpportunityDetector()
    trigger = detector.check_undigested_material(
        user_id="u1",
        uploaded_files_count=3,
        diagnosed_files_count=1,
        hours_since_upload=2.0,
    )
    assert trigger is not None
    assert trigger.trigger_type == "undigested_material"
    assert trigger.context["undigested"] == 2
    assert trigger.urgency == "medium"


def test_undigested_material_none_when_all_diagnosed() -> None:
    detector = RecallOpportunityDetector()
    trigger = detector.check_undigested_material(
        user_id="u1",
        uploaded_files_count=2,
        diagnosed_files_count=2,
        hours_since_upload=2.0,
    )
    assert trigger is None


def test_task_not_started_trigger() -> None:
    detector = RecallOpportunityDetector()
    trigger = detector.check_task_not_started(
        user_id="u1",
        task_id="t1",
        hours_since_assignment=4.0,
        has_started=False,
    )
    assert trigger is not None
    assert trigger.trigger_type == "task_not_started"
    assert trigger.urgency == "medium"


def test_task_not_started_none_when_started() -> None:
    detector = RecallOpportunityDetector()
    trigger = detector.check_task_not_started(
        user_id="u1",
        task_id="t1",
        hours_since_assignment=4.0,
        has_started=True,
    )
    assert trigger is None


def test_task_missed_trigger() -> None:
    detector = RecallOpportunityDetector()
    trigger = detector.check_task_missed(
        user_id="u1",
        task_id="t1",
        deadline_hours=-2.0,
        is_completed=False,
    )
    assert trigger is not None
    assert trigger.trigger_type == "task_missed"
    assert trigger.urgency == "high"


def test_pre_exam_silence_trigger() -> None:
    detector = RecallOpportunityDetector()
    trigger = detector.check_pre_exam_silence(
        user_id="u1",
        exam_deadline_days=1.5,
        hours_since_last_activity=5.0,
    )
    assert trigger is not None
    assert trigger.trigger_type == "pre_exam_silence"
    assert trigger.urgency == "medium"


def test_trigger_to_actionable_signal() -> None:
    detector = RecallOpportunityDetector()
    trigger = RecallTrigger(
        trigger_type="task_missed",
        user_id="u1",
        context={"task_id": "t1"},
        urgency="high",
        message_template="Test message",
    )
    signal = detector.to_actionable_signal(trigger)
    assert signal.source_system == "recall_opportunity"
    assert signal.claim == "task_missed"
    assert signal.priority == "high"


@pytest.mark.asyncio
async def test_enqueue_session_end_recall_counts_triggers() -> None:
    redis = AsyncMock()
    redis.pipeline.return_value = pipe = AsyncMock()
    pipe.execute = AsyncMock(return_value=[1, 1, 1])

    db = AsyncMock()
    scheduler = PushScheduler(db, redis=redis)

    count = await scheduler.enqueue_session_end_recall(
        user_id="u1",
        session_context={
            "uploaded_files_count": 3,
            "diagnosed_files_count": 0,
            "hours_since_upload": 2.0,
        },
    )
    assert count == 1
    redis.pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_enqueue_session_end_recall_no_triggers() -> None:
    redis = AsyncMock()
    db = AsyncMock()
    scheduler = PushScheduler(db, redis=redis)

    count = await scheduler.enqueue_session_end_recall(
        user_id="u1",
        session_context={
            "uploaded_files_count": 2,
            "diagnosed_files_count": 2,
            "hours_since_upload": 0.1,
        },
    )
    assert count == 0


@pytest.mark.asyncio
async def test_process_recall_queue_empty() -> None:
    redis = AsyncMock()

    async def _empty_iter(**kwargs):
        return
        yield  # noqa: unreachable — makes this an async generator

    redis.scan_iter = _empty_iter
    db = AsyncMock()
    scheduler = PushScheduler(db, redis=redis)

    stats = await scheduler.process_recall_queue()
    assert stats["processed"] == 0
    assert stats["sent"] == 0


@pytest.mark.asyncio
async def test_build_push_message_with_spine() -> None:
    db = AsyncMock()
    scheduler = PushScheduler(db)

    directive = MagicMock()
    directive.trigger = "recall_opportunity"
    directive.deep_link = "/tasks/t1"

    msg = scheduler._build_push_message(
        trigger_data={"message_template": "你有任务未开始"},
        spine_directive=directive,
    )
    assert msg["title"] == "Sparkle"
    assert "任务未开始" in msg["body"]
    assert msg["deep_link"] == "/tasks/t1"


@pytest.mark.asyncio
async def test_build_push_message_without_spine() -> None:
    db = AsyncMock()
    scheduler = PushScheduler(db)

    msg = scheduler._build_push_message(
        trigger_data={"message_template": "你有资料未诊断"},
        spine_directive=None,
    )
    assert msg["title"] == "Sparkle 提醒"
    assert "资料未诊断" in msg["body"]
