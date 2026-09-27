"""
Calendar API Endpoints
日历事件 CRUD 接口
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.event_bus import CalendarEventCreated, CalendarEventDeleted, CalendarEventUpdated, event_bus
from app.core.exceptions import NotFoundError
from app.core.time_utils import local_date, local_midnight_wall, utc_naive_to_wall_clock, valid_timezone_name
from app.db.session import get_db
from app.models.calendar_event import CalendarEvent
from app.models.user import PushPreference, User
from app.schemas.calendar_event import (
    BatchOperationResult,
    CalendarEventBatchRequest,
    CalendarEventBatchResponse,
    CalendarEventCreate,
    CalendarEventDetail,
    CalendarEventListResponse,
    CalendarEventUpdate,
)
from app.schemas.smart_schedule import (
    SmartScheduleRequest,
    SmartScheduleResponse,
)
from app.services.smart_schedule_service import SmartScheduleService

router = APIRouter()


async def _user_timezone(db: AsyncSession, user_id: UUID) -> str:
    """用户 IANA 时区名——push_preference.timezone 标量直查，缺省 Asia/Shanghai。

    state_aggregator._user_timezone / focus_service._local_today 先例
    （V3-FIX-37 族）：标量直查规避身份映射命中未加载关系的 async lazy-load；
    缺省/非法回落主市场 Asia/Shanghai（time_utils 口径）。
    """
    tz_name = await db.scalar(select(PushPreference.timezone).where(PushPreference.user_id == user_id))
    return valid_timezone_name(tz_name)


@router.post("/suggest-time", response_model=SmartScheduleResponse)
async def suggest_time_slots(
    request: SmartScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    智能排程建议

    根据任务参数和用户认知模式，推荐最佳时间槽。
    """
    service = SmartScheduleService(db)
    return await service.suggest_time_slots(current_user.id, request)


@router.get("", response_model=CalendarEventListResponse)
async def list_events(
    start_date: date | None = Query(None, description="开始日期筛选"),
    end_date: date | None = Query(None, description="结束日期筛选"),
    include_deleted: bool = Query(False, description="是否包含已删除事件"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    按日期范围列出日历事件
    """
    query = select(CalendarEvent).where(CalendarEvent.user_id == current_user.id)

    # 软删除过滤
    if not include_deleted:
        query = query.where(CalendarEvent.deleted_at.is_(None))

    # 日期范围过滤（V3-FIX-318）：start_date/end_date 语义 = 用户本地日；
    # CalendarEvent.start/end_time 是客户端本地墙上钟列（V3-FIX-37 定界），
    # 窗口须用同一墙钟的本地日界 naive 直比——修前构造成 aware UTC 日界
    # （生产 asyncpg/timestamptz 面上每日 16:00-24:00Z 窗口事件错日 +
    #  aware-vs-naive 未定义行为面）。墙上钟窗对任意时区都是「该日
    # 00:00-24:00 墙上钟」，tz 隐含在入参语义里，无 UTC 换算面。
    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        query = query.where(CalendarEvent.end_time >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        query = query.where(CalendarEvent.start_time <= end_dt)

    # 排序
    query = query.order_by(CalendarEvent.start_time)

    # 获取总数
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    events = result.scalars().all()

    return CalendarEventListResponse(
        data=[CalendarEventDetail.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CalendarEventDetail, status_code=201)
async def create_event(
    event_in: CalendarEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建日历事件
    """
    event = CalendarEvent(
        user_id=current_user.id,
        title=event_in.title,
        description=event_in.description,
        start_time=event_in.start_time,
        end_time=event_in.end_time,
        is_all_day=event_in.is_all_day,
        location=event_in.location,
        color=event_in.color,
        recurrence_rule=event_in.recurrence_rule,
        recurrence_end_date=event_in.recurrence_end_date,
        reminder_minutes=event_in.reminder_minutes,
        source=event_in.source,
        source_metadata=event_in.source_metadata,
        task_id=event_in.task_id,
        plan_id=event_in.plan_id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    logger.info(f"Calendar event created: {event.id} by user {current_user.id}")

    # 发布事件到 EventBus
    await event_bus.publish(
        "calendar.event.created",
        CalendarEventCreated(
            user_id=str(current_user.id),
            event_id=str(event.id),
            title=event.title,
            start_time=event.start_time,
            source=event.source,
        ).to_dict(),
    )

    # TRACKED(TD-006): 调度提醒通知

    return CalendarEventDetail.model_validate(event)


@router.get("/summary", response_model=dict[str, Any])
async def get_event_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取日历事件统计摘要
    """
    now = datetime.now(UTC)
    tz_name = await _user_timezone(db, current_user.id)
    # V3-FIX-318：「今日」按用户本地日界的墙上零点切（CalendarEvent.start_time
    # 是本地墙上钟列，V3-FIX-37 定界；eb14c205 calendar「今日」同向）——修前
    # 按 UTC 日切，上海 00:00-08:00（=前日 16:00-24:00Z）的事件计入「昨日」、
    # 本地今日清晨缺席「今日」计数。「未来 7 天」端点经 utc_naive_to_wall_clock
    # 换成用户墙上钟入 SQL 同钟比（027bb028 同款，双射；修前 UTC 瞬间直比
    # 下界松 8h、上界紧 8h）。
    now_naive = now.replace(tzinfo=None)
    local_today = local_date(now_naive, tz_name)
    today_start = local_midnight_wall(local_today)
    today_end = datetime.combine(local_today, datetime.max.time())

    # 总事件数
    total_query = select(func.count()).select_from(CalendarEvent).where(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.deleted_at.is_(None),
    )
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()

    # 今日事件数
    today_query = select(func.count()).select_from(CalendarEvent).where(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.deleted_at.is_(None),
        CalendarEvent.start_time >= today_start,
        CalendarEvent.start_time <= today_end,
    )
    today_result = await db.execute(today_query)
    today = today_result.scalar_one()

    # 即将到来的事件数 (未来7天)
    upcoming_end = now.replace(hour=23, minute=59, second=59) + timedelta(days=7)
    upcoming_start_wall = utc_naive_to_wall_clock(now, tz_name)
    upcoming_end_wall = utc_naive_to_wall_clock(upcoming_end, tz_name)
    upcoming_query = select(func.count()).select_from(CalendarEvent).where(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.deleted_at.is_(None),
        CalendarEvent.start_time >= upcoming_start_wall,
        CalendarEvent.start_time <= upcoming_end_wall,
    )
    upcoming_result = await db.execute(upcoming_query)
    upcoming = upcoming_result.scalar_one()

    # 重复事件数
    recurring_query = select(func.count()).select_from(CalendarEvent).where(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.deleted_at.is_(None),
        CalendarEvent.recurrence_rule.isnot(None),
    )
    recurring_result = await db.execute(recurring_query)
    recurring = recurring_result.scalar_one()

    return {
        "total": total,
        "upcoming": upcoming,
        "today": today,
        "recurring": recurring,
    }


@router.get("/{event_id}", response_model=CalendarEventDetail)
async def get_event(
    event_id: UUID = Path(..., description="事件 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取单个日历事件
    """
    event = await db.get(CalendarEvent, event_id)
    if not event or event.user_id != current_user.id or event.deleted_at:
        raise NotFoundError(message="事件不存在")

    return CalendarEventDetail.model_validate(event)


@router.put("/{event_id}", response_model=CalendarEventDetail)
async def update_event(
    event_in: CalendarEventUpdate,
    event_id: UUID = Path(..., description="事件 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新日历事件
    """
    event = await db.get(CalendarEvent, event_id)
    if not event or event.user_id != current_user.id or event.deleted_at:
        raise NotFoundError(message="事件不存在")

    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)

    logger.info(f"Calendar event updated: {event.id} by user {current_user.id}")

    # 发布事件到 EventBus
    await event_bus.publish(
        "calendar.event.updated",
        CalendarEventUpdated(
            user_id=str(current_user.id),
            event_id=str(event.id),
            changes=update_data,
        ).to_dict(),
    )

    return CalendarEventDetail.model_validate(event)


@router.delete("/{event_id}")
async def delete_event(
    event_id: UUID = Path(..., description="事件 ID"),
    hard_delete: bool = Query(False, description="是否永久删除"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除日历事件（默认软删除）
    """
    event = await db.get(CalendarEvent, event_id)
    if not event or event.user_id != current_user.id:
        raise NotFoundError(message="事件不存在")

    if hard_delete:
        await db.delete(event)
    else:
        event.soft_delete()
        db.add(event)

    await db.commit()

    logger.info(f"Calendar event {'hard' if hard_delete else 'soft'} deleted: {event_id} by user {current_user.id}")

    # 发布事件到 EventBus
    await event_bus.publish(
        "calendar.event.deleted",
        CalendarEventDeleted(
            user_id=str(current_user.id),
            event_id=str(event_id),
            hard_delete=hard_delete,
        ).to_dict(),
    )

    return {"success": True}


@router.post("/batch", response_model=CalendarEventBatchResponse)
async def batch_operations(
    request: CalendarEventBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    批量操作：创建/更新/删除多个事件
    """
    results: list[BatchOperationResult] = []
    success_count = 0
    failure_count = 0

    for op in request.operations:
        try:
            if op.action == "create":
                event_in = CalendarEventCreate(**op.data) if op.data else None
                if not event_in:
                    raise ValueError("Missing event data for create operation")

                event = CalendarEvent(
                    user_id=current_user.id,
                    **event_in.model_dump(),
                )
                db.add(event)
                await db.flush()
                results.append(BatchOperationResult(
                    action=op.action,
                    event_id=event.id,
                    success=True,
                ))
                success_count += 1

            elif op.action == "update":
                if not op.event_id:
                    raise ValueError("Missing event_id for update operation")
                existing_event = await db.get(CalendarEvent, op.event_id)
                if not existing_event or existing_event.user_id != current_user.id or existing_event.deleted_at:
                    raise ValueError("Event not found")

                if op.data:
                    event_update = CalendarEventUpdate(**op.data)
                    update_data = event_update.model_dump(exclude_unset=True)
                    for field, value in update_data.items():
                        setattr(existing_event, field, value)

                results.append(BatchOperationResult(
                    action=op.action,
                    event_id=op.event_id,
                    success=True,
                ))
                success_count += 1

            elif op.action == "delete":
                if not op.event_id:
                    raise ValueError("Missing event_id for delete operation")
                existing_event = await db.get(CalendarEvent, op.event_id)
                if not existing_event or existing_event.user_id != current_user.id:
                    raise ValueError("Event not found")

                existing_event.soft_delete()
                db.add(existing_event)

                results.append(BatchOperationResult(
                    action=op.action,
                    event_id=op.event_id,
                    success=True,
                ))
                success_count += 1

            else:
                raise ValueError(f"Unknown action: {op.action}")

        except Exception as e:
            results.append(BatchOperationResult(
                action=op.action,
                event_id=op.event_id,
                success=False,
                error=str(e),
            ))
            failure_count += 1
            logger.warning(f"Batch operation failed: {op.action} - {e}")

    await db.commit()

    return CalendarEventBatchResponse(
        results=results,
        success_count=success_count,
        failure_count=failure_count,
    )


@router.post("/{event_id}/restore")
async def restore_event(
    event_id: UUID = Path(..., description="事件 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    恢复已删除的日历事件
    """
    event = await db.get(CalendarEvent, event_id)
    if not event or event.user_id != current_user.id:
        raise NotFoundError(message="事件不存在")

    if not event.deleted_at:
        raise HTTPException(status_code=400, detail="事件未被删除")

    event.restore()
    db.add(event)
    await db.commit()

    logger.info(f"Calendar event restored: {event_id} by user {current_user.id}")

    return {"success": True, "data": CalendarEventDetail.model_validate(event)}
