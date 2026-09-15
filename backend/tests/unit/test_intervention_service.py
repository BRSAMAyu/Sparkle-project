from datetime import UTC, datetime


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


import pytest
from sqlalchemy import select

from app.models.card_protocol import (
    CardLifecycleStatus,
    CardType,
    InterventionRecord,
    InterventionTriggerType,
)
from app.schemas.intervention import (
    EvidenceRef,
    InterventionLevel,
    InterventionReason,
    InterventionRequestCreate,
)
from app.services.card_service import CardService
from app.services.intervention_service import InterventionService


def _build_payload(confidence: float = 0.9, with_evidence: bool = True, expires_at=None):
    evidence = [EvidenceRef(type="event", id="evt_1")] if with_evidence else []
    reason = InterventionReason(
        explanation_text="Based on recent errors.",
        confidence=confidence,
        evidence_refs=evidence,
        decision_trace=["errors=2"],
    )
    return InterventionRequestCreate(
        topic="review",
        reason=reason,
        level=InterventionLevel.CARD,
        expires_at=expires_at,
    )


def test_validate_contract_requires_evidence_and_confidence():
    service = InterventionService(db=None)
    payload = _build_payload(confidence=0.1, with_evidence=False)
    errors = service.validate_contract(payload)
    assert "missing_evidence" in errors
    assert "low_confidence" in errors


def test_validate_contract_rejects_expired():
    service = InterventionService(db=None)
    expired = _utcnow()
    payload = _build_payload(expires_at=expired)
    errors = service.validate_contract(payload)
    assert "expired_request" in errors


def test_is_quiet_hours_handles_wraparound():
    service = InterventionService(db=None)
    quiet_hours = {"start": "22:00", "end": "07:00", "timezone": "UTC"}
    late = datetime(2026, 1, 1, 23, 0, tzinfo=UTC)
    noon = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert service._is_quiet_hours(late, quiet_hours) is True
    assert service._is_quiet_hours(noon, quiet_hours) is False


@pytest.mark.asyncio
async def test_card_protocol_dual_write_records_adaptive_intervention(db_session, test_user):
    plan_card = await CardService(db_session).create_card(
        card_type=CardType.PLAN,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"name": "Intervention tracked plan"},
        lifecycle_status=CardLifecycleStatus.ACTIVE,
    )
    await db_session.commit()

    service = InterventionService(db_session)
    request = await service.create_request(
        actor_id=test_user.id,
        actor_is_admin=False,
        payload=_build_payload(),
        default_timezone="UTC",
    )
    record = await service._record_card_protocol_intervention(
        request=request,
        user_id=test_user.id,
        trigger_event="aurora_plan_risk",
        urgency=0.7,
        context={
            "plan_card_id": str(plan_card.id),
            "edge_state_id": "aurora-risk-1",
            "explanation": "计划风险上升",
        },
        intent_type="supportive_prompt",
        delivery_method="websocket",
        content_version="variant-a",
    )

    assert record is not None
    assert record.plan_card_id == plan_card.id
    assert record.trigger_type == InterventionTriggerType.PLAN_RISK
    assert record.trigger_source_ref == "aurora-risk-1"
    assert record.diagnosis_payload["legacy_intervention_request_id"] == str(request.id)

    await db_session.refresh(request)
    assert request.content["card_protocol_intervention_record_id"] == str(record.id)

    persisted = (
        await db_session.execute(
            select(InterventionRecord).where(InterventionRecord.id == record.id)
        )
    ).scalar_one()
    assert persisted.content_version == "variant-a"
