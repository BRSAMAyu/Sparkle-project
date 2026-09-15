"""
Tests for PlanState Tools

Tests LLM tools for accessing plan state and tasks.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.plan import Plan
from app.tools.plan_state_tools import (
    GetPlanStateTool,
    GetTaskSummaryTool,
    GetTaskDetailTool,
    GetPlanStateParams,
    GetTaskSummaryParams,
    GetTaskDetailParams,
)
from app.models.plan_state import PlanStateStatus


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
    async def test_falls_back_to_available_plan_for_non_uuid_ref(self, mock_db, user_id, plan_id):
        """Should gracefully resolve natural-language plan refs instead of hard failing on UUID parsing."""
        tool = GetPlanStateTool()
        params = GetPlanStateParams(plan_id="Python 学习计划")

        mock_plan = MagicMock(spec=Plan)
        mock_plan.id = plan_id
        mock_plan.name = "计算机科学基础巩固"
        mock_plan.is_primary = True
        mock_plan.is_active = True
        mock_plan.created_at = datetime.now(timezone.utc)
        mock_plan.updated_at = datetime.now(timezone.utc)
        mock_plan.deleted_at = None

        mock_state = MagicMock()
        mock_state.plan_id = plan_id
        mock_state.status = PlanStateStatus.ACTIVE.value
        mock_state.version = 1
        mock_state.facts = {}
        mock_state.milestones = []
        mock_state.task_index = {"total": 3, "completed": 1}
        mock_state.task_summaries = []
        mock_state.feedback_log = []
        mock_state.constraints = {}

        mock_plan_result = MagicMock()
        mock_plan_result.scalars.return_value.all.return_value = [mock_plan]

        with patch(
            "app.tools.plan_resolution._fetch_user_plans",
            AsyncMock(return_value=[mock_plan]),
        ), patch(
            "app.tools.plan_state_tools.PlanStateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_or_create_plan_state = AsyncMock(return_value=mock_state)
            mock_service.get_plan_state = AsyncMock(return_value=mock_state)

            result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is True
        assert result.data["plan_id"] == str(plan_id)
        assert result.data["plan_name"] == "计算机科学基础巩固"
        assert result.data["resolved_via"] == "primary_fallback"

    @pytest.mark.asyncio
    async def test_auto_creates_empty_plan_state_when_missing(self, mock_db, user_id, plan_id):
        """Should self-heal by creating a plan state instead of failing."""
        tool = GetPlanStateTool()
        params = GetPlanStateParams(plan_id=str(plan_id))

        mock_plan = MagicMock(spec=Plan)
        mock_plan.id = plan_id
        mock_plan.name = "测试计划"
        mock_plan.is_primary = True
        mock_plan.is_active = True
        mock_plan.created_at = datetime.now(timezone.utc)
        mock_plan.updated_at = datetime.now(timezone.utc)
        mock_plan.deleted_at = None

        with patch(
            "app.tools.plan_resolution._fetch_user_plans",
            AsyncMock(return_value=[mock_plan]),
        ), patch(
            "app.tools.plan_state_tools.PlanStateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_state = MagicMock()
            mock_state.plan_id = plan_id
            mock_state.status = PlanStateStatus.ACTIVE.value
            mock_state.version = 1
            mock_state.facts = {}
            mock_state.milestones = []
            mock_state.task_index = {"total": 1, "completed": 0}
            mock_state.task_summaries = [{"task_id": str(uuid4()), "title": "占位任务"}]
            mock_state.feedback_log = []
            mock_state.constraints = {}
            mock_service.get_or_create_plan_state = AsyncMock(return_value=mock_state)
            mock_service.get_plan_state = AsyncMock(return_value=mock_state)

            result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is True
        assert result.data["plan_id"] == str(plan_id)
        assert result.data["task_summary"]["total"] == 1

    @pytest.mark.asyncio
    async def test_returns_plan_state_data(self, mock_db, user_id, plan_id):
        """Should return plan state data on success"""
        tool = GetPlanStateTool()
        params = GetPlanStateParams(plan_id=str(plan_id))

        mock_plan = MagicMock(spec=Plan)
        mock_plan.id = plan_id
        mock_plan.name = "测试计划"
        mock_plan.is_primary = True
        mock_plan.is_active = True
        mock_plan.created_at = datetime.now(timezone.utc)
        mock_plan.updated_at = datetime.now(timezone.utc)
        mock_plan.deleted_at = None

        mock_state = MagicMock()
        mock_state.plan_id = plan_id
        mock_state.status = PlanStateStatus.ACTIVE.value
        mock_state.version = 2
        mock_state.facts = {"key": "value"}
        mock_state.milestones = [{"id": "ms-1", "title": "Test"}]
        mock_state.task_index = {"total": 5, "completed": 3}
        mock_state.constraints = {}

        with patch(
            "app.tools.plan_resolution._fetch_user_plans",
            AsyncMock(return_value=[mock_plan]),
        ), patch(
            "app.tools.plan_state_tools.PlanStateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_or_create_plan_state = AsyncMock(return_value=mock_state)
            mock_service.get_plan_state = AsyncMock(return_value=mock_state)

            result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is True
        assert result.data["plan_id"] == str(plan_id)
        assert result.data["version"] == 2
        assert result.data["facts"]["key"] == "value"
        assert result.widget_type == "plan_context_summary"

    @pytest.mark.asyncio
    async def test_hydrates_empty_state_from_task_sync(self, mock_db, user_id, plan_id):
        """Should rebuild summaries/index when a plan state exists but is still empty."""
        tool = GetPlanStateTool()
        params = GetPlanStateParams(plan_id=str(plan_id))

        mock_plan = MagicMock(spec=Plan)
        mock_plan.id = plan_id
        mock_plan.name = "测试计划"
        mock_plan.is_primary = True
        mock_plan.is_active = True
        mock_plan.created_at = datetime.now(timezone.utc)
        mock_plan.updated_at = datetime.now(timezone.utc)
        mock_plan.deleted_at = None

        empty_state = MagicMock()
        empty_state.plan_id = plan_id
        empty_state.status = PlanStateStatus.ACTIVE.value
        empty_state.version = 1
        empty_state.facts = {}
        empty_state.milestones = []
        empty_state.task_index = {"total": 0, "completed": 0}
        empty_state.task_summaries = []
        empty_state.feedback_log = []
        empty_state.constraints = {}

        hydrated_state = MagicMock()
        hydrated_state.plan_id = plan_id
        hydrated_state.status = PlanStateStatus.ACTIVE.value
        hydrated_state.version = 1
        hydrated_state.facts = {}
        hydrated_state.milestones = []
        hydrated_state.task_index = {"total": 3, "completed": 1}
        hydrated_state.task_summaries = [{"task_id": str(uuid4()), "title": "Task 1"}]
        hydrated_state.feedback_log = []
        hydrated_state.constraints = {}

        with patch(
            "app.tools.plan_resolution._fetch_user_plans",
            AsyncMock(return_value=[mock_plan]),
        ), patch(
            "app.tools.plan_state_tools.PlanStateService"
        ) as mock_service_class, patch(
            "app.tools.plan_state_tools.TaskStateSyncService"
        ) as mock_sync_class:
            mock_service = mock_service_class.return_value
            mock_service.get_or_create_plan_state = AsyncMock(return_value=empty_state)
            mock_service.get_plan_state = AsyncMock(return_value=hydrated_state)

            mock_sync = mock_sync_class.return_value
            mock_sync.rebuild_task_index = AsyncMock()
            mock_sync.sync_task_summaries = AsyncMock()

            result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is True
        mock_sync.rebuild_task_index.assert_awaited_once_with(user_id, plan_id)
        mock_sync.sync_task_summaries.assert_awaited_once_with(user_id, plan_id)
        assert result.data["task_summary"]["total"] == 3


class TestGetTaskSummaryTool:
    """Tests for GetTaskSummaryTool"""

    @pytest.mark.asyncio
    async def test_resolves_plan_by_name_or_fallback(self, mock_db, user_id, plan_id):
        """Should resolve non-UUID plan references for task summary queries."""
        tool = GetTaskSummaryTool()
        params = GetTaskSummaryParams(plan_id="Python")

        mock_plan = MagicMock(spec=Plan)
        mock_plan.id = plan_id
        mock_plan.name = "计算机科学基础巩固"
        mock_plan.is_primary = True
        mock_plan.is_active = True
        mock_plan.created_at = datetime.now(timezone.utc)
        mock_plan.updated_at = datetime.now(timezone.utc)
        mock_plan.deleted_at = None

        mock_summaries = [
            {"task_id": str(uuid4()), "title": "Task 1", "status": "PENDING"},
        ]

        with patch(
            "app.tools.plan_resolution._fetch_user_plans",
            AsyncMock(return_value=[mock_plan]),
        ), patch(
            "app.tools.plan_state_tools.TaskStateSyncService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_task_summaries = AsyncMock(return_value=mock_summaries)

            result = await tool.execute(params, str(user_id), mock_db)

        assert result.success is True
        assert result.data["plan_name"] == "计算机科学基础巩固"
        assert result.data["resolved_via"] == "primary_fallback"

    @pytest.mark.asyncio
    async def test_returns_task_summaries(self, mock_db, user_id, plan_id):
        """Should return task summaries on success"""
        tool = GetTaskSummaryTool()
        params = GetTaskSummaryParams(plan_id=str(plan_id), limit=10)

        mock_plan = MagicMock(spec=Plan)
        mock_plan.id = plan_id
        mock_plan.name = "测试计划"
        mock_plan.is_primary = True
        mock_plan.is_active = True
        mock_plan.created_at = datetime.now(timezone.utc)
        mock_plan.updated_at = datetime.now(timezone.utc)
        mock_plan.deleted_at = None

        mock_summaries = [
            {"task_id": str(uuid4()), "title": "Task 1", "status": "PENDING"},
            {"task_id": str(uuid4()), "title": "Task 2", "status": "COMPLETED"},
        ]

        with patch(
            "app.tools.plan_resolution._fetch_user_plans",
            AsyncMock(return_value=[mock_plan]),
        ), patch(
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
