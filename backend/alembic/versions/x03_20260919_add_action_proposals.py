"""X-03 · Action Proposal 统一 command path（action_proposals + transitions）

Revision ID: x03_20260919
Revises: x05_20260919
Create Date: 2026-09-19

契约真源：backend/app/core/action_command.py（ACTION_COMMAND_PROTOCOL_VERSION =
"action_command.v1"，封闭状态/命令/归因/授权词表，测试冻结）。

两张新表（X-03 唯一 schema 变更，全部新建、零列变更既有表）：

1. ``action_proposals`` —— V2 可信写入协议推广到 V3 Action 的生命周期唯一真源：
   proposal→approve→validate(version/permission)→commit→receipt 全链持久状态。
   - ``subject_version_token``：proposal 创建时 subject 行 updated_at 的 ISO 快照
     ——commit 前重读比对，stale 拒绝（乐观并发，不覆盖）；
   - ``diff``：前后对照 JSONB（UI 确认卡可渲染数据面）；
   - ``authorization``：前置授权决策记录（软件强制）；
   - ``receipt``：COMMITTED 权威回执本体（与状态变更同事务写入，UI 权威查询）。
2. ``action_proposal_transitions`` —— append-only 生命周期审计（X-05
   agent_run_transitions 同构；每次有效迁移一行，与 outbox 事件同事务）。

索引要点：
- ``uq_action_proposals_idem``：(user_id, idempotency_key) 部分唯一（键非空）——
  重复创建 proposal 恰一次；
- ``uq_action_proposal_transitions_idem``：(proposal_id, idempotency_key) 部分
  唯一——重复 approve 恰一次 commit 的二次兜底；
- ``ix_action_proposals_user_status``：用户确认卡收件箱列表。

枚举列不带 DB CHECK（execution_intent.py create_constraint=False 先例，X-01/X-05
同款）；JSONB 列 sqlite 侧退化为 JSON（测试）。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.models.base import GUID

revision: str = "x03_20260919"
down_revision: str | None = "x06_20260919"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_KEY_PRESENT = "idempotency_key IS NOT NULL"


def _jsonb_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "action_proposals",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("command_type", sa.String(32), nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="system"),
        sa.Column("terminal_reason", sa.String(32), nullable=True),
        sa.Column("subject_type", sa.String(32), nullable=True),
        sa.Column("subject_id", GUID(), nullable=True),
        sa.Column("subject_version_token", sa.String(64), nullable=True),
        sa.Column("payload", _jsonb_type(), nullable=False),
        sa.Column("diff", _jsonb_type(), nullable=True),
        sa.Column("authorization", _jsonb_type(), nullable=True),
        sa.Column("risk_class", sa.String(16), nullable=True),
        sa.Column("reversible", sa.String(8), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("receipt", _jsonb_type(), nullable=True),
        sa.Column("committed_at", sa.DateTime(), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("run_id", GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_action_proposals_user_id", "action_proposals", ["user_id"])
    op.create_index("ix_action_proposals_status", "action_proposals", ["status"])
    op.create_index("ix_action_proposals_subject_id", "action_proposals", ["subject_id"])
    op.create_index("ix_action_proposals_expires_at", "action_proposals", ["expires_at"])
    op.create_index("ix_action_proposals_session_id", "action_proposals", ["session_id"])
    op.create_index("ix_action_proposals_trace_id", "action_proposals", ["trace_id"])
    op.create_index("ix_action_proposals_run_id", "action_proposals", ["run_id"])
    op.create_index("ix_action_proposals_user_status", "action_proposals", ["user_id", "status"])
    op.create_index(
        "uq_action_proposals_idem",
        "action_proposals",
        ["user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(_KEY_PRESENT),
        sqlite_where=sa.text(_KEY_PRESENT),
    )

    op.create_table(
        "action_proposal_transitions",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "proposal_id",
            GUID(),
            sa.ForeignKey("action_proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(16), nullable=True),
        sa.Column("to_status", sa.String(16), nullable=False),
        sa.Column("event_name", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("reason", sa.String(64), nullable=True),
        sa.Column("details", _jsonb_type(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_action_proposal_transitions_proposal_id", "action_proposal_transitions", ["proposal_id"])
    op.create_index(
        "uq_action_proposal_transitions_idem",
        "action_proposal_transitions",
        ["proposal_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(_KEY_PRESENT),
        sqlite_where=sa.text(_KEY_PRESENT),
    )


def downgrade() -> None:
    op.drop_index("uq_action_proposal_transitions_idem", table_name="action_proposal_transitions")
    op.drop_index("ix_action_proposal_transitions_proposal_id", table_name="action_proposal_transitions")
    op.drop_table("action_proposal_transitions")
    op.drop_index("uq_action_proposals_idem", table_name="action_proposals")
    op.drop_index("ix_action_proposals_user_status", table_name="action_proposals")
    op.drop_index("ix_action_proposals_run_id", table_name="action_proposals")
    op.drop_index("ix_action_proposals_trace_id", table_name="action_proposals")
    op.drop_index("ix_action_proposals_session_id", table_name="action_proposals")
    op.drop_index("ix_action_proposals_expires_at", table_name="action_proposals")
    op.drop_index("ix_action_proposals_subject_id", table_name="action_proposals")
    op.drop_index("ix_action_proposals_status", table_name="action_proposals")
    op.drop_index("ix_action_proposals_user_id", table_name="action_proposals")
    op.drop_table("action_proposals")
