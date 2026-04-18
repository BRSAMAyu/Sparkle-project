from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from app.aurora.profile_translator import build_user_correction_claim
from app.aurora.schemas import ClaimLifecycle, ClaimSource, IdentityEvidence, InsightClaim, SparkleRelationshipState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _maturity_label(maturity: float) -> str:
    if maturity < 0.2:
        return "exploring"
    if maturity < 0.45:
        return "forming"
    if maturity < 0.7:
        return "stable"
    return "trusted"


def _communication_style(
    claims: Iterable[InsightClaim],
    identity_evidence: Iterable[IdentityEvidence],
    interaction_metadata: dict[str, Any] | None,
) -> str:
    interaction_metadata = interaction_metadata or {}
    directness = float(interaction_metadata.get("directness", 0.0) or 0.0)
    warmth = float(interaction_metadata.get("warmth", 0.0) or 0.0)
    uncertainty = float(interaction_metadata.get("uncertainty", 0.0) or 0.0)
    evidence_strength = sum(max(0.0, min(1.0, item.strength)) for item in identity_evidence)
    confirmed_claims = sum(1 for claim in claims if claim.status in {ClaimLifecycle.CONFIRMED, ClaimLifecycle.CONTEXTUALIZED})

    if uncertainty >= 0.6 or evidence_strength < 0.3:
        return "gentle and exploratory"
    if directness >= 0.7 or confirmed_claims >= 2:
        return "direct and structured"
    if warmth >= 0.5:
        return "supportive and reflective"
    return "balanced and steady"


def _extract_highlights(claims: Iterable[InsightClaim], identity_evidence: Iterable[IdentityEvidence]) -> list[str]:
    highlights: list[str] = []
    for claim in claims:
        if claim.content.strip():
            highlights.append(_normalize_text(claim.content))
        if len(highlights) >= 2:
            break
    for item in identity_evidence:
        if len(highlights) >= 3:
            break
        if item.description.strip():
            highlights.append(_normalize_text(item.description))
    return highlights[:3]


@dataclass(slots=True)
class RelationshipDerivedView:
    state: SparkleRelationshipState
    maturity_label: str
    communication_style_label: str
    summary: str
    highlight_count: int


@dataclass(slots=True)
class ClaimContextualizationResult:
    correction_claim: InsightClaim
    contextualized_claim: InsightClaim
    context_note: str


class SparkleRelationshipStateManager:
    """Derive a profile-facing relationship state from existing claims and evidence."""

    def __init__(self) -> None:
        self._current_by_user_id: dict[UUID, SparkleRelationshipState] = {}

    def register(self, state: SparkleRelationshipState) -> SparkleRelationshipState:
        self._current_by_user_id[state.user_id] = state
        return state

    def current(self, user_id: UUID) -> SparkleRelationshipState | None:
        return self._current_by_user_id.get(user_id)

    def derive_state(
        self,
        *,
        user_id: UUID,
        claims: Iterable[InsightClaim] | None = None,
        identity_evidence: Iterable[IdentityEvidence] | None = None,
        interaction_metadata: dict[str, Any] | None = None,
        bound_policy_version: str = "aurora_policy@v1.0",
        last_interaction_at: datetime | None = None,
    ) -> SparkleRelationshipState:
        claim_list = list(claims or [])
        evidence_list = list(identity_evidence or [])
        interaction_metadata = interaction_metadata or {}
        directness = float(interaction_metadata.get("directness", 0.0) or 0.0)
        warmth = float(interaction_metadata.get("warmth", 0.0) or 0.0)
        interaction_count = int(interaction_metadata.get("interaction_count") or (len(claim_list) + len(evidence_list)))
        confidence_total = sum(claim.confidence for claim in claim_list)
        evidence_total = sum(max(0.0, min(1.0, item.strength)) for item in evidence_list)
        maturity = min(
            1.0,
            round(
                0.12 * len([claim for claim in claim_list if claim.status == ClaimLifecycle.CONFIRMED])
                + 0.08 * len([claim for claim in claim_list if claim.status == ClaimLifecycle.CONTEXTUALIZED])
                + 0.08 * len([claim for claim in claim_list if claim.source == ClaimSource.USER_CORRECTION])
                + 0.18 * evidence_total
                + 0.05 * max(0, interaction_count - 1)
                + 0.08 * directness
                + 0.05 * warmth
                + 0.05 * confidence_total,
                2,
            ),
        )

        state = SparkleRelationshipState(
            user_id=user_id,
            relationship_maturity=maturity,
            communication_style_emergent=_communication_style(claim_list, evidence_list, interaction_metadata),
            interaction_count=interaction_count,
            last_interaction_at=last_interaction_at or _utcnow(),
            shared_history_highlights=_extract_highlights(claim_list, evidence_list),
            bound_policy_version=bound_policy_version,
        )
        return self.register(state)

    def derive_view(
        self,
        *,
        user_id: UUID,
        claims: Iterable[InsightClaim] | None = None,
        identity_evidence: Iterable[IdentityEvidence] | None = None,
        interaction_metadata: dict[str, Any] | None = None,
        bound_policy_version: str = "aurora_policy@v1.0",
    ) -> RelationshipDerivedView:
        state = self.derive_state(
            user_id=user_id,
            claims=claims,
            identity_evidence=identity_evidence,
            interaction_metadata=interaction_metadata,
            bound_policy_version=bound_policy_version,
        )
        summary = (
            f"协作成熟度约 {state.relationship_maturity:.0%}，"
            f"当前风格更偏向 {state.communication_style_emergent or 'balanced and steady'}。"
            f" 系统保留了 {len(state.shared_history_highlights)} 条高频历史要点。"
        )
        return RelationshipDerivedView(
            state=state,
            maturity_label=_maturity_label(state.relationship_maturity),
            communication_style_label=state.communication_style_emergent or "balanced and steady",
            summary=summary,
            highlight_count=len(state.shared_history_highlights),
        )

    def contextualize_user_correction(
        self,
        original_claim: InsightClaim,
        *,
        correction_text: str,
        evidence_refs: Iterable[str] | None = None,
        context_note: str | None = None,
        created_at: datetime | None = None,
    ) -> ClaimContextualizationResult:
        correction_claim, contextualized_claim = build_user_correction_claim(
            original_claim,
            correction_text=correction_text,
            evidence_refs=evidence_refs,
            created_at=created_at,
        )
        note = context_note or "user_correction_contextualized"
        contextualized_claim = contextualized_claim.model_copy(
            update={
                "status": ClaimLifecycle.CONTEXTUALIZED,
                "updated_at": created_at or _utcnow(),
            }
        )
        return ClaimContextualizationResult(
            correction_claim=correction_claim,
            contextualized_claim=contextualized_claim,
            context_note=note,
        )

    def build_revert_view(
        self,
        original_claim: InsightClaim,
        contextualized_claim: InsightClaim,
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        projection_policy = getattr(original_claim, "projection_policy", None)
        projection_policy_value = projection_policy.value if hasattr(projection_policy, "value") else str(projection_policy)
        return {
            "claim_id": str(original_claim.id),
            "label": original_claim.claim_type,
            "before": original_claim.content,
            "after": contextualized_claim.content,
            "projection_policy": projection_policy_value,
            "reason": reason or "dialogue_mediated",
            "requires_dialogue": True,
            "no_silent_overwrite": True,
        }
