"""J-05 · Stuck Journey —— stuck_journey_corrections 纠正反馈环表

Revision ID: j05_20260925
Revises: s04_20260924
Create Date: 2026-09-25

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：drop table
        stuck_journey_corrections（纠正反馈记录，非五源权威真源；回滚只
        丢纠正历史，旅程主判断回落引擎原生输出，不影响 tasks/goals/
        study_records 等真源）。"
    verification_query: "SELECT count(*) FROM stuck_journey_corrections;"
    backfill_plan: "无回填（新表，纠正记录从零开始）。"
    owner: "J-05 (Stream: JOURNEY)"
    ticket: "v3/07_tasks/cards/J-05.md ——「我卡住了」旗舰恢复旅程：
        用户「不是这个原因」纠正落库进反馈环（影响后续主判断，不静默
        丢弃）；摩擦诊断真源仍是冻结的 A-03 引擎，本表只存用户主观
        纠正这一正交事实。

表语义（与 app.models.stuck_journey.StuckJourneyCorrection 一一对应）：
- per-user 纠正流水；surface 仅溯源（纠正 per-user 全局生效）。
- friction_type：被纠正的摩擦类型（A-03 FRICTION_TYPES 成员）。
- context_snapshot：纠正时刻旅程 context 快照（evidence candidate）。
- 服务层读取口径：freshness 窗口（14 天）内按 corrected_at 降序，
  上限 20 条（见 stuck_journey_service 常量）。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

from app.models.base import GUID

revision: str = "j05_20260925"
down_revision: str | None = "s04_20260924"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "stuck_journey_corrections"):
        return
    op.create_table(
        "stuck_journey_corrections",
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("surface", sa.String(length=16), nullable=False),
        sa.Column("friction_type", sa.String(length=32), nullable=False),
        sa.Column("intervention_key", sa.String(length=32), nullable=True),
        sa.Column("task_id", GUID(), nullable=True),
        sa.Column("goal_id", GUID(), nullable=True),
        sa.Column("reason_text", sa.String(length=500), nullable=True),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("corrected_at", sa.DateTime(), nullable=False),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_stuck_journey_corr_user", "stuck_journey_corrections", ["user_id"]
    )
    op.create_index(
        "idx_stuck_journey_corr_ftype", "stuck_journey_corrections", ["friction_type"]
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "stuck_journey_corrections"):
        return
    op.drop_index("idx_stuck_journey_corr_ftype", table_name="stuck_journey_corrections")
    op.drop_index("idx_stuck_journey_corr_user", table_name="stuck_journey_corrections")
    op.drop_table("stuck_journey_corrections")
