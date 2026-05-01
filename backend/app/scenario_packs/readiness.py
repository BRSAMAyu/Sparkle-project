"""Readiness evaluation and pack-aware context assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from collections.abc import Mapping

from app.aurora.schemas import ReadinessCriterion, ScenarioPackManifest


@dataclass(frozen=True)
class ReadinessEvaluation:
    """Outcome of evaluating a user against a pack's readiness criteria."""

    ready: bool
    satisfied_signals: tuple[str, ...]
    missing_signals: tuple[str, ...]
    weak_signals: tuple[str, ...]
    total_required: int
    total_satisfied: int


@dataclass(frozen=True)
class PackContextAssembly:
    """Pack-aware context grouping for later signal snapshot assembly."""

    ready: bool
    core_signals: dict[str, Any]
    enhanced_signals: dict[str, Any]
    optional_signals: dict[str, Any]
    missing_signals: list[str]


def _signal_confidence(value: Any) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Mapping):
        for key in ("confidence", "score", "probability", "value"):
            raw = value.get(key)
            if isinstance(raw, (int, float)):
                return float(raw)
    return None


def _signal_satisfied(signal_value: Any, criterion: ReadinessCriterion) -> bool:
    confidence = _signal_confidence(signal_value)
    if confidence is not None:
        return confidence >= float(criterion.minimum_confidence)
    return bool(signal_value)


def evaluate_readiness(
    user_signals: Mapping[str, Any],
    manifest: ScenarioPackManifest,
) -> ReadinessEvaluation:
    """Evaluate a user against a pack's readiness criteria."""

    satisfied: list[str] = []
    missing: list[str] = []
    weak: list[str] = []

    for signal_name, criterion in manifest.readiness_criteria.items():
        value = user_signals.get(signal_name)
        if value is None:
            if criterion.required:
                missing.append(signal_name)
            continue

        if _signal_satisfied(value, criterion):
            satisfied.append(signal_name)
        else:
            if criterion.required:
                missing.append(signal_name)
            else:
                weak.append(signal_name)

    required_total = sum(1 for criterion in manifest.readiness_criteria.values() if criterion.required)
    return ReadinessEvaluation(
        ready=not missing,
        satisfied_signals=tuple(satisfied),
        missing_signals=tuple(missing),
        weak_signals=tuple(weak),
        total_required=required_total,
        total_satisfied=len(satisfied),
    )


def assemble_pack_context(
    user_signals: Mapping[str, Any],
    manifest: ScenarioPackManifest,
) -> PackContextAssembly:
    """Prioritize pack-relevant signals without touching the broader signal pipeline."""

    evaluation = evaluate_readiness(user_signals, manifest)
    priority_keys = set(manifest.readiness_criteria.keys())
    core_signals: dict[str, Any] = {}
    enhanced_signals: dict[str, Any] = {}
    optional_signals: dict[str, Any] = {}

    for signal_name, value in user_signals.items():
        if signal_name in priority_keys and signal_name not in evaluation.missing_signals:
            core_signals[signal_name] = value
        elif signal_name in priority_keys:
            enhanced_signals[signal_name] = value
        else:
            optional_signals[signal_name] = value

    if not evaluation.ready and len(core_signals) < 2:
        for node in manifest.backbone_nodes[:2]:
            optional_signals.setdefault(
                f"recommended_node:{node.node_id}",
                {"persona": node.node_persona, "prompt": node.prompt_template[:120]},
            )

    return PackContextAssembly(
        ready=evaluation.ready,
        core_signals=core_signals,
        enhanced_signals=enhanced_signals,
        optional_signals=optional_signals,
        missing_signals=list(evaluation.missing_signals),
    )
