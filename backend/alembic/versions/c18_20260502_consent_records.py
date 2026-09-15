"""create durable research consent records

Revision ID: c18_20260502
Revises: c12_20260502
Create Date: 2026-05-02 14:20:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c18_20260502"
down_revision: str | None = "c12_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.CHAR(length=36)


def upgrade() -> None:
    json_type = _json_type()
    uuid_type = _uuid_type()

    op.create_table(
        "research_consent_records",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("protocol_id", sa.String(length=64), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("scope", json_type, nullable=False),
        sa.Column("evidence", json_type, nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("grant_reason", sa.Text(), nullable=True),
        sa.Column("grant_initiator", sa.String(length=16), nullable=False),
        sa.Column("grant_ip_hash", sa.String(length=64), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("revoke_initiator", sa.String(length=16), nullable=True),
        sa.Column("revoke_ip_hash", sa.String(length=64), nullable=True),
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_consent_records_user_id", "research_consent_records", ["user_id"], unique=False)
    op.create_index(
        "ix_research_consent_records_protocol_id",
        "research_consent_records",
        ["protocol_id"],
        unique=False,
    )
    op.create_index(
        "ix_research_consent_records_granted_at",
        "research_consent_records",
        ["granted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_consent_records_revoked_at",
        "research_consent_records",
        ["revoked_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_consent_records_deleted_at",
        "research_consent_records",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_consent_user_protocol",
        "research_consent_records",
        ["user_id", "protocol_id"],
        unique=False,
    )
    op.create_index(
        "ix_research_consent_user_active",
        "research_consent_records",
        ["user_id", "protocol_id", "revoked_at"],
        unique=False,
    )

    dialect_name = op.get_bind().dialect.name
    where = sa.text("revoked_at IS NULL")
    if dialect_name == "postgresql":
        op.create_index(
            "uq_research_consent_active_protocol",
            "research_consent_records",
            ["user_id", "protocol_id"],
            unique=True,
            postgresql_where=where,
        )
    elif dialect_name == "sqlite":
        op.create_index(
            "uq_research_consent_active_protocol",
            "research_consent_records",
            ["user_id", "protocol_id"],
            unique=True,
            sqlite_where=where,
        )
    else:
        op.create_index(
            "uq_research_consent_active_protocol",
            "research_consent_records",
            ["user_id", "protocol_id", "revoked_at"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("uq_research_consent_active_protocol", table_name="research_consent_records")
    op.drop_index("ix_research_consent_user_active", table_name="research_consent_records")
    op.drop_index("ix_research_consent_user_protocol", table_name="research_consent_records")
    op.drop_index("ix_research_consent_records_deleted_at", table_name="research_consent_records")
    op.drop_index("ix_research_consent_records_revoked_at", table_name="research_consent_records")
    op.drop_index("ix_research_consent_records_granted_at", table_name="research_consent_records")
    op.drop_index("ix_research_consent_records_protocol_id", table_name="research_consent_records")
    op.drop_index("ix_research_consent_records_user_id", table_name="research_consent_records")
    op.drop_table("research_consent_records")
