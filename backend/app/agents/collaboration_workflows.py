"""
Collaboration Workflows - 多智能体协作工作流

实现三大协作模式：
1. TaskDecompositionWorkflow - 任务分解协作
2. ProgressiveExplorationWorkflow - 渐进式深度探索
3. ErrorDiagnosisWorkflow - 错题诊断循环
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from .base_agent import AgentResponse
from .enhanced_agents import EnhancedAgentContext, StudyPlannerAgent, ProblemSolverAgent
from .specialist_agents import MathAgent, CodeAgent, WritingAgent, ScienceAgent


# ==========================================
# 协作结果数据模型
# ==========================================
@dataclass
class CollaborationResult:
    """多智能体协作结果"""
    workflow_type: str  # 工作流类型
    participants: List[str]  # 参与的智能体名称
    outputs: List[AgentResponse]  # 各智能体的输出
    final_response: str  # 整合后的最终响应
    reasoning: str  # 整体推理过程
    metadata: Dict[str, Any]  # 额外元数据
    timeline: List[Dict[str, Any]]  # 执行时间线（用于可视化）
    confidence: float = 0.9


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
    , tool_call_id: Optional[str] = None) -> CollaborationResult:
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

        # Step 1: StudyPlannerAgent 分析整体情况
        logger.info("[TaskDecomposition] Step 1: Analyzing with StudyPlanner...")
        planner = StudyPlannerAgent()

        planner_response = await planner.process(context)
        timeline.append({
            "agent": "StudyPlanner",
            "action": "分析学习状态，制定整体计划",
            "timestamp": (datetime.now() - start_time).total_seconds(),
            "output_summary": planner_response.response_text[:100] + "..."
        })

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

        outputs = [planner_response]

        # 数学领域
        if subject_distribution.get("math"):
            math_context = EnhancedAgentContext(
                **{**context.__dict__,
                   "user_query": f"为以下数学知识点生成练习题：{', '.join(subject_distribution['math'][:3])}"}
            )
            parallel_tasks.append(("MathExpert", MathAgent().process(math_context)))

        # 编程领域
        if subject_distribution.get("code"):
            code_context = EnhancedAgentContext(
                **{**context.__dict__,
                   "user_query": f"为以下编程概念设计实战项目：{', '.join(subject_distribution['code'][:3])}"}
            )
            parallel_tasks.append(("CodeExpert", CodeAgent().process(code_context)))

        # 写作领域（生成学习笔记模板）
        if weak_points or forgetting_risks:
            writing_context = EnhancedAgentContext(
                **{**context.__dict__,
                   "user_query": f"为以下知识点创建学习笔记模板：{', '.join((weak_points + forgetting_risks)[:5])}"}
            )
            parallel_tasks.append(("WritingExpert", WritingAgent().process(writing_context)))

        # 并行执行
        if parallel_tasks:
            results = await asyncio.gather(*[task for _, task in parallel_tasks], return_exceptions=True)

            for i, (agent_name, result) in enumerate(zip([name for name, _ in parallel_tasks], results)):
                if isinstance(result, Exception):
                    logger.error(f"[TaskDecomposition] {agent_name} failed: {result}")
                    continue

                outputs.append(result)
                timeline.append({
                    "agent": agent_name,
                    "action": "生成专项内容",
                    "timestamp": (datetime.now() - start_time).total_seconds(),
                    "output_summary": result.response_text[:100] + "..."
                })

        # Step 4: 整合生成完整计划
        logger.info("[TaskDecomposition] Step 3: Synthesizing final plan...")
        final_response = await self._integrate_plan(planner_response, outputs, context)

        timeline.append({
            "agent": "Orchestrator",
            "action": "整合所有专家意见，生成最终计划",
            "timestamp": (datetime.now() - start_time).total_seconds(),
            "output_summary": "完成计划整合"
        })

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
                "execution_time": (datetime.now() - start_time).total_seconds()
            },
            timeline=timeline,
            confidence=0.88
        )

    def _categorize_concepts(self, concepts: List[str]) -> Dict[str, List[str]]:
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
        all_outputs: List[AgentResponse],
        context: EnhancedAgentContext
    ) -> str:
        """整合所有专家输出，生成统一的学习计划"""

        integrated = f"""# 📚 个性化学习计划

{planner_response.response_text}

---

## 📊 多专家协作建议

"""

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
    , tool_call_id: Optional[str] = None) -> CollaborationResult:
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

        # Round 1: MathAgent - 数学推导
        logger.info("[ProgressiveExploration] Round 1: Math analysis...")
        math_agent = MathAgent()
        math_response = await math_agent.process(context)
        outputs.append(math_response)
        conversation_history.append({
            "agent": "MathExpert",
            "content": math_response.response_text,
            "reasoning": math_response.reasoning
        })
        timeline.append({
            "agent": "MathExpert",
            "action": "数学原理推导",
            "timestamp": (datetime.now() - start_time).total_seconds(),
            "output_summary": math_response.response_text[:100] + "..."
        })

        # Round 2: CodeAgent - 代码实现
        logger.info("[ProgressiveExploration] Round 2: Code implementation...")
        code_context = EnhancedAgentContext(
            **{**context.__dict__,
               "previous_agent_outputs": [math_response],
               "user_query": f"基于上述数学推导，提供代码实现：{query}"}
        )
        code_agent = CodeAgent()
        code_response = await code_agent.process(code_context)
        outputs.append(code_response)
        conversation_history.append({
            "agent": "CodeExpert",
            "content": code_response.response_text,
            "reasoning": code_response.reasoning
        })
        timeline.append({
            "agent": "CodeExpert",
            "action": "代码实现",
            "timestamp": (datetime.now() - start_time).total_seconds(),
            "output_summary": code_response.response_text[:100] + "..."
        })

        # Round 3: ScienceAgent - 生物/物理类比（如果适用）
        if self._needs_scientific_analogy(query):
            logger.info("[ProgressiveExploration] Round 3: Scientific analogy...")
            science_context = EnhancedAgentContext(
                **{**context.__dict__,
                   "previous_agent_outputs": [math_response, code_response],
                   "user_query": f"用生物学或物理学概念类比解释：{query}"}
            )
            science_agent = ScienceAgent()
            science_response = await science_agent.process(science_context)
            outputs.append(science_response)
            conversation_history.append({
                "agent": "ScienceExpert",
                "content": science_response.response_text,
                "reasoning": science_response.reasoning
            })
            timeline.append({
                "agent": "ScienceExpert",
                "action": "科学类比",
                "timestamp": (datetime.now() - start_time).total_seconds(),
                "output_summary": science_response.response_text[:100] + "..."
            })

        # Round 4: WritingAgent - 学习笔记
        logger.info("[ProgressiveExploration] Round 4: Study notes generation...")
        writing_context = EnhancedAgentContext(
            **{**context.__dict__,
               "previous_agent_outputs": outputs,
               "user_query": f"基于以上多角度解释，生成学习笔记和记忆技巧：{query}"}
        )
        writing_agent = WritingAgent()
        writing_response = await writing_agent.process(writing_context)
        outputs.append(writing_response)
        timeline.append({
            "agent": "WritingExpert",
            "action": "生成学习笔记",
            "timestamp": (datetime.now() - start_time).total_seconds(),
            "output_summary": writing_response.response_text[:100] + "..."
        })

        # Round 5: StudyPlannerAgent - 复习安排
        logger.info("[ProgressiveExploration] Round 5: Review scheduling...")
        planner_context = EnhancedAgentContext(
            **{**context.__dict__,
               "user_query": f"为这个知识点安排复习计划：{query}"}
        )
        planner = StudyPlannerAgent()
        planner_response = await planner.process(planner_context)
        outputs.append(planner_response)
        timeline.append({
            "agent": "StudyPlanner",
            "action": "安排复习计划",
            "timestamp": (datetime.now() - start_time).total_seconds(),
            "output_summary": planner_response.response_text[:100] + "..."
        })

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
                "execution_time": (datetime.now() - start_time).total_seconds()
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
        conversation_history: List[Dict],
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
    , tool_call_id: Optional[str] = None) -> CollaborationResult:
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

        # Step 1: ProblemSolverAgent 分析错误模式
        logger.info("[ErrorDiagnosis] Step 1: Analyzing error pattern...")
        solver = ProblemSolverAgent()
        solver_context = EnhancedAgentContext(
            **{**context.__dict__,
               "user_query": f"分析这道题的错误模式和知识点缺陷：{query}"}
        )
        solver_response = await solver.process(solver_context)
        outputs.append(solver_response)
        timeline.append({
            "agent": "ProblemSolver",
            "action": "分析错误原因",
            "timestamp": (datetime.now() - start_time).total_seconds(),
            "output_summary": solver_response.response_text[:100] + "..."
        })

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
               "user_query": f"为薄弱知识点安排针对性复习：{', '.join(weak_points)}"}
        )
        planner_response = await planner.process(planner_context)
        outputs.append(planner_response)
        timeline.append({
            "agent": "StudyPlanner",
            "action": "制定复习计划",
            "timestamp": (datetime.now() - start_time).total_seconds(),
            "output_summary": planner_response.response_text[:100] + "..."
        })

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
                   "user_query": f"生成5道类似的练习题（难度递进）：{', '.join(weak_points)}"}
            )
            practice_response = await math_agent.process(practice_context)
        elif is_code:
            code_agent = CodeAgent()
            practice_context = EnhancedAgentContext(
                **{**context.__dict__,
                   "user_query": f"生成3个编程练习题（涉及知识点：{', '.join(weak_points)}）"}
            )
            practice_response = await code_agent.process(practice_context)

        if practice_response:
            outputs.append(practice_response)
            timeline.append({
                "agent": "PracticeGenerator",
                "action": "生成练习题",
                "timestamp": (datetime.now() - start_time).total_seconds(),
                "output_summary": practice_response.response_text[:100] + "..."
            })

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
                "execution_time": (datetime.now() - start_time).total_seconds()
            },
            timeline=timeline,
            confidence=0.90
        )

    def _format_diagnosis_report(
        self,
        solver_response: AgentResponse,
        planner_response: AgentResponse,
        practice_response: Optional[AgentResponse],
        weak_points: List[str]
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
