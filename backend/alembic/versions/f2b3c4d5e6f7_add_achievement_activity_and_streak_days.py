"""add achievement activity window and streak days

Revision ID: f2b3c4d5e6f7
Revises: e6b4c9d2a7f1
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f2b3c4d5e6f7"
down_revision = "e6b4c9d2a7f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("achievements", sa.Column("active_from", sa.DateTime(), nullable=True))
    op.add_column("achievements", sa.Column("active_to", sa.DateTime(), nullable=True))
    op.add_column("achievements", sa.Column("is_limited", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("achievements", sa.Column("event_tag", sa.String(50), nullable=True))

    op.create_table(
        "user_streak_days",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "frozen", "missed", name="streakdaystatus"),
            nullable=False,
        ),
        sa.Column("used_freeze", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_event", sa.String(50), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "day"),
    )
    op.create_index(
        "ix_user_streak_days_user_day",
        "user_streak_days",
        ["user_id", "day"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_user_streak_days_user_day", table_name="user_streak_days")
    op.drop_table("user_streak_days")
    op.execute("DROP TYPE IF EXISTS streakdaystatus")

    op.drop_column("achievements", "event_tag")
    op.drop_column("achievements", "is_limited")
    op.drop_column("achievements", "active_to")
    op.drop_column("achievements", "active_from")
