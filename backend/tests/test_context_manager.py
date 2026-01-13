
import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.context_manager import ContextOrchestrator, CognitiveContext
from app.services.focus_service import FocusService
from app.orchestration.orchestrator import ChatOrchestrator
from app.models.galaxy import KnowledgeNode
from app.models.task import Task, TaskStatus
import app.services.focus_service

@pytest.mark.asyncio
async def test_context_orchestrator_aggregation():
    # Mock dependencies
    db_session = AsyncMock()
    redis_client = AsyncMock()
    
    # Setup Redis cache miss
    redis_client.get.return_value = None
    
    orchestrator = ContextOrchestrator(db_session, redis_client)
    
    # Mock Service calls
    # Galaxy
    orchestrator.galaxy_service.stats.calculate_user_stats = AsyncMock(return_value=MagicMock(dict=lambda: {"total_sparks": 100}))
    
    # ErrorBook
    orchestrator.error_book_service.get_review_stats = AsyncMock(return_value={"total_errors": 5})
    orchestrator.error_book_service.list_errors = AsyncMock(return_value=([], 0))
    
    with pytest.MonkeyPatch.context() as m:
        # Mock TaskService
        async def mock_get_multi(*args, **kwargs):
            return [
                MagicMock(
                    id=uuid.uuid4(), title="Test Task", priority=1, due_date=None, type=MagicMock(value="study")
                )
            ], 1
        m.setattr("app.services.task_service.TaskService.get_multi", mock_get_multi)
        
        # Mock UserService
        orchestrator.user_service.get_context = AsyncMock(return_value=MagicMock(preferences={"depth": "high"}))
        orchestrator.user_service.get_analytics_summary = AsyncMock(return_value={"level": 5})
        
        # Mock FocusService
        async def mock_focus(*args):
            return {"focus_minutes": 120}
        
        # Correctly patch the static method on the FocusService class
        m.setattr(FocusService, "get_today_stats", mock_focus)

        # Execute
        user_id = str(uuid.uuid4())
        context = await orchestrator.get_user_context(user_id)
        
        # Verify
        assert isinstance(context, CognitiveContext)
        assert context.user_id == user_id
        assert context.knowledge_stats == {"total_sparks": 100}
        assert context.error_summary == {"total_errors": 5}
        assert len(context.active_tasks) == 1
        assert context.active_tasks[0]["title"] == "Test Task"
        assert context.preferences == {"depth": "high"}
        
        # Verify Cache Set
        assert redis_client.setex.called
        
@pytest.mark.asyncio
async def test_chat_orchestrator_integration():
    # Test that ChatOrchestrator calls ContextOrchestrator
    # This is an integration verification
    pass 
