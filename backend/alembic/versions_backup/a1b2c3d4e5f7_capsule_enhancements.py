"""capsule_enhancements

Revision ID: a1b2c3d4e5f7
Revises: 2b9590b2b29d
Create Date: 2026-01-23 12:00:00.000000

Capsule Enhancements System - 胶囊增强功能
支持 DeepSeek 集成、异步生成、反馈闭环、收藏共享
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM capsule_generation_jobs;"
#   backfill_plan: "n/a"
#   owner: "sparkle-team"
#   ticket: "capsule-enhancements"

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "2b9590b2b29d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type first using raw SQL for PostgreSQL
    op.execute("CREATE TYPE capsule_depth_level AS ENUM ('shallow', 'medium', 'deep')")
    op.execute("CREATE TYPE capsule_job_status AS ENUM ('pending', 'generating', 'completed', 'failed')")

    # Now add new columns to curiosity_capsules table
    op.add_column(
        "curiosity_capsules",
        sa.Column(
            "depth_level",
            sa.Enum("shallow", "medium", "deep", name="capsule_depth_level", create_type=False),
            nullable=True,
        )
    )
    op.add_column(
        "curiosity_capsules",
        sa.Column("generation_method", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "curiosity_capsules",
        sa.Column(
            "source_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        )
    )
    op.add_column(
        "curiosity_capsules",
        sa.Column("quality_score", sa.Float(), nullable=True)
    )
    op.add_column(
        "curiosity_capsules",
        sa.Column("feedback_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "curiosity_capsules",
        sa.Column("share_count", sa.Integer(), nullable=False, server_default="0")
    )

    # Create indexes for curiosity_capsules new columns
    op.create_index("ix_curiosity_capsules_depth_level", "curiosity_capsules", ["depth_level"], unique=False)
    op.create_index("ix_curiosity_capsules_quality_score", "curiosity_capsules", ["quality_score"], unique=False)

    # Create capsule_feedbacks table
    op.create_table(
        "capsule_feedbacks",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("capsule_id", app.models.base.GUID(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),  # 1-5 stars
        sa.Column("helpful", sa.Boolean(), nullable=True),  # thumbs up/down
        sa.Column("category", sa.String(length=50), nullable=True),  # too_long/too_short/just_right/other
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("inferred_depth_delta", sa.Float(), nullable=True),  # feedback effect on preference
        sa.Column("inferred_curiosity_delta", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["capsule_id"], ["curiosity_capsules.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_capsule_feedbacks_user_id", "capsule_feedbacks", ["user_id"], unique=False)
    op.create_index("ix_capsule_feedbacks_capsule_id", "capsule_feedbacks", ["capsule_id"], unique=False)
    op.create_index("ix_capsule_feedbacks_rating", "capsule_feedbacks", ["rating"], unique=False)

    # Create capsule_favorites table
    op.create_table(
        "capsule_favorites",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("capsule_id", app.models.base.GUID(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),  # User's note on why they favorited
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["capsule_id"], ["curiosity_capsules.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "capsule_id", name="uq_capsule_favorite"),
    )
    op.create_index("ix_capsule_favorites_user_id", "capsule_favorites", ["user_id"], unique=False)
    op.create_index("ix_capsule_favorites_capsule_id", "capsule_favorites", ["capsule_id"], unique=False)
    op.create_index("ix_capsule_favorites_created_at", "capsule_favorites", ["created_at"], unique=False)

    # Create capsule_generation_jobs table
    # First create the table without enum, then add the column
    op.execute("""
        CREATE TABLE capsule_generation_jobs (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            generation_type VARCHAR(50) NOT NULL,
            depth_preference FLOAT NOT NULL,
            curiosity_preference FLOAT NOT NULL,
            requested_count INTEGER NOT NULL,
            actual_count INTEGER,
            capsule_ids UUID[],
            progress FLOAT NOT NULL DEFAULT 0.0,
            error_message TEXT,
            duration_ms INTEGER,
            model_used VARCHAR(100),
            scheduled_for TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id)
        )
    """)
    # Now add the status column with the enum
    op.execute("""
        ALTER TABLE capsule_generation_jobs
        ADD COLUMN status capsule_job_status NOT NULL DEFAULT 'pending'
    """)
    op.create_index("ix_capsule_generation_jobs_user_id", "capsule_generation_jobs", ["user_id"], unique=False)
    op.create_index("ix_capsule_generation_jobs_status", "capsule_generation_jobs", ["status"], unique=False)
    op.create_index("ix_capsule_generation_jobs_generation_type", "capsule_generation_jobs", ["generation_type"], unique=False)
    op.create_index("ix_capsule_generation_jobs_created_at", "capsule_generation_jobs", ["created_at"], unique=False)
    op.create_index("ix_capsule_generation_jobs_scheduled_for", "capsule_generation_jobs", ["scheduled_for"], unique=False)


def downgrade() -> None:
    # Drop capsule_generation_jobs
    op.drop_index("ix_capsule_generation_jobs_scheduled_for", "capsule_generation_jobs")
    op.drop_index("ix_capsule_generation_jobs_created_at", "capsule_generation_jobs")
    op.drop_index("ix_capsule_generation_jobs_generation_type", "capsule_generation_jobs")
    op.drop_index("ix_capsule_generation_jobs_status", "capsule_generation_jobs")
    op.drop_index("ix_capsule_generation_jobs_user_id", "capsule_generation_jobs")
    op.drop_table("capsule_generation_jobs")

    # Drop capsule_favorites
    op.drop_index("ix_capsule_favorites_created_at", "capsule_favorites")
    op.drop_index("ix_capsule_favorites_capsule_id", "capsule_favorites")
    op.drop_index("ix_capsule_favorites_user_id", "capsule_favorites")
    op.drop_table("capsule_favorites")

    # Drop capsule_feedbacks
    op.drop_index("ix_capsule_feedbacks_rating", "capsule_feedbacks")
    op.drop_index("ix_capsule_feedbacks_capsule_id", "capsule_feedbacks")
    op.drop_index("ix_capsule_feedbacks_user_id", "capsule_feedbacks")
    op.drop_table("capsule_feedbacks")

    # Remove columns from curiosity_capsules
    op.drop_index("ix_curiosity_capsules_quality_score", "curiosity_capsules")
    op.drop_index("ix_curiosity_capsules_depth_level", "curiosity_capsules")
    op.drop_column("curiosity_capsules", "share_count")
    op.drop_column("curiosity_capsules", "feedback_count")
    op.drop_column("curiosity_capsules", "quality_score")
    op.drop_column("curiosity_capsules", "source_context")
    op.drop_column("curiosity_capsules", "generation_method")
    op.drop_column("curiosity_capsules", "depth_level")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS capsule_job_status")
    op.execute("DROP TYPE IF EXISTS capsule_depth_level")
