"""
Core: execution
Phase: reflect→adapt
Stage: Signal-to-Action Spine — Decision Realization Score

10 核心指标 — 验证 AI 判断是否真正改变了系统行动，并改善了结果。
每个指标绑定 Final Spec Section 22 定义。
"""

from __future__ import annotations

from typing import Any

from loguru import logger


# ── 指标定义 ─────────────────────────────────────────────────────────
# 每个指标有 name, description, numerator_key, denominator_key。

METRIC_DEFINITIONS = {
    "signal_to_state_rate": {
        "description": "高价值信号有多少进入状态",
        "numerator": "signals_entered_state",
        "denominator": "signals_generated",
    },
    "state_to_policy_rate": {
        "description": "状态变化有多少触发策略裁决",
        "numerator": "policies_evaluated",
        "denominator": "states_active",
    },
    "policy_to_directive_rate": {
        "description": "策略有多少变成 directive",
        "numerator": "directives_generated",
        "denominator": "policies_evaluated",
    },
    "directive_application_rate": {
        "description": "directive 有多少被下游执行",
        "numerator": "directives_applied",
        "denominator": "directives_generated",
    },
    "output_change_rate": {
        "description": "输出是否真的改变",
        "numerator": "outputs_changed",
        "denominator": "directives_applied",
    },
    "user_visible_receipt_rate": {
        "description": "用户是否感知到改变",
        "numerator": "receipts_shown",
        "denominator": "directives_applied",
    },
    "outcome_feedback_rate": {
        "description": "改变后是否记录结果",
        "numerator": "outcomes_recorded",
        "denominator": "directives_applied",
    },
    "intervention_effectiveness": {
        "description": "干预是否可能有效",
        "numerator": "effective_attributions",
        "denominator": "outcomes_recorded",
    },
    "retraction_rate": {
        "description": "系统是否能撤销错误判断",
        "numerator": "retractions",
        "denominator": "receipts_shown",
    },
    "orphan_signal_count": {
        "description": "发出但无人消费的信号数量",
        "numerator": "orphan_signals",
        "denominator": None,  # gauge, not ratio
    },
}


class SpineMetricsCollector:
    """
    收集 Signal-to-Action Spine 的 10 核心指标。

    使用方式：
    1. 每次 pipeline 运行时调用 increment_* 方法
    2. 定期调用 snapshot() 获取指标快照
    3. 快照可暴露给 Prometheus / Grafana
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self._prefix = "spine:metrics"

    async def increment(self, counter: str, amount: int = 1) -> None:
        """递增计数器。"""
        key = f"{self._prefix}:{counter}"
        await self.redis.incrby(key, amount)

    async def get_counter(self, counter: str) -> int:
        """获取计数器值。"""
        key = f"{self._prefix}:{counter}"
        raw = await self.redis.get(key)
        return int(raw) if raw else 0

    async def snapshot(self) -> dict[str, Any]:
        """
        获取所有指标的当前快照。

        Returns:
            dict with metric_name → {value, numerator, denominator, description}
        """
        result: dict[str, Any] = {}

        # Fetch all counter values
        counter_names = {
            "signals_generated", "signals_entered_state",
            "states_active", "policies_evaluated",
            "directives_generated", "directives_applied",
            "outputs_changed", "receipts_shown",
            "outcomes_recorded", "effective_attributions",
            "retractions", "orphan_signals",
        }
        counters = {}
        for name in counter_names:
            counters[name] = await self.get_counter(name)

        # Calculate rates
        for metric_name, definition in METRIC_DEFINITIONS.items():
            num_key = definition["numerator"]
            den_key = definition["denominator"]
            numerator = counters.get(num_key, 0)

            if den_key is None:
                # Gauge metric (no rate)
                result[metric_name] = {
                    "value": numerator,
                    "description": definition["description"],
                }
            else:
                denominator = counters.get(den_key, 0)
                rate = numerator / denominator if denominator > 0 else 0.0
                result[metric_name] = {
                    "value": round(rate, 4),
                    "numerator": numerator,
                    "denominator": denominator,
                    "description": definition["description"],
                }

        return result

    async def reset(self) -> None:
        """重置所有计数器（测试用）。"""
        counter_names = {
            "signals_generated", "signals_entered_state",
            "states_active", "policies_evaluated",
            "directives_generated", "directives_applied",
            "outputs_changed", "receipts_shown",
            "outcomes_recorded", "effective_attributions",
            "retractions", "orphan_signals",
        }
        for name in counter_names:
            key = f"{self._prefix}:{name}"
            await self.redis.delete(key)

    # ── Convenience methods for pipeline integration ──────────────

    async def record_signal_generated(self) -> None:
        await self.increment("signals_generated")

    async def record_signal_entered_state(self) -> None:
        await self.increment("signals_entered_state")

    async def record_policy_evaluated(self, matched: bool) -> None:
        await self.increment("policies_evaluated")
        if not matched:
            await self.increment("orphan_signals")

    async def record_directive_generated(self) -> None:
        await self.increment("directives_generated")

    async def record_directive_applied(self, changed_output: bool) -> None:
        await self.increment("directives_applied")
        if changed_output:
            await self.increment("outputs_changed")

    async def record_receipt_shown(self) -> None:
        await self.increment("receipts_shown")

    async def record_outcome_recorded(self, effective: bool) -> None:
        await self.increment("outcomes_recorded")
        if effective:
            await self.increment("effective_attributions")

    async def record_retraction(self) -> None:
        await self.increment("retractions")
