"""Migrate keywords and tags to JSONB and add GIN index.

Revision ID: p1_1_jsonb_migration
Revises: p0_vector_indexes
Create Date: 2026-01-02 14:00:00

"""
from alembic import op
import sqlalchemy as sa
from app.utils.migration_helpers import column_exists, get_inspector, table_exists
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'p1_1_jsonb_migration'
down_revision = 'p5_community_advanced_features'
branch_labels = None
depends_on = None


def upgrade():
    inspector = get_inspector()
    # 1. Migrate knowledge_nodes.keywords to JSONB
    if table_exists(inspector, "knowledge_nodes") and column_exists(inspector, "knowledge_nodes", "keywords"):
        op.execute("ALTER TABLE knowledge_nodes ALTER COLUMN keywords TYPE JSONB USING keywords::jsonb")
        op.execute("CREATE INDEX IF NOT EXISTS idx_nodes_keywords_gin ON knowledge_nodes USING GIN (keywords)")
    
    # 2. Migrate tasks.tags to JSONB
    if table_exists(inspector, "tasks") and column_exists(inspector, "tasks", "tags"):
        op.execute("ALTER TABLE tasks ALTER COLUMN tags TYPE JSONB USING tags::jsonb")
        op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_tags_gin ON tasks USING GIN (tags)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_tasks_tags_gin")
    op.execute("DROP INDEX IF EXISTS idx_nodes_keywords_gin")
    
    inspector = get_inspector()
    if table_exists(inspector, "tasks") and column_exists(inspector, "tasks", "tags"):
        op.execute("ALTER TABLE tasks ALTER COLUMN tags TYPE JSON USING tags::json")
    if table_exists(inspector, "knowledge_nodes") and column_exists(inspector, "knowledge_nodes", "keywords"):
        op.execute("ALTER TABLE knowledge_nodes ALTER COLUMN keywords TYPE JSON USING keywords::json")
