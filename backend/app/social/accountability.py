"""Accountability-partner support primitives for WS9.

This module stays intentionally write-free. It only prepares deterministic
inputs and filtered views for the existing Aurora and community layers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence
from uuid import UUID, uuid4

from app.aurora.schemas import (
    ClaimLifecycle,
    ClaimSource,
    Commitment,
    InsightClaim,
    ProjectionPolicy,
    Shareability,
    WindowMode,
    WritePath,
)

_WS9_FLAG_ENV = "SPARKLE_WS9_ACCOUNTABILITY_ENABLED"


class PartnerVisibilityRole(str, Enum):
    """Who is looking at the accountability surface."""

    OWNER = "owner"
    PARTNER = "partner"
    OBSERVER = "observer"


@dataclass(frozen=True, slots=True)
class AccountabilityPartnerConfig:
    """Feature flag and deterministic timing controls for WS9."""

    enabled: bool = False
    inactivity_threshold_days: int = 7
    check_in_interval_days: int = 7
    reminder_lead_hours: int = 24
    default_confidence: float = 0.72


@dataclass(frozen=True, slots=True)
class PartnerReportInput:
    """Normalized partner observation before Aurora claim conversion."""

    reporter_id: UUID
    user_id: UUID
    partnership_id: UUID | None = None
    summary: str = ""
    claim_type: str = "partner_report"
    confidence: float | None = None
    observed_at: datetime | None = None
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: "PartnerReportInput | Mapping[str, Any]") -> "PartnerReportInput":
        if isinstance(value, PartnerReportInput):
            return value
        payload = dict(value)
        reporter_id = UUID(str(payload["reporter_id"]))
        user_id = UUID(str(payload["user_id"]))
        partnership_id = payload.get("partnership_id")
        return cls(
            reporter_id=reporter_id,
            user_id=user_id,
            partnership_id=UUID(str(partnership_id)) if partnership_id is not None else None,
            summary=str(payload.get("summary") or payload.get("message") or "").strip(),
            claim_type=str(payload.get("claim_type") or "partner_report"),
            confidence=_coerce_confidence(payload.get("confidence")),
            observed_at=_coerce_datetime(payload.get("observed_at")),
            evidence_refs=tuple(str(item) for item in payload.get("evidence_refs") or ()),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class PartnerClaimBridgeResult:
    """Aurora-compatible claim plus provenance about the input path."""

    claim: InsightClaim
    input_path: str
    applied: bool
    reason: str
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CheckInScheduleItem:
    """Single deterministic check-in reminder."""

    due_at: datetime
    kind: str
    label: str
    milestone_id: UUID | None = None
    reminder_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RitualizedCheckInPlan:
    """Bounded weekly cadence for partner-supported check-ins."""

    commitment_id: UUID
    enabled: bool
    cadence_days: int
    items: tuple[CheckInScheduleItem, ...]
    rationale: str


@dataclass(frozen=True, slots=True)
class PartnerRecoveryProtocol:
    """Deterministic fallback when a partner has gone inactive."""

    partnership_id: UUID | None
    partner_id: UUID
    inactive_since: datetime
    threshold_days: int
    recovery_claim: InsightClaim
    next_action: str
    visibility_hint: dict[str, Any] = field(default_factory=dict)


def is_ws9_accountability_enabled(config: AccountabilityPartnerConfig | None = None) -> bool:
    """Return whether the partner layer should actively emit behavior."""

    if config is not None:
        return config.enabled
    raw = os.getenv(_WS9_FLAG_ENV, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def bind_witness_ids(commitment: Commitment, witness_ids: Sequence[UUID]) -> Commitment:
    """Return a new commitment with witness IDs bound in order."""

    merged = _unique_uuid_list([*commitment.witness_ids, *witness_ids])
    return commitment.model_copy(update={"witness_ids": merged})


def unbind_witness_ids(commitment: Commitment, witness_ids: Sequence[UUID]) -> Commitment:
    """Return a new commitment with the requested witnesses removed."""

    remove = {str(item) for item in witness_ids}
    remaining = [item for item in commitment.witness_ids if str(item) not in remove]
    return commitment.model_copy(update={"witness_ids": remaining})


def build_partner_report_claim(
    report: PartnerReportInput | Mapping[str, Any],
    *,
    claim_id: UUID | None = None,
    created_at: datetime | None = None,
    confidence_override: float | None = None,
) -> PartnerClaimBridgeResult:
    """Convert a partner report into an Aurora-compatible InsightClaim."""

    normalized = PartnerReportInput.from_value(report)
    observed_at = normalized.observed_at or created_at or _utcnow()
    confidence = confidence_override
    if confidence is None:
        confidence = normalized.confidence if normalized.confidence is not None else 0.72
    claim = InsightClaim(
        id=claim_id or uuid4(),
        user_id=normalized.user_id,
        created_at=observed_at,
        updated_at=observed_at,
        claim_type=normalized.claim_type,
        content=normalized.summary or "partner observation",
        source=ClaimSource.PARTNER_REPORT,
        confidence=float(confidence),
        status=ClaimLifecycle.OPEN,
        evidence_refs=list(normalized.evidence_refs),
        projection_policy=ProjectionPolicy.INTERNAL,
        write_path=WritePath.SYSTEM_INTERNAL,
        shareability=Shareability.PRIVATE_ONLY,
    )
    return PartnerClaimBridgeResult(
        claim=claim,
        input_path="aurora.claims.partner_report",
        applied=True,
        reason="partner_report_bridged_into_claim_input",
        provenance={
            "reporter_id": str(normalized.reporter_id),
            "partnership_id": str(normalized.partnership_id) if normalized.partnership_id else None,
            "metadata": dict(normalized.metadata),
        },
    )


def build_ritualized_checkin_plan(
    commitment: Commitment,
    *,
    reference_time: datetime | None = None,
    milestone_schedule: Mapping[UUID, datetime] | None = None,
    config: AccountabilityPartnerConfig | None = None,
) -> RitualizedCheckInPlan:
    """Create deterministic weekly and milestone-bound partner check-in reminders."""

    normalized_reference = _coerce_datetime(reference_time) or commitment.activated_at or commitment.created_at
    if normalized_reference.tzinfo is not None:
        normalized_reference = normalized_reference.astimezone(UTC).replace(tzinfo=None)
    cadence_days = max(1, (config or AccountabilityPartnerConfig()).check_in_interval_days)
    milestone_schedule = milestone_schedule or {}

    items: list[CheckInScheduleItem] = []
    cursor = normalized_reference
    while cursor <= commitment.deadline:
        due_at = cursor
        reminder_at = due_at - timedelta(hours=(config or AccountabilityPartnerConfig()).reminder_lead_hours)
        items.append(
            CheckInScheduleItem(
                due_at=due_at,
                reminder_at=reminder_at,
                kind="cadence",
                label=f"{cadence_days}-day ritualized check-in",
            )
        )
        cursor = cursor + timedelta(days=cadence_days)

    for milestone_id in commitment.milestone_ids:
        milestone_at = milestone_schedule.get(milestone_id)
        if milestone_at is None:
            continue
        if milestone_at.tzinfo is not None:
            milestone_at = milestone_at.astimezone(UTC).replace(tzinfo=None)
        items.append(
            CheckInScheduleItem(
                due_at=milestone_at,
                reminder_at=milestone_at - timedelta(hours=(config or AccountabilityPartnerConfig()).reminder_lead_hours),
                kind="milestone",
                label="milestone-bound check-in",
                milestone_id=milestone_id,
            )
        )

    ordered = tuple(_dedupe_schedule_items(items))
    return RitualizedCheckInPlan(
        commitment_id=commitment.id,
        enabled=is_ws9_accountability_enabled(config),
        cadence_days=cadence_days,
        items=ordered,
        rationale="weekly cadence anchored to commitment window with milestone reminders layered on top",
    )


def build_partner_inactivity_recovery_protocol(
    *,
    partnership_id: UUID | None,
    partner_id: UUID,
    last_seen_at: datetime,
    threshold_days: int = 7,
    reference_time: datetime | None = None,
    config: AccountabilityPartnerConfig | None = None,
    visibility_hint: dict[str, Any] | None = None,
) -> PartnerRecoveryProtocol | None:
    """Emit a deterministic recovery protocol when partner inactivity crosses threshold."""

    current_time = _coerce_datetime(reference_time) or _utcnow()
    observed_at = _coerce_datetime(last_seen_at)
    if observed_at.tzinfo is not None:
        observed_at = observed_at.astimezone(UTC).replace(tzinfo=None)

    inactive_for = current_time - observed_at
    threshold = max(1, threshold_days)
    if inactive_for < timedelta(days=threshold):
        return None

    claim_created_at = current_time
    claim = InsightClaim(
        id=uuid4(),
        user_id=partner_id,
        created_at=claim_created_at,
        updated_at=claim_created_at,
        claim_type="partner_inactive",
        content=f"partner inactive for {inactive_for.days} days",
        source=ClaimSource.SYSTEM_SENSOR,
        confidence=0.91,
        status=ClaimLifecycle.OPEN,
        evidence_refs=[f"last_seen_at:{observed_at.isoformat()}"],
        projection_policy=ProjectionPolicy.INTERNAL,
        write_path=WritePath.SYSTEM_INTERNAL,
        shareability=Shareability.PRIVATE_ONLY,
    )
    return PartnerRecoveryProtocol(
        partnership_id=partnership_id,
        partner_id=partner_id,
        inactive_since=observed_at,
        threshold_days=threshold,
        recovery_claim=claim,
        next_action="surface recovery claim to Aurora and offer a gentle rebind flow",
        visibility_hint=visibility_hint or {"surface": "owner_only", "reason": "partner_inactive"},
    )


def filter_commitment_visibility(
    commitment: Commitment,
    *,
    viewer_role: PartnerVisibilityRole,
    progress_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Application-layer visibility filter for accountability partner surfaces."""

    payload = commitment.model_dump(mode="json")
    if viewer_role == PartnerVisibilityRole.OWNER:
        return payload

    redacted = {
        "id": payload["id"],
        "user_id": payload["user_id"],
        "status": payload["status"],
        "node_id": payload["node_id"],
        "deadline": payload["deadline"],
        "window_override": payload.get("window_override"),
        "witness_count": len(commitment.witness_ids),
        "milestone_count": len(commitment.milestone_ids),
        "progress_summary": dict(progress_summary or {}),
        "visibility_mode": "partner_summary_only",
    }
    if viewer_role == PartnerVisibilityRole.OBSERVER:
        redacted["visibility_mode"] = "observer_summary_only"
    return redacted


class AccountabilityPartnerSupportService:
    """Convenience orchestrator with inert-by-default behavior."""

    def __init__(self, config: AccountabilityPartnerConfig | None = None) -> None:
        self.config = config or AccountabilityPartnerConfig()

    @property
    def enabled(self) -> bool:
        return is_ws9_accountability_enabled(self.config)

    def bind_witnesses(self, commitment: Commitment, witness_ids: Sequence[UUID]) -> Commitment:
        if not self.enabled:
            return commitment
        return bind_witness_ids(commitment, witness_ids)

    def unbind_witnesses(self, commitment: Commitment, witness_ids: Sequence[UUID]) -> Commitment:
        if not self.enabled:
            return commitment
        return unbind_witness_ids(commitment, witness_ids)

    def bridge_partner_report(
        self,
        report: PartnerReportInput | Mapping[str, Any],
        *,
        claim_id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> PartnerClaimBridgeResult:
        result = build_partner_report_claim(report, claim_id=claim_id, created_at=created_at)
        if self.enabled:
            return result
        return PartnerClaimBridgeResult(
            claim=result.claim,
            input_path=result.input_path,
            applied=False,
            reason="ws9_feature_flag_disabled",
            provenance=result.provenance,
        )

    def build_checkin_plan(
        self,
        commitment: Commitment,
        *,
        reference_time: datetime | None = None,
        milestone_schedule: Mapping[UUID, datetime] | None = None,
    ) -> RitualizedCheckInPlan:
        plan = build_ritualized_checkin_plan(
            commitment,
            reference_time=reference_time,
            milestone_schedule=milestone_schedule,
            config=self.config,
        )
        return plan

    def build_recovery_protocol(
        self,
        *,
        partnership_id: UUID | None,
        partner_id: UUID,
        last_seen_at: datetime,
        threshold_days: int | None = None,
        reference_time: datetime | None = None,
        visibility_hint: dict[str, Any] | None = None,
    ) -> PartnerRecoveryProtocol | None:
        return build_partner_inactivity_recovery_protocol(
            partnership_id=partnership_id,
            partner_id=partner_id,
            last_seen_at=last_seen_at,
            threshold_days=threshold_days or self.config.inactivity_threshold_days,
            reference_time=reference_time,
            config=self.config,
            visibility_hint=visibility_hint,
        )

    def filter_commitment(
        self,
        commitment: Commitment,
        *,
        viewer_role: PartnerVisibilityRole,
        progress_summary: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return filter_commitment_visibility(
            commitment,
            viewer_role=viewer_role,
            progress_summary=progress_summary,
        )


def _unique_uuid_list(values: Iterable[UUID]) -> list[UUID]:
    seen: set[str] = set()
    ordered: list[UUID] = []
    for value in values:
        value_str = str(value)
        if value_str in seen:
            continue
        seen.add(value_str)
        ordered.append(value)
    return ordered


def _dedupe_schedule_items(items: Iterable[CheckInScheduleItem]) -> list[CheckInScheduleItem]:
    seen: set[tuple[str, str | None]] = set()
    ordered: list[CheckInScheduleItem] = []
    for item in sorted(items, key=lambda entry: (entry.due_at, entry.kind, entry.label)):
        key = (item.due_at.isoformat(), str(item.milestone_id) if item.milestone_id else None)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def _coerce_confidence(value: Any) -> float | None:
    if value is None:
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, confidence))


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
