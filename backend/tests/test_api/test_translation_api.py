import pytest
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.translation import router
from app.api.deps import get_current_user_id, get_db
from app.tools.base import ToolResult


app = FastAPI()
app.include_router(router, prefix="/api/v1/translation")

USER_ID = str(uuid4())


@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def override_deps(mock_db):
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    app.dependency_overrides[get_db] = lambda: mock_db
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_translate_success_contract_and_compat_fields(override_deps):
    """
    Ensure the translation API returns the contract Flutter expects and that
    source_language / target_language compatibility fields are honored.
    """
    tool_result = ToolResult(
        success=True,
        tool_name="translate",
        data={
            "translation": "你好 世界",
            "source_lang": "en",
            "target_lang": "zh-CN",
            "provider": "siliconflow",
            "cache_hit": False,
            "latency_ms": 123,
            "segments": [
                {"id": "s0", "translation": "你好", "notes": []},
                {"id": "s1", "translation": "世界", "notes": ["world = 世界"]},
            ],
            "recommendation": {
                "should_create_card": True,
                "reason": "repeated_query",
                "daily_quota_remaining": 7,
            },
        },
    )

    with patch(
        "app.api.v1.translation.TranslateTextTool.execute",
        AsyncMock(return_value=tool_result),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/translation/translate",
                json={
                    "text": "Hello world",
                    # Compatibility fields (should override defaults)
                    "source_language": "en",
                    "target_language": "zh-CN",
                    "domain": "general",
                    "style": "natural",
                },
            )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["translation"] == "你好 世界"
    assert data["meta"]["source_lang"] == "en"
    assert data["meta"]["target_lang"] == "zh-CN"
    assert data["meta"]["provider"] == "siliconflow"
    assert data["meta"]["latency_ms"] == 123
    assert len(data["segments"]) == 2
    assert data["segments"][1]["notes"] == ["world = 世界"]
    assert data["recommendation"]["should_create_card"] is True


@pytest.mark.asyncio
async def test_translate_failure_surfaces_meta_error(override_deps):
    """Ensure failure responses place the error under meta.error."""
    tool_result = ToolResult(
        success=False,
        tool_name="translate",
        error_message="Upstream translation failure",
    )

    with patch(
        "app.api.v1.translation.TranslateTextTool.execute",
        AsyncMock(return_value=tool_result),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/translation/translate",
                json={
                    "text": "Hello",
                    "source_lang": "en",
                    "target_lang": "zh-CN",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["meta"]["error"] == "Upstream translation failure"
