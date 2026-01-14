"""add expansion feedback loop tables

Revision ID: p11_add_expansion_feedback
Revises: p10_persona_v31
Create Date: 2026-01-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.models.base import GUID
from app.utils.migration_helpers import column_exists, get_inspector, index_exists, table_exists

# revision identifiers, used by Alembic.
revision = 'p11_add_expansion_feedback'
down_revision = '397296dbb0e5'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = get_inspector()
    json_type = postgresql.JSONB() if bind.dialect.name == "postgresql" else sa.JSON()

    if table_exists(inspector, "node_expansion_queue"):
        if not column_exists(inspector, "node_expansion_queue", "prompt_version"):
            op.add_column('node_expansion_queue', sa.Column('prompt_version', sa.String(length=50), nullable=True))
        if not column_exists(inspector, "node_expansion_queue", "model_name"):
            op.add_column('node_expansion_queue', sa.Column('model_name', sa.String(length=50), nullable=True))

    if not table_exists(inspector, "expansion_feedback"):
        op.create_table(
            'expansion_feedback',
            sa.Column('id', GUID(), nullable=False),
            sa.Column('expansion_queue_id', GUID(), nullable=True),
            sa.Column('trigger_node_id', GUID(), nullable=False),
            sa.Column('user_id', GUID(), nullable=False),
            sa.Column('rating', sa.Integer(), nullable=True),
            sa.Column('implicit_score', sa.Float(), nullable=True),
            sa.Column('feedback_type', sa.String(length=20), nullable=True),
            sa.Column('prompt_version', sa.String(length=50), nullable=True),
            sa.Column('model_name', sa.String(length=50), nullable=True),
            sa.Column('meta_data', json_type, nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['expansion_queue_id'], ['node_expansion_queue.id']),
            sa.ForeignKeyConstraint(['trigger_node_id'], ['knowledge_nodes.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists(inspector, "expansion_feedback", "idx_expansion_feedback_queue"):
        op.create_index('idx_expansion_feedback_queue', 'expansion_feedback', ['expansion_queue_id'], unique=False)
    if not index_exists(inspector, "expansion_feedback", "idx_expansion_feedback_node"):
        op.create_index('idx_expansion_feedback_node', 'expansion_feedback', ['trigger_node_id'], unique=False)
    if not index_exists(inspector, "expansion_feedback", "idx_expansion_feedback_user"):
        op.create_index('idx_expansion_feedback_user', 'expansion_feedback', ['user_id'], unique=False)


def downgrade():
    inspector = get_inspector()
    if table_exists(inspector, "expansion_feedback"):
        if index_exists(inspector, "expansion_feedback", "idx_expansion_feedback_user"):
            op.drop_index('idx_expansion_feedback_user', table_name='expansion_feedback')
        if index_exists(inspector, "expansion_feedback", "idx_expansion_feedback_node"):
            op.drop_index('idx_expansion_feedback_node', table_name='expansion_feedback')
        if index_exists(inspector, "expansion_feedback", "idx_expansion_feedback_queue"):
            op.drop_index('idx_expansion_feedback_queue', table_name='expansion_feedback')
        op.drop_table('expansion_feedback')

    if table_exists(inspector, "node_expansion_queue"):
        if column_exists(inspector, "node_expansion_queue", "model_name"):
            op.drop_column('node_expansion_queue', 'model_name')
        if column_exists(inspector, "node_expansion_queue", "prompt_version"):
            op.drop_column('node_expansion_queue', 'prompt_version')
