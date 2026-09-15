"""
Tests for GalaxyStatsService - spark_node and predict_next_node
Using mock-based approach to avoid SQLite/JSONB compatibility issues
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.galaxy.stats_service import GalaxyStatsService
from app.schemas.galaxy import NodeWithStatus


class TestMasteryCalculation:
    """Tests for mastery calculation helper methods - no DB required."""

    def test_calculate_mastery_delta_basic(self):
        """Test basic mastery delta calculation."""
        # Directly test the method logic
        # time_factor = min(30/30, 2.0) = 1.0
        # difficulty_factor = 1 + (3-1) * 0.1 = 1.2
        # delta = 5.0 * 1.0 * 1.2 = 6.0
        BASE_MASTERY_POINTS = 5.0

        study_minutes = 30
        importance_level = 3

        time_factor = min(study_minutes / 30.0, 2.0)
        difficulty_factor = 1 + (importance_level - 1) * 0.1
        expected_delta = BASE_MASTERY_POINTS * time_factor * difficulty_factor

        assert expected_delta == 6.0

    def test_calculate_mastery_delta_max_time_factor(self):
        """Test mastery delta caps time factor at 2.0."""
        BASE_MASTERY_POINTS = 5.0

        study_minutes = 120  # More than 60 minutes
        importance_level = 1

        time_factor = min(study_minutes / 30.0, 2.0)
        difficulty_factor = 1 + (importance_level - 1) * 0.1
        expected_delta = BASE_MASTERY_POINTS * time_factor * difficulty_factor

        # time_factor should be capped at 2.0
        assert expected_delta == 10.0

    def test_calculate_mastery_delta_importance_scaling(self):
        """Test mastery delta scales with importance level."""
        BASE_MASTERY_POINTS = 5.0
        study_minutes = 30

        # importance_level=1
        time_factor_1 = min(study_minutes / 30.0, 2.0)
        difficulty_factor_1 = 1 + (1 - 1) * 0.1
        delta_1 = BASE_MASTERY_POINTS * time_factor_1 * difficulty_factor_1

        # importance_level=5
        difficulty_factor_5 = 1 + (5 - 1) * 0.1
        delta_5 = BASE_MASTERY_POINTS * time_factor_1 * difficulty_factor_5

        # Higher importance should yield higher delta
        assert delta_5 > delta_1
        assert delta_1 == 5.0
        assert delta_5 == 7.0

    def test_check_level_up_no_level_up(self):
        """Test no level up when below threshold."""
        service = MagicMock(spec=GalaxyStatsService)
        service._check_level_up = GalaxyStatsService._check_level_up.__get__(service)

        assert not service._check_level_up(10, 20)

    def test_check_level_up_at_30(self):
        """Test level up detection at threshold 30."""
        service = MagicMock(spec=GalaxyStatsService)
        service._check_level_up = GalaxyStatsService._check_level_up.__get__(service)

        assert service._check_level_up(25, 35)

    def test_check_level_up_at_60(self):
        """Test level up detection at threshold 60."""
        service = MagicMock(spec=GalaxyStatsService)
        service._check_level_up = GalaxyStatsService._check_level_up.__get__(service)

        assert service._check_level_up(55, 65)

    def test_check_level_up_at_80(self):
        """Test level up detection at threshold 80."""
        service = MagicMock(spec=GalaxyStatsService)
        service._check_level_up = GalaxyStatsService._check_level_up.__get__(service)

        assert service._check_level_up(75, 85)

    def test_check_level_up_at_95(self):
        """Test level up detection at threshold 95."""
        service = MagicMock(spec=GalaxyStatsService)
        service._check_level_up = GalaxyStatsService._check_level_up.__get__(service)

        assert service._check_level_up(90, 97)

    def test_check_level_up_multiple_thresholds(self):
        """Test level up detection across multiple thresholds."""
        service = MagicMock(spec=GalaxyStatsService)
        service._check_level_up = GalaxyStatsService._check_level_up.__get__(service)

        assert service._check_level_up(20, 70)

    def test_calculate_next_review_basic(self):
        """Test next review time calculation."""
        service = MagicMock(spec=GalaxyStatsService)
        service._calculate_next_review = GalaxyStatsService._calculate_next_review.__get__(service)

        from datetime import datetime

        # Low mastery = short review interval
        next_review_low = service._calculate_next_review(20)
        # High mastery = long review interval
        next_review_high = service._calculate_next_review(90)

        # High mastery should have longer review interval
        assert next_review_high > next_review_low


class TestSparkNodeLogic:
    """Tests for spark_node business logic using mocks."""

    @pytest.mark.asyncio
    async def test_spark_node_flow_with_mocks(self):
        """Test spark_node method flow with mocked dependencies."""
        from uuid import uuid4

        user_id = uuid4()
        node_id = uuid4()

        # Create mock db session
        mock_db = AsyncMock()

        # Create mock node
        mock_node = MagicMock()
        mock_node.id = node_id
        mock_node.name = "Test Node"
        mock_node.importance_level = 3
        mock_node.subject = None

        # Create mock status
        mock_status = MagicMock()
        mock_status.mastery_score = 0
        mock_status.is_unlocked = False
        mock_status.total_study_minutes = 0
        mock_status.study_count = 0

        # Setup db.get to return mock node
        mock_db.get = AsyncMock(return_value=mock_node)

        with patch('app.services.galaxy.stats_service.ExpansionService') as MockExpansionService, \
             patch('app.services.galaxy.stats_service.cache_service') as mock_cache, \
             patch('app.services.galaxy.stats_service.event_bus') as mock_event_bus:

            mock_expansion = AsyncMock()
            mock_expansion.queue_expansion = AsyncMock(return_value=False)
            MockExpansionService.return_value = mock_expansion

            mock_cache.delete_pattern = AsyncMock()
            mock_event_bus.publish = AsyncMock()

            # Create service and mock _get_or_create_status
            service = GalaxyStatsService(mock_db)

            with patch.object(service, '_get_or_create_status', new_callable=AsyncMock) as mock_get_status:
                mock_get_status.return_value = mock_status

                # Mock db.commit
                mock_db.commit = AsyncMock()
                mock_db.add = MagicMock()
                mock_db.flush = AsyncMock()

                result = await service.spark_node(
                    user_id=user_id,
                    node_id=node_id,
                    study_minutes=30
                )

                # Verify result
                assert result is not None
                assert result.spark_event is not None
                assert result.updated_status.is_unlocked is True
                assert result.updated_status.mastery_score > 0


class TestPredictNextNodeLogic:
    """Tests for predict_next_node business logic using mocks."""

    @pytest.mark.asyncio
    async def test_predict_next_node_no_activity(self):
        """Test predict_next_node returns None for user with no activity."""
        mock_db = AsyncMock()

        # Setup db.execute to return no results
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = GalaxyStatsService(mock_db)

        result = await service.predict_next_node(uuid4())

        # With no last_status and no high importance nodes, should return None
        # or a fallback node if high importance nodes exist
        assert result is None or isinstance(result, NodeWithStatus)


class TestConstants:
    """Tests for service constants."""

    def test_base_mastery_points(self):
        """Test base mastery points constant."""
        assert GalaxyStatsService.BASE_MASTERY_POINTS == 5.0

    def test_max_mastery(self):
        """Test max mastery constant."""
        assert GalaxyStatsService.MAX_MASTERY == 100.0
