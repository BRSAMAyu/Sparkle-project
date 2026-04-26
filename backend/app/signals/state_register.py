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
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, StateEntry, _uid


# state_key → 默认可影响的 directive 类型
_CAN_AFFECT_MAP: dict[str, list[str]] = {
    "goal_mode": ["PlanDirective", "ResponseDirective"],
    "deadline_pressure": ["ExecutionDirective", "PlanDirective", "NotificationDirective"],
    "execution_consistency": ["ExecutionDirective", "ResponseDirective"],
    "task_granularity_fit": ["ExecutionDirective"],
    "cognitive_load": ["ResponseDirective", "RetrievalDirective"],
    "knowledge_transfer": ["ExecutionDirective", "RetrievalDirective"],
    "material_utilization": ["RetrievalDirective"],
    "growth_momentum": ["ResponseDirective", "UXDirective"],
    "recall_needed": ["NotificationDirective", "PlanDirective"],
    "community_cohort_pattern": ["ExecutionDirective", "RetrievalDirective"],
    "community_resource_recommendation": ["RetrievalDirective"],
}


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class StateRegister:
    """
    Layer 4: Per-user persistent state register.

    Redis storage:
    - spine:state:{user_id}:{state_key} → JSON StateEntry
    - spine:state_index:{user_id} → Redis set of active state_keys
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def upsert_from_signal(self, user_id: str, signal: ActionableSignal) -> StateEntry:
        """
        Upsert a state from a signal. If the state_key already exists and
        the new signal has higher confidence, update; otherwise keep existing.
        """
        existing = await self.get_state(user_id, signal.state_key)

        if existing:
            # Merge: update confidence if new signal is stronger
            new_evidence = signal.evidence_summary
            if new_evidence and new_evidence not in existing.supporting_evidence:
                existing.supporting_evidence.append(new_evidence)
            if signal.confidence > existing.confidence:
                existing.confidence = signal.confidence
            existing.value = signal.claim
            existing.last_updated_at = datetime.now(UTC).isoformat()
            await self._save_state(user_id, existing)
            return existing

        # New state
        entry = StateEntry(
            state_key=signal.state_key,
            value=signal.claim,
            confidence=signal.confidence,
            scope=signal.scope,
            ttl_hours=signal.ttl_hours,
            supporting_evidence=[signal.evidence_summary] if signal.evidence_summary else [],
            counter_evidence=[],
            last_updated_at=datetime.now(UTC).isoformat(),
            can_affect=_CAN_AFFECT_MAP.get(signal.state_key, []),
            user_visible=True,
            requires_confirmation_if_high_impact=signal.confidence < 0.5 and signal.priority == "high",
        )
        await self._save_state(user_id, entry)
        logger.info(
            "StateRegister: upsert user={} key={} value={} conf={:.2f}",
            user_id, entry.state_key, entry.value, entry.confidence,
        )
        return entry

    async def get_active_states(self, user_id: str) -> list[StateEntry]:
        """Get all active (non-expired) states for a user."""
        index_key = f"spine:state_index:{user_id}"
        state_keys = await self.redis.smembers(index_key)
        if not state_keys:
            return []

        entries: list[StateEntry] = []
        expired: list[str] = []

        for raw_key in state_keys:
            key = raw_key if isinstance(raw_key, str) else raw_key.decode()
            state_key = key
            data = await self.redis.get(f"spine:state:{user_id}:{state_key}")
            if data is None:
                expired.append(state_key)
                continue

            entry = StateEntry.from_dict(json.loads(data))

            # Check TTL
            if self._is_expired(entry):
                expired.append(state_key)
                continue

            entries.append(entry)

        # Clean up expired
        if expired:
            await self._remove_keys(user_id, expired)

        # Sort by confidence descending
        entries.sort(key=lambda e: e.confidence, reverse=True)
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
            entry.counter_evidence.append(evidence)
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
        """Remove all expired states. Returns count of expired."""
        states = await self.get_active_states(user_id)
        # get_active_states already cleans expired, so count from full scan
        index_key = f"spine:state_index:{user_id}"
        all_keys = await self.redis.smembers(index_key)
        if not all_keys:
            return 0

        expired: list[str] = []
        for raw_key in all_keys:
            state_key = raw_key if isinstance(raw_key, str) else raw_key.decode()
            data = await self.redis.get(f"spine:state:{user_id}:{state_key}")
            if data is None:
                expired.append(state_key)
                continue
            entry = StateEntry.from_dict(json.loads(data))
            if self._is_expired(entry):
                expired.append(state_key)

        if expired:
            await self._remove_keys(user_id, expired)

        if expired:
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

    async def _save_state(self, user_id: str, entry: StateEntry) -> None:
        """Persist a state entry to Redis."""
        key = f"spine:state:{user_id}:{entry.state_key}"
        await self.redis.set(key, json.dumps(entry.to_dict()), ex=entry.ttl_hours * 3600)
        index_key = f"spine:state_index:{user_id}"
        await self.redis.sadd(index_key, entry.state_key)

    async def _remove_keys(self, user_id: str, state_keys: list[str]) -> None:
        """Remove state entries and their index entries."""
        index_key = f"spine:state_index:{user_id}"
        for sk in state_keys:
            await self.redis.delete(f"spine:state:{user_id}:{sk}")
            await self.redis.srem(index_key, sk)
