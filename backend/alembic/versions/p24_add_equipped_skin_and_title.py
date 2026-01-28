"""add equipped_skin and equipped_title to users

Revision ID: p24_add_equipped_fields
Revises: p23_add_shop_system
Create Date: 2026-01-28 12:00:00.000000

Migration Contract:
  type: reversible
  rollback_plan: "alembic downgrade -1"
  verification_query: "SELECT equipped_skin, equipped_title FROM users LIMIT 1;"
  backfill_plan: "N/A - new nullable fields"
  owner: "sparkle-team"
  ticket: "shop-system-effects"
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'p24_add_equipped_fields'
down_revision: Union[str, None] = 'p23_add_shop_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    添加用户装备字段

    Changes:
    - 添加 equipped_skin 字段（当前装备的皮肤ID）
    - 添加 equipped_title 字段（当前装备的称号ID）
    """

    # 添加装备皮肤字段
    op.add_column(
        'users',
        sa.Column(
            'equipped_skin',
            sa.String(50),
            nullable=True,
            comment='当前装备的皮肤ID（对应shop_items.id）'
        )
    )

    # 添加装备称号字段
    op.add_column(
        'users',
        sa.Column(
            'equipped_title',
            sa.String(50),
            nullable=True,
            comment='当前装备的称号ID（对应shop_items.id）'
        )
    )

    # 创建索引以加速查询
    op.create_index(
        'ix_users_equipped_skin',
        'users',
        ['equipped_skin']
    )

    op.create_index(
        'ix_users_equipped_title',
        'users',
        ['equipped_title']
    )


def downgrade() -> None:
    """
    回滚：删除装备字段
    """

    # 删除索引
    op.drop_index('ix_users_equipped_title', table_name='users')
    op.drop_index('ix_users_equipped_skin', table_name='users')

    # 删除字段
    op.drop_column('users', 'equipped_title')
    op.drop_column('users', 'equipped_skin')
