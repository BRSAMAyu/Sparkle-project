"""
Notification Center API Endpoints

Provides unified access to notifications and analytics.
"""
from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.unified_notification import (
    NotificationAnalyticsResponse,
    NotificationHistoryFilters,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    UnifiedNotificationResponse,
)
from app.services.notification_analytics_service import NotificationAnalyticsService
from app.services.notification_center_service import NotificationCenterService

router = APIRouter(prefix="/notification-center", tags=["notification-center"])


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
    if source_type and source_type not in ['system', 'intervention']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_type: {source_type}. Must be 'system' or 'intervention'"
        )

    notifications = await service.get_unified_notifications(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        unread_only=unread_only,
        source_type=source_type
    )

    return notifications


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

    if notification_type not in ['system', 'intervention']:
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

    if notification_type not in ['system', 'intervention']:
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
        notification_level=prefs.notification_level,
        quiet_hours_enabled=prefs.quiet_hours_enabled,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end,
        updated_at=prefs.updated_at
    )


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

    return NotificationPreferencesResponse(
        user_id=prefs.user_id,
        enable_system=prefs.enable_system,
        enable_interventions=prefs.enable_interventions,
        notification_level=prefs.notification_level,
        quiet_hours_enabled=prefs.quiet_hours_enabled,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end,
        updated_at=prefs.updated_at
    )
