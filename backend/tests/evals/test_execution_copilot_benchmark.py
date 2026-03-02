from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.task import TaskStatus
from app.services.execution_copilot_service import ExecutionCopilotService


def _build_event(*, event_type: str, days_ago: int, blockers: list[str] | None = None) -> dict:
    occurred_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_ago)
    return {
        "event_type": event_type,
        "timestamp": occurred_at.isoformat(),
        "data": {
            "blockers": blockers or [],
        },
    }


def test_execution_copilot_benchmark_timeline_and_risk() -> None:
    service = ExecutionCopilotService(db=MagicMock(), redis=None)

    healthy_events = [
        _build_event(event_type="checkpoint_due", days_ago=0, blockers=["overdue_tasks_present"]),
        _build_event(event_type="checkpoint_done", days_ago=0),
        _build_event(event_type="checkpoint_due", days_ago=1),
        _build_event(event_type="checkpoint_done", days_ago=1),
        _build_event(event_type="checkpoint_due", days_ago=2),
        _build_event(event_type="checkpoint_done", days_ago=2),
        _build_event(event_type="checkpoint_skipped", days_ago=3),
    ]

    summary = service._summarize_checkpoint_events(events=healthy_events)
    timeline = service._build_timeline_rows(events=healthy_events, days=7)
    blockers = service._top_blockers(events=healthy_events)

    tasks = [
        SimpleNamespace(status=TaskStatus.PENDING),
        SimpleNamespace(status=TaskStatus.IN_PROGRESS),
    ]
    risk_level = service._assess_risk_level(
        blockers=["overdue_tasks_present"],
        checkpoint_summary=summary,
        tasks=tasks,
        today_actions=[{"task_id": "t1", "title": "复盘错题"}],
    )

    assert summary["done_rate"] >= 0.7
    assert summary["skip_rate"] <= 0.4
    assert len(timeline) == 7
    assert blockers and blockers[0]["blocker"] == "overdue_tasks_present"
    assert risk_level in {"low", "medium"}


def test_execution_copilot_benchmark_risk_guardrail_for_skip_overload() -> None:
    service = ExecutionCopilotService(db=MagicMock(), redis=None)

    risky_events = [
        _build_event(event_type="checkpoint_done", days_ago=0),
        _build_event(event_type="checkpoint_skipped", days_ago=0),
        _build_event(event_type="checkpoint_skipped", days_ago=1),
        _build_event(event_type="checkpoint_skipped", days_ago=2),
        _build_event(event_type="checkpoint_skipped", days_ago=3),
    ]

    summary = service._summarize_checkpoint_events(events=risky_events)
    risk_level = service._assess_risk_level(
        blockers=["overdue_tasks_present", "parallel_in_progress_overload"],
        checkpoint_summary=summary,
        tasks=[SimpleNamespace(status=TaskStatus.PENDING) for _ in range(10)],
        today_actions=[{"task_id": "t1", "title": "开始任务"}],
    )

    assert summary["skip_rate"] >= 0.6
    assert risk_level == "high"
