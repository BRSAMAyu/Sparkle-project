"""
Core: execution
Phase: clarify
Stage: Signal-to-Action Spine Layer 4 StateRegister

可行动状态寄存器 — 每个用户维护一份活跃状态，驱动下游决策。

核心原则（来自 Final Spec Layer 4）：
- 不是完整用户画像，只保存会影响控制决策的状态位
- 每个状态必须有 confidence / scope / ttl / evidence / counter_evidence
- 不能改变行动的状态不进核心寄存器
- scope 纪律：sprint 状态不能写成长期人格

作用域层级（从窄到宽）：
turn → session → task → day → sprint → goal → subject → relationship → long_term
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, StateEntry

# Scope max TTL — Iron Rule 7: sprint 状态不能写成长期人格
_SCOPE_MAX_TTL: dict[str, int] = {
    "turn": 1,
    "session": 12,
    "task": 24,
    "day": 48,
    "current_sprint": 168,   # 7 days max
    "sprint": 168,
    "goal": 720,             # 30 days
    "subject": 720,
    "relationship": 720,
    "long_term": 8760,       # 1 year
}

# Maximum evidence entries per list
_MAX_EVIDENCE = 20

# state_key → 默认可影响的 directive 类型
_CAN_AFFECT_MAP: dict[str, list[str]] = {
    "goal_mode": ["PlanDirective", "ResponseDirective"],
    "deadline_pressure": ["ExecutionDirective", "PlanDirective", "NotificationDirective"],
    "execution_consistency": ["ExecutionDirective", "ResponseDirective"],
    "task_granularity_fit": ["ExecutionDirective"],
    "cognitive_load": ["ResponseDirective", "RetrievalDirective"],
    "affective_pressure": ["ResponseDirective"],
    "knowledge_transfer": ["ExecutionDirective", "RetrievalDirective"],
    "knowledge_bottleneck": ["ExecutionDirective", "RetrievalDirective"],
    "transfer_failure": ["ExecutionDirective", "RetrievalDirective"],
    "material_utilization": ["RetrievalDirective"],
    "source_relevance": ["RetrievalDirective"],
    "retrieval_risk": ["RetrievalDirective"],
    "growth_momentum": ["ResponseDirective", "UXDirective"],
    "recall_needed": ["NotificationDirective", "PlanDirective"],
    "strategy_confidence": ["ResponseDirective"],
    "intervention_effectiveness": ["ResponseDirective"],
    "community_cohort_pattern": ["ExecutionDirective", "RetrievalDirective"],
    "community_resource_recommendation": ["RetrievalDirective"],
    "model_conflict": ["ResponseDirective", "UXDirective"],
    "relationship_stance": ["ResponseDirective"],
    "user_agency_preference": ["ResponseDirective", "UXDirective"],
}


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _clamp_ttl(scope: str, requested_ttl: int) -> int:
    """Enforce scope discipline — Iron Rule 7."""
    max_ttl = _SCOPE_MAX_TTL.get(scope, 168)  # default to sprint max
    return min(requested_ttl, max_ttl)


class StateRegister:
    """
    Layer 4: Per-user persistent state register.

    Redis storage:
    - spine:state:{user_id}:{state_key} → JSON StateEntry
    - spine:state_index:{user_id} → Redis set of active state_keys
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    def _decode_redis_set(self, raw_members: Any) -> list[str]:
        """Decode Redis SMEMBERS result (bytes or str) to list of str."""
        return [m if isinstance(m, str) else m.decode() for m in raw_members]

    async def _mget_with_fallback(self, keys: list[str]) -> list[Any]:
        """Batch GET via MGET, falling back to individual GETs for FakeRedis."""
        try:
            return await self.redis.mget(*keys)
        except AttributeError:
            return [await self.redis.get(k) for k in keys]

    def _scan_expired(
        self, decoded_keys: list[str], raw_values: list[Any],
    ) -> tuple[list[StateEntry], list[str]]:
        """Scan MGET results, returning (active entries, expired keys)."""
        entries: list[StateEntry] = []
        expired: list[str] = []
        for state_key, data in zip(decoded_keys, raw_values, strict=False):
            if data is None:
                expired.append(state_key)
                continue
            entry = StateEntry.from_dict(json.loads(data))
            if self._is_expired(entry):
                expired.append(state_key)
                continue
            entries.append(entry)
        return entries, expired

    async def upsert_from_signal(self, user_id: str, signal: ActionableSignal) -> StateEntry:
        """
        Upsert a state from a signal. If the state_key already exists and
        the new signal has higher confidence, update value + confidence;
        otherwise only merge evidence.
        """
        existing = await self.get_state(user_id, signal.state_key)

        if existing:
            new_evidence = signal.evidence_summary
            if new_evidence and new_evidence not in existing.supporting_evidence:
                existing.supporting_evidence = (existing.supporting_evidence + [new_evidence])[-_MAX_EVIDENCE:]
            # Only overwrite value when confidence is higher
            if signal.confidence > existing.confidence:
                existing.confidence = signal.confidence
                existing.value = signal.claim
            existing.last_updated_at = datetime.now(UTC).isoformat()
            await self._save_state(user_id, existing)
            return existing

        # New state
        clamped_ttl = _clamp_ttl(signal.scope, signal.ttl_hours)
        entry = StateEntry(
            state_key=signal.state_key,
            value=signal.claim,
            confidence=signal.confidence,
            scope=signal.scope,
            ttl_hours=clamped_ttl,
            supporting_evidence=[signal.evidence_summary] if signal.evidence_summary else [],
            counter_evidence=[],
            last_updated_at=datetime.now(UTC).isoformat(),
            can_affect=_CAN_AFFECT_MAP.get(signal.state_key, []),
            user_visible=True,
            requires_confirmation_if_high_impact=signal.confidence < 0.5 and signal.priority == "high",
        )
        await self._save_state(user_id, entry)
        logger.info(
            "StateRegister: upsert user={} key={} value={} conf={:.2f} ttl={}",
            user_id, entry.state_key, entry.value, entry.confidence, entry.ttl_hours,
        )
        return entry

    async def get_active_states(self, user_id: str) -> list[StateEntry]:
        """Get all active (non-expired) states for a user. Uses MGET for batch loading."""
        try:
            index_key = f"spine:state_index:{user_id}"
            state_keys = await self.redis.smembers(index_key)
        except Exception:
            logger.warning("StateRegister: Redis unavailable during get_active_states for user={}", user_id)
            return []
        if not state_keys:
            return []

        decoded_keys = self._decode_redis_set(state_keys)
        redis_keys = [f"spine:state:{user_id}:{sk}" for sk in decoded_keys]
        raw_values = await self._mget_with_fallback(redis_keys)

        entries, expired = self._scan_expired(decoded_keys, raw_values)
        if expired:
            await self._remove_keys(user_id, expired)

        entries.sort(key=lambda e: (-e.confidence, e.state_key))
        return entries

    async def get_state(self, user_id: str, state_key: str) -> StateEntry | None:
        """Get a specific state entry."""
        data = await self.redis.get(f"spine:state:{user_id}:{state_key}")
        if data is None:
            return None

        entry = StateEntry.from_dict(json.loads(data))
        if self._is_expired(entry):
            await self._remove_keys(user_id, [state_key])
            return None
        return entry

    async def add_counter_evidence(self, user_id: str, state_key: str, evidence: str) -> bool:
        """Add counter-evidence to a state. Returns True if state exists."""
        entry = await self.get_state(user_id, state_key)
        if entry is None:
            return False

        if evidence not in entry.counter_evidence:
            entry.counter_evidence = (entry.counter_evidence + [evidence])[-_MAX_EVIDENCE:]
        entry.last_updated_at = datetime.now(UTC).isoformat()
        await self._save_state(user_id, entry)

        logger.info(
            "StateRegister: counter_evidence user={} key={} total={}",
            user_id, state_key, len(entry.counter_evidence),
        )
        return True

    async def remove_state(self, user_id: str, state_key: str) -> None:
        """Remove a specific state."""
        await self._remove_keys(user_id, [state_key])

    async def expire_stale(self, user_id: str) -> int:
        """Remove all expired states. Returns count of expired. Uses MGET."""
        index_key = f"spine:state_index:{user_id}"
        all_keys = await self.redis.smembers(index_key)
        if not all_keys:
            return 0

        decoded_keys = self._decode_redis_set(all_keys)
        redis_keys = [f"spine:state:{user_id}:{sk}" for sk in decoded_keys]
        raw_values = await self._mget_with_fallback(redis_keys)

        expired = [sk for sk, data in zip(decoded_keys, raw_values, strict=False)
                   if data is None or self._is_expired(StateEntry.from_dict(json.loads(data)))]

        if expired:
            await self._remove_keys(user_id, expired)
            logger.info("StateRegister: expired {} stale states for user={}", len(expired), user_id)
        return len(expired)

    async def clear_scope(self, user_id: str, scope: str) -> int:
        """Remove all states with a given scope (e.g. 'turn', 'session')."""
        states = await self.get_active_states(user_id)
        to_remove = [s.state_key for s in states if s.scope == scope]
        if to_remove:
            await self._remove_keys(user_id, to_remove)
            logger.info("StateRegister: cleared {} states with scope={} for user={}", len(to_remove), scope, user_id)
        return len(to_remove)

    def _is_expired(self, entry: StateEntry) -> bool:
        """Check if a state has exceeded its TTL."""
        try:
            updated = _parse_iso(entry.last_updated_at)
            deadline = updated + timedelta(hours=entry.ttl_hours)
            return datetime.now(UTC) > deadline
        except (ValueError, TypeError):
            return False

    async def lower_confidence(
        self,
        user_id: str,
        state_key: str,
        amount: float = 0.15,
        reason: str = "",
    ) -> StateEntry | None:
        """Lower the confidence of a state entry due to user disconfirmation.

        Confidence floor is 0.05 — it never drops to zero from lowering alone.
        Counter-evidence is recorded for audit.
        """
        entry = await self.get_state(user_id, state_key)
        if entry is None:
            return None

        entry.confidence = round(max(0.05, entry.confidence - amount), 4)
        evidence_str = f"[{datetime.now(UTC).isoformat()}] confidence lowered by {amount:.2f}: {reason}"
        entry.counter_evidence = (
            entry.counter_evidence + [evidence_str]
        )[-_MAX_EVIDENCE:]
        entry.last_updated_at = datetime.now(UTC).isoformat()
        await self._save_state(user_id, entry)

        logger.info(
            "StateRegister: lower_confidence user={} key={} new_conf={:.2f} amount={:.2f}",
            user_id, state_key, entry.confidence, amount,
        )
        return entry

    async def check_retractions(
        self,
        user_id: str,
        active_events: list[str] | None = None,
    ) -> list[str]:
        """Check all states for retract_if conditions. Returns list of retracted state_keys.

        A state is retracted if any of its retract_if conditions match an active event.
        """
        active_events = active_events or []
        states = await self.get_active_states(user_id)
        retracted = []

        for state in states:
            if not state.retract_if:
                continue
            for condition in state.retract_if:
                if condition in active_events:
                    await self.remove_state(user_id, state.state_key)
                    retracted.append(state.state_key)
                    logger.info(
                        "StateRegister: retracted state={} user={} condition={}",
                        state.state_key, user_id, condition,
                    )
                    break

        return retracted

    async def _save_state(self, user_id: str, entry: StateEntry) -> None:
        """Persist a state entry to Redis atomically (set + index in one pipeline)."""
        key = f"spine:state:{user_id}:{entry.state_key}"
        index_key = f"spine:state_index:{user_id}"
        ttl_seconds = entry.ttl_hours * 3600
        try:
            async with self.redis.pipeline() as pipe:
                pipe.set(key, json.dumps(entry.to_dict()), ex=ttl_seconds)
                pipe.sadd(index_key, entry.state_key)
                pipe.expire(index_key, max(ttl_seconds, 86400))
                await pipe.execute()
        except (AttributeError, TypeError):
            try:
                await self.redis.set(key, json.dumps(entry.to_dict()), ex=ttl_seconds)
                await self.redis.sadd(index_key, entry.state_key)
                await self.redis.expire(index_key, max(ttl_seconds, 86400))
            except Exception:
                logger.warning("StateRegister: Redis unavailable during _save_state for user={}", user_id)
        except Exception:
            logger.warning("StateRegister: Redis unavailable during pipeline _save_state for user={}", user_id)

    async def _remove_keys(self, user_id: str, state_keys: list[str]) -> None:
        """Remove state entries and their index entries using pipeline for batch deletes."""
        if not state_keys:
            return
        index_key = f"spine:state_index:{user_id}"
        try:
            async with self.redis.pipeline() as pipe:
                for sk in state_keys:
                    pipe.delete(f"spine:state:{user_id}:{sk}")
                pipe.srem(index_key, *state_keys)
                await pipe.execute()
        except (AttributeError, TypeError):
            # Fallback for FakeRedis or non-pipeline clients
            for sk in state_keys:
                await self.redis.delete(f"spine:state:{user_id}:{sk}")
            await self.redis.srem(index_key, *state_keys)
