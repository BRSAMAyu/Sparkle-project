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
_ACTIVE_DIRECTIVE_KEY = "spine:directive:{user_id}"
_TRACE_TTL = 30 * 24 * 3600  # 30 days
_DIRECTIVE_TTL = 48 * 3600   # 48 hours
_MAX_USER_TRACES = 50


class CausalTraceStore:
    def __init__(self, redis_client: Any):
        self.redis = redis_client

    # ── CausalTrace CRUD ──────────────────────────────────────────────

    async def create_trace(self, trace_id: str | None = None) -> CausalTrace:
        tid = trace_id or _uid("ct")
        trace = CausalTrace(trace_id=tid)
        await self._save_trace(trace)
        return trace

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
        trace.signal_ids.append(signal.signal_id)
        trace.state_keys_changed.append(signal.state_key)
        from datetime import UTC, datetime
        trace.updated_at = datetime.now(UTC).isoformat()
        await self._save_trace(trace)

    async def append_policy(self, trace_id: str, decision: PolicyDecision) -> None:
        trace = await self.get_trace(trace_id)
        if not trace:
            return
        trace.policy_decision_id = decision.policy_decision_id
        from datetime import UTC, datetime
        trace.updated_at = datetime.now(UTC).isoformat()
        await self._save_trace(trace)

    async def append_directive(self, trace_id: str, directive: ExecutionDirective) -> None:
        trace = await self.get_trace(trace_id)
        if not trace:
            return
        trace.directive_ids.append(directive.directive_id)
        from datetime import UTC, datetime
        trace.updated_at = datetime.now(UTC).isoformat()
        await self._save_trace(trace)

    async def append_audit(self, trace_id: str, audit: DirectiveApplicationAudit) -> None:
        trace = await self.get_trace(trace_id)
        if not trace:
            return
        trace.audit_ids.append(audit.audit_id)
        from datetime import UTC, datetime
        trace.updated_at = datetime.now(UTC).isoformat()
        await self._save_trace(trace)

    async def append_receipt(self, trace_id: str, receipt: UserVisibleReceipt) -> None:
        trace = await self.get_trace(trace_id)
        if not trace:
            return
        trace.receipt_ids.append(receipt.receipt_id)
        from datetime import UTC, datetime
        trace.updated_at = datetime.now(UTC).isoformat()
        await self._save_trace(trace)

    async def link_to_user(self, user_id: str, trace_id: str) -> None:
        key = _USER_TRACES_KEY.format(user_id=user_id)
        await self.redis.lrem(key, 0, trace_id)
        await self.redis.lpush(key, trace_id)
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
