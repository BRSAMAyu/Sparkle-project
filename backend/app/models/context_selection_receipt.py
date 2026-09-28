"""V4-I06 · ContextSelectionReceipt 落库模型（``context_selection_receipts`` 表）。

合同：``v4/evidence/V4-B05/contract_receipt_min.md`` §2。回执 = 服务器对"读了哪些
权威的哪些版本、候选了什么、用了什么、拒了什么"的权威记录（只读语义——它不证明
写入成功，只证明"读与选"；C3）。

设计对齐既有先例（``context_pack_runs``）：
- 结构化面（candidates/budget/why_now/input_versions）走 JSONBCompat——契约结构
  由 ``app.core.context_selection_receipt`` 唯一拥有并校验，表只做持久化载体，
  **不造第二真值**；
- ``memory_epoch`` 提升为独立列：来源验证（read 面 join）与"删除/纠正后旧 receipt
  失效"判定的高频过滤键（C-07 epoch 契约的读侧）；
- ``user_id + created_at`` 复合索引：U03「我的理解」读面按用户取最近回执。
"""

from typing import Any

from sqlalchemy import JSON, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class ContextSelectionReceiptRow(BaseModel):
    __tablename__ = "context_selection_receipts"

    user_id: Mapped[Any] = mapped_column(GUID(), nullable=False, index=True)
    #: 合同 §2：``csr_<ulid>``，服务端生成；幂等键（同一轮可重算不重复计数）。
    receipt_id: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    #: 封闭词表：chat_context / proposal_basis / resume_view / intervention_targeting
    selection_role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    #: null = 无 Aurora 决策参与（纯规则快路）。
    decision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: C-07：快照编译时钉住的 per-user memory epoch（独立列，读侧 join/失效判定用）。
    memory_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: selector 实现版本（合同 §2 input_versions.selector_version 必选）。
    selector_version: Mapped[str] = mapped_column(String(120), nullable=False)
    input_versions: Mapped[Any] = mapped_column(JSONBCompat, nullable=False)
    candidates: Mapped[Any] = mapped_column(JSONBCompat, nullable=False)
    budget: Mapped[Any] = mapped_column(JSONBCompat, nullable=False)
    why_now: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)
    #: 关联既有 context_pack_runs（可选；同轮 pack 观测面关联键）。
    pack_run_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __repr_fields__ = ("receipt_id", "selection_role", "memory_epoch")
    __table_args__ = (UniqueConstraint("receipt_id", name="uq_context_selection_receipts_receipt_id"),)


Index(
    "idx_context_selection_receipts_user_created",
    ContextSelectionReceiptRow.user_id,
    ContextSelectionReceiptRow.created_at,
)
Index("idx_context_selection_receipts_role", ContextSelectionReceiptRow.selection_role)
