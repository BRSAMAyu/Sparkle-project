"""c26_add_knowledge_node_exam_attrs

Revision ID: c26_20260502
Revises: b698b0802ef1
Create Date: 2026-05-02 17:45:00

P2-24: Add exam_weight, difficulty, trainability, mistakes to knowledge_nodes
for persistent retrieval ranking (KG-001)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT exam_weight, difficulty, trainability, mistakes FROM knowledge_nodes LIMIT 1;"
#   backfill_plan: "n/a"
#   owner: "architect"
#   ticket: "P2-24"

revision: str = 'c26_20260502'
down_revision: Union[str, None] = 'b698b0802ef1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("knowledge_nodes", sa.Column("exam_weight", sa.Float(), nullable=False, server_default="0.0"))
    op.add_column("knowledge_nodes", sa.Column("difficulty", sa.Float(), nullable=False, server_default="0.5"))
    op.add_column("knowledge_nodes", sa.Column("trainability", sa.Float(), nullable=False, server_default="0.5"))
    op.add_column("knowledge_nodes", sa.Column("mistakes", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("knowledge_nodes", "mistakes")
    op.drop_column("knowledge_nodes", "trainability")
    op.drop_column("knowledge_nodes", "difficulty")
    op.drop_column("knowledge_nodes", "exam_weight")
