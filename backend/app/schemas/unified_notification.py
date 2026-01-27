"""
Unified Notification Schemas

Combines system notifications and intervention requests into a single API format.
"""
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, UUID4, Field

T = TypeVar('T')


class UnifiedNotificationResponse(BaseModel):
    """Unified notification format combining system and intervention notifications"""
    id: str = Field(..., description="Notification ID (UUID as string)")
    source_type: str = Field(..., description="Source type: 'system' or 'intervention'")
    title: str
    content: str
    type: Optional[str] = Field(None, description="Original notification type")
    priority: str = Field(default="medium", description="Priority: low, medium, high")
    is_read: bool = Field(default=False)
    created_at: datetime
    read_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class NotificationInteractionCreate(BaseModel):
    """Create a notification interaction record"""
    notification_type: str = Field(..., description="system or intervention")
    notification_id: UUID4
    action_type: str = Field(..., description="viewed, clicked, dismissed")
    time_to_action: Optional[int] = Field(None, description="Seconds from creation to action")


class NotificationInteractionResponse(BaseModel):
    """Notification interaction response"""
    id: UUID4
    user_id: UUID4
    notification_type: str
    notification_id: UUID4
    action_type: str
    action_time: datetime
    time_to_action: Optional[int]

    class Config:
        from_attributes = True


class NotificationPreferencesUpdate(BaseModel):
    """Update notification preferences"""
    enable_system: Optional[bool] = None
    enable_interventions: Optional[bool] = None
    notification_level: Optional[str] = Field(None, pattern="^(minimal|standard|verbose)$")
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")


class NotificationPreferencesResponse(BaseModel):
    """Notification preferences response"""
    user_id: UUID4
    enable_system: bool
    enable_interventions: bool
    notification_level: str
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationHistoryFilters(BaseModel):
    """Filters for notification history query"""
    type: Optional[str] = Field(None, description="all, system, intervention")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = Field(None, min_length=1, max_length=100)


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
    by_type: Dict[str, NotificationTypeStats]
    trends: List[NotificationTrendData]
    hourly_distribution: List[int] = Field(..., description="24-hour distribution array")


# Pagination

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
