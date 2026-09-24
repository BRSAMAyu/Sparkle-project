"""X-03 · Action Proposal 持久模型（action_proposals + action_proposal_transitions）.

结构镜像 X-05 agent_runs（同款审计/幂等骨架，本卡是该模式在 Action 域的复用）：

1. ``action_proposals`` —— proposal 生命周期唯一持久真源：状态（封闭词表）、
   命令域、subject 与**版本 token**（乐观并发）、payload、**diff（前后对照）**、
   授权决策记录、过期时刻、receipt（COMMITTED 后权威回执本体）。
2. ``action_proposal_transitions`` —— append-only 生命周期审计（from/to/
   event_name/actor/idempotency_key/reason/details/occurred_at），每次有效
   迁移一行，与状态变更、event_outbox 事件同事务。

索引要点：
- ``uq_action_proposals_idem``：(user_id, idempotency_key) 唯一——重复创建
  proposal 恰一次（X-05 idx_agent_runs_idem 同法；NULL 键行天然不冲突）；
- ``uq_action_proposal_transitions_idem``：(proposal_id, idempotency_key) 唯一
  ——重复 approve 恰一次 commit 的二次兜底；
- ``ix_action_proposals_user_status``：用户侧列表（确认卡收件箱）。

枚举列不带 DB CHECK（execution_intent.py ``create_constraint=False`` 先例；
封闭词表由 app/core/action_command.py 契约层强制，X-01/X-05 同款）。
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.action_command import ProposalSource, ProposalStatus
from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


#: 可空 idempotency_key 的部分索引 WHERE（NULL 不参与唯一约束；两方言同构）。
_KEY_PRESENT_WHERE = text("idempotency_key IS NOT NULL")


class ActionProposal(BaseModel):
    """一条待确认/已落账的 Action 写命令（生命周期唯一真源）."""

    __tablename__ = "action_proposals"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # --- 生命周期（封闭词表：app/core/action_command.py） ------------------------
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus, values_callable=_enum_values, create_constraint=False, native_enum=False),
        nullable=False,
        default=ProposalStatus.PENDING,
        index=True,
    )
    command_type: Mapped[str] = mapped_column(String(32), nullable=False)  # ActionCommandType 词表
    source: Mapped[str] = mapped_column(String(16), nullable=False, default=ProposalSource.SYSTEM.value)
    terminal_reason: Mapped[str] = mapped_column(String(32), nullable=True)  # TERMINAL_REASON_VOCABULARY

    # --- 命令目标与乐观并发 ---------------------------------------------------
    subject_type: Mapped[str] = mapped_column(String(32), nullable=True)  # "task"（create 型命令为 NULL）
    subject_id: Mapped[Any] = mapped_column(GUID(), nullable=True, index=True)
    subject_version_token: Mapped[str] = mapped_column(String(64), nullable=True)  # proposal 时 updated_at ISO

    payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False)
    diff: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)  # {"before","after","changed_fields"}

    # --- 授权决策（前置；软件强制，非提示词） -----------------------------------
    authorization: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)

    risk_class: Mapped[str] = mapped_column(String(16), nullable=True)  # X-01 词表 low|medium|high|critical
    reversible: Mapped[str] = mapped_column(String(8), nullable=True)  # "true"/"false"/NULL（X-01 成对语义）
    summary: Mapped[str] = mapped_column(Text, nullable=True)  # 确认卡人类可读摘要

    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # --- receipt（COMMITTED 权威回执本体；与状态变更同事务写入） -----------------
    receipt: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)
    committed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # --- 关联（correlation ids；C-01/D-01 对齐） --------------------------------
    session_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    run_id: Mapped[Any] = mapped_column(GUID(), nullable=True, index=True)  # X-05 agent_run 关联（观测）

    __table_args__ = (
        # 重复创建恰一次：(user_id, idempotency_key) 唯一；NULL 键（未携带）不参与。
        Index(
            "uq_action_proposals_idem",
            "user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=_KEY_PRESENT_WHERE,
            sqlite_where=_KEY_PRESENT_WHERE,
        ),
        Index("ix_action_proposals_user_status", "user_id", "status"),
    )


class ActionProposalTransition(BaseModel):
    """append-only 生命周期审计行（每次有效迁移恰一行）."""

    __tablename__ = "action_proposal_transitions"

    proposal_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("action_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[str] = mapped_column(String(16), nullable=True)  # None = 创建（PENDING 落库）
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    event_name: Mapped[str] = mapped_column(String(64), nullable=False)  # action.proposed/accepted/rejected（D-01 词表）
    actor: Mapped[str] = mapped_column(String(32), nullable=False)  # user|system|aurora|chat
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=True)
    reason: Mapped[str] = mapped_column(String(64), nullable=True)
    details: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        # 重复 approve 恰一次审计：同 (proposal_id, idempotency_key) 唯一。
        Index(
            "uq_action_proposal_transitions_idem",
            "proposal_id",
            "idempotency_key",
            unique=True,
            postgresql_where=_KEY_PRESENT_WHERE,
            sqlite_where=_KEY_PRESENT_WHERE,
        ),
    )
