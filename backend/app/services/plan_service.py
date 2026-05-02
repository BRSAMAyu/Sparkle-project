"""
Plan Service
Handle plan business logic
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.event_bus import PlanCreatedEvent, event_bus
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.plan_state import PlanStateStatus
from app.models.task import Task, TaskStatus
from app.schemas.plan import PlanCreate, PlanUpdate
from app.services.stage33_journey_event_service import Stage33JourneyEventService


def _utcnow() -> datetime:
    """Return naive UTC datetime for compatibility with DB TIMESTAMP columns."""
    return datetime.now(UTC).replace(tzinfo=None)


async def _sync_plan_card_projection(db: AsyncSession, plan: Plan) -> None:
    plan_id = str(plan.id)
    if db.bind is None:
        return

    try:
        from app.services.card_protocol.legacy_adapter import PlanAdapter

        session_factory = async_sessionmaker(db.bind, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as shadow_db:
            shadow_plan = await shadow_db.get(Plan, plan.id)
            if shadow_plan is None:
                return
            adapter = PlanAdapter(shadow_db, event_bus)
            await adapter.plan_to_card(shadow_plan)
            await shadow_db.commit()
    except Exception as exc:
        logger.warning("Plan card dual-write failed for {}: {}", plan_id, exc)


class PlanService:
    @staticmethod
    async def get_by_id(
        db: AsyncSession, plan_id: UUID, user_id: UUID
    ) -> Plan | None:
        query = select(Plan).where(
            and_(Plan.id == plan_id, Plan.user_id == user_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        obj_in: PlanCreate,
        user_id: UUID,
        skip_quota_check: bool = False,
        redis_client=None
    ) -> Plan:
        """
        创建新计划

        Args:
            db: 数据库会话
            obj_in: 计划创建数据
            user_id: 用户ID
            skip_quota_check: 是否跳过配额检查（仅用于测试/管理员）
            redis_client: Redis客户端（用于配额服务）

        Returns:
            创建的计划对象

        Raises:
            QuotaExceededError: 配额超限
        """
        from app.services.plan_quota_service import PlanQuotaService

        # 1. 配额检查
        if not skip_quota_check:
            quota_service = PlanQuotaService(db, redis_client)
            await quota_service.check_and_raise(user_id, obj_in.type.value if obj_in.type else None)

        # 2. 检查是否是第一个计划（自动设为主计划）
        quota_service = PlanQuotaService(db, redis_client)
        quota_status = await quota_service.get_quota_status(user_id)
        is_first_plan = quota_status.used == 0

        # 3. 创建计划
        db_obj = Plan(
            user_id=user_id,
            name=obj_in.name,
            type=obj_in.type,
            plan_stage=obj_in.plan_stage or PlanStage.DAILY,
            description=obj_in.description,
            subject=obj_in.subject,
            target_date=obj_in.target_date,
            daily_available_minutes=obj_in.daily_available_minutes,
            total_estimated_hours=obj_in.total_estimated_hours,
            # 新增字段
            priority=getattr(obj_in, 'priority', None) or PlanPriority.NORMAL,
            is_primary=is_first_plan,  # 第一个计划自动设为主计划
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await _sync_plan_card_projection(db, db_obj)

        logger.info(
            f"Plan created: {db_obj.id} for user {user_id}, "
            f"is_primary={db_obj.is_primary}, priority={db_obj.priority}"
        )
        await Stage33JourneyEventService.publish(
            "plan.created",
            PlanCreatedEvent(
                user_id=str(user_id),
                plan_id=str(db_obj.id),
                source="plan_service.create",
                metadata={
                    "plan_type": db_obj.type.value if db_obj.type else None,
                    "plan_stage": db_obj.plan_stage.value if db_obj.plan_stage else None,
                    "is_primary": db_obj.is_primary,
                },
            ).to_dict(),
        )

        return db_obj

    @staticmethod
    async def update(
        db: AsyncSession, db_obj: Plan, obj_in: PlanUpdate
    ) -> Plan:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await _sync_plan_card_projection(db, db_obj)
        return db_obj

    @staticmethod
    async def list_active(
        db: AsyncSession, user_id: UUID, limit: int = 5
    ) -> list[Plan]:
        query = (
            select(Plan)
            .where(and_(Plan.user_id == user_id, Plan.is_active))
            .order_by(desc(Plan.created_at))
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_progress(
        db: AsyncSession, plan_id: UUID, user_id: UUID
    ) -> float | None:
        """
        Calculate and update plan progress based on task completion ratio.

        P0.2: Plan Progress Auto-Update
        Called automatically when tasks are completed to keep progress in sync.

        Returns:
            Updated progress value (0.0-1.0), or None if plan not found
        """
        # Verify plan exists and belongs to user
        plan = await PlanService.get_by_id(db, plan_id, user_id)
        if not plan:
            return None

        try:
            from app.services.card_protocol.phase_service import PhaseService

            async with db.begin_nested():
                weighted_progress = await PhaseService(db, event_bus).sync_legacy_plan_progress(
                    legacy_plan_id=plan_id,
                    user_id=user_id,
                )
            if weighted_progress is not None:
                await db.commit()
                await db.refresh(plan)
                await PlanService._auto_archive_completed_sprint(db, plan)
                await _sync_plan_card_projection(db, plan)
                return weighted_progress
        except Exception as exc:
            logger.warning("Weighted phase progress fallback for {} failed: {}", plan_id, exc)

        # Count total tasks for this plan
        total_query = select(func.count(Task.id)).where(Task.plan_id == plan_id)
        total_result = await db.execute(total_query)
        total_tasks = total_result.scalar_one()

        # Count completed tasks
        completed_query = select(func.count(Task.id)).where(
            and_(Task.plan_id == plan_id, Task.status == TaskStatus.COMPLETED)
        )
        completed_result = await db.execute(completed_query)
        completed_tasks = completed_result.scalar_one()

        # Calculate progress ratio
        new_progress = completed_tasks / total_tasks if total_tasks > 0 else 0.0

        # Update plan progress
        plan.progress = new_progress
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        await PlanService._auto_archive_completed_sprint(
            db,
            plan,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
        )
        await _sync_plan_card_projection(db, plan)

        return new_progress

    @staticmethod
    async def _auto_archive_completed_sprint(
        db: AsyncSession,
        plan: Plan,
        *,
        total_tasks: int | None = None,
        completed_tasks: int | None = None,
    ) -> bool:
        """Archive sprint plans as soon as every task is complete."""
        if plan.type != PlanType.SPRINT or not plan.is_active:
            return False

        if total_tasks is None or completed_tasks is None:
            total_result = await db.execute(select(func.count(Task.id)).where(Task.plan_id == plan.id))
            total_tasks = total_result.scalar_one()
            completed_result = await db.execute(
                select(func.count(Task.id)).where(
                    and_(Task.plan_id == plan.id, Task.status == TaskStatus.COMPLETED)
                )
            )
            completed_tasks = completed_result.scalar_one()

        if total_tasks <= 0 or completed_tasks < total_tasks:
            return False

        now = _utcnow()
        metadata = dict(plan.source_metadata or {})
        completion_state = metadata.get("exam_sprint_completion")
        if not isinstance(completion_state, dict):
            completion_state = {}
        completion_state.setdefault("completed_at", now.isoformat())
        completion_state["trigger"] = "all_tasks_completed"
        metadata["exam_sprint_completion"] = completion_state

        plan.source_metadata = metadata
        plan.progress = 1.0
        db.add(plan)
        await db.flush()

        archived_plan = await PlanService.archive(db=db, plan_id=plan.id, user_id=plan.user_id)
        if archived_plan is None:
            return False

        try:
            from app.services.plan_state_service import PlanStateService

            await PlanStateService(db).upsert_plan_state(
                user_id=plan.user_id,
                plan_id=plan.id,
                patch={
                    "status": PlanStateStatus.ARCHIVED.value,
                    "archived_at": now,
                },
                bump_version=False,
            )
        except Exception as exc:
            logger.warning("Failed to archive completed sprint plan state {}: {}", plan.id, exc)

        try:
            tasks_result = await db.execute(select(Task).where(Task.plan_id == plan.id))
            tasks = list(tasks_result.scalars().all())
            if PlanService._is_completed_seven_day_sprint(tasks):
                from app.services.north_star_metrics_service import NorthStarMetricsService

                await NorthStarMetricsService(db).record_seven_day_goal_completed(
                    user_id=plan.user_id,
                    plan_id=plan.id,
                    source="plan_service_auto_archive",
                    occurred_at=now,
                    payload={
                        "plan_name": plan.name,
                        "subject": plan.subject,
                        "exam_date": plan.target_date.isoformat() if plan.target_date else None,
                        "completed_tasks": completed_tasks,
                        "total_tasks": total_tasks,
                        "task_completion_rate": 1.0,
                    },
                )
        except Exception as exc:
            logger.warning("Failed to record completed sprint North Star metric {}: {}", plan.id, exc)

        await db.refresh(plan)
        logger.info("Auto-archived completed sprint plan: {}", plan.id)
        return True

    @staticmethod
    def _is_completed_seven_day_sprint(tasks: list[Task]) -> bool:
        if not tasks:
            return False
        days = {PlanService._task_day_index(task) for task in tasks}
        return set(range(1, 8)).issubset(days) and all(task.status == TaskStatus.COMPLETED for task in tasks)

    @staticmethod
    def _task_day_index(task: Task) -> int:
        guide_json = PlanService._as_dict(task.guide_json)
        for key in ("day", "day_number", "day_index"):
            value = PlanService._safe_int(guide_json.get(key))
            if value:
                return value
        tags = task.tags if isinstance(task.tags, list) else []
        for tag in tags:
            text = str(tag or "")
            if text.startswith("day:"):
                value = PlanService._safe_int(text.split(":", 1)[1])
                if value:
                    return value
        order_index = PlanService._safe_int(task.order_index)
        if order_index:
            return max(1, order_index // 1000)
        return 1

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            parsed = int(float(value))
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    @staticmethod
    async def archive(
        db: AsyncSession,
        plan_id: UUID,
        user_id: UUID,
        redis_client=None
    ) -> Plan | None:
        """
        归档计划

        归档后计划不再占用配额，但数据保留用于历史查询

        Args:
            db: 数据库会话
            plan_id: 计划ID
            user_id: 用户ID
            redis_client: Redis客户端

        Returns:
            归档后的计划对象，如果计划不存在则返回None
        """
        from app.services.plan_quota_service import PlanQuotaService

        plan = await PlanService.get_by_id(db, plan_id, user_id)
        if not plan:
            return None

        was_primary = plan.is_primary

        # 归档计划
        plan.is_active = False
        plan.is_primary = False
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        await _sync_plan_card_projection(db, plan)

        logger.info(f"Plan archived: {plan_id} for user {user_id}")

        # 如果归档的是主计划，自动选择新的主计划
        if was_primary:
            quota_service = PlanQuotaService(db, redis_client)
            new_primary_id = await quota_service.auto_set_primary_plan(user_id)
            if new_primary_id:
                logger.info(f"Auto-selected new primary plan: {new_primary_id}")

        return plan

    @staticmethod
    async def restore(
        db: AsyncSession,
        plan_id: UUID,
        user_id: UUID,
        skip_quota_check: bool = False,
        redis_client=None
    ) -> Plan | None:
        """
        恢复归档的计划

        Args:
            db: 数据库会话
            plan_id: 计划ID
            user_id: 用户ID
            skip_quota_check: 是否跳过配额检查
            redis_client: Redis客户端

        Returns:
            恢复后的计划对象

        Raises:
            QuotaExceededError: 配额超限
        """
        from app.services.plan_quota_service import PlanQuotaService

        # 查找归档的计划
        query = select(Plan).where(
            and_(
                Plan.id == plan_id,
                Plan.user_id == user_id,
                Plan.is_active.is_(False),
            )
        )
        result = await db.execute(query)
        plan = result.scalar_one_or_none()

        if not plan:
            return None

        # 配额检查
        if not skip_quota_check:
            quota_service = PlanQuotaService(db, redis_client)
            await quota_service.check_and_raise(user_id)

        # 恢复计划
        plan.is_active = True
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        await _sync_plan_card_projection(db, plan)

        logger.info(f"Plan restored: {plan_id} for user {user_id}")

        # 确保有主计划
        quota_service = PlanQuotaService(db, redis_client)
        await quota_service.ensure_primary_exists(user_id)

        return plan

    @staticmethod
    async def update_priority(
        db: AsyncSession,
        plan_id: UUID,
        user_id: UUID,
        priority: PlanPriority
    ) -> Plan | None:
        """
        更新计划优先级

        Args:
            db: 数据库会话
            plan_id: 计划ID
            user_id: 用户ID
            priority: 新优先级

        Returns:
            更新后的计划对象
        """
        plan = await PlanService.get_by_id(db, plan_id, user_id)
        if not plan:
            return None

        plan.priority = priority
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        logger.info(f"Plan priority updated: {plan_id} -> {priority}")
        return plan

    @staticmethod
    async def get_primary(
        db: AsyncSession,
        user_id: UUID
    ) -> Plan | None:
        """
        获取用户的主计划

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            主计划对象
        """
        query = select(Plan).where(
            and_(
                Plan.user_id == user_id,
                Plan.is_active,
                Plan.is_primary
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_archived(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20
    ) -> list[Plan]:
        """
        获取归档的计划列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            limit: 返回数量限制

        Returns:
            归档计划列表
        """
        query = (
            select(Plan)
            .where(and_(Plan.user_id == user_id, Plan.is_active.is_(False)))
            .order_by(desc(Plan.updated_at))
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())
