from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _no_quiet_hours_by_default(monkeypatch: pytest.MonkeyPatch):
    """P-06 时钟无关性约定（与 test_proactive_event_pipeline 同款）：本文件
    只钉任务接线，quiet 窗行为由 test_notification_burden_p06 在真实 DB 上
    确定性穷举；平台基线 quiet 在此默认关，避免挂钟时间让 sent 断言波动。"""
    from app.aurora.proactive import config as proactive_config

    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False)


class _FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None


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


# ── P-03: 四要素 payload + Goal deep link + 拒绝后 cooldown ──────────────────

_P03_GUILT_LEXICON = ("懒", "落后", "拖后腿", "堕落", "荒废", "浪费", "太差", "失败", "你怎么", "辜负", "失望", "别人都", "羞耻", "丢人", "还来得及")


def test_comeback_nudge_task_includes_suggestion_elements_without_guilt():
    """P-03 四要素：why_now / suggested_action 随通知下发，文案零 guilt。"""
    user_id = "00000000-0000-0000-0000-000000000001"
    payload = {
        "title": "好久不见，我一直在等你",
        "message": "你的计算机网络冲刺还剩 3 天。上次停在「TCP 流量控制」。",
        "days_away": 6,
        "days_remaining": 3,
        "subject": "计算机网络",
        "next_task_title": "TCP 流量控制",
        "recent_task_summary": "TCP 流量控制",
        "light_restart_suggestion": "先开一个「30分钟保底版」，把「TCP 流量控制」推进到一个最小闭环。",
        "plan_id": "00000000-0000-0000-0000-000000000002",
        "goal_state": {"goal_id": "g1", "ledger": {"completed": 1, "total": 4}},
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
            "aurora_stimulation_mode": "auto",
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
    notif_create = mock_notif_create.call_args[0][2]
    data = notif_create.data

    # 四要素之「解释」与「建议动作」必须随通知下发。
    assert isinstance(data.get("why_now"), str) and data["why_now"].strip()
    assert isinstance(data.get("suggested_action"), str) and data["suggested_action"].strip()
    assert data.get("suggestion_type") == "comeback_nudge"

    # guilt/压力文案零命中（标题/正文/why_now/建议动作全量扫描）。
    for text in (
        notif_create.title,
        notif_create.content,
        data["why_now"],
        data["suggested_action"],
    ):
        for term in _P03_GUILT_LEXICON:
            assert term not in text, f"guilt term {term!r} in {text!r}"


def test_comeback_nudge_task_deep_links_to_goal_page():
    """P-03 deep link：goal_state.goal_id 存在 → 指向 Goal 页（而非把 plan 当 goal）。"""
    user_id = "00000000-0000-0000-0000-000000000001"
    payload = {
        "title": "好久不见，我一直在等你",
        "message": "你的计算机网络冲刺还剩 3 天。",
        "days_away": 6,
        "days_remaining": 3,
        "subject": "计算机网络",
        "plan_id": "00000000-0000-0000-0000-000000000002",
        "goal_state": {"goal_id": "00000000-0000-0000-0000-00000000abc", "title": "期末目标"},
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
            "aurora_stimulation_mode": "auto",
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
    notif_create = mock_notif_create.call_args[0][2]
    assert notif_create.data["destination_route"] == (
        "/goals/00000000-0000-0000-0000-00000000abc?source=comeback_nudge"
    )
    assert notif_create.data["deep_link"] == notif_create.data["destination_route"]


def test_comeback_nudge_task_skips_while_ignore_today_cooldown_active():
    """P-03 拒绝后 cooldown：用户点了「今天不再看」，窗口内重复建议被真源抑制。

    窗口时间语义（24h 过期/恢复）由 test_proactive_suggestion_feedback.py 在
    真实 DB 上穷举；本测试钉任务侧接线：任务必须查询抑制态并遵守。
    """
    from datetime import UTC, datetime, timedelta

    user_id = "00000000-0000-0000-0000-000000000001"
    plan_id = "00000000-0000-0000-0000-000000000002"
    payload = {
        "title": "好久不见，我一直在等你",
        "message": "你的计算机网络冲刺还剩 3 天。",
        "days_away": 6,
        "days_remaining": 3,
        "subject": "计算机网络",
        "plan_id": plan_id,
    }
    future_until = (datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=20)).isoformat()
    prefs_row = SimpleNamespace(
        explicit={"proactive_suggestion_ignored_until": {"comeback_nudge": future_until}}
    )

    class _PrefsScalarResult:
        def scalar_one_or_none(self):
            return prefs_row

    fake_session_local = _FakeSessionCM()
    execute_counter = {"count": 0}

    async def _counting_execute(*args, **kwargs):
        execute_counter["count"] += 1
        return _PrefsScalarResult()

    fake_session_local.session.execute = AsyncMock(side_effect=_counting_execute)

    mock_runtime_cls = MagicMock()
    mock_runtime_instance = MagicMock()
    mock_runtime_instance.get_comeback_context = AsyncMock(return_value=payload)
    mock_runtime_cls.return_value = mock_runtime_instance

    mock_prefs_cls = MagicMock()
    mock_prefs_instance = MagicMock()
    mock_prefs_instance.get = AsyncMock(return_value={"aurora_stimulation_mode": "auto"})
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

        suppressed = comeback_nudge_task(user_id)
    finally:
        for current_patch in reversed(patches):
            current_patch.stop()

    # cooldown 生效：不创建通知，跳过原因可审计；抑制检查先于重复窗口检查。
    assert suppressed["status"] == "skipped"
    assert suppressed["reason"] == "suggestion_suppressed"
    assert suppressed["suppression"]["reason"] == "cooldown"
    assert execute_counter["count"] == 1
    mock_notif_create.assert_not_awaited()


def test_comeback_nudge_task_still_sends_without_any_suggestion_feedback():
    """对照组：无任何拒绝记录 → 建议照常下发（抑制不误伤）。"""
    fake_session_local = _FakeSessionCM()
    fake_session_local.session.execute = AsyncMock(
        return_value=_FakeScalarResult([])
    )
    user_id = "00000000-0000-0000-0000-000000000001"
    payload = {
        "title": "好久不见，我一直在等你",
        "message": "你的计算机网络冲刺还剩 3 天。",
        "days_away": 6,
        "days_remaining": 3,
        "subject": "计算机网络",
        "plan_id": "00000000-0000-0000-0000-000000000002",
    }

    mock_runtime_cls = MagicMock()
    mock_runtime_instance = MagicMock()
    mock_runtime_instance.get_comeback_context = AsyncMock(return_value=payload)
    mock_runtime_cls.return_value = mock_runtime_instance

    mock_prefs_cls = MagicMock()
    mock_prefs_instance = MagicMock()
    mock_prefs_instance.get = AsyncMock(return_value={"aurora_stimulation_mode": "auto"})
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
    mock_notif_create.assert_awaited_once()


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
