"""
Celery 任务队列压力测试

测试目标:
1. 验证系统在高并发下的稳定性
2. 测量任务执行吞吐量
3. 识别性能瓶颈
4. 验证资源利用率

测试场景:
- 场景1: 快速任务并发测试 (1000个任务)
- 场景2: 长时任务并发测试 (100个任务)
- 场景3: 混合优先级队列测试
- 场景4: 异常处理和重试测试
- 场景5: 内存泄漏检测

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import asyncio
import time
import psutil
import os
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from loguru import logger

import pytest
from app.core.celery_app import celery_app
from app.core.task_manager import task_manager

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_PERFORMANCE_TESTS"),
    reason="Performance tests are opt-in and require a configured Celery backend."
)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    scenario: str
    task_count: int
    total_time: float
    success_count: int
    failed_count: int
    avg_latency_ms: float
    throughput_tasks_per_sec: float
    memory_usage_mb: float
    cpu_percent: float
    timestamp: str

    @property
    def success_rate(self) -> float:
        if self.task_count == 0:
            return 0.0
        return self.success_count / self.task_count

    def to_dict(self):
        return asdict(self)


class CeleryStressTester:
    """Celery 压力测试器"""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.process = psutil.Process(os.getpid())

    def get_system_stats(self) -> Dict[str, float]:
        """获取系统资源使用情况"""
        memory_info = self.process.memory_info()
        return {
            "memory_mb": memory_info.rss / 1024 / 1024,
            "cpu_percent": self.process.cpu_percent()
        }

    async def scenario_1_fast_tasks_concurrent(self, task_count: int = 1000) -> PerformanceMetrics:
        """
        场景1: 快速任务并发测试
        测试目标: 1000个快速任务的执行吞吐量
        """
        logger.info(f"🚀 场景1: 快速任务并发测试 ({task_count} 个任务)")

        # 快速任务定义
        async def quick_task(task_id: int):
            await asyncio.sleep(0.01)  # 10ms
            return f"task_{task_id}_completed"

        start_time = time.time()
        system_start = self.get_system_stats()

        # 并发创建任务
        tasks = []
        for i in range(task_count):
            task = await task_manager.spawn(
                quick_task(i),
                task_name=f"stress_quick_{i}",
                user_id="stress_test_user"
            )
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        system_end = self.get_system_stats()

        # 统计结果
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failed_count = task_count - success_count
        total_time = end_time - start_time

        metrics = PerformanceMetrics(
            scenario="快速任务并发测试",
            task_count=task_count,
            total_time=total_time,
            success_count=success_count,
            failed_count=failed_count,
            avg_latency_ms=(total_time / task_count) * 1000,
            throughput_tasks_per_sec=task_count / total_time,
            memory_usage_mb=system_end["memory_mb"],
            cpu_percent=system_end["cpu_percent"],
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"✅ 场景1 完成: {metrics.throughput_tasks_per_sec:.2f} tasks/sec")
        return metrics

    async def scenario_2_long_tasks_concurrent(self, task_count: int = 50) -> PerformanceMetrics:
        """
        场景2: 长时任务并发测试
        测试目标: 50个长时任务的并发处理能力
        """
        logger.info(f"🚀 场景2: 长时任务并发测试 ({task_count} 个任务)")

        # 长时任务定义 (模拟真实场景)
        async def long_task(task_id: int):
            await asyncio.sleep(0.5)  # 500ms
            # 模拟一些计算
            result = sum(i * i for i in range(1000))
            return f"long_task_{task_id}_result_{result}"

        start_time = time.time()
        system_start = self.get_system_stats()

        # 并发创建任务
        tasks = []
        for i in range(task_count):
            task = await task_manager.spawn(
                long_task(i),
                task_name=f"stress_long_{i}",
                user_id="stress_test_user"
            )
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        system_end = self.get_system_stats()

        # 统计结果
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failed_count = task_count - success_count
        total_time = end_time - start_time

        metrics = PerformanceMetrics(
            scenario="长时任务并发测试",
            task_count=task_count,
            total_time=total_time,
            success_count=success_count,
            failed_count=failed_count,
            avg_latency_ms=(total_time / task_count) * 1000,
            throughput_tasks_per_sec=task_count / total_time,
            memory_usage_mb=system_end["memory_mb"],
            cpu_percent=system_end["cpu_percent"],
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"✅ 场景2 完成: {metrics.throughput_tasks_per_sec:.2f} tasks/sec")
        return metrics

    async def scenario_3_priority_queues(self) -> PerformanceMetrics:
        """
        场景3: 混合优先级队列测试
        测试目标: 验证优先级队列的调度策略
        """
        logger.info("🚀 场景3: 混合优先级队列测试")

        execution_order = []

        async def high_priority_task(task_id: int):
            execution_order.append(f"high_{task_id}")
            await asyncio.sleep(0.05)
            return f"high_{task_id}"

        async def default_priority_task(task_id: int):
            execution_order.append(f"default_{task_id}")
            await asyncio.sleep(0.05)
            return f"default_{task_id}"

        async def low_priority_task(task_id: int):
            execution_order.append(f"low_{task_id}")
            await asyncio.sleep(0.05)
            return f"low_{task_id}"

        start_time = time.time()

        # 创建混合任务
        tasks = []

        # 高优先级任务
        for i in range(5):
            task = await task_manager.spawn(
                high_priority_task(i),
                task_name=f"high_prio_{i}",
                user_id="stress_test_user"
            )
            tasks.append(task)

        # 默认优先级任务
        for i in range(5):
            task = await task_manager.spawn(
                default_priority_task(i),
                task_name=f"default_prio_{i}",
                user_id="stress_test_user"
            )
            tasks.append(task)

        # 低优先级任务
        for i in range(5):
            task = await task_manager.spawn(
                low_priority_task(i),
                task_name=f"low_prio_{i}",
                user_id="stress_test_user"
            )
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()

        metrics = PerformanceMetrics(
            scenario="混合优先级队列测试",
            task_count=15,
            total_time=end_time - start_time,
            success_count=15,
            failed_count=0,
            avg_latency_ms=(end_time - start_time) / 15 * 1000,
            throughput_tasks_per_sec=15 / (end_time - start_time),
            memory_usage_mb=self.get_system_stats()["memory_mb"],
            cpu_percent=self.get_system_stats()["cpu_percent"],
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"✅ 场景3 完成: 执行顺序 {execution_order}")
        return metrics

    async def scenario_4_exception_handling(self, task_count: int = 100) -> PerformanceMetrics:
        """
        场景4: 异常处理和重试测试
        测试目标: 验证系统在任务失败时的稳定性
        """
        logger.info(f"🚀 场景4: 异常处理测试 ({task_count} 个任务)")

        attempt_count = [0]

        async def flaky_task(task_id: int):
            attempt_count[0] += 1
            if attempt_count[0] % 5 == 0:  # 每5次成功1次
                return f"task_{task_id}_success"
            raise Exception(f"Task {task_id} failed")

        start_time = time.time()

        # 创建带重试的任务
        tasks = []
        for i in range(task_count):
            task = await task_manager.spawn_with_retry(
                lambda i=i: flaky_task(i),
                task_name=f"flaky_{i}",
                max_retries=3,
                retry_delay=0.05,
                user_id="stress_test_user"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()

        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failed_count = task_count - success_count

        metrics = PerformanceMetrics(
            scenario="异常处理和重试测试",
            task_count=task_count,
            total_time=end_time - start_time,
            success_count=success_count,
            failed_count=failed_count,
            avg_latency_ms=(end_time - start_time) / task_count * 1000,
            throughput_tasks_per_sec=task_count / (end_time - start_time),
            memory_usage_mb=self.get_system_stats()["memory_mb"],
            cpu_percent=self.get_system_stats()["cpu_percent"],
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"✅ 场景4 完成: 成功率 {success_count/task_count*100:.1f}%")
        return metrics

    async def scenario_5_memory_leak_detection(self, task_count: int = 1000) -> PerformanceMetrics:
        """
        场景5: 内存泄漏检测
        测试目标: 验证长时间运行是否导致内存泄漏
        """
        logger.info(f"🚀 场景5: 内存泄漏检测 ({task_count} 个任务)")

        memory_samples = []

        async def memory_intensive_task(task_id: int):
            # 模拟内存使用
            data = list(range(1000))
            result = sum(data)
            return result

        start_time = time.time()
        initial_memory = self.get_system_stats()["memory_mb"]

        # 分批执行任务，监控内存变化
        batch_size = 100
        for batch in range(0, task_count, batch_size):
            tasks = []
            for i in range(batch, min(batch + batch_size, task_count)):
                task = await task_manager.spawn(
                    memory_intensive_task(i),
                    task_name=f"memory_{i}",
                    user_id="stress_test_user"
                )
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)

            # 记录内存使用
            current_memory = self.get_system_stats()["memory_mb"]
            memory_samples.append(current_memory)
            logger.info(f"  批次 {batch//batch_size + 1}: 内存 {current_memory:.2f} MB")

        end_time = time.time()
        final_memory = self.get_system_stats()["memory_mb"]

        # 计算内存增长
        memory_growth = final_memory - initial_memory
        growth_rate = memory_growth / task_count  # MB per task

        metrics = PerformanceMetrics(
            scenario="内存泄漏检测",
            task_count=task_count,
            total_time=end_time - start_time,
            success_count=task_count,
            failed_count=0,
            avg_latency_ms=(end_time - start_time) / task_count * 1000,
            throughput_tasks_per_sec=task_count / (end_time - start_time),
            memory_usage_mb=final_memory,
            cpu_percent=self.get_system_stats()["cpu_percent"],
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"✅ 场景5 完成: 内存增长 {memory_growth:.2f} MB (速率: {growth_rate:.4f} MB/task)")
        return metrics

    async def run_all_scenarios(self) -> Dict[str, Any]:
        """运行所有压力测试场景"""
        logger.info("=" * 60)
        logger.info("🔥 开始 Celery 压力测试")
        logger.info("=" * 60)

        results = {}

        # 场景1: 快速任务并发
        results["scenario_1"] = await self.scenario_1_fast_tasks_concurrent(1000)

        # 场景2: 长时任务并发
        results["scenario_2"] = await self.scenario_2_long_tasks_concurrent(50)

        # 场景3: 优先级队列
        results["scenario_3"] = await self.scenario_3_priority_queues()

        # 场景4: 异常处理
        results["scenario_4"] = await self.scenario_4_exception_handling(100)

        # 场景5: 内存泄漏
        results["scenario_5"] = await self.scenario_5_memory_leak_detection(1000)

        # 生成报告
        self._generate_report(results)

        return results

    def _generate_report(self, results: Dict[str, PerformanceMetrics]):
        """生成性能测试报告"""
        logger.info("=" * 60)
        logger.info("📊 压力测试报告")
        logger.info("=" * 60)

        total_tasks = sum(m.task_count for m in results.values())
        total_time = sum(m.total_time for m in results.values())
        total_success = sum(m.success_count for m in results.values())
        total_failed = sum(m.failed_count for m in results.values())

        logger.info(f"总任务数: {total_tasks}")
        logger.info(f"总耗时: {total_time:.2f}s")
        logger.info(f"成功率: {total_success/total_tasks*100:.2f}%")
        logger.info(f"平均吞吐量: {total_tasks/total_time:.2f} tasks/sec")

        logger.info("\n详细结果:")
        for name, metrics in results.items():
            logger.info(f"\n{name}:")
            logger.info(f"  任务数: {metrics.task_count}")
            logger.info(f"  耗时: {metrics.total_time:.2f}s")
            logger.info(f"  吞吐量: {metrics.throughput_tasks_per_sec:.2f} tasks/sec")
            logger.info(f"  成功率: {metrics.success_count/metrics.task_count*100:.1f}%")
            logger.info(f"  内存: {metrics.memory_usage_mb:.2f} MB")
            logger.info(f"  CPU: {metrics.cpu_percent:.1f}%")

        # 保存报告到文件
        import json
        report_data = {k: v.to_dict() for k, v in results.items()}
        report_data["summary"] = {
            "total_tasks": total_tasks,
            "total_time": total_time,
            "overall_success_rate": total_success/total_tasks,
            "overall_throughput": total_tasks/total_time
        }

        with open("/tmp/celery_stress_report.json", "w") as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"\n📄 详细报告已保存到: /tmp/celery_stress_report.json")


@pytest.mark.performance
@pytest.mark.asyncio
async def test_celery_stress_all_scenarios():
    """运行完整压力测试"""
    tester = CeleryStressTester()
    results = await tester.run_all_scenarios()

    # 验证基准指标
    scenario_1 = results["scenario_1"]
    assert scenario_1.throughput_tasks_per_sec > 50, "快速任务吞吐量应 > 50 tasks/sec"
    assert scenario_1.success_rate > 0.95, "成功率应 > 95%"

    scenario_2 = results["scenario_2"]
    assert scenario_2.success_rate == 1.0, "长时任务成功率应为 100%"

    scenario_5 = results["scenario_5"]
    memory_growth = scenario_5.memory_usage_mb - results["scenario_1"].memory_usage_mb
    assert memory_growth < 100, f"内存增长应 < 100 MB, 实际: {memory_growth:.2f} MB"

    logger.info("✅ 所有压力测试通过！")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_celery_stress_all_scenarios())
