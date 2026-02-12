"""create_event_outbox_tables

Revision ID: 5f2b9b3c0e6f
Revises: 4f6c3b8e1d2a
Create Date: 2026-01-30 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

import app.models.base


# revision identifiers, used by Alembic.
revision: str = "5f2b9b3c0e6f"
down_revision: Union[str, None] = "4f6c3b8e1d2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_column():
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def _ensure_event_outbox(inspector: sa.Inspector, dialect: str) -> None:
    if not inspector.has_table("event_outbox"):
        id_default = sa.text("gen_random_uuid()") if dialect == "postgresql" else None
        op.create_table(
            "event_outbox",
            sa.Column("id", app.models.base.GUID(), server_default=id_default, nullable=False),
            sa.Column("aggregate_type", sa.String(length=100), nullable=False),
            sa.Column("aggregate_id", app.models.base.GUID(), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("event_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
            sa.Column("payload", _json_column(), nullable=False),
            sa.Column("metadata", _json_column(), nullable=True),
            sa.Column("sequence_number", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        # Repair legacy/manual schema drift (bytea payloads, missing defaults)
        if dialect == "postgresql":
            op.execute(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'event_outbox' AND column_name = 'id'
                          AND column_default IS NULL
                    ) THEN
                        ALTER TABLE event_outbox ALTER COLUMN id SET DEFAULT gen_random_uuid();
                    END IF;

                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'event_outbox' AND column_name = 'payload'
                          AND data_type = 'bytea'
                    ) THEN
                        ALTER TABLE event_outbox
                            ALTER COLUMN payload TYPE jsonb
                            USING convert_from(payload, 'UTF8')::jsonb;
                    ELSIF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'event_outbox' AND column_name = 'payload'
                          AND data_type = 'json'
                    ) THEN
                        ALTER TABLE event_outbox
                            ALTER COLUMN payload TYPE jsonb
                            USING payload::jsonb;
                    END IF;

                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'event_outbox' AND column_name = 'metadata'
                          AND data_type = 'bytea'
                    ) THEN
                        ALTER TABLE event_outbox
                            ALTER COLUMN metadata TYPE jsonb
                            USING convert_from(metadata, 'UTF8')::jsonb;
                    ELSIF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'event_outbox' AND column_name = 'metadata'
                          AND data_type = 'json'
                    ) THEN
                        ALTER TABLE event_outbox
                            ALTER COLUMN metadata TYPE jsonb
                            USING metadata::jsonb;
                    END IF;
                END $$;
                """
            )

    # Indexes (safe for existing tables)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_outbox_aggregate ON event_outbox (aggregate_type, aggregate_id, sequence_number)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_outbox_unpublished ON event_outbox (created_at) WHERE (published_at IS NULL)"
    )


def _ensure_event_sequence_counters(inspector: sa.Inspector, dialect: str) -> None:
    if not inspector.has_table("event_sequence_counters"):
        op.create_table(
            "event_sequence_counters",
            sa.Column("aggregate_type", sa.String(length=100), nullable=False),
            sa.Column("aggregate_id", app.models.base.GUID(), nullable=False),
            sa.Column("next_sequence", sa.BigInteger(), server_default=sa.text("1"), nullable=False),
            sa.PrimaryKeyConstraint("aggregate_type", "aggregate_id"),
        )
    else:
        pk = inspector.get_pk_constraint("event_sequence_counters")
        if not pk or not pk.get("constrained_columns"):
            op.create_primary_key(
                "event_sequence_counters_pkey",
                "event_sequence_counters",
                ["aggregate_type", "aggregate_id"],
            )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    _ensure_event_outbox(inspector, bind.dialect.name)
    _ensure_event_sequence_counters(inspector, bind.dialect.name)


def downgrade() -> None:
    # Intentionally a no-op: avoid destructive drops for core outbox tables.
    pass
