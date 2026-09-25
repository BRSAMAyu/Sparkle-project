from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


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


def test_comeback_nudge_task_uses_runtime_payload_for_notification():
    user_id = "00000000-0000-0000-0000-000000000001"
    payload = {
        "title": "好久不见，我一直在等你",
        "message": "你已经 6 天没来了，你的计算机网络冲刺还剩 3 天，现在回来还来得及——如果累了，先开一个「30分钟保底版」。",
        "days_away": 6,
        "days_remaining": 3,
        "subject": "计算机网络",
        "next_task_title": "TCP 流量控制",
        "recent_task_summary": "TCP 流量控制",
        "light_restart_suggestion": "先开一个「30分钟保底版」，把「TCP 流量控制」推进到一个最小闭环。",
        "plan_id": "00000000-0000-0000-0000-000000000002",
    }

    fake_session_local = _FakeSessionCM()
    mock_runtime_cls = MagicMock()
    mock_runtime_instance = MagicMock()
    mock_runtime_instance.get_comeback_context = AsyncMock(return_value=payload)
    mock_runtime_cls.return_value = mock_runtime_instance

    mock_notif_create = AsyncMock()
    mock_notif_cls = MagicMock()
    mock_notif_cls.create = staticmethod(mock_notif_create)

    patches = [
        patch("app.db.session.AsyncSessionLocal", return_value=fake_session_local),
        patch("app.aurora.runtime_v1.service.AuroraRuntimeV1Service", mock_runtime_cls),
        patch("app.services.notification_service.NotificationService", mock_notif_cls),
    ]

    for current_patch in patches:
        current_patch.start()

    try:
        from app.core.celery_tasks import comeback_nudge_task

        result = comeback_nudge_task(user_id)
    finally:
        for current_patch in reversed(patches):
            current_patch.stop()

    assert result["status"] == "sent"
    assert result["plan_id"] == payload["plan_id"]
    assert result["days_remaining"] == payload["days_remaining"]
    mock_runtime_instance.get_comeback_context.assert_awaited_once()
    mock_notif_create.assert_awaited_once()

    notif_create = mock_notif_create.call_args[0][2]
    assert notif_create.title == payload["title"]
    assert notif_create.content == payload["message"]
    assert notif_create.type == "comeback_nudge"
    assert notif_create.data["plan_id"] == payload["plan_id"]
    assert notif_create.data["days_remaining"] == payload["days_remaining"]
    assert notif_create.data["recent_task_summary"] == payload["recent_task_summary"]
    assert notif_create.data["destination_route"] == f"/plans/{payload['plan_id']}?source=comeback_nudge"
    assert notif_create.data["deep_link"] == notif_create.data["destination_route"]


def test_comeback_nudge_task_skips_duplicate_within_24h():
    user_id = "00000000-0000-0000-0000-000000000001"
    payload = {
        "title": "好久不见，我一直在等你",
        "message": "你已经 4 天没来了，回来把 TCP 流量控制补成一个最小闭环吧。",
        "days_away": 4,
        "days_remaining": 2,
        "subject": "计算机网络",
        "plan_id": "00000000-0000-0000-0000-000000000002",
    }

    fake_session_local = _FakeSessionCM()
    fake_session_local.session.execute = AsyncMock(
        return_value=_FakeScalarResult([MagicMock(data={"plan_id": payload["plan_id"]})])
    )

    mock_runtime_cls = MagicMock()
    mock_runtime_instance = MagicMock()
    mock_runtime_instance.get_comeback_context = AsyncMock(return_value=payload)
    mock_runtime_cls.return_value = mock_runtime_instance

    mock_notif_create = AsyncMock()
    mock_notif_cls = MagicMock()
    mock_notif_cls.create = staticmethod(mock_notif_create)

    patches = [
        patch("app.db.session.AsyncSessionLocal", return_value=fake_session_local),
        patch("app.aurora.runtime_v1.service.AuroraRuntimeV1Service", mock_runtime_cls),
        patch("app.services.notification_service.NotificationService", mock_notif_cls),
    ]

    for current_patch in patches:
        current_patch.start()

    try:
        from app.core.celery_tasks import comeback_nudge_task

        result = comeback_nudge_task(user_id)
    finally:
        for current_patch in reversed(patches):
            current_patch.stop()

    assert result["status"] == "skipped"
    assert result["reason"] == "duplicate_recent"
    mock_notif_create.assert_not_awaited()


def test_comeback_nudge_task_low_stimulation_quiets_and_skips_push():
    """A-07: 显式低刺激档——不主动推送、标题去敦促化、data 带档位标记。"""
    user_id = "00000000-0000-0000-0000-000000000001"
    payload = {
        "title": "好久不见，我一直在等你",
        "message": "你已经 6 天没来了，我保留着上次的进度。",
        "days_away": 6,
        "days_remaining": 3,
        "subject": "计算机网络",
        "plan_id": "00000000-0000-0000-0000-000000000002",
        "goal_state": {"goal_id": "g1", "title": "期末目标", "ledger": {"completed": 1, "total": 2}},
    }

    fake_session_local = _FakeSessionCM()
    mock_runtime_cls = MagicMock()
    mock_runtime_instance = MagicMock()
    mock_runtime_instance.get_comeback_context = AsyncMock(return_value=payload)
    mock_runtime_cls.return_value = mock_runtime_instance

    mock_prefs_cls = MagicMock()
    mock_prefs_instance = MagicMock()
    mock_prefs_instance.get = AsyncMock(
        return_value={
            "aurora_analysis_depth": "deep",
            "aurora_directness": "guided",
            "aurora_explanation_level": "detailed",
            "aurora_pressure_style": "motivating",
            "aurora_stimulation_mode": "low",
        }
    )
    mock_prefs_cls.return_value = mock_prefs_instance

    mock_notif_create = AsyncMock()
    mock_notif_cls = MagicMock()
    mock_notif_cls.create = staticmethod(mock_notif_create)

    patches = [
        patch("app.db.session.AsyncSessionLocal", return_value=fake_session_local),
        patch("app.aurora.runtime_v1.service.AuroraRuntimeV1Service", mock_runtime_cls),
        patch(
            "app.aurora.runtime_v1.user_preferences.AuroraUserPreferencesService",
            mock_prefs_cls,
        ),
        patch("app.services.notification_service.NotificationService", mock_notif_cls),
    ]

    for current_patch in patches:
        current_patch.start()

    try:
        from app.core.celery_tasks import comeback_nudge_task

        result = comeback_nudge_task(user_id)
    finally:
        for current_patch in reversed(patches):
            current_patch.stop()

    assert result["status"] == "sent"
    assert result["stimulation"] == "low"
    mock_notif_create.assert_awaited_once()

    notif_create = mock_notif_create.call_args[0][2]
    # 标题去敦促/等待压力，正文保持引擎事实性消息。
    assert notif_create.title == "你的学习计划状态"
    assert notif_create.content == payload["message"]
    # 低刺激档不主动推送（仅入应用内通知中心）。
    assert mock_notif_create.call_args.kwargs["push_via_websocket"] is False
    assert notif_create.data["stimulation_policy"] == "low"
    assert notif_create.data["goal_state"] == payload["goal_state"]
