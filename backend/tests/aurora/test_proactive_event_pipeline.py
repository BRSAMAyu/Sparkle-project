"""
P-01 — Event-trigger + Suppression Pipeline 单测（R2 返修版）。

钉住验收三条（卡定义原文）：
1. 被 mute/quiet/cooldown 抑制 = **100%**（六抑制器 × 七触发全组合逐一断言，
   加上 cap/rejection/novelty 同样全组合；store 故障 → state_unavailable
   全抑制，fail-closed 有 BrokenRedis 探针钉死）；
2. 无需 LLM 的事件不调用模型 —— 管线全程 mock 掉 LLM 客户端，断言调用数 = 0
   （本卡灵魂），辅以包源码静态扫描；
3. shadow metrics 可审 —— 每事件决定 + 抑制原因完整落
   record / 环形缓冲 / sink / Prometheus 计数。

R2 追加钉桩：
- P0-1 通电：attach() 假总线 smoke（subscribe 参数）+ app/main.py lifespan
  接线 liveness（启动路径源断言 + 假总线回调→管线的端到端）；
- P1-1 fail-closed：BrokenRedis / 损坏文档 / 无 redis → decision=suppressed、
  投递 spy 零调用；
- P1-2 可达性：deadline/overdue 用**真实 producer 序列化器**
  （TaskStartedEvent/TaskAbandoned.to_dict，due_at ← Task.due_date）构造
  载荷；run.awaiting_user 为 RESERVED 形状（outbox→RabbitMQ，本流暂无
  发布点，分类器按词表形状兼容预留）；
- P2：死名（chat.message.sent / task.status_changed）断言不在白名单且
  不产生触发；proactive_action_disabled 总闸分支覆盖（杀死 R2-M3 存活变异）。

测试完全 hermetic：内存 FakeRedis、无 DB、无网络、无 Celery。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from prometheus_client import REGISTRY

from app.aurora.proactive import (
    LIVE_SCOPE,
    ProactiveDecisionRecord,
    ProactiveEventPipeline,
    ProactiveSuppressionStore,
    ProactiveStateUnavailable,
    ProactiveTrigger,
    SHADOW_SCOPE,
    SuppressionSnapshot,
    WHITELISTED_EVENT_NAMES,
    classify_event,
    evaluate_suppression,
)
from app.aurora.proactive.metrics import PROACTIVE_PIPELINE_DECISIONS_TOTAL  # noqa: F401 — 确保计数器已注册
from app.core.event_bus import TaskAbandoned, TaskStartedEvent
from app.core.event_registry import REGISTERED_EVENT_NAMES


def _now() -> datetime:
    return datetime(2026, 9, 20, 12, 0, 0)  # 固定 naive-UTC：正午，非静默窗


def _due_soon(now: datetime) -> str:
    """日期粒度临期日（Task.due_date 序列化形态：今天+1，ISO date 串）。"""
    return (now + timedelta(days=1)).date().isoformat()


def _due_past(now: datetime) -> str:
    """日期粒度过期日（Task.due_date 序列化形态：昨天）。"""
    return (now - timedelta(days=1)).date().isoformat()


# --- 事件样例 ----------------------------------------------------------------
# 六类 reachable 触发全部用**真实 producer 序列化器**构造（R2 P1-2）：
# task.started/task.abandoned ← TaskStartedEvent/TaskAbandoned.to_dict()
# （task_service 实际发布路径）；focus/plan.health 为 service 层 to_dict 同形。

_USER = "11111111-1111-1111-1111-111111111111"


def _reachable_trigger_events(now: datetime) -> list[tuple[str, dict[str, Any], ProactiveTrigger]]:
    """本流（sparkle_events）真实可达的六类触发。"""
    return [
        (
            "task.started+due_at(real-serializer)",
            TaskStartedEvent(
                user_id=_USER, task_id="t-deadline", due_at=_due_soon(now)
            ).to_dict(),
            ProactiveTrigger.DEADLINE,
        ),
        (
            "task.abandoned(past-due, real-serializer)",
            TaskAbandoned(user_id=_USER, task_id="t-overdue", due_at=_due_past(now)).to_dict(),
            ProactiveTrigger.OVERDUE,
        ),
        (
            "focus.session.completed(incomplete)",
            {
                "event_type": "focus.session.completed",
                "user_id": _USER,
                "session_id": "s-missed",
                "completed": False,
            },
            ProactiveTrigger.SLOT_MISSED,
        ),
        (
            "task.started(real-serializer)",
            TaskStartedEvent(user_id=_USER, task_id="t-active").to_dict(),
            ProactiveTrigger.USER_ACTIVE,
        ),
        (
            "task.completed",
            {"event_type": "task.completed", "user_id": _USER, "task_id": "t-upstream"},
            ProactiveTrigger.UPSTREAM_COMPLETED,
        ),
        (
            "plan.health.alerted",
            {"event_type": "plan.health.alerted", "user_id": _USER, "plan_id": "p-stalled"},
            ProactiveTrigger.GOAL_STALLED,
        ),
    ]


def _seven_trigger_events(now: datetime) -> list[tuple[str, dict[str, Any], ProactiveTrigger]]:
    """六类 reachable + 一类 RESERVED（run_awaiting，形状兼容预留）。"""
    events = _reachable_trigger_events(now)
    events.append(
        (
            "RESERVED run.status_changed(AWAITING_USER)@bridge",
            {
                "event_type": "run.status_changed",
                "user_id": _USER,
                "run_id": "r-await",
                "run": {"to_status": "AWAITING_USER"},
            },
            ProactiveTrigger.RUN_AWAITING,
        )
    )
    return events


def _subject_of(event: dict[str, Any]) -> str:
    for key in ("task_id", "session_id", "plan_id", "run_id"):
        if event.get(key):
            return str(event[key])
    return ""


# --- FakeRedis（duck-typing：只实现 store 用到的 get/set） -------------------


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.data[key] = value
        return True


def _make_pipeline(*, shadow: bool = True, redis: FakeRedis | None = None, **kwargs: Any) -> ProactiveEventPipeline:
    return ProactiveEventPipeline(redis=redis if redis is not None else FakeRedis(), shadow=shadow, **kwargs)


@pytest.fixture(autouse=True)
def _no_quiet_hours_by_default(monkeypatch: pytest.MonkeyPatch):
    """默认关掉 quiet hours，避免挂钟时间让 notify 断言波动（quiet 行为有专属确定性测试）。"""
    from app.aurora.proactive import config as proactive_config

    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False)


ALL_TRIGGER_VALUES = [t.value for t in ProactiveTrigger]
SUPPRESSION_CASES = (
    "quiet_hours",
    "mute",
    "daily_cap",
    "cooldown",
    "recent_rejection",
    "novelty",
)


# ===========================================================================
# 1. 白名单与词表冻结一致性（零新事件名的结构性保证）
# ===========================================================================


def test_whitelist_names_in_frozen_vocabulary():
    """白名单里属于 39 冻结词表的名字必须逐字存在于词表（防 typo 漂移）。"""
    frozen_names = {
        "task.created",
        "task.started",
        "task.completed",
        "task.abandoned",
        "run.status_changed",
        "run.awaiting_user",
        "galaxy.study.recorded",
    }
    assert frozen_names <= REGISTERED_EVENT_NAMES
    assert frozen_names <= WHITELISTED_EVENT_NAMES
    # 旧名（sparkle_events 既有 producer）也必须在白名单内。
    assert {"focus.session.completed", "plan.health.alerted"} <= WHITELISTED_EVENT_NAMES


def test_dead_names_removed_from_whitelist():
    """R2 P2：查无 producer 的死名不得出现在白名单，也不得产生触发。"""
    assert "chat.message.sent" not in WHITELISTED_EVENT_NAMES
    assert "task.status_changed" not in WHITELISTED_EVENT_NAMES
    now = _now()
    assert classify_event({"event_type": "chat.message.sent", "user_id": _USER}, now=now) is None
    assert (
        classify_event(
            {"event_type": "task.status_changed", "user_id": _USER, "task_id": "t", "to_status": "OVERDUE"}, now=now
        )
        is None
    )


def test_real_serializer_shapes_are_reachable_triggers():
    """R2 P1-2：真实 producer 序列化器 → 分类器的可达性往返。

    task_service 发布路径 = TaskStartedEvent/TaskAbandoned(...).to_dict()，
    due_at 序列化自 Task.due_date（Date 粒度）。钉住：
    - 临期 due_at → DEADLINE；过期 due_at 放弃 → OVERDUE；
    - 无到期日 → 不出 due_at 键（载荷向后兼容），task.started 归 user_active、
      task.abandoned 归 goal_stalled。
    """
    now = _now()
    # 临期（明天）→ deadline
    started = TaskStartedEvent(user_id=_USER, task_id="t1", due_at=_due_soon(now)).to_dict()
    assert classify_event(started, now=now).trigger is ProactiveTrigger.DEADLINE
    # 过期（昨天）放弃 → overdue
    abandoned = TaskAbandoned(user_id=_USER, task_id="t2", due_at=_due_past(now)).to_dict()
    assert classify_event(abandoned, now=now).trigger is ProactiveTrigger.OVERDUE
    # 无到期日：载荷无 due_at 键（向后兼容），不误判
    plain_started = TaskStartedEvent(user_id=_USER, task_id="t3").to_dict()
    assert "due_at" not in plain_started
    assert classify_event(plain_started, now=now).trigger is ProactiveTrigger.USER_ACTIVE
    plain_abandoned = TaskAbandoned(user_id=_USER, task_id="t4").to_dict()
    assert "due_at" not in plain_abandoned
    assert classify_event(plain_abandoned, now=now).trigger is ProactiveTrigger.GOAL_STALLED
    # 今天到期仍算 deadline（日期粒度：due 日未过）
    today = TaskStartedEvent(user_id=_USER, task_id="t5", due_at=now.date().isoformat()).to_dict()
    assert classify_event(today, now=now).trigger is ProactiveTrigger.DEADLINE


def test_unknown_event_names_are_ignored():
    """白名单外事件一律忽略：分类器不得产生触发。"""
    now = _now()
    for event_type in ("totally.unknown", "aurora.wake.requested", "plan.created", "srl.phase.transition"):
        assert classify_event({"event_type": event_type, "user_id": "u", "task_id": "t"}, now=now) is None


async def test_unknown_events_produce_no_record():
    """管线级：白名单外事件返回 None、零计数、零状态写入。"""
    redis = FakeRedis()
    pipeline = _make_pipeline(shadow=True, redis=redis)
    assert await pipeline.handle_event({"event_type": "not.in.whitelist", "user_id": _USER}) is None
    assert len(pipeline.recent_records) == 0
    assert redis.data == {}


# ===========================================================================
# 2. 七类触发各一例：事件穿过整条管线（shadow would-notify）
# ===========================================================================


@pytest.mark.parametrize(
    "case_index",
    range(7),
    ids=[
        "deadline",
        "overdue",
        "slot_missed",
        "user_active",
        "upstream_completed",
        "goal_stalled",
        "RESERVED-run_awaiting",
    ],
)
async def test_each_of_seven_triggers_reaches_pipeline(case_index: int):
    """七类各一例穿管线（前六类为本流真实可达形状；第 7 类为 RESERVED 形状）。"""
    now = _now()
    label, event, expected_trigger = _seven_trigger_events(now)[case_index]

    sinked: list[ProactiveDecisionRecord] = []

    async def sink(record: ProactiveDecisionRecord) -> None:
        sinked.append(record)

    pipeline = _make_pipeline(shadow=True, sink=sink)
    record = await pipeline.handle_event(event)

    assert record is not None, f"{label} 应产生决定记录"
    assert record.decision == "notify", f"{label} 应 would-notify，实际 {record.decision}/{record.reason}"
    assert record.trigger == expected_trigger.value
    assert record.shadow is True
    assert record.reason is None and record.step is None
    assert sinked and sinked[-1].decision == "notify"


async def test_run_awaiting_user_registry_name_also_triggers():
    """RESERVED（R2 P1-2 如实登记）：``run.awaiting_user``（词表专名）与
    run.status_changed(AWAITING_*) 的**形状兼容**由分类器钉住——但该等价信号
    当前不在 Python sparkle_events 流上（producer 走 event_outbox → 网关
    RabbitMQ exchange），等 outbox→Redis 桥落地即生效。两例用不同 user：
    同 trigger 的 cooldown 会让第二条被抑制（属预期语义）。
    """
    now = _now()
    pipeline = _make_pipeline(shadow=True)
    for i, (event_name, extra) in enumerate(
        (
            ("run.awaiting_user", {"run_id": "r1"}),
            ("run.status_changed", {"run_id": "r2", "run": {"to_status": "AWAITING_APPROVAL"}}),
        )
    ):
        record = await pipeline.handle_event(
            {"event_type": event_name, "user_id": f"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa{i}", **extra}
        )
        assert record is not None and record.decision == "notify", event_name
        assert record.trigger == ProactiveTrigger.RUN_AWAITING.value


async def test_run_step_progress_is_never_a_trigger():
    """EXECUTING 步进（run.status_changed → EXECUTING）高频，绝不能成为触发。"""
    now = _now()
    pipeline = _make_pipeline(shadow=True)
    record = await pipeline.handle_event(
        {
            "event_type": "run.status_changed",
            "user_id": _USER,
            "run_id": "r-step",
            "run": {"to_status": "EXECUTING"},
        }
    )
    assert record is None


# ===========================================================================
# 3. 六抑制器 × 七触发：100% 抑制（acceptance 原文）
# ===========================================================================


def _suppressed_snapshot(reason: str, now: datetime, trigger: ProactiveTrigger) -> SuppressionSnapshot:
    """构造让指定抑制器必然命中的快照。"""
    trigger_name = trigger.value
    common: dict[str, Any] = {"now": now, "quiet_window": None}
    if reason == "quiet_hours":
        return SuppressionSnapshot(now=now, quiet_window=("00:00", "23:59"), timezone="UTC")
    if reason == "mute":
        return SuppressionSnapshot(**common, muted_triggers=frozenset({trigger_name}))
    if reason == "daily_cap":
        return SuppressionSnapshot(**common, daily_count=3, daily_cap=3)
    if reason == "cooldown":
        return SuppressionSnapshot(**common, last_notify_at={trigger_name: now - timedelta(minutes=10)})
    if reason == "recent_rejection":
        return SuppressionSnapshot(**common, recent_rejections={trigger_name: 2}, rejection_threshold=2)
    if reason == "novelty":
        return SuppressionSnapshot(**common, seen_subject_keys=frozenset({f"{trigger_name}:same-subject"}))
    raise AssertionError(reason)


@pytest.mark.parametrize("trigger_value", ALL_TRIGGER_VALUES)
@pytest.mark.parametrize("reason", SUPPRESSION_CASES)
def test_every_suppressor_suppresses_every_trigger_100pct(trigger_value: str, reason: str):
    """任一抑制器对任一触发都 100% 抑制，reason 与 step 精确钉住（6×7 全组合）。"""
    now = _now()
    snapshot = _suppressed_snapshot(reason, now, ProactiveTrigger(trigger_value))
    decision = evaluate_suppression(
        trigger=ProactiveTrigger(trigger_value), subject_key="same-subject", snapshot=snapshot
    )
    assert decision.allowed is False
    assert decision.reason == reason
    assert decision.step == reason


@pytest.mark.parametrize("trigger_value", ALL_TRIGGER_VALUES)
@pytest.mark.parametrize("reason", ("mute", "daily_cap", "cooldown", "recent_rejection", "novelty"))
async def test_pipeline_level_suppression_100pct(trigger_value: str, reason: str):
    """管线级复验：预置状态后 handle_event 抑制，且 reason/step 逐字一致。"""
    now = _now()
    trigger = ProactiveTrigger(trigger_value)
    label, template_event, _expected = _seven_trigger_events(now)[ALL_TRIGGER_VALUES.index(trigger_value)]
    event = dict(template_event)
    event["user_id"] = "22222222-2222-2222-2222-222222222222"
    subject = _subject_of(event)

    redis = FakeRedis()
    store = ProactiveSuppressionStore(redis)

    if reason in ("daily_cap", "cooldown", "recent_rejection", "novelty"):
        if reason == "daily_cap":
            for _ in range(3):
                await store.record_notification(
                    event["user_id"], trigger=trigger_value, subject_key="seed", scope=SHADOW_SCOPE, now=now - timedelta(minutes=30)
                )
        elif reason == "cooldown":
            await store.record_notification(
                event["user_id"], trigger=trigger_value, subject_key="seed", scope=SHADOW_SCOPE, now=now - timedelta(minutes=10)
            )
        elif reason == "recent_rejection":
            for _ in range(2):
                await store.record_rejection(event["user_id"], trigger=trigger_value, scope=SHADOW_SCOPE, now=now - timedelta(days=1))
        elif reason == "novelty":
            # 冷却已过（5h > 240min）但新颖性窗口（48h）内已提醒过同 subject。
            await store.record_notification(
                event["user_id"], trigger=trigger_value, subject_key=subject, scope=SHADOW_SCOPE, now=now - timedelta(hours=5)
            )
    elif reason == "mute":
        import json as _json

        key = store.state_key(SHADOW_SCOPE, event["user_id"])
        redis.data[key] = _json.dumps({"muted_triggers": [trigger_value]})

    pipeline = _make_pipeline(shadow=True, redis=redis)
    record = await pipeline.handle_event(event)

    assert record is not None and record.decision == "suppressed", f"{reason}×{trigger_value} 必须 100% 抑制"
    assert record.reason == reason
    assert record.step == reason


async def test_quiet_hours_suppresses_via_settings_window():
    """quiet hours 管线级：全天静默窗配置下七类事件全部抑制。"""
    from app.aurora.proactive import config as proactive_config

    now = _now()
    redis = FakeRedis()
    pipeline = _make_pipeline(shadow=True, redis=redis)
    user = "77777777-7777-7777-7777-777777777777"

    monkey = pytest.MonkeyPatch()
    try:
        monkey.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", True)
        monkey.setattr(proactive_config, "PROACTIVE_QUIET_START", "00:00")
        monkey.setattr(proactive_config, "PROACTIVE_QUIET_END", "23:59")
        monkey.setattr(proactive_config, "PROACTIVE_QUIET_TIMEZONE", "UTC")
        for _label, event, _trigger in _seven_trigger_events(now):
            probe = dict(event)
            probe["user_id"] = user
            record = await pipeline.handle_event(probe)
            assert record is not None and record.decision == "suppressed"
            assert record.reason == "quiet_hours"
    finally:
        monkey.undo()


# ===========================================================================
# 4. shadow 审计完整性（决定 + 原因 + 指标）
# ===========================================================================


async def test_shadow_record_completeness_and_metrics():
    now = _now()
    redis = FakeRedis()
    sinked: list[ProactiveDecisionRecord] = []

    async def sink(record: ProactiveDecisionRecord) -> None:
        sinked.append(record)

    pipeline = _make_pipeline(shadow=True, redis=redis, sink=sink)
    user = "33333333-3333-3333-3333-333333333333"

    # 关掉 cooldown（旋钮归零），让 cap 成为唯一约束、notify 路径连续可达。
    from app.aurora.proactive import config as proactive_config

    monkey = pytest.MonkeyPatch()
    monkey.setattr(proactive_config, "PROACTIVE_COOLDOWN_MINUTES", 0)
    try:
        first = await pipeline.handle_event({"event_type": "task.completed", "user_id": user, "task_id": "t1"})
        await pipeline.handle_event({"event_type": "task.completed", "user_id": user, "task_id": "t2"})
        await pipeline.handle_event({"event_type": "task.completed", "user_id": user, "task_id": "t3"})
        fourth = await pipeline.handle_event(
            {"event_type": "task.completed", "user_id": user, "task_id": "t4"}  # cap=3 满
        )
    finally:
        monkey.undo()

    # --- notify 记录完整性 ---
    assert first is not None and first.decision == "notify"
    assert first.event_name == "task.completed"
    assert first.trigger == "upstream_completed"
    assert first.user_id == user
    assert first.reason is None and first.step is None
    assert first.subject_key == "t1"
    assert first.shadow is True
    assert first.occurred_at
    assert "correlation" in first.details

    # --- cap 抑制记录完整性（第 4 条）---
    assert fourth is not None and fourth.decision == "suppressed"
    assert fourth.reason == "daily_cap" and fourth.step == "daily_cap"
    assert fourth.details.get("count") == 3 and fourth.details.get("cap") == 3

    # --- 环形缓冲与 sink 完整 ---
    assert len(pipeline.recent_records) == 4
    assert len(sinked) == 4
    assert [r.decision for r in sinked] == ["notify", "notify", "notify", "suppressed"]

    # --- Prometheus 计数可审 ---
    notify_count = REGISTRY.get_sample_value(
        "sparkle_proactive_pipeline_decisions_total",
        {"trigger": "upstream_completed", "event_name": "task.completed", "decision": "notify", "reason": "none"},
    )
    cap_count = REGISTRY.get_sample_value(
        "sparkle_proactive_pipeline_decisions_total",
        {
            "trigger": "upstream_completed",
            "event_name": "task.completed",
            "decision": "suppressed",
            "reason": "daily_cap",
        },
    )
    assert notify_count is not None and notify_count >= 1.0
    assert cap_count is not None and cap_count >= 1.0


async def test_shadow_does_not_touch_live_scope_state():
    """shadow would-notify 只写 shadow scope，live 状态零污染。"""
    now = _now()
    redis = FakeRedis()
    store = ProactiveSuppressionStore(redis)
    pipeline = _make_pipeline(shadow=True, redis=redis)
    user = "44444444-4444-4444-4444-444444444444"

    for i in range(5):
        await pipeline.handle_event({"event_type": "plan.health.alerted", "user_id": user, "plan_id": f"p{i}"})

    assert store.state_key(LIVE_SCOPE, user) not in redis.data
    assert store.state_key(SHADOW_SCOPE, user) in redis.data


async def test_missing_user_id_is_ignored_without_state_writes():
    redis = FakeRedis()
    pipeline = _make_pipeline(shadow=True, redis=redis)
    record = await pipeline.handle_event({"event_type": "task.completed", "task_id": "t-no-user"})
    assert record is not None and record.decision == "ignored"
    assert record.reason == "missing_user_id"
    assert redis.data == {}, "ignored 事件不得写任何状态"


async def test_duplicate_events_consume_novelty_in_shadow():
    """shadow 下同一 (trigger, subject) 重复事件：第一条 would-notify，第二条 novelty 抑制。

    cooldown 旋钮归零：保证第二条命中的是 novelty（文档顺序 cooldown 先于
    novelty，若不归零会先报 cooldown）。
    """
    from app.aurora.proactive import config as proactive_config

    redis = FakeRedis()
    pipeline = _make_pipeline(shadow=True, redis=redis)
    user = "66666666-6666-6666-6666-666666666666"
    event = {"event_type": "task.completed", "user_id": user, "task_id": "same-task"}

    monkey = pytest.MonkeyPatch()
    monkey.setattr(proactive_config, "PROACTIVE_COOLDOWN_MINUTES", 0)
    try:
        first = await pipeline.handle_event(event)
        second = await pipeline.handle_event(event)
    finally:
        monkey.undo()
    assert first.decision == "notify"
    assert second.decision == "suppressed"
    assert second.reason == "novelty"


# ===========================================================================
# 5. 零 LLM（本卡灵魂）：mock 掉 LLM 客户端断言调用数 = 0 + 静态扫描
# ===========================================================================


async def test_pipeline_never_calls_llm(monkeypatch: pytest.MonkeyPatch):
    """全管线（七类触发 × shadow/live、notify+抑制路径）零 LLM 调用。"""
    import app.services.llm_service as llm_module

    llm_mock = MagicMock()
    impl_mock = MagicMock()
    monkeypatch.setattr(llm_module, "llm_service", llm_mock, raising=True)
    monkeypatch.setattr(llm_module, "llm_service_impl", impl_mock, raising=True)

    now = _now()
    pipeline_shadow = _make_pipeline(shadow=True)

    async def fake_deliver(user_id: str, classification, event_name: str) -> bool:
        return True

    pipeline_live = _make_pipeline(shadow=False, deliver=fake_deliver)

    for label, event, _trigger in _seven_trigger_events(now):
        await pipeline_shadow.handle_event(event)
        await pipeline_live.handle_event(event)
    # live + 抑制路径（cap 灌满后再来一条）
    user = "88888888-8888-8888-8888-888888888888"
    for i in range(5):
        await pipeline_live.handle_event({"event_type": "task.completed", "user_id": user, "task_id": f"x{i}"})

    assert llm_mock.call_count == 0, f"llm_service 被调用 {llm_mock.call_count} 次"
    assert impl_mock.call_count == 0, f"llm_service_impl 被调用 {impl_mock.call_count} 次"
    assert llm_mock.method_calls == []
    assert impl_mock.method_calls == []


def test_proactive_package_source_has_no_llm_references():
    """静态扫描：管线模块源码不出现任何 LLM 客户端引用。"""
    import pathlib

    pkg_dir = pathlib.Path(__file__).resolve().parents[2] / "app" / "aurora" / "proactive"
    banned = ("llm_service", "llm_router", "llm_client", "LLMClient", "openai", "anthropic", "chat_complet")
    for path in sorted(pkg_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} 含 LLM 引用 {token!r}"


# ===========================================================================
# 6. live 模式与状态消费
# ===========================================================================


async def test_live_mode_delivers_and_consumes_state():
    from app.aurora.proactive import config as proactive_config

    redis = FakeRedis()
    delivered: list[tuple[str, str]] = []

    async def deliver(user_id: str, classification, event_name: str) -> bool:
        delivered.append((user_id, classification.trigger.value))
        return True

    pipeline = _make_pipeline(shadow=False, redis=redis, deliver=deliver)
    user = "55555555-5555-5555-5555-555555555555"

    # cooldown 归零，让 daily_cap（=3）成为唯一约束。
    monkey = pytest.MonkeyPatch()
    monkey.setattr(proactive_config, "PROACTIVE_COOLDOWN_MINUTES", 0)
    try:
        records = []
        for i in range(5):
            records.append(
                await pipeline.handle_event({"event_type": "plan.health.alerted", "user_id": user, "plan_id": f"p{i}"})
            )
    finally:
        monkey.undo()

    assert len(delivered) == 3, "cap=3：只应真发 3 条"
    assert all(r.decision == "notify" for r in records[:3])
    assert all(r.decision == "suppressed" and r.reason == "daily_cap" for r in records[3:])
    assert records[0].details.get("delivered") is True
    # live 模式状态写进 live scope
    assert ProactiveSuppressionStore(redis).state_key(LIVE_SCOPE, user) in redis.data


# ===========================================================================
# 7. 确定性（同输入同输出）
# ===========================================================================


def test_suppression_is_deterministic():
    now = _now()
    snapshot = SuppressionSnapshot(
        now=now,
        quiet_window=("22:00", "08:00"),
        timezone="Asia/Shanghai",
        daily_count=3,
        daily_cap=3,
    )
    results = {
        evaluate_suppression(trigger=ProactiveTrigger.DEADLINE, subject_key="s", snapshot=snapshot).reason
        for _ in range(20)
    }
    assert results == {"daily_cap"}


def test_quiet_hours_window_semantics():
    """跨午夜静默窗（22:00–08:00）边界语义（Asia/Shanghai = UTC+8 判定）。"""
    window = ("22:00", "08:00")
    tz = "Asia/Shanghai"

    def at_utc(hour: int, minute: int = 0) -> SuppressionSnapshot:
        return SuppressionSnapshot(now=datetime(2026, 9, 20, hour, minute), quiet_window=window, timezone=tz)

    # 本地 06:00（UTC 22:00 前一日）→ 静默
    assert evaluate_suppression(trigger=ProactiveTrigger.DEADLINE, subject_key="", snapshot=at_utc(22)).reason == "quiet_hours"
    # 本地 23:30（UTC 15:30）→ 静默
    assert evaluate_suppression(trigger=ProactiveTrigger.DEADLINE, subject_key="", snapshot=at_utc(15, 30)).reason == "quiet_hours"
    # 本地 03:00（UTC 19:00 前一日）→ 静默（跨午夜段）
    assert evaluate_suppression(trigger=ProactiveTrigger.DEADLINE, subject_key="", snapshot=at_utc(19)).reason == "quiet_hours"
    # 本地 12:00（UTC 04:00）→ 非静默
    decision = evaluate_suppression(trigger=ProactiveTrigger.DEADLINE, subject_key="", snapshot=at_utc(4))
    assert decision.allowed is True
    # 本地 18:00（UTC 10:00）→ 非静默
    decision = evaluate_suppression(trigger=ProactiveTrigger.DEADLINE, subject_key="", snapshot=at_utc(10))
    assert decision.allowed is True
    # 无效时区回退 UTC（确定性）：UTC 10:00 落在 09:00–11:00 窗内 → 静默
    fallback = SuppressionSnapshot(now=datetime(2026, 9, 20, 10, 0), quiet_window=("09:00", "11:00"), timezone="Not/AZone")
    assert evaluate_suppression(trigger=ProactiveTrigger.DEADLINE, subject_key="", snapshot=fallback).reason == "quiet_hours"


# ===========================================================================
# 8. R2 P1-1 fail-closed：store 故障 → state_unavailable 全抑制
# ===========================================================================


class BrokenRedis:
    """读必炸的 redis 探针（R2 验收员同款故障注入）。"""

    async def get(self, key: str) -> str:
        raise ConnectionError("redis down")

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        raise ConnectionError("redis down")


class CorruptRedis:
    """读得到但文档损坏（非 JSON / 非 mapping）。"""

    def __init__(self, payload: Any) -> None:
        self.payload = payload

    async def get(self, key: str) -> str:
        return self.payload

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        return True


def _deliver_spy() -> tuple[list[str], Any]:
    delivered: list[str] = []

    async def deliver(user_id: str, classification, event_name: str) -> bool:
        delivered.append(user_id)
        return True

    return delivered, deliver


@pytest.mark.parametrize("trigger_value", ALL_TRIGGER_VALUES)
async def test_broken_redis_live_fails_closed(trigger_value: str):
    """R2 P1-1 验收探针：Redis 挂 → live 模式 decision=suppressed、投递零调用。"""
    now = _now()
    _label, template_event, _trigger = _seven_trigger_events(now)[ALL_TRIGGER_VALUES.index(trigger_value)]
    event = dict(template_event)
    event["user_id"] = "99999999-9999-9999-9999-999999999999"

    delivered, deliver = _deliver_spy()
    pipeline = _make_pipeline(shadow=False, redis=BrokenRedis(), deliver=deliver)
    record = await pipeline.handle_event(event)

    assert record is not None and record.decision == "suppressed", f"Redis 故障时 {trigger_value} 必须全抑制"
    assert record.reason == "state_unavailable"
    assert record.step == "state_unavailable"
    assert delivered == [], "fail-closed：投递 spy 必须零调用"


async def test_broken_redis_shadow_fails_closed():
    """shadow 模式同样 fail-closed（诚实记录：状态不可用 ≠ would-notify）。"""
    now = _now()
    events = _seven_trigger_events(now)
    pipeline = _make_pipeline(shadow=True, redis=BrokenRedis())
    for i, (_label, event, _trigger) in enumerate(events):
        probe = dict(event)
        probe["user_id"] = f"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb{i}"
        record = await pipeline.handle_event(probe)
        assert record.decision == "suppressed" and record.reason == "state_unavailable"


async def test_corrupt_state_doc_fails_closed():
    """状态文档损坏（非 JSON）→ fail-closed，而非当作零计数放行。"""
    now = _now()
    delivered, deliver = _deliver_spy()
    pipeline = _make_pipeline(shadow=False, redis=CorruptRedis("not-json{{"), deliver=deliver)
    record = await pipeline.handle_event({"event_type": "task.completed", "user_id": _USER, "task_id": "t"})
    assert record.decision == "suppressed" and record.reason == "state_unavailable"
    assert delivered == []


async def test_missing_redis_config_fails_closed():
    """store 无 redis（未配置）→ live 模式全抑制（安全默认）。"""
    delivered, deliver = _deliver_spy()
    pipeline = ProactiveEventPipeline(store=ProactiveSuppressionStore(None), shadow=False, deliver=deliver)
    record = await pipeline.handle_event({"event_type": "task.completed", "user_id": _USER, "task_id": "t"})
    assert record.decision == "suppressed" and record.reason == "state_unavailable"
    assert delivered == []


async def test_state_unavailable_beats_all_other_steps():
    """state_unavailable 是第 0 步：即便同时满足 quiet/cap 也报 state_unavailable。"""
    snapshot = SuppressionSnapshot(
        now=_now(),
        state_unavailable=True,
        quiet_window=("00:00", "23:59"),
        timezone="UTC",
        daily_count=99,
        daily_cap=3,
    )
    decision = evaluate_suppression(trigger=ProactiveTrigger.DEADLINE, subject_key="s", snapshot=snapshot)
    assert decision.allowed is False
    assert decision.reason == "state_unavailable"


async def test_store_raises_state_unavailable_on_missing_redis():
    """store 层契约：无 redis 时 build_snapshot 显式抛 ProactiveStateUnavailable。"""
    store = ProactiveSuppressionStore(None)
    with pytest.raises(ProactiveStateUnavailable):
        await store.build_snapshot(_USER, scope=LIVE_SCOPE, now=_now())


async def test_fresh_user_empty_doc_is_not_unavailable():
    """键不存在（新用户零态）是合法空态，不得误报 state_unavailable。"""
    store = ProactiveSuppressionStore(FakeRedis())
    snapshot = await store.build_snapshot(_USER, scope=SHADOW_SCOPE, now=_now(), quiet_window=None)
    assert snapshot.state_unavailable is False
    assert snapshot.daily_count == 0


# ===========================================================================
# 9. R2 P2：proactive_action_disabled 总闸分支（杀死 R2-M3 存活变异）
# ===========================================================================


@pytest.mark.parametrize("trigger_value", ALL_TRIGGER_VALUES)
def test_master_switch_proactive_action_disabled_suppresses_all(trigger_value: str):
    """Aurora control-surface 总闸开启 → 七类触发全部抑制（reason=mute）。"""
    now = _now()
    snapshot = SuppressionSnapshot(now=now, quiet_window=None, proactive_action_disabled=True)
    decision = evaluate_suppression(
        trigger=ProactiveTrigger(trigger_value), subject_key="s", snapshot=snapshot
    )
    assert decision.allowed is False
    assert decision.reason == "mute"
    assert decision.step == "mute"
    assert decision.details.get("mute_scope") == "proactive_follow_up"


async def test_master_switch_pipeline_level():
    """管线级：状态文档置总闸 → suppressed；关闭恢复放行。"""
    import json as _json

    now = _now()
    redis = FakeRedis()
    pipeline = _make_pipeline(shadow=True, redis=redis)
    user = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    key = ProactiveSuppressionStore.state_key(SHADOW_SCOPE, user)

    redis.data[key] = _json.dumps({"proactive_action_disabled": True})
    record = await pipeline.handle_event({"event_type": "task.completed", "user_id": user, "task_id": "t1"})
    assert record.decision == "suppressed" and record.reason == "mute"
    assert record.details.get("mute_scope") == "proactive_follow_up"

    redis.data[key] = _json.dumps({"proactive_action_disabled": False})
    record = await pipeline.handle_event({"event_type": "task.completed", "user_id": user, "task_id": "t2"})
    assert record.decision == "notify"


# ===========================================================================
# 10. R2 P0-1 通电：attach() 消费者组接入 + main.py lifespan 接线
# ===========================================================================


class FakeBus:
    """假总线：记录 subscribe 参数并捕获回调，供接线端到端验证。"""

    def __init__(self) -> None:
        self.calls: dict[str, Any] = {}
        self.callback = None

    async def subscribe(self, *, stream: str, group_name: str, consumer_name: str, callback) -> None:
        self.calls = {
            "stream": stream,
            "group_name": group_name,
            "consumer_name": consumer_name,
        }
        self.callback = callback


async def test_attach_subscribes_with_expected_group():
    """attach() 的消费者组接入面：stream/group/callback 逐字钉住（R2 F1）。"""
    bus = FakeBus()
    pipeline = _make_pipeline(shadow=True)
    await pipeline.attach(bus)  # type: ignore[arg-type]

    assert bus.calls["stream"] == "sparkle_events"
    assert bus.calls["group_name"] == "aurora_proactive_pipeline"
    assert "aurora-proactive" in bus.calls["consumer_name"]
    assert callable(bus.callback)


async def test_attach_wired_callback_processes_real_event():
    """接线端到端：bus 回调 → handle_event → 决定记录（attach 的 callback 真的通）。"""
    bus = FakeBus()
    sinked: list[ProactiveDecisionRecord] = []

    async def sink(record: ProactiveDecisionRecord) -> None:
        sinked.append(record)

    pipeline = _make_pipeline(shadow=True, sink=sink)
    await pipeline.attach(bus)  # type: ignore[arg-type]

    now = _now()
    _label, event, expected_trigger = _reachable_trigger_events(now)[4]  # task.completed
    await bus.callback(dict(event))

    assert len(sinked) == 1
    assert sinked[0].decision == "notify"
    assert sinked[0].trigger == expected_trigger.value
    # 回调吞异常：白名单外事件经回调也不得抛出
    await bus.callback({"event_type": "not.in.whitelist", "user_id": _USER})
    assert len(sinked) == 1


def test_main_lifespan_wires_proactive_pipeline():
    """启动路径 liveness（R2 P0-1）：app/main.py lifespan 消费者区必须接线。

    app.main 可导入（既有 test_startup_smoke 先例），此处断言 lifespan 函数
    源码含 ProactiveEventPipeline 实例化 + attach(event_bus) + 关停段取消——
    即接线在启动路径上，而非孤立的库函数。
    """
    import inspect

    import app.main as main_mod

    lifespan_src = inspect.getsource(main_mod.lifespan)
    assert "ProactiveEventPipeline(" in lifespan_src
    assert "proactive_pipeline.attach(event_bus)" in lifespan_src
    assert "proactive_pipeline_task" in lifespan_src  # 关停段取消句柄
    # 接线在消费者启动区（与其它消费者同款 redis 守卫内）
    assert 'if cache_service.redis and event_bus is not None:' in lifespan_src
