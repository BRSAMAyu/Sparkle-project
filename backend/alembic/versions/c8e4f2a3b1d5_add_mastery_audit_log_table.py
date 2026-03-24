"""add_mastery_audit_log_table

Revision ID: c8e4f2a3b1d5
Revises: fb26d4a1c9e2
Create Date: 2026-03-15 19:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1 FROM mastery_audit_log LIMIT 1;"
#   backfill_plan: "n/a - new table"
#   owner: "galaxy-team"
#   ticket: "知识星图系统漏洞修复"

# revision identifiers, used by Alembic.
revision: str = 'c8e4f2a3b1d5'
down_revision: Union[str, None] = 'fb26d4a1c9e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create mastery_audit_log table for tracking mastery score changes."""
    # Use IF NOT EXISTS for idempotency
    op.execute("""
        CREATE TABLE IF NOT EXISTS mastery_audit_log (
            id SERIAL PRIMARY KEY,
            node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            old_mastery INTEGER NOT NULL,
            new_mastery INTEGER NOT NULL,
            reason VARCHAR(100) NOT NULL,
            request_id VARCHAR(100),
            revision INTEGER DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    # Create indexes for query optimization
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mastery_audit_log_user_id
        ON mastery_audit_log(user_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mastery_audit_log_node_id
        ON mastery_audit_log(node_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mastery_audit_log_created_at
        ON mastery_audit_log(created_at DESC)
    """)

    # Composite index for common query pattern: user + node + time
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mastery_audit_log_user_node_time
        ON mastery_audit_log(user_id, node_id, created_at DESC)
    """)


def downgrade() -> None:
    """Drop mastery_audit_log table and its indexes."""
    op.execute("DROP INDEX IF EXISTS idx_mastery_audit_log_user_node_time")
    op.execute("DROP INDEX IF EXISTS idx_mastery_audit_log_created_at")
    op.execute("DROP INDEX IF EXISTS idx_mastery_audit_log_node_id")
    op.execute("DROP INDEX IF EXISTS idx_mastery_audit_log_user_id")
    op.execute("DROP TABLE IF EXISTS mastery_audit_log")
