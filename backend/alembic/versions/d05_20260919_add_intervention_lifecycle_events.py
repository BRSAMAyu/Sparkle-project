"""D-05 · Intervention lifecycle event store (new table, additive)

Revision ID: d05_20260919
Revises: x01_20260919
Create Date: 2026-09-19

契约真源：backend/app/core/intervention_lifecycle.py
（INTERVENTION_LIFECYCLE_SCHEMA_VERSION = "intervention_lifecycle.v1"）。

新表 ``intervention_lifecycle_events``：干预生命周期事件（exposure/accept/
edit/reject/start/outcome 关联）的持久分析真源。为何不是 event_outbox：
cleanup_worker 7 天删除已发布 outbox 行，分析历史不能建立在会消失的存储上
（outbox 只承载集成通知，M-07 同款分工；本表与 outbox 互不替代）。

幂等唯一约束 ``uq_intervention_lifecycle_once (decision_id, event_type,
dedupe_subkey)`` 是「同一 intervention 不双计」的存储层机制（outcome 关联行
的 dedupe_subkey = D-02 outcome_id，其余事件为空串）。枚举列不带 DB CHECK
（X-01 同款纪律：封闭词表由应用层契约强制）。

索引：user_id / decision_id / event_type / occurred_at（摘要聚合与增量扫描面），
外加 (user_id, intervention_type) 复合索引（M-06 情境签名检索预留）。
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.models.base import GUID

revision: str = "d05_20260919"
down_revision: Union[str, None] = "x05_20260919"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "intervention_lifecycle_events",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("intervention_type", sa.String(length=40), nullable=False),
        sa.Column("execution_mode", sa.String(length=16), nullable=True),
        sa.Column("goal_type", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("friction_tag", sa.String(length=40), nullable=False, server_default="unattributed"),
        sa.Column("linkage", _jsonb_type(), nullable=True),
        sa.Column("outcome_source", sa.String(length=24), nullable=True),
        sa.Column("outcome_ref", sa.String(length=80), nullable=True),
        sa.Column("outcome_polarity", sa.String(length=16), nullable=True),
        sa.Column("outcome_truth_class", sa.String(length=16), nullable=True),
        sa.Column("detail", _jsonb_type(), nullable=True),
        sa.Column("dedupe_subkey", sa.String(length=96), nullable=False, server_default=""),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "decision_id",
            "event_type",
            "dedupe_subkey",
            name="uq_intervention_lifecycle_once",
        ),
    )
    op.create_index("ix_intervention_lifecycle_user", "intervention_lifecycle_events", ["user_id"])
    op.create_index("ix_intervention_lifecycle_decision", "intervention_lifecycle_events", ["decision_id"])
    op.create_index("ix_intervention_lifecycle_event_type", "intervention_lifecycle_events", ["event_type"])
    op.create_index("ix_intervention_lifecycle_occurred", "intervention_lifecycle_events", ["occurred_at"])
    op.create_index(
        "ix_intervention_lifecycle_user_intervention",
        "intervention_lifecycle_events",
        ["user_id", "intervention_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_intervention_lifecycle_user_intervention", table_name="intervention_lifecycle_events")
    op.drop_index("ix_intervention_lifecycle_occurred", table_name="intervention_lifecycle_events")
    op.drop_index("ix_intervention_lifecycle_event_type", table_name="intervention_lifecycle_events")
    op.drop_index("ix_intervention_lifecycle_decision", table_name="intervention_lifecycle_events")
    op.drop_index("ix_intervention_lifecycle_user", table_name="intervention_lifecycle_events")
    op.drop_table("intervention_lifecycle_events")
