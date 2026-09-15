"""add user_learning_profiles table

Revision ID: oc003c4d5e6f7
Revises: oc002b3c4d5e6
Create Date: 2026-03-28 14:40:00
"""

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID


# revision identifiers, used by Alembic.
revision = "oc003c4d5e6f7"
down_revision = "oc002b3c4d5e6"
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "user_learning_profiles"):
        op.create_table(
            "user_learning_profiles",
            sa.Column("user_id", GUID(), nullable=False),
            sa.Column("preferred_difficulty", sa.Float(), nullable=True),
            sa.Column("preferred_duration_minutes", sa.Integer(), nullable=True),
            sa.Column("preferred_time_of_day", sa.String(length=20), nullable=True),
            sa.Column("subject_distribution", sa.JSON(), nullable=True),
            sa.Column("total_study_minutes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_items_completed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("average_session_duration", sa.Float(), nullable=True),
            sa.Column("learning_vector", sa.JSON(), nullable=True),
            sa.Column("cluster_id", sa.Integer(), nullable=True),
            sa.Column("last_updated_at", sa.DateTime(), nullable=False),
            sa.Column("update_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("id", GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_user_learning_profile"),
        )
        op.create_index(
            "idx_user_learning_profiles_user_id",
            "user_learning_profiles",
            ["user_id"],
        )
        op.create_index(
            "idx_user_learning_profiles_cluster_id",
            "user_learning_profiles",
            ["cluster_id"],
        )
        op.create_index(
            "ix_user_learning_profiles_deleted_at",
            "user_learning_profiles",
            ["deleted_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "user_learning_profiles"):
        op.drop_index("ix_user_learning_profiles_deleted_at", table_name="user_learning_profiles")
        op.drop_index("idx_user_learning_profiles_cluster_id", table_name="user_learning_profiles")
        op.drop_index("idx_user_learning_profiles_user_id", table_name="user_learning_profiles")
        op.drop_table("user_learning_profiles")
