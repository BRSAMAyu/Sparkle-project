#!/usr/bin/env python3
"""
Celery 环境设置脚本

自动配置 Celery 所需的环境:
1. 检查 Redis 连接
2. 验证 Celery 配置
3. 测试任务队列
4. 生成监控仪表板配置

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from loguru import logger
import redis.asyncio as redis
from app.core.celery_app import celery_app, get_celery_status
from app.core.task_manager import task_manager
from app.core.redis_utils import resolve_redis_password


class CelerySetup:
    """Celery 环境设置"""

    def __init__(self):
        self.redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
        self.errors = []
        self.warnings = []

    async def check_redis_connection(self) -> bool:
        """检查 Redis 连接"""
        logger.info("🔍 检查 Redis 连接...")

        try:
            resolved_password, _ = resolve_redis_password(self.redis_url, os.getenv("REDIS_PASSWORD"))
            client = redis.from_url(self.redis_url, password=resolved_password)
            await client.ping()
            info = await client.info()

            logger.success(f"✅ Redis 连接成功 (版本: {info['redis_version']})")
            logger.info(f"   内存使用: {info['used_memory_human']}")
            logger.info(f"   连接数: {info['connected_clients']}")

            await client.close()
            return True

        except Exception as e:
            self.errors.append(f"Redis 连接失败: {e}")
            logger.error(f"❌ Redis 连接失败: {e}")
            return False

    async def verify_celery_config(self) -> bool:
        """验证 Celery 配置"""
        logger.info("🔍 验证 Celery 配置...")

        try:
            # 检查配置
            config = celery_app.conf

            logger.info(f"   Broker: {config.broker_url}")
            logger.info(f"   Result Backend: {config.result_backend}")
            logger.info(f"   Worker Concurrency: {config.worker_concurrency}")
            logger.info(f"   Task Queues: {len(config.task_queues)}")

            # 检查已注册任务
            registered_tasks = list(celery_app.tasks.keys())
            logger.info(f"   已注册任务数: {len(registered_tasks)}")

            if len(registered_tasks) == 0:
                self.warnings.append("没有已注册的 Celery 任务")
                logger.warning("⚠️  没有已注册的 Celery 任务")
                return False

            logger.success(f"✅ Celery 配置验证通过")
            return True

        except Exception as e:
            self.errors.append(f"Celery 配置验证失败: {e}")
            logger.error(f"❌ Celery 配置验证失败: {e}")
            return False

    async def test_task_queue(self) -> bool:
        """测试任务队列"""
        logger.info("🔍 测试任务队列...")

        try:
            # 使用 health_check_task 测试
            from app.core.celery_tasks import health_check_task

            # 发送测试任务
            result = health_check_task.apply_async()

            logger.info(f"   任务 ID: {result.id}")
            logger.info(f"   任务状态: {result.status}")

            # 等待结果 (最多 10 秒)
            for i in range(10):
                if result.ready():
                    break
                await asyncio.sleep(1)

            if result.ready():
                if result.successful():
                    logger.success(f"✅ 任务执行成功: {result.result}")
                    return True
                else:
                    self.errors.append(f"任务执行失败: {result.result}")
                    logger.error(f"❌ 任务执行失败: {result.result}")
                    return False
            else:
                self.warnings.append("任务超时 (请检查 Worker 是否运行)")
                logger.warning("⚠️  任务超时 (请检查 Worker 是否运行)")
                return False

        except Exception as e:
            self.errors.append(f"任务测试失败: {e}")
            logger.error(f"❌ 任务测试失败: {e}")
            return False

    async def check_task_manager_integration(self) -> bool:
        """检查 TaskManager 集成"""
        logger.info("🔍 检查 TaskManager 集成...")

        try:
            # 检查 TaskManager 状态
            health = task_manager.health_check()

            logger.info(f"   活跃任务数: {health['stats']['currently_running']}")
            logger.info(f"   总任务数: {health['stats']['total_spawned']}")
            logger.info(f"   失败率: {health['stats']['failure_rate']:.2f}%")

            if health['healthy']:
                logger.success("✅ TaskManager 健康")
                return True
            else:
                self.warnings.append(f"TaskManager 健康检查警告: {health['status']}")
                logger.warning(f"⚠️  TaskManager 健康检查警告: {health['status']}")
                return False

        except Exception as e:
            self.errors.append(f"TaskManager 检查失败: {e}")
            logger.error(f"❌ TaskManager 检查失败: {e}")
            return False

    async def generate_monitoring_config(self) -> bool:
        """生成监控配置"""
        logger.info("🔍 生成监控配置...")

        try:
            config_dir = Path(__file__).parent.parent / "monitoring"
            config_dir.mkdir(exist_ok=True)

            # Celery 监控配置
            celery_monitoring = """
# Celery 监控配置
# Prometheus 抓取配置

scrape_configs:
  - job_name: 'celery_worker'
    static_configs:
      - targets: ['celery_worker:8080']
    metrics_path: /metrics
    scrape_interval: 15s

  - job_name: 'celery_beat'
    static_configs:
      - targets: ['celery_beat:8080']
    metrics_path: /metrics
    scrape_interval: 15s
"""

            config_file = config_dir / "celery_prometheus.yml"
            config_file.write_text(celery_monitoring)

            logger.success(f"✅ 监控配置已生成: {config_file}")
            return True

        except Exception as e:
            self.warnings.append(f"监控配置生成失败: {e}")
            logger.warning(f"⚠️  监控配置生成失败: {e}")
            return False

    async def run_all_checks(self) -> bool:
        """运行所有检查"""
        logger.info("=" * 60)
        logger.info("🚀 Celery 环境设置检查")
        logger.info("=" * 60)

        results = []

        # 1. Redis 连接检查
        results.append(await self.check_redis_connection())

        # 2. Celery 配置验证
        results.append(await self.verify_celery_config())

        # 3. 任务队列测试
        results.append(await self.test_task_queue())

        # 4. TaskManager 集成检查
        results.append(await self.check_task_manager_integration())

        # 5. 生成监控配置
        results.append(await self.generate_monitoring_config())

        # 总结
        logger.info("=" * 60)
        logger.info("📊 检查总结")
        logger.info("=" * 60)

        if self.errors:
            logger.error(f"❌ 错误 ({len(self.errors)}):")
            for error in self.errors:
                logger.error(f"   - {error}")

        if self.warnings:
            logger.warning(f"⚠️  警告 ({len(self.warnings)}):")
            for warning in self.warnings:
                logger.warning(f"   - {warning}")

        success_count = sum(results)
        total_count = len(results)

        if success_count == total_count:
            logger.success(f"\n✅ 所有检查通过 ({success_count}/{total_count})")
            logger.info("\n🚀 Celery 环境已就绪!")
            logger.info("   下一步:")
            logger.info("   1. 启动 Worker: make celery-up")
            logger.info("   2. 查看监控: http://localhost:5555")
            return True
        else:
            logger.error(f"\n❌ 部分检查失败 ({success_count}/{total_count})")
            logger.info("\n🔧 请修复上述问题后重试")
            return False


async def main():
    """主函数"""
    setup = CelerySetup()
    success = await setup.run_all_checks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
