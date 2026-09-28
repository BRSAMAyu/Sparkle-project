"""V4-P01: 统一主动预算闸门（nudges/spine 渠道同一用户预算）。

卡面验收逐面对应（每面一正一反，反例钉显式标注）：

- 验收①「拒绝/静音/过期计划不再被另一渠道补发」：
  * 跨渠道补发反例钉：nudge 渠道拒绝（plan X）→ spine 渠道同 subject 必须
    被拦（``cross_channel_suppressed``）——:test:`test_cross_channel_rejection_blocks_spine_nail`；
  * 过期计划：spine 渠道不得补发（``subject_expired``），nudge 渠道保留
    J-07 rescope 语义不被误伤——:test:`test_expired_plan_blocks_spine_only`；
  * 删除/不存在的计划 subject 不复活——:test:`test_missing_plan_subject_blocks_spine`；
  * 冷却窗口到期释放（不过度抑制）——:test:`test_subject_cooldown_expiry_releases`。
- 验收②「回归不视为必须打扰，不改变主题推断情绪」：
  * 回归（comeback 渠道）在预算耗尽时与任何其他触发同级被拦——
    :test:`test_regression_comeback_not_privileged_nail`；
  * 预算面与抑制面对情绪推断面（CognitiveFragment.sentiment）零写入——
    :test:`test_gate_writes_no_emotion_signals`。
- 验收③「同一提示多端一次 effect，预算与因果来源可追」：
  * 同 prompt_key 一次 effect 反例钉：第二次判定被 ``already_effected``
    拦下，不同 subject 不受牵连——:test:`test_prompt_key_effect_window_nail`；
  * 预算信封可追：允许决定带 count/cap/prompt_key/channel/subject——
    :test:`test_gate_allows_within_budget_with_auditable_envelope`。
- 组合纪律：类型级抑制（既有语义）经闸门仍生效；回滚开关 off =
  passthrough；无 subject 提示不启用 effect 去重（节奏归各渠道既有冷却）。

时间纪律：全部经 ``now`` 注入可控时刻（in-memory sqlite + naive-UTC），
对挂钟与 quiet 窗挂钟面免疫（平台基线 quiet 在本文件显式关断，与
test_comeback_nudge_task 同款 fixture 纪律）。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.aurora.proactive import config as proactive_config
from app.aurora.proactive.unified_budget import (
    BUDGET_DECISION_REASONS,
    ProactiveBudgetRequest,
    ProactiveChannel,
    UnifiedProactiveBudgetService,
    build_budget_envelope,
    derive_prompt_key,
    record_cross_channel_suppression,
    subject_refs_from_payload,
)
from app.models.cognitive import CognitiveFragment
from app.models.notification import Notification
from app.models.plan import Plan
from app.models.plan import PlanType as PlanTypeEnum
from app.models.task import TaskStatus
from app.models.user_preferences import UserPreferencesCenter

USER_ID = "00000000-0000-0000-0000-00000000p001".replace("p001", "0001")
OTHER_PLAN_ID = "00000000-0000-0000-0000-000000000002"
PLAN_ID = "00000000-0000-0000-0000-00000000000a"
TASK_ID = "00000000-0000-0000-0000-00000000000b"


@pytest.fixture(autouse=True)
def _deterministic_knobs(monkeypatch: pytest.MonkeyPatch):
    """挂钟免疫：平台基线 quiet 关断 + 统一预算闸门显式开（逐测覆盖）。"""
    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False)
    monkeypatch.setattr(proactive_config, "PROACTIVE_UNIFIED_BUDGET_ENABLED", True)
    monkeypatch.setattr(proactive_config, "PROACTIVE_PROMPT_EFFECT_WINDOW_HOURS", 24)


def _moment() -> datetime:
    return datetime(2026, 9, 28, 12, 0, 0)


def _nudge_request(*, subject_refs: dict[str, str] | None = None, now: datetime | None = None):
    return ProactiveBudgetRequest(
        user_id=USER_ID,
        channel=ProactiveChannel.NUDGE,
        suggestion_type="comeback_nudge",
        subject_refs=subject_refs if subject_refs is not None else {"plan": PLAN_ID},
        prompt_kind="comeback",
        now=now or _moment(),
    )


def _spine_request(
    *,
    trigger: str = "long_silence",
    subject_refs: dict[str, str] | None = None,
    now: datetime | None = None,
):
    return ProactiveBudgetRequest(
        user_id=USER_ID,
        channel=ProactiveChannel.SPINE,
        suggestion_type="recall_notification",
        subject_refs=subject_refs if subject_refs is not None else {"plan": PLAN_ID},
        prompt_kind=trigger,
        now=now or _moment(),
    )


async def _seed_plan(
    db_session, *, plan_id: str = PLAN_ID, target_date=None, user_id=USER_ID, subject: str = "计算机网络"
) -> Plan:
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        name="计算机网络冲刺",
        type=PlanTypeEnum.SPRINT,
        subject=subject,
        target_date=target_date,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    return plan


# ── 验收③：预算面与因果来源可追 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gate_allows_within_budget_with_auditable_envelope(db_session):
    """正：预算内放行，决定带 count/cap 与 prompt_key（信封可追）。"""
    await _seed_plan(db_session, target_date=_moment().date() + timedelta(days=3))

    decision = await UnifiedProactiveBudgetService(db_session).evaluate(_nudge_request())

    assert decision.allowed is True
    assert decision.reason == "allowed"
    assert decision.prompt_key == derive_prompt_key(
        "nudge", "comeback_nudge", f"plan:{PLAN_ID}", prompt_kind="comeback"
    )
    assert decision.details["cap"] >= 1
    assert decision.details["count"] == 0
    assert decision.details["decided_at"] == _moment().isoformat()

    envelope = build_budget_envelope(channel=ProactiveChannel.NUDGE, request=_nudge_request(), decision=decision)
    assert envelope["prompt_key"] == decision.prompt_key
    assert envelope["channel"] == "nudge"
    assert envelope["suggestion_type"] == "comeback_nudge"
    assert envelope["subject"] == {"plan": PLAN_ID}
    assert envelope["daily_cap"] == decision.details["cap"]
    # 词表封闭：闸门产出的所有 reason 都在冻结集内。
    assert decision.reason in BUDGET_DECISION_REASONS


@pytest.mark.asyncio
async def test_prompt_key_effect_window_nail(db_session):
    """反例钉（多端一次 effect）：同 prompt_key 第二次判定被拦；不同 subject 不受牵连。"""
    await _seed_plan(db_session, target_date=_moment().date() + timedelta(days=3))
    await _seed_plan(
        db_session,
        plan_id=OTHER_PLAN_ID,
        target_date=_moment().date() + timedelta(days=3),
        subject="操作系统",
    )
    service = UnifiedProactiveBudgetService(db_session)

    first = await service.evaluate(_nudge_request())
    assert first.allowed is True

    # 模拟第一端已投递（账本行 + 预算信封，与任务接线落库同形状）。
    db_session.add(
        Notification(
            user_id=USER_ID,
            title="comeback",
            content="…",
            type="comeback_nudge",
            data={
                "proactive_budget": build_budget_envelope(
                    channel=ProactiveChannel.NUDGE, request=_nudge_request(), decision=first
                )
            },
        )
    )
    await db_session.commit()

    # 同一提示（同 prompt_key）再来一次（第二端/重试 tick）→ 一次 effect 钉死。
    second = await service.evaluate(_nudge_request())
    assert second.allowed is False
    assert second.reason == "already_effected"

    # 不同 subject 的提示不在去重窗内受牵连（预算仍由 cap 面管）。
    other = await service.evaluate(_nudge_request(subject_refs={"plan": OTHER_PLAN_ID}))
    assert other.allowed is True
    assert other.reason == "allowed"


# ── 验收①：跨渠道抑制 ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_channel_rejection_blocks_spine_nail(db_session):
    """反例钉（跨渠道补发）：nudge 渠道拒绝（plan X）→ spine 同 subject 必须被拦。"""
    await _seed_plan(db_session, target_date=_moment().date() + timedelta(days=3))

    # nudge 渠道建议卡被「今天不再看」→ 跨渠道 subject 抑制落库（API 写入口同款）。
    await record_cross_channel_suppression(
        db_session,
        USER_ID,
        {"plan_id": PLAN_ID, "suggestion_type": "comeback_nudge"},
        persistent=False,
        source_type="comeback_nudge",
        now=_moment(),
    )

    decision = await UnifiedProactiveBudgetService(db_session).evaluate(_spine_request())
    assert decision.allowed is False
    assert decision.reason == "cross_channel_suppressed"
    assert decision.details["subject"] == f"plan:{PLAN_ID}"

    # 反向同样成立：spine 卡（task subject 解析出 plan）被静音 → nudge 被拦。
    await record_cross_channel_suppression(
        db_session,
        USER_ID,
        {"task_id": TASK_ID, "plan_id": OTHER_PLAN_ID},
        persistent=True,
        source_type="recall_notification",
        now=_moment(),
    )
    nudge_after = await UnifiedProactiveBudgetService(db_session).evaluate(
        _nudge_request(subject_refs={"plan": OTHER_PLAN_ID})
    )
    assert nudge_after.allowed is False
    assert nudge_after.reason == "cross_channel_suppressed"
    # muted 优先：subject 级静音不是冷却，不随 24h 自愈。
    assert nudge_after.details["suppression"]["reason"] == "muted"


@pytest.mark.asyncio
async def test_subject_cooldown_expiry_releases(db_session):
    """反：subject 冷却到期后放行（不过度抑制；真实恢复语义）。"""
    await _seed_plan(db_session, target_date=_moment().date() + timedelta(days=3))
    await record_cross_channel_suppression(
        db_session,
        USER_ID,
        {"plan_id": PLAN_ID},
        persistent=False,
        source_type="comeback_nudge",
        now=_moment(),
    )

    within = await UnifiedProactiveBudgetService(db_session).evaluate(
        _spine_request(now=_moment() + timedelta(hours=23))
    )
    assert within.allowed is False

    after = await UnifiedProactiveBudgetService(db_session).evaluate(
        _spine_request(now=_moment() + timedelta(hours=25))
    )
    assert after.allowed is True
    assert after.reason == "allowed"


@pytest.mark.asyncio
async def test_expired_plan_blocks_spine_only(db_session):
    """过期计划：spine 渠道不得补发（subject_expired）；nudge 渠道保留 J-07 rescope。"""
    await _seed_plan(db_session, target_date=_moment().date() - timedelta(days=2))

    spine = await UnifiedProactiveBudgetService(db_session).evaluate(_spine_request(trigger="task_missed"))
    assert spine.allowed is False
    assert spine.reason == "subject_expired"

    nudge = await UnifiedProactiveBudgetService(db_session).evaluate(_nudge_request())
    assert nudge.allowed is True


@pytest.mark.asyncio
async def test_missing_plan_subject_blocks_spine(db_session):
    """删除/不存在的计划 subject 不复活：spine 判定 subject_expired（missing）。"""
    spine = await UnifiedProactiveBudgetService(db_session).evaluate(_spine_request())
    assert spine.allowed is False
    assert spine.reason == "subject_expired"
    assert spine.details.get("missing") is True


@pytest.mark.asyncio
async def test_type_suppression_still_blocks_own_channel(db_session):
    """既有语义保持：P-03 类型级冷却经闸门仍抑制（suggestion_suppressed）。"""
    await _seed_plan(db_session, target_date=_moment().date() + timedelta(days=3))
    future_until = _moment() + timedelta(hours=20)
    explicit_row = UserPreferencesCenter(
        user_id=USER_ID,
        explicit={"proactive_suggestion_ignored_until": {"comeback_nudge": future_until.isoformat()}},
    )
    db_session.add(explicit_row)
    await db_session.commit()

    decision = await UnifiedProactiveBudgetService(db_session).evaluate(_nudge_request())
    assert decision.allowed is False
    assert decision.reason == "suggestion_suppressed"
    assert decision.details["suppression"]["reason"] == "cooldown"


# ── 验收②：回归中性 ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_regression_comeback_not_privileged_nail(db_session, monkeypatch):
    """反例钉（回归不是必须打扰）：回归/comeback 在预算关停（cap=0）时被拦。"""
    monkeypatch.setattr(proactive_config, "PROACTIVE_DAILY_CAP", 0)

    decision = await UnifiedProactiveBudgetService(db_session).evaluate(_nudge_request())
    assert decision.allowed is False
    assert decision.reason == "daily_cap"
    assert decision.details["cap"] == 0


@pytest.mark.asyncio
async def test_gate_writes_no_emotion_signals(db_session):
    """情绪钉：预算/抑制判定对情绪推断面零写入（回归是中性事件）。"""
    await _seed_plan(db_session, target_date=_moment().date() + timedelta(days=3))
    before = len(
        (await db_session.execute(select(CognitiveFragment).where(CognitiveFragment.user_id == USER_ID)))
        .scalars()
        .all()
    )

    service = UnifiedProactiveBudgetService(db_session)
    allowed = await service.evaluate(_nudge_request())
    await record_cross_channel_suppression(
        db_session, USER_ID, {"plan_id": PLAN_ID}, persistent=False, source_type="comeback_nudge", now=_moment()
    )
    suppressed = await service.evaluate(_spine_request())

    assert allowed.allowed is True
    assert suppressed.allowed is False
    after = len(
        (await db_session.execute(select(CognitiveFragment).where(CognitiveFragment.user_id == USER_ID)))
        .scalars()
        .all()
    )
    assert after == before == 0


# ── 组合纪律：回滚开关 / 记录面 / 无 subject ────────────────────────────────


@pytest.mark.asyncio
async def test_knob_off_passthrough(db_session, monkeypatch):
    """回滚开关：闸门 off = passthrough，抑制态不再拦（恢复各渠道既有行为）。"""
    monkeypatch.setattr(proactive_config, "PROACTIVE_UNIFIED_BUDGET_ENABLED", False)
    await record_cross_channel_suppression(
        db_session, USER_ID, {"plan_id": PLAN_ID}, persistent=True, source_type="comeback_nudge", now=_moment()
    )

    decision = await UnifiedProactiveBudgetService(db_session).evaluate(_spine_request())
    assert decision.allowed is True
    assert decision.reason == "passthrough"


@pytest.mark.asyncio
async def test_record_resolves_task_plan_and_never_stacks(db_session):
    """记录面：task→plan 解析；重复拒绝一次 effect 不叠加（先到先得）。"""
    from app.models.task import Task, TaskType

    await _seed_plan(db_session)
    db_session.add(
        Task(
            id=TASK_ID,
            plan_id=PLAN_ID,
            user_id=USER_ID,
            title="TCP 流量控制",
            type=TaskType.LEARNING,
            estimated_minutes=30,
            status=TaskStatus.PENDING,
        )
    )
    await db_session.commit()

    first = await record_cross_channel_suppression(
        db_session, USER_ID, {"task_id": TASK_ID}, persistent=False, source_type="recall_notification", now=_moment()
    )
    assert set(first) == {f"task:{TASK_ID}", f"plan:{PLAN_ID}"}
    first_until = first[f"plan:{PLAN_ID}"]["until"]

    # 三小时后同 subject 再拒绝：不顺延（一次 effect）。
    second = await record_cross_channel_suppression(
        db_session,
        USER_ID,
        {"task_id": TASK_ID},
        persistent=False,
        source_type="recall_notification",
        now=_moment() + timedelta(hours=3),
    )
    assert second[f"plan:{PLAN_ID}"]["until"] == first_until

    # 静音升级：cooldown 在场时 muted 覆写（更保守方向允许升级）。
    upgraded = await record_cross_channel_suppression(
        db_session, USER_ID, {"plan_id": PLAN_ID}, persistent=True, source_type="recall_notification", now=_moment()
    )
    assert upgraded[f"plan:{PLAN_ID}"]["reason"] == "muted"


@pytest.mark.asyncio
async def test_subjectless_prompt_skips_effect_dedup_but_keeps_burden(db_session, monkeypatch):
    """无 subject 提示：不启用 effect 去重（节奏归渠道既有冷却），预算面仍在。"""
    monkeypatch.setattr(proactive_config, "PROACTIVE_DAILY_CAP", 1)
    db_session.add(Notification(user_id=USER_ID, title="t", content="c", type="recall_notification", data={}))
    await db_session.commit()

    request = ProactiveBudgetRequest(
        user_id=USER_ID,
        channel=ProactiveChannel.SPINE,
        suggestion_type="recall_notification",
        subject_refs={},
        prompt_kind="pre_exam_silence",
        now=_moment(),
    )
    decision = await UnifiedProactiveBudgetService(db_session).evaluate(request)
    assert decision.allowed is False
    assert decision.reason == "daily_cap"


@pytest.mark.asyncio
async def test_subject_refs_extraction_from_notification_payload():
    """载荷→subject refs 只认既有字段（plan_id/task_id/goal_state.goal_id）。"""
    refs = subject_refs_from_payload(
        {"plan_id": PLAN_ID, "task_id": TASK_ID, "goal_state": {"goal_id": "g-1"}, "other": "ignored"}
    )
    assert refs == {"plan": PLAN_ID, "task": TASK_ID, "goal": "g-1"}
    assert subject_refs_from_payload({}) == {}
