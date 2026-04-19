from __future__ import annotations

import json
import re
from typing import Any


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


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _build_metric_record(
    *,
    family: str,
    numerator: int,
    denominator: int,
    status: str,
    degradation_reason: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "metric_family": family,
        "numerator": int(max(numerator, 0)),
        "denominator": int(max(denominator, 0)),
        "ratio": _safe_ratio(int(max(numerator, 0)), int(max(denominator, 0))),
        "status": status,
        "degradation_reason": degradation_reason,
    }
    if extra:
        payload.update(extra)
    return payload


def build_prompt_utilization_record(prompt_signal_telemetry: dict[str, Any] | None) -> dict[str, Any]:
    telemetry = _as_dict(prompt_signal_telemetry)
    utilization = _as_dict(telemetry.get("utilization"))
    if not utilization:
        return _build_metric_record(
            family="prompt_utilization",
            numerator=0,
            denominator=0,
            status="unknown",
            degradation_reason="prompt_signal_telemetry_missing",
        )

    selected_blocks = [str(item).strip() for item in _as_list(utilization.get("selected_signal_blocks")) if str(item).strip()]
    rendered_blocks = [str(item).strip() for item in _as_list(utilization.get("rendered_signal_blocks")) if str(item).strip()]
    selected_high_value_fields = [
        str(item).strip()
        for item in _as_list(utilization.get("selected_high_value_fields"))
        if str(item).strip()
    ]
    prompt_visible_high_value_fields = [
        str(item).strip()
        for item in _as_list(utilization.get("prompt_visible_high_value_fields"))
        if str(item).strip()
    ]

    denominator = int(utilization.get("selected_signal_block_count") or len(selected_blocks))
    numerator = int(utilization.get("rendered_signal_block_count") or len(rendered_blocks))

    if denominator > 0:
        status = "known"
        degradation_reason = None
    else:
        status = "not_applicable"
        degradation_reason = "no_selected_signal_blocks"

    return _build_metric_record(
        family="prompt_utilization",
        numerator=numerator,
        denominator=denominator,
        status=status,
        degradation_reason=degradation_reason,
        extra={
            "selected_signal_blocks": selected_blocks,
            "rendered_signal_blocks": rendered_blocks,
            "selected_high_value_fields": selected_high_value_fields,
            "prompt_visible_high_value_fields": prompt_visible_high_value_fields,
        },
    )


_WORD_RE = re.compile(r"[a-z0-9]{2,}|[\u4e00-\u9fff]{1,}")


def _tokenize(value: Any) -> set[str]:
    return {
        token
        for token in _WORD_RE.findall(_normalized_text(value))
        if token.strip()
    }


def _has_traceable_overlap(full_response: str, witnesses: list[str]) -> bool:
    text = _normalized_text(full_response)
    if not text:
        return False
    text_tokens = _tokenize(text)
    for witness in witnesses:
        normalized = _normalized_text(witness)
        if not normalized:
            continue
        if len(normalized) >= 4 and normalized in text:
            return True
        witness_tokens = _tokenize(normalized)
        if witness_tokens and len(text_tokens & witness_tokens) >= min(2, len(witness_tokens)):
            return True
    return False


def _load_metadata_json(metadata: dict[str, Any], key: str) -> dict[str, Any]:
    raw = metadata.get(key)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _append_family(
    *,
    families: list[dict[str, Any]],
    family: str,
    witnesses: list[str],
    metadata_hit: bool,
    text_hit: bool,
) -> None:
    if not witnesses and not metadata_hit:
        return
    traceable = metadata_hit or text_hit
    traceability_mode = []
    if metadata_hit:
        traceability_mode.append("metadata")
    if text_hit:
        traceability_mode.append("text")
    families.append(
        {
            "family": family,
            "witnesses": witnesses[:4],
            "traceable": traceable,
            "traceability_mode": "+".join(traceability_mode) if traceability_mode else "none",
        }
    )


def build_inference_utilization_record(
    *,
    user_context_payload: dict[str, Any] | None,
    context_data: dict[str, Any] | None,
    response_metadata: dict[str, Any] | None,
    full_response: str,
) -> dict[str, Any]:
    user_context = _as_dict(user_context_payload)
    context = _as_dict(context_data)
    metadata = _as_dict(response_metadata)
    prompt_signal_telemetry = _as_dict(user_context.get("prompt_signal_telemetry"))
    situation_brief = _as_dict(context.get("situation_brief") or user_context.get("situation_brief"))
    decision_context = _as_dict(situation_brief.get("decision_context"))
    semantic_control = _as_dict(situation_brief.get("semantic_control"))
    evidence = _as_dict(situation_brief.get("evidence"))
    insight_state = _as_dict(situation_brief.get("insight_state"))

    evidence_witnesses = [
        str(item).strip()
        for item in _as_list(evidence.get("freshest_items"))
        if str(item).strip()
    ]
    summary_text = str(situation_brief.get("summary") or "").strip()
    if summary_text:
        evidence_witnesses.append(summary_text)

    high_value_witnesses = []
    for key in prompt_signal_telemetry.get("prompt_visible_high_value_fields") or []:
        if key in {"error_summary", "recent_errors"}:
            high_value_witnesses.extend(evidence_witnesses[:2])
        elif key == "recent_mastery_changes":
            high_value_witnesses.extend(
                str(item).strip()
                for item in _as_list(evidence.get("recent_wins"))
                if str(item).strip()
            )

    uncertainty_witnesses = [
        str(item).strip()
        for item in _as_list(
            decision_context.get("planning_blocking_unknowns")
            or insight_state.get("blocking_unknowns")
            or insight_state.get("missing_information")
        )
        if str(item).strip()
    ]

    families: list[dict[str, Any]] = []
    _append_family(
        families=families,
        family="situation_brief",
        witnesses=[
            summary_text,
            str(situation_brief.get("focus_question") or "").strip(),
        ],
        metadata_hit=bool(metadata.get("situation_brief") or metadata.get("situation_brief_summary")),
        text_hit=_has_traceable_overlap(
            full_response,
            [
                summary_text,
                str(situation_brief.get("focus_question") or "").strip(),
            ],
        ),
    )
    _append_family(
        families=families,
        family="decision_context",
        witnesses=[
            str(decision_context.get("what_matters_now") or "").strip(),
            str(decision_context.get("planning_readiness_action") or "").strip(),
        ],
        metadata_hit=bool(metadata.get("residual_decision_context")),
        text_hit=_has_traceable_overlap(
            full_response,
            [
                str(decision_context.get("what_matters_now") or "").strip(),
                str(decision_context.get("planning_readiness_action") or "").strip(),
            ],
        ),
    )
    semantic_doctrine = [
        str(item)
        for item in _as_list(_as_dict(semantic_control.get("rendered_doctrine_summary")).values())
        if str(item).strip()
    ]
    _append_family(
        families=families,
        family="semantic_control",
        witnesses=semantic_doctrine,
        metadata_hit=bool(metadata.get("semantic_control_trace")),
        text_hit=_has_traceable_overlap(full_response, semantic_doctrine),
    )
    _append_family(
        families=families,
        family="evidence_grounding",
        witnesses=evidence_witnesses,
        metadata_hit=bool(_load_metadata_json(metadata, "situation_brief").get("evidence")),
        text_hit=_has_traceable_overlap(full_response, evidence_witnesses),
    )
    _append_family(
        families=families,
        family="high_value_learning_signals",
        witnesses=high_value_witnesses,
        metadata_hit=bool(prompt_signal_telemetry.get("prompt_visible_high_value_fields"))
        and bool(metadata.get("situation_brief") or metadata.get("semantic_control_trace")),
        text_hit=_has_traceable_overlap(full_response, high_value_witnesses),
    )
    _append_family(
        families=families,
        family="uncertainty_markers",
        witnesses=uncertainty_witnesses,
        metadata_hit=bool(
            uncertainty_witnesses
            and _load_metadata_json(metadata, "residual_decision_context").get("planning_blocking_unknowns")
        ),
        text_hit=_has_traceable_overlap(full_response, uncertainty_witnesses)
        or any(token in _normalized_text(full_response) for token in ("不确定", "需要再确认", "可能还需要", "unknown")),
    )

    eligible_families = [item["family"] for item in families]
    traceable_families = [item["family"] for item in families if item["traceable"]]

    if not families:
        return _build_metric_record(
            family="inference_utilization",
            numerator=0,
            denominator=0,
            status="not_applicable",
            degradation_reason="no_eligible_signal_families",
        )

    return _build_metric_record(
        family="inference_utilization",
        numerator=len(traceable_families),
        denominator=len(eligible_families),
        status="known",
        degradation_reason=None,
        extra={
            "eligible_signal_families": eligible_families,
            "traceable_signal_families": traceable_families,
            "family_details": families,
        },
    )


def build_stage9_utilization_metrics(
    *,
    user_context_payload: dict[str, Any] | None,
    context_data: dict[str, Any] | None,
    response_metadata: dict[str, Any] | None,
    full_response: str,
) -> dict[str, Any]:
    prompt_signal_telemetry = _as_dict(_as_dict(user_context_payload).get("prompt_signal_telemetry"))
    return {
        "prompt_utilization": build_prompt_utilization_record(prompt_signal_telemetry),
        "inference_utilization": build_inference_utilization_record(
            user_context_payload=user_context_payload,
            context_data=context_data,
            response_metadata=response_metadata,
            full_response=full_response,
        ),
    }
