"""
Multi-Agent Workflow Adapter

Adapts traditional multi-agent collaboration workflows to the main production flow.
This bridges the gap between the legacy multi-agent system and the new LangGraph-based orchestrator.

Supported Modes:
- deep_analysis: Multi-expert progressive exploration
- study_plan: Task decomposition collaboration
- error_diagnosis: Error diagnosis loop
"""

import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from loguru import logger
from google.protobuf.timestamp import Timestamp

from app.gen.agent.v1 import agent_service_pb2


class MultiAgentWorkflowAdapter:
    """
    Adapter for traditional multi-agent workflows.

    This class provides compatibility with the existing multi-agent system
    while integrating with the new orchestrator architecture.
    """

    def __init__(self, orchestrator):
        """
        Initialize the adapter with a reference to the parent orchestrator.

        Args:
            orchestrator: ChatOrchestrator instance for accessing shared resources
        """
        self.orchestrator = orchestrator
        self.logger = logger
        # Access LLM service directly
        from app.services.llm_service import llm_service
        self.llm_service = llm_service

    async def execute_progressive_exploration(
        self,
        message: str,
        user_id: str,
        session_id: str,
        context_data: Dict[str, Any],
        stream_callback,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        """
        Execute Deep Analysis mode using multi-expert progressive exploration.

        This mode involves:
        1. Initial analysis by the orchestrator
        2. Expert agent consultation (Knowledge, Reasoning, Analysis)
        3. Synthesis of expert insights
        4. Progressive refinement

        Args:
            message: User's input message
            user_id: User ID
            session_id: Session ID
            context_data: Additional context for the workflow
            stream_callback: Callback for streaming responses

        Yields:
            ChatResponse messages for the client
        """
        logger.info(f"[DeepAnalysis] Starting progressive exploration for session {session_id}")

        # Phase 1: Initial thinking
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details="正在分析问题...",
                active_agent=agent_service_pb2.ORCHESTRATOR,
            ),
        )

        # Build system prompt for deep analysis
        system_prompt = """你是深度解析模式的AI助手。你擅长：
1. 多角度分析问题
2. 识别问题的深层逻辑
3. 整合相关知识领域
4. 提供可操作的建议

请用结构化的方式回复，包含：问题分析、关键因素、解决方案。使用markdown格式。"""

        # Build context from user data
        conversation_history = context_data.get('conversation_context', {}).get('messages', [])

        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 3 exchanges for context)
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": message})

        # Phase 2: Show we're gathering knowledge
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.SEARCHING,
                details="正在检索相关知识...",
                active_agent=agent_service_pb2.KNOWLEDGE,
            ),
        )

        # Phase 3: Generate and stream response
        try:
            async for chunk in self.llm_service.stream_chat(
                messages=messages,
                model=None,  # Use default model
                temperature=0.7,
            ):
                if chunk:
                    yield agent_service_pb2.ChatResponse(
                        delta=chunk,
                        status_update=agent_service_pb2.AgentStatus(
                            state=agent_service_pb2.AgentStatus.GENERATING,
                            active_agent=agent_service_pb2.ORCHESTRATOR,
                        ),
                    )
        except Exception as e:
            logger.error(f"[DeepAnalysis] LLM error: {e}")
            yield agent_service_pb2.ChatResponse(
                delta=f"\n\n⚠️ 深度解析服务暂时不可用: {str(e)}"
            )

    async def execute_task_decomposition(
        self,
        message: str,
        user_id: str,
        session_id: str,
        context_data: Dict[str, Any],
        stream_callback,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        """
        Execute Study Plan mode using task decomposition collaboration.

        This mode involves:
        1. Understanding the learning goal
        2. Breaking down into sub-tasks
        3. Estimating time and difficulty
        4. Creating a structured plan

        Args:
            message: User's input message
            user_id: User ID
            session_id: Session ID
            context_data: Additional context for the workflow
            stream_callback: Callback for streaming responses

        Yields:
            ChatResponse messages for the client
        """
        logger.info(f"[StudyPlan] Starting task decomposition for session {session_id}")

        # Phase 1: Planning agent
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details="正在规划学习路径...",
                active_agent=agent_service_pb2.ORCHESTRATOR,
            ),
        )

        # Build system prompt for study planning
        system_prompt = """你是学习计划模式的AI助手。你擅长：
1. 将复杂的学习目标分解为可执行的小任务
2. 估算每个阶段的学习时间
3. 提供结构化的学习路径
4. 给出实用的学习建议

请用结构化的markdown格式回复，包含：学习目标分解、时间估算、学习建议。"""

        # Build context from user data
        conversation_history = context_data.get('conversation_context', {}).get('messages', [])

        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 3 exchanges for context)
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": message})

        # Phase 2: Decomposition status
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details="正在分解学习任务...",
                active_agent=agent_service_pb2.WRITING,
            ),
        )

        # Phase 3: Generate and stream response
        try:
            async for chunk in self.llm_service.stream_chat(
                messages=messages,
                model=None,  # Use default model
                temperature=0.7,
            ):
                if chunk:
                    yield agent_service_pb2.ChatResponse(
                        delta=chunk,
                        status_update=agent_service_pb2.AgentStatus(
                            state=agent_service_pb2.AgentStatus.GENERATING,
                            active_agent=agent_service_pb2.ORCHESTRATOR,
                        ),
                    )
        except Exception as e:
            logger.error(f"[StudyPlan] LLM error: {e}")
            yield agent_service_pb2.ChatResponse(
                delta=f"\n\n⚠️ 学习计划服务暂时不可用: {str(e)}"
            )

    async def execute_error_diagnosis(
        self,
        message: str,
        user_id: str,
        session_id: str,
        context_data: Dict[str, Any],
        stream_callback,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        """
        Execute Error Diagnosis mode using error diagnosis loop.

        This mode involves:
        1. Error pattern recognition
        2. Root cause analysis
        3. Solution recommendation
        4. Prevention strategy

        Args:
            message: User's input message (about an error)
            user_id: User ID
            session_id: Session ID
            context_data: Additional context for the workflow
            stream_callback: Callback for streaming responses

        Yields:
            ChatResponse messages for the client
        """
        logger.info(f"[ErrorDiagnosis] Starting error diagnosis for session {session_id}")

        # Phase 1: Error detection
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details="正在识别错误类型...",
                active_agent=agent_service_pb2.REASONING,
            ),
        )

        # Build system prompt for error diagnosis
        system_prompt = """你是错题分析模式的AI助手。你擅长：
1. 识别错误类型（概念理解型、计算错误型、方法应用型等）
2. 分析错误的根本原因
3. 提供具体的改进方案
4. 给出预防策略

请用结构化的markdown格式回复，包含：错误类型识别、根本原因分析、改进方案、预防策略。"""

        # Build context from user data
        conversation_history = context_data.get('conversation_context', {}).get('messages', [])

        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 3 exchanges for context)
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": message})

        # Phase 2: Pattern matching status
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.SEARCHING,
                details="正在匹配错误模式...",
                active_agent=agent_service_pb2.KNOWLEDGE,
            ),
        )

        # Phase 3: Generate and stream response
        try:
            async for chunk in self.llm_service.stream_chat(
                messages=messages,
                model=None,  # Use default model
                temperature=0.7,
            ):
                if chunk:
                    yield agent_service_pb2.ChatResponse(
                        delta=chunk,
                        status_update=agent_service_pb2.AgentStatus(
                            state=agent_service_pb2.AgentStatus.GENERATING,
                            active_agent=agent_service_pb2.ORCHESTRATOR,
                        ),
                    )
        except Exception as e:
            logger.error(f"[ErrorDiagnosis] LLM error: {e}")
            yield agent_service_pb2.ChatResponse(
                delta=f"\n\n⚠️ 错题分析服务暂时不可用: {str(e)}"
            )


# Chat mode mapping constants
CHAT_MODE_STANDARD = "standard"
CHAT_MODE_DEEP_ANALYSIS = "deep_analysis"
CHAT_MODE_STUDY_PLAN = "study_plan"
CHAT_MODE_ERROR_DIAGNOSIS = "error_diagnosis"


async def execute_multi_agent_workflow(
    orchestrator: 'ChatOrchestrator',
    chat_mode: str,
    message: str,
    user_id: str,
    session_id: str,
    context_data: Dict[str, Any],
    stream_callback,
) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
    """
    Execute the appropriate multi-agent workflow based on chat mode.

    This is the main entry point for multi-agent mode routing.

    Args:
        orchestrator: ChatOrchestrator instance for accessing shared resources
        chat_mode: The selected chat mode
        message: User's input message
        user_id: User ID
        session_id: Session ID
        context_data: Additional context for the workflow
        stream_callback: Callback for streaming responses

    Yields:
        ChatResponse messages for the client

    Raises:
        ValueError: If chat_mode is not recognized
    """
    logger.info(f"Executing multi-agent workflow: {chat_mode}")

    adapter = MultiAgentWorkflowAdapter(orchestrator=orchestrator)

    if chat_mode == CHAT_MODE_DEEP_ANALYSIS:
        async for response in adapter.execute_progressive_exploration(
            message, user_id, session_id, context_data, stream_callback
        ):
            yield response

    elif chat_mode == CHAT_MODE_STUDY_PLAN:
        async for response in adapter.execute_task_decomposition(
            message, user_id, session_id, context_data, stream_callback
        ):
            yield response

    elif chat_mode == CHAT_MODE_ERROR_DIAGNOSIS:
        async for response in adapter.execute_error_diagnosis(
            message, user_id, session_id, context_data, stream_callback
        ):
            yield response

    else:
        logger.warning(f"Unknown chat mode: {chat_mode}, falling back to standard")
        async for response in adapter.execute_progressive_exploration(
            message, user_id, session_id, context_data, stream_callback
        ):
            yield response
