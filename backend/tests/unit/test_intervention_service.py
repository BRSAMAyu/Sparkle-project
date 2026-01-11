from datetime import datetime, timezone

from app.schemas.intervention import (
    EvidenceRef,
    InterventionLevel,
    InterventionReason,
    InterventionRequestCreate,
)
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
    expired = datetime.utcnow()
    payload = _build_payload(expires_at=expired)
    errors = service.validate_contract(payload)
    assert "expired_request" in errors


def test_is_quiet_hours_handles_wraparound():
    service = InterventionService(db=None)
    quiet_hours = {"start": "22:00", "end": "07:00", "timezone": "UTC"}
    late = datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc)
    noon = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert service._is_quiet_hours(late, quiet_hours) is True
    assert service._is_quiet_hours(noon, quiet_hours) is False
