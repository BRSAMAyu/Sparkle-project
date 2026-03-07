from types import SimpleNamespace
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.orchestration.grounding_validator import GroundingValidator


@pytest.mark.asyncio
async def test_grounding_validator_warns_when_prerequisite_mastery_is_low(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.flush()

    node = KnowledgeNode(
        name="多变量微积分",
        description="偏导与多重积分基础",
    )
    db_session.add(node)
    await db_session.flush()

    task = Task(
        user_id=user_id,
        title="刷多元函数极值题",
        type=TaskType.LEARNING,
        estimated_minutes=45,
        difficulty=3,
        energy_cost=3,
    )
    db_session.add(task)
    await db_session.flush()

    db_session.add(
        TaskKnowledgeLink(
            task_id=task.id,
            knowledge_node_id=node.id,
            relation_type="prerequisite",
            is_primary=True,
        )
    )
    db_session.add(UserNodeStatus(user_id=user_id, node_id=node.id, mastery_score=20.0))
    await db_session.commit()

    validator = GroundingValidator(redis_client=None)
    validator._get_allowlist = AsyncMock(return_value={"update_task_status"})
    plan = SimpleNamespace(
        schema_version="4.0",
        tool_calls=[
            SimpleNamespace(
                name="update_task_status",
                params={"task_id": str(task.id), "status": "in_progress"},
                point_of_no_return=False,
            )
        ],
    )

    result = await validator.validate_plan(
        plan=plan,
        snapshot=None,
        db_session=db_session,
        user_id=str(user_id),
    )

    assert result.is_valid is True
    assert result.warnings
    assert result.warnings[0]["message"] == "建议先复习多变量微积分基础"
