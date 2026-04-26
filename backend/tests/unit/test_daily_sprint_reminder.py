"""
Tests for F17: daily_sprint_reminder_task.

Covers:
  1. completion_rate < 0.6 and days_left > 0  →  notification sent
  2. completion_rate >= 0.6                    →  no notification
  3. days_left == 0                            →  no notification (exam day)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.exam_sprint import (
    ExamSprintDashboardProgress,
    ExamSprintDashboardResponse,
    ExamSprintDashboardTaskGroup,
    ExamSprintDashboardTaskItem,
)


class _FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


def _make_dashboard(
    *,
    active: bool = True,
    plan_id: str = "plan-1",
    subject: str = "高等数学",
    days_left: int = 3,
    completion_rate: float = 0.3,
    today_tasks: list[dict] | None = None,
) -> ExamSprintDashboardResponse:
    tasks = []
    if today_tasks is None:
        today_tasks = [
            {"id": "t1", "title": "微积分基础", "status": "pending", "completed": False},
            {"id": "t2", "title": "线性代数", "status": "completed", "completed": True},
        ]
    for t in today_tasks:
        tasks.append(
            ExamSprintDashboardTaskItem(
                id=t["id"],
                title=t["title"],
                status=t["status"],
                is_completed=t.get("completed", False),
            )
        )

    today_group = ExamSprintDashboardTaskGroup(
        day_index=5,
        is_today=True,
        completed_count=sum(1 for t in tasks if t.is_completed),
        total_count=len(tasks),
        tasks=tasks,
    )

    completed = int(completion_rate * len(tasks))
    return ExamSprintDashboardResponse(
        active=active,
        plan_id=plan_id,
        plan_name="高数冲刺",
        subject=subject,
        days_left=days_left,
        today_progress=ExamSprintDashboardProgress(
            completed=completed,
            total=len(tasks),
            completion_rate=completion_rate,
        ),
        task_groups=[today_group],
    )


class _FakeSessionCM:
    """Context manager that yields a mock async session."""

    def __init__(self):
        self.session = AsyncMock()

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args):
        return False


@pytest.fixture()
def _patched_deps():
    """
    Patch the lazy-imported sources inside the task's _run closure.

    The task does late imports like:
        from app.services.exam_sprint_dashboard_service import ExamSprintDashboardService
        from app.services.notification_service import NotificationService
        from app.db.session import AsyncSessionLocal

    We patch at the source module level so the late import picks up the mock.
    """
    fake_session_local = _FakeSessionCM()
    fake_session_local.session.execute = AsyncMock(return_value=_FakeScalarResult([]))

    mock_dashboard_cls = MagicMock()
    mock_dashboard_instance = MagicMock()
    mock_dashboard_cls.return_value = mock_dashboard_instance

    mock_notif_create = AsyncMock()
    mock_notif_cls = MagicMock()
    mock_notif_cls.create = staticmethod(mock_notif_create)

    patches = [
        patch("app.db.session.AsyncSessionLocal", return_value=fake_session_local),
        patch(
            "app.services.exam_sprint_dashboard_service.ExamSprintDashboardService",
            mock_dashboard_cls,
        ),
        patch("app.services.notification_service.NotificationService", mock_notif_cls),
    ]

    for p in patches:
        p.start()

    yield fake_session_local.session, mock_dashboard_instance, mock_notif_create

    for p in patches:
        p.stop()


class TestDailySprintReminder:
    """F17 daily sprint reminder task tests."""

    USER_ID = "00000000-0000-0000-0000-000000000001"
    PLAN_ID = "00000000-0000-0000-0000-000000000002"

    def test_sends_notification_when_behind(self, _patched_deps):
        """completion_rate=0.3, days_left=3 → push sent with subject + days."""
        _, mock_dashboard, mock_create = _patched_deps
        mock_dashboard.get_dashboard = AsyncMock(
            return_value=_make_dashboard(completion_rate=0.3, days_left=3, plan_id=self.PLAN_ID)
        )

        from app.core.celery_tasks import daily_sprint_reminder_task

        result = daily_sprint_reminder_task(self.USER_ID, self.PLAN_ID)

        assert result["status"] == "sent"
        assert result["completion_rate"] == 0.3
        assert result["days_left"] == 3
        mock_create.assert_awaited_once()

        call_args = mock_create.call_args
        notif_create = call_args[0][2]  # 3rd positional = NotificationCreate
        assert "高等数学" in notif_create.content
        assert "3" in notif_create.content
        assert "微积分基础" in notif_create.content
        assert "30%" in notif_create.content
        assert notif_create.type == "sprint_reminder"
        assert notif_create.data["destination_route"] == f"/plans/{self.PLAN_ID}?source=push_sprint_reminder"
        assert notif_create.data["deep_link"] == notif_create.data["destination_route"]

    def test_skips_when_on_track(self, _patched_deps):
        """completion_rate=0.9 → no push."""
        _, mock_dashboard, mock_create = _patched_deps
        mock_dashboard.get_dashboard = AsyncMock(
            return_value=_make_dashboard(completion_rate=0.9, days_left=3, plan_id=self.PLAN_ID)
        )

        from app.core.celery_tasks import daily_sprint_reminder_task

        result = daily_sprint_reminder_task(self.USER_ID, self.PLAN_ID)

        assert result["status"] == "skipped"
        assert result["reason"] == "on_track"
        mock_create.assert_not_awaited()

    def test_skips_on_exam_day(self, _patched_deps):
        """days_left=0 → no push (exam day)."""
        _, mock_dashboard, mock_create = _patched_deps
        mock_dashboard.get_dashboard = AsyncMock(
            return_value=_make_dashboard(completion_rate=0.1, days_left=0, plan_id=self.PLAN_ID)
        )

        from app.core.celery_tasks import daily_sprint_reminder_task

        result = daily_sprint_reminder_task(self.USER_ID, self.PLAN_ID)

        assert result["status"] == "skipped"
        assert result["reason"] == "exam_day"
        mock_create.assert_not_awaited()

    def test_skips_duplicate_notification_within_24h(self, _patched_deps):
        session, mock_dashboard, mock_create = _patched_deps
        mock_dashboard.get_dashboard = AsyncMock(
            return_value=_make_dashboard(completion_rate=0.3, days_left=3, plan_id=self.PLAN_ID)
        )
        session.execute = AsyncMock(
            return_value=_FakeScalarResult(
                [
                    MagicMock(
                        data={"plan_id": self.PLAN_ID},
                    )
                ]
            )
        )

        from app.core.celery_tasks import daily_sprint_reminder_task

        result = daily_sprint_reminder_task(self.USER_ID, self.PLAN_ID)

        assert result["status"] == "skipped"
        assert result["reason"] == "duplicate_recent"
        mock_create.assert_not_awaited()
