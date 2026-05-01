from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from collections.abc import Callable, Iterable
from uuid import uuid4

from app.aurora.schemas import ClaimLifecycle, ClaimSource, IdentityEvidence, InsightClaim, ProjectionPolicy, SparkleRelationshipState


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _coerce_projection_policy(value: ProjectionPolicy | str | None) -> ProjectionPolicy:
    if isinstance(value, ProjectionPolicy):
        return value
    if value is None:
        return ProjectionPolicy.INTERNAL
    try:
        return ProjectionPolicy(str(value))
    except ValueError:
        return ProjectionPolicy.INTERNAL


def _policy_visibility(policy: ProjectionPolicy, *, allow_sensitive_mediation: bool, include_internal: bool) -> str:
    if policy == ProjectionPolicy.INTERNAL:
        return "visible" if include_internal else "hidden"
    if policy == ProjectionPolicy.SENSITIVE_MEDIATED:
        return "visible" if allow_sensitive_mediation else "mediated"
    return "visible"


def _claim_label(claim: InsightClaim | dict[str, Any]) -> str:
    if isinstance(claim, InsightClaim):
        claim_type = claim.claim_type
        content = claim.content
    else:
        claim_type = str(claim.get("claim_type") or claim.get("type") or "profile")
        content = str(claim.get("content") or "")

    claim_type = claim_type.strip() or "profile"
    content = content.strip()
    if content:
        return f"{claim_type}: {content}"
    return claim_type


def _claim_summary_text(
    claim: InsightClaim,
    *,
    evidence_count: int,
    relationship_state: SparkleRelationshipState | None = None,
) -> str:
    source_hint = {
        ClaimSource.USER_REPORT: "来自你的直接表述",
        ClaimSource.USER_CORRECTION: "来自你的纠正",
        ClaimSource.BEHAVIORAL_SIGNAL: "来自行为信号",
        ClaimSource.SYSTEM_SENSOR: "来自系统观测",
        ClaimSource.PARTNER_REPORT: "来自协作伙伴反馈",
        ClaimSource.AURORA_INFERENCE: "来自系统推断",
    }.get(claim.source, "来自混合信号")

    base = claim.content.strip() or claim.claim_type.replace("_", " ")
    if relationship_state is not None and relationship_state.relationship_maturity >= 0.7:
        maturity_hint = "当前协作关系较稳定，系统会更谨慎地对待新的偏差判断。"
    elif relationship_state is not None and relationship_state.relationship_maturity >= 0.35:
        maturity_hint = "系统已积累到一定的协作历史，部分判断可以用更连续的方式呈现。"
    else:
        maturity_hint = "目前仍以轻量校准为主，系统会优先保留可讨论空间。"

    evidence_hint = f"有 {evidence_count} 条证据支撑。" if evidence_count else "当前没有额外证据。"
    return f"{base}。{source_hint}，{evidence_hint}{maturity_hint}"


@dataclass(slots=True)
class ProfileProjectionContext:
    surface: str = "transparent_profile"
    allow_sensitive_mediation: bool = False
    include_internal: bool = False
    dialogue_context: str | None = None


@dataclass(slots=True)
class ProfileClaimView:
    claim_id: str
    label: str
    summary: str
    projection_policy: str
    source: str
    status: str
    confidence: float
    visibility: str
    can_edit_directly: bool
    can_revert: bool
    evidence_refs: tuple[str, ...] = ()
    mediation_note: str | None = None


@dataclass(slots=True)
class ProfileRevertAction:
    claim_id: str
    label: str
    current_summary: str
    suggested_summary: str
    reason: str
    projection_policy: str
    requires_dialogue: bool = True


@dataclass(slots=True)
class ProfileTranslationResult:
    summary: str
    visible_claims: list[ProfileClaimView] = field(default_factory=list)
    mediated_claims: list[ProfileClaimView] = field(default_factory=list)
    hidden_claims: list[ProfileClaimView] = field(default_factory=list)
    revert_actions: list[ProfileRevertAction] = field(default_factory=list)
    policy_notes: list[str] = field(default_factory=list)
    relationship_snapshot: dict[str, Any] = field(default_factory=dict)


class ProfileTranslator:
    """Translate claims and evidence into a human-readable transparent profile."""

    def filter_claims(
        self,
        claims: Iterable[InsightClaim | dict[str, Any]],
        *,
        context: ProfileProjectionContext | None = None,
    ) -> list[InsightClaim | dict[str, Any]]:
        context = context or ProfileProjectionContext()
        selected: list[InsightClaim | dict[str, Any]] = []
        for claim in claims:
            policy = _coerce_projection_policy(getattr(claim, "projection_policy", None) if isinstance(claim, InsightClaim) else claim.get("projection_policy"))
            visibility = _policy_visibility(
                policy,
                allow_sensitive_mediation=context.allow_sensitive_mediation,
                include_internal=context.include_internal,
            )
            if visibility == "hidden":
                continue
            selected.append(claim)
        return selected

    def translate(
        self,
        claims: Iterable[InsightClaim | dict[str, Any]],
        evidence: Iterable[IdentityEvidence | dict[str, Any]] | None = None,
        *,
        relationship_state: SparkleRelationshipState | None = None,
        context: ProfileProjectionContext | None = None,
        llm_summarizer: Callable[[str], str] | None = None,
    ) -> ProfileTranslationResult:
        context = context or ProfileProjectionContext()
        evidence_list = list(evidence or [])
        claim_list = list(claims)

        visible_claims: list[ProfileClaimView] = []
        mediated_claims: list[ProfileClaimView] = []
        hidden_claims: list[ProfileClaimView] = []
        revert_actions: list[ProfileRevertAction] = []

        for raw_claim in claim_list:
            claim = raw_claim if isinstance(raw_claim, InsightClaim) else InsightClaim(**dict(raw_claim))
            policy = _coerce_projection_policy(getattr(claim, "projection_policy", None))
            visibility = _policy_visibility(
                policy,
                allow_sensitive_mediation=context.allow_sensitive_mediation,
                include_internal=context.include_internal,
            )
            evidence_refs = tuple(str(ref) for ref in claim.evidence_refs)
            summary = _claim_summary_text(
                claim,
                evidence_count=len(evidence_refs),
                relationship_state=relationship_state,
            )
            mediation_note = None
            can_edit_directly = policy == ProjectionPolicy.OPEN_EDITABLE
            can_revert = policy != ProjectionPolicy.INTERNAL

            view = ProfileClaimView(
                claim_id=str(claim.id),
                label=_claim_label(claim),
                summary=summary,
                projection_policy=policy.value,
                source=claim.source.value,
                status=claim.status.value,
                confidence=claim.confidence,
                visibility=visibility,
                can_edit_directly=can_edit_directly,
                can_revert=can_revert,
                evidence_refs=evidence_refs,
                mediation_note=mediation_note,
            )

            if visibility == "hidden":
                hidden_claims.append(view)
            elif visibility == "mediated":
                mediated_claims.append(view)
            else:
                visible_claims.append(view)

            if can_revert:
                revert_actions.append(
                    ProfileRevertAction(
                        claim_id=view.claim_id,
                        label=view.label,
                        current_summary=view.summary,
                        suggested_summary=_build_revert_suggestion(claim, evidence_list, relationship_state=relationship_state),
                        reason="可通过对话回退或重解释，不会静默覆盖用户参数。",
                        projection_policy=policy.value,
                        requires_dialogue=policy != ProjectionPolicy.OPEN_EDITABLE,
                    )
                )

        summary = _compose_summary(
            visible_claims,
            mediated_claims,
            relationship_state=relationship_state,
            evidence_count=len(evidence_list),
            llm_summarizer=llm_summarizer,
        )

        policy_notes = _build_policy_notes(context, visible_claims, mediated_claims, hidden_claims)
        relationship_snapshot = (
            {
                "relationship_maturity": relationship_state.relationship_maturity,
                "communication_style_emergent": relationship_state.communication_style_emergent,
                "interaction_count": relationship_state.interaction_count,
                "bound_policy_version": relationship_state.bound_policy_version,
            }
            if relationship_state is not None
            else {}
        )

        return ProfileTranslationResult(
            summary=summary,
            visible_claims=visible_claims,
            mediated_claims=mediated_claims,
            hidden_claims=hidden_claims,
            revert_actions=revert_actions,
            policy_notes=policy_notes,
            relationship_snapshot=relationship_snapshot,
        )


def _build_revert_suggestion(
    claim: InsightClaim,
    evidence: Iterable[IdentityEvidence | dict[str, Any]],
    *,
    relationship_state: SparkleRelationshipState | None,
) -> str:
    evidence_count = len(list(evidence))
    if claim.source == ClaimSource.USER_CORRECTION:
        return "该纠正已是最新的用户表述，可继续保留，不需要回退。"
    if evidence_count:
        return f"可回到上一版解释，并保留 {evidence_count} 条证据供对话校准。"
    if relationship_state is not None and relationship_state.relationship_maturity >= 0.5:
        return "建议通过对话回退到更早的解释，而不是静默修改。"
    return "建议先发起一次澄清对话，再决定是否回退。"


def _compose_summary(
    visible_claims: list[ProfileClaimView],
    mediated_claims: list[ProfileClaimView],
    *,
    relationship_state: SparkleRelationshipState | None,
    evidence_count: int,
    llm_summarizer: Callable[[str], str] | None = None,
) -> str:
    prompt_lines = [
        "请将以下画像条目压缩成一段用户可读的中文总结，语气克制、具体、可讨论。",
        *(f"- {item.label}: {item.summary}" for item in visible_claims[:4]),
    ]
    if mediated_claims:
        prompt_lines.append(f"- 还有 {len(mediated_claims)} 条需要对话中介的条目。")
    if relationship_state is not None:
        prompt_lines.append(
            f"- 协作成熟度: {relationship_state.relationship_maturity:.2f}, 风格: {relationship_state.communication_style_emergent or 'unknown'}"
        )
    prompt_lines.append(f"- 证据数量: {evidence_count}")
    prompt = "\n".join(prompt_lines)

    if llm_summarizer is not None:
        candidate = llm_summarizer(prompt).strip()
        if candidate:
            return candidate

    if not visible_claims and not mediated_claims:
        return "当前没有可公开渲染的画像条目，系统只保留了内部校准痕迹。"

    lead = visible_claims[0].label if visible_claims else mediated_claims[0].label
    secondary = visible_claims[1].label if len(visible_claims) > 1 else None
    parts = [f"当前画像以「{lead}」为主"]
    if secondary:
        parts.append(f"，并且「{secondary}」也在持续影响系统判断")
    if mediated_claims:
        parts.append(f"；另有 {len(mediated_claims)} 条需要通过对话解释的内容")
    if relationship_state is not None:
        parts.append(
            f"。你和 Sparkle 的协作成熟度约为 {relationship_state.relationship_maturity:.0%}，系统更倾向于 {relationship_state.communication_style_emergent or '平衡表达'}"
        )
    else:
        parts.append("。系统会优先保留可讨论空间")
    if evidence_count:
        parts.append(f"，当前共有 {evidence_count} 条证据参与校准")
    parts.append("。")
    return "".join(parts)


def _build_policy_notes(
    context: ProfileProjectionContext,
    visible_claims: list[ProfileClaimView],
    mediated_claims: list[ProfileClaimView],
    hidden_claims: list[ProfileClaimView],
) -> list[str]:
    notes: list[str] = []
    if hidden_claims:
        notes.append(f"已隐藏 {len(hidden_claims)} 条 internal 画像，不会进入透明视图。")
    if mediated_claims and not context.allow_sensitive_mediation:
        notes.append(f"有 {len(mediated_claims)} 条 sensitive_mediated 条目只保留为中介说明。")
    if visible_claims:
        notes.append(f"透明视图当前展示 {len(visible_claims)} 条可直接阅读的画像条目。")
    return notes


def translate_profile(
    claims: Iterable[InsightClaim | dict[str, Any]],
    evidence: Iterable[IdentityEvidence | dict[str, Any]] | None = None,
    *,
    relationship_state: SparkleRelationshipState | None = None,
    context: ProfileProjectionContext | None = None,
    llm_summarizer: Callable[[str], str] | None = None,
) -> ProfileTranslationResult:
    return ProfileTranslator().translate(
        claims,
        evidence,
        relationship_state=relationship_state,
        context=context,
        llm_summarizer=llm_summarizer,
    )


def filter_claims_by_projection_policy(
    claims: Iterable[InsightClaim | dict[str, Any]],
    *,
    context: ProfileProjectionContext | None = None,
) -> list[InsightClaim | dict[str, Any]]:
    return ProfileTranslator().filter_claims(claims, context=context)


def build_user_correction_claim(
    original_claim: InsightClaim,
    *,
    correction_text: str,
    evidence_refs: Iterable[str] | None = None,
    created_at: datetime | None = None,
) -> tuple[InsightClaim, InsightClaim]:
    """Create a correction claim and contextualize the original claim."""

    now = created_at or _utcnow()
    correction_claim = InsightClaim(
        id=uuid4(),
        user_id=original_claim.user_id,
        created_at=now,
        updated_at=now,
        claim_type="user_correction",
        content=correction_text.strip(),
        source=ClaimSource.USER_CORRECTION,
        confidence=min(max(original_claim.confidence, 0.8), 0.99),
        status=ClaimLifecycle.OPEN,
        evidence_refs=list(evidence_refs or []),
        probe_outcome_ids=[],
        projection_policy=original_claim.projection_policy,
    )
    contextualized_claim = original_claim.model_copy(
        update={
            "updated_at": now,
            "status": ClaimLifecycle.CONTEXTUALIZED,
        "evidence_refs": _merge_unique_refs(original_claim.evidence_refs, evidence_refs or []),
        }
    )
    return correction_claim, contextualized_claim


def _merge_unique_refs(existing: Iterable[str], additions: Iterable[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for ref in [*existing, *additions]:
        ref_text = str(ref)
        if ref_text and ref_text not in seen:
            seen.add(ref_text)
            merged.append(ref_text)
    return merged
