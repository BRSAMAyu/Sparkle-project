from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.galaxy import KnowledgeNode
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.galaxy_service import GalaxyService
from app.services.task_service import TaskService


@pytest.mark.asyncio
async def test_sprint_mastery_update_upserts_external_node(db_session) -> None:
    user = User(
        username=f"sprint_{uuid4().hex[:8]}",
        email=f"sprint_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = GalaxyService(db_session)
    result = await service.update_node_mastery(
        user_id=user.id,
        node_id="cn.tcp_flow",
        new_mastery=0.5,
        reason="sprint_task_completed",
    )

    summary = await service.get_sprint_mastery_summary(user.id, ["cn.tcp_flow"])
    node = await db_session.get(KnowledgeNode, GalaxyService.sprint_node_uuid("cn.tcp_flow_control"))

    assert result["success"] is True
    assert summary["cn.tcp_flow"] == pytest.approx(0.5)
    assert node is not None
    assert node.source_type == "sprint_pack"


@pytest.mark.asyncio
async def test_task_completion_increments_sprint_pack_node_mastery(db_session, monkeypatch) -> None:
    user = User(
        username=f"sprint_task_{uuid4().hex[:8]}",
        email=f"sprint_task_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        title="Day 1 · TCP 流量控制",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        tags=["exam_sprint"],
        estimated_minutes=30,
        difficulty=2,
        energy_cost=2,
        guide_json={
            "sprint_mode": "seven_day_survival",
            "sprint_pack_nodes": [
                {"node_id": "cn.tcp_flow_control", "label": "TCP 流量控制"},
            ],
            "knowledge_node_ids": ["cn.tcp_flow_control"],
        },
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.task_service.event_bus_reliable.publish", _noop)
    monkeypatch.setattr("app.services.task_service.publish_srl_event", _noop)

    await TaskService.complete(db_session, task, actual_minutes=25)

    summary = await GalaxyService(db_session).get_sprint_mastery_summary(
        user.id,
        ["cn.tcp_flow_control"],
    )
    completed_task = (
        await db_session.execute(select(Task).where(Task.id == task.id))
    ).scalar_one()

    assert completed_task.status == TaskStatus.COMPLETED
    assert summary["cn.tcp_flow_control"] == pytest.approx(0.25)
