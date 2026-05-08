import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import app.services.cognitive_service as cognitive_service_module
from app.services.cognitive_service import CognitiveService
from app.models.cognitive import CognitiveFragment, BehaviorPattern
from app.models.user import User

@pytest.mark.asyncio
async def test_analyze_behavior_creates_pattern():
    # Setup
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    service = CognitiveService(mock_db)
    
    user_id = uuid4()
    fragment_id = uuid4()
    
    # Mock Fragment Retrieval
    mock_fragment = CognitiveFragment(
        id=fragment_id,
        user_id=user_id,
        content="I always delay starting tasks.",
        context_tags={"mood": "anxious"},
        error_tags=["procrastination"],
        severity=3,
        embedding=[0.1] * 1024
    )
    
    # Mock DB execution results
    # 1. Select fragment -> returns mock_fragment
    # 2. Select RAG -> returns list of fragments
    # 3. Select existing Pattern -> returns None (so we create new)
    
    # We use side_effect for execute to handle different queries if needed, 
    # but for simplicity, we can mock the scalar_one_or_none behavior.
    
    mock_result_scalar = MagicMock()
    mock_result_scalar.scalar_one_or_none.return_value = mock_fragment
    
    mock_result_scalars = MagicMock()
    mock_result_scalars.scalars.return_value.all.return_value = []
    
    # We need to distinguish between calls. 
    # First call is get fragment. Second is RAG. Third is Check Pattern.
    mock_db.execute.side_effect = [
        mock_result_scalar, # Get Fragment
        mock_result_scalars, # RAG
        # We need another one for _upsert_pattern check
        # But _upsert_pattern calls execute too.
    ]
    
    # Mock external services
    with patch("app.services.cognitive_service.settings.ANALYSIS_SYNC_ON_EVENT", False), \
         patch("app.services.llm_fallback_utils.cognitive_llm.json_call", new_callable=AsyncMock) as mock_llm, \
         patch("app.services.cognitive_service.AnalyticsService.get_user_profile_summary", new_callable=AsyncMock) as mock_analytics, \
         patch("app.services.cognitive_service.SystemUpdateService.enqueue", new_callable=AsyncMock), \
         patch("app.services.cognitive_service.event_bus.publish", new_callable=AsyncMock):
        
        mock_analytics.return_value = "User is a student."
        
        # LLM returns valid JSON
        llm_response = {
            "root_cause": "Fear of failure",
            "pattern_name": "Procrastination Loop",
            "pattern_type": "emotional",
            "description": "Avoiding tasks due to anxiety.",
            "solution_text": "Just start for 2 mins.",
            "confidence_score": 0.9
        }
        mock_llm.return_value = llm_response
        
        # Also need to mock _upsert_pattern internal DB calls if we don't mock the method itself.
        # It's better to test _upsert_pattern logic too.
        # So we need to handle the DB calls in _upsert_pattern.
        # Call 3: Select Pattern -> None
        
        mock_result_pattern_check = MagicMock()
        mock_result_pattern_check.scalar_one_or_none.return_value = None
        
        mock_db.execute.side_effect = [
            mock_result_scalar, # 1. Get Fragment
            mock_result_scalars, # 2. RAG
            mock_result_pattern_check # 3. Check Pattern (in _upsert_pattern)
        ]

        # Action
        result = await service.analyze_behavior(user_id, fragment_id)
        
        # Assert
        assert result["pattern_name"] == "Procrastination Loop"
        assert result["confidence_score"] == 0.9
        
        # Verify DB add was called (Pattern creation)
        assert mock_db.add.called
        # Check what was added
        args, _ = mock_db.add.call_args
        added_obj = args[0]
        assert isinstance(added_obj, BehaviorPattern)
        assert added_obj.pattern_name == "Procrastination Loop"
        assert added_obj.user_id == user_id
        assert added_obj.evidence_ids == [str(fragment_id)]
        
        assert mock_db.commit.called


@pytest.mark.asyncio
async def test_create_fragment_falls_back_when_vector_runtime_unavailable(monkeypatch):
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    service = CognitiveService(mock_db)

    monkeypatch.setattr(cognitive_service_module, "_VECTOR_RUNTIME_ENABLED", True)

    stored_fragment = CognitiveFragment(
        id=uuid4(),
        user_id=uuid4(),
        content="fallback fragment",
        source_type="behavior",
        resource_type="text",
        severity=2,
    )
    result_insert = MagicMock()
    result_select = MagicMock()
    result_select.scalar_one.return_value = stored_fragment
    mock_db.execute.side_effect = [result_insert, result_select]
    mock_db.commit.side_effect = [RuntimeError("vector.so unavailable"), None]

    with patch(
        "app.services.cognitive_service.embedding_service.get_embedding",
        new_callable=AsyncMock,
    ) as mock_embedding, patch(
        "app.services.cognitive_service.event_bus.publish",
        new_callable=AsyncMock,
    ), patch(
        "app.services.cognitive_service.SystemUpdateService.enqueue",
        new_callable=AsyncMock,
    ):
        mock_embedding.return_value = [0.0] * 1024
        fragment = await service.create_fragment(
            user_id=stored_fragment.user_id,
            content=stored_fragment.content,
            source_type=stored_fragment.source_type,
            severity=stored_fragment.severity,
        )

    assert fragment is stored_fragment
    mock_db.rollback.assert_awaited_once()
    assert mock_db.execute.await_count == 2
    assert cognitive_service_module._VECTOR_RUNTIME_ENABLED is True
    assert await service._is_vector_runtime_enabled_for_user(stored_fragment.user_id) is False


async def test_disable_vector_runtime_is_scoped_per_user(monkeypatch):
    monkeypatch.setattr(cognitive_service_module, "_VECTOR_RUNTIME_ENABLED", True)
    monkeypatch.setattr(cognitive_service_module, "_VECTOR_RUNTIME_DISABLED_USERS", {})

    user_a = uuid4()
    user_b = uuid4()

    await CognitiveService._disable_vector_runtime_for_user(user_a, "pgvector unavailable")

    assert await CognitiveService._is_vector_runtime_enabled_for_user(user_a) is False
    assert await CognitiveService._is_vector_runtime_enabled_for_user(user_b) is True
