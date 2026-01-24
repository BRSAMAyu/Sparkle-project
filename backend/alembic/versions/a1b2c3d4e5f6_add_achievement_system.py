"""add_achievement_system

Revision ID: a1b2c3d4e5f6
Revises: a1b2c3d4e5f7
Create Date: 2026-01-23 00:00:00.000000

Achievement System - 成就体系
支持成就定义、用户成就记录、连胜统计、星火契约、星系皮肤
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM achievements;"
#   backfill_plan: "n/a"
#   owner: "sparkle-team"
#   ticket: "achievement-system"

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== Create achievements table ==========
    op.create_table(
        "achievements",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("type", sa.Enum(
            "milestone", "streak", "mastery", "task_complete",
            "hidden", "social", "contract", "study_time", "node_explore",
            name="achievementtype"
        ), nullable=False),
        sa.Column("rarity", sa.Enum(
            "common", "rare", "epic", "legendary",
            name="achievementrarity"
        ), nullable=True),
        sa.Column("trigger_code", sa.String(length=50), nullable=False),
        sa.Column("trigger_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, default=False),
        sa.Column("hint", sa.String(length=200), nullable=True),
        sa.Column("prerequisites", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("visual_effect_type", sa.Enum(
            "none", "black_hole", "supernova", "gravity_wave",
            "nebula_transform", "galaxy_skin", "dual_star",
            name="visualeffecttype"
        ), nullable=True),
        sa.Column("visual_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reward_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("total_unlocked", sa.Integer(), nullable=False, default=0),
        sa.Column("first_unlocker_id", app.models.base.GUID(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("parent_id", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["first_unlocker_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_id"], ["achievements.id"], ondelete="SET NULL"),
    )
    # Indexes for achievements
    with op.batch_alter_table("achievements", schema=None) as batch_op:
        batch_op.create_index("ix_achievements_type", ["type"], unique=False)
        batch_op.create_index("ix_achievements_trigger_code", ["trigger_code"], unique=True)
        batch_op.create_index("ix_achievements_category", ["category"], unique=False)
        batch_op.create_index("ix_achievements_type_rarity", ["type", "rarity"], unique=False)

    # ========== Create user_achievements table ==========
    op.create_table(
        "user_achievements",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("achievement_id", sa.String(length=50), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False, default=0.0),
        sa.Column("progress_value", sa.Integer(), nullable=False, default=0),
        sa.Column("progress_target", sa.Integer(), nullable=False, default=1),
        sa.Column("unlocked_at", sa.DateTime(), nullable=True),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, default=False),
        sa.Column("share_count", sa.Integer(), nullable=False, default=0),
        sa.Column("is_first_unlocker", sa.Boolean(), nullable=False, default=False),
        sa.Column("last_progress_update", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", "user_id", "achievement_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["achievement_id"], ["achievements.id"], ondelete="CASCADE"),
    )
    # Indexes for user_achievements
    with op.batch_alter_table("user_achievements", schema=None) as batch_op:
        batch_op.create_index("ix_user_achievements_user_unlocked", ["user_id", "unlocked_at"], unique=False)
        batch_op.create_index("ix_user_achievements_unlocked_at", ["unlocked_at"], unique=False)

    # ========== Create user_streak_stats table ==========
    op.create_table(
        "user_streak_stats",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("current_streak", sa.Integer(), nullable=False, default=0),
        sa.Column("max_streak", sa.Integer(), nullable=False, default=0),
        sa.Column("last_activity_date", sa.DateTime(), nullable=True),
        sa.Column("freeze_charges", sa.Integer(), nullable=False, default=1),
        sa.Column("max_freeze_charges", sa.Integer(), nullable=False, default=3),
        sa.Column("last_freeze_used_at", sa.DateTime(), nullable=True),
        sa.Column("total_checkin_days", sa.Integer(), nullable=False, default=0),
        sa.Column("longest_streak_start", sa.DateTime(), nullable=True),
        sa.Column("longest_streak_end", sa.DateTime(), nullable=True),
        sa.Column("longest_streak", sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint("id", "user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    # Indexes for user_streak_stats
    with op.batch_alter_table("user_streak_stats", schema=None) as batch_op:
        batch_op.create_index("ix_user_streak_stats_last_activity", ["last_activity_date"], unique=False)

    # ========== Create spark_contracts table ==========
    op.create_table(
        "spark_contracts",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("target_study_minutes", sa.Integer(), nullable=False, default=60),
        sa.Column("target_days", sa.Integer(), nullable=False, default=7),
        sa.Column("photon_stake", sa.Integer(), nullable=False, default=100),
        sa.Column("status", sa.Enum(
            "active", "completed", "failed", "expired",
            name="contractstatus"
        ), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("current_days", sa.Integer(), nullable=False, default=0),
        sa.Column("current_minutes", sa.Integer(), nullable=False, default=0),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("reward_multiplier", sa.Float(), nullable=False, default=2.0),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id", "user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # ========== Create galaxy_skins table ==========
    op.create_table(
        "galaxy_skins",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("preview_url", sa.String(length=500), nullable=True),
        sa.Column("unlock_type", sa.String(length=50), nullable=True),
        sa.Column("unlock_requirement", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("skin_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rarity", sa.Enum(
            "common", "rare", "epic", "legendary",
            name="achievementrarity"
        ), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint("id"),
    )

    # ========== Create user_galaxy_skins table ==========
    op.create_table(
        "user_galaxy_skins",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("skin_id", sa.String(length=50), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(), nullable=False),
        sa.Column("unlock_source", sa.String(length=50), nullable=True),
        sa.Column("is_equipped", sa.Boolean(), nullable=False, default=False),
        sa.PrimaryKeyConstraint("id", "user_id", "skin_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skin_id"], ["galaxy_skins.id"], ondelete="CASCADE"),
    )

    # ========== Create study_buddies table ==========
    op.create_table(
        "study_buddies",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user1_id", app.models.base.GUID(), nullable=False),
        sa.Column("user2_id", app.models.base.GUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, default="active"),
        sa.Column("connection_strength", sa.Float(), nullable=False, default=0.0),
        sa.Column("mutual_study_days", sa.Integer(), nullable=False, default=0),
        sa.Column("last_mutual_study_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user1_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user2_id"], ["users.id"], ondelete="CASCADE"),
    )

    # ========== Create user_titles table ==========
    op.create_table(
        "user_titles",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("title_id", sa.String(length=50), nullable=False),
        sa.Column("title_name", sa.String(length=100), nullable=False),
        sa.Column("title_display", sa.String(length=100), nullable=False),
        sa.Column("source_achievement_id", sa.String(length=50), nullable=True),
        sa.Column("is_equipped", sa.Boolean(), nullable=False, default=False),
        sa.Column("unlocked_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", "user_id", "title_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_achievement_id"], ["achievements.id"], ondelete="SET NULL"),
    )


def downgrade() -> None:
    # Drop user_titles
    op.drop_table("user_titles")

    # Drop study_buddies
    op.drop_table("study_buddies")

    # Drop user_galaxy_skins
    op.drop_table("user_galaxy_skins")

    # Drop galaxy_skins
    with op.batch_alter_table("galaxy_skins", schema=None) as batch_op:
        batch_op.drop_index("ix_galaxy_skins_deleted_at")
    op.drop_table("galaxy_skins")

    # Drop spark_contracts
    op.drop_table("spark_contracts")

    # Drop user_streak_stats
    with op.batch_alter_table("user_streak_stats", schema=None) as batch_op:
        batch_op.drop_index("ix_user_streak_stats_last_activity")
    op.drop_table("user_streak_stats")

    # Drop user_achievements
    with op.batch_alter_table("user_achievements", schema=None) as batch_op:
        batch_op.drop_index("ix_user_achievements_unlocked_at")
        batch_op.drop_index("ix_user_achievements_user_unlocked")
    op.drop_table("user_achievements")

    # Drop achievements
    with op.batch_alter_table("achievements", schema=None) as batch_op:
        batch_op.drop_index("ix_achievements_type_rarity")
        batch_op.drop_index("ix_achievements_category")
        batch_op.drop_index("ix_achievements_trigger_code")
        batch_op.drop_index("ix_achievements_type")
    op.drop_table("achievements")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS achievementtype CASCADE")
    op.execute("DROP TYPE IF EXISTS achievementrarity CASCADE")
    op.execute("DROP TYPE IF EXISTS visualeffecttype CASCADE")
    op.execute("DROP TYPE IF EXISTS contractstatus CASCADE")
