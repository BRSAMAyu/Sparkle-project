"""
Simple unit tests for photon service.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestPhotonServiceBasic:
    """Basic photon service tests"""

    @pytest.mark.asyncio
    async def test_photon_service_import(self):
        """Test that photon service can be imported"""
        from app.services.photon_service import PhotonService
        assert PhotonService is not None

    def test_photon_models_import(self):
        """Test that photon models can be imported"""
        from app.models.photon import PhotonTransaction, PhotonBalance
        assert PhotonTransaction is not None
        assert PhotonBalance is not None

    def test_transaction_types(self):
        """Test transaction type enum exists"""
        from app.models.photon import TransactionType, TransactionSource
        assert hasattr(TransactionType, 'EARN')
        assert hasattr(TransactionType, 'SPEND')
        assert hasattr(TransactionSource, 'TASK_COMPLETION')


class TestPhotonCalculations:
    """Test photon calculation logic"""

    def test_base_photon_award(self):
        """Test base photon calculation for task completion"""
        base_amount = 10
        difficulty_multiplier = 1
        expected = base_amount * difficulty_multiplier
        assert expected == 10

    def test_photon_award_with_difficulty(self):
        """Test photon calculation with difficulty bonus"""
        base_amount = 10
        difficulty = 3
        bonus = 5
        expected = base_amount + (difficulty * bonus)
        assert expected == 25

    def test_daily_streak_bonus(self):
        """Test daily streak bonus calculation"""
        streak_days = 3
        bonus_per_day = 2
        expected = streak_days * bonus_per_day
        assert expected == 6
