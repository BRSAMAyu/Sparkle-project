import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta

from app.services.error_book_service import ErrorBookService
from app.services.error_book_mastery_sync_service import ErrorBookMasterySyncService
from app.services.galaxy_service import GalaxyService
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode
from app.core.event_bus import event_bus, ErrorCreated
from app.schemas.error_book import ErrorRecordCreate, KnowledgeLinkBrief, SubjectEnum


class _AsyncNullContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


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
    mock_db.begin_nested = MagicMock(return_value=_AsyncNullContext())
    
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
        mock_embed.get_embedding.return_value = [0.1] * 1024
        
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
        


    # --- Step 2: Deprecated Galaxy event consumer removed ---
    # handle_error_created / update_mastery_from_error have been removed
    # from GalaxyService. Mastery writes are owned by ErrorBookMasterySyncService.
    assert not hasattr(GalaxyService, "handle_error_created"), \
        "handle_error_created should be removed from GalaxyService"
    assert not hasattr(GalaxyService, "update_mastery_from_error"), \
        "update_mastery_from_error should be removed from GalaxyService"

    print("[SUCCESS] Step 2: Deprecated Galaxy mastery methods confirmed removed")


def test_error_review_cards_cluster_real_mistakes_into_actionable_cards():
    service = ErrorBookService(AsyncMock())
    user_id = uuid4()
    node_id = uuid4()
    now = datetime.utcnow()
    common_analysis = {
        "error_type": "concept_confusion",
        "root_cause": "混淆 TCP 拥塞窗口和接收窗口的触发条件",
    }
    errors = [
        ErrorRecord(
            id=uuid4(),
            user_id=user_id,
            subject_code="computer",
            chapter="TCP",
            affected_node_id=node_id,
            linked_knowledge_node_ids=[node_id],
            mastery_level=0.35,
            review_count=1,
            next_review_at=now - timedelta(hours=2),
            created_at=now - timedelta(days=3),
            latest_analysis=common_analysis,
            question_text="窗口变量如何变化？",
        ),
        ErrorRecord(
            id=uuid4(),
            user_id=user_id,
            subject_code="computer",
            chapter="TCP",
            affected_node_id=node_id,
            linked_knowledge_node_ids=[node_id],
            mastery_level=0.45,
            review_count=2,
            next_review_at=now - timedelta(hours=1),
            created_at=now - timedelta(days=1),
            latest_analysis=common_analysis,
            question_text="rwnd 和 cwnd 的区别？",
        ),
    ]
    for error in errors:
        error.knowledge_links = [
            KnowledgeLinkBrief(id=node_id, name="TCP 拥塞控制", is_primary=True),
        ]

    cards = service._build_cluster_review_cards(errors, now=now)

    assert len(cards) == 1
    card = cards[0]
    assert card.cluster_id == f"node:{node_id}"
    assert card.error_count == 2
    assert card.due_count == 2
    assert card.affected_node_name == "TCP 拥塞控制"
    assert card.task_card["source"] == "error_book_cluster"
    assert card.task_card["type"] == "error_review"
    assert set(card.task_card["error_ids"]) == {str(error.id) for error in errors}
    assert {"start_review", "create_task", "open_knowledge_node"} <= {action.type for action in card.actions}


@pytest.mark.asyncio
async def test_forgotten_review_feedback_updates_mastery_and_evaluates_plan_pressure():
    service = ErrorBookMasterySyncService(AsyncMock())
    user_id = uuid4()
    node_id = uuid4()
    plan_id = uuid4()
    error = ErrorRecord(
        id=uuid4(),
        user_id=user_id,
        subject_code="computer",
        linked_knowledge_node_ids=[node_id],
        latest_analysis={"error_type": "concept_confusion"},
    )
    service._update_node_mastery = AsyncMock(
        return_value={
            "node_id": str(node_id),
            "error_id": str(error.id),
            "old_mastery": 40,
            "new_mastery": 38,
            "delta": -2,
        }
    )
    service._identify_error_pressure_impacted_plans = AsyncMock(return_value={plan_id})
    service._evaluate_impacted_plans = AsyncMock()

    results = await service.apply_review_feedback(user_id, error, "forgotten")

    assert results[0]["delta"] == -2
    assert service._update_node_mastery.call_args.kwargs["delta"] == -2
    service._evaluate_impacted_plans.assert_awaited_once_with(
        user_id=user_id,
        plan_ids={plan_id},
        trigger="error_review_pressure",
        feedback_category="review_forgotten",
    )
