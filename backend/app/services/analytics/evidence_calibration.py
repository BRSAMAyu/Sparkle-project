from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
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


def _as_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, *, default: int = 1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ConfidenceBin:
    bin_low: float
    bin_high: float
    evidence_count: int
    correct_count: int
    accuracy: float
    average_confidence: float
    calibration_error: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "bin_low": round(self.bin_low, 2),
            "bin_high": round(self.bin_high, 2),
            "evidence_count": self.evidence_count,
            "correct_count": self.correct_count,
            "accuracy": round(self.accuracy, 4),
            "average_confidence": round(self.average_confidence, 4),
            "calibration_error": round(self.calibration_error, 4),
        }


@dataclass(frozen=True)
class SourceTypeCalibration:
    source_type: str
    total_evidence: int
    paired_evidence: int
    overall_accuracy: float
    overall_avg_confidence: float
    overall_calibration_error: float
    confidence_bins: list[ConfidenceBin]
    recalibration_coefficient: float
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "total_evidence": self.total_evidence,
            "paired_evidence": self.paired_evidence,
            "overall_accuracy": round(self.overall_accuracy, 4),
            "overall_avg_confidence": round(self.overall_avg_confidence, 4),
            "overall_calibration_error": round(self.overall_calibration_error, 4),
            "confidence_bins": [cb.to_dict() for cb in self.confidence_bins],
            "recalibration_coefficient": round(self.recalibration_coefficient, 4),
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class EvidenceCalibrationReport:
    total_traces_analyzed: int
    total_correction_events: int
    total_evidence_paired: int
    source_type_results: list[SourceTypeCalibration]
    global_recalibration_recommended: bool
    global_recalibration_multiplier: float
    recommendation: str
    blockers: list[str] = field(default_factory=list)
    methodology: str = (
        "Compare each evidence item's self-reported confidence against whether "
        "its direction prediction agreed with the user's later correction. "
        "Binned by confidence level (0.5-0.6, 0.6-0.7, ..., 0.9-1.0). "
        "A well-calibrated extractor shows accuracy ≈ average_confidence in each bin. "
        "Overconfidence (accuracy < confidence) is typical and indicates a need "
        "for recalibration. Underconfidence (accuracy > confidence) suggests "
        "the extractor is too conservative."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "evidence_calibration.v1",
            "total_traces_analyzed": self.total_traces_analyzed,
            "total_correction_events": self.total_correction_events,
            "total_evidence_paired": self.total_evidence_paired,
            "source_type_results": [st.to_dict() for st in self.source_type_results],
            "global_recalibration_recommended": self.global_recalibration_recommended,
            "global_recalibration_multiplier": round(self.global_recalibration_multiplier, 4),
            "recommendation": self.recommendation,
            "blockers": self.blockers,
            "methodology": self.methodology,
        }


class EvidenceCalibrationAnalyzer:
    """Calibrate LLM evidence confidence against user correction ground truth.

    The core question: when the LLM says it's 0.80 confident about an evidence
    direction, is it actually right 80% of the time?

    This uses user corrections (submitted via /cognitive/belief-corrections) as
    proxy ground truth: if a user corrects emotional_block downward, then
    recent evidence that pushed emotional_block upward was incorrect.
    """

    CONFIDENCE_BINS = [
        (0.50, 0.60),
        (0.60, 0.70),
        (0.70, 0.80),
        (0.80, 0.90),
        (0.90, 1.00),
    ]

    def __init__(
        self,
        *,
        min_correction_events: int = 20,
        min_paired_evidence: int = 30,
        recalibration_overconfidence_threshold: float = 0.10,
    ) -> None:
        self.min_correction_events = min_correction_events
        self.min_paired_evidence = min_paired_evidence
        self.recalibration_overconfidence_threshold = recalibration_overconfidence_threshold

    def evaluate(
        self,
        raw_traces: list[Any],
        correction_events: list[dict[str, Any]] | None = None,
    ) -> EvidenceCalibrationReport:
        resolved_corrections = correction_events or []
        corrections = self._parse_corrections(raw_traces, resolved_corrections)

        total_traces = len(raw_traces)
        if not corrections:
            return EvidenceCalibrationReport(
                total_traces_analyzed=total_traces,
                total_correction_events=0,
                total_evidence_paired=0,
                source_type_results=[],
                global_recalibration_recommended=False,
                global_recalibration_multiplier=1.0,
                recommendation="collect_belief_correction_events_first",
                blockers=["no_correction_events_found"],
            )

        by_source: dict[str, list[tuple[float, bool]]] = defaultdict(list)
        for correction in corrections:
            source_type = correction.get("source_type", "unknown")
            confidence = _as_float(correction.get("confidence"), default=0.65)
            matched = bool(correction.get("direction_matched", False))
            if correction.get("direction_matched") is not None:
                by_source[source_type].append((confidence, matched))

        source_results: list[SourceTypeCalibration] = []
        global_paired = 0
        global_weighted_error = 0.0
        global_weight_sum = 0.0

        for source_type in sorted(by_source):
            pairs = by_source[source_type]
            total = len(pairs)
            if total < 5:
                continue
            global_paired += total
            correct = sum(1 for _, matched in pairs if matched)
            accuracy = correct / total if total else 0.0
            avg_conf = sum(conf for conf, _ in pairs) / total if total else 0.0
            error = avg_conf - accuracy

            bins: list[ConfidenceBin] = []
            for bin_low, bin_high in self.CONFIDENCE_BINS:
                bin_pairs = [(c, m) for c, m in pairs if bin_low <= c < bin_high]
                bin_n = len(bin_pairs)
                if bin_n < 3:
                    continue
                bin_correct = sum(1 for _, matched in bin_pairs if matched)
                bin_acc = bin_correct / bin_n
                bin_avg_conf = sum(c for c, _ in bin_pairs) / bin_n
                bin_err = bin_avg_conf - bin_acc
                bins.append(ConfidenceBin(
                    bin_low=bin_low,
                    bin_high=bin_high,
                    evidence_count=bin_n,
                    correct_count=bin_correct,
                    accuracy=round(bin_acc, 4),
                    average_confidence=round(bin_avg_conf, 4),
                    calibration_error=round(bin_err, 4),
                ))

            global_weighted_error += error * total
            global_weight_sum += total

            overconfident = error > self.recalibration_overconfidence_threshold
            recalibrate = 1.0 - error if overconfident and error > 0 else 1.0
            if recalibrate < 0.5:
                recalibrate = 0.5

            if overconfident:
                recommendation = (
                    f"recalibrate_by_multiplying_confidence_by_{round(recalibrate, 2)}"
                )
            elif error < -self.recalibration_overconfidence_threshold:
                recommendation = (
                    "underconfident_extractor_consider_raising_default_confidence"
                )
            else:
                recommendation = "well_calibrated"

            source_results.append(SourceTypeCalibration(
                source_type=source_type,
                total_evidence=total,
                paired_evidence=total,
                overall_accuracy=round(accuracy, 4),
                overall_avg_confidence=round(avg_conf, 4),
                overall_calibration_error=round(error, 4),
                confidence_bins=bins,
                recalibration_coefficient=round(recalibrate, 4),
                recommendation=recommendation,
            ))

        global_error = global_weighted_error / global_weight_sum if global_weight_sum else 0.0
        global_recal = 1.0 - global_error if global_error > self.recalibration_overconfidence_threshold else 1.0
        global_recal = max(0.5, min(1.0, global_recal))

        if global_paired < self.min_paired_evidence:
            return EvidenceCalibrationReport(
                total_traces_analyzed=total_traces,
                total_correction_events=len(corrections),
                total_evidence_paired=global_paired,
                source_type_results=source_results,
                global_recalibration_recommended=False,
                global_recalibration_multiplier=1.0,
                recommendation="insufficient_paired_evidence_for_calibration",
                blockers=[f"need_{self.min_paired_evidence}_paired_samples_have_{global_paired}"],
            )

        recal_needed = global_error > self.recalibration_overconfidence_threshold
        if recal_needed:
            recommendation = f"apply_global_confidence_multiplier_{round(global_recal, 2)}"
        elif global_error < -self.recalibration_overconfidence_threshold:
            recommendation = "extractor_underconfident_review_prompt_or_raise_defaults"
        else:
            recommendation = "extractor_well_calibrated_no_recalibration_needed"

        return EvidenceCalibrationReport(
            total_traces_analyzed=total_traces,
            total_correction_events=len(corrections),
            total_evidence_paired=global_paired,
            source_type_results=source_results,
            global_recalibration_recommended=recal_needed,
            global_recalibration_multiplier=round(global_recal, 4),
            recommendation=recommendation,
        )

    @staticmethod
    def _parse_corrections(
        raw_traces: list[Any],
        explicit_events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        corrections: list[dict[str, Any]] = []
        for event in explicit_events:
            corrections.append({
                "source_type": str(event.get("source_type") or "conversational_implicit"),
                "confidence": event.get("confidence"),
                "direction_matched": event.get("direction_matched"),
                "target": event.get("target"),
            })

        if explicit_events:
            return corrections

        for raw in raw_traces:
            trace = _loads(raw)
            if trace is None:
                continue
            outcome_binding = trace.get("outcome_binding")
            if not isinstance(outcome_binding, dict):
                outcome_binding = trace.get("outcome_binding_diagnostics")
            if not isinstance(outcome_binding, dict):
                continue
            correction = outcome_binding.get("correction")
            if not correction:
                continue
            evidence_snapshots = trace.get("evidence_items") or trace.get("evidence_snapshot")
            if not isinstance(evidence_snapshots, list):
                continue
            for item in evidence_snapshots:
                if not isinstance(item, dict):
                    continue
                source = str(item.get("source_type") or "unknown")
                confidence = _as_float(item.get("confidence"))
                target = str(item.get("target") or "")
                direction = str(item.get("direction") or "")
                corrected_dir = str(correction.get("direction") or "")
                if target == str(correction.get("target") or ""):
                    matched = direction == corrected_dir
                    corrections.append({
                        "source_type": source,
                        "confidence": confidence,
                        "direction_matched": matched,
                        "target": target,
                    })
        return corrections
