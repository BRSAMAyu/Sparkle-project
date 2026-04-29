"""
Phase 2b: Production-grade tests for Plan/Task AI tools.
Tests real business logic — parameter mapping, status routing, fallback behavior,
learning path matching, entity card generation, and error handling.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate
from app.tools.base import ToolResult
from app.tools.plan_tools import (
    CreatePlanTool,
    GenerateTasksForPlanTool,
    _GeneratedPlanTaskSchema,
    _LearningPathNodeRef,
)
from app.tools.schemas import (
    CreatePlanParams,
    CreateTaskParams,
    GenerateTasksForPlanParams,
    PlanStage as SchemaPlanStage,
    PlanType as SchemaPlanType,
    TaskType as SchemaTaskType,
    UpdateTaskStatusParams,
    BatchCreateTasksParams,
    BreakdownTaskParams,
    SuggestQuickTaskParams,
)
from app.tools.task_tools import (
    CreateTaskTool,
    UpdateTaskStatusTool,
    BatchCreateTasksTool,
    SuggestQuickTaskTool,
    BreakdownTaskTool,
    _BreakdownSubtaskSchema,
)


# ─── Fixtures ────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_session(db_session: AsyncSession) -> AsyncSession:
    return db_session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(username="tooluser", email="tool@test.com", hashed_password="h", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
def user_id(test_user: User) -> str:
    return str(test_user.id)


def _make_plan(**overrides) -> Plan:
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        name="Test Plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        description="desc",
        is_active=True,
        is_primary=False,
        progress=0.0,
        target_date=None,
        subject=None,
        source=None,
        source_metadata=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_task(**overrides) -> Task:
    defaults = dict(
        id=uuid4(),
        title="Test Task",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
        difficulty=2,
        energy_cost=1,
        priority=2,
        actual_minutes=None,
        guide_content="guide",
        tags=[],
        plan_id=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        due_date=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_task_create_result(**overrides) -> dict:
    defaults = dict(
        id=str(uuid4()),
        title="Test Task",
        type="LEARNING",
        status="PENDING",
        estimated_minutes=30,
        priority=2,
        guide_content="guide",
        plan_id=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        tags=[],
        difficulty=1,
        energy_cost=1,
    )
    defaults.update(overrides)
    return defaults


# ─── CreatePlanTool ──────────────────────────────────────────


class TestCreatePlanTool:
    @pytest.mark.asyncio
    async def test_creates_plan_and_returns_widget(self, db_session, test_user, user_id):
        plan = _make_plan(user_id=test_user.id)
        with patch("app.tools.plan_tools.PlanService.create", new_callable=AsyncMock, return_value=plan):
            tool = CreatePlanTool()
            params = CreatePlanParams(
                title="My Plan",
                plan_type=SchemaPlanType.GROWTH,
                description="A test plan",
            )
            result = await tool.execute(params, user_id, db_session)
            assert result.success is True
            assert result.widget_type == "plan_card"
            assert result.data["plan_id"] == str(plan.id)
            assert result.widget_data is not None
            assert result.widget_data["entity_card"]["entity_type"] == "plan"

    @pytest.mark.asyncio
    async def test_maps_all_params_to_plan_create(self, db_session, test_user, user_id):
        plan = _make_plan(user_id=test_user.id)
        with patch("app.tools.plan_tools.PlanService.create", new_callable=AsyncMock, return_value=plan) as mock_create:
            tool = CreatePlanTool()
            params = CreatePlanParams(
                title="Sprint Plan",
                plan_type=SchemaPlanType.SPRINT,
                plan_stage=SchemaPlanStage.SPRINT,
                description="Exam prep",
                subject_id="math-101",
            )
            await tool.execute(params, user_id, db_session)
            plan_create_arg = mock_create.call_args.kwargs["obj_in"]
            assert plan_create_arg.name == "Sprint Plan"
            assert plan_create_arg.type.value == "sprint"

    @pytest.mark.asyncio
    async def test_handles_service_exception(self, db_session, user_id):
        with patch("app.tools.plan_tools.PlanService.create", new_callable=AsyncMock, side_effect=Exception("DB error")):
            tool = CreatePlanTool()
            params = CreatePlanParams(title="Plan", plan_type=SchemaPlanType.GROWTH)
            result = await tool.execute(params, user_id, db_session)
            assert result.success is False
            assert "DB error" in result.error_message
            assert result.suggestion is not None


# ─── GenerateTasksForPlanTool ────────────────────────────────


class TestResolveMaxSessionMinutes:
    def test_none_returns_default(self):
        assert GenerateTasksForPlanTool._resolve_max_session_minutes(None) == 45

    def test_clamps_to_15_minimum(self):
        constraints = SimpleNamespace(max_session_minutes=5)
        assert GenerateTasksForPlanTool._resolve_max_session_minutes(constraints) == 15

    def test_clamps_to_90_maximum(self):
        constraints = SimpleNamespace(max_session_minutes=200)
        assert GenerateTasksForPlanTool._resolve_max_session_minutes(constraints) == 90

    def test_valid_value_passes_through(self):
        constraints = SimpleNamespace(max_session_minutes=60)
        assert GenerateTasksForPlanTool._resolve_max_session_minutes(constraints) == 60

    def test_none_attribute_returns_default(self):
        constraints = SimpleNamespace(max_session_minutes=None)
        assert GenerateTasksForPlanTool._resolve_max_session_minutes(constraints) == 45


class TestInferDifficulty:
    def test_reflection_always_1(self):
        for priority in range(1, 6):
            assert GenerateTasksForPlanTool._infer_difficulty("reflection", priority) == 1

    def test_training_maps_priority(self):
        assert GenerateTasksForPlanTool._infer_difficulty("training", 1) == 2
        assert GenerateTasksForPlanTool._infer_difficulty("training", 3) == 3
        assert GenerateTasksForPlanTool._infer_difficulty("training", 5) == 5

    def test_error_fix_maps_priority(self):
        assert GenerateTasksForPlanTool._infer_difficulty("error_fix", 2) == 2
        assert GenerateTasksForPlanTool._infer_difficulty("error_fix", 5) == 5

    def test_learning_default(self):
        assert GenerateTasksForPlanTool._infer_difficulty("learning", 2) == 1
        assert GenerateTasksForPlanTool._infer_difficulty("learning", 3) == 2
        assert GenerateTasksForPlanTool._infer_difficulty("learning", 5) == 4

    def test_case_insensitive(self):
        assert GenerateTasksForPlanTool._infer_difficulty("REFLECTION", 3) == 1
        assert GenerateTasksForPlanTool._infer_difficulty("Training", 3) == 3

    def test_empty_type(self):
        assert GenerateTasksForPlanTool._infer_difficulty("", 3) == 2

    def test_none_type(self):
        assert GenerateTasksForPlanTool._infer_difficulty(None, 3) == 2


class TestGenerateTasksForPlanTool:
    @pytest.mark.asyncio
    async def test_plan_not_found_returns_error(self, db_session, user_id):
        with patch("app.tools.plan_tools.PlanService.get_by_id", new_callable=AsyncMock, return_value=None):
            tool = GenerateTasksForPlanTool()
            params = GenerateTasksForPlanParams(
                plan_id=str(uuid4()),
                topic="math",
                difficulty="medium",
                task_count=3,
            )
            result = await tool.execute(params, user_id, db_session)
            assert result.success is False
            assert "不存在" in result.error_message

    @pytest.mark.asyncio
    async def test_plan_wrong_user_returns_error(self, db_session, user_id):
        other_user_id = uuid4()
        plan = _make_plan(user_id=other_user_id)
        with patch("app.tools.plan_tools.PlanService.get_by_id", new_callable=AsyncMock, return_value=plan):
            tool = GenerateTasksForPlanTool()
            params = GenerateTasksForPlanParams(
                plan_id=str(plan.id),
                topic="math",
                difficulty="medium",
            )
            result = await tool.execute(params, user_id, db_session)
            assert result.success is False
            assert "不存在" in result.error_message

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_error(self, db_session, user_id):
        tool = GenerateTasksForPlanTool()
        params = GenerateTasksForPlanParams(
            plan_id="not-a-uuid",
            topic="math",
            difficulty="medium",
        )
        result = await tool.execute(params, user_id, db_session)
        assert result.success is False
        assert "格式错误" in result.error_message

    @pytest.mark.asyncio
    async def test_uses_fallback_when_llm_fails(self, db_session, test_user, user_id):
        plan = _make_plan(user_id=test_user.id)
        mock_constraints = SimpleNamespace(
            max_session_minutes=45,
            preferred_task_size="medium",
            time_multiplier=1.0,
            require_warmup_task=False,
            to_prompt_block=lambda: "",
        )
        with (
            patch("app.tools.plan_tools.PlanService.get_by_id", new_callable=AsyncMock, return_value=plan),
            patch("app.tools.plan_tools.PersonaAwarePlanner") as mock_planner_cls,
            patch("app.tools.plan_tools.TaskService.create", new_callable=AsyncMock, side_effect=lambda db, obj_in, user_id: _make_task(id=obj_in.plan_id or uuid4(), title=obj_in.title, type=obj_in.type, estimated_minutes=obj_in.estimated_minutes, priority=obj_in.priority)),
            patch("app.tools.plan_tools.AsyncSessionLocal"),
            patch.object(GenerateTasksForPlanTool, "_generate_tasks_with_llm", new_callable=AsyncMock, return_value=None),
            patch.object(GenerateTasksForPlanTool, "_get_learning_path_node_refs", new_callable=AsyncMock, return_value=[]),
        ):
            mock_planner_cls.return_value.build_constraints = AsyncMock(return_value=mock_constraints)
            tool = GenerateTasksForPlanTool()
            params = GenerateTasksForPlanParams(
                plan_id=str(plan.id),
                topic="微积分",
                difficulty="medium",
                task_count=4,
            )
            result = await tool.execute(params, user_id, db_session)
            assert result.success is True
            assert result.data["task_count"] == 4
            assert result.data["has_context"] is False
            assert result.widget_type == "task_list"

    @pytest.mark.asyncio
    async def test_llm_generates_valid_tasks(self, db_session, test_user, user_id):
        plan = _make_plan(user_id=test_user.id)
        mock_constraints = SimpleNamespace(
            max_session_minutes=45,
            preferred_task_size="medium",
            time_multiplier=1.0,
            require_warmup_task=False,
            to_prompt_block=lambda: "",
        )
        llm_tasks = [
            {"title": "Learn basics", "description": "Read ch1", "type": "learning", "estimated_minutes": 25, "priority": 2},
            {"title": "Practice problems", "description": "Do ex 1-5", "type": "training", "estimated_minutes": 35, "priority": 3},
        ]
        with (
            patch("app.tools.plan_tools.PlanService.get_by_id", new_callable=AsyncMock, return_value=plan),
            patch("app.tools.plan_tools.PersonaAwarePlanner") as mock_planner_cls,
            patch("app.tools.plan_tools.TaskService.create", new_callable=AsyncMock, side_effect=lambda db, obj_in, user_id: _make_task(title=obj_in.title, type=obj_in.type, estimated_minutes=obj_in.estimated_minutes, priority=obj_in.priority)),
            patch("app.tools.plan_tools.AsyncSessionLocal"),
            patch.object(GenerateTasksForPlanTool, "_generate_tasks_with_llm", new_callable=AsyncMock, return_value=llm_tasks),
            patch.object(GenerateTasksForPlanTool, "_get_learning_path_node_refs", new_callable=AsyncMock, return_value=[]),
        ):
            mock_planner_cls.return_value.build_constraints = AsyncMock(return_value=mock_constraints)
            tool = GenerateTasksForPlanTool()
            params = GenerateTasksForPlanParams(
                plan_id=str(plan.id),
                topic="math",
                difficulty="hard",
                task_count=3,
            )
            result = await tool.execute(params, user_id, db_session)
            assert result.success is True
            assert result.data["task_count"] == 2
            assert result.data["has_context"] is False

    @pytest.mark.asyncio
    async def test_invalid_task_schema_skipped(self, db_session, test_user, user_id):
        plan = _make_plan(user_id=test_user.id)
        mock_constraints = SimpleNamespace(
            max_session_minutes=45,
            preferred_task_size="medium",
            time_multiplier=1.0,
            require_warmup_task=False,
            to_prompt_block=lambda: "",
        )
        llm_tasks = [
            {"title": "Valid Task", "description": "ok", "type": "learning", "estimated_minutes": 25, "priority": 2},
            {"title": "X", "description": "too short title will fail"},
            {"title": "", "description": "empty title", "type": "learning", "estimated_minutes": 25, "priority": 2},
        ]
        with (
            patch("app.tools.plan_tools.PlanService.get_by_id", new_callable=AsyncMock, return_value=plan),
            patch("app.tools.plan_tools.PersonaAwarePlanner") as mock_planner_cls,
            patch("app.tools.plan_tools.TaskService.create", new_callable=AsyncMock, side_effect=lambda db, obj_in, user_id: _make_task(title=obj_in.title, type=obj_in.type, estimated_minutes=obj_in.estimated_minutes, priority=obj_in.priority)),
            patch("app.tools.plan_tools.AsyncSessionLocal"),
            patch.object(GenerateTasksForPlanTool, "_generate_tasks_with_llm", new_callable=AsyncMock, return_value=llm_tasks),
            patch.object(GenerateTasksForPlanTool, "_get_learning_path_node_refs", new_callable=AsyncMock, return_value=[]),
        ):
            mock_planner_cls.return_value.build_constraints = AsyncMock(return_value=mock_constraints)
            tool = GenerateTasksForPlanTool()
            result = await tool.execute(
                GenerateTasksForPlanParams(plan_id=str(plan.id), topic="math", difficulty="medium", task_count=3),
                user_id, db_session,
            )
            assert result.success is True
            assert result.data["task_count"] == 1


class TestFallbackTasks:
    @pytest.mark.asyncio
    async def test_without_learning_path_nodes(self, db_session):
        plan = _make_plan(name="Calculus", subject="math")
        mock_constraints = SimpleNamespace(max_session_minutes=45)
        tool = GenerateTasksForPlanTool()
        with patch.object(tool, "_get_learning_path_node_names", new_callable=AsyncMock, return_value=[]):
            tasks = await tool._build_fallback_tasks(plan, "微积分", 4, mock_constraints, db_session)
        assert len(tasks) == 4
        assert tasks[0]["title"].startswith("梳理")
        assert tasks[0]["type"] == "learning"
        assert any(t["type"] == "training" for t in tasks)
        assert any(t["type"] == "error_fix" for t in tasks)
        assert any(t["type"] == "reflection" for t in tasks)

    @pytest.mark.asyncio
    async def test_with_learning_path_nodes(self, db_session):
        plan = _make_plan(name="Physics", subject="physics")
        mock_constraints = SimpleNamespace(max_session_minutes=45)
        tool = GenerateTasksForPlanTool()
        with patch.object(tool, "_get_learning_path_node_names", new_callable=AsyncMock, return_value=["力学", "运动学", "牛顿定律"]):
            tasks = await tool._build_fallback_tasks(plan, "牛顿定律", 5, mock_constraints, db_session)
        assert len(tasks) == 5
        assert tasks[0]["title"].startswith("补齐前置知识")
        assert tasks[-1]["type"] == "reflection"

    @pytest.mark.asyncio
    async def test_pad_to_task_count(self, db_session):
        plan = _make_plan(name="Topic", subject=None)
        mock_constraints = SimpleNamespace(max_session_minutes=45)
        tool = GenerateTasksForPlanTool()
        with patch.object(tool, "_get_learning_path_node_names", new_callable=AsyncMock, return_value=[]):
            tasks = await tool._build_fallback_tasks(plan, "math", 8, mock_constraints, db_session)
        assert len(tasks) == 8
        assert "巩固任务" in tasks[-1]["title"]

    @pytest.mark.asyncio
    async def test_respects_max_session_minutes(self, db_session):
        plan = _make_plan(name="Topic", subject=None)
        mock_constraints = SimpleNamespace(max_session_minutes=20)
        tool = GenerateTasksForPlanTool()
        with patch.object(tool, "_get_learning_path_node_names", new_callable=AsyncMock, return_value=[]):
            tasks = await tool._build_fallback_tasks(plan, "math", 4, mock_constraints, db_session)
        for task in tasks:
            assert task["estimated_minutes"] <= 20


class TestMatchLearningPathNodeId:
    def test_no_nodes_returns_none(self):
        tool = GenerateTasksForPlanTool()
        validated = _GeneratedPlanTaskSchema(title="Learn X", description="desc", type="learning", estimated_minutes=25, priority=2)
        assert tool._match_learning_path_node_id(validated=validated, node_refs=[], task_index=0) is None

    def test_matches_by_name_in_title(self):
        node_id = uuid4()
        refs = [_LearningPathNodeRef(id=node_id, name="Newton's Laws")]
        tool = GenerateTasksForPlanTool()
        validated = _GeneratedPlanTaskSchema(title="Study Newton's Laws", description="", type="learning", estimated_minutes=25, priority=2)
        assert tool._match_learning_path_node_id(validated=validated, node_refs=refs, task_index=0) == node_id

    def test_matches_by_name_in_description(self):
        node_id = uuid4()
        refs = [_LearningPathNodeRef(id=node_id, name="Calculus")]
        tool = GenerateTasksForPlanTool()
        validated = _GeneratedPlanTaskSchema(title="Read chapter", description="Learn Calculus basics", type="learning", estimated_minutes=25, priority=2)
        assert tool._match_learning_path_node_id(validated=validated, node_refs=refs, task_index=0) == node_id

    def test_single_node_returns_it(self):
        node_id = uuid4()
        refs = [_LearningPathNodeRef(id=node_id, name="Physics")]
        tool = GenerateTasksForPlanTool()
        validated = _GeneratedPlanTaskSchema(title="Unrelated", description="Nothing", type="learning", estimated_minutes=25, priority=2)
        assert tool._match_learning_path_node_id(validated=validated, node_refs=refs, task_index=5) == node_id

    def test_fallback_to_index(self):
        node_a, node_b, node_c = uuid4(), uuid4(), uuid4()
        refs = [_LearningPathNodeRef(id=node_a, name="AlphaNode"), _LearningPathNodeRef(id=node_b, name="BetaNode"), _LearningPathNodeRef(id=node_c, name="GammaNode")]
        tool = GenerateTasksForPlanTool()
        validated = _GeneratedPlanTaskSchema(title="Generic Step", description="No specific node", type="learning", estimated_minutes=25, priority=2)
        assert tool._match_learning_path_node_id(validated=validated, node_refs=refs, task_index=1) == node_b

    def test_index_beyond_nodes_returns_last(self):
        node_a, node_b = uuid4(), uuid4()
        refs = [_LearningPathNodeRef(id=node_a, name="AlphaNode"), _LearningPathNodeRef(id=node_b, name="BetaNode")]
        tool = GenerateTasksForPlanTool()
        validated = _GeneratedPlanTaskSchema(title="Generic Step", description="No specific node", type="learning", estimated_minutes=25, priority=2)
        assert tool._match_learning_path_node_id(validated=validated, node_refs=refs, task_index=10) == node_b


# ─── CreateTaskTool ──────────────────────────────────────────


class TestCreateTaskTool:
    @pytest.mark.asyncio
    async def test_creates_task_with_defaults(self, db_session, user_id):
        task = _make_task(user_id=uuid4())
        with patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, return_value=task):
            tool = CreateTaskTool()
            params = CreateTaskParams(title="Read Chapter 1")
            result = await tool.execute(params, user_id, db_session)
            assert result.success is True
            assert result.widget_type == "task_card"
            assert result.data["task_id"] == str(task.id)
            assert result.widget_data["entity_card"]["entity_type"] == "task"

    @pytest.mark.asyncio
    async def test_default_estimated_minutes_when_none(self, db_session, user_id):
        with patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, return_value=_make_task()) as mock_create:
            tool = CreateTaskTool()
            params = CreateTaskParams(title="Task", estimated_minutes=None)
            await tool.execute(params, user_id, db_session)
            obj_in = mock_create.call_args.kwargs["obj_in"]
            assert obj_in.estimated_minutes == 30

    @pytest.mark.asyncio
    async def test_explicit_estimated_minutes(self, db_session, user_id):
        with patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, return_value=_make_task()) as mock_create:
            tool = CreateTaskTool()
            params = CreateTaskParams(title="Task", estimated_minutes=45)
            await tool.execute(params, user_id, db_session)
            obj_in = mock_create.call_args.kwargs["obj_in"]
            assert obj_in.estimated_minutes == 45

    @pytest.mark.asyncio
    async def test_error_returns_failure_tool_result(self, db_session, user_id):
        with patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, side_effect=Exception("fail")):
            tool = CreateTaskTool()
            result = await tool.execute(CreateTaskParams(title="Task"), user_id, db_session)
            assert result.success is False
            assert "fail" in result.error_message


# ─── UpdateTaskStatusTool ────────────────────────────────────


class TestUpdateTaskStatusTool:
    @pytest.mark.asyncio
    async def test_routes_in_progress_to_start(self, db_session, user_id):
        task = _make_task()
        with (
            patch("app.tools.task_tools.TaskService.get_by_id", new_callable=AsyncMock, return_value=task),
            patch("app.tools.task_tools.TaskService.start", new_callable=AsyncMock, return_value=_make_task(status=TaskStatus.IN_PROGRESS, started_at=datetime.now(timezone.utc))) as mock_start,
        ):
            tool = UpdateTaskStatusTool()
            params = UpdateTaskStatusParams(task_id=str(task.id), status="in_progress")
            result = await tool.execute(params, user_id, db_session)
            assert result.success is True
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_completed_to_complete(self, db_session, user_id):
        task = _make_task(estimated_minutes=30)
        with (
            patch("app.tools.task_tools.TaskService.get_by_id", new_callable=AsyncMock, return_value=task),
            patch("app.tools.task_tools.TaskService.complete", new_callable=AsyncMock, return_value=_make_task(status=TaskStatus.COMPLETED, actual_minutes=30)) as mock_complete,
        ):
            tool = UpdateTaskStatusTool()
            params = UpdateTaskStatusParams(task_id=str(task.id), status="completed", actual_minutes=30)
            result = await tool.execute(params, user_id, db_session)
            assert result.success is True
            mock_complete.assert_called_once()
            call_kwargs = mock_complete.call_args
            assert call_kwargs.kwargs.get("actual_minutes") == 30 or (len(call_kwargs.args) > 2 and call_kwargs.args[2] == 30)

    @pytest.mark.asyncio
    async def test_completed_uses_estimated_when_no_actual(self, db_session, user_id):
        task = _make_task(estimated_minutes=45)
        with (
            patch("app.tools.task_tools.TaskService.get_by_id", new_callable=AsyncMock, return_value=task),
            patch("app.tools.task_tools.TaskService.complete", new_callable=AsyncMock, return_value=_make_task(status=TaskStatus.COMPLETED, actual_minutes=45)) as mock_complete,
        ):
            tool = UpdateTaskStatusTool()
            params = UpdateTaskStatusParams(task_id=str(task.id), status="completed")
            await tool.execute(params, user_id, db_session)
            call_kwargs = mock_complete.call_args
            actual = call_kwargs.kwargs.get("actual_minutes") or (call_kwargs.args[2] if len(call_kwargs.args) > 2 else None)
            assert actual == 45

    @pytest.mark.asyncio
    async def test_routes_abandoned_to_abandon(self, db_session, user_id):
        task = _make_task()
        with (
            patch("app.tools.task_tools.TaskService.get_by_id", new_callable=AsyncMock, return_value=task),
            patch("app.tools.task_tools.TaskService.abandon", new_callable=AsyncMock, return_value=_make_task(status=TaskStatus.ABANDONED)) as mock_abandon,
        ):
            tool = UpdateTaskStatusTool()
            params = UpdateTaskStatusParams(task_id=str(task.id), status="abandoned")
            result = await tool.execute(params, user_id, db_session)
            assert result.success is True
            mock_abandon.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_pending_to_update(self, db_session, user_id):
        task = _make_task()
        with (
            patch("app.tools.task_tools.TaskService.get_by_id", new_callable=AsyncMock, return_value=task),
            patch("app.tools.task_tools.TaskService.update", new_callable=AsyncMock, return_value=_make_task(status=TaskStatus.PENDING)) as mock_update,
        ):
            tool = UpdateTaskStatusTool()
            params = UpdateTaskStatusParams(task_id=str(task.id), status="pending")
            await tool.execute(params, user_id, db_session)
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_not_found_returns_error(self, db_session, user_id):
        with patch("app.tools.task_tools.TaskService.get_by_id", new_callable=AsyncMock, return_value=None):
            tool = UpdateTaskStatusTool()
            params = UpdateTaskStatusParams(task_id=str(uuid4()), status="completed")
            result = await tool.execute(params, user_id, db_session)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_unrecognized_status_returns_error(self, db_session, user_id):
        task = _make_task(status=TaskStatus.PENDING)
        with (
            patch("app.tools.task_tools.TaskService.get_by_id", new_callable=AsyncMock, return_value=task),
        ):
            tool = UpdateTaskStatusTool()
            params = UpdateTaskStatusParams(task_id=str(task.id), status="unknown_status")
            result = await tool.execute(params, user_id, db_session)
            assert result.success is False
            assert "不支持的状态" in result.error_message

    @pytest.mark.asyncio
    async def test_completed_returns_new_status_in_data(self, db_session, user_id):
        task = _make_task(estimated_minutes=30)
        with (
            patch("app.tools.task_tools.TaskService.get_by_id", new_callable=AsyncMock, return_value=task),
            patch("app.tools.task_tools.TaskService.complete", new_callable=AsyncMock, return_value=_make_task(status=TaskStatus.COMPLETED, actual_minutes=30)),
        ):
            tool = UpdateTaskStatusTool()
            params = UpdateTaskStatusParams(task_id=str(task.id), status="completed", actual_minutes=30)
            result = await tool.execute(params, user_id, db_session)
            assert result.data["new_status"] == "COMPLETED"


# ─── BatchCreateTasksTool ────────────────────────────────────


class TestBatchCreateTasksTool:
    @pytest.mark.asyncio
    async def test_creates_multiple_tasks(self, db_session, user_id):
        call_count = 0

        async def mock_create(db, obj_in, user_id):
            nonlocal call_count
            call_count += 1
            return _make_task(title=obj_in.title, estimated_minutes=obj_in.estimated_minutes)

        with patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, side_effect=mock_create):
            tool = BatchCreateTasksTool()
            params = BatchCreateTasksParams(
                tasks=[
                    CreateTaskParams(title="Task A", estimated_minutes=20),
                    CreateTaskParams(title="Task B", estimated_minutes=30),
                    CreateTaskParams(title="Task C", estimated_minutes=40),
                ]
            )
            result = await tool.execute(params, user_id, db_session)
            assert result.success is True
            assert result.data["task_count"] == 3
            assert result.widget_type == "task_list"
            assert len(result.widget_data["tasks"]) == 3
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_error_returns_failure(self, db_session, user_id):
        with patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, side_effect=Exception("DB error")):
            tool = BatchCreateTasksTool()
            params = BatchCreateTasksParams(tasks=[CreateTaskParams(title="Task")])
            result = await tool.execute(params, user_id, db_session)
            assert result.success is False


# ─── SuggestQuickTaskTool (real DB queries) ──────────────────


class TestSuggestQuickTaskTool:
    @pytest.mark.asyncio
    async def test_finds_pending_task_within_time(self, db_session, test_user, user_id):
        task = Task(
            user_id=test_user.id,
            title="Quick Review",
            type=TaskType.LEARNING,
            estimated_minutes=20,
            priority=3,
            difficulty=2,
            energy_cost=1,
            status=TaskStatus.PENDING,
            tags=[],
        )
        db_session.add(task)
        await db_session.commit()

        tool = SuggestQuickTaskTool()
        params = SuggestQuickTaskParams(available_minutes=25)
        result = await tool.execute(params, user_id, db_session)
        assert result.success is True
        assert result.data["task_id"] == str(task.id)
        assert result.widget_data["task"]["title"] == "Quick Review"

    @pytest.mark.asyncio
    async def test_no_matching_task_returns_error(self, db_session, test_user, user_id):
        task = Task(
            user_id=test_user.id,
            title="Long Task",
            type=TaskType.LEARNING,
            estimated_minutes=60,
            priority=3,
            difficulty=2,
            energy_cost=1,
            status=TaskStatus.PENDING,
            tags=[],
        )
        db_session.add(task)
        await db_session.commit()

        tool = SuggestQuickTaskTool()
        params = SuggestQuickTaskParams(available_minutes=15)
        result = await tool.execute(params, user_id, db_session)
        assert result.success is False
        assert "暂无匹配" in result.error_message

    @pytest.mark.asyncio
    async def test_prefers_higher_priority(self, db_session, test_user, user_id):
        low_task = Task(
            user_id=test_user.id, title="Low Priority", type=TaskType.LEARNING,
            estimated_minutes=20, priority=1, difficulty=1, energy_cost=1,
            status=TaskStatus.PENDING, tags=[],
        )
        high_task = Task(
            user_id=test_user.id, title="High Priority", type=TaskType.LEARNING,
            estimated_minutes=20, priority=5, difficulty=3, energy_cost=2,
            status=TaskStatus.PENDING, tags=[],
        )
        db_session.add_all([low_task, high_task])
        await db_session.commit()

        tool = SuggestQuickTaskTool()
        params = SuggestQuickTaskParams(available_minutes=25)
        result = await tool.execute(params, user_id, db_session)
        assert result.success is True
        assert result.widget_data["task"]["title"] == "High Priority"

    @pytest.mark.asyncio
    async def test_include_in_progress_flag(self, db_session, test_user, user_id):
        in_progress_task = Task(
            user_id=test_user.id, title="In Progress Task", type=TaskType.TRAINING,
            estimated_minutes=15, priority=3, difficulty=2, energy_cost=1,
            status=TaskStatus.IN_PROGRESS, tags=[],
        )
        db_session.add(in_progress_task)
        await db_session.commit()

        tool = SuggestQuickTaskTool()

        params_excluded = SuggestQuickTaskParams(available_minutes=20, include_in_progress=False)
        result_excluded = await tool.execute(params_excluded, user_id, db_session)
        assert result_excluded.success is False

        params_included = SuggestQuickTaskParams(available_minutes=20, include_in_progress=True)
        result_included = await tool.execute(params_included, user_id, db_session)
        assert result_included.success is True
        assert result_included.data["task_id"] == str(in_progress_task.id)

    @pytest.mark.asyncio
    async def test_excludes_completed_and_abandoned(self, db_session, test_user, user_id):
        completed_task = Task(
            user_id=test_user.id, title="Done", type=TaskType.LEARNING,
            estimated_minutes=10, priority=5, difficulty=1, energy_cost=1,
            status=TaskStatus.COMPLETED, tags=[],
        )
        abandoned_task = Task(
            user_id=test_user.id, title="Gave Up", type=TaskType.LEARNING,
            estimated_minutes=10, priority=4, difficulty=1, energy_cost=1,
            status=TaskStatus.ABANDONED, tags=[],
        )
        db_session.add_all([completed_task, abandoned_task])
        await db_session.commit()

        tool = SuggestQuickTaskTool()
        params = SuggestQuickTaskParams(available_minutes=15)
        result = await tool.execute(params, user_id, db_session)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_filters_by_preferred_types(self, db_session, test_user, user_id):
        learning_task = Task(
            user_id=test_user.id, title="Learn X", type=TaskType.LEARNING,
            estimated_minutes=20, priority=5, difficulty=2, energy_cost=1,
            status=TaskStatus.PENDING, tags=[],
        )
        training_task = Task(
            user_id=test_user.id, title="Practice X", type=TaskType.TRAINING,
            estimated_minutes=20, priority=3, difficulty=2, energy_cost=1,
            status=TaskStatus.PENDING, tags=[],
        )
        db_session.add_all([learning_task, training_task])
        await db_session.commit()

        tool = SuggestQuickTaskTool()
        params = SuggestQuickTaskParams(
            available_minutes=25,
            preferred_types=[SchemaTaskType.TRAINING],
        )
        result = await tool.execute(params, user_id, db_session)
        assert result.success is True
        assert result.widget_data["task"]["title"] == "Practice X"


# ─── BreakdownTaskTool ───────────────────────────────────────


class TestBreakdownTaskTool:
    @pytest.mark.asyncio
    async def test_breaks_down_task_successfully(self, db_session, user_id):
        mock_constraints = SimpleNamespace(
            max_session_minutes=45,
            preferred_task_size="medium",
            time_multiplier=1.0,
            require_warmup_task=False,
            to_prompt_block=lambda: "persona block",
        )
        subtasks = [
            {"title": "Step 1: Read", "estimated_minutes": 25, "type": "learning"},
            {"title": "Step 2: Practice", "estimated_minutes": 35, "type": "practice"},
            {"title": "Step 3: Review", "estimated_minutes": 20, "type": "review"},
        ]
        with (
            patch("app.tools.task_tools.PersonaAwarePlanner") as mock_planner_cls,
            patch("app.tools.task_tools.focus_service") as mock_focus,
            patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, side_effect=lambda db, obj_in, user_id: _make_task(title=obj_in.title, type=obj_in.type, estimated_minutes=obj_in.estimated_minutes)),
        ):
            mock_planner_cls.return_value.build_constraints = AsyncMock(return_value=mock_constraints)
            mock_focus.breakdown_task_via_llm = AsyncMock(return_value=subtasks)

            tool = BreakdownTaskTool()
            params = BreakdownTaskParams(title="Final Exam Prep", description="Prepare for finals")
            result = await tool.execute(params, user_id, db_session)
            assert result.success is True
            assert result.data["task_count"] == 3
            assert result.widget_type == "task_list"

    @pytest.mark.asyncio
    async def test_type_mapping_learning(self, db_session, user_id):
        mock_constraints = SimpleNamespace(max_session_minutes=45, preferred_task_size="medium", time_multiplier=1.0, require_warmup_task=False, to_prompt_block=lambda: "")
        subtasks = [{"title": "Read chapter", "estimated_minutes": 25, "type": "learning"}]
        with (
            patch("app.tools.task_tools.PersonaAwarePlanner") as mock_planner_cls,
            patch("app.tools.task_tools.focus_service") as mock_focus,
            patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, side_effect=lambda db, obj_in, user_id: _make_task(title=obj_in.title, type=obj_in.type)) as mock_create,
        ):
            mock_planner_cls.return_value.build_constraints = AsyncMock(return_value=mock_constraints)
            mock_focus.breakdown_task_via_llm = AsyncMock(return_value=subtasks)
            tool = BreakdownTaskTool()
            await tool.execute(BreakdownTaskParams(title="Test"), user_id, db_session)
            obj_in = mock_create.call_args.kwargs["obj_in"]
            assert obj_in.type == TaskType.LEARNING

    @pytest.mark.asyncio
    async def test_type_mapping_practice_to_training(self, db_session, user_id):
        mock_constraints = SimpleNamespace(max_session_minutes=45, preferred_task_size="medium", time_multiplier=1.0, require_warmup_task=False, to_prompt_block=lambda: "")
        subtasks = [{"title": "Do exercises", "estimated_minutes": 30, "type": "practice"}]
        with (
            patch("app.tools.task_tools.PersonaAwarePlanner") as mock_planner_cls,
            patch("app.tools.task_tools.focus_service") as mock_focus,
            patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, side_effect=lambda db, obj_in, user_id: _make_task(title=obj_in.title, type=obj_in.type)) as mock_create,
        ):
            mock_planner_cls.return_value.build_constraints = AsyncMock(return_value=mock_constraints)
            mock_focus.breakdown_task_via_llm = AsyncMock(return_value=subtasks)
            tool = BreakdownTaskTool()
            await tool.execute(BreakdownTaskParams(title="Test"), user_id, db_session)
            obj_in = mock_create.call_args.kwargs["obj_in"]
            assert obj_in.type == TaskType.TRAINING

    @pytest.mark.asyncio
    async def test_type_mapping_review_to_reflection(self, db_session, user_id):
        mock_constraints = SimpleNamespace(max_session_minutes=45, preferred_task_size="medium", time_multiplier=1.0, require_warmup_task=False, to_prompt_block=lambda: "")
        subtasks = [{"title": "Review notes", "estimated_minutes": 20, "type": "review"}]
        with (
            patch("app.tools.task_tools.PersonaAwarePlanner") as mock_planner_cls,
            patch("app.tools.task_tools.focus_service") as mock_focus,
            patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, side_effect=lambda db, obj_in, user_id: _make_task(title=obj_in.title, type=obj_in.type)) as mock_create,
        ):
            mock_planner_cls.return_value.build_constraints = AsyncMock(return_value=mock_constraints)
            mock_focus.breakdown_task_via_llm = AsyncMock(return_value=subtasks)
            tool = BreakdownTaskTool()
            await tool.execute(BreakdownTaskParams(title="Test"), user_id, db_session)
            obj_in = mock_create.call_args.kwargs["obj_in"]
            assert obj_in.type == TaskType.REFLECTION

    @pytest.mark.asyncio
    async def test_empty_subtasks_returns_error(self, db_session, user_id):
        mock_constraints = SimpleNamespace(max_session_minutes=45, preferred_task_size="medium", time_multiplier=1.0, require_warmup_task=False, to_prompt_block=lambda: "")
        with (
            patch("app.tools.task_tools.PersonaAwarePlanner") as mock_planner_cls,
            patch("app.tools.task_tools.focus_service") as mock_focus,
        ):
            mock_planner_cls.return_value.build_constraints = AsyncMock(return_value=mock_constraints)
            mock_focus.breakdown_task_via_llm = AsyncMock(return_value=None)
            tool = BreakdownTaskTool()
            result = await tool.execute(BreakdownTaskParams(title="Test"), user_id, db_session)
            assert result.success is False
            assert "未能生成" in result.error_message

    @pytest.mark.asyncio
    async def test_invalid_subtask_skipped(self, db_session, user_id):
        mock_constraints = SimpleNamespace(max_session_minutes=45, preferred_task_size="medium", time_multiplier=1.0, require_warmup_task=False, to_prompt_block=lambda: "")
        subtasks = [
            {"title": "Valid Task", "estimated_minutes": 25, "type": "learning"},
            {"title": "X", "estimated_minutes": 25, "type": "learning"},
            {"title": "", "estimated_minutes": 25, "type": "learning"},
            {"title": "Bad Type", "estimated_minutes": 25, "type": "unknown_type"},
        ]
        with (
            patch("app.tools.task_tools.PersonaAwarePlanner") as mock_planner_cls,
            patch("app.tools.task_tools.focus_service") as mock_focus,
            patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, side_effect=lambda db, obj_in, user_id: _make_task(title=obj_in.title, type=obj_in.type, estimated_minutes=obj_in.estimated_minutes)),
        ):
            mock_planner_cls.return_value.build_constraints = AsyncMock(return_value=mock_constraints)
            mock_focus.breakdown_task_via_llm = AsyncMock(return_value=subtasks)
            tool = BreakdownTaskTool()
            result = await tool.execute(BreakdownTaskParams(title="Test"), user_id, db_session)
            assert result.success is True
            assert result.data["task_count"] == 2

    @pytest.mark.asyncio
    async def test_max_tasks_limits_output(self, db_session, user_id):
        mock_constraints = SimpleNamespace(max_session_minutes=45, preferred_task_size="medium", time_multiplier=1.0, require_warmup_task=False, to_prompt_block=lambda: "")
        subtasks = [
            {"title": f"Step {i}", "estimated_minutes": 25, "type": "learning"}
            for i in range(8)
        ]
        with (
            patch("app.tools.task_tools.PersonaAwarePlanner") as mock_planner_cls,
            patch("app.tools.task_tools.focus_service") as mock_focus,
            patch("app.tools.task_tools.TaskService.create", new_callable=AsyncMock, side_effect=lambda db, obj_in, user_id: _make_task(title=obj_in.title, type=obj_in.type, estimated_minutes=obj_in.estimated_minutes)),
        ):
            mock_planner_cls.return_value.build_constraints = AsyncMock(return_value=mock_constraints)
            mock_focus.breakdown_task_via_llm = AsyncMock(return_value=subtasks)
            tool = BreakdownTaskTool()
            result = await tool.execute(BreakdownTaskParams(title="Test", max_tasks=3), user_id, db_session)
            assert result.success is True
            assert result.data["task_count"] == 3


# ─── Schema Validation Edge Cases ───────────────────────────


class TestGeneratedPlanTaskSchema:
    def test_valid_task(self):
        task = _GeneratedPlanTaskSchema(title="Learn X", description="desc", type="learning", estimated_minutes=25, priority=2)
        assert task.title == "Learn X"

    def test_title_too_short(self):
        with pytest.raises(Exception):
            _GeneratedPlanTaskSchema(title="A", description="", type="learning", estimated_minutes=25, priority=2)

    def test_title_too_long(self):
        with pytest.raises(Exception):
            _GeneratedPlanTaskSchema(title="X" * 101, description="", type="learning", estimated_minutes=25, priority=2)

    def test_invalid_type(self):
        with pytest.raises(Exception):
            _GeneratedPlanTaskSchema(title="Task", description="", type="invalid_type", estimated_minutes=25, priority=2)

    def test_estimated_below_minimum(self):
        with pytest.raises(Exception):
            _GeneratedPlanTaskSchema(title="Task", description="", type="learning", estimated_minutes=3, priority=2)

    def test_estimated_above_maximum(self):
        with pytest.raises(Exception):
            _GeneratedPlanTaskSchema(title="Task", description="", type="learning", estimated_minutes=100, priority=2)

    def test_priority_below_range(self):
        with pytest.raises(Exception):
            _GeneratedPlanTaskSchema(title="Task", description="", type="learning", estimated_minutes=25, priority=0)

    def test_priority_above_range(self):
        with pytest.raises(Exception):
            _GeneratedPlanTaskSchema(title="Task", description="", type="learning", estimated_minutes=25, priority=6)


class TestBreakdownSubtaskSchema:
    def test_valid_subtask(self):
        sub = _BreakdownSubtaskSchema(title="Read chapter", estimated_minutes=25, type="learning")
        assert sub.title == "Read chapter"

    def test_title_too_short(self):
        with pytest.raises(Exception):
            _BreakdownSubtaskSchema(title="X", estimated_minutes=25, type="learning")

    def test_title_too_long(self):
        with pytest.raises(Exception):
            _BreakdownSubtaskSchema(title="T" * 121, estimated_minutes=25, type="learning")

    def test_invalid_type(self):
        with pytest.raises(Exception):
            _BreakdownSubtaskSchema(title="Task", estimated_minutes=25, type="invalid")

    def test_estimated_out_of_range(self):
        with pytest.raises(Exception):
            _BreakdownSubtaskSchema(title="Task", estimated_minutes=3, type="learning")

    def test_estimated_above_maximum(self):
        with pytest.raises(Exception):
            _BreakdownSubtaskSchema(title="Task", estimated_minutes=95, type="learning")
