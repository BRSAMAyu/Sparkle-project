"""
Notification Analytics Service

Provides usage statistics and analytics for notifications.
"""
from datetime import datetime, timedelta, UTC
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import redis.asyncio as aioredis

    from app.config import settings
except ImportError:
    aioredis = None

from app.models.intervention import InterventionRequest
from app.models.notification import Notification
from app.models.notification_interaction import NotificationInteraction
from app.models.card_protocol import (
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionRecord,
)
from app.schemas.unified_notification import (
    InterventionFunnelStats,
    InterventionTimeToActionBucket,
    InterventionToneEffectiveness,
    NotificationAnalyticsResponse,
    NotificationAnalyticsSummary,
    NotificationTrendData,
    NotificationTypeStats,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class NotificationAnalyticsService:
    """
    Analytics service for notification usage and effectiveness.

    Features:
    - Summary statistics (sent, viewed, clicked, rates)
    - Type-based breakdown
    - Time-based trends (daily for period)
    - Hourly distribution (24-hour profile)
    - Redis caching for performance
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis = None

        if aioredis and settings.REDIS_URL:
            try:
                self.redis = aioredis.from_url(settings.REDIS_URL)
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for analytics: {e}")

    async def get_analytics(
        self,
        user_id: UUID,
        period: str = '7d'
    ) -> NotificationAnalyticsResponse:
        """
        Get complete notification analytics for a user.

        Args:
            user_id: User UUID
            period: Time period ('1d', '7d', '30d', 'all')

        Returns:
            NotificationAnalyticsResponse with summary, trends, and distribution
        """
        # Check cache
        if self.redis:
            cache_key = f"analytics:{user_id}:{period}"
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    import json
                    return NotificationAnalyticsResponse(**json.loads(cached))
            except Exception as e:
                logger.warning(f"Failed to read analytics from cache: {e}")

        # Calculate period start date
        start_date = self._get_period_start_date(period)

        # Fetch analytics data
        summary = await self._calculate_summary(user_id, start_date)
        by_type = await self._get_stats_by_type(user_id, start_date)
        trends = await self._get_trends(user_id, start_date)
        hourly_distribution = await self._get_hourly_distribution(user_id)
        intervention_funnels = await self._get_intervention_funnels(user_id, start_date)
        tone_effectiveness = await self._get_tone_effectiveness(user_id, start_date)
        time_to_action_buckets = await self._get_time_to_action_buckets(user_id, start_date)

        analytics = NotificationAnalyticsResponse(
            summary=summary,
            by_type=by_type,
            trends=trends,
            hourly_distribution=hourly_distribution,
            intervention_funnels=intervention_funnels,
            tone_effectiveness=tone_effectiveness,
            time_to_action_buckets=time_to_action_buckets,
        )

        # Cache for 1 hour
        if self.redis:
            try:
                cache_key = f"analytics:{user_id}:{period}"
                await self.redis.setex(cache_key, 3600, analytics.model_dump_json())
            except Exception as e:
                logger.warning(f"Failed to cache analytics: {e}")

        return analytics

    async def _calculate_summary(
        self,
        user_id: UUID,
        start_date: datetime
    ) -> NotificationAnalyticsSummary:
        """Calculate summary statistics"""
        # Count system notifications sent
        system_sent_stmt = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.created_at >= start_date,
                ~self._is_intervention_notification(),
            )
        )
        result = await self.db.execute(system_sent_stmt)
        system_sent = result.scalar() or 0

        # Count system notifications viewed (read)
        system_viewed_stmt = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.created_at >= start_date,
                Notification.is_read,
                ~self._is_intervention_notification(),
            )
        )
        result = await self.db.execute(system_viewed_stmt)
        system_viewed = result.scalar() or 0

        intervention_notification_sent_stmt = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.created_at >= start_date,
                self._is_intervention_notification(),
            )
        )
        result = await self.db.execute(intervention_notification_sent_stmt)
        intervention_notification_sent = result.scalar() or 0

        intervention_notification_viewed_stmt = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.created_at >= start_date,
                Notification.is_read,
                self._is_intervention_notification(),
            )
        )
        result = await self.db.execute(intervention_notification_viewed_stmt)
        intervention_notification_viewed = result.scalar() or 0

        # Count interventions sent
        intervention_sent_stmt = select(func.count(InterventionRequest.id)).where(
            and_(
                InterventionRequest.user_id == user_id,
                InterventionRequest.created_at >= start_date
            )
        )
        result = await self.db.execute(intervention_sent_stmt)
        intervention_sent = result.scalar() or 0

        # Count interventions viewed (acknowledged)
        intervention_viewed_stmt = select(func.count(InterventionRequest.id)).where(
            and_(
                InterventionRequest.user_id == user_id,
                InterventionRequest.created_at >= start_date,
                InterventionRequest.status.in_(['acknowledged', 'approved', 'rejected'])
            )
        )
        result = await self.db.execute(intervention_viewed_stmt)
        intervention_viewed = result.scalar() or 0

        interaction_counts = await self._interaction_counts(user_id, start_date)
        total_clicked = interaction_counts.get('clicked', 0)
        total_accepted = interaction_counts.get('accepted', 0)
        total_acted = interaction_counts.get('acted', 0)

        # Calculate totals
        total_sent = system_sent + intervention_notification_sent + intervention_sent
        total_viewed = system_viewed + intervention_notification_viewed + intervention_viewed

        # Calculate rates
        view_rate = (total_viewed / total_sent * 100) if total_sent > 0 else 0.0
        click_rate = (total_clicked / total_viewed * 100) if total_viewed > 0 else 0.0
        acceptance_rate = (total_accepted / total_viewed * 100) if total_viewed > 0 else 0.0
        action_rate = (total_acted / total_accepted * 100) if total_accepted > 0 else 0.0

        # Calculate average time to action
        avg_time_stmt = select(func.avg(NotificationInteraction.time_to_action)).where(
            and_(
                NotificationInteraction.user_id == user_id,
                NotificationInteraction.action_time >= start_date,
                NotificationInteraction.time_to_action.isnot(None)
            )
        )
        result = await self.db.execute(avg_time_stmt)
        avg_time_to_action = result.scalar() or 0.0

        return NotificationAnalyticsSummary(
            total_sent=total_sent,
            total_viewed=total_viewed,
            total_clicked=total_clicked,
            total_accepted=total_accepted,
            total_acted=total_acted,
            view_rate=round(view_rate, 2),
            click_rate=round(click_rate, 2),
            acceptance_rate=round(acceptance_rate, 2),
            action_rate=round(action_rate, 2),
            avg_time_to_action=round(avg_time_to_action, 2)
        )

    async def _get_stats_by_type(
        self,
        user_id: UUID,
        start_date: datetime
    ) -> dict[str, NotificationTypeStats]:
        """Get statistics broken down by notification type"""
        stats = {}

        # System notifications
        system_sent_stmt = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.created_at >= start_date,
                ~self._is_intervention_notification(),
            )
        )
        result = await self.db.execute(system_sent_stmt)
        system_sent = result.scalar() or 0

        system_viewed_stmt = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.created_at >= start_date,
                Notification.is_read,
                ~self._is_intervention_notification(),
            )
        )
        result = await self.db.execute(system_viewed_stmt)
        system_viewed = result.scalar() or 0

        # Interactions for system
        system_clicks_stmt = select(func.count(NotificationInteraction.id)).where(
            and_(
                NotificationInteraction.user_id == user_id,
                NotificationInteraction.action_time >= start_date,
                NotificationInteraction.notification_type == 'system',
                NotificationInteraction.action_type == 'clicked'
            )
        )
        result = await self.db.execute(system_clicks_stmt)
        system_clicked = result.scalar() or 0

        system_view_rate = (system_viewed / system_sent * 100) if system_sent > 0 else 0.0
        system_click_rate = (system_clicked / system_viewed * 100) if system_viewed > 0 else 0.0

        stats['system'] = NotificationTypeStats(
            type='system',
            sent=system_sent,
            viewed=system_viewed,
            clicked=system_clicked,
            view_rate=round(system_view_rate, 2),
            click_rate=round(system_click_rate, 2)
        )

        intervention_notification_sent_stmt = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.created_at >= start_date,
                self._is_intervention_notification(),
            )
        )
        result = await self.db.execute(intervention_notification_sent_stmt)
        intervention_notification_sent = result.scalar() or 0

        intervention_notification_viewed_stmt = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.created_at >= start_date,
                Notification.is_read,
                self._is_intervention_notification(),
            )
        )
        result = await self.db.execute(intervention_notification_viewed_stmt)
        intervention_notification_viewed = result.scalar() or 0

        # Interventions
        intervention_sent_stmt = select(func.count(InterventionRequest.id)).where(
            and_(
                InterventionRequest.user_id == user_id,
                InterventionRequest.created_at >= start_date
            )
        )
        result = await self.db.execute(intervention_sent_stmt)
        intervention_sent = result.scalar() or 0

        intervention_viewed_stmt = select(func.count(InterventionRequest.id)).where(
            and_(
                InterventionRequest.user_id == user_id,
                InterventionRequest.created_at >= start_date,
                InterventionRequest.status.in_(['acknowledged', 'approved', 'rejected'])
            )
        )
        result = await self.db.execute(intervention_viewed_stmt)
        intervention_viewed = result.scalar() or 0

        # Interactions for interventions
        intervention_counts = await self._interaction_counts(
            user_id,
            start_date,
            notification_type='intervention',
        )
        intervention_clicked = intervention_counts.get('clicked', 0)
        intervention_accepted = intervention_counts.get('accepted', 0)
        intervention_acted = intervention_counts.get('acted', 0)

        intervention_sent_total = intervention_notification_sent + intervention_sent
        intervention_viewed_total = intervention_notification_viewed + intervention_viewed
        intervention_view_rate = (intervention_viewed_total / intervention_sent_total * 100) if intervention_sent_total > 0 else 0.0
        intervention_click_rate = (intervention_clicked / intervention_viewed_total * 100) if intervention_viewed_total > 0 else 0.0
        intervention_acceptance_rate = (
            intervention_accepted / intervention_viewed_total * 100
        ) if intervention_viewed_total > 0 else 0.0
        intervention_action_rate = (
            intervention_acted / intervention_accepted * 100
        ) if intervention_accepted > 0 else 0.0

        stats['intervention'] = NotificationTypeStats(
            type='intervention',
            sent=intervention_sent_total,
            viewed=intervention_viewed_total,
            clicked=intervention_clicked,
            accepted=intervention_accepted,
            acted=intervention_acted,
            view_rate=round(intervention_view_rate, 2),
            click_rate=round(intervention_click_rate, 2),
            acceptance_rate=round(intervention_acceptance_rate, 2),
            action_rate=round(intervention_action_rate, 2),
        )

        return stats

    async def _get_trends(
        self,
        user_id: UUID,
        start_date: datetime
    ) -> list[NotificationTrendData]:
        """Get daily trend data for the period"""
        trends = []

        # Generate day-by-day data
        current_date = start_date.date()
        end_date = _utcnow().date()

        while current_date <= end_date:
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())

            # Count system notifications sent this day
            system_sent_stmt = select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.created_at >= day_start,
                    Notification.created_at <= day_end,
                    ~self._is_intervention_notification(),
                )
            )
            result = await self.db.execute(system_sent_stmt)
            system_sent = result.scalar() or 0

            # Count system viewed this day
            system_viewed_stmt = select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.created_at >= day_start,
                    Notification.created_at <= day_end,
                    Notification.is_read,
                    ~self._is_intervention_notification(),
                )
            )
            result = await self.db.execute(system_viewed_stmt)
            system_viewed = result.scalar() or 0

            intervention_notification_sent_stmt = select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.created_at >= day_start,
                    Notification.created_at <= day_end,
                    self._is_intervention_notification(),
                )
            )
            result = await self.db.execute(intervention_notification_sent_stmt)
            intervention_notification_sent = result.scalar() or 0

            intervention_notification_viewed_stmt = select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.created_at >= day_start,
                    Notification.created_at <= day_end,
                    Notification.is_read,
                    self._is_intervention_notification(),
                )
            )
            result = await self.db.execute(intervention_notification_viewed_stmt)
            intervention_notification_viewed = result.scalar() or 0

            # Count interventions sent this day
            intervention_sent_stmt = select(func.count(InterventionRequest.id)).where(
                and_(
                    InterventionRequest.user_id == user_id,
                    InterventionRequest.created_at >= day_start,
                    InterventionRequest.created_at <= day_end
                )
            )
            result = await self.db.execute(intervention_sent_stmt)
            intervention_sent = result.scalar() or 0

            # Count interventions viewed this day
            intervention_viewed_stmt = select(func.count(InterventionRequest.id)).where(
                and_(
                    InterventionRequest.user_id == user_id,
                    InterventionRequest.created_at >= day_start,
                    InterventionRequest.created_at <= day_end,
                    InterventionRequest.status.in_(['acknowledged', 'approved', 'rejected'])
                )
            )
            result = await self.db.execute(intervention_viewed_stmt)
            intervention_viewed = result.scalar() or 0

            interaction_counts = await self._interaction_counts(
                user_id,
                day_start,
                end_date=day_end,
            )
            clicked = interaction_counts.get('clicked', 0)
            accepted = interaction_counts.get('accepted', 0)
            acted = interaction_counts.get('acted', 0)

            trends.append(NotificationTrendData(
                date=current_date.isoformat(),
                sent=system_sent + intervention_notification_sent + intervention_sent,
                viewed=system_viewed + intervention_notification_viewed + intervention_viewed,
                clicked=clicked,
                accepted=accepted,
                acted=acted,
            ))

            current_date += timedelta(days=1)

        return trends

    async def _get_hourly_distribution(
        self,
        user_id: UUID
    ) -> list[int]:
        """
        Get 24-hour distribution of notification activity.

        Returns array of 24 integers representing activity for each hour.
        """
        distribution = [0] * 24

        # Get all interactions for this user
        stmt = select(NotificationInteraction).where(
            NotificationInteraction.user_id == user_id
        )
        result = await self.db.execute(stmt)
        interactions = result.scalars().all()

        for interaction in interactions:
            hour = interaction.action_time.hour
            distribution[hour] += 1

        return distribution

    async def _get_intervention_funnels(
        self,
        user_id: UUID,
        start_date: datetime,
    ) -> list[InterventionFunnelStats]:
        records = await self._get_intervention_records(user_id, start_date)
        stats_by_trigger: dict[str, dict[str, int]] = {}

        for record in records:
            key = record.trigger_type.value if record.trigger_type else "UNKNOWN"
            bucket = stats_by_trigger.setdefault(
                key,
                {"created": 0, "delivered": 0, "seen": 0, "accepted": 0, "acted": 0},
            )
            bucket["created"] += 1

            if record.acceptance_status != InterventionAcceptanceStatus.CREATED:
                bucket["delivered"] += 1
            if record.acceptance_status in {
                InterventionAcceptanceStatus.SEEN,
                InterventionAcceptanceStatus.ACCEPTED,
                InterventionAcceptanceStatus.ACTED,
                InterventionAcceptanceStatus.DISMISSED,
                InterventionAcceptanceStatus.SNOOZED,
            }:
                bucket["seen"] += 1
            if record.acceptance_status in {
                InterventionAcceptanceStatus.ACCEPTED,
                InterventionAcceptanceStatus.ACTED,
            }:
                bucket["accepted"] += 1
            if record.acceptance_status == InterventionAcceptanceStatus.ACTED:
                bucket["acted"] += 1

        funnels: list[InterventionFunnelStats] = []
        for dimension, bucket in sorted(stats_by_trigger.items()):
            seen = bucket["seen"]
            accepted = bucket["accepted"]
            funnels.append(
                InterventionFunnelStats(
                    dimension=dimension,
                    created=bucket["created"],
                    delivered=bucket["delivered"],
                    seen=seen,
                    accepted=accepted,
                    acted=bucket["acted"],
                    acceptance_rate=round((accepted / seen * 100) if seen > 0 else 0.0, 2),
                    action_rate=round((bucket["acted"] / accepted * 100) if accepted > 0 else 0.0, 2),
                )
            )
        return funnels

    async def _get_tone_effectiveness(
        self,
        user_id: UUID,
        start_date: datetime,
    ) -> list[InterventionToneEffectiveness]:
        records = await self._get_intervention_records(user_id, start_date)
        stats: dict[tuple[str, str], dict[str, int]] = {}

        for record in records:
            tone = record.delivery_strategy.value if record.delivery_strategy else DeliveryStrategy.SUPPORTIVE.value
            channel = record.delivery_channel.value if record.delivery_channel else "UNKNOWN"
            bucket = stats.setdefault(
                (tone, channel),
                {"created": 0, "accepted": 0, "acted": 0, "effective": 0},
            )
            bucket["created"] += 1
            if record.acceptance_status in {
                InterventionAcceptanceStatus.ACCEPTED,
                InterventionAcceptanceStatus.ACTED,
            }:
                bucket["accepted"] += 1
            if record.acceptance_status == InterventionAcceptanceStatus.ACTED:
                bucket["acted"] += 1
            if record.outcome_status == InterventionOutcomeStatus.EFFECTIVE:
                bucket["effective"] += 1

        effectiveness: list[InterventionToneEffectiveness] = []
        for (tone, channel), bucket in sorted(stats.items()):
            created = bucket["created"]
            effectiveness.append(
                InterventionToneEffectiveness(
                    tone=tone,
                    channel=channel,
                    created=created,
                    accepted=bucket["accepted"],
                    acted=bucket["acted"],
                    effective=bucket["effective"],
                    acted_rate=round((bucket["acted"] / created * 100) if created > 0 else 0.0, 2),
                    effective_rate=round((bucket["effective"] / created * 100) if created > 0 else 0.0, 2),
                )
            )
        return effectiveness

    async def _get_time_to_action_buckets(
        self,
        user_id: UUID,
        start_date: datetime,
    ) -> list[InterventionTimeToActionBucket]:
        result = await self.db.execute(
            select(NotificationInteraction.time_to_action).where(
                NotificationInteraction.user_id == user_id,
                NotificationInteraction.notification_type == "intervention",
                NotificationInteraction.action_type == "acted",
                NotificationInteraction.action_time >= start_date,
                NotificationInteraction.time_to_action.isnot(None),
            )
        )
        buckets = {
            "under_5m": 0,
            "5m_to_30m": 0,
            "30m_to_2h": 0,
            "over_2h": 0,
        }
        for value in result.scalars().all():
            seconds = int(value or 0)
            if seconds < 300:
                buckets["under_5m"] += 1
            elif seconds < 1800:
                buckets["5m_to_30m"] += 1
            elif seconds < 7200:
                buckets["30m_to_2h"] += 1
            else:
                buckets["over_2h"] += 1

        return [
            InterventionTimeToActionBucket(label=label, count=count)
            for label, count in buckets.items()
        ]

    def _get_period_start_date(self, period: str) -> datetime:
        """Calculate start date for the given period"""
        now = _utcnow()

        if period == '1d':
            return now - timedelta(days=1)
        elif period == '7d':
            return now - timedelta(days=7)
        elif period == '30d':
            return now - timedelta(days=30)
        elif period == 'all':
            # Return a very old date
            return datetime(2020, 1, 1)
        else:
            # Default to 7 days
            return now - timedelta(days=7)

    async def _get_intervention_records(
        self,
        user_id: UUID,
        start_date: datetime,
    ) -> list[InterventionRecord]:
        result = await self.db.execute(
            select(InterventionRecord).where(
                InterventionRecord.user_id == user_id,
                InterventionRecord.created_at >= start_date,
                InterventionRecord.not_deleted_filter(),
            )
        )
        return list(result.scalars().all())

    async def close(self):
        """Close Redis connection if exists"""
        if self.redis:
            try:
                await self.redis.close()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")

    @staticmethod
    def _is_intervention_notification():
        return Notification.type.in_(("intervention", "intervention_push"))

    async def _interaction_counts(
        self,
        user_id: UUID,
        start_date: datetime,
        *,
        notification_type: str | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, int]:
        stmt = select(
            NotificationInteraction.action_type,
            func.count(NotificationInteraction.id),
        ).where(
            NotificationInteraction.user_id == user_id,
            NotificationInteraction.action_time >= start_date,
        )
        if end_date is not None:
            stmt = stmt.where(NotificationInteraction.action_time <= end_date)
        if notification_type is not None:
            stmt = stmt.where(NotificationInteraction.notification_type == notification_type)

        stmt = stmt.group_by(NotificationInteraction.action_type)
        result = await self.db.execute(stmt)
        return {str(action_type): int(count) for action_type, count in result.all()}
