"""Add missing tables and soft delete support

Revision ID: a1b2c3d4e5f6
Revises: 5504e72df4f0
Create Date: 2025-12-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from app.models.base import GUID


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5504e72df4f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # === 1. 创建 subjects 表（如果不存在）===
    if not table_exists('subjects'):
        op.create_table(
            'subjects',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('aliases', sa.JSON(), nullable=True),
            sa.Column('category', sa.String(length=50), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
            sa.Column('sort_order', sa.Integer(), nullable=True, default=0),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index('idx_subjects_name', 'subjects', ['name'], unique=False)
        op.create_index('idx_subjects_category', 'subjects', ['category'], unique=False)
        op.create_index('idx_subjects_is_active', 'subjects', ['is_active'], unique=False)

    # === 2. 创建 jobs 表（如果不存在）===
    if not table_exists('jobs'):
        op.create_table(
            'jobs',
            sa.Column('id', GUID(), nullable=False),
            sa.Column('user_id', GUID(), nullable=False),
            sa.Column('type', sa.String(length=50), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, default='pending'),
            sa.Column('params', sa.JSON(), nullable=True),
            sa.Column('result', sa.JSON(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('progress', sa.Integer(), nullable=True, default=0),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('timeout_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_jobs_user_id', 'jobs', ['user_id'], unique=False)
        op.create_index('idx_jobs_status', 'jobs', ['status'], unique=False)
        op.create_index('idx_jobs_type', 'jobs', ['type'], unique=False)
        op.create_index('idx_jobs_deleted_at', 'jobs', ['deleted_at'], unique=False)
    else:
        # jobs 表已存在，添加 deleted_at 列（如果不存在）
        if not column_exists('jobs', 'deleted_at'):
            op.add_column('jobs', sa.Column('deleted_at', sa.DateTime(), nullable=True))
            op.create_index('idx_jobs_deleted_at', 'jobs', ['deleted_at'], unique=False)

    # === 3. 创建 idempotency_keys 表（如果不存在）===
    if not table_exists('idempotency_keys'):
        op.create_table(
            'idempotency_keys',
            sa.Column('key', sa.String(length=64), nullable=False),
            sa.Column('user_id', GUID(), nullable=False),
            sa.Column('response', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('key')
        )
        op.create_index('idx_idempotency_user_id', 'idempotency_keys', ['user_id'], unique=False)
        op.create_index('idx_idempotency_expires', 'idempotency_keys', ['expires_at'], unique=False)

    # === 4. 为所有继承 BaseModel 的表添加 deleted_at 字段（如果不存在）===

    # users 表
    if table_exists('users') and not column_exists('users', 'deleted_at'):
        op.add_column('users', sa.Column('deleted_at', sa.DateTime(), nullable=True))
        op.create_index('idx_users_deleted_at', 'users', ['deleted_at'], unique=False)

    # plans 表
    if table_exists('plans') and not column_exists('plans', 'deleted_at'):
        op.add_column('plans', sa.Column('deleted_at', sa.DateTime(), nullable=True))
        op.create_index('idx_plans_deleted_at', 'plans', ['deleted_at'], unique=False)

    # tasks 表
    if table_exists('tasks') and not column_exists('tasks', 'deleted_at'):
        op.add_column('tasks', sa.Column('deleted_at', sa.DateTime(), nullable=True))
        op.create_index('idx_tasks_deleted_at', 'tasks', ['deleted_at'], unique=False)

    # chat_messages 表
    if table_exists('chat_messages') and not column_exists('chat_messages', 'deleted_at'):
        op.add_column('chat_messages', sa.Column('deleted_at', sa.DateTime(), nullable=True))
        op.create_index('idx_chat_deleted_at', 'chat_messages', ['deleted_at'], unique=False)

    # error_records 表
    if table_exists('error_records') and not column_exists('error_records', 'deleted_at'):
        op.add_column('error_records', sa.Column('deleted_at', sa.DateTime(), nullable=True))
        op.create_index('idx_error_deleted_at', 'error_records', ['deleted_at'], unique=False)


def downgrade() -> None:
    # === 移除 deleted_at 字段 ===
    if table_exists('error_records') and column_exists('error_records', 'deleted_at'):
        op.drop_index('idx_error_deleted_at', table_name='error_records')
        op.drop_column('error_records', 'deleted_at')

    if table_exists('chat_messages') and column_exists('chat_messages', 'deleted_at'):
        op.drop_index('idx_chat_deleted_at', table_name='chat_messages')
        op.drop_column('chat_messages', 'deleted_at')

    if table_exists('tasks') and column_exists('tasks', 'deleted_at'):
        op.drop_index('idx_tasks_deleted_at', table_name='tasks')
        op.drop_column('tasks', 'deleted_at')

    if table_exists('plans') and column_exists('plans', 'deleted_at'):
        op.drop_index('idx_plans_deleted_at', table_name='plans')
        op.drop_column('plans', 'deleted_at')

    if table_exists('users') and column_exists('users', 'deleted_at'):
        op.drop_index('idx_users_deleted_at', table_name='users')
        op.drop_column('users', 'deleted_at')

    # === 删除 idempotency_keys 表 ===
    if table_exists('idempotency_keys'):
        op.drop_index('idx_idempotency_expires', table_name='idempotency_keys')
        op.drop_index('idx_idempotency_user_id', table_name='idempotency_keys')
        op.drop_table('idempotency_keys')

    # === 删除 jobs 表 ===
    if table_exists('jobs'):
        if column_exists('jobs', 'deleted_at'):
            op.drop_index('idx_jobs_deleted_at', table_name='jobs')
        op.drop_index('idx_jobs_type', table_name='jobs')
        op.drop_index('idx_jobs_status', table_name='jobs')
        op.drop_index('idx_jobs_user_id', table_name='jobs')
        op.drop_table('jobs')

    # === 删除 subjects 表 ===
    if table_exists('subjects'):
        op.drop_index('idx_subjects_is_active', table_name='subjects')
        op.drop_index('idx_subjects_category', table_name='subjects')
        op.drop_index('idx_subjects_name', table_name='subjects')
        op.drop_table('subjects')
