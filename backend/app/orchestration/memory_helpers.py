"""
Core: cognitive
Phase: reflect
Stage: P2-2 — Memory summary helpers extracted from ChatOrchestrator.

Pure utility functions for building episodic memory summaries from turn data.
No instance state — all functions are stateless.
"""
from __future__ import annotations

import contextlib
import json
from typing import Any


def memory_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def memory_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, (list, tuple)):
        return "、".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def first_memory_value(sources: list[dict[str, Any]], keys: tuple[str, ...]) -> str:
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in keys:
            text = memory_text(source.get(key))
            if text:
                return text
    return ""


def memory_json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        with contextlib.suppress(Exception):
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
    return {}


def build_aurora_modeling_memory_summary(
    *,
    modeling_snapshot: dict[str, Any] | None,
    request_extra_context: dict[str, Any] | None,
    user_context_payload: dict[str, Any] | None,
) -> str:
    snapshot = memory_dict(modeling_snapshot)
    request_context = memory_dict(request_extra_context)
    user_context = memory_dict(user_context_payload)
    profile_context = memory_dict(user_context.get("profile_context") or snapshot.get("user_model_snapshot"))
    preferences = memory_dict(profile_context.get("preferences"))
    cold_start = memory_dict(
        snapshot.get("cold_start_context")
        or user_context.get("cold_start_context")
        or profile_context.get("cold_start_context")
        or preferences.get("cold_start_context")
    )
    task_state = memory_dict(request_context.get("task_state") or user_context.get("task_state"))
    galaxy_baseline = memory_dict(
        snapshot.get("galaxy_baseline")
        or request_context.get("galaxy_baseline")
        or user_context.get("galaxy_baseline")
    )

    sources = [
        request_context,
        task_state,
        cold_start,
        profile_context,
        preferences,
        snapshot,
    ]
    subject = first_memory_value(
        sources,
        ("subject", "exam_subject", "course", "topic", "goal_subject"),
    )
    goal = first_memory_value(
        sources,
        ("goal_raw", "primary_goal_description", "goal", "target", "learning_goal"),
    )
    scope = first_memory_value(
        sources,
        ("exam_scope", "scope", "study_scope", "material_scope"),
    )
    baseline = first_memory_value(
        sources,
        ("knowledge_baseline", "baseline", "foundation", "starting_point"),
    )
    time_text = first_memory_value(
        sources,
        ("time_available", "available_time", "time_constraint", "time_budget"),
    )
    if not time_text:
        daily_hours = first_memory_value(sources, ("daily_available_hours",))
        days_left = first_memory_value(sources, ("time_constraint_days", "days_left"))
        time_parts = []
        if daily_hours:
            time_parts.append(f"每天约 {daily_hours} 小时")
        if days_left:
            time_parts.append(f"剩余约 {days_left} 天")
        time_text = "，".join(time_parts)

    weak_nodes = memory_text(
        galaxy_baseline.get("weak_nodes")
        or cold_start.get("confirmed_weak_nodes")
        or cold_start.get("galaxy_weak_nodes")
    )
    strong_nodes = memory_text(galaxy_baseline.get("strong_nodes"))
    if weak_nodes and weak_nodes not in baseline:
        baseline = f"{baseline}；薄弱={weak_nodes}" if baseline else f"薄弱={weak_nodes}"
    if strong_nodes and strong_nodes not in baseline:
        baseline = f"{baseline}；优势={strong_nodes}" if baseline else f"优势={strong_nodes}"

    parts = [
        ("subject", subject),
        ("goal", goal),
        ("scope", scope),
        ("baseline", baseline),
        ("time", time_text),
    ]
    rendered = [f"{label}={text}" for label, text in parts if text]
    if not rendered:
        return "Aurora 建模完成：已完成用户学习建模。"
    return "Aurora 建模完成：" + "；".join(rendered)


def extract_completion_state_from_response_data(final_response_data: dict[str, Any] | None) -> str:
    metadata = memory_dict((final_response_data or {}).get("metadata"))
    ux_result = memory_json_dict(metadata.get("ux_result"))
    return str(ux_result.get("completion_state") or metadata.get("completion_state") or "").strip().lower()


def build_error_memory_summary(
    *,
    request_extra_context: dict[str, Any] | None,
    final_state: Any | None,
    user_message: str,
    error: Exception | None,
) -> str:
    context = memory_dict(request_extra_context)
    bridge = memory_dict(context.get("error_replan_bridge"))
    state_context = getattr(final_state, "context_data", {}) or {}
    candidate = memory_text(
        bridge.get("node_name")
        or bridge.get("node")
        or state_context.get("failed_node")
        or state_context.get("current_node")
        or state_context.get("node_name")
    )
    if not candidate:
        errors = getattr(final_state, "errors", None) or []
        if errors:
            last_error = str(errors[-1])
            marker = "Node "
            if marker in last_error and " failed" in last_error:
                candidate = last_error.split(marker, 1)[1].split(" failed", 1)[0].strip()
            else:
                candidate = last_error[:80].strip()
    if not candidate and error is not None:
        candidate = type(error).__name__
    if not candidate:
        candidate = memory_text(user_message)[:80] or "current turn"
    return f"struggled with {candidate}"
