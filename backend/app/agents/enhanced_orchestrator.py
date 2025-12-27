"""
Enhanced Orchestrator Agent - 增强版协调者

支持：
1. 智能工作流选择（TaskDecomposition, ProgressiveExploration, ErrorDiagnosis）
2. 集成知识星图和遗忘曲线数据
3. 生产级监控和错误处理
4. OpenTelemetry 追踪
"""

import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID
from loguru import logger
from opentelemetry import trace

from .base_agent import BaseAgent, AgentRole, AgentContext, AgentResponse
from .specialist_agents import MathAgent, CodeAgent, WritingAgent, ScienceAgent
from .enhanced_agents import (
    StudyPlannerAgent,
    ProblemSolverAgent,
    EnhancedAgentContext,
    EnhancedAgentRole
)
from .collaboration_workflows import (
    TaskDecompositionWorkflow,
    ProgressiveExplorationWorkflow,
    ErrorDiagnosisWorkflow,
    CollaborationResult
)

tracer = trace.get_tracer(__name__)


class EnhancedOrchestratorAgent(BaseAgent):
    """
    增强版协调者智能体

    核心功能：
    1. 智能路由：根据查询类型选择最佳工作流
    2. 上下文增强：自动获取知识星图、遗忘曲线等数据
    3. 工作流调度：管理多智能体协作流程
    4. 响应整合：统一格式化协作结果
    5. 生产级监控：OpenTelemetry 追踪 + 错误处理
    """

    def __init__(self):
        super().__init__()
        self.role = AgentRole.ORCHESTRATOR
        self.name = "Enhanced Orchestrator"
        self.description = "Intelligently routes queries and coordinates multi-agent workflows with knowledge graph integration"
        self.capabilities = [
            "Intelligent workflow selection (Task/Exploration/Error)",
            "Knowledge graph & forgetting curve integration",
            "Multi-agent collaboration coordination",
            "Unified response synthesis",
            "Production-grade monitoring & error handling"
        ]

        # 初始化所有智能体
        self.specialist_agents: List[BaseAgent] = [
            # 增强版智能体
            StudyPlannerAgent(),
            ProblemSolverAgent(),
            # 原有专家智能体
            MathAgent(),
            CodeAgent(),
            WritingAgent(),
            ScienceAgent(),
        ]

        # 初始化协作工作流
        self.collaboration_workflows = {
            "task_decomposition": TaskDecompositionWorkflow(self),
            "progressive_exploration": ProgressiveExplorationWorkflow(self),
            "error_diagnosis": ErrorDiagnosisWorkflow(self)
        }

    def can_handle(self, query: str) -> float:
        """协调者总是可以处理任何查询"""
        return 1.0

    async def process(self, context: AgentContext) -> AgentResponse:
        """
        处理请求 - 增强版流程

        1. 分析查询意图，选择协作模式
        2. 构建增强上下文（集成知识星图等数据）
        3. 执行协作流程
        4. 格式化响应
        """
        with tracer.start_as_current_span("enhanced_orchestrator_process") as span:
            span.set_attribute("user_id", str(context.user_id))
            span.set_attribute("query_length", len(context.user_query))

            logger.info(f"[EnhancedOrchestrator] Processing: {context.user_query[:50]}...")

            try:
                # 1. 分析查询，选择工作流类型
                workflow_type = await self._select_workflow_type(context.user_query)
                span.set_attribute("workflow_type", workflow_type)
                logger.info(f"[EnhancedOrchestrator] Selected workflow: {workflow_type}")

                # 2. 构建增强上下文
                enhanced_context = await self._build_enhanced_context(context)

                # 3. 执行协作流程
                if workflow_type in self.collaboration_workflows:
                    # 使用协作工作流
                    result = await self.collaboration_workflows[workflow_type].execute(
                        context.user_query,
                        enhanced_context
                    )
                    response = self._format_collaboration_response(result)
                    span.set_attribute("collaboration_mode", True)
                    span.set_attribute("agents_count", len(result.participants))
                else:
                    # 降级到原有路由逻辑（单个或两个智能体）
                    response = await self._fallback_routing(enhanced_context)
                    span.set_attribute("collaboration_mode", False)

                span.set_attribute("response_confidence", response.confidence or 0.0)
                return response

            except Exception as e:
                logger.error(f"[EnhancedOrchestrator] Error: {e}", exc_info=True)
                span.set_attribute("error", str(e))
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))

                return self.format_response(
                    text=f"抱歉，处理你的请求时遇到错误：{str(e)}",
                    reasoning="System error occurred during orchestration",
                    confidence=0.0,
                    metadata={"error": str(e), "error_type": type(e).__name__}
                )

    async def _select_workflow_type(self, query: str) -> str:
        """
        智能选择协作模式

        基于关键词和意图分析，选择最合适的工作流
        """
        with tracer.start_as_current_span("select_workflow"):
            # 定义模式特征
            patterns = {
                "task_decomposition": {
                    "keywords": ["计划", "plan", "准备", "prepare", "复习", "review",
                                "考试", "exam", "冲刺", "sprint", "学习路径", "学什么"],
                    "weight": 1.0
                },
                "progressive_exploration": {
                    "keywords": ["解释", "explain", "理解", "understand", "详细说明", "detail",
                                "深入", "deep", "原理", "principle", "如何工作", "how it works",
                                "为什么", "why"],
                    "weight": 1.0
                },
                "error_diagnosis": {
                    "keywords": ["错题", "wrong", "错误", "error", "mistake", "不明白", "confused",
                                "不懂", "don't understand", "搞混", "混淆", "做错了", "failed"],
                    "weight": 1.2  # 错题诊断优先级稍高
                }
            }

            # 计算每个模式的匹配分数
            scores = {}
            query_lower = query.lower()

            for workflow, config in patterns.items():
                keywords = config["keywords"]
                weight = config["weight"]

                matches = sum(1 for kw in keywords if kw in query_lower)
                scores[workflow] = matches * weight

            # 选择最高分
            best_workflow = max(scores, key=scores.get)
            best_score = scores[best_workflow]

            # 如果最高分太低（< 1），降级为默认模式
            if best_score < 1:
                logger.info(f"[EnhancedOrchestrator] Low confidence ({best_score}), using fallback routing")
                return "default"

            logger.info(f"[EnhancedOrchestrator] Workflow scores: {scores}, selected: {best_workflow}")
            return best_workflow

    async def _build_enhanced_context(
        self,
        context: AgentContext
    ) -> EnhancedAgentContext:
        """
        构建增强上下文

        从知识星图、遗忘曲线、任务系统等获取数据

        注意：实际生产环境需要从 context 中获取 db_session 并调用真实服务
        这里使用模拟数据作为示例
        """
        with tracer.start_as_current_span("build_enhanced_context"):
            # TODO: 在实际生产环境中，这些数据应该通过服务获取
            # db = context.db_session
            # galaxy_service = GalaxyService(db)
            # decay_service = DecayService(db)
            # task_service = TaskService()

            # 模拟数据（实际应调用真实服务）
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

            active_tasks = []
            active_plans = []

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
                active_tasks=active_tasks,
                active_plans=active_plans,
                study_time_preference="evening",
                learning_style="visual",
                common_errors=["忘记考虑边界条件", "符号错误"]
            )

    def _format_collaboration_response(
        self,
        result: CollaborationResult
    ) -> AgentResponse:
        """
        格式化协作结果

        将 CollaborationResult 转换为 AgentResponse
        """
        # 构建可视化数据
        visualization_data = {
            "workflow_type": result.workflow_type,
            "participants": result.participants,
            "timeline": result.timeline,
            "metadata": result.metadata
        }

        # 构建 metadata
        response_metadata = {
            "collaboration": True,
            "workflow": result.workflow_type,
            "participants": result.participants,
            "outputs": [
                {
                    "agent_name": output.agent_name,
                    "agent_role": output.agent_role,
                    "confidence": output.confidence,
                    "reasoning": output.reasoning
                }
                for output in result.outputs
            ],
            "visualization": visualization_data,
            "execution_time": result.metadata.get("execution_time", 0.0)
        }

        return AgentResponse(
            agent_role=self.role.value,
            agent_name="多专家协作团队",
            response_text=result.final_response,
            reasoning=result.reasoning,
            confidence=result.confidence,
            metadata=response_metadata
        )

    async def _fallback_routing(
        self,
        context: EnhancedAgentContext
    ) -> AgentResponse:
        """
        降级路由（单个或两个智能体）

        当查询不适合协作工作流时，使用原有的路由逻辑
        """
        with tracer.start_as_current_span("fallback_routing"):
            logger.info("[EnhancedOrchestrator] Using fallback routing...")

            # 计算每个智能体的匹配度
            agent_scores = []
            for agent in self.specialist_agents:
                score = agent.can_handle(context.user_query)
                agent_scores.append((agent, score))

            # 按分数排序
            agent_scores.sort(key=lambda x: x[1], reverse=True)

            # 选择分数 > 0.3 的智能体
            selected = [agent for agent, score in agent_scores if score > 0.3]

            # 如果有多个高分智能体，保留前 2 个
            if len(selected) > 2:
                selected = selected[:2]

            logger.info(
                f"[EnhancedOrchestrator] Selected agents: {[agent.name for agent in selected]} "
                f"(scores: {[score for _, score in agent_scores[:len(selected)]]})"
            )

            if not selected:
                # 没有匹配的智能体，使用通用 LLM
                return await self._fallback_llm(context)

            # 调用选中的智能体
            agent_responses = []
            for agent in selected:
                try:
                    response = await agent.process(context)
                    agent_responses.append(response)
                    logger.info(
                        f"[EnhancedOrchestrator] Agent {agent.name} responded with confidence {response.confidence}"
                    )
                except Exception as e:
                    logger.error(f"[EnhancedOrchestrator] Agent {agent.name} failed: {e}")

            # 整合响应
            if len(agent_responses) == 1:
                return agent_responses[0]
            else:
                return await self._synthesize_responses(context, agent_responses)

    async def _synthesize_responses(
        self,
        context: EnhancedAgentContext,
        responses: List[AgentResponse]
    ) -> AgentResponse:
        """整合多个智能体的响应"""

        synthesized_text = "## 多专家协作回答\n\n"
        synthesized_text += "您的问题涉及多个领域，以下是我们团队的综合答复：\n\n"

        for i, response in enumerate(responses, 1):
            synthesized_text += f"### {i}. {response.agent_name}\n\n"
            synthesized_text += response.response_text
            synthesized_text += "\n\n---\n\n"

        synthesized_text += "### 综合建议\n\n"
        synthesized_text += "以上专家从不同角度为您提供了解答。建议您结合各专家的建议，形成完整的理解。\n"

        return self.format_response(
            text=synthesized_text,
            reasoning="Synthesized responses from multiple specialist agents",
            confidence=0.85,
            metadata={
                "multi_agent": True,
                "agent_count": len(responses),
                "agents_involved": [r.agent_name for r in responses]
            }
        )

    async def _fallback_llm(self, context: EnhancedAgentContext) -> AgentResponse:
        """降级到通用 LLM"""
        from app.services.llm_service import llm_service

        logger.warning("[EnhancedOrchestrator] No specialist agents matched, using fallback LLM")

        try:
            response_text = await llm_service.chat(
                messages=[
                    {"role": "system", "content": "你是 Sparkle AI 学习助手，帮助学生解答学习问题。"},
                    {"role": "user", "content": context.user_query}
                ],
                model="qwen-plus"
            )

            return self.format_response(
                text=response_text,
                reasoning="Fallback to general LLM (no specialist match)",
                confidence=0.7,
                metadata={"fallback": True}
            )

        except Exception as e:
            logger.error(f"[EnhancedOrchestrator] Fallback LLM failed: {e}")
            return self.format_response(
                text="抱歉，我暂时无法回答这个问题。请稍后重试。",
                confidence=0.0,
                metadata={"error": str(e)}
            )


# ==========================================
# 工厂函数
# ==========================================
def create_enhanced_orchestrator() -> EnhancedOrchestratorAgent:
    """创建增强版协调者实例"""
    return EnhancedOrchestratorAgent()
