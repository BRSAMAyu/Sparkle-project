from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_book import ErrorRecord
from app.models.task import TaskType
from app.schemas.error_book import RemediablePattern
from app.services.error_pattern_template_service import ErrorPatternTemplateService


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items


def _error_record(
    *,
    node_id=None,
    error_type: str = "concept_confusion",
    confidence: float = 0.82,
    mastery: float = 0.42,
    created_at: datetime | None = None,
    chapter: str = "函数",
) -> ErrorRecord:
    return ErrorRecord(
        id=uuid4(),
        user_id=uuid4(),
        subject_code="math",
        chapter=chapter,
        question_text="sample question",
        user_answer="wrong",
        correct_answer="right",
        latest_analysis={
            "error_type": error_type,
            "confidence": confidence,
            "root_cause": "把关键条件看成了充分条件",
        },
        affected_node_id=node_id,
        linked_knowledge_node_ids=[node_id] if node_id else [],
        mastery_level=mastery,
        review_count=1,
        created_at=created_at or _now(),
        updated_at=created_at or _now(),
        is_deleted=False,
    )


def _pattern(**overrides) -> RemediablePattern:
    node_id = overrides.pop("knowledge_node_id", uuid4())
    defaults = {
        "id": "pattern_123",
        "knowledge_node_id": node_id,
        "knowledge_node_name": "二次函数顶点",
        "error_type": "calculation_error",
        "error_type_label": "计算过程",
        "subject_code": "math",
        "chapter": "二次函数",
        "error_count": 4,
        "confidence": 0.87,
        "average_mastery": 0.38,
        "suggested_duration_minutes": 32,
        "root_cause_summary": "代入后没有验算符号",
        "representative_error_id": uuid4(),
        "error_ids": [uuid4(), uuid4(), uuid4(), uuid4()],
        "last_seen_at": _now(),
    }
    defaults.update(overrides)
    return RemediablePattern(**defaults)


@pytest.mark.asyncio
async def test_identify_remediable_patterns_clusters_by_node_and_error_type():
    user_id = uuid4()
    node_id = uuid4()
    records = [
        _error_record(node_id=node_id, created_at=_now() - timedelta(days=1)),
        _error_record(node_id=node_id, created_at=_now() - timedelta(days=2)),
        _error_record(node_id=node_id, created_at=_now() - timedelta(days=3)),
    ]
    for record in records:
        record.user_id = user_id

    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(records),
            _ScalarResult([SimpleNamespace(id=node_id, name="二次函数顶点")]),
        ]
    )

    patterns = await ErrorPatternTemplateService(db).identify_remediable_patterns(user_id)

    assert len(patterns) == 1
    assert patterns[0].knowledge_node_id == node_id
    assert patterns[0].knowledge_node_name == "二次函数顶点"
    assert patterns[0].error_type == "concept_confusion"
    assert patterns[0].error_count == 3
    assert patterns[0].confidence >= 0.6


@pytest.mark.asyncio
async def test_identify_remediable_patterns_filters_singletons():
    user_id = uuid4()
    record = _error_record()
    record.user_id = user_id

    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=_ScalarResult([record]))

    patterns = await ErrorPatternTemplateService(db).identify_remediable_patterns(user_id)

    assert patterns == []


def test_generate_task_template_contains_executable_plan_contract():
    db = MagicMock(spec=AsyncSession)
    template = ErrorPatternTemplateService(db).generate_task_template(_pattern())

    assert template.minimum_output
    assert template.success_criteria
    assert len(template.structured_steps) == 4
    assert template.guide_json["minimum_output"] == template.minimum_output
    assert template.guide_json["structured_steps"][0]["order"] == 1
    assert template.task_payload["type"] == TaskType.ERROR_FIX.value


def test_generate_task_template_specializes_calculation_steps():
    db = MagicMock(spec=AsyncSession)
    template = ErrorPatternTemplateService(db).generate_task_template(_pattern(error_type="calculation_error"))

    instructions = " ".join(step.instruction for step in template.structured_steps)
    assert "公式" in instructions
    assert "验算" in instructions


@pytest.mark.asyncio
async def test_accept_template_creates_task_from_matching_pattern():
    user_id = uuid4()
    pattern = _pattern()
    db = MagicMock(spec=AsyncSession)
    service = ErrorPatternTemplateService(db)
    fake_task = SimpleNamespace(id=uuid4(), title="补救练习")

    with (
        patch.object(service, "identify_remediable_patterns", AsyncMock(return_value=[pattern])),
        patch(
            "app.services.error_pattern_template_service.TaskService.create",
            AsyncMock(return_value=fake_task),
        ) as create_mock,
    ):
        task = await service.accept_template(user_id, pattern.id)

    assert task is fake_task
    task_create = create_mock.await_args.args[1]
    assert task_create.type == TaskType.ERROR_FIX
    assert task_create.knowledge_node_id == pattern.knowledge_node_id
    assert task_create.guide_json["pattern_id"] == pattern.id


@pytest.mark.asyncio
async def test_accept_template_raises_when_pattern_disappears():
    user_id = uuid4()
    db = MagicMock(spec=AsyncSession)
    service = ErrorPatternTemplateService(db)

    with patch.object(service, "identify_remediable_patterns", AsyncMock(return_value=[])):
        with pytest.raises(ValueError):
            await service.accept_template(user_id, "missing")
