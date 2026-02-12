"""
Tests for PlanContextBuilder and merge_plan_context

Tests plan context building and injection into ContextPack.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.plan_context import PlanContextBuilder, merge_plan_context
from app.models.plan_state import PlanState, PlanStateStatus


def _mock_db_without_plan():
    db = AsyncMock()
    plan_result = MagicMock()
    plan_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=plan_result)
    return db


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def plan_id():
    return uuid4()


@pytest.fixture
def mock_plan_state(user_id, plan_id):
    """Create a mock PlanState for testing"""
    now = datetime.now(timezone.utc)
    return PlanState(
        id=uuid4(),
        plan_id=plan_id,
        user_id=user_id,
        facts={"difficulty_preference": 0.7, "learning_style": "visual"},
        milestones=[
            {"id": "ms-1", "title": "First milestone", "achieved_at": now.isoformat()},
            {"id": "ms-2", "title": "Second milestone", "achieved_at": now.isoformat()},
        ],
        task_index={
            "total": 20,
            "completed": 15,
            "avg_completion_rate": 0.75,
            "by_type": {
                "LEARNING": {"total": 10, "completed": 8},
                "TRAINING": {"total": 10, "completed": 7},
            },
        },
        feedback_log=[
            {"type": "difficulty", "content": "too easy", "timestamp": now.isoformat()},
        ],
        constraints={"max_session_minutes": 30},
        version=3,
        status=PlanStateStatus.ACTIVE.value,
        created_at=now,
        updated_at=now,
    )


class TestPlanContextBuilder:
    """Tests for PlanContextBuilder"""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_plan_id(self, user_id):
        """Should return empty dict when plan_id is None"""
        mock_db = _mock_db_without_plan()
        builder = PlanContextBuilder(mock_db)

        result = await builder.build(user_id, plan_id=None)

        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_when_state_not_found(self, user_id, plan_id):
        """Should return empty dict when PlanState not found"""
        mock_db = _mock_db_without_plan()

        with patch(
            "app.core.plan_context.PlanStateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_plan_state = AsyncMock(return_value=None)

            builder = PlanContextBuilder(mock_db)
            result = await builder.build(user_id, plan_id)

        assert result == {}

    @pytest.mark.asyncio
    async def test_builds_context_with_facts(self, user_id, plan_id, mock_plan_state):
        """Should include facts in context"""
        mock_db = _mock_db_without_plan()

        with patch(
            "app.core.plan_context.PlanStateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_plan_state = AsyncMock(return_value=mock_plan_state)

            builder = PlanContextBuilder(mock_db)
            result = await builder.build(user_id, plan_id)

        assert "facts" in result
        assert result["facts"]["difficulty_preference"] == 0.7
        assert result["facts"]["learning_style"] == "visual"

    @pytest.mark.asyncio
    async def test_builds_context_with_task_summary(self, user_id, plan_id, mock_plan_state):
        """Should include task_summary in context"""
        mock_db = _mock_db_without_plan()

        with patch(
            "app.core.plan_context.PlanStateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_plan_state = AsyncMock(return_value=mock_plan_state)

            builder = PlanContextBuilder(mock_db)
            result = await builder.build(user_id, plan_id, include_task_index=True)

        assert "task_summary" in result
        assert result["task_summary"]["total"] == 20
        assert result["task_summary"]["completed"] == 15
        assert result["task_summary"]["avg_completion_rate"] == 0.75

    @pytest.mark.asyncio
    async def test_builds_context_with_milestones(self, user_id, plan_id, mock_plan_state):
        """Should include truncated milestones"""
        mock_db = _mock_db_without_plan()

        with patch(
            "app.core.plan_context.PlanStateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_plan_state = AsyncMock(return_value=mock_plan_state)

            builder = PlanContextBuilder(mock_db)
            result = await builder.build(user_id, plan_id, max_milestones=5)

        assert "milestones" in result
        assert len(result["milestones"]) == 2
        assert result["milestones"][0]["title"] == "First milestone"

    @pytest.mark.asyncio
    async def test_excludes_feedback_by_default(self, user_id, plan_id, mock_plan_state):
        """Should not include feedback_log by default"""
        mock_db = _mock_db_without_plan()

        with patch(
            "app.core.plan_context.PlanStateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_plan_state = AsyncMock(return_value=mock_plan_state)

            builder = PlanContextBuilder(mock_db)
            result = await builder.build(user_id, plan_id, include_feedback_log=False)

        assert "recent_feedback" not in result

    @pytest.mark.asyncio
    async def test_includes_feedback_when_requested(self, user_id, plan_id, mock_plan_state):
        """Should include feedback_log when requested"""
        mock_db = _mock_db_without_plan()

        with patch(
            "app.core.plan_context.PlanStateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_plan_state = AsyncMock(return_value=mock_plan_state)

            builder = PlanContextBuilder(mock_db)
            result = await builder.build(user_id, plan_id, include_feedback_log=True)

        assert "recent_feedback" in result
        assert len(result["recent_feedback"]) == 1


class TestMergePlanContext:
    """Tests for merge_plan_context function"""

    def test_returns_user_context_when_no_plan(self):
        """Should return user_context unchanged when plan_context is empty"""
        user_context = {"preferences": {"depth": 0.5}}

        result = merge_plan_context(user_context, {})

        assert result == user_context

    def test_adds_plan_context_section(self):
        """Should add plan_context as a separate section"""
        user_context = {"preferences": {"depth": 0.5}}
        plan_context = {"plan_id": "test-123", "facts": {}}

        result = merge_plan_context(user_context, plan_context)

        assert "plan_context" in result
        assert result["plan_context"]["plan_id"] == "test-123"

    def test_overrides_preferences_with_plan_facts(self):
        """Should override user preferences with plan-level facts"""
        user_context = {"preferences": {"difficulty_preference": 0.3}}
        plan_context = {
            "plan_id": "test-123",
            "facts": {"difficulty_preference": 0.8},
        }

        result = merge_plan_context(user_context, plan_context)

        assert result["preferences"]["difficulty_preference"] == 0.8

    def test_preserves_user_preferences_not_in_plan(self):
        """Should preserve user preferences not overridden by plan"""
        user_context = {
            "preferences": {
                "depth": 0.5,
                "curiosity": 0.7,
            }
        }
        plan_context = {
            "plan_id": "test-123",
            "facts": {"session_length_preference": 25},
        }

        result = merge_plan_context(user_context, plan_context)

        assert result["preferences"]["depth"] == 0.5
        assert result["preferences"]["curiosity"] == 0.7
