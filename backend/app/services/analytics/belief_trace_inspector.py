from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any


def _loads(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _shadow_mode(trace: dict[str, Any]) -> str | None:
    projection = trace.get("router_shadow_projection")
    if isinstance(projection, dict):
        mode = projection.get("shadow_mode")
        if mode:
            return str(mode)
    return None


def _actual_mode(trace: dict[str, Any]) -> str | None:
    mode = trace.get("actual_router_mode")
    if mode:
        return str(mode)
    snapshot = trace.get("router_snapshot")
    if isinstance(snapshot, dict) and snapshot.get("actual_router_mode"):
        return str(snapshot["actual_router_mode"])
    action = trace.get("action_taken")
    if isinstance(action, dict) and action.get("mode"):
        return str(action["mode"])
    return None


def _disagreement_type(actual: str, shadow: str) -> str:
    if actual == "execution_first" and shadow == "cognitive_first":
        return "type_1_over_hard"
    if actual == "cognitive_first" and shadow == "execution_first":
        return "type_2_over_support"
    if shadow == "balanced":
        return "shadow_balanced"
    if actual == "balanced":
        return "actual_balanced"
    return "other"


class BeliefTraceInspector:
    """Inspect Aurora belief traces before the full statistical audit exists."""

    TRACE_KEY = "aurora:belief_trace:v1:{user_id}"

    def summarize(self, raw_traces: list[Any]) -> dict[str, Any]:
        total = len(raw_traces)
        parse_errors = 0
        with_actual = 0
        with_shadow = 0
        disagreements = 0
        actual_counts: Counter[str] = Counter()
        shadow_counts: Counter[str] = Counter()
        disagreement_counts: Counter[str] = Counter()
        missing_fields: Counter[str] = Counter()
        outcome_counts: Counter[str] = Counter()
        reward_signal_counts: Counter[str] = Counter()
        reward_category_counts: Counter[str] = Counter()
        evidence_source_counts: Counter[str] = Counter()
        target_evidence_counts: Counter[str] = Counter()
        cognitive_load_type_counts: Counter[str] = Counter()
        stage_of_change_counts: Counter[str] = Counter()
        confidence_discount_count = 0
        same_source_correlation_discount_count = 0
        same_source_correlation_group_count = 0
        same_source_correlation_max_group_size = 0
        belief_projection_count = 0
        belief_projection_target_counts: Counter[str] = Counter()
        uncertainty_sums: dict[str, float] = defaultdict(float)
        uncertainty_counts: Counter[str] = Counter()
        belief_mean_sums: dict[str, float] = defaultdict(float)
        belief_mean_counts: Counter[str] = Counter()
        mode_outcome_counts: dict[str, Counter[str]] = {}
        mode_load_type_outcome_counts: dict[str, dict[str, Counter[str]]] = {}
        total_evidence_count = 0
        traces_with_evidence = 0
        training_eligible = 0
        observed_outcomes = 0
        censored_outcomes = 0
        total_reward = 0.0
        reward_count = 0
        examples: list[dict[str, Any]] = []

        for raw in raw_traces:
            trace = _loads(raw)
            if trace is None:
                parse_errors += 1
                continue
            actual = _actual_mode(trace)
            shadow = _shadow_mode(trace)
            if actual:
                with_actual += 1
                actual_counts[actual] += 1
            else:
                missing_fields["actual_router_mode"] += 1
            if shadow:
                with_shadow += 1
                shadow_counts[shadow] += 1
            else:
                missing_fields["router_shadow_projection.shadow_mode"] += 1
            outcome = str(trace.get("outcome") or "unknown")
            outcome_counts[outcome] += 1
            if actual:
                mode_outcome_counts.setdefault(actual, Counter())[outcome] += 1
            if outcome == "unknown" or trace.get("outcome_status") == "censored":
                censored_outcomes += 1
            else:
                observed_outcomes += 1
            if bool(trace.get("training_eligible")):
                training_eligible += 1
            reward = trace.get("reward")
            if isinstance(reward, dict):
                signal_type = str(reward.get("signal_type") or "unknown")
                reward_signal_counts[signal_type] += 1
                reward_category_counts[str(reward.get("reward_category") or "unknown")] += 1
                if reward.get("total_reward") is not None:
                    try:
                        total_reward += float(reward.get("total_reward"))
                        reward_count += 1
                    except (TypeError, ValueError):
                        pass
            else:
                missing_fields["reward"] += 1
            source_breakdown = trace.get("belief_source_breakdown")
            if isinstance(source_breakdown, dict):
                total_sources = source_breakdown.get("total")
                if isinstance(total_sources, dict):
                    for source, count in total_sources.items():
                        try:
                            evidence_source_counts[str(source)] += int(count)
                        except (TypeError, ValueError):
                            pass
                by_target = source_breakdown.get("by_target")
                if isinstance(by_target, dict):
                    for target, source_counts in by_target.items():
                        if isinstance(source_counts, dict):
                            try:
                                target_evidence_counts[str(target)] += sum(int(value) for value in source_counts.values())
                            except (TypeError, ValueError):
                                pass
            metadata_summary = trace.get("evidence_metadata_summary")
            if isinstance(metadata_summary, dict):
                try:
                    confidence_discount_count += int(metadata_summary.get("confidence_discount_count") or 0)
                except (TypeError, ValueError):
                    pass
                try:
                    same_source_correlation_discount_count += int(
                        metadata_summary.get("same_source_correlation_discount_count") or 0
                    )
                except (TypeError, ValueError):
                    pass
                try:
                    same_source_correlation_group_count += int(
                        metadata_summary.get("same_source_correlation_group_count") or 0
                    )
                except (TypeError, ValueError):
                    pass
                try:
                    same_source_correlation_max_group_size = max(
                        same_source_correlation_max_group_size,
                        int(metadata_summary.get("same_source_correlation_max_group_size") or 0),
                    )
                except (TypeError, ValueError):
                    pass
                load_counts = metadata_summary.get("cognitive_load_type_counts")
                if isinstance(load_counts, dict):
                    for load_type, count in load_counts.items():
                        try:
                            parsed_count = int(count)
                        except (TypeError, ValueError):
                            continue
                        cognitive_load_type_counts[str(load_type)] += parsed_count
                        if actual:
                            mode_load_type_outcome_counts.setdefault(actual, {}).setdefault(str(load_type), Counter())[
                                outcome
                            ] += parsed_count
                stage_counts = metadata_summary.get("stage_of_change_counts")
                if isinstance(stage_counts, dict):
                    for stage, count in stage_counts.items():
                        try:
                            stage_of_change_counts[str(stage)] += int(count)
                        except (TypeError, ValueError):
                            pass
            else:
                load_counts = trace.get("cognitive_load_type_counts")
                if isinstance(load_counts, dict):
                    for load_type, count in load_counts.items():
                        try:
                            cognitive_load_type_counts[str(load_type)] += int(count)
                        except (TypeError, ValueError):
                            pass
            projection_diagnostics = trace.get("belief_projection_diagnostics")
            if isinstance(projection_diagnostics, dict):
                try:
                    belief_projection_count += int(projection_diagnostics.get("projected_target_count") or 0)
                except (TypeError, ValueError):
                    pass
                projected_targets = projection_diagnostics.get("projected_targets")
                if isinstance(projected_targets, dict):
                    for target in projected_targets:
                        belief_projection_target_counts[str(target)] += 1
            variable_counts = trace.get("belief_variable_evidence_counts")
            if isinstance(variable_counts, dict):
                trace_evidence_count = 0
                for target, count in variable_counts.items():
                    try:
                        parsed_count = int(count)
                        target_evidence_counts[str(target)] += parsed_count
                        trace_evidence_count += parsed_count
                    except (TypeError, ValueError):
                        pass
                total_evidence_count += trace_evidence_count
                if trace_evidence_count > 0:
                    traces_with_evidence += 1
            uncertainty = trace.get("belief_uncertainty_vector")
            if isinstance(uncertainty, dict):
                for target, variance in uncertainty.items():
                    try:
                        uncertainty_sums[str(target)] += float(variance)
                        uncertainty_counts[str(target)] += 1
                    except (TypeError, ValueError):
                        pass
            state_vector = trace.get("belief_state_vector")
            if isinstance(state_vector, dict):
                for key, value in state_vector.items():
                    if not str(key).endswith("_mean"):
                        continue
                    target = str(key)[: -len("_mean")]
                    try:
                        belief_mean_sums[target] += float(value)
                        belief_mean_counts[target] += 1
                    except (TypeError, ValueError):
                        pass
            if actual and shadow and actual != shadow:
                disagreements += 1
                kind = _disagreement_type(actual, shadow)
                disagreement_counts[kind] += 1
                if len(examples) < 10:
                    projection = trace.get("router_shadow_projection") if isinstance(trace, dict) else {}
                    examples.append(
                        {
                            "trace_id": trace.get("trace_id"),
                            "timestamp": trace.get("timestamp"),
                            "actual_router_mode": actual,
                            "shadow_mode": shadow,
                            "disagreement_type": kind,
                            "support_pressure_score": (
                                projection.get("support_pressure_score") if isinstance(projection, dict) else None
                            ),
                            "execution_readiness_score": (
                                projection.get("execution_readiness_score") if isinstance(projection, dict) else None
                            ),
                            "outcome": trace.get("outcome"),
                            "action_taken": trace.get("action_taken"),
                        }
                    )

        comparable = min(with_actual, with_shadow)
        average_uncertainty = {
            target: round(float(uncertainty_sums[target]) / max(1, uncertainty_counts[target]), 4)
            for target in sorted(uncertainty_sums)
        }
        average_belief_means = {
            target: round(float(belief_mean_sums[target]) / max(1, belief_mean_counts[target]), 4)
            for target in sorted(belief_mean_sums)
        }
        high_uncertainty_targets = sorted(
            average_uncertainty.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:5]
        evidence_total = sum(evidence_source_counts.values())
        llm_sources = {
            "conversational_implicit",
            "conversational_explicit",
        }
        llm_evidence_count = sum(evidence_source_counts.get(source, 0) for source in llm_sources)
        fallback_evidence_count = evidence_source_counts.get("heuristic_fallback", 0)
        llm_evidence_rate = llm_evidence_count / evidence_total if evidence_total else 0.0
        fallback_evidence_rate = fallback_evidence_count / evidence_total if evidence_total else 0.0
        load_total = sum(cognitive_load_type_counts.values())
        extraneous_load_rate = cognitive_load_type_counts.get("extraneous", 0) / load_total if load_total else 0.0
        absolute_quality = self._absolute_quality(
            mode_outcome_counts=mode_outcome_counts,
            mode_load_type_outcome_counts=mode_load_type_outcome_counts,
        )
        try:
            from app.services.analytics.router_absolute_quality import RouterAbsoluteQualityAnalyzer

            within_belief_region_quality = RouterAbsoluteQualityAnalyzer().evaluate(raw_traces).to_dict()
        except Exception as exc:
            within_belief_region_quality = {
                "schema_version": "router_absolute_quality.v1",
                "blockers": ["absolute_quality_analyzer_failed"],
                "error": str(exc),
            }
        f1_blockers: list[str] = []
        if total - parse_errors <= 0:
            f1_blockers.append("no_parseable_traces")
        if comparable <= 0:
            f1_blockers.append("no_actual_shadow_comparable_traces")
        if total_evidence_count <= 0:
            f1_blockers.append("no_evidence_in_traces")
        if evidence_total > 0 and llm_evidence_rate < 0.25:
            f1_blockers.append("llm_evidence_rate_below_25_percent")
        return {
            "schema_version": "belief_trace_inspection.v1",
            "total_traces": total,
            "parse_errors": parse_errors,
            "with_actual_router_mode": with_actual,
            "with_shadow_mode": with_shadow,
            "comparable_traces": comparable,
            "disagreements": disagreements,
            "disagreement_rate": round(disagreements / comparable, 4) if comparable else 0.0,
            "actual_mode_counts": dict(actual_counts),
            "shadow_mode_counts": dict(shadow_counts),
            "disagreement_type_counts": dict(disagreement_counts),
            "outcome_counts": dict(outcome_counts),
            "observed_outcomes": observed_outcomes,
            "censored_outcomes": censored_outcomes,
            "outcome_coverage_rate": round(observed_outcomes / max(1, total - parse_errors), 4),
            "training_eligible_traces": training_eligible,
            "training_eligible_rate": round(training_eligible / max(1, total - parse_errors), 4),
            "reward_signal_counts": dict(reward_signal_counts),
            "reward_category_counts": dict(reward_category_counts),
            "average_total_reward": round(total_reward / reward_count, 4) if reward_count else 0.0,
            "evidence_source_counts": dict(evidence_source_counts),
            "llm_evidence_count": llm_evidence_count,
            "llm_evidence_rate": round(llm_evidence_rate, 4),
            "heuristic_fallback_evidence_count": fallback_evidence_count,
            "heuristic_fallback_evidence_rate": round(fallback_evidence_rate, 4),
            "confidence_discount_count": confidence_discount_count,
            "same_source_correlation_discount_count": same_source_correlation_discount_count,
            "same_source_correlation_group_count": same_source_correlation_group_count,
            "same_source_correlation_max_group_size": same_source_correlation_max_group_size,
            "belief_projection_count": belief_projection_count,
            "belief_projection_target_counts": dict(belief_projection_target_counts),
            "target_evidence_counts": dict(target_evidence_counts),
            "cognitive_load_type_counts": dict(cognitive_load_type_counts),
            "stage_of_change_counts": dict(stage_of_change_counts),
            "extraneous_load_rate": round(extraneous_load_rate, 4),
            "average_evidence_per_trace": round(total_evidence_count / max(1, total - parse_errors), 4),
            "traces_with_evidence": traces_with_evidence,
            "trace_evidence_coverage_rate": round(traces_with_evidence / max(1, total - parse_errors), 4),
            "average_belief_mean_by_target": average_belief_means,
            "average_uncertainty_by_target": average_uncertainty,
            "high_uncertainty_targets": high_uncertainty_targets,
            "f1_quality_gate": {
                "passed": not f1_blockers,
                "blockers": f1_blockers,
                "minimum_llm_evidence_rate": 0.25,
                "note": "Redis trace presence is not enough; F1 also requires evidence, actual/shadow comparison, and non-trivial LLM evidence share.",
            },
            "missing_field_counts": dict(missing_fields),
            "absolute_quality": absolute_quality,
            "within_belief_region_quality": within_belief_region_quality,
            "examples": examples,
        }

    async def summarize_redis(self, redis: Any, *, user_id: str, limit: int = 200) -> dict[str, Any]:
        key = self.TRACE_KEY.format(user_id=user_id)
        raw = await redis.lrange(key, 0, max(0, limit - 1))
        summary = self.summarize(list(raw or []))
        summary["redis_key"] = key
        summary["limit"] = limit
        lost_key = f"aurora:belief_trace_lost:v1:{user_id}"
        error_key = f"aurora:belief_collector_error:v1:{user_id}"
        calibration_key = f"aurora:evidence_calibration:v1:{user_id}"
        try:
            raw_lost = await redis.get(lost_key)
            if isinstance(raw_lost, bytes):
                raw_lost = raw_lost.decode("utf-8", errors="replace")
            summary["trace_lost_count"] = int(raw_lost or 0)
        except Exception:
            summary["trace_lost_count"] = None
        try:
            raw_error = await redis.get(error_key)
            if isinstance(raw_error, bytes):
                raw_error = raw_error.decode("utf-8", errors="replace")
            summary["collector_last_error"] = raw_error
        except Exception:
            summary["collector_last_error"] = None
        try:
            calibration_raw = await redis.lrange(calibration_key, 0, 299)
            from app.services.analytics.evidence_calibration import EvidenceCalibrationAnalyzer

            summary["evidence_calibration"] = EvidenceCalibrationAnalyzer().evaluate(
                [],
                correction_events=[_loads(item) for item in calibration_raw if _loads(item) is not None],
            ).to_dict()
        except Exception as exc:
            summary["evidence_calibration"] = {"blockers": ["calibration_read_failed"], "error": str(exc)}
        return summary

    @staticmethod
    def _absolute_quality(
        *,
        mode_outcome_counts: dict[str, Counter[str]],
        mode_load_type_outcome_counts: dict[str, dict[str, Counter[str]]],
    ) -> dict[str, Any]:
        serial_mode_counts = {
            mode: dict(counter)
            for mode, counter in sorted(mode_outcome_counts.items())
        }
        serial_load_counts = {
            mode: {load_type: dict(counter) for load_type, counter in sorted(load_map.items())}
            for mode, load_map in sorted(mode_load_type_outcome_counts.items())
        }
        observed_totals: dict[str, int] = {}
        completion_rates: dict[str, float] = {}
        for mode, counter in mode_outcome_counts.items():
            observed = sum(count for outcome, count in counter.items() if outcome != "unknown")
            observed_totals[mode] = observed
            completions = counter.get("task_completion", 0) + counter.get("explicit_gratitude", 0)
            completion_rates[mode] = round(completions / observed, 4) if observed else 0.0

        blockers: list[str] = []
        total_observed = sum(observed_totals.values())
        if total_observed < 20:
            blockers.append("insufficient_observed_outcomes")
        if sum(1 for value in observed_totals.values() if value >= 5) < 2:
            blockers.append("insufficient_mode_coverage")
        if total_observed >= 20 and completion_rates:
            spread = max(completion_rates.values()) - min(completion_rates.values())
            if spread < 0.05:
                blockers.append("router_leverage_uncertain")

        return {
            "schema_version": "router_absolute_quality.v1",
            "mode_outcome_counts": serial_mode_counts,
            "mode_cognitive_load_type_outcome_counts": serial_load_counts,
            "observed_outcome_counts_by_mode": observed_totals,
            "positive_rate_by_mode": completion_rates,
            "blockers": blockers,
        }
