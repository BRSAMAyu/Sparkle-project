from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.aurora.engine import AuroraDecisionContext, AuroraEngine
from app.aurora.profile_translator import ProfileProjectionContext, ProfileTranslator
from app.aurora.relationship_state import SparkleRelationshipStateManager
from app.aurora.schemas import (
    ClaimLifecycle,
    ClaimSource,
    Commitment,
    CommitmentStatus,
    FocusContract,
    IdentityEvidence,
    ProjectionPolicy,
    SignalSnapshot,
    WindowMode,
    WindowState,
    WritePath,
)
from app.graph.runtime import GraphRuntime
from app.learning.attributor import AttributionSignalBundle
from app.learning.pipeline import run_continuous_learning_pipeline
from app.learning.retrieval import RetrievalQueryInput, build_distilled_strategy_refs
from app.learning.strategy_store import DistilledStrategyStore
from app.scenario_packs.registry import load_default_registry
from app.social.accountability import PartnerReportInput, build_partner_report_claim


def _manifest():
    registry = load_default_registry()
    manifest = registry.get_by_id("exam_prep_14d@v1.0")
    assert manifest is not None
    return manifest


def _runtime(user_id: UUID, *, active_node: str = "day2_prerequisite_map") -> GraphRuntime:
    runtime = GraphRuntime(_manifest())
    runtime.bootstrap(
        focus_contract=FocusContract(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            user_id=user_id,
            version=2,
            scenario_pack_id="exam_prep_14d@v1.0",
            active_node=active_node,
            focus_description=f"Acceptance focus at {active_node}",
            desire_hypothesis="希望把备考节奏真正锁定下来",
            commitment_ids=[UUID("33333333-3333-3333-3333-333333333333")],
            created_at=datetime(2026, 4, 19, 9, 0, 0),
            created_by="aurora",
            evidence_refs=["acceptance-bootstrap"],
            write_path=WritePath.SYSTEM_INTERNAL,
        ),
        commitments=[
            Commitment(
                id=UUID("33333333-3333-3333-3333-333333333333"),
                user_id=user_id,
                description="锁定接下来 7 天的复习骨架",
                node_id=active_node,
                success_criteria="每日最小行动 + 晚间复盘持续执行",
                status=CommitmentStatus.ACTIVE,
                created_at=datetime(2026, 4, 18, 20, 0, 0),
                activated_at=datetime(2026, 4, 18, 20, 15, 0),
                deadline=datetime(2026, 4, 26, 23, 59, 0),
                evidence_refs=["acceptance-commitment"],
                window_override=WindowMode.COMMITMENT,
            )
        ],
        window_state=WindowState(
            id=uuid4(),
            user_id=user_id,
            created_at=datetime(2026, 4, 19, 8, 30, 0),
            global_mode=WindowMode.COMMITMENT,
            set_by="aurora",
        ),
    )
    return runtime


def _identity_evidence(user_id: UUID, description: str, *, strength: float = 0.72) -> IdentityEvidence:
    return IdentityEvidence(
        id=uuid4(),
        user_id=user_id,
        created_at=datetime(2026, 4, 19, 10, 30, 0),
        dimension="behavior",
        evidence_type="pattern",
        description=description,
        strength=strength,
        valence="positive",
        source=ClaimSource.BEHAVIORAL_SIGNAL,
        projection_policy=ProjectionPolicy.OPEN_DISCUSSABLE,
    )


def test_acceptance_loop_conversational_modeling_drives_graph_and_profile_projection() -> None:
    user_id = uuid4()
    runtime = _runtime(user_id)
    engine = AuroraEngine()
    _manifest()  # ensure the current production pack is available

    signal_snapshot = SignalSnapshot(
        snapshot_hash="ss_acceptance_profile",
        user_id=user_id,
        collected_at=datetime(2026, 4, 19, 10, 0, 0),
        scenario_pack_id="exam_prep_14d@v1.0",
        policy_version="aurora_policy@v1.0",
        core_signals={
            "user_message": "帮我把这周复习锁下来，我更适合先把节奏规划清楚。",
            "commitment_conflict": "考试提前了，原计划需要压缩",
        },
        enhanced_signals={"task_completion_7d": 0.8},
        optional_signals={"conversation_phase": "modeling"},
        total_tokens=1100,
        budget_limit=4000,
    )

    decision = engine.safe_route(
        AuroraDecisionContext(
            snapshot=signal_snapshot,
            trigger_point="pre-node-routing",
            current_node="day2_prerequisite_map",
            candidate_node="day3_schedule_lock",
            policy_version=engine.load_policy("v1.0"),
            mode="shadow",
        )
    )
    graph_result = runtime.apply_decision(decision, snapshot=signal_snapshot)

    partner_claim = build_partner_report_claim(
        PartnerReportInput(
            reporter_id=uuid4(),
            user_id=user_id,
            partnership_id=uuid4(),
            summary="他这周明显更能稳定推进，适合继续维持结构化节奏。",
            confidence=0.78,
            evidence_refs=("checkin-a",),
        )
    ).claim

    relationship_manager = SparkleRelationshipStateManager()
    relationship_state = relationship_manager.derive_state(
        user_id=user_id,
        claims=[
            partner_claim,
            partner_claim.model_copy(
                update={
                    "id": uuid4(),
                    "source": ClaimSource.USER_REPORT,
                    "content": "我最近更适合先把节奏和步骤定清楚。",
                    "status": ClaimLifecycle.CONFIRMED,
                    "projection_policy": ProjectionPolicy.OPEN_EDITABLE,
                }
            ),
        ],
        identity_evidence=[
            _identity_evidence(user_id, "连续 5 天按计划推进"),
            _identity_evidence(user_id, "在晚间复盘里持续说明自己更偏好结构化反馈", strength=0.8),
        ],
        interaction_metadata={"interaction_count": 7, "directness": 0.76, "warmth": 0.42},
    )
    projection = ProfileTranslator().translate(
        [
            partner_claim.model_copy(update={"projection_policy": ProjectionPolicy.SENSITIVE_MEDIATED}),
            partner_claim.model_copy(
                update={
                    "id": uuid4(),
                    "source": ClaimSource.USER_REPORT,
                    "content": "我最近更适合先把节奏和步骤定清楚。",
                    "status": ClaimLifecycle.CONFIRMED,
                    "projection_policy": ProjectionPolicy.OPEN_EDITABLE,
                }
            ),
        ],
        [
            _identity_evidence(user_id, "连续 5 天按计划推进"),
            _identity_evidence(user_id, "在晚间复盘里持续说明自己更偏好结构化反馈", strength=0.8),
        ],
        relationship_state=relationship_state,
        context=ProfileProjectionContext(allow_sensitive_mediation=False),
    )

    assert decision.decision_type == "transition"
    assert graph_result.current_node_id == "day3_schedule_lock"
    assert relationship_state.communication_style_emergent == "direct and structured"
    assert projection.visible_claims
    assert all(item.projection_policy != ProjectionPolicy.INTERNAL.value for item in projection.visible_claims)
    assert "结构化" in projection.summary or "节奏" in projection.summary


@pytest.mark.usefixtures("monkeypatch")
@pytest.mark.asyncio
async def test_acceptance_loop_can_attach_social_and_learning_sidecars_without_new_endpoints(
    monkeypatch: pytest.MonkeyPatch,
    db_session,
) -> None:
    monkeypatch.setenv("SPARKLE_WS7_DISTILLER_ENABLED", "true")
    monkeypatch.setenv("SPARKLE_WS7_RETRIEVAL_ENABLED", "true")

    user_id = uuid4()
    runtime = _runtime(user_id, active_node="day5_error_repair")
    engine = AuroraEngine()
    signal_snapshot = SignalSnapshot(
        snapshot_hash="ss_acceptance_learning",
        user_id=user_id,
        collected_at=datetime(2026, 4, 19, 11, 0, 0),
        scenario_pack_id="exam_prep_14d@v1.0",
        policy_version="aurora_policy@v1.0",
        core_signals={"partner_report": {"severity": "medium", "summary": "状态稳住了，可以继续"}},
        enhanced_signals={"task_completion_4d": 1.0},
        optional_signals={"conversation_phase": "review"},
        total_tokens=1200,
        budget_limit=4000,
    )

    decision = engine.safe_route(
        AuroraDecisionContext(
            snapshot=signal_snapshot,
            trigger_point="pre-node-routing",
            current_node="day5_error_repair",
            candidate_node="day6_targeted_drill",
            policy_version=engine.load_policy("v1.0"),
            mode="shadow",
        )
    )
    graph_result = runtime.apply_decision(decision, snapshot=signal_snapshot)

    social_claim = build_partner_report_claim(
        PartnerReportInput(
            reporter_id=uuid4(),
            user_id=user_id,
            partnership_id=uuid4(),
            summary="状态稳住了，可以继续推进 targeted drill。",
            confidence=0.82,
            evidence_refs=("partner-review-1",),
        )
    ).claim

    session_factory = async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    store = DistilledStrategyStore(session_factory)
    pipeline_result = await run_continuous_learning_pipeline(
        AttributionSignalBundle(
            user_id=user_id,
            scenario_pack_id="exam_prep_14d",
            goal_achieved=True,
            task_completion_streak=4,
            positive_feedback_score=0.84,
            behavioral_improvement_score=0.76,
            outcome_summary="通过把 nightly review 缩成固定 10 分钟，用户稳定坚持了 targeted drill。",
            interventions=["nightly review", "targeted drill"],
            context_excerpt="用户通过固定晚间复盘把 targeted drill 稳住了。",
            subject_tags=["physics", "exam"],
            source_refs=["task:acceptance-1", "feedback:acceptance-1"],
        ),
        store,
    )
    refs = await build_distilled_strategy_refs(
        RetrievalQueryInput(text="targeted drill nightly review"),
        store,
    )

    assert decision.decision_type == "transition"
    assert graph_result.current_node_id == "day6_targeted_drill"
    assert social_claim.source == ClaimSource.PARTNER_REPORT
    assert social_claim.projection_policy == ProjectionPolicy.INTERNAL
    assert pipeline_result.status == "created"
    assert refs
    # WS8 keeps this bounded on current seams: retrieval refs exist, but no production
    # snapshot assembler writes them yet, so we assert the sidecar output directly.
    assert await store.list()
