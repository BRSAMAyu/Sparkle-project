from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.core.celery_app import celery_app
from app.services.progress_narrative_service import WeeklyGrowthNarrative


class _FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class _FakeSessionCM:
    def __init__(self):
        self.session = AsyncMock()
        self.session.execute = AsyncMock(return_value=_FakeScalarResult([]))

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args):
        return False


def _sample_narrative() -> WeeklyGrowthNarrative:
    return WeeklyGrowthNarrative(
        period="本周成长故事",
        week_start="2026-04-20",
        week_end="2026-04-26",
        body=(
            "这周你学习了 5 天。"
            "掌握了 TCP 三次握手、子网划分 等知识点。"
            "还修复了 2 个反复出现的错误。"
            "最大的进步：路由算法 的掌握度从 30% 提升到了 65%。"
            "下周目标：继续把网络层相关的核心概念吃透。"
        ),
        sentences=[
            "这周你学习了 5 天。",
            "掌握了 TCP 三次握手、子网划分 等知识点。",
            "还修复了 2 个反复出现的错误。",
            "最大的进步：路由算法 的掌握度从 30% 提升到了 65%。",
            "下周目标：继续把网络层相关的核心概念吃透。",
        ],
        highlights=[
            "这周你学习了 5 天。",
            "掌握了 TCP 三次握手、子网划分 等知识点。",
            "还修复了 2 个反复出现的错误。",
        ],
        biggest_improvement={
            "node_name": "路由算法",
            "before_mastery": 30.0,
            "after_mastery": 65.0,
            "delta": 35.0,
        },
        next_week_suggestion="继续把网络层相关的核心概念吃透。",
        data_points={
            "tasks_completed": 4,
            "errors_fixed": 2,
            "study_days": 5,
        },
        source_counts={
            "task_completions": 4,
            "error_records": 2,
            "error_review_records": 2,
            "reflection_records": 1,
            "mastery_changes": 2,
            "achievement_unlocks": 0,
            "study_days": 5,
        },
        is_placeholder=False,
        generated_at="2026-04-26T10:00:00",
    )


def test_weekly_growth_narrative_task_sends_notification():
    fake_session_local = _FakeSessionCM()

    mock_service_cls = MagicMock()
    mock_service = MagicMock()
    mock_service.get_weekly_narrative = AsyncMock(return_value=_sample_narrative())
    mock_service_cls.return_value = mock_service

    mock_notification_create = AsyncMock()
    mock_notification_cls = MagicMock()
    mock_notification_cls.create = staticmethod(mock_notification_create)

    with patch("app.db.session.AsyncSessionLocal", return_value=fake_session_local), patch(
        "app.services.progress_narrative_service.ProgressNarrativeService",
        mock_service_cls,
    ), patch("app.services.notification_service.NotificationService", mock_notification_cls):
        from app.core.celery_tasks import weekly_growth_narrative_task

        result = weekly_growth_narrative_task("00000000-0000-0000-0000-000000000001")

    assert result["status"] == "sent"
    assert result["highlights_count"] == 3
    mock_service.get_weekly_narrative.assert_awaited_once()
    mock_notification_create.assert_awaited_once()

    notification = mock_notification_create.call_args[0][2]
    assert notification.type == "weekly_growth_narrative"
    assert notification.data["highlights"]
    assert notification.data["biggest_improvement"]["node_name"] == "路由算法"
    assert notification.data["next_week_suggestion"] == "继续把网络层相关的核心概念吃透。"
    assert notification.data["destination_route"].startswith("/learning/insights?")
    assert "initialPanel=weeklyNarrative" in notification.data["destination_route"]
    assert "weekStart=2026-04-20" in notification.data["destination_route"]
    assert notification.data["deep_link"] == notification.data["destination_route"]


def test_weekly_growth_narrative_task_skips_duplicate_week():
    fake_session_local = _FakeSessionCM()
    fake_session_local.session.execute = AsyncMock(
        return_value=_FakeScalarResult([MagicMock(data={"week_start": "2026-04-20"})])
    )

    mock_service_cls = MagicMock()
    mock_service = MagicMock()
    mock_service.get_weekly_narrative = AsyncMock(return_value=_sample_narrative())
    mock_service_cls.return_value = mock_service

    mock_notification_create = AsyncMock()
    mock_notification_cls = MagicMock()
    mock_notification_cls.create = staticmethod(mock_notification_create)

    with patch("app.db.session.AsyncSessionLocal", return_value=fake_session_local), patch(
        "app.services.progress_narrative_service.ProgressNarrativeService",
        mock_service_cls,
    ), patch("app.services.notification_service.NotificationService", mock_notification_cls):
        from app.core.celery_tasks import weekly_growth_narrative_task

        result = weekly_growth_narrative_task("00000000-0000-0000-0000-000000000001")

    assert result["status"] == "skipped"
    assert result["reason"] == "duplicate_recent"
    mock_notification_create.assert_not_awaited()


def test_weekly_growth_narrative_scan_is_registered_in_beat_schedule():
    task_config = celery_app.conf.beat_schedule["weekly-growth-narrative-scan"]

    assert task_config["task"] == "app.core.celery_tasks.scan_weekly_growth_narratives"
    assert task_config["args"] == (500,)
    assert task_config["options"] == {"queue": "default"}
    assert celery_app.conf.timezone == "Asia/Shanghai"
    assert getattr(task_config["schedule"], "_orig_hour", None) == 18
    assert getattr(task_config["schedule"], "_orig_minute", None) == 0
    assert getattr(task_config["schedule"], "_orig_day_of_week", None) == "sun"
    assert celery_app.conf.task_routes["app.core.celery_tasks.scan_weekly_growth_narratives"] == {"queue": "default"}
