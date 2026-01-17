"""add_global_spark_count

Revision ID: add_global_spark_count
Revises: effadcff68cd
Create Date: 2026-01-03 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.utils.migration_helpers import column_exists, get_inspector, table_exists

revision = 'add_global_spark_count'
down_revision = 'effadcff68cd'

def upgrade() -> None:
    inspector = get_inspector()
    if table_exists(inspector, "knowledge_nodes") and not column_exists(inspector, "knowledge_nodes", "global_spark_count"):
        op.add_column('knowledge_nodes', sa.Column('global_spark_count', sa.Integer(), server_default='0', nullable=False))

def downgrade() -> None:
    inspector = get_inspector()
    if table_exists(inspector, "knowledge_nodes") and column_exists(inspector, "knowledge_nodes", "global_spark_count"):
        op.drop_column('knowledge_nodes', 'global_spark_count')
