"""
Tests for PlanStateService

Tests cover:
- get_plan_state: Cache hit, cache miss, refresh
- upsert_plan_state: Create, update, version bump
- archive_plan_state: Status change, cache invalidation
- on_task_completed: Task index update, milestone triggers
- append_feedback: Feedback log append
"""
import json
import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Import all models to ensure relationships are resolved
import app.models  # noqa: F401

from app.services.plan_state_service import (
    PlanStateService,
    PLAN_STATE_CACHE_PREFIX,
    PLAN_STATE_CACHE_TTL,
)
from app.models.plan_state import PlanState, PlanStateStatus


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def service(mock_db, mock_redis):
    """Create a PlanStateService with mocked dependencies."""
    return PlanStateService(mock_db, mock_redis)


@pytest.fixture
def sample_plan_state():
    """Create a sample PlanState for testing."""
    user_id = uuid4()
    plan_id = uuid4()
    return PlanState(
        id=uuid4(),
        plan_id=plan_id,
        user_id=user_id,
        facts={"difficulty_preference": 0.6},
        milestones=[],
        task_index={"total": 10, "completed": 5, "by_type": {}},
        feedback_log=[],
        constraints={},
        version=3,
        status=PlanStateStatus.ACTIVE.value,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )


class TestGetPlanState:
    """Tests for get_plan_state method."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_state(
        self, service, mock_redis, sample_plan_state
    ):
        """When cache contains valid state, return it without DB query."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id

        # Setup cache hit
        mock_redis.get.return_value = json.dumps(
            sample_plan_state.to_dict(), default=str
        )

        result = await service.get_plan_state(user_id, plan_id)

        # Verify cache was checked
        cache_key = f"{PLAN_STATE_CACHE_PREFIX}{plan_id}"
        mock_redis.get.assert_called_once_with(cache_key)

        # Verify DB was not queried
        assert not service.db.execute.called

        # Verify result
        assert result is not None
        assert result.plan_id == plan_id
        assert result.version == 3

    @pytest.mark.asyncio
    async def test_cache_miss_queries_db(
        self, service, mock_db, mock_redis, sample_plan_state
    ):
        """When cache misses, query DB and update cache."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id

        # Setup cache miss
        mock_redis.get.return_value = None

        # Setup DB response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_plan_state
        mock_db.execute.return_value = mock_result

        result = await service.get_plan_state(user_id, plan_id)

        # Verify cache was checked
        mock_redis.get.assert_called_once()

        # Verify DB was queried
        mock_db.execute.assert_called_once()

        # Verify cache was updated
        mock_redis.setex.assert_called_once()

        # Verify result
        assert result is not None
        assert result.plan_id == plan_id

    @pytest.mark.asyncio
    async def test_refresh_bypasses_cache(
        self, service, mock_db, mock_redis, sample_plan_state
    ):
        """When refresh=True, bypass cache and query DB directly."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id

        # Setup cache (should be bypassed)
        mock_redis.get.return_value = json.dumps(
            sample_plan_state.to_dict(), default=str
        )

        # Setup DB response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_plan_state
        mock_db.execute.return_value = mock_result

        result = await service.get_plan_state(user_id, plan_id, refresh=True)

        # Verify cache was NOT checked
        mock_redis.get.assert_not_called()

        # Verify DB was queried
        mock_db.execute.assert_called_once()

        # Verify result
        assert result is not None

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, service, mock_db, mock_redis):
        """When state doesn't exist, return None."""
        user_id = uuid4()
        plan_id = uuid4()

        # Setup cache miss
        mock_redis.get.return_value = None

        # Setup DB returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_plan_state(user_id, plan_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_user_mismatch_falls_through_to_db(
        self, service, mock_db, mock_redis, sample_plan_state
    ):
        """When cached state belongs to different user, query DB."""
        different_user_id = uuid4()
        plan_id = sample_plan_state.plan_id

        # Setup cache with different user
        mock_redis.get.return_value = json.dumps(
            sample_plan_state.to_dict(), default=str
        )

        # Setup DB returns None (state not found for this user)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_plan_state(different_user_id, plan_id)

        # Verify DB was queried after cache mismatch
        mock_db.execute.assert_called_once()
        assert result is None


class TestUpsertPlanState:
    """Tests for upsert_plan_state method."""

    @pytest.mark.asyncio
    async def test_creates_new_state_if_not_exists(self, service, mock_db, mock_redis):
        """When state doesn't exist, create new one."""
        user_id = uuid4()
        plan_id = uuid4()

        # Setup: no existing state
        mock_redis.get.return_value = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock the created state returned by refresh
        new_state = PlanState(
            id=uuid4(),
            plan_id=plan_id,
            user_id=user_id,
            facts={"test": "value"},
            milestones=[],
            task_index={"total": 0, "completed": 0, "by_type": {}},
            feedback_log=[],
            constraints={},
            version=1,
            status=PlanStateStatus.ACTIVE.value,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )

        # Return the new state on refresh calls
        async def mock_refresh(obj):
            obj.id = new_state.id
            obj.version = 1
            obj.created_at = _utcnow()
            obj.updated_at = _utcnow()

        mock_db.refresh.side_effect = mock_refresh

        result = await service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={"facts": {"test": "value"}},
        )

        # Verify state was added to DB
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_merges_facts(self, service, mock_db, mock_redis, sample_plan_state):
        """Patch should merge into existing facts."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id

        # Setup existing state
        mock_redis.get.return_value = json.dumps(
            sample_plan_state.to_dict(), default=str
        )

        # Patch with new fact
        update_patch = {"facts": {"new_key": "new_value"}}

        # Mock get_or_create to return sample state
        with patch(
            "app.services.plan_state_service.PlanStateService.get_or_create_plan_state",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = sample_plan_state

            await service.upsert_plan_state(user_id, plan_id, update_patch)

            # Verify facts were merged
            assert "difficulty_preference" in sample_plan_state.facts
            assert "new_key" in sample_plan_state.facts
            assert sample_plan_state.facts["new_key"] == "new_value"

    @pytest.mark.asyncio
    async def test_bumps_version_by_default(
        self, service, mock_db, mock_redis, sample_plan_state
    ):
        """Version should be incremented by default."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id
        original_version = sample_plan_state.version

        with patch.object(
            service, "get_or_create_plan_state", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = sample_plan_state

            await service.upsert_plan_state(
                user_id, plan_id, patch={"facts": {"x": 1}}
            )

            assert sample_plan_state.version == original_version + 1

    @pytest.mark.asyncio
    async def test_appends_to_feedback_log(
        self, service, mock_db, mock_redis, sample_plan_state
    ):
        """Feedback log entries should be appended."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id
        sample_plan_state.feedback_log = [{"id": "fb-1", "type": "old"}]

        with patch.object(
            service, "get_or_create_plan_state", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = sample_plan_state

            await service.upsert_plan_state(
                user_id,
                plan_id,
                patch={"feedback_log": {"id": "fb-2", "type": "new"}},
            )

            assert len(sample_plan_state.feedback_log) == 2
            assert sample_plan_state.feedback_log[1]["id"] == "fb-2"


class TestArchivePlanState:
    """Tests for archive_plan_state method."""

    @pytest.mark.asyncio
    async def test_sets_archived_status(
        self, service, mock_db, mock_redis, sample_plan_state
    ):
        """Archive should set status to 'archived'."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id

        with patch.object(
            service, "get_plan_state", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = sample_plan_state

            result = await service.archive_plan_state(user_id, plan_id)

            assert result.status == PlanStateStatus.ARCHIVED.value
            assert result.archived_at is not None

    @pytest.mark.asyncio
    async def test_invalidates_cache(
        self, service, mock_db, mock_redis, sample_plan_state
    ):
        """Archive should invalidate cache."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id

        with patch.object(
            service, "get_plan_state", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = sample_plan_state

            await service.archive_plan_state(user_id, plan_id)

            # Verify cache was invalidated
            mock_redis.delete.assert_called_once()


class TestOnTaskCompleted:
    """Tests for on_task_completed method."""

    @pytest.mark.asyncio
    async def test_updates_task_index(
        self, service, mock_db, mock_redis, sample_plan_state
    ):
        """Task completion should update task_index."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id
        task_id = uuid4()

        sample_plan_state.task_index = {
            "total": 10,
            "completed": 5,
            "by_type": {"LEARNING": {"total": 10, "completed": 5}},
        }

        with patch.object(
            service, "get_or_create_plan_state", new_callable=AsyncMock
        ) as mock_get, patch.object(
            service, "upsert_plan_state", new_callable=AsyncMock
        ) as mock_upsert:
            mock_get.return_value = sample_plan_state
            mock_upsert.return_value = sample_plan_state

            await service.on_task_completed(
                user_id=user_id,
                plan_id=plan_id,
                task_id=task_id,
                task_type="LEARNING",
                actual_minutes=25,
            )

            # Verify upsert was called with updated task_index
            mock_upsert.assert_called_once()
            call_args = mock_upsert.call_args
            patch_arg = call_args.kwargs["patch"]
            assert patch_arg["task_index"]["completed"] == 6
            assert str(task_id) in patch_arg["task_index"]["last_completed_task_id"]

    @pytest.mark.asyncio
    async def test_triggers_milestone(
        self, service, mock_db, mock_redis, sample_plan_state
    ):
        """Completing 10th task should trigger milestone."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id
        task_id = uuid4()

        sample_plan_state.task_index = {
            "total": 15,
            "completed": 9,  # Will become 10
            "by_type": {},
        }
        sample_plan_state.milestones = []

        with patch.object(
            service, "get_or_create_plan_state", new_callable=AsyncMock
        ) as mock_get, patch.object(
            service, "upsert_plan_state", new_callable=AsyncMock
        ) as mock_upsert:
            mock_get.return_value = sample_plan_state
            mock_upsert.return_value = sample_plan_state

            await service.on_task_completed(
                user_id=user_id,
                plan_id=plan_id,
                task_id=task_id,
                task_type="LEARNING",
            )

            call_args = mock_upsert.call_args
            patch_arg = call_args.kwargs["patch"]

            # Verify milestone was triggered
            assert len(patch_arg["milestones"]) > 0
            assert patch_arg["milestones"][0]["id"] == "ms-first-10-tasks"

    @pytest.mark.asyncio
    async def test_returns_tuple_with_milestones(
        self, service, mock_db, mock_redis, sample_plan_state
    ):
        """on_task_completed should return (state, new_milestones)."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id
        task_id = uuid4()
        
        sample_plan_state.task_index = {"total": 10, "completed": 9}
        # This will trigger 10-tasks milestone
        
        with patch.object(
            service, "get_or_create_plan_state", new_callable=AsyncMock
        ) as mock_get, patch.object(
            service, "upsert_plan_state", new_callable=AsyncMock
        ) as mock_upsert:
            mock_get.return_value = sample_plan_state
            mock_upsert.return_value = sample_plan_state
            
            result = await service.on_task_completed(
                user_id=user_id,
                plan_id=plan_id,
                task_id=task_id,
                task_type="LEARNING"
            )
            
            assert isinstance(result, tuple)
            assert len(result) == 2
            state, milestones = result
            assert state == sample_plan_state
            
            milestone_ids = [m["id"] for m in milestones]
            assert "ms-first-10-tasks" in milestone_ids


class TestAppendFeedback:
    """Tests for append_feedback method."""

    @pytest.mark.asyncio
    async def test_appends_feedback_entry(
        self, service, mock_db, mock_redis, sample_plan_state
    ):
        """Feedback should be appended to feedback_log."""
        user_id = sample_plan_state.user_id
        plan_id = sample_plan_state.plan_id

        with patch.object(
            service, "upsert_plan_state", new_callable=AsyncMock
        ) as mock_upsert:
            mock_upsert.return_value = sample_plan_state

            await service.append_feedback(
                user_id=user_id,
                plan_id=plan_id,
                feedback_type="task_difficulty",
                content="Too hard",
                applied_adjustment={"difficulty_preference": -0.1},
            )

            mock_upsert.assert_called_once()
            call_args = mock_upsert.call_args
            patch_arg = call_args.kwargs["patch"]

            feedback = patch_arg["feedback_log"]
            assert feedback["type"] == "task_difficulty"
            assert feedback["content"] == "Too hard"
            assert "applied_adjustment" in feedback


class TestCacheOperations:
    """Tests for cache-related operations."""

    @pytest.mark.asyncio
    async def test_invalidate_deletes_cache_key(self, service, mock_redis):
        """Invalidate should delete the cache key."""
        plan_id = uuid4()

        await service.invalidate_plan_cache(plan_id)

        expected_key = f"{PLAN_STATE_CACHE_PREFIX}{plan_id}"
        mock_redis.delete.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_cache_set_uses_correct_ttl(
        self, service, mock_redis, sample_plan_state
    ):
        """Cache set should use configured TTL."""
        await service._set_cache(sample_plan_state)

        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == PLAN_STATE_CACHE_TTL

    @pytest.mark.asyncio
    async def test_no_redis_operations_without_redis(self, mock_db, sample_plan_state):
        """When Redis is None, no cache operations should occur."""
        service = PlanStateService(mock_db, redis=None)

        # These should not raise
        await service.invalidate_plan_cache(sample_plan_state.plan_id)
        await service._set_cache(sample_plan_state)

        # No assertions needed - just verify no exceptions


class TestMilestoneLogic:
    """Tests for milestone trigger logic."""

    def test_first_10_tasks_milestone(self, service):
        """First 10 tasks milestone should trigger at 10 completed."""
        task_index = {"total": 15, "completed": 10}
        existing = []

        new_milestones = service._check_milestone_triggers(task_index, existing)

        assert len(new_milestones) == 1
        assert new_milestones[0]["id"] == "ms-first-10-tasks"

    def test_no_duplicate_milestones(self, service):
        """Already achieved milestones should not be duplicated."""
        task_index = {"total": 15, "completed": 12}
        existing = [{"id": "ms-first-10-tasks"}]

        new_milestones = service._check_milestone_triggers(task_index, existing)

        # Should not include first-10-tasks again
        assert not any(m["id"] == "ms-first-10-tasks" for m in new_milestones)

    def test_50_percent_completion_milestone(self, service):
        """50% completion milestone should trigger when rate >= 0.5."""
        task_index = {
            "total": 20,
            "completed": 10,
            "avg_completion_rate": 0.5,
        }
        existing = []

        new_milestones = service._check_milestone_triggers(task_index, existing)

        assert any(m["id"] == "ms-50pct-completion" for m in new_milestones)
