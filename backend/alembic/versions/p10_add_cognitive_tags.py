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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("error_records")}

    if "cognitive_tags" not in columns:
        op.add_column('error_records', sa.Column('cognitive_tags', postgresql.ARRAY(sa.String()), server_default='{}', nullable=True))
    if "ai_analysis_summary" not in columns:
        op.add_column('error_records', sa.Column('ai_analysis_summary', sa.Text(), nullable=True))
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_error_records_cognitive_tags "
        "ON error_records USING gin (cognitive_tags)"
    )

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_error_records_cognitive_tags")
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("error_records")}
    if "ai_analysis_summary" in columns:
        op.drop_column('error_records', 'ai_analysis_summary')
    if "cognitive_tags" in columns:
        op.drop_column('error_records', 'cognitive_tags')
