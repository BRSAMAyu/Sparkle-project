"""Offline decision bench for DualCore routing outcomes.

This module is intentionally read-only. It audits historical DualCore routing
decisions, normalizes outcome evidence, and compares the current discrete mode
with a conservative continuous shadow overlay.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aurora_stage20 import RoutingDecisionLog
from app.models.intervention_adaptive import BehavioralOutcome, PassiveSignal

SUCCESS_LABEL = "success"
FAILURE_LABEL = "failure"
NEUTRAL_LABEL = "neutral"
UNKNOWN_LABEL = "unknown"

EVIDENCE_HUMAN_TRUTH = "human_truth"
EVIDENCE_EXPLICIT_FEEDBACK = "explicit_feedback"
EVIDENCE_BEHAVIORAL_SIGNAL = "behavioral_signal"
EVIDENCE_HEURISTIC_AUTO = "heuristic_auto_eval"
EVIDENCE_SHADOW_GUESS = "shadow_guess"
EVIDENCE_UNKNOWN = "unknown"

EVIDENCE_RANK = {
    EVIDENCE_UNKNOWN: 0,
    EVIDENCE_SHADOW_GUESS: 1,
    EVIDENCE_HEURISTIC_AUTO: 2,
    EVIDENCE_BEHAVIORAL_SIGNAL: 3,
    EVIDENCE_EXPLICIT_FEEDBACK: 4,
    EVIDENCE_HUMAN_TRUTH: 5,
}

SUCCESS_OUTCOMES = {"plan_success", "task_completion"}
FAILURE_OUTCOMES = {"user_correction", "timeout"}

SIGNAL_THRESHOLDS = {
    "goal_clarity": 0.72,
    "emotional_block": 0.50,
    "procrastination": 0.60,
    "cognitive_load": 0.55,
    "low_metacognition": 0.50,
    "spine_fatigue": 0.50,
    "spine_execution_low": 0.50,
    "spine_knowledge_bottleneck": 0.50,
    "recent_corrections": 0.60,
    "route_outcome_failure": 0.50,
    "route_outcome_over_scaffolded": 0.50,
}


@dataclass(frozen=True)
class TruthLabel:
    label: str
    evidence_level: str
    evidence_rank: int
    source: str
    reason: str
    confidence: float
    latency_seconds: float | None = None

    @property
    def is_known(self) -> bool:
        return self.label in {SUCCESS_LABEL, FAILURE_LABEL, NEUTRAL_LABEL}

    @property
    def is_binary_known(self) -> bool:
        return self.label in {SUCCESS_LABEL, FAILURE_LABEL}


@dataclass(frozen=True)
class DecisionExample:
    decision_id: str
    decided_at: str
    mode: str
    shadow_mode: str
    truth_label: str
    evidence_level: str
    reason: str
    signal_scores: dict[str, float]
    source_state_v2_key: str | None


@dataclass(frozen=True)
class BenchConfig:
    limit: int = 1000
    days: int | None = 30
    user_id: UUID | None = None
    min_group_size: int = 5
    examples: int = 12


def _utcnow() -> datetime:
    return datetime.utcnow()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(result) or math.isinf(result):
        return default
    return result


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return round(sorted_values[0], 3)
    position = (len(sorted_values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(sorted_values[lower], 3)
    weight = position - lower
    return round(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight, 3)


def _mode_from_record(record: RoutingDecisionLog) -> str:
    payload = dict(record.decision_payload or {})
    return str(payload.get("mode") or record.decision_type or "unknown").strip() or "unknown"


def _route_execution_mode(record: RoutingDecisionLog) -> str:
    payload = dict(record.decision_payload or {})
    return str(payload.get("route_execution_mode") or "").strip()


def _signal_scores(record: RoutingDecisionLog) -> dict[str, float]:
    payload = dict(record.decision_payload or {})
    raw_payload = payload.get("signal_scores")
    raw = raw_payload if isinstance(raw_payload, dict) else {}
    return {
        str(key): round(_safe_float(value), 6)
        for key, value in raw.items()
        if isinstance(key, str) and isinstance(value, (int, float))
    }


def _latency_seconds(decided_at: datetime, outcome_at: datetime | None) -> float | None:
    if outcome_at is None:
        return None
    return max(0.0, (outcome_at - decided_at).total_seconds())


def classify_route_history_truth(record: RoutingDecisionLog) -> TruthLabel:
    """Normalize direct RouteHistory outcome evidence."""

    mode = _mode_from_record(record)
    outcome = str(record.outcome or "").strip()
    outcome_type = str(record.outcome_type or "").strip()
    latency = _latency_seconds(record.decided_at, record.outcome_timestamp or record.outcome_collected_at)
    if not outcome:
        return TruthLabel(
            label=UNKNOWN_LABEL,
            evidence_level=EVIDENCE_UNKNOWN,
            evidence_rank=EVIDENCE_RANK[EVIDENCE_UNKNOWN],
            source="route_history.pending",
            reason="no_route_history_outcome",
            confidence=0.0,
            latency_seconds=latency,
        )

    if outcome in SUCCESS_OUTCOMES:
        explicit = outcome_type in {"thumbs_up", "explicit_positive", "human_positive"}
        evidence = EVIDENCE_EXPLICIT_FEEDBACK if explicit else EVIDENCE_BEHAVIORAL_SIGNAL
        reason = (
            f"{mode}_eventual_progress:{outcome}"
            if mode == "cognitive_first"
            else f"{mode}_objective_progress:{outcome}"
        )
        return TruthLabel(
            label=SUCCESS_LABEL,
            evidence_level=evidence,
            evidence_rank=EVIDENCE_RANK[evidence],
            source=f"route_history.{outcome}",
            reason=reason,
            confidence=0.90 if explicit else 0.78,
            latency_seconds=latency,
        )

    if outcome in FAILURE_OUTCOMES:
        explicit = outcome == "user_correction" or outcome_type in {"thumbs_down", "user_correction"}
        evidence = EVIDENCE_EXPLICIT_FEEDBACK if explicit else EVIDENCE_BEHAVIORAL_SIGNAL
        reason = (
            f"{mode}_user_disconfirmed_route"
            if outcome == "user_correction"
            else f"{mode}_timed_out_after_route"
        )
        return TruthLabel(
            label=FAILURE_LABEL,
            evidence_level=evidence,
            evidence_rank=EVIDENCE_RANK[evidence],
            source=f"route_history.{outcome}",
            reason=reason,
            confidence=0.88 if explicit else 0.72,
            latency_seconds=latency,
        )

    return TruthLabel(
        label=UNKNOWN_LABEL,
        evidence_level=EVIDENCE_UNKNOWN,
        evidence_rank=EVIDENCE_RANK[EVIDENCE_UNKNOWN],
        source=f"route_history.unsupported:{outcome}",
        reason="unsupported_route_history_outcome",
        confidence=0.0,
        latency_seconds=latency,
    )


def classify_auto_routing_truth(
    record: RoutingDecisionLog,
    outcome: BehavioralOutcome | None,
) -> TruthLabel:
    """Normalize delayed automatic routing-effectiveness evidence."""

    if outcome is None:
        return TruthLabel(
            label=UNKNOWN_LABEL,
            evidence_level=EVIDENCE_UNKNOWN,
            evidence_rank=EVIDENCE_RANK[EVIDENCE_UNKNOWN],
            source="auto_routing_eval.missing",
            reason="no_auto_routing_outcome",
            confidence=0.0,
        )
    context = dict(outcome.context or {})
    verdict = str(context.get("verdict_reason") or "routing_effectiveness")
    label = SUCCESS_LABEL if bool(outcome.success) else FAILURE_LABEL
    latency = _latency_seconds(record.decided_at, outcome.timestamp)
    return TruthLabel(
        label=label,
        evidence_level=EVIDENCE_HEURISTIC_AUTO,
        evidence_rank=EVIDENCE_RANK[EVIDENCE_HEURISTIC_AUTO],
        source="routing_outcome_evaluator",
        reason=verdict,
        confidence=0.62 if outcome.success else 0.58,
        latency_seconds=latency,
    )


def choose_best_truth(
    route_truth: TruthLabel,
    auto_truth: TruthLabel | None = None,
) -> TruthLabel:
    """Pick the highest-trust available truth label."""

    candidates = [route_truth]
    if auto_truth is not None:
        candidates.append(auto_truth)
    return max(candidates, key=lambda item: (item.evidence_rank, item.confidence))


def conservative_shadow_mode(mode: str, scores: dict[str, float]) -> tuple[str, dict[str, float | str]]:
    """A conservative continuous overlay for offline diagnostics.

    This overlay is deliberately not a replacement router. It preserves existing
    cognitive-first hard overrides and only probes two narrow questions:
    - should some execution-first cases with accumulated weak risk be balanced?
    - should some balanced cases with low support pressure be execution-first?
    """

    current_mode = str(mode or "balanced").strip() or "balanced"
    support_pressure = (
        0.34 * _safe_float(scores.get("emotional_block"))
        + 0.28 * _safe_float(scores.get("procrastination"))
        + 0.26 * _safe_float(scores.get("cognitive_load"))
        + 0.12 * _safe_float(scores.get("low_metacognition"))
        + 0.18 * _safe_float(scores.get("route_outcome_failure"))
    )
    goal = _safe_float(scores.get("goal_clarity"))
    if current_mode == "cognitive_first":
        return current_mode, {
            "support_pressure": round(support_pressure, 4),
            "shadow_reason": "preserve_current_cognitive_hard_guard",
        }
    if current_mode == "execution_first" and support_pressure >= 0.42:
        return "balanced", {
            "support_pressure": round(support_pressure, 4),
            "shadow_reason": "accumulated_weak_support_pressure",
        }
    if current_mode == "balanced" and support_pressure < 0.25 and goal >= 0.78:
        return "execution_first", {
            "support_pressure": round(support_pressure, 4),
            "shadow_reason": "low_support_pressure_high_goal_clarity",
        }
    return current_mode, {
        "support_pressure": round(support_pressure, 4),
        "shadow_reason": "no_shadow_change",
    }


def source_state_group(record: RoutingDecisionLog, scores: dict[str, float]) -> str:
    state = dict(record.source_state_v2 or {})
    tool = str(state.get("tool_category") or "unknown")
    sufficiency = str(state.get("sufficiency_level") or "unknown")
    calendar = str(state.get("calendar_pressure") or "unknown")
    load = _safe_float(scores.get("cognitive_load"))
    if load >= 0.78:
        load_bucket = "load_very_high"
    elif load >= 0.55:
        load_bucket = "load_high"
    elif load > 0:
        load_bucket = "load_present"
    else:
        load_bucket = "load_none"
    return f"tool={tool}|suff={sufficiency}|calendar={calendar}|{load_bucket}"


class DualCoreDecisionBench:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run(self, config: BenchConfig | None = None) -> dict[str, Any]:
        cfg = config or BenchConfig()
        records = await self._load_decisions(cfg)
        auto_outcomes = await self._load_auto_outcomes(records, cfg)
        analyses = []
        for record in records:
            route_truth = classify_route_history_truth(record)
            auto_truth = classify_auto_routing_truth(record, auto_outcomes.get(str(record.decision_id)))
            truth = choose_best_truth(route_truth, auto_truth)
            scores = _signal_scores(record)
            mode = _mode_from_record(record)
            shadow_mode, shadow_meta = conservative_shadow_mode(mode, scores)
            analyses.append(
                {
                    "record": record,
                    "mode": mode,
                    "route_execution_mode": _route_execution_mode(record),
                    "truth": truth,
                    "route_truth": route_truth,
                    "auto_truth": auto_truth,
                    "scores": scores,
                    "shadow_mode": shadow_mode,
                    "shadow_meta": shadow_meta,
                    "context_group": source_state_group(record, scores),
                }
            )
        return self._build_report(analyses, cfg)

    async def _load_decisions(self, cfg: BenchConfig) -> list[RoutingDecisionLog]:
        stmt = select(RoutingDecisionLog).order_by(RoutingDecisionLog.decided_at.desc()).limit(max(1, cfg.limit))
        if cfg.days is not None:
            stmt = stmt.where(RoutingDecisionLog.decided_at >= _utcnow() - timedelta(days=max(1, cfg.days)))
        if cfg.user_id is not None:
            stmt = stmt.where(RoutingDecisionLog.user_id == cfg.user_id)
        rows = (await self.db.execute(stmt)).scalars().all()
        return list(rows)

    async def _load_auto_outcomes(
        self,
        records: list[RoutingDecisionLog],
        cfg: BenchConfig,
    ) -> dict[str, BehavioralOutcome]:
        if not records:
            return {}
        since = min(record.decided_at for record in records)
        signal_stmt = select(PassiveSignal).where(PassiveSignal.signal_type == "routing_decision")
        signal_stmt = signal_stmt.where(PassiveSignal.timestamp >= since - timedelta(hours=1))
        if cfg.user_id is not None:
            signal_stmt = signal_stmt.where(PassiveSignal.user_id == cfg.user_id)
        signals = (await self.db.execute(signal_stmt.limit(max(cfg.limit * 3, 100)))).scalars().all()
        decision_to_intervention: dict[str, UUID] = {}
        intervention_ids: list[UUID] = []
        for signal in signals:
            context = dict(signal.context or {})
            decision_id = str(context.get("route_history_decision_id") or "").strip()
            if not decision_id or signal.intervention_id is None:
                continue
            decision_to_intervention[decision_id] = signal.intervention_id
            intervention_ids.append(signal.intervention_id)
        if not intervention_ids:
            return {}
        outcome_stmt = select(BehavioralOutcome).where(BehavioralOutcome.intervention_id.in_(intervention_ids))
        outcome_stmt = outcome_stmt.where(BehavioralOutcome.outcome_type == "routing_effectiveness")
        outcomes = (await self.db.execute(outcome_stmt)).scalars().all()
        intervention_to_outcome = {
            str(outcome.intervention_id): outcome
            for outcome in sorted(outcomes, key=lambda item: item.timestamp or datetime.min)
        }
        return {
            decision_id: intervention_to_outcome[str(intervention_id)]
            for decision_id, intervention_id in decision_to_intervention.items()
            if str(intervention_id) in intervention_to_outcome
        }

    def _build_report(self, analyses: list[dict[str, Any]], cfg: BenchConfig) -> dict[str, Any]:
        total = len(analyses)
        known = [item for item in analyses if item["truth"].is_known]
        binary_known = [item for item in analyses if item["truth"].is_binary_known]
        mode_counts = Counter(item["mode"] for item in analyses)
        evidence_counts = Counter(item["truth"].evidence_level for item in analyses)
        label_counts = Counter(item["truth"].label for item in analyses)
        latency_values = [
            float(item["truth"].latency_seconds)
            for item in analyses
            if item["truth"].latency_seconds is not None
        ]

        by_mode: dict[str, dict[str, Any]] = {}
        for mode in sorted(mode_counts):
            items = [item for item in analyses if item["mode"] == mode]
            mode_binary = [item for item in items if item["truth"].is_binary_known]
            success = sum(1 for item in mode_binary if item["truth"].label == SUCCESS_LABEL)
            failure = sum(1 for item in mode_binary if item["truth"].label == FAILURE_LABEL)
            by_mode[mode] = {
                "count": len(items),
                "known_count": sum(1 for item in items if item["truth"].is_known),
                "unknown_count": sum(1 for item in items if not item["truth"].is_known),
                "success": success,
                "failure": failure,
                "success_rate_known_binary": round(success / len(mode_binary), 4) if mode_binary else None,
                "evidence_levels": dict(Counter(item["truth"].evidence_level for item in items)),
            }

        report = {
            "generated_at": _utcnow().isoformat(),
            "config": asdict(cfg),
            "coverage": {
                "total_decisions": total,
                "known_outcome_count": len(known),
                "binary_known_outcome_count": len(binary_known),
                "known_outcome_rate": round(len(known) / total, 4) if total else 0.0,
                "binary_known_outcome_rate": round(len(binary_known) / total, 4) if total else 0.0,
                "unknown_count": total - len(known),
            },
            "mode_distribution": dict(mode_counts),
            "truth_label_distribution": dict(label_counts),
            "evidence_distribution": dict(evidence_counts),
            "outcome_latency_seconds": {
                "count": len(latency_values),
                "p50": _percentile(latency_values, 0.5),
                "p90": _percentile(latency_values, 0.9),
                "max": round(max(latency_values), 3) if latency_values else None,
            },
            "outcome_by_mode": by_mode,
            "signal_outcome_table": self._signal_outcome_table(binary_known),
            "shadow_overlay": self._shadow_overlay_report(analyses, cfg),
            "pseudo_causal_context_groups": self._pseudo_causal_groups(binary_known, cfg),
            "warnings": self._warnings(total, known, mode_counts, evidence_counts),
        }
        return report

    def _signal_outcome_table(self, analyses: list[dict[str, Any]]) -> dict[str, Any]:
        table: dict[str, Any] = {}
        for signal, threshold in SIGNAL_THRESHOLDS.items():
            with_signal = [item for item in analyses if signal in item["scores"]]
            if not with_signal:
                continue
            high = [item for item in with_signal if _safe_float(item["scores"].get(signal)) >= threshold]
            low = [item for item in with_signal if _safe_float(item["scores"].get(signal)) < threshold]
            table[signal] = {
                "threshold": threshold,
                "count": len(with_signal),
                "mean_value": round(
                    sum(_safe_float(item["scores"].get(signal)) for item in with_signal) / len(with_signal),
                    4,
                ),
                "high_count": len(high),
                "low_count": len(low),
                "high_failure_rate": self._failure_rate(high),
                "low_failure_rate": self._failure_rate(low),
                "failure_rate_delta_high_minus_low": self._rate_delta(high, low),
            }
        return table

    @staticmethod
    def _failure_rate(items: list[dict[str, Any]]) -> float | None:
        if not items:
            return None
        failures = sum(1 for item in items if item["truth"].label == FAILURE_LABEL)
        return round(failures / len(items), 4)

    def _rate_delta(self, high: list[dict[str, Any]], low: list[dict[str, Any]]) -> float | None:
        high_rate = self._failure_rate(high)
        low_rate = self._failure_rate(low)
        if high_rate is None or low_rate is None:
            return None
        return round(high_rate - low_rate, 4)

    def _shadow_overlay_report(self, analyses: list[dict[str, Any]], cfg: BenchConfig) -> dict[str, Any]:
        divergences = [item for item in analyses if item["mode"] != item["shadow_mode"]]
        by_transition = Counter(f"{item['mode']}->{item['shadow_mode']}" for item in divergences)
        by_truth = Counter(item["truth"].label for item in divergences)
        examples = [
            DecisionExample(
                decision_id=str(item["record"].decision_id),
                decided_at=item["record"].decided_at.isoformat(),
                mode=item["mode"],
                shadow_mode=item["shadow_mode"],
                truth_label=item["truth"].label,
                evidence_level=item["truth"].evidence_level,
                reason=str(item["shadow_meta"].get("shadow_reason") or ""),
                signal_scores=dict(item["scores"]),
                source_state_v2_key=item["record"].source_state_v2_key,
            ).__dict__
            for item in divergences[: max(0, cfg.examples)]
        ]
        return {
            "policy": "conservative_continuous_overlay_v0",
            "divergence_count": len(divergences),
            "divergence_rate": round(len(divergences) / len(analyses), 4) if analyses else 0.0,
            "by_transition": dict(by_transition),
            "truth_labels_for_divergences": dict(by_truth),
            "examples": examples,
        }

    def _pseudo_causal_groups(
        self,
        analyses: list[dict[str, Any]],
        cfg: BenchConfig,
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in analyses:
            grouped[item["context_group"]].append(item)
        rows: list[dict[str, Any]] = []
        for group, items in grouped.items():
            if len(items) < cfg.min_group_size:
                continue
            modes = sorted({item["mode"] for item in items})
            if len(modes) < 2:
                continue
            mode_rows = {}
            for mode in modes:
                mode_items = [item for item in items if item["mode"] == mode]
                mode_rows[mode] = {
                    "count": len(mode_items),
                    "failure_rate": self._failure_rate(mode_items),
                    "success_rate": self._success_rate(mode_items),
                }
            rows.append({"context_group": group, "count": len(items), "modes": mode_rows})
        rows.sort(key=lambda row: row["count"], reverse=True)
        return rows[:50]

    @staticmethod
    def _success_rate(items: list[dict[str, Any]]) -> float | None:
        if not items:
            return None
        successes = sum(1 for item in items if item["truth"].label == SUCCESS_LABEL)
        return round(successes / len(items), 4)

    @staticmethod
    def _warnings(
        total: int,
        known: list[dict[str, Any]],
        mode_counts: Counter,
        evidence_counts: Counter,
    ) -> list[str]:
        warnings = []
        if total == 0:
            return ["No DualCore routing decisions matched the selected filters."]
        known_rate = len(known) / total
        if known_rate < 0.5:
            warnings.append("Outcome coverage is below 50%; learned models may be biased by missing labels.")
        if evidence_counts.get(EVIDENCE_EXPLICIT_FEEDBACK, 0) < max(5, total * 0.05):
            warnings.append("Explicit feedback evidence is sparse; user-experience labels are underrepresented.")
        if mode_counts:
            most_common = mode_counts.most_common(1)[0]
            if most_common[1] / total > 0.8:
                warnings.append(
                    f"Mode distribution is imbalanced ({most_common[0]}={most_common[1]}/{total}); "
                    "mode-level model comparisons may be unstable."
                )
        return warnings


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# DualCore Decision Bench Report",
        "",
        f"Generated: `{report.get('generated_at')}`",
        "",
        "## Coverage",
    ]
    coverage = report.get("coverage") or {}
    for key in (
        "total_decisions",
        "known_outcome_count",
        "known_outcome_rate",
        "binary_known_outcome_count",
        "binary_known_outcome_rate",
        "unknown_count",
    ):
        lines.append(f"- `{key}`: {coverage.get(key)}")

    lines.extend(["", "## Mode Distribution"])
    for mode, count in sorted((report.get("mode_distribution") or {}).items()):
        lines.append(f"- `{mode}`: {count}")

    lines.extend(["", "## Outcome By Mode"])
    lines.append("| Mode | Count | Known | Unknown | Success | Failure | Known Binary Success Rate |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for mode, payload in sorted((report.get("outcome_by_mode") or {}).items()):
        lines.append(
            "| {mode} | {count} | {known} | {unknown} | {success} | {failure} | {rate} |".format(
                mode=mode,
                count=payload.get("count"),
                known=payload.get("known_count"),
                unknown=payload.get("unknown_count"),
                success=payload.get("success"),
                failure=payload.get("failure"),
                rate=payload.get("success_rate_known_binary"),
            )
        )

    lines.extend(["", "## Evidence Distribution"])
    for evidence, count in sorted((report.get("evidence_distribution") or {}).items()):
        lines.append(f"- `{evidence}`: {count}")

    lines.extend(["", "## Signal Outcome Table"])
    lines.append("| Signal | Count | Threshold | High Count | High Failure | Low Failure | Delta |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for signal, payload in sorted((report.get("signal_outcome_table") or {}).items()):
        lines.append(
            "| {signal} | {count} | {threshold} | {high_count} | {high_failure} | {low_failure} | {delta} |".format(
                signal=signal,
                count=payload.get("count"),
                threshold=payload.get("threshold"),
                high_count=payload.get("high_count"),
                high_failure=payload.get("high_failure_rate"),
                low_failure=payload.get("low_failure_rate"),
                delta=payload.get("failure_rate_delta_high_minus_low"),
            )
        )

    shadow = report.get("shadow_overlay") or {}
    lines.extend(["", "## Conservative Shadow Overlay"])
    lines.append(f"- `policy`: {shadow.get('policy')}")
    lines.append(f"- `divergence_count`: {shadow.get('divergence_count')}")
    lines.append(f"- `divergence_rate`: {shadow.get('divergence_rate')}")
    for transition, count in sorted((shadow.get("by_transition") or {}).items()):
        lines.append(f"- `{transition}`: {count}")

    if shadow.get("examples"):
        lines.extend(["", "### Divergence Examples"])
        for example in shadow["examples"]:
            lines.append(
                "- `{decision_id}` `{mode}->{shadow}` truth=`{truth}` evidence=`{evidence}` reason=`{reason}`".format(
                    decision_id=example.get("decision_id"),
                    mode=example.get("mode"),
                    shadow=example.get("shadow_mode"),
                    truth=example.get("truth_label"),
                    evidence=example.get("evidence_level"),
                    reason=example.get("reason"),
                )
            )

    groups = report.get("pseudo_causal_context_groups") or []
    lines.extend(["", "## Pseudo-Causal Context Groups"])
    if not groups:
        lines.append("No context group had enough labeled mixed-mode samples for comparison.")
    else:
        for group in groups[:10]:
            lines.append(f"- `{group['context_group']}` count={group['count']} modes={json.dumps(group['modes'], ensure_ascii=False)}")

    warnings = report.get("warnings") or []
    if warnings:
        lines.extend(["", "## Warnings"])
        for warning in warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines).rstrip() + "\n"

