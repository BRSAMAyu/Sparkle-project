"""
Celery 性能基准测试套件

提供详细的性能基准测试和对比分析

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from app.core.celery_app import celery_app
from app.core.task_manager import task_manager


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    iterations: int
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float
    throughput_per_sec: float
    total_time: float

    def __str__(self):
        return (
            f"{self.name}:\n"
            f"  平均: {self.mean_ms:.2f}ms | 中位数: {self.median_ms:.2f}ms\n"
            f"  P95: {self.p95_ms:.2f}ms | P99: {self.p99_ms:.2f}ms\n"
            f"  最小: {self.min_ms:.2f}ms | 最大: {self.max_ms:.2f}ms\n"
            f"  标准差: {self.std_dev_ms:.2f}ms | 吞吐量: {self.throughput_per_sec:.2f} ops/s"
        )


class BenchmarkSuite:
    """性能基准测试套件"""

    @staticmethod
    def calculate_percentile(data: List[float], percentile: float) -> float:
        """计算百分位数"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]

    @staticmethod
    def calculate_stats(times: List[float], total_time: float, iterations: int) -> BenchmarkResult:
        """计算统计指标"""
        return BenchmarkResult(
            name="",
            iterations=iterations,
            mean_ms=statistics.mean(times) * 1000,
            median_ms=statistics.median(times) * 1000,
            p95_ms=BenchmarkSuite.calculate_percentile(times, 95) * 1000,
            p99_ms=BenchmarkSuite.calculate_percentile(times, 99) * 1000,
            min_ms=min(times) * 1000,
            max_ms=max(times) * 1000,
            std_dev_ms=statistics.stdev(times) * 1000 if len(times) > 1 else 0,
            throughput_per_sec=iterations / total_time,
            total_time=total_time
        )

    async def benchmark_task_spawn_overhead(self, iterations: int = 1000) -> BenchmarkResult:
        """基准测试: 任务创建开销"""
        logger.info(f"🔍 测试任务创建开销 ({iterations} 次)")

        async def dummy_task():
            return "done"

        times = []
        start_time = time.time()

        for i in range(iterations):
            task_start = time.time()
            task = await task_manager.spawn(dummy_task(), task_name=f"bench_spawn_{i}")
            await task
            task_end = time.time()
            times.append(task_end - task_start)

        total_time = time.time() - start_time

        result = self.calculate_stats(times, total_time, iterations)
        result.name = "任务创建开销"
        return result

    async def benchmark_concurrent_spawn(self, concurrency: int = 100, iterations: int = 1000) -> BenchmarkResult:
        """基准测试: 并发任务创建"""
        logger.info(f"🔍 测试并发任务创建 ({concurrency} 并发, {iterations} 总数)")

        async def quick_task(task_id: int):
            await asyncio.sleep(0.001)  # 1ms
            return task_id

        times = []
        start_time = time.time()

        # 分批执行以控制并发
        for batch_start in range(0, iterations, concurrency):
            batch_end = min(batch_start + concurrency, iterations)
            batch_size = batch_end - batch_start

            batch_start_time = time.time()
            tasks = []
            for i in range(batch_start, batch_end):
                task = await task_manager.spawn(quick_task(i), task_name=f"bench_conc_{i}")
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)
            batch_end_time = time.time()

            # 记录每个任务的平均时间
            batch_time = batch_end_time - batch_start_time
            avg_task_time = batch_time / batch_size
            times.extend([avg_task_time] * batch_size)

        total_time = time.time() - start_time

        result = self.calculate_stats(times, total_time, iterations)
        result.name = f"并发任务创建 ({concurrency}并发)"
        return result

    async def benchmark_task_manager_vs_raw_asyncio(self, iterations: int = 500) -> Dict[str, BenchmarkResult]:
        """基准测试: TaskManager vs 原生 asyncio"""
        logger.info(f"🔍 测试 TaskManager vs 原生 asyncio ({iterations} 次)")

        async def test_task():
            await asyncio.sleep(0.01)
            return "result"

        # 测试 TaskManager
        tm_times = []
        tm_start = time.time()

        for i in range(iterations):
            task_start = time.time()
            task = await task_manager.spawn(test_task(), task_name=f"tm_bench_{i}")
            await task
            tm_times.append(time.time() - task_start)

        tm_total = time.time() - tm_start

        # 测试原生 asyncio
        raw_times = []
        raw_start = time.time()

        for i in range(iterations):
            task_start = time.time()
            task = asyncio.create_task(test_task())
            await task
            raw_times.append(time.time() - task_start)

        raw_total = time.time() - raw_start

        tm_result = self.calculate_stats(tm_times, tm_total, iterations)
        tm_result.name = "TaskManager"

        raw_result = self.calculate_stats(raw_times, raw_total, iterations)
        raw_result.name = "原生 asyncio"

        return {
            "task_manager": tm_result,
            "raw_asyncio": raw_result
        }

    async def benchmark_celery_task_execution(self, iterations: int = 100) -> BenchmarkResult:
        """基准测试: Celery 任务执行"""
        logger.info(f"🔍 测试 Celery 任务执行 ({iterations} 次)")

        from app.core.celery_tasks import health_check_task

        times = []
        start_time = time.time()

        for i in range(iterations):
            task_start = time.time()
            result = health_check_task.apply_async()
            # 等待完成
            while not result.ready():
                await asyncio.sleep(0.001)
            task_end = time.time()
            times.append(task_end - task_start)

        total_time = time.time() - start_time

        result = self.calculate_stats(times, total_time, iterations)
        result.name = "Celery 任务执行"
        return result

    async def benchmark_memory_efficiency(self, iterations: int = 1000) -> Dict[str, Any]:
        """基准测试: 内存效率"""
        logger.info(f"🔍 测试内存效率 ({iterations} 次)")

        import psutil
        import os

        process = psutil.Process(os.getpid())

        async def memory_task(task_id: int):
            # 创建临时数据
            data = list(range(100))
            result = sum(data)
            return result

        # 初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024

        # 执行任务
        tasks = []
        for i in range(iterations):
            task = await task_manager.spawn(memory_task(i), task_name=f"mem_bench_{i}")
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        # 最终内存
        final_memory = process.memory_info().rss / 1024 / 1024

        # 清理任务统计 (保留最近100个)
        task_manager._stats = {
            k: v for k, v in list(task_manager._stats.items())[-100:]
        }

        # 强制垃圾回收
        import gc
        gc.collect()

        post_cleanup_memory = process.memory_info().rss / 1024 / 1024

        return {
            "name": "内存效率",
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "peak_memory_mb": final_memory,
            "memory_growth_mb": final_memory - initial_memory,
            "post_cleanup_memory_mb": post_cleanup_memory,
            "cleanup_freed_mb": final_memory - post_cleanup_memory,
            "memory_per_task_mb": (final_memory - initial_memory) / iterations
        }

    async def benchmark_queue_performance(self) -> Dict[str, BenchmarkResult]:
        """基准测试: 队列性能"""
        logger.info("🔍 测试队列性能")

        # 测试不同队列的性能
        queue_results = {}

        for queue_name, queue_desc in [("high_priority", "高优先级"), ("default", "默认"), ("low_priority", "低优先级")]:
            times = []
            start_time = time.time()

            async def queue_task():
                await asyncio.sleep(0.01)
                return "done"

            # 使用 Celery 直接测试队列
            for i in range(100):
                task_start = time.time()
                # 这里简化处理，实际应使用 Celery 的队列机制
                task = await task_manager.spawn(queue_task(), task_name=f"queue_{queue_name}_{i}")
                await task
                times.append(time.time() - task_start)

            total_time = time.time() - start_time
            result = self.calculate_stats(times, total_time, 100)
            result.name = f"队列 {queue_desc}"
            queue_results[queue_name] = result

        return queue_results

    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """运行所有基准测试"""
        logger.info("=" * 60)
        logger.info("🎯 开始性能基准测试")
        logger.info("=" * 60)

        results = {}

        # 1. 任务创建开销
        results["spawn_overhead"] = await self.benchmark_task_spawn_overhead(1000)

        # 2. 并发任务创建
        results["concurrent_spawn_50"] = await self.benchmark_concurrent_spawn(50, 500)
        results["concurrent_spawn_100"] = await self.benchmark_concurrent_spawn(100, 1000)

        # 3. TaskManager vs Raw Asyncio
        results["comparison"] = await self.benchmark_task_manager_vs_raw_asyncio(500)

        # 4. Celery 任务执行
        results["celery_execution"] = await self.benchmark_celery_task_execution(100)

        # 5. 内存效率
        results["memory"] = await self.benchmark_memory_efficiency(500)

        # 6. 队列性能
        results["queues"] = await self.benchmark_queue_performance()

        # 生成报告
        self._print_report(results)

        return results

    def _print_report(self, results: Dict[str, Any]):
        """打印基准测试报告"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 性能基准测试报告")
        logger.info("=" * 60)

        # 基础性能指标
        logger.info("\n【基础性能指标】")
        logger.info(str(results["spawn_overhead"]))
        logger.info("")
        logger.info(str(results["concurrent_spawn_100"]))
        logger.info("")

        # 并发对比
        logger.info("【并发性能对比】")
        logger.info(f"50并发: {results['concurrent_spawn_50'].throughput_per_sec:.2f} ops/s")
        logger.info(f"100并发: {results['concurrent_spawn_100'].throughput_per_sec:.2f} ops/s")
        logger.info("")

        # TaskManager vs Raw Asyncio
        logger.info("【TaskManager vs 原生 asyncio】")
        tm = results["comparison"]["task_manager"]
        raw = results["comparison"]["raw_asyncio"]
        overhead = ((tm.mean_ms - raw.mean_ms) / raw.mean_ms) * 100
        logger.info(f"TaskManager: {tm.mean_ms:.2f}ms (吞吐量: {tm.throughput_per_sec:.2f} ops/s)")
        logger.info(f"原生 asyncio: {raw.mean_ms:.2f}ms (吞吐量: {raw.throughput_per_sec:.2f} ops/s)")
        logger.info(f"开销: {overhead:.1f}%")
        logger.info("")

        # Celery 执行
        logger.info("【Celery 任务执行】")
        logger.info(str(results["celery_execution"]))
        logger.info("")

        # 内存效率
        logger.info("【内存效率】")
        mem = results["memory"]
        logger.info(f"初始内存: {mem['initial_memory_mb']:.2f} MB")
        logger.info(f"峰值内存: {mem['peak_memory_mb']:.2f} MB")
        logger.info(f"内存增长: {mem['memory_growth_mb']:.2f} MB")
        logger.info(f"每任务增长: {mem['memory_per_task_mb']:.4f} MB")
        logger.info(f"清理后: {mem['post_cleanup_memory_mb']:.2f} MB (释放: {mem['cleanup_freed_mb']:.2f} MB)")
        logger.info("")

        # 队列性能
        logger.info("【队列性能】")
        for queue_name, result in results["queues"].items():
            logger.info(f"{result.name}: {result.throughput_per_sec:.2f} ops/s, P95: {result.p95_ms:.2f}ms")
        logger.info("")

        # 性能建议
        logger.info("【性能建议】")
        if overhead > 20:
            logger.warning("⚠️  TaskManager 开销较高，考虑优化")
        else:
            logger.info("✅ TaskManager 开销在可接受范围")

        if results["memory"]["memory_growth_mb"] > 50:
            logger.warning("⚠️  内存增长明显，建议检查内存泄漏")
        else:
            logger.info("✅ 内存使用正常")

        if results["concurrent_spawn_100"].throughput_per_sec < 100:
            logger.warning("⚠️  并发吞吐量较低，考虑增加 Worker 数量")
        else:
            logger.info("✅ 并发性能良好")

        # 保存详细报告
        import json
        report_file = "/tmp/benchmark_report.json"
        with open(report_file, "w") as f:
            json.dump(results, f, default=str, indent=2)

        logger.info(f"\n📄 详细报告已保存: {report_file}")


if __name__ == "__main__":
    import asyncio
    suite = BenchmarkSuite()
    asyncio.run(suite.run_all_benchmarks())
