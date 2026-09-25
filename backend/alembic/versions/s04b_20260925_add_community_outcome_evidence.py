"""S-04 · Community Artifact Feedback → Outcome/Evidence —— community_outcome_evidence 结构化证据表

Revision ID: s04b_20260925
Revises: j05_20260925
Create Date: 2026-09-25

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：drop table community_outcome_evidence
        （结构化社群证据行，非权威真源——采纳真源在
        shared_resource_feedbacks.adopted_at/adopted_into_goal_id 与
        Goal.metadata_payload['community_evidence'] 回执，回滚只丢结构化读面，
        不影响反馈/采纳语义与 goals/tasks 等真源）。"
    verification_query: "SELECT count(*) FROM community_outcome_evidence;"
    backfill_plan: "无回填（新表，从零开始）。存量已采纳反馈（S-03 面上的
        adopted 行）按需由后续治理脚本补影，不在本迁移内隐式改数据。"
    owner: "S-04 (Stream: COMMUNITY)"
    ticket: "v3/07_tasks/cards/S-04.md —— 同伴反馈 → 可采纳的 outcome
        evidence：S-03 已建反馈表与显式采纳端点（adopted_at/adopted_into_goal_id
        + Goal 回执），本表是采纳时刻落的学习飞轮数据面**结构化**证据行
        （全真实外键 goal/feedback/shared_resource，feedback_id 唯一=采纳
        幂等锚点），撤回传播置 retracted（行保留审计）。flywheel 事件
        community.feedback_adopted 的真源在表，outbox 行不是（同 D-05）。

表语义（与 app.models.community.CommunityOutcomeEvidence 一一对应）：
- goal_id：证据挂的目标（GJ16 Goal trajectory 消费面）。
- feedback_id：唯一（一条反馈至多一条证据行）。
- shared_resource_id / owner_id：来源共享与采纳主人。
- verdict：采纳时刻反馈词表值（helpful | insightful | applied）。
- peer_alias：采纳时刻展示别名（不存 giver id——身份留在反馈行）。
- status：adopted | retracted（撤回传播，服务层落值）。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

revision: str = "s04b_20260925"
down_revision: str | None = "j05_20260925"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "community_outcome_evidence"):
        return
    op.create_table(
        "community_outcome_evidence",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("goal_id", GUID(), nullable=False),
        sa.Column("feedback_id", GUID(), nullable=False),
        sa.Column("shared_resource_id", GUID(), nullable=False),
        sa.Column("owner_id", GUID(), nullable=False),
        sa.Column("verdict", sa.String(length=20), nullable=False),
        sa.Column("peer_alias", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="adopted"),
        sa.Column("adopted_at", sa.DateTime(), nullable=False),
        sa.Column("retracted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["feedback_id"], ["shared_resource_feedbacks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shared_resource_id"], ["shared_resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feedback_id", name="uq_coe_feedback_once"),
    )
    op.create_index("idx_coe_goal_status", "community_outcome_evidence", ["goal_id", "status"])
    op.create_index("idx_coe_owner_status", "community_outcome_evidence", ["owner_id", "status"])
    op.create_index("ix_community_outcome_evidence_goal_id", "community_outcome_evidence", ["goal_id"])
    op.create_index(
        "ix_community_outcome_evidence_shared_resource_id",
        "community_outcome_evidence",
        ["shared_resource_id"],
    )
    op.create_index("ix_community_outcome_evidence_owner_id", "community_outcome_evidence", ["owner_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "community_outcome_evidence"):
        return
    op.drop_index("ix_community_outcome_evidence_owner_id", table_name="community_outcome_evidence")
    op.drop_index("ix_community_outcome_evidence_shared_resource_id", table_name="community_outcome_evidence")
    op.drop_index("ix_community_outcome_evidence_goal_id", table_name="community_outcome_evidence")
    op.drop_index("idx_coe_owner_status", table_name="community_outcome_evidence")
    op.drop_index("idx_coe_goal_status", table_name="community_outcome_evidence")
    op.drop_table("community_outcome_evidence")
