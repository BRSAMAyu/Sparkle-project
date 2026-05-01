"""Calendar Event Schemas - 日历事件创建、更新、查询等"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import BaseSchema

# ========== Request Schemas ==========


class CalendarEventCreate(BaseModel):
    """创建日历事件"""

    title: str = Field(min_length=1, max_length=255, description="事件标题")
    description: str | None = Field(default=None, description="事件描述")
    start_time: datetime = Field(description="开始时间")
    end_time: datetime = Field(description="结束时间")
    is_all_day: bool = Field(default=False, description="是否全天事件")
    location: str | None = Field(default=None, max_length=255, description="地点")
    color: str | None = Field(default=None, max_length=32, description="颜色 (hex 或名称)")
    recurrence_rule: str | None = Field(default=None, max_length=512, description="重复规则 (RRULE)")
    recurrence_end_date: datetime | None = Field(default=None, description="重复结束日期")
    reminder_minutes: list[int] = Field(default_factory=list, description="提醒时间 (分钟数列表)")
    task_id: UUID | None = Field(default=None, description="关联任务 ID")
    plan_id: UUID | None = Field(default=None, description="关联计划 ID")
    source: str = Field(default="manual", max_length=32, description="事件来源")
    source_metadata: dict | None = Field(default=None, description="来源元数据")

    @field_validator("end_time")
    @classmethod
    def end_time_after_start_time(cls, v, info):
        """验证结束时间必须在开始时间之后"""
        start_time = info.data.get("start_time")
        if start_time and v <= start_time:
            raise ValueError("结束时间必须在开始时间之后")
        return v


class CalendarEventUpdate(BaseModel):
    """更新日历事件"""

    title: str | None = Field(default=None, min_length=1, max_length=255, description="事件标题")
    description: str | None = Field(default=None, description="事件描述")
    start_time: datetime | None = Field(default=None, description="开始时间")
    end_time: datetime | None = Field(default=None, description="结束时间")
    is_all_day: bool | None = Field(default=None, description="是否全天事件")
    location: str | None = Field(default=None, max_length=255, description="地点")
    color: str | None = Field(default=None, max_length=32, description="颜色")
    recurrence_rule: str | None = Field(default=None, max_length=512, description="重复规则")
    recurrence_end_date: datetime | None = Field(default=None, description="重复结束日期")
    reminder_minutes: list[int] | None = Field(default=None, description="提醒时间列表")


class CalendarEventListQuery(BaseModel):
    """日历事件列表查询参数"""

    start_date: date | None = Field(default=None, description="开始日期筛选")
    end_date: date | None = Field(default=None, description="结束日期筛选")
    include_deleted: bool = Field(default=False, description="是否包含已删除事件")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=50, ge=1, le=200, description="每页数量")


class BatchOperationItem(BaseModel):
    """批量操作项"""

    action: str = Field(description="操作类型: create, update, delete")
    data: dict | None = Field(default=None, description="操作数据 (create/update)")
    event_id: UUID | None = Field(default=None, description="事件 ID (update/delete)")


class CalendarEventBatchRequest(BaseModel):
    """批量操作请求"""

    operations: list[BatchOperationItem] = Field(max_length=50, description="操作列表")


# ========== Response Schemas ==========


class CalendarEventBase(BaseSchema):
    """日历事件基本信息"""

    title: str = Field(description="事件标题")
    description: str | None = Field(description="事件描述")
    start_time: datetime = Field(description="开始时间")
    end_time: datetime = Field(description="结束时间")
    is_all_day: bool = Field(description="是否全天事件")
    location: str | None = Field(description="地点")
    color: str | None = Field(description="颜色")


class CalendarEventDetail(CalendarEventBase):
    """日历事件详细信息"""

    user_id: UUID = Field(description="用户 ID")
    recurrence_rule: str | None = Field(description="重复规则")
    recurrence_end_date: datetime | None = Field(description="重复结束日期")
    reminder_minutes: list[int] = Field(description="提醒时间列表")
    source: str = Field(description="事件来源")
    source_metadata: dict | None = Field(description="来源元数据")
    task_id: UUID | None = Field(description="关联任务 ID")
    plan_id: UUID | None = Field(description="关联计划 ID")

    # 计算属性
    duration_minutes: int = Field(description="事件时长 (分钟)")
    is_recurring: bool = Field(description="是否为重复事件")


class CalendarEventSummary(BaseModel):
    """日历事件统计摘要"""

    total: int = Field(description="总事件数")
    upcoming: int = Field(description="即将到来的事件数")
    today: int = Field(description="今日事件数")
    recurring: int = Field(description="重复事件数")


class CalendarEventListResponse(BaseModel):
    """日历事件列表响应"""

    data: list[CalendarEventDetail] = Field(description="事件列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页")
    page_size: int = Field(description="每页数量")


class BatchOperationResult(BaseModel):
    """批量操作结果"""

    action: str = Field(description="操作类型")
    event_id: UUID | None = Field(default=None, description="事件 ID")
    success: bool = Field(description="是否成功")
    error: str | None = Field(default=None, description="错误信息")


class CalendarEventBatchResponse(BaseModel):
    """批量操作响应"""

    results: list[BatchOperationResult] = Field(description="操作结果列表")
    success_count: int = Field(description="成功数量")
    failure_count: int = Field(description="失败数量")
