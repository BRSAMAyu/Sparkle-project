"""
LLM 成本控制与配额管理单元测试

测试配额检查、成本估算、断路器等功能

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta

from app.core.llm_quota import (
    LLMCostGuard,
    QuotaConfig,
    QuotaCheckResult,
    UserStats,
    protected_llm_call,
    QuotaExceededError
)


class TestQuotaConfig:
    """配额配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = QuotaConfig()

        assert config.daily_token_limit == 100_000
        assert config.warning_threshold == 0.8
        assert config.emergency_mode is False
        assert config.emergency_multiplier == 2.0

    def test_custom_config(self):
        """测试自定义配置"""
        config = QuotaConfig(
            daily_token_limit=50_000,
            warning_threshold=0.9,
            emergency_multiplier=3.0
        )

        assert config.daily_token_limit == 50_000
        assert config.warning_threshold == 0.9
        assert config.emergency_multiplier == 3.0


class TestLLMCostGuard:
    """LLM 成本守卫测试类"""

    @pytest.fixture
    def mock_redis(self):
        """创建模拟 Redis 客户端"""
        redis = Mock()
        redis.get = AsyncMock(return_value=None)
        redis.incrby = AsyncMock(return_value=None)
        redis.incr = AsyncMock(return_value=None)
        redis.setex = AsyncMock(return_value=None)
        redis.delete = AsyncMock(return_value=None)
        redis.pipeline = Mock()

        # 模拟管道
        mock_pipeline = Mock()
        mock_pipeline.get = Mock(return_value=mock_pipeline)
        mock_pipeline.incrby = Mock(return_value=mock_pipeline)
        mock_pipeline.incr = Mock(return_value=mock_pipeline)
        mock_pipeline.expire = Mock(return_value=mock_pipeline)
        mock_pipeline.execute = AsyncMock(return_value=[None, None, None])
        redis.pipeline.return_value = mock_pipeline

        return redis

    @pytest.fixture
    def cost_guard(self, mock_redis):
        """创建成本守卫实例"""
        config = QuotaConfig(daily_token_limit=100_000)
        return LLMCostGuard(mock_redis, config)

    # =============================================================================
    # Token 估算测试
    # =============================================================================

    def test_estimate_tokens_chinese(self, cost_guard):
        """测试中文 Token 估算"""
        # 纯中文
        text = "你好，这是一个测试"
        tokens = cost_guard.estimate_tokens(text, is_chinese_heavy=True)
        # 8个中文字符 ≈ 4 tokens, 加上安全边际 1.2 = 4.8 ≈ 5
        assert tokens >= 4

    def test_estimate_tokens_english(self, cost_guard):
        """测试英文 Token 估算"""
        # 纯英文
        text = "Hello, this is a test"
        tokens = cost_guard.estimate_tokens(text, is_chinese_heavy=False)
        # 21个字符 ≈ 5 tokens, 加上安全边际 1.2 = 6
        assert tokens >= 5

    def test_estimate_tokens_mixed(self, cost_guard):
        """测试混合语言 Token 估算"""
        text = "你好Hello世界World"
        tokens = cost_guard.estimate_tokens(text, is_chinese_heavy=True)
        assert tokens > 0

    def test_estimate_tokens_empty(self, cost_guard):
        """测试空文本 Token 估算"""
        tokens = cost_guard.estimate_tokens("")
        assert tokens == 0

    def test_estimate_tokens_long_text(self, cost_guard):
        """测试长文本 Token 估算"""
        text = "这是一个测试 " * 1000
        tokens = cost_guard.estimate_tokens(text)
        assert tokens > 1000

    # =============================================================================
    # 配额检查测试
    # =============================================================================

    @pytest.mark.asyncio
    async def test_check_quota_allowed(self, cost_guard, mock_redis):
        """测试配额允许通过"""
        # 模拟当前使用量为 0
        mock_redis.get = AsyncMock(return_value=b"0")

        result = await cost_guard.check_quota("user_123", 1000, check_only=True)

        assert result.allowed is True
        assert result.current_usage == 0
        assert result.remaining == 99_000
        assert result.percentage == 0.0

    @pytest.mark.asyncio
    async def test_check_quota_exceeded(self, cost_guard, mock_redis):
        """测试配额超限"""
        # 模拟已使用 99,000
        mock_redis.get = AsyncMock(return_value=b"99000")

        result = await cost_guard.check_quota("user_123", 2000, check_only=True)

        assert result.allowed is False
        assert result.current_usage == 99_000
        assert result.remaining == 1_000
        assert result.percentage == 0.99
        assert "配额不足" in result.message

    @pytest.mark.asyncio
    async def test_check_quota_exact_limit(self, cost_guard, mock_redis):
        """测试正好达到配额限制"""
        mock_redis.get = AsyncMock(return_value=b"99000")

        result = await cost_guard.check_quota("user_123", 1000, check_only=True)

        assert result.allowed is True
        assert result.remaining == 0

    @pytest.mark.asyncio
    async def test_check_quota_warning_threshold(self, cost_guard, mock_redis):
        """测试配额警告阈值"""
        # 使用量达到 80%
        mock_redis.get = AsyncMock(return_value=b"80000")

        result = await cost_guard.check_quota("user_123", 1000, check_only=True)

        assert result.allowed is True
        assert result.percentage == 0.8
        assert result.message is not None
        assert "警告" in result.message

    @pytest.mark.asyncio
    async def test_check_quota_with_actual_record(self, cost_guard, mock_redis):
        """测试实际记录配额使用"""
        mock_redis.get = AsyncMock(return_value=b"0")

        # 检查并记录
        result = await cost_guard.check_quota("user_123", 1000, check_only=False)

        # 验证 incrby 被调用
        mock_redis.incrby.assert_called_once()

    # =============================================================================
    # 使用记录测试
    # =============================================================================

    @pytest.mark.asyncio
    async def test_record_usage(self, cost_guard, mock_redis):
        """测试记录使用量"""
        await cost_guard.record_usage("user_123", 1000, model="gpt-4")

        # 验证管道操作被调用
        mock_redis.pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_usage_multiple_calls(self, cost_guard, mock_redis):
        """测试多次记录使用量"""
        await cost_guard.record_usage("user_123", 500, model="gpt-4")
        await cost_guard.record_usage("user_123", 700, model="gpt-4")

        # 应该调用两次管道
        assert mock_redis.pipeline.call_count == 2

    # =============================================================================
    # 用户统计测试
    # =============================================================================

    @pytest.mark.asyncio
    async def test_get_user_stats(self, cost_guard, mock_redis):
        """测试获取用户统计"""
        # 模拟 Redis 返回
        mock_pipeline = mock_redis.pipeline.return_value
        mock_pipeline.execute = AsyncMock(return_value=[5000, 15000, 50])

        stats = await cost_guard.get_user_stats("user_123")

        assert stats.user_id == "user_123"
        assert stats.today_usage == 5000
        assert stats.daily_limit == 100_000
        assert stats.weekly_usage == 15000
        assert stats.total_calls == 50
        assert stats.avg_tokens_per_call == 100.0  # 5000 / 50

    @pytest.mark.asyncio
    async def test_get_daily_stats(self, cost_guard, mock_redis):
        """测试获取每日统计 (API 格式)"""
        mock_pipeline = mock_redis.pipeline.return_value
        mock_pipeline.execute = AsyncMock(return_value=[50000, None, 100])

        stats = await cost_guard.get_daily_stats("user_123")

        assert stats["user_id"] == "user_123"
        assert stats["today_usage"] == 50000
        assert stats["daily_limit"] == 100_000
        assert stats["remaining"] == 50000
        assert stats["percentage"] == 50.0
        assert stats["total_calls"] == 100

    # =============================================================================
    # 紧急模式测试
    # =============================================================================

    @pytest.mark.asyncio
    async def test_emergency_mode_enable(self, cost_guard, mock_redis):
        """测试启用紧急模式"""
        await cost_guard.enable_emergency_mode(duration_minutes=60)

        # 验证设置紧急模式
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "llm_emergency_mode"
        assert call_args[0][2] == "1"

    @pytest.mark.asyncio
    async def test_emergency_mode_disable(self, cost_guard, mock_redis):
        """测试禁用紧急模式"""
        await cost_guard.disable_emergency_mode()

        # 验证删除紧急模式
        mock_redis.delete.assert_called_once_with("llm_emergency_mode")

    @pytest.mark.asyncio
    async def test_emergency_mode_quota_multiplier(self, cost_guard, mock_redis):
        """测试紧急模式下的配额倍增"""
        # 启用紧急模式
        mock_redis.get = AsyncMock(side_effect=lambda key: b"1" if "emergency" in key else b"50000")

        result = await cost_guard.check_quota("user_123", 100000, check_only=True)

        # 配额应该翻倍 (200,000)
        assert result.allowed is True
        assert result.limit == 200_000

    # =============================================================================
    # 断路器测试
    # =============================================================================

    @pytest.mark.asyncio
    async def test_protected_llm_call_success(self):
        """测试断路器 - 成功调用"""
        async def mock_llm_call():
            return "Success"

        result = await protected_llm_call(mock_llm_call)
        assert result == "Success"

    @pytest.mark.asyncio
    async def test_protected_llm_call_failure(self):
        """测试断路器 - 失败调用"""
        async def failing_llm_call():
            raise Exception("LLM Error")

        with pytest.raises(Exception, match="LLM Error"):
            await protected_llm_call(failing_llm_call)

    @pytest.mark.asyncio
    async def test_protected_llm_call_with_args(self):
        """测试断路器 - 带参数调用"""
        async def mock_llm_call(messages, model):
            return f"Called with {model}"

        result = await protected_llm_call(mock_llm_call, [{"role": "user", "content": "test"}], model="gpt-4")
        assert result == "Called with gpt-4"

    # =============================================================================
    # 边界情况测试
    # =============================================================================

    @pytest.mark.asyncio
    async def test_zero_token_request(self, cost_guard, mock_redis):
        """测试零 Token 请求"""
        mock_redis.get = AsyncMock(return_value=b"0")

        result = await cost_guard.check_quota("user_123", 0, check_only=True)

        assert result.allowed is True
        assert result.current_usage == 0

    @pytest.mark.asyncio
    async def test_negative_token_request(self, cost_guard):
        """测试负 Token 请求"""
        # 应该处理为 0
        tokens = cost_guard.estimate_tokens("")
        assert tokens == 0

    @pytest.mark.asyncio
    async def test_very_large_quota(self, cost_guard, mock_redis):
        """测试超大配额"""
        mock_redis.get = AsyncMock(return_value=b"0")

        # 100万 Token
        result = await cost_guard.check_quota("user_123", 1_000_000, check_only=True)

        assert result.allowed is False
        assert "需要 1,000,000" in result.message

    # =============================================================================
    # 并发测试
    # =============================================================================

    @pytest.mark.asyncio
    async def test_concurrent_quota_checks(self, cost_guard, mock_redis):
        """测试并发配额检查"""
        # 模拟并发场景
        async def check_quota(user_id, tokens):
            return await cost_guard.check_quota(user_id, tokens, check_only=True)

        # 同时检查多个用户
        results = await asyncio.gather(
            check_quota("user_1", 1000),
            check_quota("user_2", 2000),
            check_quota("user_3", 3000),
        )

        assert len(results) == 3
        assert all(r.allowed for r in results)

    # =============================================================================
    # 配额重置测试
    # =============================================================================

    @pytest.mark.asyncio
    async def test_daily_quota_reset(self, cost_guard, mock_redis):
        """测试每日配额重置"""
        # 第一天使用 80,000
        mock_redis.get = AsyncMock(return_value=b"80000")
        result1 = await cost_guard.check_quota("user_123", 30000, check_only=True)
        assert result1.allowed is False

        # 模拟第二天 (重置)
        mock_redis.get = AsyncMock(return_value=b"0")
        result2 = await cost_guard.check_quota("user_123", 30000, check_only=True)
        assert result2.allowed is True

    # =============================================================================
    # 成本估算测试
    # =============================================================================

    def test_cost_estimation_gpt4(self, cost_guard):
        """测试 GPT-4 成本估算"""
        # 1000 input tokens + 500 output tokens
        # Cost = (1000/1000 * $0.03) + (500/1000 * $0.06) = $0.03 + $0.03 = $0.06
        cost = cost_guard.estimate_and_record_cost(
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500,
            endpoint="chat"
        )
        assert cost == 0.06

    def test_cost_estimation_gpt35(self, cost_guard):
        """测试 GPT-3.5 成本估算"""
        # 1000 input + 500 output
        # Cost = (1000/1000 * $0.001) + (500/1000 * $0.002) = $0.001 + $0.001 = $0.002
        cost = cost_guard.estimate_and_record_cost(
            model="gpt-3.5-turbo",
            input_tokens=1000,
            output_tokens=500,
            endpoint="chat"
        )
        assert cost == 0.002

    def test_cost_estimation_embedding(self, cost_guard):
        """测试 Embedding 成本估算"""
        # Embedding 通常只按输入计费
        cost = cost_guard.estimate_and_record_cost(
            model="text-embedding-ada-002",
            input_tokens=1000,
            output_tokens=0,
            endpoint="embeddings"
        )
        assert cost == 0.0001

    def test_cost_estimation_unknown_model(self, cost_guard):
        """测试未知模型成本估算 (使用默认值)"""
        cost = cost_guard.estimate_and_record_cost(
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500,
            endpoint="chat"
        )
        # 默认: input $0.03, output $0.06
        assert cost == 0.06


class TestQuotaExceededError:
    """配额超限异常测试"""

    def test_exception_message(self):
        """测试异常消息"""
        error = QuotaExceededError("配额不足: 已使用 90,000/100,000")
        assert "配额不足" in str(error)

    def test_exception_type(self):
        """测试异常类型"""
        error = QuotaExceededError("test")
        assert isinstance(error, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
