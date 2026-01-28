"""
Unit tests for app.services.task_service module.
Tests task CRUD operations, status changes, and plan integration.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.services.task_service import TaskService
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.task import TaskCreate, TaskUpdate


class TestTaskServiceGetById:
    """Test get_by_id method"""

    @pytest.mark.asyncio
    async def test_get_existing_task(self):
        """Test getting existing task by ID"""
        mock_db = AsyncMock()

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
        mock_db = AsyncMock()

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
        mock_db = AsyncMock()

        task_id = uuid4()
        correct_user_id = uuid4()
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
        mock_db = AsyncMock()
        user_id = uuid4()

        task_in = TaskCreate(
            title="Test Task",
            type=TaskType.STUDY,
            estimated_minutes=30,
            difficulty=2,
            priority=1,
            due_date=datetime.now() + timedelta(days=1)
        )

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch('app.services.task_service.get_personalization_engine'):
            task = await TaskService.create(mock_db, task_in, user_id)

            assert task.title == "Test Task"
            assert task.type == TaskType.STUDY
            assert task.estimated_minutes == 30
            assert task.difficulty == 2
            assert task.status == TaskStatus.PENDING
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_defaults(self):
        """Test creating task with default values"""
        mock_db = AsyncMock()
        user_id = uuid4()

        task_in = TaskCreate(
            title="Quick Task",
            type=TaskType.STUDY
        )

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch('app.services.task_service.get_personalization_engine') as mock_engine:
            # Mock personalization profile
            mock_profile = Mock()
            mock_profile.preferred_task_duration = 45
            mock_profile.difficulty_gradient = "moderate"
            mock_engine.return_value.get_task_plan_profile.return_value = mock_profile

            task = await TaskService.create(mock_db, task_in, user_id)

            assert task.estimated_minutes == 45
            assert task.difficulty == 1
            mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_personalization_fails(self):
        """Test task creation when personalization fails"""
        mock_db = AsyncMock()
        user_id = uuid4()

        task_in = TaskCreate(
            title="Fallback Task",
            type=TaskType.REVIEW
        )

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

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
        mock_db = AsyncMock()
        user_id = uuid4()
        plan_id = uuid4()

        task_in = TaskCreate(
            title="Plan Task",
            type=TaskType.STUDY,
            plan_id=plan_id
        )

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch('app.services.task_service.get_personalization_engine'):
            with patch('app.services.task_service.plan_state_service') as mock_plan_svc:
                task = await TaskService.create(mock_db, task_in, user_id)

                # Should sync with plan
                assert task.plan_id == plan_id


class TestTaskServiceUpdate:
    """Test update method"""

    @pytest.mark.asyncio
    async def test_update_task_title(self):
        """Test updating task title"""
        mock_db = AsyncMock()
        user_id = uuid4()

        task = Mock(spec=Task)
        task.id = uuid4()
        task.user_id = user_id
        task.title = "Old Title"

        task_in = TaskUpdate(title="New Title")

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch.object(TaskService, 'get_by_id', return_value=task):
            updated_task = await TaskService.update(mock_db, task, task_in)

            assert updated_task.title == "New Title"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_status_to_completed(self):
        """Test updating task status to completed"""
        mock_db = AsyncSession()
        user_id = uuid4()

        task = Mock(spec=Task)
        task.id = uuid4()
        task.user_id = user_id
        task.status = TaskStatus.IN_PROGRESS

        task_in = TaskUpdate(status=TaskStatus.COMPLETED)

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch.object(TaskService, 'get_by_id', return_value=task):
            with patch('app.services.task_service photons') as mock_photons:
                updated_task = await TaskService.update(mock_db, task, task_in)

                assert updated_task.status == TaskStatus.COMPLETED
                mock_db.commit.assert_called_once()


class TestTaskServiceDelete:
    """Test delete method"""

    @pytest.mark.asyncio
    async def test_delete_task(self):
        """Test deleting a task"""
        mock_db = AsyncMock()
        user_id = uuid4()

        task = Mock(spec=Task)
        task.id = uuid4()
        task.user_id = user_id

        mock_db.commit.return_value = None

        with patch.object(TaskService, 'get_by_id', return_value=task):
            await TaskService.delete(mock_db, task)

            mock_db.delete.assert_called_once_with(task)
            mock_db.commit.assert_called_once()


class TestTaskStatusChanges:
    """Test task status change logic"""

    @pytest.mark.asyncio
    async def test_start_task(self):
        """Test starting a task (PENDING -> IN_PROGRESS)"""
        mock_db = AsyncMock()
        user_id = uuid4()

        task = Mock(spec=Task)
        task.id = uuid4()
        task.user_id = user_id
        task.status = TaskStatus.PENDING

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch.object(TaskService, 'get_by_id', return_value=task):
            result = await TaskService.start_task(mock_db, task.id, user_id)

            assert result.status == TaskStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_complete_task(self):
        """Test completing a task"""
        mock_db = AsyncMock()
        user_id = uuid4()

        task = Mock(spec=Task)
        task.id = uuid4()
        task.user_id = user_id
        task.status = TaskStatus.IN_PROGRESS
        task.type = TaskType.STUDY
        task.difficulty = 2

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch.object(TaskService, 'get_by_id', return_value=task):
            with patch('app.services.task_service.photon_service') as mock_photon:
                result = await TaskService.complete_task(mock_db, task.id, user_id)

                assert result.status == TaskStatus.COMPLETED
                mock_db.commit.assert_called_once()


class TestTaskListQuery:
    """Test task list querying"""

    @pytest.mark.asyncio
    async def test_get_user_tasks(self):
        """Test getting all tasks for a user"""
        mock_db = AsyncMock()
        user_id = uuid4()

        mock_task = Mock(spec=Task)
        mock_task.id = uuid4()
        mock_task.user_id = user_id

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_task]
        mock_db.execute.return_value = mock_result

        tasks = await TaskService.get_user_tasks(mock_db, user_id)

        assert len(tasks) == 1
        assert tasks[0].user_id == user_id

    @pytest.mark.asyncio
    async def test_get_tasks_by_status(self):
        """Test filtering tasks by status"""
        mock_db = AsyncMock()
        user_id = uuid4()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        tasks = await TaskService.get_user_tasks(
            mock_db,
            user_id,
            status=TaskStatus.PENDING
        )

        # Should execute query
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tasks_with_pagination(self):
        """Test paginated task list"""
        mock_db = AsyncMock()
        user_id = uuid4()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.unique.return_value.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        tasks = await TaskService.get_user_tasks(
            mock_db,
            user_id,
            skip=0,
            limit=10
        )

        mock_db.execute.assert_called()


class TestDifficultyCalculation:
    """Test difficulty calculation logic"""

    def test_difficulty_from_gradient(self):
        """Test converting difficulty gradient to numeric value"""
        # Test known gradients
        assert TaskService._difficulty_from_gradient("easy") == 1
        assert TaskService._difficulty_from_gradient("moderate") == 2
        assert TaskService._difficulty_from_gradient("hard") == 3

    def test_difficulty_from_unknown_gradient(self):
        """Test unknown gradient defaults to 1"""
        result = TaskService._difficulty_from_gradient("unknown")
        assert result == 1


class TestTaskValidation:
    """Test task validation logic"""

    @pytest.mark.asyncio
    async def test_validate_task_due_date_future(self):
        """Test that due date must be in future"""
        mock_db = AsyncMock()
        user_id = uuid4()

        task_in = TaskCreate(
            title="Invalid Task",
            type=TaskType.STUDY,
            due_date=datetime.now() - timedelta(days=1)  # Past date
        )

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch('app.services.task_service.get_personalization_engine'):
            # Should raise validation error
            with pytest.raises(ValueError):
                await TaskService.create(mock_db, task_in, user_id)


class TestTaskSorting:
    """Test task sorting and ordering"""

    @pytest.mark.asyncio
    async def test_get_tasks_sorted_by_priority(self):
        """Test getting tasks sorted by priority"""
        mock_db = AsyncMock()
        user_id = uuid4()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        tasks = await TaskService.get_user_tasks(
            mock_db,
            user_id,
            sort_by="priority"
        )

        # Should execute query
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tasks_sorted_by_due_date(self):
        """Test getting tasks sorted by due date"""
        mock_db = AsyncMock()
        user_id = uuid4()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        tasks = await TaskService.get_user_tasks(
            mock_db,
            user_id,
            sort_by="due_date"
        )

        mock_db.execute.assert_called_once()


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_update_nonexistent_task(self):
        """Test updating nonexistent task raises error"""
        mock_db = AsyncSession()
        user_id = uuid4()
        task_id = uuid4()

        task_in = TaskUpdate(title="New Title")

        with patch.object(TaskService, 'get_by_id', return_value=None):
            with pytest.raises(ValueError):
                await TaskService.update(mock_db, Mock(), task_in)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self):
        """Test deleting nonexistent task raises error"""
        mock_db = AsyncSession()
        user_id = uuid4()
        task_id = uuid4()

        with patch.object(TaskService, 'get_by_id', return_value=None):
            with pytest.raises(ValueError):
                await TaskService.delete(mock_db, Mock())
