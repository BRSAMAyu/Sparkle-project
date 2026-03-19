"""
Collaboration Workflows - 多智能体协作工作流

实现三大协作模式：
1. TaskDecompositionWorkflow - 任务分解协作
2. ProgressiveExplorationWorkflow - 渐进式深度探索
3. ErrorDiagnosisWorkflow - 错题诊断循环
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger

from .base_agent import AgentResponse
from .enhanced_agents import EnhancedAgentContext, ProblemSolverAgent, StudyPlannerAgent
from .search_agent import SearchAgent
from .specialist_agents import CodeAgent, MathAgent, ScienceAgent, WritingAgent
from .workflow_experience import (
    HandoffPacket,
    build_collaboration_user_query,
    build_handoff_packet,
    format_handoff_packets,
    resolve_few_shot_examples,
    should_inject_few_shot,
)


# ==========================================
# 协作结果数据模型
# ==========================================
@dataclass
class CollaborationResult:
    """多智能体协作结果"""
    workflow_type: str  # 工作流类型
    participants: list[str]  # 参与的智能体名称
    outputs: list[AgentResponse]  # 各智能体的输出
    final_response: str  # 整合后的最终响应
    reasoning: str  # 整体推理过程
    metadata: dict[str, Any]  # 额外元数据
    timeline: list[dict[str, Any]]  # 执行时间线（用于可视化）
    confidence: float = 0.9


def _build_timeline_step(
    agent_name: str,
    action: str,
    start_time: datetime,
    *,
    status: str = "completed",
    output_summary: str | None = None,
    agent_role: str | None = None,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    """Normalize timeline steps to a consistent schema."""
    now = datetime.now()
    elapsed_ms = int((now - start_time).total_seconds() * 1000)
    step = {
        "agent_name": agent_name,
        "action": action,
        "status": status,
        "start_time_ms": int(start_time.timestamp() * 1000),
    }
    if agent_role:
        step["agent_role"] = agent_role
    step["duration_ms"] = duration_ms if duration_ms is not None else elapsed_ms
    if output_summary:
        step["output_summary"] = output_summary
    return step


def _copy_context(
    context: EnhancedAgentContext,
    *,
    user_query: str,
    previous_agent_outputs: list[dict[str, Any]] | None = None,
) -> EnhancedAgentContext:
    return EnhancedAgentContext(
        **{
            **context.__dict__,
            "user_query": user_query,
            "previous_agent_outputs": previous_agent_outputs,
        }
    )


async def _resolve_examples_for_agent(
    context: EnhancedAgentContext,
    *,
    workflow_type: str,
    chat_mode: str,
    agent_role: str,
    stage: str,
) -> list[dict[str, Any]]:
    if not should_inject_few_shot(
        workflow_type=workflow_type,
        stage=stage,
        agent_role=agent_role,
    ):
        return []
    return await resolve_few_shot_examples(
        db_session=context.db_session,
        user_id=context.user_id,
        workflow_type=workflow_type,
        chat_mode=chat_mode,
        agent_role=agent_role,
        stage=stage,
        count=1,
    )


def _build_query(
    *,
    base_query: str,
    workflow_type: str,
    handoff_packets: list[HandoffPacket | dict[str, Any]] | None = None,
    few_shot_examples: list[dict[str, Any]] | None = None,
    extra_instruction: str | None = None,
) -> str:
    return build_collaboration_user_query(
        base_query=base_query,
        workflow_type=workflow_type,
        handoff_packets=handoff_packets,
        few_shot_examples=few_shot_examples,
        extra_instruction=extra_instruction,
    )


# ==========================================
# 工作流 1: 任务分解协作
# ==========================================
class TaskDecompositionWorkflow:
    """
    任务分解协作工作流

    适用场景：
    - "帮我准备下周的机器学习考试"
    - "制定这学期的数学学习计划"
    - "我要在一个月内学会 Python"

    流程：
    1. StudyPlannerAgent 分析整体情况，制定宏观计划
    2. 根据计划，并行调用多个专业 Agent 生成具体内容
    3. 整合所有输出，生成完整的学习计划和任务卡片
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    async def execute(
        self,
        query: str,
        context: EnhancedAgentContext
    , tool_call_id: str | None = None) -> CollaborationResult:
        """
        执行任务分解协作

        Args:
            query: 用户查询（如 "帮我准备期末考试"）
            context: 增强上下文（包含知识星图、遗忘曲线等）

        Returns:
            CollaborationResult: 协作结果
        """
        logger.info(f"[TaskDecomposition] Starting workflow for: {query[:50]}...")
        timeline = []
        start_time = datetime.now()
        handoff_packets: list[dict[str, Any]] = []

        # Step 0: SearchAgent 检索相关背景
        logger.info("[TaskDecomposition] Step 0: Retrieving background knowledge...")
        search_agent = SearchAgent()
        search_response = await search_agent.process(context)
        timeline.append(
            _build_timeline_step(
                "SearchExpert",
                "检索背景知识",
                start_time,
                output_summary=search_response.response_text[:100] + "...",
            )
        )
        search_packet = await build_handoff_packet(
            agent="SearchExpert",
            response_text=search_response.response_text,
            workflow_type="task_decomposition",
            reasoning=search_response.reasoning,
        )
        handoff_packets.append(search_packet.to_dict())

        # Step 1: StudyPlannerAgent 分析整体情况
        logger.info("[TaskDecomposition] Step 1: Analyzing with StudyPlanner...")
        planner = StudyPlannerAgent()
        planner_examples = await _resolve_examples_for_agent(
            context,
            workflow_type="task_decomposition",
            chat_mode="study_plan",
            agent_role="study_planner",
            stage="collaboration",
        )
        planner_context = _copy_context(
            context,
            user_query=_build_query(
                base_query=query,
                workflow_type="task_decomposition",
                handoff_packets=handoff_packets,
                few_shot_examples=planner_examples,
                extra_instruction="请先给总体计划，再拆出依赖顺序、每日动作和未决条件。",
            ),
            previous_agent_outputs=handoff_packets,
        )
        planner_response = await planner.process(planner_context)
        timeline.append(
            _build_timeline_step(
                "StudyPlanner",
                "分析学习状态，制定整体计划",
                start_time,
                output_summary=planner_response.response_text[:100] + "...",
            )
        )
        planner_packet = await build_handoff_packet(
            agent="StudyPlanner",
            response_text=planner_response.response_text,
            workflow_type="task_decomposition",
            reasoning=planner_response.reasoning,
        )
        handoff_packets.append(planner_packet.to_dict())

        # Step 2: 提取关键信息
        plan_metadata = planner_response.metadata or {}
        learning_status = plan_metadata.get("learning_status", {})
        weak_points = learning_status.get("weak_points", [])
        forgetting_risks = learning_status.get("forgetting_risks", [])

        # Step 3: 并行调用专业 Agent
        logger.info("[TaskDecomposition] Step 2: Delegating to specialist agents...")
        parallel_tasks = []

        # 为不同领域生成专项内容
        # 假设知识点分类到不同领域
        subject_distribution = self._categorize_concepts(weak_points + forgetting_risks)

        outputs = [search_response, planner_response]

        # 数学领域
        if subject_distribution.get("math"):
            math_context = EnhancedAgentContext(
                **{**context.__dict__,
                   "user_query": _build_query(
                       base_query=f"为以下数学知识点生成练习题：{', '.join(subject_distribution['math'][:3])}",
                       workflow_type="task_decomposition",
                       handoff_packets=[planner_packet.to_dict()],
                       extra_instruction="直接产出专项训练建议，不要复述整份计划。",
                   ),
                   "previous_agent_outputs": [planner_packet.to_dict()]}
            )
            parallel_tasks.append(("MathExpert", MathAgent().process(math_context)))

        # 编程领域
        if subject_distribution.get("code"):
            code_context = EnhancedAgentContext(
                **{**context.__dict__,
                   "user_query": _build_query(
                       base_query=f"为以下编程概念设计实战项目：{', '.join(subject_distribution['code'][:3])}",
                       workflow_type="task_decomposition",
                       handoff_packets=[planner_packet.to_dict()],
                       extra_instruction="聚焦实战项目和训练动作，不重复宏观计划。",
                   ),
                   "previous_agent_outputs": [planner_packet.to_dict()]}
            )
            parallel_tasks.append(("CodeExpert", CodeAgent().process(code_context)))

        # 写作领域（生成学习笔记模板）
        if weak_points or forgetting_risks:
            writing_context = EnhancedAgentContext(
                **{**context.__dict__,
                   "user_query": _build_query(
                       base_query=f"为以下知识点创建学习笔记模板：{', '.join((weak_points + forgetting_risks)[:5])}",
                       workflow_type="task_decomposition",
                       handoff_packets=[planner_packet.to_dict()],
                       extra_instruction="输出适合执行的学习笔记模板，不重复整份计划。",
                   ),
                   "previous_agent_outputs": [planner_packet.to_dict()]}
            )
            parallel_tasks.append(("WritingExpert", WritingAgent().process(writing_context)))

        # 并行执行
        if parallel_tasks:
            results = await asyncio.gather(*[task for _, task in parallel_tasks], return_exceptions=True)

            for _i, (agent_name, result) in enumerate(zip([name for name, _ in parallel_tasks], results, strict=False)):
                if isinstance(result, Exception):
                    logger.error(f"[TaskDecomposition] {agent_name} failed: {result}")
                    continue

                outputs.append(result)
                packet = await build_handoff_packet(
                    agent=agent_name,
                    response_text=result.response_text,
                    workflow_type="task_decomposition",
                    reasoning=result.reasoning,
                )
                handoff_packets.append(packet.to_dict())
                timeline.append(
                    _build_timeline_step(
                        agent_name,
                        "生成专项内容",
                        start_time,
                        output_summary=result.response_text[:100] + "...",
                    )
                )

        # Step 4: 整合生成完整计划
        logger.info("[TaskDecomposition] Step 3: Synthesizing final plan...")
        final_response = await self._integrate_plan(planner_response, outputs, context, handoff_packets=handoff_packets)

        timeline.append(
            _build_timeline_step(
                "Orchestrator",
                "整合所有专家意见，生成最终计划",
                start_time,
                output_summary="完成计划整合",
            )
        )

        return CollaborationResult(
            workflow_type="task_decomposition",
            participants=[agent for agent, _ in parallel_tasks] + ["StudyPlanner", "Orchestrator"],
            outputs=outputs,
            final_response=final_response,
            reasoning=f"任务分解协作：由 StudyPlanner 制定宏观计划，" \
                     f"{len(parallel_tasks)} 个专业 Agent 协作生成具体内容",
            metadata={
                "weak_points": weak_points,
                "forgetting_risks": forgetting_risks,
                "total_tasks_generated": len(plan_metadata.get("tool_calls", [])),
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "handoff_packets": handoff_packets,
            },
            timeline=timeline,
            confidence=0.88
        )

    def _categorize_concepts(self, concepts: list[str]) -> dict[str, list[str]]:
        """将知识点分类到不同领域"""
        categorization = {
            "math": [],
            "code": [],
            "writing": [],
            "science": []
        }

        for concept in concepts:
            concept_lower = concept.lower()
            if any(kw in concept_lower for kw in ["高数", "线代", "概率", "数学", "积分", "导数", "矩阵"]):
                categorization["math"].append(concept)
            elif any(kw in concept_lower for kw in ["python", "java", "算法", "编程", "代码", "数据结构"]):
                categorization["code"].append(concept)
            elif any(kw in concept_lower for kw in ["写作", "语法", "作文"]):
                categorization["writing"].append(concept)
            else:
                categorization["science"].append(concept)

        return {k: v for k, v in categorization.items() if v}

    async def _integrate_plan(
        self,
        planner_response: AgentResponse,
        all_outputs: list[AgentResponse],
        context: EnhancedAgentContext,
        handoff_packets: list[dict[str, Any]] | None = None,
    ) -> str:
        """整合所有专家输出，生成统一的学习计划"""

        integrated = f"""# 📚 个性化学习计划

{planner_response.response_text}

---

## 📊 多专家协作建议

"""

        if handoff_packets:
            integrated += f"{format_handoff_packets(handoff_packets, title='协作摘要总览')}\n\n---\n"

        # 添加其他专家的建议
        for output in all_outputs[1:]:  # 跳过 planner 本身
            integrated += f"\n### {output.agent_name}\n\n{output.response_text}\n\n---\n"

        # 添加任务生成提示
        tool_calls = planner_response.metadata.get("tool_calls", [])
        if tool_calls:
            integrated += f"\n## ✅ 已为你生成 {len(tool_calls)} 个学习任务\n\n"
            integrated += "这些任务已添加到你的任务列表中，可以在任务页面查看和开始学习。\n"

        return integrated


# ==========================================
# 工作流 2: 渐进式深度探索
# ==========================================
class ProgressiveExplorationWorkflow:
    """
    渐进式深度探索工作流

    适用场景：
    - "解释神经网络的反向传播"
    - "深入讲解量子力学的波粒二象性"
    - "详细说明 React Hooks 的工作原理"

    流程：
    1. Round 1: MathAgent 进行数学推导
    2. Round 2: CodeAgent 提供代码实现
    3. Round 3: ScienceAgent 给出物理/生物类比
    4. Round 4: WritingAgent 生成学习笔记
    5. Round 5: StudyPlannerAgent 安排复习时间

    每一轮的输出会传递给下一轮作为上下文
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    async def execute(
        self,
        query: str,
        context: EnhancedAgentContext
    , tool_call_id: str | None = None) -> CollaborationResult:
        """
        执行渐进式深度探索

        Args:
            query: 用户查询（如 "解释神经网络反向传播"）
            context: 增强上下文

        Returns:
            CollaborationResult: 协作结果
        """
        logger.info(f"[ProgressiveExploration] Starting workflow for: {query[:50]}...")
        timeline = []
        conversation_history = []
        start_time = datetime.now()
        outputs = []
        handoff_packets: list[dict[str, Any]] = []

        # Round 0: SearchAgent - 知识检索
        logger.info("[ProgressiveExploration] Round 0: Knowledge retrieval...")
        search_agent = SearchAgent()
        search_response = await search_agent.process(context)
        outputs.append(search_response)
        conversation_history.append({
            "agent": "SearchExpert",
            "content": search_response.response_text,
            "reasoning": search_response.reasoning
        })
        timeline.append(
            _build_timeline_step(
                "SearchExpert",
                "检索知识证据",
                start_time,
                output_summary=search_response.response_text[:100] + "...",
            )
        )
        search_packet = await build_handoff_packet(
            agent="SearchExpert",
            response_text=search_response.response_text,
            workflow_type="progressive_exploration",
            reasoning=search_response.reasoning,
        )
        handoff_packets.append(search_packet.to_dict())

        # Round 1: MathAgent - 数学推导
        logger.info("[ProgressiveExploration] Round 1: Math analysis...")
        math_agent = MathAgent()
        math_examples = await _resolve_examples_for_agent(
            context,
            workflow_type="progressive_exploration",
            chat_mode="deep_analysis",
            agent_role="math",
            stage="collaboration",
        )
        math_context = _copy_context(
            context,
            user_query=_build_query(
                base_query=query,
                workflow_type="progressive_exploration",
                handoff_packets=handoff_packets,
                few_shot_examples=math_examples,
                extra_instruction="请优先完成原理推导，避免直接跳到结论。",
            ),
            previous_agent_outputs=handoff_packets,
        )
        math_response = await math_agent.process(math_context)
        outputs.append(math_response)
        conversation_history.append({
            "agent": "MathExpert",
            "content": math_response.response_text,
            "reasoning": math_response.reasoning
        })
        timeline.append(
            _build_timeline_step(
                "MathExpert",
                "数学原理推导",
                start_time,
                output_summary=math_response.response_text[:100] + "...",
            )
        )
        math_packet = await build_handoff_packet(
            agent="MathExpert",
            response_text=math_response.response_text,
            workflow_type="progressive_exploration",
            reasoning=math_response.reasoning,
        )
        handoff_packets.append(math_packet.to_dict())

        # Round 2: CodeAgent - 代码实现
        logger.info("[ProgressiveExploration] Round 2: Code implementation...")
        code_context = EnhancedAgentContext(
            **{**context.__dict__,
               "previous_agent_outputs": [math_packet.to_dict()],
               "user_query": _build_query(
                   base_query=f"基于上述数学推导，提供代码实现：{query}",
                   workflow_type="progressive_exploration",
                   handoff_packets=[math_packet.to_dict()],
                   extra_instruction="请只补充代码化视角，不要复述整段推导。",
               )}
        )
        code_agent = CodeAgent()
        code_response = await code_agent.process(code_context)
        outputs.append(code_response)
        conversation_history.append({
            "agent": "CodeExpert",
            "content": code_response.response_text,
            "reasoning": code_response.reasoning
        })
        timeline.append(
            _build_timeline_step(
                "CodeExpert",
                "代码实现",
                start_time,
                output_summary=code_response.response_text[:100] + "...",
            )
        )
        code_packet = await build_handoff_packet(
            agent="CodeExpert",
            response_text=code_response.response_text,
            workflow_type="progressive_exploration",
            reasoning=code_response.reasoning,
        )
        handoff_packets.append(code_packet.to_dict())

        # Round 3: ScienceAgent - 生物/物理类比（如果适用）
        if self._needs_scientific_analogy(query):
            logger.info("[ProgressiveExploration] Round 3: Scientific analogy...")
            science_examples = await _resolve_examples_for_agent(
                context,
                workflow_type="progressive_exploration",
                chat_mode="deep_analysis",
                agent_role="science",
                stage="collaboration",
            )
            science_context = EnhancedAgentContext(
                **{**context.__dict__,
                   "previous_agent_outputs": [math_packet.to_dict(), code_packet.to_dict()],
                   "user_query": _build_query(
                       base_query=f"用生物学或物理学概念类比解释：{query}",
                       workflow_type="progressive_exploration",
                       handoff_packets=[math_packet.to_dict(), code_packet.to_dict()],
                       few_shot_examples=science_examples,
                       extra_instruction="类比只能帮助理解，必须指出类比边界。",
                   )}
            )
            science_agent = ScienceAgent()
            science_response = await science_agent.process(science_context)
            outputs.append(science_response)
            conversation_history.append({
                "agent": "ScienceExpert",
                "content": science_response.response_text,
                "reasoning": science_response.reasoning
            })
            timeline.append(
                _build_timeline_step(
                    "ScienceExpert",
                    "科学类比",
                    start_time,
                    output_summary=science_response.response_text[:100] + "...",
                )
            )
            science_packet = await build_handoff_packet(
                agent="ScienceExpert",
                response_text=science_response.response_text,
                workflow_type="progressive_exploration",
                reasoning=science_response.reasoning,
            )
            handoff_packets.append(science_packet.to_dict())

        # Round 4: WritingAgent - 学习笔记
        logger.info("[ProgressiveExploration] Round 4: Study notes generation...")
        writing_examples = await _resolve_examples_for_agent(
            context,
            workflow_type="progressive_exploration",
            chat_mode="deep_analysis",
            agent_role="writing",
            stage="collaboration",
        )
        writing_context = EnhancedAgentContext(
            **{**context.__dict__,
               "previous_agent_outputs": handoff_packets,
               "user_query": _build_query(
                   base_query=f"基于以上多角度解释，生成学习笔记和记忆技巧：{query}",
                   workflow_type="progressive_exploration",
                   handoff_packets=handoff_packets,
                   few_shot_examples=writing_examples,
                   extra_instruction="请压缩重复内容，按概念-例子-记忆钩子组织笔记。",
               )}
        )
        writing_agent = WritingAgent()
        writing_response = await writing_agent.process(writing_context)
        outputs.append(writing_response)
        timeline.append(
            _build_timeline_step(
                "WritingExpert",
                "生成学习笔记",
                start_time,
                output_summary=writing_response.response_text[:100] + "...",
            )
        )
        writing_packet = await build_handoff_packet(
            agent="WritingExpert",
            response_text=writing_response.response_text,
            workflow_type="progressive_exploration",
            reasoning=writing_response.reasoning,
        )
        handoff_packets.append(writing_packet.to_dict())

        # Round 5: StudyPlannerAgent - 复习安排
        logger.info("[ProgressiveExploration] Round 5: Review scheduling...")
        planner_context = EnhancedAgentContext(
            **{**context.__dict__,
               "previous_agent_outputs": [writing_packet.to_dict()],
               "user_query": _build_query(
                   base_query=f"为这个知识点安排复习计划：{query}",
                   workflow_type="progressive_exploration",
                   handoff_packets=[writing_packet.to_dict()],
                   extra_instruction="复习安排只保留关键节奏和复盘节点即可。",
               )}
        )
        planner = StudyPlannerAgent()
        planner_response = await planner.process(planner_context)
        outputs.append(planner_response)
        timeline.append(
            _build_timeline_step(
                "StudyPlanner",
                "安排复习计划",
                start_time,
                output_summary=planner_response.response_text[:100] + "...",
            )
        )

        # 整合响应
        final_response = self._format_exploration_summary(conversation_history, planner_response)

        return CollaborationResult(
            workflow_type="progressive_exploration",
            participants=[item["agent"] for item in conversation_history] + ["StudyPlanner"],
            outputs=outputs,
            final_response=final_response,
            reasoning=f"渐进式深度探索：从数学原理 → 代码实现 → 科学类比 → 学习笔记 → 复习计划，" \
                     f"共 {len(outputs)} 个维度的深度解析",
            metadata={
                "exploration_depth": len(outputs),
                "perspectives": len(conversation_history),
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "handoff_packets": handoff_packets,
            },
            timeline=timeline,
            confidence=0.92
        )

    def _needs_scientific_analogy(self, query: str) -> bool:
        """判断是否需要科学类比"""
        keywords = ["神经网络", "机器学习", "深度学习", "算法", "梯度", "优化"]
        return any(kw in query for kw in keywords)

    def _format_exploration_summary(
        self,
        conversation_history: list[dict],
        planner_response: AgentResponse
    ) -> str:
        """格式化探索总结"""

        summary = "# 🔬 深度知识探索\n\n"
        summary += "我们的专家团队从多个维度为你深入解析这个概念：\n\n"

        for i, item in enumerate(conversation_history, 1):
            summary += f"## {i}. {item['agent']} 的视角\n\n"
            summary += f"{item['content']}\n\n---\n\n"

        summary += f"## {len(conversation_history) + 1}. 复习计划\n\n"
        summary += f"{planner_response.response_text}\n\n"

        summary += "\n💡 **学习建议**：建议你按照上述顺序逐步理解，从数学原理到实际应用，形成完整的知识体系。\n"

        return summary


# ==========================================
# 工作流 3: 错题诊断循环
# ==========================================
class ErrorDiagnosisWorkflow:
    """
    错题诊断循环工作流

    适用场景：
    - 用户提交做错的题目
    - "我不明白为什么这道题这样做"
    - "这个概念我总是搞混"

    流程：
    1. ProblemSolverAgent 分析错误模式
    2. 查询知识星图，识别薄弱知识点
    3. StudyPlannerAgent 安排针对性复习
    4. 生成类似练习题（MathAgent/CodeAgent）
    5. 创建错题复习任务
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    async def execute(
        self,
        query: str,
        context: EnhancedAgentContext
    , tool_call_id: str | None = None) -> CollaborationResult:
        """
        执行错题诊断

        Args:
            query: 用户查询（包含错题内容）
            context: 增强上下文

        Returns:
            CollaborationResult: 协作结果
        """
        logger.info(f"[ErrorDiagnosis] Starting workflow for: {query[:50]}...")
        timeline = []
        start_time = datetime.now()
        outputs = []
        handoff_packets: list[dict[str, Any]] = []

        # Step 1: ProblemSolverAgent 分析错误模式
        logger.info("[ErrorDiagnosis] Step 1: Analyzing error pattern...")
        solver = ProblemSolverAgent()
        solver_examples = await _resolve_examples_for_agent(
            context,
            workflow_type="error_diagnosis",
            chat_mode="error_diagnosis",
            agent_role="problem_solver",
            stage="collaboration",
        )
        solver_context = EnhancedAgentContext(
            **{**context.__dict__,
               "user_query": _build_query(
                   base_query=f"分析这道题的错误模式和知识点缺陷：{query}",
                   workflow_type="error_diagnosis",
                   few_shot_examples=solver_examples,
                   extra_instruction="请先区分错误症状与根因，再给修复动作。",
               )}
        )
        solver_response = await solver.process(solver_context)
        outputs.append(solver_response)
        timeline.append(
            _build_timeline_step(
                "ProblemSolver",
                "分析错误原因",
                start_time,
                output_summary=solver_response.response_text[:100] + "...",
            )
        )
        solver_packet = await build_handoff_packet(
            agent="ProblemSolver",
            response_text=solver_response.response_text,
            workflow_type="error_diagnosis",
            reasoning=solver_response.reasoning,
        )
        handoff_packets.append(solver_packet.to_dict())

        # Step 1.5: SearchAgent 补充检索证据
        logger.info("[ErrorDiagnosis] Step 1.5: Retrieving supporting knowledge...")
        search_agent = SearchAgent()
        search_response = await search_agent.process(context)
        outputs.append(search_response)
        timeline.append(
            _build_timeline_step(
                "SearchExpert",
                "检索支撑知识",
                start_time,
                output_summary=search_response.response_text[:100] + "...",
            )
        )
        search_packet = await build_handoff_packet(
            agent="SearchExpert",
            response_text=search_response.response_text,
            workflow_type="error_diagnosis",
            reasoning=search_response.reasoning,
        )
        handoff_packets.append(search_packet.to_dict())

        # Step 2: 识别薄弱知识点（从 metadata 中提取）
        solver_metadata = solver_response.metadata or {}
        problem_analysis = solver_metadata.get("problem_analysis", {})
        weak_points = problem_analysis.get("related_concepts", [])

        logger.info(f"[ErrorDiagnosis] Identified weak points: {weak_points}")

        # Step 3: StudyPlannerAgent 安排针对性复习
        logger.info("[ErrorDiagnosis] Step 2: Planning targeted review...")
        planner = StudyPlannerAgent()
        planner_context = EnhancedAgentContext(
            **{**context.__dict__,
               "previous_agent_outputs": handoff_packets,
               "user_query": _build_query(
                   base_query=f"为薄弱知识点安排针对性复习：{', '.join(weak_points)}",
                   workflow_type="error_diagnosis",
                   handoff_packets=handoff_packets,
                   extra_instruction="只输出针对性复习动作，不要重复完整错因分析。",
               )}
        )
        planner_response = await planner.process(planner_context)
        outputs.append(planner_response)
        timeline.append(
            _build_timeline_step(
                "StudyPlanner",
                "制定复习计划",
                start_time,
                output_summary=planner_response.response_text[:100] + "...",
            )
        )
        planner_packet = await build_handoff_packet(
            agent="StudyPlanner",
            response_text=planner_response.response_text,
            workflow_type="error_diagnosis",
            reasoning=planner_response.reasoning,
        )
        handoff_packets.append(planner_packet.to_dict())

        # Step 4: 生成类似练习题
        logger.info("[ErrorDiagnosis] Step 3: Generating practice problems...")
        # 判断领域
        is_math = any(kw in query.lower() for kw in ["数学", "计算", "求解", "方程", "积分", "导数"])
        is_code = any(kw in query.lower() for kw in ["代码", "编程", "函数", "算法", "python", "java"])

        practice_response = None
        if is_math:
            math_agent = MathAgent()
            practice_context = EnhancedAgentContext(
                **{**context.__dict__,
                   "previous_agent_outputs": [solver_packet.to_dict(), planner_packet.to_dict()],
                   "user_query": _build_query(
                       base_query=f"生成5道类似的练习题（难度递进）：{', '.join(weak_points)}",
                       workflow_type="error_diagnosis",
                       handoff_packets=[solver_packet.to_dict(), planner_packet.to_dict()],
                       extra_instruction="练习题必须围绕已识别的根因递进展开。",
                   )}
            )
            practice_response = await math_agent.process(practice_context)
        elif is_code:
            code_agent = CodeAgent()
            practice_context = EnhancedAgentContext(
                **{**context.__dict__,
                   "previous_agent_outputs": [solver_packet.to_dict(), planner_packet.to_dict()],
                   "user_query": _build_query(
                       base_query=f"生成3个编程练习题（涉及知识点：{', '.join(weak_points)}）",
                       workflow_type="error_diagnosis",
                       handoff_packets=[solver_packet.to_dict(), planner_packet.to_dict()],
                       extra_instruction="练习题要针对根因设计，不要泛泛给题。",
                   )}
            )
            practice_response = await code_agent.process(practice_context)

        if practice_response:
            outputs.append(practice_response)
            timeline.append(
                _build_timeline_step(
                    "PracticeGenerator",
                    "生成练习题",
                    start_time,
                    output_summary=practice_response.response_text[:100] + "...",
                )
            )
            practice_packet = await build_handoff_packet(
                agent="PracticeGenerator",
                response_text=practice_response.response_text,
                workflow_type="error_diagnosis",
                reasoning=practice_response.reasoning,
            )
            handoff_packets.append(practice_packet.to_dict())

        # 整合诊断报告
        final_response = self._format_diagnosis_report(
            solver_response,
            planner_response,
            practice_response,
            weak_points
        )

        return CollaborationResult(
            workflow_type="error_diagnosis",
            participants=["ProblemSolver", "StudyPlanner", "PracticeGenerator"],
            outputs=outputs,
            final_response=final_response,
            reasoning=f"错题诊断循环：分析错误模式 → 识别薄弱点（{len(weak_points)}个）→ 制定复习计划 → 生成练习题",
            metadata={
                "error_pattern": problem_analysis.get("problem_type", "unknown"),
                "weak_points": weak_points,
                "practice_generated": practice_response is not None,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "handoff_packets": handoff_packets,
            },
            timeline=timeline,
            confidence=0.90
        )

    def _format_diagnosis_report(
        self,
        solver_response: AgentResponse,
        planner_response: AgentResponse,
        practice_response: AgentResponse | None,
        weak_points: list[str]
    ) -> str:
        """格式化错题诊断报告"""

        report = "# 🔍 错题诊断报告\n\n"

        report += "## 1. 错误分析\n\n"
        report += f"{solver_response.response_text}\n\n---\n\n"

        report += "## 2. 薄弱知识点\n\n"
        if weak_points:
            report += "识别出以下知识点需要加强：\n\n"
            for i, point in enumerate(weak_points, 1):
                report += f"{i}. {point}\n"
            report += "\n---\n\n"

        report += "## 3. 针对性复习计划\n\n"
        report += f"{planner_response.response_text}\n\n---\n\n"

        if practice_response:
            report += "## 4. 举一反三练习\n\n"
            report += f"{practice_response.response_text}\n\n---\n\n"

        report += "\n💡 **学习建议**：建议先复习相关知识点，再完成练习题，最后总结错误模式。\n"

        return report
