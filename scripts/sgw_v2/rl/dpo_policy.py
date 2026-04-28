"""DPO-informed strategy policy — Stage 4 of the RL policy progression.

Selects which AI behavior strategy (give_advice, ask_question, etc.) to use
given the current user state context. Requires a trained DPOModel.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..sim.ai_behavior_classifier import AIBehaviorClass
from .dpo_trainer import DPOModel
from .spec import StrategyRecommendation

_STRATEGY_ORDER = [e.value for e in AIBehaviorClass]
_DEFAULT_STRATEGY = AIBehaviorClass.GIVE_ADVICE.value


@dataclass
class StrategyPreference:
    """Output of DPO strategy selection."""

    recommended_strategy: str
    confidence: float
    strategy_scores: dict[str, float]
    model_available: bool = True

    def to_recommendation(self, context_vector: list[float]) -> StrategyRecommendation:
        return StrategyRecommendation(
            recommended_behavior=self.recommended_strategy,
            confidence=self.confidence,
            strategy_scores=self.strategy_scores,
            context_vector=list(context_vector),
            source="dpo",
        )


class DPOPolicy:
    """DPO-informed strategy selector.

    Maps context vectors to the best AI behavior class using a trained
    DPOModel. Falls back to a rule-based heuristic when no model is loaded.
    """

    def __init__(self, model: DPOModel | None = None):
        self._model = model
        self._model_loaded_from: str = ""

    # ── Properties ──────────────────────────────────────

    @property
    def is_available(self) -> bool:
        return self._model is not None

    @property
    def model(self) -> DPOModel | None:
        return self._model

    @property
    def source_path(self) -> str:
        return self._model_loaded_from

    # ── Model management ────────────────────────────────

    def update_model(self, model: DPOModel, source: str = "") -> None:
        """Replace the current DPO model."""
        self._model = model
        self._model_loaded_from = source

    def load_model(self, path: Path) -> bool:
        """Load a DPOModel from disk."""
        try:
            self._model = DPOModel.load(path)
            self._model_loaded_from = str(path)
            return True
        except (FileNotFoundError, OSError):
            return False

    # ── Strategy selection ──────────────────────────────

    def select_strategy(self, context_vector: list[float]) -> StrategyPreference:
        """Select the best AI behavior strategy for a context vector."""
        if not self._model:
            return self._fallback(context_vector)

        import numpy as np
        cv = np.array(context_vector, dtype=np.float64)

        if len(cv) != self._model.feature_dim:
            return self._fallback(context_vector)

        strategy_scores = self._model.strategy_scores(cv)
        scores_arr = np.array(list(strategy_scores.values()))
        best_idx = int(np.argmax(scores_arr))
        best_strategy = list(strategy_scores.keys())[best_idx]
        best_score = float(scores_arr[best_idx])

        # Confidence: softmax temperature-scaled
        scores_centered = scores_arr - np.max(scores_arr)
        exp_scores = np.exp(scores_centered * 2.0)  # temperature = 0.5
        probs = exp_scores / np.sum(exp_scores)
        confidence = float(probs[best_idx])

        return StrategyPreference(
            recommended_strategy=best_strategy,
            confidence=round(min(1.0, confidence), 4),
            strategy_scores={k: round(float(v), 4) for k, v in strategy_scores.items()},
            model_available=True,
        )

    # ── Fallback ────────────────────────────────────────

    def _fallback(self, context_vector: list[float]) -> StrategyPreference:
        """Rule-based fallback when no DPO model is available."""
        scores: dict[str, float] = {s: 0.5 for s in _STRATEGY_ORDER}

        if len(context_vector) >= 5:
            opening_phase = context_vector[1] if len(context_vector) > 1 else 0
            closing_phase = context_vector[2] if len(context_vector) > 2 else 0
            has_question = context_vector[7] if len(context_vector) > 7 else 0

            if has_question > 0.5:
                scores["ask_question"] = 0.8
                scores["give_advice"] = 0.6
            elif opening_phase > 0.5:
                scores["ask_question"] = 0.7
                scores["encourage"] = 0.6
            elif closing_phase > 0.5:
                scores["encourage"] = 0.7
                scores["give_advice"] = 0.65
            else:
                scores["give_advice"] = 0.75
                scores["confirm"] = 0.55

        best = max(scores, key=scores.get)
        sorted_scores = sorted(scores.values(), reverse=True)
        confidence = (sorted_scores[0] - sorted_scores[1]) if len(sorted_scores) > 1 else 0.3
        confidence = max(0.1, min(1.0, confidence + 0.2))

        return StrategyPreference(
            recommended_strategy=best,
            confidence=round(confidence, 4),
            strategy_scores=scores,
            model_available=False,
        )

    # ── Serialization ───────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.is_available,
            "model_source": self._model_loaded_from,
            "model_info": self._model.to_dict() if self._model else None,
        }
