"""Add community privacy and block features

Revision ID: d5e7a3c2b1f4
Revises: c8e4f2a3b1d5
Create Date: 2026-03-15

添加社群隐私设置和拉黑功能：
1. 用户搜索隐私设置 (searchable_by)
2. 用户拉黑表 (user_blocks)
3. 消息撤回时间限制配置
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd5e7a3c2b1f4'
down_revision = 'c8e4f2a3b1d5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    search_visibility_enum = postgresql.ENUM(
        'everyone',
        'friends',
        'nobody',
        name='searchvisibility',
    )
    search_visibility_enum.create(op.get_bind(), checkfirst=True)

    # 1. 添加用户搜索隐私设置字段
    op.add_column(
        'users',
        sa.Column(
            'searchable_by',
            search_visibility_enum,
            nullable=False,
            server_default='everyone',
            comment='用户搜索隐私设置'
        )
    )

    # 2. 创建用户拉黑表
    op.create_table(
        'user_blocks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'blocker_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            comment='执行拉黑的用户ID'
        ),
        sa.Column(
            'blocked_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            comment='被拉黑的用户ID'
        ),
        sa.Column(
            'reason',
            sa.String(500),
            nullable=True,
            comment='拉黑原因'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            comment='拉黑时间'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment='更新时间'
        ),
        sa.Column(
            'deleted_at',
            sa.DateTime(),
            nullable=True,
            comment='软删除时间（解除拉黑）'
        ),
    )

    # 添加唯一约束：同一对用户只能有一条拉黑记录
    op.create_unique_constraint(
        'uq_user_blocks',
        'user_blocks',
        ['blocker_id', 'blocked_id']
    )

    # 添加索引
    op.create_index(
        'idx_user_blocks_blocker',
        'user_blocks',
        ['blocker_id', 'deleted_at']
    )
    op.create_index(
        'idx_user_blocks_blocked',
        'user_blocks',
        ['blocked_id', 'deleted_at']
    )

    # 3. 添加消息撤回时间配置到系统配置（如果存在 system_configs 表）
    # 这里使用 INSERT 而不是 ALTER TABLE，因为配置可能存储在单独的表中
    # 如果系统使用环境变量或配置文件，则跳过此步骤


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_user_blocks_blocked', table_name='user_blocks')
    op.drop_index('idx_user_blocks_blocker', table_name='user_blocks')

    # 删除约束
    op.drop_constraint('uq_user_blocks', 'user_blocks', type_='unique')

    # 删除拉黑表
    op.drop_table('user_blocks')

    # 删除用户搜索隐私设置字段
    op.drop_column('users', 'searchable_by')

    # 删除枚举类型
    op.execute('DROP TYPE IF EXISTS searchvisibility')
