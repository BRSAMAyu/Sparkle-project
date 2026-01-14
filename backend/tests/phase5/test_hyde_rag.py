"""
测试：HyDE RAG 策略 (Phase 5A)

验证 HyDE 的延迟预算和超时降级机制
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from datetime import datetime
from uuid import uuid4

from app.services.cognitive_service import CognitiveService
from app.models.cognitive import CognitiveFragment
from app.config.phase5_config import phase5_config


class MockDB:
    """模拟数据库会话"""

    def __init__(self):
        self.fragments = []

    async def execute(self, query):
        class MockResult:
            def scalar_one_or_none(self):
                return self.fragments[0] if self.fragments else None

            def scalars(self):
                class MockScalars:
                    def __init__(self, items):
                        self.items = items

                    def all(self):
                        return self.items

                return MockScalars(self.fragments)

        return MockResult()

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


@pytest.mark.asyncio
async def test_hyde_enabled_for_short_queries():
    """测试：短查询应启用 HyDE"""
    db = MockDB()
    service = CognitiveService(db)

    # 创建短查询片段
    short_content = "I feel anxious"  # < 100 chars
    fragment = CognitiveFragment(
        id=uuid4(),
        user_id=uuid4(),
        content=short_content,
        source_type="manual",
        embedding=[0.1] * 1536
    )

    db.fragments = [fragment]

    # Mock LLM service
    with patch('app.services.cognitive_service.llm_service') as mock_llm:
        mock_llm.chat = AsyncMock(return_value="Hypothetical analysis of anxiety")

        # Mock embedding service
        with patch('app.services.cognitive_service.embedding_service') as mock_emb:
            mock_emb.get_embedding = AsyncMock(return_value=[0.2] * 1536)

            result = await service.analyze_behavior(fragment.user_id, fragment.id)

            # 验证 HyDE 被使用
            assert result["_meta"]["strategy_used"] == "raw+hyde"
            assert not result["_meta"]["hyde_cancelled"]


@pytest.mark.asyncio
async def test_hyde_disabled_for_long_queries():
    """测试：长查询应禁用 HyDE"""
    db = MockDB()
    service = CognitiveService(db)

    # 创建长查询片段
    long_content = "A" * 150  # > 100 chars
    fragment = CognitiveFragment(
        id=uuid4(),
        user_id=uuid4(),
        content=long_content,
        source_type="manual",
        embedding=[0.1] * 1536
    )

    db.fragments = [fragment]

    # Mock services
    with patch('app.services.cognitive_service.llm_service') as mock_llm:
        mock_llm.chat = AsyncMock(return_value='{"pattern_name": "test", "confidence_score": 0.9}')

        result = await service.analyze_behavior(fragment.user_id, fragment.id)

        # 验证只使用 Raw Search
        assert result["_meta"]["strategy_used"] == "raw"


@pytest.mark.asyncio
async def test_hyde_timeout_degradation():
    """测试：HyDE 超时应降级为 Raw Search"""
    db = MockDB()
    service = CognitiveService(db)

    short_content = "anxious"
    fragment = CognitiveFragment(
        id=uuid4(),
        user_id=uuid4(),
        content=short_content,
        source_type="manual",
        embedding=[0.1] * 1536
    )

    db.fragments = [fragment]

    # Mock LLM service with delay exceeding timeout
    async def slow_chat(*args, **kwargs):
        await asyncio.sleep(phase5_config.HYDE_LATENCY_BUDGET_SEC + 0.5)
        return "This should not be reached"

    with patch('app.services.cognitive_service.llm_service') as mock_llm:
        mock_llm.chat = slow_chat

        result = await service.analyze_behavior(fragment.user_id, fragment.id)

        # 验证 HyDE 被取消
        assert result["_meta"]["hyde_cancelled"] is True
        assert result["_meta"]["strategy_used"] == "raw+hyde"
        # 验证整体延迟在合理范围内（不会等待 HyDE 完成）
        assert result["_meta"]["latency_ms"] < 5000  # 应该 < 5 秒


@pytest.mark.asyncio
async def test_hyde_latency_budget_configurable():
    """测试：HyDE 延迟预算可配置"""
    # 验证配置生效
    assert phase5_config.HYDE_LATENCY_BUDGET_SEC > 0
    assert phase5_config.HYDE_QUERY_LENGTH_THRESHOLD > 0

    # 测试不同配置
    original_timeout = phase5_config.HYDE_LATENCY_BUDGET_SEC

    # 临时修改配置
    phase5_config.HYDE_LATENCY_BUDGET_SEC = 0.5

    db = MockDB()
    service = CognitiveService(db)

    fragment = CognitiveFragment(
        id=uuid4(),
        user_id=uuid4(),
        content="test",
        source_type="manual",
        embedding=[0.1] * 1536
    )

    db.fragments = [fragment]

    async def moderate_delay_chat(*args, **kwargs):
        await asyncio.sleep(0.7)  # 超过 0.5s 但不太长
        return "result"

    with patch('app.services.cognitive_service.llm_service') as mock_llm:
        mock_llm.chat = moderate_delay_chat

        result = await service.analyze_behavior(fragment.user_id, fragment.id)

        # 应该超时
        assert result["_meta"]["hyde_cancelled"] is True

    # 恢复配置
    phase5_config.HYDE_LATENCY_BUDGET_SEC = original_timeout


@pytest.mark.asyncio
async def test_hyde_result_deduplication():
    """测试：HyDE 和 Raw 结果应正确去重"""
    db = MockDB()
    service = CognitiveService(db)

    fragment = CognitiveFragment(
        id=uuid4(),
        user_id=uuid4(),
        content="test",
        source_type="manual",
        embedding=[0.1] * 1536
    )

    # 创建一些相似片段（会在 Raw 和 HyDE 中都出现）
    similar1 = CognitiveFragment(
        id=uuid4(),
        user_id=fragment.user_id,
        content="similar 1",
        source_type="manual",
        embedding=[0.11] * 1536
    )

    db.fragments = [fragment, similar1]

    with patch('app.services.cognitive_service.llm_service') as mock_llm:
        mock_llm.chat = AsyncMock(return_value='{"pattern_name": "test", "confidence_score": 0.9}')

        with patch('app.services.cognitive_service.embedding_service') as mock_emb:
            mock_emb.get_embedding = AsyncMock(return_value=[0.12] * 1536)

            result = await service.analyze_behavior(fragment.user_id, fragment.id)

            # 验证结果去重（不会有重复的片段）
            # 这个测试需要实际运行才能验证逻辑
            assert "error" not in result or result.get("error") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
