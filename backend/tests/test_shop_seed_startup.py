"""Regression tests for gamification-eval P0 (empty shop_items in real env).

``seed_shop_items`` (15 items: 4 skins / 4 titles / 3 consumables / 4 boosts)
was only reachable via the manual ``scripts/init_shop.py`` — neither engine
startup, guest seeding, nor migrations triggered it, so every fresh
environment shipped an empty shop and the whole purchase chain was
undemoable. The startup reference-data block in ``app/main.py`` (the same
chain that ensures achievements / galaxy skins / seed libraries) must call it.
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

BACKEND_DIR = Path(__file__).resolve().parents[1]
MAIN_PATH = BACKEND_DIR / "app" / "main.py"


def test_startup_reference_data_block_seeds_shop_items():
    """main.py lifespan must wire seed_shop_items into the startup chain."""
    source = MAIN_PATH.read_text()
    assert "from app.data.shop_seeds import seed_shop_items" in source, (
        "startup must import seed_shop_items — without it shop_items stays "
        "empty in fresh environments (only the manual init_shop.py seeded)"
    )
    assert "await seed_shop_items(db)" in source, (
        "startup must await seed_shop_items(db) alongside the other "
        "reference-data seeds"
    )


@pytest.mark.asyncio
async def test_seed_shop_items_skips_when_already_seeded():
    """seed_shop_items is idempotent: existing rows → no writes, no commit."""
    from app.data.shop_seeds import seed_shop_items

    db = MagicMock(spec=AsyncSession)
    existing = MagicMock()
    existing.scalar_one_or_none.return_value = object()  # any row exists
    db.execute = AsyncMock(return_value=existing)

    await seed_shop_items(db)

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_shop_items_inserts_full_catalog_when_empty():
    """Empty table → all 15 catalog items queued for insert and committed."""
    from app.data.shop_seeds import seed_shop_items
    from app.models.shop import ShopItem

    db = MagicMock(spec=AsyncSession)
    empty = MagicMock()
    empty.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=empty)
    db.add = MagicMock()

    await seed_shop_items(db)

    added = [call.args[0] for call in db.add.call_args_list]
    assert len(added) == 15, f"expected 15 seed items, got {len(added)}"
    assert all(isinstance(item, ShopItem) for item in added)
    assert len({item.id for item in added}) == 15, "seed item ids must be unique"
    db.commit.assert_awaited_once()
