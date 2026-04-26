"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

Task Service
Handle task business logic
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from google.api import annotations_pb2  # noqa: F401
from google.protobuf import json_format
from loguru import logger
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.cache import cache_service
from app.core.event_bus import event_bus, event_bus_reliable
from app.event_publishers.srl_events import publish_srl_event
from app.gen.sparkle.inference.v1 import inference_pb2
from app.gen.sparkle.signals.v1 import signals_pb2
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskListQuery, TaskUpdate
from app.services.gateway_client import GatewayClient
from app.services.llm_dispatcher import LLMDispatcher
from app.services.personalization import get_personalization_engine


def _utcnow() -> datetime:
    """Return naive UTC datetime for compatibility with DB TIMESTAMP columns."""
    return datetime.now(UTC).replace(tzinfo=None)


async def _sync_task_card_projection(db: AsyncSession, task: Task) -> None:
    task_id = str(task.id)
    if db.bind is None:
        return

    try:
        from app.services.card_protocol.legacy_adapter import TaskAdapter

        session_factory = async_sessionmaker(db.bind, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as shadow_db:
            shadow_task = await shadow_db.get(Task, task.id)
            if shadow_task is None:
                return
            adapter = TaskAdapter(shadow_db, event_bus)
            await adapter.task_to_card(shadow_task)
            await shadow_db.commit()
    except Exception as exc:
        logger.warning("Task card dual-write failed for {}: {}", task_id, exc)


class TaskService:
    @staticmethod
    async def get_by_id(db: AsyncSession, task_id: UUID, user_id: UUID) -> Task | None:
        """Get task by ID and verify user ownership"""
        query = select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, obj_in: TaskCreate, user_id: UUID) -> Task:
        """Create new task"""
        estimated_minutes = obj_in.estimated_minutes
        difficulty = obj_in.difficulty

        if estimated_minutes is None or difficulty is None:
            try:
                engine = get_personalization_engine(db, cache_service.redis)
                profile = await engine.get_task_plan_profile(user_id)
                if estimated_minutes is None:
                    estimated_minutes = profile.preferred_task_duration
                if difficulty is None:
                    difficulty = TaskService._difficulty_from_gradient(profile.difficulty_gradient)
            except Exception:
                if estimated_minutes is None:
                    estimated_minutes = 25
                if difficulty is None:
                    difficulty = 1

        db_obj = Task(
            user_id=user_id,
            plan_id=obj_in.plan_id,
            title=obj_in.title,
            type=obj_in.type,
            tags=obj_in.tags,
            estimated_minutes=estimated_minutes,
            difficulty=difficulty,
            energy_cost=obj_in.energy_cost,
            guide_content=obj_in.guide_content,
            guide_json=obj_in.guide_json,
            ai_prompt=obj_in.ai_prompt,
            source_planning_session_id=obj_in.source_planning_session_id,
            phase_index=obj_in.phase_index,
            success_criteria=obj_in.success_criteria,
            priority=obj_in.priority,
            due_date=obj_in.due_date,
            knowledge_node_id=obj_in.knowledge_node_id,
            tool_result_id=obj_in.tool_result_id,
            order_index=await TaskService._next_top_order_index(db, user_id),
            status=TaskStatus.PENDING,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await _sync_task_card_projection(db, db_obj)

        # Sync with PlanState if task belongs to a plan
        if db_obj.plan_id:
            try:
                from app.services.task_state_sync import TaskStateSyncService

                sync_service = TaskStateSyncService(db)
                await sync_service.on_task_created(db_obj)
            except Exception as e:
                logger.warning(f"Failed to sync task creation with plan state: {e}")

        return db_obj

    @staticmethod
    async def _next_top_order_index(db: AsyncSession, user_id: UUID) -> int:
        """Allocate a new top-of-list order index while leaving gaps for reordering."""
        min_query = select(func.min(Task.order_index)).where(Task.user_id == user_id)
        min_result = await db.execute(min_query)
        current_min = min_result.scalar_one_or_none()
        if current_min is None:
            return 1000
        return int(current_min) - 1000

    @staticmethod
    async def reorder_tasks(
        db: AsyncSession,
        *,
        user_id: UUID,
        ordered_task_ids: list[UUID],
    ) -> list[Task]:
        """Persist the display order for the provided tasks."""
        unique_ids: list[UUID] = list(dict.fromkeys(ordered_task_ids))
        if not unique_ids:
            return []

        result = await db.execute(
            select(Task).where(
                and_(
                    Task.user_id == user_id,
                    Task.id.in_(unique_ids),
                )
            )
        )
        tasks = result.scalars().all()
        task_map = {task.id: task for task in tasks}

        if len(task_map) != len(unique_ids):
            missing_ids = [str(task_id) for task_id in unique_ids if task_id not in task_map]
            raise ValueError(f"Tasks not found or not owned by user: {', '.join(missing_ids)}")

        for index, task_id in enumerate(unique_ids):
            task_map[task_id].order_index = (index + 1) * 1000

        await db.commit()

        refreshed = await db.execute(
            select(Task)
            .where(
                and_(
                    Task.user_id == user_id,
                    Task.id.in_(unique_ids),
                )
            )
            .order_by(Task.order_index.asc(), desc(Task.created_at))
        )
        return refreshed.scalars().all()

    @staticmethod
    async def update(db: AsyncSession, db_obj: Task, obj_in: TaskUpdate) -> Task:
        """Update task"""
        update_data = obj_in.model_dump(exclude_unset=True)

        # Track status change for sync
        old_status = db_obj.status
        status_changed = "status" in update_data

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await _sync_task_card_projection(db, db_obj)

        # Sync with PlanState if task belongs to a plan and status changed
        if db_obj.plan_id and status_changed:
            try:
                from app.services.task_state_sync import TaskStateSyncService

                sync_service = TaskStateSyncService(db)
                await sync_service.on_task_updated(db_obj, old_status=old_status)
            except Exception as e:
                logger.warning(f"Failed to sync task update with plan state: {e}")

        return db_obj

    @staticmethod
    async def start(db: AsyncSession, db_obj: Task) -> Task:
        """Start task"""
        old_status = db_obj.status
        db_obj.status = TaskStatus.IN_PROGRESS
        db_obj.started_at = _utcnow()

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await _sync_task_card_projection(db, db_obj)

        # Sync with PlanState if task belongs to a plan
        if db_obj.plan_id:
            try:
                from app.services.task_state_sync import TaskStateSyncService

                sync_service = TaskStateSyncService(db)
                await sync_service.on_task_updated(db_obj, old_status=old_status)
            except Exception as e:
                logger.warning(f"Failed to sync task start with plan state: {e}")

        from app.core.event_bus import TaskStartedEvent

        event = TaskStartedEvent(
            user_id=str(db_obj.user_id),
            task_id=str(db_obj.id),
            plan_id=str(db_obj.plan_id) if db_obj.plan_id else None,
        )
        await event_bus_reliable.publish("task.started", event.to_dict())
        await publish_srl_event(
            user_id=db_obj.user_id,
            trigger_event_type="task.started",
            evidence_id=str(db_obj.id),
            metadata={"plan_id": str(db_obj.plan_id) if db_obj.plan_id else None},
        )

        return db_obj

    @staticmethod
    async def start_task(db: AsyncSession, task_id: UUID, user_id: UUID) -> Task:
        """
        Start task by ID - syncs with plan state

        Args:
            db: Database session
            task_id: Task ID to start
            user_id: User ID for ownership verification

        Returns:
            The started task

        Raises:
            NotFoundError: If task not found or doesn't belong to user
        """
        task = await TaskService.get_by_id(db, task_id, user_id)
        if not task:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(message="Task not found")

        return await TaskService.start(db, task)

    @staticmethod
    async def complete_task(
        db: AsyncSession, task_id: UUID, user_id: UUID, actual_minutes: int, note: str | None = None
    ) -> Task:
        """
        Complete task by ID - publishes task.completed event

        This is the preferred method for task completion as it ensures:
        - Task status is updated
        - Plan progress is updated
        - Task state is synced
        - Task completion event is published (triggers AdaptiveReplanner)

        Args:
            db: Database session
            task_id: Task ID to complete
            user_id: User ID for ownership verification
            actual_minutes: Actual time spent on task
            note: Optional user note

        Returns:
            The completed task

        Raises:
            NotFoundError: If task not found or doesn't belong to user
        """
        task = await TaskService.get_by_id(db, task_id, user_id)
        if not task:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(message="Task not found")

        return await TaskService.complete(db, task, actual_minutes, note)

    @staticmethod
    async def apply_focus_progress(
        db: AsyncSession,
        *,
        task_id: UUID,
        user_id: UUID,
        duration_minutes: int,
        started_at: datetime,
    ) -> Task | None:
        """Apply completed focus minutes to a task and finish it when the estimate is reached."""
        if duration_minutes <= 0:
            return await TaskService.get_by_id(db, task_id, user_id)

        task = await TaskService.get_by_id(db, task_id, user_id)
        if not task:
            return None
        if task.status in (TaskStatus.COMPLETED, TaskStatus.ABANDONED):
            return task

        total_minutes = int(task.actual_minutes or 0) + int(duration_minutes)
        estimated_minutes = int(task.estimated_minutes or 0)

        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = task.started_at or started_at

        if estimated_minutes > 0 and total_minutes >= estimated_minutes:
            return await TaskService.complete(
                db,
                task,
                total_minutes,
                note=None,
            )

        task.actual_minutes = total_minutes
        db.add(task)
        await db.flush()
        await _sync_task_card_projection(db, task)
        return task

    @staticmethod
    async def complete(db: AsyncSession, db_obj: Task, actual_minutes: int, note: str | None = None) -> Task:
        """Complete task and update plan progress if task belongs to a plan"""
        db_obj.status = TaskStatus.COMPLETED
        db_obj.completed_at = _utcnow()
        db_obj.actual_minutes = actual_minutes
        if note:
            db_obj.user_note = note

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await _sync_task_card_projection(db, db_obj)

        # P0.2: Auto-update plan progress when task is completed
        if db_obj.plan_id:
            from app.services.plan_service import PlanService

            await PlanService.update_progress(db, db_obj.plan_id, db_obj.user_id)

            # Sync with PlanState
            try:
                from app.services.task_state_sync import TaskStateSyncService

                sync_service = TaskStateSyncService(db)
                await sync_service.on_task_completed(db_obj, actual_minutes)
            except Exception as e:
                logger.warning(f"Failed to sync task completion with plan state: {e}")

            # Append task summary for plan context
            try:
                from app.services.plan_state_service import PlanStateService

                plan_state_service = PlanStateService(db, cache_service.redis)
                summary = TaskService._build_task_summary(db_obj, actual_minutes, note)
                await plan_state_service.append_task_summary(
                    user_id=db_obj.user_id,
                    plan_id=db_obj.plan_id,
                    summary=summary,
                    limit=20,
                )
            except Exception as e:
                logger.warning(f"Failed to append task summary: {e}")

        if db_obj.knowledge_node_id:
            from app.services.galaxy_service import GalaxyService

            study_minutes = actual_minutes or db_obj.estimated_minutes or 15
            galaxy_service = GalaxyService(db)
            try:
                await galaxy_service.spark_node(
                    user_id=db_obj.user_id,
                    node_id=db_obj.knowledge_node_id,
                    study_minutes=study_minutes,
                    task_id=db_obj.id,
                    trigger_expansion=True,
                )
            except Exception as exc:
                logger.warning("Failed to spark node for task {}: {}", db_obj.id, exc)

        task_id_for_log = str(db_obj.id)
        try:
            await TaskService._update_sprint_pack_mastery_for_completed_task(db, db_obj)
        except Exception as exc:
            logger.warning("Failed to update sprint mastery for completed task {}: {}", task_id_for_log, exc)

        # Publish task completion event for cognitive analysis
        from app.core.event_bus import TaskCompleted
        from app.models.community import GroupTaskClaim

        estimated = db_obj.estimated_minutes or 0
        completion_rate = actual_minutes / estimated if estimated > 0 else 1.0
        claim_result = await db.execute(select(GroupTaskClaim).where(GroupTaskClaim.personal_task_id == db_obj.id))
        linked_claim = claim_result.scalar_one_or_none()
        source = "group" if linked_claim else "personal"
        source_metadata = {}
        if linked_claim:
            source_metadata = {
                "group_task_claim_id": str(linked_claim.id),
                "group_task_id": str(linked_claim.group_task_id),
                "group_weight_factor": 0.7,
            }

        event = TaskCompleted(
            user_id=str(db_obj.user_id),
            task_id=str(db_obj.id),
            estimated_minutes=estimated,
            actual_minutes=actual_minutes,
            difficulty=db_obj.difficulty or 1,
            completion_rate=completion_rate,
            user_note=note,
            plan_id=str(db_obj.plan_id) if db_obj.plan_id else None,
            source=source,
            source_metadata=source_metadata,
        )
        await event_bus_reliable.publish("task.completed", event.to_dict())
        try:
            from app.aurora.runtime_v1.self_model import SparkleSelfModelService

            await SparkleSelfModelService(cache_service.redis).record_task_outcome(
                user_id=str(db_obj.user_id),
                signal_id=f"task.completed:{db_obj.id}:{db_obj.completed_at.isoformat() if db_obj.completed_at else actual_minutes}",
                completed=True,
                timed_out=bool(estimated > 0 and actual_minutes > estimated),
                estimated_minutes=estimated,
                actual_minutes=actual_minutes,
                difficulty=db_obj.difficulty,
                source="task.completed",
                reason=note,
            )
        except Exception as exc:
            logger.warning("Failed to update Aurora self model for completed task {}: {}", db_obj.id, exc)
        await publish_srl_event(
            user_id=db_obj.user_id,
            trigger_event_type="task.completed",
            evidence_id=str(db_obj.id),
            metadata={"plan_id": str(db_obj.plan_id) if db_obj.plan_id else None},
        )

        # Lane N: Auto-archive sprint when all tasks are completed
        if db_obj.plan_id:
            try:
                from app.services.exam_sprint_review_service import ExamSprintReviewService

                review_service = ExamSprintReviewService(db=db, redis_client=cache_service.redis)
                await review_service.auto_archive_if_complete(
                    plan_id=db_obj.plan_id,
                    user_id=db_obj.user_id,
                )
            except Exception as exc:
                logger.debug("Sprint auto-archive check skipped for plan {}: {}", db_obj.plan_id, exc)

        return db_obj

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _extract_sprint_pack_node_ids(task: Task) -> list[str]:
        guide_json = TaskService._as_dict(task.guide_json)
        sprint_mode = str(guide_json.get("sprint_mode") or "").strip()

        raw_nodes: list[Any] = []
        for key in ("sprint_pack_nodes", "knowledge_node_ids", "focus_nodes"):
            value = guide_json.get(key)
            if isinstance(value, list):
                raw_nodes.extend(value)

        node_ids: list[str] = []
        for raw in raw_nodes:
            if isinstance(raw, dict):
                candidate = raw.get("node_id") or raw.get("id")
            else:
                candidate = raw
            node_id = str(candidate or "").strip()
            if node_id and "." in node_id:
                node_ids.append(node_id)

        if not sprint_mode and not guide_json.get("path_mode") and not guide_json.get("last_24h_mode"):
            return []
        return list(dict.fromkeys(node_ids))

    @staticmethod
    async def _update_sprint_pack_mastery_for_completed_task(db: AsyncSession, task: Task) -> None:
        node_ids = TaskService._extract_sprint_pack_node_ids(task)
        if not node_ids:
            return

        from app.services.galaxy_service import GalaxyService

        galaxy_service = GalaxyService(db)
        current_states = await galaxy_service.get_sprint_mastery_states(task.user_id, node_ids)
        for node_id in node_ids:
            current_state = current_states.get(node_id, {})
            current_mastery = float(current_state.get("mastery_score", 0.0) or 0.0)
            new_mastery = min(100.0, current_mastery + 25.0)
            if new_mastery <= current_mastery:
                continue
            revision = current_state.get("revision")
            await galaxy_service.update_node_mastery(
                user_id=task.user_id,
                node_id=node_id,
                new_mastery=new_mastery,
                reason="sprint_task_completed",
                request_id=f"sprint_task_completed:{task.id}:{node_id}",
                revision=int(revision) if revision is not None else None,
            )

    @staticmethod
    def _difficulty_from_gradient(gradient: float) -> int:
        if gradient is None:
            return 1
        try:
            mapped = round(1 + max(0.0, min(1.0, gradient)) * 4)
        except Exception:
            return 1
        return max(1, min(5, int(mapped)))

    @staticmethod
    def _build_task_summary(task: Task, actual_minutes: int, note: str | None) -> dict:
        estimated = task.estimated_minutes or 0
        delta = actual_minutes - estimated
        delta_label = "0min" if delta == 0 else f"{'+' if delta > 0 else ''}{delta}min"

        sentiment = TaskService._infer_sentiment(note)

        return {
            "task_id": str(task.id),
            "title": task.title,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "actual_vs_estimated": delta_label,
            "user_sentiment": sentiment,
            "key_takeaway": note if note else None,
        }

    @staticmethod
    def _infer_sentiment(note: str | None) -> str:
        if not note:
            return "neutral"
        lowered = note.lower()
        negative = ["hard", "difficult", "confusing", "stuck", "tough", "frustrated"]
        positive = ["easy", "smooth", "clear", "good", "great", "helpful"]
        if any(word in lowered for word in negative):
            return "negative"
        if any(word in lowered for word in positive):
            return "positive"
        return "neutral"

    @staticmethod
    async def mark_stuck(
        db: AsyncSession,
        db_obj: Task,
        *,
        stuck_point: str | None = None,
        recent_steps: list[str] | None = None,
        current_step_index: int | None = None,
        elapsed_seconds: int | None = None,
        trigger: str | None = None,
    ) -> tuple[Task, dict[str, Any]]:
        """Mark an active task as stuck and ask Aurora for current-state help."""
        if db_obj.status in {TaskStatus.COMPLETED, TaskStatus.ABANDONED}:
            raise ValueError("Completed or abandoned tasks cannot be marked stuck")

        old_status = db_obj.status
        db_obj.status = TaskStatus.STUCK
        if db_obj.started_at is None:
            db_obj.started_at = _utcnow()

        diagnosis = await TaskService._build_stuck_diagnosis(
            db,
            db_obj,
            stuck_point=stuck_point,
            recent_steps=recent_steps or [],
            current_step_index=current_step_index,
            elapsed_seconds=elapsed_seconds,
            trigger=trigger,
        )

        guide_json = dict(TaskService._as_dict(db_obj.guide_json))
        guide_json["stuck_help"] = diagnosis
        guide_json["stuck_runtime"] = {
            "stage": "stuck",
            "stuck_point": stuck_point,
            "recent_steps": recent_steps or [],
            "current_step_index": current_step_index,
            "elapsed_seconds": elapsed_seconds,
            "updated_at": _utcnow().isoformat(),
        }
        db_obj.guide_json = guide_json

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await _sync_task_card_projection(db, db_obj)

        if db_obj.plan_id:
            try:
                from app.services.task_state_sync import TaskStateSyncService

                sync_service = TaskStateSyncService(db)
                await sync_service.on_task_updated(db_obj, old_status=old_status)
            except Exception as e:
                logger.warning(f"Failed to sync task stuck state: {e}")

        from app.core.event_bus import TaskStuckEvent

        event = TaskStuckEvent(
            user_id=str(db_obj.user_id),
            task_id=str(db_obj.id),
            plan_id=str(db_obj.plan_id) if db_obj.plan_id else None,
            stuck_point=stuck_point,
            recent_steps=recent_steps or [],
            elapsed_seconds=elapsed_seconds,
            diagnosis=diagnosis,
        )
        await event_bus_reliable.publish("task.stuck", event.to_dict())
        await publish_srl_event(
            user_id=db_obj.user_id,
            trigger_event_type="task.stuck",
            evidence_id=str(db_obj.id),
            metadata={
                "plan_id": str(db_obj.plan_id) if db_obj.plan_id else None,
                "stuck_point": stuck_point,
                "trigger": trigger,
            },
        )

        return db_obj, diagnosis

    @staticmethod
    async def _build_stuck_diagnosis(
        db: AsyncSession,
        task: Task,
        *,
        stuck_point: str | None,
        recent_steps: list[str],
        current_step_index: int | None,
        elapsed_seconds: int | None,
        trigger: str | None,
    ) -> dict[str, Any]:
        guide_json = TaskService._as_dict(task.guide_json)
        topic = stuck_point or guide_json.get("focus_cue") or task.title
        task_state = TaskService.build_stuck_task_state(
            task,
            stuck_point=stuck_point,
            recent_steps=recent_steps,
            current_step_index=current_step_index,
            elapsed_seconds=elapsed_seconds,
            stuck_topic=str(topic),
        )
        user_message = (
            stuck_point
            or trigger
            or f"我在任务「{task.title}」里卡住了，请先诊断卡点，再给我一个5分钟内能开始的小修复。"
        )

        try:
            from app.aurora.runtime_v1.service import AuroraRuntimeV1Service

            runtime = AuroraRuntimeV1Service()
            plan = await runtime.plan_turn(
                active_db=db,
                user_id=str(task.user_id),
                surface="aurora_planning",
                conversation_id=f"task-stuck:{task.id}",
                request_id=f"task-stuck:{task.id}:{int(time.time())}",
                user_message=user_message,
                request_extra_context={
                    "task_state": task_state,
                    "task_stage": "stuck",
                    "stuck_event": {
                        "task_id": str(task.id),
                        "task_title": task.title,
                        "trigger": trigger,
                        "recent_steps": recent_steps[:10],
                    },
                },
                conversation_context={},
                user_context_payload={},
            )
            message = next((item.strip() for item in plan.messages if str(item).strip()), "")
        except Exception as exc:
            logger.warning("Failed to build Aurora stuck diagnosis for task {}: {}", task.id, exc)
            message = ""

        diagnosis_question = f"你现在最像卡在「{topic}」的哪一处？"
        mistake_diagnosis = message or f"你可能不是整题不会，而是卡在「{topic}」这个断点还没有被定位。"
        targeted_fix = message or "先把卡住的位置写成一句话，再只做下一步最小动作。"
        return {
            "mistake_diagnosis": mistake_diagnosis,
            "one_targeted_fix": targeted_fix,
            "diagnosis_question": diagnosis_question,
            "diagnosis_options": ["概念没想清", "步骤顺序乱了", "题目条件不会用"],
            "targeted_fix": targeted_fix,
            "check_question": "现在只回答：下一步 5 分钟内你能先做哪一个小动作？",
            "source": "aurora_runtime_v1",
            "task_state": task_state,
        }

    @staticmethod
    def build_stuck_task_state(
        task: Task,
        *,
        stuck_point: str | None = None,
        recent_steps: list[str] | None = None,
        current_step_index: int | None = None,
        elapsed_seconds: int | None = None,
        stuck_topic: str | None = None,
    ) -> dict[str, Any]:
        """Build the runtime task_state payload Aurora's stuck rules inspect."""
        guide_json = TaskService._as_dict(task.guide_json)
        runtime = TaskService._as_dict(guide_json.get("stuck_runtime"))
        topic = stuck_topic or stuck_point or runtime.get("stuck_point") or guide_json.get("focus_cue") or task.title
        return {
            "stage": "stuck",
            "status": TaskStatus.STUCK.value,
            "task_id": str(task.id),
            "current_task_id": str(task.id),
            "task_title": task.title,
            "title": task.title,
            "stuck_topic": str(topic),
            "stuck_point": stuck_point or runtime.get("stuck_point"),
            "recent_steps": (recent_steps if recent_steps is not None else runtime.get("recent_steps") or [])[:10],
            "current_step_index": (
                current_step_index if current_step_index is not None else runtime.get("current_step_index")
            ),
            "elapsed_seconds": elapsed_seconds if elapsed_seconds is not None else runtime.get("elapsed_seconds"),
            "estimated_minutes": task.estimated_minutes,
            "success_criteria": task.success_criteria,
        }

    @staticmethod
    async def abandon(db: AsyncSession, db_obj: Task, reason: str | None = None) -> Task:
        """Abandon task"""
        db_obj.status = TaskStatus.ABANDONED
        db_obj.completed_at = _utcnow()  # using completed_at for end time
        if reason:
            db_obj.user_note = f"Abandoned: {reason}"

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await _sync_task_card_projection(db, db_obj)

        # Sync with PlanState if task belongs to a plan
        if db_obj.plan_id:
            try:
                from app.services.task_state_sync import TaskStateSyncService

                sync_service = TaskStateSyncService(db)
                await sync_service.on_task_updated(db_obj, old_status=TaskStatus(db_obj.status) if reason else None)
            except Exception as e:
                logger.warning(f"Failed to sync task abandonment with plan state: {e}")

        # Publish task abandonment event for cognitive analysis
        from app.core.event_bus import TaskAbandoned

        time_spent = None
        if db_obj.started_at:
            time_spent = int((_utcnow() - db_obj.started_at).total_seconds() / 60)

        event = TaskAbandoned(
            user_id=str(db_obj.user_id),
            task_id=str(db_obj.id),
            reason=reason,
            estimated_minutes=db_obj.estimated_minutes,
            time_spent=time_spent,
            plan_id=str(db_obj.plan_id) if db_obj.plan_id else None,
        )
        await event_bus_reliable.publish("task.abandoned", event.to_dict())
        try:
            from app.aurora.runtime_v1.self_model import SparkleSelfModelService

            await SparkleSelfModelService(cache_service.redis).record_task_outcome(
                user_id=str(db_obj.user_id),
                signal_id=f"task.abandoned:{db_obj.id}:{db_obj.completed_at.isoformat() if db_obj.completed_at else time_spent}",
                completed=False,
                timed_out=bool(
                    time_spent is not None
                    and (db_obj.estimated_minutes or 0) > 0
                    and time_spent > int(db_obj.estimated_minutes or 0)
                ),
                estimated_minutes=db_obj.estimated_minutes,
                actual_minutes=time_spent,
                difficulty=db_obj.difficulty,
                source="task.abandoned",
                reason=reason,
            )
        except Exception as exc:
            logger.warning("Failed to update Aurora self model for abandoned task {}: {}", db_obj.id, exc)
        await publish_srl_event(
            user_id=db_obj.user_id,
            trigger_event_type="task.abandoned",
            evidence_id=str(db_obj.id),
            metadata={"plan_id": str(db_obj.plan_id) if db_obj.plan_id else None},
        )

        return db_obj

    @staticmethod
    async def abandon_task(db: AsyncSession, task_id: UUID, user_id: UUID, reason: str | None = None) -> Task:
        """
        Abandon task by ID - publishes task.abandoned event

        This is the preferred method for task abandonment as it ensures:
        - Task status is updated
        - Task state is synced
        - Task abandonment event is published (for cognitive analysis)

        Args:
            db: Database session
            task_id: Task ID to abandon
            user_id: User ID for ownership verification
            reason: Optional reason for abandonment

        Returns:
            The abandoned task

        Raises:
            NotFoundError: If task not found or doesn't belong to user
        """
        task = await TaskService.get_by_id(db, task_id, user_id)
        if not task:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(message="Task not found")

        return await TaskService.abandon(db, task, reason)

    @staticmethod
    async def delete(db: AsyncSession, db_obj: Task) -> None:
        """Delete task"""
        plan_id = db_obj.plan_id
        user_id = db_obj.user_id
        await db.delete(db_obj)
        await db.commit()

        if plan_id:
            try:
                from app.services.plan_service import PlanService

                await PlanService.update_progress(db, plan_id, user_id)
            except Exception as e:
                logger.warning(f"Failed to update plan progress after task deletion: {e}")

    @staticmethod
    async def confirm_tasks_by_tool_result(db: AsyncSession, tool_result_id: str, user_id: UUID) -> list[Task]:
        """
        Confirm all tasks associated with a specific tool_result_id.
        Changes status from PENDING to IN_PROGRESS.

        Note: Uses TaskService.start() to ensure plan state synchronization.
        """
        query = select(Task).where(
            and_(Task.tool_result_id == tool_result_id, Task.user_id == user_id, Task.status == TaskStatus.PENDING)
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        if not tasks:
            return []

        task_ids = [task.id for task in tasks]
        current_time = _utcnow()
        await db.execute(
            update(Task)
            .where(
                and_(
                    Task.id.in_(task_ids),
                    Task.user_id == user_id,
                    Task.status == TaskStatus.PENDING,
                )
            )
            .values(
                status=TaskStatus.IN_PROGRESS,
                started_at=current_time,
                confirmed_at=current_time,
                updated_at=current_time,
            )
        )
        await db.commit()

        confirmed_result = await db.execute(
            select(Task)
            .where(
                and_(
                    Task.id.in_(task_ids),
                    Task.user_id == user_id,
                )
            )
            .order_by(Task.order_index.asc(), desc(Task.created_at))
        )
        confirmed_tasks = confirmed_result.scalars().all()

        sync_service = None
        for task in confirmed_tasks:
            await _sync_task_card_projection(db, task)
            if task.plan_id:
                try:
                    if sync_service is None:
                        from app.services.task_state_sync import TaskStateSyncService

                        sync_service = TaskStateSyncService(db)
                    await sync_service.on_task_updated(task, old_status=TaskStatus.PENDING)
                except Exception as e:
                    logger.warning(f"Failed to sync task confirmation with plan state: {e}")

            from app.core.event_bus import TaskStartedEvent

            event = TaskStartedEvent(
                user_id=str(task.user_id),
                task_id=str(task.id),
                plan_id=str(task.plan_id) if task.plan_id else None,
            )
            await event_bus_reliable.publish("task.started", event.to_dict())
            await publish_srl_event(
                user_id=task.user_id,
                trigger_event_type="task.started",
                evidence_id=str(task.id),
                metadata={"plan_id": str(task.plan_id) if task.plan_id else None},
            )

        return confirmed_tasks

    @staticmethod
    async def get_multi(db: AsyncSession, user_id: UUID, query_params: TaskListQuery) -> tuple[list[Task], int]:
        """Get tasks with filtering and pagination"""
        query = select(Task).where(Task.user_id == user_id)

        # Apply filters
        if query_params.status:
            query = query.where(Task.status == query_params.status)
        if query_params.type:
            query = query.where(Task.type == query_params.type)
        if query_params.plan_id:
            query = query.where(Task.plan_id == query_params.plan_id)

        # Count total (before pagination)
        # Note: simplistic count
        # For better performance on large tables, consider separate count query

        # Apply sorting (default by created_at desc)
        query = query.order_by(desc(Task.created_at))

        # Apply pagination
        offset = (query_params.page - 1) * query_params.page_size
        query = query.offset(offset).limit(query_params.page_size)

        result = await db.execute(query)
        tasks = result.scalars().all()

        return tasks, len(tasks)  # This count is wrong for total pages, but for now simple return

    @staticmethod
    async def _trigger_next_actions(db_obj: Task) -> None:
        idempotency_key = f"{db_obj.user_id}:{db_obj.id}:{int(time.time() // 120)}"
        cache_key = f"signals:idempotency:{idempotency_key}"

        if not cache_service.redis:
            await cache_service.init_redis()
        if cache_service.redis:
            cached = await cache_service.get(cache_key)
            if cached is not None:
                logger.info("Signals push skipped due to idempotency")
                return
            await cache_service.set(cache_key, {"ts": time.time()}, ttl=120)

        request = inference_pb2.InferenceRequest(
            request_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            user_id=str(db_obj.user_id),
            task_type=inference_pb2.PREDICT_NEXT_ACTIONS,
            priority=inference_pb2.P0,
            schema_version="signals_p0_v1",
            output_schema="NextActionsCandidateSet@v1",
            prompt_version="signals_p0_v1",
            idempotency_key=idempotency_key,
            budgets=inference_pb2.Budgets(
                max_output_tokens=256,
                max_cost_level="free_only",
            ),
            messages=[
                inference_pb2.Message(
                    role="user",
                    content=json.dumps(
                        {
                            "task_id": str(db_obj.id),
                            "title": db_obj.title,
                            "type": db_obj.type,
                            "actual_minutes": db_obj.actual_minutes,
                            "completed_at": db_obj.completed_at.isoformat() if db_obj.completed_at else None,
                        },
                        ensure_ascii=True,
                    ),
                )
            ],
        )

        dispatcher = LLMDispatcher()
        response = await dispatcher.run(request)
        if not response.ok or not response.content:
            return

        try:
            content_dict = json.loads(response.content)
        except json.JSONDecodeError:
            logger.warning("Signals response is not valid JSON")
            return

        candidate_set = signals_pb2.NextActionsCandidateSet()
        try:
            json_format.ParseDict(content_dict, candidate_set, ignore_unknown_fields=True)
        except Exception as exc:
            logger.warning(f"Failed to parse NextActionsCandidateSet: {exc}")
            return

        if not candidate_set.request_id:
            candidate_set.request_id = request.request_id
        if not candidate_set.trace_id:
            candidate_set.trace_id = request.trace_id
        if not candidate_set.user_id:
            candidate_set.user_id = request.user_id
        if not candidate_set.schema_version:
            candidate_set.schema_version = request.schema_version
        if not candidate_set.idempotency_key:
            candidate_set.idempotency_key = request.idempotency_key

        if not candidate_set.candidates:
            return

        gateway = GatewayClient()
        await gateway.push_next_actions(candidate_set)
