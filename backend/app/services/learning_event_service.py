from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.config import settings
from app.core.cache import cache_service

LEARNING_EVENT_TYPES = {
    "route_decision",
    "expert_selected",
    "expert_invoked",
    "expert_fallback",
    "prompt_selected",
    "prompt_applied",
    "toolchain_selected",
    "toolchain_degraded",
    "cold_start_bootstrap_applied",
    "response_feedback",
    "plan_execution_outcome",
    "plan_repair_triggered",
    "plan_repair_succeeded",
    "checkpoint_due",
    "checkpoint_done",
    "checkpoint_skipped",
    "quality_gate_blocked",
    "user_feedback_bound",
    "expert_overridden",
}

_MEM_EVENTS: list[dict[str, Any]] = []
_MEM_EVENT_DEDUP: set[str] = set()


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _event_timestamp_to_score(value: str) -> float:
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return _utcnow().timestamp()


class LearningEventService:
    """Unified learning event sink for online + continuous learning loops."""

    EVENT_PREFIX = "learning:event:"
    EVENT_INDEX_KEY = "learning:event:index"
    EVENT_DEDUP_PREFIX = "learning:event:dedup:"

    def __init__(self, redis_client=None):
        self.redis = redis_client or cache_service.redis

    async def emit(
        self,
        *,
        event_type: str,
        user_id: str = "",
        session_id: str = "",
        workflow_id: str = "",
        trace_id: str = "",
        policy_id: str = "",
        strategy_pack: str = "",
        cohort_id: str = "",
        user_scope: str = "",
        complexity_tier: str = "",
        task_type: str = "",
        response_id: str = "",
        data: dict[str, Any] | None = None,
        event_time: datetime | None = None,
    ) -> dict[str, Any]:
        if not getattr(settings, "ENABLE_LEARNING_CONTROL_PLANE", False):
            return {}

        if event_type not in LEARNING_EVENT_TYPES:
            # Keep sink strict to avoid cardinality explosion from ad-hoc events.
            return {}
        dedup_data = data if isinstance(data, dict) else {}
        if await self._is_duplicate_event(
            event_type=event_type,
            trace_id=str(trace_id or dedup_data.get("trace_id") or ""),
            response_id=str(response_id or dedup_data.get("response_id") or ""),
        ):
            return {}

        now = event_time or _utcnow()
        payload = self._build_payload(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            workflow_id=workflow_id,
            trace_id=trace_id,
            policy_id=policy_id,
            strategy_pack=strategy_pack,
            cohort_id=cohort_id,
            user_scope=user_scope,
            complexity_tier=complexity_tier,
            task_type=task_type,
            response_id=response_id,
            data=dedup_data,
            timestamp=now.isoformat(),
        )

        ttl_days = int(getattr(settings, "LEARNING_RAW_EVENT_TTL_DAYS", 30))
        ttl_seconds = max(1, ttl_days * 24 * 3600)
        await self._write_payload(payload, ttl_seconds=ttl_seconds)
        return payload

    async def list_events_since(
        self,
        *,
        since: datetime,
        limit: int = 5000,
        event_types: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        if self.redis is None:
            events = [
                item for item in _MEM_EVENTS
                if datetime.fromisoformat(item["timestamp"]) >= since
            ]
            if event_types:
                events = [item for item in events if item.get("event_type") in event_types]
            events.sort(key=lambda item: item.get("timestamp", ""))
            return events[-limit:]

        min_score = since.timestamp()
        raw_keys = await self.redis.zrangebyscore(
            self.EVENT_INDEX_KEY,
            min=min_score,
            max="+inf",
            start=0,
            num=max(1, limit),
        )
        events: list[dict[str, Any]] = []
        for key in raw_keys:
            raw = await self.redis.get(key)
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event_types and payload.get("event_type") not in event_types:
                continue
            events.append(payload)
        events.sort(key=lambda item: item.get("timestamp", ""))
        return events[-limit:]

    def _build_payload(
        self,
        *,
        event_type: str,
        user_id: str,
        session_id: str,
        workflow_id: str,
        trace_id: str,
        policy_id: str,
        strategy_pack: str,
        cohort_id: str,
        user_scope: str,
        complexity_tier: str,
        task_type: str,
        response_id: str,
        data: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        normalized_policy_id = str(policy_id or data.get("policy_id") or "")
        if not strategy_pack:
            strategy_pack = self._infer_strategy_pack(normalized_policy_id)

        normalized_data = self._sanitize_data(data)
        normalized_data.setdefault("policy_id", normalized_policy_id)
        normalized_data.setdefault("strategy_pack", strategy_pack)
        normalized_data.setdefault("complexity_tier", str(complexity_tier or data.get("complexity_tier") or ""))
        normalized_data.setdefault("task_type", str(task_type or data.get("task_type") or ""))
        normalized_data.setdefault("workflow_id", str(workflow_id or data.get("workflow_id") or ""))
        normalized_data.setdefault("trace_id", str(trace_id or data.get("trace_id") or ""))
        normalized_data.setdefault("response_id", str(response_id or data.get("response_id") or ""))
        normalized_data.setdefault("cohort_id", str(cohort_id or data.get("cohort_id") or ""))
        normalized_data.setdefault("user_scope", str(user_scope or data.get("user_scope") or ""))
        sample_validity = self._sample_validity(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            workflow_id=workflow_id or str(normalized_data.get("workflow_id", "")),
            trace_id=trace_id or str(normalized_data.get("trace_id", "")),
            data=normalized_data,
        )
        normalized_data.setdefault("sample_validity", sample_validity)

        return {
            "event_id": f"le_{uuid.uuid4().hex}",
            "timestamp": timestamp,
            "event_type": event_type,
            "user_id": str(user_id or ""),
            "session_id": str(session_id or ""),
            "workflow_id": str(workflow_id or normalized_data.get("workflow_id", "")),
            "trace_id": str(trace_id or normalized_data.get("trace_id", "")),
            "policy_id": normalized_policy_id,
            "strategy_pack": strategy_pack,
            "cohort_id": str(cohort_id or normalized_data.get("cohort_id", "")),
            "user_scope": str(user_scope or normalized_data.get("user_scope", "")),
            "complexity_tier": str(complexity_tier or normalized_data.get("complexity_tier", "")),
            "task_type": str(task_type or normalized_data.get("task_type", "")),
            "sample_validity": sample_validity,
            "data": normalized_data,
        }

    async def _write_payload(self, payload: dict[str, Any], *, ttl_seconds: int) -> None:
        if self.redis is None:
            _MEM_EVENTS.append(payload)
            if len(_MEM_EVENTS) > 50000:
                del _MEM_EVENTS[: len(_MEM_EVENTS) - 50000]
            return

        key = f"{self.EVENT_PREFIX}{payload['event_id']}"
        score = _event_timestamp_to_score(payload["timestamp"])
        try:
            await self.redis.setex(key, ttl_seconds, json.dumps(payload, ensure_ascii=False))
            await self.redis.zadd(self.EVENT_INDEX_KEY, {key: score})
            # Keep the zset index size bounded by time window.
            await self.redis.zremrangebyscore(self.EVENT_INDEX_KEY, "-inf", score - ttl_seconds)
        except Exception as exc:
            logger.warning("Failed writing learning event: {}", exc)

    async def _is_duplicate_event(
        self,
        *,
        event_type: str,
        trace_id: str,
        response_id: str,
    ) -> bool:
        if event_type not in {"prompt_applied", "toolchain_selected", "plan_execution_outcome"}:
            return False
        normalized_trace = str(trace_id or "").strip()
        normalized_response = str(response_id or "").strip()
        if not normalized_trace or not normalized_response:
            return False
        dedup_key = f"{self.EVENT_DEDUP_PREFIX}{event_type}:{normalized_trace}:{normalized_response}"
        if self.redis is None:
            if dedup_key in _MEM_EVENT_DEDUP:
                return True
            _MEM_EVENT_DEDUP.add(dedup_key)
            if len(_MEM_EVENT_DEDUP) > 80000:
                _MEM_EVENT_DEDUP.clear()
            return False
        try:
            created = await self.redis.set(dedup_key, "1", nx=True, ex=86400)
            return not bool(created)
        except Exception as exc:
            logger.warning("Learning event dedup check failed: {}", exc)
            return False

    @staticmethod
    def _infer_strategy_pack(policy_id: str) -> str:
        if ":" in policy_id:
            rest = policy_id.split(":", 1)[1]
            if ":candidate_" in rest:
                return rest.split(":candidate_", 1)[0]
            if ":" in rest:
                return rest.split(":", 1)[0]
            return rest
        return "default"

    @staticmethod
    def _sanitize_data(data: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            lower_key = str(key).lower()
            if any(token in lower_key for token in ("message", "prompt", "query", "content", "full_text", "raw_text")):
                if isinstance(value, str):
                    digest = hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:16]
                    sanitized[f"{key}_sha1"] = digest
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[str(key)] = value
                continue
            if isinstance(value, list):
                sanitized[str(key)] = [str(item) for item in value[:10]]
                continue
            if isinstance(value, dict):
                compact: dict[str, str] = {}
                for nested_key, nested_val in list(value.items())[:20]:
                    compact[str(nested_key)] = str(nested_val)[:120]
                sanitized[str(key)] = compact
                continue
            sanitized[str(key)] = str(value)
        return sanitized

    @staticmethod
    def _sample_validity(
        *,
        event_type: str,
        user_id: str,
        session_id: str,
        workflow_id: str,
        trace_id: str,
        data: dict[str, Any],
    ) -> str:
        if bool(data.get("is_test")):
            return "invalid_test_traffic"
        if str(workflow_id).startswith("test") or str(workflow_id).startswith("debug"):
            return "invalid_test_workflow"
        if event_type in {
            "route_decision",
            "prompt_applied",
            "toolchain_selected",
            "plan_execution_outcome",
            "response_feedback",
        } and not trace_id:
            return "invalid_missing_trace"
        if not user_id and not session_id and event_type in {"response_feedback", "user_feedback_bound", "prompt_applied"}:
            return "invalid_missing_actor"
        return "valid"
