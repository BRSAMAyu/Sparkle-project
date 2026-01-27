"""add photon balance to users

Revision ID: d71e6a4a774f
Revises: cf32be97c82a
Create Date: 2026-01-28 02:38:22.079595

Migration Contract:
  type: reversible
  rollback_plan: "alembic downgrade -1"
  verification_query: "SELECT COUNT(*) FROM users WHERE photon_balance IS NOT NULL;"
  backfill_plan: "Set default photon_balance = 0 for existing users"
  owner: "sparkle-team"
  ticket: "photon-system"
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd71e6a4a774f'
down_revision: Union[str, None] = 'cf32be97c82a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    添加光子积分字段到 users 表

    Changes:
    - 添加 photon_balance: INTEGER (默认 0)
    - 添加 photon_updated_at: TIMESTAMP (可为 NULL)
    - 创建索引以优化查询
    """
    # 添加 photon_balance 字段（默认值为 0）
    op.add_column(
        'users',
        sa.Column(
            'photon_balance',
            sa.Integer(),
            nullable=False,
            server_default='0'
        )
    )

    # 添加 photon_updated_at 字段
    op.add_column(
        'users',
        sa.Column(
            'photon_updated_at',
            sa.DateTime(),
            nullable=True
        )
    )

    # 创建索引以优化光子排行榜查询
    op.create_index(
        'ix_users_photon_balance',
        'users',
        ['photon_balance'],
        unique=False
    )


def downgrade() -> None:
    """
    回滚迁移：删除光子积分相关字段
    """
    # 删除索引
    op.drop_index('ix_users_photon_balance', table_name='users')

    # 删除字段
    op.drop_column('users', 'photon_updated_at')
    op.drop_column('users', 'photon_balance')
