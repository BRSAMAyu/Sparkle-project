import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.models.shop import ItemRarity, ShopItem, ShopItemType, ShopPurchase
from app.services.shop_service import ShopService


class _AsyncTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _result_with_scalar(value):
    result = Mock()
    result.scalar_one_or_none.return_value = value
    return result


def _result_with_scalars(values):
    result = Mock()
    result.scalars.return_value.all.return_value = values
    return result


def _build_item(item_id: str | None = None) -> ShopItem:
    item = Mock(spec=ShopItem)
    item.id = item_id or str(uuid4())
    item.name = "Test Item"
    item.description = "desc"
    item.item_type = ShopItemType.CONSUMABLE
    item.category = "boost"
    item.price_photons = 100
    item.original_price = 120
    item.discount_percent = 0
    item.is_available = True
    item.is_limited = False
    item.stock_quantity = 10
    item.icon_url = None
    item.rarity = ItemRarity.COMMON
    item.item_config = {}
    item.sort_order = 1
    item.has_discount = False
    item.is_in_stock = True
    return item


@pytest.mark.asyncio
async def test_get_available_items_returns_mapped_fields():
    db = AsyncMock()
    db.execute.return_value = _result_with_scalars([_build_item()])

    service = ShopService(db)
    items = await service.get_available_items()

    assert len(items) == 1
    assert items[0]["name"] == "Test Item"
    assert items[0]["price_photons"] == 100
    assert items[0]["is_owned"] is False


@pytest.mark.asyncio
async def test_purchase_item_success():
    db = AsyncMock()
    db.begin = Mock(return_value=_AsyncTx())
    db.in_transaction = Mock(return_value=False)
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()

    item = _build_item(item_id=str(uuid4()))
    db.execute.return_value = _result_with_scalar(item)

    with patch("app.core.cache.cache_service") as mock_cache:
        mock_cache.delete = AsyncMock()
        service = ShopService(db)
        service._check_item_ownership = AsyncMock(return_value=False)
        service._grant_item_to_user = AsyncMock()
        service.photon_service._update_balance = AsyncMock(return_value=(300, 200, None))
        service.photon_service.record_transaction = AsyncMock()

        result = await service.purchase_item(str(uuid4()), str(item.id))

    assert result["success"] is True
    assert result["item_id"] == str(item.id)
    service._grant_item_to_user.assert_called_once()
    service.photon_service.record_transaction.assert_called_once()


@pytest.mark.asyncio
async def test_purchase_item_rejects_out_of_stock():
    db = AsyncMock()
    db.begin = Mock(return_value=_AsyncTx())
    db.in_transaction = Mock(return_value=False)
    db.rollback = AsyncMock()

    item = _build_item(item_id=str(uuid4()))
    item.is_limited = True
    item.stock_quantity = 0
    db.execute.return_value = _result_with_scalar(item)

    service = ShopService(db)
    with pytest.raises(ValueError, match="out of stock"):
        await service.purchase_item(str(uuid4()), str(item.id))


@pytest.mark.asyncio
async def test_get_user_purchases_returns_paged_result():
    db = AsyncMock()
    purchase = Mock(spec=ShopPurchase)
    purchase.id = uuid4()
    purchase.item_id = str(uuid4())
    purchase.price_paid = 100
    purchase.photon_balance_before = 200
    purchase.photon_balance_after = 100
    purchase.created_at = None
    purchase.item = _build_item()

    db.execute.side_effect = [
        _result_with_scalars([purchase]),
        Mock(scalar_one=Mock(return_value=1)),
    ]

    service = ShopService(db)
    payload = await service.get_user_purchases(str(uuid4()), limit=10, offset=0)

    assert payload["total_count"] == 1
    assert len(payload["purchases"]) == 1
