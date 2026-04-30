"""
Phase 4 Galaxy Services Verification Tests

Tests for:
- GalaxyFeedbackService
- TaskEventListener
- GalaxyStreamingService
"""
import asyncio
import pytest
from uuid import UUID, uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from app.services.galaxy.feedback_service import (
    GalaxyFeedbackService, FeedbackType
)
from app.services.galaxy.event_listener import TaskEventListener
from app.services.galaxy.streaming_service import GalaxyStreamingService


# ==================== GalaxyFeedbackService Tests ====================

class TestGalaxyFeedbackService:
    """Test GalaxyFeedbackService functionality"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        db.add = Mock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def feedback_service(self, mock_db):
        """Create feedback service instance"""
        return GalaxyFeedbackService(mock_db)

    def test_feedback_type_constants(self):
        """Test feedback type constants are defined"""
        assert FeedbackType.TASK_COMPLETED == "task_completed"
        assert FeedbackType.ERROR_CREATED == "error_created"
        assert FeedbackType.STUDY_SESSION == "study_session"
        assert FeedbackType.QUIZ_PASSED == "quiz_passed"
        assert FeedbackType.QUIZ_FAILED == "quiz_failed"

    def test_feedback_scores_config(self):
        """Test feedback score configuration"""
        service = GalaxyFeedbackService(None)
        assert service.FEEDBACK_SCORES[FeedbackType.TASK_COMPLETED] == 0.8
        assert service.FEEDBACK_SCORES[FeedbackType.ERROR_CREATED] == -0.3
        assert service.FEEDBACK_SCORES[FeedbackType.QUIZ_PASSED] == 1.0
        assert service.FEEDBACK_SCORES[FeedbackType.QUIZ_FAILED] == -0.5

    @pytest.mark.asyncio
    async def test_calculate_feedback_score_task_completed(self, feedback_service):
        """Test feedback score calculation for task completion"""
        event_data = {
            "type": FeedbackType.TASK_COMPLETED,
            "user_id": uuid4(),
            "node_id": uuid4()
        }
        score = await feedback_service._calculate_feedback_score(event_data)
        assert score == 0.8

    @pytest.mark.asyncio
    async def test_calculate_feedback_score_study_session(self, feedback_service):
        """Test feedback score calculation for study session"""
        event_data = {
            "type": FeedbackType.STUDY_SESSION,
            "duration_minutes": 30
        }
        score = await feedback_service._calculate_feedback_score(event_data)
        assert score == 1.0

        # Test with less than 30 minutes
        event_data["duration_minutes"] = 15
        score = await feedback_service._calculate_feedback_score(event_data)
        assert score == 0.5

    @pytest.mark.asyncio
    async def test_calculate_feedback_score_error_created(self, feedback_service):
        """Test feedback score calculation for error creation"""
        event_data = {
            "type": FeedbackType.ERROR_CREATED,
            "user_id": uuid4(),
            "node_id": uuid4()
        }
        score = await feedback_service._calculate_feedback_score(event_data)
        assert score == -0.3

    @pytest.mark.asyncio
    async def test_collect_implicit_feedback_missing_fields(self, feedback_service):
        """Test that missing required fields returns None"""
        result = await feedback_service.collect_implicit_feedback({
            "type": "task_completed"
            # Missing user_id and node_id
        })
        assert result is None

    @pytest.mark.asyncio
    async def test_record_feedback(self, feedback_service, mock_db):
        """Test recording feedback to database"""
        user_id = uuid4()
        node_id = uuid4()

        await feedback_service._record_feedback(
            user_id=user_id,
            node_id=node_id,
            feedback_type="implicit",
            implicit_score=0.8,
            source="test",
            metadata={"test": "data"}
        )

        # Verify db.add was called with a valid feedback record
        mock_db.add.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.user_id == user_id
        assert added_obj.trigger_node_id == node_id
        assert added_obj.implicit_score == 0.8

        # Verify db.commit was called (note: mock_db.commit is an AsyncMock, not a coroutine)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_explicit_feedback_invalid_rating(self, feedback_service):
        """Test explicit feedback with invalid rating"""
        user_id = uuid4()
        node_id = uuid4()

        # Rating too low
        result = await feedback_service.collect_explicit_feedback(
            user_id, node_id, 0
        )
        assert result is None

        # Rating too high
        result = await feedback_service.collect_explicit_feedback(
            user_id, node_id, 6
        )
        assert result is None


# ==================== TaskEventListener Tests ====================

class TestTaskEventListener:
    """Test TaskEventListener functionality"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_feedback_service(self):
        """Mock feedback service"""
        service = AsyncMock()
        service.collect_implicit_feedback = AsyncMock(return_value={
            "node_id": "test",
            "old_mastery": 10,
            "new_mastery": 20
        })
        return service

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus"""
        event_bus = AsyncMock()
        event_bus.connect = AsyncMock()
        event_bus.close = AsyncMock()
        event_bus.subscribe = Mock(side_effect=lambda *args, **kwargs: asyncio.sleep(0))
        return event_bus

    @pytest.fixture
    def event_listener(self, mock_db, mock_feedback_service, mock_event_bus):
        """Create event listener instance"""
        return TaskEventListener(mock_db, mock_feedback_service, mock_event_bus)

    def test_event_listener_initialization(self, event_listener):
        """Test event listener initializes correctly"""
        assert event_listener.STREAM_NAME == "sparkle_events"
        assert event_listener.GROUP_NAME == "galaxy_listeners"
        assert event_listener._running is False

    @pytest.mark.asyncio
    async def test_on_event_task_completed(self, event_listener, mock_feedback_service):
        """Test handling task completed event"""
        task_id = uuid4()
        user_id = uuid4()

        event = {
            "event_type": "task.completed",
            "task_id": str(task_id),
            "user_id": str(user_id),
            "actual_minutes": 30,
            "difficulty": 3
        }

        # Mock _get_task_related_nodes to return a node
        with patch.object(event_listener, '_get_task_related_nodes', return_value=[uuid4()]):
            await event_listener.on_task_completed(event)

    @pytest.mark.asyncio
    async def test_on_event_error_created(self, event_listener, mock_feedback_service):
        """Test handling error created event"""
        error_id = str(uuid4())
        user_id = str(uuid4())
        node_id = str(uuid4())

        event = {
            "event_type": "error_created",
            "error_id": error_id,
            "user_id": user_id,
            "linked_node_ids": [node_id]
        }

        await event_listener.on_error_created(event)

        # Verify feedback was collected
        assert mock_feedback_service.collect_implicit_feedback.called

    @pytest.mark.asyncio
    async def test_on_event_task_abandoned(self, event_listener, mock_feedback_service):
        """Test handling task abandoned event"""
        task_id = str(uuid4())
        user_id = str(uuid4())

        event = {
            "event_type": "task.abandoned",
            "task_id": task_id,
            "user_id": user_id,
            "time_spent": 20
        }

        with patch.object(event_listener, '_get_task_related_nodes', return_value=[uuid4()]):
            await event_listener.on_task_abandoned(event)

    @pytest.mark.asyncio
    async def test_on_event_unknown_type(self, event_listener):
        """Test handling unknown event type"""
        event = {
            "event_type": "unknown.event",
            "data": "test"
        }

        # Should not raise exception
        await event_listener._on_event(event)

    def test_stop(self, event_listener):
        """Test stopping the event listener"""
        event_listener._running = True
        event_listener.stop()
        assert event_listener._running is False

    @pytest.mark.asyncio
    async def test_shutdown_closes_event_bus(self, event_listener, mock_event_bus):
        """Test shutdown releases event bus resources."""
        event_listener._running = True
        await event_listener.shutdown()
        assert event_listener._running is False
        mock_event_bus.close.assert_awaited_once()


# ==================== GalaxyStreamingService Tests ====================

class TestGalaxyStreamingService:
    """Test GalaxyStreamingService functionality"""

    @pytest.fixture
    def mock_ws_manager(self):
        """Mock WebSocket manager"""
        manager = AsyncMock()
        manager.send_personal_message = AsyncMock()
        return manager

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus"""
        event_bus = AsyncMock()
        event_bus.connect = AsyncMock()
        event_bus.subscribe = Mock(side_effect=lambda *args, **kwargs: asyncio.sleep(0))
        return event_bus

    @pytest.fixture
    def streaming_service(self, mock_ws_manager, mock_event_bus):
        """Create streaming service instance"""
        return GalaxyStreamingService(mock_ws_manager, mock_event_bus)

    def test_message_type_constants(self):
        """Test WebSocket message type constants"""
        assert GalaxyStreamingService.MSG_MASTERY_UPDATED == "galaxy.mastery_updated"
        assert GalaxyStreamingService.MSG_NODE_EXPANDED == "galaxy.nodes_expanded"
        assert GalaxyStreamingService.MSG_NODE_UNLOCKED == "galaxy.node_unlocked"
        assert GalaxyStreamingService.MSG_LEVEL_UP == "galaxy.level_up"
        assert GalaxyStreamingService.MSG_BATCH_UPDATE == "galaxy.batch_update"

    def test_streaming_service_initialization(self, streaming_service):
        """Test streaming service initializes correctly"""
        assert streaming_service._running is False
        assert streaming_service._consumer_started is False

    @pytest.mark.asyncio
    async def test_broadcast_mastery_update(self, streaming_service, mock_ws_manager):
        """Test broadcasting mastery update"""
        user_id = uuid4()
        node_id = uuid4()

        await streaming_service.broadcast_mastery_update(
            user_id=user_id,
            node_id=node_id,
            old_mastery=10,
            new_mastery=20,
            reason="test"
        )

        # Verify send_personal_message was called with correct user_id and message structure
        mock_ws_manager.send_personal_message.assert_called_once()

        # Get the message that was sent
        call_args = mock_ws_manager.send_personal_message.call_args
        message = call_args[0][0]
        sent_user_id = call_args[0][1]

        assert message["type"] == "galaxy.mastery_updated"
        assert message["data"]["node_id"] == str(node_id)
        assert message["data"]["old_mastery"] == 10
        assert message["data"]["new_mastery"] == 20
        assert message["data"]["delta"] == 10
        assert sent_user_id == str(user_id)

    @pytest.mark.asyncio
    async def test_broadcast_node_unlocked(self, streaming_service, mock_ws_manager):
        """Test broadcasting node unlocked"""
        user_id = uuid4()
        node_id = uuid4()

        await streaming_service.broadcast_node_unlocked(
            user_id=user_id,
            node_id=node_id,
            node_name="Test Node"
        )

        mock_ws_manager.send_personal_message.assert_called_once()

        call_args = mock_ws_manager.send_personal_message.call_args
        message = call_args[0][0]
        sent_user_id = call_args[0][1]

        assert message["type"] == "galaxy.node_unlocked"
        assert message["data"]["node_id"] == str(node_id)
        assert message["data"]["node_name"] == "Test Node"
        assert sent_user_id == str(user_id)

    @pytest.mark.asyncio
    async def test_broadcast_level_up(self, streaming_service, mock_ws_manager):
        """Test broadcasting level up"""
        user_id = uuid4()
        node_id = uuid4()

        await streaming_service.broadcast_level_up(
            user_id=user_id,
            node_id=node_id,
            old_level=2,
            new_level=3
        )

        mock_ws_manager.send_personal_message.assert_called_once()

        call_args = mock_ws_manager.send_personal_message.call_args
        message = call_args[0][0]
        sent_user_id = call_args[0][1]

        assert message["type"] == "galaxy.level_up"
        assert message["data"]["old_level"] == 2
        assert message["data"]["new_level"] == 3
        assert sent_user_id == str(user_id)

    @pytest.mark.asyncio
    async def test_broadcast_batch_update(self, streaming_service, mock_ws_manager):
        """Test broadcasting batch update"""
        user_id = uuid4()

        updates = [
            {"node_id": str(uuid4()), "old_mastery": 10, "new_mastery": 20},
            {"node_id": str(uuid4()), "old_mastery": 5, "new_mastery": 15}
        ]

        await streaming_service.broadcast_batch_update(
            user_id=user_id,
            updates=updates
        )

        mock_ws_manager.send_personal_message.assert_called_once()

        call_args = mock_ws_manager.send_personal_message.call_args
        message = call_args[0][0]
        sent_user_id = call_args[0][1]

        assert message["type"] == "galaxy.batch_update"
        assert message["data"]["count"] == 2
        assert sent_user_id == str(user_id)

    @pytest.mark.asyncio
    async def test_on_mastery_updated_event(self, streaming_service, mock_ws_manager):
        """Test handling mastery updated event"""
        user_id = uuid4()
        node_id = uuid4()

        with patch.object(streaming_service, '_get_node_name', return_value="Test Node"):
            event_data = {
                "event_type": "node_mastery_updated",
                "user_id": str(user_id),
                "node_id": str(node_id),
                "old_mastery": 0,
                "new_mastery": 15,
                "reason": "test"
            }

            await streaming_service._on_mastery_updated(event_data)

            # Should send mastery update + unlock notification + level up (0→1)
            assert mock_ws_manager.send_personal_message.call_count == 3

    def test_stop(self, streaming_service):
        """Test stopping the streaming service"""
        streaming_service._running = True
        streaming_service.stop()
        assert streaming_service._running is False


# ==================== Integration Tests ====================

class TestPhase4Integration:
    """Integration tests for Phase 4 services"""

    @pytest.mark.asyncio
    async def test_event_flow_task_complete_to_websocket(self):
        """Test full event flow from task completion to WebSocket push"""
        # This would require more complex setup with actual DB and event bus
        # For now, we verify the modules can be imported and instantiated
        from app.services.galaxy.feedback_service import GalaxyFeedbackService
        from app.services.galaxy.event_listener import TaskEventListener
        from app.services.galaxy.streaming_service import GalaxyStreamingService

        # Verify classes can be instantiated
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_ws = AsyncMock()
        mock_event_bus = AsyncMock()

        feedback_service = GalaxyFeedbackService(mock_db, mock_redis)
        event_listener = TaskEventListener(mock_db, feedback_service, mock_event_bus)
        streaming_service = GalaxyStreamingService(mock_ws, mock_event_bus)

        assert feedback_service is not None
        assert event_listener is not None
        assert streaming_service is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
