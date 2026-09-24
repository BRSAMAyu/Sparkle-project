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

from app.core.action_plan import clear_action_plan
from app.core.cache import cache_service
from app.core.event_bus import event_bus, event_bus_reliable
from app.event_publishers.srl_events import publish_srl_event
from app.gen.sparkle.inference.v1 import inference_pb2
from app.gen.sparkle.signals.v1 import signals_pb2
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.task import TaskCreate, TaskListQuery, TaskUpdate
from app.services.gateway_client import GatewayClient
from app.services.llm_dispatcher import LLMDispatcher
from app.services.personalization import get_personalization_engine
from app.services.task_document_service import task_document_service


def _utcnow() -> datetime:
    """Return naive UTC datetime for compatibility with DB TIMESTAMP columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def _is_mock_session(db: AsyncSession) -> bool:
    return db.__class__.__module__.startswith("unittest.mock")


# ── FSM Transition Map (R1A4-P2-2) ──────────────────────────────────
_VALID_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.ABANDONED}),
    TaskStatus.IN_PROGRESS: frozenset({
        TaskStatus.COMPLETED, TaskStatus.PAUSED, TaskStatus.STUCK, TaskStatus.ABANDONED,
    }),
    TaskStatus.PAUSED: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.ABANDONED}),
    TaskStatus.STUCK: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.ABANDONED}),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.ABANDONED: frozenset(),
}


def _validate_transition(current: TaskStatus, target: TaskStatus) -> None:
    """Raise ValueError if *current* -> *target* is not in the transition map."""
    allowed = _VALID_TRANSITIONS.get(current)
    if allowed is None:
        raise ValueError(f"Unknown current status: {current!r}")
    if target not in allowed:
        raise ValueError(
            f"Invalid state transition: {current.value} -> {target.value}"
        )


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
    # ── PLAN-LINK · 手动任务默认关联计划（plan→task 关联链补齐）─────────────
    # 背景（P1-4 遗留 / LOOP1 C1b）：手动创建的任务不带 plan_id，脱离计划域，
    # 按计划维度的进度聚合（计划完成率 / 里程碑视图）对其不可见。
    # 裁决（创建时上下文决定归属）：active sprint plan 存续期手动建的学习任务
    # 默认关联它；无 sprint plan 回落 goal plan（goal 分解产出的计划）；两者皆无
    # 保持 NULL——不强行造计划。多计划并存时取 is_primary 优先、创建最新
    # （对齐 community_service 群任务→个人任务的既有默认关联先例）。
    # 显式语义边界：TaskCreate 显式传 plan_id=null（fields_set 含 plan_id）视为
    # 「明确不关联」（card_protocol 单卡导入等依赖此语义），不做默认解析。
    # UI 现无「不关联」选择器（mobile task_create_screen 仅 plan 深链带 planId），
    # 计划选择器/豁免开关属 UI 后续（见 v3-output/PLAN-LINK/REPORT.md）。
    _DEFAULT_LINK_TASK_TYPES: frozenset[TaskType] = frozenset(
        {
            TaskType.LEARNING,
            TaskType.TRAINING,
            TaskType.ERROR_FIX,
            TaskType.REFLECTION,
        }
    )

    @staticmethod
    async def resolve_default_plan_id(db: AsyncSession, user_id: UUID, task_type: TaskType) -> UUID | None:
        """Resolve the plan a manually created learning task should default to.

        sprint plan 优先，无则 goal plan（goal_id 非空的活跃计划），无则 None。
        解析失败不阻断创建（兜底正确优先）：调用方须 catch 后保持 NULL。
        """
        if task_type not in TaskService._DEFAULT_LINK_TASK_TYPES:
            return None

        from app.models.plan import Plan, PlanType

        async def _pick(*conditions) -> UUID | None:
            query = (
                select(Plan.id)
                .where(Plan.user_id == user_id, Plan.deleted_at.is_(None), *conditions)
                .order_by(desc(Plan.is_primary), desc(Plan.created_at))
                .limit(1)
            )
            result = await db.execute(query)
            return result.scalar_one_or_none()

        # 1) active sprint plan 优先
        sprint_plan_id = await _pick(Plan.type == PlanType.SPRINT, Plan.is_active.is_(True))
        if sprint_plan_id is not None:
            return sprint_plan_id
        # 2) goal plan（goal 分解产出的计划）回落
        return await _pick(Plan.goal_id.isnot(None), Plan.is_active.is_(True))

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

        plan_id = obj_in.plan_id
        if plan_id is None and "plan_id" not in obj_in.model_fields_set:
            # PLAN-LINK：未显式声明 plan 归属的创建 → 学习型任务默认关联
            try:
                plan_id = await TaskService.resolve_default_plan_id(db, user_id, obj_in.type)
            except Exception as exc:  # noqa: BLE001 — 关联失败不阻断任务创建（保持 NULL 可观测）
                logger.warning("PLAN-LINK default plan resolution failed for user {}: {}", user_id, exc)
                plan_id = None

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
            plan_id=plan_id,
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
        # X-01 · ActionPlan V3：整块写入结构化契约列（DTO 已在 parse 时全量校验）
        if obj_in.action_plan is not None:
            obj_in.action_plan.to_contract().apply_to_task(db_obj)
        db.add(db_obj)
        await db.flush()
        if not _is_mock_session(db):
            await task_document_service.auto_link_from_task_context(db, task=db_obj, linked_by="ai")
        await db.commit()
        await db.refresh(db_obj)
        if not _is_mock_session(db):
            try:
                from app.services.focus_context_service import focus_context_service

                await focus_context_service.preload_for_task(
                    db,
                    user_id=db_obj.user_id,
                    task=db_obj,
                    seed_query=db_obj.title,
                )
            except Exception as exc:
                logger.warning("Focus context warmup failed after task create {}: {}", db_obj.id, exc)
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

        # X-01 · ActionPlan V3：action_plan 是契约块，不走逐列 setattr；
        # 显式传 null（fields_set 含 action_plan 且值为 None）= 清除 V3 语义回到 legacy。
        if "action_plan" in obj_in.model_fields_set:
            if obj_in.action_plan is None:
                clear_action_plan(db_obj)
            else:
                obj_in.action_plan.to_contract().apply_to_task(db_obj)
        update_data.pop("action_plan", None)

        # Track status change for sync
        old_status = db_obj.status
        status_changed = "status" in update_data

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.flush()
        if not _is_mock_session(db):
            await task_document_service.auto_link_from_task_context(db, task=db_obj, linked_by="ai")
        await db.commit()
        await db.refresh(db_obj)
        if not _is_mock_session(db):
            try:
                from app.services.focus_context_service import focus_context_service

                await focus_context_service.invalidate_for_task(user_id=db_obj.user_id, task_id=db_obj.id)
            except Exception as exc:
                logger.warning("Focus context invalidation failed after task update {}: {}", db_obj.id, exc)
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
        _validate_transition(db_obj.status, TaskStatus.IN_PROGRESS)
        old_status = db_obj.status
        db_obj.status = TaskStatus.IN_PROGRESS
        db_obj.started_at = db_obj.started_at or _utcnow()

        db.add(db_obj)
        if not _is_mock_session(db):
            try:
                # X-04：Focus 是 optional capability——缺席时优雅降级（跳过预载，
                # action 流照常），不做无差别裸 try/except
                from app.services.task_optional_capabilities import focus_preload_available

                if await focus_preload_available(db):
                    from app.services.focus_context_service import focus_context_service

                    await focus_context_service.preload_for_task(
                        db,
                        user_id=db_obj.user_id,
                        task=db_obj,
                        seed_query=db_obj.title,
                    )
            except Exception as exc:
                logger.warning("Focus context preload failed for task {}: {}", db_obj.id, exc)
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
            due_at=db_obj.due_date.isoformat() if db_obj.due_date else None,
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
    async def pause(db: AsyncSession, db_obj: Task, reason: str | None = None) -> Task:
        """Pause a task without marking it as a success or failure."""
        _validate_transition(db_obj.status, TaskStatus.PAUSED)

        old_status = db_obj.status
        paused_at = _utcnow()
        guide_json = dict(db_obj.guide_json or {})
        pause_state = dict(guide_json.get("pause_state") or {})
        pause_count = int(pause_state.get("paused_count") or 0) + 1
        pause_state.update(
            {
                "paused_at": paused_at.isoformat(),
                "reason": reason,
                "paused_count": pause_count,
                "resumed_at": None,
            }
        )
        guide_json["pause_state"] = pause_state
        db_obj.status = TaskStatus.PAUSED
        db_obj.guide_json = guide_json
        db_obj.paused_at = paused_at
        if reason:
            db_obj.paused_reason = reason
            db_obj.user_note = f"Paused: {reason}"

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
                logger.warning(f"Failed to sync task pause with plan state: {e}")

        event_payload = {
            "event_type": "task.paused",
            "user_id": str(db_obj.user_id),
            "task_id": str(db_obj.id),
            "plan_id": str(db_obj.plan_id) if db_obj.plan_id else None,
            "reason": reason,
            "paused_count": pause_count,
            "timestamp": paused_at.isoformat(),
        }
        await event_bus_reliable.publish("task.paused", event_payload)
        try:
            from app.signals.outcome_tracker import OutcomeTracker

            await OutcomeTracker(cache_service.redis).record_actual_for_user(
                user_id=str(db_obj.user_id),
                actual_outcome={
                    "task_id": str(db_obj.id),
                    "plan_id": str(db_obj.plan_id) if db_obj.plan_id else None,
                    "paused": True,
                    "paused_count": pause_count,
                    "completed": None,
                    "user_responded": True,
                    "behavior_changed": True,
                },
                exclude_context={"task_id": str(db_obj.id)},
            )
        except Exception as exc:
            logger.warning("Failed to record neutral paused outcome for task {}: {}", db_obj.id, exc)
        await publish_srl_event(
            user_id=db_obj.user_id,
            trigger_event_type="task.paused",
            evidence_id=str(db_obj.id),
            metadata={
                "plan_id": str(db_obj.plan_id) if db_obj.plan_id else None,
                "reason": reason,
                "paused_count": pause_count,
            },
        )
        return db_obj

    @staticmethod
    async def pause_task(db: AsyncSession, task_id: UUID, user_id: UUID, reason: str | None = None) -> Task:
        """Pause task by ID and verify user ownership."""
        task = await TaskService.get_by_id(db, task_id, user_id)
        if not task:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(message="Task not found")
        return await TaskService.pause(db, task, reason)

    @staticmethod
    async def resume(db: AsyncSession, db_obj: Task) -> Task:
        """Resume a paused or stuck task."""
        _validate_transition(db_obj.status, TaskStatus.IN_PROGRESS)

        old_status = db_obj.status
        resumed_at = _utcnow()
        guide_json = dict(db_obj.guide_json or {})
        pause_state = dict(guide_json.get("pause_state") or {})
        # X-04：累计暂停时长（actual = 起止差 − 暂停区间 的真源积累）
        total_paused = int(pause_state.get("total_paused_seconds") or 0)
        paused_at_raw = pause_state.get("paused_at")
        if isinstance(paused_at_raw, str):
            try:
                paused_start = datetime.fromisoformat(paused_at_raw)
                if paused_start.tzinfo is not None:
                    paused_start = paused_start.replace(tzinfo=None)
                segment = (resumed_at - paused_start).total_seconds()
                if segment > 0:
                    total_paused += int(segment)
            except ValueError:
                pass
        pause_state["total_paused_seconds"] = total_paused
        pause_state["resumed_at"] = resumed_at.isoformat()
        guide_json["pause_state"] = pause_state

        # Record recovery from stuck if applicable.
        if old_status == TaskStatus.STUCK:
            stuck_recovery = dict(guide_json.get("stuck_recovery") or {})
            stuck_recovery["recovered_at"] = resumed_at.isoformat()
            stuck_recovery["previous_status"] = TaskStatus.STUCK.value
            guide_json["stuck_recovery"] = stuck_recovery

        db_obj.status = TaskStatus.IN_PROGRESS
        db_obj.started_at = db_obj.started_at or resumed_at
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
                logger.warning(f"Failed to sync task resume with plan state: {e}")

        event_type = "task.resumed_from_stuck" if old_status == TaskStatus.STUCK else "task.resumed"
        await event_bus_reliable.publish(
            event_type,
            {
                "event_type": event_type,
                "user_id": str(db_obj.user_id),
                "task_id": str(db_obj.id),
                "plan_id": str(db_obj.plan_id) if db_obj.plan_id else None,
                "previous_status": old_status.value,
                "timestamp": resumed_at.isoformat(),
            },
        )
        await publish_srl_event(
            user_id=db_obj.user_id,
            trigger_event_type=event_type,
            evidence_id=str(db_obj.id),
            metadata={"plan_id": str(db_obj.plan_id) if db_obj.plan_id else None},
        )
        return db_obj

    @staticmethod
    async def resume_task(db: AsyncSession, task_id: UUID, user_id: UUID) -> Task:
        """Resume paused task by ID and verify user ownership."""
        task = await TaskService.get_by_id(db, task_id, user_id)
        if not task:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(message="Task not found")
        return await TaskService.resume(db, task)

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
        db: AsyncSession,
        task_id: UUID,
        user_id: UUID,
        actual_minutes: int | None,
        note: str | None = None,
        route_history_decision_id: str | None = None,
        routing_outcome_signal_id: str | None = None,
        routing_trace_id: str | None = None,
        evidence: list[dict[str, Any]] | None = None,
        evidence_source: str = "user",
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
            actual_minutes: **Measured** actual time spent (X-04: None → derived
                from real start/end timestamps; NEVER backfilled from estimated)
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

        return await TaskService.complete(
            db,
            task,
            actual_minutes,
            note,
            route_history_decision_id=route_history_decision_id,
            routing_outcome_signal_id=routing_outcome_signal_id,
            routing_trace_id=routing_trace_id,
            evidence=evidence,
            evidence_source=evidence_source,
        )

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
            # X-04：focus 计时器触发的自动完成——证据来源标记 focus_auto，
            # 无附带证据时回落 system_event（focus timer 不等于学习成果，低信任打型）
            return await TaskService.complete(
                db,
                task,
                total_minutes,
                note=None,
                evidence_source="focus_auto",
            )

        task.actual_minutes = total_minutes
        db.add(task)
        await db.flush()
        await _sync_task_card_projection(db, task)
        return task

    @staticmethod
    async def complete(
        db: AsyncSession,
        db_obj: Task,
        actual_minutes: int | None = None,
        note: str | None = None,
        route_history_decision_id: str | None = None,
        routing_outcome_signal_id: str | None = None,
        routing_trace_id: str | None = None,
        evidence: list[dict[str, Any]] | None = None,
        evidence_source: str = "user",
    ) -> Task:
        """Complete task and update plan progress if task belongs to a plan

        X-04 红线：``actual_minutes`` 只认**实测**值（客户端计时器）；
        缺省时由真实起止时间（started_at → completed_at，扣除暂停区间）推算；
        **永不回填 estimated_minutes**（计划输入不是执行观测）。
        ``evidence`` 为完成时附带的证据（分型校验），``evidence_source`` 决定
        无证据时的诚实回落类型（user → user_confirmation；focus_auto/agent →
        system_event）。
        """
        from app.services.task_completion_evidence import (
            append_completion_evidence_record,
            build_completion_evidence_record,
            resolve_actual_minutes,
        )

        _validate_transition(db_obj.status, TaskStatus.COMPLETED)
        db_obj.status = TaskStatus.COMPLETED
        completed_at = _utcnow()
        actual_minutes = resolve_actual_minutes(db_obj, provided=actual_minutes, ended_at=completed_at)
        db_obj.completed_at = completed_at
        db_obj.actual_minutes = actual_minutes
        if note:
            db_obj.user_note = note

        # X-04：完成证据分型记录（guide_json 增量；X-01 completion_evidence 声明列不动）
        try:
            evidence_record = build_completion_evidence_record(
                db_obj,
                provided=evidence,
                source=evidence_source,
                completed_at=completed_at,
            )
            append_completion_evidence_record(db_obj, evidence_record)
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001 — 证据记录失败不阻断完成（记录缺省可观测）
            logger.warning("Failed to build completion evidence record for task {}: {}", db_obj.id, exc)

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
            try:
                # X-04：galaxy 子系统缺席（如 gen 模块未生成）不得阻断完成——
                # 导入一并纳入 best-effort try（spark 本就允许失败告警）
                from app.services.galaxy_service import GalaxyService
                from app.services.task_completion_evidence import resolve_spark_study_minutes

                galaxy_service = GalaxyService(db)
                await galaxy_service.spark_node(
                    user_id=db_obj.user_id,
                    node_id=db_obj.knowledge_node_id,
                    study_minutes=resolve_spark_study_minutes(actual_minutes),
                    task_id=db_obj.id,
                    trigger_expansion=True,
                )
            except Exception as exc:
                logger.warning("Failed to spark node for task {}: {}", db_obj.id, exc)

        # daily-flow DF-5: everyday tasks without a galaxy anchor (no
        # knowledge_node_id, no sprint-pack guide) still grow the star map —
        # match an existing node by title or ignite a stable task-derived star,
        # then spark it so unlocked/mastered/study_minutes react to real study.
        if not db_obj.knowledge_node_id:
            try:
                from app.services.galaxy_service import GalaxyService
                from app.services.task_completion_evidence import resolve_spark_study_minutes

                galaxy_service = GalaxyService(db)
                anchor_id = await galaxy_service.ensure_task_node(
                    db_obj.title, task_id=db_obj.id
                )
                await galaxy_service.spark_node(
                    user_id=db_obj.user_id,
                    node_id=anchor_id,
                    study_minutes=resolve_spark_study_minutes(actual_minutes),
                    task_id=db_obj.id,
                    trigger_expansion=False,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to couple completed task {} to galaxy: {}", db_obj.id, exc
                )

        task_id_for_log = str(db_obj.id)
        try:
            await TaskService._update_sprint_pack_mastery_for_completed_task(db, db_obj)
        except Exception as exc:
            logger.warning("Failed to update sprint mastery for completed task {}: {}", task_id_for_log, exc)

        # Publish task completion event for cognitive analysis
        from app.core.event_bus import TaskCompleted
        from app.models.community import GroupTaskClaim

        estimated = db_obj.estimated_minutes or 0
        # X-04：actual 未知（无 started_at 的历史/合成行）时诚实缺省——
        # completion_rate=None（消费方已知处理 None），绝不为算比率而回填 estimated
        if estimated > 0:
            completion_rate = (actual_minutes / estimated) if actual_minutes is not None else None
        else:
            completion_rate = 1.0
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
        if route_history_decision_id:
            source_metadata["route_history_decision_id"] = route_history_decision_id
        if routing_outcome_signal_id:
            source_metadata["routing_outcome_signal_id"] = routing_outcome_signal_id
        if routing_trace_id:
            source_metadata["routing_trace_id"] = routing_trace_id

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
            route_history_decision_id=route_history_decision_id,
            routing_outcome_signal_id=routing_outcome_signal_id,
            routing_trace_id=routing_trace_id,
        )
        await event_bus_reliable.publish("task.completed", event.to_dict())
        # X-08：统一 Outcome 捕获（Human/Hybrid 完成面）——映射 outcome 身份 +
        # 极性并广播 outcome.recorded；真相面仍由 D-02 账本查询时点重算（单一真源）。
        try:
            from app.services.outcome_capture_service import capture_task_outcome

            await capture_task_outcome(db_obj)
        except Exception as exc:  # noqa: BLE001 — 广播失败不阻断完成（账本读模型可重放）
            logger.warning("Failed to capture outcome for completed task {}: {}", db_obj.id, exc)
        try:
            from app.aurora.runtime_v1.self_model import SparkleSelfModelService

            await SparkleSelfModelService(cache_service.redis).record_task_outcome(
                user_id=str(db_obj.user_id),
                signal_id=f"task.completed:{db_obj.id}:{db_obj.completed_at.isoformat() if db_obj.completed_at else actual_minutes}",
                completed=True,
                timed_out=bool(estimated > 0 and actual_minutes is not None and actual_minutes > estimated),
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
        try:
            from app.services.north_star_metrics_service import (
                NorthStarMetricsService,
                NorthStarMetricType,
            )

            await NorthStarMetricsService(db).record_cold_start_milestone(
                user_id=db_obj.user_id,
                plan_id=db_obj.plan_id,
                task_id=db_obj.id,
                milestone=NorthStarMetricType.FIRST_TASK_COMPLETED,
                source="task_service_complete",
                occurred_at=db_obj.completed_at,
                payload={
                    "task_title": db_obj.title,
                    "actual_minutes": actual_minutes,
                    "estimated_minutes": estimated,
                    "completion_rate": completion_rate,
                },
            )
        except Exception as exc:
            logger.warning("Failed to record first task North Star metric {}: {}", db_obj.id, exc)

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
    def _build_task_summary(task: Task, actual_minutes: int | None, note: str | None) -> dict:
        estimated = task.estimated_minutes or 0
        # X-04：actual 未知时 delta 诚实标注，不做 estimated 假对比
        if actual_minutes is None:
            delta_label = "unknown"
        else:
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
        _validate_transition(db_obj.status, TaskStatus.STUCK)

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
    async def abandon(
        db: AsyncSession,
        db_obj: Task,
        reason: str | None = None,
        route_history_decision_id: str | None = None,
        routing_outcome_signal_id: str | None = None,
        routing_trace_id: str | None = None,
    ) -> Task:
        """Abandon task

        X-04：放弃也要留痕——持久化真实投入时长（started_at → abandoned_at 扣
        暂停；**未开始过则保持 None，绝不拿 estimated 顶替**）并在 guide_json
        追加 abandon_record（原因/时刻/时长/此前状态），重开与复盘可回溯。
        """
        from app.services.task_completion_evidence import (
            ABANDON_RECORD_KEY,
            compute_actual_minutes_from_timestamps,
        )

        _validate_transition(db_obj.status, TaskStatus.ABANDONED)
        status_before = db_obj.status
        abandoned_at = _utcnow()
        db_obj.status = TaskStatus.ABANDONED
        db_obj.completed_at = abandoned_at  # using completed_at for end time
        # X-04：真实投入时长持久化（未开始 → None；永不从 estimated 回填）
        db_obj.actual_minutes = compute_actual_minutes_from_timestamps(db_obj, ended_at=abandoned_at)
        if reason:
            db_obj.user_note = f"Abandoned: {reason}"

        # X-04：放弃留痕（append-only，重开不抹）
        try:
            guide_json = dict(db_obj.guide_json or {})
            record = {
                "reason": reason,
                "abandoned_at": abandoned_at.isoformat(timespec="seconds"),
                "actual_minutes": db_obj.actual_minutes,
                "status_before": status_before.value if isinstance(status_before, TaskStatus) else str(status_before),
                "user_note": db_obj.user_note,
            }
            history = guide_json.get(ABANDON_RECORD_KEY)
            if isinstance(history, list):
                history = [*history, record]
            elif history is None:
                history = [record]
            else:
                history = [history, record]
            guide_json[ABANDON_RECORD_KEY] = history
            db_obj.guide_json = guide_json
        except Exception as exc:  # noqa: BLE001 — 留痕失败不阻断放弃（可观测降级）
            logger.warning("Failed to record abandon trace for task {}: {}", db_obj.id, exc)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await _sync_task_card_projection(db, db_obj)

        # Sync with PlanState if task belongs to a plan
        if db_obj.plan_id:
            try:
                from app.services.task_state_sync import TaskStateSyncService

                sync_service = TaskStateSyncService(db)
                # X-04 修复：此处必须传**迁移前**状态（曾误传迁移后的 ABANDONED，
                # 使 plan 侧把放弃误当 continue-from-ABANDONED）
                await sync_service.on_task_updated(db_obj, old_status=status_before)
            except Exception as e:
                logger.warning(f"Failed to sync task abandonment with plan state: {e}")

        # Publish task abandonment event for cognitive analysis
        from app.core.event_bus import TaskAbandoned

        # X-04：事件时长与持久化值同源（真实起止推算，未开始为 None）
        time_spent = db_obj.actual_minutes

        event = TaskAbandoned(
            user_id=str(db_obj.user_id),
            task_id=str(db_obj.id),
            reason=reason,
            estimated_minutes=db_obj.estimated_minutes,
            time_spent=time_spent,
            plan_id=str(db_obj.plan_id) if db_obj.plan_id else None,
            source_metadata={
                key: value
                for key, value in {
                    "route_history_decision_id": route_history_decision_id,
                    "routing_outcome_signal_id": routing_outcome_signal_id,
                    "routing_trace_id": routing_trace_id,
                }.items()
                if value
            },
            route_history_decision_id=route_history_decision_id,
            routing_outcome_signal_id=routing_outcome_signal_id,
            routing_trace_id=routing_trace_id,
            due_at=db_obj.due_date.isoformat() if db_obj.due_date else None,
        )
        await event_bus_reliable.publish("task.abandoned", event.to_dict())
        # X-08：失败 outcome 统一捕获（polarity=NEGATIVE）——「partial/failed 保留，
        # 不得静默丢弃」；负极性 outcome 结构性不可点亮（WVPL loop 谓词要求
        # status=COMPLETED，Goal.progress 只数 COMPLETED）。
        try:
            from app.services.outcome_capture_service import capture_task_outcome

            await capture_task_outcome(db_obj)
        except Exception as exc:  # noqa: BLE001 — 广播失败不阻断放弃（可观测降级）
            logger.warning("Failed to capture outcome for abandoned task {}: {}", db_obj.id, exc)
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
    async def abandon_task(
        db: AsyncSession,
        task_id: UUID,
        user_id: UUID,
        reason: str | None = None,
        route_history_decision_id: str | None = None,
        routing_outcome_signal_id: str | None = None,
        routing_trace_id: str | None = None,
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

        return await TaskService.abandon(
            db,
            task,
            reason,
            route_history_decision_id=route_history_decision_id,
            routing_outcome_signal_id=routing_outcome_signal_id,
            routing_trace_id=routing_trace_id,
        )

    # ── X-04 · 重开（reopen）与重定范围（rescope）──────────────────────────
    # 设计纪律：二者是**独立的显式用户动作**，不并入 _VALID_TRANSITIONS——
    # X-03 的 status_change_semantics 以「FSM 无出边 = 终态不可逆」推导 complete/
    # abandon 的 medium/irreversible 授权分级；若给终态加出边，complete 会被
    # 降级为 low/reversible，削弱既有授权守卫（X-04 Forbidden 条款）。重开走
    # 本专用路径：终态限定 + 历史保留 + 显式 reason。

    @staticmethod
    async def reopen(
        db: AsyncSession,
        db_obj: Task,
        reason: str | None = None,
    ) -> Task:
        """重开终态任务（COMPLETED/ABANDONED → IN_PROGRESS），**重开保留状态**.

        保留语义：上一次终态尝试的完整快照（状态/完成时刻/真实时长/完成证据
        记录/备注/原因）append 进 ``guide_json["reopen_history"]`` 后才清理
        工作列（completed_at/actual_minutes 复位，started_at 刷新为本轮起点）
        ——历史不丢，actual 永远只反映当前一轮的真实起止。
        """
        from app.services.task_completion_evidence import REOPEN_HISTORY_KEY

        if db_obj.status not in (TaskStatus.COMPLETED, TaskStatus.ABANDONED):
            raise ValueError(
                f"Only terminal tasks can be reopened (current: {db_obj.status.value})"
            )
        status_before = db_obj.status
        reopened_at = _utcnow()

        guide_json = dict(db_obj.guide_json or {})
        snapshot = {
            "reopened_at": reopened_at.isoformat(timespec="seconds"),
            "reason": reason,
            "status_before": status_before.value,
            "completed_at": db_obj.completed_at.isoformat() if db_obj.completed_at else None,
            "actual_minutes": db_obj.actual_minutes,
            "user_note": db_obj.user_note,
            "completion_evidence_record": guide_json.get("completion_evidence_record"),
        }
        history = guide_json.get(REOPEN_HISTORY_KEY)
        history = [*history, snapshot] if isinstance(history, list) else ([history, snapshot] if history else [snapshot])
        guide_json[REOPEN_HISTORY_KEY] = history

        db_obj.status = TaskStatus.IN_PROGRESS
        db_obj.started_at = reopened_at  # 本轮真实起点（actual 只计本轮真实起止）
        db_obj.completed_at = None
        db_obj.actual_minutes = None
        db_obj.paused_at = None
        db_obj.paused_reason = None
        pause_state = dict(guide_json.get("pause_state") or {})
        if pause_state:
            guide_json["pause_state"] = {
                **pause_state,
                "paused_at": None,
                "resumed_at": None,
                "total_paused_seconds": 0,
            }
        if reason:
            db_obj.user_note = f"Reopened: {reason}"
        db_obj.guide_json = guide_json

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await _sync_task_card_projection(db, db_obj)

        if db_obj.plan_id:
            try:
                from app.services.task_state_sync import TaskStateSyncService

                sync_service = TaskStateSyncService(db)
                await sync_service.on_task_updated(db_obj, old_status=status_before)
            except Exception as e:
                logger.warning(f"Failed to sync task reopen with plan state: {e}")

        # 事件词表 39 冻结：重开是新一轮开始，复用既有 task.started 名
        await event_bus_reliable.publish(
            "task.started",
            {
                "event_type": "task.started",
                "user_id": str(db_obj.user_id),
                "task_id": str(db_obj.id),
                "plan_id": str(db_obj.plan_id) if db_obj.plan_id else None,
                "reopened_from": status_before.value,
                "reason": reason,
                "due_at": db_obj.due_date.isoformat() if db_obj.due_date else None,
            },
        )
        await publish_srl_event(
            user_id=db_obj.user_id,
            trigger_event_type="task.started",
            evidence_id=str(db_obj.id),
            metadata={
                "plan_id": str(db_obj.plan_id) if db_obj.plan_id else None,
                "reopened_from": status_before.value,
            },
        )
        return db_obj

    @staticmethod
    async def reopen_task(
        db: AsyncSession,
        task_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> Task:
        """Reopen a terminal task by ID (ownership verified)."""
        task = await TaskService.get_by_id(db, task_id, user_id)
        if not task:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(message="Task not found")
        return await TaskService.reopen(db, task, reason)

    @staticmethod
    async def rescope(
        db: AsyncSession,
        db_obj: Task,
        fields: dict[str, Any],
        reason: str | None = None,
    ) -> Task:
        """重定范围（rescope）：收缩/调整任务口径，**历史保留**.

        - 仅活跃态可 rescope（PENDING/IN_PROGRESS/PAUSED/STUCK）；终态先重开；
        - 字段白名单（RESCOPE_FIELD_WHITELIST，与 X-03 提案白名单同词表）；
        - before/after 快照 append 进 ``guide_json["rescope_history"]``；
        - 零有效变更 → no-op（幂等：不追加历史、不触碰 updated_at 语义）；
        - started_at / 状态 / 完成证据一律不动——rescope 只改口径，不重置执行。
        """
        from app.services.task_completion_evidence import RESCOPE_FIELD_WHITELIST

        if db_obj.status in (TaskStatus.COMPLETED, TaskStatus.ABANDONED):
            raise ValueError(
                f"Terminal tasks cannot be rescoped; reopen first (current: {db_obj.status.value})"
            )
        if not isinstance(fields, dict) or not fields:
            raise ValueError("rescope fields must be a non-empty object")
        illegal = sorted(set(fields) - RESCOPE_FIELD_WHITELIST)
        if illegal:
            raise ValueError(f"rescope fields outside whitelist: {illegal}")

        changes: dict[str, dict[str, Any]] = {}
        for key, value in fields.items():
            current = getattr(db_obj, key, None)
            if key == "due_date" and isinstance(value, str) and value:
                from datetime import date as date_cls

                value = date_cls.fromisoformat(value)
            if current == value:
                continue
            if hasattr(current, "isoformat"):
                current_out = current.isoformat()
            elif hasattr(current, "value"):
                current_out = current.value
            else:
                current_out = current
            if hasattr(value, "isoformat"):
                value_out = value.isoformat()
            else:
                value_out = value
            changes[key] = {"before": current_out, "after": value_out}
            setattr(db_obj, key, value)

        if not changes:
            return db_obj  # 幂等 no-op：零有效变更不留痕

        from app.services.task_completion_evidence import RESCOPE_HISTORY_KEY

        rescoped_at = _utcnow()
        guide_json = dict(db_obj.guide_json or {})
        entry = {
            "rescoped_at": rescoped_at.isoformat(timespec="seconds"),
            "reason": reason,
            "changes": changes,
            "status": db_obj.status.value if isinstance(db_obj.status, TaskStatus) else str(db_obj.status),
        }
        history = guide_json.get(RESCOPE_HISTORY_KEY)
        history = [*history, entry] if isinstance(history, list) else ([history, entry] if history else [entry])
        guide_json[RESCOPE_HISTORY_KEY] = history
        db_obj.guide_json = guide_json

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await _sync_task_card_projection(db, db_obj)

        if db_obj.plan_id:
            try:
                from app.services.task_state_sync import TaskStateSyncService

                sync_service = TaskStateSyncService(db)
                await sync_service.on_task_updated(db_obj)
            except Exception as e:
                logger.warning(f"Failed to sync task rescope with plan state: {e}")
        return db_obj

    @staticmethod
    async def rescope_task(
        db: AsyncSession,
        task_id: UUID,
        user_id: UUID,
        fields: dict[str, Any],
        reason: str | None = None,
    ) -> Task:
        """Rescope a task by ID (ownership verified)."""
        task = await TaskService.get_by_id(db, task_id, user_id)
        if not task:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(message="Task not found")
        return await TaskService.rescope(db, task, fields, reason)


    @staticmethod
    async def delete(db: AsyncSession, db_obj: Task) -> None:
        """Delete task"""
        plan_id = db_obj.plan_id
        user_id = db_obj.user_id
        await db.delete(db_obj)
        await db.commit()

        # G-04 残影守卫（best-effort）：任务硬删后星图读面的目标关联
        # （goal-connected nodes）与任务星关联旧值不得活过缓存 TTL
        # （view ttl=600 + shield 10s）。已吸收的掌握度与溯源不回滚——
        # 真实完成过的学习是已发生事实；已删任务的 outcome 再点亮由
        # absorber 的 GHOST-OUTCOME 守卫阻断。
        try:
            from app.services.galaxy.consistency_service import invalidate_galaxy_view_for_user

            await invalidate_galaxy_view_for_user(user_id)
        except Exception as e:
            logger.warning(f"Failed to invalidate galaxy view after task deletion: {e}")

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
                due_at=task.due_date.isoformat() if task.due_date else None,
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
