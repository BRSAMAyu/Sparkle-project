"""
Multi-Agent Workflow Adapter

Adapts traditional multi-agent collaboration workflows to the main production flow.
This bridges the gap between the legacy multi-agent system and the new LangGraph-based orchestrator.

Supported Modes:
- deep_analysis: Multi-expert progressive exploration
- study_plan: Task decomposition collaboration
- error_diagnosis: Error diagnosis loop
"""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.prompts import build_system_prompt

if TYPE_CHECKING:
    from app.orchestration.orchestrator import ChatOrchestrator

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
        # 🔧 修复：创建新的 LLMService 实例而不是使用全局实例
        # 这确保在运行时使用最新的环境变量配置
        from app.services.llm_service import LLMService
        from app.core.agent_profiles import AgentRole
        try:
            self.llm_service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)
            logger.info(f"[MultiAgent] LLMService initialized with model: {self.llm_service.chat_model}")
        except Exception as e:
            logger.error(f"[MultiAgent] Failed to initialize LLMService: {e}", exc_info=True)
            # Fallback to global instance
            from app.services.llm_service import llm_service
            self.llm_service = llm_service

    async def execute_progressive_exploration(
        self,
        message: str,
        user_id: str,
        session_id: str,
        context_data: dict[str, Any],
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

        # Build system prompt for deep analysis (inject user context)
        base_prompt = build_system_prompt(
            context_data.get("user_context") or {},
            conversation_history=context_data.get("conversation_context") or {},
            prompt_version=context_data.get("prompt_version") or "v1",
            plan_context=context_data.get("plan_context"),
        )
        system_prompt = f"""{base_prompt}

## 深度解析模式指令
目标：帮助用户获得深层、可验证、可执行的理解与方案。
原则：
1. 先澄清问题边界与假设，必要时列出需补充的信息
2. 结构化拆解问题（因果、约束、权衡、关键变量）
3. 多视角验证（反例、风险、替代路径）
4. 输出可执行建议，并说明验证方式

输出要求（Markdown）：
- 问题复述与边界
- 关键因素/约束
- 分析过程（可用要点或小节）
- 结论与可执行方案
- 风险与验证步骤（含可观测指标/验收标准）"""

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
            logger.info(f"[DeepAnalysis] Calling LLM service with {len(messages)} messages")
            chunk_count = 0
            first_chunk = True
            async for chunk in self.llm_service.stream_chat(
                messages=messages,
                model=None,  # Use default model
                temperature=0.7,
            ):
                if chunk:
                    chunk_count += 1
                    if chunk_count == 1:
                        logger.info(f"[DeepAnalysis] Received first chunk from LLM: '{chunk[:50]}...'")
                    # 🔧 调试：每10个chunk记录一次
                    if chunk_count % 10 == 0:
                        logger.info(f"[DeepAnalysis] Processed {chunk_count} chunks, current: '{chunk[:30]}...'")

                    # 🔧 修复：在第一个chunk之前发送GENERATING状态（oneof要求分开发送）
                    if first_chunk:
                        yield agent_service_pb2.ChatResponse(
                            status_update=agent_service_pb2.AgentStatus(
                                state=agent_service_pb2.AgentStatus.GENERATING,
                                details="正在生成深度分析...",
                                active_agent=agent_service_pb2.ORCHESTRATOR,
                            ),
                        )
                        first_chunk = False

                    # 🔧 修复：只设置 delta，不设置 status_update（它们是 oneof，会互相覆盖）
                    response = agent_service_pb2.ChatResponse(delta=chunk)
                    logger.debug(f"[DeepAnalysis] Yielding response {chunk_count} with delta length: {len(chunk)}")
                    yield response

            logger.info(f"[DeepAnalysis] LLM stream completed with {chunk_count} chunks")

            # 🔧 修复：如果没有生成任何内容，提供默认回复
            if chunk_count == 0:
                logger.error(f"[DeepAnalysis] No chunks received from LLM! Check LLM service configuration.")
                yield agent_service_pb2.ChatResponse(
                    delta="⚠️ 深度解析模式暂时无法生成回复。LLM 服务可能未正确配置，请检查 API 密钥和网络连接。",
                )

            # 🔧 修复：发送流结束信号，清除前端状态（isSending, aiStatus等）
            yield agent_service_pb2.ChatResponse(
                finish_reason=agent_service_pb2.STOP,
            )
            logger.info(f"[DeepAnalysis] Sent finish_reason=STOP signal")

        except Exception as e:
            logger.error(f"[DeepAnalysis] LLM error: {e}", exc_info=True)
            logger.error(f"[DeepAnalysis] Messages sent: {messages}")
            yield agent_service_pb2.ChatResponse(
                delta=f"\n\n⚠️ 深度解析服务暂时不可用: {str(e)}\n\n请检查后端日志获取详细信息。",
                finish_reason=agent_service_pb2.ERROR,
            )

    async def execute_task_decomposition(
        self,
        message: str,
        user_id: str,
        session_id: str,
        context_data: dict[str, Any],
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

        # Build system prompt for study planning (inject user context)
        base_prompt = build_system_prompt(
            context_data.get("user_context") or {},
            conversation_history=context_data.get("conversation_context") or {},
            prompt_version=context_data.get("prompt_version") or "v1",
            plan_context=context_data.get("plan_context"),
        )
        system_prompt = f"""{base_prompt}

## 学习计划模式指令
目标：把学习目标转化为可执行、可跟踪、可调整的计划。
原则：
1. 明确学习目标与评估标准（能做什么/达到什么水平）
2. 自顶向下拆解为阶段与任务，并标注先后依赖
3. 给出时间估算与每周节奏（可调整）
4. 加入复盘与纠错机制，避免只学不练

输出要求（Markdown）：
- 目标与评估标准
- 阶段拆解（阶段目标/任务/产出）
- 时间安排（每周节奏与里程碑）
- 学习建议（资源类型、练习方式、复盘机制）
- 风险与应对（可能掉队的点与补救方式）"""

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
            first_chunk = True
            async for chunk in self.llm_service.stream_chat(
                messages=messages,
                model=None,  # Use default model
                temperature=0.7,
            ):
                if chunk:
                    # 🔧 修复：在第一个chunk之前发送GENERATING状态（oneof要求分开发送）
                    if first_chunk:
                        yield agent_service_pb2.ChatResponse(
                            status_update=agent_service_pb2.AgentStatus(
                                state=agent_service_pb2.AgentStatus.GENERATING,
                                details="正在生成学习计划...",
                                active_agent=agent_service_pb2.ORCHESTRATOR,
                            ),
                        )
                        first_chunk = False

                    # 🔧 修复：只设置 delta，不设置 status_update（它们是 oneof，会互相覆盖）
                    yield agent_service_pb2.ChatResponse(delta=chunk)

            # 🔧 修复：发送流结束信号，清除前端状态
            yield agent_service_pb2.ChatResponse(
                finish_reason=agent_service_pb2.STOP,
            )
            logger.info(f"[StudyPlan] Sent finish_reason=STOP signal")

        except Exception as e:
            logger.error(f"[StudyPlan] LLM error: {e}")
            yield agent_service_pb2.ChatResponse(
                delta=f"\n\n⚠️ 学习计划服务暂时不可用: {str(e)}",
                finish_reason=agent_service_pb2.ERROR,
            )

    async def execute_error_diagnosis(
        self,
        message: str,
        user_id: str,
        session_id: str,
        context_data: dict[str, Any],
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

        # Build system prompt for error diagnosis (inject user context)
        base_prompt = build_system_prompt(
            context_data.get("user_context") or {},
            conversation_history=context_data.get("conversation_context") or {},
            prompt_version=context_data.get("prompt_version") or "v1",
            plan_context=context_data.get("plan_context"),
        )
        system_prompt = f"""{base_prompt}

## 错题分析模式指令
目标：定位错误根因并形成可执行的改进闭环。
原则：
1. 先复述题意与用户思路，确保对齐
2. 明确错误类型与触发点（概念/计算/方法/审题/步骤遗漏）
3. 给出可操作的修正步骤与通用化方法
4. 提供防错清单与练习策略

输出要求（Markdown）：
- 题意与思路对齐
- 错误类型与触发点
- 根因分析
- 修正步骤（含正确解法/关键步骤）
- 防错清单与训练建议"""

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
            first_chunk = True
            async for chunk in self.llm_service.stream_chat(
                messages=messages,
                model=None,  # Use default model
                temperature=0.7,
            ):
                if chunk:
                    # 🔧 修复：在第一个chunk之前发送GENERATING状态（oneof要求分开发送）
                    if first_chunk:
                        yield agent_service_pb2.ChatResponse(
                            status_update=agent_service_pb2.AgentStatus(
                                state=agent_service_pb2.AgentStatus.GENERATING,
                                details="正在分析错题...",
                                active_agent=agent_service_pb2.ORCHESTRATOR,
                            ),
                        )
                        first_chunk = False

                    # 🔧 修复：只设置 delta，不设置 status_update（它们是 oneof，会互相覆盖）
                    yield agent_service_pb2.ChatResponse(delta=chunk)

            # 🔧 修复：发送流结束信号，清除前端状态
            yield agent_service_pb2.ChatResponse(
                finish_reason=agent_service_pb2.STOP,
            )
            logger.info(f"[ErrorDiagnosis] Sent finish_reason=STOP signal")

        except Exception as e:
            logger.error(f"[ErrorDiagnosis] LLM error: {e}")
            yield agent_service_pb2.ChatResponse(
                delta=f"\n\n⚠️ 错题分析服务暂时不可用: {str(e)}",
                finish_reason=agent_service_pb2.ERROR,
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
    context_data: dict[str, Any],
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
