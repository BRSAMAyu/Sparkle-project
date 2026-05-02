from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.api.v1.error_book import error_book_router
from app.models.task import TaskStatus, TaskType
from app.schemas.error_book import RemediablePattern, StructuredRemediationStep, TaskTemplate

USER_ID = uuid4()


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _app(mock_db):
    app = FastAPI()
    app.include_router(error_book_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user_id] = lambda: str(USER_ID)
    app.dependency_overrides[get_db] = lambda: mock_db
    return app


def _pattern() -> RemediablePattern:
    return RemediablePattern(
        id="pattern_abc",
        knowledge_node_id=uuid4(),
        knowledge_node_name="二次函数顶点",
        error_type="calculation_error",
        error_type_label="计算过程",
        subject_code="math",
        chapter="二次函数",
        error_count=3,
        confidence=0.82,
        average_mastery=0.41,
        suggested_duration_minutes=32,
        root_cause_summary="符号代入后没有验算",
        representative_error_id=uuid4(),
        error_ids=[uuid4(), uuid4(), uuid4()],
        last_seen_at=_now(),
    )


def _template(pattern: RemediablePattern) -> TaskTemplate:
    return TaskTemplate(
        pattern_id=pattern.id,
        title="补救练习：二次函数顶点 · 计算过程",
        objective="修复重复错因",
        estimated_minutes=32,
        difficulty=3,
        knowledge_node_id=pattern.knowledge_node_id,
        error_type=pattern.error_type,
        success_criteria=["能解释错因"],
        minimum_output="完成 1 张错因对照卡",
        structured_steps=[
            StructuredRemediationStep(
                order=1,
                title="定位错因",
                instruction="标出错误一步",
                duration_minutes=5,
                checkpoint="能指出错误开始的位置",
            )
        ],
        guide_json={"minimum_output": "完成 1 张错因对照卡"},
        task_payload={"title": "补救练习：二次函数顶点 · 计算过程"},
    )


@pytest.mark.asyncio
async def test_remediable_patterns_endpoint_returns_patterns():
    mock_db = MagicMock(spec=AsyncSession)
    app = _app(mock_db)
    pattern = _pattern()

    with patch(
        "app.services.error_pattern_template_service.ErrorPatternTemplateService.identify_remediable_patterns",
        AsyncMock(return_value=[pattern]),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/error-book/remediable-patterns")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["id"] == "pattern_abc"
    assert data[0]["error_count"] == 3


@pytest.mark.asyncio
async def test_generate_template_endpoint_returns_preview():
    mock_db = MagicMock(spec=AsyncSession)
    app = _app(mock_db)
    pattern = _pattern()
    template = _template(pattern)

    with (
        patch(
            "app.services.error_pattern_template_service.ErrorPatternTemplateService.identify_remediable_patterns",
            AsyncMock(return_value=[pattern]),
        ),
        patch(
            "app.services.error_pattern_template_service.ErrorPatternTemplateService.generate_task_template",
            MagicMock(return_value=template),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/error-book/patterns/pattern_abc/generate-template")

    assert response.status_code == 200
    data = response.json()
    assert data["pattern_id"] == "pattern_abc"
    assert data["minimum_output"] == "完成 1 张错因对照卡"


@pytest.mark.asyncio
async def test_accept_template_endpoint_creates_task():
    mock_db = MagicMock(spec=AsyncSession)
    app = _app(mock_db)
    now = _now()
    task = SimpleNamespace(
        id=uuid4(),
        created_at=now,
        updated_at=now,
        title="补救练习：二次函数顶点 · 计算过程",
        type=TaskType.ERROR_FIX,
        status=TaskStatus.PENDING,
        tags=["error_book"],
        estimated_minutes=32,
        difficulty=3,
        energy_cost=2,
        priority=64,
        due_date=None,
        user_id=USER_ID,
        plan_id=None,
        guide_content="修复重复错因",
        started_at=None,
        confirmed_at=None,
        completed_at=None,
        actual_minutes=None,
        user_note=None,
        knowledge_node_id=uuid4(),
        tool_result_id=None,
        execution_mode=None,
        order_index=0,
        subtasks_total=0,
        subtasks_completed=0,
        guide_json={"minimum_output": "完成 1 张错因对照卡"},
        ai_prompt=None,
        source_planning_session_id=None,
        phase_index=None,
        success_criteria="能解释错因",
    )

    with patch(
        "app.services.error_pattern_template_service.ErrorPatternTemplateService.accept_template",
        AsyncMock(return_value=task),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/error-book/patterns/pattern_abc/accept-template")

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "补救练习：二次函数顶点 · 计算过程"
    assert data["status"] == TaskStatus.PENDING.value


@pytest.mark.asyncio
async def test_generate_template_endpoint_404_for_missing_pattern():
    mock_db = MagicMock(spec=AsyncSession)
    app = _app(mock_db)

    with patch(
        "app.services.error_pattern_template_service.ErrorPatternTemplateService.identify_remediable_patterns",
        AsyncMock(return_value=[]),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/error-book/patterns/missing/generate-template")

    assert response.status_code == 404
