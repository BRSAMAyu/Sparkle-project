from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.schemas import ExecutablePlan
from app.orchestration.sufficiency_checker import SufficiencyStatus, sufficiency_checker
from app.orchestration.goal_quality_evaluator import goal_quality_evaluator
from app.orchestration.tool_result_extractor import ToolResultExtractor
from app.orchestration.statechart_engine import WorkflowState
from app.services.plan_execution_record_service import PlanExecutionRecordService
from app.services.plan_execution_validator import PlanExecutionValidator
from app.services.perceptible_intelligence_service import ProgressComparisonService
from app.services.system_update_service import SystemUpdateService, build_system_update


class ValidationEngineMixin:
    """Mixin providing request validation, sufficiency checking, goal quality
    evaluation, and plan-execution validation capabilities.

    Designed to be mixed into the main Orchestrator class.  Methods reference
    ``self.validator``, ``self.redis``, and several helper methods that live on
    the orchestrator (``_check_idempotency``, ``_publish_execution_feedback``).
    """

    # ------------------------------------------------------------------
    # Proto request validation
    # ------------------------------------------------------------------

    async def _validate_request(
        self,
        request: agent_service_pb2.ChatRequest,
        *,
        response_id: str,
        request_id: str,
    ) -> agent_service_pb2.ChatResponse | None:
        if not self.validator:
            return None
        validation_result = await self.validator.validate_chat_request(request)
        if validation_result.is_valid:
            return None
        logger.error(f"Validation failed: {validation_result.error_message}")
        return agent_service_pb2.ChatResponse(
            response_id=response_id,
            created_at=int(datetime.now().timestamp()),
            request_id=request_id,
            error=agent_service_pb2.Error(
                message=validation_result.error_message,
                retryable=False,
                error_code=agent_service_pb2.ERROR_CODE_INVALID_ARGUMENT,
            ),
            finish_reason=agent_service_pb2.ERROR,
        )

    # ------------------------------------------------------------------
    # Idempotency check with response generation
    # ------------------------------------------------------------------

    async def _check_idempotency_response(
        self,
        *,
        session_id: str,
        request_id: str,
        response_id: str,
    ) -> agent_service_pb2.ChatResponse | None:
        cached_response = await self._check_idempotency(session_id, request_id)
        if not cached_response:
            return None
        logger.info(f"Cache hit for session {session_id}, request {request_id}")
        cached_metadata = cached_response.get("metadata") if isinstance(cached_response, dict) else None
        metadata_map = {}
        if isinstance(cached_metadata, dict):
            metadata_map = {str(k): str(v) for k, v in cached_metadata.items()}
        return agent_service_pb2.ChatResponse(
            response_id=response_id,
            created_at=int(datetime.now().timestamp()),
            request_id=request_id,
            full_text=cached_response.get("full_text") or cached_response.get("message", ""),
            metadata=metadata_map,
            finish_reason=agent_service_pb2.STOP,
        )

    # ------------------------------------------------------------------
    # Sufficiency checking
    # ------------------------------------------------------------------

    async def _check_sufficiency(
        self,
        *,
        request: agent_service_pb2.ChatRequest,
        user_message: str,
        user_id: str,
        plan_id: uuid.UUID | None,
        conversation_context: dict[str, Any] | None,
        stream_callback,
        queue,
    ) -> tuple[bool, str]:
        from app.services.shadow_prediction_service import shadow_prediction_service

        if request.HasField("tool_result"):
            return False, ""
        try:
            prediction = await shadow_prediction_service.predict_intent_only(
                user_message=user_message,
                active_plan_id=str(plan_id) if plan_id else None,
                user_id=user_id,
            )
            intent_type = prediction.get("intent_type", "unknown")
            extracted_entities = self._build_sufficiency_entities(
                intent_type=intent_type,
                user_message=user_message,
                prediction=prediction,
            )
            check_result = await sufficiency_checker.check(
                intent=intent_type,
                extracted_entities=extracted_entities,
                conversation_context=(conversation_context or {}).get("messages", []),
                user_message=user_message,
                use_llm_fallback=intent_type in {"create_plan", "time_planning"},
            )

            if check_result.status == SufficiencyStatus.NEED_CLARIFICATION:
                questions = check_result.clarification_questions
                if check_result.clarification_text:
                    questions = [check_result.clarification_text]
                question_text = "\n".join([f"- {q}" for q in questions if q]) if questions else "- 请补充更多关键信息"
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=f"我需要更多信息来帮您：\n\n{question_text}\n\n请提供以上信息，我将为您处理。",
                    metadata={
                        "requires_clarification": "true",
                        "missing_fields": ",".join(check_result.missing_fields),
                    },
                ))
                await stream_callback(agent_service_pb2.ChatResponse(finish_reason=agent_service_pb2.STOP))
                return True, intent_type

            if check_result.status == SufficiencyStatus.NEED_CONFIRMATION:
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=check_result.confirmation_message,
                    metadata={"requires_confirmation": "true"},
                ))
                await stream_callback(agent_service_pb2.ChatResponse(finish_reason=agent_service_pb2.STOP))
                return True, intent_type
        except Exception as e:
            logger.warning(f"Sufficiency check failed, continuing: {e}")
        return False, intent_type if 'intent_type' in locals() else ""

    # ------------------------------------------------------------------
    # Build sufficiency entities
    # ------------------------------------------------------------------

    def _build_sufficiency_entities(
        self,
        *,
        intent_type: str,
        user_message: str,
        prediction: dict[str, Any],
    ) -> dict[str, Any]:
        extracted_entities = {
                "intent_type": intent_type,
                "suggested_tools": prediction.get("suggested_tools", []),
            }
        normalized_message = user_message.strip()
        msg_lower = normalized_message.lower()

        if intent_type == "knowledge_query" and normalized_message:
            extracted_entities["query"] = normalized_message

        if intent_type in {"create_plan", "time_planning"} and normalized_message:
            extracted_entities["plan_title"] = normalized_message
            if any(keyword in msg_lower for keyword in ["冲刺", "突击", "期末", "考试", "sprint", "exam"]):
                extracted_entities["plan_type"] = "sprint"
            elif any(keyword in msg_lower for keyword in ["长期", "成长", "习惯", "体系", "long-term", "growth"]):
                extracted_entities["plan_type"] = "growth"
            elif "计划" in normalized_message or "复习" in normalized_message:
                extracted_entities["plan_type"] = "growth"

        if intent_type == "task_management" and normalized_message:
            extracted_entities["task_title"] = normalized_message

        return extracted_entities

    # ------------------------------------------------------------------
    # Goal quality checking
    # ------------------------------------------------------------------

    async def _check_goal_quality(
        self,
        *,
        intent_type: str,
        user_message: str,
        user_id: str,
        plan_id: uuid.UUID | None,
        active_db: AsyncSession | None,
        conversation_context: dict[str, Any] | None,
        stream_callback,
        state: WorkflowState,
    ) -> bool:
        if intent_type not in {"create_plan", "set_goal"}:
            state.context_data["goal_quality"] = {"passed": True, "skipped": True}
            return False

        if active_db and plan_id:
            try:
                from app.services.plan_state_service import PlanStateService

                plan_state = await PlanStateService(active_db, self.redis).get_plan_state(
                    uuid.UUID(user_id),
                    plan_id,
                )
                goal_quality = ((plan_state.facts or {}).get("goal_quality")) if plan_state else None
                if isinstance(goal_quality, dict) and goal_quality.get("passed") is True:
                    state.context_data["goal_quality"] = goal_quality
                    return False
            except Exception as e:
                logger.warning(f"Failed to load goal quality mark from plan state: {e}")

        evaluation = await goal_quality_evaluator.evaluate(
            user_message=user_message,
            intent=intent_type,
            conversation_context=(conversation_context or {}).get("messages", []),
        )
        state.context_data["goal_quality"] = evaluation.to_dict()

        if not evaluation.passed:
            question_text = "\n".join(
                f"- {question}" for question in evaluation.clarification_questions if question
            ) or "- 请把目标再说具体一点"
            await stream_callback(
                agent_service_pb2.ChatResponse(
                    delta=(
                        "我想先把目标收紧到足够可执行，再开始做计划：\n\n"
                        f"{question_text}\n\n"
                        "你补充这些信息后，我就能给你更靠谱的阶段方案。"
                    ),
                    metadata={
                        "requires_goal_clarification": "true",
                        "goal_quality_scores": json.dumps(evaluation.scores.to_dict(), ensure_ascii=False),
                    },
                )
            )
            await stream_callback(agent_service_pb2.ChatResponse(finish_reason=agent_service_pb2.STOP))
            return True

        if active_db and plan_id:
            try:
                from app.services.plan_state_service import PlanStateService

                await PlanStateService(active_db, self.redis).upsert_plan_state(
                    user_id=uuid.UUID(user_id),
                    plan_id=plan_id,
                    patch={"facts": {"goal_quality": evaluation.to_dict()}},
                    bump_version=False,
                )
            except Exception as e:
                logger.warning(f"Failed to persist goal quality mark: {e}")

        return False

    # ------------------------------------------------------------------
    # Plan execution validation
    # ------------------------------------------------------------------

    async def _validate_plan_execution(
        self,
        *,
        executable_plan: ExecutablePlan | None,
        active_db: AsyncSession | None,
        final_state: WorkflowState,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any] | None:
        if not executable_plan or not hasattr(executable_plan, "plan_id") or not active_db:
            return None
        try:
            record_service = PlanExecutionRecordService(active_db)
            execution_validator = PlanExecutionValidator(record_service=record_service)
            plan_result = final_state.context_data.get("plan_execution_result")

            if plan_result is not None and hasattr(plan_result, "step_results"):
                adaptation_records: list[dict[str, Any]] = []
                validation_result = await execution_validator.validate_plan_execution(
                    plan=executable_plan,
                    plan_result=plan_result,
                    user_id=uuid.UUID(user_id),
                )
                adaptation_records = await self._publish_execution_feedback(
                    active_db=active_db,
                    executable_plan=executable_plan,
                    plan_result=plan_result,
                    validation_result=validation_result,
                    user_id=user_id,
                    session_id=session_id,
                )
                if adaptation_records:
                    final_state.context_data["adaptation_records"] = adaptation_records
                if (
                    settings.ENABLE_PERCEPTIBLE_INTELLIGENCE
                    and settings.ENABLE_PROGRESS_COMPARISONS
                    and validation_result.validation_status == "passed"
                ):
                    try:
                        comparison = await ProgressComparisonService(active_db).build_best_comparison(
                            user_id=uuid.UUID(user_id),
                            plan_id=uuid.UUID(str(executable_plan.plan_id)),
                        )
                        if comparison:
                            await SystemUpdateService(getattr(self, "redis", None)).enqueue(
                                user_id,
                                build_system_update(
                                    update_type="progress_comparison",
                                    category="evolution",
                                    title="你和之前相比，已经不是同一种推进状态了",
                                    description=str(comparison.get("delta_text") or ""),
                                    priority="medium",
                                    metadata={
                                        "evolution_kind": "progress_comparison",
                                        "comparison": comparison,
                                        "headline": "你和之前相比，已经不是同一种推进状态了",
                                        "summary": str(comparison.get("delta_text") or ""),
                                        "evidence_summary": str(comparison.get("evidence_summary") or ""),
                                        "period_range": str(comparison.get("period_range") or ""),
                                        "evidence_source": str(comparison.get("source") or "comparison"),
                                        "confidence_tier": "inferred",
                                    },
                                ),
                            )
                            EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL.labels(kind="progress_comparison").inc()
                    except Exception as exc:
                        logger.warning(f"Failed to enqueue progress comparison: {exc}")
                logger.info(
                    "DAG plan execution validation: plan_id={} status={} score={:.2f} steps={} aborted={}",
                    validation_result.plan_id,
                    validation_result.validation_status,
                    validation_result.quality_score,
                    len(getattr(validation_result, "step_validations", []) or []),
                    getattr(validation_result, "aborted", False),
                )
                return {
                    "validation_status": validation_result.validation_status,
                    "quality_score": validation_result.quality_score,
                    "tools_total": validation_result.tool_summary.get("total", 0),
                    "tools_successful": validation_result.tool_summary.get("successful", 0),
                    "steps_total": len(getattr(validation_result, "step_validations", []) or []),
                    "steps_passed": sum(1 for sv in (getattr(validation_result, "step_validations", []) or []) if sv.passed),
                    "aborted": bool(getattr(validation_result, "aborted", False)),
                }

            tool_extractor = ToolResultExtractor()
            tool_results = tool_extractor.extract_from_messages(final_state.messages)
            if not (tool_results or executable_plan.tool_calls):
                return None

            validation_result = await execution_validator.validate_and_record(
                plan=executable_plan,
                tool_results=tool_results,
                user_id=uuid.UUID(user_id),
            )
            logger.info(
                f"Plan execution validation: plan_id={validation_result.plan_id}, "
                f"validation_status={validation_result.validation_status}, "
                f"score={validation_result.quality_score:.2f}"
            )
            return {
                "validation_status": validation_result.validation_status,
                "quality_score": validation_result.quality_score,
                "tools_total": validation_result.tool_summary.get("total", 0),
                "tools_successful": validation_result.tool_summary.get("successful", 0),
            }
        except Exception as e:
            logger.warning(f"Plan execution validation failed: {e}", exc_info=True)
            return None
