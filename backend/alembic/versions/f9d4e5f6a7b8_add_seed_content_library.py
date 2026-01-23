"""add_seed_content_library

Revision ID: f9d4e5f6a7b8
Revises: f8c3d4e5f6a7
Create Date: 2026-01-23 00:00:00.000000

Seed Content Library System - 模块化种子内容库
支持 few-shot 示例、预设教学内容、通用回复模板
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector
import app.models.base

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM seed_libraries;"
#   backfill_plan: "n/a"
#   owner: "sparkle-team"
#   ticket: "seed-content-library"

revision: str = "f9d4e5f6a7b8"
down_revision: Union[str, None] = "f8c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create seed_libraries table
    op.create_table(
        "seed_libraries",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False, default="private"),
        sa.Column("owner_id", app.models.base.GUID(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, default="zh"),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_official", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False, default=False),
        sa.Column("usage_count", sa.Integer(), nullable=False, default=0),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
    )
    # Indexes for seed_libraries
    with op.batch_alter_table("seed_libraries", schema=None) as batch_op:
        batch_op.create_index("ix_seed_libraries_category", ["category"], unique=False)
        batch_op.create_index("ix_seed_libraries_visibility", ["visibility"], unique=False)
        batch_op.create_index("ix_seed_libraries_owner_id", ["owner_id"], unique=False)
        batch_op.create_index("ix_seed_libraries_is_official", ["is_official"], unique=False)
        batch_op.create_index("ix_seed_libraries_is_featured", ["is_featured"], unique=False)
        batch_op.create_index("ix_seed_libraries_tags", ["tags"], unique=False, postgresql_using="gin")
        batch_op.create_index("ix_seed_libraries_deleted_at", ["deleted_at"], unique=False)

    # Create seed_items table
    op.create_table(
        "seed_items",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("library_id", app.models.base.GUID(), nullable=False),
        sa.Column("item_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("subject", sa.String(length=100), nullable=True),
        sa.Column("difficulty_level", sa.String(length=20), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, default=0),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["library_id"], ["seed_libraries.id"], ondelete="CASCADE"),
    )
    # Indexes for seed_items
    with op.batch_alter_table("seed_items", schema=None) as batch_op:
        batch_op.create_index("ix_seed_items_library_id", ["library_id"], unique=False)
        batch_op.create_index("ix_seed_items_item_type", ["item_type"], unique=False)
        batch_op.create_index("ix_seed_items_subject", ["subject"], unique=False)
        batch_op.create_index("ix_seed_items_difficulty_level", ["difficulty_level"], unique=False)
        batch_op.create_index("ix_seed_items_is_active", ["is_active"], unique=False)
        batch_op.create_index("ix_seed_items_tags", ["tags"], unique=False, postgresql_using="gin")
        batch_op.create_index("ix_seed_items_deleted_at", ["deleted_at"], unique=False)
        # HNSW index for vector similarity search
        batch_op.create_index(
            "ix_seed_items_embedding_hnsw",
            ["embedding"],
            unique=False,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_l2_ops"},
        )

    # Create user_library_subscriptions table
    op.create_table(
        "user_library_subscriptions",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("library_id", app.models.base.GUID(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column("priority", sa.Integer(), nullable=False, default=0),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("subscribed_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["library_id"], ["seed_libraries.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "library_id", name="uq_user_library_subscription"),
    )
    # Indexes for user_library_subscriptions
    with op.batch_alter_table("user_library_subscriptions", schema=None) as batch_op:
        batch_op.create_index("ix_user_library_subscriptions_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_user_library_subscriptions_library_id", ["library_id"], unique=False)
        batch_op.create_index("ix_user_library_subscriptions_is_enabled", ["is_enabled"], unique=False)
        batch_op.create_index("ix_user_library_subscriptions_deleted_at", ["deleted_at"], unique=False)


def downgrade() -> None:
    # Drop user_library_subscriptions
    with op.batch_alter_table("user_library_subscriptions", schema=None) as batch_op:
        batch_op.drop_index("ix_user_library_subscriptions_deleted_at")
        batch_op.drop_index("ix_user_library_subscriptions_is_enabled")
        batch_op.drop_index("ix_user_library_subscriptions_library_id")
        batch_op.drop_index("ix_user_library_subscriptions_user_id")

    op.drop_table("user_library_subscriptions")

    # Drop seed_items
    with op.batch_alter_table("seed_items", schema=None) as batch_op:
        batch_op.drop_index("ix_seed_items_deleted_at")
        batch_op.drop_index("ix_seed_items_tags")
        batch_op.drop_index("ix_seed_items_is_active")
        batch_op.drop_index("ix_seed_items_difficulty_level")
        batch_op.drop_index("ix_seed_items_subject")
        batch_op.drop_index("ix_seed_items_item_type")
        batch_op.drop_index("ix_seed_items_library_id")
        batch_op.drop_index("ix_seed_items_embedding_hnsw")

    op.drop_table("seed_items")

    # Drop seed_libraries
    with op.batch_alter_table("seed_libraries", schema=None) as batch_op:
        batch_op.drop_index("ix_seed_libraries_deleted_at")
        batch_op.drop_index("ix_seed_libraries_tags")
        batch_op.drop_index("ix_seed_libraries_is_featured")
        batch_op.drop_index("ix_seed_libraries_is_official")
        batch_op.drop_index("ix_seed_libraries_owner_id")
        batch_op.drop_index("ix_seed_libraries_visibility")
        batch_op.drop_index("ix_seed_libraries_category")

    op.drop_table("seed_libraries")
