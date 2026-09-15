from types import SimpleNamespace
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.services.community_service import GroupTaskService


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _ExecResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _ScalarResult(self._values)


class _Task(SimpleNamespace):
    @property
    def claims(self):
        raise AssertionError("get_group_tasks should not access lazy task.claims")


@pytest.mark.asyncio
async def test_get_group_tasks_uses_batched_claim_lookup():
    group_id = uuid4()
    user_id = uuid4()

    task1 = _Task(
        id=uuid4(),
        title="task-1",
        description="d1",
        tags=["x"],
        estimated_minutes=30,
        difficulty=2,
        total_claims=1,
        total_completions=1,
        due_date=None,
        created_at=None,
        updated_at=None,
        creator=SimpleNamespace(id=uuid4()),
    )
    task2 = _Task(
        id=uuid4(),
        title="task-2",
        description="d2",
        tags=["y"],
        estimated_minutes=40,
        difficulty=3,
        total_claims=0,
        total_completions=0,
        due_date=None,
        created_at=None,
        updated_at=None,
        creator=SimpleNamespace(id=uuid4()),
    )

    claim = SimpleNamespace(group_task_id=task1.id, is_completed=True)

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ExecResult([task1, task2]),
            _ExecResult([claim]),
        ]
    )

    tasks = await GroupTaskService.get_group_tasks(db, group_id, user_id)

    assert len(tasks) == 2
    assert tasks[0]["is_claimed_by_me"] is True
    assert tasks[0]["my_completion_status"] is True
    assert tasks[1]["is_claimed_by_me"] is False
    assert tasks[1]["my_completion_status"] is None
    assert db.execute.await_count == 2
