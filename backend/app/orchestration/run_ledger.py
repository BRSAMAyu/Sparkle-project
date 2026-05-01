from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.config import settings
from app.core.metrics import (
    RUN_LEDGER_EVENT_TOTAL,
    RUN_LEDGER_FEEDBACK_EFFECT_TOTAL,
    RUN_LEDGER_REVIEW_SCORE,
)


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


def _safe_json_loads(raw: str | bytes | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


class RunLedgerStore:
    """Redis-backed store for unified control-tower run ledgers."""

    SUMMARY_PREFIX = "run_ledger:summary:"
    EVENTS_PREFIX = "run_ledger:events:"
    SESSION_PREFIX = "run_ledger:session:"
    RESPONSE_PREFIX = "run_ledger:response:"

    @classmethod
    def summary_key(cls, trace_id: str) -> str:
        return f"{cls.SUMMARY_PREFIX}{trace_id}"

    @classmethod
    def events_key(cls, trace_id: str) -> str:
        return f"{cls.EVENTS_PREFIX}{trace_id}"

    @classmethod
    def session_key(cls, session_id: str) -> str:
        return f"{cls.SESSION_PREFIX}{session_id}"

    @classmethod
    def response_key(cls, response_id: str) -> str:
        return f"{cls.RESPONSE_PREFIX}{response_id}"

    @classmethod
    def build_empty_summary(
        cls,
        *,
        trace_id: str,
        session_id: str = "",
        workflow_id: str = "",
        response_id: str = "",
        prompt_version: str = "",
        request_id: str = "",
    ) -> dict[str, Any]:
        return {
            "trace_id": trace_id,
            "session_id": session_id,
            "workflow_id": workflow_id,
            "response_id": response_id,
            "prompt_version": prompt_version,
            "request_id": request_id,
            "status": "running",
            "created_at": _utcnow_iso(),
            "updated_at": _utcnow_iso(),
            "event_count": 0,
            "timeline": [],
            "route": {},
            "models": [],
            "agents": [],
            "quality": {
                "reviewed": False,
                "review_score": None,
                "review_decision": "",
                "reviewer_model_key": "",
                "reviewer_provider": "",
                "review_profile_id": "",
                "reflection_triggered": False,
                "reflection_completed": False,
                "reflection_rounds": 0,
                "reflection_delta": 0.0,
                "reflection_model_key": "",
                "reflection_provider": "",
                "reflection_profile_id": "",
                "reflection_early_stop_reason": "",
                "reflection_best_round_number": 0,
                "tool_review_issue_count": 0,
            },
            "evidence": {
                "context_pack_id": "",
                "focus_mode": "",
                "context_briefing_note": "",
                "preferences": 0,
                "goals": 0,
                "episodic": 0,
                "evidence_score_avg": None,
            },
            "response": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "finish_reason": "",
                "fallback_used": False,
            },
            "feedback": {
                "received": False,
                "feedback_type": "",
                "reasons": [],
                "strategy_effects": [],
                "effect_latency_seconds": None,
            },
            "semantic_control": {
                "selected_terms": [],
                "rendered_doctrine_summary": {},
                "response_contract": {},
                "compliance_expectations": {},
                "observed_compliance_flags": {},
            },
        }

    @classmethod
    async def load_summary(cls, redis_client, trace_id: str) -> dict[str, Any] | None:
        if not redis_client or not trace_id:
            return None
        raw = await redis_client.get(cls.summary_key(trace_id))
        summary = _safe_json_loads(raw, None)
        return summary if isinstance(summary, dict) else None

    @classmethod
    async def load_events(cls, redis_client, trace_id: str) -> list[dict[str, Any]]:
        if not redis_client or not trace_id:
            return []
        if not hasattr(redis_client, "lrange"):
            return []
        raw_items = await redis_client.lrange(cls.events_key(trace_id), 0, -1)
        events: list[dict[str, Any]] = []
        for raw in raw_items or []:
            item = _safe_json_loads(raw, None)
            if isinstance(item, dict):
                events.append(item)
        return events

    @classmethod
    async def get_trace_id_for_response(cls, redis_client, response_id: str) -> str | None:
        if not redis_client or not response_id:
            return None
        raw = await redis_client.get(cls.response_key(response_id))
        if not raw:
            return None
        return str(raw)

    @classmethod
    def apply_event(cls, summary: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        updated = deepcopy(summary or {})
        updated.setdefault("timeline", [])
        updated.setdefault("models", [])
        updated.setdefault("agents", [])
        updated.setdefault("quality", {})
        updated.setdefault("evidence", {})
        updated.setdefault("response", {})
        updated.setdefault("feedback", {})
        updated.setdefault("semantic_control", {})
        updated["updated_at"] = event.get("timestamp") or _utcnow_iso()
        updated["event_count"] = int(updated.get("event_count") or 0) + 1

        timeline = list(updated.get("timeline") or [])
        timeline.append(
            {
                "event_type": event.get("event_type", ""),
                "label": event.get("label", ""),
                "workflow_stage": event.get("workflow_stage", ""),
                "timestamp": event.get("timestamp", ""),
                "status": event.get("status", ""),
            }
        )
        updated["timeline"] = timeline[-12:]

        event_type = str(event.get("event_type") or "").strip().lower()
        metadata = event.get("metadata") or {}

        if event_type == "route_selected":
            updated["route"] = {
                **dict(updated.get("route") or {}),
                **dict(metadata or {}),
            }
        elif event_type in {"generation_started", "generation_completed", "review_completed", "reflection_completed"}:
            role = str(metadata.get("role") or "").strip() or event_type.replace("_completed", "").replace("_started", "")
            updated["models"] = cls._upsert_model(updated.get("models") or [], role=role, metadata=metadata)
            if event_type == "review_completed":
                quality = dict(updated.get("quality") or {})
                quality.update(
                    {
                        "reviewed": True,
                        "review_score": metadata.get("overall_score"),
                        "review_decision": metadata.get("decision") or "",
                        "reviewer_model_key": metadata.get("model_key") or "",
                        "reviewer_provider": metadata.get("provider") or "",
                        "review_profile_id": metadata.get("review_profile_id") or "",
                    }
                )
                updated["quality"] = quality
            elif event_type == "reflection_completed":
                quality = dict(updated.get("quality") or {})
                quality.update(
                    {
                        "reflection_triggered": True,
                        "reflection_completed": bool(metadata.get("success")),
                        "reflection_rounds": int(metadata.get("rounds") or 0),
                        "reflection_delta": float(metadata.get("score_delta") or 0.0),
                        "reflection_model_key": metadata.get("model_key") or "",
                        "reflection_provider": metadata.get("provider") or "",
                        "reflection_profile_id": metadata.get("review_profile_id") or "",
                        "reflection_early_stop_reason": metadata.get("early_stop_reason") or "",
                        "reflection_best_round_number": int(metadata.get("best_round_number") or 0),
                    }
                )
                updated["quality"] = quality
        elif event_type in {"agent_started", "agent_completed"}:
            updated["agents"] = cls._upsert_agent(updated.get("agents") or [], metadata=metadata, status=event.get("status") or "")
        elif event_type in {"context_pack_built", "evidence_attached"}:
            evidence = dict(updated.get("evidence") or {})
            evidence.update({k: v for k, v in dict(metadata or {}).items() if v not in (None, "")})
            updated["evidence"] = evidence
        elif event_type == "semantic_control_attached":
            semantic_control = dict(updated.get("semantic_control") or {})
            semantic_control.update({k: v for k, v in dict(metadata or {}).items() if v not in (None, "")})
            updated["semantic_control"] = semantic_control
        elif event_type == "tool_reviewed":
            quality = dict(updated.get("quality") or {})
            quality["tool_review_issue_count"] = int(metadata.get("issue_count") or 0)
            updated["quality"] = quality
        elif event_type == "response_streamed":
            response = dict(updated.get("response") or {})
            response.update({k: v for k, v in dict(metadata or {}).items() if v is not None})
            updated["response"] = response
            updated["status"] = "completed"
        elif event_type == "feedback_received":
            feedback = dict(updated.get("feedback") or {})
            feedback.update(
                {
                    "received": True,
                    "feedback_type": metadata.get("feedback_type") or "",
                    "reasons": list(metadata.get("reasons") or []),
                }
            )
            updated["feedback"] = feedback
        elif event_type == "strategy_effect_applied":
            feedback = dict(updated.get("feedback") or {})
            effects = list(feedback.get("strategy_effects") or [])
            effects.append(
                {
                    "target": metadata.get("effect_target") or "",
                    "status": metadata.get("status") or "",
                    "detail": metadata.get("detail") or "",
                }
            )
            feedback["strategy_effects"] = effects[-10:]
            if metadata.get("effect_latency_seconds") is not None:
                feedback["effect_latency_seconds"] = metadata.get("effect_latency_seconds")
            updated["feedback"] = feedback

        return updated

    @classmethod
    def _upsert_model(cls, models: list[dict[str, Any]], *, role: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        next_models = [dict(item) for item in models]
        payload = {
            "role": role,
            "model_key": metadata.get("model_key") or "",
            "provider": metadata.get("provider") or "",
            "tier": metadata.get("tier") or "",
            "estimated_cost_per_1k": metadata.get("estimated_cost_per_1k"),
            "is_fallback": bool(metadata.get("is_fallback")),
        }
        for index, item in enumerate(next_models):
            if str(item.get("role") or "") == role:
                next_models[index] = {**item, **payload}
                break
        else:
            next_models.append(payload)
        return next_models

    @classmethod
    def _upsert_agent(cls, agents: list[dict[str, Any]], *, metadata: dict[str, Any], status: str) -> list[dict[str, Any]]:
        next_agents = [dict(item) for item in agents]
        agent_id = str(metadata.get("agent_id") or "").strip()
        if not agent_id:
            return next_agents
        payload = {
            "agent_id": agent_id,
            "display_name": metadata.get("display_name") or agent_id,
            "description": metadata.get("description") or "",
            "collaboration_mode": metadata.get("collaboration_mode") or "",
            "phase": metadata.get("phase") or "",
            "status": status or metadata.get("status") or "",
        }
        for index, item in enumerate(next_agents):
            if str(item.get("agent_id") or "") == agent_id:
                next_agents[index] = {**item, **payload}
                break
        else:
            next_agents.append(payload)
        return next_agents

    @classmethod
    async def persist(
        cls,
        redis_client,
        *,
        summary: dict[str, Any],
        event: dict[str, Any],
    ) -> None:
        if not redis_client or not settings.RUN_LEDGER_ENABLED:
            return
        trace_id = str(summary.get("trace_id") or "")
        if not trace_id:
            return
        ttl = int(getattr(settings, "RUN_LEDGER_TTL_SECONDS", 86400) or 86400)
        summary_payload = json.dumps(summary, ensure_ascii=False)
        event_payload = json.dumps(event, ensure_ascii=False)
        await redis_client.setex(cls.summary_key(trace_id), ttl, summary_payload)
        if hasattr(redis_client, "rpush"):
            await redis_client.rpush(cls.events_key(trace_id), event_payload)
            if hasattr(redis_client, "expire"):
                await redis_client.expire(cls.events_key(trace_id), ttl)
        session_id = str(summary.get("session_id") or "")
        response_id = str(summary.get("response_id") or "")
        if session_id:
            await redis_client.setex(cls.session_key(session_id), ttl, trace_id)
        if response_id:
            await redis_client.setex(cls.response_key(response_id), ttl, trace_id)

    @classmethod
    async def append_external_event(
        cls,
        redis_client,
        *,
        trace_id: str,
        event_type: str,
        label: str,
        workflow_stage: str,
        metadata: dict[str, Any] | None = None,
        status: str = "completed",
    ) -> dict[str, Any] | None:
        if not redis_client or not trace_id or not settings.RUN_LEDGER_ENABLED:
            return None
        summary = await cls.load_summary(redis_client, trace_id)
        if not summary:
            summary = cls.build_empty_summary(trace_id=trace_id)
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "label": label,
            "workflow_stage": workflow_stage,
            "timestamp": _utcnow_iso(),
            "status": status,
            "metadata": dict(metadata or {}),
        }
        summary = cls.apply_event(summary, event)
        await cls.persist(redis_client, summary=summary, event=event)
        cls._record_metrics(event_type=event_type, workflow_stage=workflow_stage, metadata=metadata or {})
        return summary

    @classmethod
    def _record_metrics(cls, *, event_type: str, workflow_stage: str, metadata: dict[str, Any]) -> None:
        RUN_LEDGER_EVENT_TOTAL.labels(
            event_type=event_type or "unknown",
            workflow_stage=workflow_stage or "unknown",
        ).inc()
        if event_type == "review_completed":
            try:
                RUN_LEDGER_REVIEW_SCORE.labels(
                    target_type=str(metadata.get("target_type") or "llm_response"),
                    decision=str(metadata.get("decision") or "unknown"),
                ).observe(float(metadata.get("overall_score") or 0.0))
            except Exception:
                pass
        elif event_type == "strategy_effect_applied":
            RUN_LEDGER_FEEDBACK_EFFECT_TOTAL.labels(
                effect_target=str(metadata.get("effect_target") or "unknown"),
                status=str(metadata.get("status") or "unknown"),
            ).inc()


class RunLedgerRecorder:
    """Live recorder for a single chat run."""

    def __init__(
        self,
        *,
        trace_id: str,
        session_id: str = "",
        workflow_id: str = "",
        response_id: str = "",
        prompt_version: str = "",
        request_id: str = "",
        redis_client=None,
        stream_callback=None,
    ) -> None:
        self.trace_id = trace_id
        self.session_id = session_id
        self.workflow_id = workflow_id
        self.response_id = response_id
        self.prompt_version = prompt_version
        self.request_id = request_id
        self.redis = redis_client
        self.stream_callback = stream_callback
        self.summary = RunLedgerStore.build_empty_summary(
            trace_id=trace_id,
            session_id=session_id,
            workflow_id=workflow_id,
            response_id=response_id,
            prompt_version=prompt_version,
            request_id=request_id,
        )

    async def record_event(
        self,
        *,
        event_type: str,
        label: str,
        workflow_stage: str,
        metadata: dict[str, Any] | None = None,
        status: str = "completed",
        emit_snapshot: bool | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "label": label,
            "workflow_stage": workflow_stage,
            "timestamp": _utcnow_iso(),
            "status": status,
            "metadata": dict(metadata or {}),
        }
        self.summary = RunLedgerStore.apply_event(self.summary, event)
        await RunLedgerStore.persist(self.redis, summary=self.summary, event=event)
        RunLedgerStore._record_metrics(
            event_type=event_type,
            workflow_stage=workflow_stage,
            metadata=metadata or {},
        )
        should_emit = settings.RUN_LEDGER_STREAM_SNAPSHOTS if emit_snapshot is None else emit_snapshot
        if should_emit:
            await self.emit_snapshot(latest_event=event)
        return event

    async def emit_snapshot(self, latest_event: dict[str, Any] | None = None) -> None:
        if not self.stream_callback or not settings.RUN_LEDGER_STREAM_SNAPSHOTS:
            return
        try:
            from app.gen.agent.v1 import agent_service_pb2

            await self.stream_callback(
                agent_service_pb2.ChatResponse(
                    metadata={
                        "event_type": "run_ledger",
                        "payload": json.dumps(
                            {
                                "summary": self.summary,
                                "latest_event": latest_event,
                            },
                            ensure_ascii=False,
                        ),
                    }
                )
            )
        except Exception as exc:
            logger.debug(f"Failed to emit run ledger snapshot: {exc}")

    def to_metadata_payload(self) -> str:
        return json.dumps(self.summary, ensure_ascii=False)

    @classmethod
    async def restore(
        cls,
        redis_client,
        *,
        trace_id: str,
        stream_callback=None,
    ) -> RunLedgerRecorder | None:
        if not redis_client or not trace_id:
            return None
        summary = await RunLedgerStore.load_summary(redis_client, trace_id)
        if not summary:
            return None
        recorder = cls(
            trace_id=trace_id,
            session_id=str(summary.get("session_id") or ""),
            workflow_id=str(summary.get("workflow_id") or ""),
            response_id=str(summary.get("response_id") or ""),
            prompt_version=str(summary.get("prompt_version") or ""),
            request_id=str(summary.get("request_id") or ""),
            redis_client=redis_client,
            stream_callback=stream_callback,
        )
        recorder.summary = summary
        return recorder
