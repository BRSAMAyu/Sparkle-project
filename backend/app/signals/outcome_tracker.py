"""
Core: execution
Phase: reflect→adapt
Stage: Signal-to-Action Spine P1-4 Outcome Tracker

干预结果追踪器 — 在 Directive 生效时注册预期结果，
在用户行为发生时记录实际结果，驱动 OutcomeRecorder 进行归因。

核心原则:
- 每个 Directive 必须注册 expected_outcome（无预期则不追踪）
- 实际结果在行为发生时被动写入（不阻塞主流程）
- 追踪窗口有 TTL（超时自动标记 inconclusive）
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.signals.outcome_recorder import OutcomeRecorder
from app.signals.types import CausalTrace, OutcomeRecord, _uid

_PENDING_KEY = "spine:pending_outcomes:"
_TRACE_KEY_PREFIX = "spine:trace:"
_DEFAULT_TTL_HOURS = 48


class OutcomeTracker:
    """
    Tracks intervention outcomes from registration to verification.

    Flow:
    1. register_expected() — called when a directive is issued
    2. record_actual() — called when user behavior is observed
    3. verify_pending() — periodic job that resolves timed-out outcomes
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.recorder = OutcomeRecorder(redis_client)

    async def register_expected(
        self,
        *,
        user_id: str,
        directive_type: str,
        trace: CausalTrace,
        expected_outcome: str,
        verification_window_hours: int = _DEFAULT_TTL_HOURS,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Register an expected outcome when a directive is issued.

        Returns a pending_outcome_id for later matching.
        """
        outcome_id = _uid("po")
        pending = {
            "outcome_id": outcome_id,
            "user_id": user_id,
            "directive_type": directive_type,
            "trace_id": trace.trace_id,
            "expected_outcome": expected_outcome,
            "context": context or {},
            "registered_at": _now_iso(),
            "verification_window_hours": verification_window_hours,
            "resolved": False,
        }
        key = f"{_PENDING_KEY}{outcome_id}"
        ttl_seconds = verification_window_hours * 3600
        await self.redis.set(key, json.dumps(pending, ensure_ascii=False), ex=ttl_seconds)

        # Also index by user for quick lookup.
        user_index_key = f"{_PENDING_KEY}user:{user_id}"
        pipe = self.redis.pipeline()
        pipe.lpush(user_index_key, outcome_id)
        pipe.ltrim(user_index_key, 0, 49)
        pipe.expire(user_index_key, ttl_seconds)
        await pipe.execute()

        logger.debug(
            f"Registered expected outcome {outcome_id} "
            f"for directive={directive_type} user={user_id} "
            f"window={verification_window_hours}h"
        )
        return outcome_id

    async def record_actual(
        self,
        *,
        pending_outcome_id: str,
        actual_outcome: dict[str, Any],
    ) -> OutcomeRecord | None:
        """
        Record the actual outcome for a previously registered expectation.

        Resolves the pending outcome and runs attribution via OutcomeRecorder.
        """
        key = f"{_PENDING_KEY}{pending_outcome_id}"
        raw = await self.redis.get(key)
        if not raw:
            logger.warning(f"No pending outcome found for {pending_outcome_id}")
            return None

        pending = json.loads(raw)
        if pending.get("resolved"):
            logger.debug(f"Outcome {pending_outcome_id} already resolved")
            return None

        # Build trace for OutcomeRecorder
        trace = CausalTrace(
            trace_id=pending["trace_id"],
            raw_event_ids=[],
            signal_ids=[],
            directive_ids=[],
        )

        record = await self.recorder.record_outcome(
            trace=trace,
            intervention=pending["directive_type"],
            reason=pending.get("context", {}).get("reason", ""),
            expected_outcome=pending["expected_outcome"],
            actual_outcome=actual_outcome,
        )

        # Mark as resolved
        pending["resolved"] = True
        pending["resolved_at"] = _now_iso()
        pending["attribution"] = record.attribution
        await self.redis.set(key, json.dumps(pending, ensure_ascii=False), ex=3600)

        logger.info(
            f"Outcome resolved: {pending_outcome_id} "
            f"attribution={record.attribution} "
            f"confidence={record.attribution_confidence:.2f}"
        )
        return record

    async def verify_pending(self, user_id: str) -> list[OutcomeRecord]:
        """
        Check for pending outcomes whose verification window has expired.
        Mark them as inconclusive and run attribution.

        Called periodically by the scheduler.
        """
        user_index_key = f"{_PENDING_KEY}user:{user_id}"
        pending_ids = await self.redis.lrange(user_index_key, 0, -1)
        resolved: list[OutcomeRecord] = []

        for pid in pending_ids:
            pid_str = pid.decode() if isinstance(pid, bytes) else pid
            key = f"{_PENDING_KEY}{pid_str}"
            raw = await self.redis.get(key)
            if not raw:
                continue

            pending = json.loads(raw)
            if pending.get("resolved"):
                continue

            # Window expired → mark inconclusive
            record = await self.record_actual(
                pending_outcome_id=pid_str,
                actual_outcome={"timeout": True, "no_observable_change": True},
            )
            if record:
                resolved.append(record)

        return resolved

    async def get_pending_count(self, user_id: str) -> int:
        """Count unresolved pending outcomes for a user."""
        user_index_key = f"{_PENDING_KEY}user:{user_id}"
        pending_ids = await self.redis.lrange(user_index_key, 0, -1)
        count = 0
        for pid in pending_ids:
            pid_str = pid.decode() if isinstance(pid, bytes) else pid
            raw = await self.redis.get(f"{_PENDING_KEY}{pid_str}")
            if raw:
                data = json.loads(raw)
                if not data.get("resolved"):
                    count += 1
        return count


def _now_iso() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()
