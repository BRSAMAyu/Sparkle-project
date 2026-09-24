"""
Understanding Depth daily baseline models.

数据飞轮专项：把"越用越懂用户"从运行时现算（UnderstandingDepthService.evaluate，
纯 Redis 态）升级为可回归的每日持久化基线。每个用户每天至多一行（UTC 日期），
合成分 0-1，各维度原始值落在 components JSONB 里，保证可解释、可重放。

数据源全部为已有生产表：
- context_pack_runs.memory_counts  → 记忆注入量 / 个性化 run 占比
- chat_messages (role=user)        → 重复提问率、纠正强度分母
- memory_corrections               → 用户主动纠正次数
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import JSON, Date, Float, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class UnderstandingDepthDaily(BaseModel):
    __tablename__ = "understanding_depth_daily"

    user_id: Mapped[Any] = mapped_column(GUID(), nullable=False, index=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    # 0-1 合成分；无活动日不落行，有活动但维度缺失按 0 计。
    score: Mapped[float] = mapped_column(Float, nullable=False)
    # 各维度原始值与归一化分量（memory_injection/personalization/non_correction/non_repeat）
    # 以及样本量（context_pack_runs、chat_turns、memory_corrections、repeat_questions）。
    components: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    # 冗余样本量列（便于 SQL 直接做人群聚合，不必解 JSONB）。
    context_pack_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chat_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "metric_date", name="uq_understanding_depth_daily_user_date"),
        Index("idx_understanding_depth_daily_date", "metric_date"),
    )
