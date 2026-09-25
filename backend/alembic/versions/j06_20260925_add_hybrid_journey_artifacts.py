"""J-06 · Hybrid Flagship Journey —— hybrid_journey_artifacts 分段产物表

Revision ID: j06_20260925
Revises: j05_20260925
Create Date: 2026-09-25

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：drop table
        hybrid_journey_artifacts（旅程分段产物与 citation 结构；回滚只丢
        产物回放面，run 脊柱/tasks/materials 等真源不受影响）。"
    verification_query: "SELECT count(*) FROM hybrid_journey_artifacts;"
    backfill_plan: "无回填（新表，产物从零开始）。"
    owner: "J-06 (Stream: JOURNEY)"
    ticket: "v3/07_tasks/cards/J-06.md —— Hybrid 旗舰旅程：四段链
        （Agent prep → Human judgment → Agent execute/check → Outcome）
        每段产物带 source/citation 结构；本表只存产物内容与引用结构，
        旅程脊柱仍是 X-05/X-07 agent_runs（零平行真源）。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

revision: str = "j06_20260925"
down_revision: str | None = "s04b_20260925"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "hybrid_journey_artifacts"):
        return
    op.create_table(
        "hybrid_journey_artifacts",
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("run_id", GUID(), nullable=False),
        sa.Column("task_id", GUID(), nullable=True),
        sa.Column("stage", sa.String(length=24), nullable=False),
        sa.Column("artifact_kind", sa.String(length=32), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_hybrid_journey_artifact_run", "hybrid_journey_artifacts", ["run_id"])
    op.create_index("idx_hybrid_journey_artifact_user", "hybrid_journey_artifacts", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "hybrid_journey_artifacts"):
        return
    op.drop_index("idx_hybrid_journey_artifact_user", table_name="hybrid_journey_artifacts")
    op.drop_index("idx_hybrid_journey_artifact_run", table_name="hybrid_journey_artifacts")
    op.drop_table("hybrid_journey_artifacts")
