"""add plan execution records table

Revision ID: p21_plan_execution_records
Revises: p20_user_settings
Create Date: 2026-01-27 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.utils.migration_helpers import get_inspector, table_exists

# revision identifiers, used by Alembic.
revision: str = "p21_plan_execution_records"
down_revision: Union[str, None] = "p20_user_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = get_inspector()

    if not table_exists(inspector, "plan_execution_records"):
        op.create_table(
            "plan_execution_records",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            # Foreign keys
            sa.Column(
                "plan_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("plans.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            # Validation results
            sa.Column("validation_status", sa.String(length=20), nullable=False),
            sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
            # Criteria results
            sa.Column("criteria_results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            # Tool execution stats
            sa.Column("total_tools", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("successful_tools", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_tools", sa.Integer(), nullable=False, server_default="0"),
            # Issues
            sa.Column("issues", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            # User feedback
            sa.Column("user_satisfaction", sa.Integer(), nullable=True),
            sa.Column("user_feedback", sa.Text(), nullable=True),
            # Learning flag
            sa.Column("applied_to_learning", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

        # Create indexes
        op.create_index(
            "ix_plan_execution_records_plan_id",
            "plan_execution_records",
            ["plan_id"]
        )
        op.create_index(
            "ix_plan_execution_records_user_id",
            "plan_execution_records",
            ["user_id"]
        )
        op.create_index(
            "ix_plan_execution_records_plan_user",
            "plan_execution_records",
            ["plan_id", "user_id"]
        )
        op.create_index(
            "ix_plan_execution_records_status",
            "plan_execution_records",
            ["validation_status"]
        )
        op.create_index(
            "ix_plan_execution_records_created",
            "plan_execution_records",
            ["created_at"]
        )


def downgrade() -> None:
    op.drop_table("plan_execution_records")
