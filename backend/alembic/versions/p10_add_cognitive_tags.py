"""add cognitive_tags and ai_analysis_summary to error_records

Revision ID: p10_add_cognitive_tags
Revises: p9_add_group_files
Create Date: 2026-01-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'p10_add_cognitive_tags'
down_revision = 'p9_add_group_files'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('error_records', sa.Column('cognitive_tags', postgresql.ARRAY(sa.String()), server_default='{}', nullable=True))
    op.add_column('error_records', sa.Column('ai_analysis_summary', sa.Text(), nullable=True))
    op.create_index('idx_error_records_cognitive_tags', 'error_records', ['cognitive_tags'], unique=False, postgresql_using='gin')

def downgrade() -> None:
    op.drop_index('idx_error_records_cognitive_tags', table_name='error_records')
    op.drop_column('error_records', 'ai_analysis_summary')
    op.drop_column('error_records', 'cognitive_tags')
