"""add cognitive fragment embedding hnsw index

Revision ID: e8f1a2b3c4d5
Revises: c4d5e6f7a8b9
Create Date: 2026-03-26 23:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "e8f1a2b3c4d5"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def _pgvector_installed(conn) -> bool:
    result = conn.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql" or not _pgvector_installed(conn):
        return

    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cognitive_fragments_embedding_hnsw
            ON cognitive_fragments USING hnsw (embedding vector_cosine_ops)
            WHERE embedding IS NOT NULL
            """
        )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_cognitive_fragments_embedding_hnsw")
