"""PHOTON-TUNE · 商城消耗品真实接线（D-MONETIZE 审计 §1.6-4/R4）。

审计背景：use_consumable 五类效果全是桩（TRACKED(TD-006)）——「已展示
可兑换但后端未发货」。本卡接线 streak_freeze（唯一有真实消费点的效果：
user_streak_stats.freeze_charges，断连保护据此扣卡），并把数量扣减改为
原子条件 UPDATE（并发双用不再双发货）。

hint_reveal 等四类裁决不接线：后端无对应消费系统，发货面=造假——
桩保留并在交付报告登记（下架属产品裁决，不在本卡）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.achievement import UserStreakStats
from app.models.shop import ShopItem, UserConsumable
from app.services.inventory_service import InventoryService


def _freeze_item() -> ShopItem:
    return ShopItem(
        id="tune_streak_freeze_001",
        name="连击冻结卡（测试）",
        description="PHOTON-TUNE wiring test",
        item_type="boost",
        category="streak_protection",
        price_photons=150,
        is_available=True,
        is_limited=False,
        item_config={"effect_type": "streak_freeze", "charges": 1},
        sort_order=99,
    )


@pytest.mark.asyncio
async def test_streak_freeze_consumable_actually_delivers_charges(db_session, test_user):
    """发货真实性：使用后 freeze_charges 真实 +1（写入断连保护的消费面）。"""
    db_session.add(_freeze_item())
    db_session.add(
        UserConsumable(
            id=str(uuid4()),
            user_id=test_user.id,
            consumable_id="tune_streak_freeze_001",
            effect_type="streak_freeze",
            quantity=2,
        )
    )
    db_session.add(
        UserStreakStats(user_id=test_user.id, freeze_charges=1, max_freeze_charges=3)
    )
    await db_session.commit()

    service = InventoryService(db_session)
    result = await service.use_consumable(str(test_user.id), "tune_streak_freeze_001", quantity=1)

    assert result["success"] is True
    assert result["effect_result"]["effect"] == "streak_freeze"
    assert result["effect_result"]["charges_added"] == 1
    assert result["effect_result"]["charges_capped"] is False
    assert result["remaining_quantity"] == 1

    stats = (
        await db_session.execute(
            select(UserStreakStats).where(UserStreakStats.user_id == test_user.id)
        )
    ).scalar_one()
    assert stats.freeze_charges == 2


@pytest.mark.asyncio
async def test_streak_freeze_delivery_caps_at_max_charges(db_session, test_user):
    """上限纪律：与成就 freeze_charge 奖励同式 min(+q, max)，诚实回报实发。"""
    db_session.add(_freeze_item())
    db_session.add(
        UserConsumable(
            id=str(uuid4()),
            user_id=test_user.id,
            consumable_id="tune_streak_freeze_001",
            effect_type="streak_freeze",
            quantity=3,
        )
    )
    db_session.add(
        UserStreakStats(user_id=test_user.id, freeze_charges=2, max_freeze_charges=3)
    )
    await db_session.commit()

    service = InventoryService(db_session)
    result = await service.use_consumable(str(test_user.id), "tune_streak_freeze_001", quantity=2)

    assert result["effect_result"]["charges_added"] == 1
    assert result["effect_result"]["charges_capped"] is True
    assert result["effect_result"]["freeze_charges"] == 3

    stats = (
        await db_session.execute(
            select(UserStreakStats).where(UserStreakStats.user_id == test_user.id)
        )
    ).scalar_one()
    assert stats.freeze_charges == 3
    # 卡照实扣（用户用了 2 张，其中 1 张被上限吃掉——如实扣减不退）
    assert result["remaining_quantity"] == 1


@pytest.mark.asyncio
async def test_streak_freeze_creates_stats_when_missing(db_session, test_user):
    """无连胜记录的用户使用：建档并发货（不静默丢效果）。"""
    db_session.add(_freeze_item())
    db_session.add(
        UserConsumable(
            id=str(uuid4()),
            user_id=test_user.id,
            consumable_id="tune_streak_freeze_001",
            effect_type="streak_freeze",
            quantity=1,
        )
    )
    await db_session.commit()

    service = InventoryService(db_session)
    result = await service.use_consumable(str(test_user.id), "tune_streak_freeze_001", quantity=1)

    assert result["effect_result"]["charges_added"] >= 1
    stats = (
        await db_session.execute(
            select(UserStreakStats).where(UserStreakStats.user_id == test_user.id)
        )
    ).scalar_one()
    assert stats.freeze_charges >= 1


@pytest.mark.asyncio
async def test_insufficient_quantity_atomic_no_delivery(db_session, test_user):
    """原子扣减：数量不足直接拒绝，效果零发货（旧路径可被并发击穿）。"""
    db_session.add(_freeze_item())
    db_session.add(
        UserConsumable(
            id=str(uuid4()),
            user_id=test_user.id,
            consumable_id="tune_streak_freeze_001",
            effect_type="streak_freeze",
            quantity=1,
        )
    )
    db_session.add(
        UserStreakStats(user_id=test_user.id, freeze_charges=1, max_freeze_charges=3)
    )
    await db_session.commit()

    service = InventoryService(db_session)
    with pytest.raises(ValueError, match="Insufficient consumable quantity"):
        await service.use_consumable(str(test_user.id), "tune_streak_freeze_001", quantity=2)

    stats = (
        await db_session.execute(
            select(UserStreakStats).where(UserStreakStats.user_id == test_user.id)
        )
    ).scalar_one()
    assert stats.freeze_charges == 1  # 效果未发货

    consumable = (
        await db_session.execute(
            select(UserConsumable).where(
                UserConsumable.user_id == test_user.id,
                UserConsumable.consumable_id == "tune_streak_freeze_001",
            )
        )
    ).scalar_one()
    assert consumable.quantity == 1  # 库存未动


# ── V3-FIX-457：发货路径首建并发+无锁读改写（451 三件套同构）────────────────


@pytest.mark.asyncio
async def test_streak_freeze_firstbuild_id_deterministic_shared_with_engine(db_session, test_user):
    """首建 id=uuid5 确定性派生，且与 achievement_engine 451 派生同一字符串——
    复合主键 (user_id,id) 依赖两侧 id 相等仲裁 inventory↔engine 跨路径并发
    首建（真 PG 双连接实证见 v3-output/WT742-INV457/）。"""
    from uuid import NAMESPACE_URL, uuid5

    db_session.add(_freeze_item())
    db_session.add(
        UserConsumable(
            id=str(uuid4()),
            user_id=test_user.id,
            consumable_id="tune_streak_freeze_001",
            effect_type="streak_freeze",
            quantity=1,
        )
    )
    await db_session.commit()

    service = InventoryService(db_session)
    result = await service.use_consumable(str(test_user.id), "tune_streak_freeze_001", quantity=1)

    assert result["effect_result"]["effect"] == "streak_freeze"
    stats = (
        await db_session.execute(
            select(UserStreakStats).where(UserStreakStats.user_id == test_user.id)
        )
    ).scalar_one()  # 单行；随机 id 旧形态在 PG 下双行此处 MultipleResultsFound
    expected_id = uuid5(NAMESPACE_URL, f"achievement-streak-stats:{str(test_user.id)}")
    assert stats.id == expected_id


@pytest.mark.asyncio
async def test_streak_freeze_firstbuild_then_engine_reads_same_row(db_session, test_user):
    """跨路径收敛钉子：inventory 首建后，engine _get_or_create_streak_stats
    命中同一行（不另建）——交叉读单行，无重复行落地面。"""
    from app.services.achievement_engine import AchievementEngine

    db_session.add(_freeze_item())
    db_session.add(
        UserConsumable(
            id=str(uuid4()),
            user_id=test_user.id,
            consumable_id="tune_streak_freeze_001",
            effect_type="streak_freeze",
            quantity=2,
        )
    )
    await db_session.commit()

    service = InventoryService(db_session)
    await service.use_consumable(str(test_user.id), "tune_streak_freeze_001", quantity=1)

    engine = AchievementEngine(db_session)
    stats = await engine._get_or_create_streak_stats(str(test_user.id))
    assert int(stats.freeze_charges or 0) >= 1

    rows = (
        (await db_session.execute(select(UserStreakStats).where(UserStreakStats.user_id == test_user.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    # engine 后续奖励路径对同一行继续累加，不产生第二行
    stats.freeze_charges = min(int(stats.freeze_charges or 0) + 1, int(stats.max_freeze_charges or 0))
    await db_session.flush()
    rows_after = (
        (await db_session.execute(select(UserStreakStats).where(UserStreakStats.user_id == test_user.id)))
        .scalars()
        .all()
    )
    assert len(rows_after) == 1
