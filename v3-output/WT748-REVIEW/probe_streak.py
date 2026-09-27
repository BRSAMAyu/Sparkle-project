"""WT748 review probe — streak 表三入口收敛一致性 sqlite 面运行级抽查.

焦点1: 451/457 修后合并态跨路径收敛 + 467 未修路径重复行对 scalar_one_or_none 读面暴露。
自备 sqlite 内存库，不触碰仓库文件。
"""

import sys
import os
from uuid import NAMESPACE_URL, uuid4, uuid5

BACKEND = "/Users/brsama/code/GitHub/Sparkle-project/backend"
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "app"))
sys.path.insert(0, os.path.join(BACKEND, "app", "gen"))

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base

import importlib
import pkgutil
import app.models as _app_models
for _m in pkgutil.walk_packages(_app_models.__path__, "app.models."):
    try:
        importlib.import_module(_m.name)
    except Exception:
        pass

from app.models.user import User
from app.models.achievement import UserStreakStats
from app.models.shop import ShopItem, UserConsumable
from app.services.achievement_engine import AchievementEngine
from app.services.inventory_service import InventoryService
from app.services.guest_seed_service import _ensure_user_streak_stats


@pytest_asyncio.fixture()
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture()
async def test_user(db_session):
    user = User(
        username=f"wt748_{uuid4().hex[:8]}",
        email=f"wt748_{uuid4().hex[:8]}@probe.local",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _freeze_item() -> ShopItem:
    return ShopItem(
        id="wt748_freeze_001",
        name="probe freeze",
        description="probe",
        item_type="boost",
        category="streak_protection",
        price_photons=1,
        is_available=True,
        is_limited=False,
        item_config={"effect_type": "streak_freeze", "charges": 1},
        sort_order=99,
    )


async def _row_ids(db, user_id):
    rows = (
        (await db.execute(select(UserStreakStats).where(UserStreakStats.user_id == user_id)))
        .scalars()
        .all()
    )
    return [r.id for r in rows]


@pytest.mark.asyncio
async def test_p1_engine_firstcreate_deterministic_id(db_session, test_user):
    """451: engine 首建 id == uuid5(NAMESPACE_URL, 'achievement-streak-stats:<uid>')，单行。"""
    engine = AchievementEngine(db_session)
    stats = await engine._get_or_create_streak_stats(str(test_user.id))
    expected = uuid5(NAMESPACE_URL, f"achievement-streak-stats:{test_user.id}")
    assert stats.id == expected, f"engine id {stats.id} != expected {expected}"
    ids = await _row_ids(db_session, test_user.id)
    assert len(ids) == 1


@pytest.mark.asyncio
async def test_p2_inventory_firstcreate_same_id_and_engine_cross_read(db_session, test_user):
    """457: inventory 首建 id 与 451 同源；engine 交叉读同一行不另建。"""
    db_session.add(_freeze_item())
    db_session.add(
        UserConsumable(
            id=str(uuid4()), user_id=test_user.id,
            consumable_id="wt748_freeze_001", effect_type="streak_freeze", quantity=1,
        )
    )
    await db_session.commit()
    svc = InventoryService(db_session)
    result = await svc.use_consumable(str(test_user.id), "wt748_freeze_001", quantity=1)
    assert result["effect_result"]["effect"] == "streak_freeze"
    expected = uuid5(NAMESPACE_URL, f"achievement-streak-stats:{test_user.id}")
    ids = await _row_ids(db_session, test_user.id)
    assert ids == [expected], f"inventory 首建 id 异源: {ids} != [{expected}]"

    engine = AchievementEngine(db_session)
    stats = await engine._get_or_create_streak_stats(str(test_user.id))
    assert stats.id == expected
    ids_after = await _row_ids(db_session, test_user.id)
    assert len(ids_after) == 1, f"engine 交叉读后行数 {len(ids_after)} != 1"


@pytest.mark.asyncio
async def test_p3_engine_firstcreate_then_inventory_same_row(db_session, test_user):
    """反向交叉：engine 首建（451）→ inventory 发货读同一行（不另建双行）。"""
    db_session.add(_freeze_item())
    db_session.add(
        UserConsumable(
            id=str(uuid4()), user_id=test_user.id,
            consumable_id="wt748_freeze_001", effect_type="streak_freeze", quantity=2,
        )
    )
    await db_session.commit()
    engine = AchievementEngine(db_session)
    stats = await engine._get_or_create_streak_stats(str(test_user.id))
    stats.freeze_charges = 0
    await db_session.commit()

    svc = InventoryService(db_session)
    result = await svc.use_consumable(str(test_user.id), "wt748_freeze_001", quantity=2)
    expected = uuid5(NAMESPACE_URL, f"achievement-streak-stats:{test_user.id}")
    ids = await _row_ids(db_session, test_user.id)
    assert len(ids) == 1, f"inventory 交叉发货后行数 {len(ids)} != 1"
    assert result["effect_result"]["charges_added"] == 2


@pytest.mark.asyncio
async def test_p4_467_duplicate_rows_break_engine_read(db_session, test_user):
    """467 竞态产物（同 user_id 双行）落库后：engine 451 修后读面 scalar_one_or_none
    恒 MultipleResultsFound——读面暴露真实存在（运行级）。"""
    expected = uuid5(NAMESPACE_URL, f"achievement-streak-stats:{test_user.id}")
    # 模拟 451/457 任一路径已建行 + 467 随机 id 行（并发双落形态）
    db_session.add(UserStreakStats(user_id=test_user.id, id=expected, current_streak=5))
    db_session.add(UserStreakStats(user_id=test_user.id, id=uuid4(), current_streak=9))
    await db_session.commit()
    assert len(await _row_ids(db_session, test_user.id)) == 2

    engine = AchievementEngine(db_session)
    with pytest.raises(Exception) as exc_info:
        await engine._get_or_create_streak_stats(str(test_user.id))
    assert "MultipleResultsFound" in type(exc_info.value).__name__ or "multiple rows" in str(exc_info.value).lower(), (
        f"engine 读面未炸: {type(exc_info.value).__name__}: {exc_info.value}"
    )


@pytest.mark.asyncio
async def test_p5_467_duplicate_rows_break_inventory_read(db_session, test_user):
    """同上，inventory 457 修后读面同型暴露。"""
    expected = uuid5(NAMESPACE_URL, f"achievement-streak-stats:{test_user.id}")
    db_session.add(UserStreakStats(user_id=test_user.id, id=expected))
    db_session.add(UserStreakStats(user_id=test_user.id, id=uuid4()))
    db_session.add(_freeze_item())
    db_session.add(
        UserConsumable(
            id=str(uuid4()), user_id=test_user.id,
            consumable_id="wt748_freeze_001", effect_type="streak_freeze", quantity=1,
        )
    )
    await db_session.commit()

    svc = InventoryService(db_session)
    with pytest.raises(Exception) as exc_info:
        await svc.use_consumable(str(test_user.id), "wt748_freeze_001", quantity=1)
    assert "MultipleResultsFound" in type(exc_info.value).__name__ or "multiple rows" in str(exc_info.value).lower(), (
        f"inventory 读面未炸: {type(exc_info.value).__name__}: {exc_info.value}"
    )


@pytest.mark.asyncio
async def test_p6_467_seed_fn_sees_duplicate_and_467_seq_firstcreate_no_dup(db_session, test_user):
    """①467 竞态产物双行下 seed 自身 scalar_one_or_none 同炸；
    ②顺序形态（seed 先建随机 id 行→提交→engine 读）不产生重复行但 engine
    认领的是 467 的随机 id 行——确定性 id 仲裁面被 467 先到绕开。"""
    # ①双行炸 seed 读
    db_session.add(UserStreakStats(user_id=test_user.id, id=uuid4()))
    db_session.add(UserStreakStats(user_id=test_user.id, id=uuid4()))
    await db_session.commit()
    with pytest.raises(Exception) as exc_info:
        await _ensure_user_streak_stats(
            db_session, user_id=test_user.id, current_streak=3, max_streak=3,
            total_checkin_days=9, last_activity_date=None,
        )
    assert "MultipleResultsFound" in type(exc_info.value).__name__ or "multiple rows" in str(exc_info.value).lower()

    # ②顺序 seed 先建 → engine 后读
    await db_session.execute(delete(UserStreakStats).where(UserStreakStats.user_id == test_user.id))
    await db_session.commit()
    await _ensure_user_streak_stats(
        db_session, user_id=test_user.id, current_streak=3, max_streak=3,
        total_checkin_days=9, last_activity_date=None,
    )
    await db_session.commit()
    ids = await _row_ids(db_session, test_user.id)
    assert len(ids) == 1
    expected = uuid5(NAMESPACE_URL, f"achievement-streak-stats:{test_user.id}")
    assert ids[0] != expected, "467 先建行竟带确定性 id？"
    engine = AchievementEngine(db_session)
    stats = await engine._get_or_create_streak_stats(str(test_user.id))
    assert stats.id == ids[0], "engine 未认领 467 已有行"
    assert len(await _row_ids(db_session, test_user.id)) == 1, "engine 读 467 随机 id 行后另建了第二行"
