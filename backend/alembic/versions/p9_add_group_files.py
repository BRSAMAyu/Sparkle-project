"""add group_files table and file share message type

Revision ID: p9_add_group_files
Revises: p8_add_document_chunks
Create Date: 2026-01-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.models.base import GUID
from app.utils.migration_helpers import get_inspector, index_exists, table_exists

# revision identifiers, used by Alembic.
revision = 'p9_add_group_files'
down_revision = 'p8_add_document_chunks'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = get_inspector()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE messagetype ADD VALUE IF NOT EXISTS 'FILE_SHARE'")

    if not table_exists(inspector, "group_files"):
        op.create_table(
            'group_files',
            sa.Column('id', GUID(), nullable=False),
            sa.Column('group_id', GUID(), nullable=False),
            sa.Column('file_id', GUID(), nullable=False),
            sa.Column('shared_by_id', GUID(), nullable=False),
            sa.Column('category', sa.String(length=64), nullable=True),
            sa.Column('tags', sa.JSON(), nullable=False),
            sa.Column('view_role', sa.Enum('OWNER', 'ADMIN', 'MEMBER', name='grouprole'), nullable=False),
            sa.Column('download_role', sa.Enum('OWNER', 'ADMIN', 'MEMBER', name='grouprole'), nullable=False),
            sa.Column('manage_role', sa.Enum('OWNER', 'ADMIN', 'MEMBER', name='grouprole'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['file_id'], ['stored_files.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['shared_by_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('group_id', 'file_id', name='uq_group_files_group_file'),
        )
    if not index_exists(inspector, "group_files", "idx_group_files_group"):
        op.create_index('idx_group_files_group', 'group_files', ['group_id'], unique=False)
    if not index_exists(inspector, "group_files", "idx_group_files_file"):
        op.create_index('idx_group_files_file', 'group_files', ['file_id'], unique=False)
    if not index_exists(inspector, "group_files", "idx_group_files_shared_by"):
        op.create_index('idx_group_files_shared_by', 'group_files', ['shared_by_id'], unique=False)
    if not index_exists(inspector, "group_files", "idx_group_files_category"):
        op.create_index('idx_group_files_category', 'group_files', ['category'], unique=False)
    if not index_exists(inspector, "group_files", "idx_group_files_deleted_at"):
        op.create_index('idx_group_files_deleted_at', 'group_files', ['deleted_at'], unique=False)


def downgrade():
    inspector = get_inspector()
    if table_exists(inspector, "group_files"):
        if index_exists(inspector, "group_files", "idx_group_files_deleted_at"):
            op.drop_index('idx_group_files_deleted_at', table_name='group_files')
        if index_exists(inspector, "group_files", "idx_group_files_category"):
            op.drop_index('idx_group_files_category', table_name='group_files')
        if index_exists(inspector, "group_files", "idx_group_files_shared_by"):
            op.drop_index('idx_group_files_shared_by', table_name='group_files')
        if index_exists(inspector, "group_files", "idx_group_files_file"):
            op.drop_index('idx_group_files_file', table_name='group_files')
        if index_exists(inspector, "group_files", "idx_group_files_group"):
            op.drop_index('idx_group_files_group', table_name='group_files')
        op.drop_table('group_files')
    # NOTE: Postgres enum value removal is not supported without recreating the type.
