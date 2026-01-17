"""add event sequence counters

Revision ID: p18_event_sequence_counters
Revises: p17_learning_assets
Create Date: 2026-01-16 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.utils.migration_helpers import get_inspector, table_exists

# revision identifiers, used by Alembic.
revision: str = 'p18_event_sequence_counters'
down_revision: Union[str, None] = 'p17_learning_assets'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create event_sequence_counters table for outbox sequencing."""
    inspector = get_inspector()

    if not table_exists(inspector, "event_sequence_counters"):
        op.create_table(
            'event_sequence_counters',
            sa.Column('aggregate_type', sa.String(length=100), nullable=False),
            sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('next_sequence', sa.BigInteger(), nullable=False, server_default='1'),
            sa.PrimaryKeyConstraint('aggregate_type', 'aggregate_id')
        )


def downgrade() -> None:
    """Drop event_sequence_counters table."""
    op.drop_table('event_sequence_counters')
