from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.v1.exam_sprint import router as exam_sprint_router
from app.models.user import User


@pytest.fixture
def exam_sprint_client(db_session):
    app = FastAPI()
    app.include_router(exam_sprint_router, prefix="/exam-sprint")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


@pytest.mark.asyncio
async def test_exam_sprint_intake_endpoint_returns_structured_payload(exam_sprint_client, db_session):
    client, state = exam_sprint_client
    user = User(
        username="exam_sprint_user",
        email="exam_sprint_user@example.com",
        hashed_password="hashed",
        nickname="Mika",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    exam_date = date.today() + timedelta(days=7)
    payload = {
        "subject": "计算机网络",
        "exam_date": exam_date.isoformat(),
        "target_mode": "hold",
        "scope_context": {
            "text": "老师说重点看传输层、网络层和应用层",
            "file_ids": ["file_1"],
            "file_names": ["重点范围.pdf"],
        },
        "baseline": {
            "current_level": 38,
            "weak_chapters": ["传输层", "网络层"],
        },
        "daily_study_minutes": 90,
    }
    response_payload = {
        "planning_session_id": "planning-session-1",
        "conversation_id": "exam-sprint-1",
        "user_model": {
            "subject": "计算机网络",
            "exam_scope": "老师说重点看传输层、网络层和应用层",
            "knowledge_baseline": "上过课但没复习",
            "current_level": 38,
            "weak_chapters": ["传输层", "网络层"],
            "daily_study_minutes": 90,
            "available_materials": ["老师重点", "上传资料"],
            "scope_file_ids": ["file_1"],
            "scope_file_names": ["重点范围.pdf"],
            "planning_session_id": "planning-session-1",
            "conversation_id": "exam-sprint-1",
        },
        "goal_model": {
            "exam_date": exam_date.isoformat(),
            "days_left": 7,
            "target_mode": "hold",
            "estimated_score_now": 38,
            "target_score_hint": 75,
            "recommended_mode": "pass",
        },
        "selected_pack": {
            "pack_id": "generic_exam_survival",
            "pack_name": "7-Day Survival Sprint",
            "selection_type": "generic_policy",
            "reason": "距离考试只有 7 天，优先启用保底生存策略。",
        },
        "initial_assessment": {
            "pass_probability": 0.41,
            "recommended_mode": "pass",
            "recommended_mode_label": "先过",
            "summary": "基于你的基础、时间和范围清晰度，7 天内通过概率约 41%。建议先用「先过」模式，今天先把第一天任务跑起来。",
        },
        "strategy_preview": {
            "sprint_mode": "seven_day_survival",
            "daily_commitment_range": "1–2小时",
            "first_day_focus": "诊断分诊",
            "first_day_output": "先做 5 题探针或 8 分钟闭卷回忆，再整理一张「保底 / 补强 / defer_or_skip」三栏清单。",
        },
        "launch": {
            "plan_id": "plan_1",
            "plan_name": "7天计算机网络冲刺",
            "first_day_task_ids": ["task_1"],
            "recommended_task_id": "task_1",
            "plan_route": "/plans/plan_1",
            "recommended_task_route": "/tasks/task_1",
        },
    }

    with patch(
        "app.api.v1.exam_sprint.ExamSprintIntakeService.intake",
        new=AsyncMock(return_value=response_payload),
    ) as mock_intake:
        response = client.post("/exam-sprint/intake", json=payload)

    assert response.status_code == 200
    assert response.json() == response_payload
    mock_intake.assert_awaited_once()
    _, kwargs = mock_intake.await_args
    assert kwargs["user_id"] == user.id
    assert kwargs["request"].subject == "计算机网络"


def test_exam_sprint_intake_endpoint_rejects_past_exam_date(exam_sprint_client):
    client, state = exam_sprint_client
    state["current_user"] = User(
        username="exam_sprint_validation_user",
        email="exam_sprint_validation_user@example.com",
        hashed_password="hashed",
    )

    payload = {
        "subject": "高数",
        "exam_date": (date.today() - timedelta(days=1)).isoformat(),
        "target_mode": "pass",
        "scope_context": {"text": ""},
        "baseline": {"current_level": 20, "weak_chapters": []},
        "daily_study_minutes": 60,
    }

    response = client.post("/exam-sprint/intake", json=payload)

    assert response.status_code == 422
