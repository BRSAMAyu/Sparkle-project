"""add document_retrieval_feedback table and document_quality_score column

Revision ID: df1a2b3c4d5e
Revises: z1a2b3c4d5e6
Create Date: 2026-04-26 00:00:00
"""

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID

# revision identifiers, used by Alembic.
revision = "df1a2b3c4d5e"
down_revision = "z1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add document_quality_score to stored_files
    op.add_column(
        "stored_files",
        sa.Column("document_quality_score", sa.Float(), nullable=False, server_default="0.0"),
    )

    # 2. Create document_retrieval_feedback table
    op.create_table(
        "document_retrieval_feedback",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_id", GUID(), sa.ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", GUID(), sa.ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("query_intent_type", sa.String(64), nullable=True),
        sa.Column("feedback_score", sa.Integer(), nullable=False),
        sa.Column("feedback_source", sa.String(32), nullable=False),
        sa.Column("conversation_id", sa.String(128), nullable=True),
        sa.Column("context", sa.JSON(), nullable=True),
    )
    op.create_index("ix_document_retrieval_feedback_user_id", "document_retrieval_feedback", ["user_id"])
    op.create_index("ix_document_retrieval_feedback_file_id", "document_retrieval_feedback", ["file_id"])
    op.create_index("ix_document_retrieval_feedback_created_at", "document_retrieval_feedback", ["created_at"])
    op.create_index("ix_document_retrieval_feedback_deleted_at", "document_retrieval_feedback", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_document_retrieval_feedback_deleted_at", table_name="document_retrieval_feedback")
    op.drop_index("ix_document_retrieval_feedback_created_at", table_name="document_retrieval_feedback")
    op.drop_index("ix_document_retrieval_feedback_file_id", table_name="document_retrieval_feedback")
    op.drop_index("ix_document_retrieval_feedback_user_id", table_name="document_retrieval_feedback")
    op.drop_table("document_retrieval_feedback")
    op.drop_column("stored_files", "document_quality_score")
