"""
Shop Service Unit Tests

Tests the core business logic of the shop system:
- Purchase flow with sufficient balance
- Purchase with insufficient balance
- Out-of-stock handling
- Discount calculation
- Transaction history recording
- Item ownership checking
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.shop_service import ShopService
from app.services.photon_service import PhotonService
from app.models.shop import ShopItem, ShopPurchase, UserConsumable, ShopItemType
from app.models.user import User


@pytest.fixture
async def test_shop_items(db_session: AsyncSession) -> list[ShopItem]:
    """Create test shop items"""
    items = [
        ShopItem(
            id="skin_common_001",
            name="Common Skin",
            description="A common skin",
            item_type=ShopItemType.SKIN,
            category="skins",
            price_photons=100,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://example.com/skin.png",
            rarity="common",
            item_config={"skin_id": "skin_001"},
            sort_order=1,
        ),
        ShopItem(
            id="skin_rare_001",
            name="Rare Skin",
            description="A rare skin with discount",
            item_type=ShopItemType.SKIN,
            category="skins",
            price_photons=400,
            original_price=500,
            discount_percent=20,
            is_available=True,
            is_limited=False,
            icon_url="https://example.com/skin_rare.png",
            rarity="rare",
            item_config={"skin_id": "skin_002"},
            sort_order=2,
        ),
        ShopItem(
            id="consumable_boost_001",
            name="EXP Boost",
            description="2x experience for 24 hours",
            item_type=ShopItemType.CONSUMABLE,
            category="boosts",
            price_photons=50,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=True,
            stock_quantity=10,
            icon_url="https://example.com/boost.png",
            rarity="common",
            item_config={"effect_type": "exp_boost", "duration_hours": 24},
            sort_order=3,
        ),
        ShopItem(
            id="title_legendary_001",
            name="Legendary Title",
            description="A legendary title",
            item_type=ShopItemType.TITLE,
            category="titles",
            price_photons=1000,
            original_price=None,
            discount_percent=None,
            is_available=True,
            is_limited=False,
            icon_url="https://example.com/title.png",
            rarity="legendary",
            item_config={"text": "Legend"},
            sort_order=4,
        ),
    ]

    for item in items:
        db_session.add(item)
    await db_session.commit()

    for item in items:
        await db_session.refresh(item)

    return items


@pytest.mark.asyncio
async def test_get_available_items(
    db_session: AsyncSession,
    test_user: User,
    test_shop_items: list[ShopItem]
):
    """Test retrieving available shop items"""
    service = ShopService(db_session)

    # Get all items
    items = await service.get_available_items(user_id=str(test_user.id))

    assert len(items) == 4
    assert items[0]["id"] == "skin_common_001"
    assert items[1]["id"] == "skin_rare_001"


@pytest.mark.asyncio
async def test_get_available_items_with_type_filter(
    db_session: AsyncSession,
    test_user: User,
    test_shop_items: list[ShopItem]
):
    """Test filtering items by type"""
    service = ShopService(db_session)

    # Get only skins
    skins = await service.get_available_items(
        item_type=ShopItemType.SKIN,
        user_id=str(test_user.id)
    )

    assert len(skins) == 2
    assert all(item["item_type"] == ShopItemType.SKIN for item in skins)


@pytest.mark.asyncio
async def test_purchase_item_success(
    db_session: AsyncSession,
    test_user: User,
    test_shop_items: list[ShopItem]
):
    """Test successful item purchase with sufficient balance"""
    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    # Grant user 500 photons
    await photon_service.grant_photons(
        user_id=str(test_user.id),
        amount=500,
        source="test_grant"
    )

    # Purchase item costing 100 photons
    result = await shop_service.purchase_item(
        user_id=str(test_user.id),
        item_id="skin_common_001"
    )

    assert result["success"] is True
    assert result["price_paid"] == 100
    assert result["balance_before"] == 500
    assert result["balance_after"] == 400
    assert result["item_id"] == "skin_common_001"

    # Verify purchase record was created
    purchases_query = select(ShopPurchase).where(
        ShopPurchase.user_id == test_user.id
    )
    purchases_result = await db_session.execute(purchases_query)
    purchases = purchases_result.scalars().all()

    assert len(purchases) == 1
    assert purchases[0].item_id == "skin_common_001"
    assert purchases[0].price_paid == 100

    # Verify photon balance was deducted
    balance = await photon_service.get_balance(str(test_user.id))
    assert balance == 400


@pytest.mark.asyncio
async def test_purchase_item_insufficient_balance(
    db_session: AsyncSession,
    test_user: User,
    test_shop_items: list[ShopItem]
):
    """Test purchase with insufficient balance"""
    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    # Grant user only 50 photons
    await photon_service.grant_photons(
        user_id=str(test_user.id),
        amount=50,
        source="test_grant"
    )

    # Try to purchase item costing 100 photons
    with pytest.raises(ValueError, match="Insufficient photon balance"):
        await shop_service.purchase_item(
            user_id=str(test_user.id),
            item_id="skin_common_001"
        )

    # Verify balance was not deducted
    balance = await photon_service.get_balance(str(test_user.id))
    assert balance == 50


@pytest.mark.asyncio
async def test_purchase_item_out_of_stock(
    db_session: AsyncSession,
    test_user: User,
    test_shop_items: list[ShopItem]
):
    """Test purchase of out-of-stock limited item"""
    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    # Set stock to 0
    item = test_shop_items[2]  # consumable_boost_001
    item.stock_quantity = 0
    await db_session.commit()

    # Grant user enough photons
    await photon_service.grant_photons(
        user_id=str(test_user.id),
        amount=500,
        source="test_grant"
    )

    # Try to purchase out-of-stock item
    with pytest.raises(ValueError, match="out of stock"):
        await shop_service.purchase_item(
            user_id=str(test_user.id),
            item_id="consumable_boost_001"
        )


@pytest.mark.asyncio
async def test_purchase_consumable_creates_user_consumable(
    db_session: AsyncSession,
    test_user: User,
    test_shop_items: list[ShopItem]
):
    """Test that purchasing consumable creates user_consumable record"""
    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    # Grant user 200 photons
    await photon_service.grant_photons(
        user_id=str(test_user.id),
        amount=200,
        source="test_grant"
    )

    # Purchase consumable
    await shop_service.purchase_item(
        user_id=str(test_user.id),
        item_id="consumable_boost_001"
    )

    # Verify user_consumable was created
    consumable_query = select(UserConsumable).where(
        UserConsumable.user_id == test_user.id
    )
    consumable_result = await db_session.execute(consumable_query)
    consumable = consumable_result.scalar_one_or_none()

    assert consumable is not None
    assert consumable.consumable_id == "consumable_boost_001"
    assert consumable.quantity == 1


@pytest.mark.asyncio
async def test_purchase_already_owned_item(
    db_session: AsyncSession,
    test_user: User,
    test_shop_items: list[ShopItem]
):
    """Test that purchasing an already owned skin fails"""
    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    # Grant user 500 photons
    await photon_service.grant_photons(
        user_id=str(test_user.id),
        amount=500,
        source="test_grant"
    )

    # First purchase should succeed
    await shop_service.purchase_item(
        user_id=str(test_user.id),
        item_id="skin_common_001"
    )

    # Second purchase should fail (already owned)
    with pytest.raises(ValueError, match="already owns"):
        await shop_service.purchase_item(
            user_id=str(test_user.id),
            item_id="skin_common_001"
        )


@pytest.mark.asyncio
async def test_purchase_reduces_limited_item_stock(
    db_session: AsyncSession,
    test_user: User,
    test_shop_items: list[ShopItem]
):
    """Test that purchasing limited item reduces stock"""
    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    item = test_shop_items[2]  # consumable_boost_001
    initial_stock = item.stock_quantity

    # Grant user enough photons
    await photon_service.grant_photons(
        user_id=str(test_user.id),
        amount=500,
        source="test_grant"
    )

    # Purchase item
    await shop_service.purchase_item(
        user_id=str(test_user.id),
        item_id="consumable_boost_001"
    )

    # Refresh item from DB
    await db_session.refresh(item)

    # Verify stock was reduced
    assert item.stock_quantity == initial_stock - 1


@pytest.mark.asyncio
async def test_get_purchase_history(
    db_session: AsyncSession,
    test_user: User,
    test_shop_items: list[ShopItem]
):
    """Test retrieving user purchase history"""
    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    # Grant photons
    await photon_service.grant_photons(
        user_id=str(test_user.id),
        amount=1000,
        source="test_grant"
    )

    # Make 3 purchases
    await shop_service.purchase_item(
        user_id=str(test_user.id),
        item_id="skin_common_001"
    )
    await shop_service.purchase_item(
        user_id=str(test_user.id),
        item_id="skin_rare_001"
    )
    await shop_service.purchase_item(
        user_id=str(test_user.id),
        item_id="consumable_boost_001"
    )

    # Get purchase history
    history = await shop_service.get_user_purchases(
        user_id=str(test_user.id),
        limit=10,
        offset=0
    )

    assert history["total_count"] == 3
    assert len(history["purchases"]) == 3
    assert history["purchases"][0]["item_name"] == "Common Skin"
    assert history["purchases"][1]["item_name"] == "Rare Skin"
    assert history["purchases"][2]["item_name"] == "EXP Boost"


@pytest.mark.asyncio
async def test_get_purchase_history_pagination(
    db_session: AsyncSession,
    test_user: User,
    test_shop_items: list[ShopItem]
):
    """Test purchase history pagination"""
    shop_service = ShopService(db_session)
    photon_service = PhotonService(db_session)

    # Grant photons
    await photon_service.grant_photons(
        user_id=str(test_user.id),
        amount=5000,
        source="test_grant"
    )

    # Make 5 purchases
    for _ in range(5):
        await shop_service.purchase_item(
            user_id=str(test_user.id),
            item_id="skin_common_001"
        )

    # Get first page
    page1 = await shop_service.get_user_purchases(
        user_id=str(test_user.id),
        limit=2,
        offset=0
    )
    assert len(page1["purchases"]) == 2

    # Get second page
    page2 = await shop_service.get_user_purchases(
        user_id=str(test_user.id),
        limit=2,
        offset=2
    )
    assert len(page2["purchases"]) == 2

    # Get third page (1 item)
    page3 = await shop_service.get_user_purchases(
        user_id=str(test_user.id),
        limit=2,
        offset=4
    )
    assert len(page3["purchases"]) == 1


@pytest.mark.asyncio
async def test_check_item_ownership_for_consumable(
    db_session: AsyncSession,
    test_user: User,
    test_shop_items: list[ShopItem]
):
    """Test checking if user owns consumable"""
    service = ShopService(db_session)

    # Initially should not own
    owned = await service._check_item_ownership(
        user_id=str(test_user.id),
        item_id="consumable_boost_001",
        item_type=ShopItemType.CONSUMABLE
    )
    assert owned is False


@pytest.mark.asyncio
async def test_get_item_by_id(
    db_session: AsyncSession,
    test_shop_items: list[ShopItem]
):
    """Test retrieving item by ID"""
    service = ShopService(db_session)

    item = await service.get_item_by_id("skin_common_001")

    assert item is not None
    assert item.id == "skin_common_001"
    assert item.name == "Common Skin"
    assert item.price_photons == 100


@pytest.mark.asyncio
async def test_get_item_by_id_not_found(
    db_session: AsyncSession
):
    """Test retrieving non-existent item"""
    service = ShopService(db_session)

    item = await service.get_item_by_id("nonexistent_item")

    assert item is None
