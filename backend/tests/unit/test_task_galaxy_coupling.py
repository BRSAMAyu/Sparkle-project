"""Regression tests for daily-flow DF-5: galaxy zero coupling.

daily-flow-eval: three simulated days, four completed tasks, and the galaxy
stats stayed at unlocked=0 / mastered=0 / study_minutes=0 — everyday task
completion never touched the star map because the only galaxy hooks required a
pre-linked knowledge_node_id or sprint-pack guide_json, which self-created
tasks never have. TaskService.complete must now anchor unlinked tasks to the
galaxy (existing node match, else a stable task-derived node) and spark it.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.task import Task, TaskStatus, TaskType
from app.services.galaxy_service import GalaxyService
from app.services.task_service import TaskService


@pytest.fixture(autouse=True)
def _mute_event_bus(monkeypatch):
    """Keep Redis/DLQ noise out of these unit tests."""

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.task_service.event_bus_reliable.publish", _noop)
    monkeypatch.setattr("app.services.task_service.publish_srl_event", _noop)
    monkeypatch.setattr(
        "app.services.galaxy.stats_service.event_bus.publish", _noop, raising=False
    )


async def _mk_task(db_session, user_id, title: str) -> Task:
    task = Task(
        user_id=user_id,
        title=title,
        type=TaskType.TRAINING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=40,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.mark.asyncio
async def test_completing_unlinked_task_ignites_a_galaxy_star(db_session, test_user):
    task = await _mk_task(db_session, test_user.id, "复习动量守恒题型")

    await TaskService.complete(db_session, task, actual_minutes=40)

    node = (
        await db_session.execute(
            select(KnowledgeNode).where(KnowledgeNode.source_task_id == task.id)
        )
    ).scalar_one_or_none()
    assert node is not None, "completing an unlinked task must materialize a task-derived star"

    status_row = (
        await db_session.execute(
            select(UserNodeStatus).where(
                UserNodeStatus.user_id == test_user.id, UserNodeStatus.node_id == node.id
            )
        )
    ).scalar_one_or_none()
    assert status_row is not None
    assert status_row.is_unlocked is True
    assert status_row.total_study_minutes >= 40

    record = (
        await db_session.execute(
            select(StudyRecord).where(
                StudyRecord.user_id == test_user.id, StudyRecord.task_id == task.id
            )
        )
    ).scalar_one_or_none()
    assert record is not None, "study activity must be recorded on the star"


@pytest.mark.asyncio
async def test_same_topic_tasks_share_one_star(db_session, test_user):
    """Deterministic anchor: re-studying the same topic must accumulate mastery
    on one star instead of spawning duplicate nodes."""
    task1 = await _mk_task(db_session, test_user.id, "复习动量守恒题型")
    task2 = await _mk_task(db_session, test_user.id, "复习 动量守恒题型 ")  # same topic, whitespace noise

    await TaskService.complete(db_session, task1, actual_minutes=30)
    await TaskService.complete(db_session, task2, actual_minutes=20)

    node = (
        await db_session.execute(
            select(KnowledgeNode).where(KnowledgeNode.source_task_id == task1.id)
        )
    ).scalar_one_or_none()
    assert node is not None

    status_row = await db_session.get(UserNodeStatus, (test_user.id, node.id))
    assert status_row is not None
    assert status_row.study_count >= 2, "same-topic completions must accumulate on the same star"

    node_count = len(
        (
            await db_session.execute(
                select(KnowledgeNode.id).where(KnowledgeNode.name.ilike("%动量守恒%"))
            )
        ).scalars().all()
    )
    assert node_count == 1, "normalized same-title tasks must not duplicate stars"


@pytest.mark.asyncio
async def test_exact_title_match_sparks_existing_seed_node(db_session, test_user):
    """Completing a task whose title equals an existing node must light THAT
    star instead of creating a duplicate."""
    seed = KnowledgeNode(name="TCP 拥塞控制", description="seed", importance_level=4)
    db_session.add(seed)
    await db_session.commit()
    await db_session.refresh(seed)

    task = await _mk_task(db_session, test_user.id, "TCP 拥塞控制")
    await TaskService.complete(db_session, task, actual_minutes=25)

    status_row = await db_session.get(UserNodeStatus, (test_user.id, seed.id))
    assert status_row is not None, "exact-title tasks must spark the existing node"
    assert status_row.is_unlocked is True
    assert status_row.total_study_minutes >= 25

    dup_count = len(
        (
            await db_session.execute(
                select(KnowledgeNode.id).where(KnowledgeNode.name == "TCP 拥塞控制")
            )
        ).scalars().all()
    )
    assert dup_count == 1


def test_task_node_uuid_is_deterministic():
    a = GalaxyService.task_node_uuid("复习 动量守恒题型")
    b = GalaxyService.task_node_uuid("复习动量守恒题型")
    assert a == b, "whitespace-normalized titles must map to the same star"
