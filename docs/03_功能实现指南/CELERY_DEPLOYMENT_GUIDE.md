# Celery 任务队列部署指南

## 📋 概述

本文档描述了 Sparkle 项目中 Celery 任务队列系统的部署、配置和运维指南。

**版本**: 1.0
**创建时间**: 2026-01-03
**作者**: Claude Code (Opus 4.5)

---

## 🏗 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    Sparkle Task Queue System                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐ │
│  │  Celery Beat │─────▶│  Redis Broker│◀────▶│ Flower   │ │
│  │  (Scheduler) │      │  (Queue)     │      │ (Monitor)│ │
│  └──────────────┘      └──────────────┘      └──────────┘ │
│         │                    │                               │
│         │                    │                               │
│         ▼                    ▼                               │
│  ┌──────────────────────────────────────┐                  │
│  │      Celery Worker Cluster (2+)      │                  │
│  │  ┌──────────┐  ┌──────────┐         │                  │
│  │  │ Worker 1 │  │ Worker 2 │  ...    │                  │
│  │  └──────────┘  └──────────┘         │                  │
│  └──────────────────────────────────────┘                  │
│                                                             │
│  Queues: high_priority, default, low_priority              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速启动

### 方式 1: 使用 Make 命令 (推荐)

```bash
# 启动所有 Celery 服务 (Worker + Beat + Flower)
make celery-up

# 查看 Worker 日志
make celery-logs-worker

# 查看 Beat 日志
make celery-logs-beat

# 打开 Flower 监控面板
make celery-flower
```

### 方式 2: Docker Compose 直接启动

```bash
# 启动 Celery Worker (2 个副本)
docker compose up -d celery_worker

# 启动 Celery Beat (定时任务)
docker compose up -d celery_beat

# 启动 Flower (监控面板)
docker compose up -d flower

# 查看所有 Celery 服务状态
docker compose ps | grep celery
```

### 方式 3: 完整开发环境

```bash
# 一键启动所有服务 (数据库 + Redis + Celery + gRPC + Gateway)
make dev-all
```

---

## 🔧 服务配置

### Celery Worker

**容器名**: `sparkle_proj_celery_worker`
**副本数**: 2 (可配置)
**内存限制**: 2GB
**队列**: high_priority, default, low_priority

**环境变量**:
```yaml
DATABASE_URL=postgresql://user:pass@sparkle_db:5432/sparkle
REDIS_URL=redis://:pass@redis:6379/1
CELERY_BROKER_URL=redis://:pass@redis:6379/1
CELERY_RESULT_BACKEND=redis://:pass@redis:6379/2
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
```

### Celery Beat (定时任务调度器)

**容器名**: `sparkle_proj_celery_beat`
**功能**: 周期性任务调度

**当前配置的定时任务**:
```python
beat_schedule = {
    "cleanup-every-day": {
        "task": "cleanup_old_data",
        "schedule": 86400.0,  # 每天一次
    },
    "daily-report": {
        "task": "daily_report",
        "schedule": 86400.0,  # 每天一次
    },
}
```

### Flower (监控面板)

**容器名**: `sparkle_proj_flower`
**端口**: 5555
**访问地址**: http://localhost:5555

**功能**:
- 实时监控 Worker 状态
- 任务执行历史和统计
- 队列长度监控
- Worker 管理 (重启、关闭)

---

## 📊 任务队列策略

### 优先级队列

| 队列名称 | 用途 | 优先级 | 示例任务 |
|---------|------|--------|---------|
| **high_priority** | 立即执行的关键任务 | 最高 | 用户请求、实时分析 |
| **default** | 常规后台任务 | 中等 | Embedding 生成、数据同步 |
| **low_priority** | 批量/低优先级任务 | 最低 | 统计汇总、数据清理 |

### 使用示例

```python
from app.core.celery_app import celery_app

# 高优先级任务
@celery_app.task(bind=True, queue="high_priority")
def critical_task(self, data):
    pass

# 默认队列
@celery_app.task(bind=True, queue="default")  # 或省略 queue 参数
def normal_task(self, data):
    pass

# 低优先级队列
@celery_app.task(bind=True, queue="low_priority")
def batch_task(self, data):
    pass
```

---

## 🔍 监控与运维

### Flower 监控面板

访问: http://localhost:5555

**主要功能**:
- **Workers**: 查看所有 Worker 状态 (在线/离线)
- **Tasks**: 任务执行历史、状态、耗时
- **Queues**: 队列长度、任务积压情况
- **Charts**: 实时性能图表

### 命令行监控

```bash
# 查看 Worker 状态
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app status

# 查看队列统计
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app inspect active

# 查看定时任务
docker exec sparkle_proj_celery_beat celery -A app.core.celery_app inspect scheduled

# 查看任务统计
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app inspect stats
```

### 日志查看

```bash
# 实时 Worker 日志
docker logs -f sparkle_proj_celery_worker

# 实时 Beat 日志
docker logs -f sparkle_proj_celery_beat

# 查看特定 Worker 日志 (副本 1)
docker logs -f sparkle_proj_celery_worker.1

# 查看历史日志 (最后 100 行)
docker logs --tail 100 sparkle_proj_celery_worker
```

---

## 🛠 常用命令

### 管理命令

```bash
# 重启所有 Celery 服务
make celery-restart

# 重启特定服务
docker compose restart celery_worker
docker compose restart celery_beat

# 停止 Celery 服务
docker compose stop celery_worker celery_beat flower

# 完全停止并删除容器
docker compose down celery_worker celery_beat flower
```

### 队列管理

```bash
# 清空队列 (危险操作!)
make celery-flush

# 或手动清空
docker exec sparkle_proj_redis redis-cli -n 1 FLUSHDB

# 查看队列长度
docker exec sparkle_proj_redis redis-cli -n 1 LLEN celery

# 手动添加任务到队列 (测试用)
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app call app.core.celery_tasks.health_check_task
```

### 任务管理

```bash
# 查看活动任务
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app inspect active

# 查看保留任务 (正在执行)
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app inspect reserved

# 取消任务
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app revoke <task_id> --terminate

# 重新执行失败任务
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app retry <task_id>
```

---

## 📈 性能调优

### Worker 配置

**并发数调整**:
```python
# 在 celery_app.py 中配置
celery_app.conf.update(
    worker_concurrency=4,  # 每个 Worker 的并发数
    worker_max_tasks_per_child=1000,  # 每个进程最大任务数 (防内存泄漏)
    worker_prefetch_multiplier=4,  # 预取任务数
)
```

**Docker 资源调整**:
```yaml
# docker-compose.yml
celery_worker:
  deploy:
    replicas: 3  # 增加 Worker 副本数
    resources:
      limits:
        memory: 4G  # 增加内存限制
      reservations:
        memory: 1G
```

### Redis 配置

**Redis 数据库分配**:
- DB 0: Python 应用缓存
- DB 1: Celery Broker (任务队列)
- DB 2: Celery Result Backend (任务结果)

**性能优化**:
```bash
# 监控 Redis 内存使用
docker exec sparkle_proj_redis redis-cli INFO memory

# 监控 Redis 键数量
docker exec sparkle_proj_redis redis-cli DBSIZE
```

---

## 🔒 安全与监控

### 健康检查

```bash
# 检查 Worker 是否健康
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app inspect ping

# 检查 Beat 是否健康
docker exec sparkle_proj_celery_beat ps aux | grep celery

# 检查 Flower 是否健康
curl -s http://localhost:5555/api/workers | jq .
```

### Prometheus 指标

Celery Worker 暴露的指标:
- `celery_task_started_total` - 任务启动数
- `celery_task_succeeded_total` - 成功任务数
- `celery_task_failed_total` - 失败任务数
- `celery_task_runtime_seconds` - 任务执行时间

### 告警规则

```yaml
# 示例: Prometheus 告警规则
groups:
  - name: celery_alerts
    rules:
      - alert: CeleryWorkerDown
        expr: up{job="celery_worker"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Celery Worker is down"

      - alert: CeleryQueueBacklog
        expr: celery_queue_length > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Celery queue backlog detected"
```

---

## 🐛 故障排查

### 常见问题

**1. Worker 无法连接 Redis**

```bash
# 检查 Redis 是否运行
docker compose ps redis

# 检查 Redis 连接
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app inspect ping

# 查看 Redis 日志
docker logs sparkle_proj_redis
```

**2. 任务卡在队列中不执行**

```bash
# 检查 Worker 是否在线
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app status

# 查看活动 Worker
docker exec sparkle_proj_celery_worker celery -A app.core.celery_app inspect active

# 重启 Worker
docker compose restart celery_worker
```

**3. Beat 不触发定时任务**

```bash
# 检查 Beat 日志
docker logs sparkle_proj_celery_beat

# 查看已注册的定时任务
docker exec sparkle_proj_celery_beat celery -A app.core.celery_app inspect scheduled

# 重启 Beat
docker compose restart celery_beat
```

**4. Flower 无法访问**

```bash
# 检查 Flower 容器状态
docker compose ps flower

# 检查 Flower 日志
docker logs sparkle_proj_flower

# 检查端口占用
lsof -i :5555
```

### 调试任务执行

```python
# 在任务代码中添加日志
from loguru import logger

@celery_app.task(bind=True, name="debug_task")
def debug_task(self, data):
    logger.info(f"Task started: {self.request.id}")
    logger.info(f"Task args: {self.request.args}")
    logger.info(f"Task kwargs: {self.request.kwargs}")

    try:
        # 任务逻辑
        result = do_something(data)
        logger.info(f"Task completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise self.retry(exc=e, countdown=60)
```

---

## 📦 部署清单

### 生产环境部署前检查

- [ ] Redis 密码已配置 (`.env` 文件)
- [ ] 数据库连接字符串正确
- [ ] Celery Worker 副本数根据负载调整
- [ ] 监控系统 (Prometheus + Grafana) 已配置
- [ ] 日志聚合 (Loki/ELK) 已配置
- [ ] 告警通道 (Slack/Email) 已配置
- [ ] Flower 面板访问控制 (Nginx 反向代理 + 认证)
- [ ] 定时任务时间已调整为生产时区
- [ ] 资源限制已根据实际负载测试

### 环境变量清单

```bash
# .env 文件示例
# Database
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_NAME=sparkle

# Redis
REDIS_PASSWORD=your_redis_password

# Celery
CELERY_BROKER_URL=redis://:your_redis_password@redis:6379/1
CELERY_RESULT_BACKEND=redis://:your_redis_password@redis:6379/2

# Monitoring
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
```

---

## 🔄 升级与迁移

### 从 TaskManager 迁移到 Celery

**阶段 1: 并行运行**
```python
# 同时支持两种方式
async def create_node(...):
    # 方案1: TaskManager (快速任务)
    await task_manager.spawn(
        self._process_node_background(...),
        task_name="node_embedding"
    )

    # 方案2: Celery (长时任务) - 可选
    # schedule_long_task("generate_node_embedding", ...)
```

**阶段 2: 逐步迁移**
1. 监控任务执行时间
2. 识别超过 10 秒的任务
3. 逐步迁移到 Celery
4. 保留 TaskManager 用于 < 10 秒任务

**阶段 3: 完全迁移**
- 所有长时任务使用 Celery
- TaskManager 仅用于请求生命周期内的任务

### 版本升级

```bash
# 1. 停止服务
docker compose down

# 2. 更新镜像
docker compose pull

# 3. 重建容器
docker compose up -d --build

# 4. 验证服务
docker compose ps
make celery-flower
```

---

## 📞 支持与维护

### 日常运维

**每日检查清单**:
- [ ] Flower 面板显示所有 Worker 在线
- [ ] 队列长度 < 50
- [ ] 失败任务数 < 5
- [ ] Redis 内存使用 < 80%
- [ ] 日志无异常错误

**每周检查清单**:
- [ ] 清理旧的任务结果 (Redis)
- [ ] 检查 Worker 内存泄漏
- [ ] 审核定时任务执行情况
- [ ] 备份 Redis 数据

### 性能指标参考

| 指标 | 正常范围 | 警告阈值 | 严重阈值 |
|------|---------|---------|---------|
| Worker CPU 使用率 | < 70% | 70-85% | > 85% |
| Worker 内存使用 | < 2GB | 2-3GB | > 3GB |
| 队列长度 | < 20 | 20-100 | > 100 |
| 任务失败率 | < 1% | 1-5% | > 5% |
| 平均任务耗时 | < 5s | 5-30s | > 30s |

---

## 📚 相关文档

- [Celery 官方文档](https://docs.celeryq.dev/)
- [Flower 文档](https://flower.readthedocs.io/)
- [Sparkle 架构设计](./02_技术架构.md)
- [任务管理器设计](../backend/app/core/task_manager.py)
- [Celery 配置](../backend/app/core/celery_app.py)

---

**文档维护**: 请在系统升级或配置变更时更新此文档
**最后更新**: 2026-01-03
