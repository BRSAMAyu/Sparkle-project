"""evidence_score_and_corrections

Revision ID: b7c1d8e5f3a7
Revises: a4b9d7c6e1f2
Create Date: 2026-01-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.models.base


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "team-name"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = "b7c1d8e5f3a7"
down_revision: Union[str, None] = "a4b9d7c6e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("memory_preferences") as batch_op:
        batch_op.add_column(sa.Column("evidence_score", sa.Float(), nullable=False, server_default=sa.text("0.0")))
        batch_op.add_column(sa.Column("correction_count", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.create_index("idx_memory_preferences_evidence_score", ["evidence_score"], unique=False)

    with op.batch_alter_table("memory_goals") as batch_op:
        batch_op.add_column(sa.Column("evidence_score", sa.Float(), nullable=False, server_default=sa.text("0.0")))
        batch_op.add_column(sa.Column("correction_count", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.create_index("idx_memory_goals_evidence_score", ["evidence_score"], unique=False)

    with op.batch_alter_table("episodic_memories") as batch_op:
        batch_op.add_column(sa.Column("evidence_score", sa.Float(), nullable=False, server_default=sa.text("0.0")))
        batch_op.add_column(sa.Column("correction_count", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.create_index("idx_episodic_memories_evidence_score", ["evidence_score"], unique=False)

    op.create_table(
        "memory_corrections",
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("memory_type", sa.String(length=30), nullable=False),
        sa.Column("memory_id", app.models.base.GUID(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_memory_corrections_user_type_created",
        "memory_corrections",
        ["user_id", "memory_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_memory_corrections_deleted_at",
        "memory_corrections",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_memory_corrections_deleted_at", table_name="memory_corrections")
    op.drop_index("idx_memory_corrections_user_type_created", table_name="memory_corrections")
    op.drop_table("memory_corrections")

    with op.batch_alter_table("episodic_memories") as batch_op:
        batch_op.drop_index("idx_episodic_memories_evidence_score")
        batch_op.drop_column("correction_count")
        batch_op.drop_column("evidence_score")

    with op.batch_alter_table("memory_goals") as batch_op:
        batch_op.drop_index("idx_memory_goals_evidence_score")
        batch_op.drop_column("correction_count")
        batch_op.drop_column("evidence_score")

    with op.batch_alter_table("memory_preferences") as batch_op:
        batch_op.drop_index("idx_memory_preferences_evidence_score")
        batch_op.drop_column("correction_count")
        batch_op.drop_column("evidence_score")
