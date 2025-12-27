"""add cqrs infrastructure tables

Revision ID: cqrs_001
Revises: add_agent_stats_table
Create Date: 2025-12-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'cqrs_001'
down_revision = 'add_agent_stats_table'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Event Outbox Table (Transactional Outbox Pattern)
    op.create_table('event_outbox',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('aggregate_type', sa.String(100), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('sequence_number', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Partial index for unpublished events (optimized for publisher polling)
    op.execute("""
        CREATE INDEX idx_outbox_unpublished ON event_outbox (created_at)
        WHERE published_at IS NULL
    """)

    # Index for aggregate event lookup
    op.create_index('idx_outbox_aggregate', 'event_outbox',
                    ['aggregate_type', 'aggregate_id', 'sequence_number'], unique=False)

    # 2. Event Store Table (Complete Event History for Event Sourcing)
    op.create_table('event_store',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('aggregate_type', sa.String(100), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_version', sa.Integer(), nullable=False),
        sa.Column('sequence_number', sa.BigInteger(), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aggregate_type', 'aggregate_id', 'sequence_number', name='unique_event')
    )

    op.create_index('idx_event_store_aggregate', 'event_store',
                    ['aggregate_type', 'aggregate_id', 'sequence_number'], unique=False)
    op.create_index('idx_event_store_type', 'event_store',
                    ['event_type', 'created_at'], unique=False)

    # 3. Processed Events Table (Idempotency Tracking)
    op.create_table('processed_events',
        sa.Column('event_id', sa.String(100), nullable=False),
        sa.Column('consumer_group', sa.String(100), nullable=False),
        sa.Column('processed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('event_id')
    )

    op.create_index('idx_processed_events_cleanup', 'processed_events',
                    ['processed_at'], unique=False)
    op.create_index('idx_processed_events_group', 'processed_events',
                    ['consumer_group', 'processed_at'], unique=False)

    # 4. Projection Metadata Table (Projection Lifecycle Management)
    op.create_table('projection_metadata',
        sa.Column('projection_name', sa.String(100), nullable=False),
        sa.Column('last_processed_position', sa.String(100), nullable=True),
        sa.Column('last_processed_at', sa.DateTime(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(20), nullable=False, server_default="'active'"),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('projection_name')
    )

    # 5. Projection Snapshots Table (Fast Projection Recovery)
    op.create_table('projection_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('projection_name', sa.String(100), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('snapshot_data', postgresql.JSONB(), nullable=False),
        sa.Column('stream_position', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('projection_name', 'aggregate_id', name='unique_snapshot')
    )

    op.create_index('idx_snapshots_projection', 'projection_snapshots',
                    ['projection_name', 'created_at'], unique=False)

    # Insert default projection metadata for existing projections
    op.execute("""
        INSERT INTO projection_metadata (projection_name, status, version)
        VALUES
            ('community_feed', 'active', 1),
            ('task_list', 'active', 1),
            ('galaxy_graph', 'active', 1)
        ON CONFLICT (projection_name) DO NOTHING
    """)


def downgrade():
    op.drop_table('projection_snapshots')
    op.drop_table('projection_metadata')
    op.drop_table('processed_events')
    op.drop_table('event_store')
    op.execute('DROP INDEX IF EXISTS idx_outbox_unpublished')
    op.drop_table('event_outbox')
