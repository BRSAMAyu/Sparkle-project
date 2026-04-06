"""
Unified Notification Schemas

Combines system notifications and intervention requests into a single API format.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import UUID4, BaseModel, ConfigDict, Field

T = TypeVar('T')


class UnifiedNotificationResponse(BaseModel):
    """Unified notification format combining system and intervention notifications"""
    id: str = Field(..., description="Notification ID (UUID as string)")
    source_type: str = Field(..., description="Source type: 'system' or 'intervention'")
    title: str
    content: str
    type: str | None = Field(None, description="Original notification type")
    priority: str = Field(default="medium", description="Priority: low, medium, high")
    is_read: bool = Field(default=False)
    created_at: datetime
    read_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class NotificationInteractionCreate(BaseModel):
    """Create a notification interaction record"""
    notification_type: str = Field(..., description="system or intervention")
    notification_id: UUID4
    action_type: str = Field(..., description="viewed, clicked, dismissed")
    time_to_action: int | None = Field(None, description="Seconds from creation to action")


class NotificationInteractionResponse(BaseModel):
    """Notification interaction response"""
    id: UUID4
    user_id: UUID4
    notification_type: str
    notification_id: UUID4
    action_type: str
    action_time: datetime
    time_to_action: int | None

    model_config = ConfigDict(from_attributes=True)


class InterventionNotificationActionRequest(BaseModel):
    """Transition a notification-backed intervention record from mobile."""

    action: str = Field(
        ...,
        pattern="^(seen|accepted|acted|dismissed|snoozed)$",
        description="Desired intervention action",
    )
    action_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional client-side evidence such as source, route, CTA label, or acted context",
    )


class NotificationPreferencesUpdate(BaseModel):
    """Update notification preferences"""
    enable_system: bool | None = None
    enable_interventions: bool | None = None
    notification_level: str | None = Field(None, pattern="^(minimal|standard|verbose)$")
    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: str | None = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")


class NotificationPreferencesResponse(BaseModel):
    """Notification preferences response"""
    user_id: UUID4
    enable_system: bool
    enable_interventions: bool
    notification_level: str
    quiet_hours_enabled: bool
    quiet_hours_start: str | None
    quiet_hours_end: str | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationHistoryFilters(BaseModel):
    """Filters for notification history query"""
    type: str | None = Field(None, description="all, system, intervention")
    start_date: datetime | None = None
    end_date: datetime | None = None
    search: str | None = Field(None, min_length=1, max_length=100)


# Analytics Schemas

class NotificationAnalyticsSummary(BaseModel):
    """Summary statistics for notifications"""
    total_sent: int = 0
    total_viewed: int = 0
    total_clicked: int = 0
    total_accepted: int = 0
    total_acted: int = 0
    view_rate: float = 0.0
    click_rate: float = 0.0
    acceptance_rate: float = 0.0
    action_rate: float = 0.0
    avg_time_to_action: float = 0.0


class NotificationTypeStats(BaseModel):
    """Statistics for a specific notification type"""
    type: str
    sent: int
    viewed: int
    clicked: int
    accepted: int = 0
    acted: int = 0
    view_rate: float
    click_rate: float
    acceptance_rate: float = 0.0
    action_rate: float = 0.0


class NotificationTrendData(BaseModel):
    """Trend data point (date + metrics)"""
    date: str  # ISO date string
    sent: int
    viewed: int
    clicked: int
    accepted: int = 0
    acted: int = 0


class InterventionFunnelStats(BaseModel):
    """Lifecycle funnel metrics for one intervention dimension."""

    dimension: str
    created: int = 0
    delivered: int = 0
    seen: int = 0
    accepted: int = 0
    acted: int = 0
    acceptance_rate: float = 0.0
    action_rate: float = 0.0


class InterventionToneEffectiveness(BaseModel):
    """Outcome and action performance for a strategy/channel pair."""

    tone: str
    channel: str
    created: int = 0
    accepted: int = 0
    acted: int = 0
    effective: int = 0
    acted_rate: float = 0.0
    effective_rate: float = 0.0


class InterventionTimeToActionBucket(BaseModel):
    """Bucketted action latency for intervention analytics."""

    label: str
    count: int = 0


class NotificationAnalyticsResponse(BaseModel):
    """Complete analytics response"""
    summary: NotificationAnalyticsSummary
    by_type: dict[str, NotificationTypeStats]
    trends: list[NotificationTrendData]
    hourly_distribution: list[int] = Field(..., description="24-hour distribution array")
    intervention_funnels: list[InterventionFunnelStats] = Field(default_factory=list)
    tone_effectiveness: list[InterventionToneEffectiveness] = Field(default_factory=list)
    time_to_action_buckets: list[InterventionTimeToActionBucket] = Field(default_factory=list)


# Pagination

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
