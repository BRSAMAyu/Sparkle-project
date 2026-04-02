"""
PlanHealthSignalService — Converts plan health evaluations into controlled, deduplicated events.

This is断点3: 把已有的 warning/critical/adjust/replan 变成一个受控、可消费、不重复骚扰用户的事件源。

Design principles:
  - Events emit from _handle_report(), not from evaluate_progress() (which is also a read model)
  - Every event carries action_taken, not just "you have a problem"
  - Dedup by signature + cooldown; severity upgrade always re-emits
  - When action_taken is "incremental_adjustment_applied" or "full_replan_triggered",
    consumer skips generating a second visible user update (断点1 already does that)

See: docs/product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md (breakpoint 3)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from loguru import logger

from app.core.event_bus import event_bus
from app.core.event_types import PLAN_HEALTH_ALERTED


# ---------------------------------------------------------------------------
# Cooldown durations (seconds)
# ---------------------------------------------------------------------------

COOLDOWNS: dict[str, int] = {
    "warning": 2 * 3600,   # 2 hours
    "critical": 12 * 3600, # 12 hours (same as AUTO_REPLAN_COOLDOWN)
}


class PlanHealthSignalService:
    """Generates stable, deduplicated plan health events."""

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def maybe_publish(
        self,
        *,
        report: Any,  # PlanHealthReport
        trigger: str,
        task_id: UUID | None = None,
        feedback_category: str | None = None,
        action_taken: str = "none",
        adaptation_records: list | None = None,
        existing_facts: dict | None = None,
    ) -> bool:
        """Evaluate whether to emit a plan.health.alerted event, then emit if allowed.

        Returns True if event was emitted, False otherwise.
        """
        facts = existing_facts or {}

        # Only emit for reports that require adjustment
        severity = getattr(report, "severity", "healthy")
        if severity == "healthy" or not getattr(report, "requires_adjustment", False):
            return False

        signature = self._build_signature(report)
        last_meta = self._get_last_signal_meta(facts)

        if not self._should_emit(last_meta, signature, severity):
            return False

        payload = self._build_payload(
            report=report,
            trigger=trigger,
            task_id=task_id,
            feedback_category=feedback_category,
            action_taken=action_taken,
            adaptation_records=adaptation_records,
            signature=signature,
        )

        # Publish event
        try:
            await event_bus.publish(PLAN_HEALTH_ALERTED, payload)
            logger.info(
                "PlanHealthSignal: emitted {} for user={}, plan={}, action={}",
                severity,
                payload.get("user_id"),
                payload.get("plan_id"),
                action_taken,
            )
        except Exception as exc:
            logger.warning("PlanHealthSignal: publish failed: {}", exc)
            return False

        # Persist signal meta for future dedup
        await self._persist_signal_meta(
            user_id=report.user_id,
            plan_id=report.plan_id,
            signature=signature,
            severity=severity,
            action_taken=action_taken,
            facts=facts,
        )

        return True

    # ------------------------------------------------------------------
    # Signature & dedup
    # ------------------------------------------------------------------

    def _build_signature(self, report: Any) -> str:
        """Build a stable signature: severity|recommended_action|sorted(reasons)."""
        severity = getattr(report, "severity", "unknown")
        action = getattr(report, "recommended_action", "none")
        reasons = sorted(getattr(report, "reasons", []))
        return f"{severity}|{action}|{','.join(reasons)}"

    def _get_last_signal_meta(self, facts: dict) -> dict:
        """Read last signal metadata from PlanState.facts.adaptive_meta.plan_health_signal."""
        adaptive_meta = facts.get("adaptive_meta", {})
        return adaptive_meta.get("plan_health_signal", {})

    def _cooldown_for(self, severity: str) -> int:
        """Return cooldown in seconds for a given severity."""
        return COOLDOWNS.get(severity, COOLDOWNS["warning"])

    def _should_emit(self, last_meta: dict, signature: str, severity: str) -> bool:
        """Decide whether to emit based on dedup and severity upgrade rules.

        Rules:
          - Same signature within cooldown → suppress
          - Severity upgrade (warning → critical) → always emit
          - No previous signal → emit
        """
        if not last_meta:
            return True

        last_signature = last_meta.get("signature", "")
        last_severity = last_meta.get("severity", "")
        last_emitted_at = last_meta.get("emitted_at", "")

        # Severity upgrade: always re-emit
        severity_order = {"healthy": 0, "warning": 1, "critical": 2}
        if severity_order.get(severity, 0) > severity_order.get(last_severity, 0):
            return True

        # Same or lower severity: check cooldown by signature
        if last_signature == signature and last_emitted_at:
            try:
                last_dt = datetime.fromisoformat(last_emitted_at)
                if last_dt.tzinfo is not None:
                    last_dt = last_dt.replace(tzinfo=None)
                now = datetime.utcnow()
                elapsed = (now - last_dt).total_seconds()
                cooldown = self._cooldown_for(severity)
                if elapsed < cooldown:
                    return False
            except (ValueError, TypeError):
                pass  # Corrupt timestamp → allow re-emit

        return True

    # ------------------------------------------------------------------
    # Payload
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        *,
        report: Any,
        trigger: str,
        task_id: UUID | None,
        feedback_category: str | None,
        action_taken: str,
        adaptation_records: list | None,
        signature: str,
    ) -> dict[str, Any]:
        """Build the event payload."""
        return {
            "event_type": PLAN_HEALTH_ALERTED,
            "user_id": str(report.user_id),
            "plan_id": str(report.plan_id),
            "severity": getattr(report, "severity", "unknown"),
            "recommended_action": getattr(report, "recommended_action", "none"),
            "reasons": list(getattr(report, "reasons", [])),
            "metrics": dict(getattr(report, "metrics", {})),
            "trigger": trigger,
            "task_id": str(task_id) if task_id else None,
            "feedback_category": feedback_category,
            "action_taken": action_taken,
            "adaptation_count": len(adaptation_records) if adaptation_records else 0,
            "signature": signature,
            "emitted_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _persist_signal_meta(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        signature: str,
        severity: str,
        action_taken: str,
        facts: dict,
    ) -> None:
        """Write signal metadata back to PlanState.facts.adaptive_meta.plan_health_signal.

        plan_state_service.upsert_plan_state does shallow merge on facts,
        so we must read → merge → write back the whole adaptive_meta.
        """
        try:
            from app.services.plan_state_service import PlanStateService

            ps = PlanStateService(self.db, self.redis)
            state = await ps.get_plan_state(user_id, plan_id)
            if not state:
                return

            # Read current adaptive_meta, merge signal meta in
            current_facts = state.facts or {}
            adaptive_meta = dict(current_facts.get("adaptive_meta", {}))
            adaptive_meta["plan_health_signal"] = {
                "signature": signature,
                "severity": severity,
                "action_taken": action_taken,
                "emitted_at": datetime.now(timezone.utc).isoformat(),
            }

            await ps.upsert_plan_state(
                user_id=user_id,
                plan_id=plan_id,
                patch={"facts": {"adaptive_meta": adaptive_meta}},
            )
        except Exception as exc:
            logger.warning("PlanHealthSignal: persist meta failed: {}", exc)
