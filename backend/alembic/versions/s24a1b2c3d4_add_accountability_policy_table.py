"""add accountability policy compiler table

Revision ID: s24a1b2c3d4
Revises: s23a1b2c3d4
Create Date: 2026-04-21 23:55:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "s24a1b2c3d4"
down_revision = "s23a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accountability_policies",
        sa.Column("policy_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("policy_type", sa.String(length=64), nullable=False),
        sa.Column("trigger_type", sa.String(length=64), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("ir_payload", sa.JSON(), nullable=False),
        sa.Column("ir_hash", sa.String(length=64), nullable=False),
        sa.Column("next_trigger_at", sa.DateTime(), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("cooldown_until", sa.DateTime(), nullable=True),
        sa.Column("last_event_key", sa.String(length=128), nullable=True),
        sa.Column("execution_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_shadow", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_skip_reason", sa.String(length=64), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["commitment_id"], ["episodic_memories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id"),
    )
    op.create_index("ix_accountability_policies_deleted_at", "accountability_policies", ["deleted_at"], unique=False)
    op.create_index("ix_accountability_policies_policy_id", "accountability_policies", ["policy_id"], unique=True)
    op.create_index("ix_accountability_policies_user_id", "accountability_policies", ["user_id"], unique=False)
    op.create_index(
        "idx_accountability_policies_user_next_trigger",
        "accountability_policies",
        ["user_id", "next_trigger_at"],
        unique=False,
    )
    op.create_index(
        "idx_accountability_policies_commitment_enabled",
        "accountability_policies",
        ["commitment_id", "is_enabled"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_accountability_policies_commitment_enabled", table_name="accountability_policies")
    op.drop_index("idx_accountability_policies_user_next_trigger", table_name="accountability_policies")
    op.drop_index("ix_accountability_policies_user_id", table_name="accountability_policies")
    op.drop_index("ix_accountability_policies_policy_id", table_name="accountability_policies")
    op.drop_index("ix_accountability_policies_deleted_at", table_name="accountability_policies")
    op.drop_table("accountability_policies")
