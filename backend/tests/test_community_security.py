"""
社群安全模块测试
Tests for community security fixes
"""
import asyncio
import pytest
from datetime import datetime,from uuid import uuid4from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession


class TestCommunitySecurity:
    """社群安全模块测试类"""

    @pytest.fixture
    def mock_db():
        """创建模拟数据库会话"""
        db = AsyncMock(spec=AsyncSession)
        return db

    # ============ 数据一致性测试 ============

    @pytest.mark.asyncio
    async def test_group_task_complete_transaction(self, mock_db):
        """测试群任务完成的数据库一致性"""
        from app.services.community_service import GroupTaskService
        from app.models.community import GroupTask, GroupTaskClaim, GroupMember, Group
        from app.models.user import User

        # 模拟数据
        mock_claim = AsyncMock(spec=GroupTaskClaim)
        mock_claim.id = uuid4()
        mock_claim.group_task_id = uuid4()
        mock_claim.user_id = uuid4()
        mock_claim.is_completed = False

        mock_group_task = AsyncMock(spec=GroupTask)
        mock_group_task.id = mock_claim.group_task_id
        mock_group_task.group_id = uuid4()
        mock_group_task.total_completions = 5

        mock_member = AsyncMock(spec=GroupMember)
        mock_member.tasks_completed = 10
        mock_member.group_id = mock_group_task.group_id

        mock_group = AsyncMock(spec=Group)
        mock_group.id = mock_group_task.group_id
        mock_group.total_tasks_completed = 100

        # 模拟数据库查询
        mock_db.execute.return_value = mock_claim
        mock_db.execute.return_value = mock_group_task
        mock_db.execute.return_value = mock_member
        mock_db.execute.return_value = mock_group

        # 执行完成
        result = await GroupTaskService.complete_task(mock_db, mock_claim.id)

        assert result is not None
        assert mock_claim.is_completed is True
        assert mock_claim.completed_at is not None
        assert mock_group_task.total_completions == 6
        assert mock_member.tasks_completed == 11
        assert mock_group.total_tasks_completed == 101

    # ============ 拉黑机制测试 ============

    @pytest.mark.asyncio
    async def test_block_user(self, mock_db):
        """测试拉黑用户功能"""
        from app.services.community_service import UserBlockService
        from app.models.community import UserBlock, Friendship, FriendshipStatus

        from app.models.user import User

        blocker_id = uuid4()
        blocked_id = uuid4()

        # 模拟数据库查询 - 没有现有拉黑记录
        mock_db.execute.return_value = None
        # 模拟数据库查询 - 没有好友关系
        mock_db.execute.return_value = None
        # 模拟添加
        mock_db.add.return_value = None
        mock_db.flush.return_value = None
        mock_db.refresh.return_value = None

        block = await UserBlockService.block_user(
            db=mock_db,
            blocker_id=blocker_id,
            blocked_id=blocked_id,
            reason="测试拉黑"
        )

        assert block is not None
        assert block.blocker_id == blocker_id
        assert block.blocked_id == blocked_id

    @pytest.mark.asyncio
    async def test_block_user_twice(self, mock_db):
        """测试重复拉黑"""
        from app.services.community_service import UserBlockService

        from app.models.community import UserBlock

        blocker_id = uuid4()
        blocked_id = uuid4()

        # 模拟现有拉黑记录
        existing_block = AsyncMock(spec=UserBlock)
        existing_block.blocker_id = blocker_id
        existing_block.blocked_id = blocked_id
        existing_block.deleted_at = None

        mock_db.execute.return_value = existing_block

        with pytest.raises(ValueError, match="已拉黑该用户"):
            await UserBlockService.block_user(
                db=mock_db,
                blocker_id=blocker_id,
                blocked_id=blocked_id
            )

    @pytest.mark.asyncio
    async def test_unblock_user(self, mock_db):
        """测试解除拉黑"""
        from app.services.community_service import UserBlockService
        from app.models.community import UserBlock

        from app.models.user import User

        blocker_id = uuid4()
        blocked_id = uuid4()

        # 模拟现有拉黑记录
        existing_block = AsyncMock(spec=UserBlock)
        existing_block.blocker_id = blocker_id
        existing_block.blocked_id = blocked_id
        existing_block.deleted_at = None

        mock_db.execute.return_value = existing_block

        result = await UserBlockService.unblock_user(
            db=mock_db,
            blocker_id=blocker_id,
            blocked_id=blocked_id
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_is_blocked(self, mock_db):
        """测试检查拉黑状态"""
        from app.services.community_service import UserBlockService
        from app.models.community import UserBlock

        from app.models.user import User

        blocker_id = uuid4()
        blocked_id = uuid4()

        # 模拟拉黑记录存在
        existing_block = AsyncMock(spec=UserBlock)
        mock_db.execute.return_value = existing_block

        assert await UserBlockService.is_blocked(mock_db, blocked_id, blocker_id) is True

        # 模拟拉黑记录不存在
        mock_db.execute.return_value = None
        assert await UserBlockService.is_blocked(mock_db, blocked_id, blocker_id) is False

