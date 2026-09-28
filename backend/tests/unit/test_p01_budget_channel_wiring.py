"""V4-P01: 两渠道任务接线——统一预算闸门在生成源头生效。

与 test_proactive_unified_budget（闸门穷举、真实 DB）互补，本文件钉**任务侧
接线**（fake session + mock 外呼，celery 任务经 ``_run_async`` 自建 loop，
与既有 test_comeback_nudge_task / test_comeback_nudge_burden_p06 同款纪律；
闸门自身的抑制/预算语义在真实 DB 上穷举，不在此重复）：

- 跨渠道补发反例钉（任务级）：nudge 渠道拒绝（plan X）后，
  ``recall_notification_task`` 对同一 subject 必须在生成源头跳过——spine
  构建不发生、通知不落库、spine 冷却状态不消耗；
- spine 渠道放行路径：通知 data 必须携带 ``proactive_budget`` 预算信封
  （prompt_key/channel/subject/count/cap——预算与因果来源可追）；
- nudge 渠道放行路径：``comeback_nudge_task`` 生成的通知同样盖预算信封
  （两渠道同一审计形状）。

quiet 挂钟免疫与既有任务测试同款（平台基线 quiet 关断）。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.aurora.proactive import config as proactive_config
from app.aurora.proactive.unified_budget import (
    ProactiveChannel,
    derive_prompt_key,
)

PLAN_ID = "00000000-0000-0000-0000-00000000000a"
TASK_ID = "00000000-0000-0000-0000-00000000000b"
USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def _deterministic_knobs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False)
    monkeypatch.setattr(proactive_config, "PROACTIVE_UNIFIED_BUDGET_ENABLED", True)
    monkeypatch.setattr(proactive_config, "PROACTIVE_DAILY_CAP", 3)


class _FakeScalarResult:
    """按构造参数同时支持 scalar_one_or_none / scalars().all 两种读法。"""

    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None


class _FakeSessionCM:
    def __init__(self, execute_result_factory):
        self.session = AsyncMock()
        self._factory = execute_result_factory
        self.execute_count = {"count": 0}
        self.session.execute = AsyncMock(side_effect=self._execute)

    async def _execute(self, *args, **kwargs):
        self.execute_count["count"] += 1
        return self._factory()

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args):
        return False


def _subject_suppressed_row(plan_id: str, *, until: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        explicit={
            "proactive_subject_suppressed": {f"plan:{plan_id}": {"reason": "cooldown", "until": until.isoformat()}}
        }
    )


def _make_spine_message() -> SimpleNamespace:
    return SimpleNamespace(
        trigger_type="long_silence",
        strategy="gentle_nudge",
        message_id="msg-1",
        cooldown_until=None,
        frequency_tag="1_per_day",
        title="好久不见",
        body="你的计划还在等你。",
        deep_link="/chat?source=recall",
        reasoning="recall",
        value_reason="接续",
        effort_estimate="5 分钟",
        deadline_pressure_label="",
        recall_score=0.8,
    )


def test_spine_recall_blocked_after_nudge_rejection_nail():
    """反例钉（任务级跨渠道补发）：拒绝后 spine 渠道补发必须被拦。"""
    future_until = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=20)
    fake_session_local = _FakeSessionCM(
        lambda: _FakeScalarResult([_subject_suppressed_row(PLAN_ID, until=future_until)])
    )

    mock_spine_cls = MagicMock()
    mock_spine = MagicMock()
    mock_spine.on_recall_check = AsyncMock()
    mock_spine.build_recall_notification = AsyncMock(return_value=_make_spine_message())
    mock_spine_cls.return_value = mock_spine

    mock_notif_create = AsyncMock()
    mock_notif_cls = MagicMock()
    mock_notif_cls.create = staticmethod(mock_notif_create)

    patches = [
        patch("app.core.cache.cache_service.redis", MagicMock()),
        patch("app.db.session.AsyncSessionLocal", return_value=fake_session_local),
        patch("app.signals.spine_orchestrator.get_spine_orchestrator", mock_spine_cls),
        patch("app.services.notification_service.NotificationService", mock_notif_cls),
    ]
    for p in patches:
        p.start()
    try:
        from app.core.celery_tasks import recall_notification_task

        result = recall_notification_task(USER_ID, "long_silence", json.dumps({"plan_id": PLAN_ID}))
    finally:
        for p in reversed(patches):
            p.stop()

    assert result["status"] == "skipped"
    assert result["reason"] == "cross_channel_suppressed"
    assert result["budget"]["channel"] == "spine"
    assert result["budget"]["prompt_key"]
    # 生成源头抑制：spine 构建、trace、投递全部不发生；闸门单读判定。
    mock_spine.build_recall_notification.assert_not_awaited()
    mock_spine.on_recall_check.assert_not_awaited()
    mock_notif_create.assert_not_awaited()
    assert fake_session_local.execute_count["count"] == 1


def test_spine_recall_allowed_stamps_budget_envelope():
    """正：spine 渠道预算内放行，通知 data 携带可追预算信封。

    一审 C-1 修复钉（生产者半场）：上下文 subject 键（task_id/plan_id）必须
    直落通知 data——suggestion-action 提取面读这些键升格跨渠道抑制。
    """
    fake_session_local = _FakeSessionCM(lambda: _FakeScalarResult([]))

    mock_spine_cls = MagicMock()
    mock_spine = MagicMock()
    mock_spine.on_recall_check = AsyncMock()
    mock_spine.build_recall_notification = AsyncMock(return_value=_make_spine_message())
    mock_spine_cls.return_value = mock_spine

    captured: dict = {}

    async def _capture_create(_session, _user_id, payload, **kwargs):
        captured["data"] = payload.data
        return SimpleNamespace(id="n-1")

    mock_notif_cls = MagicMock()
    mock_notif_cls.create = staticmethod(_capture_create)

    patches = [
        patch("app.core.cache.cache_service.redis", MagicMock()),
        patch("app.db.session.AsyncSessionLocal", return_value=fake_session_local),
        patch("app.signals.spine_orchestrator.get_spine_orchestrator", mock_spine_cls),
        patch("app.services.notification_service.NotificationService", mock_notif_cls),
    ]
    for p in patches:
        p.start()
    try:
        from app.core.celery_tasks import recall_notification_task

        result = recall_notification_task(USER_ID, "long_silence", json.dumps({"task_id": TASK_ID}))
    finally:
        for p in reversed(patches):
            p.stop()

    assert result["status"] == "sent"
    # C-1 修复钉：上下文 subject 键直落 data（修复前固定形状不含该键）。
    assert captured["data"]["task_id"] == TASK_ID
    envelope = captured["data"]["proactive_budget"]
    assert envelope["channel"] == "spine"
    assert envelope["suggestion_type"] == "recall_notification"
    assert envelope["prompt_kind"] == "long_silence"
    assert envelope["subject"] == {"task": TASK_ID}
    assert envelope["prompt_key"] == derive_prompt_key(
        ProactiveChannel.SPINE, "recall_notification", f"task:{TASK_ID}", prompt_kind="long_silence"
    )
    assert isinstance(envelope["daily_cap"], int)
    assert "decided_at" in envelope


def test_comeback_nudge_stamps_budget_envelope():
    """正：nudge 渠道放行路径同样盖预算信封（两渠道同一审计形状）。"""
    payload = {
        "title": "好久不见",
        "message": "你的计算机网络冲刺还剩 3 天。",
        "days_away": 6,
        "days_remaining": 3,
        "subject": "计算机网络",
        "plan_id": PLAN_ID,
    }

    fake_session_local = _FakeSessionCM(lambda: _FakeScalarResult([]))

    mock_runtime_cls = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.get_comeback_context = AsyncMock(return_value=dict(payload))
    mock_runtime_cls.return_value = mock_runtime

    mock_prefs_cls = MagicMock()
    mock_prefs = MagicMock()
    mock_prefs.get = AsyncMock(return_value={"aurora_stimulation_mode": "auto"})
    mock_prefs_cls.return_value = mock_prefs

    captured: dict = {}

    async def _capture_create(_session, _user_id, notification, push_via_websocket=True):
        captured["notification"] = notification
        return SimpleNamespace(id="n-2")

    mock_notif_cls = MagicMock()
    mock_notif_cls.create = staticmethod(_capture_create)

    patches = [
        patch("app.db.session.AsyncSessionLocal", return_value=fake_session_local),
        patch("app.aurora.runtime_v1.service.AuroraRuntimeV1Service", mock_runtime_cls),
        patch("app.aurora.runtime_v1.user_preferences.AuroraUserPreferencesService", mock_prefs_cls),
        patch("app.services.notification_service.NotificationService", mock_notif_cls),
    ]
    for p in patches:
        p.start()
    try:
        from app.core.celery_tasks import comeback_nudge_task

        result = comeback_nudge_task(USER_ID)
    finally:
        for p in reversed(patches):
            p.stop()

    assert result["status"] == "sent"
    notification = captured["notification"]
    envelope = notification.data["proactive_budget"]
    assert envelope["channel"] == "nudge"
    assert envelope["suggestion_type"] == "comeback_nudge"
    assert envelope["subject"] == {"plan": PLAN_ID}
    assert envelope["prompt_key"]
    assert envelope["daily_cap"] == 3


def test_comeback_nudge_blocked_by_effect_dedup_second_dispatch():
    """一次 effect 钉（任务级）：同 prompt_key 已投递（账本行信封匹配）→ 跳过。"""
    from app.aurora.proactive.unified_budget import (
        ProactiveBudgetRequest,
        build_budget_envelope,
    )

    payload = {
        "title": "好久不见",
        "message": "你的计算机网络冲刺还剩 3 天。",
        "days_away": 6,
        "days_remaining": 3,
        "subject": "计算机网络",
        "plan_id": PLAN_ID,
    }
    request = ProactiveBudgetRequest(
        user_id=USER_ID,
        channel=ProactiveChannel.NUDGE,
        suggestion_type="comeback_nudge",
        subject_refs={"plan": PLAN_ID},
        prompt_kind="comeback",
    )
    first_decision = SimpleNamespace(
        allowed=True,
        reason="allowed",
        prompt_key=derive_prompt_key(
            ProactiveChannel.NUDGE, "comeback_nudge", f"plan:{PLAN_ID}", prompt_kind="comeback"
        ),
        details={"count": 0, "cap": 3, "decided_at": datetime.now(UTC).replace(tzinfo=None).isoformat()},
    )
    ledger_row = SimpleNamespace(
        data={
            "proactive_budget": build_budget_envelope(
                channel=ProactiveChannel.NUDGE, request=request, decision=first_decision
            )
        }
    )

    reads = iter(
        [
            _FakeScalarResult([]),  # P-03 类型/subject 联合读：未抑制
            _FakeScalarResult([ledger_row]),  # effect 去重读：同 prompt_key 已在账本
        ]
    )
    fake_session_local = _FakeSessionCM(lambda: next(reads, _FakeScalarResult([])))

    mock_runtime_cls = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.get_comeback_context = AsyncMock(return_value=dict(payload))
    mock_runtime_cls.return_value = mock_runtime

    mock_prefs_cls = MagicMock()
    mock_prefs = MagicMock()
    mock_prefs.get = AsyncMock(return_value={"aurora_stimulation_mode": "auto"})
    mock_prefs_cls.return_value = mock_prefs

    mock_notif_create = AsyncMock()
    mock_notif_cls = MagicMock()
    mock_notif_cls.create = staticmethod(mock_notif_create)

    patches = [
        patch("app.db.session.AsyncSessionLocal", return_value=fake_session_local),
        patch("app.aurora.runtime_v1.service.AuroraRuntimeV1Service", mock_runtime_cls),
        patch("app.aurora.runtime_v1.user_preferences.AuroraUserPreferencesService", mock_prefs_cls),
        patch("app.services.notification_service.NotificationService", mock_notif_cls),
    ]
    for p in patches:
        p.start()
    try:
        from app.core.celery_tasks import comeback_nudge_task

        result = comeback_nudge_task(USER_ID)
    finally:
        for p in reversed(patches):
            p.stop()

    assert result["status"] == "skipped"
    assert result["reason"] == "already_effected"
    assert result["budget"]["prompt_key"] == first_decision.prompt_key
    mock_notif_create.assert_not_awaited()
