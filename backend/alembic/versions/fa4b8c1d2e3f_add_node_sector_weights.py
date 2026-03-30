"""add node sector weights

Revision ID: fa4b8c1d2e3f
Revises: a9c4e7f1b2d3, c8e4f2a3b1d6, d1f2a3b4c5e6, e8f1a2b3c4d5, f3c1d9a7b6e5, oc003c4d5e6f7, z1a2b3c4d5e6
Create Date: 2026-03-30 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "fa4b8c1d2e3f"
down_revision = (
    "a9c4e7f1b2d3",
    "c8e4f2a3b1d6",
    "d1f2a3b4c5e6",
    "e8f1a2b3c4d5",
    "f3c1d9a7b6e5",
    "oc003c4d5e6f7",
    "z1a2b3c4d5e6",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_type = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()

    op.add_column("knowledge_nodes", sa.Column("sector_weights", json_type, nullable=True))
    op.add_column(
        "knowledge_nodes",
        sa.Column(
            "dominant_sector_code",
            sa.String(length=20),
            nullable=False,
            server_default="VOID",
        ),
    )
    op.add_column(
        "knowledge_nodes",
        sa.Column(
            "sector_classification_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("knowledge_nodes", sa.Column("sector_classification_model", sa.String(length=100), nullable=True))
    op.add_column("knowledge_nodes", sa.Column("sector_classified_at", sa.DateTime(), nullable=True))

    op.create_index(
        "ix_knowledge_nodes_dominant_sector_code",
        "knowledge_nodes",
        ["dominant_sector_code"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_nodes_sector_classification_status",
        "knowledge_nodes",
        ["sector_classification_status"],
        unique=False,
    )

    if is_postgres:
        op.execute(
            """
            UPDATE knowledge_nodes AS kn
            SET
              dominant_sector_code = COALESCE(s.sector_code, 'VOID'),
              sector_weights = CASE
                WHEN s.sector_code IS NOT NULL THEN jsonb_build_object(s.sector_code, 100)
                ELSE jsonb_build_object('VOID', 100)
              END,
              sector_classification_status = CASE
                WHEN s.sector_code IS NOT NULL THEN 'completed'
                ELSE 'pending'
              END,
              sector_classified_at = CASE
                WHEN s.sector_code IS NOT NULL THEN NOW()
                ELSE NULL
              END
            FROM subjects AS s
            WHERE kn.subject_id = s.id
            """
        )
        op.execute(
            """
            UPDATE knowledge_nodes
            SET
              dominant_sector_code = 'VOID',
              sector_weights = jsonb_build_object('VOID', 100),
              sector_classification_status = COALESCE(sector_classification_status, 'pending')
            WHERE sector_weights IS NULL
            """
        )
    else:
        op.execute(
            """
            UPDATE knowledge_nodes
            SET dominant_sector_code = 'VOID',
                sector_classification_status = 'pending'
            WHERE dominant_sector_code IS NULL
            """
        )


def downgrade() -> None:
    op.drop_index("ix_knowledge_nodes_sector_classification_status", table_name="knowledge_nodes")
    op.drop_index("ix_knowledge_nodes_dominant_sector_code", table_name="knowledge_nodes")
    op.drop_column("knowledge_nodes", "sector_classified_at")
    op.drop_column("knowledge_nodes", "sector_classification_model")
    op.drop_column("knowledge_nodes", "sector_classification_status")
    op.drop_column("knowledge_nodes", "dominant_sector_code")
    op.drop_column("knowledge_nodes", "sector_weights")
