"""
PlanAdjustmentApplier — Applies adaptive_replanner adjustments to actual task entities.

This bridges the critical gap: AdaptiveReplanner calculates parameter adjustments and
writes them to PlanState.facts, but those adjustments never reach the actual Task
entities that the user sees. This service reads those adjustments and patches the
upcoming tasks accordingly.

Four patch types supported (Phase 1):
1. Time scaling — apply time_multiplier to future task estimated_minutes
2. Difficulty adjustment — apply difficulty_shift to future task difficulty
3. Prerequisite review insertion — insert a short review task before tasks linked to weak nodes
4. Concurrency reduction — mark low-priority future tasks as hidden via plan state metadata
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import and_, select, update

from app.models.task import Task, TaskStatus, TaskType
from app.services.plan_state_service import PlanStateService
from app.services.system_update_service import SystemUpdateService, build_system_update


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PlanAdjustmentResult:
    """Outcome of applying incremental adjustments to a plan's tasks."""

    applied: bool
    plan_id: UUID
    user_id: UUID
    patch_summary: dict[str, Any] = field(default_factory=dict)
    affected_task_ids: list[UUID] = field(default_factory=list)
    inserted_task_ids: list[UUID] = field(default_factory=list)
    hidden_task_ids: list[UUID] = field(default_factory=list)
    user_facing_summary: str = ""
    rollback_snapshot_id: str | None = None
    task_state_snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Only look at tasks due within this window
LOOKAHEAD_DAYS = 3

# Clamp values to prevent runaway adjustments
MIN_ESTIMATED_MINUTES = 5
MAX_ESTIMATED_MINUTES = 480
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 5
MAX_TASKS_TO_PATCH = 10  # Safety limit per adjustment run


class PlanAdjustmentApplier:
    """Reads adaptive_adjustments from PlanState and patches upcoming tasks."""

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.plan_state_service = PlanStateService(db, redis)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def apply_incremental_changes(
        self,
        user_id: UUID,
        plan_id: UUID,
        trigger: str = "auto",
    ) -> PlanAdjustmentResult:
        """Main entry point: read adjustments → patch tasks → record snapshot.

        Returns a PlanAdjustmentResult describing what happened.
        """
        state = await self.plan_state_service.get_plan_state(user_id, plan_id)
        if not state:
            logger.warning("PlanAdjustmentApplier: no plan state for {}/{}", user_id, plan_id)
            return PlanAdjustmentResult(applied=False, plan_id=plan_id, user_id=user_id)

        facts = state.facts or {}
        constraints = state.constraints or {}
        adjustments = facts.get("adaptive_adjustments", {})
        if not adjustments and not self._has_constraint_patches(constraints):
            return PlanAdjustmentResult(applied=False, plan_id=plan_id, user_id=user_id)

        # Fetch upcoming pending tasks
        upcoming = await self._fetch_upcoming_tasks(user_id, plan_id)
        if not upcoming:
            return PlanAdjustmentResult(applied=False, plan_id=plan_id, user_id=user_id)

        snapshot_id = str(uuid4())
        result = PlanAdjustmentResult(
            applied=True,
            plan_id=plan_id,
            user_id=user_id,
            rollback_snapshot_id=snapshot_id,
        )

        # Apply patches in order (as per implementation doc §7.2)
        await self._patch_prerequisite_reviews(
            upcoming, constraints, adjustments, result
        )
        await self._patch_difficulty(
            upcoming, adjustments, result
        )
        await self._patch_time_multiplier(
            upcoming, adjustments, result
        )
        await self._patch_concurrency(
            upcoming, constraints, result
        )

        # Record snapshot for rollback (断点1 Fix #3: include hidden_task_ids)
        if result.affected_task_ids or result.inserted_task_ids or result.hidden_task_ids:
            await self._record_snapshot(
                user_id, plan_id, snapshot_id, trigger, result
            )
            result.user_facing_summary = self._build_user_facing_summary(result)

            # Notify user via system update (low-defense language)
            await self._notify_user(user_id, result)

        await self.db.commit()
        return result

    # -----------------------------------------------------------------------
    # Patch 1: Time multiplier
    # -----------------------------------------------------------------------

    async def _patch_time_multiplier(
        self,
        tasks: list[Task],
        adjustments: dict[str, Any],
        result: PlanAdjustmentResult,
    ) -> None:
        multiplier = adjustments.get("time_multiplier", 1.0)
        if multiplier == 1.0:
            return

        count = 0
        for task in tasks:
            if count >= MAX_TASKS_TO_PATCH:
                break
            if task.id in result.inserted_task_ids:
                continue  # Don't scale tasks we just inserted

            old_minutes = task.estimated_minutes
            new_minutes = self._clamp(
                round(old_minutes * multiplier),
                MIN_ESTIMATED_MINUTES,
                MAX_ESTIMATED_MINUTES,
            )
            if new_minutes != old_minutes:
                self._capture_task_state(result, task)
                task.estimated_minutes = new_minutes
                # Mark as adaptively adjusted
                tags = list(task.tags) if task.tags else []
                if "adaptive_adjusted" not in tags:
                    tags.append("adaptive_adjusted")
                task.tags = tags
                result.affected_task_ids.append(task.id)
                count += 1

        if count:
            result.patch_summary["time_scaled"] = {
                "multiplier": multiplier,
                "tasks_affected": count,
            }

    # -----------------------------------------------------------------------
    # Patch 2: Difficulty shift
    # -----------------------------------------------------------------------

    async def _patch_difficulty(
        self,
        tasks: list[Task],
        adjustments: dict[str, Any],
        result: PlanAdjustmentResult,
    ) -> None:
        shift = adjustments.get("difficulty_shift", 0.0)
        if shift == 0.0:
            return

        count = 0
        for task in tasks:
            if count >= MAX_TASKS_TO_PATCH:
                break
            if task.id in result.inserted_task_ids:
                continue

            old_diff = task.difficulty
            # difficulty_shift is continuous (-0.5 to 0.5), map to integer step
            # Negative shift = easier, positive = harder
            step = round(shift)
            if step == 0:
                # For fractional shifts, apply probabilistic nudge on harder tasks
                if old_diff >= 3 and shift < 0:
                    step = -1
                elif old_diff <= 2 and shift > 0:
                    step = 1
                else:
                    continue

            new_diff = self._clamp(old_diff + step, MIN_DIFFICULTY, MAX_DIFFICULTY)
            if new_diff != old_diff:
                self._capture_task_state(result, task)
                task.difficulty = new_diff
                tags = list(task.tags) if task.tags else []
                if "adaptive_adjusted" not in tags:
                    tags.append("adaptive_adjusted")
                task.tags = tags
                result.affected_task_ids.append(task.id)
                count += 1

        if count:
            result.patch_summary["difficulty_adjusted"] = {
                "shift": shift,
                "tasks_affected": count,
            }

    # -----------------------------------------------------------------------
    # Patch 3: Prerequisite review insertion
    # -----------------------------------------------------------------------

    async def _patch_prerequisite_reviews(
        self,
        tasks: list[Task],
        constraints: dict[str, Any],
        adjustments: dict[str, Any],
        result: PlanAdjustmentResult,
    ) -> None:
        should_insert = constraints.get("insert_prerequisite_review", False)
        weak_node_ids = constraints.get("weak_knowledge_node_ids", [])
        if not should_insert or not weak_node_ids:
            return

        inserted_count = 0
        for task in tasks:
            if inserted_count >= 3:  # Max 3 review insertions per run
                break
            if task.knowledge_node_id is None:
                continue
            if str(task.knowledge_node_id) not in [str(nid) for nid in weak_node_ids]:
                continue
            # This task targets a weak node — insert a review task before it
            review_task = Task(
                user_id=task.user_id,
                plan_id=task.plan_id,
                title=f"前置复习: {task.title}",
                type=TaskType.LEARNING,
                estimated_minutes=10,
                difficulty=max(1, task.difficulty - 1),
                energy_cost=1,
                status=TaskStatus.PENDING,
                priority=task.priority + 1,  # Slightly higher priority
                order_index=task.order_index,  # Same order = before via sorting
                due_date=task.due_date,
                tags=["adaptive_prerequisite_review", "adaptive_adjusted"],
                guide_content="快速复习这个知识点，确保基础扎实后再进入下一个任务。",
            )
            self.db.add(review_task)
            result.inserted_task_ids.append(review_task.id)
            inserted_count += 1

            # Push the original task order back
            self._capture_task_state(result, task)
            task.order_index += 1

        if inserted_count:
            result.patch_summary["prerequisite_reviews_inserted"] = inserted_count

    # -----------------------------------------------------------------------
    # Patch 4: Concurrency reduction / window contraction
    # -----------------------------------------------------------------------

    async def _patch_concurrency(
        self,
        tasks: list[Task],
        constraints: dict[str, Any],
        result: PlanAdjustmentResult,
    ) -> None:
        max_concurrent = constraints.get("max_concurrent_tasks", 0)
        hide_distant = constraints.get("hide_distant_phases", False)

        if max_concurrent <= 0 and not hide_distant:
            return

        # If hiding distant phases, mark tasks beyond top N as hidden
        if hide_distant and max_concurrent > 0:
            # Sort by order_index, keep only top max_concurrent visible
            sorted_tasks = sorted(
                [t for t in tasks if t.id not in result.inserted_task_ids],
                key=lambda t: t.order_index,
            )
            for task in sorted_tasks[max_concurrent:]:
                tags = list(task.tags) if task.tags else []
                if "adaptive_hidden" not in tags:
                    self._capture_task_state(result, task)
                    tags.append("adaptive_hidden")
                    task.tags = tags
                    result.hidden_task_ids.append(task.id)

        if max_concurrent > 0:
            result.patch_summary["max_concurrent_set"] = max_concurrent
        if result.hidden_task_ids:
            result.patch_summary["hidden_tasks"] = len(result.hidden_task_ids)

    # -----------------------------------------------------------------------
    # Snapshot & rollback
    # -----------------------------------------------------------------------

    async def _record_snapshot(
        self,
        user_id: UUID,
        plan_id: UUID,
        snapshot_id: str,
        trigger: str,
        result: PlanAdjustmentResult,
    ) -> None:
        """Record a task-level patch snapshot in PlanState for rollback."""
        now = datetime.now(timezone.utc).isoformat()
        snapshot = {
            "id": snapshot_id,
            "trigger": trigger,
            "created_at": now,
            "patch_summary": result.patch_summary,
            "affected_task_ids": [str(tid) for tid in result.affected_task_ids],
            "inserted_task_ids": [str(tid) for tid in result.inserted_task_ids],
            "hidden_task_ids": [str(tid) for tid in result.hidden_task_ids],
            "task_state_snapshots": dict(result.task_state_snapshots),
        }

        #断点1 Fix #2: Deep-merge — read existing adaptive_meta first to avoid
        # destroying replanner's cooldown/evolution/rollback metadata.
        state = await self.plan_state_service.get_plan_state(user_id, plan_id)
        existing_meta = dict((state.facts or {}).get("adaptive_meta") or {}) if state else {}
        existing_snapshots = list(existing_meta.get("task_patch_snapshots") or [])
        existing_snapshots.append(snapshot)

        merged_meta = dict(existing_meta)
        merged_meta["task_patch_snapshots"] = existing_snapshots

        await self.plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={
                "facts": {
                    "adaptive_meta": merged_meta,
                },
            },
            bump_version=False,  # Don't bump for snapshot metadata
        )

    async def rollback_last_patch(
        self,
        user_id: UUID,
        plan_id: UUID,
    ) -> bool:
        """Roll back the most recent task-level patch.

        Currently supports hiding the review tasks that were inserted and
        restoring original difficulty/time. Full restoration requires
        fetching the snapshot and reversing each change.
        """
        state = await self.plan_state_service.get_plan_state(user_id, plan_id)
        if not state:
            return False

        meta = (state.facts or {}).get("adaptive_meta", {})
        snapshots = meta.get("task_patch_snapshots", [])
        if not snapshots:
            return False

        last = snapshots[-1]
        # Remove inserted review tasks
        inserted_ids = last.get("inserted_task_ids", [])
        if inserted_ids:
            from sqlalchemy import delete
            stmt = delete(Task).where(
                Task.id.in_([UUID(tid) for tid in inserted_ids]),
                Task.tags.contains(["adaptive_prerequisite_review"]),
            )
            await self.db.execute(stmt)

        # Restore original task state (minutes / difficulty / order / tags)
        task_state_snapshots = dict(last.get("task_state_snapshots") or {})
        if task_state_snapshots:
            tasks = await self.db.execute(
                select(Task).where(
                    Task.id.in_([UUID(tid) for tid in task_state_snapshots.keys()])
                )
            )
            for task in tasks.scalars():
                original = task_state_snapshots.get(str(task.id)) or {}
                if "estimated_minutes" in original:
                    task.estimated_minutes = original["estimated_minutes"]
                if "difficulty" in original:
                    task.difficulty = original["difficulty"]
                if "order_index" in original:
                    task.order_index = original["order_index"]
                if "tags" in original:
                    task.tags = list(original["tags"] or [])
        else:
            # Backward-compatible fallback for older snapshots that only track hidden ids.
            hidden_ids = last.get("hidden_task_ids", [])
            if hidden_ids:
                tasks = await self.db.execute(
                    select(Task).where(
                        Task.id.in_([UUID(tid) for tid in hidden_ids])
                    )
                )
                for task in tasks.scalars():
                    tags = list(task.tags) if task.tags else []
                    if "adaptive_hidden" in tags:
                        tags.remove("adaptive_hidden")
                        task.tags = tags

        # Remove the rolled-back snapshot
        snapshots.pop()
        current_meta = dict(meta)
        current_meta["task_patch_snapshots"] = snapshots
        await self.plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={"facts": {"adaptive_meta": current_meta}},
            bump_version=True,
        )

        await self.db.commit()
        logger.info("Rolled back task patch {} for plan {}", last.get("id"), plan_id)
        return True

    # -----------------------------------------------------------------------
    # User notification
    # -----------------------------------------------------------------------

    async def _notify_user(
        self,
        user_id: UUID,
        result: PlanAdjustmentResult,
    ) -> None:
        """Send a low-defense system update about the plan adjustment."""
        summary = result.user_facing_summary
        if not summary:
            return

        await SystemUpdateService(self.redis).enqueue(
            user_id,
            build_system_update(
                update_type="plan_adjustment_applied",
                category="evolution",
                title="路径微调",
                description=summary,
                priority="low",
                metadata={
                    "evolution_kind": "plan_adjustment",
                    "plan_id": str(result.plan_id),
                    "patch_summary": result.patch_summary,
                },
            ),
        )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _build_user_facing_summary(self, result: PlanAdjustmentResult) -> str:
        """Generate user-facing summary using low-defense language."""
        parts = []

        if result.patch_summary.get("prerequisite_reviews_inserted"):
            parts.append("我帮你补了几个关键前置概念，后面会顺很多。")

        if result.patch_summary.get("time_scaled"):
            multiplier = result.patch_summary["time_scaled"]["multiplier"]
            if multiplier > 1.0:
                parts.append("接下来几步的时间安排更贴近真实节奏了。")

        if result.patch_summary.get("difficulty_adjusted"):
            shift = result.patch_summary["difficulty_adjusted"]["shift"]
            if shift < 0:
                parts.append("后续任务的难度收得更平滑了一点。")

        if result.hidden_task_ids:
            parts.append("我把视线外的任务先收起来，只保留最关键的那几步。")

        if not parts:
            return ""

        return " ".join(parts) + " 你可以随时切回原来的安排。"

    def _capture_task_state(
        self,
        result: PlanAdjustmentResult,
        task: Task,
    ) -> None:
        """Capture a task's original state once so rollback can fully restore it."""
        key = str(task.id)
        if key in result.task_state_snapshots:
            return
        result.task_state_snapshots[key] = {
            "estimated_minutes": task.estimated_minutes,
            "difficulty": task.difficulty,
            "order_index": task.order_index,
            "tags": list(task.tags) if task.tags else [],
        }

    async def _fetch_upcoming_tasks(
        self,
        user_id: UUID,
        plan_id: UUID,
    ) -> list[Task]:
        """Fetch pending, uncompleted tasks due within the lookahead window."""
        cutoff = date.today() + timedelta(days=LOOKAHEAD_DAYS)
        stmt = (
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.plan_id == plan_id,
                Task.status == TaskStatus.PENDING,
                # Include tasks with no due date OR due within window
                (Task.due_date == None) | (Task.due_date <= cutoff),  # noqa: E711
            )
            .order_by(Task.order_index, Task.due_date)
            .limit(MAX_TASKS_TO_PATCH + 3)  # A bit extra for insertion room
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _has_constraint_patches(self, constraints: dict[str, Any]) -> bool:
        """Check if constraints contain values that should trigger task patches."""
        return bool(
            constraints.get("insert_prerequisite_review", False)
            or constraints.get("max_concurrent_tasks", 0) > 0
            or constraints.get("hide_distant_phases", False)
        )

    @staticmethod
    def _clamp(value: int, low: int, high: int) -> int:
        return max(low, min(high, value))
