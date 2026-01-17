"""Add shared resource links for curiosity capsules and prism patterns.

Revision ID: p3_add_shared_resource_capsule_prism
Revises: p2_add_user_tool_history
Create Date: 2025-01-20 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from app.models.base import GUID
from app.utils.migration_helpers import (
    column_exists,
    foreign_key_exists,
    get_inspector,
    index_exists,
    table_exists,
)

revision = 'p3_shared_rsrc_prism'
down_revision = 'p2_add_user_tool_history'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = get_inspector()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE messagetype ADD VALUE IF NOT EXISTS 'CAPSULE_SHARE'")
        op.execute("ALTER TYPE messagetype ADD VALUE IF NOT EXISTS 'PRISM_SHARE'")

    if table_exists(inspector, "shared_resources"):
        with op.batch_alter_table('shared_resources') as batch_op:
            if not column_exists(inspector, "shared_resources", "curiosity_capsule_id"):
                batch_op.add_column(sa.Column('curiosity_capsule_id', GUID(), nullable=True))
            if not column_exists(inspector, "shared_resources", "behavior_pattern_id"):
                batch_op.add_column(sa.Column('behavior_pattern_id', GUID(), nullable=True))
            if not index_exists(inspector, "shared_resources", "idx_share_resource_capsule"):
                batch_op.create_index('idx_share_resource_capsule', ['curiosity_capsule_id'])
            if not index_exists(inspector, "shared_resources", "idx_share_resource_pattern"):
                batch_op.create_index('idx_share_resource_pattern', ['behavior_pattern_id'])
            if not foreign_key_exists(inspector, "shared_resources", "shared_resources_curiosity_capsule_id_fkey"):
                batch_op.create_foreign_key(
                    'shared_resources_curiosity_capsule_id_fkey',
                    'curiosity_capsules',
                    ['curiosity_capsule_id'],
                    ['id']
                )
            if not foreign_key_exists(inspector, "shared_resources", "shared_resources_behavior_pattern_id_fkey"):
                batch_op.create_foreign_key(
                    'shared_resources_behavior_pattern_id_fkey',
                    'behavior_patterns',
                    ['behavior_pattern_id'],
                    ['id']
                )


def downgrade():
    inspector = get_inspector()
    if table_exists(inspector, "shared_resources"):
        with op.batch_alter_table('shared_resources') as batch_op:
            if foreign_key_exists(inspector, "shared_resources", "shared_resources_behavior_pattern_id_fkey"):
                batch_op.drop_constraint('shared_resources_behavior_pattern_id_fkey', type_='foreignkey')
            if foreign_key_exists(inspector, "shared_resources", "shared_resources_curiosity_capsule_id_fkey"):
                batch_op.drop_constraint('shared_resources_curiosity_capsule_id_fkey', type_='foreignkey')
            if index_exists(inspector, "shared_resources", "idx_share_resource_pattern"):
                batch_op.drop_index('idx_share_resource_pattern')
            if index_exists(inspector, "shared_resources", "idx_share_resource_capsule"):
                batch_op.drop_index('idx_share_resource_capsule')
            if column_exists(inspector, "shared_resources", "behavior_pattern_id"):
                batch_op.drop_column('behavior_pattern_id')
            if column_exists(inspector, "shared_resources", "curiosity_capsule_id"):
                batch_op.drop_column('curiosity_capsule_id')

    # NOTE: Postgres enum value removal is not supported without recreating the type.
