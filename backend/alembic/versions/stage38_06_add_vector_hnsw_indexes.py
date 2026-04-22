"""stage38 add vector hnsw indexes

Revision ID: stage38_06_add_vector_hnsw_indexes
Revises: stage38_04_add_simulation_and_report_snapshots
Create Date: 2026-04-23 02:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "stage38_06_add_vector_hnsw_indexes"
down_revision = "stage38_04_add_simulation_and_report_snapshots"
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
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_document_chunks_embedding_hnsw
            ON document_chunks USING hnsw (embedding vector_cosine_ops)
            WHERE embedding IS NOT NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_nodes_embedding_hnsw
            ON knowledge_nodes USING hnsw (embedding vector_cosine_ops)
            WHERE embedding IS NOT NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_episodic_memories_embedding_hnsw
            ON episodic_memories USING hnsw (embedding vector_cosine_ops)
            WHERE embedding IS NOT NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scenes_centroid_embedding_hnsw
            ON scenes USING hnsw (centroid_embedding vector_cosine_ops)
            WHERE centroid_embedding IS NOT NULL
            """
        )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_scenes_centroid_embedding_hnsw")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_episodic_memories_embedding_hnsw")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_knowledge_nodes_embedding_hnsw")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_document_chunks_embedding_hnsw")
