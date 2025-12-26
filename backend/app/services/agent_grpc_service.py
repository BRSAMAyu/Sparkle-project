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
from app.services.llm_service import LLMService
from app.db.session import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, ChatMessage as DBChatMessage
from app.config import settings


class AgentServiceImpl(agent_service_pb2_grpc.AgentServiceServicer):
    """
    AgentService 的 gRPC 实现
    负责处理流式对话和记忆检索
    """

    def __init__(self):
        self.llm_service = LLMService()
        logger.info("AgentServiceImpl initialized")

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

            # 发送状态更新：开始处理
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{trace_id}_0",
                created_at=int(datetime.now().timestamp()),
                request_id=request.request_id,
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.THINKING,
                    details="正在思考..."
                )
            )

            # 获取用户消息
            user_message = ""
            if request.HasField("message"):
                user_message = request.message
            elif request.HasField("tool_result"):
                # 处理工具调用结果
                tool_result = request.tool_result
                user_message = f"工具 {tool_result.tool_name} 执行结果: {tool_result.result_json}"

            if not user_message:
                yield agent_service_pb2.ChatResponse(
                    response_id=f"resp_{trace_id}_error",
                    created_at=int(datetime.now().timestamp()),
                    request_id=request.request_id,
                    error=agent_service_pb2.Error(
                        code="INVALID_REQUEST",
                        message="消息内容不能为空",
                        retryable=False
                    ),
                    finish_reason=agent_service_pb2.ERROR
                )
                return

            # 构建对话历史
            messages = []

            # 添加系统提示词
            messages.append({
                "role": "system",
                "content": self._build_system_prompt(request.user_profile)
            })

            # 添加历史消息
            for hist_msg in request.history:
                messages.append({
                    "role": hist_msg.role,
                    "content": hist_msg.content
                })

            # 添加当前用户消息
            messages.append({
                "role": "user",
                "content": user_message
            })

            # 发送状态更新：开始生成
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{trace_id}_1",
                created_at=int(datetime.now().timestamp()),
                request_id=request.request_id,
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.GENERATING,
                    details="正在生成回复..."
                )
            )

            # 调用 LLM 服务进行流式生成
            full_response = ""
            chunk_count = 0

            # 获取配置
            model = request.config.model if request.config and request.config.model else None
            temperature = request.config.temperature if request.config and request.config.temperature > 0 else None
            max_tokens = request.config.max_tokens if request.config and request.config.max_tokens > 0 else None

            async for chunk in self.llm_service.stream_chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                if chunk:
                    full_response += chunk
                    chunk_count += 1

                    # 流式发送文本片段
                    yield agent_service_pb2.ChatResponse(
                        response_id=f"resp_{trace_id}_{chunk_count}",
                        created_at=int(datetime.now().timestamp()),
                        request_id=request.request_id,
                        delta=chunk
                    )

            # 发送最终完整响应
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{trace_id}_final",
                created_at=int(datetime.now().timestamp()),
                request_id=request.request_id,
                full_text=full_response,
                finish_reason=agent_service_pb2.STOP,
                usage=agent_service_pb2.Usage(
                    prompt_tokens=0,  # TODO: 从 LLM 响应中获取
                    completion_tokens=0,
                    total_tokens=0
                )
            )

            logger.info(f"StreamChat completed - chunks={chunk_count}, length={len(full_response)}")

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
                finish_reason=agent_service_pb2.ERROR
            )

    async def RetrieveMemory(
        self,
        request: agent_service_pb2.MemoryQuery,
        context: grpc.aio.ServicerContext,
    ) -> agent_service_pb2.MemoryResult:
        """
        从向量数据库检索长期记忆
        实现 RAG (Retrieval-Augmented Generation)
        """
        try:
            logger.info(f"RetrieveMemory - user={request.user_id}, query={request.query_text[:50]}...")

            # TODO: 实现向量检索
            # 1. 将 query_text 转换为 embedding
            # 2. 在 pgvector 中进行相似度搜索
            # 3. 返回最相关的记忆片段

            # 临时返回空结果
            return agent_service_pb2.MemoryResult(
                items=[],
                total_found=0
            )

        except Exception as e:
            logger.error(f"RetrieveMemory error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_service_pb2.MemoryResult(items=[], total_found=0)

    def _build_system_prompt(self, user_profile: Optional[agent_service_pb2.UserProfile]) -> str:
        """
        构建系统提示词
        根据用户画像进行个性化
        """
        base_prompt = """你是 Sparkle AI，一个智能学习助手。你的职责是：
1. 帮助学生制定学习计划
2. 解答学习问题
3. 提供个性化的学习建议
4. 使用知识星图追踪学习进度

请用简洁、友好的语言回复，必要时使用 emoji 增加亲和力。"""

        if user_profile:
            nickname = user_profile.nickname or "同学"
            base_prompt = f"你是 Sparkle AI，{nickname}的专属学习助手。" + base_prompt[len("你是 Sparkle AI，"):]

            # 根据偏好调整
            preferences = dict(user_profile.preferences)
            if preferences.get("concise_mode") == "true":
                base_prompt += "\n\n注意：用户偏好简洁模式，请用最精炼的语言回复。"

        return base_prompt
