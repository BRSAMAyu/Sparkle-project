"""共学自习室 schemas（D-COMM-4 · beacon 式在场证明，服务端 TTL 真源）。

在场证明的展示语义（ROOM-PRESENCE 修订：TTL 过期=诚实离场）：
- ``in_room``：有开放会话（exited_at IS NULL）**且** 心跳在 TTL 内——
  杀进程/切后台后最多 TTL 内残留，过期后读路径如实判离场（不造假在场）；
- ``is_stale``：开放会话但 TTL 已过期（异常退出待回收的崩溃恢复线索，
  非惩罚；展示层弱提示，不作状态降级）；
- 时长一律分钟粒度、地板取整，「今日」按成员本地日界（复用督促域
  的时区惯例：push_preference.timezone，默认 Asia/Shanghai）。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# 在场 TTL（秒）：最后活性证明（last_heartbeat_at）超过此时长即诚实离场。
# 续期信号 = 前台房间轮询（详情屏可见 + app 前台时 30s 一拍，绝不要求
# 后台 Timer）；显式 enter/exit 仍是主信号。90s 给前台 30s 轮询留两次
# 失手余量；移动端字号级别的小 JSON 调用，功耗可忽略。
STUDY_ROOM_PRESENCE_TTL_SECONDS = 90


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
    """心跳（续期信号）：有开放会话即刷新 last_heartbeat_at（TTL 续命，
    含已 decayed 的开放记录——房间 UI 发来的活性证明）；无开放会话不自动重开。"""

    in_room: bool
    last_heartbeat_at: datetime | None = None
    today_minutes: int = Field(default=0, ge=0)


class StudyRoomPresenceEntry(BaseModel):
    """单成员在场视图（含未入场成员，时长如实为 0——不伪装、不缺席惩罚）。"""

    user_id: UUID
    display_name: str | None = Field(default=None, description="昵称或用户名（缺失为 None）")
    role: str
    in_room: bool = Field(description="开放会话且心跳在 TTL 内（TTL 过期=诚实离场）")
    is_stale: bool = Field(
        default=False,
        description="有开放会话但 TTL 已过期（异常退出待回收的崩溃恢复线索，非惩罚）",
    )
    entered_at: datetime | None = Field(default=None, description="当前在场会话的进入时刻（不在场为 None）")
    current_session_minutes: int = Field(default=0, ge=0, description="当前在场会话已持续分钟数（不在场为 0）")
    today_minutes: int = Field(default=0, ge=0, description="今日累计自习分钟数（本地日界，跨会话求和；decay 不虚增）")

    model_config = ConfigDict(from_attributes=True)


class StudyRoomPresenceResponse(BaseModel):
    """小队自习室在场聚合（仅小队成员可见，非成员 403）。"""

    group_id: UUID
    member_count: int
    in_room_count: int
    generated_at: datetime
    members: list[StudyRoomPresenceEntry]
