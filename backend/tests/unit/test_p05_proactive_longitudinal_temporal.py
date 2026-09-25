"""P-05 · 时序交互断言（pytest 契约锁）：mute 跨天 / cooldown 边界 / auto 授权纵向.

卡面验收「cooldown/mute（P-03）与 auto-execute（P-04）在纵向时间线里的交互行为
正确」的红绿/契约锁口径——全部经 **真实服务链**（生产 comeback 任务直调 +
ActionCommand/Permission/FeedbackService + 可控时钟引擎）驱动，断言对象是
DB 真相与全量事件记录，不是渲染层：

1. **mute 跨天不复发**：mute 时刻起，后续多天生成一律真源抑制（muted），
   DB 中不再出现新建议通知；
2. **cooldown 边界**：dismiss 后同日二次生成被 cooldown 抑制（P-03 真源抑制
   先于重复窗口检查）；满 24h 后的下一天 AM 生成恢复投放（>=24h 过界语义，
   与 test_proactive_suggestion_feedback 的 +1s 口径一致）——并观察「每天一次
   的召回节奏下 dismiss 只买同日安静」的真实产品语义；
3. **auto 授权纵向演变**：grant 前 proposal；grant 后低风险可逆步骤 auto 直通
   （COMPLETED 中风险不可逆仍恒 proposal+确认——授权不压风险门）；revoke 后
   同类操作回 proposal（auto_forbidden_category_not_allowlisted），显式确认
   仍可执行；
4. **基线组（主动面关闭）零建议投放**——两组唯一差异的契约锁。

红绿能力：断言钉在「若 P-03 抑制不接线 / P-04 判定不读真源，结果必然翻转」
的谓词上（mute 违例计数、auto/confirmation 模式与 reason code）。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.proactive_longitudinal.engine import PersonaWorld
from tests.proactive_longitudinal.persona import build_population, with_decision_script


def _persona(
    arc_prefix: str,
    *,
    avoid_intrinsic_days: tuple[int, ...] = (),
    require_intrinsic_days: tuple[int, ...] = (),
) -> Any:
    """选指定谱 persona：断言窗口内无/有内在自发重启（场景展开确定）。"""
    specs = build_population(seed=20260925, per_arc=4, days=8)
    for spec in specs:
        if not spec.persona_id.startswith(arc_prefix):
            continue
        if set(avoid_intrinsic_days) & set(spec.intrinsic_restart_days):
            continue
        if not set(require_intrinsic_days).issubset(set(spec.intrinsic_restart_days)):
            continue
        return spec
    raise AssertionError(f"no {arc_prefix} persona with avoid={avoid_intrinsic_days} require={require_intrinsic_days}")


def _generations(records: list[dict[str, Any]], *, slot: str | None = None) -> list[dict[str, Any]]:
    return [r for r in records if r["kind"] == "generation" and (slot is None or r.get("slot") == slot)]


def _suggestions(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in records if r["kind"] == "suggestion"]


async def _notification_count(world: PersonaWorld) -> int:
    from sqlalchemy import func, select

    from app.models.notification import Notification

    assert world.session is not None and world.user_id is not None
    return int(
        (
            await world.session.execute(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.user_id == world.user_id,
                    Notification.type == "comeback_nudge",
                    Notification.deleted_at.is_(None),
                )
            )
        ).scalar_one()
    )


# ── 1. mute 跨天不复发 ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mute_blocks_regeneration_across_remaining_days():
    spec = with_decision_script(
        _persona("stalled", avoid_intrinsic_days=(0, 1, 2, 3, 4, 5)),
        {0: "silent", 1: "mute"},
    )
    async with PersonaWorld(spec, group="proactive", days=6) as world:
        records = await world.run()
        assert await _notification_count(world) == 2  # day0 + day1 各一条，mute 后归零

    am = _generations(records, slot="am")
    by_day: dict[int, dict[str, Any]] = {int(r["sim_day"]): r for r in am}
    assert by_day[0]["result"] == "sent"
    assert by_day[1]["result"] == "sent"
    for day in (2, 3, 4, 5):
        assert by_day[day]["result"] == "skipped", f"day{day} 必须被真源抑制"
        assert by_day[day]["reason"] == "suggestion_suppressed"
        assert by_day[day]["suppression"]["reason"] == "muted"

    suggestions = _suggestions(records)
    assert [int(s["sim_day"]) for s in suggestions] == [0, 1]
    assert suggestions[-1]["disposition"] == "mute"


# ── 2. cooldown 窗口边界（同日抑制 / 满 24h 恢复） ────────────────────────────


@pytest.mark.asyncio
async def test_cooldown_suppresses_same_day_and_recovers_next_am():
    spec = with_decision_script(
        _persona("stalled", avoid_intrinsic_days=(0, 1, 2)),
        {0: "silent", 1: "dismiss", 2: "silent"},
    )
    async with PersonaWorld(spec, group="proactive", days=3) as world:
        records = await world.run()
        # DB 真相：建议通知数 = 投放数（day0/day1/day2 各一，PM 探针被抑制未落通知）
        assert await _notification_count(world) == len(_suggestions(records)) == 3

    generations = _generations(records)
    pm = [r for r in generations if r.get("slot") == "pm"]
    # dismiss 同日 PM 探针：P-03 cooldown 真源抑制（先于重复窗口检查被命中）
    assert len(pm) == 1 and int(pm[0]["sim_day"]) == 1
    assert pm[0]["result"] == "skipped"
    assert pm[0]["suppression"]["reason"] == "cooldown"

    am_by_day = {int(r["sim_day"]): r for r in generations if r.get("slot") == "am"}
    assert am_by_day[0]["result"] == "sent"
    assert am_by_day[1]["result"] == "sent"  # dismiss 当日 AM 建议照常投放
    # 满 24h（+ε）后的下一天 AM：cooldown 与重复窗口都已过界 → 恢复投放。
    # 这是真实语义（>=24h 过界，与单元测试 +1s 口径一致）；同时如实暴露
    # 「每日召回节奏下 dismiss 只买同日安静」的负担事实（进 REPORT 反例区）。
    assert am_by_day[2]["result"] == "sent"


# ── 3. auto 授权纵向演变（grant → auto；revoke → proposal） ───────────────────


@pytest.mark.asyncio
async def test_auto_grant_then_revoke_evolution_across_timeline():
    import dataclasses

    from sqlalchemy import select

    from app.models.action_proposal import ActionProposal
    from app.models.task import Task, TaskStatus

    base = with_decision_script(
        _persona("deadline", avoid_intrinsic_days=(0, 1, 2, 3)),
        {0: "accept", 3: "accept"},
    )
    spec = dataclasses.replace(base, auto_grant_on_first_accept=True)

    async def _revoke_at_day1(world: PersonaWorld) -> None:
        await world._revoke_auto()
        world._record("lifecycle", {"sim_day": 1, "event": "auto_revoke", "trigger": "test-hook"})

    async with PersonaWorld(spec, group="proactive", days=4, day_hooks={1: _revoke_at_day1}) as world:
        records = await world.run()
        assert world.session is not None

        suggestions = _suggestions(records)
        assert [int(s["sim_day"]) for s in suggestions] == [0, 3]

        # t0（grant 后）：低风险可逆步骤 auto 直通；COMPLETED 恒 proposal+确认
        day0_steps = suggestions[0]["action"]["actions"]
        assert day0_steps[0]["step"] == "IN_PROGRESS" and day0_steps[0]["mode"] == "auto"
        assert day0_steps[1]["step"] == "COMPLETED" and day0_steps[1]["mode"] == "confirmation"
        assert day0_steps[1]["executed"] is True  # persona 显式确认路径

        # t1（revoke 后）：同类操作回 proposal，且 reason code 指向授权面收窄
        day3_steps = suggestions[1]["action"]["actions"]
        assert day3_steps[0]["step"] == "IN_PROGRESS" and day3_steps[0]["mode"] == "confirmation"
        assert "auto_forbidden_category_not_allowlisted" in day3_steps[0]["reason_codes"]
        # 授权永不夺走确认权：COMPLETED 仍确认执行，账本推进
        assert day3_steps[1]["executed"] is True

        # DB 真相：两次行动都真实落账（任务完成），auto receipt 只存在于 grant 窗口
        proposals = (
            (await world.session.execute(select(ActionProposal).where(ActionProposal.status == "COMMITTED")))
            .scalars()
            .all()
        )
        assert len(proposals) >= 4  # 每次行动 = start+complete 两个 proposal
        tasks = (await world.session.execute(select(Task).where(Task.user_id == world.user_id))).scalars().all()
        assert sum(1 for t in tasks if t.status is TaskStatus.COMPLETED) == 4  # 2 pre + 2 accept


# ── 4. 基线组（同时间线、主动面关闭）零建议投放 ────────────────────────────────


@pytest.mark.asyncio
async def test_baseline_group_never_generates_any_suggestion():
    spec = _persona("stalled", require_intrinsic_days=(0,))
    async with PersonaWorld(spec, group="baseline", days=5) as world:
        records = await world.run()
        assert await _notification_count(world) == 0
    assert _generations(records) == []
    assert _suggestions(records) == []
    # 内在行为照常（两组共享的时间线基线）
    assert any(r["kind"] == "lifecycle" and r.get("event") == "intrinsic_restart" for r in records)


# ── 5. completion 事件谱正控：目标账本完成 → sprint auto-archive → 主动面停 ────


@pytest.mark.asyncio
async def test_ledger_completion_stops_proactive_generation():
    """账本 100% 完成（deadline 达成）后，后续多天生成一律 not_eligible。

    机制（真实链路）：TaskService 完成最后任务 → ExamSprintReviewService
    auto_archive_if_complete → Plan 归档（is_active=False）→ get_comeback_context
    查不到活跃计划 → 建议源头停。这是「主动面不追着已完成目标打扰」的正控契约锁
    （P-05 反例排查结论：完成后打扰在 sprint 谱不存在）。
    """
    spec = with_decision_script(
        _persona("completion", avoid_intrinsic_days=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)),
        {0: "accept", 3: "accept", 6: "accept"},
    )
    async with PersonaWorld(spec, group="proactive", days=11) as world:
        records = await world.run()
        from sqlalchemy import select

        from app.models.plan import Plan

        assert world.session is not None and world.user_id is not None
        plan = (await world.session.execute(select(Plan).where(Plan.user_id == world.user_id))).scalars().first()
        assert plan is not None and plan.is_active is False  # 账本完成 → auto-archive

    suggestions = _suggestions(records)
    assert [int(s["sim_day"]) for s in suggestions] == [0, 3, 6]
    assert suggestions[-1]["ledger_done_after"] == suggestions[-1]["action"].get("ledger_total")
    assert suggestions[-1]["action"].get("deadline_met") is True
    am_by_day = {int(r["sim_day"]): r for r in _generations(records, slot="am")}
    for day in (7, 8, 9, 10):
        assert am_by_day[day]["result"] == "skipped"
        assert am_by_day[day]["reason"] == "not_eligible"
