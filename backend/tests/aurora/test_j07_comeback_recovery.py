"""J-07 · Return / Stale Plan / Comeback Recovery（引擎侧）。

四档可控时钟（1/3/7/14 day test clock）+ plan drift/deadline change 检测 +
rationale 差异化（真实变化依据）+ rescope（复用 wt313 replan 端点，不重建）+
≤2 actions 量化 + 零 guilt 词表（P-03/J-05 同源红线）。

不重建纪律：comeback 真源仍是 A-07 的 ``get_comeback_context``；
deadline 重锚执行面仍是 wt313 的 ``POST /plans/{id}/replan``；
drift 阈值与 PlanProgressService（plan health）同源，不设第二套口径。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.models.chat import ChatMessage, MessageRole
from app.models.plan import Plan, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User

#: 固定锚点（可控时钟的 T0）：最后真实活动时刻。
T0 = datetime(2026, 9, 1, 10, 0, 0)


def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


async def _seed_j07_fixture(
    db_session,
    *,
    plan_created_at: datetime,
    plan_target_date: datetime,
    completed_tasks: int = 1,
    pending_tasks: int = 1,
    replan_receipt: dict | None = None,
) -> tuple[User, Plan]:
    """单一真源 fixture：最后真实活动 = T0（用户消息），任务完成都在 T0 之前。"""
    user = User(
        id=uuid4(),
        username=f"j07_{uuid4().hex[:8]}",
        email=f"j07_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    plan = Plan(
        name="7天计算机网络冲刺",
        user_id=user.id,
        type=PlanType.SPRINT,
        subject="计算机网络",
        target_date=_naive(plan_target_date).date(),
        plan_stage=PlanStage.SPRINT,
        is_active=True,
        is_primary=True,
        created_at=_naive(plan_created_at),
        updated_at=_naive(plan_created_at),
    )
    if replan_receipt is not None:
        plan.source_metadata = {"last_replan": replan_receipt}
    db_session.add_all([user, plan])
    await db_session.flush()

    db_session.add(
        ChatMessage(
            user_id=user.id,
            role=MessageRole.USER,
            content="我先去忙几天。",
            created_at=_naive(T0),
        )
    )
    for offset in range(completed_tasks):
        db_session.add(
            Task(
                user_id=user.id,
                plan_id=plan.id,
                title=f"已完成任务 {offset}",
                type=TaskType.LEARNING,
                estimated_minutes=30,
                difficulty=1,
                energy_cost=1,
                status=TaskStatus.COMPLETED,
                completed_at=_naive(T0 - timedelta(days=1 + offset)),
                order_index=offset,
            )
        )
    for offset in range(pending_tasks):
        db_session.add(
            Task(
                user_id=user.id,
                plan_id=plan.id,
                title=f"Day {offset + 4} · 待续任务",
                type=TaskType.LEARNING,
                estimated_minutes=45,
                difficulty=2,
                energy_cost=2,
                status=TaskStatus.PENDING,
                order_index=10 + offset,
            )
        )
    await db_session.commit()
    return user, plan


async def _fetch_payload(db_session, user, *, reference: datetime) -> dict | None:
    service = AuroraRuntimeV1Service()
    return await service.get_comeback_context(
        active_db=db_session,
        user_id=user.id,
        reference_time=_naive(reference),
    )


# ── 1/3/7/14 day test clock（可控时钟，全档覆盖） ─────────────────────────────


@pytest.mark.asyncio
async def test_four_tier_clock_one_day_below_threshold_stays_quiet(db_session):
    """1 天档：低于 3 天阈值，长离面不唤醒（push 口径）。"""
    user, _plan = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=2),
        plan_target_date=T0 + timedelta(days=5),
    )
    payload = await _fetch_payload(db_session, user, reference=T0 + timedelta(days=1))
    assert payload is None


@pytest.mark.asyncio
async def test_four_tier_clock_three_day_threshold_fresh_window(db_session):
    """3 天档：阈值触发、窗口未过期——纯 time_passed，rescope 不推荐。"""
    user, plan = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=2),
        plan_target_date=T0 + timedelta(days=5),
    )
    payload = await _fetch_payload(db_session, user, reference=T0 + timedelta(days=3))
    assert payload is not None
    assert payload["days_away"] == 3
    assert payload["comeback_kind"] == "checkpoint_debrief"
    assert payload["plan_expired"] is False
    assert payload["rescope"]["available"] is True
    assert payload["rescope"]["recommended"] is False
    assert payload["rationale"]["sources"] == ["time_passed"]
    assert payload["rationale"]["primary"] == "time_passed"
    assert payload["primary_action"]["kind"] == "open_task"
    assert plan.id is not None


@pytest.mark.asyncio
async def test_four_tier_clock_seven_day_window_expired_rescope_recommended(db_session):
    """7 天档：窗口在离开期间耗尽——诚实呈报，rescope 推荐复用 wt313 端点。"""
    user, plan = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=2),
        plan_target_date=T0 + timedelta(days=5),
    )
    payload = await _fetch_payload(db_session, user, reference=T0 + timedelta(days=7))
    assert payload is not None
    assert payload["days_away"] == 7
    assert payload["plan_expired"] is True
    assert payload["stale_focus"] is True
    message = payload["message"]
    assert "已经结束" in message
    assert "来得及" not in message and "收尾窗口" not in message
    rescope = payload["rescope"]
    assert rescope["recommended"] is True
    assert rescope["available"] is True
    assert rescope["endpoint"] == f"/api/v1/plans/{plan.id}/replan"
    assert rescope["reason"] == "plan_window_expired"
    assert payload["primary_action"]["kind"] == "rescope_plan"
    assert payload["primary_action"]["within_actions"] <= 2


@pytest.mark.asyncio
async def test_four_tier_clock_fourteen_day_long_absence_stays_honest(db_session):
    """14 天档：长离仍走同一真源，陈旧任务不包装成当前步，零 guilt。"""
    user, _plan = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=2),
        plan_target_date=T0 + timedelta(days=5),
    )
    payload = await _fetch_payload(db_session, user, reference=T0 + timedelta(days=14))
    assert payload is not None
    assert payload["days_away"] == 14
    assert payload["plan_expired"] is True
    message = payload["message"]
    assert "已经结束" in message
    assert "重新校准" in message
    assert "最近最适合重新捡起来" not in message
    for banned in ("焦虑", "压力", "落后", "耽误", "羞耻", "责备"):
        assert banned not in message


@pytest.mark.asyncio
async def test_controlled_clock_is_deterministic_same_clock_same_payload(db_session):
    """可控时钟确定性：同一 reference_time 两次调用，payload 完全一致（非墙钟漂移）。"""
    user, _plan = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=2),
        plan_target_date=T0 + timedelta(days=5),
    )
    first = await _fetch_payload(db_session, user, reference=T0 + timedelta(days=3))
    second = await _fetch_payload(db_session, user, reference=T0 + timedelta(days=3))
    assert first is not None and second is not None
    assert first == second


# ── rationale 差异化：deadline 变化 vs 进度漂移（真实变化依据） ────────────────


@pytest.mark.asyncio
async def test_rationale_deadline_changed_driven_by_replan_during_absence(db_session):
    """deadline_changed 源：wt313 replan 回执晚于最后活动 = 离开期间终点真的变过。"""
    previous_target = (T0 - timedelta(days=1)).date()
    new_target = (T0 + timedelta(days=12)).date()
    user, _plan = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=5),
        plan_target_date=datetime.fromordinal(new_target.toordinal()),
        completed_tasks=3,
        pending_tasks=1,
        replan_receipt={
            "at": (T0 + timedelta(days=1)).isoformat(),
            "trigger": "api",
            "previous_target_date": previous_target.isoformat(),
            "new_target_date": new_target.isoformat(),
            "days_shifted": 13,
        },
    )
    payload = await _fetch_payload(db_session, user, reference=T0 + timedelta(days=4))
    assert payload is not None
    rationale = payload["rationale"]
    assert rationale["sources"] == ["time_passed", "deadline_changed"]
    assert rationale["primary"] == "deadline_changed"
    evidence = rationale["evidence"]["deadline_changed"]
    assert evidence["kind"] == "replanned_during_absence"
    assert evidence["new_target_date"] == new_target.isoformat()
    # 差异化文案：deadline 驱动的 rationale 指向新终点（事实陈述，零 guilt）。
    assert new_target.isoformat() in payload["message"]
    assert "重新校准" in payload["message"]
    assert payload["plan_expired"] is False


@pytest.mark.asyncio
async def test_rationale_progress_drifted_driven_by_lag_between_window_and_ledger(db_session):
    """progress_drifted 源：窗口时间进度与任务账本完成率拉开 ≥ plan health 同源阈值。"""
    user, _plan = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=27),
        plan_target_date=T0 + timedelta(days=13),
        completed_tasks=1,
        pending_tasks=3,
    )
    payload = await _fetch_payload(db_session, user, reference=T0 + timedelta(days=3))
    assert payload is not None
    rationale = payload["rationale"]
    assert rationale["sources"] == ["time_passed", "progress_drifted"]
    assert rationale["primary"] == "progress_drifted"
    evidence = rationale["evidence"]["progress_drifted"]
    assert evidence["ledger_completed"] == 1
    assert evidence["ledger_total"] == 4
    assert evidence["lag"] >= 0.25
    # 差异化文案：进度漂移驱动的 rationale 陈述账本事实（不做人身评价）。
    assert "1/4" in payload["message"]
    assert payload["plan_expired"] is False


@pytest.mark.asyncio
async def test_rationale_two_drivers_produce_differentiated_rationales(db_session):
    """三源至少两类：deadline 驱动与进度漂移驱动的 rationale 必须不同，且各有真实依据。"""
    previous_target = (T0 - timedelta(days=1)).date()
    new_target = (T0 + timedelta(days=12)).date()
    deadline_user, _ = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=5),
        plan_target_date=datetime.fromordinal(new_target.toordinal()),
        completed_tasks=3,
        pending_tasks=1,
        replan_receipt={
            "at": (T0 + timedelta(days=1)).isoformat(),
            "trigger": "api",
            "previous_target_date": previous_target.isoformat(),
            "new_target_date": new_target.isoformat(),
            "days_shifted": 13,
        },
    )
    drift_user, _ = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=27),
        plan_target_date=T0 + timedelta(days=13),
        completed_tasks=1,
        pending_tasks=3,
    )
    deadline_payload = await _fetch_payload(db_session, deadline_user, reference=T0 + timedelta(days=4))
    drift_payload = await _fetch_payload(db_session, drift_user, reference=T0 + timedelta(days=3))
    assert deadline_payload is not None and drift_payload is not None
    deadline_rationale = deadline_payload["rationale"]
    drift_rationale = drift_payload["rationale"]
    # 两类驱动源，rationale 结构性不同。
    assert deadline_rationale["primary"] == "deadline_changed"
    assert drift_rationale["primary"] == "progress_drifted"
    assert deadline_rationale["sources"] != drift_rationale["sources"]
    assert deadline_rationale["summary"] != drift_rationale["summary"]
    # 各自 message 的驱动子句不同（deadline 指向新终点，drift 陈述账本）。
    assert deadline_payload["message"] != drift_payload["message"]
    assert "重新校准" in deadline_payload["message"]
    assert "1/4" in drift_payload["message"]
    # 零 guilt 词表（P-03/J-05 同源红线）对两类驱动同时成立。
    for payload in (deadline_payload, drift_payload):
        for banned in ("焦虑", "压力", "落后", "耽误", "羞耻", "责备"):
            assert banned not in payload["message"]
            assert banned not in payload["rationale"]["summary"]


# ── ≤2 actions 量化 + rescope 复用 wt313 replan ──────────────────────────────


@pytest.mark.asyncio
async def test_primary_action_fresh_window_is_one_tap_to_next_task(db_session):
    """新鲜窗口：primary_action = 直接打开下一个任务（1 次交互到可执行步）。"""
    user, plan = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=2),
        plan_target_date=T0 + timedelta(days=5),
    )
    payload = await _fetch_payload(db_session, user, reference=T0 + timedelta(days=3))
    assert payload is not None
    primary = payload["primary_action"]
    assert primary["kind"] == "open_task"
    assert primary["route"].startswith("/tasks/")
    assert primary["within_actions"] <= 2
    # rescope 可用但不抢主位（复用 wt313 端点，只做入口不重建）。
    assert payload["rescope"]["endpoint"] == f"/api/v1/plans/{plan.id}/replan"


@pytest.mark.asyncio
async def test_primary_action_stale_window_is_rescope_within_two_actions(db_session):
    """陈旧窗口：primary_action = rescope（≤2 次交互），不复用陈旧任务当最优步。"""
    user, plan = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=2),
        plan_target_date=T0 + timedelta(days=5),
    )
    payload = await _fetch_payload(db_session, user, reference=T0 + timedelta(days=7))
    assert payload is not None
    primary = payload["primary_action"]
    assert primary["kind"] == "rescope_plan"
    assert primary["within_actions"] <= 2
    assert primary["route"] == f"/plans/{plan.id}/edit"
    # 未完成任务仍在 unfinished_items 里可直达（可继续，但不再是"当前最优步"话术）。
    task_items = [item for item in payload["unfinished_items"] if item["type"] == "task"]
    assert task_items, "unfinished items 仍保留未完成任务入口"


@pytest.mark.asyncio
async def test_unfinished_tasks_never_accumulate_guilt(db_session):
    """未完成任务不做羞辱式累积：unfinished_items 与 rationale 摘要零 guilt 词表。"""
    user, _plan = await _seed_j07_fixture(
        db_session,
        plan_created_at=T0 - timedelta(days=27),
        plan_target_date=T0 + timedelta(days=13),
        completed_tasks=1,
        pending_tasks=3,
    )
    payload = await _fetch_payload(db_session, user, reference=T0 + timedelta(days=5))
    assert payload is not None
    assert len(payload["unfinished_items"]) > 0
    for item in payload["unfinished_items"]:
        text = f"{item.get('title', '')}{item.get('subtitle', '')}"
        for banned in ("焦虑", "压力", "落后", "欠", "耽误", "羞耻", "责备", "堆积"):
            assert banned not in text
    summary = payload["rationale"]["summary"]
    assert summary
    for banned in ("焦虑", "压力", "落后", "欠", "耽误", "羞耻", "责备", "堆积"):
        assert banned not in summary
