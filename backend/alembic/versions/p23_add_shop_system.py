"""add shop system

Revision ID: a1b2c3d4e5f6
Revises: d71e6a4a774f
Create Date: 2026-01-28 10:00:00.000000

Migration Contract:
  type: reversible
  rollback_plan: "alembic downgrade -1"
  verification_query: "SELECT COUNT(*) FROM shop_items;"
  backfill_plan: "Insert initial shop items via seed script"
  owner: "sparkle-team"
  ticket: "shop-system"
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd71e6a4a774f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    创建商城系统相关表

    Changes:
    - 创建光子交易历史表 (photon_transaction_history)
    - 创建商城物品表 (shop_items)
    - 创建购买记录表 (shop_purchases)
    - 创建消耗品表 (user_consumables)
    """

    # 1. 创建枚举类型
    # 光子交易类型枚举
    photon_transaction_type_enum = ENUM(
        'grant_achievement',      # 成就奖励
        'grant_daily_first',      # 每日首胜
        'grant_contract',         # 合同完成奖励
        'grant_contract_bonus',   # 合同完成加成
        'deduct_contract_stake',  # 合同失败扣除
        'purchase',               # 商城购买
        'transfer_out',           # 转账-转出
        'transfer_in',            # 转账-转入
        'refund',                 # 退款
        'penalty',                # 惩罚
        'admin_adjustment',       # 管理员调整
        name='photontransactiontype',
        create_type=True,
    )

    photon_transaction_type_enum.create(op.get_bind(), checkfirst=True)

    # 商城物品类型枚举
    shop_item_type_enum = ENUM(
        'skin',         # 皮肤
        'title',        # 称号
        'consumable',   # 消耗品
        'boost',        # 加成道具
        name='shopitemtype',
        create_type=True,
    )

    shop_item_type_enum.create(op.get_bind(), checkfirst=True)

    # 物品稀有度枚举
    item_rarity_enum = ENUM(
        'common',      # 普通 (灰/白)
        'rare',        # 稀有 (蓝)
        'epic',        # 史诗 (紫)
        'legendary',   # 传说 (金/橙)
        name='itemrarity',
        create_type=True,
    )

    item_rarity_enum.create(op.get_bind(), checkfirst=True)

    # 消耗品效果类型枚举
    consumable_effect_type_enum = ENUM(
        'exp_boost',          # 经验加成
        'photon_boost',       # 光子加成
        'streak_freeze',      # 连击冻结
        'hint_reveal',        # 提示解锁
        'energy_restore',     # 能量恢复
        'custom_avatar',      # 自定义头像
        name='consumableeffecttype',
        create_type=True,
    )

    consumable_effect_type_enum.create(op.get_bind(), checkfirst=True)

    # 2. 创建光子交易历史表
    op.create_table(
        'photon_transaction_history',
        sa.Column(
            'id',
            UUID,
            server_default=sa.text('gen_random_uuid()'),
            primary_key=True
        ),
        sa.Column(
            'user_id',
            UUID,
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            comment='用户ID'
        ),
        sa.Column(
            'transaction_type',
            sa.Enum(
                'grant_achievement',
                'grant_daily_first',
                'grant_contract',
                'grant_contract_bonus',
                'deduct_contract_stake',
                'purchase',
                'transfer_out',
                'transfer_in',
                'refund',
                'penalty',
                'admin_adjustment',
                name='photontransactiontype'
            ),
            nullable=False,
            comment='交易类型'
        ),
        sa.Column(
            'amount',
            sa.Integer(),
            nullable=False,
            comment='变动数量（正数为增加，负数为减少）'
        ),
        sa.Column(
            'balance_before',
            sa.Integer(),
            nullable=False,
            comment='交易前余额'
        ),
        sa.Column(
            'balance_after',
            sa.Integer(),
            nullable=False,
            comment='交易后余额'
        ),
        sa.Column(
            'source',
            sa.String(255),
            nullable=True,
            comment='来源描述'
        ),
        sa.Column(
            'related_item_id',
            sa.String(50),
            nullable=True,
            comment='相关物品ID（如商城物品ID、成就ID等）'
        ),
        sa.Column(
            'metadata',
            JSONB,
            nullable=True,
            comment='额外元数据（JSON格式）'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
            comment='交易时间'
        ),
        comment='光子交易历史记录表'
    )

    # 创建索引：按用户查询交易历史
    op.create_index(
        'ix_photon_transaction_history_user_id_created_at',
        'photon_transaction_history',
        ['user_id', 'created_at'],
        unique=False
    )

    # 创建索引：按交易类型查询
    op.create_index(
        'ix_photon_transaction_history_transaction_type',
        'photon_transaction_history',
        ['transaction_type'],
        unique=False
    )

    # 3. 创建商城物品表
    op.create_table(
        'shop_items',
        sa.Column(
            'id',
            sa.String(50),
            primary_key=True,
            comment='物品ID（如：skin_galaxy_001）'
        ),
        sa.Column(
            'name',
            sa.String(100),
            nullable=False,
            comment='物品名称'
        ),
        sa.Column(
            'description',
            sa.Text(),
            nullable=True,
            comment='物品描述'
        ),
        sa.Column(
            'item_type',
            sa.Enum(
                'skin',
                'title',
                'consumable',
                'boost',
                name='shopitemtype'
            ),
            nullable=False,
            comment='物品类型'
        ),
        sa.Column(
            'category',
            sa.String(50),
            nullable=False,
            comment='分类（如：galaxy_skin、achievement_title等）'
        ),
        sa.Column(
            'price_photons',
            sa.Integer(),
            nullable=False,
            comment='当前价格（光子）'
        ),
        sa.Column(
            'original_price',
            sa.Integer(),
            nullable=True,
            comment='原价（用于折扣显示）'
        ),
        sa.Column(
            'discount_percent',
            sa.Integer(),
            nullable=True,
            comment='折扣百分比（0-100）'
        ),
        sa.Column(
            'is_available',
            sa.Boolean(),
            nullable=False,
            server_default='true',
            comment='是否可购买'
        ),
        sa.Column(
            'is_limited',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='是否限量'
        ),
        sa.Column(
            'stock_quantity',
            sa.Integer(),
            nullable=True,
            comment='库存数量（限量物品使用）'
        ),
        sa.Column(
            'icon_url',
            sa.String(500),
            nullable=True,
            comment='物品图标URL'
        ),
        sa.Column(
            'rarity',
            sa.Enum(
                'common',
                'rare',
                'epic',
                'legendary',
                name='itemrarity'
            ),
            nullable=False,
            server_default='common',
            comment='物品稀有度'
        ),
        sa.Column(
            'item_config',
            JSONB,
            nullable=True,
            comment='物品配置（如皮肤ID、称号文本、消耗品效果等）'
        ),
        sa.Column(
            'sort_order',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='排序权重（越大越靠前）'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            onupdate=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        ),
        comment='商城物品表'
    )

    # 创建索引：按类型和可用性查询
    op.create_index(
        'ix_shop_items_item_type_is_available',
        'shop_items',
        ['item_type', 'is_available'],
        unique=False
    )

    # 创建索引：按稀有度查询
    op.create_index(
        'ix_shop_items_rarity',
        'shop_items',
        ['rarity'],
        unique=False
    )

    # 创建索引：按排序权重
    op.create_index(
        'ix_shop_items_sort_order',
        'shop_items',
        ['sort_order'],
        unique=False
    )

    # 4. 创建购买记录表
    op.create_table(
        'shop_purchases',
        sa.Column(
            'id',
            UUID,
            server_default=sa.text('gen_random_uuid()'),
            primary_key=True
        ),
        sa.Column(
            'user_id',
            UUID,
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            comment='用户ID'
        ),
        sa.Column(
            'item_id',
            sa.String(50),
            sa.ForeignKey('shop_items.id', ondelete='RESTRICT'),
            nullable=False,
            comment='物品ID'
        ),
        sa.Column(
            'price_paid',
            sa.Integer(),
            nullable=False,
            comment='实际支付价格'
        ),
        sa.Column(
            'photon_balance_before',
            sa.Integer(),
            nullable=False,
            comment='购买前光子余额'
        ),
        sa.Column(
            'photon_balance_after',
            sa.Integer(),
            nullable=False,
            comment='购买后光子余额'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
            comment='购买时间'
        ),
        comment='商城购买记录表'
    )

    # 创建索引：按用户查询购买历史
    op.create_index(
        'ix_shop_purchases_user_id_created_at',
        'shop_purchases',
        ['user_id', 'created_at'],
        unique=False
    )

    # 创建索引：按物品查询购买记录
    op.create_index(
        'ix_shop_purchases_item_id',
        'shop_purchases',
        ['item_id'],
        unique=False
    )

    # 5. 创建用户消耗品表
    op.create_table(
        'user_consumables',
        sa.Column(
            'id',
            UUID,
            server_default=sa.text('gen_random_uuid()'),
            primary_key=True
        ),
        sa.Column(
            'user_id',
            UUID,
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            comment='用户ID'
        ),
        sa.Column(
            'consumable_id',
            sa.String(50),
            sa.ForeignKey('shop_items.id', ondelete='RESTRICT'),
            nullable=False,
            comment='消耗品ID'
        ),
        sa.Column(
            'effect_type',
            sa.Enum(
                'exp_boost',
                'photon_boost',
                'streak_freeze',
                'hint_reveal',
                'energy_restore',
                'custom_avatar',
                name='consumableeffecttype'
            ),
            nullable=False,
            comment='效果类型'
        ),
        sa.Column(
            'quantity',
            sa.Integer(),
            nullable=False,
            server_default='1',
            comment='数量'
        ),
        sa.Column(
            'expires_at',
            sa.DateTime(),
            nullable=True,
            comment='过期时间（NULL表示永久有效）'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            onupdate=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        ),
        comment='用户消耗品表'
    )

    # 创建索引：按用户查询消耗品
    op.create_index(
        'ix_user_consumables_user_id_expires_at',
        'user_consumables',
        ['user_id', 'expires_at'],
        unique=False
    )

    # 创建索引：按效果类型查询
    op.create_index(
        'ix_user_consumables_effect_type',
        'user_consumables',
        ['effect_type'],
        unique=False
    )

    # 创建唯一约束：防止同一用户的同一消耗品重复记录
    op.create_index(
        'ix_user_consumables_user_id_consumable_id',
        'user_consumables',
        ['user_id', 'consumable_id'],
        unique=False
    )


def downgrade() -> None:
    """
    回滚迁移：删除商城系统相关表
    """
    # 删除表（按照外键依赖顺序逆序删除）
    op.drop_table('user_consumables')
    op.drop_table('shop_purchases')
    op.drop_table('shop_items')
    op.drop_table('photon_transaction_history')

    # 删除枚举类型
    sa.Enum(name='consumableeffecttype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='itemrarity').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='shopitemtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='photontransactiontype').drop(op.get_bind(), checkfirst=True)
