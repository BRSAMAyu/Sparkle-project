"""S-04 · Community Artifact Feedback —— shared_resource_feedbacks 表

Revision ID: s04_20260924
Revises: gseed_20260923
Create Date: 2026-09-24

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：drop table shared_resource_feedbacks
        （社区反馈记录，非权威真源；回滚只丢社群反馈记录本身，不影响
        tasks/goals/study_records 等五源与信念状态）。"
    verification_query: "SELECT count(*) FROM shared_resource_feedbacks;"
    backfill_plan: "无回填（新表，存量共享资源反馈从零开始）。"
    owner: "S-04 (Stream: COMMUNITY)"
    ticket: "v3/07_tasks/cards/S-04.md —— 把同伴反馈变成可选择的 Goal
        evidence：feedback/ack 不自动成为 mastery；用户可采纳为 outcome
        evidence（采纳回执落 Goal.metadata_payload，证据走 services/evidence
        既有链，本表是社群表面记录，不是证据真源）。

表语义（与 app.models.community.SharedResourceFeedback 一一对应）：
- 唯一约束 (shared_resource_id, feedback_by)：一人一资源一条反馈，重复反馈
  = 服务层 upsert（更新 verdict/comment）。
- adopted_at / adopted_into_goal_id：资源主人采纳回执；goals 外键 SET NULL，
  目标删除不阻塞反馈行留存。
- retracted_at：共享撤回（SharedResource 软删）时的派生引用更新戳；
  行保留供审计，查询面按 retracted_at IS NULL 过滤活跃反馈。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

from app.models.base import GUID

revision: str = "s04_20260924"
down_revision: str | None = "gseed_20260923"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "shared_resource_feedbacks"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", GUID(), nullable=False),
        sa.Column("shared_resource_id", GUID(), nullable=False),
        sa.Column("feedback_by", GUID(), nullable=False),
        sa.Column("verdict", sa.String(length=20), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("adopted_at", sa.DateTime(), nullable=True),
        sa.Column("adopted_into_goal_id", GUID(), nullable=True),
        sa.Column("retracted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["shared_resource_id"], ["shared_resources.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["feedback_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["adopted_into_goal_id"], ["goals.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shared_resource_id", "feedback_by", name="uq_sr_feedback_resource_user"
        ),
    )
    op.create_index(
        "ix_shared_resource_feedbacks_shared_resource_id",
        _TABLE,
        ["shared_resource_id"],
    )
    op.create_index("ix_shared_resource_feedbacks_feedback_by", _TABLE, ["feedback_by"])
    op.create_index(
        "idx_sr_feedback_resource_active", _TABLE, ["shared_resource_id", "retracted_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_sr_feedback_resource_active", table_name=_TABLE)
    op.drop_index("ix_shared_resource_feedbacks_feedback_by", table_name=_TABLE)
    op.drop_index(
        "ix_shared_resource_feedbacks_shared_resource_id", table_name=_TABLE
    )
    op.drop_table(_TABLE)
