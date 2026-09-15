"""add community_signal to knowledge_nodes

Revision ID: cs001
Revises:
Create Date: 2026-04-26

"""
from alembic import op
import sqlalchemy as sa

revision = "cs001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_nodes",
        sa.Column("community_signal", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_nodes", "community_signal")
