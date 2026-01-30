"""add pgvector hnsw indexes

Revision ID: a7c9e1f2b3d4
Revises: f5d0a1b2c3d4
Create Date: 2025-01-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a7c9e1f2b3d4"
down_revision = "f5d0a1b2c3d4"
branch_labels = None
depends_on = None


def _pgvector_installed(conn) -> bool:
    result = conn.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()
    if not _pgvector_installed(conn):
        return

    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_nodes_embedding_hnsw
            ON knowledge_nodes USING hnsw (embedding vector_cosine_ops)
            WHERE embedding IS NOT NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_document_chunks_embedding_hnsw
            ON document_chunks USING hnsw (embedding vector_cosine_ops)
            WHERE embedding IS NOT NULL
            """
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_document_chunks_embedding_hnsw")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_knowledge_nodes_embedding_hnsw")
