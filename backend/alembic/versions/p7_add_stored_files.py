"""add stored_files table

Revision ID: p7_add_stored_files
Revises: p6_add_revision_to_mastery
Create Date: 2026-01-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.utils.migration_helpers import get_inspector, index_exists, table_exists

# revision identifiers, used by Alembic.
revision = 'p7_add_stored_files'
down_revision = 'p6_add_revision_to_mastery'
branch_labels = None
depends_on = None


def upgrade():
    inspector = get_inspector()
    if not table_exists(inspector, "stored_files"):
        op.create_table(
            'stored_files',
            sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('file_name', sa.String(length=255), nullable=False),
            sa.Column('mime_type', sa.String(length=150), nullable=False),
            sa.Column('file_size', sa.BigInteger(), nullable=False),
            sa.Column('bucket', sa.String(length=128), nullable=False),
            sa.Column('object_key', sa.String(length=512), nullable=False),
            sa.Column('status', sa.String(length=32), server_default='uploading', nullable=False),
            sa.Column('visibility', sa.String(length=32), server_default='private', nullable=False),
            sa.Column('error_message', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
    if not index_exists(inspector, "stored_files", "idx_stored_files_user_id"):
        op.create_index('idx_stored_files_user_id', 'stored_files', ['user_id'], unique=False)
    if not index_exists(inspector, "stored_files", "idx_stored_files_status"):
        op.create_index('idx_stored_files_status', 'stored_files', ['status'], unique=False)
    if not index_exists(inspector, "stored_files", "idx_stored_files_created_at"):
        op.create_index('idx_stored_files_created_at', 'stored_files', ['created_at'], unique=False)
    if not index_exists(inspector, "stored_files", "idx_stored_files_object_key"):
        op.create_index('idx_stored_files_object_key', 'stored_files', ['object_key'], unique=True)


def downgrade():
    inspector = get_inspector()
    if table_exists(inspector, "stored_files"):
        if index_exists(inspector, "stored_files", "idx_stored_files_object_key"):
            op.drop_index('idx_stored_files_object_key', table_name='stored_files')
        if index_exists(inspector, "stored_files", "idx_stored_files_created_at"):
            op.drop_index('idx_stored_files_created_at', table_name='stored_files')
        if index_exists(inspector, "stored_files", "idx_stored_files_status"):
            op.drop_index('idx_stored_files_status', table_name='stored_files')
        if index_exists(inspector, "stored_files", "idx_stored_files_user_id"):
            op.drop_index('idx_stored_files_user_id', table_name='stored_files')
        op.drop_table('stored_files')
