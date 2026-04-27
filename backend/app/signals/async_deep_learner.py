"""
Core: execution
Phase: adapt
Stage: Signal-to-Action Spine P3-3 L4 Async Deep Learning

Per ruling Section 11, L4 never modifies live state directly.
L4 only produces candidates for downstream consumption.

6 L4 Jobs (ruling-mandated):
  1. DailyGoalReflectionJob — yesterday's bottleneck → today's focus
  2. PolicyEffectCompactionJob — PolicyEffectLedger → StrategyBelief
  3. SkillCandidateJob — repeated effective strategies → SkillCandidate
  4. SourceEffectivenessJob — which materials work in which context
  5. CommunityAggregationJob — anonymous common errors + resource quality
  6. StateDecayAndRetractionJob — decay stale state confidence + find counter-evidence

All outputs require: evidence, confidence, scope, user_visible flag.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger


_QUEUE_KEY = "spine:deep_learning_queue"
_SIGNAL_ACCUMULATION_KEY = "spine:deep_learning_accumulation:{user_id}"
_RESULT_KEY = "spine:deep_learning_result:{user_id}"
_L4_CANDIDATE_KEY = "spine:l4_candidate:{user_id}:{job_type}"
_MIN_SIGNALS_FOR_TRIGGER = 10
_ACCUMULATION_TTL = 48 * 3600  # 48 hours
_CANDIDATE_TTL = 7 * 24 * 3600  # 7 days


# ── L4 Candidate Output Types ────────────────────────────────────────

L4_JOB_TYPES = frozenset({
    "daily_goal_reflection",
    "policy_effect_compaction",
    "skill_candidate",
    "source_effectiveness",
    "community_aggregation",
    "state_decay_and_retraction",
})


class AsyncDeepLearner:
    """Queue and process L4 async deep learning analysis."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def accumulate_signal(
        self,
        user_id: str,
        signal_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Accumulate a signal for potential deep learning analysis.

        Returns {"triggered": bool, "accumulated_count": int}
        """
        key = _SIGNAL_ACCUMULATION_KEY.format(user_id=user_id)
        raw = await self.redis.get(key)
        signals: list[dict] = json.loads(raw) if raw else []

        signals.append(signal_data)
        # Keep only last 50 signals
        signals = signals[-50:]

        await self.redis.set(key, json.dumps(signals), ex=_ACCUMULATION_TTL)

        count = len(signals)
        triggered = False

        if count >= _MIN_SIGNALS_FOR_TRIGGER:
            triggered = await self._check_and_trigger(user_id, signals)

        return {"triggered": triggered, "accumulated_count": count}

    async def _check_and_trigger(
        self,
        user_id: str,
        signals: list[dict],
    ) -> bool:
        """Check if conditions warrant a deep learning analysis trigger."""
        # Don't trigger if there's a pending analysis
        existing = await self.redis.get(_RESULT_KEY.format(user_id=user_id))
        if existing:
            return False

        # Analyze signal patterns
        state_keys = [s.get("state_key", "") for s in signals]
        unique_keys = set(state_keys)

        # Trigger if we have diverse signals (>= 5 unique state keys)
        # or if any single key appears >= 5 times (persistent issue)
        should_trigger = len(unique_keys) >= 5
        if not should_trigger:
            from collections import Counter
            counts = Counter(state_keys)
            if counts and counts.most_common(1)[0][1] >= 5:
                should_trigger = True

        if should_trigger:
            task = {
                "user_id": user_id,
                "signal_count": len(signals),
                "unique_state_keys": list(unique_keys),
                "triggered_at": _utcnow(),
            }
            try:
                await self.redis.rpush(_QUEUE_KEY, json.dumps(task))
            except AttributeError:
                # Fallback for FakeRedis — store as single task
                await self.redis.set(_QUEUE_KEY + ":latest", json.dumps(task))
            logger.info(
                "DeepLearning: triggered for user={} signals={} keys={}",
                user_id, len(signals), len(unique_keys),
            )
            return True

        return False

    async def pop_task(self) -> dict[str, Any] | None:
        """Pop a task from the deep learning queue for processing."""
        try:
            raw = await self.redis.lpop(_QUEUE_KEY)
        except AttributeError:
            # Fallback for FakeRedis
            raw = await self.redis.get(_QUEUE_KEY + ":latest")
            if raw:
                await self.redis.delete(_QUEUE_KEY + ":latest")
        if not raw:
            return None
        return json.loads(raw)

    async def store_result(
        self,
        user_id: str,
        result: dict[str, Any],
    ) -> None:
        """Store a deep learning analysis result."""
        await self.redis.set(
            _RESULT_KEY.format(user_id=user_id),
            json.dumps(result),
            ex=7 * 24 * 3600,  # 7-day retention
        )

    async def get_result(self, user_id: str) -> dict[str, Any] | None:
        """Retrieve the latest deep learning result for a user."""
        raw = await self.redis.get(_RESULT_KEY.format(user_id=user_id))
        if not raw:
            return None
        return json.loads(raw)

    def analyze_signal_patterns(self, signals: list[dict]) -> dict[str, Any]:
        """Pure computation: analyze accumulated signals for patterns.

        This is the core L4 analysis logic — runs synchronously after pop.
        """
        if not signals:
            return {"patterns": [], "recommendations": []}

        state_keys = [s.get("state_key", "") for s in signals]
        from collections import Counter
        key_counts = Counter(state_keys)

        patterns: list[dict[str, Any]] = []
        recommendations: list[dict[str, Any]] = []

        # Pattern 1: Persistent issue
        for key, count in key_counts.most_common(5):
            if count >= 5:
                patterns.append({
                    "type": "persistent_issue",
                    "state_key": key,
                    "occurrences": count,
                })
                recommendations.append({
                    "action": "strategy_reassess",
                    "target": key,
                    "reason": f"appeared {count} times without resolution",
                })

        # Pattern 2: Related issues cluster
        related_groups = {
            "execution": {"task_granularity_fit", "execution_consistency", "deadline_pressure"},
            "knowledge": {"knowledge_bottleneck", "knowledge_transfer", "retrieval_risk"},
            "affective": {"affective_pressure", "cognitive_load", "growth_momentum"},
        }
        for group_name, group_keys in related_groups.items():
            group_count = sum(key_counts.get(k, 0) for k in group_keys)
            if group_count >= 3:
                patterns.append({
                    "type": "cluster",
                    "group": group_name,
                    "related_keys": [k for k in group_keys if key_counts.get(k, 0) > 0],
                })

        return {
            "patterns": patterns,
            "recommendations": recommendations,
            "total_signals": len(signals),
            "unique_keys": len(set(state_keys)),
        }

    # ── L4 Job Runners (ruling Section 11) ────────────────────────────
    # Each job produces a candidate with: evidence, confidence, scope, user_visible

    async def run_daily_goal_reflection(
        self,
        user_id: str,
        accumulated_signals: list[dict[str, Any]],
        recent_outcomes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Job 1: DailyGoalReflection — yesterday's bottleneck → today's focus.

        Output: bottleneck, highest_value_node, strategy_correction_needed,
                suggest_aurora_calibration
        """
        from collections import Counter

        recent_outcomes = recent_outcomes or []

        # Find most frequent bottleneck from signals
        state_keys = [s.get("state_key", "") for s in accumulated_signals]
        key_counts = Counter(state_keys)
        bottleneck = key_counts.most_common(1)[0] if key_counts else ("none", 0)

        # Count failures vs successes from outcomes
        failures = [o for o in recent_outcomes if o.get("attribution") == "insufficient"]
        successes = [o for o in recent_outcomes if o.get("attribution") == "sufficient"]

        strategy_correction = len(failures) > len(successes) and len(failures) >= 2
        suggest_aurora = len(failures) >= 3 or bottleneck[1] >= 8

        # Determine highest-value node from recent signal patterns
        knowledge_signals = [s for s in accumulated_signals if "knowledge" in s.get("state_key", "")]
        highest_value_node = knowledge_signals[0].get("state_key", "") if knowledge_signals else bottleneck[0]

        candidate = {
            "job_type": "daily_goal_reflection",
            "user_id": user_id,
            "output": {
                "yesterday_bottleneck": bottleneck[0],
                "bottleneck_frequency": bottleneck[1],
                "highest_value_node": highest_value_node,
                "strategy_correction_needed": strategy_correction,
                "suggest_aurora_calibration": suggest_aurora,
                "failure_count": len(failures),
                "success_count": len(successes),
            },
            "evidence": {
                "signal_count": len(accumulated_signals),
                "outcome_count": len(recent_outcomes),
                "top_bottleneck": bottleneck,
            },
            "confidence": min(1.0, 0.5 + bottleneck[1] * 0.05),
            "scope": "daily_reflection",
            "user_visible": True,
            "created_at": _utcnow(),
        }

        await self._store_candidate(user_id, "daily_goal_reflection", candidate)
        return candidate

    async def run_policy_effect_compaction(
        self,
        user_id: str,
        policy_ledger_entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Job 2: PolicyEffectCompaction — compress PolicyEffectLedger → StrategyBelief.

        Groups policy outcomes by strategy type and produces confidence-updated beliefs.
        """
        from collections import Counter

        if not policy_ledger_entries:
            return self._empty_candidate("policy_effect_compaction", user_id)

        # Group by strategy
        strategy_outcomes: dict[str, list[str]] = {}
        for entry in policy_ledger_entries:
            strategy = entry.get("strategy", "unknown")
            outcome = entry.get("outcome", "neutral")
            strategy_outcomes.setdefault(strategy, []).append(outcome)

        beliefs: list[dict[str, Any]] = []
        for strategy, outcomes in strategy_outcomes.items():
            counts = Counter(outcomes)
            total = len(outcomes)
            positive = counts.get("positive", 0)
            negative = counts.get("negative", 0)
            belief_strength = (positive - negative) / max(total, 1)

            beliefs.append({
                "strategy": strategy,
                "belief_strength": round(belief_strength, 3),
                "total_observations": total,
                "positive_count": positive,
                "negative_count": negative,
            })

        candidate = {
            "job_type": "policy_effect_compaction",
            "user_id": user_id,
            "output": {"strategy_beliefs": beliefs},
            "evidence": {"ledger_entry_count": len(policy_ledger_entries)},
            "confidence": min(1.0, 0.3 + len(policy_ledger_entries) * 0.05),
            "scope": "strategy_belief_update",
            "user_visible": False,
            "created_at": _utcnow(),
        }

        await self._store_candidate(user_id, "policy_effect_compaction", candidate)
        return candidate

    async def run_skill_candidate(
        self,
        user_id: str,
        strategy_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Job 3: SkillCandidate — repeated effective strategies → SkillCandidate.

        Identifies strategies that consistently produce positive outcomes.
        """
        from collections import Counter

        if not strategy_history:
            return self._empty_candidate("skill_candidate", user_id)

        # Find strategies with high positive rate and >= 3 uses
        strategy_stats: dict[str, dict[str, int]] = {}
        for entry in strategy_history:
            strategy = entry.get("strategy", "")
            outcome = entry.get("outcome", "neutral")
            stats = strategy_stats.setdefault(strategy, {"positive": 0, "total": 0})
            stats["total"] += 1
            if outcome == "positive":
                stats["positive"] += 1

        candidates: list[dict[str, Any]] = []
        for strategy, stats in strategy_stats.items():
            if stats["total"] >= 3:
                success_rate = stats["positive"] / stats["total"]
                if success_rate >= 0.6:
                    candidates.append({
                        "strategy": strategy,
                        "success_rate": round(success_rate, 3),
                        "usage_count": stats["total"],
                        "skill_type": self._classify_skill_type(strategy),
                    })

        candidate = {
            "job_type": "skill_candidate",
            "user_id": user_id,
            "output": {"skill_candidates": candidates},
            "evidence": {"strategy_history_count": len(strategy_history)},
            "confidence": min(1.0, 0.4 + len(candidates) * 0.1),
            "scope": "skill_extraction",
            "user_visible": False,
            "created_at": _utcnow(),
        }

        await self._store_candidate(user_id, "skill_candidate", candidate)
        return candidate

    async def run_source_effectiveness(
        self,
        user_id: str,
        source_interactions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Job 4: SourceEffectiveness — which materials work in which context.

        Output: per-source effectiveness tags like "适合概念压缩", "不适合考前24h".
        """
        if not source_interactions:
            return self._empty_candidate("source_effectiveness", user_id)

        # Group by source_id
        source_stats: dict[str, dict[str, Any]] = {}
        for interaction in source_interactions:
            source_id = interaction.get("source_id", "unknown")
            stats = source_stats.setdefault(source_id, {
                "total_uses": 0, "positive": 0, "contexts": [],
            })
            stats["total_uses"] += 1
            if interaction.get("outcome") == "positive":
                stats["positive"] += 1
            if interaction.get("context"):
                stats["contexts"].append(interaction["context"])

        effectiveness: list[dict[str, Any]] = []
        for source_id, stats in source_stats.items():
            if stats["total_uses"] < 2:
                continue
            rate = stats["positive"] / stats["total_uses"]
            context_counts = {}
            for ctx in stats["contexts"]:
                context_counts[ctx] = context_counts.get(ctx, 0) + 1
            best_context = max(context_counts, key=context_counts.get) if context_counts else "general"

            tag = "effective" if rate >= 0.6 else ("neutral" if rate >= 0.3 else "ineffective")
            effectiveness.append({
                "source_id": source_id,
                "effectiveness_tag": tag,
                "success_rate": round(rate, 3),
                "best_context": best_context,
                "usage_count": stats["total_uses"],
            })

        candidate = {
            "job_type": "source_effectiveness",
            "user_id": user_id,
            "output": {"source_effectiveness": effectiveness},
            "evidence": {"interaction_count": len(source_interactions)},
            "confidence": min(1.0, 0.3 + len(source_interactions) * 0.05),
            "scope": "source_quality",
            "user_visible": False,
            "created_at": _utcnow(),
        }

        await self._store_candidate(user_id, "source_effectiveness", candidate)
        return candidate

    async def run_community_aggregation(
        self,
        user_id: str,
        community_signals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Job 5: CommunityAggregation — anonymous common errors + resource quality.

        Aggregates anonymized patterns from community (same goal/topic cohort).
        """
        if not community_signals:
            return self._empty_candidate("community_aggregation", user_id)

        from collections import Counter

        # Aggregate common error patterns (anonymized)
        error_patterns: list[str] = []
        resource_ratings: dict[str, list[float]] = {}
        for signal in community_signals:
            if signal.get("error_pattern"):
                error_patterns.append(signal["error_pattern"])
            if signal.get("resource_id") and signal.get("rating") is not None:
                resource_ratings.setdefault(signal["resource_id"], []).append(signal["rating"])

        error_counter = Counter(error_patterns)
        common_errors = [
            {"pattern": p, "frequency": c}
            for p, c in error_counter.most_common(10)
            if c >= 2
        ]

        resource_quality = [
            {
                "resource_id": rid,
                "avg_rating": round(sum(ratings) / len(ratings), 2),
                "rating_count": len(ratings),
            }
            for rid, ratings in resource_ratings.items()
            if len(ratings) >= 2
        ]

        candidate = {
            "job_type": "community_aggregation",
            "user_id": user_id,
            "output": {
                "common_errors": common_errors,
                "resource_quality": resource_quality,
            },
            "evidence": {"signal_count": len(community_signals)},
            "confidence": min(1.0, 0.3 + len(community_signals) * 0.02),
            "scope": "community_aggregate",
            "user_visible": False,
            "created_at": _utcnow(),
        }

        await self._store_candidate(user_id, "community_aggregation", candidate)
        return candidate

    async def run_state_decay_and_retraction(
        self,
        user_id: str,
        active_states: list[dict[str, Any]],
        new_signals: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Job 6: StateDecayAndRetraction — decay stale state confidence + find counter-evidence.

        Reduces confidence on old states and identifies contradictions.
        """
        new_signals = new_signals or []
        decayed: list[dict[str, Any]] = []
        retractions: list[dict[str, Any]] = []

        new_claims = {s.get("state_key", ""): s for s in new_signals}

        for state in active_states:
            confidence = state.get("confidence", 0.5)
            created_at = state.get("created_at", "")
            state_key = state.get("state_key", "")

            # Decay: reduce confidence based on age
            age_hours = self._estimate_age_hours(created_at)
            if age_hours > 48:
                decay_factor = max(0.1, 1.0 - (age_hours - 48) * 0.01)
                new_confidence = round(confidence * decay_factor, 4)
                if new_confidence < confidence:
                    decayed.append({
                        "state_key": state_key,
                        "old_confidence": confidence,
                        "new_confidence": new_confidence,
                        "age_hours": age_hours,
                    })

            # Retraction: check for counter-evidence in new signals
            if state_key in new_claims:
                new_claim = new_claims[state_key]
                if new_claim.get("claim", "") != state.get("value", ""):
                    retractions.append({
                        "state_key": state_key,
                        "old_value": state.get("value", ""),
                        "counter_evidence": new_claim.get("claim", ""),
                        "counter_confidence": new_claim.get("confidence", 0.5),
                    })

        candidate = {
            "job_type": "state_decay_and_retraction",
            "user_id": user_id,
            "output": {
                "decayed_states": decayed,
                "retractions": retractions,
            },
            "evidence": {
                "active_state_count": len(active_states),
                "new_signal_count": len(new_signals),
            },
            "confidence": 0.7,
            "scope": "state_maintenance",
            "user_visible": False,
            "created_at": _utcnow(),
        }

        await self._store_candidate(user_id, "state_decay_and_retraction", candidate)
        return candidate

    # ── Helpers ────────────────────────────────────────────────────────

    async def _store_candidate(
        self, user_id: str, job_type: str, candidate: dict[str, Any],
    ) -> None:
        """Store an L4 candidate for downstream consumption."""
        key = _L4_CANDIDATE_KEY.format(user_id=user_id, job_type=job_type)
        await self.redis.set(key, json.dumps(candidate), ex=_CANDIDATE_TTL)
        logger.info(
            "L4 candidate stored: user={} job={} confidence={:.2f}",
            user_id, job_type, candidate.get("confidence", 0),
        )

    async def get_candidate(
        self, user_id: str, job_type: str,
    ) -> dict[str, Any] | None:
        """Retrieve a stored L4 candidate."""
        key = _L4_CANDIDATE_KEY.format(user_id=user_id, job_type=job_type)
        raw = await self.redis.get(key)
        if not raw:
            return None
        return json.loads(raw)

    def _empty_candidate(self, job_type: str, user_id: str) -> dict[str, Any]:
        """Return an empty candidate when no data is available."""
        return {
            "job_type": job_type,
            "user_id": user_id,
            "output": {},
            "evidence": {"note": "insufficient_data"},
            "confidence": 0.0,
            "scope": job_type,
            "user_visible": False,
            "created_at": _utcnow(),
        }

    @staticmethod
    def _classify_skill_type(strategy: str) -> str:
        """Classify a strategy into a skill category."""
        strategy_lower = strategy.lower()
        if any(kw in strategy_lower for kw in ("worked_example", "example", "practice")):
            return "practice_oriented"
        if any(kw in strategy_lower for kw in ("review", "spaced", "repetition")):
            return "retention"
        if any(kw in strategy_lower for kw in ("teach", "explain", "feynman")):
            return "teaching"
        if any(kw in strategy_lower for kw in ("decompose", "chunk", "break_down")):
            return "decomposition"
        return "general"

    @staticmethod
    def _estimate_age_hours(created_at: str) -> float:
        """Estimate hours since creation from ISO timestamp."""
        try:
            from datetime import UTC, datetime
            created = datetime.fromisoformat(created_at)
            now = datetime.now(UTC)
            return max(0, (now - created).total_seconds() / 3600)
        except (ValueError, TypeError):
            return 0.0


def _utcnow() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()
