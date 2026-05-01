"""
Core: execution
Phase: sense→reflect
Stage: Signal-to-Action Spine M1-Step1

CausalTrace Store — 持久化审计链路到 Redis。
先做 trace 骨架，不做智能。即使中间字段先为空也要能看到 trace 框架。
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.signals.types import (
    ActionableSignal,
    CausalTrace,
    DirectiveApplicationAudit,
    ExecutionDirective,
    PolicyDecision,
    UserVisibleReceipt,
    _uid,
)

_TRACE_KEY = "spine:trace:{trace_id}"
_USER_TRACES_KEY = "spine:user_traces:{user_id}"
_USER_COMPACT_KEY = "spine:user_traces_compact:{user_id}"
_ACTIVE_DIRECTIVE_KEY = "spine:directive:{user_id}"
_TRACE_TTL = 30 * 24 * 3600  # 30 days
_COMPACT_TTL = 90 * 24 * 3600  # 90 days for compacted summaries
_DIRECTIVE_TTL = 48 * 3600   # 48 hours
_MAX_USER_TRACES = 50
_MAX_LIST_ITEMS = 20  # max items per trace list field (prevents unbounded growth)
_COMPACT_BATCH_SIZE = 10  # compact when traces exceed this many


class CausalTraceStore:
    def __init__(self, redis_client: Any):
        self.redis = redis_client

    # ── CausalTrace CRUD ──────────────────────────────────────────────

    async def create_trace(self, trace_id: str | None = None) -> CausalTrace:
        tid = trace_id or _uid("ct")
        trace = CausalTrace(trace_id=tid)
        await self._save_trace(trace)
        return trace

    @staticmethod
    def _bounded_append(lst: list, item: str) -> None:
        """Append item to list, trimming oldest entries if over limit."""
        lst.append(item)
        if len(lst) > _MAX_LIST_ITEMS:
            del lst[:len(lst) - _MAX_LIST_ITEMS]

    async def get_trace(self, trace_id: str) -> CausalTrace | None:
        raw = await self.redis.get(_TRACE_KEY.format(trace_id=trace_id))
        if not raw:
            return None
        return CausalTrace.from_dict(json.loads(raw))

    async def append_signal(self, trace_id: str, signal: ActionableSignal) -> None:
        trace = await self.get_trace(trace_id)
        if not trace:
            logger.warning("trace {} not found for signal append", trace_id)
            return
        self._bounded_append(trace.signal_ids, signal.signal_id)
        self._bounded_append(trace.state_keys_changed, signal.state_key)
        from datetime import UTC, datetime
        trace.updated_at = datetime.now(UTC).isoformat()
        await self._save_trace(trace)

    async def append_policy(self, trace_id: str, decision: PolicyDecision) -> None:
        trace = await self.get_trace(trace_id)
        if not trace:
            logger.warning("trace {} not found for policy append", trace_id)
            return
        trace.policy_decision_id = decision.policy_decision_id
        # Policy is singular — no list append needed
        from datetime import UTC, datetime
        trace.updated_at = datetime.now(UTC).isoformat()
        await self._save_trace(trace)
        # Store policy object for timeline retrieval
        key = f"spine:policy:{decision.policy_decision_id}"
        await self.redis.set(key, json.dumps(decision.to_dict()), ex=_TRACE_TTL)

    async def append_directive(self, trace_id: str, directive: ExecutionDirective) -> None:
        trace = await self.get_trace(trace_id)
        if not trace:
            logger.warning("trace {} not found for directive append", trace_id)
            return
        self._bounded_append(trace.directive_ids, directive.directive_id)
        from datetime import UTC, datetime
        trace.updated_at = datetime.now(UTC).isoformat()
        await self._save_trace(trace)
        # Store directive object for timeline retrieval
        key = f"spine:directive_by_id:{directive.directive_id}"
        await self.redis.set(key, json.dumps(directive.to_dict()), ex=_TRACE_TTL)

    async def store_directive_by_id(self, directive_id: str, data: dict) -> None:
        """Store any directive type by ID for timeline retrieval."""
        key = f"spine:directive_by_id:{directive_id}"
        await self.redis.set(key, json.dumps(data), ex=_TRACE_TTL)

    async def append_audit(self, trace_id: str, audit: DirectiveApplicationAudit) -> None:
        trace = await self.get_trace(trace_id)
        if not trace:
            logger.warning("trace {} not found for audit append", trace_id)
            return
        self._bounded_append(trace.audit_ids, audit.audit_id)
        from datetime import UTC, datetime
        trace.updated_at = datetime.now(UTC).isoformat()
        await self._save_trace(trace)

    async def append_receipt(self, trace_id: str, receipt: UserVisibleReceipt) -> None:
        trace = await self.get_trace(trace_id)
        if not trace:
            logger.warning("trace {} not found for receipt append", trace_id)
            return
        self._bounded_append(trace.receipt_ids, receipt.receipt_id)
        from datetime import UTC, datetime
        trace.updated_at = datetime.now(UTC).isoformat()
        await self._save_trace(trace)

    async def link_to_user(self, user_id: str, trace_id: str) -> None:
        key = _USER_TRACES_KEY.format(user_id=user_id)
        await self.redis.lrem(key, 0, trace_id)
        await self.redis.lpush(key, trace_id)
        # Before trimming, compact traces that would be dropped
        try:
            current_count = len(await self.redis.lrange(key, 0, -1))
            if current_count > _MAX_USER_TRACES:
                await self.compact_old_traces(user_id)
        except Exception:
            logger.warning("Trace compaction failed for user={}", user_id, exc_info=True)
        await self.redis.ltrim(key, 0, _MAX_USER_TRACES - 1)
        await self.redis.expire(key, _TRACE_TTL)

    async def get_user_traces(self, user_id: str, limit: int = 10) -> list[CausalTrace]:
        key = _USER_TRACES_KEY.format(user_id=user_id)
        trace_ids = await self.redis.lrange(key, 0, limit - 1)
        traces = []
        for tid in trace_ids:
            t = await self.get_trace(tid)
            if t:
                traces.append(t)
        return traces

    # ── Trace Compaction ──────────────────────────────────────────────

    async def compact_old_traces(self, user_id: str) -> dict[str, Any] | None:
        """Compact traces beyond the retention window into a summary.

        Reads the oldest traces, aggregates their key statistics into a
        compact summary, deletes the individual traces, and returns the
        summary.  Keeps the most recent _MAX_USER_TRACES intact.

        Returns None if there are not enough traces to compact.
        """
        key = _USER_TRACES_KEY.format(user_id=user_id)
        all_ids = await self.redis.lrange(key, 0, -1)
        total = len(all_ids)
        if total <= _MAX_USER_TRACES:
            return None

        # IDs to compact: everything beyond the kept window
        keep_count = _MAX_USER_TRACES
        compact_ids = all_ids[keep_count:]

        summary: dict[str, Any] = {
            "compaction_id": _uid("compact"),
            "user_id": user_id,
            "traces_compacted": len(compact_ids),
            "signal_types": {},
            "policy_strategies": {},
            "directive_types": {},
            "outcomes": {"effective": 0, "insufficient": 0, "inconclusive": 0},
            "time_range": {"earliest": None, "latest": None},
        }

        for tid in compact_ids:
            tid_str = tid if isinstance(tid, str) else tid.decode()
            t = await self.get_trace(tid_str)
            if not t:
                continue

            # Aggregate signal state keys
            for sk in t.state_keys_changed:
                summary["signal_types"][sk] = summary["signal_types"].get(sk, 0) + 1

            # Track time range
            if t.created_at:
                if summary["time_range"]["earliest"] is None or t.created_at < summary["time_range"]["earliest"]:
                    summary["time_range"]["earliest"] = t.created_at
                if summary["time_range"]["latest"] is None or t.created_at > summary["time_range"]["latest"]:
                    summary["time_range"]["latest"] = t.created_at

            # Aggregate directive types
            for did in t.directive_ids:
                d_raw = await self.redis.get(f"spine:directive_by_id:{did}")
                if d_raw:
                    d = json.loads(d_raw if isinstance(d_raw, str) else d_raw.decode())
                    dtype = d.get("directive_type", "unknown")
                    summary["directive_types"][dtype] = summary["directive_types"].get(dtype, 0) + 1

            # Aggregate outcomes
            if t.outcome_to_measure:
                o_raw = await self.redis.get(f"spine:outcome:{t.trace_id}")
                if o_raw:
                    o = json.loads(o_raw if isinstance(o_raw, str) else o_raw.decode())
                    eff = o.get("attribution", "inconclusive")
                    if eff in summary["outcomes"]:
                        summary["outcomes"][eff] += 1

            # Delete individual trace
            await self.redis.delete(_TRACE_KEY.format(trace_id=tid_str))

        # Trim user traces list to kept window
        await self.redis.ltrim(key, 0, keep_count - 1)

        # Store compact summary
        compact_key = _USER_COMPACT_KEY.format(user_id=user_id)
        existing_raw = await self.redis.get(compact_key)
        existing_summaries = []
        if existing_raw:
            existing_summaries = json.loads(existing_raw if isinstance(existing_raw, str) else existing_raw.decode())

        existing_summaries.append(summary)
        # Keep max 10 compact summaries
        if len(existing_summaries) > 10:
            existing_summaries = existing_summaries[-10:]

        await self.redis.set(compact_key, json.dumps(existing_summaries), ex=_COMPACT_TTL)

        logger.info(
            "TraceCompaction: user={} compacted={} traces, kept {} summaries",
            user_id, summary["traces_compacted"], len(existing_summaries),
        )
        return summary

    async def get_compact_summaries(self, user_id: str) -> list[dict[str, Any]]:
        """Retrieve all compact summaries for a user."""
        compact_key = _USER_COMPACT_KEY.format(user_id=user_id)
        raw = await self.redis.get(compact_key)
        if not raw:
            return []
        return json.loads(raw if isinstance(raw, str) else raw.decode())

    async def get_full_trace_history(self, user_id: str) -> dict[str, Any]:
        """Get combined view: active traces + compacted summaries."""
        active = await self.get_user_traces(user_id, limit=_MAX_USER_TRACES)
        compact = await self.get_compact_summaries(user_id)
        return {
            "active_traces": len(active),
            "compact_summaries": len(compact),
            "traces": [t.to_dict() for t in active],
            "compacted": compact,
        }

    # ── Active Directive ──────────────────────────────────────────────

    async def set_active_directive(self, user_id: str, directive: ExecutionDirective) -> None:
        key = _ACTIVE_DIRECTIVE_KEY.format(user_id=user_id)
        await self.redis.set(key, json.dumps(directive.to_dict()), ex=_DIRECTIVE_TTL)

    async def get_active_directive(self, user_id: str) -> ExecutionDirective | None:
        key = _ACTIVE_DIRECTIVE_KEY.format(user_id=user_id)
        raw = await self.redis.get(key)
        if not raw:
            return None
        d = json.loads(raw)
        return ExecutionDirective(
            directive_id=d["directive_id"],
            policy_decision_id=d["policy_decision_id"],
            target_module=d["target_module"],
            scope=d["scope"],
            hard_constraints=d["hard_constraints"],
            user_visible_reason=d["user_visible_reason"],
            created_at=d.get("created_at", ""),
        )

    async def clear_active_directive(self, user_id: str) -> None:
        await self.redis.delete(_ACTIVE_DIRECTIVE_KEY.format(user_id=user_id))

    # ── Signal Store ──────────────────────────────────────────────────

    async def store_signal(self, signal: ActionableSignal) -> None:
        key = f"spine:signal:{signal.signal_id}"
        ttl = signal.ttl_hours * 3600
        await self.redis.set(key, json.dumps(signal.to_dict()), ex=max(ttl, 3600))

    async def get_signal(self, signal_id: str) -> ActionableSignal | None:
        raw = await self.redis.get(f"spine:signal:{signal_id}")
        if not raw:
            return None
        return ActionableSignal.from_dict(json.loads(raw))

    # ── Private ───────────────────────────────────────────────────────

    async def _save_trace(self, trace: CausalTrace) -> None:
        key = _TRACE_KEY.format(trace_id=trace.trace_id)
        await self.redis.set(key, json.dumps(trace.to_dict()), ex=_TRACE_TTL)
