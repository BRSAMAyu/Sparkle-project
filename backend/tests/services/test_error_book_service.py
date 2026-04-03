
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import timezone, datetime
from sqlalchemy.ext.asyncio import AsyncSession

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


from app.services.error_book_service import ErrorBookService
from app.schemas.error_book import ErrorRecordCreate, ErrorQueryParams, ReviewPerformanceEnum, SubjectEnum
from app.models.error_book import ErrorRecord
# Import models to ensure they are registered in SQLAlchemy mapper
from app.models.audit_log import SecurityAuditLog
from app.models.user import User


class _AsyncNullContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_create_error_with_cognitive_tags():
    """测试创建带有认知标签的错题"""
    db_mock = MagicMock(spec=AsyncSession)
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()
    
    service = ErrorBookService(db_mock)
    user_id = uuid4()
    
    create_data = ErrorRecordCreate(
        question_text="Test Question",
        subject=SubjectEnum.MATH,
        cognitive_tags=["analysis", "memory"],
        ai_analysis_summary="This is a test analysis summary"
    )
    
    # Mock behavior of refresh to set ID and other fields
    async def mock_refresh(obj):
        obj.id = uuid4()
        obj.created_at = _utcnow()
        obj.updated_at = _utcnow()
    
    db_mock.refresh.side_effect = mock_refresh
    
    result = await service.create_error(user_id, create_data)
    
    assert result.user_id == user_id
    assert result.cognitive_tags == ["analysis", "memory"]
    assert result.ai_analysis_summary == "This is a test analysis summary"
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()

@pytest.mark.asyncio
async def test_list_errors_filtering_by_cognitive_dimension():
    """测试按认知维度筛选错题列表"""
    db_mock = MagicMock(spec=AsyncSession)
    db_mock.execute = AsyncMock()
    
    service = ErrorBookService(db_mock)
    user_id = uuid4()
    
    # Test filtering by 'analysis'
    params = ErrorQueryParams(cognitive_dimension="analysis")
    
    # Mock execute result for items and count
    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = []
    
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 0
    
    db_mock.execute.side_effect = [mock_count_result, mock_items_result]
    
    items, total = await service.list_errors(user_id, params)
    
    assert total == 0
    assert items == []
    
    # Verify the query assembly (we'd need more complex mocking to verify the SQL clauses perfectly,
    # but checking that execute was called twice is a good start)
    assert db_mock.execute.call_count == 2

@pytest.mark.asyncio
async def test_update_error_cognitive_tags():
    """测试更新错题的认知标签"""
    from app.schemas.error_book import ErrorRecordUpdate
    
    db_mock = MagicMock(spec=AsyncSession)
    db_mock.execute = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()
    
    service = ErrorBookService(db_mock)
    user_id = uuid4()
    error_id = uuid4()
    
    # Mock existing record
    # Avoid instantiating ErrorRecord directly if it causes mapper issues, 
    # but here we need it for result verification.
    # We use a simple mock object that looks like ErrorRecord if real one fails.
    existing_error = MagicMock(spec=ErrorRecord)
    existing_error.id = error_id
    existing_error.user_id = user_id
    existing_error.cognitive_tags = ["memory"]
    existing_error.ai_analysis_summary = None
    existing_error.is_deleted = False
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_error
    db_mock.execute.return_value = mock_result
    
    update_data = ErrorRecordUpdate(
        cognitive_tags=["analysis"],
        ai_analysis_summary="Updated summary"
    )
    
    result = await service.update_error(error_id, user_id, update_data)
    
    assert result is not None
    assert result.cognitive_tags == ["analysis"]
    assert result.ai_analysis_summary == "Updated summary"
    db_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_and_link_publishes_event_without_links():
    """即使没有关联知识点，也应该发布 error_created 事件以驱动画像回流。"""
    db_mock = MagicMock(spec=AsyncSession)
    db_mock.execute = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.rollback = AsyncMock()
    db_mock.begin_nested = MagicMock(return_value=_AsyncNullContext())

    service = ErrorBookService(db_mock)
    user_id = uuid4()
    error_id = uuid4()

    error = MagicMock(spec=ErrorRecord)
    error.id = error_id
    error.user_id = user_id
    error.question_text = "What does pointer dereference return?"
    error.question_image_url = None
    error.user_answer = "address"
    error.correct_answer = "value"
    error.subject_code = "computer"
    error.latest_analysis = None
    error.linked_knowledge_node_ids = []

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = error
    db_mock.execute.return_value = mock_result

    with patch.object(service, "_search_knowledge_nodes", AsyncMock(return_value=[])), \
         patch.object(
             service,
             "_run_llm_analysis",
             AsyncMock(
                 return_value={
                     "error_type": "concept_confusion",
                     "error_type_label": "概念混淆",
                     "root_cause": "把地址和值混淆了",
                     "correct_approach": "先解引用再读取值",
                     "similar_traps": [],
                     "recommended_knowledge": [],
                     "study_suggestion": "回看指针与引用",
                 }
             ),
         ), \
         patch("app.services.error_book_service.event_bus.publish", new=AsyncMock()) as mock_publish, \
         patch("app.services.error_book_service.SemanticMemoryService") as mock_semantic:
        mock_semantic.return_value.upsert_strategy_from_error = AsyncMock()
        await service.analyze_and_link(error_id, user_id)

    mock_publish.assert_awaited_once()
    event_type, payload = mock_publish.await_args.args
    assert event_type == "error_created"
    assert payload["error_id"] == str(error_id)
    assert payload["linked_node_ids"] == []


@pytest.mark.asyncio
async def test_analyze_and_link_flushes_node_mastery_events_after_commit():
    db_mock = MagicMock(spec=AsyncSession)
    db_mock.execute = AsyncMock()
    db_mock.rollback = AsyncMock()
    db_mock.begin_nested = MagicMock(return_value=_AsyncNullContext())

    timeline: list[str] = []
    commit_count = {"value": 0}

    async def _commit():
        commit_count["value"] += 1
        timeline.append(f"commit{commit_count['value']}")

    db_mock.commit = AsyncMock(side_effect=_commit)

    service = ErrorBookService(db_mock)
    user_id = uuid4()
    error_id = uuid4()
    linked_node_id = uuid4()

    error = MagicMock(spec=ErrorRecord)
    error.id = error_id
    error.user_id = user_id
    error.question_text = "What does pointer dereference return?"
    error.question_image_url = None
    error.user_answer = "address"
    error.correct_answer = "value"
    error.subject_code = "computer"
    error.latest_analysis = None
    error.linked_knowledge_node_ids = []

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = error
    db_mock.execute.return_value = mock_result

    linked_node = MagicMock()
    linked_node.id = linked_node_id

    mastery_result = [{
        "_pending_event": {
            "topic": "node_mastery_updated",
            "payload": {"event_type": "node_mastery_updated", "node_id": str(linked_node_id)},
        }
    }]

    async def _publish(topic, payload):
        timeline.append(topic)

    with patch.object(service, "_search_knowledge_nodes", AsyncMock(return_value=[linked_node])), \
         patch.object(
             service,
             "_run_llm_analysis",
             AsyncMock(
                 return_value={
                     "error_type": "concept_confusion",
                     "error_type_label": "概念混淆",
                     "root_cause": "把地址和值混淆了",
                     "correct_approach": "先解引用再读取值",
                     "similar_traps": [],
                     "recommended_knowledge": [],
                     "study_suggestion": "回看指针与引用",
                 }
             ),
         ), \
         patch("app.services.error_book_service.event_bus.publish", new=AsyncMock(side_effect=_publish)), \
         patch("app.services.error_book_service.SemanticMemoryService") as mock_semantic, \
         patch("app.services.error_book_signal_processor.ErrorBookSignalProcessor") as mock_processor, \
         patch("app.services.error_book_mastery_sync_service.ErrorBookMasterySyncService") as mock_mastery:
        mock_semantic.return_value.upsert_strategy_from_error = AsyncMock()
        mock_processor.return_value.process_error_created = AsyncMock()
        mock_mastery.return_value.apply_error_diagnosis = AsyncMock(return_value=mastery_result)
        await service.analyze_and_link(error_id, user_id)

    assert "node_mastery_updated" in timeline
    assert "error_created" in timeline
    assert timeline.index("commit2") < timeline.index("node_mastery_updated")


@pytest.mark.asyncio
async def test_search_knowledge_nodes_keyword_fallback_when_vector_search_unavailable():
    """向量检索不可用时，错题服务应退回关键词检索而不是整条链失败。"""
    db_mock = MagicMock(spec=AsyncSession)
    db_mock.execute = AsyncMock()
    db_mock.begin_nested = MagicMock(return_value=_AsyncNullContext())

    service = ErrorBookService(db_mock)
    user_id = uuid4()
    node = MagicMock(spec=ErrorRecord)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [node]
    db_mock.execute.return_value = mock_result

    with patch(
        "app.services.error_book_service.embedding_service.get_embedding",
        new=AsyncMock(side_effect=RuntimeError("pgvector unavailable")),
    ):
        results = await service._search_knowledge_nodes(user_id, "牛顿第二定律 受力分析")

    assert results == [node]
    db_mock.execute.assert_awaited_once()


def test_review_scheduler_caps_easiness_factor_growth():
    service = ErrorBookService(MagicMock(spec=AsyncSession))

    _, new_ef, _, _ = service.review_scheduler.calculate_next_review(
        current_mastery=0.9,
        easiness_factor=2.5,
        interval_days=30.0,
        review_count=8,
        performance=ReviewPerformanceEnum.REMEMBERED,
    )

    assert new_ef == 2.5
