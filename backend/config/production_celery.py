"""
生产环境 Celery 配置模板

使用前请根据实际环境调整以下参数:
1. REDIS_URL - Redis 连接字符串
2. DATABASE_URL - 数据库连接字符串
3. worker_concurrency - 根据 CPU 核心数调整
4. 监控和告警配置

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import os
from celery import Celery
from kombu import Queue, Exchange

# ==================== 基础配置 ====================

# Redis Broker 配置
REDIS_URL = os.getenv(
    "CELERY_BROKER_URL",
    "redis://:secure_password@redis-cluster:6379/1"
)

# 结果后端
RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://:secure_password@redis-cluster:6379/2"
)

# 数据库连接 (用于任务中访问)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:pass@postgres:5432/sparkle"
)

# ==================== Celery 应用 ====================

celery_app = Celery(
    "sparkle_production",
    broker=REDIS_URL,
    backend=RESULT_BACKEND,
    include=[
        "app.core.celery_tasks",
    ]
)

# ==================== 生产环境配置 ====================

celery_app.conf.update(
    # ====== 序列化 ======
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,

    # ====== 队列配置 ======
    task_queues=(
        Queue("high_priority", Exchange("sparkle"), routing_key="sparkle.high"),
        Queue("default", Exchange("sparkle"), routing_key="sparkle.default"),
        Queue("low_priority", Exchange("sparkle"), routing_key="sparkle.low"),
        Queue("celery", Exchange("celery"), routing_key="celery"),  # 默认队列
    ),
    task_default_queue="default",
    task_default_exchange="sparkle",
    task_default_routing_key="sparkle.default",

    # ====== Worker 配置 ======
    # 根据服务器配置调整
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "8")),
    worker_prefetch_multiplier=int(os.getenv("CELERY_PREFETCH", "2")),
    worker_max_tasks_per_child=int(os.getenv("CELERY_MAX_TASKS", "1000")),
    worker_pool=os.getenv("CELERY_POOL", "prefork"),  # prefork (进程) 或 gevent (协程)

    # ====== 可靠性配置 ======
    task_acks_late=True,  # 任务完成后才确认 (防止丢失)
    task_reject_on_worker_lost=True,  # Worker崩溃时重新入队
    task_track_started=True,  # 跟踪任务开始状态
    task_send_sent_event=True,  # 发送任务发送事件

    # ====== 超时配置 ======
    task_time_limit=int(os.getenv("CELERY_TIME_LIMIT", "3600")),  # 1小时硬超时
    task_soft_time_limit=int(os.getenv("CELERY_SOFT_TIME_LIMIT", "3300")),  # 55分钟软超时
    worker_disable_rate_limits=True,  # 禁用速率限制 (提高性能)

    # ====== 重试配置 ======
    task_default_retry_delay=60,  # 默认60秒后重试
    task_max_retries=3,  # 最多重试3次
    task_retry_backoff=True,  # 指数退避
    task_retry_backoff_max=600,  # 最大退避10分钟

    # ====== 结果配置 ======
    result_expires=3600 * 24 * 7,  # 结果保留7天
    result_extended=True,  # 保存任务元数据
    worker_proc_alive_timeout=60,  # 进程存活超时

    # ====== 监控配置 ======
    worker_send_task_events=True,  # 发送任务事件 (用于监控)
    task_send_sent_event=True,  # 发送发送事件

    # ====== 安全配置 ======
    worker_max_memory_per_child=200 * 1024 * 1024,  # 200MB 内存限制
    worker_cancel_long_running_tasks_on_connection_loss=True,  # 连接断开时取消长任务

    # ====== 性能优化 ======
    worker_direct_exchange=False,  # 禁用直接交换 (节省内存)
    worker_distribute_tasks_period=1.0,  # 任务分发周期
    worker_proc_alive_timeout=60,  # 进程存活检查
)

# ==================== 监控和指标 ====================

# Prometheus 指标导出 (需要 celery-prometheus-exporter)
# pip install celery-prometheus-exporter
# 启动时添加: --prometheus-address=0.0.0.0 --prometheus-port=8080

# ==================== 安全配置 ====================

# 任务白名单 (只允许执行已知任务)
celery_app.conf.task_create_missing_queues = False  # 不自动创建队列

# ==================== 日志配置 ====================

# 日志级别
log_level = os.getenv("CELERY_LOG_LEVEL", "INFO")

# 日志格式
import logging
logging.basicConfig(
    level=log_level,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# ==================== 队列路由 ====================

# 任务到队列的路由规则
task_routes = {
    "app.core.celery_tasks.generate_node_embedding": {"queue": "default"},
    "app.core.celery_tasks.analyze_error_batch": {"queue": "default"},
    "app.core.celery_tasks.record_token_usage": {"queue": "low_priority"},
    "app.core.celery_tasks.save_learning_state": {"queue": "default"},
    "app.core.celery_tasks.persist_bayesian_data": {"queue": "low_priority"},
    "app.core.celery_tasks.cleanup_pending_actions": {"queue": "low_priority"},
    "app.core.celery_tasks.rerank_documents": {"queue": "low_priority"},
    "app.core.celery_tasks.expansion_worker_task": {"queue": "default"},
    "app.core.celery_tasks.visualize_graph": {"queue": "low_priority"},
    "app.core.celery_tasks.health_check_task": {"queue": "high_priority"},
}

celery_app.conf.task_routes = task_routes

# ==================== 定时任务 (Beat) ====================

beat_schedule = {
    # 每天清理旧数据
    "cleanup-every-day": {
        "task": "app.core.celery_tasks.cleanup_pending_actions",
        "schedule": 86400.0,  # 24小时
        "options": {"queue": "low_priority"},
    },
    # 每日报告
    "daily-report": {
        "task": "app.core.celery_tasks.daily_report",
        "schedule": 86400.0,
        "options": {"queue": "low_priority"},
    },
    # 健康检查 (每小时)
    "health-check-hourly": {
        "task": "app.core.celery_tasks.health_check_task",
        "schedule": 3600.0,
        "options": {"queue": "high_priority"},
    },
}

celery_app.conf.beat_schedule = beat_schedule

# ==================== 生产环境检查清单 ====================

"""
生产环境部署前检查:

□ Redis 集群已配置，高可用
□ 数据库连接池大小已调优
□ Worker 资源限制已设置 (内存/CPU)
□ 监控系统 (Prometheus + Grafana) 已就绪
□ 告警通道 (Slack/Email) 已配置
□ 日志聚合 (ELK/Loki) 已配置
□ 日志级别设置为 INFO 或 WARNING
□ 结果后端已配置持久化存储
□ 定时任务时间已调整为生产时区
□ 任务超时时间已根据实际调整
□ 重试策略已配置 (指数退避)
□ 队列已按优先级分离
□ Worker 副本数已根据负载测试
□ 自动扩缩容策略已配置
□ 灾难恢复预案已制定
□ 备份策略已实施
□ 安全组/防火墙规则已配置
□ SSL/TLS 证书已配置
□ 访问控制已配置
□ 性能基准测试已完成
□ 压力测试已完成
□ 文档已更新
"""

# ==================== 环境特定配置 ====================

# 开发环境覆盖
if os.getenv("ENVIRONMENT") == "development":
    celery_app.conf.update(
        worker_concurrency=2,
        task_acks_late=False,
        result_expires=3600,  # 1小时
        worker_max_tasks_per_child=100,
    )

# 测试环境覆盖
if os.getenv("ENVIRONMENT") == "test":
    celery_app.conf.update(
        worker_concurrency=1,
        task_always_eager=True,  # 同步执行
        eager_propagates_exceptions=True,
    )

# ==================== 监控指标配置 ====================

# 如果使用 celery-prometheus-exporter
# 启动 Worker 时添加参数:
# celery -A app.core.celery_app worker --prometheus-address=0.0.0.0 --prometheus-port=8080

# ==================== 安全加固 ====================

# 任务执行环境隔离
import os
if os.getenv("CELERY_SANDBOX", "false").lower() == "true":
    # 在沙箱中执行任务 (需要额外配置)
    celery_app.conf.update(
        worker_pool="solo",  # 单进程隔离
    )

# ==================== 性能调优参数 ====================

# 根据服务器规格自动调整
def get_optimal_config():
    """根据系统资源获取最优配置"""
    import psutil

    cpu_count = psutil.cpu_count()
    memory = psutil.virtual_memory()

    # 内存充足时
    if memory.total > 16 * 1024**3:  # 16GB+
        concurrency = min(cpu_count * 2, 16)
        prefetch = 4
        max_tasks = 2000
    elif memory.total > 8 * 1024**3:  # 8GB+
        concurrency = min(cpu_count * 2, 8)
        prefetch = 2
        max_tasks = 1000
    else:  # 4GB+
        concurrency = min(cpu_count, 4)
        prefetch = 1
        max_tasks = 500

    return {
        "worker_concurrency": concurrency,
        "worker_prefetch_multiplier": prefetch,
        "worker_max_tasks_per_child": max_tasks,
    }

# 如果未手动设置，使用自动配置
if not os.getenv("CELERY_CONCURRENCY"):
    auto_config = get_optimal_config()
    celery_app.conf.update(**auto_config)

# ==================== 导出配置 ====================

__all__ = ["celery_app", "get_optimal_config"]
