"""
Unit tests for Memory Evolution Service
记忆演化服务单元测试
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_evolution_service import MemoryEvolutionService
from app.models.memory_evolution import MemoryEvolution, EvolutionPrediction


@pytest.fixture
def db_session():
    """Mock database session"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def evolution_service(db_session):
    """Create memory evolution service instance"""
    return MemoryEvolutionService(db_session)


@pytest.mark.asyncio
async def test_track_memory_change(evolution_service: MemoryEvolutionService):
    """Test tracking memory change"""
    memory_id = str(uuid4())

    # Mock数据库添加和提交
    evolution_service.db.add = Mock()
    evolution_service.db.commit = AsyncMock()
    evolution_service.db.refresh = AsyncMock()

    # Mock内部方法
    with patch.object(evolution_service, '_calculate_impact_score', return_value=0.5):
        with patch.object(evolution_service, '_find_affected_decisions', return_value=[]):
            with patch.object(evolution_service, '_find_related_memories', return_value=[]):
                with patch.object(evolution_service, '_update_predictions', return_value=None):
                    with patch.object(evolution_service, '_detect_change_type', return_value='update'):
                        with patch.object(evolution_service, '_identify_trigger_source', return_value='test'):
                            result = await evolution_service.track_memory_change(
                                memory_id=memory_id,
                                memory_type="preference",
                                old_value={"pref_key": "old", "confidence": 0.5},
                                new_value={"pref_key": "new", "confidence": 0.8},
                                change_reason="user_edit",
                                trigger_event="preference_update",
                                workflow_id="test-workflow"
                            )

                            assert result.memory_id == memory_id
                            assert result.change_reason == "user_edit"
                            assert abs(result.confidence_delta - 0.3) < 0.001  # 0.8 - 0.5 (浮点数容差)
                            evolution_service.db.add.assert_called_once()


@pytest.mark.asyncio
async def test_get_evolution_history(evolution_service: MemoryEvolutionService):
    """Test getting evolution history"""
    memory_id = str(uuid4())

    # Mock数据库执行结果
    mock_evo = Mock(spec=MemoryEvolution)
    mock_evo.id = 1
    mock_evo.memory_id = memory_id
    mock_evo.created_at = datetime.now()
    mock_evo.change_type = "update"
    mock_evo.change_reason = "user_edit"
    mock_evo.old_value = {"confidence": 0.5}
    mock_evo.new_value = {"confidence": 0.8}
    mock_evo.confidence_delta = 0.3
    mock_evo.impact_score = 0.7
    mock_evo.trigger_event = "update"
    mock_evo.trigger_source = "user"
    mock_evo.workflow_id = "test"

    # Mock execute返回AsyncMock结果
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = [mock_evo]

    evolution_service.db.execute = AsyncMock(return_value=mock_result)

    history = await evolution_service.get_evolution_history(
        memory_id=memory_id,
        limit=50,
        include_predictions=True
    )

    assert len(history) == 1
    assert history[0]["memory_id"] == memory_id


@pytest.mark.asyncio
async def test_compare_memory_versions(evolution_service: MemoryEvolutionService):
    """Test comparing memory versions"""
    evolution_id = 1

    # Mock演化记录
    mock_evo = Mock(spec=MemoryEvolution)
    mock_evo.id = evolution_id
    mock_evo.memory_id = str(uuid4())
    mock_evo.old_value = {"confidence": 0.5, "value": "A"}
    mock_evo.new_value = {"confidence": 0.8, "value": "B"}
    mock_evo.confidence_delta = 0.3
    mock_evo.impact_score = 0.7

    # Mock数据库查询
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = mock_evo
    evolution_service.db.execute = AsyncMock(return_value=mock_result)

    comparison = await evolution_service.compare_memory_versions(evolution_id)

    assert comparison["evolution_id"] == str(evolution_id)
    assert "field_changes" in comparison
    assert comparison["confidence_delta"] == 0.3


@pytest.mark.asyncio
async def test_predict_evolution(evolution_service: MemoryEvolutionService):
    """Test predicting memory evolution"""
    memory_id = str(uuid4())

    # Mock数据库查询
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = []  # 无历史记录
    evolution_service.db.execute = AsyncMock(return_value=mock_result)

    # Mock添加预测
    evolution_service.db.add = Mock()
    evolution_service.db.commit = AsyncMock()

    predictions = await evolution_service.predict_evolution(
        memory_id=memory_id,
        time_horizon_days=7
    )

    assert isinstance(predictions, list)


@pytest.mark.asyncio
async def test_visualize_evolution(evolution_service: MemoryEvolutionService):
    """Test evolution visualization data"""
    memory_id = str(uuid4())
    time_range = 30

    # Mock演化数据
    mock_evo1 = Mock(spec=MemoryEvolution)
    mock_evo1.created_at = datetime.now() - timedelta(days=1)
    mock_evo1.confidence_after = 0.6
    mock_evo1.impact_score = 0.5

    mock_evo2 = Mock(spec=MemoryEvolution)
    mock_evo2.created_at = datetime.now() - timedelta(days=15)
    mock_evo2.confidence_after = 0.7
    mock_evo2.impact_score = 0.6

    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = [mock_evo1, mock_evo2]
    evolution_service.db.execute = AsyncMock(return_value=mock_result)

    viz_data = await evolution_service.visualize_evolution(
        memory_id=memory_id,
        time_range_days=time_range
    )

    assert viz_data["memory_id"] == memory_id
    assert viz_data["time_range_days"] == time_range
    assert "timeline" in viz_data
    assert len(viz_data["timeline"]["timestamps"]) == 2


@pytest.mark.asyncio
async def test_detect_change_type(evolution_service: MemoryEvolutionService):
    """Test change type detection"""
    # Test create (no old_value)
    assert evolution_service._detect_change_type({}, {"value": "new"}) == "create"

    # Test delete (no new_value)
    assert evolution_service._detect_change_type({"value": "old"}, {}) == "delete"

    # Test update (both exist)
    assert evolution_service._detect_change_type(
        {"value": "old"}, {"value": "new"}
    ) == "update"


@pytest.mark.asyncio
async def test_calculate_impact_score(evolution_service: MemoryEvolutionService):
    """Test impact score calculation"""
    memory_id = str(uuid4())

    old_value = {"confidence": 0.5, "evidence_count": 10}
    new_value = {"confidence": 0.8, "evidence_count": 20}

    # Mock无关联决策或记忆
    evolution_service.db.execute = AsyncMock(return_value=AsyncMock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))))

    impact = await evolution_service._calculate_impact_score(
        memory_id, old_value, new_value
    )

    # Impact应该基于置信度变化
    assert 0 <= impact <= 1
