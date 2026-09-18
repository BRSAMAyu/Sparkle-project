"""Regression tests for gamification-eval P1-1 (GET /achievements/{id} 500).

The "public alias" methods (get_achievement / is_unlocked /
build_achievement_detail) were defined on ContractService instead of
AchievementEngine, so api/v1/achievements.py's `engine.get_achievement(...)`
raised AttributeError on every detail request
(``'AchievementEngine' object has no attribute 'get_achievement'``).

The aliases belong to AchievementEngine — the class the API layer actually
instantiates — and must not silently sit on ContractService.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.achievement_engine import AchievementEngine, ContractService


@pytest.fixture
def engine() -> AchievementEngine:
    return AchievementEngine(MagicMock(spec=AsyncSession))


@pytest.mark.asyncio
async def test_engine_get_achievement_alias_returns_definition(engine):
    sentinel = SimpleNamespace(id="streak_7")
    engine._get_achievement = AsyncMock(return_value=sentinel)

    assert await engine.get_achievement("streak_7") is sentinel


@pytest.mark.asyncio
async def test_engine_is_unlocked_alias(engine):
    engine._is_unlocked = AsyncMock(return_value=True)

    assert await engine.is_unlocked(uuid4(), "streak_7") is True


def test_engine_build_achievement_detail_alias(engine):
    sentinel = SimpleNamespace(id="streak_7")
    engine._build_achievement_detail = MagicMock(return_value={"id": "streak_7"})

    assert engine.build_achievement_detail(sentinel, "zh") == {"id": "streak_7"}
    engine._build_achievement_detail.assert_called_once_with(sentinel, "zh")


def test_aliases_are_not_on_contract_service():
    """The aliases must live on AchievementEngine, not ContractService.

    ContractService.__init__ takes a db session but has no achievement cache,
    so calling them there could only ever fail; keeping them is how the bug
    slipped through review.
    """
    assert hasattr(AchievementEngine, "get_achievement")
    assert hasattr(AchievementEngine, "is_unlocked")
    assert hasattr(AchievementEngine, "build_achievement_detail")
    assert not hasattr(ContractService, "get_achievement")
    assert not hasattr(ContractService, "is_unlocked")
    assert not hasattr(ContractService, "build_achievement_detail")
