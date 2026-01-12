"""
Orchestrator Agent - 协调者智能体

负责路由查询到合适的专业智能体，并整合多个智能体的响应
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from .base_agent import BaseAgent, AgentRole, AgentContext, AgentResponse
from .specialist_agents import MathAgent, CodeAgent, WritingAgent, ScienceAgent


class OrchestratorAgent(BaseAgent):
    """协调者智能体 - 路由和协调多个专业智能体"""

    def __init__(self):
        super().__init__()
        self.role = AgentRole.ORCHESTRATOR
        self.name = "Orchestrator"
        self.description = "Routes queries to specialist agents and coordinates multi-agent collaboration"
        self.capabilities = [
            "Route queries to appropriate specialists",
            "Coordinate multi-agent workflows",
            "Synthesize responses from multiple agents",
            "Handle complex multi-domain queries"
        ]

        # 初始化专家智能体
        self.specialist_agents: List[BaseAgent] = [
            MathAgent(),
            CodeAgent(),
            WritingAgent(),
            ScienceAgent(),
        ]

    def can_handle(self, query: str) -> float:
        """协调者总是可以处理任何查询（降级默认）"""
        return 0.5

    async def process(self, context: AgentContext) -> AgentResponse:
        """
        处理请求 - 主要流程：
        1. 分析查询，判断需要哪些专家
        2. 路由到合适的智能体
        3. 收集并整合响应
        """
        logger.info(f"Orchestrator processing: {context.user_query[:50]}...")

        # 1. 路由决策：选择最合适的智能体
        selected_agents = await self._route_query(context.user_query)

        if not selected_agents:
            # 没有专家可用，降级为通用响应
            return await self._fallback_response(context)

        # 2. 并发调用多个智能体（如果需要）
        agent_responses = []

        for agent in selected_agents:
            try:
                response = await agent.process(context)
                agent_responses.append(response)
                logger.info(
                    f"Agent {agent.name} responded with confidence {response.confidence}"
                )
            except Exception as e:
                logger.error(f"Agent {agent.name} failed: {e}")

        # 3. 整合响应
        if len(agent_responses) == 1:
            # 单个智能体响应，直接返回
            return agent_responses[0]
        else:
            # 多个智能体响应，需要整合
            return await self._synthesize_responses(context, agent_responses)

    async def _route_query(self, query: str) -> List[BaseAgent]:
        """
        路由查询到合适的智能体

        Returns:
            List[BaseAgent]: 选中的智能体列表（按置信度排序）
        """
        # 计算每个智能体的匹配度
        agent_scores = []
        for agent in self.specialist_agents:
            score = agent.can_handle(query)
            agent_scores.append((agent, score))

        # 按分数排序
        agent_scores.sort(key=lambda x: x[1], reverse=True)

        # 选择分数 > 0.3 的智能体
        selected = [agent for agent, score in agent_scores if score > 0.3]

        # 如果有多个高分智能体（多领域查询），保留前2个
        if len(selected) > 2:
            selected = selected[:2]

        logger.info(
            f"Routing decision: {[agent.name for agent in selected]} "
            f"(scores: {[score for _, score in agent_scores[:len(selected)]]})"
        )

        return selected

    async def _synthesize_responses(
        self,
        context: AgentContext,
        responses: List[AgentResponse]
    ) -> AgentResponse:
        """
        整合多个智能体的响应

        Args:
            context: 用户上下文
            responses: 多个智能体的响应

        Returns:
            AgentResponse: 整合后的响应
        """
        logger.info(f"Synthesizing {len(responses)} agent responses")

        # 构建整合后的响应文本
        synthesized_text = f"## 多专家协作回答\n\n"
        synthesized_text += f"您的问题涉及多个领域，以下是我们团队的综合答复：\n\n"

        for i, response in enumerate(responses, 1):
            synthesized_text += f"### {i}. {response.agent_name} 的回答\n\n"
            synthesized_text += response.response_text
            synthesized_text += "\n\n---\n\n"

        # 添加总结（可选：调用 LLM 生成总结）
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

    async def _fallback_response(self, context: AgentContext) -> AgentResponse:
        """降级响应（当没有专家可用时）"""
        from app.services.llm_service import llm_service

        logger.warning("No specialist agents matched, using fallback LLM")

        try:
            response_text = await llm_service.chat(
                prompt=f"User Query: {context.user_query}",
                model="qwen-plus"
            )

            return self.format_response(
                text=response_text,
                reasoning="Fallback to general LLM (no specialist match)",
                confidence=0.7,
                metadata={"fallback": True}
            )

        except Exception as e:
            logger.error(f"Fallback response failed: {e}")
            return self.format_response(
                text="抱歉，我暂时无法回答这个问题。请稍后重试。",
                confidence=0.0,
                metadata={"error": str(e)}
            )


class MultiAgentWorkflow:
    """多智能体工作流 - 高级协作模式"""

    def __init__(self):
        self.orchestrator = OrchestratorAgent()

    async def execute(
        self,
        user_query: str,
        user_id: str,
        session_id: str,
        tool_call_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行多智能体工作流

        Args:
            user_query: 用户查询
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            dict: 工作流执行结果
        """
        # 构建上下文
        context = AgentContext(
            user_id=user_id,
            session_id=session_id,
            user_query=user_query,
            conversation_history=kwargs.get("conversation_history", []),
            knowledge_context=kwargs.get("knowledge_context"),
            user_preferences=kwargs.get("user_preferences"),
        )

        # 执行协调器
        result = await self.orchestrator.process(context)

        return {
            "response_text": result.response_text,
            "agent_role": result.agent_role,
            "agent_name": result.agent_name,
            "reasoning": result.reasoning,
            "confidence": result.confidence,
            "metadata": result.metadata or {},
        }


# 便捷工厂函数
def create_multi_agent_workflow() -> MultiAgentWorkflow:
    """创建多智能体工作流实例"""
    return MultiAgentWorkflow()
