"""P-06: comeback_nudge_task 接线统一通知负担闸门（quiet/cap）。

任务顺序契约：P-03 抑制检查**先于**负担闸门（mute 最优先，不因 cap 重置
而复活）；负担闸门在生成源头抑制（不产通知）。cap/quiet 判定语义由
test_notification_burden_p06 / test_notification_burden_24h_clock 在真实
DB 上穷举；本文件只钉任务侧接线。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.aurora.proactive import config as proactive_config


@pytest.fixture(autouse=True)
def _deterministic_knobs(monkeypatch: pytest.MonkeyPatch):
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


_PAYLOAD = {
    "title": "好久不见，我一直在等你",
    "message": "你的计算机网络冲刺还剩 3 天。",
    "days_away": 6,
    "days_remaining": 3,
    "subject": "计算机网络",
    "plan_id": "00000000-0000-0000-0000-000000000002",
}


def _make_patches(fake_session_local, stimulation_mode="auto"):
    mock_runtime_cls = MagicMock()
    mock_runtime_instance = MagicMock()
    mock_runtime_instance.get_comeback_context = AsyncMock(return_value=dict(_PAYLOAD))
    mock_runtime_cls.return_value = mock_runtime_instance

    mock_prefs_cls = MagicMock()
    mock_prefs_instance = MagicMock()
    mock_prefs_instance.get = AsyncMock(return_value={"aurora_stimulation_mode": stimulation_mode})
    mock_prefs_cls.return_value = mock_prefs_instance

    mock_notif_create = AsyncMock()
    mock_notif_cls = MagicMock()
    mock_notif_cls.create = staticmethod(mock_notif_create)

    patches = [
        patch("app.db.session.AsyncSessionLocal", return_value=fake_session_local),
        patch("app.aurora.runtime_v1.service.AuroraRuntimeV1Service", mock_runtime_cls),
        patch("app.aurora.runtime_v1.user_preferences.AuroraUserPreferencesService", mock_prefs_cls),
        patch("app.services.notification_service.NotificationService", mock_notif_cls),
    ]
    return patches, mock_notif_create


def test_nudge_task_suppressed_when_user_cap_is_zero(monkeypatch):
    """daily_cap=0 = 用户关停：任务在生成源头跳过，不产通知。"""
    monkeypatch.setattr(proactive_config, "PROACTIVE_DAILY_CAP", 0)

    fake_session_local = _FakeSessionCM()
    patches, mock_notif_create = _make_patches(fake_session_local)
    for p in patches:
        p.start()
    try:
        from app.core.celery_tasks import comeback_nudge_task

        result = comeback_nudge_task("00000000-0000-0000-0000-000000000001")
    finally:
        for p in reversed(patches):
            p.stop()

    assert result["status"] == "skipped"
    assert result["reason"] == "notification_burden"
    assert result["burden"]["reason"] == "daily_cap"
    assert result["burden"]["details"]["cap"] == 0
    mock_notif_create.assert_not_awaited()


def test_nudge_task_sends_when_burden_allows(monkeypatch):
    """对照组：cap=3、无 quiet → 负担闸门放行，通知照常生成（不误伤）。"""
    monkeypatch.setattr(proactive_config, "PROACTIVE_DAILY_CAP", 3)

    fake_session_local = _FakeSessionCM()
    patches, mock_notif_create = _make_patches(fake_session_local)
    for p in patches:
        p.start()
    try:
        from app.core.celery_tasks import comeback_nudge_task

        result = comeback_nudge_task("00000000-0000-0000-0000-000000000001")
    finally:
        for p in reversed(patches):
            p.stop()

    assert result["status"] == "sent"
    mock_notif_create.assert_awaited_once()
