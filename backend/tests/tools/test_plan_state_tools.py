"""
Tests for PlanState Tools

Tests LLM tools for accessing plan state and tasks.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.tools.plan_state_tools import (
    GetPlanStateTool,
    GetTaskSummaryTool,
    GetTaskDetailTool,
    GetPlanStateParams,
    GetTaskSummaryParams,
    GetTaskDetailParams,
)
from app.models.plan_state import PlanState, PlanStateStatus


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def plan_id():
    return uuid4()


@pytest.fixture
def task_id():
    return uuid4()


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestGetPlanStateTool:
    """Tests for GetPlanStateTool"""

    @pytest.mark.asyncio
    async def test_returns_error_on_invalid_uuid(self, mock_db, user_id):
        """Should return error for invalid plan_id format"""
        tool = GetPlanStateTool()
        params = GetPlanStateParams(plan_id="not-a-uuid")

        result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is False
        assert "无效的ID格式" in result.error_message

    @pytest.mark.asyncio
    async def test_returns_error_when_state_not_found(self, mock_db, user_id, plan_id):
        """Should return error when plan state not found"""
        tool = GetPlanStateTool()
        params = GetPlanStateParams(plan_id=str(plan_id))

        with patch(
            "app.tools.plan_state_tools.PlanStateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_plan_state = AsyncMock(return_value=None)

            result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is False
        assert "未找到计划状态" in result.error_message

    @pytest.mark.asyncio
    async def test_returns_plan_state_data(self, mock_db, user_id, plan_id):
        """Should return plan state data on success"""
        tool = GetPlanStateTool()
        params = GetPlanStateParams(plan_id=str(plan_id))

        now = datetime.now(timezone.utc)
        mock_state = MagicMock()
        mock_state.plan_id = plan_id
        mock_state.status = PlanStateStatus.ACTIVE.value
        mock_state.version = 2
        mock_state.facts = {"key": "value"}
        mock_state.milestones = [{"id": "ms-1", "title": "Test"}]
        mock_state.task_index = {"total": 5, "completed": 3}
        mock_state.constraints = {}

        with patch(
            "app.tools.plan_state_tools.PlanStateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_plan_state = AsyncMock(return_value=mock_state)

            result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is True
        assert result.data["plan_id"] == str(plan_id)
        assert result.data["version"] == 2
        assert result.data["facts"]["key"] == "value"
        assert result.widget_type == "plan_context_summary"


class TestGetTaskSummaryTool:
    """Tests for GetTaskSummaryTool"""

    @pytest.mark.asyncio
    async def test_returns_error_on_invalid_uuid(self, mock_db, user_id):
        """Should return error for invalid plan_id format"""
        tool = GetTaskSummaryTool()
        params = GetTaskSummaryParams(plan_id="not-a-uuid")

        result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is False
        assert "无效的ID格式" in result.error_message

    @pytest.mark.asyncio
    async def test_returns_task_summaries(self, mock_db, user_id, plan_id):
        """Should return task summaries on success"""
        tool = GetTaskSummaryTool()
        params = GetTaskSummaryParams(plan_id=str(plan_id), limit=10)

        mock_summaries = [
            {"task_id": str(uuid4()), "title": "Task 1", "status": "PENDING"},
            {"task_id": str(uuid4()), "title": "Task 2", "status": "COMPLETED"},
        ]

        with patch(
            "app.tools.plan_state_tools.TaskStateSyncService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_task_summaries = AsyncMock(return_value=mock_summaries)

            result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is True
        assert result.data["task_count"] == 2
        assert len(result.data["tasks"]) == 2
        assert result.widget_type == "task_list"


class TestGetTaskDetailTool:
    """Tests for GetTaskDetailTool"""

    @pytest.mark.asyncio
    async def test_returns_error_on_invalid_uuid(self, mock_db, user_id):
        """Should return error for invalid task_id format"""
        tool = GetTaskDetailTool()
        params = GetTaskDetailParams(task_id="not-a-uuid")

        result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is False
        assert "无效的ID格式" in result.error_message

    @pytest.mark.asyncio
    async def test_returns_error_when_task_not_found(self, mock_db, user_id, task_id):
        """Should return error when task not found"""
        tool = GetTaskDetailTool()
        params = GetTaskDetailParams(task_id=str(task_id))

        with patch(
            "app.tools.plan_state_tools.TaskStateSyncService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_task_detail = AsyncMock(return_value=None)

            result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is False
        assert "未找到任务" in result.error_message

    @pytest.mark.asyncio
    async def test_returns_task_detail(self, mock_db, user_id, task_id, plan_id):
        """Should return task detail on success"""
        tool = GetTaskDetailTool()
        params = GetTaskDetailParams(task_id=str(task_id))

        mock_detail = {
            "task_id": str(task_id),
            "plan_id": str(plan_id),
            "title": "Test Task",
            "status": "PENDING",
            "type": "LEARNING",
            "difficulty": 3,
            "estimated_minutes": 25,
        }

        with patch(
            "app.tools.plan_state_tools.TaskStateSyncService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_task_detail = AsyncMock(return_value=mock_detail)

            result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is True
        assert result.data["task_id"] == str(task_id)
        assert result.data["title"] == "Test Task"
        assert result.widget_type == "task_detail"
