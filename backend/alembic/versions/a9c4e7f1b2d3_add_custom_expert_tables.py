"""add custom expert tables

Revision ID: a9c4e7f1b2d3
Revises: 4f8c2b1a9d3e
Create Date: 2026-03-19 19:40:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a9c4e7f1b2d3"
down_revision = "4f8c2b1a9d3e"
branch_labels = None
depends_on = None


def _guid_type():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "custom_expert_profiles",
        sa.Column("user_id", _guid_type(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("base_expert_id", sa.String(length=100), nullable=True),
        sa.Column("preferred_model_key", sa.String(length=100), nullable=True),
        sa.Column("preferred_model_tier", sa.String(length=40), nullable=True),
        sa.Column("reasoning_mode", sa.String(length=40), nullable=False, server_default="balanced"),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="user_defined"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("id", _guid_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_custom_expert_profiles_user_enabled", "custom_expert_profiles", ["user_id", "is_enabled"])
    op.create_index(op.f("ix_custom_expert_profiles_user_id"), "custom_expert_profiles", ["user_id"])
    op.create_index(op.f("ix_custom_expert_profiles_deleted_at"), "custom_expert_profiles", ["deleted_at"])
    op.create_index(op.f("ix_custom_expert_profiles_base_expert_id"), "custom_expert_profiles", ["base_expert_id"])
    op.create_index(op.f("ix_custom_expert_profiles_preferred_model_key"), "custom_expert_profiles", ["preferred_model_key"])
    op.create_index(op.f("ix_custom_expert_profiles_preferred_model_tier"), "custom_expert_profiles", ["preferred_model_tier"])

    op.create_table(
        "custom_expert_teams",
        sa.Column("user_id", _guid_type(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("collaboration_mode", sa.String(length=40), nullable=False, server_default="auto"),
        sa.Column("expert_ids", sa.JSON(), nullable=False),
        sa.Column("answer_expert_ids", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("id", _guid_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_custom_expert_teams_user_enabled", "custom_expert_teams", ["user_id", "is_enabled"])
    op.create_index(op.f("ix_custom_expert_teams_user_id"), "custom_expert_teams", ["user_id"])
    op.create_index(op.f("ix_custom_expert_teams_deleted_at"), "custom_expert_teams", ["deleted_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_custom_expert_teams_deleted_at"), table_name="custom_expert_teams")
    op.drop_index(op.f("ix_custom_expert_teams_user_id"), table_name="custom_expert_teams")
    op.drop_index("idx_custom_expert_teams_user_enabled", table_name="custom_expert_teams")
    op.drop_table("custom_expert_teams")

    op.drop_index(op.f("ix_custom_expert_profiles_preferred_model_tier"), table_name="custom_expert_profiles")
    op.drop_index(op.f("ix_custom_expert_profiles_preferred_model_key"), table_name="custom_expert_profiles")
    op.drop_index(op.f("ix_custom_expert_profiles_base_expert_id"), table_name="custom_expert_profiles")
    op.drop_index(op.f("ix_custom_expert_profiles_deleted_at"), table_name="custom_expert_profiles")
    op.drop_index(op.f("ix_custom_expert_profiles_user_id"), table_name="custom_expert_profiles")
    op.drop_index("idx_custom_expert_profiles_user_enabled", table_name="custom_expert_profiles")
    op.drop_table("custom_expert_profiles")
