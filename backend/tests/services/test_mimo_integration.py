"""
MIMO v2-pro 集成测试

测试 MIMO 体系的：
1. 分层路由（STANDARD 和 MAX 层级）
2. 联网搜索功能
3. 思考链响应处理
"""
import pytest
from unittest.mock import MagicMock, patch

from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.llm_router import LLMRouter, ModelConfig, ModelProvider


class TestMIMOPRoTierRouting:
    """测试 MIMO 分层路由"""

    def test_mimo_flash_thinking_is_available_in_standard_tier(self):
        """验证标准层使用 flash 思考模型而非 mimo_pro"""
        router = LLMRouter()

        standard_models = router._tier_mapping.get(ModelTier.STANDARD, [])

        assert "xiaomi_standard_thinking" in standard_models
        assert "mimo_pro" not in standard_models

    def test_mimo_pro_is_available_in_max_tier(self):
        """验证 mimo_pro 被提升到 MAX 层级"""
        router = LLMRouter()

        max_models = router._tier_mapping.get(ModelTier.MAX, [])

        assert "mimo_pro" in max_models

    def test_mimo_pro_config_has_web_search_enabled(self):
        """验证 mimo_pro 配置启用了联网搜索"""
        router = LLMRouter()

        mimo_pro_config = router._available_models.get("mimo_pro")

        assert mimo_pro_config is not None, "mimo_pro 配置应该存在"
        assert mimo_pro_config.enable_web_search is True, "mimo_pro 应该启用联网搜索"
        assert mimo_pro_config.thinking_mode == "enabled", "mimo_pro 应该启用思考模式"

    def test_select_model_returns_standard_tier_model_for_standard_task(self):
        """验证 STANDARD 任务不再默认命中 mimo_pro"""
        router = LLMRouter()

        selection = router.select_model(
            agent_role=AgentRole.GENERATION,
            task_type=TaskType.STANDARD_RESPONSE,
            reasoning_mode='balanced',
        )

        assert selection.model_key in {"xiaomi_standard_thinking", "dashscope_standard_thinking"}

    def test_select_model_returns_pro_tier_model_for_reasoning_task(self):
        """验证深任务默认走 pro 层而不是 max"""
        router = LLMRouter()

        selection = router.select_model(
            agent_role=AgentRole.EXAM_ORACLE,
            task_type=TaskType.DEEP_REASONING,
            reasoning_mode='deep',
        )

        assert selection.model_key in {"dashscope_reason", "deepseek_reason"}


class TestMIMOProConfigFields:
    """测试 mimo_pro 配置字段"""

    def test_mimo_pro_uses_xiaomi_provider(self):
        """验证 mimo_pro 使用 XIAOMI 提供商"""
        router = LLMRouter()

        mimo_pro_config = router._available_models.get("mimo_pro")

        assert mimo_pro_config.provider == ModelProvider.XIAOMI

    def test_mimo_pro_model_name_is_correct(self):
        """验证 mimo_pro 使用正确的模型名称"""
        router = LLMRouter()

        mimo_pro_config = router._available_models.get("mimo_pro")

        assert mimo_pro_config.model_name == "mimo-v2-pro"

    def test_mimo_pro_temperature_is_correct(self):
        """验证 mimo_pro 使用正确的默认温度"""
        router = LLMRouter()

        mimo_pro_config = router._available_models.get("mimo_pro")

        # mimo-v2-pro 默认温度是 1.0
        assert mimo_pro_config.temperature == 1.0


class TestMIMOWebSearchTool:
    """测试 MIMO 联网搜索工具"""

    def test_web_search_tool_structure(self):
        """验证联网搜索工具的结构正确"""
        web_search_tool = {"type": "web_search"}

        assert web_search_tool["type"] == "web_search"
        assert "function" not in web_search_tool  # 联网搜索不是 function 工具


class TestMIMOResponseFields:
    """测试 MIMO 响应字段处理"""

    def test_llm_response_has_mimo_fields(self):
        """验证 LLMResponse 包含 MIMO 特有字段"""
        from app.services.llm_service import LLMResponse

        response = LLMResponse(
            content="Hello",
            reasoning_content="Let me think...",
            annotations=[{"title": "Search Result", "url": "https://example.com"}],
            web_search_usage={"tool_usage": 1, "page_usage": 3}
        )

        assert response.reasoning_content == "Let me think..."
        assert len(response.annotations) == 1
        assert response.web_search_usage["tool_usage"] == 1

    def test_stream_chunk_has_mimo_fields(self):
        """验证 StreamChunk 包含 MIMO 特有字段"""
        from app.services.llm_service import StreamChunk

        chunk = StreamChunk(
            type="reasoning",
            reasoning_content="Thinking..."
        )

        assert chunk.type == "reasoning"
        assert chunk.reasoning_content == "Thinking..."

        annotation_chunk = StreamChunk(
            type="annotation",
            annotations=[{"title": "Test"}]
        )

        assert annotation_chunk.type == "annotation"
        assert len(annotation_chunk.annotations) == 1
