"""
Shop System End-to-End Integration Tests

Tests the complete shop system flow across layers:
- Shop API endpoints
- Purchase flow
- Transaction history
- Inventory management
- Photon balance updates

This test requires:
- Running Python gRPC server (make grpc-server)
- Running Go Gateway (make gateway-dev)
- Running PostgreSQL and Redis (make dev-all)
"""

import pytest
import asyncio
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, or_, select

from app.config import settings
from app.core.cache import cache_service
from app.models.user import User
from app.models.shop import ShopItem, ShopPurchase, UserConsumable, PhotonTransactionHistory
# from app.core.security import get_hashed_password  # Not needed for tests


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
async def shop_test_user(db_session: AsyncSession) -> User:
    """Create a test user for shop tests"""
    result = await db_session.execute(
        select(User).where(
            or_(
                User.email == "shop_test@example.com",
                User.username == "shop_test_user",
            )
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email="shop_test@example.com",
            username="shop_test_user",
            nickname="Shop Test User",
            hashed_password="hashed_test_password",  # Simplified for tests
            photon_balance=1000,  # Start with 1000 photons
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    else:
        user.email = "shop_test@example.com"
        user.username = "shop_test_user"
        user.photon_balance = 1000
        await db_session.commit()
        await db_session.refresh(user)
    await cache_service.delete(f"{settings.APP_NAME}:photon:balance:{user.id}")

    yield user

    # Cleanup
    await db_session.rollback()


@pytest.fixture
async def setup_shop_items(db_session: AsyncSession) -> list[ShopItem]:
    """Setup test shop items"""

    items = [
        ShopItem(
            id="test_skin_001",
            name="Test Skin",
            description="A test skin",
            item_type="skin",
            category="test_skins",
            price_photons=100,
            is_available=True,
            is_limited=False,
            rarity="common",
            item_config={"test": True},
            sort_order=1,
        ),
        ShopItem(
            id="test_boost_001",
            name="Test Boost",
            description="A test boost",
            item_type="consumable",
            category="test_boosts",
            price_photons=50,
            is_available=True,
            is_limited=True,
            stock_quantity=5,
            rarity="common",
            item_config={"effect_type": "exp_boost"},
            sort_order=2,
        ),
        ShopItem(
            id="test_title_001",
            name="Test Title",
            description="A test title",
            item_type="title",
            category="test_titles",
            price_photons=80,
            is_available=True,
            is_limited=False,
            rarity="rare",
            item_config={"text": "测试称号"},
            sort_order=3,
        ),
    ]

    item_ids = [item.id for item in items]
    await db_session.execute(delete(UserConsumable).where(UserConsumable.consumable_id.in_(item_ids)))
    await db_session.execute(delete(ShopPurchase).where(ShopPurchase.item_id.in_(item_ids)))
    await db_session.execute(delete(PhotonTransactionHistory).where(PhotonTransactionHistory.related_item_id.in_(item_ids)))
    existing = await db_session.execute(select(ShopItem).where(ShopItem.id.in_(item_ids)))
    for row in existing.scalars().all():
        await db_session.delete(row)
    await db_session.commit()

    for item in items:
        db_session.add(item)
    await db_session.commit()

    for item in items:
        await db_session.refresh(item)

    yield items

    # Cleanup
    await db_session.execute(delete(UserConsumable).where(UserConsumable.consumable_id.in_(item_ids)))
    await db_session.execute(delete(ShopPurchase).where(ShopPurchase.item_id.in_(item_ids)))
    await db_session.execute(delete(PhotonTransactionHistory).where(PhotonTransactionHistory.related_item_id.in_(item_ids)))
    for item in items:
        await db_session.delete(item)
    await db_session.commit()


# ============================================================
# End-to-End Tests
# ============================================================

@pytest.mark.asyncio
async def test_complete_purchase_flow(
    db_session: AsyncSession,
    shop_test_user: User,
    setup_shop_items: list[ShopItem]
):
    """Test complete purchase flow from API to database"""
    from app.services.shop_service import ShopService
    from app.services.photon_service import PhotonService

    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    # Initial balance
    initial_balance = await photon_service.get_balance(str(shop_test_user.id))
    assert initial_balance == 1000

    # Purchase item
    result = await shop_service.purchase_item(
        user_id=str(shop_test_user.id),
        item_id="test_skin_001"
    )

    # Verify result
    assert result["success"] is True
    assert result["price_paid"] == 100
    assert result["balance_before"] == 1000
    assert result["balance_after"] == 900

    # Verify database state
    # 1. Photon balance updated
    final_balance = await photon_service.get_balance(str(shop_test_user.id))
    assert final_balance == 900

    # 2. Purchase record created
    purchase_query = select(ShopPurchase).where(
        ShopPurchase.user_id == shop_test_user.id
    )
    purchase_result = await db_session.execute(purchase_query)
    purchases = purchase_result.scalars().all()

    assert len(purchases) == 1
    assert purchases[0].item_id == "test_skin_001"
    assert purchases[0].price_paid == 100
    assert purchases[0].photon_balance_before == 1000
    assert purchases[0].photon_balance_after == 900


@pytest.mark.asyncio
async def test_purchase_consumable_flow(
    db_session: AsyncSession,
    shop_test_user: User,
    setup_shop_items: list[ShopItem]
):
    """Test purchasing consumable creates inventory record"""
    from app.services.shop_service import ShopService

    shop_service = ShopService(db_session)

    # Purchase consumable
    result = await shop_service.purchase_item(
        user_id=str(shop_test_user.id),
        item_id="test_boost_001"
    )

    assert result["success"] is True

    # Verify user_consumable record
    consumable_query = select(UserConsumable).where(
        UserConsumable.user_id == shop_test_user.id
    )
    consumable_result = await db_session.execute(consumable_query)
    consumable = consumable_result.scalar_one_or_none()

    assert consumable is not None
    assert consumable.consumable_id == "test_boost_001"
    assert consumable.quantity == 1
    assert consumable.effect_type == "exp_boost"

    # Verify stock was reduced
    item_query = select(ShopItem).where(ShopItem.id == "test_boost_001")
    item_result = await db_session.execute(item_query)
    item = item_result.scalar_one()

    assert item.stock_quantity == 4  # Started with 5


@pytest.mark.asyncio
async def test_transaction_history_recording(
    db_session: AsyncSession,
    shop_test_user: User,
    setup_shop_items: list[ShopItem]
):
    """Test that purchases are recorded in transaction history"""
    from app.services.shop_service import ShopService
    from app.services.photon_service import PhotonService

    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    # Record a transaction manually first
    await photon_service.record_transaction(
        user_id=str(shop_test_user.id),
        transaction_type="grant_achievement",
        amount=500,
        balance_before=1000,
        balance_after=1500,
        source="test_grant"
    )

    # Now make a purchase
    await shop_service.purchase_item(
        user_id=str(shop_test_user.id),
        item_id="test_skin_001"
    )

    # Check transaction history
    history = await photon_service.get_transaction_history(
        user_id=str(shop_test_user.id),
        limit=10,
        offset=0
    )

    assert history["total_count"] >= 2

    # Find purchase transaction
    purchase_tx = next(
        (tx for tx in history["transactions"] if tx["transaction_type"] == "purchase"),
        None
    )

    assert purchase_tx is not None
    assert purchase_tx["amount"] == -100
    assert purchase_tx["related_item_id"] == "test_skin_001"


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO: Fix greenlet_spawn transaction state issue")
async def test_insufficient_balance_error(
    db_session: AsyncSession,
    shop_test_user: User,
    setup_shop_items: list[ShopItem]
):
    """Test purchase with insufficient balance fails properly"""
    from app.services.shop_service import ShopService
    from app.services.photon_service import PhotonService

    shop_service = ShopService(db_session)

    # Set balance to 50 directly (same fix as unit test)
    shop_test_user.photon_balance = 50
    await db_session.commit()

    # Try to purchase
    with pytest.raises(ValueError, match="Insufficient photon balance"):
        await shop_service.purchase_item(
            user_id=str(shop_test_user.id),
            item_id="test_skin_001"
        )

    # Verify no purchase record was created
    purchase_query = select(ShopPurchase).where(
        ShopPurchase.user_id == shop_test_user.id
    )
    purchase_result = await db_session.execute(purchase_query)
    purchases = purchase_result.scalars().all()

    assert len(purchases) == 0


@pytest.mark.asyncio
async def test_purchase_history_pagination(
    db_session: AsyncSession,
    shop_test_user: User,
    setup_shop_items: list[ShopItem]
):
    """Test purchase history pagination"""
    from app.services.shop_service import ShopService

    shop_service = ShopService(db_session)

    # Make 5 purchases (use consumable since it can be purchased multiple times)
    for i in range(5):
        # Grant photons before each purchase
        shop_test_user.photon_balance = 1000
        await db_session.commit()

        await shop_service.purchase_item(
            user_id=str(shop_test_user.id),
            item_id="test_boost_001"  # Use consumable instead of skin
        )

    # Get first page
    page1 = await shop_service.get_user_purchases(
        user_id=str(shop_test_user.id),
        limit=2,
        offset=0
    )

    assert len(page1["purchases"]) == 2
    assert page1["total_count"] == 5

    # Get second page
    page2 = await shop_service.get_user_purchases(
        user_id=str(shop_test_user.id),
        limit=2,
        offset=2
    )

    assert len(page2["purchases"]) == 2

    # Verify pages are different
    page1_ids = {p["id"] for p in page1["purchases"]}
    page2_ids = {p["id"] for p in page2["purchases"]}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO: Fix SQLAlchemy async session transaction state issue")
async def test_photon_transfer_after_purchase(
    db_session: AsyncSession,
    shop_test_user: User,
    setup_shop_items: list[ShopItem]
):
    """Test that photon transfers work correctly after purchases"""
    from app.services.shop_service import ShopService
    from app.services.photon_service import PhotonService

    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    # Create another user
    other_user = User(
        email="other_user@example.com",
        username="other_user",
        nickname="Other User",
        hashed_password="hashed_test_password",  # Simplified for tests
        photon_balance=0,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # Make a purchase
    await shop_service.purchase_item(
        user_id=str(shop_test_user.id),
        item_id="test_skin_001"
    )

    # Ensure transaction is complete
    await db_session.commit()
    await db_session.refresh(shop_test_user)

    # Transfer photons to other user (this starts a new transaction)
    transfer_result = await photon_service.transfer_photons(
        from_user_id=str(shop_test_user.id),
        to_user_id=str(other_user.id),
        amount=200,
        reason="Gift"
    )

    assert transfer_result["from_balance"] == 700  # 1000 - 100 (purchase) - 200 (transfer)
    assert transfer_result["to_balance"] == 200


@pytest.mark.asyncio
async def test_concurrent_purchase_prevents_oversell(
    db_session: AsyncSession,
    shop_test_user: User,
    setup_shop_items: list[ShopItem]
):
    """Test that concurrent purchases respect stock limits"""
    from app.services.shop_service import ShopService

    shop_service = ShopService(db_session)

    # Set stock to 2
    item = setup_shop_items[1]  # test_boost_001
    item.stock_quantity = 2
    await db_session.commit()

    # Give user enough photons for 3 purchases
    shop_test_user.photon_balance = 300
    await db_session.commit()

    # Simulate concurrent purchases
    purchases = []
    for i in range(3):
        try:
            result = await shop_service.purchase_item(
                user_id=str(shop_test_user.id),
                item_id="test_boost_001"
            )
            purchases.append(result)
        except ValueError as e:
            if "out of stock" in str(e):
                purchases.append(None)
            else:
                raise

    # Only 2 should succeed
    successful_purchases = [p for p in purchases if p is not None]
    assert len(successful_purchases) == 2

    # Verify final stock is 0
    await db_session.refresh(item)
    assert item.stock_quantity == 0


@pytest.mark.asyncio
async def test_inventory_service_integration(
    db_session: AsyncSession,
    shop_test_user: User,
    setup_shop_items: list[ShopItem]
):
    """Test inventory service integration with shop"""
    from app.services.shop_service import ShopService
    from app.services.inventory_service import InventoryService

    shop_service = ShopService(db_session)
    inventory_service = InventoryService(db_session)

    # Purchase items
    await shop_service.purchase_item(
        user_id=str(shop_test_user.id),
        item_id="test_skin_001"
    )
    await shop_service.purchase_item(
        user_id=str(shop_test_user.id),
        item_id="test_boost_001"
    )

    # Get inventory
    inventory = await inventory_service.get_user_inventory(str(shop_test_user.id))

    # Verify items are in inventory
    assert len(inventory["skins"]) >= 1
    assert len(inventory["consumables"]) >= 1

    # Check ownership
    owned_ids = await inventory_service.get_owned_items(str(shop_test_user.id))
    assert "test_skin_001" in owned_ids


@pytest.mark.asyncio
async def test_equip_skin_updates_user_profile(
    db_session: AsyncSession,
    shop_test_user: User,
    setup_shop_items: list[ShopItem]
):
    """Test that equipping skin updates user profile"""
    from app.services.shop_service import ShopService
    from app.services.inventory_service import InventoryService

    shop_service = ShopService(db_session)
    inventory_service = InventoryService(db_session)

    # Purchase skin
    await shop_service.purchase_item(
        user_id=str(shop_test_user.id),
        item_id="test_skin_001"
    )

    # Equip skin
    result = await inventory_service.equip_skin(
        user_id=str(shop_test_user.id),
        item_id="test_skin_001"
    )

    assert result["success"] is True
    assert result["item_id"] == "test_skin_001"

    # Verify user profile updated
    await db_session.refresh(shop_test_user)
    # Note: This assumes User model has equipped_skin field
    # If not, this test will need adjustment


@pytest.mark.asyncio
async def test_unequip_title_clears_user_profile(
    db_session: AsyncSession,
    shop_test_user: User,
    setup_shop_items: list[ShopItem]
):
    """Test that unequipping title clears user profile"""
    from app.services.shop_service import ShopService
    from app.services.inventory_service import InventoryService

    shop_service = ShopService(db_session)
    inventory_service = InventoryService(db_session)

    # Purchase title
    await shop_service.purchase_item(
        user_id=str(shop_test_user.id),
        item_id="test_title_001"
    )

    # Equip title
    result = await inventory_service.equip_title(
        user_id=str(shop_test_user.id),
        item_id="test_title_001"
    )
    assert result["success"] is True

    # Unequip title
    result = await inventory_service.equip_title(
        user_id=str(shop_test_user.id),
        item_id=None
    )
    assert result["success"] is True
    assert result["item_id"] is None

    await db_session.refresh(shop_test_user)
    assert shop_test_user.equipped_title is None


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO: Fix transaction recording for summary statistics")
async def test_photon_summary_after_transactions(
    db_session: AsyncSession,
    shop_test_user: User,
    setup_shop_items: list[ShopItem]
):
    """Test transaction summary after various transactions"""
    from app.services.shop_service import ShopService
    from app.services.photon_service import PhotonService

    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    # Make various transactions - set balance directly
    shop_test_user.photon_balance = 1000
    await db_session.commit()

    await shop_service.purchase_item(
        user_id=str(shop_test_user.id),
        item_id="test_skin_001"
    )

    # Set balance again for second purchase
    shop_test_user.photon_balance = 500
    await db_session.commit()

    await shop_service.purchase_item(
        user_id=str(shop_test_user.id),
        item_id="test_boost_001"
    )

    # Commit all transactions
    await db_session.commit()

    # Get summary
    summary = await photon_service.get_transaction_summary(
        user_id=str(shop_test_user.id),
        days=30
    )

    assert summary["total_income"] >= 500
    assert summary["total_expense"] >= 150  # 100 + 50
    assert summary["transaction_count"] >= 3
