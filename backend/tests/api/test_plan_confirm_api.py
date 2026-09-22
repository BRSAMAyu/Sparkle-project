"""CP-01：exam-sprint 计划人工确认端点（POST /plans/{plan_id}/confirm）API 级测试。

闭环语义（行为定义，REPORT.md 同步登记）：
- 首次确认 → 200，confirmed_at 落值，already_confirmed=False；
- 重复确认 → 200 幂等：confirmed_at 保留首次值，already_confirmed=True；
- 他人计划 → 404（对齐 plans 域统一 404 防资源枚举风格）；
- 计划不存在 → 404；
- 软删计划（deleted_at 非空）→ 404；
- 已归档（is_active=False）未软删 → 允许确认：确认记录用户意图，
  不改 is_active（最小行为面，不扩散到归档/配额域）。
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.plans import router as plans_router
from app.db.session import get_db
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.user import User


@pytest.fixture
def confirm_client(db_session):
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


async def _make_user(db_session, username: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_plan(db_session, user_id, **overrides) -> Plan:
    defaults: dict = {
        "user_id": user_id,
        "name": "7天高数冲刺",
        "type": PlanType.SPRINT,
        "description": "考试冲刺计划",
        "plan_stage": PlanStage.SPRINT,
        "target_date": date.today() + timedelta(days=7),
        "daily_available_minutes": 90,
        "total_estimated_hours": 12,
        "subject": "高等数学",
        "is_active": True,
        "priority": PlanPriority.HIGH,
    }
    defaults.update(overrides)
    plan = Plan(**defaults)
    db_session.add(plan)
    await db_session.flush()
    return plan


@pytest.mark.asyncio
async def test_confirm_plan_first_time_returns_200_with_confirmed_at(db_session, confirm_client):
    client, state = confirm_client
    user = await _make_user(db_session, "confirm_owner")
    plan = await _make_plan(db_session, user.id)
    await db_session.commit()
    state["current_user"] = user

    response = client.post(f"/plans/{plan.id}/confirm")

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan_id"] == str(plan.id)
    assert payload["plan_stage"] == PlanStage.SPRINT.value
    assert payload["confirmed_at"] is not None
    assert payload["already_confirmed"] is False
    assert payload["message"]

    await db_session.refresh(plan)
    assert plan.confirmed_at is not None


@pytest.mark.asyncio
async def test_confirm_plan_is_idempotent_keeps_first_timestamp(db_session, confirm_client):
    client, state = confirm_client
    user = await _make_user(db_session, "confirm_idempotent")
    plan = await _make_plan(db_session, user.id)
    await db_session.commit()
    state["current_user"] = user

    first = client.post(f"/plans/{plan.id}/confirm")
    assert first.status_code == 200
    first_confirmed_at = first.json()["confirmed_at"]

    second = client.post(f"/plans/{plan.id}/confirm")
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["already_confirmed"] is True
    assert second_payload["confirmed_at"] == first_confirmed_at

    await db_session.refresh(plan)
    assert plan.confirmed_at.isoformat() == first_confirmed_at


@pytest.mark.asyncio
async def test_confirm_plan_of_other_user_returns_404(db_session, confirm_client):
    client, state = confirm_client
    owner = await _make_user(db_session, "confirm_owner_b")
    intruder = await _make_user(db_session, "confirm_intruder")
    plan = await _make_plan(db_session, owner.id)
    await db_session.commit()
    state["current_user"] = intruder

    response = client.post(f"/plans/{plan.id}/confirm")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_confirm_missing_plan_returns_404(db_session, confirm_client):
    import uuid as uuid_mod

    client, state = confirm_client
    user = await _make_user(db_session, "confirm_missing")
    await db_session.commit()
    state["current_user"] = user

    response = client.post(f"/plans/{uuid_mod.uuid4()}/confirm")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_confirm_soft_deleted_plan_returns_404(db_session, confirm_client):
    client, state = confirm_client
    user = await _make_user(db_session, "confirm_softdel")
    plan = await _make_plan(db_session, user.id, deleted_at=None)
    await db_session.commit()
    # 软删（走 SoftDeleteMixin 语义：deleted_at 置值）
    plan.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db_session.add(plan)
    await db_session.commit()
    state["current_user"] = user

    response = client.post(f"/plans/{plan.id}/confirm")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_confirm_archived_but_not_deleted_plan_is_allowed(db_session, confirm_client):
    """行为定义：已归档（is_active=False）未软删的计划允许确认。

    确认记录的是用户意图（认可这份计划），不隐含恢复/激活——
    不改 is_active，不进归档/配额域（最小行为面）。
    """
    client, state = confirm_client
    user = await _make_user(db_session, "confirm_archived")
    plan = await _make_plan(db_session, user.id, is_active=False)
    await db_session.commit()
    state["current_user"] = user

    response = client.post(f"/plans/{plan.id}/confirm")

    assert response.status_code == 200
    payload = response.json()
    assert payload["confirmed_at"] is not None

    await db_session.refresh(plan)
    assert plan.confirmed_at is not None
    assert plan.is_active is False
