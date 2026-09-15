from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from app.signals.causal_trace_store import CausalTraceStore


class RecentDirectiveAuditService:
    """Builds user-visible audit rows from CausalTrace directive records."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.trace_store = CausalTraceStore(redis_client)

    async def list_recent_directives(
        self,
        *,
        user_id: str,
        limit: int = 20,
        directive_type: str | None = None,
        hours: int | None = None,
    ) -> list[dict[str, Any]]:
        traces = await self.trace_store.get_user_traces(user_id, limit=max(limit * 3, limit))
        cutoff = datetime.now(UTC) - timedelta(hours=hours) if hours else None

        entries: list[dict[str, Any]] = []
        for trace in traces:
            signal = await self._first_signal(trace.signal_ids)
            policy = await self._policy(trace.policy_decision_id)
            audits = await self._audits(trace.audit_ids)

            for directive_id in trace.directive_ids:
                directive = await self._json_get(f"spine:directive_by_id:{directive_id}")
                if not directive:
                    continue
                inferred_type = self._infer_directive_type(directive)
                display_type = self._display_type(directive, inferred_type)
                if directive_type and directive_type not in {inferred_type, display_type}:
                    continue

                created_at = str(directive.get("created_at") or trace.created_at)
                if cutoff and self._parse_time(created_at) < cutoff:
                    continue

                audit = next(
                    (item for item in audits if item.get("directive_id") == directive_id),
                    None,
                )

                entries.append(
                    {
                        "trace_id": trace.trace_id,
                        "directive_id": directive_id,
                        "directive_type": inferred_type,
                        "display_type": display_type,
                        "created_at": created_at,
                        "target_module": directive.get("target_module", ""),
                        "scope": directive.get("scope", ""),
                        "user_visible_reason": self._reason_for_user(directive),
                        "trigger_signal": self._signal_summary(signal),
                        "policy": self._policy_summary(policy),
                        "actual_result": self._audit_summary(audit),
                        "raw_directive": directive,
                    }
                )
                if len(entries) >= limit:
                    return entries

        return entries

    async def _first_signal(self, signal_ids: list[str]) -> dict[str, Any] | None:
        if not signal_ids:
            return None
        return await self._json_get(f"spine:signal:{signal_ids[0]}")

    async def _policy(self, policy_id: str | None) -> dict[str, Any] | None:
        if not policy_id:
            return None
        return await self._json_get(f"spine:policy:{policy_id}")

    async def _audits(self, audit_ids: list[str]) -> list[dict[str, Any]]:
        audits: list[dict[str, Any]] = []
        for audit_id in audit_ids:
            audit = await self._json_get(f"spine:audit_by_id:{audit_id}")
            if audit:
                audits.append(audit)
        return audits

    async def _json_get(self, key: str) -> dict[str, Any] | None:
        raw = await self.redis.get(key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _infer_directive_type(directive: dict[str, Any]) -> str:
        if "allowed" in directive and "message_strategy" in directive:
            return "NotificationDirective"
        if "retrieval_mode" in directive:
            return "RetrievalDirective"
        if "plan_action" in directive:
            return "PlanDirective"
        if "writes" in directive:
            return "ModelWriteDirective"
        if "status_band_state" in directive:
            return "UXDirective"
        if "cohort_hint_shown" in directive or "resource_quality_filter" in directive:
            return "CommunityDirective"
        if "skill_action" in directive:
            return "SkillDirective"
        if "tone" in directive and "must_acknowledge" in directive:
            return "ResponseDirective"
        return "ExecutionDirective"

    @staticmethod
    def _display_type(directive: dict[str, Any], directive_type: str) -> str:
        if directive_type == "NotificationDirective":
            if not directive.get("allowed", True) or directive.get("channel") == "silent":
                return "SkipReminder"
            return "NotifyUser"
        if directive_type == "ExecutionDirective":
            constraints = directive.get("hard_constraints") or {}
            if "max_task_duration_min" in constraints or constraints.get("required_task_type"):
                return "DowngradeIntensity"
            return "AdjustExecution"
        if directive_type == "PlanDirective":
            return "ReplanLocally"
        if directive_type == "RetrievalDirective":
            return "ConstrainRetrieval"
        if directive_type == "UXDirective":
            return "ShowStatusBand"
        if directive_type == "ModelWriteDirective":
            return "WriteModelClaim"
        if directive_type == "CommunityDirective":
            return "UseCommunitySignal"
        if directive_type == "SkillDirective":
            return "UseLearningSkill"
        if directive_type == "ResponseDirective":
            return "ShapeResponse"
        return directive_type

    @staticmethod
    def _reason_for_user(directive: dict[str, Any]) -> str:
        return str(
            directive.get("user_visible_reason")
            or directive.get("reason_for_user")
            or directive.get("trigger")
            or directive.get("plan_action")
            or directive.get("status_band_state")
            or ""
        )

    @staticmethod
    def _signal_summary(signal: dict[str, Any] | None) -> dict[str, Any] | None:
        if not signal:
            return None
        return {
            "signal_id": signal.get("signal_id"),
            "state_key": signal.get("state_key"),
            "claim": signal.get("claim") or signal.get("description") or signal.get("reason"),
            "confidence": signal.get("confidence"),
        }

    @staticmethod
    def _policy_summary(policy: dict[str, Any] | None) -> dict[str, Any] | None:
        if not policy:
            return None
        return {
            "policy_decision_id": policy.get("policy_decision_id"),
            "primary_strategy": policy.get("primary_strategy"),
            "secondary_strategy": policy.get("secondary_strategy"),
            "risk_level": policy.get("risk_level"),
            "reasoning_summary": policy.get("reasoning_summary"),
        }

    @staticmethod
    def _audit_summary(audit: dict[str, Any] | None) -> dict[str, Any] | None:
        if not audit:
            return None
        return {
            "audit_id": audit.get("audit_id"),
            "applied": audit.get("applied"),
            "applied_constraints": audit.get("applied_constraints") or [],
            "violations": audit.get("violations") or [],
            "generated_output_id": audit.get("generated_output_id"),
            "generated_output_summary": audit.get("generated_output_summary") or {},
        }

    @staticmethod
    def _parse_time(value: str) -> datetime:
        try:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return datetime.min.replace(tzinfo=UTC)
