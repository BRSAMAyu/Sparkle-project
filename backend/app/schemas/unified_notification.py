"""
Unified Notification Schemas

Combines system notifications and intervention requests into a single API format.
"""
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import UUID4, BaseModel, Field

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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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
    view_rate: float = 0.0
    click_rate: float = 0.0
    avg_time_to_action: float = 0.0


class NotificationTypeStats(BaseModel):
    """Statistics for a specific notification type"""
    type: str
    sent: int
    viewed: int
    clicked: int
    view_rate: float
    click_rate: float


class NotificationTrendData(BaseModel):
    """Trend data point (date + metrics)"""
    date: str  # ISO date string
    sent: int
    viewed: int
    clicked: int


class NotificationAnalyticsResponse(BaseModel):
    """Complete analytics response"""
    summary: NotificationAnalyticsSummary
    by_type: dict[str, NotificationTypeStats]
    trends: list[NotificationTrendData]
    hourly_distribution: list[int] = Field(..., description="24-hour distribution array")


# Pagination

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
