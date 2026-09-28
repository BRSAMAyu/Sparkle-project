"""V4-P01 一审 C-1 整改：spine↔nudge 跨渠道 subject 抑制端到端（真实链）。

一审 F1 亲证的结构性失效：``recall_notification_task`` 是 ``recall_notification``
类型通知的唯一生产者，其 ``Notification.data`` 固定形状不含 ``plan_id``/
``task_id``——suggestion-action 提取面（``subject_refs_from_payload``）读不到
上下文键 → spine 卡拒绝/静音后 ``record_cross_channel_suppression`` 零写入、
同 plan nudge 照常放行。原证据测试反向半场直接喂合成载荷
``{"task_id", "plan_id"}``——真实 spine 通知永不携带该形状，「API→提取→写库」
一环被跳过。

本文件钉**真实链**，双向矩阵对称（每方向一测，全链零合成载荷）：

1. **真实生产者形状**：经真实 ``recall_notification_task`` /
   ``comeback_nudge_task`` 任务体（外呼 mock + 闸门读面 fake session——与
   ``test_p01_budget_channel_wiring`` 同款纪律，闸门自身语义不在此重复）捕获
   任务真实构造的 ``NotificationCreate``，再经真实 ``NotificationService.create``
   落库（``push_via_websocket=False``）——账本行 data 与生产者逐字段一致；
2. **真实 API**：真实 ``record_suggestion_action`` handler（归属/动作校验、
   类型级 + subject 级写库全真）；
3. **真实写库判定**：P-03 服务读回 + 统一预算闸门 ``evaluate``（真实 DB）。

矩阵：

- spine 卡静音（mute_type）→ 同 plan nudge 被 ``cross_channel_suppressed`` 拦；
- nudge 卡拒绝（ignore_today）→ 同 subject spine 被 ``cross_channel_suppressed`` 拦。

mutation 判据：摘除 C-1 两处修复（生产者键落 data + 提取面读预算信封）后，
spine→nudge 方向必红；单摘任一半场由另一半场兜底（设计即双保险，两半场
各自另有独立钉：接线测试 data 键钉 / 闸门测试信封提取钉）。

时间纪律：生产者半场 quiet 挂钟关断（平台基线，与既有任务测试同款）；
API 写库与闸门判定用真实时钟（抑制 until=now+24h，判定时刻在其内）。
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.proactive import config as proactive_config
from app.aurora.proactive.unified_budget import (
    ProactiveBudgetRequest,
    ProactiveChannel,
    UnifiedProactiveBudgetService,
)
from app.models.plan import Plan
from app.models.plan import PlanType as PlanTypeEnum
from app.models.task import Task, TaskStatus, TaskType

PLAN_ID = "00000000-0000-0000-0000-00000000000a"
TASK_ID = "00000000-0000-0000-0000-00000000000b"


@pytest.fixture(autouse=True)
def _deterministic_knobs(monkeypatch: pytest.MonkeyPatch):
    """quiet 挂钟关断（与既有任务/闸门测试同款）+ 统一预算闸门显式开。"""
    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False)
    monkeypatch.setattr(proactive_config, "PROACTIVE_UNIFIED_BUDGET_ENABLED", True)


class _FakeScalarResult:
    """同时支持 scalar_one_or_none / scalars().all 两种读法（wiring 测试同款）。"""

    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None


class _FakeSessionCM:
    """按预定读序出结果、其后一律空读的假会话（闸门读面不在此验）。"""

    def __init__(self, sequenced_reads):
        self.session = AsyncMock()
        self._reads = iter(sequenced_reads)
        self.session.execute = AsyncMock(side_effect=self._execute)

    async def _execute(self, *args, **kwargs):
        try:
            return next(self._reads)
        except StopIteration:
            return _FakeScalarResult([])

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args):
        return False


def _make_spine_message() -> SimpleNamespace:
    """spine 构建产物（与 SpineOrchestrator.RecallMessage 字段面一致）。"""
    return SimpleNamespace(
        trigger_type="task_missed",
        strategy="gentle_nudge",
        message_id="msg-e2e-1",
        cooldown_until=None,
        frequency_tag="1_per_day",
        title="这张任务错过了截止时间",
        body="回来接续它。",
        deep_link="/chat?source=recall",
        reasoning="recall",
        value_reason="接续",
        effort_estimate="5 分钟",
        deadline_pressure_label="",
        recall_score=0.8,
    )


async def _seed_plan_and_task(db_session: AsyncSession, user_id) -> None:
    db_session.add(
        Plan(
            id=PLAN_ID,
            user_id=user_id,
            name="计算机网络冲刺",
            type=PlanTypeEnum.SPRINT,
            subject="计算机网络",
            target_date=date.today() + timedelta(days=3),
            is_active=True,
        )
    )
    db_session.add(
        Task(
            id=TASK_ID,
            plan_id=PLAN_ID,
            user_id=user_id,
            title="TCP 流量控制",
            type=TaskType.LEARNING,
            estimated_minutes=30,
            status=TaskStatus.PENDING,
        )
    )
    await db_session.commit()


# ── 方向一（一审 F1 失效面）：spine 卡静音 → 同 plan nudge 被拦 ──────────────


@pytest.mark.asyncio
async def test_spine_mute_blocks_same_plan_nudge_end_to_end(db_session: AsyncSession, test_user) -> None:
    """真实链：recall_notification_task 产形 → 落库 → suggestion-action 静音 →
    提取面拿到 subject → 写库 → 同 plan 的 nudge 渠道被 cross_channel_suppressed。"""
    await _seed_plan_and_task(db_session, test_user.id)

    # 1. 真实生产者半场：任务体真实构造 NotificationCreate（外呼 mock，
    #    闸门读面 fake——读序：explicit 空 → plan 未过期 → effect 空 → 负担空）。
    future_date = date.today() + timedelta(days=3)
    fake_session_local = _FakeSessionCM([_FakeScalarResult([]), _FakeScalarResult([future_date])])

    mock_spine_cls = MagicMock()
    mock_spine = MagicMock()
    mock_spine.on_recall_check = AsyncMock()
    mock_spine.build_recall_notification = AsyncMock(return_value=_make_spine_message())
    mock_spine_cls.return_value = mock_spine

    captured: dict = {}

    async def _capture_create(_session, _user_id, payload, **kwargs):
        captured["create"] = payload
        return SimpleNamespace(id="captured-spine")

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

        # 任务经 _run_async 自建 loop——放工作线程跑（本测试已在 asyncio loop 上）。
        result = await asyncio.to_thread(
            recall_notification_task,
            str(test_user.id),
            "task_missed",
            json.dumps({"plan_id": PLAN_ID, "task_id": TASK_ID}),
        )
    finally:
        for p in reversed(patches):
            p.stop()

    assert result["status"] == "sent"
    # 生产者修复钉：真实构造的 data 携带上下文 subject 键 + 信封同一 subject。
    spine_create = captured["create"]
    assert spine_create.data["plan_id"] == PLAN_ID
    assert spine_create.data["task_id"] == TASK_ID
    assert spine_create.data["proactive_budget"]["subject"] == {"plan": PLAN_ID, "task": TASK_ID}

    # 2. 真实落库：真实 NotificationService 把生产者产物写进账本（零手工拼装）。
    from app.services.notification_service import NotificationService

    notification = await NotificationService.create(db_session, test_user.id, spine_create, push_via_websocket=False)

    # 3. 真实 API：用户对 spine 卡「不再提醒此类」。
    from app.api.v1.notification_center import record_suggestion_action
    from app.schemas.unified_notification import SuggestionActionRequest

    api_result = await record_suggestion_action(
        notification.id,
        SuggestionActionRequest(action="mute_type"),
        current_user=test_user,
        db=db_session,
    )

    # 4. C-1 核心断言：提取面从真实 spine data 拿到 subject（修复前为空 dict
    #    ——零写入、同 plan nudge 照常放行，即一审 F1）。
    assert set(api_result["subject_suppression"]) == {f"plan:{PLAN_ID}", f"task:{TASK_ID}"}
    assert api_result["subject_suppression"][f"plan:{PLAN_ID}"]["reason"] == "muted"

    # 5. 真实写库读回：subject 级抑制确实在 P-03 权威里。
    from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackService

    stored = await ProactiveSuggestionFeedbackService(db_session).get_subject_suppression(
        test_user.id, f"plan:{PLAN_ID}"
    )
    assert stored is not None
    assert stored["reason"] == "muted"

    # 6. 双向矩阵·方向一：同 plan nudge 渠道被跨渠道抑制拦（非类型级——
    #    mute 的是 recall_notification，nudge 类型不在其中）。
    decision = await UnifiedProactiveBudgetService(db_session).evaluate(
        ProactiveBudgetRequest(
            user_id=test_user.id,
            channel=ProactiveChannel.NUDGE,
            suggestion_type="comeback_nudge",
            subject_refs={"plan": PLAN_ID},
            prompt_kind="comeback",
        )
    )
    assert decision.allowed is False
    assert decision.reason == "cross_channel_suppressed"
    assert decision.details["suppression"]["reason"] == "muted"


# ── 方向二：nudge 卡拒绝 → 同 subject spine 被拦（对称半场，同为真实链）──────


@pytest.mark.asyncio
async def test_nudge_rejection_blocks_same_subject_spine_end_to_end(db_session: AsyncSession, test_user) -> None:
    """真实链：comeback_nudge_task 产形 → 落库 → suggestion-action 拒绝 →
    同 plan 的 spine 渠道被 cross_channel_suppressed。"""
    await _seed_plan_and_task(db_session, test_user.id)

    # 1. 真实生产者半场（nudge 渠道既有 data 本就带 plan_id——本方向同时
    #    钉「nudge→spine 方向端到端」与产形一致性）。
    payload = {
        "title": "好久不见",
        "message": "你的计算机网络冲刺还剩 3 天。",
        "days_away": 6,
        "days_remaining": 3,
        "subject": "计算机网络",
        "plan_id": PLAN_ID,
    }
    fake_session_local = _FakeSessionCM([])

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
        captured["create"] = notification
        return SimpleNamespace(id="captured-nudge")

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

        result = await asyncio.to_thread(comeback_nudge_task, str(test_user.id))
    finally:
        for p in reversed(patches):
            p.stop()

    assert result["status"] == "sent"
    nudge_create = captured["create"]
    assert nudge_create.data["plan_id"] == PLAN_ID
    assert nudge_create.data["proactive_budget"]["subject"] == {"plan": PLAN_ID}

    # 2. 真实落库 + 真实 API：「今天不再看」。
    from app.services.notification_service import NotificationService

    notification = await NotificationService.create(db_session, test_user.id, nudge_create, push_via_websocket=False)

    from app.api.v1.notification_center import record_suggestion_action
    from app.schemas.unified_notification import SuggestionActionRequest

    api_result = await record_suggestion_action(
        notification.id,
        SuggestionActionRequest(action="ignore_today"),
        current_user=test_user,
        db=db_session,
    )
    assert set(api_result["subject_suppression"]) == {f"plan:{PLAN_ID}"}

    # 3. 双向矩阵·方向二：同 subject spine 渠道被跨渠道抑制拦（真实 DB 闸门）。
    decision = await UnifiedProactiveBudgetService(db_session).evaluate(
        ProactiveBudgetRequest(
            user_id=test_user.id,
            channel=ProactiveChannel.SPINE,
            suggestion_type="recall_notification",
            subject_refs={"plan": PLAN_ID},
            prompt_kind="task_missed",
        )
    )
    assert decision.allowed is False
    assert decision.reason == "cross_channel_suppressed"
    assert decision.details["suppression"]["reason"] == "cooldown"
