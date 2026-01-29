"""
PlanStateService - 计划状态管理服务

Provides plan-level state management with Redis caching.
Implements the PlanScope layer as defined in docs/state/plan_state_spec.md.

Features:
- Redis-first read with DB fallback
- Optimistic locking via version field
- Automatic cache invalidation on updates
- Support for archiving and state promotion

Usage:
    from app.services.plan_state_service import PlanStateService

    service = PlanStateService(db, redis)
    state = await service.get_plan_state(user_id, plan_id)
    await service.upsert_plan_state(user_id, plan_id, {"facts": {"difficulty_preference": 0.7}})
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan_state import PlanState, PlanStateStatus

# Cache configuration
PLAN_STATE_CACHE_TTL = 3600  # 1 hour
PLAN_STATE_CACHE_PREFIX = "state:plan:"


class PlanStateService:
    """
    PlanStateService - 计划状态管理服务

    Design principles:
    1. Redis-first read: Check cache before hitting DB
    2. DB-first write: Write to DB, then update cache
    3. User isolation: All operations scoped to user_id
    4. Version control: Optimistic locking for concurrent updates
    """

    def __init__(
        self,
        db: AsyncSession,
        redis=None,
        cache_ttl: int = PLAN_STATE_CACHE_TTL,
    ):
        self.db = db
        self.redis = redis
        self.cache_ttl = cache_ttl

    # ==================== Read Operations ====================

    async def get_plan_state(
        self,
        user_id: UUID,
        plan_id: UUID,
        refresh: bool = False,
    ) -> PlanState | None:
        """
        Get plan state with Redis caching.

        Args:
            user_id: Owner user ID (for permission check)
            plan_id: Plan ID to get state for
            refresh: If True, bypass cache and read from DB

        Returns:
            PlanState or None if not found
        """
        cache_key = self._cache_key(plan_id)

        # Try cache first (unless refresh requested)
        if not refresh and self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    state = PlanState.from_dict(data)
                    # Verify user ownership
                    if state.user_id == user_id:
                        logger.debug(
                            f"Plan state cache hit: plan_id={plan_id}"
                        )
                        return state
                    else:
                        logger.warning(
                            f"Plan state user mismatch: expected={user_id}, cached={state.user_id}"
                        )
                        # Don't return mismatched state, fall through to DB
            except Exception as e:
                logger.warning(f"Plan state cache read failed: {e}")

        # Read from DB
        result = await self.db.execute(
            select(PlanState).where(
                PlanState.plan_id == plan_id,
                PlanState.user_id == user_id,
                PlanState.deleted_at.is_(None),
            )
        )
        state = result.scalar_one_or_none()

        if state is None:
            return None

        # Update cache
        await self._set_cache(state)

        return state

    async def get_active_plan_states(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[PlanState]:
        """
        Get all active plan states for a user.

        Args:
            user_id: Owner user ID
            limit: Maximum number of states to return

        Returns:
            List of active PlanState records
        """
        result = await self.db.execute(
            select(PlanState)
            .where(
                PlanState.user_id == user_id,
                PlanState.status == PlanStateStatus.ACTIVE.value,
                PlanState.deleted_at.is_(None),
            )
            .order_by(PlanState.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ==================== Write Operations ====================

    async def get_or_create_plan_state(
        self,
        user_id: UUID,
        plan_id: UUID,
        initial_facts: dict[str, Any] | None = None,
        initial_constraints: dict[str, Any] | None = None,
        for_write: bool = True,
    ) -> PlanState:
        """
        Get existing plan state or create a new one.

        Args:
            user_id: Owner user ID
            plan_id: Plan ID
            initial_facts: Initial facts for new state
            initial_constraints: Initial constraints for new state
            for_write: If True, bypass cache to get session-tracked object

        Returns:
            Existing or newly created PlanState (always session-tracked)
        """
        # For write operations, always get a session-tracked object from DB
        # to avoid detached instance issues with cached objects
        existing = await self.get_plan_state(user_id, plan_id, refresh=for_write)
        if existing:
            return existing

        # Create new state
        state = PlanState(
            plan_id=plan_id,
            user_id=user_id,
            facts=initial_facts or {},
            milestones=[],
            task_index={"total": 0, "completed": 0, "by_type": {}},
            task_summaries=[],
            feedback_log=[],
            constraints=initial_constraints or {},
            version=1,
            status=PlanStateStatus.ACTIVE.value,
        )
        self.db.add(state)
        await self.db.commit()
        await self.db.refresh(state)

        # Update cache
        await self._set_cache(state)

        logger.info(
            f"Created plan state: plan_id={plan_id}, user_id={user_id}"
        )
        return state

    async def upsert_plan_state(
        self,
        user_id: UUID,
        plan_id: UUID,
        patch: dict[str, Any],
        bump_version: bool = True,
    ) -> PlanState | None:
        """
        Update plan state with patch.

        Supports partial updates to JSON fields:
        - facts: Merged with existing facts
        - milestones: Appended to existing list
        - task_index: Merged with existing index
        - feedback_log: Appended to existing log
        - constraints: Merged with existing constraints

        Args:
            user_id: Owner user ID
            plan_id: Plan ID
            patch: Dictionary of fields to update
            bump_version: If True, increment version number

        Returns:
            Updated PlanState or None if not found
        """
        state = await self.get_or_create_plan_state(user_id, plan_id)

        # Apply patches to JSON fields
        if "facts" in patch:
            current_facts = state.facts or {}
            current_facts.update(patch["facts"])
            state.facts = current_facts

        if "milestones" in patch:
            current_milestones = state.milestones or []
            if isinstance(patch["milestones"], list):
                current_milestones.extend(patch["milestones"])
            else:
                current_milestones.append(patch["milestones"])
            state.milestones = current_milestones

        if "task_index" in patch:
            current_index = state.task_index or {}
            self._deep_merge(current_index, patch["task_index"])
            state.task_index = current_index

        if "task_summaries" in patch:
            summaries = patch["task_summaries"]
            if isinstance(summaries, list):
                state.task_summaries = summaries

        if "feedback_log" in patch:
            current_log = state.feedback_log or []
            if isinstance(patch["feedback_log"], list):
                current_log.extend(patch["feedback_log"])
            else:
                current_log.append(patch["feedback_log"])
            state.feedback_log = current_log

        if "constraints" in patch:
            current_constraints = state.constraints or {}
            current_constraints.update(patch["constraints"])
            state.constraints = current_constraints

        if "status" in patch:
            state.status = patch["status"]

        if "archived_at" in patch:
            state.archived_at = patch["archived_at"]

        # P0-2: Handle consecutive_rejection_count direct update
        if "consecutive_rejection_count" in patch:
            state.consecutive_rejection_count = patch["consecutive_rejection_count"]

        # Bump version if requested
        if bump_version:
            state.version = (state.version or 0) + 1

        state.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(state)

        # Update cache
        await self._set_cache(state)

        logger.info(
            f"Updated plan state: plan_id={plan_id}, version={state.version}"
        )
        return state

    async def archive_plan_state(
        self,
        user_id: UUID,
        plan_id: UUID,
    ) -> PlanState | None:
        """
        Archive a plan state.

        Sets status to 'archived' and records archived_at timestamp.
        Does not delete the state - it remains queryable.

        Args:
            user_id: Owner user ID
            plan_id: Plan ID

        Returns:
            Archived PlanState or None if not found
        """
        # Bypass cache to get session-tracked object for write operation
        state = await self.get_plan_state(user_id, plan_id, refresh=True)
        if state is None:
            return None

        state.status = PlanStateStatus.ARCHIVED.value
        state.archived_at = datetime.utcnow()
        state.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(state)

        # Invalidate cache (archived states shouldn't be cached)
        await self.invalidate_plan_cache(plan_id)

        logger.info(
            f"Archived plan state: plan_id={plan_id}"
        )
        return state

    async def append_task_summary(
        self,
        user_id: UUID,
        plan_id: UUID,
        summary: dict[str, Any],
        limit: int = 20,
    ) -> PlanState | None:
        """
        Append a task summary to PlanState.task_summaries.

        Keeps the newest summaries first and trims to a fixed size.
        """
        state = await self.get_or_create_plan_state(user_id, plan_id)
        summaries = state.task_summaries or []
        summaries.insert(0, summary)
        if len(summaries) > limit:
            summaries = summaries[:limit]
        state.task_summaries = summaries
        state.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(state)
        await self._set_cache(state)

        logger.debug(
            f"Appended task summary: plan_id={plan_id}, count={len(summaries)}"
        )
        return state

    # ==================== Task Event Handlers ====================

    async def on_task_completed(
        self,
        user_id: UUID,
        plan_id: UUID,
        task_id: UUID,
        task_type: str,
        actual_minutes: int | None = None,
    ) -> tuple[PlanState | None, list[dict[str, Any]]]:
        """
        Handle task completion event.

        Updates task_index and checks for milestone triggers.

        Args:
            user_id: Owner user ID
            plan_id: Plan ID
            task_id: Completed task ID
            task_type: Task type (LEARNING, TRAINING, etc.)
            actual_minutes: Actual time spent

        Returns:
            Tuple of (Updated PlanState, List of new milestones)
        """
        state = await self.get_or_create_plan_state(user_id, plan_id)

        # Update task_index
        task_index = state.task_index or {"total": 0, "completed": 0, "by_type": {}}
        task_index["completed"] = task_index.get("completed", 0) + 1
        task_index["last_completed_task_id"] = str(task_id)

        # Update by_type
        by_type = task_index.get("by_type", {})
        type_stats = by_type.get(task_type, {"total": 0, "completed": 0})
        type_stats["completed"] = type_stats.get("completed", 0) + 1
        by_type[task_type] = type_stats
        task_index["by_type"] = by_type

        # Update completion rate
        total = task_index.get("total", 0)
        completed = task_index.get("completed", 0)
        if total > 0:
            task_index["avg_completion_rate"] = round(completed / total, 3)

        # Update avg_task_duration if actual_minutes provided
        facts = state.facts or {}
        if actual_minutes:
            current_avg = facts.get("avg_task_duration_minutes", 0)
            if current_avg > 0 and completed > 1:
                # Weighted average
                new_avg = ((current_avg * (completed - 1)) + actual_minutes) / completed
                facts["avg_task_duration_minutes"] = round(new_avg, 1)
            else:
                facts["avg_task_duration_minutes"] = actual_minutes

        # Check for milestone triggers
        milestones = state.milestones or []
        new_milestones = self._check_milestone_triggers(task_index, milestones)

        # Apply updates
        updated_state = await self.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={
                "task_index": task_index,
                "facts": facts,
                "milestones": new_milestones,
            },
            bump_version=True,
        )
        return updated_state, new_milestones

    async def on_milestone_triggered(
        self,
        user_id: UUID,
        plan_id: UUID,
        milestone: dict[str, Any],
        pending_task_count: int,
    ) -> None:
        """
        Handle milestone trigger event.

        Args:
            user_id: User ID
            plan_id: Plan ID
            milestone: The milestone data
            pending_task_count: Number of pending tasks
        """
        # This is a hook for future state updates related to milestones
        # e.g. recording the event in a timeline or history
        logger.info(f"Milestone triggered: {milestone.get('id')} for plan {plan_id}")

    async def on_task_created(
        self,
        user_id: UUID,
        plan_id: UUID,
        task_type: str,
    ) -> PlanState | None:
        """
        Handle task creation event.

        Updates task_index total counts.

        Args:
            user_id: Owner user ID
            plan_id: Plan ID
            task_type: Task type

        Returns:
            Updated PlanState
        """
        state = await self.get_or_create_plan_state(user_id, plan_id)

        task_index = state.task_index or {"total": 0, "completed": 0, "by_type": {}}
        task_index["total"] = task_index.get("total", 0) + 1

        by_type = task_index.get("by_type", {})
        type_stats = by_type.get(task_type, {"total": 0, "completed": 0})
        type_stats["total"] = type_stats.get("total", 0) + 1
        by_type[task_type] = type_stats
        task_index["by_type"] = by_type

        return await self.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={"task_index": task_index},
            bump_version=True,
        )

    async def append_feedback(
        self,
        user_id: UUID,
        plan_id: UUID,
        feedback_type: str,
        content: str,
        task_id: UUID | None = None,
        applied_adjustment: dict[str, Any] | None = None,
    ) -> PlanState | None:
        """
        Append feedback to feedback_log.

        Args:
            user_id: Owner user ID
            plan_id: Plan ID
            feedback_type: Type of feedback (e.g., "task_difficulty")
            content: Feedback content
            task_id: Related task ID (optional)
            applied_adjustment: Adjustment applied based on feedback

        Returns:
            Updated PlanState
        """
        import uuid

        feedback_entry = {
            "id": f"fb-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.utcnow().isoformat(),
            "type": feedback_type,
            "content": content,
        }
        if task_id:
            feedback_entry["task_id"] = str(task_id)
        if applied_adjustment:
            feedback_entry["applied_adjustment"] = applied_adjustment

        return await self.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={"feedback_log": feedback_entry},
            bump_version=True,
        )

    async def replace_feedback_log(
        self,
        user_id: UUID,
        plan_id: UUID,
        feedback_log: list[dict[str, Any]],
        bump_version: bool = True,
    ) -> PlanState | None:
        """
        Replace feedback_log entries for a plan state.

        Args:
            user_id: Owner user ID
            plan_id: Plan ID
            feedback_log: Full feedback list to persist
            bump_version: Whether to increment version

        Returns:
            Updated PlanState or None
        """
        state = await self.get_or_create_plan_state(user_id, plan_id)
        state.feedback_log = feedback_log
        if bump_version:
            state.version = (state.version or 0) + 1
        state.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(state)
        await self._set_cache(state)
        return state

    # ==================== Cache Operations ====================

    async def invalidate_plan_cache(self, plan_id: UUID) -> None:
        """
        Invalidate cache for a plan state.

        Args:
            plan_id: Plan ID to invalidate
        """
        if not self.redis:
            return

        cache_key = self._cache_key(plan_id)
        try:
            await self.redis.delete(cache_key)
            logger.debug(f"Invalidated plan state cache: plan_id={plan_id}")
        except Exception as e:
            logger.warning(f"Failed to invalidate plan state cache: {e}")

    # ==================== Private Methods ====================

    def _cache_key(self, plan_id: UUID) -> str:
        """Generate cache key for plan state."""
        return f"{PLAN_STATE_CACHE_PREFIX}{plan_id}"

    async def _set_cache(self, state: PlanState) -> None:
        """Set plan state in cache."""
        if not self.redis:
            return

        cache_key = self._cache_key(state.plan_id)
        try:
            data = json.dumps(state.to_dict(), ensure_ascii=False, default=str)
            await self.redis.setex(cache_key, self.cache_ttl, data)
            logger.debug(
                f"Set plan state cache: plan_id={state.plan_id}, ttl={self.cache_ttl}"
            )
        except Exception as e:
            logger.warning(f"Failed to set plan state cache: {e}")

    def _deep_merge(self, base: dict, overlay: dict) -> None:
        """Deep merge overlay into base dict."""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _check_milestone_triggers(
        self,
        task_index: dict[str, Any],
        existing_milestones: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Check if any milestone triggers should fire.

        Returns list of new milestones to add.
        """

        new_milestones = []
        completed = task_index.get("completed", 0)
        existing_ids = {m.get("id") for m in existing_milestones}

        # Milestone: First 10 tasks
        if completed >= 10 and "ms-first-10-tasks" not in existing_ids:
            new_milestones.append({
                "id": "ms-first-10-tasks",
                "title": "Completed first 10 tasks",
                "achieved_at": datetime.utcnow().isoformat(),
                "tasks_completed": completed,
            })

        # Milestone: 25 tasks
        if completed >= 25 and "ms-25-tasks" not in existing_ids:
            new_milestones.append({
                "id": "ms-25-tasks",
                "title": "Completed 25 tasks",
                "achieved_at": datetime.utcnow().isoformat(),
                "tasks_completed": completed,
            })

        # Milestone: 50 tasks
        if completed >= 50 and "ms-50-tasks" not in existing_ids:
            new_milestones.append({
                "id": "ms-50-tasks",
                "title": "Completed 50 tasks",
                "achieved_at": datetime.utcnow().isoformat(),
                "tasks_completed": completed,
            })

        # Milestone: 25% completion
        total = task_index.get("total", 0)
        rate = task_index.get("avg_completion_rate", 0)
        if total >= 10 and rate >= 0.25 and "ms-25pct-completion" not in existing_ids:
            new_milestones.append({
                "id": "ms-25pct-completion",
                "title": "Reached 25% completion rate",
                "achieved_at": datetime.utcnow().isoformat(),
                "completion_rate": rate,
            })

        # Milestone: 50% completion
        if total >= 10 and rate >= 0.5 and "ms-50pct-completion" not in existing_ids:
            new_milestones.append({
                "id": "ms-50pct-completion",
                "title": "Reached 50% completion rate",
                "achieved_at": datetime.utcnow().isoformat(),
                "completion_rate": rate,
            })

        # Milestone: 75% completion
        if total >= 10 and rate >= 0.75 and "ms-75pct-completion" not in existing_ids:
            new_milestones.append({
                "id": "ms-75pct-completion",
                "title": "Reached 75% completion rate",
                "achieved_at": datetime.utcnow().isoformat(),
                "completion_rate": rate,
            })

        return new_milestones
