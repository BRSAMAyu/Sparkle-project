"""
Unit tests for app.services.task_service module.
Tests task CRUD operations, status changes, and plan integration.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from datetime import datetime, timedelta

from app.services.task_service import TaskService
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.task import TaskCreate, TaskUpdate, TaskListQuery


def _mock_db():
    db = AsyncMock()
    db.add = Mock()
    db.delete = AsyncMock()
    return db


class TestTaskServiceGetById:
    """Test get_by_id method"""

    @pytest.mark.asyncio
    async def test_get_existing_task(self):
        """Test getting existing task by ID"""
        mock_db = _mock_db()

        task_id = uuid4()
        user_id = uuid4()

        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.user_id = user_id

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_db.execute.return_value = mock_result

        result = await TaskService.get_by_id(mock_db, task_id, user_id)

        assert result is mock_task
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """Test getting nonexistent task returns None"""
        mock_db = _mock_db()

        task_id = uuid4()
        user_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await TaskService.get_by_id(mock_db, task_id, user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_task_wrong_user(self):
        """Test getting task with wrong user ID returns None"""
        mock_db = _mock_db()

        task_id = uuid4()
        wrong_user_id = uuid4()

        # Query returns None because user_id doesn't match
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await TaskService.get_by_id(mock_db, task_id, wrong_user_id)

        assert result is None


class TestTaskServiceCreate:
    """Test create method"""

    @pytest.mark.asyncio
    async def test_create_task_with_all_fields(self):
        """Test creating task with all fields specified"""
        mock_db = _mock_db()
        user_id = uuid4()

        task_in = TaskCreate(
            title="Test Task",
            type=TaskType.LEARNING,
            estimated_minutes=30,
            difficulty=2,
            priority=1,
            due_date=datetime.now() + timedelta(days=1)
        )

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        min_result = Mock()
        min_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = min_result

        with patch('app.services.task_service.get_personalization_engine'):
            task = await TaskService.create(mock_db, task_in, user_id)

            assert task.title == "Test Task"
            assert task.type == TaskType.LEARNING
            assert task.estimated_minutes == 30
            assert task.difficulty == 2
            assert task.status == TaskStatus.PENDING
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_defaults(self):
        """Test creating task with default values"""
        mock_db = _mock_db()
        user_id = uuid4()

        task_in = TaskCreate(
            title="Quick Task",
            type=TaskType.LEARNING
        )

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        min_result = Mock()
        min_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = min_result

        with patch('app.services.task_service.get_personalization_engine') as mock_engine:
            # Mock personalization profile
            mock_profile = Mock()
            mock_profile.preferred_task_duration = 45
            mock_profile.difficulty_gradient = 0.5 # Should map to difficulty 3 (1 + 0.5*4 = 3)
            
            # Make get_task_plan_profile return an awaitable (AsyncMock)
            mock_engine.return_value.get_task_plan_profile = AsyncMock(return_value=mock_profile)

            task = await TaskService.create(mock_db, task_in, user_id)

            assert task.estimated_minutes == 45
            assert task.difficulty == 3
            mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_personalization_fails(self):
        """Test task creation when personalization fails"""
        mock_db = _mock_db()
        user_id = uuid4()

        task_in = TaskCreate(
            title="Fallback Task",
            type=TaskType.ERROR_FIX
        )

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        min_result = Mock()
        min_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = min_result

        with patch('app.services.task_service.get_personalization_engine') as mock_engine:
            # Personalization raises exception
            mock_engine.return_value.get_task_plan_profile.side_effect = Exception("Engine failed")

            task = await TaskService.create(mock_db, task_in, user_id)

            # Should use fallback defaults
            assert task.estimated_minutes == 25
            assert task.difficulty == 1

    @pytest.mark.asyncio
    async def test_create_task_with_plan(self):
        """Test creating task that belongs to a plan"""
        mock_db = _mock_db()
        user_id = uuid4()
        plan_id = uuid4()

        task_in = TaskCreate(
            title="Plan Task",
            type=TaskType.LEARNING,
            plan_id=plan_id
        )

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        min_result = Mock()
        min_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = min_result

        # Mock TaskStateSyncService
        with patch('app.services.task_state_sync.TaskStateSyncService') as MockSyncService:
            mock_sync = MockSyncService.return_value
            mock_sync.on_task_created = AsyncMock()
            
            with patch('app.services.task_service.get_personalization_engine'):
                task = await TaskService.create(mock_db, task_in, user_id)

                assert task.plan_id == plan_id
                mock_sync.on_task_created.assert_called_once()


class TestTaskServiceUpdate:
    """Test update method"""

    @pytest.mark.asyncio
    async def test_update_task_title(self):
        """Test updating task title"""
        mock_db = _mock_db()
        user_id = uuid4()

        task = Mock(spec=Task)
        task.id = uuid4()
        task.user_id = user_id
        task.title = "Old Title"
        task.plan_id = None

        task_in = TaskUpdate(title="New Title")

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        updated_task = await TaskService.update(mock_db, task, task_in)

        assert updated_task.title == "New Title"
        mock_db.commit.assert_called_once()


class TestTaskServiceDelete:
    """Test delete method"""

    @pytest.mark.asyncio
    async def test_delete_task(self):
        """Test deleting a task"""
        mock_db = _mock_db()
        user_id = uuid4()

        task = Mock(spec=Task)
        task.id = uuid4()
        task.user_id = user_id

        mock_db.commit.return_value = None

        await TaskService.delete(mock_db, task)

        mock_db.delete.assert_called_once_with(task)
        mock_db.commit.assert_called_once()


class TestTaskStatusChanges:
    """Test task status change logic"""

    @pytest.mark.asyncio
    async def test_start_task(self):
        """Test starting a task (PENDING -> IN_PROGRESS)"""
        mock_db = _mock_db()
        user_id = uuid4()

        task = Mock(spec=Task)
        task.id = uuid4()
        task.user_id = user_id
        task.status = TaskStatus.PENDING
        task.plan_id = None

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch.object(TaskService, 'get_by_id', return_value=task):
            result = await TaskService.start_task(mock_db, task.id, user_id)

            assert result.status == TaskStatus.IN_PROGRESS
            assert result.started_at is not None

    @pytest.mark.asyncio
    async def test_complete_task(self):
        """Test completing a task"""
        mock_db = _mock_db()
        user_id = uuid4()

        task = Mock(spec=Task)
        task.id = uuid4()
        task.user_id = user_id
        task.status = TaskStatus.IN_PROGRESS
        task.type = TaskType.LEARNING
        task.difficulty = 2
        task.estimated_minutes = 30
        task.plan_id = None
        task.knowledge_node_id = None

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        claim_result = Mock()
        claim_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = claim_result
        
        # Mock event bus
        with patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_publish:
            with patch.object(TaskService, 'get_by_id', return_value=task):
                result = await TaskService.complete_task(mock_db, task.id, user_id, actual_minutes=25)

                assert result.status == TaskStatus.COMPLETED
                mock_db.commit.assert_called()
                mock_publish.assert_called()


class TestTaskListQuery:
    """Test task list querying"""

    @pytest.mark.asyncio
    async def test_get_user_tasks(self):
        """Test getting all tasks for a user via get_multi"""
        mock_db = _mock_db()
        user_id = uuid4()

        mock_task = Mock(spec=Task)
        mock_task.id = uuid4()
        mock_task.user_id = user_id

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_task]
        mock_db.execute.return_value = mock_result

        tasks, count = await TaskService.get_multi(mock_db, user_id, TaskListQuery())

        assert len(tasks) == 1
        assert tasks[0].user_id == user_id

    @pytest.mark.asyncio
    async def test_get_tasks_by_status(self):
        """Test filtering tasks by status"""
        mock_db = _mock_db()
        user_id = uuid4()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        tasks, count = await TaskService.get_multi(
            mock_db,
            user_id,
            TaskListQuery(status=TaskStatus.PENDING)
        )

        # Should execute query
        mock_db.execute.assert_called_once()


class TestDifficultyCalculation:
    """Test difficulty calculation logic"""

    def test_difficulty_from_gradient(self):
        """Test converting difficulty gradient (float) to numeric value"""
        # Test known gradients (0.0 to 1.0)
        assert TaskService._difficulty_from_gradient(0.0) == 1
        assert TaskService._difficulty_from_gradient(0.25) == 2
        assert TaskService._difficulty_from_gradient(0.5) == 3
        assert TaskService._difficulty_from_gradient(0.75) == 4
        assert TaskService._difficulty_from_gradient(1.0) == 5

    def test_difficulty_from_unknown_gradient(self):
        """Test invalid gradient defaults to 1"""
        result = TaskService._difficulty_from_gradient(None)
        assert result == 1
