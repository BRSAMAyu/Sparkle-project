"""
Notification Center API Endpoints

Provides unified access to notifications and analytics.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.user import User
from app.schemas.unified_notification import (
    AuroraConfirmActionRequest,
    InterventionNotificationActionRequest,
    NotificationAnalyticsResponse,
    NotificationHistoryFilters,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    PushNotificationActionRequest,
    RecallNotificationFeedbackRequest,
    SuggestionActionRequest,
    UnifiedNotificationResponse,
)
from app.services.aurora_calibration_card_service import AuroraCalibrationCardService
from app.services.notification_analytics_service import NotificationAnalyticsService
from app.services.notification_center_service import NotificationCenterService
from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackService

router = APIRouter(prefix="/notification-center", tags=["notification-center"])

_SOURCE_TYPES = ("system", "intervention", "push", "aurora_confirm")
_NOTIFICATION_TYPES = ("system", "intervention", "push", "aurora_confirm")


# route-tier: authed
@router.get("/notifications", response_model=list[UnifiedNotificationResponse])
async def get_unified_notifications(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    unread_only: bool = Query(False, description="Only return unread notifications"),
    source_type: str | None = Query(None, description="Filter by source: system, intervention"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get unified list of notifications (system + interventions).

    Supports:
    - Pagination (skip, limit)
    - Filter by unread status
    - Filter by source type
    - Sorted by created_at descending
    """
    service = NotificationCenterService(db)

    # Validate source_type
    if source_type and source_type not in _SOURCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_type: {source_type}. Must be one of {', '.join(_SOURCE_TYPES)}"
        )

    notifications = await service.get_unified_notifications(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        unread_only=unread_only,
        source_type=source_type
    )

    return notifications


# route-tier: authed
@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    notification_type: str = Query(..., description="Notification type: system or intervention"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a notification as read.

    For system notifications: marks is_read=True and sets read_at
    For interventions: sets status='acknowledged'
    """
    service = NotificationCenterService(db)

    if notification_type not in _NOTIFICATION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid notification_type: {notification_type}"
        )

    success = await service.mark_notification_read(
        user_id=current_user.id,
        notification_id=notification_id,
        notification_type=notification_type
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Notification not found: {notification_id}"
        )

    return {"message": "Notification marked as read"}


# route-tier: authed
@router.put("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark all notifications as read for the current user.

    Returns the number of notifications marked as read.
    """
    service = NotificationCenterService(db)

    count = await service.mark_all_notifications_read(current_user.id)

    return {
        "message": f"Marked {count} notifications as read",
        "count": count
    }


# route-tier: authed
# NOTE(R2-EI-13): literal routes MUST be declared before same-shape parameterized
# routes; otherwise "/notifications/clear-read" is captured by
# "/notifications/{notification_id}" below and always fails UUID validation (422).
# route-tier: authed
@router.delete("/notifications/clear-read")
async def clear_read_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Clear all read notifications for the current user.

    Returns the number of notifications deleted.
    """
    service = NotificationCenterService(db)

    count = await service.clear_read_notifications(current_user.id)

    return {
        "message": f"Cleared {count} read notifications",
        "count": count
    }


# route-tier: authed
@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    notification_type: str = Query(..., description="Notification type: system or intervention"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a notification.

    For system notifications: permanently deletes
    For interventions: marks as acknowledged (cannot be deleted)
    """
    service = NotificationCenterService(db)

    if notification_type not in _NOTIFICATION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid notification_type: {notification_type}"
        )

    success = await service.delete_notification(
        user_id=current_user.id,
        notification_id=notification_id,
        notification_type=notification_type
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Notification not found: {notification_id}"
        )

    return {"message": "Notification deleted"}


# route-tier: internal
@router.post("/notifications/{notification_id}/intervention-action")
async def transition_intervention_notification(
    notification_id: UUID,
    request: InterventionNotificationActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Apply a real lifecycle action to a notification-backed intervention.

    Supported actions:
    - seen
    - accepted
    - acted
    - dismissed
    - snoozed
    """
    service = NotificationCenterService(db)

    success = await service.transition_intervention_notification(
        user_id=current_user.id,
        notification_id=notification_id,
        action=request.action,
        action_payload=request.action_payload or {},
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Intervention notification not found: {notification_id}",
        )

    return {"message": f"Intervention action applied: {request.action}"}


# route-tier: internal
@router.post("/notifications/{notification_id}/push-action")
async def transition_push_notification(
    notification_id: UUID,
    request: PushNotificationActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationCenterService(db)
    success = await service.transition_push_notification(
        user_id=current_user.id,
        notification_id=notification_id,
        action=request.action,
        action_payload=request.action_payload or {},
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Push notification not found: {notification_id}",
        )
    return {"message": f"Push action applied: {request.action}"}


# route-tier: internal
@router.post("/notifications/{notification_id}/recall-feedback")
async def record_recall_notification_feedback(
    notification_id: UUID,
    request: RecallNotificationFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationCenterService(db)
    success = await service.record_recall_notification_feedback(
        user_id=current_user.id,
        notification_id=notification_id,
        is_accurate=request.is_accurate,
        feedback_reason=request.feedback_reason,
        action_payload=request.action_payload or {},
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Recall notification not found: {notification_id}",
        )
    return {"message": "Recall notification feedback recorded"}


# route-tier: authed
@router.post("/notifications/{notification_id}/aurora-confirm-action")
async def transition_aurora_confirm_notification(
    notification_id: str,
    request: AuroraConfirmActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Apply a user response to an Aurora confirmation queue item (B4-INBOX).

    The notification id IS the calibration card (claim) id.  Delegates to the
    EXISTING calibration respond API — no new write path:
    - confirm: claim confirmed
    - incorrect: claim rejected (optionally with corrected_assumption)
    - mute: dismissed for now
    """
    service = AuroraCalibrationCardService(db, cache_service.redis)
    try:
        result = await service.respond(
            user_id=current_user.id,
            card_id=notification_id,
            response=request.action,
            reason=request.reason,
            corrected_assumption=request.corrected_assumption,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=f"Aurora confirm item not found: {notification_id}") from exc

    return {"message": f"Aurora confirm action applied: {request.action}", "card": result.get("card")}


# route-tier: authed
@router.post("/notifications/{notification_id}/suggestion-action")
async def record_suggestion_action(
    notification_id: UUID,
    request: SuggestionActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """P-03: record user feedback on a proactive suggestion card.

    四要素的两个「可忽略」入口：
    - ``ignore_today``（今天不再看）→ 该建议类型 24h 冷却（拒绝后 cooldown）。
    - ``mute_type``（不再提醒此类）→ 持久静音该建议类型。

    校验通知归属；反馈即已读；抑制态真实落库，nudge 生成路径据此抑制。
    """
    service = NotificationCenterService(db)
    notification = await service.get_system_notification(current_user.id, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=404,
            detail=f"Notification not found: {notification_id}",
        )

    suggestion_type = (notification.type or "").strip()
    if not suggestion_type:
        raise HTTPException(
            status_code=400,
            detail="Notification has no suggestion type to act on",
        )

    if request.action not in ("ignore_today", "mute_type"):
        # 双保险：schema pattern 之外，handler 层显式拒绝未知动作。
        raise HTTPException(
            status_code=422,
            detail=f"Invalid suggestion action: {request.action}",
        )

    feedback = ProactiveSuggestionFeedbackService(db)
    if request.action == "ignore_today":
        suppression = await feedback.record_ignore_today(current_user.id, suggestion_type)
    else:
        suppression = await feedback.record_mute(current_user.id, suggestion_type)

    # 反馈即已读：处理过的建议不再挂未读角标。
    await service.mark_notification_read(current_user.id, notification_id, "system")

    logger.info(
        "Suggestion feedback recorded: user={} type={} action={}",
        current_user.id, suggestion_type, request.action,
    )
    return {
        "message": f"Suggestion feedback recorded: {request.action}",
        "suppression": suppression,
    }


# route-tier: internal
@router.post("/interventions/{record_id}/action")
async def transition_intervention_record(
    record_id: UUID,
    request: InterventionNotificationActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Apply a lifecycle action to an InterventionRecord directly.

    Used by chat, push-open, focus mode, and task execution surfaces when the
    client only has the card-protocol intervention identifier.
    """
    service = NotificationCenterService(db)

    success = await service.transition_intervention_record(
        user_id=current_user.id,
        record_id=record_id,
        action=request.action,
        action_payload=request.action_payload or {},
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Intervention record not found: {record_id}",
        )

    return {"message": f"Intervention record action applied: {request.action}"}


# route-tier: authed
@router.get("/history")
async def get_notification_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    type: str | None = Query(None, description="Filter by type: all, system, intervention"),
    start_date: str | None = Query(None, description="Start date (ISO format)"),
    end_date: str | None = Query(None, description="End date (ISO format)"),
    search: str | None = Query(None, description="Search in title/content"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated notification history with filters.

    Supports:
    - Pagination
    - Filter by type
    - Date range filtering
    - Keyword search
    """
    service = NotificationCenterService(db)

    # Parse filters
    from datetime import datetime
    filters = NotificationHistoryFilters(
        type=type,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        search=search
    )

    result = await service.get_notification_history(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        filters=filters
    )

    return result


# route-tier: authed
@router.get("/analytics", response_model=NotificationAnalyticsResponse)
async def get_notification_analytics(
    period: str = Query("7d", description="Time period: 1d, 7d, 30d, all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get notification analytics and usage statistics.

    Returns:
    - Summary: total sent, viewed, clicked, view rate, click rate, avg time to action
    - By type: breakdown for system vs intervention
    - Trends: daily data for the period
    - Hourly distribution: 24-hour activity profile

    Cached for 1 hour in Redis.
    """
    service = NotificationAnalyticsService(db)

    # Validate period
    valid_periods = ['1d', '7d', '30d', 'all']
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period: {period}. Must be one of {valid_periods}"
        )

    analytics = await service.get_analytics(
        user_id=current_user.id,
        period=period
    )

    return analytics


# route-tier: authed
@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user notification preferences.
    """
    service = NotificationCenterService(db)

    prefs = await service.get_or_create_preferences(current_user.id)

    return NotificationPreferencesResponse(
        user_id=prefs.user_id,
        enable_system=prefs.enable_system,
        enable_interventions=prefs.enable_interventions,
        disabled_types=prefs.disabled_types or [],
        notification_level=prefs.notification_level,
        quiet_hours_enabled=prefs.quiet_hours_enabled,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end,
        updated_at=prefs.updated_at
    )


# route-tier: authed
@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    update: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user notification preferences.

    Fields:
    - enable_system: Enable/disable system notifications
    - enable_interventions: Enable/disable intervention notifications
    - notification_level: minimal, standard, or verbose
    - quiet_hours_enabled: Enable quiet hours
    - quiet_hours_start: Start time in HH:MM format
    - quiet_hours_end: End time in HH:MM format
    """
    service = NotificationCenterService(db)

    prefs = await service.update_preferences(current_user.id, update)

    # Sync to UserPreferencesCenter for PreferenceConsumptionService
    try:
        from app.services.personalization.preference_service import PreferenceService
        pref_service = PreferenceService(db, cache_service.redis)
        notif_prefs = {
            "notification_level": prefs.notification_level or "standard",
            "enable_system": prefs.enable_system,
            "enable_interventions": prefs.enable_interventions,
            "disabled_types": list(prefs.disabled_types or []),
            "quiet_hours_enabled": prefs.quiet_hours_enabled or False,
            "quiet_hours_start": prefs.quiet_hours_start or "22:00",
            "quiet_hours_end": prefs.quiet_hours_end or "08:00",
        }
        await pref_service.update_explicit(current_user.id, {
            "notification_preferences": notif_prefs,
        })
    except Exception as e:
        logger.warning(f"Failed to sync notification preferences to UserPreferencesCenter: {e}")

    return NotificationPreferencesResponse(
        user_id=prefs.user_id,
        enable_system=prefs.enable_system,
        enable_interventions=prefs.enable_interventions,
        disabled_types=prefs.disabled_types or [],
        notification_level=prefs.notification_level,
        quiet_hours_enabled=prefs.quiet_hours_enabled,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end,
        updated_at=prefs.updated_at
    )
