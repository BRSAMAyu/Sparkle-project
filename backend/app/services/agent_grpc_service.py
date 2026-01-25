"""
AgentService gRPC Implementation
实现 gRPC 服务端，对接现有的 LLM 服务和 RAG 能力
"""
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import AsyncIterator, Callable

import grpc
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.gen.agent.v1 import agent_service_pb2, agent_service_pb2_grpc
from app.learning.prompt_bandit import PromptBandit
from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.plan_review_service import plan_review_service, ReviewDecision
from app.services.response_feedback_service import ResponseFeedbackService
from app.core.metrics import FEEDBACK_TO_EFFECT_SECONDS


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

    async def StreamChat(
        self,
        request: agent_service_pb2.ChatRequest,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[agent_service_pb2.ChatResponse]:
        """
        处理流式聊天请求
        实现打字机效果的 AI 响应
        """
        try:
            # 从 metadata 获取追踪信息
            raw_metadata = context.invocation_metadata()
            metadata = {k: v for k, v in raw_metadata} if raw_metadata else {}
            user_id = request.user_id or metadata.get("user-id", "")
            
            # Security Audit: Log missing authorization headers
            if not metadata.get("authorization") and not request.user_id:
                logger.warning(f"SECURITY ALERT: StreamChat call without authorization metadata or user_id. Session: {request.session_id}")
            elif metadata.get("authorization"):
                logger.debug(f"Auth metadata found for user_id={user_id}")
            
            trace_id = metadata.get("x-trace-id", request.request_id) or str(uuid.uuid4())

            workflow_id = "standard_chat"
            prompt_versions = ["v1", "v2"]
            prompt_version = "v1"
            try:
                bandit = PromptBandit(redis_client=self.orchestrator.redis)
                prompt_version = await bandit.select(workflow_id, prompt_versions)
            except Exception as e:
                logger.warning(f"Prompt bandit selection failed: {e}")

            await self._observe_feedback_effect(user_id, workflow_id, prompt_version)

            logger.info(
                f"StreamChat started - user_id={user_id}, session={request.session_id}, trace={trace_id}, "
                f"workflow={workflow_id}, prompt_version={prompt_version}"
            )

            # Create a dedicated DB session for this stream
            async with self.db_session_factory() as db_session:
                try:
                    # Delegate to Orchestrator
                    async for response in self.orchestrator.process_stream(
                        request,
                        db_session=db_session,
                        context_data={
                            "workflow_id": workflow_id,
                            "prompt_version": prompt_version,
                        },
                    ):
                        response.trace_id = trace_id
                        if not response.workflow_id:
                            response.workflow_id = workflow_id
                        if not response.prompt_version:
                            response.prompt_version = prompt_version
                        yield response
                    await db_session.commit()
                except Exception:
                    await db_session.rollback()
                    raise

            logger.info(f"StreamChat completed for trace={trace_id}")

        except Exception as e:
            logger.error(f"StreamChat error: {e}", exc_info=True)
            yield agent_service_pb2.ChatResponse(
                response_id=str(uuid.uuid4()),
                created_at=int(datetime.now().timestamp()),
                request_id=request.request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                error=agent_service_pb2.Error(
                    code="INTERNAL_ERROR",
                    message=str(e),
                    retryable=True
                ),
                finish_reason=agent_service_pb2.STOP # Using STOP as finish reason even for errors in gRPC mapping if needed, or define ERROR
            )

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
            metadata = {k: v for k, v in raw_metadata} if raw_metadata else {}
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
            FEEDBACK_TO_EFFECT_SECONDS.labels(
                workflow_id=workflow_id,
                prompt_version=prompt_version
            ).observe(delta)
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
                from app.services.galaxy_service import GalaxyService
                import uuid
                
                # Use GalaxyService for structured search
                galaxy_service = GalaxyService(db_session)
                
                # Perform semantic search
                search_results = await galaxy_service.semantic_search(
                    user_id=uuid.UUID(request.user_id),
                    query=request.query_text,
                    limit=request.limit if request.limit > 0 else 10,
                    threshold=request.min_score if request.min_score > 0 else 0.3
                )
                
                # Convert to gRPC MemoryResult items
                memory_items = []
                for result in search_results:
                    # Build metadata
                    metadata = {
                        "sector_code": result.node.sector_code.value if hasattr(result.node.sector_code, 'value') else str(result.node.sector_code),
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
                        metadata=metadata
                    )
                    memory_items.append(memory_item)
                
                return agent_service_pb2.MemoryResult(
                    items=memory_items,
                    total_found=len(memory_items)
                )

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
                    str(key): str(value)
                    for key, value in (user_context.preferences or {}).items()
                    if value is not None
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

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)

            async with self.db_session_factory() as db_session:
                from app.services.analytics.weekly_stats_service import WeeklyStatsService

                stats_service = WeeklyStatsService(db_session)
                stats = await stats_service.get_weekly_summary(request.user_id, start_date, end_date)

                summary_text = (
                    f"Week {request.week_id or start_date.isocalendar()[1]}: "
                    f"{stats.get('tasks_completed', 0)} tasks completed, "
                    f"{stats.get('total_study_minutes', 0)} minutes studied, "
                    f"{stats.get('focus_sessions_count', 0)} focus sessions."
                )

                return agent_service_pb2.WeeklyReport(
                    summary=summary_text,
                    tasks_completed=stats.get("tasks_completed", 0),
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
            metadata = {k: v for k, v in raw_metadata} if raw_metadata else {}
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
                                f"Phase rollback will be triggered for plan {plan_id} "
                                f"(rejection_count={count})"
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
                    )
                logger.info(f"Plan {plan_id} resumed after approval by {user_id}, task_generation={result.get('task_generation_initiated')}")

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
