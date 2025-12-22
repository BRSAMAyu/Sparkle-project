"""add_cognitive_prism_tables

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2025-12-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
import app


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create cognitive prism tables"""
    
    # Create cognitive_fragments table
    op.create_table('cognitive_fragments',
        sa.Column('user_id', app.models.base.GUID(), nullable=False),
        sa.Column('task_id', app.models.base.GUID(), nullable=True),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sentiment', sa.String(length=20), nullable=True),
        sa.Column('tags', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('id', app.models.base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cognitive_fragments_deleted_at'), 'cognitive_fragments', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_cognitive_fragments_user_id'), 'cognitive_fragments', ['user_id'], unique=False)

    # Create behavior_patterns table
    op.create_table('behavior_patterns',
        sa.Column('user_id', app.models.base.GUID(), nullable=False),
        sa.Column('pattern_name', sa.String(length=100), nullable=False),
        sa.Column('pattern_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('solution_text', sa.Text(), nullable=True),
        sa.Column('evidence_ids', sa.ARRAY(app.models.base.GUID()), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True),
        sa.Column('id', app.models.base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_behavior_patterns_deleted_at'), 'behavior_patterns', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_behavior_patterns_user_id'), 'behavior_patterns', ['user_id'], unique=False)


def downgrade() -> None:
    """Drop cognitive prism tables"""
    op.drop_index(op.f('ix_behavior_patterns_user_id'), table_name='behavior_patterns')
    op.drop_index(op.f('ix_behavior_patterns_deleted_at'), table_name='behavior_patterns')
    op.drop_table('behavior_patterns')
    op.drop_index(op.f('ix_cognitive_fragments_user_id'), table_name='cognitive_fragments')
    op.drop_index(op.f('ix_cognitive_fragments_deleted_at'), table_name='cognitive_fragments')
    op.drop_table('cognitive_fragments')
