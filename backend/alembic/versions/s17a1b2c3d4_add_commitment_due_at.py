"""add Stage 17 social commitment fields

Revision ID: s17a1b2c3d4
Revises: cl2c1d2e3f4, f9c16a4b2d3e
Create Date: 2026-04-20 18:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "s17a1b2c3d4"
down_revision = ("cl2c1d2e3f4", "f9c16a4b2d3e")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("episodic_memories", sa.Column("subject_type", sa.String(length=32), nullable=False, server_default="self"))
    op.add_column("episodic_memories", sa.Column("due_at", sa.DateTime(), nullable=True))
    op.add_column("episodic_memories", sa.Column("resolved_at", sa.DateTime(), nullable=True))
    op.add_column("episodic_memories", sa.Column("mentioned_entity_hash", sa.String(length=64), nullable=True))
    op.add_column("episodic_memories", sa.Column("mentioned_entity_owner_user_id", sa.UUID(), nullable=True))
    op.create_index("idx_episodic_memories_subject_type", "episodic_memories", ["user_id", "subject_type"], unique=False)
    op.create_index("idx_episodic_memories_due_at", "episodic_memories", ["user_id", "due_at"], unique=False)
    op.alter_column("episodic_memories", "subject_type", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_episodic_memories_due_at", table_name="episodic_memories")
    op.drop_index("idx_episodic_memories_subject_type", table_name="episodic_memories")
    op.drop_column("episodic_memories", "mentioned_entity_owner_user_id")
    op.drop_column("episodic_memories", "mentioned_entity_hash")
    op.drop_column("episodic_memories", "resolved_at")
    op.drop_column("episodic_memories", "due_at")
    op.drop_column("episodic_memories", "subject_type")
