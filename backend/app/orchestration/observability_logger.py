"""
Observability Logger - Phase 3

Responsibilities:
1. Unified observability logging interface
2. Structured log output
3. Event tracking
4. Prometheus metrics integration
"""
import json
from typing import Any

from loguru import logger

from app.config import settings
from app.orchestration.schemas import ObservabilityEvent


class ObservabilityLogger:
    """Observability Logger

    Responsibilities:
    1. Log routing decisions
    2. Log LangGraph planning
    3. Log validation failures
    4. Log circuit breaker events
    5. Log collaboration events
    6. Log Shadow Mode predictions
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client

    async def log_route_decision(
        self,
        user_id: str,
        session_id: str,
        message: str,
        decision: dict[str, Any]
    ):
        """Log routing decision"""
        try:
            confidence_value = float(decision.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence_value = 0.0
        logger.info(
            f"Route decision: user={user_id[:8]}, "
            f"mode={decision.get('execution_mode')}, "
            f"intent={decision.get('intent')}, "
            f"risk={decision.get('risk_level')}, "
            f"confidence={confidence_value:.2f}, "
            f"layer={decision.get('routing_layer', 'unknown')}, "
            f"adaptive={decision.get('adaptive_notes', '')}, "
            f"policy={decision.get('policy_id', '')}, "
            f"pack={decision.get('strategy_pack', '')}, "
            f"reason={decision.get('reason', '')[:50]}"
        )

        await self.log_event(
            event_type="route_decision",
            user_id=user_id,
            session_id=session_id,
            data={
                "message_preview": message[:100],
                **decision
            }
        )

        # Metrics
        try:
            from app.core.metrics import REQUEST_COUNT
            REQUEST_COUNT.labels(
                module="orchestration",
                method="route_decision",
                status=decision.get('execution_mode', 'unknown')
            ).inc()
        except ImportError:
            pass

    async def log_langgraph_plan(
        self,
        user_id: str,
        session_id: str,
        plan_id: str,
        plan_data: dict[str, Any]
    ):
        """Log LangGraph planning"""
        agents = plan_data.get("agents_involved", [])
        tool_count = len(plan_data.get("tool_calls", []))
        confidence = plan_data.get("confidence", 0.0)
        collaboration_mode = plan_data.get("collaboration_mode", "single")

        logger.info(
            f"LangGraph plan: plan_id={plan_id[:8]}, "
            f"agents={agents}, "
            f"tools={tool_count}, "
            f"confidence={confidence:.2f}, "
            f"collaboration={collaboration_mode}"
        )

        await self.log_event(
            event_type="langgraph_plan",
            user_id=user_id,
            session_id=session_id,
            plan_id=plan_id,
            data=plan_data
        )

        # Metrics
        try:
            from app.core.metrics import LANGGRAPH_PLANNING_TOTAL
            LANGGRAPH_PLANNING_TOTAL.labels(
                collaboration_mode=collaboration_mode,
                agents_count=len(agents)
            ).inc()
        except ImportError:
            pass

    async def log_validation_failed(
        self,
        user_id: str,
        session_id: str,
        plan_id: str,
        failure_reason: str,
        suggestion: str | None = None
    ):
        """Log validation failure"""
        logger.warning(
            f"Validation failed: plan_id={plan_id[:8]}, "
            f"reason={failure_reason[:100]}"
        )

        await self.log_event(
            event_type="validation_failed",
            user_id=user_id,
            session_id=session_id,
            plan_id=plan_id,
            data={
                "failure_reason": failure_reason,
                "suggestion": suggestion
            }
        )

        # Metrics
        try:
            from app.core.metrics import REQUEST_COUNT
            REQUEST_COUNT.labels(
                module="validation",
                method="validate_plan",
                status="failed"
            ).inc()
        except ImportError:
            pass

    async def log_circuit_state_change(
        self,
        circuit_name: str,
        old_state: str,
        new_state: str,
        reason: str,
        metadata: dict[str, Any] | None = None
    ):
        """Log circuit breaker state change"""
        logger.info(
            f"Circuit state change: {circuit_name}, "
            f"{old_state} -> {new_state}, "
            f"reason={reason}"
        )

        await self.log_event(
            event_type="circuit_state_change",
            data={
                "circuit_name": circuit_name,
                "old_state": old_state,
                "new_state": new_state,
                "reason": reason,
                **(metadata or {})
            }
        )

        # Metrics
        try:
            from app.core.metrics import CIRCUIT_BREAKER_RESETS, CIRCUIT_BREAKER_TRIPS
            if new_state == "open":
                CIRCUIT_BREAKER_TRIPS.labels(circuit_name=circuit_name).inc()
            elif old_state in ["open", "half_open"] and new_state == "closed":
                CIRCUIT_BREAKER_RESETS.labels(circuit_name=circuit_name).inc()
        except ImportError:
            pass

    async def log_collaboration_start(
        self,
        user_id: str,
        session_id: str,
        agents: list[str],
        mode: str
    ):
        """Log collaboration start"""
        logger.info(
            f"Collaboration start: user={user_id[:8]}, "
            f"agents={agents}, mode={mode}"
        )

        await self.log_event(
            event_type="collaboration_start",
            user_id=user_id,
            session_id=session_id,
            data={
                "agents": agents,
                "mode": mode
            }
        )

    async def log_collaboration_end(
        self,
        user_id: str,
        session_id: str,
        agents: list[str],
        mode: str,
        tool_calls_count: int,
        latency_ms: float
    ):
        """Log collaboration end"""
        logger.info(
            f"Collaboration end: user={user_id[:8]}, "
            f"agents={agents}, tools={tool_calls_count}, "
            f"latency={latency_ms:.0f}ms"
        )

        await self.log_event(
            event_type="collaboration_end",
            user_id=user_id,
            session_id=session_id,
            data={
                "agents": agents,
                "mode": mode,
                "tool_calls_count": tool_calls_count,
                "latency_ms": latency_ms
            }
        )

    async def log_shadow_prediction(
        self,
        user_id: str,
        session_id: str,
        prediction: dict[str, Any]
    ):
        """Log Shadow Mode prediction"""
        is_correct = prediction.get("is_correct", False)
        accuracy = prediction.get("accuracy_score", 0.0)

        logger.debug(
            f"Shadow prediction: user={user_id[:8]}, "
            f"correct={is_correct}, accuracy={accuracy:.2f}"
        )

        await self.log_event(
            event_type="shadow_prediction",
            user_id=user_id,
            session_id=session_id,
            data=prediction
        )

    async def log_tool_execution(
        self,
        user_id: str,
        session_id: str,
        tool_name: str,
        success: bool,
        latency_ms: float
    ):
        """Log tool execution"""
        status = "success" if success else "failed"
        logger.debug(
            f"Tool execution: {tool_name}, {status}, {latency_ms:.0f}ms"
        )

        await self.log_event(
            event_type="tool_execution",
            user_id=user_id,
            session_id=session_id,
            data={
                "tool_name": tool_name,
                "success": success,
                "latency_ms": latency_ms
            }
        )

    async def log_expert_selected(
        self,
        *,
        user_id: str,
        session_id: str,
        expert_id: str,
        strategy: str,
        entry_source: str,
        workflow_id: str,
        policy_id: str = "",
        cohort_id: str = "",
        complexity_tier: str = "",
        task_type: str = "",
    ):
        await self.log_event(
            event_type="expert_selected",
            user_id=user_id,
            session_id=session_id,
            data={
                "expert_id": expert_id,
                "strategy": strategy,
                "entry_source": entry_source,
                "workflow_id": workflow_id,
                "policy_id": policy_id,
                "cohort_id": cohort_id,
                "complexity_tier": complexity_tier,
                "task_type": task_type,
            },
        )
        try:
            from app.core.metrics import EXPERT_SELECTED_TOTAL
            EXPERT_SELECTED_TOTAL.labels(
                expert_id=expert_id,
                strategy=strategy,
                entry_source=entry_source,
            ).inc()
        except ImportError:
            pass

    async def log_expert_invoked(
        self,
        *,
        user_id: str,
        session_id: str,
        expert_id: str,
        workflow_id: str,
        policy_id: str = "",
        cohort_id: str = "",
        complexity_tier: str = "",
        task_type: str = "",
    ):
        await self.log_event(
            event_type="expert_invoked",
            user_id=user_id,
            session_id=session_id,
            data={
                "expert_id": expert_id,
                "workflow_id": workflow_id,
                "policy_id": policy_id,
                "cohort_id": cohort_id,
                "complexity_tier": complexity_tier,
                "task_type": task_type,
            },
        )
        try:
            from app.core.metrics import EXPERT_INVOKED_TOTAL
            EXPERT_INVOKED_TOTAL.labels(expert_id=expert_id, workflow_id=workflow_id).inc()
        except ImportError:
            pass

    async def log_expert_fallback(
        self,
        *,
        user_id: str,
        session_id: str,
        reason: str,
        from_mode: str,
        workflow_id: str,
        policy_id: str = "",
        cohort_id: str = "",
        complexity_tier: str = "",
        task_type: str = "",
    ):
        await self.log_event(
            event_type="expert_fallback",
            user_id=user_id,
            session_id=session_id,
            data={
                "reason": reason,
                "from_mode": from_mode,
                "workflow_id": workflow_id,
                "policy_id": policy_id,
                "cohort_id": cohort_id,
                "complexity_tier": complexity_tier,
                "task_type": task_type,
            },
        )
        try:
            from app.core.metrics import EXPERT_FALLBACK_TOTAL
            EXPERT_FALLBACK_TOTAL.labels(reason=reason, from_mode=from_mode).inc()
        except ImportError:
            pass

    async def log_expert_overridden(
        self,
        *,
        user_id: str,
        session_id: str,
        requested_expert: str,
        used_expert: str,
        workflow_id: str,
        policy_id: str = "",
        cohort_id: str = "",
        complexity_tier: str = "",
        task_type: str = "",
    ):
        await self.log_event(
            event_type="expert_overridden",
            user_id=user_id,
            session_id=session_id,
            data={
                "requested_expert": requested_expert,
                "used_expert": used_expert,
                "workflow_id": workflow_id,
                "policy_id": policy_id,
                "cohort_id": cohort_id,
                "complexity_tier": complexity_tier,
                "task_type": task_type,
            },
        )
        try:
            from app.core.metrics import EXPERT_OVERRIDDEN_TOTAL
            EXPERT_OVERRIDDEN_TOTAL.labels(
                requested_expert=requested_expert,
                used_expert=used_expert,
            ).inc()
        except ImportError:
            pass

    async def log_user_feedback_bound(
        self,
        *,
        user_id: str,
        session_id: str,
        response_id: str,
        workflow_id: str,
        selected_experts: list[str],
        policy_id: str = "",
        cohort_id: str = "",
        user_scope: str = "",
    ):
        await self.log_event(
            event_type="user_feedback_bound",
            user_id=user_id,
            session_id=session_id,
            data={
                "response_id": response_id,
                "workflow_id": workflow_id,
                "selected_experts": selected_experts,
                "policy_id": policy_id,
                "cohort_id": cohort_id,
                "user_scope": user_scope,
            },
        )
        try:
            from app.core.metrics import USER_FEEDBACK_BOUND_TOTAL
            USER_FEEDBACK_BOUND_TOTAL.labels(workflow_id=workflow_id).inc()
        except ImportError:
            pass

    async def log_prompt_selected(
        self,
        *,
        user_id: str,
        session_id: str,
        workflow_id: str,
        prompt_version: str,
        trace_id: str = "",
        policy_id: str = "",
        strategy_pack: str = "",
        cohort_id: str = "",
        user_scope: str = "",
        complexity_tier: str = "",
        task_type: str = "",
    ) -> None:
        await self.log_event(
            event_type="prompt_selected",
            user_id=user_id,
            session_id=session_id,
            data={
                "workflow_id": workflow_id,
                "prompt_version": prompt_version,
                "trace_id": trace_id,
                "policy_id": policy_id,
                "strategy_pack": strategy_pack,
                "cohort_id": cohort_id,
                "user_scope": user_scope,
                "complexity_tier": complexity_tier,
                "task_type": task_type,
            },
        )
        try:
            from app.core.metrics import PROMPT_SELECTED_TOTAL
            PROMPT_SELECTED_TOTAL.labels(workflow_id=workflow_id, prompt_version=prompt_version).inc()
        except ImportError:
            pass

    async def log_prompt_applied(
        self,
        *,
        user_id: str,
        session_id: str,
        workflow_id: str,
        prompt_version: str,
        response_id: str = "",
        trace_id: str = "",
        policy_id: str = "",
        strategy_pack: str = "",
        cohort_id: str = "",
        user_scope: str = "",
        complexity_tier: str = "",
        task_type: str = "",
    ) -> None:
        await self.log_event(
            event_type="prompt_applied",
            user_id=user_id,
            session_id=session_id,
            data={
                "workflow_id": workflow_id,
                "prompt_version": prompt_version,
                "response_id": response_id,
                "trace_id": trace_id,
                "policy_id": policy_id,
                "strategy_pack": strategy_pack,
                "cohort_id": cohort_id,
                "user_scope": user_scope,
                "complexity_tier": complexity_tier,
                "task_type": task_type,
            },
        )
        try:
            from app.core.metrics import PROMPT_APPLIED_TOTAL
            PROMPT_APPLIED_TOTAL.labels(workflow_id=workflow_id, prompt_version=prompt_version).inc()
        except ImportError:
            pass

    async def log_toolchain_selected(
        self,
        *,
        user_id: str,
        session_id: str,
        workflow_id: str,
        toolchain_id: str,
        trace_id: str = "",
        response_id: str = "",
        policy_id: str = "",
        strategy_pack: str = "",
        cohort_id: str = "",
        user_scope: str = "",
        complexity_tier: str = "",
        task_type: str = "",
        latency_ms: float | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "workflow_id": workflow_id,
            "toolchain_id": toolchain_id,
            "trace_id": trace_id,
            "response_id": response_id,
            "policy_id": policy_id,
            "strategy_pack": strategy_pack,
            "cohort_id": cohort_id,
            "user_scope": user_scope,
            "complexity_tier": complexity_tier,
            "task_type": task_type,
        }
        if latency_ms is not None:
            payload["latency_ms"] = float(latency_ms)
        await self.log_event(
            event_type="toolchain_selected",
            user_id=user_id,
            session_id=session_id,
            data=payload,
        )
        try:
            from app.core.metrics import TOOLCHAIN_SELECTED_TOTAL
            TOOLCHAIN_SELECTED_TOTAL.labels(workflow_id=workflow_id, toolchain_id=toolchain_id).inc()
        except ImportError:
            pass

    async def log_toolchain_degraded(
        self,
        *,
        user_id: str,
        session_id: str,
        workflow_id: str,
        reason: str,
        trace_id: str = "",
        response_id: str = "",
        policy_id: str = "",
        strategy_pack: str = "",
        cohort_id: str = "",
        user_scope: str = "",
        complexity_tier: str = "",
        task_type: str = "",
    ) -> None:
        await self.log_event(
            event_type="toolchain_degraded",
            user_id=user_id,
            session_id=session_id,
            data={
                "workflow_id": workflow_id,
                "reason": reason,
                "trace_id": trace_id,
                "response_id": response_id,
                "policy_id": policy_id,
                "strategy_pack": strategy_pack,
                "cohort_id": cohort_id,
                "user_scope": user_scope,
                "complexity_tier": complexity_tier,
                "task_type": task_type,
            },
        )
        try:
            from app.core.metrics import TOOLCHAIN_DEGRADED_TOTAL
            TOOLCHAIN_DEGRADED_TOTAL.labels(workflow_id=workflow_id, reason=reason).inc()
        except ImportError:
            pass

    async def log_cold_start_bootstrap(
        self,
        *,
        user_id: str,
        session_id: str,
        workflow_id: str,
        strategy: str,
        chat_mode: str,
        trace_id: str = "",
        response_id: str = "",
        cohort_id: str = "",
        user_scope: str = "",
        policy_id: str = "",
        strategy_pack: str = "",
    ) -> None:
        await self.log_event(
            event_type="cold_start_bootstrap_applied",
            user_id=user_id,
            session_id=session_id,
            data={
                "workflow_id": workflow_id,
                "strategy": strategy,
                "chat_mode": chat_mode,
                "trace_id": trace_id,
                "response_id": response_id,
                "cohort_id": cohort_id,
                "user_scope": user_scope,
                "policy_id": policy_id,
                "strategy_pack": strategy_pack,
            },
        )
        try:
            from app.core.metrics import COLD_START_BOOTSTRAP_TOTAL
            COLD_START_BOOTSTRAP_TOTAL.labels(strategy=strategy, chat_mode=chat_mode).inc()
        except ImportError:
            pass

    async def log_event(
        self,
        event_type: str,
        user_id: str = "",
        session_id: str = "",
        plan_id: str = "",
        data: dict[str, Any] | None = None
    ):
        """Log generic event"""
        event = ObservabilityEvent(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            plan_id=plan_id,
            data=data or {}
        )

        # Write to Redis (optional)
        if self.redis:
            await self._write_to_redis(event)

        if getattr(settings, "ENABLE_LEARNING_CONTROL_PLANE", False):
            await self._write_to_learning_stream(
                event_type=event_type,
                user_id=user_id,
                session_id=session_id,
                data=data or {},
            )

    async def _write_to_redis(self, event: ObservabilityEvent):
        """Write to Redis"""
        key = f"observability:event:{event.event_type}:{event.timestamp}"
        try:
            payload = json.dumps({
                "event_id": event.event_id,
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "plan_id": event.plan_id,
                "data": event.data
            })
            await self.redis.setex(key, 3600, payload)  # TTL 1 hour
        except Exception as e:
            logger.warning(f"Failed to write event to Redis: {e}")

    async def _write_to_learning_stream(
        self,
        *,
        event_type: str,
        user_id: str,
        session_id: str,
        data: dict[str, Any],
    ) -> None:
        try:
            from app.services.learning_event_service import LearningEventService

            payload = data if isinstance(data, dict) else {}
            policy_id = str(payload.get("policy_id", ""))
            strategy_pack = str(payload.get("strategy_pack", ""))
            if not strategy_pack and ":" in policy_id:
                rest = policy_id.split(":", 1)[1]
                if ":candidate_" in rest:
                    strategy_pack = rest.split(":candidate_", 1)[0]
                else:
                    strategy_pack = rest.split(":", 1)[0]
            service = LearningEventService(redis_client=self.redis)
            await service.emit(
                event_type=event_type,
                user_id=user_id,
                session_id=session_id,
                workflow_id=str(payload.get("workflow_id", "")),
                trace_id=str(payload.get("trace_id", "")),
                response_id=str(payload.get("response_id", "")),
                policy_id=policy_id,
                strategy_pack=strategy_pack,
                cohort_id=str(payload.get("cohort_id", "")),
                user_scope=str(payload.get("user_scope", "")),
                complexity_tier=str(payload.get("complexity_tier", "")),
                task_type=str(payload.get("task_type", "")),
                data=payload,
            )
        except Exception as exc:
            logger.warning("Failed writing learning event from observability: {}", exc)


# Global instance
observability_logger = ObservabilityLogger()
