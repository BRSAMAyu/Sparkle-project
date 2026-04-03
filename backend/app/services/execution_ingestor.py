"""Execution ingestion service for Phase 2 OpenClaw integration."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.openclaw.result_parser import ResultParser
from app.config import settings
from app.core.event_bus import event_bus
from app.core.event_types import (
    EXECUTION_APPROVAL_DECISION,
    EXECUTION_HANDED_BACK,
    EXECUTION_QUALITY_RECORDED,
    EXECUTION_RESULT_INGESTED,
    EXECUTION_STATUS_CHANGED,
    EXECUTION_WAITING_APPROVAL,
)
from app.core.execution_trust import ExecutionTrustEngine, TrustEvaluation
from app.core.task_monitor import task_monitor_service
from app.models.background_task import BackgroundTaskStatus, BackgroundTaskType
from app.models.execution_intent import ExecutionIntent, ExecutionIntentStatus, ExecutionMode, TrustLevel
from app.models.execution_record import ExecutionRecord
from app.models.task import Task, TaskStatus
from app.services.execution_learning_service import ExecutionLearningService
from app.services.execution_quality_service import ExecutionQualityService
from app.services.execution_result_validator import ExecutionResultValidator
from app.services.plan_execution_record_service import PlanExecutionRecordService

DELEGATED_COMPLETION_NOTE = "Completed by delegated OpenClaw execution"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExecutionIngestor:
    """All external execution results must pass through this service."""

    def __init__(self, db: AsyncSession, redis=None):
        self._db = db
        self._redis = redis
        self._parser = ResultParser()
        self._trust_engine = ExecutionTrustEngine(
            auto_trust_min_history=settings.OPENCLAW_TRUST_AUTO_PROMOTE_MIN_HISTORY,
            auto_trust_success_rate=settings.OPENCLAW_TRUST_AUTO_PROMOTE_SUCCESS_RATE,
        )
        self._plan_record_service = PlanExecutionRecordService(db)
        self._learning_service = ExecutionLearningService(db=db, redis=redis)
        self._quality_service = ExecutionQualityService(db)
        self._result_validator = ExecutionResultValidator()

    async def ingest(
        self,
        *,
        intent: ExecutionIntent,
        raw_result: dict[str, Any],
        user_confirmed: bool = False,
    ) -> ExecutionRecord:
        parsed = self._parser.parse(raw_result)
        parsed = self._validate_parsed_output_contract(parsed=parsed, result_contract=intent.result_contract or {})
        parsed = self._apply_local_hybrid_gate(intent=intent, parsed=parsed, user_confirmed=user_confirmed)
        parsed_for_evaluation = (
            self._materialize_confirmed_result(parsed)
            if user_confirmed
            else parsed
        )
        evaluation = self._evaluate(intent=intent, parsed=parsed_for_evaluation)
        if user_confirmed and evaluation.trust_level != TrustLevel.TRUSTED:
            evaluation = replace(
                evaluation,
                trust_level=TrustLevel.TRUSTED,
            )

        record = await self._upsert_execution_record(
            intent=intent,
            raw_response=raw_result,
            parsed=parsed_for_evaluation,
            evaluation=evaluation,
            approval_increment=parsed.get("approval_requests", 0),
        )

        if parsed.get("requires_approval") and not user_confirmed:
            await self._mark_waiting_approval(
                intent=intent,
                record=record,
                parsed=parsed,
                evaluation=evaluation,
            )
            return record

        await self._apply_execution_result(
            intent=intent,
            parsed=parsed_for_evaluation,
            evaluation=evaluation,
            record=record,
            user_confirmed=user_confirmed,
        )
        return record

    async def confirm_result(
        self,
        *,
        record_id: UUID,
        user_id: UUID,
    ) -> ExecutionRecord:
        record = await self._get_user_record(record_id=record_id, user_id=user_id)
        intent = await self._get_user_intent(intent_id=record.execution_intent_id, user_id=user_id)

        if record.trust_level == TrustLevel.TRUSTED.value and intent.trust_level == TrustLevel.TRUSTED:
            return record

        parsed = self._materialize_confirmed_result(self._parser.parse(record.raw_response or {}))
        evaluation = self._evaluate(intent=intent, parsed=parsed)
        if evaluation.trust_level != TrustLevel.TRUSTED:
            evaluation = replace(
                evaluation,
                trust_level=TrustLevel.TRUSTED,
            )

        record = await self._upsert_execution_record(
            intent=intent,
            raw_response=record.raw_response or {},
            parsed=parsed,
            evaluation=evaluation,
            approval_increment=0,
            existing_record=record,
        )

        if intent.status == ExecutionIntentStatus.WAITING_APPROVAL:
            await self._apply_execution_result(
                intent=intent,
                parsed=parsed,
                evaluation=evaluation,
                record=record,
                user_confirmed=True,
            )
        else:
            old_status = intent.status
            intent.trust_level = TrustLevel.TRUSTED
            self._db.add(intent)
            await self._db.commit()
            await self._db.refresh(intent)
            await self._publish_status_event(intent, old_status=old_status)
            await self._publish_result_ingested_event(
                intent=intent,
                record=record,
                trust_level=TrustLevel.TRUSTED,
                success=bool(parsed.get("success")),
                error_category=intent.error_category,
            )
            if parsed.get("success"):
                await self._learning_service.handle_trusted_execution(
                    intent=intent,
                    record=record,
                    parsed=parsed,
                )

        await event_bus.publish(
            EXECUTION_APPROVAL_DECISION,
            {
                "event_type": EXECUTION_APPROVAL_DECISION,
                "user_id": str(user_id),
                "execution_intent_id": str(intent.id),
                "execution_record_id": str(record.id),
                "task_id": str(intent.task_id),
                "approved": True,
                "timestamp": _utcnow().isoformat(),
            },
        )
        await self._learning_service.handle_approval_speed_signal(
            intent=intent,
            record=record,
            approved=True,
        )
        await self._learning_service.handle_task_type_delegation_tendency(
            user_id=user_id,
            task_type=intent.target_env.value if intent.target_env else "general",
        )
        await self._learning_service.handle_quality_sensitivity(
            intent=intent,
            record=record,
            approved=True,
        )
        return record

    async def reject_result(
        self,
        *,
        record_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> ExecutionRecord:
        record = await self._get_user_record(record_id=record_id, user_id=user_id)
        intent = await self._get_user_intent(intent_id=record.execution_intent_id, user_id=user_id)
        task = None
        if not self._should_skip_task_sync(intent):
            task = await self._get_user_task(task_id=intent.task_id, user_id=user_id)
            await self._rollback_task_if_needed(task)

        old_status = intent.status
        intent.status = ExecutionIntentStatus.HANDED_BACK
        intent.completed_at = _utcnow()
        intent.error_category = "user_rejected"
        intent.error_message = reason or "Rejected by user"
        intent.trust_level = TrustLevel.RAW
        if task is not None:
            task.execution_mode = "human"

        record.trust_level = TrustLevel.RAW.value
        record.error_category = "user_rejected"
        record.error_message = reason or "Rejected by user"

        if task is not None:
            self._db.add(task)
        self._db.add(intent)
        self._db.add(record)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._db.refresh(record)

        await self._publish_status_event(intent, old_status=old_status)
        await event_bus.publish(
            EXECUTION_APPROVAL_DECISION,
            {
                "event_type": EXECUTION_APPROVAL_DECISION,
                "user_id": str(user_id),
                "execution_intent_id": str(intent.id),
                "execution_record_id": str(record.id),
                "task_id": str(intent.task_id),
                "approved": False,
                "reason": reason,
                "timestamp": _utcnow().isoformat(),
            },
        )
        await event_bus.publish(
            EXECUTION_HANDED_BACK,
            {
                "event_type": EXECUTION_HANDED_BACK,
                "user_id": str(user_id),
                "execution_intent_id": str(intent.id),
                "task_id": str(intent.task_id),
                "reason": reason,
                "progress_at_handback": 1.0 if task is not None and task.status == TaskStatus.IN_PROGRESS else 0.0,
                "timestamp": _utcnow().isoformat(),
            },
        )
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.CANCELLED,
            progress=1.0,
            progress_message="Execution rejected and returned to user",
            error_message=intent.error_message,
        )
        await self._learning_service.handle_handed_back(
            intent=intent,
            record=record,
            reason=reason,
        )
        await self._learning_service.handle_approval_speed_signal(
            intent=intent,
            record=record,
            approved=False,
        )
        await self._learning_service.handle_task_type_delegation_tendency(
            user_id=user_id,
            task_type=intent.target_env.value if intent.target_env else "general",
        )
        await self._learning_service.handle_quality_sensitivity(
            intent=intent,
            record=record,
            approved=False,
        )
        await self._learning_service.handle_rejection_sentiment(
            intent=intent,
            record=record,
            reason=reason,
        )
        await self._quality_service.record_outcome(
            intent=intent,
            record=record,
            outcome="handed_back",
        )
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
        return record

    def _evaluate(
        self,
        *,
        intent: ExecutionIntent,
        parsed: dict[str, Any],
    ) -> TrustEvaluation:
        return self._trust_engine.evaluate(
            raw_result=self._build_evaluation_input(parsed),
            success_criteria=intent.success_criteria or {},
            result_contract=intent.result_contract or {},
            executor_history=None,
        )

    async def _upsert_execution_record(
        self,
        *,
        intent: ExecutionIntent,
        raw_response: dict[str, Any],
        parsed: dict[str, Any],
        evaluation: TrustEvaluation,
        approval_increment: int,
        existing_record: ExecutionRecord | None = None,
    ) -> ExecutionRecord:
        record = existing_record
        if record is None:
            result = await self._db.execute(
                select(ExecutionRecord).where(ExecutionRecord.execution_intent_id == intent.id)
            )
            record = result.scalar_one_or_none()
        if record is None:
            record = ExecutionRecord(
                execution_intent_id=intent.id,
                user_id=intent.user_id,
                task_id=intent.task_id,
            )

        record.executor_type = intent.executor.value
        record.external_run_id = raw_response.get("id") or record.external_run_id
        enriched_raw_response = dict(raw_response)
        quality_warnings = self._result_validator.validate(
            parsed=parsed,
            result_contract=intent.result_contract or {},
        )
        if (intent.policy or {}).get("contains_sensitive_data") is True and all(
            str(item.get("code") or "") != "contains_sensitive_data"
            for item in quality_warnings
            if isinstance(item, dict)
        ):
            risk = (intent.policy or {}).get("_risk_assessment")
            matches = []
            if isinstance(risk, dict):
                matches = [
                    item.get("label")
                    for item in list(risk.get("sensitive_signals") or [])
                    if isinstance(item, dict) and str(item.get("label") or "").strip()
                ]
            label_suffix = f"（{', '.join(matches[:3])}）" if matches else ""
            quality_warnings.append(
                {
                    "code": "contains_sensitive_data",
                    "severity": "warning",
                    "message": f"本次执行涉及敏感数据{label_suffix}，请确认执行环境和结果回传链路是安全的。",
                }
            )
        enriched_raw_response["_sparkle_quality_warnings"] = quality_warnings
        record.raw_response = enriched_raw_response
        record.parsed_output = parsed.get("parsed_output")
        record.artifacts = parsed.get("artifacts", [])
        record.trust_level = evaluation.trust_level.value
        record.validation_passed = evaluation.validation_passed
        record.validation_total = evaluation.validation_total
        record.quality_score = evaluation.quality_score
        record.token_usage = parsed.get("token_usage")
        record.tool_calls_count = parsed.get("tool_calls_count", 0)
        record.approval_requested = (record.approval_requested or 0) + approval_increment
        if parsed.get("requires_approval"):
            record.error_category = "approval_required"
        else:
            record.error_category = None if parsed.get("success") else record.error_category or "execution_failed"
        record.error_message = parsed.get("error_message")
        record.execution_started_at = intent.dispatched_at
        record.execution_completed_at = _utcnow()
        if intent.dispatched_at:
            record.duration_ms = max(
                0,
                int((record.execution_completed_at - intent.dispatched_at).total_seconds() * 1000),
            )
        self._db.add(record)
        await self._db.commit()
        await self._db.refresh(record)
        return record

    async def _mark_waiting_approval(
        self,
        *,
        intent: ExecutionIntent,
        record: ExecutionRecord,
        parsed: dict[str, Any],
        evaluation: TrustEvaluation,
    ) -> None:
        old_status = intent.status
        intent.status = ExecutionIntentStatus.WAITING_APPROVAL
        intent.external_run_id = record.external_run_id
        intent.trust_level = evaluation.trust_level
        intent.error_category = "approval_required"
        intent.error_message = parsed.get("error_message") or "Waiting for user approval"
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)

        await self._publish_status_event(intent, old_status=old_status)
        await event_bus.publish(
            EXECUTION_WAITING_APPROVAL,
            {
                "event_type": EXECUTION_WAITING_APPROVAL,
                "user_id": str(intent.user_id),
                "execution_intent_id": str(intent.id),
                "execution_record_id": str(record.id),
                "task_id": str(intent.task_id),
                "approval_requested": record.approval_requested,
                "timestamp": _utcnow().isoformat(),
            },
        )
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.RUNNING,
            progress=0.85,
            progress_message="Waiting for approval",
            result_data={
                "intent_id": str(intent.id),
                "status": intent.status.value,
                "trust_level": evaluation.trust_level.value,
            },
            error_message=intent.error_message,
        )

    async def _apply_execution_result(
        self,
        *,
        intent: ExecutionIntent,
        parsed: dict[str, Any],
        evaluation: TrustEvaluation,
        record: ExecutionRecord,
        user_confirmed: bool,
    ) -> None:
        old_status = intent.status
        now = _utcnow()

        intent.external_run_id = record.external_run_id
        intent.trust_level = TrustLevel.TRUSTED if user_confirmed else evaluation.trust_level
        intent.completed_at = now
        intent.error_category = None
        intent.error_message = None

        if parsed.get("success"):
            intent.status = ExecutionIntentStatus.SUCCEEDED
        elif parsed.get("output"):
            intent.status = ExecutionIntentStatus.PARTIAL
        else:
            intent.status = ExecutionIntentStatus.FAILED
            intent.error_category = "execution_failed"
            intent.error_message = parsed.get("error_message")

        task = None
        if not self._should_skip_task_sync(intent):
            task = await self._get_user_task(task_id=intent.task_id, user_id=intent.user_id)
            task.execution_mode = intent.execution_mode.value

            if (evaluation.can_update_task or user_confirmed) and parsed.get("success"):
                await self._complete_task_safely(task=task)
                if intent.plan_id:
                    await self._create_plan_execution_record(
                        intent=intent,
                        parsed=parsed,
                        evaluation=evaluation,
                        trust_level=intent.trust_level,
                    )
            else:
                self._db.add(task)

        record.trust_level = intent.trust_level.value
        self._db.add(record)
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._db.refresh(record)

        await self._publish_status_event(intent, old_status=old_status)
        await self._publish_result_ingested_event(
            intent=intent,
            record=record,
            trust_level=intent.trust_level,
            success=bool(parsed.get("success")),
            error_category=intent.error_category,
        )
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.COMPLETED if parsed.get("success") else BackgroundTaskStatus.FAILED,
            progress=1.0,
            progress_message="Execution completed" if parsed.get("success") else "Execution failed",
            result_data={
                "intent_id": str(intent.id),
                "trust_level": intent.trust_level.value,
                "status": intent.status.value,
            },
            error_message=intent.error_message,
        )
        if intent.trust_level == TrustLevel.TRUSTED and parsed.get("success"):
            await self._learning_service.handle_trusted_execution(
                intent=intent,
                record=record,
                parsed=parsed,
            )
        await self._quality_service.record_outcome(
            intent=intent,
            record=record,
            outcome=intent.status.value,
        )
        await event_bus.publish(
            EXECUTION_QUALITY_RECORDED,
            {
                "event_type": EXECUTION_QUALITY_RECORDED,
                "user_id": str(intent.user_id),
                "execution_intent_id": str(intent.id),
                "execution_record_id": str(record.id),
                "variant_name": ((intent.policy or {}).get("quality_strategy") or {}).get("variant_name"),
                "outcome": intent.status.value,
                "quality_score": record.quality_score,
                "timestamp": _utcnow().isoformat(),
            },
        )

    async def _complete_task_safely(self, *, task: Task) -> None:
        task.status = TaskStatus.COMPLETED
        task.completed_at = _utcnow()
        task.actual_minutes = 0
        if not task.user_note:
            task.user_note = DELEGATED_COMPLETION_NOTE
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
        trust_level: TrustLevel,
    ) -> None:
        validation_status = "passed" if parsed.get("success") else "partial" if parsed.get("output") else "failed"
        issues = list(evaluation.reasons) + list(evaluation.blocked_fields)
        await self._plan_record_service.create_record(
            plan_id=intent.plan_id,
            user_id=intent.user_id,
            validation_status=validation_status,
            quality_score=evaluation.quality_score,
            criteria_results={
                "trust_level": trust_level.value,
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

    async def _rollback_task_if_needed(self, task: Task) -> None:
        if task.status != TaskStatus.COMPLETED:
            self._db.add(task)
            return

        task.status = TaskStatus.IN_PROGRESS
        task.completed_at = None
        task.actual_minutes = None
        if task.user_note == DELEGATED_COMPLETION_NOTE:
            task.user_note = None
        self._db.add(task)

    async def _get_user_intent(self, *, intent_id: UUID, user_id: UUID) -> ExecutionIntent:
        intent = await self._db.get(ExecutionIntent, intent_id)
        if not intent or intent.user_id != user_id or intent.deleted_at is not None:
            raise ValueError("Execution intent not found")
        return intent

    async def _get_user_task(self, *, task_id: UUID, user_id: UUID) -> Task:
        task = await self._db.get(Task, task_id)
        if not task or task.user_id != user_id or task.deleted_at is not None:
            raise ValueError("Task not found")
        return task

    @staticmethod
    def _should_skip_task_sync(intent: ExecutionIntent) -> bool:
        return bool((intent.policy or {}).get("chat_control"))

    async def _get_user_record(self, *, record_id: UUID, user_id: UUID) -> ExecutionRecord:
        result = await self._db.execute(
            select(ExecutionRecord)
            .where(
                ExecutionRecord.id == record_id,
                ExecutionRecord.user_id == user_id,
                ExecutionRecord.deleted_at.is_(None),
            )
            .order_by(desc(ExecutionRecord.created_at))
        )
        record = result.scalar_one_or_none()
        if not record:
            raise ValueError("Execution record not found")
        return record

    def _build_evaluation_input(self, parsed: dict[str, Any]) -> dict[str, Any]:
        evaluation_input = dict(parsed)
        parsed_output = parsed.get("parsed_output")
        if isinstance(parsed_output, dict):
            for key, value in parsed_output.items():
                evaluation_input.setdefault(key, value)
        return evaluation_input

    def _materialize_confirmed_result(self, parsed: dict[str, Any]) -> dict[str, Any]:
        confirmed = dict(parsed)
        confirmed["requires_approval"] = False
        confirmed["approval_requests"] = 0
        confirmed["success"] = True
        confirmed["error_message"] = None
        confirmed["raw_status"] = "confirmed"
        return confirmed

    def _apply_local_hybrid_gate(
        self,
        *,
        intent: ExecutionIntent,
        parsed: dict[str, Any],
        user_confirmed: bool,
    ) -> dict[str, Any]:
        if user_confirmed or intent.execution_mode != ExecutionMode.HYBRID:
            return parsed

        approval_policy = str((intent.policy or {}).get("approval_policy") or "")
        if approval_policy not in {"require_before_completion", "require_for_side_effects"}:
            return parsed
        if not parsed.get("success"):
            return parsed

        gated = dict(parsed)
        gated["requires_approval"] = True
        gated["approval_requests"] = max(int(gated.get("approval_requests") or 0), 1)
        gated["success"] = False
        gated["error_message"] = "Waiting for final user confirmation"
        gated["raw_status"] = "hybrid_review_required"
        return gated

    def _validate_parsed_output_contract(
        self,
        *,
        parsed: dict[str, Any],
        result_contract: dict[str, Any],
    ) -> dict[str, Any]:
        schema = result_contract.get("parsed_output_schema")
        parsed_output = parsed.get("parsed_output")

        if not schema or parsed_output is None:
            return parsed

        if not isinstance(parsed_output, dict):
            updated = dict(parsed)
            updated["output"] = ""
            updated["parsed_output"] = None
            updated["success"] = False
            updated["error_message"] = "parsed_output_schema_invalid:not_object"
            return updated

        required_fields = schema.get("required", []) if isinstance(schema, dict) else []
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        errors: list[str] = []
        for field_name in required_fields:
            if parsed_output.get(field_name) is None:
                errors.append(f"missing:{field_name}")

        for field_name, field_schema in properties.items():
            if not isinstance(field_schema, dict):
                continue
            if field_name not in parsed_output or parsed_output[field_name] is None:
                continue
            schema_type = field_schema.get("type")
            expected_labels: list[str] = []
            expected_types: list[type[Any] | tuple[type[Any], ...]] = []
            if isinstance(schema_type, list):
                for item in schema_type:
                    python_type = type_map.get(item)
                    if python_type:
                        expected_labels.append(str(item))
                        expected_types.append(python_type)
            else:
                python_type = type_map.get(schema_type)
                if python_type:
                    expected_labels.append(str(schema_type))
                    expected_types.append(python_type)
            if expected_types and not isinstance(parsed_output[field_name], tuple(expected_types)):
                errors.append(f"type:{field_name}:{'|'.join(expected_labels)}")

        if not errors:
            return parsed

        updated = dict(parsed)
        updated["output"] = ""
        updated["parsed_output"] = None
        updated["success"] = False
        updated["error_message"] = f"parsed_output_schema_invalid:{','.join(errors)}"
        return updated

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

    async def _publish_result_ingested_event(
        self,
        *,
        intent: ExecutionIntent,
        record: ExecutionRecord,
        trust_level: TrustLevel,
        success: bool,
        error_category: str | None,
    ) -> None:
        await event_bus.publish(
            EXECUTION_RESULT_INGESTED,
            {
                "event_type": EXECUTION_RESULT_INGESTED,
                "user_id": str(intent.user_id),
                "execution_intent_id": str(intent.id),
                "execution_record_id": str(record.id),
                "task_id": str(intent.task_id),
                "trust_level": trust_level.value,
                "quality_score": record.quality_score,
                "success": success,
                "error_category": error_category,
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
        await task_monitor_service.publish_progress(
            user_id=intent.user_id,
            task_type=self._background_task_type_for_intent(intent),
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

    def _background_task_type_for_intent(self, intent: ExecutionIntent) -> BackgroundTaskType:
        return BackgroundTaskType.AI_GENERATION
