"""add_accountability_interaction_fields

Revision ID: c8e4f2a3b1d6
Revises: b1c2d3e4f5a6
Create Date: 2026-03-17 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c8e4f2a3b1d6"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add likes column to accountability_checkin
    op.add_column(
        "accountability_checkin",
        sa.Column(
            "likes",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),
    )

    # Add encouragements column to accountability_checkin
    op.add_column(
        "accountability_checkin",
        sa.Column(
            "encouragements",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )

    # Add index for created_at to improve timeline queries
    op.create_index(
        "idx_accountability_checkin_created_at",
        "accountability_checkin",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_accountability_checkin_created_at",
        table_name="accountability_checkin",
    )
    op.drop_column("accountability_checkin", "encouragements")
    op.drop_column("accountability_checkin", "likes")
