"""Execution orchestration service for OpenClaw handoff."""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import String, cast, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.openclaw import OpenClawClient, OpenClawConfig, IntentTranslator, ResultParser
from app.adapters.openclaw.client import OpenClawConfigurationError, OpenClawError, OpenClawTimeout
from app.config import settings
from app.core.event_bus import event_bus
from app.core.event_types import (
    EXECUTION_DELEGATED,
    EXECUTION_HANDED_BACK,
    EXECUTION_NODE_SELECTED,
    EXECUTION_QUALITY_RECORDED,
    EXECUTION_RESULT_INGESTED,
    EXECUTION_STATUS_CHANGED,
    EXECUTION_TEMPLATE_SELECTED,
)
from app.core.execution_router import ExecutionRouter, RoutingDecision
from app.core.execution_trust import ExecutionTrustEngine, TrustEvaluation
from app.core.task_monitor import task_monitor_service
from app.models.background_task import BackgroundTaskStatus, BackgroundTaskType
from app.models.execution_intent import (
    ExecutionIntent,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionTargetEnv,
    ExecutorType,
    TrustLevel,
)
from app.models.execution_record import ExecutionRecord
from app.models.task import Task, TaskStatus
from app.services.execution_ingestor import ExecutionIngestor
from app.services.execution_learning_service import ExecutionLearningService
from app.services.execution_node_service import ExecutionNodeService
from app.services.execution_quality_service import ExecutionQualityService
from app.services.execution_result_validator import ExecutionResultValidator
from app.services.execution_template_service import ExecutionTemplateService
from app.services.plan_execution_record_service import PlanExecutionRecordService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExecutionService:
    """Phase 1 execution service for task handoff and synchronous dispatch."""

    _shared_classify_cache: dict[str, tuple[RoutingDecision, float]] = {}
    _classify_cache_ttl_seconds = 300.0
    _failure_counts: dict[str, int] = {}
    _degraded_users: dict[str, float] = {}
    _degradation_threshold = 3
    _degradation_window_seconds = 1800.0

    def __init__(self, db: AsyncSession, redis=None):
        self._db = db
        self._redis = redis
        self._config = OpenClawConfig.from_settings()
        self._router = ExecutionRouter(openclaw_enabled=self._config.enabled)
        self._trust_engine = ExecutionTrustEngine(
            auto_trust_min_history=settings.OPENCLAW_TRUST_AUTO_PROMOTE_MIN_HISTORY,
            auto_trust_success_rate=settings.OPENCLAW_TRUST_AUTO_PROMOTE_SUCCESS_RATE,
        )
        self._client = OpenClawClient(self._config) if self._config.enabled else None
        self._translator = IntentTranslator()
        self._parser = ResultParser()
        self._plan_record_service = PlanExecutionRecordService(db)
        self._ingestor = ExecutionIngestor(db=db, redis=redis)
        self._learning_service = ExecutionLearningService(db=db, redis=redis)
        self._template_service = ExecutionTemplateService()
        self._node_service = ExecutionNodeService(self._client)
        self._quality_service = ExecutionQualityService(db)
        self._result_validator = ExecutionResultValidator()
        self._classify_cache = self.__class__._shared_classify_cache
        self._classify_cache_ttl = self.__class__._classify_cache_ttl_seconds

    async def get_health(self) -> dict[str, Any]:
        health_snapshot = await self._client.health_snapshot() if self._client else {"reachable": False}
        nodes = await self._node_service.list_nodes(connected_only=True) if self._client else []
        degradation = self.get_degradation_snapshot()
        return {
            "openclaw_enabled": self._config.enabled,
            "gateway_url": self._config.gateway_url if self._config.enabled else None,
            "transport": self._config.transport,
            "ws_url": self._config.ws_url if self._config.transport == "gateway_ws" else None,
            "reachable": bool(health_snapshot.get("reachable")),
            "latency_ms": health_snapshot.get("latency_ms"),
            "message": health_snapshot.get("message"),
            "supports_approvals": True,
            "ingestion_layer": "execution_ingestor",
            "connected_nodes": len(nodes),
            "supports_nodes": self._config.transport == "gateway_ws",
            "supports_templates": True,
            "supports_quality_loop": True,
            "capabilities": list(health_snapshot.get("capabilities") or []),
            "degraded_user_count": degradation["degraded_user_count"],
            "degradation_threshold": degradation["degradation_threshold"],
        }

    async def classify_task(self, *, task_id: UUID, user_id: UUID) -> RoutingDecision:
        task = await self._get_user_task(task_id=task_id, user_id=user_id)
        if self._is_user_degraded(user_id):
            return RoutingDecision(
                execution_mode=ExecutionMode.HUMAN,
                target_env=ExecutionTargetEnv.HUMAN,
                reason="execution_temporarily_degraded",
                confidence=0.98,
                risk_flags=["degraded_due_to_consecutive_failures"],
            )
        task_type = getattr(task.type, "value", task.type) or ""
        task_description = getattr(task, "description", "") or ""
        task_tags = getattr(task, "tags", None) or []
        cache_key = hashlib.md5(
            "|".join(
                [
                    str(task_type),
                    str(task.title or ""),
                    str(task_description),
                    ",".join(sorted(str(tag) for tag in task_tags)),
                ]
            ).encode("utf-8")
        ).hexdigest()
        now = time.time()
        cached = self._classify_cache.get(cache_key)
        if cached is not None:
            decision, cached_at = cached
            if now - cached_at < self._classify_cache_ttl:
                return decision

        decision = self._classify_task_entity(task)
        self._classify_cache[cache_key] = (decision, now)
        if len(self._classify_cache) > 100:
            cutoff = now - self._classify_cache_ttl
            self._classify_cache = {
                key: value for key, value in self._classify_cache.items() if value[1] >= cutoff
            }
        return decision

    async def create_intent(
        self,
        *,
        task_id: UUID,
        user_id: UUID,
        goal: str | None = None,
        instructions: list[str] | None = None,
        policy: dict[str, Any] | None = None,
        success_criteria: dict[str, Any] | None = None,
        result_contract: dict[str, Any] | None = None,
        template_id: str | None = None,
        preferred_node_id: str | None = None,
    ) -> ExecutionIntent:
        task = await self._get_user_task(task_id=task_id, user_id=user_id)
        if self._is_user_degraded(user_id):
            task.execution_mode = ExecutionMode.HUMAN.value
            self._db.add(task)
            await self._db.commit()
            raise ValueError("AI execution is temporarily degraded after consecutive failures")
        await self._ensure_no_active_intent(task_id=task.id, user_id=user_id)
        execution_goal = (goal or task.title or "").strip()
        selected_template = None
        template_payload: dict[str, Any] | None = None
        if template_id:
            selected_template = self._template_service.get_definition(template_id)
            template_payload = self._template_service.apply_template(
                task=task,
                template_id=template_id,
                goal_override=execution_goal,
            )
        elif not success_criteria and not result_contract:
            auto_template = self._template_service.auto_select(task=task, goal_override=execution_goal)
            if auto_template is not None:
                selected_template = auto_template.definition
                template_payload = self._template_service.apply_template(
                    task=task,
                    template_id=auto_template.definition.template_id,
                    goal_override=execution_goal,
                )

        decision = self._router.classify(
            task_type=task.type.value if task.type else "",
            goal=execution_goal,
            has_side_effects=self._infer_side_effects(execution_goal),
            has_clear_criteria=bool(success_criteria or (template_payload or {}).get("success_criteria")),
            task_tags=task.tags or [],
        )
        if selected_template is not None and template_payload is not None:
            decision = RoutingDecision(
                execution_mode=template_payload["execution_mode"],
                target_env=template_payload["target_env"],
                reason=f"template_selected:{selected_template.template_id}",
                confidence=max(decision.confidence, 0.82),
                risk_flags=list(decision.risk_flags),
            )
        if decision.execution_mode == ExecutionMode.HUMAN:
            raise ValueError(f"Task is not eligible for AI execution: {decision.reason}")

        intent_instructions = self._build_instructions(
            task,
            template_instructions=(template_payload or {}).get("instructions"),
            extra_instructions=instructions,
        )
        intent_policy = self._merge_dicts(
            self._default_policy(decision.target_env),
            (template_payload or {}).get("policy"),
            policy or {},
        )
        intent_success = self._merge_dicts(
            (template_payload or {}).get("success_criteria"),
            success_criteria or {"type": "non_empty"},
        )
        intent_contract = self._merge_dicts(
            (template_payload or {}).get("result_contract"),
            result_contract or {},
        )

        strategy = await self._quality_service.assign_strategy(
            user_id=user_id,
            target_env=decision.target_env.value if decision.target_env else "general",
            execution_mode=decision.execution_mode,
            template_id=selected_template.template_id if selected_template else None,
        )
        intent_policy["quality_strategy"] = strategy.to_policy_payload()
        self._apply_strategy_to_payload(
            strategy=strategy,
            instructions=intent_instructions,
            policy=intent_policy,
            result_contract=intent_contract,
        )

        required_node_command = str(
            intent_policy.get("target_node_command")
            or intent_policy.get("required_node_command")
            or (template_payload or {}).get("required_node_command")
            or ""
        ) or None
        selected_node = None
        try:
            selected_node = await self._node_service.select_node(
                preferred_node_id=preferred_node_id,
                required_command=required_node_command,
                target_env=decision.target_env,
            )
        except ValueError:
            raise
        except Exception as exc:
            logger.warning("Execution node discovery failed for task {}: {}", task.id, exc)
            if required_node_command:
                raise ValueError(
                    f"Task requires a node with {required_node_command} capability, but none is available."
                ) from exc
        if required_node_command and selected_node is None:
            raise ValueError(
                f"Task requires a node with {required_node_command} capability, but none is available."
            )
        if selected_node is not None:
            intent_policy = self._merge_dicts(
                intent_policy,
                self._node_service.build_policy_patch(
                    node=selected_node,
                    required_command=required_node_command,
                ),
            )
        idempotency_key = self._build_idempotency_key(task)

        intent = ExecutionIntent(
            plan_id=task.plan_id,
            task_id=task.id,
            user_id=user_id,
            execution_mode=decision.execution_mode,
            executor=ExecutorType.OPENCLAW,
            goal=execution_goal,
            instructions=intent_instructions,
            target_env=decision.target_env,
            policy=intent_policy,
            success_criteria=intent_success,
            result_contract=intent_contract,
            timeout_seconds=self._config.default_timeout_seconds,
            status=ExecutionIntentStatus.READY,
            trust_level=TrustLevel.RAW,
            idempotency_key=idempotency_key,
        )
        self._db.add(intent)
        task.execution_mode = decision.execution_mode.value
        self._db.add(task)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._db.refresh(task)

        await self._publish_status_event(intent, old_status=None)
        await event_bus.publish(
            EXECUTION_DELEGATED,
            {
                "event_type": EXECUTION_DELEGATED,
                "user_id": str(user_id),
                "task_id": str(task.id),
                "plan_id": str(task.plan_id) if task.plan_id else None,
                "execution_intent_id": str(intent.id),
                "execution_mode": intent.execution_mode.value,
                "executor": intent.executor.value,
                "target_env": intent.target_env.value if intent.target_env else None,
                "timestamp": _utcnow().isoformat(),
            },
        )
        if selected_template is not None:
            await event_bus.publish(
                EXECUTION_TEMPLATE_SELECTED,
                {
                    "event_type": EXECUTION_TEMPLATE_SELECTED,
                    "user_id": str(user_id),
                    "task_id": str(task.id),
                    "execution_intent_id": str(intent.id),
                    "template_id": selected_template.template_id,
                    "template_name": selected_template.name,
                    "timestamp": _utcnow().isoformat(),
                },
            )
        if selected_node is not None:
            await event_bus.publish(
                EXECUTION_NODE_SELECTED,
                {
                    "event_type": EXECUTION_NODE_SELECTED,
                    "user_id": str(user_id),
                    "task_id": str(task.id),
                    "execution_intent_id": str(intent.id),
                    "node_id": selected_node.node_id,
                    "node_name": selected_node.name,
                    "node_platform": selected_node.platform,
                    "timestamp": _utcnow().isoformat(),
                },
            )
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.PENDING,
            progress=0.0,
            progress_message="Execution intent created",
        )
        return intent

    async def dispatch(self, *, intent_id: UUID, user_id: UUID) -> ExecutionIntent:
        intent = await self._get_user_intent(intent_id=intent_id, user_id=user_id)
        if intent.status not in {ExecutionIntentStatus.DRAFT, ExecutionIntentStatus.READY}:
            raise ValueError(f"Intent {intent_id} is in status {intent.status.value}, cannot dispatch")
        if not self._client:
            raise OpenClawError("OpenClaw integration is not enabled")

        old_status = intent.status
        intent.status = ExecutionIntentStatus.DISPATCHED
        intent.dispatched_at = _utcnow()
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.RUNNING,
            progress=0.2,
            progress_message="Dispatching to OpenClaw",
        )

        try:
            request_body = self._build_dispatch_payload(intent)
            old_status = intent.status
            intent.status = ExecutionIntentStatus.RUNNING
            self._db.add(intent)
            await self._db.commit()
            await self._db.refresh(intent)
            await self._publish_status_event(intent, old_status=old_status)

            execute_kwargs: dict[str, Any] = {
                "timeout_seconds": intent.timeout_seconds,
            }
            if self._config.transport == "gateway_ws":
                execute_kwargs["event_callback"] = lambda frame: self._handle_gateway_stream_event(intent, frame)
            raw_response = await self._client.execute(request_body, **execute_kwargs)
            await self._ingestor.ingest(intent=intent, raw_result=raw_response)
            await self._db.refresh(intent)
            if intent.status in {
                ExecutionIntentStatus.WAITING_APPROVAL,
                ExecutionIntentStatus.SUCCEEDED,
                ExecutionIntentStatus.PARTIAL,
            }:
                self._clear_failure_state(user_id)
            return intent
        except OpenClawTimeout as exc:
            await self._mark_intent_failure(
                intent=intent,
                status=ExecutionIntentStatus.TIMED_OUT,
                error_category="timeout",
                error_message=str(exc),
            )
            return intent
        except OpenClawError as exc:
            await self._mark_intent_failure(
                intent=intent,
                status=ExecutionIntentStatus.FAILED,
                error_category="adapter_error",
                error_message=str(exc),
            )
            return intent
        except Exception as exc:
            await self._mark_intent_failure(
                intent=intent,
                status=ExecutionIntentStatus.FAILED,
                error_category="unexpected_error",
                error_message=str(exc),
            )
            return intent

    async def handoff_to_openclaw(
        self,
        *,
        task_id: UUID,
        user_id: UUID,
        goal: str | None = None,
        instructions: list[str] | None = None,
        policy: dict[str, Any] | None = None,
        success_criteria: dict[str, Any] | None = None,
        result_contract: dict[str, Any] | None = None,
        template_id: str | None = None,
        preferred_node_id: str | None = None,
    ) -> ExecutionIntent:
        intent = await self.create_intent(
            task_id=task_id,
            user_id=user_id,
            goal=goal,
            instructions=instructions,
            policy=policy,
            success_criteria=success_criteria,
            result_contract=result_contract,
            template_id=template_id,
            preferred_node_id=preferred_node_id,
        )
        return await self.dispatch(intent_id=intent.id, user_id=user_id)

    async def get_intent(self, *, intent_id: UUID, user_id: UUID) -> ExecutionIntent:
        return await self._get_user_intent(intent_id=intent_id, user_id=user_id)

    async def list_task_intents(self, *, task_id: UUID, user_id: UUID) -> list[ExecutionIntent]:
        await self._get_user_task(task_id=task_id, user_id=user_id)
        result = await self._db.execute(
            select(ExecutionIntent)
            .where(
                ExecutionIntent.task_id == task_id,
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.deleted_at.is_(None),
            )
            .order_by(desc(ExecutionIntent.created_at))
        )
        return list(result.scalars().all())

    async def list_templates(self, *, task_id: UUID, user_id: UUID) -> list[dict[str, Any]]:
        task = await self._get_user_task(task_id=task_id, user_id=user_id)
        matches = self._template_service.list_templates(task=task)
        return [match.to_dict() for match in matches]

    async def list_nodes(
        self,
        *,
        connected_only: bool = True,
        last_connected: str | None = None,
    ) -> list[dict[str, Any]]:
        nodes = await self._node_service.list_nodes(
            connected_only=connected_only,
            last_connected=last_connected,
        )
        return [node.to_dict() for node in nodes]

    async def invoke_node(
        self,
        *,
        node_id: str,
        command: str,
        params: dict[str, Any] | None = None,
        invoke_timeout_ms: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return await self._node_service.invoke_node(
            node_id=node_id,
            command=command,
            params=params,
            invoke_timeout_ms=invoke_timeout_ms,
            idempotency_key=idempotency_key,
        )

    async def get_quality_summary(self) -> dict[str, Any]:
        return await self._quality_service.get_summary()

    async def get_execution_record(self, *, intent_id: UUID, user_id: UUID) -> ExecutionRecord | None:
        intent = await self._get_user_intent(intent_id=intent_id, user_id=user_id)
        result = await self._db.execute(
            select(ExecutionRecord).where(
                ExecutionRecord.execution_intent_id == intent.id,
                ExecutionRecord.user_id == user_id,
                ExecutionRecord.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def confirm_result(self, *, record_id: UUID, user_id: UUID) -> ExecutionRecord:
        record = await self._ingestor._get_user_record(record_id=record_id, user_id=user_id)
        intent = await self._get_user_intent(intent_id=record.execution_intent_id, user_id=user_id)
        approval_id = self._extract_approval_id(record.raw_response or {})

        if (
            self._client
            and self._config.transport == "gateway_ws"
            and intent.status == ExecutionIntentStatus.WAITING_APPROVAL
            and approval_id
            and intent.external_run_id
        ):
            raw_response = await self._client.resolve_approval(
                approval_id=approval_id,
                decision="allow-once",
                run_id=intent.external_run_id,
                session_key=self._session_key_for_intent(intent),
                timeout_seconds=intent.timeout_seconds,
                event_callback=lambda frame: self._handle_gateway_stream_event(intent, frame),
            )
            confirmed = await self._ingestor.ingest(
                intent=intent,
                raw_result=raw_response,
                user_confirmed=raw_response.get("status") != "requires_action",
            )
            self._clear_failure_state(user_id)
            return confirmed

        confirmed = await self._ingestor.confirm_result(record_id=record_id, user_id=user_id)
        self._clear_failure_state(user_id)
        return confirmed

    async def reject_result(
        self,
        *,
        record_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> ExecutionRecord:
        record = await self._ingestor._get_user_record(record_id=record_id, user_id=user_id)
        intent = await self._get_user_intent(intent_id=record.execution_intent_id, user_id=user_id)
        approval_id = self._extract_approval_id(record.raw_response or {})

        if (
            self._client
            and self._config.transport == "gateway_ws"
            and intent.status == ExecutionIntentStatus.WAITING_APPROVAL
            and approval_id
            and intent.external_run_id
        ):
            try:
                await self._client.resolve_approval(
                    approval_id=approval_id,
                    decision="deny",
                    run_id=intent.external_run_id,
                    session_key=self._session_key_for_intent(intent),
                    timeout_seconds=max(30, intent.timeout_seconds),
                    event_callback=lambda frame: self._handle_gateway_stream_event(intent, frame),
                )
            except OpenClawError as exc:
                logger.warning("Failed to deny remote OpenClaw approval for intent {}: {}", intent.id, exc)

        return await self._ingestor.reject_result(record_id=record_id, user_id=user_id, reason=reason)

    async def cancel(self, *, intent_id: UUID, user_id: UUID) -> ExecutionIntent:
        intent = await self._get_user_intent(intent_id=intent_id, user_id=user_id)
        if intent.status in self._terminal_statuses():
            raise ValueError("Execution is already terminal")

        if self._client and self._config.transport == "gateway_ws":
            try:
                await self._client.cancel_run(
                    session_key=self._session_key_for_intent(intent),
                    run_id=intent.external_run_id,
                )
            except OpenClawError as exc:
                logger.warning("Failed to cancel remote OpenClaw run for intent {}: {}", intent.id, exc)

        old_status = intent.status
        intent.status = ExecutionIntentStatus.CANCELED
        intent.completed_at = _utcnow()
        intent.error_category = "canceled"
        intent.error_message = "Canceled by user"
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.CANCELLED,
            progress=1.0,
            progress_message="Execution canceled",
        )
        self._clear_failure_state(user_id)
        record = await self.get_execution_record(intent_id=intent.id, user_id=user_id)
        if record is not None:
            await self._quality_service.record_outcome(intent=intent, record=record, outcome="canceled")
            await event_bus.publish(
                EXECUTION_QUALITY_RECORDED,
                {
                    "event_type": EXECUTION_QUALITY_RECORDED,
                    "user_id": str(user_id),
                    "execution_intent_id": str(intent.id),
                    "execution_record_id": str(record.id),
                    "variant_name": ((intent.policy or {}).get("quality_strategy") or {}).get("variant_name"),
                    "outcome": "canceled",
                    "quality_score": record.quality_score,
                    "timestamp": _utcnow().isoformat(),
                },
            )
        return intent

    async def handback(self, *, intent_id: UUID, user_id: UUID, reason: str | None = None) -> ExecutionIntent:
        intent = await self._get_user_intent(intent_id=intent_id, user_id=user_id)
        if intent.status in self._terminal_statuses():
            raise ValueError("Execution is already terminal")
        task = await self._get_user_task(task_id=intent.task_id, user_id=user_id)

        old_status = intent.status
        intent.status = ExecutionIntentStatus.HANDED_BACK
        intent.completed_at = _utcnow()
        intent.error_category = "handed_back"
        intent.error_message = reason or "Returned to user"
        task.execution_mode = ExecutionMode.HUMAN.value
        self._db.add(intent)
        self._db.add(task)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await event_bus.publish(
            EXECUTION_HANDED_BACK,
            {
                "event_type": EXECUTION_HANDED_BACK,
                "user_id": str(user_id),
                "execution_intent_id": str(intent.id),
                "task_id": str(task.id),
                "reason": reason,
                "progress_at_handback": 0.0,
                "timestamp": _utcnow().isoformat(),
            },
        )
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.CANCELLED,
            progress=1.0,
            progress_message="Execution returned to user",
        )
        self._clear_failure_state(user_id)
        record = await self.get_execution_record(intent_id=intent.id, user_id=user_id)
        if record is not None:
            await self._quality_service.record_outcome(intent=intent, record=record, outcome="handed_back")
            await event_bus.publish(
                EXECUTION_QUALITY_RECORDED,
                {
                    "event_type": EXECUTION_QUALITY_RECORDED,
                    "user_id": str(user_id),
                    "execution_intent_id": str(intent.id),
                    "execution_record_id": str(record.id),
                    "variant_name": ((intent.policy or {}).get("quality_strategy") or {}).get("variant_name"),
                    "outcome": "handed_back",
                    "quality_score": record.quality_score,
                    "timestamp": _utcnow().isoformat(),
                },
            )
        await self._learning_service.handle_handed_back(
            intent=intent,
            reason=reason,
        )
        return intent

    def _classify_task_entity(self, task: Task) -> RoutingDecision:
        return self._router.classify(
            task_type=task.type.value if task.type else "",
            goal=task.title or "",
            has_side_effects=self._infer_side_effects(task.title or ""),
            has_clear_criteria=False,
            task_tags=task.tags or [],
        )

    def _build_dispatch_payload(self, intent: ExecutionIntent) -> dict[str, Any]:
        if self._config.transport == "gateway_ws":
            return self._translator.translate_gateway_request(
                intent,
                agent_id=self._config.default_agent_id,
            )
        return self._translator.translate(intent, agent_id=self._config.default_agent_id)

    def _session_key_for_intent(self, intent: ExecutionIntent) -> str:
        return self._translator.build_session_key(intent, agent_id=self._config.default_agent_id)

    def _extract_approval_id(self, raw_response: dict[str, Any]) -> str | None:
        approval = raw_response.get("approval")
        if isinstance(approval, dict):
            approval_id = approval.get("id") or approval.get("approvalId")
            if approval_id:
                return str(approval_id)
        required_action = raw_response.get("required_action")
        if isinstance(required_action, dict):
            approval_id = required_action.get("approval_id") or required_action.get("approvalId")
            if approval_id:
                return str(approval_id)
        return None

    async def _handle_gateway_stream_event(self, intent: ExecutionIntent, frame: dict[str, Any]) -> None:
        if self._config.transport != "gateway_ws":
            return

        event_name = frame.get("event")
        payload = frame.get("payload") or {}

        if event_name == "agent":
            stream = payload.get("stream")
            if stream == "lifecycle":
                phase = payload.get("phase")
                if phase == "start":
                    await self._publish_monitor_progress(
                        intent=intent,
                        status=BackgroundTaskStatus.RUNNING,
                        progress=0.35,
                        progress_message="OpenClaw started execution",
                    )
                elif phase == "end":
                    await self._publish_monitor_progress(
                        intent=intent,
                        status=BackgroundTaskStatus.RUNNING,
                        progress=0.95,
                        progress_message="OpenClaw finished execution",
                    )
                elif phase == "error":
                    await self._publish_monitor_progress(
                        intent=intent,
                        status=BackgroundTaskStatus.RUNNING,
                        progress=0.95,
                        progress_message="OpenClaw reported an execution error",
                        error_message=str(payload.get("error") or "OpenClaw lifecycle error"),
                    )
            elif stream == "assistant":
                await self._publish_monitor_progress(
                    intent=intent,
                    status=BackgroundTaskStatus.RUNNING,
                    progress=0.7,
                    progress_message="OpenClaw is producing output",
                )
            elif stream == "tool":
                await self._publish_monitor_progress(
                    intent=intent,
                    status=BackgroundTaskStatus.RUNNING,
                    progress=0.55,
                    progress_message="OpenClaw is using tools",
                )
            return

        if event_name == "exec.approval.requested":
            await self._publish_monitor_progress(
                intent=intent,
                status=BackgroundTaskStatus.RUNNING,
                progress=0.85,
                progress_message="OpenClaw is waiting for approval",
                result_data={
                    "intent_id": str(intent.id),
                    "status": ExecutionIntentStatus.WAITING_APPROVAL.value,
                },
            )

    async def _get_user_task(self, *, task_id: UUID, user_id: UUID) -> Task:
        task = await self._db.get(Task, task_id)
        if not task or task.user_id != user_id or task.deleted_at is not None:
            raise ValueError("Task not found")
        return task

    async def _get_user_intent(self, *, intent_id: UUID, user_id: UUID) -> ExecutionIntent:
        intent = await self._db.get(ExecutionIntent, intent_id)
        if not intent or intent.user_id != user_id or intent.deleted_at is not None:
            raise ValueError("Execution intent not found")
        return intent

    async def _ensure_no_active_intent(self, *, task_id: UUID, user_id: UUID) -> None:
        terminal_statuses = [status.value for status in self._terminal_statuses()]
        result = await self._db.execute(
            select(ExecutionIntent)
            .where(
                ExecutionIntent.task_id == task_id,
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.deleted_at.is_(None),
                cast(ExecutionIntent.status, String).notin_(terminal_statuses),
            )
            .order_by(desc(ExecutionIntent.created_at))
        )
        active_intent = result.scalar_one_or_none()
        if active_intent is not None:
            raise ValueError(f"Active execution already exists for task: {active_intent.id}")

    def _build_idempotency_key(self, task: Task) -> str:
        plan_id = str(task.plan_id) if task.plan_id else "noplan"
        return f"{plan_id}:{task.id}:{uuid.uuid4().hex[:8]}"

    def _build_instructions(
        self,
        task: Task,
        *,
        template_instructions: list[str] | None,
        extra_instructions: list[str] | None,
    ) -> list[str]:
        instructions = list(template_instructions or [])
        instructions.extend(extra_instructions or [])
        if task.guide_content:
            instructions.append(f"Reference guide: {task.guide_content[:500]}")
        deduped: list[str] = []
        seen: set[str] = set()
        for item in instructions:
            normalized = str(item).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    def _default_policy(self, target_env: ExecutionTargetEnv | None) -> dict[str, Any]:
        allowed_tools: list[str] = []
        if target_env == ExecutionTargetEnv.BROWSER:
            allowed_tools = ["browser"]
        elif target_env == ExecutionTargetEnv.DOCUMENT:
            allowed_tools = ["browser", "read"]
        elif target_env == ExecutionTargetEnv.API:
            allowed_tools = ["http"]
        elif target_env == ExecutionTargetEnv.SHELL:
            allowed_tools = ["exec", "read"]

        return {
            "allow_exec": False,
            "allowed_tools": allowed_tools,
            "allowed_domains": [],
            "approval_policy": "deny",
        }

    def _infer_side_effects(self, goal: str) -> bool:
        side_effect_keywords = {"更新", "修改", "提交", "发送", "发布", "删除", "创建", "写入"}
        return any(keyword in goal for keyword in side_effect_keywords)

    def _apply_strategy_to_payload(
        self,
        *,
        strategy,
        instructions: list[str],
        policy: dict[str, Any],
        result_contract: dict[str, Any],
    ) -> None:
        configuration = strategy.configuration or {}
        for instruction in configuration.get("instruction_suffixes", []):
            if instruction not in instructions:
                instructions.append(str(instruction))

        artifact_types = configuration.get("artifact_types")
        if artifact_types:
            existing = list(result_contract.get("artifact_types") or [])
            for artifact_type in artifact_types:
                if artifact_type not in existing:
                    existing.append(artifact_type)
            result_contract["artifact_types"] = existing

        timeout_multiplier = configuration.get("timeout_multiplier")
        if timeout_multiplier:
            policy["timeout_multiplier"] = timeout_multiplier

    def _merge_dicts(self, *values: dict[str, Any] | None) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for value in values:
            if not value:
                continue
            for key, item in value.items():
                if isinstance(item, dict) and isinstance(merged.get(key), dict):
                    merged[key] = self._merge_dicts(merged.get(key), item)
                else:
                    merged[key] = item
        return merged

    def _build_evaluation_input(self, parsed: dict[str, Any]) -> dict[str, Any]:
        evaluation_input = dict(parsed)
        parsed_output = parsed.get("parsed_output")
        if isinstance(parsed_output, dict):
            for key, value in parsed_output.items():
                evaluation_input.setdefault(key, value)
        return evaluation_input

    async def _upsert_execution_record(
        self,
        *,
        intent: ExecutionIntent,
        raw_response: dict[str, Any],
        parsed: dict[str, Any],
        evaluation: TrustEvaluation,
    ) -> ExecutionRecord:
        result = await self._db.execute(select(ExecutionRecord).where(ExecutionRecord.execution_intent_id == intent.id))
        record = result.scalar_one_or_none()
        if record is None:
            record = ExecutionRecord(
                execution_intent_id=intent.id,
                user_id=intent.user_id,
                task_id=intent.task_id,
            )

        record.executor_type = intent.executor.value
        record.external_run_id = raw_response.get("id")
        enriched_raw_response = dict(raw_response)
        enriched_raw_response["_sparkle_quality_warnings"] = self._result_validator.validate(
            parsed=parsed,
            result_contract=intent.result_contract or {},
        )
        record.raw_response = enriched_raw_response
        record.parsed_output = parsed.get("parsed_output")
        record.artifacts = parsed.get("artifacts", [])
        record.trust_level = evaluation.trust_level.value
        record.validation_passed = evaluation.validation_passed
        record.validation_total = evaluation.validation_total
        record.quality_score = evaluation.quality_score
        record.token_usage = parsed.get("token_usage")
        record.tool_calls_count = parsed.get("tool_calls_count", 0)
        record.error_category = None if parsed.get("success") else "execution_failed"
        record.error_message = parsed.get("error_message")
        record.execution_started_at = intent.dispatched_at
        record.execution_completed_at = _utcnow()
        self._db.add(record)
        await self._db.commit()
        await self._db.refresh(record)
        return record

    async def _apply_execution_result(
        self,
        *,
        intent: ExecutionIntent,
        parsed: dict[str, Any],
        evaluation: TrustEvaluation,
        record: ExecutionRecord,
    ) -> None:
        old_status = intent.status
        now = _utcnow()

        intent.external_run_id = record.external_run_id
        intent.trust_level = evaluation.trust_level
        intent.completed_at = now

        if parsed.get("success"):
            intent.status = ExecutionIntentStatus.SUCCEEDED
        elif parsed.get("output"):
            intent.status = ExecutionIntentStatus.PARTIAL
        else:
            intent.status = ExecutionIntentStatus.FAILED
            intent.error_category = "execution_failed"
            intent.error_message = parsed.get("error_message")

        task = await self._get_user_task(task_id=intent.task_id, user_id=intent.user_id)
        task.execution_mode = intent.execution_mode.value

        if evaluation.can_update_task and parsed.get("success"):
            await self._complete_task_safely(task=task, intent=intent, parsed=parsed)
            if intent.plan_id:
                await self._create_plan_execution_record(intent=intent, parsed=parsed, evaluation=evaluation)
        else:
            self._db.add(task)

        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await event_bus.publish(
            EXECUTION_RESULT_INGESTED,
            {
                "event_type": EXECUTION_RESULT_INGESTED,
                "user_id": str(intent.user_id),
                "execution_intent_id": str(intent.id),
                "execution_record_id": str(record.id),
                "task_id": str(intent.task_id),
                "trust_level": evaluation.trust_level.value,
                "quality_score": evaluation.quality_score,
                "success": bool(parsed.get("success")),
                "error_category": intent.error_category,
                "timestamp": _utcnow().isoformat(),
            },
        )
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.COMPLETED if parsed.get("success") else BackgroundTaskStatus.FAILED,
            progress=1.0,
            progress_message="Execution completed" if parsed.get("success") else "Execution failed",
            result_data={
                "intent_id": str(intent.id),
                "trust_level": evaluation.trust_level.value,
                "status": intent.status.value,
            },
            error_message=intent.error_message,
        )

    async def _complete_task_safely(self, *, task: Task, intent: ExecutionIntent, parsed: dict[str, Any]) -> None:
        task.status = TaskStatus.COMPLETED
        task.completed_at = _utcnow()
        task.actual_minutes = 0
        if not task.user_note:
            task.user_note = "Completed by delegated OpenClaw execution"
        self._db.add(task)

        if task.plan_id:
            from app.services.plan_service import PlanService
            from app.services.task_state_sync import TaskStateSyncService

            await self._db.commit()
            await self._db.refresh(task)
            await PlanService.update_progress(self._db, task.plan_id, task.user_id)
            sync_service = TaskStateSyncService(self._db, self._redis)
            await sync_service.on_task_completed(task, actual_minutes=task.actual_minutes)
        else:
            await self._db.commit()
            await self._db.refresh(task)

    async def _create_plan_execution_record(
        self,
        *,
        intent: ExecutionIntent,
        parsed: dict[str, Any],
        evaluation: TrustEvaluation,
    ) -> None:
        if not intent.plan_id:
            return

        validation_status = "passed" if parsed.get("success") else "partial" if parsed.get("output") else "failed"
        issues = list(evaluation.reasons) + list(evaluation.blocked_fields)
        await self._plan_record_service.create_record(
            plan_id=intent.plan_id,
            user_id=intent.user_id,
            validation_status=validation_status,
            quality_score=evaluation.quality_score,
            criteria_results={
                "trust_level": evaluation.trust_level.value,
                "validation_passed": evaluation.validation_passed,
                "validation_total": evaluation.validation_total,
            },
            tool_summary={
                "total": parsed.get("tool_calls_count", 0),
                "successful": parsed.get("tool_calls_count", 0) if parsed.get("success") else 0,
                "failed": 0 if parsed.get("success") else parsed.get("tool_calls_count", 0),
            },
            issues=issues,
        )

    async def _mark_intent_failure(
        self,
        *,
        intent: ExecutionIntent,
        status: ExecutionIntentStatus,
        error_category: str,
        error_message: str,
    ) -> None:
        old_status = intent.status
        intent.status = status
        intent.error_category = error_category
        intent.error_message = error_message
        intent.completed_at = _utcnow()
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.FAILED,
            progress=1.0,
            progress_message=error_message,
            error_message=error_message,
        )
        degraded = self._record_failure(intent.user_id)
        if degraded:
            task = await self._get_user_task(task_id=intent.task_id, user_id=intent.user_id)
            task.execution_mode = ExecutionMode.HUMAN.value
            self._db.add(task)
            await self._db.commit()

    async def _publish_status_event(
        self,
        intent: ExecutionIntent,
        *,
        old_status: ExecutionIntentStatus | None,
    ) -> None:
        await event_bus.publish(
            EXECUTION_STATUS_CHANGED,
            {
                "event_type": EXECUTION_STATUS_CHANGED,
                "user_id": str(intent.user_id),
                "execution_intent_id": str(intent.id),
                "task_id": str(intent.task_id),
                "old_status": old_status.value if old_status else None,
                "new_status": intent.status.value,
                "trust_level": intent.trust_level.value if intent.trust_level else None,
                "timestamp": _utcnow().isoformat(),
            },
        )

    async def _publish_monitor_progress(
        self,
        *,
        intent: ExecutionIntent,
        status: BackgroundTaskStatus,
        progress: float,
        progress_message: str,
        result_data: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        try:
            await task_monitor_service.publish_progress(
                user_id=intent.user_id,
                task_type=BackgroundTaskType.AI_GENERATION,
                name=f"OpenClaw execution for task {intent.task_id}",
                status=status,
                progress=progress,
                progress_message=progress_message,
                external_task_id=str(intent.id),
                related_entity_id=intent.task_id,
                related_entity_type="task",
                result_data=result_data,
                error_message=error_message,
            )
        except Exception as exc:
            logger.warning("Failed to publish execution task monitor progress: {}", exc)

    @staticmethod
    def _terminal_statuses() -> set[ExecutionIntentStatus]:
        return {
            ExecutionIntentStatus.SUCCEEDED,
            ExecutionIntentStatus.PARTIAL,
            ExecutionIntentStatus.FAILED,
            ExecutionIntentStatus.CANCELED,
            ExecutionIntentStatus.TIMED_OUT,
            ExecutionIntentStatus.HANDED_BACK,
        }

    def get_degradation_snapshot(self) -> dict[str, Any]:
        self._cleanup_degradation_state()
        return {
            "degraded_user_count": len(self.__class__._degraded_users),
            "failure_counts": dict(self.__class__._failure_counts),
            "degraded_users": dict(self.__class__._degraded_users),
            "degradation_threshold": self.__class__._degradation_threshold,
            "degradation_window_seconds": self.__class__._degradation_window_seconds,
        }

    def _is_user_degraded(self, user_id: UUID) -> bool:
        self._cleanup_degradation_state()
        return str(user_id) in self.__class__._degraded_users

    def _record_failure(self, user_id: UUID) -> bool:
        self._cleanup_degradation_state()
        key = str(user_id)
        next_count = self.__class__._failure_counts.get(key, 0) + 1
        self.__class__._failure_counts[key] = next_count
        if next_count >= self.__class__._degradation_threshold:
            self.__class__._degraded_users[key] = time.time() + self.__class__._degradation_window_seconds
            return True
        return False

    def _clear_failure_state(self, user_id: UUID) -> None:
        key = str(user_id)
        self.__class__._failure_counts.pop(key, None)
        self.__class__._degraded_users.pop(key, None)

    def _cleanup_degradation_state(self) -> None:
        now = time.time()
        expired = [
            key
            for key, expires_at in self.__class__._degraded_users.items()
            if expires_at <= now
        ]
        for key in expired:
            self.__class__._degraded_users.pop(key, None)
            self.__class__._failure_counts.pop(key, None)
