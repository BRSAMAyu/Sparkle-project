from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.aurora.runtime_v1.planning import AuroraRuntimePlanningState
from app.core.exceptions import QuotaExceededError
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskType
from app.schemas.exam_sprint import ExamSprintIntakeRequest
from app.services.exam_sprint_intake_service import ExamSprintIntakeService, GeneratedPlanBundle


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_exam_sprint_intake_saves_session_and_returns_launch_payload(db_session) -> None:
    redis = FakeRedis()
    service = ExamSprintIntakeService(db=db_session, redis_client=redis)
    request = ExamSprintIntakeRequest.model_validate(
        {
            "subject": "计算机网络",
            "exam_date": (date.today() + timedelta(days=7)).isoformat(),
            "target_mode": "hold",
            "scope_context": {
                "text": "老师重点是传输层和网络层",
                "file_ids": ["file_1"],
                "file_names": ["scope.pdf"],
            },
            "baseline": {
                "current_level": 42,
                "weak_chapters": ["传输层", "网络层"],
            },
            "daily_study_minutes": 90,
        }
    )
    runtime_state = AuroraRuntimePlanningState(
        user_id=str(uuid4()),
        surface="aurora_planning",
        conversation_id="exam-sprint-conversation",
        runtime_session_id="runtime-session-1",
    )

    service._persist_profile_payloads = AsyncMock()  # type: ignore[method-assign]
    mocked_plan_id = uuid4()  # plans.id 是 GUID 列：真实 _generate_plan_and_tasks 返回原生 UUID
    service._generate_plan_and_tasks = AsyncMock(  # type: ignore[method-assign]
        return_value=GeneratedPlanBundle(
            plan_id=mocked_plan_id,
            plan_name="7天计算机网络冲刺",
            first_day_task_ids=["task_1", "task_2"],
            recommended_task_id="task_1",
            first_day_focus="先做诊断分诊，确认高频保底范围。",
            first_day_output="先做 5 题探针，再整理三栏清单。",
        )
    )
    service.planning_manager.runtime_adapter.get_or_create_state = AsyncMock(return_value=runtime_state)  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.save_state = AsyncMock()  # type: ignore[method-assign]

    user_id = uuid4()
    response = await service.intake(user_id=user_id, request=request)

    assert response.goal_model.days_left in (7, 8)  # UTC vs local date boundary
    assert response.goal_model.target_mode == "hold"
    assert response.goal_model.estimated_score_now == 42
    assert response.initial_assessment.recommended_mode == "pass"
    assert response.selected_pack.pack_id in ("generic_exam_survival", "exam_prep_14d@v1.0")
    assert UUID(response.launch.plan_id) == mocked_plan_id
    assert response.launch.recommended_task_route == "/tasks/task_1"

    # 键格式实为 planning:session:{user_id}::{chat_session_id}
    # （PLANNING_SESSION_PREFIX 自带尾冒号，save_session 的 user_prefix 再补一个）
    raw_session = redis.store[f"planning:session:{user_id}::{response.conversation_id}"]
    payload = json.loads(raw_session)
    assert payload["planning_session_id"] == response.planning_session_id
    assert payload["collected"]["subject"] == "计算机网络"
    assert payload["collected"]["target_mode"] == "hold"
    assert payload["collected"]["cold_start_context"]["weak_chapters"] == ["传输层", "网络层"]


@pytest.mark.asyncio
async def test_exam_sprint_intake_reuses_existing_plan_for_same_goal(db_session) -> None:
    """BP-7 幂等：同 user + 同 goal（subject+exam_date）复跑 intake 必须返回既有 plan，而非 403/双计划。"""
    user_id = uuid4()
    exam_date = date.today() + timedelta(days=7)
    plan = Plan(
        user_id=user_id,
        name="7天离散数学冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject="离散数学",
        target_date=exam_date,
        daily_available_minutes=165,
        is_active=True,
        priority=PlanPriority.HIGH,
    )
    db_session.add(plan)
    await db_session.flush()
    # INTAKE-TEMPLATE 形状契约：intake 真实生成的任务恒带 day:N 标签
    # （见 _create_sprint_template_tasks 的 tags）——夹具必须忠实于该形状，
    # 否则复用补模板会把此夹具误判为"无模板计划"而补任务。
    day_one = Task(
        user_id=user_id,
        plan_id=plan.id,
        title="Day 1 · 起步 - 图论高频保底",
        type=TaskType.LEARNING,
        estimated_minutes=90,
        order_index=1000,
        guide_json={"objective": "图论高频保底", "output_action": "完成 5 题探针"},
        tags=["规划生成", "离散数学", "phase:1", "day:1"],
    )
    day_two = Task(
        user_id=user_id,
        plan_id=plan.id,
        title="Day 2 · 递进 - 集合与关系",
        type=TaskType.LEARNING,
        estimated_minutes=90,
        order_index=2000,
        tags=["规划生成", "离散数学", "phase:1", "day:2"],
    )
    db_session.add_all([day_one, day_two])
    await db_session.commit()

    service = ExamSprintIntakeService(db=db_session, redis_client=FakeRedis())
    runtime_state = AuroraRuntimePlanningState(
        user_id=str(user_id),
        surface="aurora_planning",
        conversation_id="exam-sprint-idempotent",
        runtime_session_id="runtime-session-idempotent",
    )
    service._persist_profile_payloads = AsyncMock()  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.get_or_create_state = AsyncMock(return_value=runtime_state)  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.save_state = AsyncMock()  # type: ignore[method-assign]
    # 复现 BP-7：若幂等失效走到生成路径，将触发计划配额 403（QuotaExceededError）
    service._generate_plan_and_tasks = AsyncMock(  # type: ignore[method-assign]
        side_effect=QuotaExceededError("已达计划数量上限(3个)，请归档旧计划或升级账户")
    )

    request = ExamSprintIntakeRequest.model_validate(
        {
            "subject": "离散数学",
            "exam_date": exam_date.isoformat(),
            "target_mode": "pass",
            "scope_context": {"text": "覆盖 CH1-CH6"},
            "baseline": {"current_level": 42, "weak_chapters": ["CH4 图论"]},
            "daily_study_minutes": 165,
        }
    )

    response = await service.intake(user_id=user_id, request=request)

    service._generate_plan_and_tasks.assert_not_called()
    assert UUID(response.launch.plan_id) == plan.id
    assert response.launch.plan_name == "7天离散数学冲刺"
    assert response.launch.first_day_task_ids == [str(day_one.id)]
    assert response.launch.recommended_task_id == str(day_one.id)
    assert response.launch.plan_route == f"/plans/{plan.id}"
    assert response.strategy_preview.first_day_focus == "图论高频保底"
    assert response.strategy_preview.first_day_output == "完成 5 题探针"


def test_exam_sprint_pack_selection_uses_builtin_pack_for_14_day_window(db_session) -> None:
    service = ExamSprintIntakeService(db=db_session, redis_client=FakeRedis())

    selected = service._select_pack(days_left=14)
    assessment = service._build_initial_assessment(
        request=ExamSprintIntakeRequest.model_validate(
            {
                "subject": "操作系统",
                "exam_date": (date.today() + timedelta(days=14)).isoformat(),
                "target_mode": "high_score",
                "scope_context": {"text": "进程、内存、文件系统"},
                "baseline": {
                    "current_level": 78,
                    "weak_chapters": ["内存管理"],
                },
                "daily_study_minutes": 150,
            }
        ),
        goal_model=service._build_goal_model(
            request=ExamSprintIntakeRequest.model_validate(
                {
                    "subject": "操作系统",
                    "exam_date": (date.today() + timedelta(days=14)).isoformat(),
                    "target_mode": "high_score",
                    "scope_context": {"text": "进程、内存、文件系统"},
                    "baseline": {
                        "current_level": 78,
                        "weak_chapters": ["内存管理"],
                    },
                    "daily_study_minutes": 150,
                }
            ),
            days_left=14,
        ),
        days_left=14,
    )

    assert selected.selection_type == "scenario_pack"
    assert selected.pack_id == "exam_prep_14d@v1.0"
    assert assessment.recommended_mode in {"hold", "high_score"}


# ---------------------------------------------------------------------------
# NBP-3（v3-output/NORTHSTAR-LOOP2/REPORT.md）：goal→intake 双计划残余。
# goals.py create_goal 自建的 sprint 计划 subject=None，BP-7 匹配键
# (subject, target_date) 永不命中 → intake 另建第二份 active sprint plan
# （subject 为 NULL 的行不在 uq_plans_user_sprint_goal_active 索引谓词内，
# 不撞索引、静默双计划）。修复语义：subject 匹配不到时按 goal→plan 关联
# 兜底（同 user + SPRINT + active + target_date==exam_date + 关联 exam 型
# goal），复用时回填 subject——回填后同表单复跑走 BP-7 主键且纳入
# INTAKE-IDX 唯一索引保护，幂等语义收敛为自愈。
# ---------------------------------------------------------------------------
from app.models.goal import Goal  # noqa: E402


async def _seed_goal_linked_sprint_plan(db_session, user_id, *, exam_date, goal_type="exam", subject=None):
    """复刻 goals.py create_goal 的 goal→plan 落库形状（plan.subject 恒为 NULL）。"""
    goal = Goal(
        user_id=user_id,
        title="离散数学期末 7 天冲刺：及格冲 70+",
        goal_type=goal_type,
        target_date=exam_date,
        status="active",
    )
    db_session.add(goal)
    await db_session.flush()
    plan = Plan(
        user_id=user_id,
        goal_id=goal.id,
        name="离散数学期末 7 天冲刺：及格冲 70+",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject=subject,  # goal 驱动创建路径从不写 subject
        target_date=exam_date,
        daily_available_minutes=60,
        is_active=True,
        priority=PlanPriority.HIGH,
    )
    db_session.add(plan)
    await db_session.flush()
    day_one = Task(
        user_id=user_id,
        plan_id=plan.id,
        title="Day 1 · 起步 - 目标里程碑第一步",
        type=TaskType.LEARNING,
        estimated_minutes=25,
        order_index=1000,
        tags=["goal_first_step"],
    )
    db_session.add(day_one)
    await db_session.commit()
    return goal, plan, day_one


def _intake_request_for(exam_date, subject="离散数学") -> ExamSprintIntakeRequest:
    return ExamSprintIntakeRequest.model_validate(
        {
            "subject": subject,
            "exam_date": exam_date.isoformat(),
            "target_mode": "pass",
            "scope_context": {"text": "覆盖 CH1-CH6"},
            "baseline": {"current_level": 42, "weak_chapters": ["CH4 图论"]},
            "daily_study_minutes": 165,
        }
    )


@pytest.mark.asyncio
async def test_intake_reuses_goal_created_plan_when_subject_is_null(db_session) -> None:
    """NBP-3 主红：goal 建的 plan（subject=NULL）必须被 intake 复用，而非静默双计划。"""
    user_id = uuid4()
    exam_date = date.today() + timedelta(days=7)
    goal, plan, day_one = await _seed_goal_linked_sprint_plan(db_session, user_id, exam_date=exam_date)

    service = ExamSprintIntakeService(db=db_session, redis_client=FakeRedis())
    runtime_state = AuroraRuntimePlanningState(
        user_id=str(user_id),
        surface="aurora_planning",
        conversation_id="exam-sprint-goal-reuse",
        runtime_session_id="runtime-session-goal-reuse",
    )
    service._persist_profile_payloads = AsyncMock()  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.get_or_create_state = AsyncMock(return_value=runtime_state)  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.save_state = AsyncMock()  # type: ignore[method-assign]
    # 复现 BP-7 断言口径：若 goal 关联兜底缺失走到生成路径，立即以配额 403 炸红
    service._generate_plan_and_tasks = AsyncMock(  # type: ignore[method-assign]
        side_effect=QuotaExceededError("已达计划数量上限(3个)，请归档旧计划或升级账户")
    )

    response = await service.intake(user_id=user_id, request=_intake_request_for(exam_date))

    service._generate_plan_and_tasks.assert_not_called()
    assert UUID(response.launch.plan_id) == plan.id
    assert response.launch.plan_name == "离散数学期末 7 天冲刺：及格冲 70+"
    # INTAKE-TEMPLATE：复用补模板后，day-1 包 = 既有里程碑任务 + 新模板任务
    assert str(day_one.id) in response.launch.first_day_task_ids

    # 只有一份 active sprint 计划（无第二份静默双计划）
    sprint_plans = (
        (await db_session.execute(select(Plan).where(Plan.user_id == user_id, Plan.type == PlanType.SPRINT)))
        .scalars()
        .all()
    )
    assert len(sprint_plans) == 1

    # 自愈回填：复用后 plan.subject 收敛为 intake 表单 subject（此后复跑走
    # BP-7 主键，并纳入 INTAKE-IDX 唯一索引保护）
    await db_session.refresh(plan)
    assert plan.subject == "离散数学"

    # INTAKE-TEMPLATE：复用不再让 7 天脊柱缺位——计划必须获得 day:N 模板任务
    plan_tasks = (await db_session.execute(select(Task).where(Task.plan_id == plan.id))).scalars().all()
    day_indices = {
        int(str(tag).split(":", maxsplit=1)[1])
        for task in plan_tasks
        for tag in (task.tags or [])
        if str(tag).startswith("day:")
    }
    assert day_indices, "goal 计划复用后必须补出 day:N 模板任务"
    assert str(day_one.id) in {str(task.id) for task in plan_tasks}  # 用户已有任务不删


@pytest.mark.asyncio
async def test_intake_reuses_goal_created_plan_with_canonical_academic_type(db_session) -> None:
    """NBP-3b（LOOP3 实测）：真实 goal_decomposition 链把 exam 归一为模板键 academic
    落库（_CANONICAL_TO_TEMPLATE），夹具若只插 "exam" 会复现「单测绿运行红」——
    canonical 族键必须同样命中复用，否则用户走真实链路即双计划。"""
    user_id = uuid4()
    exam_date = date.today() + timedelta(days=7)
    goal, plan, day_one = await _seed_goal_linked_sprint_plan(
        db_session, user_id, exam_date=exam_date, goal_type="academic"
    )

    service = ExamSprintIntakeService(db=db_session, redis_client=FakeRedis())
    runtime_state = AuroraRuntimePlanningState(
        user_id=str(user_id),
        surface="aurora_planning",
        conversation_id="exam-sprint-goal-reuse-academic",
        runtime_session_id="runtime-session-goal-reuse-academic",
    )
    service._persist_profile_payloads = AsyncMock()  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.get_or_create_state = AsyncMock(return_value=runtime_state)  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.save_state = AsyncMock()  # type: ignore[method-assign]
    service._generate_plan_and_tasks = AsyncMock(side_effect=AssertionError("academic 键必须命中复用，不得生成新计划"))  # type: ignore[method-assign]

    response = await service.intake(user_id=user_id, request=_intake_request_for(exam_date))

    service._generate_plan_and_tasks.assert_not_called()
    assert UUID(response.launch.plan_id) == plan.id
    # INTAKE-TEMPLATE：canonical academic 键命中复用后同样补 day:N 模板
    assert str(day_one.id) in response.launch.first_day_task_ids
    plan_tasks = (await db_session.execute(select(Task).where(Task.plan_id == plan.id))).scalars().all()
    assert any(str(tag).startswith("day:") for task in plan_tasks for tag in (task.tags or [])), (
        "academic 族复用后必须补出 day:N 模板任务"
    )


@pytest.mark.asyncio
async def test_intake_does_not_reuse_goal_plan_for_different_exam_date(db_session) -> None:
    """不同 exam_date = 不同目标：goal 关联兜底不得越界复用（保持 BP-7 语义）。"""
    user_id = uuid4()
    exam_date = date.today() + timedelta(days=7)
    await _seed_goal_linked_sprint_plan(db_session, user_id, exam_date=exam_date)

    service = ExamSprintIntakeService(db=db_session, redis_client=FakeRedis())
    runtime_state = AuroraRuntimePlanningState(
        user_id=str(user_id),
        surface="aurora_planning",
        conversation_id="exam-sprint-goal-reuse-neg",
        runtime_session_id="runtime-session-goal-reuse-neg",
    )
    service._persist_profile_payloads = AsyncMock()  # type: ignore[method-assign]
    service._record_north_star_intake_metrics = AsyncMock()  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.get_or_create_state = AsyncMock(return_value=runtime_state)  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.save_state = AsyncMock()  # type: ignore[method-assign]
    other_plan_id = uuid4()
    service._generate_plan_and_tasks = AsyncMock(  # type: ignore[method-assign]
        return_value=GeneratedPlanBundle(
            plan_id=other_plan_id,
            plan_name="7天离散数学冲刺",
            first_day_task_ids=[],
            recommended_task_id=None,
            first_day_focus="",
            first_day_output="",
        )
    )

    response = await service.intake(user_id=user_id, request=_intake_request_for(exam_date + timedelta(days=30)))

    service._generate_plan_and_tasks.assert_awaited_once()
    assert UUID(response.launch.plan_id) == other_plan_id


@pytest.mark.asyncio
async def test_intake_does_not_reuse_non_exam_goal_plan(db_session) -> None:
    """非 exam 型 goal 的同日计划不构成同一考试目标：不得复用。"""
    user_id = uuid4()
    exam_date = date.today() + timedelta(days=7)
    await _seed_goal_linked_sprint_plan(db_session, user_id, exam_date=exam_date, goal_type="project")

    service = ExamSprintIntakeService(db=db_session, redis_client=FakeRedis())
    runtime_state = AuroraRuntimePlanningState(
        user_id=str(user_id),
        surface="aurora_planning",
        conversation_id="exam-sprint-goal-reuse-neg2",
        runtime_session_id="runtime-session-goal-reuse-neg2",
    )
    service._persist_profile_payloads = AsyncMock()  # type: ignore[method-assign]
    service._record_north_star_intake_metrics = AsyncMock()  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.get_or_create_state = AsyncMock(return_value=runtime_state)  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.save_state = AsyncMock()  # type: ignore[method-assign]
    other_plan_id = uuid4()
    service._generate_plan_and_tasks = AsyncMock(  # type: ignore[method-assign]
        return_value=GeneratedPlanBundle(
            plan_id=other_plan_id,
            plan_name="7天离散数学冲刺",
            first_day_task_ids=[],
            recommended_task_id=None,
            first_day_focus="",
            first_day_output="",
        )
    )

    response = await service.intake(user_id=user_id, request=_intake_request_for(exam_date))

    service._generate_plan_and_tasks.assert_awaited_once()
    assert UUID(response.launch.plan_id) == other_plan_id


# ---------------------------------------------------------------------------
# INTAKE-TEMPLATE（v3-output/INTAKE-TEMPLATE/REPORT.md）：复用路径补 7 天模板。
# NBP-3/3b 复用防住了双计划，但 goal 计划只有里程碑梯任务（goals.py 只建
# goal_first_step，无 day:N 标签）——daily_task_selection._plan_current_day
# 依赖 day:N 标签推进旅程，复用即跳过模板生成 = exam-sprint 的 Day1-Day7
# 脊柱在最常见路径缺位（JOURNEY-DRIVER 实测 S2 不可观测）。修复语义（方案
# A，保复用防双计划 + 补模板保旅程）：复用后计划无 day:N 形状任务则补生成
# 模板挂到该计划——幂等（已有则跳过）、不删用户已有任务、不新建计划。
# ---------------------------------------------------------------------------
from datetime import UTC, datetime  # noqa: E402


def _expected_days_left(exam_date: date) -> int:
    """与 ExamSprintIntakeService._today()（UTC）同一口径，吃掉时区边界抖动。"""
    return max(1, (exam_date - datetime.now(UTC).date()).days)


async def _plan_day_indices(db_session, plan_id) -> tuple[dict[int, list[Task]], list[Task]]:
    """返回 (day_index -> 任务列表, 无 day 标签的任务列表)。"""
    plan_tasks = (await db_session.execute(select(Task).where(Task.plan_id == plan_id))).scalars().all()
    by_day: dict[int, list[Task]] = {}
    untagged: list[Task] = []
    for task in plan_tasks:
        day_of_task = next(
            (int(str(tag).split(":", maxsplit=1)[1]) for tag in (task.tags or []) if str(tag).startswith("day:")),
            None,
        )
        if day_of_task is None:
            untagged.append(task)
        else:
            by_day.setdefault(day_of_task, []).append(task)
    return by_day, untagged


def _reuse_service(db_session, user_id, conversation: str) -> ExamSprintIntakeService:
    """复用路径测试的标准 mock 面（与 NBP-3 族夹具一致）。"""
    service = ExamSprintIntakeService(db=db_session, redis_client=FakeRedis())
    runtime_state = AuroraRuntimePlanningState(
        user_id=str(user_id),
        surface="aurora_planning",
        conversation_id=conversation,
        runtime_session_id=f"runtime-{conversation}",
    )
    service._persist_profile_payloads = AsyncMock()  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.get_or_create_state = AsyncMock(return_value=runtime_state)  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.save_state = AsyncMock()  # type: ignore[method-assign]
    return service


@pytest.mark.asyncio
async def test_intake_reuse_supplements_seven_day_template_for_goal_plan(db_session) -> None:
    """主红：goal 建计划 → intake 复用 → 计划必须获得 Day1..DayN 模板脊柱。"""
    user_id = uuid4()
    exam_date = date.today() + timedelta(days=7)
    goal, plan, milestone = await _seed_goal_linked_sprint_plan(db_session, user_id, exam_date=exam_date)

    service = _reuse_service(db_session, user_id, "intake-template-supplement")
    # 复用语义红线：补模板绝不允许退化成第二份计划生成
    service._generate_plan_and_tasks = AsyncMock(  # type: ignore[method-assign]
        side_effect=AssertionError("复用路径不得触发新计划生成（NBP-3 双计划回归）")
    )

    response = await service.intake(user_id=user_id, request=_intake_request_for(exam_date))

    service._generate_plan_and_tasks.assert_not_called()

    # 仍只有一份 sprint 计划；模板任务挂在该计划上
    sprint_plans = (
        (await db_session.execute(select(Plan).where(Plan.user_id == user_id, Plan.type == PlanType.SPRINT)))
        .scalars()
        .all()
    )
    assert len(sprint_plans) == 1
    assert sprint_plans[0].id == plan.id

    # Day1..DayN 全脊柱：与 intake 计算的 days_left 同一预期口径
    by_day, untagged = await _plan_day_indices(db_session, plan.id)
    expected_days = set(range(1, _expected_days_left(exam_date) + 1))
    assert set(by_day) == expected_days, f"day 脊柱缺口: {sorted(set(expected_days) - set(by_day))}"

    # 模板形状契约：day:N 标签 + day*1000 order_index（daily_task_selection 双口径）
    for day, tasks in by_day.items():
        for task in tasks:
            assert int(task.order_index or 0) // 1000 == day
    # 冲刺 pack 形状：任务带 phase:/task_kind 标签（sprint pack 任务卡）
    assert any(
        any(str(tag).startswith("phase:") for tag in (task.tags or [])) for tasks in by_day.values() for task in tasks
    )

    # 用户已有任务不删：里程碑任务原样保留
    assert milestone.id in {task.id for task in untagged}

    # 复用计划升级为一等冲刺计划：元数据块齐全（dashboard/day_highlights/考后复盘）
    await db_session.refresh(plan)
    metadata = plan.source_metadata if isinstance(plan.source_metadata, dict) else {}
    assert "exam_sprint_intake" in metadata
    assert "day_highlights" in metadata
    assert metadata["post_exam_review"]["eligible_after"] == exam_date.isoformat()

    # launch 锚点指向补模板后的 day-1 包（含既有里程碑）
    assert response.launch.first_day_task_ids
    assert str(milestone.id) in response.launch.first_day_task_ids


@pytest.mark.asyncio
async def test_intake_reuse_supplement_is_idempotent_on_repeat(db_session) -> None:
    """幂等：重复 intake 不得重复生成模板（第二次经 BP-7 主键复用 + 形状闸跳过）。"""
    user_id = uuid4()
    exam_date = date.today() + timedelta(days=7)
    goal, plan, milestone = await _seed_goal_linked_sprint_plan(db_session, user_id, exam_date=exam_date)

    first_service = _reuse_service(db_session, user_id, "intake-template-idem-1")
    first_service._generate_plan_and_tasks = AsyncMock(side_effect=AssertionError("must reuse"))  # type: ignore[method-assign]
    first_response = await first_service.intake(user_id=user_id, request=_intake_request_for(exam_date))

    tasks_after_first = (await db_session.execute(select(Task).where(Task.plan_id == plan.id))).scalars().all()
    count_after_first = len(tasks_after_first)
    assert count_after_first > 1  # 补模板已发生

    second_service = _reuse_service(db_session, user_id, "intake-template-idem-2")
    second_service._generate_plan_and_tasks = AsyncMock(side_effect=AssertionError("must reuse"))  # type: ignore[method-assign]
    second_response = await second_service.intake(user_id=user_id, request=_intake_request_for(exam_date))

    # 同一计划、任务零增长（不重复生成）
    assert UUID(second_response.launch.plan_id) == UUID(first_response.launch.plan_id) == plan.id
    tasks_after_second = (await db_session.execute(select(Task).where(Task.plan_id == plan.id))).scalars().all()
    assert len(tasks_after_second) == count_after_first

    by_day, _ = await _plan_day_indices(db_session, plan.id)
    expected_days = set(range(1, _expected_days_left(exam_date) + 1))
    assert set(by_day) == expected_days  # 且脊柱完整


@pytest.mark.asyncio
async def test_intake_does_not_force_template_on_non_exam_goal_plan(db_session) -> None:
    """非 exam 族 goal 的计划不复用也不强加模板（补模板只跟随 exam-sprint 复用）。"""
    user_id = uuid4()
    exam_date = date.today() + timedelta(days=7)
    goal, plan, milestone = await _seed_goal_linked_sprint_plan(
        db_session, user_id, exam_date=exam_date, goal_type="project"
    )

    service = _reuse_service(db_session, user_id, "intake-template-neg")
    service._record_north_star_intake_metrics = AsyncMock()  # type: ignore[method-assign]
    service._supplement_sprint_template_tasks = AsyncMock()  # type: ignore[method-assign]
    other_plan_id = uuid4()
    service._generate_plan_and_tasks = AsyncMock(  # type: ignore[method-assign]
        return_value=GeneratedPlanBundle(
            plan_id=other_plan_id,
            plan_name="7天离散数学冲刺",
            first_day_task_ids=[],
            recommended_task_id=None,
            first_day_focus="",
            first_day_output="",
        )
    )

    response = await service.intake(user_id=user_id, request=_intake_request_for(exam_date))

    # 走生成路径（project 族不复用），且补模板根本不被触发
    service._generate_plan_and_tasks.assert_awaited_once()
    service._supplement_sprint_template_tasks.assert_not_awaited()
    assert UUID(response.launch.plan_id) == other_plan_id

    # project goal 计划保持原样：无 day:N 任务被强加，里程碑无恙
    by_day, untagged = await _plan_day_indices(db_session, plan.id)
    assert by_day == {}
    assert milestone.id in {task.id for task in untagged}


@pytest.mark.asyncio
async def test_intake_supplement_skips_non_goal_plan_even_without_day_tags(db_session) -> None:
    """goal 闸：无 goal_id 的计划即使没有 day:N 标签也不得补挂。

    这钉住并发契约：intake 生成路径先提交计划、任务随后（PlanService.create
    内部 commit 与任务不同事务），并发 intake 的复用查询可能命中"已提交但
    脊柱未落"的半成品计划——那种计划的生成方正在补齐自己的模板，补挂会
    造成双模板 + plan_state 竞态（真并发测试实测）。只有 goal 计划（无生成
    方）才是补挂对象。
    """
    user_id = uuid4()
    exam_date = date.today() + timedelta(days=7)
    plan = Plan(
        user_id=user_id,
        name="7天离散数学冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject="离散数学",
        target_date=exam_date,
        daily_available_minutes=165,
        is_active=True,
        priority=PlanPriority.HIGH,
        # goal_id 恒为 None：intake/手动创建的计划
    )
    db_session.add(plan)
    await db_session.flush()
    bare_task = Task(
        user_id=user_id,
        plan_id=plan.id,
        title="普通任务",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        order_index=10,
        tags=["手动"],
    )
    db_session.add(bare_task)
    await db_session.commit()

    service = _reuse_service(db_session, user_id, "intake-template-goal-gate")
    service._generate_plan_and_tasks = AsyncMock(side_effect=AssertionError("must reuse"))  # type: ignore[method-assign]
    service._supplement_sprint_template_tasks = AsyncMock(  # type: ignore[method-assign]
        wraps=service._supplement_sprint_template_tasks
    )

    response = await service.intake(user_id=user_id, request=_intake_request_for(exam_date))

    # 复用发生，补挂被 goal 闸跳过：任务零增长
    service._generate_plan_and_tasks.assert_not_called()
    service._supplement_sprint_template_tasks.assert_awaited_once()
    assert UUID(response.launch.plan_id) == plan.id
    tasks_now = (await db_session.execute(select(Task).where(Task.plan_id == plan.id))).scalars().all()
    assert [task.id for task in tasks_now] == [bare_task.id]
