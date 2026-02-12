from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger

from app.config import settings
from app.core.cache import cache_service


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ExpertPolicyReportService:
    """Aggregate expert strategy quality signals from observability events."""

    def __init__(self, redis_client=None):
        self.redis = redis_client or cache_service.redis

    async def build_report(self, days: int = 7) -> dict[str, Any]:
        now = _utcnow()
        since = now - timedelta(days=max(1, days))
        events = await self._load_events_since(since)
        return self._aggregate(events=events, days=days, generated_at=now)

    async def _load_events_since(self, since: datetime) -> list[dict[str, Any]]:
        if not self.redis:
            return []

        events: list[dict[str, Any]] = []
        try:
            async for key in self.redis.scan_iter("observability:event:*"):
                raw = await self.redis.get(key)
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                timestamp = payload.get("timestamp")
                if not isinstance(timestamp, str):
                    continue
                try:
                    occurred_at = datetime.fromisoformat(timestamp)
                except ValueError:
                    continue
                if occurred_at < since:
                    continue
                events.append(payload)
        except Exception as exc:
            logger.warning("Failed to load expert policy events: %s", exc)
        return events

    @staticmethod
    def _aggregate(*, events: list[dict[str, Any]], days: int, generated_at: datetime) -> dict[str, Any]:
        selected_total = 0
        invoked_total = 0
        fallback_total = 0
        overridden_total = 0
        feedback_bound_total = 0
        prompt_selected_total = 0
        prompt_applied_total = 0
        toolchain_selected_total = 0
        toolchain_degraded_total = 0

        selected_by_expert: Counter[str] = Counter()
        invoked_by_expert: Counter[str] = Counter()
        fallback_by_reason: Counter[str] = Counter()
        policy_feedback_bindings: Counter[str] = Counter()
        workflow_feedback_bindings: Counter[str] = Counter()
        selected_by_policy: Counter[str] = Counter()
        selected_by_cohort: Counter[str] = Counter()
        selected_by_complexity: Counter[str] = Counter()
        selected_by_task_type: Counter[str] = Counter()
        fallback_by_policy: Counter[str] = Counter()
        fallback_by_cohort: Counter[str] = Counter()
        fallback_by_complexity: Counter[str] = Counter()
        fallback_by_task_type: Counter[str] = Counter()
        feedback_by_task_type: Counter[str] = Counter()
        feedback_by_cohort: Counter[str] = Counter()

        for event in events:
            event_type = str(event.get("event_type", ""))
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            policy_id = str(data.get("policy_id", "unknown"))
            complexity_tier = str(data.get("complexity_tier", "unknown"))
            task_type = str(data.get("task_type", "unknown"))
            cohort_id = str(data.get("cohort_id", "cohort::unknown") or "cohort::unknown")

            if event_type == "expert_selected":
                selected_total += 1
                expert_id = str(data.get("expert_id", "unknown"))
                selected_by_expert[expert_id] += 1
                selected_by_policy[policy_id] += 1
                selected_by_cohort[cohort_id] += 1
                selected_by_complexity[complexity_tier] += 1
                selected_by_task_type[task_type] += 1
            elif event_type == "expert_invoked":
                invoked_total += 1
                expert_id = str(data.get("expert_id", "unknown"))
                invoked_by_expert[expert_id] += 1
            elif event_type == "expert_fallback":
                fallback_total += 1
                reason = str(data.get("reason", "unknown"))
                fallback_by_reason[reason] += 1
                fallback_by_policy[policy_id] += 1
                fallback_by_cohort[cohort_id] += 1
                fallback_by_complexity[complexity_tier] += 1
                fallback_by_task_type[task_type] += 1
            elif event_type == "expert_overridden":
                overridden_total += 1
            elif event_type == "prompt_selected":
                prompt_selected_total += 1
            elif event_type == "prompt_applied":
                prompt_applied_total += 1
            elif event_type == "toolchain_selected":
                toolchain_selected_total += 1
            elif event_type == "toolchain_degraded":
                toolchain_degraded_total += 1
            elif event_type == "user_feedback_bound":
                feedback_bound_total += 1
                workflow_id = str(data.get("workflow_id", "unknown"))
                workflow_feedback_bindings[workflow_id] += 1
                policy_id = str(data.get("policy_id", "unknown"))
                policy_feedback_bindings[policy_id] += 1
                feedback_by_task_type[task_type] += 1
                feedback_by_cohort[cohort_id] += 1

        coverage_rate = (invoked_total / selected_total) if selected_total else 0.0
        fallback_rate = (fallback_total / selected_total) if selected_total else 0.0
        feedback_binding_rate = (feedback_bound_total / invoked_total) if invoked_total else 0.0
        prompt_apply_rate = (prompt_applied_total / prompt_selected_total) if prompt_selected_total else 0.0
        toolchain_degrade_rate = (toolchain_degraded_total / toolchain_selected_total) if toolchain_selected_total else 0.0
        fallback_rate_by_policy = _rate_by_selected(selected_by_policy, fallback_by_policy)
        fallback_rate_by_cohort = _rate_by_selected(selected_by_cohort, fallback_by_cohort)
        fallback_rate_by_complexity = _rate_by_selected(selected_by_complexity, fallback_by_complexity)
        fallback_rate_by_task_type = _rate_by_selected(selected_by_task_type, fallback_by_task_type)
        feedback_binding_rate_by_policy = _rate_by_selected(selected_by_policy, policy_feedback_bindings)
        feedback_binding_rate_by_cohort = _rate_by_selected(selected_by_cohort, feedback_by_cohort)
        q_score_by_policy, delta_vs_baseline = _build_q_scores_by_policy(
            selected_by_policy=selected_by_policy,
            fallback_rate_by_policy=fallback_rate_by_policy,
            feedback_binding_rate_by_policy=feedback_binding_rate_by_policy,
        )
        q_score_by_cohort, cohort_delta_vs_baseline = _build_q_scores_by_policy(
            selected_by_policy=selected_by_cohort,
            fallback_rate_by_policy=fallback_rate_by_cohort,
            feedback_binding_rate_by_policy=feedback_binding_rate_by_cohort,
        )
        stable_cohort_q_gap = _stable_q_gap(
            q_score_by_scope=q_score_by_cohort,
            selected_by_scope=selected_by_cohort,
        )
        policy_health = _build_policy_health(
            selected_by_policy=selected_by_policy,
            fallback_rate_by_policy=fallback_rate_by_policy,
        )
        recommendations = _build_recommendations(
            selected_total=selected_total,
            coverage_rate=coverage_rate,
            fallback_rate=fallback_rate,
            feedback_binding_rate=feedback_binding_rate,
            fallback_rate_by_policy=fallback_rate_by_policy,
            selected_by_policy=selected_by_policy,
            fallback_by_reason=fallback_by_reason,
        )

        return {
            "window_days": max(1, days),
            "generated_at": generated_at.isoformat(),
            "totals": {
                "expert_selected": selected_total,
                "expert_invoked": invoked_total,
                "expert_fallback": fallback_total,
                "expert_overridden": overridden_total,
                "user_feedback_bound": feedback_bound_total,
                "prompt_selected": prompt_selected_total,
                "prompt_applied": prompt_applied_total,
                "toolchain_selected": toolchain_selected_total,
                "toolchain_degraded": toolchain_degraded_total,
            },
            "rates": {
                "coverage_rate": round(coverage_rate, 4),
                "fallback_rate": round(fallback_rate, 4),
                "feedback_binding_rate": round(feedback_binding_rate, 4),
                "prompt_apply_rate": round(prompt_apply_rate, 4),
                "toolchain_degrade_rate": round(toolchain_degrade_rate, 4),
            },
            "policy_health": policy_health,
            "recommendations": recommendations,
            "q_score_by_policy": q_score_by_policy,
            "delta_vs_baseline": delta_vs_baseline,
            "q_score_by_cohort": q_score_by_cohort,
            "cohort_delta_vs_baseline": cohort_delta_vs_baseline,
            "stable_cohort_q_gap": stable_cohort_q_gap,
            "by_expert": {
                "selected": dict(selected_by_expert.most_common()),
                "invoked": dict(invoked_by_expert.most_common()),
            },
            "fallback_reasons": dict(fallback_by_reason.most_common()),
            "feedback_bindings": {
                "by_policy": dict(policy_feedback_bindings.most_common()),
                "by_workflow": dict(workflow_feedback_bindings.most_common()),
            },
            "breakdown": {
                "selected_by_policy": dict(selected_by_policy.most_common()),
                "selected_by_cohort": dict(selected_by_cohort.most_common()),
                "selected_by_complexity": dict(selected_by_complexity.most_common()),
                "selected_by_task_type": dict(selected_by_task_type.most_common()),
                "fallback_by_policy": dict(fallback_by_policy.most_common()),
                "fallback_by_cohort": dict(fallback_by_cohort.most_common()),
                "fallback_by_complexity": dict(fallback_by_complexity.most_common()),
                "fallback_by_task_type": dict(fallback_by_task_type.most_common()),
                "feedback_by_task_type": dict(feedback_by_task_type.most_common()),
                "fallback_rate_by_policy": fallback_rate_by_policy,
                "fallback_rate_by_cohort": fallback_rate_by_cohort,
                "feedback_binding_rate_by_policy": feedback_binding_rate_by_policy,
                "feedback_binding_rate_by_cohort": feedback_binding_rate_by_cohort,
                "fallback_rate_by_complexity": fallback_rate_by_complexity,
                "fallback_rate_by_task_type": fallback_rate_by_task_type,
            },
        }


def _rate_by_selected(selected: Counter[str], fallback: Counter[str]) -> dict[str, float]:
    rates: dict[str, float] = {}
    for key, selected_count in selected.items():
        if selected_count <= 0:
            rates[key] = 0.0
            continue
        rates[key] = round(fallback.get(key, 0) / selected_count, 4)
    return rates


def _build_policy_health(
    *,
    selected_by_policy: Counter[str],
    fallback_rate_by_policy: dict[str, float],
) -> dict[str, Any]:
    health: dict[str, Any] = {}
    for policy_id, selected_count in selected_by_policy.items():
        rate = float(fallback_rate_by_policy.get(policy_id, 0.0))
        if selected_count < 5:
            status = "insufficient_data"
        elif rate <= 0.06:
            status = "healthy"
        elif rate <= 0.12:
            status = "watch"
        else:
            status = "needs_tuning"
        health[policy_id] = {
            "selected": int(selected_count),
            "fallback_rate": round(rate, 4),
            "status": status,
        }
    return health


def _build_recommendations(
    *,
    selected_total: int,
    coverage_rate: float,
    fallback_rate: float,
    feedback_binding_rate: float,
    fallback_rate_by_policy: dict[str, float],
    selected_by_policy: Counter[str],
    fallback_by_reason: Counter[str],
) -> list[dict[str, str]]:
    recs: list[dict[str, str]] = []
    if selected_total == 0:
        return recs

    if coverage_rate < 0.9:
        recs.append(
            {
                "priority": "P0",
                "title": "Improve Expert Invocation Coverage",
                "action": "Check routing-to-execution drop and enforce invocation retries for selected experts.",
            }
        )
    if fallback_rate > 0.08:
        recs.append(
            {
                "priority": "P0",
                "title": "Reduce Global Fallback Rate",
                "action": "Lower multi-expert aggressiveness for low-signal queries and tighten minimum selected score.",
            }
        )
    if feedback_binding_rate < 0.97:
        recs.append(
            {
                "priority": "P1",
                "title": "Raise Feedback Binding Reliability",
                "action": "Audit response feedback metadata propagation and enforce selected_experts + policy_id on every assistant response.",
            }
        )

    worst_policy = ""
    worst_rate = -1.0
    for policy_id, rate in fallback_rate_by_policy.items():
        if selected_by_policy.get(policy_id, 0) < 10:
            continue
        if rate > worst_rate:
            worst_rate = float(rate)
            worst_policy = policy_id
    if worst_policy and worst_rate > 0.1:
        recs.append(
            {
                "priority": "P1",
                "title": "Tune Underperforming Strategy Pack",
                "action": f"Policy {worst_policy} fallback is {worst_rate:.2f}; lower expert count threshold and revisit preferred experts.",
            }
        )

    if fallback_by_reason:
        top_reason, _ = fallback_by_reason.most_common(1)[0]
        recs.append(
            {
                "priority": "P2",
                "title": "Address Top Fallback Reason",
                "action": f"Top fallback reason is '{top_reason}'; add targeted guardrail and route-preview diagnostics.",
            }
        )
    return recs


def _build_q_scores_by_policy(
    *,
    selected_by_policy: Counter[str],
    fallback_rate_by_policy: dict[str, float],
    feedback_binding_rate_by_policy: dict[str, float],
) -> tuple[dict[str, float], dict[str, float]]:
    q_score_by_policy: dict[str, float] = {}
    total_weight = 0
    weighted_sum = 0.0

    for policy_id, selected in selected_by_policy.items():
        fallback_rate = float(fallback_rate_by_policy.get(policy_id, 0.0))
        binding_rate = float(feedback_binding_rate_by_policy.get(policy_id, 0.0))
        q_score = 0.7 * (1.0 - fallback_rate) + 0.3 * binding_rate
        q_score = max(0.0, min(round(q_score, 4), 1.0))
        q_score_by_policy[policy_id] = q_score
        weight = max(1, int(selected))
        total_weight += weight
        weighted_sum += q_score * weight

    baseline = (weighted_sum / total_weight) if total_weight else 0.0
    delta_vs_baseline = {
        policy_id: round(score - baseline, 4)
        for policy_id, score in q_score_by_policy.items()
    }
    return q_score_by_policy, delta_vs_baseline


def _stable_q_gap(
    *,
    q_score_by_scope: dict[str, float],
    selected_by_scope: Counter[str],
) -> float:
    min_support = int(getattr(settings, "LONG_TAIL_COHORT_MIN_SUPPORT", 20))
    values: list[float] = []
    for scope, score in q_score_by_scope.items():
        if int(selected_by_scope.get(scope, 0)) < min_support:
            continue
        values.append(float(score))
    if not values:
        return 0.0
    return round(max(values) - min(values), 4)
