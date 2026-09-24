from __future__ import annotations

import asyncio
import json
import logging
import weakref
from collections import Counter
from typing import Any
from uuid import uuid4

from app.services.evidence.belief_state import BeliefState
from app.services.evidence.reward_model import RewardBreakdown, RoutingRewardModel
from app.services.evidence.unified_evidence import (
    EvidenceDirection,
    EvidenceSourceType,
    EvidenceTarget,
    UnifiedEvidence,
)

logger = logging.getLogger(__name__)

# WT294-P0: update_user_state 是 GET->fuse->SETEX 的跨 await 读改写。同一用户的
# 并发写入方（chat_signal_collector 每轮信号、task_event_consumer 结局回灌、
# cognitive API）会在 load_state 与 save_state 之间交错，后写者覆盖前写者，
# 静默丢失证据（复现：8 路并发丢 7 条）。FusionEngine 在各调用点按次实例化，
# 实例级锁无效——锁必须模块级、按已解析 user_id 取。WeakValueDictionary 保证
# 无持锁者且无等待者时条目自动回收（等待中的协程帧持有 Lock 强引用）。
_user_state_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()


class FusionEngine:
    """
    V1 Belief Fusion Engine.
    Converts UnifiedEvidence into probabilistic updates for the user's Belief State.
    This serves as the foundational observation model for future RL policies.
    """

    BELIEF_STATE_KEY = "aurora:belief_state:v1:{user_id}"
    BELIEF_SCOPED_STATE_KEY = "aurora:belief_state:v1:{user_id}:{scope_level}:{scope_id}"
    BELIEF_TRACE_KEY = "aurora:belief_trace:v1:{user_id}"
    BELIEF_TRACE_LOST_KEY = "aurora:belief_trace_lost:v1:{user_id}"
    COLLECTOR_LAST_ERROR_KEY = "aurora:belief_collector_error:v1:{user_id}"
    BELIEF_STATE_TTL_SECONDS = 7 * 24 * 3600
    TRACE_TTL_SECONDS = 7 * 24 * 3600
    TRACE_LIMIT = 120
    HEURISTIC_MIN_OBSERVATION_VARIANCE = 0.15
    SAME_SOURCE_MIN_OBSERVATION_VARIANCE = 0.08
    SAME_SOURCE_CONFIDENCE_DECAY = 0.85

    # Explicit Mapping: Evidence Targets to Router Signals (for Shadow comparison)
    # This addresses Claude's requirement to explicitly map what continuous variables
    # influence the mode vs. strategy.
    TARGET_ROUTER_MAPPING = {
        EvidenceTarget.EMOTIONAL_BLOCK: {"router_signal": "emotional_block", "impacts_mode": True},
        EvidenceTarget.TASK_AVERSION: {"router_signal": "procrastination_pattern", "impacts_mode": True},
        EvidenceTarget.COGNITIVE_LOAD: {"router_signal": "high_cognitive_load", "impacts_mode": True},
        EvidenceTarget.GOAL_CLARITY: {"router_signal": "goal_clear", "impacts_mode": True},
        EvidenceTarget.EXECUTION_CAPACITY: {"router_signal": "execution_first_viability", "impacts_mode": True},
        EvidenceTarget.METACOGNITION_ACCURACY: {"router_signal": "low_metacognition_accuracy", "impacts_mode": True},
        EvidenceTarget.SYSTEM_DISSATISFACTION: {"router_signal": "route_outcome_support_needed", "impacts_mode": True},
        # Strategy-only targets
        EvidenceTarget.AI_VERBOSITY_PREFERENCE: {"router_signal": "suggested_verbosity", "impacts_mode": False},
        EvidenceTarget.DIRECTNESS_PREFERENCE: {"router_signal": "aurora_directness", "impacts_mode": False},
        EvidenceTarget.CONVERSATION_RHYTHM: {"router_signal": "conversation_rhythm", "impacts_mode": False},
        EvidenceTarget.TASK_COMPLETION_STATE: {"router_signal": "task_completion_state", "impacts_mode": False},
    }

    def __init__(self, user_id: str | None = None):
        self.user_id = user_id

    def fuse_evidence(self, current_belief: BeliefState, evidence: UnifiedEvidence) -> BeliefState:
        """
        Takes the current belief state and a new piece of evidence, returning the updated belief state.
        V1: Confidence-weighted Independent Gaussian update (No block-covariance yet).
        """
        if not evidence or evidence.target_latent_variable not in self.TARGET_ROUTER_MAPPING:
            # We only fuse evidence that maps to known latent variables.
            return current_belief

        target = evidence.target_latent_variable
        belief_var = current_belief.get_variable(target)

        # 1. Map Evidence Direction & Strength to an Observed Mean
        # Strength is interpreted as the observed target level.
        # INCREASE says "the target is present at this level"; DECREASE says
        # "the opposite is present at this level"; OBSERVE reports the direct level.
        if evidence.direction == EvidenceDirection.INCREASE:
            observed_mean = evidence.strength
        elif evidence.direction == EvidenceDirection.DECREASE:
            observed_mean = 1.0 - evidence.strength
        else:
            # Observe means the extractor is directly reporting a target value.
            observed_mean = evidence.strength

        effective_confidence, min_observation_variance, discount_reason = self._effective_observation_params(evidence)
        evidence.metadata["effective_confidence"] = round(effective_confidence, 4)
        if discount_reason:
            evidence.metadata["confidence_discount_applied"] = True
            evidence.metadata["confidence_discount_reason"] = discount_reason
            evidence.metadata["min_observation_variance"] = round(min_observation_variance, 4)

        # 2. Bayesian Update (1D Kalman Step)
        # We pass the calculated observed_mean and the evidence's effective confidence.
        belief_var.update_from_evidence(
            observed_mean=observed_mean,
            confidence=effective_confidence,
            min_observation_variance=min_observation_variance,
            observed_at=evidence.timestamp,
            evidence_id=evidence.evidence_id,
            source_type=evidence.source_type.value,
        )

        logger.debug(
            "Fused Evidence -> User: %s | Target: %s | New Mean: %.3f | New Variance: %.3f",
            self.user_id or current_belief.user_id,
            target.value,
            belief_var.mean,
            belief_var.variance,
        )

        # 3. Update State metadata
        current_belief.last_fused_at = evidence.timestamp
        return current_belief

    def _effective_observation_params(self, evidence: UnifiedEvidence) -> tuple[float, float, str | None]:
        metadata = evidence.metadata or {}
        extractor = str(metadata.get("extractor") or "").strip()
        is_heuristic = evidence.source_type == EvidenceSourceType.HEURISTIC_FALLBACK or extractor == "rule_fallback"
        confidence = max(0.0, min(1.0, float(evidence.confidence)))
        min_variance = 0.01
        reasons: list[str] = []
        if is_heuristic:
            confidence = min(confidence, 0.62)
            min_variance = max(min_variance, self.HEURISTIC_MIN_OBSERVATION_VARIANCE)
            reasons.append("heuristic_fallback_variance_floor")

        if metadata.get("same_source_correlation_discount_applied") is True:
            try:
                group_index = max(1, int(metadata.get("same_source_group_index") or 1))
            except (TypeError, ValueError):
                group_index = 1
            confidence *= self.SAME_SOURCE_CONFIDENCE_DECAY ** group_index
            min_variance = max(min_variance, self.SAME_SOURCE_MIN_OBSERVATION_VARIANCE)
            reasons.append("same_source_correlation_variance_floor")

        return confidence, min_variance, "+".join(reasons) if reasons else None

    def fuse_many(self, current_belief: BeliefState, evidence_items: list[UnifiedEvidence]) -> BeliefState:
        for evidence in self._decorrelate_same_source_evidence(evidence_items):
            current_belief = self.fuse_evidence(current_belief, evidence)
        return current_belief

    def _decorrelate_same_source_evidence(self, evidence_items: list[UnifiedEvidence]) -> list[UnifiedEvidence]:
        """Mark same-turn, same-source evidence so it is not treated as fully independent.

        Bayesian sequential fusion assumes conditional independence between observations.
        A single user message can produce several evidence objects, but those are often
        correlated features of the same observation. V1 keeps the simple sequential
        update, while inflating observation noise for the second and later item in the
        same source group.
        """
        ordered = sorted(evidence_items or [], key=lambda item: item.timestamp)
        group_sizes = Counter(self._same_source_group_key(evidence) for evidence in ordered)
        group_seen: Counter[str] = Counter()
        for evidence in ordered:
            key = self._same_source_group_key(evidence)
            index = group_seen[key]
            group_seen[key] += 1
            if group_sizes[key] <= 1:
                continue
            evidence.metadata["same_source_group_id"] = key
            evidence.metadata["same_source_group_size"] = int(group_sizes[key])
            evidence.metadata["same_source_group_index"] = int(index)
            if index > 0:
                evidence.metadata["same_source_correlation_discount_applied"] = True
                evidence.metadata["correlation_discount_reason"] = (
                    "same_turn_same_source_evidence_not_conditionally_independent"
                )
        return ordered

    @staticmethod
    def _same_source_group_key(evidence: UnifiedEvidence) -> str:
        metadata = evidence.metadata if isinstance(evidence.metadata, dict) else {}
        scope = evidence.scope if isinstance(evidence.scope, dict) else {}
        extractor = str(metadata.get("extractor") or evidence.source_type.value or "unknown").strip()
        conversation_id = str(scope.get("conversation_id") or metadata.get("conversation_id") or "").strip()
        turn_index = scope.get("turn_index", metadata.get("turn_index"))
        if conversation_id and turn_index is not None:
            return f"conversation:{conversation_id}:turn:{turn_index}:source:{evidence.source_type.value}:extractor:{extractor}"
        task_id = str(scope.get("task_id") or metadata.get("task_id") or "").strip()
        if task_id:
            return f"task:{task_id}:source:{evidence.source_type.value}:extractor:{extractor}"
        text = " ".join(str(evidence.evidence_text or "").split())[:80]
        timestamp_bucket = evidence.timestamp.replace(microsecond=0).isoformat() if evidence.timestamp else "unknown_time"
        return f"text:{text}:time:{timestamp_bucket}:source:{evidence.source_type.value}:extractor:{extractor}"

    @staticmethod
    def scope_from_evidence(evidence_items: list[UnifiedEvidence]) -> tuple[str | None, str | None]:
        for evidence in evidence_items:
            scope = evidence.scope if isinstance(evidence.scope, dict) else {}
            goal_id = str(scope.get("goal_id") or "").strip()
            if goal_id and goal_id != "None":
                return "goal", goal_id
        for evidence in evidence_items:
            scope = evidence.scope if isinstance(evidence.scope, dict) else {}
            plan_id = str(scope.get("plan_id") or "").strip()
            if plan_id and plan_id != "None":
                return "plan", plan_id
        return None, None

    def project_router_signals(self, belief_state: BeliefState) -> dict[str, Any]:
        """
        Project continuous beliefs into a shadow version of the current Router interface.

        This does not drive production routing. It exists to measure disagreement between
        belief-state routing and the current boolean/threshold router.
        """
        emotional_score = (
            belief_state.peek_variable(EvidenceTarget.EMOTIONAL_BLOCK)
            or belief_state.get_variable(EvidenceTarget.EMOTIONAL_BLOCK)
        ).mean
        aversion_score = (
            belief_state.peek_variable(EvidenceTarget.TASK_AVERSION)
            or belief_state.get_variable(EvidenceTarget.TASK_AVERSION)
        ).mean
        load_score = (
            belief_state.peek_variable(EvidenceTarget.COGNITIVE_LOAD)
            or belief_state.get_variable(EvidenceTarget.COGNITIVE_LOAD)
        ).mean
        goal_score = (
            belief_state.peek_variable(EvidenceTarget.GOAL_CLARITY)
            or belief_state.get_variable(EvidenceTarget.GOAL_CLARITY)
        ).mean
        capacity_score = (
            belief_state.peek_variable(EvidenceTarget.EXECUTION_CAPACITY)
            or belief_state.get_variable(EvidenceTarget.EXECUTION_CAPACITY)
        ).mean
        metacognition_score = (
            belief_state.peek_variable(EvidenceTarget.METACOGNITION_ACCURACY)
            or belief_state.get_variable(EvidenceTarget.METACOGNITION_ACCURACY)
        ).mean
        dissatisfaction_score = (
            belief_state.peek_variable(EvidenceTarget.SYSTEM_DISSATISFACTION)
            or belief_state.get_variable(EvidenceTarget.SYSTEM_DISSATISFACTION)
        ).mean
        metacognition_risk = 1.0 - metacognition_score
        support_pressure_score = min(
            1.0,
            0.24 * emotional_score
            + 0.21 * aversion_score
            + 0.19 * load_score
            + 0.13 * metacognition_risk
            + 0.11 * (1.0 - capacity_score)
            + 0.12 * dissatisfaction_score,
        )
        execution_readiness_score = max(
            0.0,
            0.34 * goal_score
            + 0.30 * capacity_score
            + 0.18 * (1.0 - load_score)
            + 0.10 * metacognition_score
            + 0.08 * (1.0 - aversion_score),
        )
        if (
            support_pressure_score >= 0.70
            or emotional_score >= 0.72
            or aversion_score >= 0.72
            or dissatisfaction_score >= 0.78
            or (load_score >= 0.78 and capacity_score <= 0.45)
        ):
            shadow_mode = "cognitive_first"
        elif execution_readiness_score >= 0.66 and support_pressure_score <= 0.46:
            shadow_mode = "execution_first"
        else:
            shadow_mode = "balanced"

        return {
            "schema_version": "router_shadow_projection.v1",
            "shadow_mode": shadow_mode,
            "support_pressure_score": round(support_pressure_score, 4),
            "execution_readiness_score": round(execution_readiness_score, 4),
            "signals": {
                "emotional_block_detected": emotional_score >= 0.62,
                "procrastination_pattern": aversion_score >= 0.62,
                "high_cognitive_load": load_score >= 0.55,
                "very_high_cognitive_load": load_score >= 0.78,
                "goal_clear": goal_score >= 0.62,
                "low_metacognition_accuracy": metacognition_score <= 0.45,
                "execution_capacity_low": capacity_score <= 0.42,
                "system_dissatisfaction": dissatisfaction_score >= 0.68,
            },
            "raw_scores": {
                "emotional_block": round(emotional_score, 4),
                "task_aversion": round(aversion_score, 4),
                "cognitive_load": round(load_score, 4),
                "goal_clarity": round(goal_score, 4),
                "execution_capacity": round(capacity_score, 4),
                "metacognition_accuracy": round(metacognition_score, 4),
                "system_dissatisfaction": round(dissatisfaction_score, 4),
            },
            "target_router_mapping": {
                target.value: dict(mapping) for target, mapping in self.TARGET_ROUTER_MAPPING.items()
            },
        }

    def generate_rl_trace(
        self,
        belief_state: BeliefState,
        router_decision: str | None = None,
        outcome: str = "unknown",
        *,
        action_taken: dict[str, Any] | str | None = None,
        actual_router_mode: str | None = None,
        router_snapshot: dict[str, Any] | None = None,
        alternative_actions: list[dict[str, Any]] | None = None,
        reward: RewardBreakdown | dict[str, Any] | None = None,
        reward_proxy: dict[str, Any] | None = None,
        cost_proxy: dict[str, Any] | None = None,
        evidence_metadata_summary: dict[str, Any] | None = None,
        training_eligible: bool = True,
    ) -> dict[str, Any]:
        """
        Generates the RL-ready Trace Log required for future Constrained RL training.
        """
        resolved_action = action_taken if action_taken is not None else router_decision
        reward_payload = self._coerce_reward_payload(reward) or (
            RoutingRewardModel.unknown().to_trace_payload() if outcome == "unknown" else {}
        )
        metadata_summary = dict(evidence_metadata_summary or {})
        router_snapshot_payload = dict(router_snapshot or {})
        scope_metadata = getattr(belief_state, "scope_metadata", {}) or {}
        mode_stability = router_snapshot_payload.get("mode_stability")
        if not isinstance(mode_stability, dict):
            mode_stability = {}
        return {
            "schema_version": "rl_ready_trace.v1",
            "trace_id": str(uuid4()),
            "user_id": self.user_id or belief_state.user_id,
            "timestamp": belief_state.last_fused_at.isoformat(),
            "belief_state_id": belief_state.state_id,
            "belief_scope_level": scope_metadata.get("belief_scope_level")
            or router_snapshot_payload.get("belief_scope_level")
            or "global",
            "belief_scope_id": scope_metadata.get("belief_scope_id") or router_snapshot_payload.get("belief_scope_id"),
            "global_belief_state_id": scope_metadata.get("global_belief_state_id")
            or router_snapshot_payload.get("global_belief_state_id")
            or belief_state.state_id,
            "scoped_belief_state_id": scope_metadata.get("scoped_belief_state_id")
            or router_snapshot_payload.get("scoped_belief_state_id"),
            "belief_state_vector": belief_state.to_rl_vector(),
            "belief_uncertainty_vector": belief_state.uncertainty_vector(),
            "belief_projection_diagnostics": belief_state.projection_diagnostics(),
            "belief_source_breakdown": self._belief_source_breakdown(belief_state),
            "evidence_metadata_summary": metadata_summary,
            "cognitive_load_type_counts": metadata_summary.get("cognitive_load_type_counts", {}),
            "stage_of_change_counts": metadata_summary.get("stage_of_change_counts", {}),
            "extraneous_load_rate": metadata_summary.get("extraneous_load_rate", 0.0),
            "belief_variable_evidence_counts": {
                key: int(value.evidence_count) for key, value in sorted(belief_state.variables.items())
            },
            "router_shadow_projection": self.project_router_signals(belief_state),
            "router_snapshot": router_snapshot_payload,
            "raw_mode": mode_stability.get("raw_mode") or router_snapshot_payload.get("raw_mode"),
            "stabilized_mode": (
                mode_stability.get("stabilized_mode")
                or router_snapshot_payload.get("stabilized_mode")
                or actual_router_mode
            ),
            "mode_stability_reason": mode_stability.get("reason") or router_snapshot_payload.get("mode_stability_reason"),
            "commitment_remaining": mode_stability.get("commitment_remaining"),
            "l1_intent": router_snapshot_payload.get("l1_intent"),
            "intent_filter_applied": bool(router_snapshot_payload.get("intent_filter_applied", False)),
            "l1_override_applied": bool(router_snapshot_payload.get("l1_override_applied", False)),
            "active_probe_target": router_snapshot_payload.get("active_probe_target"),
            "action_taken": resolved_action,
            "actual_router_mode": actual_router_mode,
            "alternative_actions": alternative_actions or [],
            "outcome": outcome,  # Filled asynchronously by the Truth Matrix
            "outcome_status": "censored" if outcome == "unknown" else "observed",
            "reward": reward_payload,
            "reward_proxy": reward_proxy or {},
            "cost_proxy": cost_proxy or {},
            "training_eligible": bool(training_eligible and outcome != "unknown"),
            "is_shadow_mode": True,
        }

    @staticmethod
    def summarize_evidence_metadata(evidence_items: list[UnifiedEvidence]) -> dict[str, Any]:
        cognitive_load_type_counts: Counter[str] = Counter()
        stage_of_change_counts: Counter[str] = Counter()
        academic_prior_counts: Counter[str] = Counter()
        confidence_discount_count = 0
        same_source_correlation_discount_count = 0
        same_source_group_sizes: Counter[str] = Counter()
        cognitive_load_total = 0
        for evidence in evidence_items or []:
            metadata = evidence.metadata if isinstance(evidence.metadata, dict) else {}
            if metadata.get("confidence_discount_applied") is True:
                confidence_discount_count += 1
            if metadata.get("same_source_correlation_discount_applied") is True:
                same_source_correlation_discount_count += 1
            group_id = str(metadata.get("same_source_group_id") or "").strip()
            if group_id:
                try:
                    same_source_group_sizes[group_id] = max(
                        same_source_group_sizes[group_id],
                        int(metadata.get("same_source_group_size") or 1),
                    )
                except (TypeError, ValueError):
                    same_source_group_sizes[group_id] = max(same_source_group_sizes[group_id], 1)
            stage = str(metadata.get("stage_of_change") or "unknown").strip() or "unknown"
            stage_of_change_counts[stage] += 1
            academic_prior = str(metadata.get("academic_prior") or "").strip()
            if academic_prior:
                academic_prior_counts[academic_prior] += 1
            if evidence.target_latent_variable == EvidenceTarget.COGNITIVE_LOAD:
                cognitive_load_total += 1
                load_type = str(metadata.get("cognitive_load_type") or "unknown").strip() or "unknown"
                cognitive_load_type_counts[load_type] += 1
        extraneous_count = cognitive_load_type_counts.get("extraneous", 0)
        return {
            "schema_version": "evidence_metadata_summary.v1",
            "cognitive_load_type_counts": dict(cognitive_load_type_counts),
            "stage_of_change_counts": dict(stage_of_change_counts),
            "academic_prior_counts": dict(academic_prior_counts),
            "cognitive_load_evidence_count": cognitive_load_total,
            "extraneous_load_rate": round(extraneous_count / cognitive_load_total, 4) if cognitive_load_total else 0.0,
            "confidence_discount_count": confidence_discount_count,
            "same_source_correlation_discount_count": same_source_correlation_discount_count,
            "same_source_correlation_group_count": len(same_source_group_sizes),
            "same_source_correlation_max_group_size": max(same_source_group_sizes.values(), default=0),
            "system_output_issue_hint": bool(cognitive_load_total and extraneous_count / cognitive_load_total >= 0.5),
        }

    def _state_key(self, *, user_id: str, scope_level: str | None = None, scope_id: str | None = None) -> str:
        if scope_level and scope_id:
            return self.BELIEF_SCOPED_STATE_KEY.format(user_id=user_id, scope_level=scope_level, scope_id=scope_id)
        return self.BELIEF_STATE_KEY.format(user_id=user_id)

    @staticmethod
    def calibration_key(user_id: str) -> str:
        return f"aurora:evidence_calibration:v1:{user_id}"

    async def load_state(
        self,
        redis: Any,
        user_id: str | None = None,
        *,
        scope_level: str | None = None,
        scope_id: str | None = None,
    ) -> BeliefState:
        resolved_user_id = str(user_id or self.user_id or "")
        if not resolved_user_id:
            raise ValueError("user_id is required to load belief state")
        key = self._state_key(user_id=resolved_user_id, scope_level=scope_level, scope_id=scope_id)
        raw = await redis.get(key)
        if raw:
            try:
                return BeliefState.model_validate_json(raw)
            except Exception:
                logger.warning("Failed to parse belief state for user %s; starting fresh", resolved_user_id)
        return BeliefState(user_id=resolved_user_id)

    async def save_state(
        self,
        redis: Any,
        belief_state: BeliefState,
        *,
        scope_level: str | None = None,
        scope_id: str | None = None,
    ) -> None:
        key = self._state_key(user_id=belief_state.user_id, scope_level=scope_level, scope_id=scope_id)
        payload = belief_state.model_dump_json()
        if hasattr(redis, "setex"):
            await redis.setex(key, self.BELIEF_STATE_TTL_SECONDS, payload)
        else:
            await redis.set(key, payload)
            await redis.expire(key, self.BELIEF_STATE_TTL_SECONDS)

    async def update_user_state(
        self,
        redis: Any,
        *,
        user_id: str,
        evidence_items: list[UnifiedEvidence],
    ) -> BeliefState:
        # WT294-P0: 同一用户的并发读改写必须串行化，否则跨 await 的
        # load->fuse->save 会互相覆盖（丢证据）。锁按已解析 user_id 取，
        # 与 load_state/save_state 的 key 解析保持同一口径。
        resolved_user_id = str(user_id or self.user_id or "")
        if not resolved_user_id:
            raise ValueError("user_id is required to load belief state")
        state_lock = _user_state_locks.setdefault(resolved_user_id, asyncio.Lock())
        async with state_lock:
            global_state = await self.load_state(redis, resolved_user_id)
            global_state = self.fuse_many(global_state, evidence_items)
            await self.save_state(redis, global_state)

            scope_level, scope_id = self.scope_from_evidence(evidence_items)
            if not scope_level or not scope_id:
                global_state.scope_metadata = {  # type: ignore[attr-defined]
                    "belief_scope_level": "global",
                    "belief_scope_id": None,
                    "global_belief_state_id": global_state.state_id,
                    "scoped_belief_state_id": None,
                }
                return global_state

            scoped_state = await self.load_state(
                redis, resolved_user_id, scope_level=scope_level, scope_id=scope_id
            )
            scoped_state = self.fuse_many(scoped_state, evidence_items)
            await self.save_state(redis, scoped_state, scope_level=scope_level, scope_id=scope_id)
            scoped_state.scope_metadata = {  # type: ignore[attr-defined]
                "belief_scope_level": scope_level,
                "belief_scope_id": scope_id,
                "global_belief_state_id": global_state.state_id,
                "scoped_belief_state_id": scoped_state.state_id,
            }
            return scoped_state

    async def append_trace(self, redis: Any, *, user_id: str, trace: dict[str, Any]) -> None:
        key = self.BELIEF_TRACE_KEY.format(user_id=user_id)
        payload = json.dumps(trace, ensure_ascii=False, default=str)
        try:
            await redis.lpush(key, payload)
            await redis.ltrim(key, 0, self.TRACE_LIMIT - 1)
            await redis.expire(key, self.TRACE_TTL_SECONDS)
        except Exception as exc:
            await self.record_trace_loss(redis, user_id=user_id, error=str(exc))
            raise

    async def record_trace_loss(self, redis: Any, *, user_id: str, error: str | None = None) -> None:
        lost_key = self.BELIEF_TRACE_LOST_KEY.format(user_id=user_id)
        error_key = self.COLLECTOR_LAST_ERROR_KEY.format(user_id=user_id)
        try:
            await redis.incr(lost_key)
            await redis.expire(lost_key, self.TRACE_TTL_SECONDS)
            if error:
                await redis.setex(error_key, self.TRACE_TTL_SECONDS, str(error)[:500])
        except Exception:
            logger.debug("Failed to record belief trace loss for user %s", user_id, exc_info=True)

    async def bind_outcome_to_recent_trace(
        self,
        redis: Any,
        *,
        user_id: str,
        outcome: str,
        reward: RewardBreakdown | dict[str, Any],
        match: dict[str, Any],
        limit: int = 80,
    ) -> dict[str, Any] | None:
        """Attach an observed outcome to a matching pre-outcome trace.

        This prevents reward leakage: task outcome events should label the trace
        that existed before the outcome evidence was fused, not train on a
        post-outcome belief state.
        """
        key = self.BELIEF_TRACE_KEY.format(user_id=user_id)
        raw_entries = await redis.lrange(key, 0, max(0, limit - 1))
        reward_payload = self._coerce_reward_payload(reward) or {}
        for index, raw in enumerate(raw_entries or []):
            trace = self._loads_trace(raw)
            if not trace:
                continue
            if str(trace.get("outcome") or "unknown") != "unknown":
                continue
            score, matched_fields = self._match_score(trace, match)
            if score <= 0:
                continue
            is_weak_heuristic = (
                reward_payload.get("outcome_strength") == "weak_heuristic"
                or reward_payload.get("evidence_strength") == "weak_heuristic"
            )
            trace["outcome"] = outcome
            trace["outcome_status"] = "observed"
            trace["outcome_strength"] = "weak_heuristic" if is_weak_heuristic else trace.get("outcome_strength", "strong")
            trace["reward"] = reward_payload
            trace["training_eligible"] = not is_weak_heuristic
            trace["outcome_binding"] = {
                "schema_version": "trace_outcome_binding.v1",
                "match_score": score,
                "matched_fields": matched_fields,
                "match": {key: value for key, value in match.items() if value is not None},
                "outcome_strength": "weak_heuristic" if is_weak_heuristic else "strong",
            }
            await redis.lset(key, index, json.dumps(trace, ensure_ascii=False, default=str))
            await redis.expire(key, self.TRACE_TTL_SECONDS)
            return trace
        return None

    async def append_calibration_sample(
        self,
        redis: Any,
        *,
        user_id: str,
        sample: dict[str, Any],
        limit: int = 300,
    ) -> None:
        key = self.calibration_key(user_id)
        payload = json.dumps(sample, ensure_ascii=False, default=str)
        await redis.lpush(key, payload)
        await redis.ltrim(key, 0, max(0, limit - 1))
        await redis.expire(key, self.TRACE_TTL_SECONDS)

    async def diagnose_outcome_binding(
        self,
        redis: Any,
        *,
        user_id: str,
        match: dict[str, Any],
        limit: int = 80,
    ) -> dict[str, Any]:
        """Explain whether an outcome event has IDs that can bind to prior traces."""
        key = self.BELIEF_TRACE_KEY.format(user_id=user_id)
        raw_entries = await redis.lrange(key, 0, max(0, limit - 1))
        available_match_keys = sorted(key for key, value in match.items() if value is not None)
        best_score = 0
        best_trace: dict[str, Any] | None = None
        best_fields: list[str] = []
        inspected = 0
        trace_id_coverage: dict[str, int] = {
            "routing_trace_id": 0,
            "route_history_decision_id": 0,
            "routing_outcome_signal_id": 0,
            "conversation_id": 0,
            "task_id": 0,
            "plan_id": 0,
        }
        for raw in raw_entries or []:
            trace = self._loads_trace(raw)
            if not trace:
                continue
            inspected += 1
            for field in trace_id_coverage:
                if self._trace_lookup(trace, field):
                    trace_id_coverage[field] += 1
            score, fields = self._match_score(trace, match)
            if score > best_score:
                best_score = score
                best_fields = fields
                best_trace = trace
        return {
            "schema_version": "outcome_binding_diagnostics.v1",
            "redis_key": key,
            "inspected_traces": inspected,
            "available_match_keys": available_match_keys,
            "best_match_score": best_score,
            "best_matched_fields": best_fields,
            "best_trace_id": (best_trace or {}).get("trace_id") if best_trace else None,
            "trace_id_coverage": trace_id_coverage,
            "bindable": best_score > 0,
            "blockers": self._binding_blockers(
                best_score=best_score,
                available_match_keys=available_match_keys,
                inspected=inspected,
            ),
        }

    @staticmethod
    def _coerce_reward_payload(reward: RewardBreakdown | dict[str, Any] | None) -> dict[str, Any] | None:
        if reward is None:
            return None
        if isinstance(reward, RewardBreakdown):
            return reward.to_trace_payload()
        return dict(reward) if isinstance(reward, dict) else None

    @staticmethod
    def _binding_blockers(*, best_score: int, available_match_keys: list[str], inspected: int) -> list[str]:
        blockers: list[str] = []
        if inspected == 0:
            blockers.append("no_prior_traces")
        if not available_match_keys:
            blockers.append("outcome_event_missing_route_ids")
        if best_score <= 0 and inspected > 0:
            blockers.append("no_trace_id_overlap")
        return blockers

    @staticmethod
    def _belief_source_breakdown(belief_state: BeliefState) -> dict[str, Any]:
        total: Counter[str] = Counter()
        by_target: dict[str, dict[str, int]] = {}
        for key, variable in sorted(belief_state.variables.items()):
            source_counts = {str(source): int(count) for source, count in variable.source_breakdown.items()}
            by_target[key] = source_counts
            total.update(source_counts)
        return {
            "total": dict(total),
            "by_target": by_target,
        }

    @staticmethod
    def _loads_trace(raw: Any) -> dict[str, Any] | None:
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

    @classmethod
    def _match_score(cls, trace: dict[str, Any], match: dict[str, Any]) -> tuple[int, list[str]]:
        fields = {
            "routing_trace_id": cls._trace_lookup(trace, "routing_trace_id"),
            "route_history_decision_id": cls._trace_lookup(trace, "route_history_decision_id"),
            "routing_outcome_signal_id": cls._trace_lookup(trace, "routing_outcome_signal_id"),
            "conversation_id": cls._trace_lookup(trace, "conversation_id"),
            "task_id": cls._trace_lookup(trace, "task_id"),
            "plan_id": cls._trace_lookup(trace, "plan_id"),
        }
        weights = {
            "routing_trace_id": 5,
            "route_history_decision_id": 5,
            "routing_outcome_signal_id": 4,
            "conversation_id": 2,
            "task_id": 2,
            "plan_id": 1,
        }
        score = 0
        matched: list[str] = []
        for field, trace_value in fields.items():
            match_value = match.get(field)
            if not trace_value or not match_value:
                continue
            if str(trace_value) == str(match_value):
                score += weights[field]
                matched.append(field)
        return score, matched

    @staticmethod
    def _trace_lookup(trace: dict[str, Any], field: str) -> Any:
        if trace.get(field):
            return trace.get(field)
        for section_name in ("router_snapshot", "action_taken", "outcome_binding"):
            section = trace.get(section_name)
            if isinstance(section, dict) and section.get(field):
                return section.get(field)
            if section_name == "outcome_binding" and isinstance(section, dict):
                match = section.get("match")
                if isinstance(match, dict) and match.get(field):
                    return match.get(field)
        return None
