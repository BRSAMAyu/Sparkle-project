"""小队榜 schemas（D-COMM-4 · 冲刺完成度口径榜）。

榜分口径红线（D20 防刷）：唯一来自 D-COMM-3 的冲刺完成度聚合面
（SquadService.get_squad_sprint_progress → sprint_task_ledger，BP-4
单一事实源）；XP/光子/榜单行为量禁入，由
tests/unit/test_community_study_room.py 的 AST + 行为双断言钉死。

<3 人裁决（设计卡 §3.2/§5）：小队不足 SQUAD_MIN_MEMBERS 人时榜单不成立
（board_valid=False / self_view_only=True），客户端切自我锚视图。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.exam_sprint import SprintTaskStats


class LeaderboardEntry(BaseModel):
    """小队榜单条目：D-COMM-3 完成度聚合 + 排名包装（不新增口径）。"""

    rank: int = Field(ge=1, description="并列名次（完成度键全同的成员同名次）")
    user_id: UUID
    display_name: str | None = None
    role: str
    task_total: int = Field(default=0, ge=0)
    task_completed: int = Field(default=0, ge=0)
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    has_ledger_data: bool = Field(description="账本是否非空（空数据诚实语义，沿用 D-COMM-3）")
    percentile: int = Field(
        ge=0, le=100, description="名次区间：完成度严格低于该成员的队员占比（D21 默认展示区间而非赤裸名次）"
    )
    stats: SprintTaskStats = Field(description="与 sprint_task_ledger 同源的原始统计（透传 D-COMM-3 聚合）")

    model_config = ConfigDict(from_attributes=True)


class SquadLeaderboardResponse(BaseModel):
    """小队榜（冲刺完成度口径，仅小队成员可见；非成员 403）。"""

    squad_id: UUID
    member_count: int
    sprint_active: bool
    board_valid: bool = Field(description="榜单是否成立（成员数 ≥ 3）")
    self_view_only: bool = Field(description="成员数不足 3 人时 True——客户端应切自我锚视图（设计裁决）")
    generated_at: datetime
    my_rank: int | None = Field(default=None, description="请求者名次（成员必在榜上，正常不为 None）")
    total: int = Field(ge=0, description="榜上总人数（分页前的全集）")
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    entries: list[LeaderboardEntry]
