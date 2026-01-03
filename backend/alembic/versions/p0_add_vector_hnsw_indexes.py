"""P0: Add HNSW vector indexes for knowledge_nodes and cognitive_fragments

This migration addresses critical performance issues identified in the 2025 Tech Audit:
- knowledge_nodes.embedding: HNSW index for fast vector search
- cognitive_fragments.embedding: HNSW index for fragment similarity
- chat_messages: Composite index for session history pagination

Revision ID: p0_vector_indexes
Revises: cqrs_001
Create Date: 2025-12-28

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'p0_vector_indexes'
down_revision = 'cqrs_001'
branch_labels = None
depends_on = None


def upgrade():
    # P0: CRITICAL - Add HNSW index for knowledge_nodes embedding
    # This prevents O(N) full table scans during vector similarity search
    # Parameters: m=16 (connections per layer), ef_construction=64 (build quality)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_embedding_hnsw
        ON public.knowledge_nodes
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)

    # P0: Add HNSW index for cognitive_fragments embedding (same pattern)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cognitive_fragments_embedding_hnsw
        ON public.cognitive_fragments
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)

    # P2: Composite index for chat_messages history pagination
    # Optimizes: SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at DESC
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
        ON public.chat_messages (session_id, created_at DESC);
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_knowledge_nodes_embedding_hnsw;")
    op.execute("DROP INDEX IF EXISTS idx_cognitive_fragments_embedding_hnsw;")
    op.execute("DROP INDEX IF EXISTS idx_chat_messages_session_created;")
