"""add push history interactions

Revision ID: f4c9d1e2a3b5
Revises: f3b8c1d2e4f5
Create Date: 2026-02-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "f4c9d1e2a3b5"
down_revision = "f3b8c1d2e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("push_histories", sa.Column("interaction_type", sa.String(length=50), nullable=True))
    op.add_column("push_histories", sa.Column("interacted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("push_histories", "interacted_at")
    op.drop_column("push_histories", "interaction_type")
