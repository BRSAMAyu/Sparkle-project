"""add_chat_sessions_table

Revision ID: e7e90c21943d
Revises: 5f2b9b3c0e6f
Create Date: 2026-01-31 21:03:36.781932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1 FROM chat_sessions LIMIT 1;"
#   backfill_plan: "n/a"
#   owner: "team-sparkle"
#   ticket: "E2E-TEST-001"

# revision identifiers, used by Alembic.
revision: str = 'e7e90c21943d'
down_revision: Union[str, None] = '5f2b9b3c0e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create chat_sessions table for E2E test support."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table('chat_sessions'):
        op.create_table('chat_sessions',
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('last_message_at', sa.DateTime(), nullable=True),
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_session_active ON chat_sessions (is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_session_user_id ON chat_sessions (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_sessions_deleted_at ON chat_sessions (deleted_at)")


def downgrade() -> None:
    """Drop chat_sessions table."""
    with op.batch_alter_table('chat_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_chat_sessions_deleted_at'))
        batch_op.drop_index('idx_chat_session_user_id')
        batch_op.drop_index('idx_chat_session_active')

    op.drop_table('chat_sessions')
