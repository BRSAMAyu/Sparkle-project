"""add missing columns to user_tool_history

Revision ID: dd145e048e0c
Revises: d1e2f3a4b5c7
Create Date: 2026-01-27 01:43:10.036813

This migration adds missing columns to user_tool_history table that are
defined in the model but missing from the database schema.

Root cause: Code expects tool_category, error_type, input_args, output_summary,
user_satisfaction, and was_helpful columns which don't exist, causing
InFailedSQLTransactionError cascades.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'dd145e048e0c'
down_revision: Union[str, None] = '781704add2b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Get existing columns
    existing_columns = {col.get("name") for col in inspector.get_columns('user_tool_history')}

    # Add missing columns with idempotency checks
    with op.batch_alter_table('user_tool_history', schema=None) as batch_op:
        if 'tool_category' not in existing_columns:
            batch_op.add_column(sa.Column('tool_category', sa.String(length=50), nullable=True))
        if 'error_type' not in existing_columns:
            batch_op.add_column(sa.Column('error_type', sa.String(length=100), nullable=True))
        if 'input_args' not in existing_columns:
            batch_op.add_column(sa.Column('input_args', postgresql.JSON(), nullable=True))
        if 'output_summary' not in existing_columns:
            batch_op.add_column(sa.Column('output_summary', sa.Text(), nullable=True))
        if 'user_satisfaction' not in existing_columns:
            batch_op.add_column(sa.Column('user_satisfaction', sa.Integer(), nullable=True))
        if 'was_helpful' not in existing_columns:
            batch_op.add_column(sa.Column('was_helpful', sa.Boolean(), nullable=True))

        # Fix context_snapshot type from JSONB to JSON if needed
        # (Model says JSON, DB has JSONB - both compatible, but keeping consistency)


def downgrade() -> None:
    # Remove the added columns
    with op.batch_alter_table('user_tool_history', schema=None) as batch_op:
        batch_op.drop_column('was_helpful')
        batch_op.drop_column('user_satisfaction')
        batch_op.drop_column('output_summary')
        batch_op.drop_column('input_args')
        batch_op.drop_column('error_type')
        batch_op.drop_column('tool_category')
