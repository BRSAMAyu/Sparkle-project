"""add_memory_evolution_tracking

Revision ID: 7ac528228e20
Revises: 781704add2b9
Create Date: 2026-01-27 01:45:00.000000

Memory Evolution Tracking System - 记忆演化追踪系统
支持记忆变化历史记录、版本对比和预测
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base


revision: str = '7ac528228e20'
down_revision: Union[str, None] = '781704add2b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create memory_evolutions table
    op.create_table(
        "memory_evolutions",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("memory_id", app.models.base.GUID(), nullable=False),
        sa.Column("memory_type", sa.String(length=50), nullable=False),
        sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column("change_reason", sa.String(length=100), nullable=False),
        sa.Column("confidence_delta", sa.Float(), nullable=False, default=0.0),
        sa.Column("confidence_before", sa.Float(), nullable=False, default=0.0),
        sa.Column("confidence_after", sa.Float(), nullable=False, default=0.0),
        sa.Column("evidence_count_before", sa.Integer(), nullable=False, default=0),
        sa.Column("evidence_count_after", sa.Integer(), nullable=False, default=0),
        sa.Column("new_evidence_ids", postgresql.ARRAY(app.models.base.GUID()), nullable=True),
        sa.Column("impact_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("affected_decisions", postgresql.ARRAY(app.models.base.GUID()), nullable=True),
        sa.Column("affected_memories", postgresql.ARRAY(app.models.base.GUID()), nullable=True),
        sa.Column("trigger_event", sa.String(length=100), nullable=True),
        sa.Column("trigger_source", sa.String(length=100), nullable=True),
        sa.Column("workflow_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for memory_evolutions
    with op.batch_alter_table("memory_evolutions", schema=None) as batch_op:
        batch_op.create_index("ix_memory_evolutions_memory_id", ["memory_id"], unique=False)
        batch_op.create_index("ix_memory_evolutions_memory_type", ["memory_type"], unique=False)
        batch_op.create_index("ix_memory_evolutions_change_reason", ["change_reason"], unique=False)
        batch_op.create_index("ix_memory_evolutions_created_at", ["created_at"], unique=False)
        batch_op.create_index("ix_memory_evolutions_deleted_at", ["deleted_at"], unique=False)
        # Composite index for querying evolution history
        batch_op.create_index(
            "ix_memory_evolutions_memory_created",
            ["memory_id", "created_at"],
            unique=False
        )

    # Create evolution_predictions table
    op.create_table(
        "evolution_predictions",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("memory_id", app.models.base.GUID(), nullable=False),
        sa.Column("prediction_type", sa.String(length=50), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("time_horizon", sa.Integer(), nullable=True),
        sa.Column("predicted_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("predicted_confidence", sa.Float(), nullable=True),
        sa.Column("factors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("similar_evolutions", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("actualized_at", sa.DateTime(), nullable=True),
        sa.Column("actualization_error", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for evolution_predictions
    with op.batch_alter_table("evolution_predictions", schema=None) as batch_op:
        batch_op.create_index("ix_evolution_predictions_memory_id", ["memory_id"], unique=False)
        batch_op.create_index("ix_evolution_predictions_type", ["prediction_type"], unique=False)
        batch_op.create_index("ix_evolution_predictions_created_at", ["created_at"], unique=False)
        batch_op.create_index("ix_evolution_predictions_actualized_at", ["actualized_at"], unique=False)
        batch_op.create_index("ix_evolution_predictions_deleted_at", ["deleted_at"], unique=False)


def downgrade() -> None:
    # Drop evolution_predictions
    with op.batch_alter_table("evolution_predictions", schema=None) as batch_op:
        batch_op.drop_index("ix_evolution_predictions_deleted_at")
        batch_op.drop_index("ix_evolution_predictions_actualized_at")
        batch_op.drop_index("ix_evolution_predictions_created_at")
        batch_op.drop_index("ix_evolution_predictions_type")
        batch_op.drop_index("ix_evolution_predictions_memory_id")

    op.drop_table("evolution_predictions")

    # Drop memory_evolutions
    with op.batch_alter_table("memory_evolutions", schema=None) as batch_op:
        batch_op.drop_index("ix_memory_evolutions_deleted_at")
        batch_op.drop_index("ix_memory_evolutions_memory_created")
        batch_op.drop_index("ix_memory_evolutions_created_at")
        batch_op.drop_index("ix_memory_evolutions_change_reason")
        batch_op.drop_index("ix_memory_evolutions_memory_type")
        batch_op.drop_index("ix_memory_evolutions_memory_id")

    op.drop_table("memory_evolutions")
