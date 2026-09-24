"""D-05 · Intervention lifecycle event store（intervention_lifecycle_events 表）。

存储真源 = 生命周期事件本身（exposure/accept/edit/reject/start/outcome 关联）：
- event_outbox **不是**这个存储（cleanup_worker 7 天删除已发布行——分析历史不能
  建立在会消失的 outbox 上；outbox 只承载集成通知，M-07 同款分工）；
- D-02 outcome ledger 是 outcome 事实真源，本表 ``outcome_observed`` 行只存
  (decision_id, outcome_ref) 链接与方向/真相镜像（读模型快照，重算可对账）。

幂等（「同一 intervention 不双计」的存储层机制）：
``uq_intervention_lifecycle_once (decision_id, event_type, dedupe_subkey)`` ——
- exposure/accept/edit/reject/start：dedupe_subkey = ""（同一 decision 同一类型
  恰一行）；
- outcome_observed：dedupe_subkey = D-02 outcome_id（同一 outcome 对同一 decision
  恰关联一次；不同 outcome 各自成行）。

契约真源：backend/app/core/intervention_lifecycle.py（词表/语义/幂等键）。
枚举列不带 DB CHECK（X-01 同款纪律：封闭词表由应用层契约强制）。
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class InterventionLifecycleEvent(BaseModel):
    """id/created_at/updated_at/deleted_at 由 BaseModel 提供（软删除口径与
    D-02 五流一致：摘要聚合走 ``not_deleted_filter``）。"""

    __tablename__ = "intervention_lifecycle_events"
    __table_args__ = (
        UniqueConstraint(
            "decision_id",
            "event_type",
            "dedupe_subkey",
            name="uq_intervention_lifecycle_once",
        ),
    )

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # -- 干预身份（A-01 决策产物锚点）--------------------------------------
    decision_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # aurora_<32hex>
    event_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)  # LifecycleEventType
    intervention_type: Mapped[str] = mapped_column(String(40), nullable=False)  # A-01 目录 17 成员
    execution_mode: Mapped[str] = mapped_column(String(16), nullable=True)  # human|agent|hybrid|NULL(inert 不可 exposure)

    # -- 切片维度（记录时点固化；goal/friction/execution_mode）----------------
    goal_type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    friction_tag: Mapped[str] = mapped_column(String(40), nullable=False, default="unattributed")

    # -- 关联键（exposure 时点捕获；canonical UUID str）----------------------
    linkage: Mapped[Any] = mapped_column(JSON, nullable=True)  # {task_id, plan_id, node_id, intervention_request_id}

    # -- outcome 关联（outcome_observed 行专用；其余事件为 NULL）--------------
    outcome_source: Mapped[str] = mapped_column(String(24), nullable=True)  # D-02 OutcomeSource 值
    outcome_ref: Mapped[str] = mapped_column(String(80), nullable=True)  # outc_<sha256[:32]>
    outcome_polarity: Mapped[str] = mapped_column(String(16), nullable=True)  # positive|negative|neutral
    outcome_truth_class: Mapped[str] = mapped_column(String(16), nullable=True)  # actual|self_reported|…

    # -- 事件补充（content-light：类型判别码/窗口参数，不存正文）--------------
    detail: Mapped[Any] = mapped_column(JSON, nullable=True)  # 如 {"window_hours": 72} / {"feedback_kind": "edited"}
    dedupe_subkey: Mapped[str] = mapped_column(String(96), nullable=False, default="")

    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    user = relationship("User", backref="intervention_lifecycle_events")
