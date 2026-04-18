from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.aurora.schemas import Commitment, CommitmentStatus, WindowMode
from app.social.accountability import (
    AccountabilityPartnerConfig,
    AccountabilityPartnerSupportService,
    PartnerReportInput,
    PartnerVisibilityRole,
    bind_witness_ids,
    build_partner_inactivity_recovery_protocol,
    build_partner_report_claim,
    build_ritualized_checkin_plan,
    filter_commitment_visibility,
    unbind_witness_ids,
)


def _build_commitment(*, witness_ids: list[UUID] | None = None) -> Commitment:
    return Commitment(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        user_id=UUID("22222222-2222-2222-2222-222222222222"),
        description="完成前五章并复盘",
        node_id="day3",
        success_criteria="完成题目并整理错因",
        status=CommitmentStatus.ACTIVE,
        created_at=datetime(2026, 4, 17, 9, 0, 0),
        activated_at=datetime(2026, 4, 17, 9, 15, 0),
        deadline=datetime(2026, 4, 30, 23, 59, 0),
        milestone_ids=[UUID("44444444-4444-4444-4444-444444444444")],
        witness_ids=witness_ids or [],
        window_override=WindowMode.COMMITMENT,
        evidence_refs=["commitment-evidence"],
    )


def test_commitment_witness_binding_and_unbinding_is_append_safe() -> None:
    partner_a = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    partner_b = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    commitment = _build_commitment(witness_ids=[partner_a])

    bound = bind_witness_ids(commitment, [partner_b, partner_a])
    unbound = unbind_witness_ids(bound, [partner_a])

    assert commitment.witness_ids == [partner_a]
    assert bound.witness_ids == [partner_a, partner_b]
    assert unbound.witness_ids == [partner_b]


def test_partner_report_bridge_produces_internal_insight_claim() -> None:
    report = PartnerReportInput(
        reporter_id=uuid4(),
        user_id=uuid4(),
        partnership_id=uuid4(),
        summary="今天对方连续三次按时完成",
        confidence=0.84,
        evidence_refs=("checkin-1", "checkin-2"),
        metadata={"tone": "encouraging"},
    )

    result = build_partner_report_claim(report)

    assert result.applied is True
    assert result.input_path == "aurora.claims.partner_report"
    assert result.claim.source.value == "partner_report"
    assert result.claim.projection_policy.value == "internal"
    assert result.claim.write_path.value == "system_internal"
    assert result.claim.shareability.value == "private_only"
    assert result.claim.content == "今天对方连续三次按时完成"


def test_ritualized_check_in_plan_includes_weekly_and_milestone_boundaries() -> None:
    commitment = _build_commitment()
    plan = build_ritualized_checkin_plan(
        commitment,
        reference_time=datetime(2026, 4, 17, 9, 0, 0),
        milestone_schedule={
            UUID("44444444-4444-4444-4444-444444444444"): datetime(2026, 4, 20, 18, 0, 0),
        },
        config=AccountabilityPartnerConfig(enabled=True, check_in_interval_days=7, reminder_lead_hours=12),
    )

    assert plan.enabled is True
    assert plan.cadence_days == 7
    assert [item.kind for item in plan.items] == ["cadence", "milestone", "cadence"]
    assert plan.items[0].due_at == datetime(2026, 4, 17, 9, 0, 0)
    assert plan.items[1].milestone_id == UUID("44444444-4444-4444-4444-444444444444")


def test_partner_inactivity_recovery_emits_claim_after_threshold() -> None:
    protocol = build_partner_inactivity_recovery_protocol(
        partnership_id=uuid4(),
        partner_id=uuid4(),
        last_seen_at=datetime(2026, 4, 1, 9, 0, 0),
        threshold_days=7,
        reference_time=datetime(2026, 4, 10, 9, 0, 0),
    )

    assert protocol is not None
    assert protocol.recovery_claim.source.value == "system_sensor"
    assert protocol.recovery_claim.claim_type == "partner_inactive"
    assert "9 days" in protocol.recovery_claim.content
    assert protocol.next_action.startswith("surface recovery claim")


def test_partner_visibility_filter_redacts_raw_commitment_details_for_partner() -> None:
    commitment = _build_commitment()
    progress_summary = {"completed": 3, "total": 5, "label": "X completed 3/5 tasks this week"}

    owner_view = filter_commitment_visibility(commitment, viewer_role=PartnerVisibilityRole.OWNER)
    partner_view = filter_commitment_visibility(
        commitment,
        viewer_role=PartnerVisibilityRole.PARTNER,
        progress_summary=progress_summary,
    )

    assert owner_view["description"] == "完成前五章并复盘"
    assert "description" not in partner_view
    assert partner_view["progress_summary"] == progress_summary
    assert partner_view["visibility_mode"] == "partner_summary_only"


def test_service_defaults_to_inert_mode_until_flag_is_enabled() -> None:
    service = AccountabilityPartnerSupportService(AccountabilityPartnerConfig(enabled=False))
    commitment = _build_commitment(witness_ids=[uuid4()])
    report = PartnerReportInput(reporter_id=uuid4(), user_id=commitment.user_id, summary="note")

    bridged = service.bridge_partner_report(report)
    bound = service.bind_witnesses(commitment, [uuid4()])
    plan = service.build_checkin_plan(commitment)

    assert service.enabled is False
    assert bridged.applied is False
    assert bound.witness_ids == commitment.witness_ids
    assert plan.enabled is False
