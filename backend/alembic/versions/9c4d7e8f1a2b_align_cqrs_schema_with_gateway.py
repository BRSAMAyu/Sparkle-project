"""align_cqrs_schema_with_gateway

Revision ID: 9c4d7e8f1a2b
Revises: 8b2f0b2d9b1a
Create Date: 2026-03-06 14:40:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9c4d7e8f1a2b"
down_revision: Union[str, None] = "8b2f0b2d9b1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;

        CREATE TABLE IF NOT EXISTS event_store (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            aggregate_type varchar(100) NOT NULL,
            aggregate_id uuid NOT NULL,
            event_type varchar(100) NOT NULL,
            event_version integer NOT NULL,
            sequence_number bigint NOT NULL,
            payload jsonb NOT NULL,
            metadata jsonb,
            created_at timestamp without time zone NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_event_store_aggregate
            ON event_store (aggregate_type, aggregate_id, sequence_number);

        CREATE TABLE IF NOT EXISTS processed_events (
            event_id varchar(100) NOT NULL,
            consumer_group varchar(100) NOT NULL,
            processed_at timestamp without time zone NOT NULL DEFAULT now()
        );

        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'processed_events_pkey'
                  AND conrelid = 'processed_events'::regclass
            ) THEN
                ALTER TABLE processed_events DROP CONSTRAINT processed_events_pkey;
            END IF;
        EXCEPTION
            WHEN undefined_table THEN NULL;
        END $$;

        ALTER TABLE processed_events
            ADD CONSTRAINT processed_events_pkey PRIMARY KEY (event_id, consumer_group);

        CREATE TABLE IF NOT EXISTS projection_metadata (
            projection_name varchar(100) PRIMARY KEY,
            last_processed_position varchar(100),
            last_processed_at timestamp without time zone,
            version integer NOT NULL DEFAULT 1,
            status varchar(20) NOT NULL DEFAULT 'active',
            error_message text,
            created_at timestamp without time zone NOT NULL DEFAULT now(),
            updated_at timestamp without time zone NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS projection_snapshots (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            projection_name varchar(100) NOT NULL,
            aggregate_id uuid,
            snapshot_data jsonb NOT NULL,
            stream_position varchar(100) NOT NULL,
            created_at timestamp without time zone NOT NULL DEFAULT now()
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_projection_snapshots_projection_aggregate
            ON projection_snapshots (projection_name, aggregate_id);

        ALTER TABLE event_outbox
            ALTER COLUMN id SET DEFAULT gen_random_uuid();

        ALTER TABLE event_outbox
            ALTER COLUMN event_version SET DEFAULT 1;

        ALTER TABLE event_outbox
            ALTER COLUMN sequence_number SET DEFAULT 1;

        CREATE INDEX IF NOT EXISTS idx_outbox_aggregate
            ON event_outbox (aggregate_type, aggregate_id, sequence_number);

        CREATE INDEX IF NOT EXISTS idx_outbox_unpublished
            ON event_outbox (created_at) WHERE published_at IS NULL;
        """
    )


def downgrade() -> None:
    # Forward-only safety migration: do not drop CQRS tables on downgrade.
    pass
