
import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.error_book_service import ErrorBookService
from app.schemas.error_book import ErrorRecordCreate, ErrorQueryParams, SubjectEnum
from app.models.error_book import ErrorRecord
# Import models to ensure they are registered in SQLAlchemy mapper
from app.models.audit_log import SecurityAuditLog
from app.models.user import User

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
        obj.created_at = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
    
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
