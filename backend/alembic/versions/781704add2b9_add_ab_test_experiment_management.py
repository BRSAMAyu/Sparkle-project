"""add_ab_test_experiment_management

Revision ID: 781704add2b9
Revises: d1e2f3a4b5c7
Create Date: 2026-01-27 01:29:19.954824

A/B Test Experiment Management System - A/B测试实验管理系统
支持实验生命周期管理、变体配置、指标跟踪和统计分析
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM ab_experiments;"
#   backfill_plan: "n/a"
#   owner: "sparkle-team"
#   ticket: "ab-test-experiment-management"

revision: str = '781704add2b9'
down_revision: Union[str, None] = 'd1e2f3a4b5c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ab_experiments table (without winning_variant_id FK initially)
    op.create_table(
        "ab_experiments",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, default="created"),
        sa.Column("created_by", app.models.base.GUID(), nullable=True),
        sa.Column("sample_size_target", sa.Integer(), nullable=True),
        sa.Column("significance_level", sa.Float(), nullable=False, default=0.05),
        sa.Column("power", sa.Float(), nullable=False, default=0.8),
        sa.Column("minimum_detectable_effect", sa.Float(), nullable=True),
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("winning_variant_id", app.models.base.GUID(), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )

    # Indexes for ab_experiments
    with op.batch_alter_table("ab_experiments", schema=None) as batch_op:
        batch_op.create_index("ix_ab_experiments_status", ["status"], unique=False)
        batch_op.create_index("ix_ab_experiments_created_by", ["created_by"], unique=False)
        batch_op.create_index("ix_ab_experiments_start_date", ["start_date"], unique=False)
        batch_op.create_index("ix_ab_experiments_deleted_at", ["deleted_at"], unique=False)

    # Create ab_experiment_variants table
    op.create_table(
        "ab_experiment_variants",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("experiment_id", app.models.base.GUID(), nullable=False),
        sa.Column("variant_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_control", sa.Boolean(), nullable=False, default=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("allocation_weight", sa.Float(), nullable=False, default=0.5),
        sa.Column("traffic_allocation_percentage", sa.Float(), nullable=False, default=50.0),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["experiment_id"], ["ab_experiments.id"], ondelete="CASCADE"),
    )

    # Indexes for ab_experiment_variants
    with op.batch_alter_table("ab_experiment_variants", schema=None) as batch_op:
        batch_op.create_index("ix_ab_experiment_variants_experiment_id", ["experiment_id"], unique=False)
        batch_op.create_index("ix_ab_experiment_variants_is_control", ["is_control"], unique=False)
        batch_op.create_index("ix_ab_experiment_variants_deleted_at", ["deleted_at"], unique=False)

    # Add foreign key constraint for winning_variant_id after variants table exists
    op.create_foreign_key(
        "fk_ab_experiments_winning_variant",
        "ab_experiments",
        "ab_experiment_variants",
        ["winning_variant_id"],
        ["id"],
        ondelete="SET NULL"
    )

    # Create ab_experiment_metrics table
    op.create_table(
        "ab_experiment_metrics",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("experiment_id", app.models.base.GUID(), nullable=False),
        sa.Column("variant_id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=True),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("metric_type", sa.String(length=50), nullable=False),  # success, latency, engagement, etc.
        sa.Column("context_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["experiment_id"], ["ab_experiments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["ab_experiment_variants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )

    # Indexes for ab_experiment_metrics
    with op.batch_alter_table("ab_experiment_metrics", schema=None) as batch_op:
        batch_op.create_index("ix_ab_experiment_metrics_experiment_id", ["experiment_id"], unique=False)
        batch_op.create_index("ix_ab_experiment_metrics_variant_id", ["variant_id"], unique=False)
        batch_op.create_index("ix_ab_experiment_metrics_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_ab_experiment_metrics_metric_name", ["metric_name"], unique=False)
        batch_op.create_index("ix_ab_experiment_metrics_timestamp", ["timestamp"], unique=False)
        batch_op.create_index("ix_ab_experiment_metrics_deleted_at", ["deleted_at"], unique=False)
        # Composite index for common queries
        batch_op.create_index(
            "ix_ab_experiment_metrics_experiment_variant_metric",
            ["experiment_id", "variant_id", "metric_name"],
            unique=False
        )

    # Create ab_experiment_assignments table (for tracking user assignments)
    op.create_table(
        "ab_experiment_assignments",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("experiment_id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("variant_id", app.models.base.GUID(), nullable=False),
        sa.Column("assignment_date", sa.DateTime(), nullable=False),
        sa.Column("is_excluded", sa.Boolean(), nullable=False, default=False),
        sa.Column("exclusion_reason", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["experiment_id"], ["ab_experiments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["ab_experiment_variants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("experiment_id", "user_id", name="uq_experiment_user_assignment"),
    )

    # Indexes for ab_experiment_assignments
    with op.batch_alter_table("ab_experiment_assignments", schema=None) as batch_op:
        batch_op.create_index("ix_ab_experiment_assignments_experiment_id", ["experiment_id"], unique=False)
        batch_op.create_index("ix_ab_experiment_assignments_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_ab_experiment_assignments_variant_id", ["variant_id"], unique=False)
        batch_op.create_index("ix_ab_experiment_assignments_is_excluded", ["is_excluded"], unique=False)
        batch_op.create_index("ix_ab_experiment_assignments_deleted_at", ["deleted_at"], unique=False)


def downgrade() -> None:
    # Drop ab_experiment_assignments
    with op.batch_alter_table("ab_experiment_assignments", schema=None) as batch_op:
        batch_op.drop_index("ix_ab_experiment_assignments_deleted_at")
        batch_op.drop_index("ix_ab_experiment_assignments_is_excluded")
        batch_op.drop_index("ix_ab_experiment_assignments_variant_id")
        batch_op.drop_index("ix_ab_experiment_assignments_user_id")
        batch_op.drop_index("ix_ab_experiment_assignments_experiment_id")

    op.drop_table("ab_experiment_assignments")

    # Drop ab_experiment_metrics
    with op.batch_alter_table("ab_experiment_metrics", schema=None) as batch_op:
        batch_op.drop_index("ix_ab_experiment_metrics_experiment_variant_metric")
        batch_op.drop_index("ix_ab_experiment_metrics_timestamp")
        batch_op.drop_index("ix_ab_experiment_metrics_metric_name")
        batch_op.drop_index("ix_ab_experiment_metrics_user_id")
        batch_op.drop_index("ix_ab_experiment_metrics_variant_id")
        batch_op.drop_index("ix_ab_experiment_metrics_experiment_id")
        batch_op.drop_index("ix_ab_experiment_metrics_deleted_at")

    op.drop_table("ab_experiment_metrics")

    # Drop foreign key constraint first
    op.drop_constraint("fk_ab_experiments_winning_variant", "ab_experiments", type_="foreignkey")

    # Drop ab_experiment_variants
    with op.batch_alter_table("ab_experiment_variants", schema=None) as batch_op:
        batch_op.drop_index("ix_ab_experiment_variants_deleted_at")
        batch_op.drop_index("ix_ab_experiment_variants_is_control")
        batch_op.drop_index("ix_ab_experiment_variants_experiment_id")

    op.drop_table("ab_experiment_variants")

    # Drop ab_experiments
    with op.batch_alter_table("ab_experiments", schema=None) as batch_op:
        batch_op.drop_index("ix_ab_experiments_deleted_at")
        batch_op.drop_index("ix_ab_experiments_start_date")
        batch_op.drop_index("ix_ab_experiments_created_by")
        batch_op.drop_index("ix_ab_experiments_status")

    op.drop_table("ab_experiments")
