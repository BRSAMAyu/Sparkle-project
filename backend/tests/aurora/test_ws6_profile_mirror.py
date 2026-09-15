from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.aurora.profile_translator import (
    ProfileProjectionContext,
    ProfileTranslator,
    build_user_correction_claim,
    filter_claims_by_projection_policy,
)
from app.aurora.relationship_state import SparkleRelationshipStateManager
from app.aurora.schemas import ClaimLifecycle, ClaimSource, IdentityEvidence, InsightClaim, ProjectionPolicy


def _claim(
    *,
    claim_type: str,
    content: str,
    source: ClaimSource,
    projection_policy: ProjectionPolicy,
    confidence: float = 0.7,
    status: ClaimLifecycle = ClaimLifecycle.OPEN,
) -> InsightClaim:
    now = datetime(2026, 4, 18, 10, 0, 0)
    return InsightClaim(
        id=uuid4(),
        user_id=uuid4(),
        created_at=now,
        updated_at=now,
        claim_type=claim_type,
        content=content,
        source=source,
        confidence=confidence,
        status=status,
        projection_policy=projection_policy,
    )


def _evidence(description: str, *, strength: float = 0.6) -> IdentityEvidence:
    now = datetime(2026, 4, 18, 10, 30, 0)
    return IdentityEvidence(
        id=uuid4(),
        user_id=uuid4(),
        created_at=now,
        dimension="behavior",
        evidence_type="pattern",
        description=description,
        strength=strength,
        valence="positive",
        source=ClaimSource.BEHAVIORAL_SIGNAL,
    )


def test_profile_translator_filters_projection_policy_and_builds_readable_summary() -> None:
    user_id = uuid4()
    open_claim = _claim(
        claim_type="focus",
        content="你最近在学习上比较自律，连续完成了计划。",
        source=ClaimSource.USER_REPORT,
        projection_policy=ProjectionPolicy.OPEN_EDITABLE,
    )
    open_claim = open_claim.model_copy(update={"user_id": user_id, "evidence_refs": ["e1"]})
    mediated_claim = _claim(
        claim_type="energy",
        content="近期能量波动较大，需要在对话里慢慢校准。",
        source=ClaimSource.AURORA_INFERENCE,
        projection_policy=ProjectionPolicy.SENSITIVE_MEDIATED,
    ).model_copy(update={"user_id": user_id, "evidence_refs": ["e2"]})
    internal_claim = _claim(
        claim_type="internal_note",
        content="仅供系统内部调试使用。",
        source=ClaimSource.SYSTEM_SENSOR,
        projection_policy=ProjectionPolicy.INTERNAL,
    ).model_copy(update={"user_id": user_id, "evidence_refs": ["e3"]})

    translator = ProfileTranslator()
    result = translator.translate(
        [open_claim, mediated_claim, internal_claim],
        [_evidence("最近连续五天完成计划"), _evidence("保持固定节奏")],
        context=ProfileProjectionContext(allow_sensitive_mediation=False),
    )

    assert "连续完成了计划" in result.summary
    assert len(result.visible_claims) == 1
    assert len(result.mediated_claims) == 1
    assert len(result.hidden_claims) == 1
    assert all(item.projection_policy != ProjectionPolicy.INTERNAL.value for item in result.visible_claims)
    assert "internal" in result.policy_notes[0]

    mediated_result = translator.translate(
        [open_claim, mediated_claim, internal_claim],
        context=ProfileProjectionContext(allow_sensitive_mediation=True, include_internal=False),
    )
    assert len(mediated_result.visible_claims) == 2
    assert mediated_result.hidden_claims and mediated_result.hidden_claims[0].projection_policy == ProjectionPolicy.INTERNAL.value


def test_projection_policy_filter_excludes_internal_claims() -> None:
    claims = [
        _claim(
            claim_type="user_note",
            content="可见内容",
            source=ClaimSource.USER_REPORT,
            projection_policy=ProjectionPolicy.OPEN_DISCUSSABLE,
        ),
        _claim(
            claim_type="internal_note",
            content="不可见内容",
            source=ClaimSource.SYSTEM_SENSOR,
            projection_policy=ProjectionPolicy.INTERNAL,
        ),
    ]

    filtered = filter_claims_by_projection_policy(claims, context=ProfileProjectionContext())

    assert len(filtered) == 1
    assert filtered[0].projection_policy == ProjectionPolicy.OPEN_DISCUSSABLE


def test_relationship_state_manager_derives_state_and_contextualizes_user_correction() -> None:
    user_id = uuid4()
    manager = SparkleRelationshipStateManager()
    claims = [
        _claim(
            claim_type="focus",
            content="你更喜欢提前规划。",
            source=ClaimSource.USER_REPORT,
            projection_policy=ProjectionPolicy.OPEN_EDITABLE,
            status=ClaimLifecycle.CONFIRMED,
        ).model_copy(update={"user_id": user_id}),
        _claim(
            claim_type="style",
            content="系统观察到你更倾向于结构化反馈。",
            source=ClaimSource.AURORA_INFERENCE,
            projection_policy=ProjectionPolicy.OPEN_DISCUSSABLE,
            status=ClaimLifecycle.CONTEXTUALIZED,
        ).model_copy(update={"user_id": user_id}),
    ]
    evidence = [
        _evidence("过去一周的任务完成率较稳", strength=0.8).model_copy(update={"user_id": user_id}),
        _evidence("你对提醒更偏好提前提示", strength=0.7).model_copy(update={"user_id": user_id}),
    ]

    state = manager.derive_state(
        user_id=user_id,
        claims=claims,
        identity_evidence=evidence,
        interaction_metadata={"directness": 0.8, "warmth": 0.4, "interaction_count": 6},
    )
    view = manager.derive_view(
        user_id=user_id,
        claims=claims,
        identity_evidence=evidence,
        interaction_metadata={"directness": 0.8, "warmth": 0.4, "interaction_count": 6},
    )
    correction = manager.contextualize_user_correction(
        claims[0],
        correction_text="我最近状态其实不错，节奏比之前更稳。",
        evidence_refs=["user-correction-1"],
    )

    assert state.relationship_maturity > 0
    assert state.communication_style_emergent in {"direct and structured", "supportive and reflective", "balanced and steady", "gentle and exploratory"}
    assert view.maturity_label in {"forming", "stable", "trusted"}
    assert view.highlight_count >= 1
    assert correction.correction_claim.source == ClaimSource.USER_CORRECTION
    assert correction.contextualized_claim.status == ClaimLifecycle.CONTEXTUALIZED
    assert "user-correction-1" in correction.contextualized_claim.evidence_refs

    revert_view = manager.build_revert_view(claims[0], correction.contextualized_claim)
    assert revert_view["no_silent_overwrite"] is True
    assert revert_view["requires_dialogue"] is True
    assert revert_view["before"] == claims[0].content
    assert revert_view["after"] == correction.contextualized_claim.content


def test_build_user_correction_claim_keeps_original_contextualized() -> None:
    original = _claim(
        claim_type="energy",
        content="你最近容易疲惫。",
        source=ClaimSource.AURORA_INFERENCE,
        projection_policy=ProjectionPolicy.SENSITIVE_MEDIATED,
    )

    correction_claim, contextualized_claim = build_user_correction_claim(
        original,
        correction_text="我最近其实状态不错，只是作息略晚。",
        evidence_refs=["evidence-a"],
    )

    assert correction_claim.source == ClaimSource.USER_CORRECTION
    assert correction_claim.projection_policy == original.projection_policy
    assert contextualized_claim.status == ClaimLifecycle.CONTEXTUALIZED
    assert "evidence-a" in contextualized_claim.evidence_refs
