from __future__ import annotations

import inspect
import json
from dataclasses import asdict, dataclass
from typing import Any

from app.orchestration.companion_constitution import COMPANION_CONSTITUTION, CONSTITUTION_VERSION
from app.orchestration.companion_identity_kernel import IDENTITY_KERNEL_VERSION, SPARKLE_IDENTITY_KERNEL

SOUL_COMPILER_VERSION = "2026-04-04.shadow.v1"


@dataclass(frozen=True)
class CompanionStateDefaults:
    warmth_calibration: float = 0.55
    candor_calibration: float = 0.75
    challenge_style: str = "balanced"
    emotional_explicitness: float = 0.35
    relationship_stage: str = "building"
    self_description_note: str = ""
    companion_growth_note: str = ""
    relationship_note: str = ""
    preferred_truth_style: str = "honest_warm"
    growth_confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_COMPANION_STATE = CompanionStateDefaults()


def _coalesce_state_value(source: dict[str, Any], key: str, default: Any) -> Any:
    value = source.get(key)
    return default if value is None else value


@dataclass(frozen=True)
class SoulRuntimeContext:
    constitutional_summary: str
    identity_summary: str
    companion_stance: str
    relationship_context: str
    no_drift_flags: list[str]
    evidence_trace: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "constitutional_summary": self.constitutional_summary,
            "identity_summary": self.identity_summary,
            "companion_stance": self.companion_stance,
            "relationship_context": self.relationship_context,
            "no_drift_flags": list(self.no_drift_flags),
            "evidence_trace": dict(self.evidence_trace),
        }


@dataclass(frozen=True)
class ShadowSoulRuntimePayload:
    context: SoulRuntimeContext
    debug: dict[str, Any]

    def as_context_data(self) -> dict[str, Any]:
        return {
            "soul_runtime_context": self.context.to_dict(),
            "soul_runtime_debug": dict(self.debug),
        }


class SoulCompiler:
    """Compile the constitutional and identity layers into a small runtime shadow."""

    def __init__(
        self,
        *,
        constitution=COMPANION_CONSTITUTION,
        identity_kernel=SPARKLE_IDENTITY_KERNEL,
        default_companion_state: CompanionStateDefaults = DEFAULT_COMPANION_STATE,
    ) -> None:
        self.constitution = constitution
        self.identity_kernel = identity_kernel
        self.default_companion_state = default_companion_state

    def compile(
        self,
        *,
        user_context: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        visible_intelligence_context: dict[str, Any] | None,
        dual_core_snapshot: dict[str, Any] | None,
        effective_companion_state: dict[str, Any] | None = None,
        relationship_profile: dict[str, Any] | None = None,
        recent_revisions: list[dict[str, Any]] | None = None,
    ) -> SoulRuntimeContext:
        user_context = user_context if isinstance(user_context, dict) else {}
        plan_context = plan_context if isinstance(plan_context, dict) else {}
        visible_intelligence_context = (
            visible_intelligence_context if isinstance(visible_intelligence_context, dict) else {}
        )
        dual_core_snapshot = dual_core_snapshot if isinstance(dual_core_snapshot, dict) else {}
        effective_companion_state = self._effective_companion_state(effective_companion_state)
        relationship_profile = relationship_profile if isinstance(relationship_profile, dict) else {}
        recent_revisions = [dict(item) for item in (recent_revisions or []) if isinstance(item, dict)][:5]

        constitutional_summary = self._build_constitutional_summary()
        identity_summary = self._build_identity_summary()
        companion_stance = self._build_companion_stance(
            visible_intelligence_context=visible_intelligence_context,
            dual_core_snapshot=dual_core_snapshot,
            effective_companion_state=effective_companion_state,
        )
        relationship_context = self._build_relationship_context(
            visible_intelligence_context=visible_intelligence_context,
            effective_companion_state=effective_companion_state,
            relationship_profile=relationship_profile,
        )
        no_drift_flags = self._build_no_drift_flags()
        evidence_trace = self._build_evidence_trace(
            user_context=user_context,
            plan_context=plan_context,
            visible_intelligence_context=visible_intelligence_context,
            dual_core_snapshot=dual_core_snapshot,
            effective_companion_state=effective_companion_state,
            relationship_profile=relationship_profile,
            recent_revisions=recent_revisions,
        )
        return SoulRuntimeContext(
            constitutional_summary=constitutional_summary,
            identity_summary=identity_summary,
            companion_stance=companion_stance,
            relationship_context=relationship_context,
            no_drift_flags=no_drift_flags,
            evidence_trace=evidence_trace,
        )

    def _build_companion_stance(
        self,
        *,
        visible_intelligence_context: dict[str, Any],
        dual_core_snapshot: dict[str, Any],
        effective_companion_state: dict[str, Any],
    ) -> str:
        mode = str(dual_core_snapshot.get("mode") or "balanced").strip() or "balanced"
        candor = float(
            _coalesce_state_value(
                effective_companion_state,
                "candor_calibration",
                self.default_companion_state.candor_calibration,
            )
        )
        warmth = float(
            _coalesce_state_value(
                effective_companion_state,
                "warmth_calibration",
                self.default_companion_state.warmth_calibration,
            )
        )
        emotional_explicitness = float(
            _coalesce_state_value(
                effective_companion_state,
                "emotional_explicitness",
                self.default_companion_state.emotional_explicitness,
            )
        )
        challenge_style = str(
            _coalesce_state_value(
                effective_companion_state,
                "challenge_style",
                self.default_companion_state.challenge_style,
            )
        ).strip()
        truth_style = str(
            _coalesce_state_value(
                effective_companion_state,
                "preferred_truth_style",
                self.default_companion_state.preferred_truth_style,
            )
        ).strip()

        base = "Show warm, honest, structured companionship; treat emotion as a signal about value and friction."
        calibration_bits = [
            f"Warmth stays around {warmth:.2f}.",
            f"Candor stays around {candor:.2f}.",
        ]
        if challenge_style == "firm":
            calibration_bits.append("Challenge should be clear and steady rather than softening the core judgment.")
        elif challenge_style == "gentle":
            calibration_bits.append("Challenge should stay gentle and low-pressure while still naming reality.")
        else:
            calibration_bits.append("Challenge should stay balanced: direct enough to help, warm enough to land.")
        if truth_style == "direct_structured":
            calibration_bits.append("Prefer direct, structured truth over affective padding.")
        elif truth_style == "gentle_reflective":
            calibration_bits.append("Deliver truth reflectively and with pacing sensitivity.")
        if emotional_explicitness >= 0.55:
            calibration_bits.append("It is appropriate to name emotional friction a bit more explicitly.")

        mode_specific = {
            "cognitive_first": "Lead by naming the user's friction with care, then move toward clarity without losing candor.",
            "execution_first": "Lead with actionable clarity and crisp structure, while keeping warmth present and non-performative.",
            "balanced": "Balance attunement and execution so the user feels understood without losing forward motion.",
        }.get(mode, "Balance attunement and execution while keeping constitutional discipline intact.")

        continuity_hint = ""
        if self._collect_visible_lines(visible_intelligence_context):
            continuity_hint = (
                " Carry continuity from the latest visible changes instead of acting like each turn starts from zero."
            )

        return f"{base} {' '.join(calibration_bits)} {mode_specific}{continuity_hint}".strip()

    def _build_relationship_context(
        self,
        *,
        visible_intelligence_context: dict[str, Any],
        effective_companion_state: dict[str, Any],
        relationship_profile: dict[str, Any],
    ) -> str:
        visible_lines = self._collect_visible_lines(visible_intelligence_context)
        relationship_stage = str(
            _coalesce_state_value(
                effective_companion_state,
                "relationship_stage",
                self.default_companion_state.relationship_stage,
            )
        ).strip()
        trust_level = float(relationship_profile.get("trust_level") or 0.0)
        candor_tolerance = float(relationship_profile.get("candor_tolerance") or 0.5)
        stage_prefix = {
            "early": "Keep the relationship light, respectful, and non-assumptive.",
            "building": "Show continuity through steadiness and follow-through rather than intimacy theater.",
            "trusted": "You can be a bit more direct because trust has some foundation.",
            "deepening": "Continuity can feel more personal, but constitutional boundaries still lead.",
        }.get(relationship_stage, "Show continuity through steadiness and respectful candor.")
        if visible_lines:
            return (
                f"{stage_prefix} Relationship continuity should be shown through remembered progress and respectful candor. "
                f"Trust level {trust_level:.2f}, candor tolerance {candor_tolerance:.2f}. "
                f"Most relevant shared context: {' | '.join(visible_lines[:2])}"
            )
        return (
            f"{stage_prefix} Relationship is still governed through steady, respectful continuity: let consistency, honesty, "
            "and memory of progress create warmth rather than roleplay."
        )

    def _build_no_drift_flags(self) -> list[str]:
        flags = [str(item).strip() for item in (self.constitution.no_drift_commitments or ()) if str(item).strip()]
        if self.constitution.amendment_policy.runtime_mutable is False:
            flags.append("Constitution-level change is not runtime mutable.")
        if self.constitution.amendment_policy.requires_explicit_review:
            flags.append("Constitutional amendments require explicit review.")
        return flags[:6]

    def _build_constitutional_summary(self) -> str:
        top_principles = [principle.title for principle in self.constitution.non_negotiables[:4] if principle.title]
        principle_summary = ", ".join(top_principles)
        return (
            f"{self.constitution.user_centered_telos} "
            f"Core constitutional priorities: {principle_summary}. "
            f"{self.constitution.engineering_compression}"
        ).strip()

    def _build_identity_summary(self) -> str:
        top_facets = [facet.summary for facet in self.identity_kernel.core_facets[:3] if facet.summary]
        facet_summary = " ".join(top_facets)
        return f"{self.identity_kernel.essence} {self.identity_kernel.not_this} {facet_summary}".strip()

    def _build_evidence_trace(
        self,
        *,
        user_context: dict[str, Any],
        plan_context: dict[str, Any],
        visible_intelligence_context: dict[str, Any],
        dual_core_snapshot: dict[str, Any],
        effective_companion_state: dict[str, Any],
        relationship_profile: dict[str, Any],
        recent_revisions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        active_plan = str(
            plan_context.get("plan_title") or plan_context.get("title") or plan_context.get("goal") or ""
        ).strip()
        user_preferences = user_context.get("preferences") if isinstance(user_context.get("preferences"), dict) else {}
        return {
            "compiler_version": SOUL_COMPILER_VERSION,
            "constitution_version": self.constitution.version,
            "identity_kernel_version": self.identity_kernel.version,
            "companion_state": {
                "source": "effective_read_path",
                "version": "effective-read.v1",
                "values": effective_companion_state,
            },
            "relationship_profile": relationship_profile,
            "recent_revisions": recent_revisions,
            "visible_intelligence": {
                "source": "current_context",
                "signals": dict(visible_intelligence_context),
                "signal_count": len(self._collect_visible_lines(visible_intelligence_context)),
            },
            "dual_core": {
                "source": str(dual_core_snapshot.get("source") or "default"),
                "mode": str(dual_core_snapshot.get("mode") or "balanced"),
                "reason": str(dual_core_snapshot.get("reason") or ""),
                "timestamp": str(dual_core_snapshot.get("timestamp") or ""),
            },
            "user_context": {
                "has_preferences": bool(user_preferences),
                "preference_keys": sorted(str(key) for key in user_preferences.keys())[:8],
                "current_query_present": bool(str(user_context.get("current_query") or "").strip()),
            },
            "plan_context": {
                "active_plan": active_plan,
                "has_plan_context": bool(plan_context),
                "has_constraints": isinstance(plan_context.get("constraints"), dict),
            },
        }

    def _effective_companion_state(self, raw: dict[str, Any] | None) -> dict[str, Any]:
        merged = self.default_companion_state.to_dict()
        if isinstance(raw, dict):
            for key in merged:
                if key in raw and raw.get(key) is not None:
                    merged[key] = raw.get(key)
        return merged

    @staticmethod
    def _collect_visible_lines(visible_intelligence_context: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        proactive = str(visible_intelligence_context.get("proactive_opening_message") or "").strip()
        pending = str(visible_intelligence_context.get("pending_observation") or "").strip()
        followup = str(visible_intelligence_context.get("post_adaptation_question") or "").strip()
        if proactive:
            lines.append(proactive)
        if pending:
            lines.append(pending)
        if followup:
            lines.append(followup)
        for item in visible_intelligence_context.get("evolution_highlights") or []:
            text = str(item).strip()
            if text:
                lines.append(text)
        return lines


def _extract_visible_intelligence_context(
    *,
    user_context: dict[str, Any] | None,
    state_context_data: dict[str, Any] | None,
) -> dict[str, Any]:
    state_context_data = state_context_data if isinstance(state_context_data, dict) else {}
    user_context = user_context if isinstance(user_context, dict) else {}
    visible_update_context = (
        state_context_data.get("visible_update_context")
        if isinstance(state_context_data.get("visible_update_context"), dict)
        else {}
    )
    evolution_highlights = list(state_context_data.get("evolution_highlights") or [])
    if not evolution_highlights:
        evolution_highlights = list(user_context.get("evolution_highlights") or [])
    return {
        "proactive_opening_message": str(
            visible_update_context.get("proactive_opening_message")
            or user_context.get("proactive_opening_message")
            or ""
        ).strip(),
        "pending_observation": str(
            visible_update_context.get("pending_observation") or user_context.get("pending_observation") or ""
        ).strip(),
        "post_adaptation_question": str(
            visible_update_context.get("post_adaptation_question") or user_context.get("post_adaptation_question") or ""
        ).strip(),
        "evolution_highlights": [str(item).strip() for item in evolution_highlights if str(item).strip()],
    }


async def _load_recent_dual_core_snapshot(redis_client: Any, user_id: str) -> dict[str, Any] | None:
    if not redis_client or not user_id:
        return None
    try:
        raw = redis_client.get(f"user:routing:last_dual_core:{user_id}")
        if inspect.isawaitable(raw):
            raw = await raw
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            data = json.loads(raw)
        elif isinstance(raw, dict):
            data = raw
        else:
            return None
        return {
            **data,
            "source": "redis_snapshot",
        }
    except Exception:
        return None


def _extract_dual_core_snapshot_from_state(state_context_data: dict[str, Any] | None) -> dict[str, Any] | None:
    state_context_data = state_context_data if isinstance(state_context_data, dict) else {}
    decision = state_context_data.get("dual_core_decision")
    if not isinstance(decision, dict):
        return None
    signal_snapshot = state_context_data.get("dual_core_signal_snapshot")
    signal_snapshot = signal_snapshot if isinstance(signal_snapshot, dict) else {}
    return {
        "source": "state_context",
        "mode": str(decision.get("mode") or "balanced"),
        "reason": str(decision.get("reason") or ""),
        "routing_profile": signal_snapshot.get("routing_profile"),
        "current_guidance": signal_snapshot.get("current_guidance"),
        "routing_debug": signal_snapshot.get("routing_debug") or decision.get("routing_debug") or {},
        "timestamp": str(signal_snapshot.get("timestamp") or ""),
    }


async def build_shadow_soul_runtime_payload(
    *,
    redis_client: Any,
    user_id: str,
    user_context: dict[str, Any] | None,
    plan_context: dict[str, Any] | None,
    state_context_data: dict[str, Any] | None = None,
    effective_companion_state: dict[str, Any] | None = None,
    relationship_profile: dict[str, Any] | None = None,
    recent_revisions: list[dict[str, Any]] | None = None,
) -> ShadowSoulRuntimePayload:
    state_context_data = state_context_data if isinstance(state_context_data, dict) else {}
    visible_intelligence_context = _extract_visible_intelligence_context(
        user_context=user_context,
        state_context_data=state_context_data,
    )
    dual_core_snapshot = _extract_dual_core_snapshot_from_state(state_context_data)
    if dual_core_snapshot is None:
        dual_core_snapshot = await _load_recent_dual_core_snapshot(redis_client, user_id)
    if dual_core_snapshot is None:
        dual_core_snapshot = {
            "source": "default",
            "mode": "balanced",
            "reason": "",
            "timestamp": "",
        }

    compiler = SoulCompiler()
    context = compiler.compile(
        user_context=user_context,
        plan_context=plan_context,
        visible_intelligence_context=visible_intelligence_context,
        dual_core_snapshot=dual_core_snapshot,
        effective_companion_state=effective_companion_state,
        relationship_profile=relationship_profile,
        recent_revisions=recent_revisions,
    )
    debug = {
        "compiler_version": SOUL_COMPILER_VERSION,
        "constitution_version": CONSTITUTION_VERSION,
        "identity_kernel_version": IDENTITY_KERNEL_VERSION,
        "dual_core_source": str(dual_core_snapshot.get("source") or "default"),
        "dual_core_mode": str(dual_core_snapshot.get("mode") or "balanced"),
        "visible_signal_count": int(context.evidence_trace.get("visible_intelligence", {}).get("signal_count") or 0),
    }
    return ShadowSoulRuntimePayload(context=context, debug=debug)


async def attach_shadow_soul_runtime(
    *,
    target_context: dict[str, Any],
    redis_client: Any,
    user_id: str,
    user_context: dict[str, Any] | None,
    plan_context: dict[str, Any] | None,
    effective_companion_state: dict[str, Any] | None = None,
    relationship_profile: dict[str, Any] | None = None,
    recent_revisions: list[dict[str, Any]] | None = None,
) -> ShadowSoulRuntimePayload:
    payload = await build_shadow_soul_runtime_payload(
        redis_client=redis_client,
        user_id=user_id,
        user_context=user_context,
        plan_context=plan_context,
        state_context_data=target_context,
        effective_companion_state=effective_companion_state,
        relationship_profile=relationship_profile,
        recent_revisions=recent_revisions,
    )
    target_context.update(payload.as_context_data())
    return payload
