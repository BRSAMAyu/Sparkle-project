"""
Enhanced Educational Agents - 教育导向的增强智能体

基于 Sparkle 的知识星图、遗忘曲线和任务系统，提供深度个性化的学习支持
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from enum import Enum
from loguru import logger
from dataclasses import dataclass

from .base_agent import BaseAgent, AgentRole, AgentContext, AgentResponse
from app.services.llm_service import llm_service
from app.services.galaxy_service import GalaxyService
from app.services.task_service import TaskService
from app.services.decay_service import DecayService


# ==========================================
# 扩展 AgentRole
# ==========================================
class EnhancedAgentRole(Enum):
    """增强版智能体角色"""
    STUDY_PLANNER = "study_planner"  # 学习规划师
    PROBLEM_SOLVER = "problem_solver"  # 问题解决导师


# ==========================================
# 增强版上下文（集成知识星图和用户数据）
# ==========================================
@dataclass
class EnhancedAgentContext(AgentContext):
    """
    增强版智能体上下文

    在原有 AgentContext 基础上，添加：
    - 用户知识图谱数据
    - 掌握度分析
    - 遗忘曲线数据
    - 任务和计划信息
    - 学习行为模式
    """
    # 知识星图数据
    knowledge_graph: Optional[Dict[str, Any]] = None
    mastery_levels: Optional[Dict[str, float]] = None
    weak_concepts: Optional[List[str]] = None

    # 遗忘曲线数据
    forgetting_risks: Optional[List[Dict[str, Any]]] = None
    last_review_times: Optional[Dict[str, datetime]] = None

    # 任务和计划
    active_tasks: Optional[List[Dict[str, Any]]] = None
    active_plans: Optional[List[Dict[str, Any]]] = None

    # 学习行为
    study_time_preference: Optional[str] = None
    learning_style: Optional[str] = None
    common_errors: Optional[List[str]] = None


# ==========================================
# StudyPlannerAgent - 学习规划师
# ==========================================
class StudyPlannerAgent(BaseAgent):
    """
    学习规划师智能体

    核心能力：
    1. 基于艾宾浩斯遗忘曲线安排复习
    2. 分析知识星图，识别薄弱知识点
    3. 制定个性化学习路径
    4. 生成任务卡片（自动调用工具）
    5. 考试冲刺计划优化
    """

    def __init__(self):
        super().__init__()
        self.role = EnhancedAgentRole.STUDY_PLANNER
        self.name = "学习规划师 StudyPlanner"
        self.description = "基于遗忘曲线和知识星图，制定个性化学习计划和复习策略"
        self.capabilities = [
            "分析用户知识掌握度（知识星图）",
            "基于遗忘曲线安排科学复习",
            "制定考试冲刺计划",
            "动态调整学习路径",
            "识别学习瓶颈和薄弱点",
            "生成学习任务卡片（Learning/Training 类型）"
        ]

    def can_handle(self, query: str) -> float:
        """识别学习规划相关查询"""
        planning_keywords = [
            "计划", "plan", "复习", "review", "考试", "exam",
            "冲刺", "sprint", "安排", "schedule", "时间表", "timeline",
            "遗忘", "forget", "记忆", "memory", "准备", "prepare",
            "学什么", "怎么学", "今天学", "学习路径", "学习建议"
        ]

        query_lower = query.lower()
        matches = sum(1 for kw in planning_keywords if kw in query_lower)

        # 高权重关键词
        high_priority = ["计划", "复习", "考试", "冲刺", "准备"]
        high_matches = sum(1 for kw in high_priority if kw in query_lower)

        confidence = min((matches * 0.2) + (high_matches * 0.3), 1.0)
        return confidence

    async def process(self, context: AgentContext) -> AgentResponse:
        """处理学习规划请求"""
        logger.info(f"[StudyPlannerAgent] Processing: {context.user_query[:50]}...")

        try:
            # 获取增强上下文（知识星图、遗忘曲线等）
            enhanced_context = await self._build_enhanced_context(context)

            # 分析用户学习状态
            learning_status = await self._analyze_learning_status(enhanced_context)

            # 生成学习计划
            plan = await self._generate_study_plan(
                enhanced_context,
                learning_status
            )

            # 构建响应
            return self.format_response(
                text=plan["summary"],
                reasoning=plan["reasoning"],
                confidence=0.92,
                metadata={
                    "agent_type": "study_planner",
                    "learning_status": learning_status,
                    "plan_details": plan,
                    "tool_calls": plan.get("tool_calls", [])  # 任务生成指令
                }
            )

        except Exception as e:
            logger.error(f"[StudyPlannerAgent] Error: {e}", exc_info=True)
            return self.format_response(
                text=f"抱歉，生成学习计划时遇到错误：{str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )

    async def _build_enhanced_context(
        self,
        context: AgentContext
    ) -> EnhancedAgentContext:
        """
        构建增强上下文

        集成知识星图、遗忘曲线、任务系统的数据
        """
        # 这里需要实际的 DB session，简化示例中使用模拟数据
        # 生产环境应该从 context 中获取 db session

        # TODO: 从 context 中获取 db session
        # db = context.db_session
        # galaxy_service = GalaxyService(db)
        # decay_service = DecayService(db)
        # task_service = TaskService()

        # 模拟数据获取（实际应调用真实服务）
        knowledge_graph = {
            "total_nodes": 50,
            "unlocked_nodes": 35,
            "average_mastery": 0.72
        }

        mastery_levels = {
            "高数-极限": 0.85,
            "高数-导数": 0.65,
            "高数-积分": 0.50,
            "线代-矩阵": 0.40
        }

        weak_concepts = ["高数-积分", "线代-矩阵"]

        forgetting_risks = [
            {
                "concept": "高数-导数",
                "last_review": "5天前",
                "predicted_retention": 0.60,
                "risk_level": "medium"
            },
            {
                "concept": "线代-矩阵",
                "last_review": "10天前",
                "predicted_retention": 0.35,
                "risk_level": "high"
            }
        ]

        return EnhancedAgentContext(
            user_id=context.user_id,
            session_id=context.session_id,
            user_query=context.user_query,
            conversation_history=context.conversation_history,
            knowledge_context=context.knowledge_context,
            user_preferences=context.user_preferences,
            previous_agent_outputs=context.previous_agent_outputs,
            # 增强数据
            knowledge_graph=knowledge_graph,
            mastery_levels=mastery_levels,
            weak_concepts=weak_concepts,
            forgetting_risks=forgetting_risks,
            active_tasks=[],
            active_plans=[],
            study_time_preference="evening",
            learning_style="visual"
        )

    async def _analyze_learning_status(
        self,
        context: EnhancedAgentContext
    ) -> Dict[str, Any]:
        """分析用户学习状态"""

        # 计算整体掌握度
        avg_mastery = sum(context.mastery_levels.values()) / len(context.mastery_levels) \
            if context.mastery_levels else 0.0

        # 识别高风险遗忘点
        high_risk_concepts = [
            item["concept"] for item in (context.forgetting_risks or [])
            if item["risk_level"] == "high"
        ]

        # 识别薄弱点
        weak_points = [
            concept for concept, score in (context.mastery_levels or {}).items()
            if score < 0.6
        ]

        return {
            "overall_mastery": avg_mastery,
            "weak_points": weak_points,
            "forgetting_risks": high_risk_concepts,
            "total_concepts": len(context.mastery_levels or {}),
            "unlocked_percentage": context.knowledge_graph.get("unlocked_nodes", 0) /
                                   context.knowledge_graph.get("total_nodes", 1) if context.knowledge_graph else 0
        }

    async def _generate_study_plan(
        self,
        context: EnhancedAgentContext,
        learning_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成个性化学习计划

        调用 LLM 生成计划，同时准备任务生成的工具调用
        """

        # 构建 LLM 提示词
        system_prompt = f"""{self.get_system_prompt()}

你是 Sparkle 的学习规划师。你的任务是基于用户的知识星图和遗忘曲线数据，生成科学的学习计划。

**用户学习状态**：
- 整体掌握度：{learning_status['overall_mastery']:.1%}
- 薄弱知识点：{', '.join(learning_status['weak_points'][:3]) if learning_status['weak_points'] else '无'}
- 遗忘风险点：{', '.join(learning_status['forgetting_risks'][:3]) if learning_status['forgetting_risks'] else '无'}
- 知识星图进度：{learning_status['unlocked_percentage']:.1%}

**规划原则**：
1. 优先复习高遗忘风险的知识点（遵循艾宾浩斯遗忘曲线）
2. 针对薄弱点安排针对性训练
3. 平衡复习和新知识学习
4. 考虑用户偏好学习时间（{context.study_time_preference}）和学习风格（{context.learning_style}）

**输出格式**：
1. 总体学习建议（2-3句话）
2. 今日推荐任务（3-5项，标注优先级）
3. 本周复习计划（时间轴）
4. 长期目标建议

请用友好、激励的语气回复。
"""

        user_message = context.user_query

        # 调用 LLM
        response_text = await llm_service.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model="qwen-plus",
            temperature=0.7
        )

        # 准备任务生成的工具调用（这里是示例，实际应该通过 LLM 工具调用生成）
        tool_calls = []

        # 如果检测到高风险遗忘点，生成复习任务
        if learning_status['forgetting_risks']:
            for concept in learning_status['forgetting_risks'][:2]:
                tool_calls.append({
                    "function": "create_task",
                    "arguments": {
                        "title": f"复习 {concept}",
                        "type": "learning",
                        "priority": "high",
                        "estimated_minutes": 30,
                        "tags": ["复习", "遗忘曲线"]
                    }
                })

        # 如果有薄弱点，生成训练任务
        if learning_status['weak_points']:
            concept = learning_status['weak_points'][0]
            tool_calls.append({
                "function": "create_task",
                "arguments": {
                    "title": f"{concept} 专项训练",
                    "type": "training",
                    "priority": "medium",
                    "estimated_minutes": 45,
                    "tags": ["薄弱点", "强化训练"]
                }
            })

        reasoning = f"基于用户掌握度 {learning_status['overall_mastery']:.1%}，" \
                   f"识别出 {len(learning_status['weak_points'])} 个薄弱点，" \
                   f"{len(learning_status['forgetting_risks'])} 个遗忘风险点。" \
                   f"已生成 {len(tool_calls)} 个任务建议。"

        return {
            "summary": response_text,
            "reasoning": reasoning,
            "tool_calls": tool_calls,
            "learning_status": learning_status
        }


# ==========================================
# ProblemSolverAgent - 问题解决导师
# ==========================================
class ProblemSolverAgent(BaseAgent):
    """
    问题解决导师智能体

    核心能力：
    1. 苏格拉底式教学法（引导式提问）
    2. 知识点关联教学（基于知识星图）
    3. 错题模式识别
    4. 举一反三训练
    5. 概念深度解析
    """

    def __init__(self):
        super().__init__()
        self.role = EnhancedAgentRole.PROBLEM_SOLVER
        self.name = "问题解决导师 ProblemSolver"
        self.description = "通过引导式提问和知识点关联，帮助学生深入理解和解决问题"
        self.capabilities = [
            "苏格拉底式引导提问",
            "知识点关联教学（基于知识星图）",
            "错题模式识别和分析",
            "举一反三训练",
            "概念深度解析",
            "生成类似练习题"
        ]

    def can_handle(self, query: str) -> float:
        """识别问题解决相关查询"""
        problem_keywords = [
            "怎么做", "how to", "解释", "explain", "为什么", "why",
            "不懂", "don't understand", "不明白", "confused",
            "错题", "wrong", "错了", "mistake", "理解", "understand",
            "原理", "principle", "概念", "concept", "题", "problem",
            "练习", "practice", "解答", "solution"
        ]

        query_lower = query.lower()
        matches = sum(1 for kw in problem_keywords if kw in query_lower)

        # 检测疑问句模式
        is_question = any(q in query for q in ["?", "？", "吗", "呢", "怎么", "为什么"])

        confidence = min((matches * 0.2) + (0.3 if is_question else 0), 1.0)
        return confidence

    async def process(self, context: AgentContext) -> AgentResponse:
        """处理问题解决请求"""
        logger.info(f"[ProblemSolverAgent] Processing: {context.user_query[:50]}...")

        try:
            # 获取增强上下文
            enhanced_context = await self._build_enhanced_context(context)

            # 分析问题类型和难度
            problem_analysis = await self._analyze_problem(
                context.user_query,
                enhanced_context
            )

            # 生成苏格拉底式回答
            socratic_response = await self._generate_socratic_response(
                context.user_query,
                problem_analysis,
                enhanced_context
            )

            return self.format_response(
                text=socratic_response["answer"],
                reasoning=socratic_response["reasoning"],
                confidence=0.90,
                metadata={
                    "agent_type": "problem_solver",
                    "problem_analysis": problem_analysis,
                    "related_concepts": problem_analysis.get("related_concepts", []),
                    "follow_up_questions": socratic_response.get("follow_up_questions", [])
                }
            )

        except Exception as e:
            logger.error(f"[ProblemSolverAgent] Error: {e}", exc_info=True)
            return self.format_response(
                text=f"抱歉，解答问题时遇到错误：{str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )

    async def _build_enhanced_context(
        self,
        context: AgentContext
    ) -> EnhancedAgentContext:
        """构建增强上下文（简化版本，实际应调用真实服务）"""

        # 模拟数据
        knowledge_graph = {"total_nodes": 50, "unlocked_nodes": 35}
        mastery_levels = {
            "高数-极限": 0.85,
            "高数-导数": 0.65
        }
        common_errors = ["忘记考虑定义域", "符号错误", "计算粗心"]

        return EnhancedAgentContext(
            user_id=context.user_id,
            session_id=context.session_id,
            user_query=context.user_query,
            conversation_history=context.conversation_history,
            knowledge_context=context.knowledge_context,
            user_preferences=context.user_preferences,
            previous_agent_outputs=context.previous_agent_outputs,
            knowledge_graph=knowledge_graph,
            mastery_levels=mastery_levels,
            common_errors=common_errors
        )

    async def _analyze_problem(
        self,
        query: str,
        context: EnhancedAgentContext
    ) -> Dict[str, Any]:
        """分析问题类型和涉及的知识点"""

        # 简单关键词匹配（实际应使用 NLP 或 LLM）
        problem_type = "conceptual"  # conceptual, computational, application
        difficulty = "medium"  # easy, medium, hard

        # 从知识星图中查找相关概念
        related_concepts = []
        for concept in (context.mastery_levels or {}).keys():
            if any(kw in query for kw in concept.split("-")):
                related_concepts.append(concept)

        # 检查用户常见错误
        potential_pitfalls = [
            error for error in (context.common_errors or [])
            if any(kw in query for kw in ["计算", "求", "解"])
        ]

        return {
            "problem_type": problem_type,
            "difficulty": difficulty,
            "related_concepts": related_concepts or ["通用数学概念"],
            "potential_pitfalls": potential_pitfalls
        }

    async def _generate_socratic_response(
        self,
        query: str,
        problem_analysis: Dict[str, Any],
        context: EnhancedAgentContext
    ) -> Dict[str, Any]:
        """
        生成苏格拉底式回答

        不直接给答案，而是引导学生思考
        """

        related_concepts_str = ", ".join(problem_analysis["related_concepts"])

        system_prompt = f"""{self.get_system_prompt()}

你是 Sparkle 的问题解决导师。使用**苏格拉底式教学法**，通过引导式提问帮助学生自己发现答案。

**用户背景**：
- 相关知识点：{related_concepts_str}
- 这些知识点的掌握度：{', '.join([f'{c}: {context.mastery_levels.get(c, 0):.0%}' for c in problem_analysis['related_concepts'][:3]])}
- 用户常见错误：{', '.join((context.common_errors or [])[:3])}

**教学策略**：
1. **不要直接给答案**，而是引导学生思考
2. 分步骤提问，让学生自己推导
3. 关联用户已掌握的知识点（知识星图）
4. 提醒用户注意常见错误
5. 最后总结关键思路和方法

**回答结构**：
1. **理解问题**：复述问题核心
2. **引导思考**：提出 2-3 个引导性问题
3. **关键提示**：给出思路提示（不是完整答案）
4. **知识关联**：链接到知识星图中的相关概念
5. **注意事项**：提醒常见错误

请用友好、鼓励的语气回复。
"""

        response_text = await llm_service.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            model="qwen-plus",
            temperature=0.8
        )

        # 生成后续问题（用于深化理解）
        follow_up_questions = [
            "你能说说这个问题的关键难点在哪里吗？",
            "如果条件变化，你会如何调整解题思路？",
            "这个方法可以应用到哪些类似的题目？"
        ]

        reasoning = f"识别问题类型为 {problem_analysis['problem_type']}，" \
                   f"难度 {problem_analysis['difficulty']}，" \
                   f"涉及知识点：{related_concepts_str}"

        return {
            "answer": response_text,
            "reasoning": reasoning,
            "follow_up_questions": follow_up_questions
        }
