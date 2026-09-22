from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

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
    day_one = Task(
        user_id=user_id,
        plan_id=plan.id,
        title="Day 1 · 起步 - 图论高频保底",
        type=TaskType.LEARNING,
        estimated_minutes=90,
        order_index=1000,
        guide_json={"objective": "图论高频保底", "output_action": "完成 5 题探针"},
        tags=["规划生成", "离散数学"],
    )
    day_two = Task(
        user_id=user_id,
        plan_id=plan.id,
        title="Day 2 · 递进 - 集合与关系",
        type=TaskType.LEARNING,
        estimated_minutes=90,
        order_index=2000,
        tags=["规划生成", "离散数学"],
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
