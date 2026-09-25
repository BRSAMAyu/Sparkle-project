"""J-05 ·「我卡住了」旗舰恢复旅程 —— 纠正反馈环持久化模型。

「不是这个原因」纠正的唯一真源表：用户否定一次卡点主判断
（friction_type）后，记录在此；后续 stuck-journey start/answer 派生时
读取本表（freshness 窗口内）把被纠正类型从主判断提名中垫后——纠正
进入反馈环影响后续判断，不静默丢弃（卡面验收第 3 条）。

不重建真源纪律：摩擦诊断本身仍由冻结的 A-03 引擎
（app/aurora/friction_diagnosis.py）产出；本表只存「用户纠正」这一
不可从任务行推导的用户主观事实，是 A-03 输入事实集之外的正交证据。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class StuckJourneyCorrection(BaseModel):
    """一次「不是这个原因」纠正（per user；纠正对象 = 摩擦类型主判断）。"""

    __tablename__ = "stuck_journey_corrections"

    user_id: Mapped[Any] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: 纠正发起面（home/goal/action）——溯源用；纠正本身 per-user 全局生效。
    surface: Mapped[str] = mapped_column(String(16), nullable=False)
    #: 被纠正的摩擦类型（FRICTION_TYPES 成员，路由层校验；unknown 不接受）。
    friction_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    #: 被纠正时的主 intervention（可选，审计面）。
    intervention_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: 纠正时刻的任务/目标锚点（可选，溯源面）。
    task_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    goal_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    #: 用户可选补充说明（原文，≤500）。
    reason_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    #: 纠正时刻的旅程 context 快照（evidence candidate——D 链/复盘可回放）。
    context_snapshot: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    #: 旅程 schema 版本（漂移审计）。
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    corrected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - repr only
        return (
            f"<StuckJourneyCorrection(id={self.id}, user_id={self.user_id}, "
            f"friction_type={self.friction_type}, surface={self.surface})>"
        )
