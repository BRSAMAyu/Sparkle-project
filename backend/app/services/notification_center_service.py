"""
Notification Center Service

Provides unified access to system notifications and intervention requests.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import InterventionAcceptanceStatus, InterventionRecord
from app.models.intervention import InterventionRequest
from app.models.notification import Notification
from app.models.notification_interaction import NotificationInteraction, NotificationPreferences
from app.models.push_delivery_record import PushDeliveryRecord
from app.schemas.notification import NotificationCreate
from app.schemas.unified_notification import (
    NotificationHistoryFilters,
    NotificationPreferencesUpdate,
    UnifiedNotificationResponse,
)
from app.services.intervention_record_service import InterventionRecordService
from app.services.notification_service import NotificationService
from app.services.push_delivery_service import PushDeliveryService


def _escape_like(value: str) -> str:
    """Escape LIKE wildcard characters % and _ for safe use in ilike patterns."""
    return re.sub(r"([%_])", r"\\\1", value)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


SPACED_REPETITION_NOTIFICATION_TYPE = "spaced_repetition_reminder"
SPACED_REPETITION_CATEGORY = "spaced_repetition"
SPACED_REPETITION_MIN_COOLDOWN_DAYS = 1
SPACED_REPETITION_ESTIMATED_MINUTES = 10


class NotificationCenterService:
    """
    Unified notification service combining system notifications and intervention requests.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_spaced_repetition_reminder(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        node_name: str,
        interval_days: int,
        mastery: float,
        estimated_minutes: int = SPACED_REPETITION_ESTIMATED_MINUTES,
        now: datetime | None = None,
    ) -> Notification | None:
        """Create and push an Aurora spaced-repetition reminder for one Galaxy node."""
        reference_time = now or _utcnow()
        if await self.has_recent_spaced_repetition_reminder(
            user_id=user_id,
            node_id=node_id,
            now=reference_time,
        ):
            return None

        display_name = (node_name or "这个知识点").strip()
        title = "Aurora 复习提醒"
        content = (
            f"{display_name}已经 {interval_days} 天没复习了，"
            f"今天花 {estimated_minutes} 分钟巩固一下是最佳时机。"
        )
        route = f"/galaxy?nodeId={node_id}"

        return await NotificationService.create(
            self.db,
            user_id,
            NotificationCreate(
                title=title,
                content=content,
                type=SPACED_REPETITION_NOTIFICATION_TYPE,
                data={
                    "source_type": "push",
                    "category": SPACED_REPETITION_CATEGORY,
                    "node_id": str(node_id),
                    "node_name": display_name,
                    "mastery": round(float(mastery), 4),
                    "interval_days": interval_days,
                    "estimated_minutes": estimated_minutes,
                    "deep_link": route,
                    "route": route,
                    "primary_action": {
                        "label": "开始复习",
                        "route": route,
                        "action_type": "galaxy_node_review",
                        "payload": {
                            "node_id": str(node_id),
                            "review_mode": "spaced_repetition",
                        },
                    },
                },
            ),
            push_via_websocket=True,
        )

    async def has_recent_spaced_repetition_reminder(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        now: datetime | None = None,
        min_interval_days: int = SPACED_REPETITION_MIN_COOLDOWN_DAYS,
    ) -> bool:
        """Return True if this node already received a recent review reminder."""
        reference_time = now or _utcnow()
        since = reference_time - timedelta(days=max(1, min_interval_days))
        result = await self.db.execute(
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.type == SPACED_REPETITION_NOTIFICATION_TYPE,
                Notification.created_at >= since,
                Notification.deleted_at.is_(None),
            )
            .order_by(desc(Notification.created_at))
        )
        target_node_id = str(node_id)
        for notification in result.scalars().all():
            if str((notification.data or {}).get("node_id") or "") == target_node_id:
                return True
        return False

    async def get_unified_notifications(
        self, user_id: UUID, skip: int = 0, limit: int = 50, unread_only: bool = False, source_type: str | None = None
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
        if not source_type or source_type == "system":
            system_stmt = select(Notification).where(
                Notification.user_id == user_id,
                ~self._is_intervention_notification(),
                ~self._is_push_notification(),
            )

            if unread_only:
                system_stmt = system_stmt.where(Notification.is_read.is_(False))

            system_stmt = system_stmt.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
            system_result = await self.db.execute(system_stmt)
            system_notifications = system_result.scalars().all()

            for notif in system_notifications:
                notifications.append(self._system_to_unified(notif))

        # Fetch intervention requests
        if not source_type or source_type == "intervention":
            intervention_notif_stmt = select(Notification).where(
                Notification.user_id == user_id,
                self._is_intervention_notification(),
            )

            if unread_only:
                intervention_notif_stmt = intervention_notif_stmt.where(Notification.is_read.is_(False))

            intervention_notif_stmt = (
                intervention_notif_stmt.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
            )
            intervention_notif_result = await self.db.execute(intervention_notif_stmt)
            intervention_notifications = intervention_notif_result.scalars().all()
            enriched_intervention_records = await self._load_intervention_records_for_notifications(
                intervention_notifications
            )

            for notif in intervention_notifications:
                notifications.append(
                    self._system_to_unified(
                        notif,
                        intervention_record=enriched_intervention_records.get(notif.id),
                    )
                )

            # Determine status filter for "unread"
            # Intervention status: pending, approved, rejected, acknowledged, superseded
            intervention_statuses = ["pending", "approved"]
            if unread_only:
                intervention_statuses = ["pending"]

            intervention_stmt = select(InterventionRequest).where(
                and_(InterventionRequest.user_id == user_id, InterventionRequest.status.in_(intervention_statuses))
            )

            # Don't show expired interventions
            intervention_stmt = intervention_stmt.where(
                or_(InterventionRequest.expires_at.is_(None), InterventionRequest.expires_at > _utcnow())
            )

            intervention_stmt = (
                intervention_stmt.order_by(desc(InterventionRequest.created_at)).offset(skip).limit(limit)
            )
            intervention_result = await self.db.execute(intervention_stmt)
            interventions = intervention_result.scalars().all()

            for intervention in interventions:
                notifications.append(self._intervention_to_unified(intervention))

        if not source_type or source_type == "push":
            push_stmt = select(Notification).where(
                Notification.user_id == user_id,
                self._is_push_notification(),
                Notification.deleted_at.is_(None),
            )
            if unread_only:
                push_stmt = push_stmt.where(Notification.is_read.is_(False))
            push_stmt = push_stmt.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
            push_result = await self.db.execute(push_stmt)
            push_notifications = push_result.scalars().all()
            push_records = await self._load_push_records_for_notifications(push_notifications)
            for notif in push_notifications:
                notifications.append(
                    self._system_to_unified(
                        notif,
                        push_record=push_records.get(notif.id),
                    )
                )

        # Sort all by created_at descending
        notifications.sort(key=lambda x: x.created_at, reverse=True)
        notifications = self._dedupe_unified_notifications(notifications)

        # Apply limit after merging
        if len(notifications) > limit:
            notifications = notifications[:limit]

        return notifications

    async def mark_notification_read(self, user_id: UUID, notification_id: UUID, notification_type: str) -> bool:
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
            if notification_type == "system":
                # Mark Notification as read
                stmt = select(Notification).where(
                    and_(Notification.id == notification_id, Notification.user_id == user_id)
                )
                result = await self.db.execute(stmt)
                notification = result.scalar_one_or_none()

                if notification:
                    notification.is_read = True
                    notification.read_at = _utcnow()
                    await self.db.commit()

                    # Record interaction
                    await self._record_interaction(
                        user_id=user_id,
                        notification_type="system",
                        notification_id=notification_id,
                        action_type="viewed",
                        created_at=notification.created_at,
                    )

                    return True

            elif notification_type == "push":
                delivery_service = PushDeliveryService(self.db)
                record = await delivery_service.apply_action(
                    user_id=user_id,
                    notification_id=notification_id,
                    action="seen",
                )
                return record is not None

            elif notification_type == "intervention":
                notification_stmt = select(Notification).where(
                    and_(
                        Notification.id == notification_id,
                        Notification.user_id == user_id,
                        self._is_intervention_notification(),
                    )
                )
                result = await self.db.execute(notification_stmt)
                notification = result.scalar_one_or_none()

                if notification:
                    return await self.transition_intervention_notification(
                        user_id=user_id,
                        notification_id=notification_id,
                        action="seen",
                        action_payload={"source": "notification_center.mark_read"},
                    )

                # Mark InterventionRequest as acknowledged (legacy flow fallback)
                stmt = select(InterventionRequest).where(
                    and_(InterventionRequest.id == notification_id, InterventionRequest.user_id == user_id)
                )
                result = await self.db.execute(stmt)
                intervention = result.scalar_one_or_none()

                if intervention:
                    intervention.status = "acknowledged"
                    await self.db.commit()

                    # Record interaction
                    await self._record_interaction(
                        user_id=user_id,
                        notification_type="intervention",
                        notification_id=notification_id,
                        action_type="viewed",
                        created_at=intervention.created_at,
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

        Uses bulk UPDATE + batch INSERT for interactions instead of
        per-row ORM updates to avoid N+1 query pattern.

        Args:
            user_id: User UUID

        Returns:
            Number of notifications marked as read
        """
        count = 0
        now = _utcnow()

        try:
            # --- Bulk UPDATE: system (non-intervention) notifications ---
            system_ids_stmt = select(Notification.id, Notification.created_at).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                    ~self._is_intervention_notification(),
                )
            )
            result = await self.db.execute(system_ids_stmt)
            system_rows = result.all()

            if system_rows:
                system_ids = [row.id for row in system_rows]
                await self.db.execute(
                    sa_update(Notification)
                    .where(Notification.id.in_(system_ids))
                    .values(is_read=True, read_at=now)
                )
                count += len(system_ids)

                # Batch INSERT interactions
                self.db.add_all([
                    NotificationInteraction(
                        id=uuid4(),
                        user_id=user_id,
                        notification_type="system",
                        notification_id=row.id,
                        action_type="viewed",
                        action_time=now,
                        time_to_action=max(0, int((now - row.created_at).total_seconds())),
                    )
                    for row in system_rows
                ])

            # --- Intervention notifications: must loop for side effects ---
            intervention_notification_stmt = select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                    self._is_intervention_notification(),
                )
            )
            result = await self.db.execute(intervention_notification_stmt)
            unread_intervention_notifications = result.scalars().all()

            for notif in unread_intervention_notifications:
                notif.is_read = True
                notif.read_at = now
                count += 1

                record_id = self._extract_notification_record_id(notif)
                if record_id:
                    await self._apply_intervention_record_action(
                        user_id=user_id,
                        record_id=record_id,
                        action="seen",
                        action_payload={"source": "notification_center.mark_all_read"},
                    )

                await self._record_interaction(
                    user_id=user_id,
                    notification_type="intervention",
                    notification_id=notif.id,
                    action_type="viewed",
                    created_at=notif.created_at,
                )

            # --- Bulk UPDATE: pending intervention requests ---
            intervention_ids_stmt = select(InterventionRequest.id, InterventionRequest.created_at).where(
                and_(InterventionRequest.user_id == user_id, InterventionRequest.status == "pending")
            )
            result = await self.db.execute(intervention_ids_stmt)
            intervention_rows = result.all()

            if intervention_rows:
                intervention_ids = [row.id for row in intervention_rows]
                await self.db.execute(
                    sa_update(InterventionRequest)
                    .where(InterventionRequest.id.in_(intervention_ids))
                    .values(status="acknowledged")
                )
                count += len(intervention_ids)

                # Batch INSERT interactions
                self.db.add_all([
                    NotificationInteraction(
                        id=uuid4(),
                        user_id=user_id,
                        notification_type="intervention",
                        notification_id=row.id,
                        action_type="viewed",
                        action_time=now,
                        time_to_action=max(0, int((now - row.created_at).total_seconds())),
                    )
                    for row in intervention_rows
                ])

            await self.db.commit()
            return count

        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            await self.db.rollback()
            return 0

    async def delete_notification(self, user_id: UUID, notification_id: UUID, notification_type: str) -> bool:
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
            if notification_type == "system":
                stmt = select(Notification).where(
                    and_(
                        Notification.id == notification_id,
                        Notification.user_id == user_id,
                        ~self._is_intervention_notification(),
                    )
                )
                result = await self.db.execute(stmt)
                notification = result.scalar_one_or_none()

                if notification:
                    # Record dismiss interaction before deleting
                    await self._record_interaction(
                        user_id=user_id,
                        notification_type="system",
                        notification_id=notification_id,
                        action_type="dismissed",
                        created_at=notification.created_at,
                    )

                    await self.db.delete(notification)
                    await self.db.commit()
                    return True

            elif notification_type == "push":
                delivery_service = PushDeliveryService(self.db)
                record = await delivery_service.apply_action(
                    user_id=user_id,
                    notification_id=notification_id,
                    action="dismissed",
                )
                return record is not None

            elif notification_type == "intervention":
                notification_stmt = select(Notification).where(
                    and_(
                        Notification.id == notification_id,
                        Notification.user_id == user_id,
                        self._is_intervention_notification(),
                    )
                )
                result = await self.db.execute(notification_stmt)
                notification = result.scalar_one_or_none()

                if notification:
                    record_id = self._extract_notification_record_id(notification)
                    if record_id:
                        await self._apply_intervention_record_action(
                            user_id=user_id,
                            record_id=record_id,
                            action="dismissed",
                            action_payload={"source": "notification_center.delete"},
                        )
                    await self._record_interaction(
                        user_id=user_id,
                        notification_type="intervention",
                        notification_id=notification_id,
                        action_type="dismissed",
                        created_at=notification.created_at,
                    )
                    await self.db.delete(notification)
                    await self.db.commit()
                    return True

                # Legacy interventions can't be deleted, only acknowledged
                return await self.mark_notification_read(user_id, notification_id, "intervention")

            return False

        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            await self.db.rollback()
            return False

    async def transition_intervention_notification(
        self,
        user_id: UUID,
        notification_id: UUID,
        action: str,
        action_payload: dict[str, Any] | None = None,
    ) -> bool:
        """Apply a mobile/user interaction to a notification-backed intervention."""
        action_payload = dict(action_payload or {})
        try:
            stmt = select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                    self._is_intervention_notification(),
                )
            )
            result = await self.db.execute(stmt)
            notification = result.scalar_one_or_none()
            if not notification:
                return False

            if action in {"seen", "accepted", "acted", "dismissed"} and not notification.is_read:
                notification.is_read = True
                notification.read_at = _utcnow()

            record_id = self._extract_notification_record_id(notification)
            if record_id:
                await self._apply_intervention_record_action(
                    user_id=user_id,
                    record_id=record_id,
                    action=action,
                    action_payload={
                        **action_payload,
                        "notification_id": str(notification.id),
                        "notification_type": notification.type,
                    },
                )

            await self._record_interaction(
                user_id=user_id,
                notification_type="intervention",
                notification_id=notification_id,
                action_type=self._interaction_action_for_intervention_action(action),
                created_at=notification.created_at,
            )
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error applying intervention action: {e}")
            await self.db.rollback()
            return False

    async def transition_push_notification(
        self,
        user_id: UUID,
        notification_id: UUID,
        action: str,
        action_payload: dict[str, Any] | None = None,
    ) -> bool:
        del action_payload
        try:
            delivery_service = PushDeliveryService(self.db)
            record = await delivery_service.apply_action(
                user_id=user_id,
                notification_id=notification_id,
                action=action,
            )
            if not record:
                return False
            await self._record_interaction(
                user_id=user_id,
                notification_type="push",
                notification_id=notification_id,
                action_type=action,
                created_at=record.created_at,
            )
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error applying push action: {e}")
            await self.db.rollback()
            return False

    async def transition_intervention_record(
        self,
        user_id: UUID,
        record_id: UUID,
        action: str,
        action_payload: dict[str, Any] | None = None,
    ) -> bool:
        """Apply a lifecycle action directly to an InterventionRecord."""
        action_payload = dict(action_payload or {})
        try:
            record = await self.db.get(InterventionRecord, record_id)
            if not record or record.user_id != user_id:
                return False

            notification = await self._find_notification_for_record(user_id, record_id)
            if notification and action in {"seen", "accepted", "acted", "dismissed"} and not notification.is_read:
                notification.is_read = True
                notification.read_at = _utcnow()

            await self._apply_intervention_record_action(
                user_id=user_id,
                record_id=record_id,
                action=action,
                action_payload={
                    **action_payload,
                    "record_id": str(record_id),
                    **(
                        {
                            "notification_id": str(notification.id),
                            "notification_type": notification.type,
                        }
                        if notification
                        else {}
                    ),
                },
            )

            await self._record_interaction(
                user_id=user_id,
                notification_type="intervention",
                notification_id=notification.id if notification else record.id,
                action_type=self._interaction_action_for_intervention_action(action),
                created_at=notification.created_at if notification else record.created_at or _utcnow(),
            )
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error applying direct intervention action: {e}")
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
                    Notification.is_read,
                    ~self._is_intervention_notification(),
                    ~self._is_push_notification(),
                )
            )
            result = await self.db.execute(stmt)
            read_notifications = result.scalars().all()

            for notif in read_notifications:
                await self.db.delete(notif)
                count += 1

            push_stmt = select(PushDeliveryRecord).where(
                PushDeliveryRecord.user_id == user_id,
                PushDeliveryRecord.read_at.is_not(None),
                PushDeliveryRecord.deleted_at.is_(None),
                PushDeliveryRecord.retracted_at.is_(None),
            )
            push_result = await self.db.execute(push_stmt)
            push_records = push_result.scalars().all()
            notification_ids = [record.notification_id for record in push_records if record.notification_id]
            notifications_by_id: dict[UUID, Notification] = {}
            if notification_ids:
                linked_result = await self.db.execute(
                    select(Notification).where(
                        Notification.user_id == user_id,
                        Notification.id.in_(notification_ids),
                    )
                )
                notifications_by_id = {
                    notification.id: notification for notification in linked_result.scalars().all()
                }

            for record in push_records:
                record.deleted_at = _utcnow()
                if record.notification_id:
                    notification = notifications_by_id.get(record.notification_id)
                    if notification is not None:
                        notification.deleted_at = _utcnow()
                count += 1

            await self.db.commit()
            return count

        except Exception as e:
            logger.error(f"Error clearing read notifications: {e}")
            await self.db.rollback()
            return 0

    async def get_notification_history(
        self, user_id: UUID, page: int = 1, page_size: int = 50, filters: NotificationHistoryFilters | None = None
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
        if not filters.type or filters.type == "system" or filters.type == "all":
            system_stmt = select(Notification).where(
                Notification.user_id == user_id,
                ~self._is_intervention_notification(),
            )

            if filters.start_date:
                system_stmt = system_stmt.where(Notification.created_at >= filters.start_date)
            if filters.end_date:
                system_stmt = system_stmt.where(Notification.created_at <= filters.end_date)
            if filters.search:
                system_stmt = system_stmt.where(
                    or_(
                        Notification.title.ilike(f"%{_escape_like(filters.search)}%"),
                        Notification.content.ilike(f"%{_escape_like(filters.search)}%"),
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
        if not filters.type or filters.type == "intervention" or filters.type == "all":
            intervention_notification_stmt = select(Notification).where(
                Notification.user_id == user_id,
                self._is_intervention_notification(),
            )

            if filters.start_date:
                intervention_notification_stmt = intervention_notification_stmt.where(
                    Notification.created_at >= filters.start_date
                )
            if filters.end_date:
                intervention_notification_stmt = intervention_notification_stmt.where(
                    Notification.created_at <= filters.end_date
                )
            if filters.search:
                intervention_notification_stmt = intervention_notification_stmt.where(
                    or_(
                        Notification.title.ilike(f"%{_escape_like(filters.search)}%"),
                        Notification.content.ilike(f"%{_escape_like(filters.search)}%"),
                    )
                )

            count_stmt = select(func.count()).select_from(intervention_notification_stmt.subquery())
            count_result = await self.db.execute(count_stmt)
            intervention_notification_total = count_result.scalar() or 0
            total += intervention_notification_total

            intervention_notification_stmt = (
                intervention_notification_stmt.order_by(desc(Notification.created_at)).offset(offset).limit(page_size)
            )
            intervention_notification_result = await self.db.execute(intervention_notification_stmt)
            intervention_notifications = intervention_notification_result.scalars().all()
            enriched_intervention_records = await self._load_intervention_records_for_notifications(
                intervention_notifications
            )

            for notif in intervention_notifications:
                notifications.append(
                    self._system_to_unified(
                        notif,
                        intervention_record=enriched_intervention_records.get(notif.id),
                    )
                )

            intervention_stmt = select(InterventionRequest).where(InterventionRequest.user_id == user_id)

            if filters.start_date:
                intervention_stmt = intervention_stmt.where(InterventionRequest.created_at >= filters.start_date)
            if filters.end_date:
                intervention_stmt = intervention_stmt.where(InterventionRequest.created_at <= filters.end_date)
            if filters.search:
                intervention_stmt = intervention_stmt.where(InterventionRequest.topic.ilike(f"%{_escape_like(filters.search)}%"))

            # Count total
            count_stmt = select(func.count()).select_from(intervention_stmt.subquery())
            count_result = await self.db.execute(count_stmt)
            intervention_total = count_result.scalar() or 0
            total += intervention_total

            # Fetch paginated
            intervention_stmt = (
                intervention_stmt.order_by(desc(InterventionRequest.created_at)).offset(offset).limit(page_size)
            )
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
            "total_pages": total_pages,
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
                updated_at=_utcnow(),
            )
            self.db.add(prefs)
            await self.db.commit()
            await self.db.refresh(prefs)

        return prefs

    async def update_preferences(self, user_id: UUID, update: NotificationPreferencesUpdate) -> NotificationPreferences:
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

        prefs.updated_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(prefs)

        return prefs

    async def _record_interaction(
        self, user_id: UUID, notification_type: str, notification_id: UUID, action_type: str, created_at: datetime
    ):
        """Record a notification interaction"""
        try:
            # Calculate time to action in seconds
            time_to_action = max(0, int((_utcnow() - created_at).total_seconds()))

            interaction = NotificationInteraction(
                id=uuid4(),
                user_id=user_id,
                notification_type=notification_type,
                notification_id=notification_id,
                action_type=action_type,
                action_time=_utcnow(),
                time_to_action=time_to_action,
            )
            self.db.add(interaction)
            await self.db.flush()  # Don't commit yet, let caller handle transaction

        except Exception as e:
            logger.error(f"Error recording interaction: {e}")

    async def _apply_intervention_record_action(
        self,
        user_id: UUID,
        record_id: UUID,
        action: str,
        action_payload: dict[str, Any] | None = None,
    ) -> None:
        record = await self.db.get(InterventionRecord, record_id)
        if not record or record.user_id != user_id:
            return

        service = InterventionRecordService(self.db)
        payload = dict(action_payload or {})

        if action == "seen":
            if record.acceptance_status == InterventionAcceptanceStatus.DELIVERED:
                await service.mark_seen(record.id)
            return

        if action == "accepted":
            if record.acceptance_status in {
                InterventionAcceptanceStatus.DELIVERED,
                InterventionAcceptanceStatus.SEEN,
                InterventionAcceptanceStatus.SNOOZED,
            }:
                await service.mark_accepted(record.id)
            await self._materialize_specialized_repair_task_if_needed(
                user_id=user_id,
                record_id=record.id,
                action_payload=payload,
            )
            return

        if action == "acted":
            if record.acceptance_status in {
                InterventionAcceptanceStatus.DELIVERED,
                InterventionAcceptanceStatus.SEEN,
                InterventionAcceptanceStatus.SNOOZED,
            }:
                await service.mark_accepted(record.id)
            materialized_payload = await self._materialize_specialized_repair_task_if_needed(
                user_id=user_id,
                record_id=record.id,
                action_payload=payload,
            )
            if record.acceptance_status == InterventionAcceptanceStatus.ACCEPTED:
                await service.mark_acted(record.id, action_payload={**payload, **materialized_payload})
            return

        if action == "dismissed":
            if record.acceptance_status in {
                InterventionAcceptanceStatus.DELIVERED,
                InterventionAcceptanceStatus.SEEN,
                InterventionAcceptanceStatus.SNOOZED,
            }:
                await service.mark_dismissed(record.id)
            return

        if action == "snoozed":
            if record.acceptance_status in {
                InterventionAcceptanceStatus.DELIVERED,
                InterventionAcceptanceStatus.SEEN,
            }:
                snooze_hours = int(payload.get("snooze_hours", 24))
                await service.mark_snoozed(record.id, snooze_hours=snooze_hours)

    async def _materialize_specialized_repair_task_if_needed(
        self,
        *,
        user_id: UUID,
        record_id: UUID,
        action_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = await self.db.get(InterventionRecord, record_id)
        if not record or record.user_id != user_id:
            return {}
        if not dict(record.diagnosis_payload or {}).get("specialized_repair"):
            return {}

        from app.services.error_replan_bridge import ErrorReplanBridge

        return await ErrorReplanBridge(self.db).materialize_specialized_repair_task_from_record(
            user_id=user_id,
            record=record,
            action_payload=action_payload,
        )

    @staticmethod
    def _extract_notification_record_id(notification: Notification) -> UUID | None:
        raw = (notification.data or {}).get("record_id")
        if not raw:
            return None
        try:
            return UUID(str(raw))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _interaction_action_for_intervention_action(action: str) -> str:
        return {
            "seen": "viewed",
            "accepted": "accepted",
            "acted": "acted",
            "dismissed": "dismissed",
            "snoozed": "snoozed",
        }.get(action, action)

    def _system_to_unified(
        self,
        notification: Notification,
        intervention_record: InterventionRecord | None = None,
        push_record: PushDeliveryRecord | None = None,
    ) -> UnifiedNotificationResponse:
        """Convert Notification model to UnifiedNotificationResponse"""
        source_type = "intervention" if self._notification_is_intervention(notification) else "system"
        if self._notification_is_push(notification):
            source_type = "push"
        priority = "high" if source_type == "intervention" and notification.type == "intervention_push" else "medium"
        metadata = dict(notification.data or {})
        if intervention_record:
            metadata.update(
                {
                    "acceptance_status": intervention_record.acceptance_status.value,
                    "outcome_status": intervention_record.outcome_status.value,
                    "outcome_window_days": intervention_record.outcome_window_days,
                }
            )
            if intervention_record.evidence_payload:
                metadata["outcome_evidence"] = intervention_record.evidence_payload
            if intervention_record.action_payload:
                if intervention_record.action_payload.get("acted_at"):
                    metadata["acted_at"] = intervention_record.action_payload.get("acted_at")
                if intervention_record.action_payload.get("parameter_compilation"):
                    metadata["parameter_compilation"] = intervention_record.action_payload.get("parameter_compilation")
        if push_record:
            metadata.update(
                {
                    "category": push_record.category,
                    "policy_id": push_record.policy_id,
                    "message_template_id": push_record.message_template_id,
                    "delivery_record_id": str(push_record.id),
                    "delivery_channel": push_record.delivery_channel,
                    "retractable_until": (
                        push_record.retractable_until.isoformat() if push_record.retractable_until else None
                    ),
                    "push_status": push_record.status,
                }
            )
            metadata.setdefault("context_variables", push_record.metadata_payload or {})
        return UnifiedNotificationResponse(
            id=str(notification.id),
            source_type=source_type,
            title=notification.title,
            content=notification.content,
            type=notification.type,
            priority=priority,
            is_read=notification.is_read,
            created_at=notification.created_at,
            read_at=notification.read_at,
            metadata=metadata,
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
        is_read = intervention.status not in ["pending", "approved"]

        return UnifiedNotificationResponse(
            id=str(intervention.id),
            source_type="intervention",
            title=title,
            content=content or "请查看您的干预通知",
            type=intervention.intent_type or "intervention",
            priority="high" if intervention.requested_level in ["modal", "card"] else "medium",
            is_read=is_read,
            created_at=intervention.created_at,
            read_at=None,  # Interventions don't have read_at, use status instead
            metadata={
                "status": intervention.status,
                "requested_level": intervention.requested_level,
                "final_level": intervention.final_level,
            },
        )

    def _dedupe_unified_notifications(
        self,
        notifications: list[UnifiedNotificationResponse],
    ) -> list[UnifiedNotificationResponse]:
        """
        Collapse exact duplicate entries that can appear when the same
        notification is materialized more than once upstream.
        """
        deduped: list[UnifiedNotificationResponse] = []
        seen_ids: set[str] = set()
        seen_fingerprints: set[str] = set()

        for notification in notifications:
            if notification.id and notification.id in seen_ids:
                continue
            if notification.id:
                seen_ids.add(notification.id)

            created_at_bucket = int(notification.created_at.timestamp())
            fingerprint = "|".join(
                [
                    notification.source_type,
                    notification.type or "",
                    notification.title.strip(),
                    notification.content.strip(),
                    str(created_at_bucket),
                ]
            )
            if fingerprint in seen_fingerprints:
                logger.warning(
                    "Deduplicated notification center entry for user payload: {}",
                    fingerprint,
                )
                continue

            seen_fingerprints.add(fingerprint)
            deduped.append(notification)

        return deduped

    @staticmethod
    def _notification_is_intervention(notification: Notification) -> bool:
        return str(notification.type or "").strip().lower() in {"intervention", "intervention_push"}

    @staticmethod
    def _notification_is_push(notification: Notification) -> bool:
        return str(notification.type or "").strip().lower() == "aurora_push"

    async def _load_intervention_records_for_notifications(
        self,
        notifications: list[Notification],
    ) -> dict[UUID, InterventionRecord]:
        record_ids_by_notification: dict[UUID, UUID] = {}
        for notification in notifications:
            record_id = self._extract_notification_record_id(notification)
            if record_id:
                record_ids_by_notification[notification.id] = record_id

        if not record_ids_by_notification:
            return {}

        result = await self.db.execute(
            select(InterventionRecord).where(InterventionRecord.id.in_(list(record_ids_by_notification.values())))
        )
        records = {record.id: record for record in result.scalars().all()}
        return {
            notification_id: records[record_id]
            for notification_id, record_id in record_ids_by_notification.items()
            if record_id in records
        }

    async def _find_notification_for_record(
        self,
        user_id: UUID,
        record_id: UUID,
    ) -> Notification | None:
        result = await self.db.execute(
            select(Notification)
            .where(
                Notification.user_id == user_id,
                self._is_intervention_notification(),
            )
            .order_by(desc(Notification.created_at))
        )
        target = str(record_id)
        for notification in result.scalars().all():
            if str((notification.data or {}).get("record_id") or "") == target:
                return notification
        return None

    @staticmethod
    def _is_intervention_notification():
        return Notification.type.in_(("intervention", "intervention_push"))

    @staticmethod
    def _is_push_notification():
        return Notification.type == "aurora_push"

    async def _load_push_records_for_notifications(
        self,
        notifications: list[Notification],
    ) -> dict[UUID, PushDeliveryRecord]:
        notification_ids = [notification.id for notification in notifications]
        if not notification_ids:
            return {}
        result = await self.db.execute(
            select(PushDeliveryRecord).where(
                PushDeliveryRecord.notification_id.in_(notification_ids),
                PushDeliveryRecord.retracted_at.is_(None),
            )
        )
        records = {record.notification_id: record for record in result.scalars().all() if record.notification_id}
        return {notification_id: record for notification_id, record in records.items()}
