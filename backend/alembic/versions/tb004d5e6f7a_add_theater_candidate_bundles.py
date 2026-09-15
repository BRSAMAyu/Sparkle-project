"""add theater candidate bundles

Revision ID: tb004d5e6f7a
Revises: fa4b8c1d2e3f
Create Date: 2026-03-30 00:00:01.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "tb004d5e6f7a"
down_revision = "fa4b8c1d2e3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_type = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()
    guid_type = postgresql.UUID(as_uuid=True) if is_postgres else sa.String(length=36)

    op.create_table(
        "theater_candidate_bundles",
        sa.Column("id", guid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", guid_type, nullable=False),
        sa.Column("prediction_id", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("target_name", sa.String(length=255), nullable=False),
        sa.Column("target_resolution_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending_review"),
        sa.Column("nodes_payload", json_type, nullable=False),
        sa.Column("edges_payload", json_type, nullable=False),
        sa.Column("semantic_matches", json_type, nullable=False),
        sa.Column("source_metadata", json_type, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prediction_id", name="uq_theater_candidate_bundles_prediction_id"),
    )
    op.create_index(
        "ix_theater_candidate_bundles_user_id",
        "theater_candidate_bundles",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_theater_candidate_bundles_prediction_id",
        "theater_candidate_bundles",
        ["prediction_id"],
        unique=False,
    )
    op.create_index(
        "ix_theater_candidate_bundles_status",
        "theater_candidate_bundles",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_theater_candidate_bundles_target_resolution_mode",
        "theater_candidate_bundles",
        ["target_resolution_mode"],
        unique=False,
    )
    op.create_index(
        "ix_theater_candidate_bundles_deleted_at",
        "theater_candidate_bundles",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_theater_candidate_bundles_deleted_at", table_name="theater_candidate_bundles")
    op.drop_index("ix_theater_candidate_bundles_target_resolution_mode", table_name="theater_candidate_bundles")
    op.drop_index("ix_theater_candidate_bundles_status", table_name="theater_candidate_bundles")
    op.drop_index("ix_theater_candidate_bundles_prediction_id", table_name="theater_candidate_bundles")
    op.drop_index("ix_theater_candidate_bundles_user_id", table_name="theater_candidate_bundles")
    op.drop_table("theater_candidate_bundles")
