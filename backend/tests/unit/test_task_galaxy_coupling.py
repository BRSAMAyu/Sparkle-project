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


# ---------------------------------------------------------------------------
# F-2 内部命名泄漏（v3-output/WT324-SIMEVIDENCE/REPORT.md §四）：评测 harness
# 把全局唯一 token 拼进任务标题（feature_tour S7），DF-5 seed 链路曾把它原样
# 拷进用户可见节点名/描述/关键词。生成侧必须产出干净人类可读名，token 只留在
# id / source_task_id 等非展示字段。
# ---------------------------------------------------------------------------

TOUR_TITLE = "TOUR 专题7-d91d5df0-10-5dc70d: 真题演练与错因回看"


@pytest.mark.asyncio
async def test_tokened_task_title_seeds_clean_node_naming(db_session, test_user):
    task = await _mk_task(db_session, test_user.id, TOUR_TITLE)

    await TaskService.complete(db_session, task, actual_minutes=40)

    node = (
        await db_session.execute(
            select(KnowledgeNode).where(KnowledgeNode.source_task_id == task.id)
        )
    ).scalar_one_or_none()
    assert node is not None, "tokened task must still ignite a star"
    assert node.name == "真题演练与错因回看", "node name must drop the internal token"
    assert node.description == "来自任务的学习主题：真题演练与错因回看"
    assert node.keywords == ["真题演练与错因回看"]
    # 内部标识只留在非展示字段
    assert str(node.id) != TOUR_TITLE
    assert node.source_task_id == task.id


@pytest.mark.asyncio
async def test_same_semantic_tail_tokened_titles_share_one_star(db_session, test_user):
    """同一语义尾、不同 harness token 的任务必须收敛到同一颗星（零改写映射对
    干净标题不变；tokened 标题按清洗后的语义名建星）。"""
    task1 = await _mk_task(db_session, test_user.id, "TOUR 专题1-d91d5df0-1-aaaaaa: 真题演练与错因回看")
    task2 = await _mk_task(db_session, test_user.id, "TOUR 专题2-d91d5df0-2-bbbbbb: 真题演练与错因回看")

    await TaskService.complete(db_session, task1, actual_minutes=30)
    await TaskService.complete(db_session, task2, actual_minutes=20)

    names = (
        await db_session.execute(
            select(KnowledgeNode.name).where(KnowledgeNode.name == "真题演练与错因回看")
        )
    ).scalars().all()
    assert len(names) == 1, "same semantic tail must collapse onto one clean-named star"

    node = (
        await db_session.execute(
            select(KnowledgeNode).where(KnowledgeNode.name == "真题演练与错因回看")
        )
    ).scalar_one()
    status_row = await db_session.get(UserNodeStatus, (test_user.id, node.id))
    assert status_row is not None
    assert status_row.study_count >= 2, "both tokened completions must accumulate on the same star"


@pytest.mark.asyncio
async def test_tokened_task_title_sparks_existing_same_name_seed(db_session, test_user):
    """清洗后的语义名与既有节点同名时，必须点亮那颗既有星而不是复制新星。"""
    seed = KnowledgeNode(name="真题演练与错因回看", description="seed", importance_level=3)
    db_session.add(seed)
    await db_session.commit()
    await db_session.refresh(seed)

    task = await _mk_task(db_session, test_user.id, TOUR_TITLE)
    await TaskService.complete(db_session, task, actual_minutes=25)

    status_row = await db_session.get(UserNodeStatus, (test_user.id, seed.id))
    assert status_row is not None, "sanitized-title match must light the existing star"
    assert status_row.is_unlocked is True


def test_task_node_uuid_keys_on_sanitized_title():
    a = GalaxyService.task_node_uuid(TOUR_TITLE)
    b = GalaxyService.task_node_uuid("真题演练与错因回看")
    assert a == b, "tokened title and its semantic tail must map to the same star"


def test_task_node_uuid_clean_title_mapping_unchanged():
    """零改写纪律：干净标题的确定性映射与旧口径完全一致（whitespace 不敏感）。"""
    import uuid as _uuid

    from app.services.galaxy_service import TASK_NODE_UUID_NAMESPACE

    legacy = _uuid.uuid5(TASK_NODE_UUID_NAMESPACE, "复习动量守恒题型")
    assert GalaxyService.task_node_uuid("复习 动量守恒题型") == legacy
    assert GalaxyService.task_node_uuid("复习动量守恒题型") == legacy
