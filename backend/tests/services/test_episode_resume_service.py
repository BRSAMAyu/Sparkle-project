"""V4-I01 · EpisodeResumeView 聚合服务守卫（sqlite 隔离，不触 dev DB）。

覆盖卡验收（必须可失败）与 B05 合同 §5/§8/§9 用例：
- 组成：goal/task/run/outcome/subtask/plan 各权威 → 视图字段逐位接线
  （run_ref 只取在途、last_confirmed_step subtask 优先、pending_human_step
  经 X-01 统一读侧门、freshness 钉 epoch + receipt ref）；
- 已删对象不复活：task/goal 软删 → ``object_not_found``，视图不出；
- 跨用户拒绝（I3）：他人对象 → ``cross_object_access``，视图不出；
- 目标改变退回明确校准：goal 终态 / plan 绑定 goal 不一致 →
  ``goal_changed_requires_calibration``，旧计划不出（不强推）；
- 无历史不造分数：无 outcome → ``last_valid_outcome`` 恒 null；无 V3 计划 →
  ``pending_human_step`` 恒 null；COMPLETED/ABANDONED 任务无待办步；
- 过期降级：``expires_at`` 过后 ``resume_view_stale_reason`` 判过期；
  epoch bump 判 stale（重算出口，不就地修补）；
- why_now v1 行 null 语义：无 why_now 字段位 → 视图 why_now=null（不臆测回填），
  视图仍完整组成；
- receipt 门：无 ``context_selection://`` ref → ``context_receipt_missing``。
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.core.action_plan import ActionPlanContract, CompletionEvidenceSpec, SmallestUsefulStep
from app.core.episode_resume_view import resume_view_stale_reason, validate_resume_view_shape
from app.core.run_state_machine import RunStatus
from app.core.time_utils import utcnow
from app.models.agent_run import AgentRun, AgentRunKind
from app.models.execution_intent import ExecutionMode
from app.models.focus import FocusSession, FocusStatus
from app.models.goal import Goal
from app.models.plan import Plan, PlanType
from app.models.task import CognitiveOwnership, SubTask, SubTaskStatus, Task, TaskStatus, TaskType
from app.models.user import User
from app.services.episode_resume_service import EpisodeResumeService

pytestmark = pytest.mark.asyncio

_NOW = datetime(2026, 9, 28, 8, 55, 0)
_RECEIPT = "context_selection://csr_i01_test"


async def _make_user(db_session, *, suffix: str = "") -> User:
    user = User(
        username=f"i01{suffix}{uuid4().hex[:8]}",
        email=f"i01{suffix}{uuid4().hex[:8]}@t.co",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _plan_contract() -> ActionPlanContract:
    return ActionPlanContract(
        desired_outcome="独立完成 1 道同型题",
        smallest_useful_step=SmallestUsefulStep(
            description="独立完成 1 道同型题并通过自查清单",
            useful_because=("builds_capability",),
        ),
        completion_evidence=(CompletionEvidenceSpec(evidence_kind="quiz_result"),),
        execution_mode=ExecutionMode.HYBRID,
        cognitive_ownership=CognitiveOwnership.USER_CORE,
        source_refs=("goal://11111111-1111-1111-1111-111111111111",),
    )


async def _make_episode(
    db_session,
    user: User,
    *,
    task_status: TaskStatus = TaskStatus.IN_PROGRESS,
    apply_plan: bool = True,
    goal_status: str = "active",
    source_refs: tuple[str, ...] | None = None,
) -> tuple[Goal, Task]:
    goal = Goal(user_id=user.id, title="考研数学", goal_type="exam", status=goal_status)
    db_session.add(goal)
    await db_session.flush()
    plan = Plan(user_id=user.id, goal_id=goal.id, name="数学冲刺", type=PlanType.SPRINT)
    db_session.add(plan)
    await db_session.flush()
    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="极限专题",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        status=task_status,
    )
    contract = _plan_contract()
    # 默认 source_refs 绑定真实 goal（计划 ↔ goal 一致面）；显式传参用于绑定不一致反例。
    contract = replace(contract, source_refs=source_refs if source_refs is not None else (f"goal://{goal.id}",))
    if apply_plan:
        contract.apply_to_task(task)
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return goal, task


async def _add_subtask(db_session, task: Task, *, completed_at: datetime | None) -> SubTask:
    sub = SubTask(
        parent_task_id=task.id,
        title="看示例题",
        order=1,
        status=SubTaskStatus.COMPLETED if completed_at else SubTaskStatus.PENDING,
        completed_at=completed_at,
    )
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)
    return sub


async def _add_run(db_session, task: Task, *, status: RunStatus) -> AgentRun:
    run = AgentRun(
        user_id=task.user_id,
        kind=AgentRunKind.EXECUTION,
        objective="准备同型题",
        heartbeat_at=utcnow(),
        status=status,
        task_id=task.id,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


async def _add_focus(db_session, task: Task, *, minutes: int = 30, end: datetime | None = None) -> None:
    focus_end = end or _NOW
    db_session.add(
        FocusSession(
            user_id=task.user_id,
            task_id=task.id,
            start_time=focus_end - timedelta(minutes=minutes),
            end_time=focus_end,
            duration_minutes=minutes,
            status=FocusStatus.COMPLETED,
        )
    )
    await db_session.commit()


# ---------------------------------------------------------------------------
# 组成：各权威 → 视图字段逐位接线
# ---------------------------------------------------------------------------


async def test_full_composition_wires_every_authority(db_session):
    user = await _make_user(db_session)
    goal, task = await _make_episode(db_session, user)
    sub = await _add_subtask(db_session, task, completed_at=_NOW - timedelta(hours=1))
    run = await _add_run(db_session, task, status=RunStatus.AWAITING_USER)
    task.completed_at = None
    task.status = TaskStatus.IN_PROGRESS
    # outcome：任务完成 + focus 覆盖 → actual（先落完成态再恢复，避免污染 pending 断言）
    completed = Task(
        user_id=user.id,
        plan_id=task.plan_id,
        title="极限专题（前次）",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        status=TaskStatus.COMPLETED,
        completed_at=_NOW - timedelta(days=1),
        actual_minutes=30,
    )
    db_session.add(completed)
    await _add_focus(db_session, completed)
    await db_session.commit()

    result = await EpisodeResumeService(db_session).build_resume_view(
        user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
    )
    assert result.degraded is False and result.reason_code is None
    view = result.view
    assert validate_resume_view_shape(view) == ()
    assert view["goal_ref"] == f"goal://{goal.id}"
    assert view["task_ref"] == f"task://{task.id}"
    assert view["run_ref"] == f"run://{run.id}"  # 在途 run 进 run_ref
    assert view["last_confirmed_step"] == {
        "step_ref": f"subtask://{sub.id}",
        "description": "看示例题",
        "confirmed_at": (_NOW - timedelta(hours=1)).replace(tzinfo=None).isoformat(timespec="seconds"),
        "version_token": sub.updated_at.replace(tzinfo=None).isoformat(timespec="microseconds"),
    }
    assert view["pending_human_step"] == {
        "description": "独立完成 1 道同型题并通过自查清单",
        "cognitive_ownership": "user_core",
        "execution_mode": "hybrid",
    }
    assert view["why_now"] is None  # v1 行（无 why_now 字段位）→ null，不臆测回填
    assert view["expires_at"] == "2026-09-28T09:25:00"
    assert view["freshness"]["context_receipt_ref"] == _RECEIPT
    assert view["freshness"]["computed_at"] == "2026-09-28T08:55:00"
    assert isinstance(view["freshness"]["memory_epoch_at_compute"], int)


async def test_last_valid_outcome_from_ledger_actual_and_self_reported(db_session):
    user = await _make_user(db_session)
    goal, task = await _make_episode(db_session, user, task_status=TaskStatus.COMPLETED)
    task.completed_at = _NOW - timedelta(days=1)
    task.actual_minutes = 30
    await db_session.commit()
    # 覆盖 30 分钟 ≥ threshold → actual；focus 结束于完成时刻（最新关联 outcome 即该刻）
    await _add_focus(db_session, task, end=_NOW - timedelta(days=1))

    svc = EpisodeResumeService(db_session)
    result = await svc.build_resume_view(user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW)
    assert result.view is not None
    outcome = result.view["last_valid_outcome"]
    assert outcome is not None
    assert outcome["truth_class"] == "actual"
    assert outcome["outcome_ref"].startswith("outcome://outc_")
    assert outcome["recorded_at"] == "2026-09-27T08:55:00"
    # 完成任务无待办步（pending=null），但接续卡仍有已确认位置
    assert result.view["pending_human_step"] is None
    assert result.view["last_confirmed_step"]["step_ref"] == f"task://{task.id}"

    # 无独立证据的另一任务 → self_reported（诚实降级，不升 actual）
    _, task2 = await _make_episode(db_session, user, task_status=TaskStatus.COMPLETED)
    task2.completed_at = _NOW - timedelta(days=2)
    task2.actual_minutes = 30
    await db_session.commit()
    result2 = await svc.build_resume_view(user_id=user.id, task_id=task2.id, context_receipt_ref=_RECEIPT, now=_NOW)
    assert result2.view["last_valid_outcome"]["truth_class"] == "self_reported"


async def test_no_history_yields_nulls_no_fabricated_scores(db_session):
    """无历史：last_valid_outcome=null、pending=null、视图仍封闭——不造连续学习/理解分数。"""
    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user, apply_plan=False)  # legacy 行（无 V3 计划）

    result = await EpisodeResumeService(db_session).build_resume_view(
        user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
    )
    assert result.view is not None
    view = result.view
    assert view["last_valid_outcome"] is None  # 无可引用成果——不造「练了 N 分钟」替代面
    assert view["last_confirmed_step"] is None  # 无已确认步
    assert view["pending_human_step"] is None  # 无 V3 计划 → 诚实降级
    assert view["run_ref"] is None  # 无在途 run
    assert validate_resume_view_shape(view) == ()  # 字段集封闭：不存在进度/分数类字段位
    assert "progress" not in view and "mastery" not in view and "minutes" not in view


# ---------------------------------------------------------------------------
# 删除不复活 / 跨用户拒绝 / goal 门
# ---------------------------------------------------------------------------


async def test_deleted_task_does_not_revive(db_session):
    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    svc = EpisodeResumeService(db_session)
    first = await svc.build_resume_view(user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW)
    assert first.view is not None

    task.soft_delete()
    await db_session.commit()
    second = await svc.build_resume_view(user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW)
    assert second.view is None
    assert second.reason_code == "object_not_found"  # 已删对象不复活


async def test_deleted_goal_does_not_revive(db_session):
    user = await _make_user(db_session)
    goal, task = await _make_episode(db_session, user)
    goal.soft_delete()
    await db_session.commit()
    result = await EpisodeResumeService(db_session).build_resume_view(
        user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
    )
    assert result.view is None
    assert result.reason_code == "object_not_found"


async def test_cross_user_task_rejected(db_session):
    owner = await _make_user(db_session, suffix="owner")
    outsider = await _make_user(db_session, suffix="out")
    _, task = await _make_episode(db_session, owner)
    result = await EpisodeResumeService(db_session).build_resume_view(
        user_id=outsider.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
    )
    assert result.view is None
    assert result.reason_code == "cross_object_access"  # I3：拒绝，不 500 泄漏、不静默跨读


async def test_task_without_goal_chain_is_goal_unresolved(db_session):
    user = await _make_user(db_session)
    task = Task(
        user_id=user.id,
        plan_id=None,
        title="无计划任务",
        type=TaskType.LEARNING,
        estimated_minutes=10,
        status=TaskStatus.IN_PROGRESS,
    )
    db_session.add(task)
    await db_session.commit()
    result = await EpisodeResumeService(db_session).build_resume_view(
        user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
    )
    assert result.view is None
    assert result.reason_code == "goal_unresolved"


async def test_goal_closed_returns_calibration_not_old_plan(db_session):
    """目标改变（终态）→ 退回明确校准，旧计划不强推（视图不出）。"""
    user = await _make_user(db_session)
    for closed in ("completed", "archived", "cancelled"):
        _, task = await _make_episode(db_session, user, goal_status=closed)
        result = await EpisodeResumeService(db_session).build_resume_view(
            user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
        )
        assert result.view is None, closed
        assert result.reason_code == "goal_changed_requires_calibration", closed


async def test_plan_bound_to_other_goal_returns_calibration(db_session):
    """task 计划绑定 goal:// 与解析 goal 不一致 → 校准，不跨目标接续旧计划。"""
    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user, source_refs=("goal://22222222-2222-2222-2222-222222222222",))
    result = await EpisodeResumeService(db_session).build_resume_view(
        user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
    )
    assert result.view is None
    assert result.reason_code == "goal_changed_requires_calibration"


async def test_active_goal_statuses_allow_view(db_session):
    user = await _make_user(db_session)
    for active in ("draft", "active", "paused"):
        _, task = await _make_episode(db_session, user, goal_status=active)
        result = await EpisodeResumeService(db_session).build_resume_view(
            user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
        )
        assert result.view is not None, active


# ---------------------------------------------------------------------------
# run 面
# ---------------------------------------------------------------------------


async def test_terminal_run_not_in_run_ref(db_session):
    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    await _add_run(db_session, task, status=RunStatus.SUCCEEDED)
    result = await EpisodeResumeService(db_session).build_resume_view(
        user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
    )
    assert result.view["run_ref"] is None  # 终态 run ≠ 在途


async def test_abandoned_task_has_no_pending_step(db_session):
    """ABANDONED 任务：旧计划不强推 → pending_human_step=null。"""
    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user, task_status=TaskStatus.ABANDONED)
    result = await EpisodeResumeService(db_session).build_resume_view(
        user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
    )
    assert result.view["pending_human_step"] is None


# ---------------------------------------------------------------------------
# receipt 门 / 过期 / epoch 陈旧
# ---------------------------------------------------------------------------


async def test_missing_or_wrong_scheme_receipt_ref_blocks_view(db_session):
    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    svc = EpisodeResumeService(db_session)
    for ref in ("", "outcome://outc_x", "context_selection:"):
        result = await svc.build_resume_view(user_id=user.id, task_id=task.id, context_receipt_ref=ref, now=_NOW)
        assert result.view is None
        assert result.reason_code == "context_receipt_missing"


async def test_view_expires_and_requires_recompute(db_session):
    """§9 反例：过期 EpisodeResumeView 只允许说明不确定性，不自动接续。"""
    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    result = await EpisodeResumeService(db_session).build_resume_view(
        user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
    )
    view = result.view
    assert resume_view_stale_reason(view, now=_NOW + timedelta(minutes=29), current_memory_epoch=1) is None
    assert (
        resume_view_stale_reason(view, now=_NOW + timedelta(minutes=31), current_memory_epoch=1) == "expires_at_passed"
    )


async def test_epoch_bump_marks_view_stale(db_session):
    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    result = await EpisodeResumeService(db_session).build_resume_view(
        user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
    )
    view = result.view
    assert view["freshness"]["memory_epoch_at_compute"] == 1  # MemoryService 默认 epoch
    assert resume_view_stale_reason(view, now=_NOW, current_memory_epoch=2) == "memory_epoch_changed"


async def test_recompute_is_deterministic_same_authorities_same_view(db_session):
    """同权威 + 同输入 → 逐键相同视图（读模型，非有状态第二真值）。"""
    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    svc = EpisodeResumeService(db_session)
    a = await svc.build_resume_view(user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW)
    db_session.expunge_all()
    b = await svc.build_resume_view(user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW)
    assert a.view == b.view


async def test_outcome_scan_overflow_returns_honest_null(db_session, monkeypatch):
    """I01-R1 C1：有界扫描压顶（>3 页全不匹配且游标不断）→ last_valid_outcome
    诚实 null——不报错、不以替代指标呈现、不死循环。若移除 _OUTCOME_SCAN_MAX_PAGES
    有界性，本测试将挂起/超时（可失败性来源）。"""
    from types import SimpleNamespace

    from app.services import episode_resume_service as _ers

    class _StubLedger:
        def __init__(self, db):
            self.db = db

        async def query(self, *, user_id, until, limit, cursor):
            entry = SimpleNamespace(
                outcome_id="outc_stub",
                truth_class=SimpleNamespace(value="self_reported"),
                occurred_at=_NOW - timedelta(minutes=5),
                correlation={"task_id": "other-task"},
            )
            return SimpleNamespace(items=[entry] * limit, next_cursor="next")

    monkeypatch.setattr(_ers, "OutcomeLedgerService", _StubLedger)
    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    result = await EpisodeResumeService(db_session).build_resume_view(
        user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW
    )
    assert result.view is not None
    assert result.view["last_valid_outcome"] is None


async def test_ttl_validation(db_session):
    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    svc = EpisodeResumeService(db_session)
    with pytest.raises(ValueError, match="ttl_seconds"):
        await svc.build_resume_view(
            user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW, ttl_seconds=0
        )
    with pytest.raises(ValueError, match="ttl_seconds"):
        await svc.build_resume_view(
            user_id=user.id, task_id=task.id, context_receipt_ref=_RECEIPT, now=_NOW, ttl_seconds=25 * 3600
        )
