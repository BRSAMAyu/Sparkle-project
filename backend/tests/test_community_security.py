"""
社群安全模块测试
Tests for community security fixes.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        if self._value is None:
            return []
        if isinstance(self._value, list):
            return self._value
        return [self._value]


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
        partnership = SimpleNamespace(status="active", ended_at=None)

        existing_block_result = _ScalarResult(None)
        friendship_result = _ScalarResult(friendship)
        partnership_result = _ScalarResult([partnership])

        async def refresh_side_effect(obj):
            if getattr(obj, "blocker_id", None) is None:
                obj.blocker_id = blocker_id
            if getattr(obj, "blocked_id", None) is None:
                obj.blocked_id = blocked_id

        mock_db.execute.side_effect = [existing_block_result, friendship_result, partnership_result]
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
        assert partnership.ended_at is not None
        assert mock_db.flush.await_count == 2

    @pytest.mark.asyncio
    async def test_delete_friendship_also_ends_partnerships(self, mock_db):
        """删好友时应同时结束双方的责任伙伴关系。"""
        from app.services.community_service import FriendshipService

        user_id = uuid4()
        other_user_id = uuid4()
        friendship = SimpleNamespace(
            user_id=user_id,
            friend_id=other_user_id,
            delete=AsyncMock(),
        )
        partnership = SimpleNamespace(status="active", ended_at=None)

        mock_db.execute.side_effect = [_ScalarResult(friendship), _ScalarResult([partnership])]

        result = await FriendshipService.delete_friendship(
            db=mock_db,
            user_id=user_id,
            friendship_id=uuid4(),
        )

        assert result is True
        friendship.delete.assert_awaited_once_with(mock_db, soft=True)
        assert partnership.ended_at is not None
        mock_db.flush.assert_awaited()

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

        mock_db.execute.side_effect = [
            _ScalarResult(existing_block),
            _ScalarResult(None),
            _ScalarResult([]),
        ]

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

    @pytest.mark.asyncio
    async def test_send_friend_request_integrity_error_accepts_reverse_pending(self, mock_db):
        """双向同时发起请求时，唯一约束冲突后应回退为自动接受。"""
        from app.models.community import FriendshipStatus
        from app.services.community_service import FriendshipService

        user_id = uuid4()
        target_id = uuid4()
        reverse_pending = SimpleNamespace(
            user_id=min(user_id, target_id, key=str),
            friend_id=max(user_id, target_id, key=str),
            status=FriendshipStatus.PENDING,
            initiated_by=target_id,
        )

        mock_db.execute.side_effect = [
            _ScalarResult(None),  # user row lock
            _ScalarResult(None),  # reverse pending pre-check
            _ScalarResult(None),  # existing relationship pre-check
            _ScalarResult(reverse_pending),  # re-query after IntegrityError
        ]
        mock_db.flush.side_effect = [
            IntegrityError("insert", {}, Exception("duplicate key")),
            None,
        ]

        result = await FriendshipService.send_friend_request(mock_db, user_id, target_id)

        assert result is reverse_pending
        assert reverse_pending.status == FriendshipStatus.ACCEPTED
        mock_db.refresh.assert_awaited_once_with(reverse_pending)

    @pytest.mark.asyncio
    async def test_join_group_integrity_error_maps_to_already_member(self, mock_db):
        """加入群组时若并发插入触发唯一约束，应返回明确错误。"""
        from app.services.community_service import GroupService

        group_id = uuid4()
        user_id = uuid4()
        group = SimpleNamespace(id=group_id, max_members=5)

        mock_db.execute.side_effect = [
            _ScalarResult(group),  # locked group
            _ScalarResult(None),  # existing membership pre-check
            _ScalarResult(1),  # current member count
        ]
        mock_db.flush.side_effect = IntegrityError("insert", {}, Exception("duplicate key"))

        with pytest.raises(ValueError, match="已是群组成员"):
            await GroupService.join_group(mock_db, group_id, user_id)

    @pytest.mark.asyncio
    async def test_claim_task_integrity_error_maps_to_already_claimed(self, mock_db, monkeypatch):
        """认领群任务时若并发写入 claim 失败，应返回明确错误。"""
        from app.models.community import GroupType
        from app.services.community_service import GroupTaskService
        from app.services.task_service import TaskService

        task_id = uuid4()
        user_id = uuid4()
        group_task = SimpleNamespace(
            id=task_id,
            title="群任务",
            tags=["focus"],
            estimated_minutes=30,
            difficulty=2,
            due_date=None,
            total_claims=0,
            group=SimpleNamespace(name="测试群", type=GroupType.SQUAD),
        )

        mock_db.execute.side_effect = [
            _ScalarResult(group_task),
            _ScalarResult(None),
        ]
        mock_db.flush.side_effect = [
            None,
            IntegrityError("insert", {}, Exception("duplicate key")),
        ]
        monkeypatch.setattr(TaskService, "_next_top_order_index", AsyncMock(return_value=0))

        with pytest.raises(ValueError, match="已认领此任务"):
            await GroupTaskService.claim_task(mock_db, task_id, user_id)
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

    @pytest.mark.asyncio
    async def test_share_resource_rejects_block_relationship(self, mock_db):
        """有拉黑关系时不允许继续向对方分享资源。"""
        from app.models.community import SharedResourceType
        from app.services.collaboration_service import CollaborationService

        user_id = uuid4()
        target_user_id = uuid4()

        mock_db.execute.side_effect = [_ScalarResult(object())]

        with pytest.raises(ValueError, match="blocked user"):
            await CollaborationService.share_resource(
                db=mock_db,
                user_id=user_id,
                resource_type=SharedResourceType.TASK,
                resource_id=uuid4(),
                target_user_id=target_user_id,
            )
