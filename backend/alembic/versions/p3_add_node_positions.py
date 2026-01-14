"""Add position columns to knowledge_nodes for viewport culling.

Revision ID: p3_add_node_positions
Revises: p1_1_jsonb_migration
Create Date: 2026-01-02 15:00:00

"""
from alembic import op
import sqlalchemy as sa
from app.utils.migration_helpers import column_exists, get_inspector, index_exists, table_exists

# revision identifiers, used by Alembic.
revision = 'p3_add_node_positions'
down_revision = 'p1_1_jsonb_migration'
branch_labels = None
depends_on = None


def upgrade():
    inspector = get_inspector()
    if table_exists(inspector, "knowledge_nodes"):
        if not column_exists(inspector, "knowledge_nodes", "position_x"):
            op.add_column('knowledge_nodes', sa.Column('position_x', sa.Float(), nullable=True))
        if not column_exists(inspector, "knowledge_nodes", "position_y"):
            op.add_column('knowledge_nodes', sa.Column('position_y', sa.Float(), nullable=True))
        if not index_exists(inspector, "knowledge_nodes", "idx_nodes_position"):
            # Add index for bounding box queries
            op.create_index('idx_nodes_position', 'knowledge_nodes', ['position_x', 'position_y'])


def downgrade():
    inspector = get_inspector()
    if table_exists(inspector, "knowledge_nodes"):
        if index_exists(inspector, "knowledge_nodes", "idx_nodes_position"):
            op.drop_index('idx_nodes_position', table_name='knowledge_nodes')
        if column_exists(inspector, "knowledge_nodes", "position_y"):
            op.drop_column('knowledge_nodes', 'position_y')
        if column_exists(inspector, "knowledge_nodes", "position_x"):
            op.drop_column('knowledge_nodes', 'position_x')
