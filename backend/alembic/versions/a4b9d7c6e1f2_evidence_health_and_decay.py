"""evidence_health_and_decay

Revision ID: a4b9d7c6e1f2
Revises: 9f4c8a1b2c3d
Create Date: 2026-01-19 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "team-name"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = "a4b9d7c6e1f2"
down_revision: Union[str, None] = "9f4c8a1b2c3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("memory_preferences") as batch_op:
        batch_op.add_column(sa.Column("evidence_missing", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch_op.add_column(sa.Column("evidence_checked_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("retracted_at", sa.DateTime(), nullable=True))
        batch_op.create_index("idx_memory_preferences_evidence_missing", ["evidence_missing"], unique=False)

    with op.batch_alter_table("memory_goals") as batch_op:
        batch_op.add_column(sa.Column("evidence_missing", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch_op.add_column(sa.Column("evidence_checked_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("retracted_at", sa.DateTime(), nullable=True))
        batch_op.create_index("idx_memory_goals_evidence_missing", ["evidence_missing"], unique=False)

    with op.batch_alter_table("episodic_memories") as batch_op:
        batch_op.add_column(sa.Column("evidence_missing", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch_op.add_column(sa.Column("evidence_checked_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("evidence_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        batch_op.add_column(sa.Column("retracted_at", sa.DateTime(), nullable=True))
        batch_op.create_index("idx_episodic_memories_evidence_missing", ["evidence_missing"], unique=False)

    with op.batch_alter_table("behavior_patterns") as batch_op:
        batch_op.add_column(sa.Column("last_observed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_decay_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("behavior_patterns") as batch_op:
        batch_op.drop_column("last_decay_at")
        batch_op.drop_column("last_observed_at")

    with op.batch_alter_table("episodic_memories") as batch_op:
        batch_op.drop_index("idx_episodic_memories_evidence_missing")
        batch_op.drop_column("retracted_at")
        batch_op.drop_column("evidence_snapshot")
        batch_op.drop_column("evidence_checked_at")
        batch_op.drop_column("evidence_missing")

    with op.batch_alter_table("memory_goals") as batch_op:
        batch_op.drop_index("idx_memory_goals_evidence_missing")
        batch_op.drop_column("retracted_at")
        batch_op.drop_column("evidence_checked_at")
        batch_op.drop_column("evidence_missing")

    with op.batch_alter_table("memory_preferences") as batch_op:
        batch_op.drop_index("idx_memory_preferences_evidence_missing")
        batch_op.drop_column("retracted_at")
        batch_op.drop_column("evidence_checked_at")
        batch_op.drop_column("evidence_missing")
