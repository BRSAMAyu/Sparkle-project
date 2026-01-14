"""Add agent execution stats table

Revision ID: add_agent_stats
Revises: a1b2c3d4e5f6
Create Date: 2025-12-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.utils.migration_helpers import get_inspector, table_exists

# revision identifiers, used by Alembic.
revision = 'add_agent_stats'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    inspector = get_inspector()
    # Create agent_execution_stats table
    if not table_exists(inspector, "agent_execution_stats"):
        op.create_table(
            'agent_execution_stats',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('session_id', sa.String(255), nullable=False),
            sa.Column('request_id', sa.String(255), nullable=False),

            # Agent information
            sa.Column('agent_type', sa.String(50), nullable=False),  # orchestrator, knowledge, math, etc.
            sa.Column('agent_name', sa.String(100), nullable=True),  # Human-readable name

            # Execution metrics
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('duration_ms', sa.Integer(), nullable=True),  # Computed: completed_at - started_at
            sa.Column('status', sa.String(20), nullable=False),  # 'success', 'failed', 'timeout'

            # Tool/operation details
            sa.Column('tool_name', sa.String(100), nullable=True),  # If agent executed a tool
            sa.Column('operation', sa.String(255), nullable=True),  # Description of operation

            # Metadata
            sa.Column('metadata', postgresql.JSONB(), nullable=True),  # Additional context
            sa.Column('error_message', sa.Text(), nullable=True),  # If failed

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

            # Primary key
            sa.PrimaryKeyConstraint('id'),

            # Indexes
            sa.Index('ix_agent_stats_user_id', 'user_id'),
            sa.Index('ix_agent_stats_session_id', 'session_id'),
            sa.Index('ix_agent_stats_agent_type', 'agent_type'),
            sa.Index('ix_agent_stats_created_at', 'created_at'),
            sa.Index('ix_agent_stats_user_agent_type', 'user_id', 'agent_type'),  # Composite index for user analytics
        )

    # Create materialized view for aggregated stats (optional, for performance)
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS agent_stats_summary AS
        SELECT
            user_id,
            agent_type,
            COUNT(*) as execution_count,
            AVG(duration_ms) as avg_duration_ms,
            MAX(duration_ms) as max_duration_ms,
            MIN(duration_ms) as min_duration_ms,
            COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failure_count,
            MAX(created_at) as last_used_at
        FROM agent_execution_stats
        WHERE completed_at IS NOT NULL
        GROUP BY user_id, agent_type;
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_stats_summary_user_agent
        ON agent_stats_summary (user_id, agent_type);
    """)


def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS agent_stats_summary;")
    inspector = get_inspector()
    if table_exists(inspector, "agent_execution_stats"):
        op.drop_table('agent_execution_stats')
