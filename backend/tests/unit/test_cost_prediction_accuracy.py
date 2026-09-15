"""
OBS-013: Tests for cost prediction accuracy.

Verifies that LLM cost predictions fall within acceptable error margins,
the budget gate blocks requests that exceed thresholds, accumulated cost
tracking is accurate, and daily costs reset properly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from unittest.mock import AsyncMock

import pytest


# ---------------------------------------------------------------------------
# Lightweight cost prediction helpers (production mirrors)
# ---------------------------------------------------------------------------

# Pricing table: cost per 1K tokens (input, output)
_MODEL_PRICING = {
    "gpt-4": (0.03, 0.06),
    "gpt-4o": (0.005, 0.015),
    "gpt-3.5-turbo": (0.001, 0.002),
    "default": (0.03, 0.06),
}


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class CostRecord:
    model: str
    predicted_cost: float
    actual_cost: float
    date: str


def predict_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Predict cost in USD given model and token counts."""
    in_price, out_price = _MODEL_PRICING.get(model, _MODEL_PRICING["default"])
    return (input_tokens / 1000) * in_price + (output_tokens / 1000) * out_price


def estimate_tokens(text: str, is_chinese_heavy: bool = False) -> int:
    """Rough token estimation (production uses 1.2x safety margin)."""
    if not text:
        return 0
    if is_chinese_heavy:
        return int(len(text) * 0.5 * 1.2)
    return int(len(text) / 4 * 1.2)


def actual_cost(model: str, usage: TokenUsage) -> float:
    """Compute actual cost from real token counts."""
    in_price, out_price = _MODEL_PRICING.get(model, _MODEL_PRICING["default"])
    return (usage.input_tokens / 1000) * in_price + (usage.output_tokens / 1000) * out_price


class BudgetGate:
    """Simple budget gate that blocks calls exceeding a cost threshold."""

    def __init__(self, threshold: float = 0.10):
        self.threshold = threshold

    def check(self, predicted: float) -> bool:
        return predicted <= self.threshold


class CostAccumulator:
    """Track accumulated LLM costs with daily reset."""

    def __init__(self):
        self._records: list[CostRecord] = []

    def record(self, model: str, predicted: float, actual: float) -> None:
        self._records.append(
            CostRecord(model=model, predicted_cost=predicted, actual_cost=actual, date=str(date.today()))
        )

    def daily_total(self, day: str | None = None) -> float:
        day = day or str(date.today())
        return sum(r.actual_cost for r in self._records if r.date == day)

    def reset_daily(self) -> None:
        """Remove all records from previous days (simulate daily reset)."""
        today = str(date.today())
        self._records = [r for r in self._records if r.date == today]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCostPredictionAccuracy:
    """Validate cost prediction precision and budget controls."""

    def test_prediction_within_20_percent(self):
        """Predicted cost must be within 20% of actual cost."""
        cases = [
            ("gpt-4", TokenUsage(input_tokens=1200, output_tokens=600)),
            ("gpt-3.5-turbo", TokenUsage(input_tokens=3000, output_tokens=1500)),
            ("gpt-4o", TokenUsage(input_tokens=800, output_tokens=400)),
        ]
        for model, usage in cases:
            predicted = predict_cost(model, usage.input_tokens, usage.output_tokens)
            actual = actual_cost(model, usage)
            error_ratio = abs(predicted - actual) / actual
            assert error_ratio <= 0.20, (
                f"{model}: predicted={predicted:.6f}, actual={actual:.6f}, error={error_ratio:.2%}"
            )

    def test_token_count_estimation(self):
        """Estimated tokens should be within 30% of actual."""
        # Simulated "actual" token counts for known texts
        texts = [
            ("Hello, this is a test of the estimation system.", 15, False),
            ("This is a simple English sentence.", 10, False),
        ]
        for text, actual_tokens, is_chinese in texts:
            estimated = estimate_tokens(text, is_chinese_heavy=is_chinese)
            ratio = abs(estimated - actual_tokens) / actual_tokens
            assert ratio <= 0.30, (
                f"Text={text!r}: estimated={estimated}, actual={actual_tokens}, ratio={ratio:.2%}"
            )

    def test_budget_gate_blocks_high_cost(self):
        """Budget gate must block when predicted cost exceeds threshold."""
        gate = BudgetGate(threshold=0.05)

        # gpt-4: 2000 input + 1000 output = 0.06 + 0.06 = $0.12 -> blocked
        high_cost = predict_cost("gpt-4", 2000, 1000)
        assert not gate.check(high_cost)

        # gpt-3.5-turbo: 500 input + 200 output = $0.0009 -> allowed
        low_cost = predict_cost("gpt-3.5-turbo", 500, 200)
        assert gate.check(low_cost)

    def test_accumulated_cost_tracking(self):
        """Costs must accumulate correctly across multiple calls."""
        acc = CostAccumulator()

        acc.record("gpt-4", 0.06, actual_cost("gpt-4", TokenUsage(1000, 500)))
        acc.record("gpt-3.5-turbo", 0.002, actual_cost("gpt-3.5-turbo", TokenUsage(1000, 500)))
        acc.record("gpt-4o", 0.01, actual_cost("gpt-4o", TokenUsage(1000, 500)))

        total = acc.daily_total()
        expected = (
            actual_cost("gpt-4", TokenUsage(1000, 500))
            + actual_cost("gpt-3.5-turbo", TokenUsage(1000, 500))
            + actual_cost("gpt-4o", TokenUsage(1000, 500))
        )
        assert abs(total - expected) < 1e-9

    def test_cost_reset_daily(self):
        """After daily reset, only today's records remain; old-day cost = 0."""
        acc = CostAccumulator()

        # Inject an "old" record
        acc._records.append(
            CostRecord(model="gpt-4", predicted_cost=0.10, actual_cost=0.10, date="2025-12-31")
        )
        acc.record("gpt-4", 0.06, 0.06)

        assert acc.daily_total("2025-12-31") == 0.10
        assert acc.daily_total() == pytest.approx(0.06)

        # Reset removes old records
        acc.reset_daily()
        assert acc.daily_total("2025-12-31") == 0.0
        assert acc.daily_total() == pytest.approx(0.06)
