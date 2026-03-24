"""add_knowledge_node_id_to_subtasks

Revision ID: 43ff976a8b29
Revises: 0896bb7f89b3
Create Date: 2026-03-15 13:54:53.998163

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible|forward_only|destructive
#   rollback_plan: "alembic downgrade -1" | "forward_fix_only"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "team-name"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = '43ff976a8b29'
down_revision: Union[str, None] = '0896bb7f89b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('subtasks', sa.Column('knowledge_node_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_subtasks_knowledge_node_id', 'subtasks', 'knowledge_nodes', ['knowledge_node_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_subtasks_knowledge_node_id'), 'subtasks', ['knowledge_node_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_subtasks_knowledge_node_id'), table_name='subtasks')
    op.drop_constraint('fk_subtasks_knowledge_node_id', 'subtasks', type_='foreignkey')
    op.drop_column('subtasks', 'knowledge_node_id')
