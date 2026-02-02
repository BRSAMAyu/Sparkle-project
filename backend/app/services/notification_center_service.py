"""
Notification Center Service

Provides unified access to system notifications and intervention requests.
"""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intervention import InterventionRequest
from app.models.notification import Notification
from app.models.notification_interaction import NotificationInteraction, NotificationPreferences
from app.schemas.unified_notification import (
    NotificationHistoryFilters,
    NotificationPreferencesUpdate,
    UnifiedNotificationResponse,
)


class NotificationCenterService:
    """
    Unified notification service combining system notifications and intervention requests.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_unified_notifications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
        source_type: str | None = None
    ) -> list[UnifiedNotificationResponse]:
        """
        Get unified list of notifications (system + interventions).

        Args:
            user_id: User UUID
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            unread_only: Only return unread notifications
            source_type: Filter by source ('system', 'intervention', or None for all)

        Returns:
            List of unified notifications sorted by created_at desc
        """
        notifications = []

        # Fetch system notifications
        if not source_type or source_type == 'system':
            system_stmt = select(Notification).where(Notification.user_id == user_id)

            if unread_only:
                system_stmt = system_stmt.where(not Notification.is_read)

            system_stmt = system_stmt.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
            system_result = await self.db.execute(system_stmt)
            system_notifications = system_result.scalars().all()

            for notif in system_notifications:
                notifications.append(self._system_to_unified(notif))

        # Fetch intervention requests
        if not source_type or source_type == 'intervention':
            # Determine status filter for "unread"
            # Intervention status: pending, approved, rejected, acknowledged, superseded
            intervention_statuses = ['pending', 'approved']
            if unread_only:
                intervention_statuses = ['pending']

            intervention_stmt = select(InterventionRequest).where(
                and_(
                    InterventionRequest.user_id == user_id,
                    InterventionRequest.status.in_(intervention_statuses)
                )
            )

            # Don't show expired interventions
            intervention_stmt = intervention_stmt.where(
                or_(
                    InterventionRequest.expires_at is None,
                    InterventionRequest.expires_at > datetime.utcnow()
                )
            )

            intervention_stmt = intervention_stmt.order_by(desc(InterventionRequest.created_at)).offset(skip).limit(limit)
            intervention_result = await self.db.execute(intervention_stmt)
            interventions = intervention_result.scalars().all()

            for intervention in interventions:
                notifications.append(self._intervention_to_unified(intervention))

        # Sort all by created_at descending
        notifications.sort(key=lambda x: x.created_at, reverse=True)

        # Apply limit after merging
        if len(notifications) > limit:
            notifications = notifications[:limit]

        return notifications

    async def mark_notification_read(
        self,
        user_id: UUID,
        notification_id: UUID,
        notification_type: str
    ) -> bool:
        """
        Mark a notification as read.

        Args:
            user_id: User UUID
            notification_id: Notification UUID
            notification_type: 'system' or 'intervention'

        Returns:
            True if marked successfully, False otherwise
        """
        try:
            if notification_type == 'system':
                # Mark Notification as read
                stmt = select(Notification).where(
                    and_(
                        Notification.id == notification_id,
                        Notification.user_id == user_id
                    )
                )
                result = await self.db.execute(stmt)
                notification = result.scalar_one_or_none()

                if notification:
                    notification.is_read = True
                    notification.read_at = datetime.utcnow()
                    await self.db.commit()

                    # Record interaction
                    await self._record_interaction(
                        user_id=user_id,
                        notification_type='system',
                        notification_id=notification_id,
                        action_type='viewed',
                        created_at=notification.created_at
                    )

                    return True

            elif notification_type == 'intervention':
                # Mark InterventionRequest as acknowledged
                stmt = select(InterventionRequest).where(
                    and_(
                        InterventionRequest.id == notification_id,
                        InterventionRequest.user_id == user_id
                    )
                )
                result = await self.db.execute(stmt)
                intervention = result.scalar_one_or_none()

                if intervention:
                    intervention.status = 'acknowledged'
                    await self.db.commit()

                    # Record interaction
                    await self._record_interaction(
                        user_id=user_id,
                        notification_type='intervention',
                        notification_id=notification_id,
                        action_type='viewed',
                        created_at=intervention.created_at
                    )

                    return True

            return False

        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            await self.db.rollback()
            return False

    async def mark_all_notifications_read(self, user_id: UUID) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: User UUID

        Returns:
            Number of notifications marked as read
        """
        count = 0

        try:
            # Mark all system notifications as read
            system_stmt = select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    not Notification.is_read
                )
            )
            result = await self.db.execute(system_stmt)
            unread_system = result.scalars().all()

            for notif in unread_system:
                notif.is_read = True
                notif.read_at = datetime.utcnow()
                count += 1

                # Record interaction
                await self._record_interaction(
                    user_id=user_id,
                    notification_type='system',
                    notification_id=notif.id,
                    action_type='viewed',
                    created_at=notif.created_at
                )

            # Mark all pending interventions as acknowledged
            intervention_stmt = select(InterventionRequest).where(
                and_(
                    InterventionRequest.user_id == user_id,
                    InterventionRequest.status == 'pending'
                )
            )
            result = await self.db.execute(intervention_stmt)
            pending_interventions = result.scalars().all()

            for intervention in pending_interventions:
                intervention.status = 'acknowledged'
                count += 1

                # Record interaction
                await self._record_interaction(
                    user_id=user_id,
                    notification_type='intervention',
                    notification_id=intervention.id,
                    action_type='viewed',
                    created_at=intervention.created_at
                )

            await self.db.commit()
            return count

        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            await self.db.rollback()
            return 0

    async def delete_notification(
        self,
        user_id: UUID,
        notification_id: UUID,
        notification_type: str
    ) -> bool:
        """
        Delete a notification.

        For system notifications: mark as read and optionally soft delete
        For interventions: cannot delete, only acknowledge

        Args:
            user_id: User UUID
            notification_id: Notification UUID
            notification_type: 'system' or 'intervention'

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if notification_type == 'system':
                stmt = select(Notification).where(
                    and_(
                        Notification.id == notification_id,
                        Notification.user_id == user_id
                    )
                )
                result = await self.db.execute(stmt)
                notification = result.scalar_one_or_none()

                if notification:
                    # Record dismiss interaction before deleting
                    await self._record_interaction(
                        user_id=user_id,
                        notification_type='system',
                        notification_id=notification_id,
                        action_type='dismissed',
                        created_at=notification.created_at
                    )

                    await self.db.delete(notification)
                    await self.db.commit()
                    return True

            elif notification_type == 'intervention':
                # Interventions can't be deleted, only acknowledged
                return await self.mark_notification_read(user_id, notification_id, 'intervention')

            return False

        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            await self.db.rollback()
            return False

    async def clear_read_notifications(self, user_id: UUID) -> int:
        """
        Clear all read notifications for a user.

        Args:
            user_id: User UUID

        Returns:
            Number of notifications deleted
        """
        count = 0

        try:
            # Delete read system notifications
            stmt = select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read
                )
            )
            result = await self.db.execute(stmt)
            read_notifications = result.scalars().all()

            for notif in read_notifications:
                await self.db.delete(notif)
                count += 1

            await self.db.commit()
            return count

        except Exception as e:
            logger.error(f"Error clearing read notifications: {e}")
            await self.db.rollback()
            return 0

    async def get_notification_history(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 50,
        filters: NotificationHistoryFilters | None = None
    ) -> dict[str, Any]:
        """
        Get paginated notification history with filters.

        Args:
            user_id: User UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            filters: Optional filters

        Returns:
            Dict with items, total, page, page_size, total_pages
        """
        filters = filters or NotificationHistoryFilters()
        offset = (page - 1) * page_size

        notifications = []
        total = 0

        # Fetch system notifications
        if not filters.type or filters.type == 'system' or filters.type == 'all':
            system_stmt = select(Notification).where(Notification.user_id == user_id)

            if filters.start_date:
                system_stmt = system_stmt.where(Notification.created_at >= filters.start_date)
            if filters.end_date:
                system_stmt = system_stmt.where(Notification.created_at <= filters.end_date)
            if filters.search:
                system_stmt = system_stmt.where(
                    or_(
                        Notification.title.ilike(f"%{filters.search}%"),
                        Notification.content.ilike(f"%{filters.search}%")
                    )
                )

            # Count total
            count_stmt = select(func.count()).select_from(system_stmt.subquery())
            count_result = await self.db.execute(count_stmt)
            system_total = count_result.scalar() or 0
            total += system_total

            # Fetch paginated
            system_stmt = system_stmt.order_by(desc(Notification.created_at)).offset(offset).limit(page_size)
            system_result = await self.db.execute(system_stmt)
            system_notifications = system_result.scalars().all()

            for notif in system_notifications:
                notifications.append(self._system_to_unified(notif))

        # Fetch interventions
        if not filters.type or filters.type == 'intervention' or filters.type == 'all':
            intervention_stmt = select(InterventionRequest).where(InterventionRequest.user_id == user_id)

            if filters.start_date:
                intervention_stmt = intervention_stmt.where(InterventionRequest.created_at >= filters.start_date)
            if filters.end_date:
                intervention_stmt = intervention_stmt.where(InterventionRequest.created_at <= filters.end_date)
            if filters.search:
                intervention_stmt = intervention_stmt.where(
                    InterventionRequest.topic.ilike(f"%{filters.search}%")
                )

            # Count total
            count_stmt = select(func.count()).select_from(intervention_stmt.subquery())
            count_result = await self.db.execute(count_stmt)
            intervention_total = count_result.scalar() or 0
            total += intervention_total

            # Fetch paginated
            intervention_stmt = intervention_stmt.order_by(desc(InterventionRequest.created_at)).offset(offset).limit(page_size)
            intervention_result = await self.db.execute(intervention_stmt)
            interventions = intervention_result.scalars().all()

            for intervention in interventions:
                notifications.append(self._intervention_to_unified(intervention))

        # Sort by created_at descending
        notifications.sort(key=lambda x: x.created_at, reverse=True)

        # Apply page_size limit after merging
        if len(notifications) > page_size:
            notifications = notifications[:page_size]

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "items": notifications,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    async def get_or_create_preferences(self, user_id: UUID) -> NotificationPreferences:
        """Get user notification preferences, create default if not exists"""
        stmt = select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
        result = await self.db.execute(stmt)
        prefs = result.scalar_one_or_none()

        if not prefs:
            prefs = NotificationPreferences(
                user_id=user_id,
                enable_system=True,
                enable_interventions=True,
                notification_level="standard",
                quiet_hours_enabled=False,
                updated_at=datetime.utcnow()
            )
            self.db.add(prefs)
            await self.db.commit()
            await self.db.refresh(prefs)

        return prefs

    async def update_preferences(
        self,
        user_id: UUID,
        update: NotificationPreferencesUpdate
    ) -> NotificationPreferences:
        """Update user notification preferences"""
        prefs = await self.get_or_create_preferences(user_id)

        if update.enable_system is not None:
            prefs.enable_system = update.enable_system
        if update.enable_interventions is not None:
            prefs.enable_interventions = update.enable_interventions
        if update.notification_level is not None:
            prefs.notification_level = update.notification_level
        if update.quiet_hours_enabled is not None:
            prefs.quiet_hours_enabled = update.quiet_hours_enabled
        if update.quiet_hours_start is not None:
            prefs.quiet_hours_start = update.quiet_hours_start
        if update.quiet_hours_end is not None:
            prefs.quiet_hours_end = update.quiet_hours_end

        prefs.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(prefs)

        return prefs

    async def _record_interaction(
        self,
        user_id: UUID,
        notification_type: str,
        notification_id: UUID,
        action_type: str,
        created_at: datetime
    ):
        """Record a notification interaction"""
        try:
            # Calculate time to action in seconds
            time_to_action = int((datetime.utcnow() - created_at).total_seconds())

            interaction = NotificationInteraction(
                id=uuid4(),
                user_id=user_id,
                notification_type=notification_type,
                notification_id=notification_id,
                action_type=action_type,
                action_time=datetime.utcnow(),
                time_to_action=time_to_action
            )
            self.db.add(interaction)
            await self.db.flush()  # Don't commit yet, let caller handle transaction

        except Exception as e:
            logger.error(f"Error recording interaction: {e}")

    def _system_to_unified(self, notification: Notification) -> UnifiedNotificationResponse:
        """Convert Notification model to UnifiedNotificationResponse"""
        return UnifiedNotificationResponse(
            id=str(notification.id),
            source_type="system",
            title=notification.title,
            content=notification.content,
            type=notification.type,
            priority="medium",
            is_read=notification.is_read,
            created_at=notification.created_at,
            read_at=notification.read_at,
            metadata=notification.data or {}
        )

    def _intervention_to_unified(self, intervention: InterventionRequest) -> UnifiedNotificationResponse:
        """Convert InterventionRequest to UnifiedNotificationResponse"""
        # Extract title from content or topic
        title = intervention.topic or "系统通知"
        content = ""

        if intervention.content:
            if isinstance(intervention.content, dict):
                content = intervention.content.get("message") or intervention.content.get("text", "")
            else:
                content = str(intervention.content)

        # Map intervention status to is_read
        is_read = intervention.status not in ['pending', 'approved']

        return UnifiedNotificationResponse(
            id=str(intervention.id),
            source_type="intervention",
            title=title,
            content=content or "请查看您的干预通知",
            type=intervention.intent_type or "intervention",
            priority="high" if intervention.requested_level in ['modal', 'card'] else "medium",
            is_read=is_read,
            created_at=intervention.created_at,
            read_at=None,  # Interventions don't have read_at, use status instead
            metadata={
                "status": intervention.status,
                "requested_level": intervention.requested_level,
                "final_level": intervention.final_level
            }
        )
