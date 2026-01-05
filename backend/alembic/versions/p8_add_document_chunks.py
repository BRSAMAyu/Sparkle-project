"""add document_chunks table

Revision ID: p8_add_document_chunks
Revises: p7_add_stored_files
Create Date: 2026-01-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = 'p8_add_document_chunks'
down_revision = 'p7_add_stored_files'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('section_title', sa.String(length=255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(dim=1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['stored_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_document_chunks_file_id', 'document_chunks', ['file_id'], unique=False)
    op.create_index('idx_document_chunks_user_id', 'document_chunks', ['user_id'], unique=False)
    op.create_index('idx_document_chunks_chunk_index', 'document_chunks', ['file_id', 'chunk_index'], unique=True)
    op.create_index('idx_document_chunks_deleted_at', 'document_chunks', ['deleted_at'], unique=False)


def downgrade():
    op.drop_index('idx_document_chunks_deleted_at', table_name='document_chunks')
    op.drop_index('idx_document_chunks_chunk_index', table_name='document_chunks')
    op.drop_index('idx_document_chunks_user_id', table_name='document_chunks')
    op.drop_index('idx_document_chunks_file_id', table_name='document_chunks')
    op.drop_table('document_chunks')
