"""add reflection payload to task feedbacks

Revision ID: d4f7a2c9b3e1
Revises: b7c1f2d4e6a1
Create Date: 2026-03-07 15:30:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d4f7a2c9b3e1"
down_revision = "b7c1f2d4e6a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task_feedbacks",
        sa.Column(
            "reflection_payload",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("task_feedbacks", "reflection_payload")
