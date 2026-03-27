"""
社群安全模块测试
Tests for community security fixes.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _AsyncNullContext:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def mock_db():
    """创建模拟数据库会话。"""
    db = AsyncMock(spec=AsyncSession)
    db.begin_nested.return_value = _AsyncNullContext()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


class TestCommunitySecurity:
    """社群安全模块测试类。"""

    @pytest.mark.asyncio
    async def test_group_task_complete_transaction(self, mock_db):
        """完成群任务时应同步更新 claim、任务、成员与群组统计。"""
        from app.services.community_service import GroupTaskService

        claim_id = uuid4()
        group_id = uuid4()
        user_id = uuid4()

        claim = SimpleNamespace(
            id=claim_id,
            group_task_id=uuid4(),
            user_id=user_id,
            is_completed=False,
            completed_at=None,
        )
        group_task = SimpleNamespace(
            id=claim.group_task_id,
            group_id=group_id,
            total_completions=5,
        )
        member = SimpleNamespace(
            group_id=group_id,
            user_id=user_id,
            tasks_completed=10,
        )
        group = SimpleNamespace(
            id=group_id,
            total_tasks_completed=100,
        )

        mock_db.execute.side_effect = [
            _ScalarResult(claim),
            _ScalarResult(group_task),
            _ScalarResult(member),
            _ScalarResult(group),
        ]

        result = await GroupTaskService.complete_task(mock_db, claim_id)

        assert result is claim
        assert claim.is_completed is True
        assert claim.completed_at is not None
        assert group_task.total_completions == 6
        assert member.tasks_completed == 11
        assert group.total_tasks_completed == 101
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_group_task_complete_missing_group_raises(self, mock_db):
        """若群组记录缺失，应抛出异常而不是写入半状态。"""
        from app.services.community_service import GroupTaskService

        claim = SimpleNamespace(
            id=uuid4(),
            group_task_id=uuid4(),
            user_id=uuid4(),
            is_completed=False,
            completed_at=None,
        )
        group_task = SimpleNamespace(
            id=claim.group_task_id,
            group_id=uuid4(),
            total_completions=1,
        )

        mock_db.execute.side_effect = [
            _ScalarResult(claim),
            _ScalarResult(group_task),
            _ScalarResult(None),
            _ScalarResult(None),
        ]

        with pytest.raises(ValueError, match="群组不存在"):
            await GroupTaskService.complete_task(mock_db, claim.id)

    @pytest.mark.asyncio
    async def test_block_user_creates_block_and_soft_deletes_friendship(self, mock_db):
        """拉黑用户时应创建拉黑记录，并自动软删除已有好友关系。"""
        from app.services.community_service import UserBlockService

        blocker_id = uuid4()
        blocked_id = uuid4()
        friendship = SimpleNamespace(soft_delete=MagicMock())

        existing_block_result = _ScalarResult(None)
        friendship_result = _ScalarResult(friendship)

        async def refresh_side_effect(obj):
            if getattr(obj, "blocker_id", None) is None:
                obj.blocker_id = blocker_id
            if getattr(obj, "blocked_id", None) is None:
                obj.blocked_id = blocked_id

        mock_db.execute.side_effect = [existing_block_result, friendship_result]
        mock_db.refresh.side_effect = refresh_side_effect

        block = await UserBlockService.block_user(
            db=mock_db,
            blocker_id=blocker_id,
            blocked_id=blocked_id,
            reason="测试拉黑",
        )

        assert block.blocker_id == blocker_id
        assert block.blocked_id == blocked_id
        assert block.reason == "测试拉黑"
        friendship.soft_delete.assert_called_once()
        assert mock_db.flush.await_count == 2

    @pytest.mark.asyncio
    async def test_block_user_twice_raises(self, mock_db):
        """重复拉黑同一用户应返回明确错误。"""
        from app.services.community_service import UserBlockService

        blocker_id = uuid4()
        blocked_id = uuid4()
        existing_block = SimpleNamespace(
            blocker_id=blocker_id,
            blocked_id=blocked_id,
            deleted_at=None,
        )
        mock_db.execute.side_effect = [_ScalarResult(existing_block)]

        with pytest.raises(ValueError, match="已拉黑该用户"):
            await UserBlockService.block_user(
                db=mock_db,
                blocker_id=blocker_id,
                blocked_id=blocked_id,
            )

    @pytest.mark.asyncio
    async def test_block_user_restores_soft_deleted_block(self, mock_db):
        """软删除后的拉黑记录再次拉黑时应恢复而不是重复创建。"""
        from app.services.community_service import UserBlockService

        blocker_id = uuid4()
        blocked_id = uuid4()
        existing_block = SimpleNamespace(
            blocker_id=blocker_id,
            blocked_id=blocked_id,
            deleted_at=object(),
            reason=None,
        )

        mock_db.execute.side_effect = [_ScalarResult(existing_block), _ScalarResult(None)]

        block = await UserBlockService.block_user(
            db=mock_db,
            blocker_id=blocker_id,
            blocked_id=blocked_id,
            reason="重新拉黑",
        )

        assert block is existing_block
        assert existing_block.deleted_at is None
        assert existing_block.reason == "重新拉黑"

    @pytest.mark.asyncio
    async def test_unblock_user_soft_deletes_record(self, mock_db):
        """解除拉黑应对记录做软删除。"""
        from app.services.community_service import UserBlockService

        blocker_id = uuid4()
        blocked_id = uuid4()
        existing_block = SimpleNamespace(soft_delete=MagicMock())
        mock_db.execute.side_effect = [_ScalarResult(existing_block)]

        result = await UserBlockService.unblock_user(
            db=mock_db,
            blocker_id=blocker_id,
            blocked_id=blocked_id,
        )

        assert result is True
        existing_block.soft_delete.assert_called_once()
        mock_db.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_is_blocked_checks_reverse_relationship(self, mock_db):
        """is_blocked 应检查 target 是否拉黑了当前 user。"""
        from app.services.community_service import UserBlockService

        blocked_user_id = uuid4()
        blocker_id = uuid4()

        mock_db.execute.side_effect = [_ScalarResult(object()), _ScalarResult(None)]

        assert await UserBlockService.is_blocked(mock_db, blocked_user_id, blocker_id) is True
        assert await UserBlockService.is_blocked(mock_db, blocked_user_id, blocker_id) is False
