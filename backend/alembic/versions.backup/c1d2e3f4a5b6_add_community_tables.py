"""add_community_tables

Revision ID: c1d2e3f4a5b6
Revises: 54e1f05154ad
Create Date: 2025-12-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = '54e1f05154ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建社群功能相关表"""

    # 创建枚举类型
    friendship_status = sa.Enum('pending', 'accepted', 'blocked', name='friendshipstatus')
    group_type = sa.Enum('squad', 'sprint', name='grouptype')
    group_role = sa.Enum('owner', 'admin', 'member', name='grouprole')
    message_type = sa.Enum('text', 'task_share', 'progress', 'achievement', 'checkin', 'system', name='messagetype')

    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    # 只在 PostgreSQL 中创建枚举类型
    if is_postgresql:
        friendship_status.create(op.get_bind(), checkfirst=True)
        group_type.create(op.get_bind(), checkfirst=True)
        group_role.create(op.get_bind(), checkfirst=True)
        message_type.create(op.get_bind(), checkfirst=True)

    # 创建 friendships 表
    op.create_table('friendships',
        sa.Column('user_id', app.models.base.GUID(), nullable=False),
        sa.Column('friend_id', app.models.base.GUID(), nullable=False),
        sa.Column('status', friendship_status if is_postgresql else sa.String(20), nullable=False, server_default='pending'),
        sa.Column('initiated_by', app.models.base.GUID(), nullable=False),
        sa.Column('match_reason', sa.JSON(), nullable=True),
        sa.Column('id', app.models.base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['friend_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['initiated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'friend_id', name='uq_friendship')
    )
    with op.batch_alter_table('friendships', schema=None) as batch_op:
        batch_op.create_index('idx_friendship_user', ['user_id'])
        batch_op.create_index('idx_friendship_friend', ['friend_id'])
        batch_op.create_index('idx_friendship_status', ['status'])
        batch_op.create_index(batch_op.f('ix_friendships_deleted_at'), ['deleted_at'])

    # 创建 groups 表
    op.create_table('groups',
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('type', group_type if is_postgresql else sa.String(20), nullable=False),
        sa.Column('focus_tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('sprint_goal', sa.Text(), nullable=True),
        sa.Column('max_members', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('join_requires_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('total_flame_power', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('today_checkin_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tasks_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('id', app.models.base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('groups', schema=None) as batch_op:
        batch_op.create_index('idx_group_type', ['type'])
        batch_op.create_index('idx_group_public', ['is_public'])
        batch_op.create_index(batch_op.f('ix_groups_deleted_at'), ['deleted_at'])

    # 创建 group_members 表
    op.create_table('group_members',
        sa.Column('group_id', app.models.base.GUID(), nullable=False),
        sa.Column('user_id', app.models.base.GUID(), nullable=False),
        sa.Column('role', group_role if is_postgresql else sa.String(20), nullable=False, server_default='member'),
        sa.Column('is_muted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('flame_contribution', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tasks_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('checkin_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_checkin_date', sa.DateTime(), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Column('last_active_at', sa.DateTime(), nullable=False),
        sa.Column('id', app.models.base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'user_id', name='uq_group_member')
    )
    with op.batch_alter_table('group_members', schema=None) as batch_op:
        batch_op.create_index('idx_member_group', ['group_id'])
        batch_op.create_index('idx_member_user', ['user_id'])
        batch_op.create_index(batch_op.f('ix_group_members_deleted_at'), ['deleted_at'])

    # 创建 group_messages 表
    op.create_table('group_messages',
        sa.Column('group_id', app.models.base.GUID(), nullable=False),
        sa.Column('sender_id', app.models.base.GUID(), nullable=True),  # 系统消息可为空
        sa.Column('message_type', message_type if is_postgresql else sa.String(20), nullable=False, server_default='text'),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_data', sa.JSON(), nullable=True),
        sa.Column('reply_to_id', app.models.base.GUID(), nullable=True),
        sa.Column('id', app.models.base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reply_to_id'], ['group_messages.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('group_messages', schema=None) as batch_op:
        batch_op.create_index('idx_message_group_time', ['group_id', 'created_at'])
        batch_op.create_index(batch_op.f('ix_group_messages_deleted_at'), ['deleted_at'])

    # 创建 group_tasks 表
    op.create_table('group_tasks',
        sa.Column('group_id', app.models.base.GUID(), nullable=False),
        sa.Column('created_by', app.models.base.GUID(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('estimated_minutes', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('difficulty', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('total_claims', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_completions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('id', app.models.base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('group_tasks', schema=None) as batch_op:
        batch_op.create_index('idx_group_task_group', ['group_id'])
        batch_op.create_index(batch_op.f('ix_group_tasks_deleted_at'), ['deleted_at'])

    # 创建 group_task_claims 表
    op.create_table('group_task_claims',
        sa.Column('group_task_id', app.models.base.GUID(), nullable=False),
        sa.Column('user_id', app.models.base.GUID(), nullable=False),
        sa.Column('personal_task_id', app.models.base.GUID(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('claimed_at', sa.DateTime(), nullable=False),
        sa.Column('id', app.models.base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['group_task_id'], ['group_tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['personal_task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_task_id', 'user_id', name='uq_task_claim')
    )
    with op.batch_alter_table('group_task_claims', schema=None) as batch_op:
        batch_op.create_index('idx_claim_task', ['group_task_id'])
        batch_op.create_index('idx_claim_user', ['user_id'])
        batch_op.create_index(batch_op.f('ix_group_task_claims_deleted_at'), ['deleted_at'])


def downgrade() -> None:
    """删除社群功能相关表"""
    op.drop_table('group_task_claims')
    op.drop_table('group_tasks')
    op.drop_table('group_messages')
    op.drop_table('group_members')
    op.drop_table('groups')
    op.drop_table('friendships')

    # 删除枚举类型
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS messagetype')
        op.execute('DROP TYPE IF EXISTS grouprole')
        op.execute('DROP TYPE IF EXISTS grouptype')
        op.execute('DROP TYPE IF EXISTS friendshipstatus')
