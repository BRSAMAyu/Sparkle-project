from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.plans import router as plans_router
from app.db.session import get_db
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.plan_state import PlanState, PlanStateStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User


@pytest.fixture
def plans_client(db_session):
    app = FastAPI()
    app.include_router(plans_router, prefix="/plans")

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
async def test_growth_archive_restore_round_trip_does_not_raise(db_session, plans_client):
    client, state = plans_client
    user = User(
        username="plan_growth_user",
        email="plan_growth_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="长期计划",
        type=PlanType.GROWTH,
        description="测试成长计划归档与恢复",
        plan_stage=PlanStage.REVIEW,
        target_date=date(2026, 7, 1),
        daily_available_minutes=45,
        total_estimated_hours=40,
        subject="系统设计",
        mastery_level=0.4,
        progress=0.6,
        is_active=True,
        priority=PlanPriority.HIGH,
    )
    db_session.add(plan)
    await db_session.flush()

    db_session.add(
        PlanState(
            user_id=user.id,
            plan_id=plan.id,
            status=PlanStateStatus.ACTIVE.value,
            version=1,
        )
    )
    await db_session.commit()
    await db_session.refresh(plan)
    state["current_user"] = user

    archive_response = client.post(f"/plans/{plan.id}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == PlanStateStatus.ARCHIVED.value

    await db_session.refresh(plan)
    assert plan.is_active is False

    restore_response = client.post(f"/plans/{plan.id}/restore")
    assert restore_response.status_code == 200
    assert restore_response.json()["status"] == PlanStateStatus.ACTIVE.value

    await db_session.refresh(plan)
    assert plan.is_active is True


@pytest.mark.asyncio
async def test_plan_list_and_detail_include_mobile_required_fields(db_session, plans_client):
    client, state = plans_client
    user = User(
        username="plan_contract_user",
        email="plan_contract_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="成长计划契约",
        type=PlanType.GROWTH,
        description="检查移动端依赖字段",
        plan_stage=PlanStage.DAILY,
        target_date=date(2026, 8, 1),
        daily_available_minutes=50,
        total_estimated_hours=60,
        subject="分布式系统",
        mastery_level=0.3,
        progress=0.2,
        is_active=True,
        priority=PlanPriority.NORMAL,
        source="learning_path",
        source_metadata={"target_node_id": "node-1"},
    )
    db_session.add(plan)
    await db_session.flush()

    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="任务 1",
            type=TaskType.LEARNING,
            tags=["plan"],
            estimated_minutes=30,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.PENDING,
            priority=2,
        )
    )
    db_session.add(
        PlanState(
            user_id=user.id,
            plan_id=plan.id,
            status=PlanStateStatus.ACTIVE.value,
            version=1,
            task_index={"completed": 1, "total": 4, "avg_completion_rate": 0.25},
            task_summaries=[],
        )
    )
    await db_session.commit()
    state["current_user"] = user

    list_response = client.get("/plans")
    assert list_response.status_code == 200
    item = list_response.json()["data"][0]
    for required_key in (
        "user_id",
        "daily_available_minutes",
        "updated_at",
        "plan_stage",
        "source",
        "source_metadata",
        "health_score",
        "health_status",
    ):
        assert required_key in item
    assert item["health_score"] is not None

    detail_response = client.get(f"/plans/{plan.id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["health_score"] is not None
    assert detail["health_status"] in {"healthy", "warning", "critical"}
    assert detail["tasks"] is not None
    assert len(detail["tasks"]) == 1
    assert detail["tasks"][0]["plan_id"] == str(plan.id)


@pytest.mark.asyncio
async def test_plan_today_exposes_compressed_recovery_task(db_session, plans_client):
    client, state = plans_client
    user = User(
        username="plan_today_compressed_user",
        email="plan_today_compressed_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="7天计网冲刺",
        type=PlanType.SPRINT,
        description='{"strategy": {"total_days": 7}}',
        plan_stage=PlanStage.SPRINT,
        target_date=date.today() + timedelta(days=3),
        daily_available_minutes=120,
        total_estimated_hours=14,
        subject="计算机网络",
        mastery_level=0.3,
        progress=0.3,
        is_active=True,
        priority=PlanPriority.HIGH,
    )
    db_session.add(plan)
    await db_session.flush()

    reason = "前一天完成率只有 30%，低于 50%，而距离考试只剩 5 天；所以 Day 5 自动压缩为保底版。"
    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="Day 5 · 压缩保底 - TCP 拥塞控制",
            type=TaskType.LEARNING,
            tags=["day:5", "compressed_recovery"],
            estimated_minutes=35,
            difficulty=1,
            energy_cost=1,
            status=TaskStatus.PENDING,
            priority=2,
            order_index=5000,
            guide_json={
                "compressed": True,
                "compression_reason": reason,
                "task_kind": "compressed_recovery",
                "daily_spec": {"day": 5, "compressed": True},
            },
        )
    )
    await db_session.commit()
    state["current_user"] = user

    response = client.get(f"/plans/{plan.id}/today")

    assert response.status_code == 200
    payload = response.json()
    assert payload["day"] == 5
    assert payload["compressed"] is True
    assert payload["compression_reason"] == reason
    assert payload["tasks"][0]["compressed"] is True
    assert payload["tasks"][0]["compression_reason"] == reason
