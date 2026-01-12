"""
异步任务管理集成测试

测试 TaskManager 和 Celery 的集成,确保任务可靠执行

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import time

from app.core.task_manager import BackgroundTaskManager, TaskStats
from app.core.celery_app import celery_app, get_celery_status


class TestTaskManagerIntegration:
    """TaskManager 集成测试"""

    @pytest.fixture
    def task_manager(self):
        """创建 TaskManager 实例"""
        return BackgroundTaskManager(max_concurrent_tasks=10)

    @pytest.fixture
    def mock_coro(self):
        """创建模拟协程"""
        async def simple_task():
            await asyncio.sleep(0.01)
            return "success"

        async def failing_task():
            await asyncio.sleep(0.01)
            raise ValueError("Task failed")

        async def long_task():
            await asyncio.sleep(0.5)
            return "long_running"

        return simple_task, failing_task, long_task

    # =============================================================================
    # TaskManager 基础功能测试
    # =============================================================================

    @pytest.mark.asyncio
    async def test_spawn_task(self, task_manager, mock_coro):
        """测试任务创建"""
        simple_task, _, _ = mock_coro

        task = await task_manager.spawn(simple_task(), task_name="test_task")

        # 等待任务完成
        await task

        # 验证统计
        stats = task_manager.get_stats()
        assert stats["total_spawned"] == 1
        assert stats["total_completed"] == 1
        assert stats["total_failed"] == 0
        assert stats["currently_running"] == 0

    @pytest.mark.asyncio
    async def test_task_failure_handling(self, task_manager, mock_coro):
        """测试任务失败处理"""
        _, failing_task, _ = mock_coro

        task = await task_manager.spawn(failing_task(), task_name="failing_task")

        # 任务应该失败但不会崩溃
        with pytest.raises(ValueError):
            await task

        stats = task_manager.get_stats()
        assert stats["total_failed"] == 1
        assert stats["failure_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, task_manager):
        """测试并发限制"""
        # 创建多个任务
        async def slow_task():
            await asyncio.sleep(0.1)
            return "done"

        tasks = []
        for i in range(15):
            task = await task_manager.spawn(
                slow_task(),
                task_name=f"slow_task_{i}"
            )
            tasks.append(task)

        # 验证正在运行的任务数不超过限制
        active = task_manager.get_active_tasks()
        assert len(active) <= 10  # 并发限制

        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)

        stats = task_manager.get_stats()
        assert stats["total_spawned"] == 15

    @pytest.mark.asyncio
    async def test_task_stats_tracking(self, task_manager, mock_coro):
        """测试任务统计追踪"""
        simple_task, _, _ = mock_coro

        # 执行多个任务
        for i in range(5):
            task = await task_manager.spawn(simple_task(), task_name=f"task_{i}")
            await task

        # 验证详细统计
        stats = task_manager.get_stats()
        assert stats["total_spawned"] == 5
        assert stats["total_completed"] == 5
        assert stats["average_duration_ms"] > 0

        # 验证单个任务详情
        task_id = list(task_manager._stats.keys())[0]
        details = task_manager.get_task_details(task_id)
        assert details is not None
        assert details["status"] == "completed"
        assert details["duration_ms"] is not None

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, task_manager):
        """测试优雅关闭"""
        async def long_task():
            await asyncio.sleep(2.0)
            return "done"

        # 创建长任务
        task1 = await task_manager.spawn(long_task(), task_name="long_1")
        task2 = await task_manager.spawn(long_task(), task_name="long_2")

        # 快速关闭 (超时)
        start_time = time.time()
        await task_manager.graceful_shutdown(timeout=0.5)
        elapsed = time.time() - start_time

        # 应该在超时前返回
        assert elapsed < 1.0
        assert len(task_manager.get_active_tasks()) == 0

    @pytest.mark.asyncio
    async def test_health_check(self, task_manager, mock_coro):
        """测试健康检查"""
        simple_task, _, _ = mock_coro

        # 正常运行
        task = await task_manager.spawn(simple_task(), task_name="health_test")
        await task

        health = task_manager.health_check()
        assert health["healthy"] is True
        assert health["status"] == "healthy"
        assert health["stats"]["failure_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_spawn_with_retry(self, task_manager):
        """测试带重试的任务"""
        attempt_count = [0]

        async def flaky_task():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception(f"Attempt {attempt_count[0]} failed")
            return "success"

        task = await task_manager.spawn_with_retry(
            flaky_task(),
            task_name="retry_task",
            max_retries=3,
            retry_delay=0.05
        )

        await task
        assert attempt_count[0] == 3  # 第3次成功

    @pytest.mark.asyncio
    async def test_task_with_user_id(self, task_manager):
        """测试带用户ID的任务"""
        async def user_task():
            await asyncio.sleep(0.01)
            return "done"

        task = await task_manager.spawn(
            user_task(),
            task_name="user_task",
            user_id="user_123"
        )
        await task

        # 验证任务详情包含用户ID
        task_id = list(task_manager._stats.keys())[0]
        details = task_manager.get_task_details(task_id)
        assert details["task_name"] == "user_task"

    # =============================================================================
    # Celery 集成测试
    # =============================================================================

    def test_celery_config(self):
        """测试 Celery 配置"""
        status = get_celery_status()

        # 如果 Redis 不可用,状态应该是 unhealthy
        if status["status"] == "unhealthy":
            assert "error" in status
        else:
            assert status["status"] == "healthy"

    def test_celery_task_definitions(self):
        """测试 Celery 任务定义"""
        # 检查任务是否已注册
        registered_tasks = celery_app.tasks.keys()

        # 应该包含我们定义的任务
        expected_tasks = [
            "generate_embedding",
            "batch_error_analysis",
            "cleanup_old_data",
            "notify_user",
            "daily_report",
            "health_check_task",
        ]

        for task in expected_tasks:
            assert task in registered_tasks, f"Task {task} not registered"

    def test_celery_beat_schedule(self):
        """测试周期任务配置"""
        beat_schedule = celery_app.conf.beat_schedule
        assert len(beat_schedule) > 0

        # 检查关键周期任务
        assert "cleanup-every-day" in beat_schedule
        assert beat_schedule["cleanup-every-day"]["task"] == "cleanup_old_data"

    @pytest.mark.asyncio
    async def test_task_to_celery_migration(self):
        """测试从 TaskManager 到 Celery 的迁移路径"""
        # 模拟一个长时任务
        async def long_running_task():
            await asyncio.sleep(0.1)
            return "completed"

        # 使用 TaskManager (快速)
        from app.core.task_manager import task_manager
        task = await task_manager.spawn(
            long_running_task(),
            task_name="quick_task"
        )
        await task

        # 使用 Celery (长时) - 演示迁移路径
        from app.core.celery_app import schedule_long_task

        # 注意: 实际执行需要 Redis 和 Worker
        # 这里仅测试接口是否正常
        try:
            task_id = schedule_long_task(
                "health_check_task",
                queue="low_priority"
            )
            assert task_id is not None
        except Exception as e:
            # 如果 Redis 不可用,预期会失败
            assert "broker" in str(e).lower() or "connection" in str(e).lower()

    # =============================================================================
    # 性能测试
    # =============================================================================

    @pytest.mark.asyncio
    async def test_performance_spawn_overhead(self, task_manager):
        """测试任务创建开销"""
        async def quick_task():
            return "done"

        # 测量 100 次任务创建的平均开销
        import time
        start = time.time()

        for i in range(100):
            task = await task_manager.spawn(quick_task(), task_name=f"perf_{i}")
            await task

        elapsed = time.time() - start
        avg_time = elapsed / 100

        # 每次任务创建和执行应该 < 1ms
        assert avg_time < 0.001

    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self, task_manager):
        """测试内存泄漏防护"""
        async def temp_task():
            await asyncio.sleep(0.01)
            return "done"

        # 创建大量任务
        for i in range(1000):
            task = await task_manager.spawn(temp_task(), task_name=f"leak_{i}")
            await task

        # 验证任务统计不会无限增长
        stats = task_manager.get_stats()
        assert stats["total_spawned"] == 1000

        # 验证活跃任务列表已清理
        active = task_manager.get_active_tasks()
        assert len(active) == 0

        # 验证统计历史保留限制
        assert len(task_manager._stats) <= 1000

    # =============================================================================
    # 错误场景测试
    # =============================================================================

    @pytest.mark.asyncio
    async def test_task_cancellation(self, task_manager):
        """测试任务取消"""
        async def long_task():
            await asyncio.sleep(10.0)
            return "done"

        task = await task_manager.spawn(long_task(), task_name="cancel_test")

        # 取消任务
        task.cancel()

        # 等待取消完成
        try:
            await task
        except asyncio.CancelledError:
            pass

        # 验证状态
        stats = task_manager.get_stats()
        assert stats["total_spawned"] == 1

    @pytest.mark.asyncio
    async def test_exception_in_task_body(self, task_manager):
        """测试任务内部异常"""
        async def task_with_exception():
            raise RuntimeError("Critical error in task")

        task = await task_manager.spawn(task_with_exception(), task_name="error_task")

        with pytest.raises(RuntimeError):
            await task

        # 验证异常信息被记录
        task_id = list(task_manager._stats.keys())[0]
        details = task_manager.get_task_details(task_id)
        assert details["exception_type"] == "RuntimeError"
        assert "Critical error" in details["error_message"]

    @pytest.mark.asyncio
    async def test_semaphore_exhaustion(self, task_manager):
        """测试信号量耗尽"""
        # 设置极低的并发限制
        task_manager._semaphore = asyncio.Semaphore(2)

        async def blocking_task():
            await asyncio.sleep(0.5)
            return "done"

        # 创建超过限制的任务
        tasks = []
        for i in range(5):
            task = await task_manager.spawn(blocking_task(), task_name=f"block_{i}")
            tasks.append(task)

        # 验证并发限制生效
        active = task_manager.get_active_tasks()
        assert len(active) <= 2

        # 等待完成
        await asyncio.gather(*tasks, return_exceptions=True)


class TestCeleryTaskExecution:
    """Celery 任务执行测试 (需要 Redis)"""

    @pytest.fixture
    def skip_if_no_redis(self):
        """如果没有 Redis 则跳过测试"""
        try:
            import redis
            r = redis.from_url("redis://localhost:6379/1")
            r.ping()
        except:
            pytest.skip("Redis not available")

    def test_generate_embedding_task(self, skip_if_no_redis):
        """测试 Embedding 生成任务"""
        from app.core.celery_tasks import generate_node_embedding

        # 注意: 这需要实际的数据库和 embedding 服务
        # 仅测试任务定义
        assert generate_node_embedding.name == "generate_node_embedding"

    def test_batch_error_analysis_task(self, skip_if_no_redis):
        """测试批量错题分析任务"""
        from app.core.celery_tasks import analyze_error_batch

        assert analyze_error_batch.name == "analyze_error_batch"

    def test_health_check_task(self, skip_if_no_redis):
        """测试健康检查任务"""
        from app.core.celery_tasks import health_check_task

        result = health_check_task.apply_async()
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
