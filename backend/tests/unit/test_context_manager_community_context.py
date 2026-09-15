from uuid import uuid4

import pytest

from app.core.context_manager import ContextOrchestrator
from app.models.community import Group, GroupMember, GroupTask, GroupTaskClaim, GroupType
from app.models.user import User


@pytest.mark.asyncio
async def test_context_orchestrator_builds_lightweight_community_context(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)

    sprint_group = Group(
        name="高数突击",
        type=GroupType.SPRINT,
        is_public=True,
    )
    db_session.add(sprint_group)
    await db_session.flush()

    member = GroupMember(group_id=sprint_group.id, user_id=user_id)
    group_task = GroupTask(
        group_id=sprint_group.id,
        created_by=user_id,
        title="复习多变量微积分",
        estimated_minutes=30,
        difficulty=3,
    )
    db_session.add_all([member, group_task])
    await db_session.flush()

    db_session.add(
        GroupTaskClaim(
            group_task_id=group_task.id,
            user_id=user_id,
            is_completed=False,
        )
    )
    await db_session.commit()

    orchestrator = ContextOrchestrator(db_session, redis_client=None)
    profile = await orchestrator._get_community_profile(user_id)

    assert profile["active_group_count"] == 1
    assert profile["active_group_types"]["sprint"] == 1
    assert profile["has_pending_group_tasks"] is True
    assert "高数突击" in profile["sprint_progress"][0]
