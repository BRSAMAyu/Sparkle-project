"""
Task Service
Handle task business logic
"""
from __future__ import annotations
import json
import time
import uuid
from datetime import timezone, datetime
from uuid import UUID

from google.protobuf import json_format
from google.api import annotations_pb2  # noqa: F401
from loguru import logger
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.cache import cache_service
from app.core.event_bus import event_bus
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
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    async def get_by_id(
        db: AsyncSession, task_id: UUID, user_id: UUID
    ) -> Task | None:
        """Get task by ID and verify user ownership"""
        query = select(Task).where(
            and_(Task.id == task_id, Task.user_id == user_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession, obj_in: TaskCreate, user_id: UUID
    ) -> Task:
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
    async def update(
        db: AsyncSession, db_obj: Task, obj_in: TaskUpdate
    ) -> Task:
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
        await event_bus.publish("task.started", event.to_dict())
        await publish_srl_event(
            user_id=db_obj.user_id,
            trigger_event_type="task.started",
            evidence_id=str(db_obj.id),
            metadata={"plan_id": str(db_obj.plan_id) if db_obj.plan_id else None},
        )

        return db_obj

    @staticmethod
    async def start_task(
        db: AsyncSession, task_id: UUID, user_id: UUID
    ) -> Task:
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
        db: AsyncSession, task_id: UUID, user_id: UUID,
        actual_minutes: int, note: str | None = None
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
    async def complete(
        db: AsyncSession, db_obj: Task, actual_minutes: int, note: str | None = None
    ) -> Task:
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

        # Publish task completion event for cognitive analysis
        from app.core.event_bus import TaskCompleted
        from app.models.community import GroupTaskClaim

        estimated = db_obj.estimated_minutes or 0
        completion_rate = actual_minutes / estimated if estimated > 0 else 1.0
        claim_result = await db.execute(
            select(GroupTaskClaim).where(GroupTaskClaim.personal_task_id == db_obj.id)
        )
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
        await event_bus.publish("task.completed", event.to_dict())
        await publish_srl_event(
            user_id=db_obj.user_id,
            trigger_event_type="task.completed",
            evidence_id=str(db_obj.id),
            metadata={"plan_id": str(db_obj.plan_id) if db_obj.plan_id else None},
        )

        return db_obj

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
    async def abandon(
        db: AsyncSession, db_obj: Task, reason: str | None = None
    ) -> Task:
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
        await event_bus.publish("task.abandoned", event.to_dict())
        await publish_srl_event(
            user_id=db_obj.user_id,
            trigger_event_type="task.abandoned",
            evidence_id=str(db_obj.id),
            metadata={"plan_id": str(db_obj.plan_id) if db_obj.plan_id else None},
        )

        return db_obj

    @staticmethod
    async def abandon_task(
        db: AsyncSession, task_id: UUID, user_id: UUID,
        reason: str | None = None
    ) -> Task:
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
    async def confirm_tasks_by_tool_result(
        db: AsyncSession, tool_result_id: str, user_id: UUID
    ) -> list[Task]:
        """
        Confirm all tasks associated with a specific tool_result_id.
        Changes status from PENDING to IN_PROGRESS.

        Note: Uses TaskService.start() to ensure plan state synchronization.
        """
        query = select(Task).where(
            and_(
                Task.tool_result_id == tool_result_id,
                Task.user_id == user_id,
                Task.status == TaskStatus.PENDING
            )
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        if not tasks:
            return []

        current_time = _utcnow()
        confirmed_tasks = []
        for task in tasks:
            # Use TaskService.start() to ensure proper state synchronization
            started_task = await TaskService.start(db, task)
            # Set confirmed_at for tracking purposes
            started_task.confirmed_at = current_time
            db.add(started_task)
            confirmed_tasks.append(started_task)

        await db.commit()
        # Refresh all tasks to get updated fields
        for task in confirmed_tasks:
            await db.refresh(task)

        return confirmed_tasks

    @staticmethod
    async def get_multi(
        db: AsyncSession,
        user_id: UUID,
        query_params: TaskListQuery
    ) -> tuple[list[Task], int]:
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

        return tasks, len(tasks) # This count is wrong for total pages, but for now simple return

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
                            "completed_at": db_obj.completed_at.isoformat()
                            if db_obj.completed_at
                            else None,
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
