"""Close the loop between DualCore routing decisions and SGW outcomes."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.metrics import AURORA_ROUTING_OUTCOME_TOTAL, AURORA_ROUTING_SIGNAL_TOTAL
from app.models.base import _utcnow
from app.models.intervention import InterventionRequest
from app.models.intervention_adaptive import BehavioralOutcome, PassiveSignal
from app.scaffolding.scaffolding_fsm import ScaffoldingFSM


class RoutingOutcomeRecorder:
    """Persist every DualCore routing decision as a passive signal.

    The record gives Aurora/SGW a durable handle for later evaluation. This
    prevents DualCore from being only a prompt-time adjustment with no outcome
    memory.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        *,
        user_id: UUID,
        decision: dict[str, Any],
        route_execution_mode: str,
        source_state_key: str | None = None,
        request_id: str | None = None,
        session_id: str | None = None,
    ) -> PassiveSignal:
        intervention = InterventionRequest(
            user_id=user_id,
            dedupe_key=f"routing:{decision.get('routing_trace_id') or request_id or _utcnow().timestamp()}",
            topic="dual_core_routing",
            requested_level="L1",
            final_level="L1",
            status="recorded",
            reason={
                "type": "dual_core_routing",
                "mode": decision.get("mode"),
                "dominant_signal": (decision.get("routing_debug") or {}).get("dominant_signal"),
            },
            content={
                "routing_trace_id": decision.get("routing_trace_id"),
                "route_execution_mode": route_execution_mode,
                "request_id": request_id,
                "session_id": session_id,
            },
            schema_version="routing_outcome.v1",
            policy_version="aurora_sgw_closed_loop.v1",
            model_version="dual_core_router",
            intent_type=str(decision.get("mode") or "balanced"),
        )
        self.db.add(intervention)
        await self.db.flush()

        context = {
            "routing_trace_id": decision.get("routing_trace_id"),
            "routing_mode": decision.get("mode"),
            "route_execution_mode": route_execution_mode,
            "reason": decision.get("reason"),
            "signal_scores": decision.get("signal_scores") or {},
            "scaffolding_zone": decision.get("scaffolding_zone"),
            "cognitive_adjustments_count": len(decision.get("cognitive_adjustments") or []),
            "execution_constraints_count": len(decision.get("execution_constraints") or []),
            "dominant_signal": (decision.get("routing_debug") or {}).get("dominant_signal"),
            "source_state_key": source_state_key,
            "request_id": request_id,
            "session_id": session_id,
            "evaluation_due_at": (_utcnow() + timedelta(hours=48)).isoformat(),
            "outcome_recorded": False,
        }
        signal = PassiveSignal(
            user_id=user_id,
            signal_type="routing_decision",
            intervention_id=intervention.id,
            context=context,
        )
        self.db.add(signal)
        await self.db.commit()
        await self.db.refresh(signal)
        AURORA_ROUTING_SIGNAL_TOTAL.labels(
            mode=str(decision.get("mode") or "unknown"),
            dominant_signal=str(context.get("dominant_signal") or "unknown"),
        ).inc()
        return signal


class RoutingOutcomeEvaluator:
    """Evaluate delayed routing effectiveness and feed SGW support back."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate_due(self, *, limit: int = 100) -> int:
        now = _utcnow()
        result = await self.db.execute(
            select(PassiveSignal)
            .where(PassiveSignal.signal_type == "routing_decision")
            .order_by(PassiveSignal.timestamp.asc())
            .limit(limit)
        )
        evaluated = 0
        for signal in result.scalars().all():
            context = dict(signal.context or {})
            if context.get("outcome_recorded") is True:
                continue
            due_at = str(context.get("evaluation_due_at") or "")
            if due_at:
                try:
                    if datetime.fromisoformat(due_at) > now:
                        continue
                except ValueError:
                    pass
            if signal.intervention_id is None:
                continue
            try:
                success, reason, weight = self._judge_success(context)
                outcome = BehavioralOutcome(
                    user_id=signal.user_id,
                    intervention_id=signal.intervention_id,
                    outcome_type="routing_effectiveness",
                    time_to_outcome=max(0, int((now - signal.timestamp).total_seconds())),
                    success=success,
                    context={**context, "verdict_reason": reason},
                    timestamp=now,
                )
                self.db.add(outcome)
                await ScaffoldingFSM(self.db).apply_feedback(
                    signal.user_id,
                    success=success,
                    feedback=reason,
                    weight=weight,
                )
                context["outcome_recorded"] = True
                context["outcome_success"] = success
                context["outcome_reason"] = reason
                signal.context = context
                flag_modified(signal, "context")
                evaluated += 1
                AURORA_ROUTING_OUTCOME_TOTAL.labels(
                    mode=str(context.get("routing_mode") or "unknown"),
                    success="true" if success else "false",
                    reason=reason,
                ).inc()
            except Exception as exc:
                logger.warning("Routing outcome evaluation failed for signal {}: {}", signal.id, exc)
        if evaluated:
            await self.db.commit()
        return evaluated

    @staticmethod
    def _judge_success(context: dict[str, Any]) -> tuple[bool, str, float]:
        scores = context.get("signal_scores") if isinstance(context.get("signal_scores"), dict) else {}
        routing_mode = str(context.get("routing_mode") or "balanced")
        if float(scores.get("recent_corrections") or 0.0) >= 0.6:
            return False, "recent_corrections_after_routing", 1.25
        if routing_mode == "cognitive_first" and float(scores.get("emotional_block") or 0.0) >= 0.55:
            return True, "cognitive_first_matched_emotional_block", 1.1
        if routing_mode == "execution_first" and float(scores.get("goal_clarity") or 0.0) >= 0.75:
            return True, "execution_first_matched_goal_clarity", 1.0
        if str(context.get("scaffolding_zone") or "") == "frustration":
            return routing_mode != "execution_first", "frustration_zone_requires_support", 1.2
        return True, "no_negative_followup_signal", 0.8
