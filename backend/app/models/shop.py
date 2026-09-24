# AI-OPAQUE: photon transaction history is economy/audit data and should not be treated as direct learner semantics.
"""
Shop System Models
商城系统数据模型 - 包含商城物品、购买记录、光子交易历史、用户消耗品
"""
import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PhotonTransactionType(enum.StrEnum):
    """光子交易类型"""
    GRANT_ACHIEVEMENT = "grant_achievement"       # 成就奖励
    GRANT_DAILY_FIRST = "grant_daily_first"       # 每日首胜
    GRANT_CONTRACT = "grant_contract"             # 合同完成奖励
    GRANT_CONTRACT_BONUS = "grant_contract_bonus" # 合同完成加成
    GRANT_BONUS = "grant_bonus"                   # combo 加成（PHOTON-STREAM：补录审计流水，杜绝 admin_adjustment 兜底误标）
    DEDUCT_CONTRACT_STAKE = "deduct_contract_stake" # 合同失败扣除
    PURCHASE = "purchase"                         # 商城购买
    TRANSFER_OUT = "transfer_out"                 # 转账-转出
    TRANSFER_IN = "transfer_in"                   # 转账-转入
    REFUND = "refund"                             # 退款
    PENALTY = "penalty"                           # 惩罚
    ADMIN_ADJUSTMENT = "admin_adjustment"         # 管理员调整
    REDEEM_PRO = "redeem_pro"                     # 光子兑换 Pro（D-COMM-2 学出会员）
    CONTRACT_ESCROW = "contract_escrow"           # 契约押金托管预扣（MINT-FIX：创建时扣，完成结算含还本，失败即没收）
    GUEST_SEED = "guest_seed"                     # 访客体验种子（MINT-FIX：营销补贴出「可兑换基数」词表，非学习所得）


class ShopItemType(enum.StrEnum):
    """商城物品类型"""
    SKIN = "skin"           # 皮肤
    TITLE = "title"         # 称号
    CONSUMABLE = "consumable" # 消耗品
    BOOST = "boost"         # 加成道具
    VISUAL_ELEMENT = "visual_element"  # 视觉元素（背景、粒子、特效）


class ItemRarity(enum.StrEnum):
    """物品稀有度"""
    COMMON = "common"       # 普通 (灰/白)
    RARE = "rare"           # 稀有 (蓝)
    EPIC = "epic"           # 史诗 (紫)
    LEGENDARY = "legendary" # 传说 (金/橙)


class ConsumableEffectType(enum.StrEnum):
    """消耗品效果类型"""
    EXP_BOOST = "exp_boost"           # 经验加成
    PHOTON_BOOST = "photon_boost"     # 光子加成
    STREAK_FREEZE = "streak_freeze"   # 连击冻结
    HINT_REVEAL = "hint_reveal"       # 提示解锁
    ENERGY_RESTORE = "energy_restore" # 能量恢复
    CUSTOM_AVATAR = "custom_avatar"   # 自定义头像


class PhotonTransactionHistory(BaseModel):
    """光子交易历史记录表"""
    __tablename__ = "photon_transaction_history"

    id: Mapped[Any] = mapped_column(GUID(), primary_key=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, comment="变动数量（正数为增加，负数为减少）")
    balance_before: Mapped[int] = mapped_column(Integer, nullable=False, comment="交易前余额")
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False, comment="交易后余额")
    source: Mapped[str] = mapped_column(String(255), nullable=True, comment="来源描述")
    related_item_id: Mapped[str] = mapped_column(String(50), nullable=True, comment="相关物品ID（如商城物品ID、成就ID等）")
    extra_data: Mapped[Any] = mapped_column(JSON, nullable=True, comment="额外元数据（JSON格式）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="photon_transactions")

    __table_args__ = (
        Index("ix_photon_transaction_history_user_id_created_at", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<PhotonTransactionHistory(id={self.id}, user_id={self.user_id}, type={self.transaction_type}, amount={self.amount})>"


class ShopItem(BaseModel):
    """商城物品表"""
    __tablename__ = "shop_items"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="物品ID（如：skin_galaxy_001）")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="物品名称")
    description: Mapped[str] = mapped_column(Text, nullable=True, comment="物品描述")
    item_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="物品类型")
    category: Mapped[str] = mapped_column(String(50), nullable=False, comment="分类（如：galaxy_skin、achievement_title等）")
    price_photons: Mapped[int] = mapped_column(Integer, nullable=False, comment="当前价格（光子）")
    original_price: Mapped[int] = mapped_column(Integer, nullable=True, comment="原价（用于折扣显示）")
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=True, comment="折扣百分比（0-100）")
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否可购买")
    is_limited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否限量")
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=True, comment="库存数量（限量物品使用）")
    icon_url: Mapped[str] = mapped_column(String(500), nullable=True, comment="物品图标URL")
    rarity: Mapped[str] = mapped_column(String(50), nullable=False, default="common", comment="物品稀有度")
    item_config: Mapped[Any] = mapped_column(JSON, nullable=True, comment="物品配置（如皮肤ID、称号文本、消耗品效果等）")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序权重（越大越靠前）")

    # 关系
    purchases = relationship("ShopPurchase", back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_shop_items_item_type_is_available", "item_type", "is_available"),
        Index("ix_shop_items_rarity", "rarity"),
        Index("ix_shop_items_sort_order", "sort_order"),
    )

    @property
    def has_discount(self) -> bool:
        """是否有折扣"""
        return self.discount_percent is not None and self.discount_percent > 0

    @property
    def is_in_stock(self) -> bool:
        """是否有库存"""
        if not self.is_limited:
            return True
        return self.stock_quantity is not None and self.stock_quantity > 0

    def __repr__(self):
        return f"<ShopItem(id={self.id}, name={self.name}, type={self.item_type}, price={self.price_photons})>"


class ShopPurchase(BaseModel):
    """商城购买记录表"""
    __tablename__ = "shop_purchases"

    id: Mapped[Any] = mapped_column(GUID(), primary_key=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(50), ForeignKey("shop_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    price_paid: Mapped[int] = mapped_column(Integer, nullable=False, comment="实际支付价格")
    photon_balance_before: Mapped[int] = mapped_column(Integer, nullable=False, comment="购买前光子余额")
    photon_balance_after: Mapped[int] = mapped_column(Integer, nullable=False, comment="购买后光子余额")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="shop_purchases")
    item = relationship("ShopItem", back_populates="purchases")

    __table_args__ = (
        Index("ix_shop_purchases_user_id_created_at", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<ShopPurchase(id={self.id}, user_id={self.user_id}, item_id={self.item_id}, price={self.price_paid})>"


class UserConsumable(BaseModel):
    """用户消耗品表"""
    __tablename__ = "user_consumables"

    id: Mapped[Any] = mapped_column(GUID(), primary_key=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consumable_id: Mapped[str] = mapped_column(String(50), ForeignKey("shop_items.id", ondelete="RESTRICT"), nullable=False)
    effect_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="效果类型")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="数量")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, comment="过期时间（NULL表示永久有效）")

    # 关系
    user = relationship("User", back_populates="consumables")
    consumable_item = relationship("ShopItem")

    __table_args__ = (
        Index("ix_user_consumables_user_id_expires_at", "user_id", "expires_at"),
        Index("ix_user_consumables_effect_type", "effect_type"),
        Index("ix_user_consumables_user_id_consumable_id", "user_id", "consumable_id"),
    )

    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.expires_at is None:
            return False
        return _utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """是否有效（未过期且有库存）"""
        return not self.is_expired and self.quantity > 0

    def __repr__(self):
        return f"<UserConsumable(id={self.id}, user_id={self.user_id}, effect_type={self.effect_type}, quantity={self.quantity})>"
