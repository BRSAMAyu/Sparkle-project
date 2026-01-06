import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI

from app.api.v1.error_book import router
from app.api.deps import get_current_user_id, get_db
from app.schemas.error_book import SubjectEnum
# Import models to ensure they are registered in SQLAlchemy mapper
from app.models.audit_log import SecurityAuditLog
from app.models.user import User
from app.models.error_book import ErrorRecord

# Create a minimal app for testing the router in isolation
app = FastAPI()
app.include_router(router, prefix="/api/v1")

# Mock data
USER_ID = str(uuid4())

@pytest.fixture
def mock_db():
    db = MagicMock(spec=AsyncSession)
    return db

@pytest.fixture
def override_deps(mock_db):
    # Use dependency_overrides on the local app instance
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    app.dependency_overrides[get_db] = lambda: mock_db
    yield
    app.dependency_overrides = {}

from datetime import datetime

@pytest.mark.asyncio
async def test_create_error_api(override_deps, mock_db):
    """测试创建错题接口"""
    # Mock database behavior
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    
    async def mock_refresh(obj):
        obj.id = uuid4()
        obj.created_at = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
        # Also need these fields which are expected by ErrorRecordResponse
        obj.suggested_concepts = []
        obj.knowledge_links = []
        obj.subject_code = "math" # Needed for subject mapping
        
    mock_db.refresh = AsyncMock(side_effect=mock_refresh)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/errors",
            json={
                "question_text": "Api Test Question",
                "subject": "math",
                "cognitive_tags": ["analysis"],
                "ai_analysis_summary": "API test summary"
            }
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["question_text"] == "Api Test Question"
    assert data["cognitive_tags"] == ["analysis"]
    assert data["ai_analysis_summary"] == "API test summary"

@pytest.mark.asyncio
async def test_list_errors_with_cognitive_filter_api(override_deps, mock_db):
    """测试按认知维度筛选列表接口"""
    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = []
    
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 0
    
    # execute is called twice: once for count, once for items
    mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_items_result])
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/errors",
            params={"cognitive_dimension": "analysis"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 0

@pytest.mark.asyncio
async def test_create_error_invalid_cognitive_tag_api(override_deps):
    """测试无效认知标签时的验证"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/errors",
            json={
                "question_text": "Invalid Tag Question",
                "subject": "math",
                "cognitive_tags": ["invalid_tag"]
            }
        )
    
    assert response.status_code == 422