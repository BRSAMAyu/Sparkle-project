from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.business_metrics import EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.planning_intent import detect_planning_like_turn
from app.orchestration.schemas import ExecutablePlan
from app.orchestration.sufficiency_checker import SufficiencyStatus, sufficiency_checker
from app.orchestration.goal_quality_evaluator import goal_quality_evaluator
from app.orchestration.tool_result_extractor import ToolResultExtractor
from app.orchestration.statechart_engine import WorkflowState
from app.services.plan_execution_record_service import PlanExecutionRecordService
from app.services.plan_execution_validator import PlanExecutionValidator
from app.services.perceptible_intelligence_service import ProgressComparisonService
from app.services.llm_service import get_configured_llm_service_for_tier
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

    async def _compose_fast_interaction_copy(
        self,
        *,
        user_message: str,
        interaction_type: str,
        fallback_text: str,
        prompts: list[str] | None = None,
    ) -> str:
        if not getattr(settings, "FAST_INTERACTION_COPY_ENABLED", True):
            return fallback_text

        prompt_lines = "\n".join(f"- {item}" for item in (prompts or []) if item)
        prompt = (
            "你是 Sparkle 的快响交互助手。"
            "请用中文输出一段简洁、自然、专业的用户交互文案。"
            "要求：1. 先确认系统已开始处理；2. 明确当前还需要用户提供或确认什么；"
            "3. 语气减少等待焦虑；4. 直接输出正文，不加标题。\n\n"
            f"交互类型：{interaction_type}\n"
            f"用户原话：{user_message}\n"
            f"需要确认/补充的信息：\n{prompt_lines or '- 无'}\n\n"
            f"兜底文案：{fallback_text}"
        )

        try:
            llm = await get_configured_llm_service_for_tier(
                AgentRole.ORCHESTRATOR,
                ModelTier.FAST,
                task_type=TaskType.ROUTING,
            )
            response = await llm.chat(
                [
                    {
                        "role": "system",
                        "content": "你是 Sparkle 的快响交互助手，只输出用户可见的简洁中文文案。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            cleaned = str(response or "").strip()
            return cleaned or fallback_text
        except Exception as exc:
            logger.debug(f"Fast interaction copy fallback triggered: {exc}")
            return fallback_text

    async def _emit_fast_interaction(
        self,
        *,
        stream_callback,
        text: str,
        details: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        payload = metadata or {}
        await stream_callback(
            agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.THINKING,
                    details=details,
                    current_agent_name="Sparkle Flash",
                ),
                metadata=payload,
            )
        )
        cleaned = str(text or "").strip()
        if cleaned:
            logger.info(
                "Emitting fast interaction copy "
                f"(chars={len(cleaned)}, preview={cleaned[:80]!r})"
            )
            await stream_callback(
                agent_service_pb2.ChatResponse(
                    full_text=cleaned,
                    finish_reason=agent_service_pb2.STOP,
                )
            )
        else:
            logger.warning("Fast interaction copy resolved to empty text")

    @staticmethod
    def _persist_phase_a_evaluation(
        *,
        state: WorkflowState | None,
        user_context_payload: dict[str, Any] | None,
        evaluation: dict[str, Any],
    ) -> None:
        if isinstance(user_context_payload, dict):
            user_context_payload["phase_a_evaluation"] = dict(evaluation)
        if isinstance(state, WorkflowState):
            state.context_data["phase_a_evaluation"] = dict(evaluation)
            existing_user_context = state.context_data.get("user_context")
            if isinstance(existing_user_context, dict):
                existing_user_context["phase_a_evaluation"] = dict(evaluation)

    @staticmethod
    def _normalize_sufficiency_intent_type(
        *,
        intent_type: str,
        user_message: str,
    ) -> str:
        normalized = str(intent_type or "").strip().lower()
        if normalized not in {"create_plan", "time_planning"}:
            return normalized

        message = str(user_message or "").strip()
        advisory_markers = (
            "先学哪个",
            "应该先",
            "怎么选",
            "判断标准",
            "取舍",
            "比较",
            "区别",
            "优先学",
            "值不值得",
        )
        explicit_plan_markers = (
            "制定计划",
            "做计划",
            "生成计划",
            "创建计划",
            "安排一下",
            "排个计划",
            "帮我规划",
            "帮我安排",
            "学习计划",
            "复习计划",
        )

        if any(marker in message for marker in advisory_markers) and not any(
            marker in message for marker in explicit_plan_markers
        ):
            return "knowledge_query"
        return normalized

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
        session_id: str | None,
        conversation_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        state: WorkflowState | None,
        active_db: AsyncSession | None,
        session_feedback_signal: dict[str, Any] | None,
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
            raw_intent_type = str(prediction.get("intent_type", "unknown") or "unknown")
            intent_type = self._normalize_sufficiency_intent_type(
                intent_type=raw_intent_type,
                user_message=user_message,
            )
            logger.info(
                "Sufficiency intent resolved "
                f"(raw={raw_intent_type}, normalized={intent_type}, message={user_message[:80]!r})"
            )
            phase_a_handled = await self._check_phase_a_planning_preflight(
                intent_type=intent_type,
                request=request,
                user_message=user_message,
                user_id=user_id,
                session_id=session_id,
                plan_id=plan_id,
                active_db=active_db,
                user_context_payload=user_context_payload,
                plan_context=plan_context,
                state=state,
                stream_callback=stream_callback,
                session_feedback_signal=session_feedback_signal,
            )
            if phase_a_handled:
                return True, intent_type

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
                tracking_key=":".join(
                    part
                    for part in (
                        user_id,
                        str((conversation_context or {}).get("session_id") or "").strip(),
                        intent_type,
                    )
                    if part
                ) or f"{user_id}:{intent_type}",
            )

            if check_result.status == SufficiencyStatus.NEED_CLARIFICATION:
                questions = check_result.clarification_questions
                if check_result.clarification_text:
                    questions = [check_result.clarification_text]
                question_text = "\n".join([f"- {q}" for q in questions if q]) if questions else "- 请补充更多关键信息"
                fallback_text = f"我需要更多信息来帮您：\n\n{question_text}\n\n请提供以上信息，我将为您处理。"
                interaction_text = await self._compose_fast_interaction_copy(
                    user_message=user_message,
                    interaction_type="clarification",
                    fallback_text=fallback_text,
                    prompts=questions or check_result.missing_fields,
                )
                await self._emit_fast_interaction(
                    stream_callback=stream_callback,
                    text=interaction_text,
                    details="我先快速确认缺失信息，再继续帮你推进。",
                    metadata={
                        "requires_clarification": "true",
                        "missing_fields": ",".join(check_result.missing_fields),
                    },
                )
                return True, intent_type

            if check_result.status == SufficiencyStatus.NEED_CONFIRMATION:
                interaction_text = await self._compose_fast_interaction_copy(
                    user_message=user_message,
                    interaction_type="confirmation",
                    fallback_text=check_result.confirmation_message,
                    prompts=[check_result.confirmation_message],
                )
                await self._emit_fast_interaction(
                    stream_callback=stream_callback,
                    text=interaction_text,
                    details="我先和你确认方向，再继续后面的协作。",
                    metadata={"requires_confirmation": "true"},
                )
                return True, intent_type
        except Exception as e:
            logger.warning(f"Sufficiency check failed, continuing: {e}")
        return False, intent_type if 'intent_type' in locals() else ""

    async def _check_phase_a_planning_preflight(
        self,
        *,
        intent_type: str,
        request: agent_service_pb2.ChatRequest,
        user_message: str,
        user_id: str,
        session_id: str | None,
        plan_id: uuid.UUID | None,
        active_db: AsyncSession | None,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        state: WorkflowState | None,
        stream_callback,
        session_feedback_signal: dict[str, Any] | None,
    ) -> bool:
        if not isinstance(user_context_payload, dict):
            return False

        context_focus = user_context_payload.get("context_focus") if isinstance(user_context_payload, dict) else None
        route_intent = ""
        if isinstance(context_focus, dict):
            route_intent = str(context_focus.get("route_intent") or "").strip()
        existing_decision_context = user_context_payload.get("residual_decision_context")
        if not isinstance(existing_decision_context, dict):
            existing_brief = user_context_payload.get("situation_brief")
            if isinstance(existing_brief, dict):
                existing_decision_context = existing_brief.get("decision_context")
        planning_like, detection_source = detect_planning_like_turn(
            normalized_intent=intent_type,
            route_intent=route_intent,
            user_message=user_message,
            decision_context=existing_decision_context if isinstance(existing_decision_context, dict) else None,
        )
        if not planning_like:
            return False

        user_context_payload.setdefault("current_query", user_message)
        if request.file_ids and not user_context_payload.get("file_ids"):
            user_context_payload["file_ids"] = [str(file_id) for file_id in request.file_ids if str(file_id).strip()]

        if not isinstance(user_context_payload.get("user_strategy_state"), dict):
            user_context_payload = await self._attach_user_strategy_state(
                active_db=active_db,
                user_id=user_id,
                session_id=session_id,
                plan_id=plan_id,
                user_context_payload=user_context_payload,
                state=state,
            )
        user_context_payload = await self._attach_situation_brief(
            active_db=active_db,
            user_id=user_id,
            user_context_payload=user_context_payload,
            plan_context=plan_context,
            state=state,
            session_feedback_signal=session_feedback_signal,
        )
        if not isinstance(user_context_payload, dict):
            return False

        situation_brief = user_context_payload.get("situation_brief")
        decision_context = (
            situation_brief.get("decision_context")
            if isinstance(situation_brief, dict)
            else user_context_payload.get("residual_decision_context")
        )
        if not isinstance(decision_context, dict):
            return False

        insight_state = situation_brief.get("insight_state") if isinstance(situation_brief, dict) else {}
        contradiction_map = insight_state.get("contradiction_map") if isinstance(insight_state, dict) else []
        contradiction_ids = [
            str(item.get("id") or "").strip()
            for item in contradiction_map
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        ]
        blocking_unknowns = [
            str(item).strip()
            for item in (decision_context.get("planning_blocking_unknowns") or [])
            if str(item).strip()
        ]
        phase_a_guardrail = str(decision_context.get("phase_a_guardrail") or "").strip()
        phase_a_evaluation = {
            "planning_like": "true",
            "planning_detection_source": detection_source,
            "planning_readiness": str(decision_context.get("planning_readiness") or "").strip(),
            "planning_readiness_action": str(decision_context.get("planning_readiness_action") or "").strip(),
            "phase_a_guardrail": phase_a_guardrail,
            "blocking_unknowns": blocking_unknowns[:3],
            "contradiction_ids": contradiction_ids[:3],
            "hard_stop": "false",
        }
        self._persist_phase_a_evaluation(
            state=state,
            user_context_payload=user_context_payload,
            evaluation=phase_a_evaluation,
        )
        observability = getattr(self, "observability", None)

        if str(decision_context.get("planning_readiness_action") or "").strip() != "ask":
            if observability is not None and hasattr(observability, "log_phase_a_decision"):
                try:
                    await observability.log_phase_a_decision(
                        user_id=user_id,
                        session_id=session_id or "",
                        decision={
                            "planning_like": True,
                            "planning_detection_source": detection_source,
                            "planning_readiness": phase_a_evaluation["planning_readiness"],
                            "planning_readiness_action": phase_a_evaluation["planning_readiness_action"],
                            "phase_a_guardrail": phase_a_guardrail,
                            "blocking_unknowns": blocking_unknowns[:3],
                            "contradiction_ids": contradiction_ids[:3],
                            "contradictions": contradiction_map[:3] if isinstance(contradiction_map, list) else [],
                            "hard_stop": False,
                        },
                    )
                except Exception as exc:
                    logger.debug(f"Failed to record Phase A observability: {exc}")
            return False

        clarification_questions = [
            str(question).strip()
            for question in (decision_context.get("strategic_clarification_questions") or [])
            if str(question).strip()
        ]
        question = clarification_questions[0] if clarification_questions else "你现在最缺的关键信息是什么？"
        fallback_text = (
            "我先不急着给你完整计划，先确认一个最关键的问题：\n\n"
            f"- {question}\n\n"
            "你告诉我这个信息后，我就按它给你做下一步计划。"
        )
        interaction_text = await self._compose_fast_interaction_copy(
            user_message=user_message,
            interaction_type="clarification",
            fallback_text=fallback_text,
            prompts=[question],
        )
        await self._emit_fast_interaction(
            stream_callback=stream_callback,
            text=interaction_text,
            details="我先确认一个关键缺口，再继续为你规划。",
            metadata={
                "requires_clarification": "true",
                "clarification_source": "phase_a",
                "phase_a_guardrail": "ask_before_plan",
                "planning_readiness": str(decision_context.get("planning_readiness") or ""),
                "planning_detection_source": detection_source,
            },
        )
        phase_a_evaluation["hard_stop"] = "true"
        phase_a_evaluation["phase_a_guardrail"] = "ask_before_plan"
        self._persist_phase_a_evaluation(
            state=state,
            user_context_payload=user_context_payload,
            evaluation=phase_a_evaluation,
        )
        if observability is not None and hasattr(observability, "log_phase_a_decision"):
            try:
                await observability.log_phase_a_decision(
                    user_id=user_id,
                    session_id=session_id or "",
                    decision={
                        "planning_like": True,
                        "planning_detection_source": detection_source,
                        "planning_readiness": phase_a_evaluation["planning_readiness"],
                        "planning_readiness_action": phase_a_evaluation["planning_readiness_action"],
                        "phase_a_guardrail": "ask_before_plan",
                        "blocking_unknowns": blocking_unknowns[:3],
                        "contradiction_ids": contradiction_ids[:3],
                        "contradictions": contradiction_map[:3] if isinstance(contradiction_map, list) else [],
                        "hard_stop": True,
                    },
                )
            except Exception as exc:
                logger.debug(f"Failed to record Phase A hard-stop observability: {exc}")
        return True

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
            fallback_text = (
                "我想先把目标收紧到足够可执行，再开始做计划：\n\n"
                f"{question_text}\n\n"
                "你补充这些信息后，我就能给你更靠谱的阶段方案。"
            )
            interaction_text = await self._compose_fast_interaction_copy(
                user_message=user_message,
                interaction_type="goal_clarification",
                fallback_text=fallback_text,
                prompts=evaluation.clarification_questions,
            )
            await self._emit_fast_interaction(
                stream_callback=stream_callback,
                text=interaction_text,
                details="我先快速把目标边界确认清楚，再进入规划。",
                metadata={
                    "requires_goal_clarification": "true",
                    "goal_quality_scores": json.dumps(evaluation.scores.to_dict(), ensure_ascii=False),
                },
            )
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
                from app.services.execution_result_validator import ExecutionResultValidator

                result_validator = ExecutionResultValidator()
                validation_summary = result_validator.build_validation_summary(validation_result)
                result_preview = result_validator.extract_plan_result_preview(plan_result)
                return {
                    "validation_status": validation_result.validation_status,
                    "quality_score": validation_result.quality_score,
                    "tools_total": validation_result.tool_summary.get("total", 0),
                    "tools_successful": validation_result.tool_summary.get("successful", 0),
                    "steps_total": len(getattr(validation_result, "step_validations", []) or []),
                    "steps_passed": sum(1 for sv in (getattr(validation_result, "step_validations", []) or []) if sv.passed),
                    "aborted": bool(getattr(validation_result, "aborted", False)),
                    "result_preview": result_preview,
                    "replay_steps": result_validator.build_replay_steps_from_plan_result(plan_result),
                    "quality_warnings": validation_summary["quality_warnings"],
                    "validation_issues": validation_summary["validation_issues"],
                    "comparison_summary": validation_summary["comparison_summary"],
                    "self_verification": result_validator.build_self_verification(
                        parsed_output=result_preview,
                        quality_warnings=validation_summary["quality_warnings"],
                    ),
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
