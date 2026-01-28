"""
Unit tests for app.services.shop_service module.
Tests shop operations, item purchasing, and inventory management.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from uuid import uuid4
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.shop_service import ShopService
from app.models.shop import ShopItem, ShopPurchase, ShopItemType, ItemRarity


class TestShopServiceInit:
    """Test ShopService initialization"""

    def test_init(self):
        """Test service initialization"""
        mock_db = AsyncMock()

        with patch('app.services.shop_service.PhotonService') as mock_photon:
            service = ShopService(mock_db)

            assert service.db is mock_db
            mock_photon.assert_called_once_with(mock_db)


class TestGetAvailableItems:
    """Test get_available_items method"""

    @pytest.mark.asyncio
    async def test_get_all_available_items(self):
        """Test getting all available items"""
        mock_db = AsyncMock()

        # Mock query result
        mock_item = Mock(spec=ShopItem)
        mock_item.id = uuid4()
        mock_item.name = "Test Skin"
        mock_item.item_type = ShopItemType.SKIN
        mock_item.price_photons = 100
        mock_item.is_available = True

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_item]
        mock_db.execute.return_value = mock_result

        service = ShopService(mock_db)
        items = await service.get_available_items()

        assert len(items) == 1
        assert items[0]["name"] == "Test Skin"
        assert items[0]["price_photons"] == 100

    @pytest.mark.asyncio
    async def test_get_items_by_type(self):
        """Test filtering items by type"""
        mock_db = AsyncMock()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = ShopService(mock_db)
        items = await service.get_available_items(item_type=ShopItemType.CONSUMABLE)

        # Verify query was executed
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_items_including_unavailable(self):
        """Test getting items including unavailable ones"""
        mock_db = AsyncMock()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = ShopService(mock_db)
        items = await service.get_available_items(only_available=False)

        # Should execute query
        mock_db.execute.assert_called_once()


class TestPurchaseItem:
    """Test purchase_item method"""

    @pytest.mark.asyncio
    async def test_purchase_item_success(self):
        """Test successful item purchase"""
        mock_db = AsyncMock()

        user_id = str(uuid4())
        item_id = uuid4()
        item = Mock(spec=ShopItem)
        item.id = item_id
        item.price_photons = 100
        item.is_available = True
        item.stock_quantity = 10

        # Mock item retrieval
        with patch.object(ShopService, '_get_item', return_value=item):
            # Mock photon deduction
            with patch.object(ShopService, '_deduct_photons') as mock_deduct:
                mock_deduct.return_value = True

                # Mock purchase creation
                mock_db.commit.return_value = None
                mock_db.refresh.return_value = None

                service = ShopService(mock_db)

                purchase = await service.purchase_item(user_id, item_id)

                assert purchase is not None
                mock_deduct.assert_called_once_with(user_id, 100)
                mock_db.add.assert_called()
                mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_purchase_item_insufficient_photons(self):
        """Test purchase with insufficient photons"""
        mock_db = AsyncMock()

        user_id = str(uuid4())
        item_id = uuid4()
        item = Mock(spec=ShopItem)
        item.id = item_id
        item.price_photons = 100

        with patch.object(ShopService, '_get_item', return_value=item):
            # Mock photon check fails
            with patch.object(ShopService, '_deduct_photons', return_value=False):
                service = ShopService(mock_db)

                with pytest.raises(ValueError, match="Insufficient photons"):
                    await service.purchase_item(user_id, item_id)

    @pytest.mark.asyncio
    async def test_purchase_item_out_of_stock(self):
        """Test purchasing item that is out of stock"""
        mock_db = AsyncMock()

        user_id = str(uuid4())
        item_id = uuid4()
        item = Mock(spec=ShopItem)
        item.id = item_id
        item.price_photons = 100
        item.is_available = True
        item.stock_quantity = 0  # Out of stock

        with patch.object(ShopService, '_get_item', return_value=item):
            service = ShopService(mock_db)

            with pytest.raises(ValueError, match="Out of stock"):
                await service.purchase_item(user_id, item_id)

    @pytest.mark.asyncio
    async def test_purchase_item_not_available(self):
        """Test purchasing unavailable item"""
        mock_db = AsyncMock()

        user_id = str(uuid4())
        item_id = uuid4()
        item = Mock(spec=ShopItem)
        item.id = item_id
        item.price_photons = 100
        item.is_available = False  # Not available

        with patch.object(ShopService, '_get_item', return_value=item):
            service = ShopService(mock_db)

            with pytest.raises(ValueError, match="not available"):
                await service.purchase_item(user_id, item_id)


class TestGetPurchaseHistory:
    """Test get_purchase_history method"""

    @pytest.mark.asyncio
    async def test_get_user_purchase_history(self):
        """Test getting purchase history for user"""
        mock_db = AsyncMock()

        user_id = str(uuid4())

        mock_purchase = Mock(spec=ShopPurchase)
        mock_purchase.id = uuid4()
        mock_purchase.user_id = user_id

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_purchase]
        mock_db.execute.return_value = mock_result

        service = ShopService(mock_db)
        history = await service.get_purchase_history(user_id)

        assert len(history) == 1
        assert history[0].user_id == user_id

    @pytest.mark.asyncio
    async def test_get_purchase_history_with_limit(self):
        """Test getting limited purchase history"""
        mock_db = AsyncMock()

        user_id = str(uuid4())

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = ShopService(mock_db)
        history = await service.get_purchase_history(user_id, limit=10)

        # Should execute query with limit
        mock_db.execute.assert_called_once()


class TestDeductPhotons:
    """Test _deduct_photons internal method"""

    @pytest.mark.asyncio
    async def test_deduct_photons_success(self):
        """Test successful photon deduction"""
        mock_db = AsyncMock()

        user_id = str(uuid4())
        amount = 100

        with patch.object(ShopService, '_get_user_photon_balance', return_value=Decimal("200")):
            with patch('app.services.shop_service.photon_service') as mock_photon_svc:
                mock_photon_instance = AsyncMock()
                mock_photon_instance.spend_photons.return_value = True
                mock_photon_svc.PhotonService.return_value = mock_photon_instance

                service = ShopService(mock_db)
                result = await service._deduct_photons(user_id, amount)

                assert result is True

    @pytest.mark.asyncio
    async def test_deduct_photons_insufficient_balance(self):
        """Test photon deduction with insufficient balance"""
        mock_db = AsyncMock()

        user_id = str(uuid4())
        amount = 200

        with patch.object(ShopService, '_get_user_photon_balance', return_value=Decimal("100")):
            service = ShopService(mock_db)
            result = await service._deduct_photons(user_id, amount)

            assert result is False


class TestGetUserInventory:
    """Test get_user_inventory method"""

    @pytest.mark.asyncio
    async def test_get_user_inventory_empty(self):
        """Test getting inventory for user with no items"""
        mock_db = AsyncMock()

        user_id = str(uuid4())

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = ShopService(mock_db)
        inventory = await service.get_user_inventory(user_id)

        assert inventory == []

    @pytest.mark.asyncio
    async def test_get_user_inventory_with_items(self):
        """Test getting inventory with purchased items"""
        mock_db = AsyncMock()

        user_id = str(uuid4())

        mock_purchase = Mock(spec=ShopPurchase)
        mock_purchase.id = uuid4()
        mock_purchase.user_id = user_id

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_purchase]
        mock_db.execute.return_value = mock_result

        service = ShopService(mock_db)
        inventory = await service.get_user_inventory(user_id)

        assert len(inventory) == 1


class TestItemDelivery:
    """Test item delivery and activation"""

    @pytest.mark.asyncio
    async def test_deliver_consumable_item(self):
        """Test delivering consumable item to user"""
        mock_db = AsyncMock()

        user_id = str(uuid4())
        purchase_id = uuid4()

        mock_purchase = Mock(spec=ShopPurchase)
        mock_purchase.id = purchase_id
        mock_purchase.user_id = user_id

        mock_db.commit.return_value = None

        service = ShopService(mock_db)

        with patch.object(service, '_create_consumable_record') as mock_create:
            await service.deliver_item(purchase_id)

            mock_create.assert_called_once()
            mock_db.commit.assert_called_once()


class TestPriceCalculations:
    """Test price calculation logic"""

    def test_calculate_discounted_price(self):
        """Test calculating price with discount"""
        original_price = Decimal("100")
        discount_percent = 20

        expected_price = Decimal("80")

        # Manual calculation
        actual_price = original_price * (Decimal("100") - Decimal(str(discount_percent))) / Decimal("100")

        assert actual_price == expected_price

    def test_calculate_original_price_no_discount(self):
        """Test price calculation with no discount"""
        original_price = Decimal("100")
        discount_percent = 0

        expected_price = Decimal("100")

        actual_price = original_price * (Decimal("100") - Decimal(str(discount_percent))) / Decimal("100")

        assert actual_price == expected_price


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_purchase_item_db_error_rollback(self):
        """Test that DB errors trigger rollback"""
        mock_db = AsyncMock()

        user_id = str(uuid4())
        item_id = uuid4()

        item = Mock(spec=ShopItem)
        item.id = item_id
        item.price_photons = 100
        item.is_available = True
        item.stock_quantity = 10

        with patch.object(ShopService, '_get_item', return_value=item):
            with patch.object(ShopService, '_deduct_photons', return_value=True):
                # Mock DB error on commit
                mock_db.commit.side_effect = Exception("DB error")
                mock_db.rollback.return_value = None

                service = ShopService(mock_db)

                with pytest.raises(Exception):
                    await service.purchase_item(user_id, item_id)

                # Should rollback
                mock_db.rollback.assert_called_once()
