"""冲刺小队 MVP schemas（D-COMM-3 · 社群×exam_sprint 首联动）。

小队 = 既有 Group(type=SPRINT) 的场景化门面（复用裁决见
services/community_squad_service.py 模块注释），不新增表。成员完成度口径
唯一来自 app/services/sprint_task_ledger.py（sprint-completion 单一事实源，
BP-4）；XP/光子等行为量禁入（D20 防刷红线）。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.exam_sprint import SprintTaskStats

# 设计卡 D-COMMUNITY 3.3：小队 3-8 人（不足 3 人时前端兜底切自我视图）。
SQUAD_MIN_MEMBERS = 3
SQUAD_MAX_MEMBERS = 8


class SquadCreate(BaseModel):
    """创建冲刺小队（type 固定 SPRINT，deadline 必填——冲刺周期既是可见性窗口也是加入窗口）。"""

    name: str = Field(min_length=2, max_length=100, description="小队名称")
    description: str | None = Field(default=None, max_length=500, description="小队描述")
    focus_tags: list[str] = Field(default_factory=list, max_length=10, description="关注标签")
    deadline: datetime = Field(description="冲刺截止（冲刺周期终点）")
    sprint_goal: str | None = Field(default=None, max_length=500, description="冲刺目标")
    max_members: int = Field(
        default=SQUAD_MAX_MEMBERS,
        ge=SQUAD_MIN_MEMBERS,
        le=SQUAD_MAX_MEMBERS,
        description=f"人数上限（小队 {SQUAD_MIN_MEMBERS}-{SQUAD_MAX_MEMBERS} 人）",
    )
    is_public: bool = Field(default=True, description="是否公开可搜索")

    @field_validator("deadline")
    @classmethod
    def deadline_must_be_future(cls, v: datetime) -> datetime:
        # 与 schemas/community.py GroupCreate.validate_deadline 同一惯例；
        # 归一化掉 tzinfo 以免 aware/naive 比较炸 500。
        naive = v.replace(tzinfo=None) if v.tzinfo is not None else v
        if naive <= datetime.now():
            raise ValueError("截止日期不能是过去的时间")
        return naive


class SquadInfo(BaseModel):
    """冲刺小队详情。"""

    id: UUID
    name: str
    description: str | None = None
    focus_tags: list[str] = Field(default_factory=list)
    deadline: datetime | None = None
    sprint_goal: str | None = None
    max_members: int
    is_public: bool
    member_count: int
    days_remaining: int | None = None
    my_role: str | None = Field(default=None, description="当前用户在小队中的角色（非成员为 None）")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SquadListItem(BaseModel):
    """「我的小队」列表项（仅冲刺周期内的小队可见）。"""

    id: UUID
    name: str
    sprint_goal: str | None = None
    deadline: datetime | None = None
    days_remaining: int | None = None
    member_count: int
    max_members: int
    my_role: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SquadMemberBrief(BaseModel):
    """小队成员简要信息（成员列表端点，仅小队成员可见）。"""

    user_id: UUID
    username: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    role: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SquadMemberSprintProgress(BaseModel):
    """单成员冲刺完成度（sprint-completion 口径，唯一来源 sprint_task_ledger）。

    空数据诚实语义：成员名下无任务时 task_total=0 / task_completed=0 /
    completion_rate=0.0 且 has_ledger_data=False——明确表达「账本还没有数据」，
    而不是把 0 伪装成「0% 完成率」。
    """

    user_id: UUID
    display_name: str | None = Field(default=None, description="昵称或用户名（缺失为 None）")
    role: str
    task_total: int = Field(default=0, ge=0)
    task_completed: int = Field(default=0, ge=0)
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    has_ledger_data: bool = Field(description="该成员任务账本是否非空（空数据诚实语义标记）")
    stats: SprintTaskStats = Field(description="与 sprint_task_ledger 同源的原始统计")

    model_config = ConfigDict(from_attributes=True)


class SquadSprintProgressResponse(BaseModel):
    """小队冲刺完成度聚合视图（仅小队成员可见）。"""

    squad_id: UUID
    member_count: int
    sprint_active: bool = Field(description="是否仍在冲刺周期内（deadline 未过）")
    generated_at: datetime
    members: list[SquadMemberSprintProgress]
