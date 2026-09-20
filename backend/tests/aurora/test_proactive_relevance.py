"""
P-02 — Proactive Relevance Decision（NO_ACTION 语义层）单测。

钉住验收（卡定义原文）：
1. **20+ suppression/relevance cases 违规 = 0**：26 对「该提醒 vs 不该提醒」
   镜像场景（52 个确定性案例）逐一断言——不该提醒侧 100% 以预期结构化
   reason 短路（duplicate / already_aware / no_new_information /
   not_actionable），该提醒侧 100% 放行；每个案例跑两遍钉死确定性。
2. **管线接入位置**：抑制链之后、状态消费与出口之前——no_action 不消耗
   cap/cooldown/novelty、投递 spy 零调用、reason 落 record/metrics（有界
   label）；上下文读失败 → context_unavailable fail-closed 不打扰。
3. **零 LLM**：纯函数判定 + 确定性摘要/起点派生；模块源码静态扫描 +
   出口 spy 双重钉死。

**确定性纪律（吸取 P-01 cooldown 时钟炸弹教训）**：纯函数层全部使用固定
naive-UTC 时刻（与墙钟无关）；管线集成层的预置状态一律以**运行时真实时刻
为基准取相对偏移**，任何时刻运行行为一致。

测试完全 hermetic：内存 FakeRedis、无 DB、无网络、无 Celery、无 LLM。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from prometheus_client import REGISTRY

from app.aurora.proactive import (
    LIVE_SCOPE,
    RELEVANCE_REASONS,
    SHADOW_SCOPE,
    ProactiveEventPipeline,
    ProactiveRelevanceContextUnavailable,
    ProactiveRelevanceStore,
    ProactiveSuppressionStore,
    ProactiveTrigger,
    RelevanceContext,
    derive_information_digest,
    derive_information_onset,
    evaluate_relevance,
)
from app.core.event_bus import TaskAbandoned, TaskStartedEvent

# ---------------------------------------------------------------------------
# 固定时刻（纯函数层专用：与墙钟零耦合）
# ---------------------------------------------------------------------------

NOW = datetime(2026, 9, 21, 12, 0, 0)  # 固定 naive-UTC 正午


def T(**kw: int) -> datetime:
    """NOW 的确定性偏移。"""
    return NOW + timedelta(**kw)


@pytest.fixture(autouse=True)
def _no_quiet_hours_by_default(monkeypatch: pytest.MonkeyPatch):
    """关闭 quiet hours：真实时刻可能落在本地静默窗内，会让管线测试在
    抑制链就被拦下而到不了语义层（quiet 行为由 P-01 专属测试钉住）。"""
    from app.aurora.proactive import config as proactive_config

    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False)


# ---------------------------------------------------------------------------
# Part 1 — 成对 scenarios（26 对镜像对；卡面验收的核心证据）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pair:
    """一对镜像场景：act_ctx = 该提醒；quiet_ctx = 不该提醒（带预期 reason）。"""

    id: str
    trigger: ProactiveTrigger
    act_ctx: RelevanceContext
    quiet_ctx: RelevanceContext
    quiet_reason: str


def _p(
    pid: str,
    trigger: ProactiveTrigger,
    quiet_reason: str,
    **sides: Any,
) -> Pair:
    """便捷构造：``act=RelevanceContext(...)`` / ``quiet=RelevanceContext(...)``。"""
    return Pair(
        id=pid,
        trigger=trigger,
        act_ctx=sides["act"],
        quiet_ctx=sides["quiet"],
        quiet_reason=quiet_reason,
    )


PAIRS: list[Pair] = [
    # ---- 卡面原例族 -------------------------------------------------------
    _p(
        "01-deadline-unseen-3d-vs-viewed-1h-ago",
        ProactiveTrigger.DEADLINE,
        "already_aware",
        # 该提醒：临期窗三天前开启，用户三天没看任务页
        act=RelevanceContext(
            subject_last_viewed_at=T(days=-3),
            current_digest="d-deadline",
            subject_state_changed_at=T(days=-1),  # 临期窗开启 = due-2d
        ),
        # 不该提醒：用户一小时前刚看过任务页，其后任务无实质变化
        quiet=RelevanceContext(
            subject_last_viewed_at=T(hours=-1),
            current_digest="d-deadline",
            subject_state_changed_at=T(days=-1),
        ),
    ),
    _p(
        "02-overdue-unseen-vs-viewed-after-due",
        ProactiveTrigger.OVERDUE,
        "already_aware",
        # 该提醒：逾期已发生（昨日），用户自那以后没看过
        act=RelevanceContext(
            subject_last_viewed_at=T(days=-2),
            current_digest="d-overdue",
            subject_state_changed_at=T(days=-1),  # due 日结束 = 逾期起点
        ),
        # 不该提醒：逾期但用户已知（今晨刚看过任务页且其后无新信息）
        quiet=RelevanceContext(
            subject_last_viewed_at=T(hours=-5),
            current_digest="d-overdue",
            subject_state_changed_at=T(days=-1),
        ),
    ),
    # ---- already_aware：查看/交互时刻 vs 状态起点 ------------------------
    _p(
        "03-deadline-interaction-after-onset",
        ProactiveTrigger.DEADLINE,
        "already_aware",
        act=RelevanceContext(
            subject_last_interaction_at=T(days=-2),
            current_digest="d",
            subject_state_changed_at=T(hours=-12),
        ),
        quiet=RelevanceContext(
            subject_last_interaction_at=T(hours=-2),  # 两小时前刚推进过该任务
            current_digest="d",
            subject_state_changed_at=T(hours=-12),
        ),
    ),
    _p(
        "04-overdue-boundary-equal-is-aware",
        ProactiveTrigger.OVERDUE,
        "already_aware",
        # 该提醒：查看发生在状态起点之前 1 小时（逾期发生在其查看之后）
        act=RelevanceContext(
            subject_last_viewed_at=T(hours=-4),
            current_digest="d",
            subject_state_changed_at=T(hours=-3),
        ),
        # 边界：恰在状态起点那一刻看过 = 已知晓（确定性约定，>= 判定）
        quiet=RelevanceContext(
            subject_last_viewed_at=T(hours=-3),
            current_digest="d",
            subject_state_changed_at=T(hours=-3),
        ),
    ),
    _p(
        "05-upstream-completed-user-did-it-themselves",
        ProactiveTrigger.UPSTREAM_COMPLETED,
        "already_aware",
        act=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(hours=-1),
        ),
        # 不该提醒：完成就是用户自己做的（交互时刻 = 完成时刻）
        quiet=RelevanceContext(
            subject_last_interaction_at=T(hours=-1),
            current_digest="d",
            subject_state_changed_at=T(hours=-1),
        ),
    ),
    _p(
        "06-upstream-completed-viewed-before-vs-after",
        ProactiveTrigger.UPSTREAM_COMPLETED,
        "already_aware",
        act=RelevanceContext(
            subject_last_viewed_at=T(hours=-2),
            current_digest="d",
            subject_state_changed_at=T(hours=-1),
        ),
        quiet=RelevanceContext(
            subject_last_viewed_at=T(minutes=-30),
            current_digest="d",
            subject_state_changed_at=T(hours=-1),
        ),
    ),
    _p(
        "07-run-awaiting-user-on-run-page",
        ProactiveTrigger.RUN_AWAITING,
        "already_aware",
        act=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(minutes=-40),
        ),
        # 不该提醒：用户已经在运行详情页上（正盯着等它进入 awaiting）
        quiet=RelevanceContext(
            subject_last_viewed_at=T(minutes=-10),
            current_digest="d",
            subject_state_changed_at=T(minutes=-40),
        ),
    ),
    _p(
        "08-goal-stalled-viewed-after-alert",
        ProactiveTrigger.GOAL_STALLED,
        "already_aware",
        act=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(hours=-6),
        ),
        quiet=RelevanceContext(
            subject_last_viewed_at=T(hours=-1),
            current_digest="d",
            subject_state_changed_at=T(hours=-6),
        ),
    ),
    _p(
        "09-slot-missed-already-rescheduled",
        ProactiveTrigger.SLOT_MISSED,
        "already_aware",
        act=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(hours=-2),  # 时段在两小时前错过
        ),
        # 不该提醒：用户已经自己补救过（重排了计划 = 错过后的交互）
        quiet=RelevanceContext(
            subject_last_interaction_at=T(hours=-1),
            current_digest="d",
            subject_state_changed_at=T(hours=-2),
        ),
    ),
    _p(
        "10-user-active-own-action-covers-stored-change",
        ProactiveTrigger.USER_ACTIVE,
        "already_aware",
        act=RelevanceContext(current_digest="", subject_state_changed_at=None),
        # 不该提醒：subject 两小时前有实质变化（已落存储），用户此刻的动作
        # （交互=现在）说明他对当前状态知情
        quiet=RelevanceContext(
            subject_last_interaction_at=NOW,
            current_digest="",
            subject_state_changed_at=T(hours=-2),
        ),
    ),
    _p(
        "11-goal-stalled-aware-via-latest-of-view-and-interaction",
        ProactiveTrigger.GOAL_STALLED,
        "already_aware",
        act=RelevanceContext(
            subject_last_viewed_at=T(days=-1),
            current_digest="d",
            subject_state_changed_at=T(hours=-10),
        ),
        # 不该提醒：查看较早、但交互较晚——取 max(查看, 交互) ≥ 起点
        quiet=RelevanceContext(
            subject_last_viewed_at=T(days=-1),
            subject_last_interaction_at=T(hours=-2),
            current_digest="d",
            subject_state_changed_at=T(hours=-10),
        ),
    ),
    # ---- duplicate：内容级重复（与频控 novelty 互补：TTL 过期仍拦截）-----
    _p(
        "12-deadline-same-content-beyond-novelty-ttl",
        ProactiveTrigger.DEADLINE,
        "duplicate",
        act=RelevanceContext(
            current_digest="due=2026-09-22",
            subject_state_changed_at=T(days=-1),
        ),
        # 不该提醒：48h 新颖性窗口早已过期（频控放行），但 due 未变——
        # 提醒内容与上次逐字相同 = 我们在重复自己
        quiet=RelevanceContext(
            last_reminder_at=T(days=-4),
            last_reminder_digest="due=2026-09-22",
            current_digest="due=2026-09-22",
            subject_state_changed_at=T(days=-1),
        ),
    ),
    _p(
        "13-overdue-same-due-refire",
        ProactiveTrigger.OVERDUE,
        "duplicate",
        act=RelevanceContext(
            current_digest="due=2026-09-19",
            subject_state_changed_at=T(days=-2),
        ),
        quiet=RelevanceContext(
            last_reminder_at=T(hours=-30),
            last_reminder_digest="due=2026-09-19",
            current_digest="due=2026-09-19",
            subject_state_changed_at=T(days=-2),
        ),
    ),
    _p(
        "14-run-awaiting-same-run-same-status",
        ProactiveTrigger.RUN_AWAITING,
        "duplicate",
        act=RelevanceContext(
            current_digest="run=r1|to_status=AWAITING_USER",
            subject_state_changed_at=T(hours=-1),
        ),
        quiet=RelevanceContext(
            last_reminder_at=T(minutes=-90),
            last_reminder_digest="run=r1|to_status=AWAITING_USER",
            current_digest="run=r1|to_status=AWAITING_USER",
            subject_state_changed_at=T(hours=-1),
        ),
    ),
    _p(
        "15-slot-missed-same-session",
        ProactiveTrigger.SLOT_MISSED,
        "duplicate",
        act=RelevanceContext(
            current_digest="session=s1",
            subject_state_changed_at=T(hours=-2),
        ),
        quiet=RelevanceContext(
            last_reminder_at=T(hours=-1),
            last_reminder_digest="session=s1",
            current_digest="session=s1",
            subject_state_changed_at=T(hours=-2),
        ),
    ),
    # ---- no_new_information：当前状态早已告知，其后无新变化 --------------
    _p(
        "16-overdue-reminded-after-due-different-wording",
        ProactiveTrigger.OVERDUE,
        "no_new_information",
        act=RelevanceContext(
            current_digest="d-v2",
            subject_state_changed_at=T(days=-1),
        ),
        # 不该提醒：due 之后已提醒过（措辞不同→摘要不同→duplicate 不中），
        # 但事实（当前状态）早已告知且其后无变化
        quiet=RelevanceContext(
            last_reminder_at=T(hours=-6),
            last_reminder_digest="d-v1",
            current_digest="d-v2",
            subject_state_changed_at=T(days=-1),
        ),
    ),
    _p(
        "17-goal-stalled-nothing-since-last-reminder",
        ProactiveTrigger.GOAL_STALLED,
        "no_new_information",
        act=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(days=-2),
        ),
        quiet=RelevanceContext(
            last_reminder_at=T(hours=-20),
            last_reminder_digest="d-old",
            current_digest="d",
            subject_state_changed_at=T(days=-2),
        ),
    ),
    _p(
        "18-upstream-completed-told-after-change",
        ProactiveTrigger.UPSTREAM_COMPLETED,
        "no_new_information",
        act=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(hours=-3),
        ),
        quiet=RelevanceContext(
            last_reminder_at=T(hours=-2),
            last_reminder_digest="d-old",
            current_digest="d",
            subject_state_changed_at=T(hours=-3),
        ),
    ),
    _p(
        "19-run-awaiting-status-moved-but-already-told",
        ProactiveTrigger.RUN_AWAITING,
        "no_new_information",
        act=RelevanceContext(
            current_digest="run=r1|to_status=AWAITING_APPROVAL",
            subject_state_changed_at=T(hours=-4),
        ),
        quiet=RelevanceContext(
            last_reminder_at=T(hours=-1),
            last_reminder_digest="run=r1|to_status=AWAITING_USER",
            current_digest="run=r1|to_status=AWAITING_APPROVAL",
            subject_state_changed_at=T(hours=-4),
        ),
    ),
    _p(
        "20-slot-missed-told-right-after-miss",
        ProactiveTrigger.SLOT_MISSED,
        "no_new_information",
        act=RelevanceContext(
            current_digest="session=s1",
            subject_state_changed_at=T(hours=-3),
        ),
        quiet=RelevanceContext(
            last_reminder_at=T(hours=-2),
            last_reminder_digest="other",
            current_digest="session=s1",
            subject_state_changed_at=T(hours=-3),
        ),
    ),
    _p(
        "21-goal-stalled-told-then-realert-same-onset",
        ProactiveTrigger.GOAL_STALLED,
        "no_new_information",
        act=RelevanceContext(
            current_digest="alert#2",
            subject_state_changed_at=T(days=-1),
        ),
        # 重发告警但状态起点未前移（同一次告警的重投递形态）→ 无新信息
        quiet=RelevanceContext(
            last_reminder_at=T(hours=-12),
            last_reminder_digest="alert#1",
            current_digest="alert#2",
            subject_state_changed_at=T(days=-1),
        ),
    ),
    # ---- not_actionable：有新信息但点开后无可执行下一步 ------------------
    _p(
        "22-goal-stalled-archived-plan",
        ProactiveTrigger.GOAL_STALLED,
        "not_actionable",
        act=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(hours=-1),
            has_actionable_step=True,
        ),
        # 不该提醒：计划已归档，用户无任何可执行动作
        quiet=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(hours=-1),
            has_actionable_step=False,
        ),
    ),
    _p(
        "23-overdue-archived-task",
        ProactiveTrigger.OVERDUE,
        "not_actionable",
        act=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(days=-1),
            has_actionable_step=True,
        ),
        # 不该提醒：任务已取消/归档——"仅逾期不够"（卡面原话）
        quiet=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(days=-1),
            has_actionable_step=False,
        ),
    ),
    _p(
        "24-deadline-cancelled-task",
        ProactiveTrigger.DEADLINE,
        "not_actionable",
        act=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(days=-1),
            has_actionable_step=True,
        ),
        quiet=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(days=-1),
            has_actionable_step=False,
        ),
    ),
    _p(
        "25-run-awaiting-terminal-run",
        ProactiveTrigger.RUN_AWAITING,
        "not_actionable",
        act=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(minutes=-30),
            has_actionable_step=True,
        ),
        quiet=RelevanceContext(
            current_digest="d",
            subject_state_changed_at=T(minutes=-30),
            has_actionable_step=False,  # 运行已被其他入口处理，无待确认动作
        ),
    ),
    # ---- 镜像补充：新信息到达时刻决定一切 --------------------------------
    _p(
        "26-overdue-due-extended-after-reminder",
        ProactiveTrigger.OVERDUE,
        "no_new_information",
        act=RelevanceContext(
            last_reminder_at=T(days=-3),  # 很久前提醒过（旧 due）
            last_reminder_digest="due=2026-09-18",
            current_digest="due=2026-09-23",  # due 已顺延 → 新信息
            subject_state_changed_at=T(hours=-2),  # 变化发生在提醒之后
            has_actionable_step=True,
        ),
        # 不该提醒：提醒发生在状态变化之后（用户被改变后告知过）且无其后变化
        quiet=RelevanceContext(
            last_reminder_at=T(hours=-1),
            last_reminder_digest="due=2026-09-18",
            current_digest="due=2026-09-23",
            subject_state_changed_at=T(hours=-2),
            has_actionable_step=True,
        ),
    ),
]


def test_acceptance_pair_count_and_reason_coverage():
    """验收门槛自检：≥20 对镜像场景；四类语义 reason 全覆盖。"""
    assert len(PAIRS) >= 20, f"成对场景不足 20：{len(PAIRS)}"
    reasons = {p.quiet_reason for p in PAIRS}
    assert reasons == {
        "duplicate",
        "already_aware",
        "no_new_information",
        "not_actionable",
    }, f"reason 覆盖不全：{reasons}"
    # 词表封闭：任何 quiet_reason 都必须在封闭词表内
    assert reasons <= set(RELEVANCE_REASONS)


@pytest.mark.parametrize("pair", PAIRS, ids=[p.id for p in PAIRS])
def test_mirror_pair_act_vs_no_action(pair: Pair):
    """每对镜像场景：该提醒侧 100% 放行；不该提醒侧 100% 以预期 reason 短路。"""
    act = evaluate_relevance(trigger=pair.trigger, context=pair.act_ctx)
    assert act.allowed is True, f"[{pair.id}] 该提醒侧被误拦：{act.reason}/{dict(act.details)}"
    assert act.reason is None

    quiet = evaluate_relevance(trigger=pair.trigger, context=pair.quiet_ctx)
    assert quiet.suppressed is True, f"[{pair.id}] 不该提醒侧被打扰（违规！）"
    assert quiet.reason == pair.quiet_reason, f"[{pair.id}] reason 不符：预期 {pair.quiet_reason}，实际 {quiet.reason}"
    assert quiet.reason in RELEVANCE_REASONS


@pytest.mark.parametrize("pair", PAIRS, ids=[p.id for p in PAIRS])
def test_mirror_pair_determinism(pair: Pair):
    """确定性：同一输入跑两遍，裁决逐字段一致。"""
    assert evaluate_relevance(trigger=pair.trigger, context=pair.act_ctx) == evaluate_relevance(
        trigger=pair.trigger, context=pair.act_ctx
    )
    assert evaluate_relevance(trigger=pair.trigger, context=pair.quiet_ctx) == evaluate_relevance(
        trigger=pair.trigger, context=pair.quiet_ctx
    )


def test_card_example_overdue_known_user_is_never_disturbed():
    """卡面灵魂句直证：仅逾期不够——逾期但用户已知且无新信息 = 不打扰。"""
    ctx = RelevanceContext(
        subject_last_viewed_at=T(hours=-1),
        current_digest="d",
        subject_state_changed_at=T(days=-1),
    )
    decision = evaluate_relevance(trigger=ProactiveTrigger.OVERDUE, context=ctx)
    assert decision.reason == "already_aware"


# ---------------------------------------------------------------------------
# Part 2 — 确定性派生：digest / onset
# ---------------------------------------------------------------------------


def test_digest_is_deterministic_and_subject_scoped():
    e = {"due_at": "2026-09-22"}
    d1 = derive_information_digest(ProactiveTrigger.DEADLINE, "t1", e)
    assert d1 == derive_information_digest(ProactiveTrigger.DEADLINE, "t1", e)
    # 同内容不同 subject → 摘要不同（永不跨 subject 碰撞）
    assert d1 != derive_information_digest(ProactiveTrigger.DEADLINE, "t2", e)
    # 内容变化 → 摘要变化（新信息可被识别）
    assert d1 != derive_information_digest(ProactiveTrigger.DEADLINE, "t1", {"due_at": "2026-09-23"})


def test_digest_empty_for_user_active_and_fieldless_payload():
    assert derive_information_digest(ProactiveTrigger.USER_ACTIVE, "t1", {"task_id": "t1"}) == ""
    assert derive_information_digest(ProactiveTrigger.GOAL_STALLED, "", {}) == ""


def test_onset_deadline_window_entry():
    # due=2026-09-23 → 临期窗开启 = 2026-09-21 00:00（due-2d 零点）
    onset = derive_information_onset(ProactiveTrigger.DEADLINE, {"due_at": "2026-09-23"}, now=NOW)
    assert onset == datetime(2026, 9, 21, 0, 0, 0)


def test_onset_overdue_starts_after_due_day():
    onset = derive_information_onset(ProactiveTrigger.OVERDUE, {"due_at": "2026-09-20"}, now=NOW)
    assert onset == datetime(2026, 9, 21, 0, 0, 0)  # due 日次日零点


def test_onset_fact_triggers_use_payload_timestamp():
    onset = derive_information_onset(ProactiveTrigger.UPSTREAM_COMPLETED, {"timestamp": "2026-09-21T10:30:00"}, now=NOW)
    assert onset == datetime(2026, 9, 21, 10, 30, 0)
    assert derive_information_onset(ProactiveTrigger.GOAL_STALLED, {}, now=NOW) is None


def test_onset_user_active_is_none():
    assert derive_information_onset(ProactiveTrigger.USER_ACTIVE, {"timestamp": NOW.isoformat()}, now=NOW) is None


def test_digest_with_real_producer_serializer():
    """真实 producer 序列化形状（TaskStartedEvent）→ 摘要/起点可派生。"""
    event = TaskStartedEvent(user_id="u", task_id="t9", due_at=(NOW + timedelta(days=1)).date().isoformat()).to_dict()
    digest = derive_information_digest(ProactiveTrigger.DEADLINE, "t9", event)
    assert digest
    onset = derive_information_onset(ProactiveTrigger.DEADLINE, event, now=NOW)
    assert onset is not None and onset < NOW  # 窗口已开启


def test_real_serializer_overdue_abandoned():
    event = TaskAbandoned(user_id="u", task_id="t8", due_at=(NOW - timedelta(days=1)).date().isoformat()).to_dict()
    onset = derive_information_onset(ProactiveTrigger.OVERDUE, event, now=NOW)
    assert onset == datetime.combine((NOW - timedelta(days=1)).date(), datetime.min.time()) + timedelta(days=1)


# ---------------------------------------------------------------------------
# Part 3 — 上下文存储（fail-closed 读语义 / scope 隔离 / 合法空态）
# ---------------------------------------------------------------------------


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def get(self, key: str):
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.data[key] = value


class BrokenRedis:
    async def get(self, key: str):
        raise RuntimeError("redis down")

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        raise RuntimeError("redis down")


async def test_store_empty_state_is_valid_zero():
    """键不存在 = 合法空态（新用户零历史），不是故障。"""
    store = ProactiveRelevanceStore(FakeRedis())
    ctx = await store.build_context("u1", "t1", scope=SHADOW_SCOPE)
    assert ctx == RelevanceContext()  # 全缺省 → 判定层放行


async def test_store_roundtrip_reminder_and_view():
    store = ProactiveRelevanceStore(FakeRedis())
    await store.record_reminder("u1", "t1", digest="abc123", at=T(hours=-2), scope=LIVE_SCOPE)
    await store.record_subject_view("u1", "t1", at=T(hours=-1), scope=LIVE_SCOPE)
    ctx = await store.build_context("u1", "t1", scope=LIVE_SCOPE)
    assert ctx.last_reminder_digest == "abc123"
    assert ctx.last_reminder_at == T(hours=-2)
    assert ctx.subject_last_viewed_at == T(hours=-1)


async def test_store_scope_isolation():
    store = ProactiveRelevanceStore(FakeRedis())
    await store.record_reminder("u1", "t1", digest="live-digest", at=T(hours=-2), scope=LIVE_SCOPE)
    ctx_shadow = await store.build_context("u1", "t1", scope=SHADOW_SCOPE)
    assert ctx_shadow.last_reminder_digest == ""  # live 写入不漏进 shadow


async def test_store_no_redis_raises_unavailable():
    store = ProactiveRelevanceStore(None)
    with pytest.raises(ProactiveRelevanceContextUnavailable):
        await store.build_context("u1", "t1", scope=LIVE_SCOPE)


async def test_store_corrupt_doc_raises_unavailable():
    redis = FakeRedis()
    redis.data[ProactiveRelevanceStore.context_key(LIVE_SCOPE, "u1")] = "not-json{{"
    store = ProactiveRelevanceStore(redis)
    with pytest.raises(ProactiveRelevanceContextUnavailable):
        await store.build_context("u1", "t1", scope=LIVE_SCOPE)


async def test_store_broken_redis_raises_unavailable():
    store = ProactiveRelevanceStore(BrokenRedis())
    with pytest.raises(ProactiveRelevanceContextUnavailable):
        await store.build_context("u1", "t1", scope=LIVE_SCOPE)


async def test_store_empty_subject_returns_zero_context():
    store = ProactiveRelevanceStore(FakeRedis())
    ctx = await store.build_context("u1", "", scope=LIVE_SCOPE)
    assert ctx == RelevanceContext()


# ---------------------------------------------------------------------------
# Part 4 — 管线集成：抑制链后 / 出口前；no_action 落 record+metrics
# ---------------------------------------------------------------------------


def _real_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _make_pipeline(shadow: bool = True, redis: Any = None, **kw: Any) -> tuple[ProactiveEventPipeline, Any]:
    redis = redis if redis is not None else FakeRedis()
    return ProactiveEventPipeline(redis=redis, shadow=shadow, **kw), redis


def _deliver_spy():
    delivered: list[tuple[str, str]] = []

    async def deliver(user_id: str, classification, event_name: str) -> bool:
        delivered.append((user_id, str(classification.trigger.value)))
        return True

    return delivered, deliver


def _prime_relevance_view(redis: FakeRedis, user: str, subject: str, viewed_at: datetime) -> None:
    key = ProactiveRelevanceStore.context_key(SHADOW_SCOPE, user)
    redis.data[key] = json.dumps({"subjects": {subject: {"last_viewed_at": viewed_at.isoformat()}}})


async def test_pipeline_already_aware_overdue_is_no_action():
    """管线级卡面原例：逾期 + 用户一小时前看过（其后无新变化）→ no_action。"""
    now = _real_now()
    due = (now - timedelta(days=2)).date().isoformat()  # 两天前到期（onset 恒早于预置查看时刻：防午夜时钟边界）
    pipeline, redis = _make_pipeline(shadow=True)
    delivered, deliver = _deliver_spy()
    pipeline._deliver = deliver
    user = "aaaaaaaa-1111-1111-1111-111111111111"

    _prime_relevance_view(redis, user, "t-known", now - timedelta(hours=1))

    event = TaskAbandoned(user_id=user, task_id="t-known", due_at=due).to_dict()
    record = await pipeline.handle_event(event)

    assert record is not None and record.decision == "no_action"
    assert record.reason == "already_aware"
    assert record.step == "relevance"
    assert record.trigger == "overdue"
    assert delivered == [], "no_action 事件绝不投递"
    # fail-closed 边界：no_action 不消耗频控状态（cap/cooldown/novelty 零写入）
    suppression_doc = redis.data.get(ProactiveSuppressionStore.state_key(SHADOW_SCOPE, user))
    assert suppression_doc is None, "no_action 不得写通知计数/seen"
    # 也不写提醒摘要（没提醒就没有摘要可记）
    relevance_doc = json.loads(redis.data[ProactiveRelevanceStore.context_key(SHADOW_SCOPE, user)])
    assert "last_reminder_at" not in relevance_doc["subjects"]["t-known"]


async def test_pipeline_overdue_unseen_still_notifies():
    """镜像侧管线级：逾期 + 用户从未看过 → 正常 would-notify（P-01 语义保留）。"""
    now = _real_now()
    due = (now - timedelta(days=2)).date().isoformat()
    pipeline, redis = _make_pipeline(shadow=True)
    delivered, deliver = _deliver_spy()
    pipeline._deliver = deliver
    user = "aaaaaaaa-2222-2222-2222-222222222222"

    record = await pipeline.handle_event(TaskAbandoned(user_id=user, task_id="t-fresh", due_at=due).to_dict())
    assert record.decision == "notify", f"实际 {record.decision}/{record.reason}"
    assert record.trigger == "overdue"
    assert delivered == [], "shadow 模式零投递（would-notify 只记录）"


async def test_pipeline_duplicate_after_prior_notify_records_reason():
    """notify 写提醒摘要 → 同内容再触发（频控放行：无 seen/无 last_notify）→ duplicate。"""
    pipeline, redis = _make_pipeline(shadow=True)
    delivered, deliver = _deliver_spy()
    pipeline._deliver = deliver
    user = "aaaaaaaa-3333-3333-3333-333333333333"
    due = (_real_now() + timedelta(days=1)).date().isoformat()
    event = TaskStartedEvent(user_id=user, task_id="t-dup", due_at=due).to_dict()

    first = await pipeline.handle_event(dict(event))
    assert first.decision == "notify"
    # 频控面状态确已消费（cap/seen 计数）——第二发的拦截面必须是语义层
    suppression_doc = json.loads(redis.data[ProactiveSuppressionStore.state_key(SHADOW_SCOPE, user)])
    assert suppression_doc.get("day_count") == 1

    # 清掉频控痕迹（模拟 48h 新颖性过期 / 冷却过期后的状态面），
    # 相关性记忆（提醒摘要）保留 → 第二发应被 duplicate 拦截。
    redis.data[ProactiveSuppressionStore.state_key(SHADOW_SCOPE, user)] = json.dumps(
        {"day": suppression_doc["day"], "day_count": 0}
    )
    second = await pipeline.handle_event(dict(event))
    assert second.decision == "no_action"
    assert second.reason == "duplicate", f"实际 {second.reason}/{dict(second.details)}"
    assert second.details.get("rule") == "digest_match"
    assert delivered == [], "shadow 模式全程零投递；两发都只走记录面"


async def test_pipeline_no_new_information_when_reminder_covers_onset():
    """提醒发生在状态起点之后且其后无变化 → no_new_information。"""
    now = _real_now()
    pipeline, redis = _make_pipeline(shadow=True)
    delivered, deliver = _deliver_spy()
    pipeline._deliver = deliver
    user = "aaaaaaaa-4444-4444-4444-444444444444"
    key = ProactiveRelevanceStore.context_key(SHADOW_SCOPE, user)
    # 预置：1 小时前就同 subject 提醒过（摘要不同 → duplicate 不中）
    redis.data[key] = json.dumps(
        {
            "subjects": {
                "p-stall": {
                    "last_reminder_at": (now - timedelta(hours=1)).isoformat(),
                    "last_reminder_digest": "older-content",
                }
            }
        }
    )
    # 告警事实起点 = 3 小时前（timestamp 相对真实时刻取偏移）
    record = await pipeline.handle_event(
        {
            "event_type": "plan.health.alerted",
            "user_id": user,
            "plan_id": "p-stall",
            "timestamp": (now - timedelta(hours=3)).isoformat(),
        }
    )
    assert record.decision == "no_action"
    assert record.reason == "no_new_information"


async def test_pipeline_not_actionable_via_payload_flag():
    """载荷显式 actionable=False 且用户未见 → not_actionable（不是误放行）。"""
    now = _real_now()
    pipeline, _ = _make_pipeline(shadow=True)
    delivered, deliver = _deliver_spy()
    pipeline._deliver = deliver
    user = "aaaaaaaa-5555-5555-5555-555555555555"
    record = await pipeline.handle_event(
        {
            "event_type": "plan.health.alerted",
            "user_id": user,
            "plan_id": "p-archived",
            "actionable": False,
            "timestamp": (now - timedelta(minutes=30)).isoformat(),
        }
    )
    assert record.decision == "no_action"
    assert record.reason == "not_actionable"
    assert delivered == []


async def test_pipeline_context_unavailable_fails_closed():
    """相关性上下文读失败 → context_unavailable fail-closed（宁可漏发）。"""
    pipeline = ProactiveEventPipeline(
        store=ProactiveSuppressionStore(FakeRedis()),  # 频控面正常
        redis=FakeRedis(),
        relevance_store=ProactiveRelevanceStore(BrokenRedis()),  # 语义面故障
        shadow=True,
    )
    delivered, deliver = _deliver_spy()
    pipeline._deliver = deliver
    user = "aaaaaaaa-6666-6666-6666-666666666666"
    record = await pipeline.handle_event({"event_type": "task.completed", "user_id": user, "task_id": "t1"})
    assert record.decision == "no_action"
    assert record.reason == "context_unavailable"
    assert record.step == "relevance"
    assert delivered == []


async def test_pipeline_no_action_does_not_consume_or_reach_delivery_live_mode():
    """live 模式下 no_action 同样零投递、零状态消费。"""
    now = _real_now()
    pipeline, redis = _make_pipeline(shadow=False)
    delivered, deliver = _deliver_spy()
    pipeline._deliver = deliver
    user = "aaaaaaaa-7777-7777-7777-777777777777"
    due = (now - timedelta(days=2)).date().isoformat()
    key = ProactiveRelevanceStore.context_key(LIVE_SCOPE, user)
    redis.data[key] = json.dumps(
        {"subjects": {"t-live": {"last_viewed_at": (now - timedelta(minutes=30)).isoformat()}}}
    )
    record = await pipeline.handle_event(TaskAbandoned(user_id=user, task_id="t-live", due_at=due).to_dict())
    assert record.decision == "no_action" and record.reason == "already_aware"
    assert record.shadow is False
    assert delivered == []
    assert ProactiveSuppressionStore.state_key(LIVE_SCOPE, user) not in redis.data


async def test_pipeline_no_action_metrics_bounded_labels():
    """no_action 落 Prometheus 计数：reason ∈ 封闭词表（有界 label）。"""
    now = _real_now()
    pipeline, redis = _make_pipeline(shadow=True)
    user = "aaaaaaaa-8888-8888-8888-888888888888"
    due = (now - timedelta(days=2)).date().isoformat()
    _prime_relevance_view(redis, user, "t-metric", now - timedelta(minutes=30))

    metric = "sparkle_proactive_pipeline_decisions_total"
    labels = {
        "trigger": "overdue",
        "event_name": "task.abandoned",
        "decision": "no_action",
        "reason": "already_aware",
    }
    before = REGISTRY.get_sample_value(metric, labels) or 0.0
    await pipeline.handle_event(TaskAbandoned(user_id=user, task_id="t-metric", due_at=due).to_dict())
    after = REGISTRY.get_sample_value(metric, labels) or 0.0
    assert after == before + 1.0


async def test_pipeline_run_awaiting_already_aware_end_to_end():
    """run_awaiting：用户已在运行页（查看晚于状态迁移）→ no_action。"""
    now = _real_now()
    pipeline, redis = _make_pipeline(shadow=True)
    delivered, deliver = _deliver_spy()
    pipeline._deliver = deliver
    user = "aaaaaaaa-9999-9999-9999-999999999999"
    _prime_relevance_view(redis, user, "r-view", now - timedelta(minutes=5))
    record = await pipeline.handle_event(
        {
            "event_type": "run.status_changed",
            "user_id": user,
            "run_id": "r-view",
            "run": {"to_status": "AWAITING_USER"},
            "timestamp": (now - timedelta(minutes=30)).isoformat(),
        }
    )
    assert record.decision == "no_action"
    assert record.reason == "already_aware"
    assert delivered == []


# ---------------------------------------------------------------------------
# Part 5 — 零 LLM 静态扫描（本卡灵魂的源码级钉桩）
# ---------------------------------------------------------------------------


def test_relevance_modules_have_zero_llm_imports():
    import inspect
    import re

    from app.aurora.proactive import pipeline as pipeline_mod
    from app.aurora.proactive import relevance as relevance_mod

    forbidden = re.compile(
        r"(openai|anthropic|dashscope|zhipuai|langchain|langfuse|litellm|chatglm|"
        r"llm_bridge|ChatCompletion|completion\.create)",
        re.IGNORECASE,
    )
    for mod in (relevance_mod, pipeline_mod):
        src = inspect.getsource(mod)
        assert not forbidden.search(src), f"{mod.__name__} 源码出现 LLM 相关符号"
