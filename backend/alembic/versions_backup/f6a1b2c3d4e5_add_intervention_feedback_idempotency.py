"""add intervention feedback idempotency key

Revision ID: f6a1b2c3d4e5
Revises: f5d0a1b2c3d4
Create Date: 2026-01-20 17:15:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f6a1b2c3d4e5'
down_revision = 'f5d0a1b2c3d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'intervention_feedback',
        sa.Column('idempotency_key', sa.String(length=200), nullable=True),
    )
    op.execute(
        "UPDATE intervention_feedback "
        "SET idempotency_key = request_id::text || ':' || feedback_type "
        "WHERE idempotency_key IS NULL"
    )
    op.alter_column('intervention_feedback', 'idempotency_key', nullable=False)
    op.create_unique_constraint(
        'uq_intervention_feedback_idempotency',
        'intervention_feedback',
        ['user_id', 'request_id', 'feedback_type', 'idempotency_key'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_intervention_feedback_idempotency',
        'intervention_feedback',
        type_='unique',
    )
    op.drop_column('intervention_feedback', 'idempotency_key')
