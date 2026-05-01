from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.aurora.runtime_v1.planning import AuroraRuntimePlanningState
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
    service._generate_plan_and_tasks = AsyncMock(  # type: ignore[method-assign]
        return_value=GeneratedPlanBundle(
            plan_id="plan_123",
            plan_name="7天计算机网络冲刺",
            first_day_task_ids=["task_1", "task_2"],
            recommended_task_id="task_1",
            first_day_focus="先做诊断分诊，确认高频保底范围。",
            first_day_output="先做 5 题探针，再整理三栏清单。",
        )
    )
    service.planning_manager.runtime_adapter.get_or_create_state = AsyncMock(return_value=runtime_state)  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.save_state = AsyncMock()  # type: ignore[method-assign]

    response = await service.intake(user_id=uuid4(), request=request)

    assert response.goal_model.days_left == 7
    assert response.goal_model.target_mode == "hold"
    assert response.goal_model.estimated_score_now == 42
    assert response.initial_assessment.recommended_mode == "pass"
    assert response.selected_pack.pack_id == "generic_exam_survival"
    assert response.launch.plan_id == "plan_123"
    assert response.launch.recommended_task_route == "/tasks/task_1"

    raw_session = redis.store[f"planning:session:{response.conversation_id}"]
    payload = json.loads(raw_session)
    assert payload["planning_session_id"] == response.planning_session_id
    assert payload["collected"]["subject"] == "计算机网络"
    assert payload["collected"]["target_mode"] == "hold"
    assert payload["collected"]["cold_start_context"]["weak_chapters"] == ["传输层", "网络层"]


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
