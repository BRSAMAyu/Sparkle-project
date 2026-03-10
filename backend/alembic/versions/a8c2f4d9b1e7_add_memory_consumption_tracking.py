"""add memory consumption tracking

Revision ID: a8c2f4d9b1e7
Revises: f1a6b3e9c4d2
Create Date: 2026-03-10 22:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a8c2f4d9b1e7"
down_revision = "f1a6b3e9c4d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("memory_preferences", "memory_goals", "episodic_memories"):
        op.add_column(table_name, sa.Column("last_consumed_at", sa.DateTime(), nullable=True))
        op.add_column(table_name, sa.Column("archived_at", sa.DateTime(), nullable=True))

    op.create_index("idx_memory_preferences_last_consumed_at", "memory_preferences", ["last_consumed_at"], unique=False)
    op.create_index("idx_memory_preferences_archived_at", "memory_preferences", ["archived_at"], unique=False)
    op.create_index("idx_memory_goals_last_consumed_at", "memory_goals", ["last_consumed_at"], unique=False)
    op.create_index("idx_memory_goals_archived_at", "memory_goals", ["archived_at"], unique=False)
    op.create_index("idx_episodic_memories_last_consumed_at", "episodic_memories", ["last_consumed_at"], unique=False)
    op.create_index("idx_episodic_memories_archived_at", "episodic_memories", ["archived_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_episodic_memories_archived_at", table_name="episodic_memories")
    op.drop_index("idx_episodic_memories_last_consumed_at", table_name="episodic_memories")
    op.drop_index("idx_memory_goals_archived_at", table_name="memory_goals")
    op.drop_index("idx_memory_goals_last_consumed_at", table_name="memory_goals")
    op.drop_index("idx_memory_preferences_archived_at", table_name="memory_preferences")
    op.drop_index("idx_memory_preferences_last_consumed_at", table_name="memory_preferences")

    for table_name in ("episodic_memories", "memory_goals", "memory_preferences"):
        op.drop_column(table_name, "archived_at")
        op.drop_column(table_name, "last_consumed_at")
