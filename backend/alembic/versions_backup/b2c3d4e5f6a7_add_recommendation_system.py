"""add_recommendation_system

Revision ID: b2c3d4e5f6a7
Revises: f9d4e5f6a7b8
Create Date: 2026-01-23 00:00:00.000000

Collaborative Filtering Recommendation System - 协同过滤推荐系统
支持用户相似度、物品相似度、交互记录、学习画像等
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM user_similarities;"
#   backfill_plan: "n/a (new tables)"
#   owner: "sparkle-team"
#   ticket: "recommendation-system"

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "f9d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_similarities table
    op.create_table(
        "user_similarities",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id_1", app.models.base.GUID(), nullable=False),
        sa.Column("user_id_2", app.models.base.GUID(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("common_items_count", sa.Integer(), nullable=False, default=0),
        sa.Column("common_subjects", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_calculated_at", sa.DateTime(), nullable=False),
        sa.Column("calculation_version", sa.Integer(), nullable=False, default=1),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id_1"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id_2"], ["users.id"], ondelete="CASCADE"),
    )
    # Indexes for user_similarities
    with op.batch_alter_table("user_similarities", schema=None) as batch_op:
        batch_op.create_index("idx_user_similarity_user1", ["user_id_1"], unique=False)
        batch_op.create_index("idx_user_similarity_user2", ["user_id_2"], unique=False)
        batch_op.create_index("idx_user_similarity_score", ["similarity_score"], unique=False)
        batch_op.create_index("idx_user_similarity_calculated", ["last_calculated_at"], unique=False)
        batch_op.create_index("idx_user_similarities_deleted_at", ["deleted_at"], unique=False)

    # Create item_similarities table
    op.create_table(
        "item_similarities",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("item_id_1", app.models.base.GUID(), nullable=False),
        sa.Column("item_type_1", sa.String(length=50), nullable=False),
        sa.Column("item_id_2", app.models.base.GUID(), nullable=False),
        sa.Column("item_type_2", sa.String(length=50), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("common_learners", sa.Integer(), nullable=False, default=0),
        sa.Column("total_learners_either", sa.Integer(), nullable=False, default=0),
        sa.Column("last_calculated_at", sa.DateTime(), nullable=False),
        sa.Column("subject_id", app.models.base.GUID(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Indexes for item_similarities
    with op.batch_alter_table("item_similarities", schema=None) as batch_op:
        batch_op.create_index("idx_item_similarity_item1", ["item_id_1", "item_type_1"], unique=False)
        batch_op.create_index("idx_item_similarity_item2", ["item_id_2", "item_type_2"], unique=False)
        batch_op.create_index("idx_item_similarity_score", ["similarity_score"], unique=False)
        batch_op.create_index("idx_item_similarities_deleted_at", ["deleted_at"], unique=False)

    # Create user_item_interactions table
    op.create_table(
        "user_item_interactions",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("item_id", app.models.base.GUID(), nullable=False),
        sa.Column("item_type", sa.String(length=50), nullable=False),
        sa.Column("interaction_type", sa.String(length=50), nullable=False),
        sa.Column("interaction_weight", sa.Float(), nullable=False, default=1.0),
        sa.Column("subject_id", app.models.base.GUID(), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    # Indexes for user_item_interactions
    with op.batch_alter_table("user_item_interactions", schema=None) as batch_op:
        batch_op.create_index("idx_user_interaction_user", ["user_id"], unique=False)
        batch_op.create_index("idx_user_interaction_item", ["item_id"], unique=False)
        batch_op.create_index("idx_user_interaction_type", ["interaction_type"], unique=False)
        batch_op.create_index("idx_user_interaction_user_item", ["user_id", "item_id"], unique=False)
        batch_op.create_index("idx_user_interaction_time", ["created_at"], unique=False)
        batch_op.create_index("idx_user_item_interactions_deleted_at", ["deleted_at"], unique=False)

    # Create user_learning_profiles table
    op.create_table(
        "user_learning_profiles",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("preferred_difficulty", sa.Float(), nullable=True),
        sa.Column("preferred_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("preferred_time_of_day", sa.String(length=20), nullable=True),
        sa.Column("subject_distribution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("total_study_minutes", sa.Integer(), nullable=False, default=0),
        sa.Column("total_items_completed", sa.Integer(), nullable=False, default=0),
        sa.Column("average_session_duration", sa.Float(), nullable=True),
        sa.Column("learning_vector", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cluster_id", sa.Integer(), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(), nullable=False),
        sa.Column("update_version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_learning_profile"),
    )
    # Indexes for user_learning_profiles
    with op.batch_alter_table("user_learning_profiles", schema=None) as batch_op:
        batch_op.create_index("idx_user_learning_profiles_user_id", ["user_id"], unique=False)
        batch_op.create_index("idx_user_learning_profiles_cluster_id", ["cluster_id"], unique=False)
        batch_op.create_index("idx_user_learning_profiles_deleted_at", ["deleted_at"], unique=False)

    # Create recommendation_cache table
    op.create_table(
        "recommendation_cache",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("recommendation_type", sa.String(length=50), nullable=False),
        sa.Column("cached_recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    # Indexes for recommendation_cache
    with op.batch_alter_table("recommendation_cache", schema=None) as batch_op:
        batch_op.create_index("idx_rec_cache_user_type", ["user_id", "recommendation_type"], unique=False)
        batch_op.create_index("idx_rec_cache_expires", ["expires_at"], unique=False)
        batch_op.create_index("idx_recommendation_cache_deleted_at", ["deleted_at"], unique=False)

    # Create leaderboard_snapshots table
    op.create_table(
        "leaderboard_snapshots",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("snapshot_type", sa.String(length=50), nullable=False),
        sa.Column("period", sa.String(length=20), nullable=False),
        sa.Column("subject_id", app.models.base.GUID(), nullable=True),
        sa.Column("snapshot_date", sa.DateTime(), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("rankings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("total_participants", sa.Integer(), nullable=False),
        sa.Column("generation_time_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Indexes for leaderboard_snapshots
    with op.batch_alter_table("leaderboard_snapshots", schema=None) as batch_op:
        batch_op.create_index("idx_leaderboard_snapshot_type_date", ["snapshot_type", "snapshot_date"], unique=False)
        batch_op.create_index("idx_leaderboard_snapshot_period", ["period"], unique=False)
        batch_op.create_index("idx_leaderboard_snapshots_deleted_at", ["deleted_at"], unique=False)


def downgrade() -> None:
    # Drop leaderboard_snapshots
    with op.batch_alter_table("leaderboard_snapshots", schema=None) as batch_op:
        batch_op.drop_index("idx_leaderboard_snapshots_deleted_at")
        batch_op.drop_index("idx_leaderboard_snapshot_period")
        batch_op.drop_index("idx_leaderboard_snapshot_type_date")
    op.drop_table("leaderboard_snapshots")

    # Drop recommendation_cache
    with op.batch_alter_table("recommendation_cache", schema=None) as batch_op:
        batch_op.drop_index("idx_recommendation_cache_deleted_at")
        batch_op.drop_index("idx_rec_cache_expires")
        batch_op.drop_index("idx_rec_cache_user_type")
    op.drop_table("recommendation_cache")

    # Drop user_learning_profiles
    with op.batch_alter_table("user_learning_profiles", schema=None) as batch_op:
        batch_op.drop_index("idx_user_learning_profiles_deleted_at")
        batch_op.drop_index("idx_user_learning_profiles_cluster_id")
        batch_op.drop_index("idx_user_learning_profiles_user_id")
    op.drop_table("user_learning_profiles")

    # Drop user_item_interactions
    with op.batch_alter_table("user_item_interactions", schema=None) as batch_op:
        batch_op.drop_index("idx_user_item_interactions_deleted_at")
        batch_op.drop_index("idx_user_interaction_time")
        batch_op.drop_index("idx_user_interaction_user_item")
        batch_op.drop_index("idx_user_interaction_type")
        batch_op.drop_index("idx_user_interaction_item")
        batch_op.drop_index("idx_user_interaction_user")
    op.drop_table("user_item_interactions")

    # Drop item_similarities
    with op.batch_alter_table("item_similarities", schema=None) as batch_op:
        batch_op.drop_index("idx_item_similarities_deleted_at")
        batch_op.drop_index("idx_item_similarity_score")
        batch_op.drop_index("idx_item_similarity_item2")
        batch_op.drop_index("idx_item_similarity_item1")
    op.drop_table("item_similarities")

    # Drop user_similarities
    with op.batch_alter_table("user_similarities", schema=None) as batch_op:
        batch_op.drop_index("idx_user_similarities_deleted_at")
        batch_op.drop_index("idx_user_similarity_calculated")
        batch_op.drop_index("idx_user_similarity_score")
        batch_op.drop_index("idx_user_similarity_user2")
        batch_op.drop_index("idx_user_similarity_user1")
    op.drop_table("user_similarities")
