"""add theater predictions table

Revision ID: tp0c1d2e3f4a5
Revises: tb004d5e6f7a
Create Date: 2026-03-31 00:00:01.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "tp0c1d2e3f4a5"
down_revision = "tb004d5e6f7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_type = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()
    guid_type = postgresql.UUID(as_uuid=True) if is_postgres else sa.String(length=36)

    op.create_table(
        "theater_predictions",
        sa.Column("id", guid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        # Core identity
        sa.Column("prediction_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", guid_type, nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("target_name", sa.String(length=255), nullable=False),
        sa.Column("target_node_id", guid_type, nullable=True),
        sa.Column("target_resolution_mode", sa.String(length=32), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("preview_mode", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        # References
        sa.Column("candidate_bundle_id", guid_type, nullable=True),
        sa.Column("simulation_session_id", sa.String(length=128), nullable=True),
        sa.Column("recommended_route_id", sa.String(length=64), nullable=True),
        # Adoption state
        sa.Column("adopted_plan_id", guid_type, nullable=True),
        sa.Column("adopted_at", sa.DateTime(), nullable=True),
        # Accuracy tracking
        sa.Column("accuracy_status", sa.String(length=32), nullable=False, server_default="pending_feedback"),
        sa.Column("accuracy_due_on", sa.DateTime(), nullable=True),
        # Nested data (JSONB)
        sa.Column("paths", json_type, nullable=False),
        sa.Column("discussion_turns", json_type, nullable=False),
        sa.Column("timeline", json_type, nullable=False),
        sa.Column("selected_prediction", json_type, nullable=True),
        sa.Column("routing_notes", json_type, nullable=False),
        sa.Column("accuracy_tracking", json_type, nullable=False),
        sa.Column("accuracy_summary", json_type, nullable=True),
        # Constraints
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["candidate_bundle_id"],
            ["theater_candidate_bundles.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prediction_id", name="uq_theater_predictions_prediction_id"),
    )

    # Single-column indexes
    op.create_index("ix_theater_predictions_user_id", "theater_predictions", ["user_id"])
    op.create_index("ix_theater_predictions_prediction_id", "theater_predictions", ["prediction_id"])
    op.create_index("ix_theater_predictions_generated_at", "theater_predictions", ["generated_at"])
    op.create_index(
        "ix_theater_predictions_target_resolution_mode",
        "theater_predictions",
        ["target_resolution_mode"],
    )
    op.create_index("ix_theater_predictions_accuracy_status", "theater_predictions", ["accuracy_status"])
    op.create_index("ix_theater_predictions_accuracy_due_on", "theater_predictions", ["accuracy_due_on"])
    op.create_index("ix_theater_predictions_deleted_at", "theater_predictions", ["deleted_at"])

    # Composite indexes
    op.create_index(
        "ix_theater_predictions_user_generated",
        "theater_predictions",
        ["user_id", sa.text("generated_at DESC")],
    )
    op.create_index(
        "ix_theater_predictions_accuracy_pending",
        "theater_predictions",
        ["accuracy_status", "accuracy_due_on"],
    )


def downgrade() -> None:
    op.drop_index("ix_theater_predictions_accuracy_pending", table_name="theater_predictions")
    op.drop_index("ix_theater_predictions_user_generated", table_name="theater_predictions")
    op.drop_index("ix_theater_predictions_deleted_at", table_name="theater_predictions")
    op.drop_index("ix_theater_predictions_accuracy_due_on", table_name="theater_predictions")
    op.drop_index("ix_theater_predictions_accuracy_status", table_name="theater_predictions")
    op.drop_index("ix_theater_predictions_target_resolution_mode", table_name="theater_predictions")
    op.drop_index("ix_theater_predictions_generated_at", table_name="theater_predictions")
    op.drop_index("ix_theater_predictions_prediction_id", table_name="theater_predictions")
    op.drop_index("ix_theater_predictions_user_id", table_name="theater_predictions")
    op.drop_table("theater_predictions")
