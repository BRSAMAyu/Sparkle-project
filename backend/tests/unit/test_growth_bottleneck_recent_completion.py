"""F-5（wt324 实测 major）：瓶颈误报——刚完成的任务不得立即成为 bottleneck 信号。

缺陷链（v3-output/WT324-SIMEVIDENCE/REPORT.md §四 F-5；wt306 风险4 预警成真）：
用户完成任务「Readiness check」后，growth dashboard 的 ``_get_weakest_area``
只按 ``UserNodeStatus.mastery_score`` 升序取最低知识节点——该任务关联节点
掌握度仍低即被指认为 weakest area → ``_build_active_bottleneck`` 立即把它
命名为 active_bottleneck（topic=任务同名节点），mobile cockpit 据此转
stalled，掩盖刚产出的 active 完成态。

修法（时间窗判定，与现有推导一致性理由见 REPORT）：
排除「窗口期内有关联任务完成」的知识节点；窗口取
``BOTTLENECK_RECENT_COMPLETION_WINDOW_HOURS``（默认 24h）。
全部节点都被窗口覆盖时返回 None（诚实空态优于指认一个刚被处理过的节点）。
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.growth_dashboard_service import GrowthDashboardService


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    row = User(username="f5_user", email="f5_user@example.com", hashed_password="hashed")
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_node(
    db_session: AsyncSession,
    *,
    name: str,
    user_id,
    mastery: float,
) -> KnowledgeNode:
    node = KnowledgeNode(name=name)
    db_session.add(node)
    await db_session.flush()
    db_session.add(UserNodeStatus(user_id=user_id, node_id=node.id, mastery_score=mastery))
    await db_session.flush()
    return node


async def _add_completed_task(
    db_session: AsyncSession,
    *,
    user_id,
    node: KnowledgeNode,
    title: str,
    completed_at_offset: timedelta,
) -> Task:
    from app.services.growth_dashboard_service import _utcnow

    task = Task(
        user_id=user_id,
        title=title,
        type=TaskType.LEARNING,
        estimated_minutes=25,
        knowledge_node_id=node.id,
        status=TaskStatus.COMPLETED,
        completed_at=_utcnow() + completed_at_offset,
    )
    db_session.add(task)
    await db_session.commit()
    return task


@pytest.mark.asyncio
async def test_just_completed_task_node_is_not_bottleneck(db_session, user):
    """红测主断言：完成任务后，其关联节点不得立即成为 active_bottleneck。"""
    just_done = await _add_node(db_session, name="Readiness check", user_id=user.id, mastery=5.0)
    await _add_node(db_session, name="线性代数", user_id=user.id, mastery=40.0)
    await _add_completed_task(
        db_session,
        user_id=user.id,
        node=just_done,
        title="Readiness check",
        completed_at_offset=timedelta(minutes=-5),
    )

    service = GrowthDashboardService(db_session)
    weakest = await service._get_weakest_area(user.id)
    bottleneck = service._build_active_bottleneck(weakest)

    assert weakest != "Readiness check", "刚完成任务的同名节点不得立即成为瓶颈信号"
    assert bottleneck is not None and bottleneck["topic"] != "Readiness check"
    assert bottleneck["topic"] == "线性代数"


@pytest.mark.asyncio
async def test_node_without_recent_completion_still_surfaceable(db_session, user):
    """未在窗口内完成的低掌握节点照常指认（不因本修失去瓶颈发现能力）。"""
    await _add_node(db_session, name="概率论", user_id=user.id, mastery=8.0)
    strong = await _add_node(db_session, name="英语听力", user_id=user.id, mastery=90.0)

    service = GrowthDashboardService(db_session)
    weakest = await service._get_weakest_area(user.id)

    assert weakest == "概率论"
    assert strong.name != weakest


@pytest.mark.asyncio
async def test_completion_outside_window_requalifies_as_bottleneck(db_session, user):
    """窗口外的完成任务不掩盖节点：完成两天后仍是最低掌握 → 可再指认。"""
    stale = await _add_node(db_session, name="古代汉语", user_id=user.id, mastery=3.0)
    other = await _add_node(db_session, name="现代文学", user_id=user.id, mastery=60.0)
    await _add_completed_task(
        db_session,
        user_id=user.id,
        node=stale,
        title="古代汉语任务",
        completed_at_offset=timedelta(days=-2),
    )

    service = GrowthDashboardService(db_session)
    weakest = await service._get_weakest_area(user.id)

    assert weakest == "古代汉语"
    assert other.name != weakest


@pytest.mark.asyncio
async def test_all_nodes_recently_completed_yields_honest_none(db_session, user):
    """全部节点都在窗口内被处理 → 诚实空态（None），不硬指认刚处理过的节点。"""
    only = await _add_node(db_session, name="Readiness check", user_id=user.id, mastery=5.0)
    await _add_completed_task(
        db_session,
        user_id=user.id,
        node=only,
        title="Readiness check",
        completed_at_offset=timedelta(minutes=-30),
    )

    service = GrowthDashboardService(db_session)
    weakest = await service._get_weakest_area(user.id)

    assert weakest is None
    assert service._build_active_bottleneck(weakest) is None


@pytest.mark.asyncio
async def test_pending_task_does_not_suppress_its_node(db_session, user):
    """排除面只针对 completed：pending/进行中任务的节点仍可被指认为瓶颈。"""
    pending_node = await _add_node(db_session, name="机器学习基础", user_id=user.id, mastery=6.0)
    healthy = await _add_node(db_session, name="数据结构", user_id=user.id, mastery=70.0)

    from app.services.growth_dashboard_service import _utcnow

    db_session.add(
        Task(
            user_id=user.id,
            title="机器学习基础任务",
            type=TaskType.LEARNING,
            estimated_minutes=25,
            knowledge_node_id=pending_node.id,
            status=TaskStatus.IN_PROGRESS,
            completed_at=None,
            started_at=_utcnow(),
        )
    )
    await db_session.commit()

    service = GrowthDashboardService(db_session)
    weakest = await service._get_weakest_area(user.id)

    assert weakest == "机器学习基础"
    assert healthy.name != weakest
