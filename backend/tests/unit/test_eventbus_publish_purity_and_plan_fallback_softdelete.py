"""R2-F（H8+S1）红绿测：event_bus.publish 纯度 + plan_service 兜底软删过滤。

H8（修前 backend/app/core/event_bus.py:1081-1082）：
``publish`` 直接就地改写调用方字典（``payload["schema_version"] = "1.0"``）——
同一 payload 连发两个 stream 时，第二次起调用方 dict 已被污染，观察者可感知
schema_version 键（副作用泄漏进调用方数据）。
修复：``message = {"schema_version": "1.0", **payload}`` 构造新 dict，后续一律用
``message``——调用方 dict 恒不被改写；payload 自带 schema_version 时仍以调用方
为准（与修前 ``if "schema_version" not in payload`` 语义一致），wire 格式不变
（注入默认值仍为 "1.0"）。

S1（修前 backend/app/services/plan_service.py:215-219）：
``update_progress`` 兜底两查询（total/completed）不过滤 ``deleted_at``——软删
任务计入分子分母，软删后进度被抬高。
修复：两查询补 ``Task.deleted_at.is_(None)``。
（触达路径：无 card_protocol 计划卡时 ``sync_legacy_plan_progress`` 返回 None，
自然落入兜底计数，无需 monkeypatch。）
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.plan_service import PlanService


# ── H8：publish 不改写调用方 payload ────────────────────────────────────────
async def test_publish_does_not_mutate_caller_payload():
    bus = EventBus()
    captured: list[dict] = []

    async def fake_publish_once(event_type: str, payload: dict, stream: str) -> str:
        captured.append(dict(payload))
        return "0-1"

    bus._publish_once = fake_publish_once  # type: ignore[method-assign]

    payload = {"event_type": "progress_updated", "user_id": "u-1"}
    await bus.publish("progress_updated", payload, stream="stream_a")
    await bus.publish("progress_updated", payload, stream="stream_b")

    assert "schema_version" not in payload, (
        f"publish 不得改写调用方 dict（H8 修前第一次 publish 就地注入 schema_version）：{sorted(payload)}"
    )
    # wire 格式不变（Forbidden）：注入默认值仍为 "1.0"，两次发出的消息都带
    assert all(message.get("schema_version") == "1.0" for message in captured), captured
    assert len(captured) == 2


async def test_publish_preserves_caller_supplied_schema_version():
    """调用方自带 schema_version 时保持调用方值（与修前 not-in 语义一致，非本次注入覆盖）。"""
    bus = EventBus()
    captured: list[dict] = []

    async def fake_publish_once(event_type: str, payload: dict, stream: str) -> str:
        captured.append(dict(payload))
        return "0-1"

    bus._publish_once = fake_publish_once  # type: ignore[method-assign]

    payload = {"event_type": "x", "schema_version": "0.9"}
    await bus.publish("x", payload)

    assert payload == {"event_type": "x", "schema_version": "0.9"}
    assert captured[0]["schema_version"] == "0.9"


# ── S1：plan 兜底进度不计软删任务 ──────────────────────────────────────────
async def test_update_progress_fallback_excludes_soft_deleted(db_session: AsyncSession):
    user = User(username=f"wt368-{uuid4().hex[:8]}", email=f"wt368-{uuid4().hex[:8]}@test.local", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        id=uuid4(),
        user_id=user.id,
        name="wt368 兜底软删",
        type=PlanType.SPRINT,
        subject="数学",
        progress=0.0,
        target_date=datetime.utcnow() + timedelta(days=7),
        is_active=True,
    )
    db_session.add(plan)
    await db_session.flush()

    now = datetime.utcnow()
    tasks = [
        # 活跃已完成 → 分子 1
        Task(user_id=user.id, plan_id=plan.id, title="done", type="LEARNING", estimated_minutes=10,
             status=TaskStatus.COMPLETED, completed_at=now),
        # 活跃待办 → 分母 2
        Task(user_id=user.id, plan_id=plan.id, title="pending", type="LEARNING", estimated_minutes=10,
             status=TaskStatus.PENDING),
        # 软删已完成 → 修前计入分子分母（2/3≈0.667），修复后不可见
        Task(user_id=user.id, plan_id=plan.id, title="soft-deleted done", type="LEARNING", estimated_minutes=10,
             status=TaskStatus.COMPLETED, completed_at=now, deleted_at=now),
    ]
    for task in tasks:
        db_session.add(task)
    await db_session.commit()

    result = await PlanService.update_progress(db_session, plan.id, user.id)

    assert result is not None
    assert result == 0.5, f"兜底口径应为 1/2=0.5（软删完成不计），修前 2/3≈0.667：{result}"
    await db_session.refresh(plan)
    assert plan.progress == 0.5
