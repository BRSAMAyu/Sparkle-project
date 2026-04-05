from __future__ import annotations

from typing import Any
import re


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _strip(value: Any) -> str:
    return str(value or "").strip()


class CapabilityRequirementCompiler:
    """Compile a deterministic Phase D capability requirement profile."""

    _SPECIALIST_PATTERNS = (
        r"\b(debug|diagnos|root cause|prove|deriv|formal|expert|specialist)\b",
        r"根因|诊断|报错|debug|证明|推导|专家|专项",
    )
    _LOW_LATENCY_PATTERNS = (
        r"\b(quick|fast|brief|simple|just tell me|one sentence)\b",
        r"快一点|简短|一句话|直接说结论|先给结论",
    )
    _OVERLOAD_PATTERNS = (
        r"\b(overwhelmed|cannot start|can't start|too much|burned out|exhausted)\b",
        r"太多了|开始不了|启动不了|撑不住|扛不住|没精力",
    )
    _VISIBLE_ADAPTATION_PATTERNS = (
        r"\b(accountability|community|celebrate|streak|mood|focus music|visual)\b",
        r"打卡|社区|陪跑|庆祝|氛围|音乐|视觉",
    )

    def compile(
        self,
        *,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        decision_context: dict[str, Any] | None,
        insight_state: dict[str, Any] | None,
        planning_strategy: dict[str, Any] | None,
        route_intent: str | None,
    ) -> dict[str, Any]:
        user_context = _as_dict(user_context_payload)
        plan_context = _as_dict(plan_context)
        decision_context = _as_dict(decision_context)
        insight_state = _as_dict(insight_state)
        planning_strategy = _as_dict(planning_strategy)
        normalized_intent = _strip(route_intent or user_context.get("context_focus", {}).get("route_intent")).lower()
        strategy_state = _as_dict(user_context.get("user_strategy_state"))

        text_corpus = " | ".join(
            part
            for part in (
                _strip(user_context.get("current_query")),
                _strip(user_context.get("context_briefing_note")),
                _strip(decision_context.get("what_matters_now")),
                _strip(plan_context.get("goal")),
                _strip(plan_context.get("plan_title")),
            )
            if part
        )

        attached_materials = bool(user_context.get("materials_attached")) or any(
            _as_list(user_context.get(key))
            for key in ("attached_materials", "uploaded_materials", "material_sources", "file_ids")
        ) or bool(_as_dict(user_context.get("user_material_grounding")))
        retrieval_emphasis = _strip(strategy_state.get("retrieval_emphasis")).lower()
        grounding_priority = [str(item).strip().lower() for item in _as_list(decision_context.get("grounding_priority"))]
        planning_readiness = _strip(insight_state.get("readiness_level") or decision_context.get("planning_readiness")).lower()
        experience_mode = _strip(decision_context.get("experience_mode")).lower()
        planning_depth = _strip(planning_strategy.get("plan_depth") or decision_context.get("planning_depth")).lower()

        material_dependency = "none"
        grounding_required = "optional"
        if attached_materials or retrieval_emphasis == "user_materials" or "user_materials" in grounding_priority:
            material_dependency = "mandatory"
            grounding_required = "mandatory"
        elif normalized_intent in {"knowledge", "learn", "review", "translation"}:
            material_dependency = "helpful"
            grounding_required = "helpful"
        elif normalized_intent in {"plan", "planning"} and retrieval_emphasis == "balanced":
            material_dependency = "profile_supported"
            grounding_required = "required_from_profile"

        specialization_signals = [
            bool(user_context.get("error_pattern_present")),
            bool(user_context.get("domain_specialist_needed")),
            normalized_intent == "translation" and bool(user_context.get("specialist_translation_available")),
        ]
        specialization_required = any(
            re.search(pattern, text_corpus, re.IGNORECASE) for pattern in self._SPECIALIST_PATTERNS
        ) or normalized_intent in {"error_diagnosis", "prediction"} or any(specialization_signals)
        latency_sensitivity = "normal"
        if any(re.search(pattern, text_corpus, re.IGNORECASE) for pattern in self._LOW_LATENCY_PATTERNS):
            latency_sensitivity = "high"
        elif normalized_intent in {"chat", "knowledge"} and planning_readiness in {"high", "medium"}:
            latency_sensitivity = "medium"

        adaptation_visibility_required = any(
            re.search(pattern, text_corpus, re.IGNORECASE) for pattern in self._VISIBLE_ADAPTATION_PATTERNS
        ) or normalized_intent in {"community", "accountability", "group"}
        bounded_adjustments_allowed = experience_mode in {"stabilize", "mobilize", "reframe", "explain"}

        overload_detected = any(
            re.search(pattern, text_corpus, re.IGNORECASE) for pattern in self._OVERLOAD_PATTERNS
        ) or experience_mode == "stabilize"

        if overload_detected:
            planning_depth_required = "light"
            cost_band = "low"
        elif specialization_required:
            planning_depth_required = "targeted"
            cost_band = (
                "low"
                if normalized_intent == "translation" and bool(user_context.get("specialist_translation_available"))
                else "medium"
            )
        elif planning_depth in {"deep", "full"} or normalized_intent in {"plan", "planning"}:
            planning_depth_required = "deep" if planning_readiness not in {"low"} else "targeted"
            cost_band = "medium"
        else:
            planning_depth_required = "light"
            cost_band = "low" if latency_sensitivity == "high" else "balanced"

        if planning_readiness == "high" and planning_depth_required == "deep" and not specialization_required:
            planning_depth_required = "targeted"
        if normalized_intent in {"prediction"}:
            cost_band = "medium"
        if (
            specialization_required
            and cost_band == "low"
            and normalized_intent != "translation"
            and not bool(user_context.get("specialist_translation_available"))
        ):
            cost_band = "medium"

        forbidden_paths: list[str] = []
        if overload_detected:
            forbidden_paths.extend(["theatrical_escalation", "deep_planning"])
        if not specialization_required:
            forbidden_paths.append("specialist_escalation")
        if grounding_required == "mandatory":
            forbidden_paths.append("ungrounded_generalization")
        if cost_band == "low":
            forbidden_paths.append("pro_tier_default")

        return {
            "planning_depth_required": planning_depth_required,
            "grounding_required": grounding_required,
            "material_dependency": material_dependency,
            "specialization_required": specialization_required,
            "latency_sensitivity": latency_sensitivity,
            "adaptation_visibility_required": adaptation_visibility_required,
            "bounded_adjustments_allowed": bounded_adjustments_allowed,
            "cost_band": cost_band,
            "forbidden_paths": sorted(set(forbidden_paths)),
        }
