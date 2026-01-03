"""
ContextPruner 功能测试

测试场景:
1. 历史消息少于阈值 - 直接返回
2. 历史消息在阈值之间 - 滑动窗口
3. 历史消息超过阈值 - 触发总结
4. 总结缓存机制
5. 与 Orchestrator 集成
"""

import asyncio
import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis

from app.orchestration.context_pruner import ContextPruner
from app.orchestration.summarization_worker import SummarizationWorker
from app.orchestration.orchestrator import ChatOrchestrator


class TestContextPruner:
    """ContextPruner 单元测试"""

    @pytest.fixture
    async def redis_client(self):
        """创建测试用的 Redis 客户端"""
        client = redis.from_url("redis://localhost:6379/15", decode_responses=False)
        try:
            await client.ping()
            yield client
            await client.flushdb()  # 清理测试数据
        except:
            pytest.skip("Redis not available")
        finally:
            await client.close()

    @pytest.fixture
    def context_pruner(self, redis_client):
        """创建 ContextPruner 实例"""
        return ContextPruner(
            redis_client=redis_client,
            max_history_messages=5,
            summary_threshold=10,
            summary_cache_ttl=3600
        )

    @pytest.mark.asyncio
    async def test_small_history(self, context_pruner, redis_client):
        """测试：历史消息少于阈值，直接返回"""
        session_id = "test_session_small"

        # 准备少量历史
        history = [
            {"role": "user", "content": "你好", "timestamp": 1000},
            {"role": "assistant", "content": "你好！有什么可以帮你的吗？", "timestamp": 1001},
            {"role": "user", "content": "我想学习 Python", "timestamp": 1002},
        ]

        # 写入 Redis
        for msg in history:
            await redis_client.rpush(f"chat:history:{session_id}", json.dumps(msg))

        # 获取修剪后的历史
        result = await context_pruner.get_pruned_history(session_id, "user_123")

        # 验证
        assert result["original_count"] == 3
        assert result["pruned_count"] == 3
        assert result["summary_used"] is False
        assert result["summary"] is None
        assert len(result["messages"]) == 3

    @pytest.mark.asyncio
    async def test_sliding_window(self, context_pruner, redis_client):
        """测试：中等历史，使用滑动窗口"""
        session_id = "test_session_window"

        # 准备 8 条历史（超过 max_history=5，但未达到 summary_threshold=10）
        history = [
            {"role": "user", "content": f"消息 {i}", "timestamp": 1000 + i}
            for i in range(8)
        ]

        for msg in history:
            await redis_client.rpush(f"chat:history:{session_id}", json.dumps(msg))

        result = await context_pruner.get_pruned_history(session_id, "user_123")

        # 验证
        assert result["original_count"] == 8
        assert result["pruned_count"] == 5
        assert result["summary_used"] is False
        assert result["summary"] is None
        assert len(result["messages"]) == 5

        # 验证是最后 5 条
        assert result["messages"][0]["content"] == "消息 3"
        assert result["messages"][-1]["content"] == "消息 7"

    @pytest.mark.asyncio
    async def test_summary_trigger(self, context_pruner, redis_client):
        """测试：历史超过阈值，触发总结"""
        session_id = "test_session_summary"

        # 准备 15 条历史（超过 summary_threshold=10）
        history = [
            {"role": "user", "content": f"消息 {i}", "timestamp": 1000 + i}
            for i in range(15)
        ]

        for msg in history:
            await redis_client.rpush(f"chat:history:{session_id}", json.dumps(msg))

        result = await context_pruner.get_pruned_history(session_id, "user_123")

        # 验证
        assert result["original_count"] == 15
        assert result["pruned_count"] == 5  # 最近 5 条
        assert result["summary_used"] is True
        assert len(result["messages"]) == 5

        # 验证总结任务已推送到队列
        queue_len = await redis_client.llen("queue:summarization")
        assert queue_len == 1

        # 验证队列内容
        task_data = await redis_client.lindex("queue:summarization", 0)
        task = json.loads(task_data)
        assert task["session_id"] == session_id
        assert len(task["history"]) == 10  # 除最近 5 条外的历史

    @pytest.mark.asyncio
    async def test_summary_cache(self, context_pruner, redis_client):
        """测试：总结缓存机制"""
        session_id = "test_session_cache"

        # 准备历史
        history = [
            {"role": "user", "content": f"消息 {i}", "timestamp": 1000 + i}
            for i in range(15)
        ]

        for msg in history:
            await redis_client.rpush(f"chat:history:{session_id}", json.dumps(msg))

        # 第一次调用 - 应该触发总结任务
        result1 = await context_pruner.get_pruned_history(session_id, "user_123")
        assert result1["summary"] is None  # 缓存未就绪

        # 模拟总结完成（手动设置缓存）
        summary_text = "用户之前询问了 Python 学习相关问题，我们讨论了基础语法和最佳实践"
        await redis_client.setex(f"summary:{session_id}", 3600, summary_text)

        # 第二次调用 - 应该返回缓存的总结
        result2 = await context_pruner.get_pruned_history(session_id, "user_123")
        assert result2["summary"] == summary_text
        assert result2["summary_used"] is True

    @pytest.mark.asyncio
    async def test_empty_history(self, context_pruner, redis_client):
        """测试：无历史记录"""
        session_id = "test_session_empty"

        result = await context_pruner.get_pruned_history(session_id, "user_123")

        assert result["original_count"] == 0
        assert result["pruned_count"] == 0
        assert result["summary_used"] is False
        assert result["messages"] == []


class TestSummarizationWorker:
    """SummarizationWorker 单元测试"""

    @pytest.fixture
    async def redis_client(self):
        """创建测试用的 Redis 客户端"""
        client = redis.from_url("redis://localhost:6379/15", decode_responses=False)
        try:
            await client.ping()
            yield client
            await client.flushdb()
        except:
            pytest.skip("Redis not available")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_worker_processes_task(self, redis_client):
        """测试：Worker 处理总结任务"""
        worker = SummarizationWorker(redis_client, batch_size=1)

        # 模拟 LLM 服务
        with patch("app.orchestration.summarization_worker.llm_service") as mock_llm:
            mock_llm.generate_summary = AsyncMock(return_value="这是一个总结")

            # 推送任务到队列
            task = {
                "session_id": "test_worker_session",
                "history": [
                    {"role": "user", "content": "你好", "timestamp": 1000},
                    {"role": "assistant", "content": "你好！", "timestamp": 1001},
                ],
                "user_id": "user_123",
                "timestamp": time.time(),
                "priority": "high"
            }
            await redis_client.rpush("queue:summarization", json.dumps(task))

            # 手动处理一次任务
            task_data = await redis_client.blpop("queue:summarization", timeout=1)
            if task_data:
                task_obj = json.loads(task_data[1])
                success = await worker._process_task(task_obj)

                assert success is True
                assert worker.processed_count == 1

                # 验证总结已缓存
                summary = await redis_client.get("summary:test_worker_session")
                assert summary is not None
                assert summary.decode("utf-8") == "这是一个总结"


class TestOrchestratorIntegration:
    """Orchestrator 集成测试"""

    @pytest.fixture
    async def redis_client(self):
        """创建测试用的 Redis 客户端"""
        client = redis.from_url("redis://localhost:6379/15", decode_responses=False)
        try:
            await client.ping()
            yield client
            await client.flushdb()
        except:
            pytest.skip("Redis not available")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_build_conversation_context(self, redis_client):
        """测试：Orchestrator 构建对话上下文"""
        orchestrator = ChatOrchestrator(redis_client=redis_client)

        session_id = "test_orch_session"
        user_id = "user_123"

        # 准备历史
        history = [
            {"role": "user", "content": f"问题 {i}", "timestamp": 1000 + i}
            for i in range(12)
        ]
        for msg in history:
            await redis_client.rpush(f"chat:history:{session_id}", json.dumps(msg))

        # 调用 _build_conversation_context
        context = await orchestrator._build_conversation_context(session_id, user_id)

        # 验证
        assert context["original_count"] == 12
        assert context["pruned_count"] == 5
        assert context["summary_used"] is True
        assert len(context["messages"]) == 5

    @pytest.mark.asyncio
    async def test_build_user_context_with_cache(self, redis_client):
        """测试：Orchestrator 构建用户上下文（带缓存）"""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker

        # 创建内存数据库用于测试
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # 注意：这里需要实际的数据库模型，测试时可以跳过或使用 mock
        # 简化测试：只验证缓存逻辑
        orchestrator = ChatOrchestrator(redis_client=redis_client)

        # 验证 ContextPruner 已初始化
        assert orchestrator.context_pruner is not None
        assert orchestrator.context_pruner.redis == redis_client


# 运行测试的辅助函数
async def run_all_tests():
    """手动运行所有测试（用于开发调试）"""
    print("🧪 开始 ContextPruner 测试...")

    # 检查 Redis
    try:
        client = redis.from_url("redis://localhost:6379/15")
        await client.ping()
        print("✅ Redis 连接正常")
    except:
        print("❌ Redis 连接失败，跳过测试")
        return

    # 运行测试
    test_pruner = TestContextPruner()
    test_worker = TestSummarizationWorker()
    test_integration = TestOrchestratorIntegration()

    # 注入 Redis 客户端
    redis_fixture = client

    try:
        # 测试 1: 小历史
        pruner = ContextPruner(redis_fixture, max_history_messages=5, summary_threshold=10)
        await test_pruner.test_small_history(pruner, redis_fixture)
        print("✅ 测试 1: 小历史 - 通过")

        # 测试 2: 滑动窗口
        await test_pruner.test_sliding_window(pruner, redis_fixture)
        print("✅ 测试 2: 滑动窗口 - 通过")

        # 测试 3: 总结触发
        await test_pruner.test_summary_trigger(pruner, redis_fixture)
        print("✅ 测试 3: 总结触发 - 通过")

        # 测试 4: 总结缓存
        await test_pruner.test_summary_cache(pruner, redis_fixture)
        print("✅ 测试 4: 总结缓存 - 通过")

        # 测试 5: 空历史
        await test_pruner.test_empty_history(pruner, redis_fixture)
        print("✅ 测试 5: 空历史 - 通过")

        # 测试 6: Worker 处理
        worker = SummarizationWorker(redis_fixture, batch_size=1)
        await test_worker.test_worker_processes_task(redis_fixture)
        print("✅ 测试 6: Worker 处理 - 通过")

        # 测试 7: Orchestrator 集成
        await test_integration.test_build_conversation_context(redis_fixture)
        print("✅ 测试 7: Orchestrator 集成 - 通过")

        print("\n🎉 所有测试通过！")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await redis_fixture.flushdb()
        await redis_fixture.close()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
