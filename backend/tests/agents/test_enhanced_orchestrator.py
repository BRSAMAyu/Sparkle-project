"""
Enhanced Orchestrator Agent - Unit Tests

测试增强版协调器的核心功能
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from app.agents.enhanced_orchestrator import EnhancedOrchestratorAgent
from app.agents.base_agent import AgentContext, AgentResponse
from app.agents.enhanced_agents import EnhancedAgentContext


@pytest.fixture
def orchestrator():
    """创建 EnhancedOrchestratorAgent 实例"""
    return EnhancedOrchestratorAgent()


@pytest.fixture
def sample_context():
    """创建测试用的 AgentContext"""
    return AgentContext(
        user_id=uuid4(),
        session_id=str(uuid4()),
        user_query="帮我准备高数期末考试",
        conversation_history=[],
        knowledge_context=None,
        user_preferences=None
    )


class TestWorkflowSelection:
    """测试工作流选择逻辑"""

    @pytest.mark.asyncio
    async def test_select_task_decomposition_workflow(self, orchestrator):
        """测试任务分解工作流的识别"""
        queries = [
            "帮我准备下周的机器学习考试",
            "制定这学期的数学学习计划",
            "我要在一个月内学会 Python"
        ]

        for query in queries:
            workflow_type = await orchestrator._select_workflow_type(query)
            assert workflow_type == "task_decomposition", \
                f"Query '{query}' should trigger task_decomposition workflow"

    @pytest.mark.asyncio
    async def test_select_progressive_exploration_workflow(self, orchestrator):
        """测试渐进式探索工作流的识别"""
        queries = [
            "解释神经网络的反向传播",
            "详细说明量子力学的波粒二象性",
            "深入讲解 React Hooks 的工作原理"
        ]

        for query in queries:
            workflow_type = await orchestrator._select_workflow_type(query)
            assert workflow_type == "progressive_exploration", \
                f"Query '{query}' should trigger progressive_exploration workflow"

    @pytest.mark.asyncio
    async def test_select_error_diagnosis_workflow(self, orchestrator):
        """测试错题诊断工作流的识别"""
        queries = [
            "这道极限题我总是做错",
            "我不明白为什么这道题这样做",
            "这个概念我总是搞混"
        ]

        for query in queries:
            workflow_type = await orchestrator._select_workflow_type(query)
            assert workflow_type == "error_diagnosis", \
                f"Query '{query}' should trigger error_diagnosis workflow"

    @pytest.mark.asyncio
    async def test_fallback_to_default_workflow(self, orchestrator):
        """测试降级到默认工作流"""
        low_confidence_queries = [
            "你好",
            "今天天气怎么样",
            "xyz"
        ]

        for query in low_confidence_queries:
            workflow_type = await orchestrator._select_workflow_type(query)
            assert workflow_type == "default", \
                f"Query '{query}' should fallback to default workflow"


class TestEnhancedContextBuilding:
    """测试增强上下文构建"""

    @pytest.mark.asyncio
    async def test_build_enhanced_context(self, orchestrator, sample_context):
        """测试构建增强上下文"""
        enhanced_context = await orchestrator._build_enhanced_context(sample_context)

        # 验证类型
        assert isinstance(enhanced_context, EnhancedAgentContext)

        # 验证基础字段
        assert enhanced_context.user_id == sample_context.user_id
        assert enhanced_context.user_query == sample_context.user_query

        # 验证增强字段存在
        assert enhanced_context.knowledge_graph is not None
        assert enhanced_context.mastery_levels is not None
        assert enhanced_context.weak_concepts is not None
        assert enhanced_context.forgetting_risks is not None

        # 验证数据结构
        assert isinstance(enhanced_context.knowledge_graph, dict)
        assert isinstance(enhanced_context.mastery_levels, dict)
        assert isinstance(enhanced_context.weak_concepts, list)
        assert isinstance(enhanced_context.forgetting_risks, list)

    @pytest.mark.asyncio
    async def test_enhanced_context_contains_learning_data(self, orchestrator, sample_context):
        """测试增强上下文包含学习数据"""
        enhanced_context = await orchestrator._build_enhanced_context(sample_context)

        # 验证知识星图数据
        assert "total_nodes" in enhanced_context.knowledge_graph
        assert "unlocked_nodes" in enhanced_context.knowledge_graph
        assert "average_mastery" in enhanced_context.knowledge_graph

        # 验证掌握度数据
        assert len(enhanced_context.mastery_levels) > 0
        for concept, mastery in enhanced_context.mastery_levels.items():
            assert 0.0 <= mastery <= 1.0

        # 验证遗忘风险数据
        for risk in enhanced_context.forgetting_risks:
            assert "concept" in risk
            assert "risk_level" in risk
            assert risk["risk_level"] in ["low", "medium", "high"]


class TestCollaborationResponse:
    """测试协作响应格式化"""

    @pytest.mark.asyncio
    async def test_format_collaboration_response(self, orchestrator):
        """测试协作结果格式化"""
        from app.agents.collaboration_workflows import CollaborationResult
        from app.agents.base_agent import AgentResponse

        # 创建模拟的协作结果
        mock_result = CollaborationResult(
            workflow_type="task_decomposition",
            participants=["StudyPlanner", "MathExpert", "CodeExpert"],
            outputs=[
                AgentResponse(
                    agent_role="study_planner",
                    agent_name="学习规划师",
                    response_text="已分析学习状态...",
                    confidence=0.9
                ),
                AgentResponse(
                    agent_role="math",
                    agent_name="数学专家",
                    response_text="已生成练习题...",
                    confidence=0.85
                )
            ],
            final_response="完整的学习计划...",
            reasoning="任务分解协作完成",
            metadata={"execution_time": 2.5},
            timeline=[
                {"agent": "StudyPlanner", "action": "分析学习状态", "timestamp": 0.5},
                {"agent": "MathExpert", "action": "生成练习题", "timestamp": 1.5}
            ],
            confidence=0.88
        )

        # 格式化响应
        response = orchestrator._format_collaboration_response(mock_result)

        # 验证响应结构
        assert isinstance(response, AgentResponse)
        assert response.response_text == mock_result.final_response
        assert response.confidence == mock_result.confidence

        # 验证元数据
        assert response.metadata["collaboration"] is True
        assert response.metadata["workflow"] == "task_decomposition"
        assert response.metadata["participants"] == ["StudyPlanner", "MathExpert", "CodeExpert"]

        # 验证可视化数据
        assert "visualization" in response.metadata
        viz_data = response.metadata["visualization"]
        assert viz_data["workflow_type"] == "task_decomposition"
        assert len(viz_data["timeline"]) == 2


class TestErrorHandling:
    """测试错误处理和降级机制"""

    @pytest.mark.asyncio
    async def test_fallback_routing_on_workflow_failure(self, orchestrator, sample_context):
        """测试工作流失败时的降级路由"""
        with patch.object(
            orchestrator.collaboration_workflows["task_decomposition"],
            "execute",
            side_effect=Exception("Mock workflow failure")
        ):
            # 应该降级到 fallback_routing
            response = await orchestrator.process(sample_context)

            # 验证返回了响应（即使工作流失败）
            assert isinstance(response, AgentResponse)
            # 置信度应该较低
            assert response.confidence is not None

    @pytest.mark.asyncio
    async def test_fallback_llm_on_agent_failure(self, orchestrator, sample_context):
        """测试所有 Agent 失败时的 LLM 降级"""
        # Mock 所有 specialist agents 失败
        for agent in orchestrator.specialist_agents:
            agent.can_handle = Mock(return_value=0.0)

        # Force default workflow to trigger fallback routing logic
        with patch.object(orchestrator, "_select_workflow_type", new=AsyncMock(return_value="default")):
            # 应该降级到 fallback_llm
            with patch("app.services.llm_service.llm_service") as mock_llm:
                mock_llm.chat = AsyncMock(return_value="LLM 降级响应")

                response = await orchestrator.process(sample_context)

                # 验证调用了 LLM
                mock_llm.chat.assert_called_once()

                # 验证返回了降级响应
                assert isinstance(response, AgentResponse)
                assert response.metadata.get("fallback") is True


class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_response_time_under_threshold(self, orchestrator, sample_context):
        """测试响应时间在阈值内"""
        import time

        start_time = time.time()
        response = await orchestrator.process(sample_context)
        elapsed_time = time.time() - start_time

        # 验证响应时间 < 10秒（单个 Agent）
        assert elapsed_time < 10.0, \
            f"Response time ({elapsed_time:.2f}s) exceeds threshold"

        # 验证返回了有效响应
        assert isinstance(response, AgentResponse)
        assert len(response.response_text) > 0


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_task_decomposition(self, orchestrator):
        """端到端测试：任务分解工作流"""
        context = AgentContext(
            user_id=uuid4(),
            session_id=str(uuid4()),
            user_query="帮我准备下周的机器学习考试",
            conversation_history=[]
        )

        response = await orchestrator.process(context)

        # 验证响应
        assert isinstance(response, AgentResponse)
        assert response.response_text is not None
        assert len(response.response_text) > 100  # 应该有详细的学习计划

        # 验证协作元数据
        if response.metadata and response.metadata.get("collaboration"):
            assert response.metadata["workflow"] == "task_decomposition"
            assert len(response.metadata["participants"]) >= 2

    @pytest.mark.asyncio
    async def test_end_to_end_error_diagnosis(self, orchestrator):
        """端到端测试：错题诊断工作流"""
        context = AgentContext(
            user_id=uuid4(),
            session_id=str(uuid4()),
            user_query="这道极限题我总是做错：lim(x→0) sin(x)/x",
            conversation_history=[]
        )

        response = await orchestrator.process(context)

        # 验证响应
        assert isinstance(response, AgentResponse)
        assert response.response_text is not None

        # 应该包含错误分析
        assert any(keyword in response.response_text for keyword in ["错误", "分析", "建议"])


# ==========================================
# Pytest Configuration
# ==========================================

@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """配置测试日志"""
    import logging
    logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
