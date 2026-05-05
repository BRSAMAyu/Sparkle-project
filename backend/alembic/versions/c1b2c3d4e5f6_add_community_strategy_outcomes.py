"""add community_strategy_outcomes table

Revision ID: c1b2c3d4e5f6
Revises: z1a2b3c4d5e6
Create Date: 2026-05-06 13:20:00
"""

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID


revision = "c1b2c3d4e5f6"
down_revision = "z1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("community_strategy_outcomes"):
        return

    op.create_table(
        "community_strategy_outcomes",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("directive_id", sa.String(128), nullable=False),
        sa.Column(
            "trigger_type",
            sa.String(64),
            nullable=False,
            comment="What triggered this: cohort_mistake, partner_feedback, resource_recommendation, accountability_checkin",
        ),
        sa.Column(
            "decision",
            sa.String(32),
            nullable=False,
            comment="User choice: accepted, rejected, dismissed, modified, auto_expired",
        ),
        sa.Column(
            "context_snapshot",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql"),
            nullable=False,
            server_default="{}",
            comment="Snapshot of the directive payload at decision time",
        ),
        sa.Column("time_to_decision_seconds", sa.Integer(), nullable=True),
        sa.Column("user_feedback", sa.Text(), nullable=True),
        sa.Column(
            "source",
            sa.String(32),
            nullable=False,
            server_default="system",
            comment="How the decision was recorded: user_action, timeout, system",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_index("ix_cso_user_trigger", "community_strategy_outcomes", ["user_id", "trigger_type"])
    op.create_index("ix_cso_user_decision", "community_strategy_outcomes", ["user_id", "decision"])
    op.create_index("ix_cso_directive", "community_strategy_outcomes", ["directive_id"])


def downgrade() -> None:
    op.drop_table("community_strategy_outcomes")
