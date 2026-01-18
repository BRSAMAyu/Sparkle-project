"""
AgentService gRPC Implementation
实现 gRPC 服务端，对接现有的 LLM 服务和 RAG 能力
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import AsyncIterator, Callable

import grpc
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.gen.agent.v1 import agent_service_pb2, agent_service_pb2_grpc
from app.learning.prompt_bandit import PromptBandit
from app.orchestration.orchestrator import ChatOrchestrator
from app.services.response_feedback_service import ResponseFeedbackService


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
