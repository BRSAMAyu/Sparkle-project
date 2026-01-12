import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.error_book_service import ErrorBookService
from app.services.galaxy_service import GalaxyService
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode
from app.core.event_bus import event_bus, ErrorCreated
from app.schemas.error_book import ErrorRecordCreate, SubjectEnum

@pytest.mark.asyncio
async def test_error_to_galaxy_loop_flow():
    """
    Test the full loop:
    1. Create Error -> Publish Event
    2. Galaxy Service -> Consume Event -> Update Mastery -> Publish Update Event
    """
    
    # Mock DB Session
    mock_db = AsyncMock()
    
    # --- Step 1: Error Service publishes event ---
    error_service = ErrorBookService(mock_db)
    
    # Mock data
    user_id = uuid4()
    error_id = uuid4()
    node_id_1 = uuid4()
    
    # Mock error record
    mock_error = ErrorRecord(
        id=error_id,
        user_id=user_id,
        subject_code="MATH",
        linked_knowledge_node_ids=[node_id_1],
        mastery_level=0.5,
        question_text="test question"
    )
    
    # Mock DB returns
    # Create a MagicMock for the Result object because scalar_one_or_none is synchronous
    mock_result_error = MagicMock()
    mock_result_error.scalar_one_or_none.return_value = mock_error
    
    # Configure execute to return the mock_result when awaited
    mock_db.execute.return_value = mock_result_error
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    
    # Mock LLM and Embedding services to avoid external calls
    with patch('app.services.error_book_service.llm_client') as mock_llm, \
         patch('app.services.error_book_service.embedding_service') as mock_embed, \
         patch('app.core.event_bus.event_bus.publish') as mock_publish:
        
        # Setup mocks
        mock_llm.chat_completion.return_value = {
            "error_type": "concept_confusion",
            "root_cause": "test",
            "study_suggestion": "test"
        }
        mock_embed.get_embedding.return_value = [0.1] * 1536
        
        # Mock search_knowledge_nodes to return our node
        error_service._search_knowledge_nodes = AsyncMock(return_value=[
            KnowledgeNode(id=node_id_1, name="Test Concept")
        ])
        
        # Call analyze_and_link (which triggers the event)
        await error_service.analyze_and_link(error_id, user_id)
        
        # Verify Event Published
        assert mock_publish.called
        call_args = mock_publish.call_args
        event_type = call_args[0][0]
        event_payload = call_args[0][1]
        
        assert event_type == "error_created"
        assert event_payload["user_id"] == str(user_id)
        assert event_payload["error_id"] == str(error_id)
        assert str(node_id_1) in event_payload["linked_node_ids"]
        
        print("\n[SUCCESS] Step 1: Error Created Event Published")
        
        
    # --- Step 2: Galaxy Service consumes event ---
    galaxy_service = GalaxyService(mock_db)
    
    # Mock update_node_mastery
    galaxy_service.update_node_mastery = AsyncMock()
    
    # Mock DB for fetching current mastery
    # Needs to return a Result object that returns the scalar
    mock_result_mastery = MagicMock()
    mock_result_mastery.scalar_one_or_none.return_value = 80 # Current mastery
    mock_db.execute.return_value = mock_result_mastery
    
    # Call handler
    event_data = {
        "user_id": str(user_id),
        "error_id": str(error_id),
        "linked_node_ids": [str(node_id_1)]
    }
    
    with patch('app.core.event_bus.event_bus.publish') as mock_publish_galaxy:
        await galaxy_service.handle_error_created(event_data)
        
        # Verify Mastery Update Called
        galaxy_service.update_node_mastery.assert_called_once()
        call_kwargs = galaxy_service.update_node_mastery.call_args.kwargs
        
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["node_id"] == node_id_1
        assert call_kwargs["new_mastery"] == 72 # 80 * 0.9 = 72
        assert call_kwargs["reason"] == "error_penalty"
        
        # Verify Realtime Update Event Published
        assert mock_publish_galaxy.called
        galaxy_event_type = mock_publish_galaxy.call_args[0][0]
        galaxy_event_payload = mock_publish_galaxy.call_args[0][1]
        
        assert galaxy_event_type == "galaxy.node.updated"
        assert galaxy_event_payload["node_id"] == str(node_id_1)
        assert galaxy_event_payload["new_mastery"] == 72
        
        print(f"[SUCCESS] Step 2: Galaxy Mastery Updated (80 -> 72) and Event Published")
