"""Add position columns to knowledge_nodes for viewport culling.

Revision ID: p3_add_node_positions
Revises: p1_1_jsonb_migration
Create Date: 2026-01-02 15:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'p3_add_node_positions'
down_revision = 'p1_1_jsonb_migration'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('knowledge_nodes', sa.Column('position_x', sa.Float(), nullable=True))
    op.add_column('knowledge_nodes', sa.Column('position_y', sa.Float(), nullable=True))
    
    # Add index for bounding box queries
    op.create_index('idx_nodes_position', 'knowledge_nodes', ['position_x', 'position_y'])


def downgrade():
    op.drop_index('idx_nodes_position', table_name='knowledge_nodes')
    op.drop_column('knowledge_nodes', 'position_y')
    op.drop_column('knowledge_nodes', 'position_x')
