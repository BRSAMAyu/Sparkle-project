"""add missing recommendation tables

Revision ID: a6e9c1f4d2b3
Revises: fb26d4a1c9e2
Create Date: 2026-03-14 19:08:00
"""

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID


# revision identifiers, used by Alembic.
revision = "a6e9c1f4d2b3"
down_revision = "fb26d4a1c9e2"
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "user_item_interactions"):
        op.create_table(
            "user_item_interactions",
            sa.Column("user_id", GUID(), nullable=False),
            sa.Column("item_id", GUID(), nullable=False),
            sa.Column("item_type", sa.String(length=50), nullable=False),
            sa.Column("interaction_type", sa.String(length=50), nullable=False),
            sa.Column("interaction_weight", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("subject_id", GUID(), nullable=True),
            sa.Column("session_id", sa.String(length=100), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("id", GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_user_interaction_user", "user_item_interactions", ["user_id"])
        op.create_index("idx_user_interaction_item", "user_item_interactions", ["item_id"])
        op.create_index(
            "idx_user_interaction_type", "user_item_interactions", ["interaction_type"],
        )
        op.create_index(
            "idx_user_interaction_user_item",
            "user_item_interactions",
            ["user_id", "item_id"],
        )
        op.create_index("idx_user_interaction_time", "user_item_interactions", ["created_at"])
        op.create_index(
            "ix_user_item_interactions_deleted_at",
            "user_item_interactions",
            ["deleted_at"],
        )

    if not _has_table(bind, "recommendation_cache"):
        op.create_table(
            "recommendation_cache",
            sa.Column("user_id", GUID(), nullable=False),
            sa.Column("recommendation_type", sa.String(length=50), nullable=False),
            sa.Column("cached_recommendations", sa.JSON(), nullable=False),
            sa.Column("generated_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("id", GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "idx_rec_cache_user_type",
            "recommendation_cache",
            ["user_id", "recommendation_type"],
        )
        op.create_index("idx_rec_cache_expires", "recommendation_cache", ["expires_at"])
        op.create_index(
            "ix_recommendation_cache_deleted_at",
            "recommendation_cache",
            ["deleted_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "recommendation_cache"):
        op.drop_index("ix_recommendation_cache_deleted_at", table_name="recommendation_cache")
        op.drop_index("idx_rec_cache_expires", table_name="recommendation_cache")
        op.drop_index("idx_rec_cache_user_type", table_name="recommendation_cache")
        op.drop_table("recommendation_cache")

    if _has_table(bind, "user_item_interactions"):
        op.drop_index("ix_user_item_interactions_deleted_at", table_name="user_item_interactions")
        op.drop_index("idx_user_interaction_time", table_name="user_item_interactions")
        op.drop_index("idx_user_interaction_user_item", table_name="user_item_interactions")
        op.drop_index("idx_user_interaction_type", table_name="user_item_interactions")
        op.drop_index("idx_user_interaction_item", table_name="user_item_interactions")
        op.drop_index("idx_user_interaction_user", table_name="user_item_interactions")
        op.drop_table("user_item_interactions")
