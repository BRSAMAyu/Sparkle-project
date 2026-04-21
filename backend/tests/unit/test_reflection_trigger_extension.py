from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.card_protocol import InterventionAcceptanceStatus, InterventionOutcomeStatus, InterventionTriggerType
from app.services.card_protocol.outcome_verifier import InterventionOutcomeVerifier
from app.services.task_reflection_service import TaskReflectionService


def test_reflection_service_exposes_all_six_categories() -> None:
    assert TaskReflectionService.ELIGIBLE_CATEGORIES == {
        "too_difficult",
        "unclear",
        "abandoned",
        "intervention_ineffective",
        "plan_stall",
        "overload",
    }


def test_reflection_service_registers_new_prompt_templates() -> None:
    for category in ("intervention_ineffective", "plan_stall", "overload"):
        template = TaskReflectionService.PROMPT_TEMPLATES[category]
        assert template["question"]
        assert len(template["options"]) == 3


def test_outcome_verifier_derives_intervention_ineffective_trigger() -> None:
    record = SimpleNamespace(
        trigger_type=InterventionTriggerType.PLAN_RISK,
        acceptance_status=InterventionAcceptanceStatus.ACCEPTED,
    )

    category = InterventionOutcomeVerifier._derive_reflection_category(
        record,
        InterventionOutcomeStatus.INEFFECTIVE,
        {"improvement": {}},
    )

    assert category == "intervention_ineffective"


def test_outcome_verifier_derives_plan_stall_trigger() -> None:
    record = SimpleNamespace(
        trigger_type=InterventionTriggerType.STALL_PATTERN,
        acceptance_status=InterventionAcceptanceStatus.SEEN,
    )

    category = InterventionOutcomeVerifier._derive_reflection_category(
        record,
        InterventionOutcomeStatus.UNKNOWN,
        {"improvement": {"post_intervention_negative_feedback_count": 2}},
    )

    assert category == "plan_stall"


def test_outcome_verifier_derives_overload_trigger() -> None:
    record = SimpleNamespace(
        trigger_type=InterventionTriggerType.OVERLOAD,
        acceptance_status=InterventionAcceptanceStatus.SEEN,
    )

    category = InterventionOutcomeVerifier._derive_reflection_category(
        record,
        InterventionOutcomeStatus.UNKNOWN,
        {"improvement": {"post_intervention_negative_feedback_count": 1}},
    )

    assert category == "overload"


@pytest.mark.asyncio
async def test_trigger_handle_skips_when_category_toggle_is_disabled(db_session, monkeypatch) -> None:
    service = TaskReflectionService(db_session)
    monkeypatch.setattr(service.kill_switch, "is_trigger_enabled", AsyncMock(return_value=False))

    result = await service.handle_triggered_reflection(
        user_id=uuid4(),
        category="plan_stall",
        trigger_payload={},
    )

    assert result["reason"] == "category_disabled"


@pytest.mark.asyncio
async def test_trigger_handle_skips_when_on_cooldown(db_session, monkeypatch) -> None:
    service = TaskReflectionService(db_session)
    monkeypatch.setattr(service.kill_switch, "is_trigger_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr(service, "_trigger_on_cooldown", AsyncMock(return_value=True))

    result = await service.handle_triggered_reflection(
        user_id=uuid4(),
        category="overload",
        trigger_payload={},
    )

    assert result["reason"] == "cooldown"


@pytest.mark.asyncio
async def test_trigger_handle_skips_when_wire_mode_is_off(db_session, monkeypatch) -> None:
    service = TaskReflectionService(db_session)
    monkeypatch.setattr(service.kill_switch, "is_trigger_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr(service, "_trigger_on_cooldown", AsyncMock(return_value=False))
    monkeypatch.setattr(service.kill_switch, "get_mode", AsyncMock(return_value="off"))

    result = await service.handle_triggered_reflection(
        user_id=uuid4(),
        category="intervention_ineffective",
        trigger_payload={},
    )

    assert result["reason"] == "off"
