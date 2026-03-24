"""
排行榜系统 Schema
Leaderboard System Schemas

支持多种类型的排行榜：全局、好友、群组、学科、周榜、连胜榜
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LeaderboardType(str, Enum):
    """排行榜类型"""
    GLOBAL = "global"          # 全局综合排行榜
    FRIENDS = "friends"        # 好友排行榜
    GROUP = "group"            # 群组排行榜
    SUBJECT = "subject"        # 学科排行榜
    WEEKLY = "weekly"          # 本周学习排行榜
    STREAK = "streak"          # 连胜排行榜
    GROUP_FLAME = "group_flame"  # 群组火苗榜
    PHOTON = "photon"          # 光子积分排行榜
    PHOTON_WEEKLY = "photon_weekly"  # 本周光子收入排行榜


class LeaderboardPeriod(str, Enum):
    """排行榜周期"""
    ALL_TIME = "all_time"      # 全部时间
    WEEKLY = "weekly"          # 本周
    MONTHLY = "monthly"        # 本月
    DAILY = "daily"            # 今日


class LeaderboardEntry(BaseModel):
    """排行榜条目"""
    rank: int = Field(description="排名")
    user_id: UUID = Field(description="用户ID")
    username: str = Field(description="用户名")
    avatar_url: str | None = Field(default=None, description="头像URL")
    score: float = Field(description="分数")
    score_label: str = Field(description='分数标签（如"1234分"）')
    is_me: bool = Field(default=False, description="是否为当前用户")
    change: int | None = Field(default=None, description="排名变化（正数=上升，负数=下降）")
    stats: dict[str, Any] = Field(default_factory=dict, description="额外统计信息")
    badge: str | None = Field(default=None, description="徽章URL（前三名）")


class GroupLeaderboardEntry(BaseModel):
    """群组排行榜条目"""
    rank: int = Field(description="排名")
    group_id: UUID = Field(description="群组ID")
    group_name: str = Field(description="群组名称")
    avatar_url: str | None = Field(default=None, description="群组头像")
    score: float = Field(description="分数")
    score_label: str = Field(description="分数标签")
    member_count: int = Field(description="成员数量")
    is_my_group: bool = Field(default=False, description="是否为我的群组")
    change: int | None = Field(default=None, description="排名变化")


class LeaderboardResponse(BaseModel):
    """排行榜响应"""
    type: LeaderboardType = Field(description="排行榜类型")
    title: str = Field(description="排行榜标题")
    entries: list[LeaderboardEntry] = Field(description="排行榜条目")
    my_rank: int | None = Field(default=None, description="我的排名")
    my_score: float | None = Field(default=None, description="我的分数")
    last_updated: datetime = Field(description="最后更新时间")
    total_participants: int = Field(description="总参与人数")
    period: LeaderboardPeriod = Field(default=LeaderboardPeriod.ALL_TIME, description="统计周期")


class GroupLeaderboardResponse(BaseModel):
    """群组排行榜响应"""
    type: LeaderboardType = Field(description="排行榜类型")
    title: str = Field(description="排行榜标题")
    entries: list[GroupLeaderboardEntry] = Field(description="群组条目")
    my_group_rank: int | None = Field(default=None, description="我的群组排名")
    last_updated: datetime = Field(description="最后更新时间")
    total_groups: int = Field(description="总群组数")


class LeaderboardSummary(BaseModel):
    """排行榜摘要"""
    global_ranking: LeaderboardResponse | None = Field(default=None, description="全局榜")
    friends: LeaderboardResponse | None = Field(default=None, description="好友榜")
    weekly: LeaderboardResponse | None = Field(default=None, description="周榜")
    streak: LeaderboardResponse | None = Field(default=None, description="连胜榜")
    photon: LeaderboardResponse | None = Field(default=None, description="光子积分榜")
    photon_weekly: LeaderboardResponse | None = Field(default=None, description="本周光子收入榜")
    my_stats: dict[str, Any] = Field(default_factory=dict, description="我的统计信息")


class LeaderboardRequest(BaseModel):
    """排行榜查询请求"""
    type: LeaderboardType = Field(description="排行榜类型")
    limit: int = Field(default=50, ge=1, le=100, description="返回数量")
    offset: int = Field(default=0, ge=0, description="偏移量")
    period: LeaderboardPeriod = Field(default=LeaderboardPeriod.ALL_TIME, description="统计周期")
    subject_id: UUID | None = Field(default=None, description="学科ID（仅学科榜）")
    group_id: UUID | None = Field(default=None, description="群组ID（仅群组榜）")


class MyRankResponse(BaseModel):
    """我的排名响应"""
    rank: int = Field(description="排名")
    score: float = Field(description="分数")
    score_label: str = Field(description="分数标签")
    total_participants: int = Field(description="总参与人数")
    percentile: float = Field(description="百分位数（0-1）")
    change_from_last_period: int | None = Field(default=None, description="与上周期排名变化")
    nearby_users: list[LeaderboardEntry] = Field(default_factory=list, description="附近用户")


class LeaderboardConfig(BaseModel):
    """排行榜配置"""
    enabled_types: list[LeaderboardType] = Field(description="启用的排行榜类型")
    update_frequency_minutes: int = Field(default=60, description="更新频率（分钟）")
    cache_ttl_seconds: int = Field(default=300, description="缓存TTL（秒）")
    min_participants: int = Field(default=10, description="最小参与人数")
