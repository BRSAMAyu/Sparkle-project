"""J-07 · 陈旧建议不复用（缓存穿透负测，SHIELD-INVAL）。

comeback-context 走进程内 TTL 缓存（恢复风暴防护，8s）。deadline 变化
（wt313 replan / 计划编辑重锚）写路径必须宣告读面失效——否则回来的人在
TTL 窗口内拿到的是重锚前的陈旧建议（"窗口已经结束"），即缓存穿透。

复用纪律：replan 执行面 = wt313 ``POST /plans/{id}/replan`` 原端点；
失效面 = 既有 ``EndpointShield.invalidate_prefix`` / SHIELD-INVAL 注册表
（galaxy_graph 同款），不建第二套缓存或失效机制。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.api.v1.aurora import router as aurora_router
from app.api.v1.plans import router as plans_router
from app.models.chat import ChatMessage, MessageRole
from app.models.plan import Plan, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User


@pytest.fixture
def comeback_app(db_session):
    app = FastAPI()
    app.include_router(aurora_router)
    app.include_router(plans_router, prefix="/plans")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    return app, state


async def _seed_expired_plan_user(db_session) -> tuple[User, Plan]:
    now = datetime.now(UTC).replace(tzinfo=None)
    user = User(
        id=uuid4(),
        username=f"j07_inval_{uuid4().hex[:8]}",
        email=f"j07_inval_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    plan = Plan(
        name="7天计算机网络冲刺",
        user_id=user.id,
        type=PlanType.SPRINT,
        subject="计算机网络",
        target_date=(now - timedelta(days=5)).date(),
        plan_stage=PlanStage.SPRINT,
        is_active=True,
        is_primary=True,
    )
    db_session.add_all([user, plan])
    await db_session.flush()
    db_session.add(
        ChatMessage(
            user_id=user.id,
            role=MessageRole.USER,
            content="四天前还在学。",
            created_at=now - timedelta(days=4),
        )
    )
    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="Day 4 · TCP 流量控制",
            type=TaskType.LEARNING,
            estimated_minutes=45,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.PENDING,
            order_index=1,
        )
    )
    await db_session.commit()
    return user, plan


@pytest.mark.asyncio
async def test_replan_invalidates_comeback_cache_stale_suggestion_not_reused(db_session, comeback_app):
    """负测：replan 重锚后（TTL 窗口内再查），comeback 建议必须重估而非复用陈旧缓存。"""
    app, state = comeback_app
    user, plan = await _seed_expired_plan_user(db_session)
    state["current_user"] = user

    with TestClient(app) as client:
        first = client.get(f"/aurora/comeback-context?user_id={user.id}")
        assert first.status_code == 200
        stale = first.json()
        # 第一次查询命中过期窗口真源：陈旧建议被诚实标注（TTL 缓存同时被预热）。
        assert stale["plan_expired"] is True
        assert "已经结束" in stale["message"]
        assert stale["rescope"]["recommended"] is True

        replanned = client.post(f"/plans/{plan.id}/replan")
        assert replanned.status_code == 200
        assert replanned.json()["replanned"] is True

        # 关键负测：仍在 8s TTL 窗口内第二次查询——必须拿到重估后的新建议，
        # 不允许穿透回重锚前的陈旧缓存。
        second = client.get(f"/aurora/comeback-context?user_id={user.id}")
        assert second.status_code == 200
        fresh = second.json()
        assert fresh["plan_expired"] is False
        assert "已经结束" not in fresh["message"]
        assert fresh["rescope"]["recommended"] is False
        # rationale 有真实变化依据：离开期间终点被重锚（deadline_changed 源）。
        assert "deadline_changed" in fresh["rationale"]["sources"]

    # 真源复核：target_date 已重锚到未来。
    row = await db_session.execute(select(Plan).where(Plan.id == plan.id))
    persisted = row.scalar_one()
    assert persisted.target_date > datetime.now(UTC).date()
