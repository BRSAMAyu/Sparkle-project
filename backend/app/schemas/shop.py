"""Shop Schemas - Shop system request/response models"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.shop import ItemRarity, ShopItemType
from app.schemas.common import BaseSchema

# ========== Shop Item Schemas ==========

class ShopItemBase(BaseSchema):
    """Shop item basic information"""
    id: str = Field(description="Item ID")
    name: str = Field(description="Item name")
    description: str | None = Field(default=None, description="Item description")
    item_type: ShopItemType = Field(description="Item type")
    category: str = Field(description="Category")
    icon_url: str | None = Field(default=None, description="Icon URL")
    rarity: ItemRarity = Field(description="Item rarity")
    item_config: dict[str, Any] | None = Field(default=None, description="Item config")


class ShopItemDetail(ShopItemBase):
    """Shop item detailed information"""
    price_photons: int = Field(description="Current price in photons")
    original_price: int | None = Field(default=None, description="Original price")
    discount_percent: int | None = Field(default=None, description="Discount percentage")
    is_available: bool = Field(description="Is available for purchase")
    is_limited: bool = Field(description="Is limited edition")
    stock_quantity: int | None = Field(default=None, description="Stock quantity")
    sort_order: int = Field(description="Sort order")

    @property
    def has_discount(self) -> bool:
        """Has discount"""
        return self.discount_percent is not None and self.discount_percent > 0

    @property
    def is_in_stock(self) -> bool:
        """Is in stock"""
        if not self.is_limited:
            return True
        return self.stock_quantity is not None and self.stock_quantity > 0


class ShopItemSummary(BaseModel):
    """Shop item summary for list views"""
    id: str = Field(description="Item ID")
    name: str = Field(description="Item name")
    icon_url: str | None = Field(default=None, description="Icon URL")
    item_type: ShopItemType = Field(description="Item type")
    rarity: ItemRarity = Field(description="Item rarity")
    price_photons: int = Field(description="Current price in photons")
    original_price: int | None = Field(default=None, description="Original price")
    discount_percent: int | None = Field(default=None, description="Discount percentage")
    is_available: bool = Field(description="Is available")
    is_limited: bool = Field(description="Is limited")
    stock_quantity: int | None = Field(default=None, description="Stock quantity")
    is_owned: bool = Field(default=False, description="User owns this item")

    model_config = ConfigDict(from_attributes=True)


class ShopItemListResponse(BaseModel):
    """Shop item list response"""
    success: bool = Field(default=True)
    data: list[ShopItemSummary] = Field(default_factory=list, description="Shop items")
    meta: dict[str, Any] = Field(default_factory=dict, description="Metadata like categories, filters")


class ShopItemDetailResponse(BaseModel):
    """Shop item detail response"""
    success: bool = Field(default=True)
    data: ShopItemDetail = Field(description="Shop item detail")


# ========== Purchase Schemas ==========

class PurchaseRequest(BaseModel):
    """Purchase request"""
    item_id: str = Field(description="Item ID to purchase")

    model_config = ConfigDict(json_schema_extra={"example": {"item_id": "skin_galaxy_001"}})


class PurchaseResponse(BaseModel):
    """Purchase response"""
    success: bool = Field(default=True)
    message: str = Field(description="Success message")
    data: dict[str, Any] = Field(description="Purchase result")
    item: ShopItemSummary = Field(description="Purchased item")
    balance_before: int = Field(description="Photon balance before purchase")
    balance_after: int = Field(description="Photon balance after purchase")
    price_paid: int = Field(description="Price paid")


class PurchaseHistoryItem(BaseModel):
    """Purchase history item"""
    id: UUID = Field(description="Purchase ID")
    item_id: str = Field(description="Item ID")
    item_name: str = Field(description="Item name")
    item_icon_url: str | None = Field(default=None, description="Item icon URL")
    item_type: ShopItemType = Field(description="Item type")
    price_paid: int = Field(description="Price paid")
    photon_balance_before: int = Field(description="Balance before")
    photon_balance_after: int = Field(description="Balance after")
    created_at: datetime = Field(description="Purchase time")

    model_config = ConfigDict(from_attributes=True)


class PurchaseHistoryResponse(BaseModel):
    """Purchase history response"""
    success: bool = Field(default=True)
    data: list[PurchaseHistoryItem] = Field(default_factory=list, description="Purchase history")
    meta: dict[str, Any] = Field(default_factory=dict, description="Pagination info")


# ========== Inventory Schemas ==========

class InventoryItem(BaseModel):
    """User inventory item"""
    id: str = Field(description="Item ID")
    name: str = Field(description="Item name")
    icon_url: str | None = Field(default=None, description="Icon URL")
    item_type: ShopItemType = Field(description="Item type")
    rarity: ItemRarity = Field(description="Item rarity")
    category: str = Field(description="Category")
    quantity: int = Field(default=1, description="Quantity (for consumables)")
    is_equipped: bool = Field(default=False, description="Is equipped")
    expires_at: datetime | None = Field(default=None, description="Expiration time (consumables)")
    item_config: dict[str, Any] | None = Field(default=None, description="Item config")

    model_config = ConfigDict(from_attributes=True)


class InventoryResponse(BaseModel):
    """User inventory response"""
    success: bool = Field(default=True)
    data: dict[str, list[InventoryItem]] = Field(default_factory=dict, description="Inventory grouped by type")
    meta: dict[str, Any] = Field(default_factory=dict, description="Metadata like total counts")


class EquipRequest(BaseModel):
    """Equip item request"""
    item_id: str | None = Field(default=None, description="Item ID to equip (null to unequip)")
    item_type: ShopItemType = Field(description="Item type (skin, title)")

    model_config = ConfigDict(
        json_schema_extra={"example": {"item_id": "skin_galaxy_001", "item_type": "skin"}}
    )


class EquipResponse(BaseModel):
    """Equip item response"""
    success: bool = Field(default=True)
    message: str = Field(description="Success message")
    data: dict[str, Any] = Field(default_factory=dict, description="Equipped item info")


# ========== Consumable Schemas ==========

class UseConsumableRequest(BaseModel):
    """Use consumable request"""
    consumable_id: str = Field(description="Consumable ID to use")
    quantity: int = Field(default=1, ge=1, description="Quantity to use")

    model_config = ConfigDict(
        json_schema_extra={"example": {"consumable_id": "boost_exp_2x_001", "quantity": 1}}
    )


class UseConsumableResponse(BaseModel):
    """Use consumable response"""
    success: bool = Field(default=True)
    message: str = Field(description="Success message")
    data: dict[str, Any] = Field(description="Effect details")
    remaining_quantity: int = Field(description="Remaining quantity")
