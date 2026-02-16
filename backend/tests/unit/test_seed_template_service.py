"""
Seed Template Service Unit Tests
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import settings
from app.models.seed_template import SeedTemplate, SeedTemplateVersion, TemplatePromotionState
from app.services.seed_template_service import SeedTemplateService


@pytest.fixture
def service() -> SeedTemplateService:
    return SeedTemplateService()


def test_quality_gate_missing_contract_fields(service: SeedTemplateService) -> None:
    report = service._quality_gate("goal: x\nconstraints: y")
    assert report["passed"] is False
    assert "acceptance_criteria" in report["missing"]


def test_moderation_gate_blocks_terms(service: SeedTemplateService) -> None:
    report = service._moderation_gate("这个模板包含诈骗内容")
    assert report["passed"] is False
    assert "诈骗" in report["blocked_terms"]


@pytest.mark.asyncio
async def test_evaluate_promotion_can_recommend(service: SeedTemplateService, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENABLE_SEED_TEMPLATE_AUTO_PROMOTION_V1", True)
    rows = [
        ("reuse", 8),
        ("adopt_success", 4),
        ("like", 8),
        ("downvote", 1),
        ("report", 0),
    ]
    mock_result = SimpleNamespace(all=lambda: rows)
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    promotion = await service._evaluate_promotion(mock_db, uuid4())

    assert promotion.support == 21
    assert promotion.promotion_state == TemplatePromotionState.PUBLIC_RECOMMENDED.value
    assert promotion.adoption_rate >= service.AUTO_PROMOTION_MIN_ADOPTION
    assert promotion.negative_feedback_rate <= service.AUTO_PROMOTION_MAX_NEGATIVE


@pytest.mark.asyncio
async def test_instantiate_collects_unresolved_and_metadata(service: SeedTemplateService) -> None:
    template = SeedTemplate(
        id=uuid4(),
        pack_id=uuid4(),
        name="Study Template",
        template_role="default",
        forked_from_template_id=uuid4(),
        is_official=False,
    )
    version = SeedTemplateVersion(
        id=uuid4(),
        template_id=template.id,
        version_no=1,
        status="published",
        body="goal:{goal};milestones:{milestones};owner:{owner}",
    )

    service._resolve_publish_version = AsyncMock(return_value=version)  # type: ignore[method-assign]

    _, rendered, unresolved, metadata = await service.instantiate(
        AsyncMock(),
        template=template,
        variables={"goal": "pass exam"},
        context={"owner": "alice"},
    )

    assert rendered == "goal:pass exam;milestones:{milestones};owner:alice"
    assert unresolved == ["milestones"]
    assert metadata["seed_template_source"] == "fork"
    assert metadata["seed_template_id"] == str(template.id)
    assert metadata["seed_template_version_id"] == str(version.id)


@pytest.mark.asyncio
async def test_list_subscriptions_filters_enabled(service: SeedTemplateService) -> None:
    enabled = SimpleNamespace(id=uuid4(), is_enabled=True)
    disabled = SimpleNamespace(id=uuid4(), is_enabled=False)
    mock_result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [enabled, disabled]))
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    rows = await service.list_subscriptions(
        mock_db,
        user_id=uuid4(),
        only_enabled=True,
        limit=10,
    )

    assert len(rows) == 2
    assert any(item.is_enabled for item in rows)
