"""
AgentService gRPC Implementation
实现 gRPC 服务端，对接现有的 LLM 服务和 RAG 能力
"""
import asyncio
import json
from typing import AsyncIterator, Optional
from datetime import datetime
from loguru import logger
import grpc

from app.gen.agent.v1 import agent_service_pb2, agent_service_pb2_grpc
from app.orchestration.orchestrator import ChatOrchestrator
from app.db.session import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.config import settings


class AgentServiceImpl(agent_service_pb2_grpc.AgentServiceServicer):
    """
    AgentService 的 gRPC 实现
    负责处理流式对话和记忆检索
    """

    def __init__(self):
        # 初始化 Orchestrator
        self.orchestrator = ChatOrchestrator()
        logger.info("AgentServiceImpl initialized with ChatOrchestrator")

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
            metadata = dict(context.invocation_metadata())
            user_id = request.user_id or metadata.get("user-id", "")
            trace_id = metadata.get("x-trace-id", request.request_id)

            logger.info(f"StreamChat started - user_id={user_id}, session={request.session_id}, trace={trace_id}")

            # Create a dedicated DB session for this stream
            async with AsyncSessionLocal() as db_session:
                # Delegate to Orchestrator
                async for response in self.orchestrator.process_stream(request, db_session=db_session):
                    yield response

            logger.info(f"StreamChat completed for trace={trace_id}")

        except Exception as e:
            logger.error(f"StreamChat error: {e}", exc_info=True)
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_error_{datetime.now().timestamp()}",
                created_at=int(datetime.now().timestamp()),
                request_id=request.request_id,
                error=agent_service_pb2.Error(
                    code="INTERNAL_ERROR",
                    message=str(e),
                    retryable=True
                ),
                finish_reason=agent_service_pb2.STOP # Using STOP as finish reason even for errors in gRPC mapping if needed, or define ERROR
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

            async with AsyncSessionLocal() as db_session:
                from app.services.knowledge_service import KnowledgeService
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