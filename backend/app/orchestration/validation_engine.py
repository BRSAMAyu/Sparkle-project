from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Callable

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.business_metrics import EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.goal_quality_evaluator import goal_quality_evaluator
from app.orchestration.planning_intent import detect_planning_like_turn, has_correction_signal
from app.orchestration.schemas import ExecutablePlan
from app.orchestration.statechart_engine import WorkflowState
from app.orchestration.sufficiency_checker import SufficiencyStatus, sufficiency_checker
from app.orchestration.tool_result_extractor import ToolResultExtractor
from app.services.galaxy_service import GalaxyService
from app.services.llm_service import get_configured_llm_service_for_tier
from app.services.perceptible_intelligence_service import ProgressComparisonService
from app.services.plan_execution_record_service import PlanExecutionRecordService
from app.services.plan_execution_validator import PlanExecutionValidator
from app.services.system_update_service import SystemUpdateService, build_system_update

# TTFT-CFG: 规划前置链预算收敛。探针实测 suff 单次 LLM 3.2-19.2s 串行在首个事件之前；
# 超预算即放弃本轮充分性裁决、继续通用链路（与既有 "check failed, continuing" 语义一致）。
SUFFICIENCY_CHECK_BUDGET_SECONDS = 5.0


def _ws_turn_capture(
    *,
    user_id: str | None,
    session_id: str | None,
    user_message: str | None,
    request_id: str | None,
) -> dict[str, str] | None:
    """NBP-1：构造快交互出口的轮次记忆捕获上下文（缺关键字段时返回 None，
    捕获静默跳过——绝不影响回复主链路）。"""
    resolved_user_id = str(user_id or "").strip()
    resolved_session_id = str(session_id or "").strip()
    if not resolved_user_id or not resolved_session_id:
        return None
    return {
        "user_id": resolved_user_id,
        "session_id": resolved_session_id,
        "user_message": str(user_message or ""),
        "request_id": str(request_id or ""),
    }


class ValidationEngineMixin:
    """Mixin providing request validation, sufficiency checking, goal quality
    evaluation, and plan-execution validation capabilities.

    Designed to be mixed into the main Orchestrator class.  Methods reference
    ``self.validator``, ``self.redis``, and several helper methods that live on
    the orchestrator (``_check_idempotency``, ``_publish_execution_feedback``).
    """
    redis: Any
    validator: Any
    _check_idempotency: Callable[..., Any]
    _attach_user_strategy_state: Callable[..., Any]
    _attach_situation_brief: Callable[..., Any]
    _publish_execution_feedback: Callable[..., Any]

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
        turn_capture: dict[str, str] | None = None,
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
            # NBP-1（2026-09-22）：澄清/确认类快交互短路轮此前只发帧——不
            # 持久化、不建 finalize 任务，整轮零记忆写账触发器（LOOP2 B1
            # Day0 声明事实 0 入库的直接断点）。此处直调与 REST
            # api/v1/chat.py 收尾同款 enqueue_from_chat_turn 面（单一事实
            # 源；零 LLM 正则抽取，不新增预算面）；协议帧形状不变。
            if turn_capture:
                try:
                    from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService

                    evidence_token = str(turn_capture.get("request_id") or "").strip() or str(uuid.uuid4())
                    MemoryInferredWriteLaneService.enqueue_from_chat_turn(
                        user_id=uuid.UUID(str(turn_capture["user_id"])),
                        session_id=uuid.UUID(str(turn_capture["session_id"])),
                        user_message=str(turn_capture.get("user_message") or ""),
                        assistant_message=cleaned,
                        user_message_id=evidence_token,
                        assistant_message_id=None,
                    )
                except (KeyError, TypeError, ValueError):
                    logger.debug("fast-interaction turn memory capture skipped: invalid turn context")
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

        # BP-3B 判定序：用户明示纠正/指错信号（你说错了/不对/纠正/其实是…）
        # 优先于规划词汇（复习/总结等）触发——含纠正信号的规划词面消息是
        # 纠正请求，不得被规划澄清快速通道劫持；仅在用户同时明确要求
        # 出计划（explicit_plan_markers）时维持规划意图。
        correction_present = has_correction_signal(message)
        if (correction_present or any(marker in message for marker in advisory_markers)) and not any(
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
            planning_material_context = await self._build_planning_material_context(
                active_db=active_db,
                intent_type=intent_type,
                user_id=user_id,
                user_message=user_message,
                request=request,
                user_context_payload=user_context_payload,
            )
            try:
                # TTFT-CFG: 充分性检查（含 LLM 精化）整体封顶，超时继续通用链路
                async with asyncio.timeout(SUFFICIENCY_CHECK_BUDGET_SECONDS):
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
                        planning_material_context=planning_material_context,
                    )
            except TimeoutError:
                logger.warning(
                    f"Sufficiency check budget ({SUFFICIENCY_CHECK_BUDGET_SECONDS}s) exceeded, "
                    "continuing generic path"
                )
                return False, intent_type

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
                    turn_capture=_ws_turn_capture(
                        user_id=user_id,
                        session_id=session_id,
                        user_message=user_message,
                        request_id=request.request_id,
                    ),
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
                    turn_capture=_ws_turn_capture(
                        user_id=user_id,
                        session_id=session_id,
                        user_message=user_message,
                        request_id=request.request_id,
                    ),
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
        if not isinstance(contradiction_map, list):
            # ORCH-DEBT P2：insight_state 为 dict 但 contradiction_map 缺省/显式 None
            # （生产形状：situation_brief 的 profile-missing 回退分支无该键）＝
            # 无矛盾数据，按空表降级。否则下面的推导抛 TypeError，被
            # _check_sufficiency 的兜底 except 吞掉后整个 sufficiency 检查
            # （含澄清与 Phase A 硬停）无声跳过。
            contradiction_map = []
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

        pending_ask_action = str(decision_context.get("planning_readiness_action") or "").strip()

        if pending_ask_action == "ask" and str(decision_context.get("phase_a_ask_surfaced") or "").strip() == "true":
            # ORCH-DEBT P3：残留 pending ask 是上一回合已向用户问出的问题
            # （Phase A 硬停早退不回写会话态，导致 ask 残留）。本回合消息是
            # 用户的回答/推进——一次性消费该 ask：清理残留标记并放行，
            # 不得用同一问题再次硬停（会话死锁，用户回答永远送不到规划链路）。
            decision_context["planning_readiness_action"] = ""
            decision_context["phase_a_guardrail"] = ""
            phase_a_evaluation["ask_residual_consumed"] = "true"
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
                            "phase_a_guardrail": phase_a_guardrail,
                            "blocking_unknowns": blocking_unknowns[:3],
                            "contradiction_ids": contradiction_ids[:3],
                            "contradictions": contradiction_map[:3],
                            "ask_residual_consumed": True,
                            "hard_stop": False,
                        },
                    )
                except Exception as exc:
                    logger.debug(f"Failed to record Phase A residual-ask release observability: {exc}")
            return False

        if pending_ask_action != "ask":
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
        # ORCH-DEBT P3：ask 一次性消费——问出即在会话态落 surfaced 标记并清零
        # pending ask。硬停早退不会走执行引擎的元数据回写，若不在此处修复会话态，
        # 残留 ask 会让下一回合（用户的回答）被同一问题再次硬停，会话死锁。
        decision_context["phase_a_ask_surfaced"] = "true"
        decision_context["phase_a_ask_surfaced_at"] = datetime.now(UTC).isoformat()
        decision_context["planning_readiness_action"] = ""
        decision_context["phase_a_guardrail"] = ""
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
        phase_a_metadata = {
            "requires_clarification": "true",
            "clarification_source": "phase_a",
            "phase_a_guardrail": "ask_before_plan",
            "planning_readiness": str(decision_context.get("planning_readiness") or ""),
            "planning_detection_source": detection_source,
        }
        if settings.ENABLE_CONTEXT_FOCUS_METADATA:
            # 残留态修复通道：把消费后的 brief 随快响帧回传（与执行引擎的
            # response_metadata 持久化约定一致），下一回合不再回放残留 ask。
            if isinstance(situation_brief, dict):
                phase_a_metadata["situation_brief"] = json.dumps(situation_brief, ensure_ascii=False)
            residual_decision = user_context_payload.get("residual_decision_context")
            if isinstance(residual_decision, dict):
                phase_a_metadata["residual_decision_context"] = json.dumps(
                    residual_decision,
                    ensure_ascii=False,
                )
        await self._emit_fast_interaction(
            stream_callback=stream_callback,
            text=interaction_text,
            details="我先确认一个关键缺口，再继续为你规划。",
            metadata=phase_a_metadata,
            turn_capture=_ws_turn_capture(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                request_id=request.request_id,
            ),
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
            elif any(keyword in msg_lower for keyword in ["长期", "成长", "习惯", "体系", "long-term", "growth"]) or "计划" in normalized_message or "复习" in normalized_message:
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
        session_id: str | None = None,
        request_id: str | None = None,
    ) -> bool:
        if intent_type not in {"create_plan", "set_goal", "time_planning"}:
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
                turn_capture=_ws_turn_capture(
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    request_id=request_id,
                ),
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
    # Planning material sufficiency
    # ------------------------------------------------------------------

    async def _build_planning_material_context(
        self,
        *,
        active_db: AsyncSession | None,
        intent_type: str,
        user_id: str,
        user_message: str,
        request: agent_service_pb2.ChatRequest,
        user_context_payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if active_db is None or intent_type not in {"create_plan", "time_planning"}:
            return None

        payload = user_context_payload if isinstance(user_context_payload, dict) else {}
        preferred_file_ids = [str(file_id).strip() for file_id in request.file_ids if str(file_id).strip()]
        if not preferred_file_ids:
            preferred_file_ids = [
                str(file_id).strip()
                for file_id in list(payload.get("file_ids") or [])
                if str(file_id).strip()
            ]
        if not preferred_file_ids:
            return None

        try:
            summary = await GalaxyService(active_db).summarize_study_materials_for_planning(
                user_id=uuid.UUID(user_id),
                topic_hints=[user_message],
                preferred_file_ids=preferred_file_ids,
            )
        except Exception as exc:
            logger.warning("Failed to load planning material context for sufficiency check: {}", exc)
            return None

        matched_documents_count = int(summary.get("matched_documents_count") or 0)
        has_materials = bool(summary.get("has_materials"))
        material_gaps: list[str] = []
        if has_materials and matched_documents_count == 0:
            material_gaps.append("目前还没有找到和这次规划目标直接匹配的已上传章节资料")

        return {
            "enabled": True,
            "subject": user_message,
            "has_materials": has_materials,
            "material_gaps": material_gaps,
        }

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
            logger.opt(exception=e).warning(f"Plan execution validation failed: {e}")
            return None
