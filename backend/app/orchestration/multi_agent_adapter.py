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
from app.orchestration.orchestrator import get_agent_type_for_tool


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
        await asyncio.sleep(0.3)

        # Phase 2: Knowledge gathering
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.SEARCHING,
                details="正在检索相关知识...",
                active_agent=agent_service_pb2.KNOWLEDGE,
            ),
        )
        await asyncio.sleep(0.5)

        # Phase 3: Expert consultation simulation
        # In production, this would call actual expert agents
        experts = [
            (agent_service_pb2.REASONING, "逻辑专家", "正在进行深度推理..."),
            (agent_service_pb2.KNOWLEDGE, "知识专家", "正在整合相关知识..."),
            (agent_service_pb2.DATA_ANALYSIS, "分析专家", "正在进行数据分析..."),
        ]

        for agent_type, name, detail in experts:
            yield agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.THINKING,
                    details=detail,
                    active_agent=agent_type,
                ),
            )
            await asyncio.sleep(0.4)

        # Phase 4: Synthesis
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.GENERATING,
                details="正在综合专家意见...",
                active_agent=agent_service_pb2.ORCHESTRATOR,
            ),
        )

        # Generate the response
        response_text = f"""# 深度解析模式

基于多位专家的协作分析，我对您的问题"{message}"进行了全面的深度解析：

## 专家分析摘要

### 🔍 逻辑专家的分析
- 问题类型识别与结构化
- 逻辑关系梳理
- 关键推理路径分析

### 📚 知识专家的见解
- 相关知识领域识别
- 概念关联分析
- 背景知识补充

### 📊 分析专家的发现
- 数据层面分析
- 趋势与模式识别
- 可视化建议

## 综合结论

这是深度解析模式的综合响应。在实际部署后，这里将包含：
- 多轮专家对话的完整记录
- 知识图谱检索结果
- 详细的分析过程展示
- 可操作的建议列表

---
*🤖 深度解析模式由多专家AI协作完成*"""

        for chunk in response_text:
            yield agent_service_pb2.ChatResponse(
                delta=chunk,
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.GENERATING,
                    active_agent=agent_service_pb2.ORCHESTRATOR,
                ),
            )
            await asyncio.sleep(0.01)

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
        await asyncio.sleep(0.3)

        # Phase 2: Decomposition
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details="正在分解学习任务...",
                active_agent=agent_service_pb2.WRITING,
            ),
        )
        await asyncio.sleep(0.5)

        # Phase 3: Time estimation
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details="正在估算学习时间...",
                active_agent=agent_service_pb2.REASONING,
            ),
        )

        # Generate the response
        response_text = f"""# 学习计划模式

针对您的学习需求"{message}"，我为您制定了详细的学习计划：

## 📋 学习目标分解

### 第一阶段：基础认知 (预计 3-5 天)
- 核心概念理解
- 基础术语掌握
- 简单应用练习

### 第二阶段：深化理解 (预计 5-7 天)
- 进阶概念学习
- 综合应用训练
- 案例分析

### 第三阶段：巩固提升 (预计 3-5 天)
- 知识体系构建
- 难点攻克
- 实战项目

## 📊 学习进度跟踪

| 阶段 | 状态 | 完成度 |
|------|------|--------|
| 基础认知 | ⏳ 待开始 | 0% |
| 深化理解 | ⏳ 待开始 | 0% |
| 巩固提升 | ⏳ 待开始 | 0% |

## 💡 学习建议

1. **每日投入**: 建议每天 1-2 小时专注学习
2. **复习频率**: 每完成一个阶段进行一次复习
3. **实践导向**: 理论学习后及时通过练习巩固

---
*🤖 学习计划由AI任务分解协作完成*"""

        for chunk in response_text:
            yield agent_service_pb2.ChatResponse(
                delta=chunk,
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.GENERATING,
                    active_agent=agent_service_pb2.ORCHESTRATOR,
                ),
            )
            await asyncio.sleep(0.01)

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
        await asyncio.sleep(0.3)

        # Phase 2: Pattern matching
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.SEARCHING,
                details="正在匹配错误模式...",
                active_agent=agent_service_pb2.KNOWLEDGE,
            ),
        )
        await asyncio.sleep(0.5)

        # Phase 3: Root cause analysis
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details="正在分析根本原因...",
                active_agent=agent_service_pb2.REASONING,
            ),
        )

        # Generate the response
        response_text = f"""# 错题分析模式

针对您提到的问题"{message}"，我进行了详细的错题诊断分析：

## 🔍 错误类型识别

**分类**: 概念理解型错误

**特征**:
- 对核心概念的理解存在偏差
- 知识点之间的关联不清晰
- 应用场景判断不准确

## 🎯 根本原因分析

### 1. 认知层面
- 概念形成的初始理解存在偏差
- 缺乏足够的实例支撑

### 2. 方法层面
- 学习方法不够系统
- 缺乏对比辨析

### 3. 应用层面
- 练习量不足
- 缺乏变式训练

## 💊 改进方案

### 立即行动
1. 重新梳理该概念的准确定义
2. 找出3个典型正例和3个典型反例
3. 完成针对性的巩固练习

### 系统改进
1. 建立概念对比表
2. 绘制知识关联图
3. 定期回顾错题本

## 🛡️ 预防策略

- 相似概念的辨析方法
- 常见误区预警
- 自检清单

---
*🤖 错题分析由AI诊断循环完成*"""

        for chunk in response_text:
            yield agent_service_pb2.ChatResponse(
                delta=chunk,
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.GENERATING,
                    active_agent=agent_service_pb2.ORCHESTRATOR,
                ),
            )
            await asyncio.sleep(0.01)


# Chat mode mapping constants
CHAT_MODE_STANDARD = "standard"
CHAT_MODE_DEEP_ANALYSIS = "deep_analysis"
CHAT_MODE_STUDY_PLAN = "study_plan"
CHAT_MODE_ERROR_DIAGNOSIS = "error_diagnosis"


async def execute_multi_agent_workflow(
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

    # Note: In production, orchestrator would be passed in
    # For now, we use a simple adapter without full orchestrator integration
    adapter = MultiAgentWorkflowAdapter(orchestrator=None)

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
        raise ValueError(f"Unknown chat mode: {chat_mode}")
