"""共学自习室 schemas（D-COMM-4 · beacon 式在场证明）。

在场证明的展示语义：
- ``in_room``：有开放会话（exited_at IS NULL）即在场；
- ``is_stale``：在场但心跳超过阈值（崩溃恢复线索，非惩罚）；
- 时长一律分钟粒度、地板取整，「今日」按成员本地日界（复用督促域
  的时区惯例：push_preference.timezone，默认 Asia/Shanghai）。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# 心跳陈旧阈值：超过即标 is_stale（在场但客户端可能已失联）。
# beacon 式在场以显式进出为主，心跳只兜底崩溃恢复，阈值放宽以降低误伤。
STUDY_ROOM_STALE_MINUTES = 15


class StudyRoomEnterResponse(BaseModel):
    """进入自习室（幂等：已在场则刷新心跳并返回既有会话）。"""

    session_id: UUID
    group_id: UUID
    user_id: UUID
    entered_at: datetime
    reentered: bool = Field(description="是否命中既有开放会话（True=本次未新建记录，仅刷新心跳）")
    today_minutes: int = Field(default=0, ge=0, description="该成员今日累计自习分钟数（本地日界）")


class StudyRoomExitResponse(BaseModel):
    """退出自习室（幂等：无开放会话时诚实上报 already_out）。"""

    session_id: UUID | None = Field(default=None, description="本次关闭的会话（无开放会话时为 None）")
    exited_at: datetime | None = None
    session_minutes: int = Field(default=0, ge=0, description="本次会话时长（分钟，地板取整）")
    already_out: bool = Field(default=False, description="进入时已不在场（重复退出的诚实上报）")
    today_minutes: int = Field(default=0, ge=0, description="退出后该成员今日累计自习分钟数")


class StudyRoomHeartbeatResponse(BaseModel):
    """心跳（仅兜底崩溃恢复）：在场则刷新 last_heartbeat_at。"""

    in_room: bool
    last_heartbeat_at: datetime | None = None
    today_minutes: int = Field(default=0, ge=0)


class StudyRoomPresenceEntry(BaseModel):
    """单成员在场视图（含未入场成员，时长如实为 0——不伪装、不缺席惩罚）。"""

    user_id: UUID
    display_name: str | None = Field(default=None, description="昵称或用户名（缺失为 None）")
    role: str
    in_room: bool
    is_stale: bool = Field(default=False, description="在场但心跳超过阈值（崩溃恢复线索）")
    entered_at: datetime | None = Field(default=None, description="当前在场会话的进入时刻（不在场为 None）")
    current_session_minutes: int = Field(default=0, ge=0, description="当前在场会话已持续分钟数（不在场为 0）")
    today_minutes: int = Field(default=0, ge=0, description="今日累计自习分钟数（本地日界，跨会话求和）")

    model_config = ConfigDict(from_attributes=True)


class StudyRoomPresenceResponse(BaseModel):
    """小队自习室在场聚合（仅小队成员可见，非成员 403）。"""

    group_id: UUID
    member_count: int
    in_room_count: int
    generated_at: datetime
    members: list[StudyRoomPresenceEntry]
