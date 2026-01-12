"""
Worker 性能调优器

自动分析性能指标并提供调优建议

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import asyncio
import psutil
import os
from typing import Dict, Any, List
from dataclasses import dataclass
from loguru import logger

from app.core.celery_app import celery_app
from app.core.task_manager import task_manager


@dataclass
class TuningRecommendation:
    """调优建议"""
    parameter: str
    current_value: Any
    recommended_value: Any
    reason: str
    expected_improvement: str

    def __str__(self):
        return (
            f"🔧 {self.parameter}:\n"
            f"  当前: {self.current_value}\n"
            f"  建议: {self.recommended_value}\n"
            f"  原因: {self.reason}\n"
            f"  预期: {self.expected_improvement}"
        )


class WorkerTuner:
    """Worker 性能调优器"""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.recommendations: List[TuningRecommendation] = []

    async def analyze_system_resources(self) -> Dict[str, Any]:
        """分析系统资源"""
        logger.info("🔍 分析系统资源...")

        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu_count": cpu_count,
            "cpu_percent": cpu_percent,
            "memory_total_gb": memory.total / (1024**3),
            "memory_available_gb": memory.available / (1024**3),
            "memory_percent": memory.percent,
            "disk_total_gb": disk.total / (1024**3),
            "disk_free_gb": disk.free / (1024**3),
            "disk_percent": disk.percent
        }

    async def analyze_worker_performance(self) -> Dict[str, Any]:
        """分析 Worker 性能"""
        logger.info("🔍 分析 Worker 性能...")

        # 获取 TaskManager 统计
        stats = task_manager.get_stats()

        # 获取进程资源
        process_memory = self.process.memory_info()
        process_cpu = self.process.cpu_percent()

        return {
            "active_tasks": stats["currently_running"],
            "total_spawned": stats["total_spawned"],
            "total_completed": stats["total_completed"],
            "total_failed": stats["total_failed"],
            "failure_rate": stats["failure_rate"],
            "avg_duration_ms": stats["average_duration_ms"],
            "memory_mb": process_memory.rss / 1024 / 1024,
            "memory_virtual_mb": process_memory.vms / 1024 / 1024,
            "cpu_percent": process_cpu
        }

    async def analyze_celery_config(self) -> Dict[str, Any]:
        """分析 Celery 配置"""
        logger.info("🔍 分析 Celery 配置...")

        config = celery_app.conf

        return {
            "worker_concurrency": config.worker_concurrency,
            "worker_prefetch_multiplier": config.worker_prefetch_multiplier,
            "worker_max_tasks_per_child": config.worker_max_tasks_per_child,
            "worker_pool": config.worker_pool,
            "worker_disable_rate_limits": config.worker_disable_rate_limits,
            "task_acks_late": config.task_acks_late,
            "task_reject_on_worker_lost": config.task_reject_on_worker_lost,
            "task_time_limit": config.task_time_limit,
            "task_soft_time_limit": config.task_soft_time_limit,
            "broker_url": config.broker_url,
            "result_backend": config.result_backend
        }

    async def generate_recommendations(self) -> List[TuningRecommendation]:
        """生成调优建议"""
        logger.info("🔧 生成调优建议...")

        self.recommendations = []

        # 1. 分析资源
        system = await self.analyze_system_resources()
        worker = await self.analyze_worker_performance()
        celery = await self.analyze_celery_config()

        # 2. 生成建议

        # 建议 1: Worker 并发数
        cpu_count = system["cpu_count"]
        current_concurrency = celery["worker_concurrency"]

        if cpu_count > 4 and current_concurrency < cpu_count:
            recommended = min(cpu_count * 2, 8)  # 2倍CPU数，最多8
            self.recommendations.append(
                TuningRecommendation(
                    parameter="worker_concurrency",
                    current_value=current_concurrency,
                    recommended_value=recommended,
                    reason=f"CPU核心数为{cpu_count}，当前并发数{current_concurrency}偏低",
                    expected_improvement=f"吞吐量提升 {((recommended/current_concurrency)-1)*100:.0f}%"
                )
            )

        # 建议 2: 内存限制
        memory_total = system["memory_total_gb"]
        memory_used = worker["memory_mb"] / 1024

        if memory_total < 4 and memory_used > memory_total * 0.7:
            self.recommendations.append(
                TuningRecommendation(
                    parameter="worker_max_tasks_per_child",
                    current_value=celery["worker_max_tasks_per_child"],
                    recommended_value=500,
                    reason=f"内存有限({memory_total:.1f}GB)，任务内存使用较高",
                    expected_improvement="防止内存泄漏，保持稳定"
                )
            )

        # 建议 3: 预取策略
        prefetch = celery["worker_prefetch_multiplier"]
        if prefetch > 4:
            self.recommendations.append(
                TuningRecommendation(
                    parameter="worker_prefetch_multiplier",
                    current_value=prefetch,
                    recommended_value=2,
                    reason="预取过多可能导致任务堆积和内存压力",
                    expected_improvement="降低内存使用，提高响应性"
                )
            )

        # 建议 4: 任务确认策略
        if not celery["task_acks_late"]:
            self.recommendations.append(
                TuningRecommendation(
                    parameter="task_acks_late",
                    current_value=False,
                    recommended_value=True,
                    reason="防止任务在执行前崩溃导致丢失",
                    expected_improvement="提高任务可靠性"
                )
            )

        # 建议 5: TaskManager 统计清理
        if worker["total_spawned"] > 10000 and len(task_manager._stats) > 5000:
            self.recommendations.append(
                TuningRecommendation(
                    parameter="TaskManager 统计保留",
                    current_value="无限制",
                    recommended_value="保留最近1000个",
                    reason="统计历史过多占用内存",
                    expected_improvement="内存使用降低 50-80%"
                )
            )

        # 建议 6: 失败率处理
        if worker["failure_rate"] > 5:
            self.recommendations.append(
                TuningRecommendation(
                    parameter="task_max_retries",
                    current_value=3,
                    recommended_value=5,
                    reason=f"当前失败率 {worker['failure_rate']:.1f}% 偏高",
                    expected_improvement="提高任务成功率"
                )
            )

        # 建议 7: 资源限制
        if system["memory_percent"] > 80:
            self.recommendations.append(
                TuningRecommendation(
                    parameter="Worker 内存限制",
                    current_value="无限制",
                    recommended_value=f"{int(memory_total * 0.7)}GB",
                    reason=f"系统内存使用率 {system['memory_percent']:.1f}% 过高",
                    expected_improvement="防止系统OOM"
                )
            )

        # 建议 8: 并发池类型
        if celery["worker_pool"] == "prefork" and system["cpu_count"] > 4:
            self.recommendations.append(
                TuningRecommendation(
                    parameter="worker_pool",
                    current_value="prefork",
                    recommended_value="gevent",
                    reason="高并发场景下gevent更高效",
                    expected_improvement="并发能力提升 2-3倍"
                )
            )

        return self.recommendations

    async def apply_recommendations(self, recommendations: List[TuningRecommendation]) -> Dict[str, Any]:
        """应用调优建议"""
        logger.info("🔧 应用调优建议...")

        applied = []
        skipped = []

        for rec in recommendations:
            if "TaskManager" in rec.parameter or "Worker" in rec.parameter:
                # 这些需要手动配置，跳过自动应用
                skipped.append(rec)
                continue

            if rec.parameter == "worker_concurrency":
                # 更新 Celery 配置
                celery_app.conf.update(worker_concurrency=rec.recommended_value)
                applied.append(rec)

            elif rec.parameter == "worker_prefetch_multiplier":
                celery_app.conf.update(worker_prefetch_multiplier=rec.recommended_value)
                applied.append(rec)

            elif rec.parameter == "task_acks_late":
                celery_app.conf.update(task_acks_late=rec.recommended_value)
                applied.append(rec)

            elif rec.parameter == "worker_max_tasks_per_child":
                celery_app.conf.update(worker_max_tasks_per_child=rec.recommended_value)
                applied.append(rec)

        return {
            "applied": applied,
            "skipped": skipped,
            "manual_config_required": [r.parameter for r in skipped]
        }

    async def run_tuning_analysis(self) -> Dict[str, Any]:
        """运行完整的调优分析"""
        logger.info("=" * 60)
        logger.info("🔧 Worker 性能调优分析")
        logger.info("=" * 60)

        # 收集数据
        system = await self.analyze_system_resources()
        worker = await self.analyze_worker_performance()
        celery = await self.analyze_celery_config()

        # 生成建议
        recommendations = await self.generate_recommendations()

        # 显示系统信息
        logger.info("\n📊 系统资源:")
        logger.info(f"  CPU: {system['cpu_count']} 核心, {system['cpu_percent']:.1f}% 使用率")
        logger.info(f"  内存: {system['memory_available_gb']:.1f}GB / {system['memory_total_gb']:.1f}GB ({system['memory_percent']:.1f}%)")
        logger.info(f"  磁盘: {system['disk_free_gb']:.1f}GB / {system['disk_total_gb']:.1f}GB ({system['disk_percent']:.1f}%)")

        # 显示 Worker 信息
        logger.info("\n⚙️  Worker 状态:")
        logger.info(f"  活跃任务: {worker['active_tasks']}")
        logger.info(f"  总任务: {worker['total_spawned']} (成功: {worker['total_completed']}, 失败: {worker['total_failed']})")
        logger.info(f"  失败率: {worker['failure_rate']:.2f}%")
        logger.info(f"  平均耗时: {worker['avg_duration_ms']:.2f}ms")
        logger.info(f"  内存使用: {worker['memory_mb']:.2f}MB")

        # 显示 Celery 配置
        logger.info("\n⚙️  Celery 配置:")
        logger.info(f"  并发数: {celery['worker_concurrency']}")
        logger.info(f"  预取倍数: {celery['worker_prefetch_multiplier']}")
        logger.info(f"  最大任务/子进程: {celery['worker_max_tasks_per_child']}")
        logger.info(f"  池类型: {celery['worker_pool']}")

        # 显示建议
        logger.info("\n💡 调优建议:")
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                logger.info(f"\n{i}. {rec}")
        else:
            logger.info("  当前配置已优化，无需调整")

        # 应用建议
        logger.info("\n🔧 应用建议...")
        result = await self.apply_recommendations(recommendations)

        if result["applied"]:
            logger.info(f"✅ 已自动应用 {len(result['applied'])} 条建议")

        if result["manual_config_required"]:
            logger.info(f"⚠️  需要手动配置: {', '.join(result['manual_config_required'])}")

        # 生成配置文件
        config_content = self._generate_config_file(recommendations)
        config_file = "/tmp/celery_optimized_config.py"
        with open(config_file, "w") as f:
            f.write(config_content)

        logger.info(f"\n📄 优化后的配置已生成: {config_file}")

        return {
            "system": system,
            "worker": worker,
            "celery": celery,
            "recommendations": recommendations,
            "applied": result["applied"],
            "manual_config_required": result["manual_config_required"],
            "config_file": config_file
        }

    def _generate_config_file(self, recommendations: List[TuningRecommendation]) -> str:
        """生成优化后的配置文件"""
        config_lines = [
            "# Celery 优化配置",
            "# 由 WorkerTuner 自动生成",
            "",
            "from celery import Celery",
            "",
            "celery_app = Celery('sparkle', broker='redis://localhost:6379/1')",
            "",
            "# 优化后的配置",
            "celery_app.conf.update(",
        ]

        # 根据建议生成配置
        for rec in recommendations:
            if rec.parameter == "worker_concurrency":
                config_lines.append(f"    worker_concurrency={rec.recommended_value},")
            elif rec.parameter == "worker_prefetch_multiplier":
                config_lines.append(f"    worker_prefetch_multiplier={rec.recommended_value},")
            elif rec.parameter == "worker_max_tasks_per_child":
                config_lines.append(f"    worker_max_tasks_per_child={rec.recommended_value},")
            elif rec.parameter == "task_acks_late":
                config_lines.append(f"    task_acks_late={rec.recommended_value},")
            elif rec.parameter == "worker_pool":
                config_lines.append(f"    worker_pool='{rec.recommended_value}',")

        config_lines.append(")")
        config_lines.append("")
        config_lines.append("# 其他推荐配置")
        config_lines.append("# task_time_limit = 3600  # 1小时")
        config_lines.append("# task_soft_time_limit = 3300  # 55分钟")
        config_lines.append("# worker_prefetch_multiplier = 2  # 降低内存使用")
        config_lines.append("# task_acks_late = True  # 提高可靠性")

        return "\n".join(config_lines)


if __name__ == "__main__":
    import asyncio
    tuner = WorkerTuner()
    asyncio.run(tuner.run_tuning_analysis())
