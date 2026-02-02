"""add_notification_center_tables

Revision ID: cf32be97c82a
Revises: ec25882a0a41
Create Date: 2026-01-28 01:31:14.676938

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM notification_interactions;"
#   backfill_plan: "n/a"
#   owner: "backend-team"
#   ticket: "notification-center-enhancement"

# revision identifiers, used by Alembic.
revision: str = 'cf32be97c82a'
down_revision: Union[str, None] = 'ec25882a0a41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notification_interactions table
    op.create_table(
        "notification_interactions",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("notification_type", sa.String(20), nullable=False, comment="system or intervention"),
        sa.Column("notification_id", UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(40), nullable=False, comment="viewed, clicked, dismissed"),
        sa.Column("action_time", sa.DateTime(), nullable=False),
        sa.Column("time_to_action", sa.Integer(), nullable=True, comment="Seconds from creation to action"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_interactions_user_id", "notification_interactions", ["user_id"])
    op.create_index("ix_notification_interactions_notification_id", "notification_interactions", ["notification_id"])
    op.create_index("ix_notification_interactions_action_time", "notification_interactions", ["action_time"])

    # Create notification_preferences table
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("enable_system", sa.Boolean(), default=True, nullable=False),
        sa.Column("enable_interventions", sa.Boolean(), default=True, nullable=False),
        sa.Column("notification_level", sa.String(20), default="standard", nullable=False),
        sa.Column("quiet_hours_enabled", sa.Boolean(), default=False, nullable=False),
        sa.Column("quiet_hours_start", sa.String(5), nullable=True, comment="HH:MM format"),
        sa.Column("quiet_hours_end", sa.String(5), nullable=True, comment="HH:MM format"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_table("notification_interactions")
