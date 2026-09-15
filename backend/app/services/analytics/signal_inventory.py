from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.services.evidence import (
    ConversationalEvidenceExtractor,
    RoutingRewardModel,
    build_task_feedback_evidence,
    build_task_outcome_evidence,
)


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


class ProductionSignalInventory:
    """Inventory current production-visible evidence/reward signals."""

    CONVERSATION_SAMPLES: tuple[tuple[str, str], ...] = (
        ("overload", "这几步太多了，我脑子乱了"),
        ("aversion", "我不想开始，真的下不了手"),
        ("emotion", "我今天很累，有点焦虑快崩了"),
        ("completion_mention", "我刚做完了"),
        ("verbosity_friction", "太啰嗦了，短一点"),
        ("directness_preference", "别安慰，直接告诉我怎么做"),
        ("dissatisfaction", "不对，我还是没懂"),
    )

    @classmethod
    def configured_inventory(cls) -> dict[str, Any]:
        extractor = ConversationalEvidenceExtractor(llm_enabled=False)
        user_id = UUID("00000000-0000-0000-0000-000000000001")
        timestamp = datetime(2026, 1, 1, tzinfo=UTC).replace(tzinfo=None)
        evidence_routes: list[dict[str, Any]] = []

        for sample_name, message in cls.CONVERSATION_SAMPLES:
            items = extractor.extract_rule_based(
                user_message=message,
                timestamp=timestamp,
                scope={"user_id": str(user_id), "conversation_id": "inventory", "turn_index": 1},
                metadata={"sample_name": sample_name},
            )
            evidence_routes.extend(cls._evidence_route("conversation.rule_fallback", sample_name, item) for item in items)

        completed_event = {
            "event_type": "task.completed",
            "task_id": "inventory_task",
            "plan_id": "inventory_plan",
            "completion_rate": 1.0,
            "estimated_minutes": 30,
            "actual_minutes": 42,
            "difficulty": 4,
            "timestamp": timestamp.isoformat(),
        }
        abandoned_event = {
            "event_type": "task.abandoned",
            "task_id": "inventory_task",
            "plan_id": "inventory_plan",
            "reason": "too_difficult anxious",
            "timestamp": timestamp.isoformat(),
        }
        feedback_negative = {
            "event_type": "task.feedback_submitted",
            "task_id": "inventory_task",
            "category": "too_difficult",
            "feedback_text": "太难了，我卡住了",
            "timestamp": timestamp.isoformat(),
        }
        feedback_positive = {
            "event_type": "task.feedback_submitted",
            "task_id": "inventory_task",
            "category": "too_easy",
            "feedback_text": "很轻松",
            "timestamp": timestamp.isoformat(),
        }
        for name, items in (
            ("task.completed", build_task_outcome_evidence(completed_event, completed=True)),
            ("task.abandoned", build_task_outcome_evidence(abandoned_event, completed=False)),
            ("task.feedback_negative", build_task_feedback_evidence(feedback_negative)),
            ("task.feedback_positive", build_task_feedback_evidence(feedback_positive)),
        ):
            evidence_routes.extend(cls._evidence_route("outcome_adapter", name, item) for item in items)

        reward_routes = [
            cls._reward_route("task.completed", RoutingRewardModel.from_task_outcome(completed_event, completed=True)),
            cls._reward_route("task.abandoned", RoutingRewardModel.from_task_outcome(abandoned_event, completed=False)),
            cls._reward_route("task.feedback_negative", RoutingRewardModel.from_task_feedback(feedback_negative)),
            cls._reward_route("task.feedback_positive", RoutingRewardModel.from_task_feedback(feedback_positive)),
            cls._reward_route(
                "chat.explicit_complaint",
                RoutingRewardModel.from_chat_turn(gratitude=False, dissatisfaction=True),
            ),
            cls._reward_route(
                "chat.explicit_gratitude",
                RoutingRewardModel.from_chat_turn(gratitude=True, dissatisfaction=False),
            ),
        ]
        reward_routes = [item for item in reward_routes if item is not None]

        return {
            "schema_version": "production_signal_inventory.v1",
            "evidence_routes": evidence_routes,
            "evidence_route_count": len(evidence_routes),
            "evidence_source_counts": dict(Counter(item["source_type"] for item in evidence_routes)),
            "evidence_target_counts": dict(Counter(item["target"] for item in evidence_routes)),
            "reward_routes": reward_routes,
            "reward_signal_counts": dict(Counter(item["signal_type"] for item in reward_routes)),
            "reward_category_counts": dict(Counter(item["reward_category"] for item in reward_routes)),
            "currently_missing_or_weak": [
                "sustainability_cost is only approximated from task duration ratio; no micro-probe source exists yet.",
                "long_horizon_reward is schema-only until retention/return events are wired into traces.",
                "chat gratitude/complaint is weak because it depends on rule fallback markers, not calibrated human labels.",
                "counterfactual outcomes are unavailable without randomized/canary routing or stronger experimental design.",
            ],
        }

    @classmethod
    def observed_from_traces(cls, raw_traces: list[Any]) -> dict[str, Any]:
        reward_counts: Counter[str] = Counter()
        reward_category_counts: Counter[str] = Counter()
        source_counts: Counter[str] = Counter()
        target_counts: Counter[str] = Counter()
        outcome_counts: Counter[str] = Counter()
        total = 0
        parse_errors = 0
        for raw in raw_traces:
            trace = _loads(raw)
            if trace is None:
                parse_errors += 1
                continue
            total += 1
            outcome_counts[str(trace.get("outcome") or "unknown")] += 1
            reward = trace.get("reward")
            if isinstance(reward, dict):
                reward_counts[str(reward.get("signal_type") or "unknown")] += 1
                reward_category_counts[str(reward.get("reward_category") or "unknown")] += 1
            source_breakdown = trace.get("belief_source_breakdown")
            if isinstance(source_breakdown, dict):
                total_sources = source_breakdown.get("total")
                if isinstance(total_sources, dict):
                    for source, count in total_sources.items():
                        try:
                            source_counts[str(source)] += int(count)
                        except (TypeError, ValueError):
                            pass
                by_target = source_breakdown.get("by_target")
                if isinstance(by_target, dict):
                    for target, counts in by_target.items():
                        if isinstance(counts, dict):
                            try:
                                target_counts[str(target)] += sum(int(value) for value in counts.values())
                            except (TypeError, ValueError):
                                pass
        return {
            "schema_version": "observed_signal_inventory.v1",
            "total_traces": total,
            "parse_errors": parse_errors,
            "observed_outcome_counts": dict(outcome_counts),
            "observed_reward_signal_counts": dict(reward_counts),
            "observed_reward_category_counts": dict(reward_category_counts),
            "observed_evidence_source_counts": dict(source_counts),
            "observed_target_evidence_counts": dict(target_counts),
        }

    @staticmethod
    def _evidence_route(source: str, trigger: str, evidence: Any) -> dict[str, Any]:
        return {
            "source": source,
            "trigger": trigger,
            "source_type": evidence.source_type.value,
            "target": evidence.target_latent_variable.value,
            "direction": evidence.direction.value,
            "strength": round(float(evidence.strength), 4),
            "confidence": round(float(evidence.confidence), 4),
            "ttl_seconds": int(evidence.ttl_seconds),
            "rule": evidence.metadata.get("rule"),
        }

    @staticmethod
    def _reward_route(trigger: str, reward: Any) -> dict[str, Any] | None:
        if reward is None:
            return None
        payload = reward.to_trace_payload()
        return {
            "trigger": trigger,
            "signal_type": payload["signal_type"],
            "reward_category": payload["reward_category"],
            "outcome_label": payload["outcome_label"],
            "horizon": payload["horizon"],
            "evidence_strength": payload["evidence_strength"],
            "confidence": payload["confidence"],
            "components_present": [
                key
                for key in (
                    "immediate_interaction_reward",
                    "task_progress_reward",
                    "sustainability_cost",
                    "long_horizon_reward",
                    "information_gain_reward",
                )
                if float(payload.get(key) or 0.0) != 0.0
            ],
        }
