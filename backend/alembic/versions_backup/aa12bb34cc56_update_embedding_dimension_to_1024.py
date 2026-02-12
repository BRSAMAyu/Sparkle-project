"""update embedding dimension to 1024

Revision ID: aa12bb34cc56
Revises: f8c3d4e5f6a7
Create Date: 2026-02-01 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "aa12bb34cc56"
down_revision = "f8c3d4e5f6a7"
branch_labels = None
depends_on = None


def _alter_embedding_dim(table: str, column: str, dim: int) -> None:
    op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE vector({dim});")


def _null_embeddings(table: str, column: str) -> None:
    op.execute(f"UPDATE {table} SET {column} = NULL;")


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    for table in ("knowledge_nodes", "document_chunks", "episodic_memories", "cognitive_fragments"):
        _alter_embedding_dim(table, "embedding", 1024)
        _null_embeddings(table, "embedding")


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    for table in ("knowledge_nodes", "document_chunks", "episodic_memories", "cognitive_fragments"):
        _alter_embedding_dim(table, "embedding", 1536)
        _null_embeddings(table, "embedding")
