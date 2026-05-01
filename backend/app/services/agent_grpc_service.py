"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

AgentService gRPC Implementation
实现 gRPC 服务端，对接现有的 LLM 服务和 RAG 能力
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta

import grpc
from google.protobuf.json_format import MessageToDict
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import (
    FEEDBACK_TO_EFFECT_SECONDS,
    PROTO_ERROR_CODE_FALLBACK_TOTAL,
    PROTO_FIELD_READ_TOTAL,
)
from app.core.safe_error_messages import build_safe_chat_error
from app.gen.agent.v1 import agent_service_pb2, agent_service_pb2_grpc
from app.learning.prompt_bandit import PromptBandit
from app.orchestration.chat_modes import (
    CHAT_MODE_DEEP_ANALYSIS,
    CHAT_MODE_ERROR_DIAGNOSIS,
    CHAT_MODE_EXPERT_AUTO,
    CHAT_MODE_EXPERT_PREFIX,
    CHAT_MODE_STANDARD,
    CHAT_MODE_STUDY_PLAN,
    CHAT_MODE_TEAM_PREFIX,
    normalize_chat_mode,
)
from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.plan_review_service import ReviewDecision, plan_review_service
from app.orchestration.run_ledger import RunLedgerStore
from app.services.progress_narrative_service import ProgressNarrativeService
from app.services.response_feedback_service import ResponseFeedbackService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _grpc_status_for_chat_error(error_code: int) -> grpc.StatusCode:
    _MAP = {
        agent_service_pb2.ERROR_CODE_INVALID_ARGUMENT: grpc.StatusCode.INVALID_ARGUMENT,
        agent_service_pb2.ERROR_CODE_UNAUTHORIZED: grpc.StatusCode.UNAUTHENTICATED,
        agent_service_pb2.ERROR_CODE_FORBIDDEN: grpc.StatusCode.PERMISSION_DENIED,
        agent_service_pb2.ERROR_CODE_NOT_FOUND: grpc.StatusCode.NOT_FOUND,
        agent_service_pb2.ERROR_CODE_CONFLICT: grpc.StatusCode.ALREADY_EXISTS,
        agent_service_pb2.ERROR_CODE_RATE_LIMITED: grpc.StatusCode.RESOURCE_EXHAUSTED,
        agent_service_pb2.ERROR_CODE_UNAVAILABLE: grpc.StatusCode.UNAVAILABLE,
        agent_service_pb2.ERROR_CODE_TIMEOUT: grpc.StatusCode.DEADLINE_EXCEEDED,
        agent_service_pb2.ERROR_CODE_INTERNAL: grpc.StatusCode.INTERNAL,
    }
    return _MAP.get(error_code, grpc.StatusCode.INTERNAL)


class AgentServiceImpl(agent_service_pb2_grpc.AgentServiceServicer):
    """
    AgentService 的 gRPC 实现
    负责处理流式对话和记忆检索
    """

    def __init__(self, orchestrator: ChatOrchestrator, db_session_factory: Callable[[], AsyncSession]):
        # 初始化 Orchestrator (依赖注入)
        self.orchestrator = orchestrator
        self.db_session_factory = db_session_factory
        logger.info("AgentServiceImpl initialized with injected dependencies")

    @staticmethod
    def _resolve_workflow_id(chat_mode: str) -> str:
        mode = normalize_chat_mode(chat_mode)
        if mode == CHAT_MODE_STANDARD:
            return "standard_chat"
        if mode == CHAT_MODE_DEEP_ANALYSIS:
            return "deep_analysis_workflow"
        if mode == CHAT_MODE_STUDY_PLAN:
            return "study_plan_workflow"
        if mode == CHAT_MODE_ERROR_DIAGNOSIS:
            return "error_diagnosis_workflow"
        if mode == CHAT_MODE_EXPERT_AUTO:
            return "expert_auto_workflow"
        if mode.startswith(CHAT_MODE_EXPERT_PREFIX):
            expert_id = mode[len(CHAT_MODE_EXPERT_PREFIX) :].strip() or "unknown"
            return f"expert_{expert_id}_workflow"
        if mode.startswith(CHAT_MODE_TEAM_PREFIX):
            return "expert_team_workflow"
        return "standard_chat"

    @staticmethod
    def _normalize_v2_response(response: agent_service_pb2.ChatResponse) -> agent_service_pb2.ChatResponse:
        service = "agent_grpc_service"

        if not response.HasField("event_time"):
            response.event_time.FromDatetime(datetime.now(UTC))
            PROTO_FIELD_READ_TOTAL.labels(service=service, field="chat_response.event_time", source="defaulted").inc()
        else:
            PROTO_FIELD_READ_TOTAL.labels(service=service, field="chat_response.event_time", source="new").inc()

        if response.HasField("error"):
            if response.error.error_code == agent_service_pb2.ERROR_CODE_UNSPECIFIED:
                response.error.error_code = agent_service_pb2.ERROR_CODE_UNKNOWN
                PROTO_ERROR_CODE_FALLBACK_TOTAL.labels(
                    service=service,
                    direction="enum_missing_defaulted",
                ).inc()
        return response

    async def _require_admin(
        self,
        context: grpc.aio.ServicerContext,
        metadata: dict[str, str],
    ) -> str | None:
        user_id = metadata.get("user-id")
        if not user_id:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("user_id is required")
            return None

        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("user_id must be a valid UUID")
            return None

        try:
            async with self.db_session_factory() as db_session:
                from app.services.user_service import UserService

                user_service = UserService(db_session)
                user = await user_service.get_user_by_id(user_uuid)
                if not user or not user.is_superuser:
                    context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                    context.set_details("Admin access required")
                    return None
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return None

        return user_id

    async def StreamChat(
        self,
        request: agent_service_pb2.ChatRequest,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[agent_service_pb2.ChatResponse]:
        """
        处理流式聊天请求
        实现打字机效果的 AI 响应
        """
        trace_id = request.request_id or str(uuid.uuid4())
        workflow_id = "standard_chat"
        prompt_version = "v1"
        try:
            # 从 metadata 获取追踪信息
            raw_metadata = context.invocation_metadata()
            metadata = dict(raw_metadata) if raw_metadata else {}
            user_id = request.user_id or metadata.get("user-id", "")

            # Security Audit: Log missing authorization headers
            if not metadata.get("authorization") and not request.user_id:
                logger.warning(
                    f"SECURITY ALERT: StreamChat call without authorization metadata or user_id. Session: {request.session_id}"
                )
            elif metadata.get("authorization"):
                logger.debug(f"Auth metadata found for user_id={user_id}")

            trace_id = metadata.get("x-trace-id", request.request_id) or trace_id

            # 🔧 根据请求的 chat_mode 选择 workflow
            chat_mode = normalize_chat_mode(getattr(request, "chat_mode", None) or CHAT_MODE_STANDARD)
            request_extra_context: dict[str, object] = {}
            if request.HasField("extra_context"):
                try:
                    request_extra_context = MessageToDict(request.extra_context)
                except Exception as exc:
                    logger.warning(f"Failed to parse request extra_context in StreamChat: {exc}")
            reasoning_mode = str(request_extra_context.get("reasoning_mode") or "balanced").strip().lower()
            if reasoning_mode not in {"fast", "balanced", "deep"}:
                reasoning_mode = "balanced"
            logger.info(f"📋 Chat mode: {chat_mode}")
            workflow_id = self._resolve_workflow_id(chat_mode)

            prompt_versions = ["v1", "v2"]
            try:
                bandit = PromptBandit(redis_client=self.orchestrator.redis)
                prompt_version = await bandit.select(workflow_id, prompt_versions)
            except Exception as e:
                logger.warning(f"Prompt bandit selection failed: {e}")

            await self._observe_feedback_effect(user_id, workflow_id, prompt_version, trace_id=trace_id)

            logger.info(
                f"StreamChat started - user_id={user_id}, session={request.session_id}, trace={trace_id}, "
                f"chat_mode={chat_mode}, workflow={workflow_id}, prompt_version={prompt_version}"
            )

            # Create a dedicated DB session for this stream
            has_text_content = False
            async with self.db_session_factory() as db_session:
                try:
                    # Delegate to Orchestrator
                    async for response in self.orchestrator.process_stream(
                        request,
                        db_session=db_session,
                        context_data={
                            "chat_mode": chat_mode,
                            "reasoning_mode": reasoning_mode,
                            "workflow_id": workflow_id,
                            "prompt_version": prompt_version,
                        },
                    ):
                        # Track whether we actually streamed any text content
                        if response.WhichOneof("content") in ("delta", "full_text"):
                            has_text_content = True
                        response.trace_id = trace_id
                        if not response.workflow_id:
                            response.workflow_id = workflow_id
                        if not response.prompt_version:
                            response.prompt_version = prompt_version
                        # Ensure session_id is always set for conversation continuity
                        if not response.session_id:
                            response.session_id = request.session_id
                        yield self._normalize_v2_response(response)
                    await db_session.commit()
                except Exception:
                    await db_session.rollback()
                    raise

            if not has_text_content:
                logger.warning(
                    f"StreamChat completed without text content for trace={trace_id}, session={request.session_id}"
                )
                fallback = agent_service_pb2.ChatResponse(
                    response_id=str(uuid.uuid4()),
                    created_at=int(datetime.now().timestamp()),
                    request_id=request.request_id,
                    trace_id=trace_id,
                    workflow_id=workflow_id,
                    prompt_version=prompt_version,
                    session_id=request.session_id,
                    full_text="(System) No valid response generated. Please try again later.",
                    finish_reason=agent_service_pb2.STOP,
                )
                fallback.event_time.FromDatetime(datetime.now(UTC))
                yield fallback

            logger.info(f"StreamChat completed for trace={trace_id}")

            # Fire-and-forget: check recall opportunities at session end
            if user_id:
                try:
                    from app.services.push_scheduler import PushScheduler
                    async with self.db_session_factory() as recall_db:
                        push_scheduler = PushScheduler(recall_db)
                        await push_scheduler.enqueue_session_end_recall(
                            user_id=user_id,
                            session_context={
                                "uploaded_files_count": len(request_extra_context.get("file_ids") or []),
                                "diagnosed_files_count": 0,
                            },
                        )
                except Exception as recall_err:
                    logger.debug(f"Session-end recall check failed (non-fatal): {recall_err}")

        except Exception as e:
            logger.error(f"StreamChat error: {e}", exc_info=True)
            safe_message, error_code, retryable = build_safe_chat_error(e)
            context.set_code(_grpc_status_for_chat_error(error_code))
            context.set_details(safe_message)
            response = agent_service_pb2.ChatResponse(
                response_id=str(uuid.uuid4()),
                created_at=int(datetime.now().timestamp()),
                request_id=request.request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                session_id=request.session_id,
                error=agent_service_pb2.Error(
                    message=safe_message,
                    retryable=retryable,
                    error_code=error_code,
                ),
                finish_reason=agent_service_pb2.ERROR,
            )
            response.event_time.FromDatetime(datetime.now(UTC))
            yield response

    async def SubmitResponseFeedback(
        self,
        request: agent_service_pb2.ResponseFeedbackRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.ResponseFeedbackResponse:
        """
        Submit user feedback for an AI response.
        """
        try:
            raw_metadata = context.invocation_metadata()
            metadata = dict(raw_metadata) if raw_metadata else {}
            meta_user_id = metadata.get("user-id")
            user_id = meta_user_id or request.user_id
            if request.user_id and meta_user_id and request.user_id != meta_user_id:
                logger.warning(
                    "Response feedback user_id mismatch metadata=%s request=%s",
                    meta_user_id,
                    request.user_id,
                )

            if not user_id or not request.response_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id and response_id are required")
                return agent_service_pb2.ResponseFeedbackResponse(
                    success=False,
                    message="Missing required fields",
                    response_id=request.response_id,
                )

            trace_id = request.trace_id or metadata.get("x-trace-id") or str(uuid.uuid4())
            if request.feedback_type not in (
                agent_service_pb2.FEEDBACK_TYPE_UP,
                agent_service_pb2.FEEDBACK_TYPE_DOWN,
            ):
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("invalid feedback_type")
                return agent_service_pb2.ResponseFeedbackResponse(
                    success=False,
                    message="invalid feedback_type",
                    response_id=request.response_id,
                )

            feedback_type = 1 if request.feedback_type == agent_service_pb2.FEEDBACK_TYPE_UP else 2
            reasons = ResponseFeedbackService.normalize_reasons(list(request.reasons))

            async with self.db_session_factory() as db_session:
                service = ResponseFeedbackService(db_session, redis_client=self.orchestrator.redis)
                try:
                    result = await service.submit_feedback(
                        user_id=user_id,
                        response_id=request.response_id,
                        trace_id=trace_id,
                        feedback_type=feedback_type,
                        reasons=reasons,
                        free_text=request.free_text or None,
                        workflow_id=request.workflow_id or None,
                        prompt_version=request.prompt_version or None,
                        meta=dict(request.meta) if request.meta else None,
                    )
                except ValueError as exc:
                    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                    context.set_details(str(exc))
                    return agent_service_pb2.ResponseFeedbackResponse(
                        success=False,
                        message=str(exc),
                        response_id=request.response_id,
                    )

            message = "already_recorded" if result.already_recorded else "ok"
            workflow_id = request.workflow_id or ""
            selected_experts_raw = (request.meta or {}).get("selected_experts", "")
            selected_experts = [item.strip() for item in selected_experts_raw.split(",") if item.strip()]
            if workflow_id and hasattr(self.orchestrator, "observability"):
                await self.orchestrator.observability.log_user_feedback_bound(
                    user_id=user_id,
                    session_id="",
                    response_id=request.response_id,
                    workflow_id=workflow_id,
                    selected_experts=selected_experts,
                )
            return agent_service_pb2.ResponseFeedbackResponse(
                success=result.success,
                message=message,
                response_id=result.response_id,
            )
        except Exception as e:
            logger.error(f"SubmitResponseFeedback error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.ResponseFeedbackResponse(
                success=False,
                message="Internal error",
                response_id=request.response_id,
            )

    async def _observe_feedback_effect(
        self,
        user_id: str,
        workflow_id: str,
        prompt_version: str,
        *,
        trace_id: str,
    ) -> None:
        if not self.orchestrator.redis:
            return
        if not user_id:
            return
        key = f"bandit:last_feedback_ts:{user_id}:{workflow_id}:{prompt_version}"
        try:
            raw = await self.orchestrator.redis.get(key)
            if not raw:
                return
            try:
                last_ts = int(raw)
            except (TypeError, ValueError):
                return
            delta = max(0, int(time.time()) - last_ts)
            FEEDBACK_TO_EFFECT_SECONDS.labels(workflow_id=workflow_id, prompt_version=prompt_version).observe(delta)
            await RunLedgerStore.append_external_event(
                self.orchestrator.redis,
                trace_id=trace_id,
                event_type="strategy_effect_applied",
                label="历史反馈已在本轮生效",
                workflow_stage="feedback",
                metadata={
                    "effect_target": "prompt_selection",
                    "status": "observed",
                    "detail": f"{workflow_id}:{prompt_version}",
                    "effect_latency_seconds": delta,
                },
            )
            await self.orchestrator.redis.delete(key)
        except Exception:
            return

    async def RetrieveMemory(
        self,
        request: agent_service_pb2.MemoryQuery,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.MemoryResult:
        """
        从向量数据库检索长期记忆
        实现 RAG (Retrieval-Augmented Generation) with structured results
        """
        try:
            logger.info(f"RetrieveMemory - user={request.user_id}, query={request.query_text[:50]}...")

            # Validate request
            if not request.user_id or not request.query_text:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id and query_text are required")
                return agent_service_pb2.MemoryResult(items=[], total_found=0)

            async with self.db_session_factory() as db_session:
                import uuid

                from app.services.galaxy_service import GalaxyService

                # Use GalaxyService for structured search
                galaxy_service = GalaxyService(db_session)

                # Perform semantic search
                search_results = await galaxy_service.semantic_search(
                    user_id=uuid.UUID(request.user_id),
                    query=request.query_text,
                    limit=request.limit if request.limit > 0 else 10,
                    threshold=request.min_score if request.min_score > 0 else 0.3,
                )

                # Convert to gRPC MemoryResult items
                memory_items = []
                for result in search_results:
                    # Build metadata
                    metadata = {
                        "sector_code": result.node.sector_code.value
                        if hasattr(result.node.sector_code, "value")
                        else str(result.node.sector_code),
                        "importance_level": str(result.node.importance_level),
                        "is_seed": str(result.node.is_seed),
                    }

                    # Add user status if available
                    if result.user_status:
                        metadata["mastery_score"] = str(result.user_status.mastery_score)
                        metadata["is_unlocked"] = str(result.user_status.is_unlocked)
                        metadata["total_study_minutes"] = str(result.user_status.total_study_minutes)

                    # Create MemoryItem
                    memory_item = agent_service_pb2.MemoryItem(
                        id=str(result.node.id),
                        content=f"{result.node.name}: {result.node.description}",
                        score=result.similarity,
                        metadata=metadata,
                    )
                    memory_items.append(memory_item)

                return agent_service_pb2.MemoryResult(items=memory_items, total_found=len(memory_items))

        except Exception as e:
            logger.error(f"RetrieveMemory error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.MemoryResult(items=[], total_found=0)

    async def GetUserProfile(
        self,
        request: agent_service_pb2.ProfileRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.UserProfile:
        """
        返回用户档案信息，供前端或 Orchestrator 使用
        """
        try:
            if not request.user_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id is required")
                return agent_service_pb2.UserProfile()

            try:
                user_uuid = uuid.UUID(request.user_id)
            except ValueError:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id must be a valid UUID")
                return agent_service_pb2.UserProfile()

            async with self.db_session_factory() as db_session:
                from app.services.user_service import UserService

                user_service = UserService(db_session)
                user_context = await user_service.get_context(user_uuid)

                if not user_context:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details("user not found or inactive")
                    return agent_service_pb2.UserProfile()

                # preferences map requires string values
                preferences = {
                    str(key): str(value) for key, value in (user_context.preferences or {}).items() if value is not None
                }
                extra_payload = {
                    "active_slots": user_context.active_slots,
                    "daily_cap": user_context.daily_cap,
                    "persona_type": user_context.persona_type,
                }

                return agent_service_pb2.UserProfile(
                    nickname=user_context.nickname,
                    timezone=user_context.timezone,
                    language=user_context.language,
                    is_pro=user_context.is_pro,
                    preferences=preferences,
                    extra_context=json.dumps(extra_payload, ensure_ascii=False),
                )
        except Exception as e:
            logger.error(f"GetUserProfile error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.UserProfile()

    async def GetWeeklyReport(
        self,
        request: agent_service_pb2.WeeklyReportRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.WeeklyReport:
        """
        生成或返回用户的周报摘要
        """
        try:
            if not request.user_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id is required")
                return agent_service_pb2.WeeklyReport()

            end_date = _utcnow()
            start_date = end_date - timedelta(days=7)

            async with self.db_session_factory() as db_session:
                snapshot_service = ProgressNarrativeService(db_session, getattr(self.orchestrator, "redis", None))
                snapshot = await snapshot_service.build_snapshot(
                    request.user_id,
                    period_label="本周",
                    period_days=7,
                )

                summary_text = (
                    f"Week {request.week_id or start_date.isocalendar()[1]}: "
                    f"{snapshot.highlights[0]} "
                    f"当前连胜 {snapshot.streak_info.get('current_streak', 0)} 天。"
                )

                return agent_service_pb2.WeeklyReport(
                    summary=summary_text,
                    tasks_completed=int(snapshot.comparisons["tasks_completed"]["current"]),
                )
        except Exception as e:
            logger.error(f"GetWeeklyReport error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.WeeklyReport()

    async def SubmitPlanReview(
        self,
        request: agent_service_pb2.PlanReviewRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.PlanReviewResponse:
        """
        Submit user feedback for a plan review.

        Handles the user's decision (approve, reject, modify, acknowledge) on a plan review
        and triggers appropriate follow-up actions.
        """
        try:
            raw_metadata = context.invocation_metadata()
            metadata = dict(raw_metadata) if raw_metadata else {}
            user_id = request.user_id or metadata.get("user-id")

            if not user_id:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("user_id is required")
                return agent_service_pb2.PlanReviewResponse(
                    success=False,
                    message="Authentication required",
                )

            if not request.review_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("review_id is required")
                return agent_service_pb2.PlanReviewResponse(
                    success=False,
                    message="review_id is required",
                )

            trace_id = request.trace_id or metadata.get("x-trace-id") or str(uuid.uuid4())

            # Map proto enum to internal ReviewDecision
            decision_map = {
                agent_service_pb2.APPROVE: ReviewDecision.APPROVED,
                agent_service_pb2.REJECT: ReviewDecision.REJECTED,
                agent_service_pb2.MODIFY: ReviewDecision.NEEDS_MODIFICATION,
                agent_service_pb2.ACKNOWLEDGE: ReviewDecision.REQUIRES_CONFIRMATION,
            }

            proto_decision = request.decision
            if proto_decision not in decision_map:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Invalid decision: {proto_decision}")
                return agent_service_pb2.PlanReviewResponse(
                    success=False,
                    message="Invalid decision value",
                )

            user_decision = decision_map[proto_decision].value
            plan_id = request.plan_id or ""

            logger.info(
                f"SubmitPlanReview - user={user_id}, review={request.review_id}, "
                f"plan={plan_id}, decision={user_decision}, trace={trace_id}"
            )

            # P1 Fix #10: Process the review feedback with db_session
            async with self.db_session_factory() as db_session:
                result = await plan_review_service.handle_review_feedback(
                    review_id=request.review_id,
                    user_decision=user_decision,
                    user_id=user_id,
                    db_session=db_session,  # Now required
                    user_comment=request.user_comment or None,
                    modifications=dict(request.meta) if request.meta else None,
                )

            if result.get("status") != "success":
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(result.get("message", "Failed to process review"))
                return agent_service_pb2.PlanReviewResponse(
                    success=False,
                    message=result.get("message", "Failed to process review"),
                )

            # Trigger follow-up actions based on decision
            updated_plan_id = ""

            # P0-2: Track consecutive rejections for phase rollback
            if plan_id:
                try:
                    from app.services.plan_feedback_service import get_plan_feedback_service

                    async with self.db_session_factory() as db:
                        feedback_svc = get_plan_feedback_service(db, self.orchestrator.redis)
                        is_rejection = proto_decision == agent_service_pb2.REJECT
                        count, should_rollback = await feedback_svc.track_rejection(
                            user_id=uuid.UUID(user_id),
                            plan_id=uuid.UUID(plan_id),
                            is_rejection=is_rejection,
                        )
                        if should_rollback:
                            logger.info(
                                f"Phase rollback will be triggered for plan {plan_id} (rejection_count={count})"
                            )
                except Exception as e:
                    logger.warning(f"Failed to track rejection for plan {plan_id}: {e}")

            if proto_decision == agent_service_pb2.APPROVE:
                # Resume plan execution after approval with db_session for task generation
                async with self.db_session_factory() as db:
                    result = await plan_review_service.resume_plan_after_approval(
                        plan_id=plan_id,
                        user_id=user_id,
                        db_session=db,
                        modifications=dict(request.meta) if request.meta else None,
                    )
                logger.info(
                    f"Plan {plan_id} resumed after approval by {user_id}, task_generation={result.get('task_generation_initiated')}"
                )

            elif proto_decision == agent_service_pb2.REJECT:
                # Handle rejection - notify and stop
                await plan_review_service.notify_plan_rejected(
                    plan_id=plan_id,
                    user_id=user_id,
                    feedback=request.user_comment or "Plan rejected by user",
                )
                logger.info(f"Plan {plan_id} rejected by {user_id}")

            elif proto_decision == agent_service_pb2.MODIFY:
                # Trigger replanning with user feedback
                replan_result = await plan_review_service.trigger_replanning(
                    plan_id=plan_id,
                    user_id=user_id,
                    feedback=request.user_comment or "User requested modifications",
                    modifications=dict(request.meta) if request.meta else None,
                )
                updated_plan_id = replan_result.get("new_plan_id", "")
                logger.info(f"Plan {plan_id} marked for replanning by {user_id}")

            return agent_service_pb2.PlanReviewResponse(
                success=True,
                message=result.get("message", "Review submitted successfully"),
                review_id=request.review_id,
                updated_plan_id=updated_plan_id,
            )

        except grpc.aio.AioRpcError as e:
            # gRPC level error
            logger.error(f"SubmitPlanReview gRPC error: {e.code()}: {e.details()}")
            context.set_code(e.code())
            context.set_details(e.details())
            return agent_service_pb2.PlanReviewResponse(
                success=False,
                message=str(e.details()),
            )
        except Exception as e:
            logger.error(f"SubmitPlanReview error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.PlanReviewResponse(
                success=False,
                message="Internal error processing review",
            )

    async def SubmitContentReviewFeedback(
        self,
        request: agent_service_pb2.ContentReviewFeedbackRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.ContentReviewFeedbackResponse:
        """
        Submit user feedback for a content review (Phase 2c).

        Records user feedback on content reviews and stores it for learning.
        """
        import uuid

        try:
            raw_metadata = context.invocation_metadata()
            metadata = dict(raw_metadata) if raw_metadata else {}
            user_id = request.user_id or metadata.get("user-id")

            if not user_id:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("user_id is required")
                return agent_service_pb2.ContentReviewFeedbackResponse(
                    success=False,
                    message="Authentication required",
                )

            if not request.review_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("review_id is required")
                return agent_service_pb2.ContentReviewFeedbackResponse(
                    success=False,
                    message="review_id is required",
                )

            trace_id = metadata.get("x-trace-id", str(uuid.uuid4()))

            # Map proto enum to FeedbackType
            feedback_type_map = {
                agent_service_pb2.SATISFIED: "satisfied",
                agent_service_pb2.UNSATISFIED: "unsatisfied",
                agent_service_pb2.MODIFIED: "modified",
                agent_service_pb2.REPORTED_ERROR: "reported_error",
                agent_service_pb2.SKIPPED: "skipped",
            }

            proto_feedback_type = request.feedback_type
            if proto_feedback_type not in feedback_type_map:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Invalid feedback_type: {proto_feedback_type}")
                return agent_service_pb2.ContentReviewFeedbackResponse(
                    success=False,
                    message="Invalid feedback_type value",
                )

            feedback_type_str = feedback_type_map[proto_feedback_type]
            logger.info(
                f"SubmitContentReviewFeedback - user={user_id}, review={request.review_id}, "
                f"feedback_type={feedback_type_str}, trace={trace_id}"
            )

            # Import review history service (Phase 2c)
            try:
                from app.services.review_history_service import FeedbackType, get_review_history_service
            except ImportError:
                logger.warning("[AgentService] Review history service not available")
                # Return success even if service is unavailable (don't block user)
                return agent_service_pb2.ContentReviewFeedbackResponse(
                    success=True,
                    message="Feedback received (history unavailable)",
                    feedback_id=f"fb_{uuid.uuid4().hex[:12]}",
                )

            # Record feedback to history
            async with self.db_session_factory() as db_session:
                history_service = get_review_history_service(db_session)
                feedback_entry = await history_service.record_user_feedback(
                    review_id=request.review_id,
                    user_id=user_id,
                    feedback_type=FeedbackType(feedback_type_str),
                    rating=request.rating if request.rating > 0 else None,
                    comment=request.comment if request.comment else None,
                    issues_reported=list(request.issues_reported) if request.issues_reported else None,
                )
                await db_session.commit()

                # Trigger learning analysis (async, non-blocking)
                try:
                    from app.services.feedback_learning_service import get_feedback_learning_service

                    learning_service = get_feedback_learning_service(history_service)

                    # Run learning analysis in background
                    async def run_learning():
                        try:
                            report = await learning_service.analyze_and_learn(days=7)
                            logger.info(
                                f"[ContentReviewFeedback] Learning analysis complete: "
                                f"misclassification_rate={report.misclassification_rate:.2%}"
                            )
                        except Exception as e:
                            logger.warning(f"[ContentReviewFeedback] Learning analysis failed: {e}")

                    # Don't await - run in background
                    asyncio.create_task(run_learning())
                except ImportError:
                    logger.debug("[ContentReviewFeedback] Learning service not available")
                except Exception as e:
                    logger.warning(f"[ContentReviewFeedback] Failed to trigger learning: {e}")

            return agent_service_pb2.ContentReviewFeedbackResponse(
                success=True,
                message="Feedback recorded successfully",
                feedback_id=feedback_entry.feedback_id,
            )

        except grpc.aio.AioRpcError as e:
            logger.error(f"SubmitContentReviewFeedback gRPC error: {e.code()}: {e.details()}")
            context.set_code(e.code())
            context.set_details(e.details())
            return agent_service_pb2.ContentReviewFeedbackResponse(
                success=False,
                message=str(e.details()),
            )
        except Exception as e:
            logger.error(f"SubmitContentReviewFeedback error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.ContentReviewFeedbackResponse(
                success=False,
                message="Internal error processing feedback",
            )

    # ========================================================================
    # Phase 2e: Review Override & Appeal
    # ========================================================================

    async def SubmitReviewOverride(
        self,
        request: agent_service_pb2.ReviewOverrideRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.ReviewOverrideResponse:
        """
        Submit user override of a review decision.

        Allows user to override a review decision when they disagree with it.
        """
        try:
            raw_metadata = context.invocation_metadata()
            metadata = dict(raw_metadata) if raw_metadata else {}
            user_id = request.user_id or metadata.get("user-id")

            if not user_id:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("user_id is required")
                return agent_service_pb2.ReviewOverrideResponse(
                    success=False,
                    message="Authentication required",
                )

            if not request.review_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("review_id is required")
                return agent_service_pb2.ReviewOverrideResponse(
                    success=False,
                    message="review_id is required",
                )

            logger.info(
                f"SubmitReviewOverride - user={user_id}, review={request.review_id}, "
                f"original={request.original_decision} -> new={request.new_decision}"
            )

            async with self.db_session_factory() as db_session:
                from app.services.review_history_service import get_review_history_service

                history_service = get_review_history_service(db_session)

                override = await history_service.record_user_override(
                    review_id=request.review_id,
                    user_id=user_id,
                    original_decision=request.original_decision,
                    new_decision=request.new_decision,
                    reason=request.reason or "",
                )
                await db_session.commit()

                return agent_service_pb2.ReviewOverrideResponse(
                    success=True,
                    message="Override recorded successfully",
                    override_id=override.override_id,
                )

        except ValueError as e:
            logger.error(f"SubmitReviewOverride error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return agent_service_pb2.ReviewOverrideResponse(
                success=False,
                message=str(e),
            )
        except Exception as e:
            logger.error(f"SubmitReviewOverride error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.ReviewOverrideResponse(
                success=False,
                message="Internal error processing override",
            )

    async def SubmitReviewAppeal(
        self,
        request: agent_service_pb2.ReviewAppealRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.ReviewAppealResponse:
        """
        Submit an appeal against a review decision.

        Initiates a secondary review process when user disagrees with review.
        """
        try:
            raw_metadata = context.invocation_metadata()
            metadata = dict(raw_metadata) if raw_metadata else {}
            user_id = request.user_id or metadata.get("user-id")

            if not user_id:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("user_id is required")
                return agent_service_pb2.ReviewAppealResponse(
                    success=False,
                    message="Authentication required",
                )

            if not request.review_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("review_id is required")
                return agent_service_pb2.ReviewAppealResponse(
                    success=False,
                    message="review_id is required",
                )

            if not request.appeal_reason:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("appeal_reason is required")
                return agent_service_pb2.ReviewAppealResponse(
                    success=False,
                    message="appeal_reason is required",
                )

            logger.info(
                f"SubmitReviewAppeal - user={user_id}, review={request.review_id}, "
                f"reason={request.appeal_reason[:50]}..."
            )

            async with self.db_session_factory() as db_session:
                from app.services.review_appeal_service import (
                    AppealRequest,
                    get_appeal_review_service,
                )

                appeal_service = get_appeal_review_service(db_session)

                appeal_request = AppealRequest(
                    user_id=user_id,
                    review_id=request.review_id,
                    appeal_reason=request.appeal_reason,
                    issues_with_review=list(request.issues_with_review) if request.issues_with_review else [],
                )

                appeal = await appeal_service.submit_appeal(appeal_request)
                await db_session.commit()

                return agent_service_pb2.ReviewAppealResponse(
                    success=True,
                    appeal_id=appeal.appeal_id,
                    status=appeal.status.value,
                    message="Appeal submitted successfully",
                )

        except ValueError as e:
            logger.error(f"SubmitReviewAppeal error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return agent_service_pb2.ReviewAppealResponse(
                success=False,
                message=str(e),
            )
        except Exception as e:
            logger.error(f"SubmitReviewAppeal error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.ReviewAppealResponse(
                success=False,
                message="Internal error processing appeal",
            )

    async def GetAppealStatus(
        self,
        request: agent_service_pb2.AppealStatusRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.AppealStatusResponse:
        """
        Get the status of an appeal.

        Returns current status and resolution details if available.
        """
        try:
            if not request.appeal_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("appeal_id is required")
                return agent_service_pb2.AppealStatusResponse()

            logger.info(f"GetAppealStatus - appeal={request.appeal_id}")

            async with self.db_session_factory() as db_session:
                from app.services.review_appeal_service import get_appeal_review_service

                appeal_service = get_appeal_review_service(db_session)
                status_data = await appeal_service.get_appeal_status(request.appeal_id)

                if not status_data:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details("Appeal not found")
                    return agent_service_pb2.AppealStatusResponse()

                return agent_service_pb2.AppealStatusResponse(
                    appeal_id=status_data.get("appeal_id", ""),
                    review_id=status_data.get("review_id", ""),
                    status=status_data.get("status", ""),
                    submitted_at=status_data.get("submitted_at", ""),
                    appeal_reason=status_data.get("appeal_reason", ""),
                    resolution=status_data.get("resolution", ""),
                    resolved_by=status_data.get("resolved_by", ""),
                    resolved_at=status_data.get("resolved_at", ""),
                    secondary_decision=status_data.get("secondary_decision", ""),
                    secondary_score=status_data.get("secondary_score", 0.0),
                )

        except Exception as e:
            logger.error(f"GetAppealStatus error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.AppealStatusResponse()

    # ========================================================================
    # Phase 2f: Review Feedback & Regeneration
    # ========================================================================

    async def SubmitReviewFeedback(
        self,
        request: agent_service_pb2.ReviewFeedbackRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.ReviewFeedbackResponse:
        """
        Submit feedback on a review.

        Allows users to rate and provide feedback on review quality.
        """
        try:
            user_id = request.user_id

            if not user_id:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("user_id is required")
                return agent_service_pb2.ReviewFeedbackResponse(
                    success=False,
                    message="Authentication required",
                )

            if not request.review_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("review_id is required")
                return agent_service_pb2.ReviewFeedbackResponse(
                    success=False,
                    message="review_id is required",
                )

            logger.info(
                f"SubmitReviewFeedback - user={user_id}, review={request.review_id}, type={request.feedback_type}"
            )

            async with self.db_session_factory() as db_session:
                from app.services.feedback_driven_generation import (
                    FeedbackType,
                    get_feedback_driven_generation_service,
                )

                feedback_service = get_feedback_driven_generation_service(db_session)

                # Map feedback type string to enum
                feedback_type_map = {
                    "rating": FeedbackType.RATING,
                    "quality": FeedbackType.QUALITY,
                    "accuracy": FeedbackType.ACCURACY,
                    "specificity": FeedbackType.SPECIFICITY,
                }
                feedback_type = feedback_type_map.get(
                    request.feedback_type,
                    FeedbackType.RATING,
                )

                feedback = await feedback_service.submit_review_feedback(
                    review_id=request.review_id,
                    user_id=user_id,
                    feedback_type=feedback_type,
                    rating=request.rating if request.rating > 0 else None,
                    was_helpful=request.was_helpful,
                    was_accurate=request.was_accurate,
                    inaccurate_points=list(request.inaccurate_points) if request.inaccurate_points else None,
                    specificity_level=request.specificity_level if request.specificity_level else None,
                    comments=request.comments,
                    tags=list(request.tags) if request.tags else None,
                )
                await db_session.commit()

                return agent_service_pb2.ReviewFeedbackResponse(
                    success=True,
                    feedback_id=feedback.feedback_id,
                    message="Feedback submitted successfully",
                )

        except ValueError as e:
            logger.error(f"SubmitReviewFeedback error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return agent_service_pb2.ReviewFeedbackResponse(
                success=False,
                message=str(e),
            )
        except Exception as e:
            logger.error(f"SubmitReviewFeedback error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.ReviewFeedbackResponse(
                success=False,
                message="Internal error processing feedback",
            )

    async def RequestRegeneration(
        self,
        request: agent_service_pb2.RegenerationRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.RegenerationResponse:
        """
        Request content regeneration based on feedback.

        Triggers AI to regenerate content with improvements.
        """
        try:
            user_id = request.user_id

            if not user_id:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("user_id is required")
                return agent_service_pb2.RegenerationResponse(
                    success=False,
                    message="Authentication required",
                )

            if not request.original_content_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("original_content_id is required")
                return agent_service_pb2.RegenerationResponse(
                    success=False,
                    message="original_content_id is required",
                )

            logger.info(
                f"RequestRegeneration - user={user_id}, content={request.original_content_id}, "
                f"type={request.regeneration_type}"
            )

            async with self.db_session_factory() as db_session:
                from app.services.feedback_driven_generation import (
                    RegenerationType,
                    get_feedback_driven_generation_service,
                )

                regen_service = get_feedback_driven_generation_service(db_session)

                # Map regeneration type string to enum
                regen_type_map = {
                    "improve_quality": RegenerationType.IMPROVE_QUALITY,
                    "fix_issues": RegenerationType.FIX_ISSUES,
                    "change_style": RegenerationType.CHANGE_STYLE,
                    "add_details": RegenerationType.ADD_DETAILS,
                    "simplify": RegenerationType.SIMPLIFY,
                    "custom": RegenerationType.CUSTOM,
                }
                regen_type = regen_type_map.get(
                    request.regeneration_type,
                    RegenerationType.IMPROVE_QUALITY,
                )

                # Create regeneration request
                regen_request = await regen_service.request_regeneration(
                    original_content_id=request.original_content_id,
                    review_id=request.review_id,
                    user_id=user_id,
                    regeneration_type=regen_type,
                    improvement_hints=list(request.improvement_hints) if request.improvement_hints else None,
                    focus_areas=list(request.focus_areas) if request.focus_areas else None,
                    custom_instructions=request.custom_instructions,
                )

                # Process the regeneration
                result = await regen_service.process_regeneration(regen_request.request_id)
                await db_session.commit()

                return agent_service_pb2.RegenerationResponse(
                    success=result.success,
                    request_id=result.request_id,
                    new_content=result.new_content or "",
                    new_content_id=result.new_content_id or "",
                    improvement_summary=result.improvement_summary,
                    changes_made=result.changes_made,
                    score_improvement=result.score_improvement,
                    generation_time_ms=result.generation_time_ms,
                )

        except ValueError as e:
            logger.error(f"RequestRegeneration error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return agent_service_pb2.RegenerationResponse(
                success=False,
                message=str(e),
            )
        except Exception as e:
            logger.error(f"RequestRegeneration error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.RegenerationResponse(
                success=False,
                message="Internal error processing regeneration",
            )

    async def GetFeedbackStatistics(
        self,
        request: agent_service_pb2.FeedbackStatisticsRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.FeedbackStatisticsResponse:
        """
        Get feedback statistics for a user.

        Returns aggregated feedback data over a time period.
        """
        try:
            user_id = request.user_id

            if not user_id:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("user_id is required")
                return agent_service_pb2.FeedbackStatisticsResponse()

            period_days = request.period_days if request.period_days > 0 else 30

            logger.info(f"GetFeedbackStatistics - user={user_id}, period={period_days} days")

            async with self.db_session_factory() as db_session:
                from app.services.feedback_driven_generation import (
                    get_feedback_driven_generation_service,
                )

                feedback_service = get_feedback_driven_generation_service(db_session)
                stats = await feedback_service.get_feedback_statistics(days=period_days)

                return agent_service_pb2.FeedbackStatisticsResponse(
                    total_feedbacks=stats.get("total_feedbacks", 0),
                    avg_rating=stats.get("avg_rating", 0.0),
                    helpful_rate=stats.get("helpful_rate", 0.0),
                    accuracy_rate=stats.get("accuracy_rate", 0.0),
                    regeneration_requests=stats.get("regeneration_requests", 0),
                    successful_regenerations=stats.get("successful_regenerations", 0),
                    period_days=period_days,
                )

        except Exception as e:
            logger.error(f"GetFeedbackStatistics error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.FeedbackStatisticsResponse()

    # ========================================================================
    # Phase 2g: Arbitration System
    # ========================================================================

    async def GetArbitrationQueue(
        self,
        request: agent_service_pb2.GetArbitrationQueueRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.GetArbitrationQueueResponse:
        """
        Get pending arbitration cases for admins.

        Returns list of cases awaiting arbitration.
        """
        try:
            limit = request.limit if request.limit > 0 else 50
            priority_filter = request.priority_filter if request.priority_filter else None
            status_filter = request.status_filter if request.status_filter else None

            raw_metadata = context.invocation_metadata()
            metadata = dict(raw_metadata) if raw_metadata else {}
            if not await self._require_admin(context, metadata):
                return agent_service_pb2.GetArbitrationQueueResponse()

            logger.info(f"GetArbitrationQueue - limit={limit}, priority={priority_filter}, status={status_filter}")

            async with self.db_session_factory() as db_session:
                from app.services.arbitration_service import (
                    ArbitrationPriority,
                    get_arbitration_service,
                )

                arbitration_service = get_arbitration_service(db_session)

                # Map priority string to enum
                priority_map = {
                    "low": ArbitrationPriority.LOW,
                    "normal": ArbitrationPriority.NORMAL,
                    "high": ArbitrationPriority.HIGH,
                    "urgent": ArbitrationPriority.URGENT,
                }
                priority = priority_map.get(priority_filter) if priority_filter else None

                cases = await arbitration_service.get_pending_queue(
                    limit=limit,
                    priority=priority,
                )

                # Filter by status if specified
                if status_filter:
                    cases = [c for c in cases if c.status == status_filter]

                # Convert to proto
                proto_cases = []
                for case in cases:
                    proto_case = agent_service_pb2.ArbitrationCaseInfo(
                        case_id=case.case_id,
                        appeal_id=case.appeal_id,
                        review_id=case.review_id,
                        user_id=case.user_id,
                        escalation_reason=case.escalation_reason.value,
                        priority=case.priority.value,
                        created_at=case.created_at,
                        status=case.status,
                        assigned_to=case.assigned_to or "",
                        assigned_at=case.assigned_at or "",
                        original_review_score=case.original_review_score,
                        secondary_review_score=case.secondary_review_score or 0.0,
                        score_discrepancy=case.score_discrepancy,
                        resolution=case.resolution or "",
                        final_decision=case.final_decision or "",
                        resolved_at=case.resolved_at or "",
                        resolved_by=case.resolved_by or "",
                        notes=case.notes,
                    )
                    proto_cases.append(proto_case)

                return agent_service_pb2.GetArbitrationQueueResponse(
                    cases=proto_cases,
                    total_count=len(cases),
                )

        except Exception as e:
            logger.error(f"GetArbitrationQueue error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.GetArbitrationQueueResponse()

    async def AssignArbitrationCase(
        self,
        request: agent_service_pb2.AssignArbitrationCaseRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.AssignArbitrationCaseResponse:
        """
        Assign an arbitration case to an arbitrator.

        Claims a case for review by an admin.
        """
        try:
            raw_metadata = context.invocation_metadata()
            metadata = dict(raw_metadata) if raw_metadata else {}
            if not await self._require_admin(context, metadata):
                return agent_service_pb2.AssignArbitrationCaseResponse(
                    success=False,
                    message="Admin access required",
                )

            if not request.case_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("case_id is required")
                return agent_service_pb2.AssignArbitrationCaseResponse(
                    success=False,
                    message="case_id is required",
                )

            if not request.arbitrator_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("arbitrator_id is required")
                return agent_service_pb2.AssignArbitrationCaseResponse(
                    success=False,
                    message="arbitrator_id is required",
                )

            logger.info(f"AssignArbitrationCase - case={request.case_id}, arbitrator={request.arbitrator_id}")

            async with self.db_session_factory() as db_session:
                from app.services.arbitration_service import (
                    ArbitratorRole,
                    get_arbitration_service,
                )

                arbitration_service = get_arbitration_service(db_session)

                # Map role string to enum
                role_map = {
                    "auto": ArbitratorRole.AUTO,
                    "reviewer": ArbitratorRole.REVIEWER,
                    "senior": ArbitratorRole.SENIOR,
                    "admin": ArbitratorRole.ADMIN,
                }
                role = role_map.get(
                    request.arbitrator_role,
                    ArbitratorRole.REVIEWER,
                )

                await arbitration_service.assign_case(
                    case_id=request.case_id,
                    arbitrator_id=request.arbitrator_id,
                    arbitrator_role=role,
                )
                await db_session.commit()

                return agent_service_pb2.AssignArbitrationCaseResponse(
                    success=True,
                    message=f"Case {request.case_id} assigned to {request.arbitrator_id}",
                )

        except ValueError as e:
            logger.error(f"AssignArbitrationCase error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return agent_service_pb2.AssignArbitrationCaseResponse(
                success=False,
                message=str(e),
            )
        except Exception as e:
            logger.error(f"AssignArbitrationCase error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.AssignArbitrationCaseResponse(
                success=False,
                message="Internal error assigning case",
            )

    async def SubmitArbitrationDecision(
        self,
        request: agent_service_pb2.SubmitArbitrationDecisionRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.SubmitArbitrationDecisionResponse:
        """
        Submit an arbitrator's decision on a case.

        Finalizes the arbitration with a decision.
        """
        try:
            raw_metadata = context.invocation_metadata()
            metadata = dict(raw_metadata) if raw_metadata else {}
            if not await self._require_admin(context, metadata):
                return agent_service_pb2.SubmitArbitrationDecisionResponse(
                    success=False,
                    message="Admin access required",
                )

            if not request.case_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("case_id is required")
                return agent_service_pb2.SubmitArbitrationDecisionResponse(
                    success=False,
                    message="case_id is required",
                )

            if not request.decision:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("decision is required")
                return agent_service_pb2.SubmitArbitrationDecisionResponse(
                    success=False,
                    message="decision is required",
                )

            if not request.arbitrator_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("arbitrator_id is required")
                return agent_service_pb2.SubmitArbitrationDecisionResponse(
                    success=False,
                    message="arbitrator_id is required",
                )

            logger.info(f"SubmitArbitrationDecision - case={request.case_id}, decision={request.decision}")

            async with self.db_session_factory() as db_session:
                from app.services.arbitration_service import (
                    AppealDecision,
                    ArbitratorRole,
                    get_arbitration_service,
                )

                arbitration_service = get_arbitration_service(db_session)

                # Map decision string to enum
                decision_map = {
                    "approved": AppealDecision.APPROVED,
                    "rejected": AppealDecision.REJECTED,
                    "partially_approved": AppealDecision.PARTIALLY_APPROVED,
                    "escalated": AppealDecision.ESCALATED,
                }
                decision = decision_map.get(request.decision)
                if not decision:
                    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                    context.set_details(f"Invalid decision: {request.decision}")
                    return agent_service_pb2.SubmitArbitrationDecisionResponse(
                        success=False,
                        message=f"Invalid decision: {request.decision}",
                    )

                # Map role string to enum
                role_map = {
                    "auto": ArbitratorRole.AUTO,
                    "reviewer": ArbitratorRole.REVIEWER,
                    "senior": ArbitratorRole.SENIOR,
                    "admin": ArbitratorRole.ADMIN,
                }
                role = role_map.get(
                    request.arbitrator_role,
                    ArbitratorRole.REVIEWER,
                )

                arb_decision = await arbitration_service.submit_decision(
                    case_id=request.case_id,
                    decision=decision,
                    explanation=request.explanation,
                    arbitrator_id=request.arbitrator_id,
                    arbitrator_role=role,
                    feedback_for_model=request.feedback_for_model,
                )
                await db_session.commit()

                return agent_service_pb2.SubmitArbitrationDecisionResponse(
                    success=True,
                    decision_id=arb_decision.case_id,  # Use case_id as decision_id
                    message="Decision submitted successfully",
                )

        except ValueError as e:
            logger.error(f"SubmitArbitrationDecision error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return agent_service_pb2.SubmitArbitrationDecisionResponse(
                success=False,
                message=str(e),
            )
        except Exception as e:
            logger.error(f"SubmitArbitrationDecision error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.SubmitArbitrationDecisionResponse(
                success=False,
                message="Internal error submitting decision",
            )

    async def GetArbitrationQueueStats(
        self,
        request: agent_service_pb2.GetArbitrationQueueStatsRequest,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.GetArbitrationQueueStatsResponse:
        """
        Get arbitration queue statistics.

        Returns statistics about pending cases and resolution metrics.
        """
        try:
            logger.info("GetArbitrationQueueStats")

            raw_metadata = context.invocation_metadata()
            metadata = dict(raw_metadata) if raw_metadata else {}
            if not await self._require_admin(context, metadata):
                return agent_service_pb2.GetArbitrationQueueStatsResponse()

            async with self.db_session_factory() as db_session:
                from app.services.arbitration_service import get_arbitration_service

                arbitration_service = get_arbitration_service(db_session)
                stats = await arbitration_service.get_queue_stats()

                proto_stats = agent_service_pb2.ArbitrationQueueStatsInfo(
                    total_pending=stats.total_pending,
                    total_assigned=stats.total_assigned,
                    total_in_review=stats.total_in_review,
                    total_resolved_today=stats.total_resolved_today,
                    avg_resolution_time_hours=stats.avg_resolution_time_hours,
                    by_priority=stats.by_priority,
                    by_reason=stats.by_reason,
                )

                return agent_service_pb2.GetArbitrationQueueStatsResponse(
                    stats=proto_stats,
                )

        except Exception as e:
            logger.error(f"GetArbitrationQueueStats error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.GetArbitrationQueueStatsResponse()
