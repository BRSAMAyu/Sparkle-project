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
from app.config import settings
from app.core.redis_utils import resolve_redis_password


class TestContextPruner:
    """ContextPruner 单元测试"""

    @pytest.fixture
    async def redis_client(self):
        """创建测试用的 Redis 客户端"""
        redis_url = "redis://localhost:6379/15"
        resolved_password, _ = resolve_redis_password(redis_url, None)
        client = redis.from_url(redis_url, decode_responses=False, password=resolved_password)
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
        """测试：中等历史走二层重要性压缩（C-06/RB-07：不静默丢帧、不触发总结）。

        V3-FIX-121：旧「滑窗截到最后 5 条」语义已废——importance_threshold =
        max(summary_threshold, 30)，8 条落在二层压缩带（5 < 8 ≤ 30），消息计数
        保持、超出 recent 窗的普通消息改写为低信号简述。
        """
        session_id = "test_session_window"

        # 准备 8 条历史（超过 max_history=5，未达 importance_threshold=30）
        history = [
            {"role": "user", "content": f"消息 {i}", "timestamp": 1000 + i}
            for i in range(8)
        ]

        for msg in history:
            await redis_client.rpush(f"chat:history:{session_id}", json.dumps(msg))

        result = await context_pruner.get_pruned_history(session_id, "user_123")

        # 验证：帧数保持（RB-07 不静默丢），summary 面为零
        assert result["original_count"] == 8
        assert result["pruned_count"] == len(result["messages"]) == 8
        assert result["summary_used"] is False
        assert result["summary"] is None

        # 最近窗（6 条）原文保留；更早的普通消息压缩为简述
        assert result["messages"][-1]["content"] == "消息 7"
        assert result["messages"][0]["content"].startswith("[user简述]")
        assert result["messages"][0]["compressed"] is True

    @pytest.mark.asyncio
    async def test_summary_trigger(self, context_pruner, redis_client):
        """测试：超阈值带（≤importance_threshold）二层压缩、不再推 LLM 总结队列。

        V3-FIX-121：C-06（960bc498）后 LLM 总结是可选档（ENABLE_LLM_SESSION_
        SUMMARY），pruner 不再向 queue:summarization 投递任务；summary_threshold=10
        经 max(·,30) 抬升后 15 条仍在二层压缩带。
        """
        session_id = "test_session_summary"

        # 准备 15 条历史
        history = [
            {"role": "user", "content": f"消息 {i}", "timestamp": 1000 + i}
            for i in range(15)
        ]

        for msg in history:
            await redis_client.rpush(f"chat:history:{session_id}", json.dumps(msg))

        result = await context_pruner.get_pruned_history(session_id, "user_123")

        # 验证：二层压缩带内计数保持、不触发总结
        assert result["original_count"] == 15
        assert result["pruned_count"] == len(result["messages"]) == 15
        assert result["summary_used"] is False

        # C-06：LLM 总结队列面已拆除
        queue_len = await redis_client.llen("queue:summarization")
        assert queue_len == 0

    @pytest.mark.asyncio
    async def test_summary_cache(self, context_pruner, redis_client, monkeypatch):
        """测试：LLM 同步总结缓存机制（ENABLE_LLM_SESSION_SUMMARY 可选档）。

        V3-FIX-121：缓存键演进为摘要内容 digest（summary:{sid}:{digest} +
        latest 指针），且仅 LLM 档读写——改以「首调生成并落缓存、次调命中缓存
        （LLM 恰被调一次）」钉缓存语义，历史须超 importance_threshold=30。
        """
        session_id = "test_session_cache"

        class _StubSummarizer:
            def __init__(self) -> None:
                self.calls = 0

            async def chat(self, messages, **kwargs):
                self.calls += 1
                return "测试总结：用户在验证总结缓存机制，这段文本长度超过下限。"

        stub = _StubSummarizer()

        async def _fake_resolver(*args, **kwargs):
            return stub

        monkeypatch.setattr(settings, "ENABLE_LLM_SESSION_SUMMARY", True, raising=False)
        monkeypatch.setattr(
            "app.services.llm_service.get_configured_llm_service_for_tier", _fake_resolver
        )

        # 准备 35 条历史（> importance_threshold=30，进入 LLM 总结档）
        history = [
            {"role": "user", "content": f"消息 {i}", "timestamp": 1000 + i}
            for i in range(35)
        ]

        for msg in history:
            await redis_client.rpush(f"chat:history:{session_id}", json.dumps(msg))

        # 第一次调用 - 生成总结并写缓存
        result1 = await context_pruner.get_pruned_history(session_id, "user_123")
        assert result1["summary_used"] is True
        assert result1["summary"] == "测试总结：用户在验证总结缓存机制，这段文本长度超过下限。"
        assert stub.calls == 1
        latest = await redis_client.get(f"summary:{session_id}:latest")
        assert latest is not None

        # 第二次调用 - 命中摘要缓存，LLM 不再被调用
        result2 = await context_pruner.get_pruned_history(session_id, "user_123")
        assert result2["summary"] == result1["summary"]
        assert result2["summary_used"] is True
        assert stub.calls == 1

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
        redis_url = "redis://localhost:6379/15"
        resolved_password, _ = resolve_redis_password(redis_url, None)
        client = redis.from_url(redis_url, decode_responses=False, password=resolved_password)
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

        # V3-FIX-121：worker 的 LLM 面演进为 llm_fallback_utils.summarization_llm.call
        # （模块级 llm_service 已不存在）；摘要 ≥10 字才会入缓存，桩文本加长。
        summary_text = "这是一个总结，包含足够的长度用于缓存。"
        with patch(
            "app.services.llm_fallback_utils.summarization_llm"
        ) as mock_llm:
            mock_llm.call = AsyncMock(return_value=summary_text)

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
                # V3-FIX-121：processed_count 只在 _process_batch 循环内递增，
                # 直调 _process_task 不计数——删除断言对齐计数语义。

                # 验证总结已缓存
                summary = await redis_client.get("summary:test_worker_session")
                assert summary is not None
                assert summary.decode("utf-8") == summary_text


class TestOrchestratorIntegration:
    """Orchestrator 集成测试"""

    @pytest.fixture
    async def redis_client(self):
        """创建测试用的 Redis 客户端"""
        redis_url = "redis://localhost:6379/15"
        resolved_password, _ = resolve_redis_password(redis_url, None)
        client = redis.from_url(redis_url, decode_responses=False, password=resolved_password)
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
        """测试：Orchestrator 构建对话上下文（C-06 二层压缩带内计数保持）。

        V3-FIX-121：orchestrator 内建 pruner 为默认参数（max_history=10、
        importance_threshold=max(20,30)=30），12 条落在二层压缩带——不静默丢帧、
        不触发总结；旧「截到 5 条 + LLM 总结」语义已废（C-06 960bc498）。
        """
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

        # 验证：二层压缩带——帧数保持、总结面为零
        assert context["original_count"] == 12
        assert context["pruned_count"] == len(context["messages"]) == 12
        assert context["summary_used"] is False
        assert context["summary"] is None

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
        redis_url = "redis://localhost:6379/15"
        resolved_password, _ = resolve_redis_password(redis_url, None)
        client = redis.from_url(redis_url, password=resolved_password)
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
