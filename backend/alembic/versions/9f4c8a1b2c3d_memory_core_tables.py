"""memory_core_tables

Revision ID: 9f4c8a1b2c3d
Revises: 8ccc1db58856
Create Date: 2026-01-19 12:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector
import app.models.base


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "team-name"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = "9f4c8a1b2c3d"
down_revision: Union[str, None] = "8ccc1db58856"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memory_preferences",
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("pref_key", sa.String(length=80), nullable=False),
        sa.Column("pref_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("replaced_by_id", app.models.base.GUID(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "pref_key", "version"),
    )
    op.create_index(
        "idx_memory_preferences_user_pref",
        "memory_preferences",
        ["user_id", "pref_key"],
        unique=False,
    )
    op.create_index(
        "ix_memory_preferences_deleted_at",
        "memory_preferences",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "memory_goals",
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("linked_task_id", app.models.base.GUID(), nullable=True),
        sa.Column("linked_plan_id", app.models.base.GUID(), nullable=True),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["linked_plan_id"], ["plans.id"]),
        sa.ForeignKeyConstraint(["linked_task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_memory_goals_user_status_target",
        "memory_goals",
        ["user_id", "status", "target_date"],
        unique=False,
    )
    op.create_index(
        "idx_memory_goals_expires_at",
        "memory_goals",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_memory_goals_deleted_at",
        "memory_goals",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "episodic_memories",
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("summary", sa.String(length=2000), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=True),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_episodic_memories_user_occurred",
        "episodic_memories",
        ["user_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_episodic_memories_deleted_at",
        "episodic_memories",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_episodic_memories_deleted_at", table_name="episodic_memories")
    op.drop_index("idx_episodic_memories_user_occurred", table_name="episodic_memories")
    op.drop_table("episodic_memories")

    op.drop_index("ix_memory_goals_deleted_at", table_name="memory_goals")
    op.drop_index("idx_memory_goals_expires_at", table_name="memory_goals")
    op.drop_index("idx_memory_goals_user_status_target", table_name="memory_goals")
    op.drop_table("memory_goals")

    op.drop_index("ix_memory_preferences_deleted_at", table_name="memory_preferences")
    op.drop_index("idx_memory_preferences_user_pref", table_name="memory_preferences")
    op.drop_table("memory_preferences")
