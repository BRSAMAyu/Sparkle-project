from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from app.services.soul_drift_evaluator import SoulDriftEvaluator


@dataclass(frozen=True)
class ScorecardDimension:
    score: float
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(float(self.score), 4),
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class ExperiencePhaseEvaluationReport:
    scenario_id: str | None
    outcome_scorecard: dict[str, ScorecardDimension]
    experience_scorecard: dict[str, ScorecardDimension]
    intelligence_scorecard: dict[str, ScorecardDimension]
    overall_scores: dict[str, float]
    recommendation: str
    supporting_metrics: dict[str, Any]
    soul_drift: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "outcome_scorecard": {key: value.to_dict() for key, value in self.outcome_scorecard.items()},
            "experience_scorecard": {key: value.to_dict() for key, value in self.experience_scorecard.items()},
            "intelligence_scorecard": {key: value.to_dict() for key, value in self.intelligence_scorecard.items()},
            "overall_scores": dict(self.overall_scores),
            "recommendation": self.recommendation,
            "supporting_metrics": dict(self.supporting_metrics),
            "soul_drift": dict(self.soul_drift) if isinstance(self.soul_drift, dict) else None,
        }


class ExperiencePhaseEvaluator:
    """Evaluate the north-star experience phase with outcome, experience, and intelligence scorecards."""

    OUTCOME_DIMENSIONS = (
        "misconception_reduction",
        "task_execution",
        "consistency",
        "real_world_performance",
    )
    EXPERIENCE_DIMENSIONS = (
        "felt_understood",
        "timely_guidance",
        "real_change",
        "continuity_and_trust",
    )
    INTELLIGENCE_DIMENSIONS = (
        "correct_residual_diagnosis",
        "correct_loop_selection",
        "grounded_evidence_use",
        "good_reversibility",
        "freedom_preservation",
        "low_drift",
    )

    def __init__(self) -> None:
        self.soul_drift_evaluator = SoulDriftEvaluator()

    def evaluate(
        self,
        *,
        scenario_id: str | None = None,
        turns: list[dict[str, Any]] | None = None,
        outcomes: dict[str, Any] | None = None,
        experience: dict[str, Any] | None = None,
        intelligence: dict[str, Any] | None = None,
        current_runtime: dict[str, Any] | None = None,
        previous_runtime: dict[str, Any] | None = None,
        drift_outcomes: dict[str, Any] | None = None,
        drift_signals: dict[str, Any] | None = None,
    ) -> ExperiencePhaseEvaluationReport:
        turns = [dict(item) for item in (turns or []) if isinstance(item, dict)]
        outcomes = dict(outcomes or {})
        experience = dict(experience or {})
        intelligence = dict(intelligence or {})

        drift_report = self.soul_drift_evaluator.evaluate(
            scenario_id=scenario_id,
            current_runtime=current_runtime if isinstance(current_runtime, dict) else {},
            previous_runtime=previous_runtime if isinstance(previous_runtime, dict) else {},
            outcomes=drift_outcomes if isinstance(drift_outcomes, dict) else {},
            signals=drift_signals if isinstance(drift_signals, dict) else {},
        )
        low_drift_score = round(max(0.0, 1.0 - float(drift_report.drift_score)), 4)

        inferred_intelligence = self._infer_intelligence_metrics(turns, low_drift_score=low_drift_score)
        inferred_experience = self._infer_experience_metrics(turns)

        outcome_scorecard = self._build_scorecard(
            dimensions=self.OUTCOME_DIMENSIONS,
            values=outcomes,
            evidence_builder=self._outcome_evidence,
        )
        experience_scorecard = self._build_scorecard(
            dimensions=self.EXPERIENCE_DIMENSIONS,
            values={**inferred_experience, **experience},
            evidence_builder=self._experience_evidence,
        )
        intelligence_scorecard = self._build_scorecard(
            dimensions=self.INTELLIGENCE_DIMENSIONS,
            values={**inferred_intelligence, **intelligence, "low_drift": low_drift_score},
            evidence_builder=self._intelligence_evidence,
        )

        outcome_average = self._average_score(outcome_scorecard)
        experience_average = self._average_score(experience_scorecard)
        intelligence_average = self._average_score(intelligence_scorecard)

        overall_scores = {
            "outcome_average": outcome_average,
            "experience_average": experience_average,
            "intelligence_average": intelligence_average,
        }
        recommendation = self._recommendation(
            outcome_average=outcome_average,
            experience_average=experience_average,
            intelligence_average=intelligence_average,
            low_drift_score=low_drift_score,
        )

        supporting_metrics = {
            "turn_count": len(turns),
            "residual_accuracy_rate": inferred_intelligence["correct_residual_diagnosis"],
            "loop_accuracy_rate": inferred_intelligence["correct_loop_selection"],
            "grounding_rate": inferred_intelligence["grounded_evidence_use"],
            "reversibility_rate": inferred_intelligence["good_reversibility"],
            "real_change_rate": inferred_experience["real_change"],
            "continuity_rate": inferred_experience["continuity_and_trust"],
            "drift_score": round(float(drift_report.drift_score), 4),
            "drift_recommendation": drift_report.recommendation,
        }

        return ExperiencePhaseEvaluationReport(
            scenario_id=scenario_id,
            outcome_scorecard=outcome_scorecard,
            experience_scorecard=experience_scorecard,
            intelligence_scorecard=intelligence_scorecard,
            overall_scores=overall_scores,
            recommendation=recommendation,
            supporting_metrics=supporting_metrics,
            soul_drift=drift_report.to_dict(),
        )

    def evaluate_scenarios(self, scenarios: list[dict[str, Any]]) -> list[ExperiencePhaseEvaluationReport]:
        reports: list[ExperiencePhaseEvaluationReport] = []
        for item in scenarios:
            if not isinstance(item, dict):
                continue
            reports.append(
                self.evaluate(
                    scenario_id=str(item.get("scenario_id") or "").strip() or None,
                    turns=item.get("turns"),
                    outcomes=item.get("outcomes"),
                    experience=item.get("experience"),
                    intelligence=item.get("intelligence"),
                    current_runtime=item.get("current_runtime"),
                    previous_runtime=item.get("previous_runtime"),
                    drift_outcomes=item.get("drift_outcomes"),
                    drift_signals=item.get("drift_signals"),
                )
            )
        return reports

    @staticmethod
    def load_scenarios(path: str | Path) -> list[dict[str, Any]]:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [dict(item) for item in raw if isinstance(item, dict)]
        return []

    def _infer_intelligence_metrics(self, turns: list[dict[str, Any]], *, low_drift_score: float) -> dict[str, float]:
        if not turns:
            return {
                "correct_residual_diagnosis": 0.5,
                "correct_loop_selection": 0.5,
                "grounded_evidence_use": 0.5,
                "good_reversibility": 0.5,
                "freedom_preservation": 0.5,
                "low_drift": low_drift_score,
            }

        residual_hits: list[float] = []
        loop_hits: list[float] = []
        grounding_hits: list[float] = []
        reversibility_hits: list[float] = []
        freedom_hits: list[float] = []

        for turn in turns:
            decision_context = turn.get("decision_context") if isinstance(turn.get("decision_context"), dict) else {}
            expected_residual = str(turn.get("expected_residual") or "").strip()
            expected_loop = str(turn.get("expected_loop_type") or "").strip()
            if expected_residual:
                residual_hits.append(1.0 if str(decision_context.get("primary_residual") or "").strip() == expected_residual else 0.0)
            if expected_loop:
                loop_hits.append(1.0 if str(decision_context.get("loop_type") or "").strip() == expected_loop else 0.0)

            expected_grounding = str(turn.get("expected_grounding") or "").strip()
            actual_grounding = ""
            grounding_priority = decision_context.get("grounding_priority")
            if isinstance(grounding_priority, list) and grounding_priority:
                actual_grounding = str(grounding_priority[0] or "").strip()
            grounding_runtime = turn.get("user_material_grounding") if isinstance(turn.get("user_material_grounding"), dict) else {}
            if expected_grounding:
                grounded = str(grounding_runtime.get("status") or "").strip()
                grounding_hits.append(
                    1.0 if actual_grounding == expected_grounding and grounded == "grounded" else 0.0
                )

            auto_adjustments = [
                item for item in (turn.get("auto_strategy_adjustments") or []) if isinstance(item, dict)
            ]
            if auto_adjustments:
                reversibility_hits.append(
                    1.0 if all(str(item.get("layer") or "").strip() == "session" for item in auto_adjustments) else 0.0
                )
            else:
                reversibility_hits.append(0.8)

            freedom_hits.append(float(turn.get("freedom_preservation", 0.75)))

        return {
            "correct_residual_diagnosis": round(mean(residual_hits) if residual_hits else 0.5, 4),
            "correct_loop_selection": round(mean(loop_hits) if loop_hits else 0.5, 4),
            "grounded_evidence_use": round(mean(grounding_hits) if grounding_hits else 0.5, 4),
            "good_reversibility": round(mean(reversibility_hits) if reversibility_hits else 0.5, 4),
            "freedom_preservation": round(mean(freedom_hits) if freedom_hits else 0.5, 4),
            "low_drift": round(low_drift_score, 4),
        }

    @staticmethod
    def _infer_experience_metrics(turns: list[dict[str, Any]]) -> dict[str, float]:
        if not turns:
            return {
                "felt_understood": 0.5,
                "timely_guidance": 0.5,
                "real_change": 0.5,
                "continuity_and_trust": 0.5,
            }

        understood_hits: list[float] = []
        timely_hits: list[float] = []
        real_change_hits: list[float] = []
        continuity_hits: list[float] = []

        for turn in turns:
            user_signal = str(turn.get("user_signal") or "").strip().lower()
            if user_signal:
                understood_hits.append(1.0 if user_signal in {"clearer", "helped", "accepted", "started"} else 0.45)

            expected_mode = str(turn.get("expected_mode") or "").strip()
            decision_context = turn.get("decision_context") if isinstance(turn.get("decision_context"), dict) else {}
            if expected_mode:
                timely_hits.append(1.0 if str(decision_context.get("experience_mode") or "").strip() == expected_mode else 0.0)

            has_real_change = bool(turn.get("auto_strategy_adjustments")) or bool(turn.get("auto_feedback_binding")) or bool(
                (turn.get("user_material_grounding") or {}).get("results")
            )
            real_change_hits.append(1.0 if has_real_change else 0.35)

            continuity_signal = 0.4
            if turn.get("auto_feedback_binding"):
                continuity_signal = 1.0
            elif turn.get("active_interventions"):
                continuity_signal = 0.85
            elif turn.get("auto_strategy_adjustments"):
                continuity_signal = 0.75
            continuity_hits.append(continuity_signal)

        return {
            "felt_understood": round(mean(understood_hits) if understood_hits else 0.5, 4),
            "timely_guidance": round(mean(timely_hits) if timely_hits else 0.5, 4),
            "real_change": round(mean(real_change_hits) if real_change_hits else 0.5, 4),
            "continuity_and_trust": round(mean(continuity_hits) if continuity_hits else 0.5, 4),
        }

    @staticmethod
    def _build_scorecard(
        *,
        dimensions: tuple[str, ...],
        values: dict[str, Any],
        evidence_builder,
    ) -> dict[str, ScorecardDimension]:
        scorecard: dict[str, ScorecardDimension] = {}
        for dimension in dimensions:
            score = max(0.0, min(1.0, float(values.get(dimension, 0.5))))
            scorecard[dimension] = ScorecardDimension(
                score=round(score, 4),
                evidence=evidence_builder(dimension=dimension, score=score, values=values),
            )
        return scorecard

    @staticmethod
    def _average_score(scorecard: dict[str, ScorecardDimension]) -> float:
        if not scorecard:
            return 0.0
        return round(mean(item.score for item in scorecard.values()), 4)

    @staticmethod
    def _outcome_evidence(*, dimension: str, score: float, values: dict[str, Any]) -> list[str]:
        summary = {
            "misconception_reduction": "Concept confusion is dropping instead of repeating.",
            "task_execution": "The user is more able to start and complete the next move.",
            "consistency": "Progress is holding across turns instead of collapsing after one reply.",
            "real_world_performance": "The journey is improving real exam-facing performance, not just chat polish.",
        }.get(dimension, "Outcome improved.")
        return [summary, f"score={round(score, 4)}", f"source={values.get(dimension + '_source', 'scenario')}"]

    @staticmethod
    def _experience_evidence(*, dimension: str, score: float, values: dict[str, Any]) -> list[str]:
        summary = {
            "felt_understood": "The replies track the user's actual bottleneck rather than a generic tutoring script.",
            "timely_guidance": "The mode shift happens in the turn where the user signal appears.",
            "real_change": "Sparkle changes something real in runtime state or grounding behavior.",
            "continuity_and_trust": "Later turns preserve memory of interventions and accepted adjustments.",
        }.get(dimension, "Experience improved.")
        return [summary, f"score={round(score, 4)}"]

    @staticmethod
    def _intelligence_evidence(*, dimension: str, score: float, values: dict[str, Any]) -> list[str]:
        summary = {
            "correct_residual_diagnosis": "Residual selection matches the scenario's real bottleneck.",
            "correct_loop_selection": "Truth-seeking vs normative guidance is chosen correctly.",
            "grounded_evidence_use": "User materials are used when they should lead the evidence stack.",
            "good_reversibility": "Adjustments stay session-scoped and reversible unless stronger evidence exists.",
            "freedom_preservation": "The system supports judgment without overprescribing the user's life.",
            "low_drift": "The governed experience stays useful without stylized drift.",
        }.get(dimension, "Intelligence improved.")
        return [summary, f"score={round(score, 4)}"]

    @staticmethod
    def _recommendation(
        *,
        outcome_average: float,
        experience_average: float,
        intelligence_average: float,
        low_drift_score: float,
    ) -> str:
        if min(outcome_average, experience_average, intelligence_average) >= 0.72 and low_drift_score >= 0.7:
            return "accept"
        if min(outcome_average, experience_average, intelligence_average) >= 0.58 and low_drift_score >= 0.55:
            return "refine"
        return "block"
