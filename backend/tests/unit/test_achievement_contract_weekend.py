"""
P1-13: Tests for AchievementEngine contract and weekend warrior logic.

Covers:
- ContractService: creation, duplicate prevention, status checks (active/completed/failed)
- ContractService.update_daily_progress: minute accumulation, day rollover
- Weekend streak calculation: bucket assignment, streak counting, edge cases
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.achievement_engine import AchievementEngine, ContractService


# ── Weekend bucket tests (static methods) ──────────────────────


class TestWeekendBucket:
    def test_saturday_returns_bucket(self):
        ts = datetime(2026, 5, 2, 14, 0, tzinfo=UTC)
        bucket = AchievementEngine._weekend_bucket_for(ts)
        assert bucket == date(2026, 5, 2)

    def test_sunday_same_bucket_as_saturday(self):
        sat = datetime(2026, 5, 2, 14, 0, tzinfo=UTC)
        sun = datetime(2026, 5, 3, 10, 0, tzinfo=UTC)
        assert AchievementEngine._weekend_bucket_for(sat) == AchievementEngine._weekend_bucket_for(sun)

    def test_weekday_returns_none(self):
        ts = datetime(2026, 5, 4, 10, 0, tzinfo=UTC)  # Monday
        assert AchievementEngine._weekend_bucket_for(ts) is None

    def test_friday_returns_none(self):
        ts = datetime(2026, 5, 1, 23, 59, tzinfo=UTC)
        assert AchievementEngine._weekend_bucket_for(ts) is None


class TestWeekendStreak:
    def test_consecutive_weekends_count(self):
        base = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
        timestamps = [base + timedelta(days=7 * i) for i in range(3)]
        assert AchievementEngine._calculate_weekend_streak(timestamps) == 3

    def test_gap_breaks_streak(self):
        base = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
        timestamps = [base, base + timedelta(days=14)]
        assert AchievementEngine._calculate_weekend_streak(timestamps) == 1

    def test_empty_timestamps(self):
        assert AchievementEngine._calculate_weekend_streak([]) == 0

    def test_single_weekend(self):
        ts = [datetime(2026, 5, 2, 10, 0, tzinfo=UTC)]
        assert AchievementEngine._calculate_weekend_streak(ts) == 1

    def test_multiple_entries_same_weekend_count_as_one(self):
        base = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
        timestamps = [base, base + timedelta(hours=3), base + timedelta(hours=12)]
        assert AchievementEngine._calculate_weekend_streak(timestamps) == 1

    def test_weekday_entries_ignored(self):
        base = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)  # Saturday
        timestamps = [base, base + timedelta(days=2), base + timedelta(days=3)]
        assert AchievementEngine._calculate_weekend_streak(timestamps) == 1

    def test_four_consecutive_weekends(self):
        base = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
        timestamps = [base + timedelta(days=7 * i) for i in range(4)]
        assert AchievementEngine._calculate_weekend_streak(timestamps) == 4

    def test_five_consecutive_weekends(self):
        base = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
        timestamps = [base + timedelta(days=7 * i) for i in range(5)]
        assert AchievementEngine._calculate_weekend_streak(timestamps) == 5

    def test_new_year_boundary(self):
        sat = datetime(2027, 1, 2, 10, 0, tzinfo=UTC)
        sun = datetime(2027, 1, 3, 10, 0, tzinfo=UTC)
        assert AchievementEngine._weekend_bucket_for(sat) == AchievementEngine._weekend_bucket_for(sun)

    def test_dst_boundary(self):
        ts = datetime(2026, 3, 7, 2, 30, tzinfo=UTC)  # Saturday
        assert AchievementEngine._weekend_bucket_for(ts) is not None


# ── Contract tests using _get_active_contract patch ────────────


@dataclass
class FakeContract:
    """Simple contract stub with real field types matching SQLAlchemy model."""
    id: str = "c1"
    user_id: str = "u1"
    status: str = "active"
    target_study_minutes: int = 30
    target_days: int = 7
    current_minutes: int = 0
    current_days: int = 0
    end_date: datetime = datetime(2026, 5, 7)  # DateTime column in DB
    photon_stake: int = 100
    reward_multiplier: float = 1.5
    failure_reason: str | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None


def _make_service() -> tuple[ContractService, MagicMock]:
    db = MagicMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return ContractService(db), db


class TestContractCreation:
    @pytest.mark.asyncio
    async def test_create_contract(self):
        service, db = _make_service()
        db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None),
        ))
        db.refresh = AsyncMock()

        contract = await service.create_contract("u1", study_minutes=30, days=7, photon_stake=100)
        db.add.assert_called_once()
        added_contract = db.add.call_args[0][0]
        assert added_contract.user_id == "u1"
        assert added_contract.target_study_minutes == 30
        assert added_contract.target_days == 7
        assert added_contract.photon_stake == 100

    @pytest.mark.asyncio
    async def test_rejects_duplicate_active(self):
        service, db = _make_service()
        existing = FakeContract()
        db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=existing),
        ))

        with pytest.raises(ValueError, match="already has an active"):
            await service.create_contract("u1", study_minutes=30, days=7, photon_stake=100)


class TestContractStatus:
    @pytest.mark.asyncio
    async def test_no_contract_returns_none(self):
        service, db = _make_service()
        service._get_active_contract = AsyncMock(return_value=None)
        result = await service.check_contract_status("u1")
        assert result is None

    @pytest.mark.asyncio
    async def test_active_contract_shows_progress(self):
        service, db = _make_service()
        future = datetime(2030, 1, 1)
        contract = FakeContract(current_days=3, current_minutes=60, end_date=future)
        service._get_active_contract = AsyncMock(return_value=contract)

        result = await service.check_contract_status("u1")
        assert result is not None
        assert result["status"] == "active"
        assert "3/7" in result["progress"]

    @pytest.mark.asyncio
    async def test_expired_and_completed(self):
        service, db = _make_service()
        past = datetime(2020, 1, 1)
        contract = FakeContract(
            current_days=7, current_minutes=300, end_date=past,
        )
        service._get_active_contract = AsyncMock(return_value=contract)
        service._grant_rewards = AsyncMock()
        service._trigger_contract_achievement = AsyncMock()

        result = await service.check_contract_status("u1")
        assert result["status"] == "completed"
        assert result["reward"] == 100 * 1.5

    @pytest.mark.asyncio
    async def test_expired_and_failed(self):
        service, db = _make_service()
        past = datetime(2020, 1, 1)
        contract = FakeContract(
            current_days=3, current_minutes=100, end_date=past,
        )
        service._get_active_contract = AsyncMock(return_value=contract)
        service._deduct_photons = AsyncMock()
        service._trigger_contract_achievement = AsyncMock()

        result = await service.check_contract_status("u1")
        assert result["status"] == "failed"
        assert result["lost"] == 100


class TestDailyProgress:
    @pytest.mark.asyncio
    async def test_minute_accumulation_triggers_day_rollover(self):
        service, db = _make_service()
        contract = FakeContract(current_minutes=15, current_days=2)
        service._get_active_contract = AsyncMock(return_value=contract)
        service.check_contract_status = AsyncMock(return_value={"status": "active"})

        await service.update_daily_progress("u1", study_minutes=20)
        # 15 + 20 = 35 >= 30 target
        assert contract.current_days == 3

    @pytest.mark.asyncio
    async def test_no_rollover_when_below_target(self):
        service, db = _make_service()
        contract = FakeContract(current_minutes=10, current_days=2)
        service._get_active_contract = AsyncMock(return_value=contract)
        service.check_contract_status = AsyncMock(return_value={"status": "active"})

        await service.update_daily_progress("u1", study_minutes=5)
        # 10 + 5 = 15 < 30
        assert contract.current_days == 2

    @pytest.mark.asyncio
    async def test_no_contract_no_crash(self):
        service, db = _make_service()
        service._get_active_contract = AsyncMock(return_value=None)
        await service.update_daily_progress("u1", study_minutes=30)
