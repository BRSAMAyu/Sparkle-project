import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics.behavior_pattern_service import BehaviorPatternService
from app.models.task import Task
from app.models.cognitive import BehaviorPattern

@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def service(mock_db):
    # Mock dependencies inside __init__
    with patch("app.services.analytics.behavior_pattern_service.BlindspotAnalyzer") as MockAnalyzer, \
         patch("app.services.analytics.behavior_pattern_service.NudgeService") as MockNudge:
        srv = BehaviorPatternService(mock_db)
        srv.blindspot_analyzer = MockAnalyzer.return_value
        srv.nudge_service = MockNudge.return_value
        return srv

@pytest.mark.asyncio
async def test_analyze_planning_optimism_detected(service, mock_db):
    # Setup
    user_id = uuid.uuid4()
    task_id = uuid.uuid4()
    
    # Mock current task (Actual 90m > Estimated 45m * 1.5)
    mock_task = MagicMock(spec=Task)
    mock_task.id = task_id
    mock_task.estimated_minutes = 45
    mock_task.actual_minutes = 90
    mock_db.get.return_value = mock_task

    # Mock history (recurrence)
    mock_history_task = MagicMock(spec=Task)
    mock_history_task.estimated_minutes = 30
    mock_history_task.actual_minutes = 60 # Also optimistic
    
    # Mock DB execution for history query
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_history_task]
    
    # Mock DB execution for pattern query (not found first)
    mock_pattern_result = MagicMock()
    # If we want to simulate "not found", scalars().first() should return None.
    # The previous error suggests it was returning a MagicMock (default behavior).
    mock_pattern_result.scalars.return_value.first.return_value = None
    
    # Mock DB add/commit/refresh
    def side_effect(query):
        # Using string representation to differentiate queries
        if "FROM behavior_patterns" in str(query) or "behavior_patterns" in str(query):
            return mock_pattern_result
        return mock_result
    
    mock_db.execute.side_effect = side_effect

    # Mock DB add/refresh to simulate return value
    # We don't need real logic here, just ensure it doesn't crash
    mock_db.refresh = AsyncMock()
    
    # Capture added object
    added_objects = []
    def mock_add(obj):
        added_objects.append(obj)
    mock_db.add.side_effect = mock_add

    # Act
    with patch("app.core.event_bus.event_bus.publish", new_callable=AsyncMock) as mock_publish:
        result = await service.analyze_planning_optimism(user_id, task_id)

    # Assert
    assert result is not None
    # Result is the object we created in the service
    assert result.pattern_name == "Planning Optimism"
    assert result.confidence_score >= 0.6
    
    # Verify DB add called
    assert mock_db.add.called
    assert mock_db.commit.called

@pytest.mark.asyncio
async def test_analyze_planning_optimism_no_bias(service, mock_db):
    # Setup
    user_id = uuid.uuid4()
    task_id = uuid.uuid4()
    
    # Mock task (Actual 50m < Estimated 45m * 1.5)
    mock_task = MagicMock(spec=Task)
    mock_task.estimated_minutes = 45
    mock_task.actual_minutes = 50
    mock_db.get.return_value = mock_task

    # Act
    result = await service.analyze_planning_optimism(user_id, task_id)

    # Assert
    assert result is None
    assert not mock_db.add.called

@pytest.mark.asyncio
async def test_analyze_focus_decay_detected(service, mock_db):
    # Setup
    user_id = uuid.uuid4()
    
    # Mock 3 days stats
    async def mock_avg_side_effect(uid, date):
        today = datetime.date.today()
        if date == today: return 30.0
        if date == today - datetime.timedelta(days=1): return 60.0
        if date == today - datetime.timedelta(days=2): return 100.0
        return 0.0

    service._get_daily_focus_average = AsyncMock(side_effect=mock_avg_side_effect)
    
    # Mock Pattern query (None)
    mock_pattern_result = MagicMock()
    mock_pattern_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_pattern_result
    mock_db.refresh = AsyncMock()

    # Act
    with patch("app.core.event_bus.event_bus.publish", new_callable=AsyncMock) as mock_publish:
        result = await service.analyze_focus_decay(user_id)

    # Assert
    assert result is not None
    assert result.pattern_name == "Focus Decay"
    assert mock_publish.called
    assert mock_publish.call_args[0][0] == "nudge.triggered"

@pytest.mark.asyncio
async def test_analyze_blindspots(service, mock_db):
    # Setup
    user_id = uuid.uuid4()
    
    # Mock Analyzer Result
    mock_blindspot = {
        "node_id": uuid.uuid4(),
        "node_name": "Recursion",
        "reason": "Prerequisites mastered but node neglected",
        "score": 100
    }
    service.blindspot_analyzer.analyze_blindspots = AsyncMock(return_value=[mock_blindspot])
    
    # Mock Pattern Query (None)
    mock_pattern_result = MagicMock()
    mock_pattern_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_pattern_result
    mock_db.refresh = AsyncMock()

    # Act
    with patch("app.core.event_bus.event_bus.publish", new_callable=AsyncMock) as mock_publish:
        results = await service.analyze_cognitive_blindspots(user_id)

    # Assert
    assert len(results) == 1
    assert results[0].pattern_name == "Cognitive Blindspot"
    assert mock_publish.called
