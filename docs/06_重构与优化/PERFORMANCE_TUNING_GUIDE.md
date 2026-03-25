# 🚀 Celery 性能调优指南

**版本**: 1.0
**创建时间**: 2026-01-03
**作者**: Claude Code (Opus 4.5)

---

## 📊 性能基准

### 关键指标参考

| 指标 | 优秀 | 良好 | 需要优化 | 严重 |
|------|------|------|---------|------|
| **任务吞吐量** | > 200 ops/s | 100-200 ops/s | 50-100 ops/s | < 50 ops/s |
| **P95 延迟** | < 50ms | 50-100ms | 100-500ms | > 500ms |
| **失败率** | < 1% | 1-3% | 3-5% | > 5% |
| **内存增长** | < 10MB/千任务 | 10-50MB | 50-100MB | > 100MB |
| **CPU 使用率** | < 50% | 50-70% | 70-85% | > 85% |

---

## 🔧 快速调优

### 1. Worker 并发数

**问题**: 任务执行慢，CPU 使用率低

**解决方案**:
```bash
# 查看 CPU 核心数
nproc

# 调整并发数 (推荐: CPU核心数 × 2)
celery -A app.core.celery_app worker --concurrency=8
```

**Docker 配置**:
```yaml
# docker-compose.yml
celery_worker:
  command: celery -A app.core.celery_app worker --concurrency=8
```

### 2. 内存优化

**问题**: 内存使用持续增长

**解决方案**:
```python
# celery_app.py
celery_app.conf.update(
    worker_max_tasks_per_child=1000,  # 每1000个任务重启进程
    worker_prefetch_multiplier=2,     # 减少预取任务数
)
```

**原理**:
- `max_tasks_per_child`: 防止内存泄漏累积
- `prefetch_multiplier`: 降低内存压力

### 3. 队列策略优化

**问题**: 高优先级任务被阻塞

**解决方案**:
```python
# 使用专用队列
@celery_app.task(queue="high_priority")
def critical_task():
    pass

@celery_app.task(queue="low_priority")
def batch_task():
    pass

# 启动专用 Worker
celery -A app worker -Q high_priority --concurrency=4
celery -A app worker -Q low_priority --concurrency=8
```

### 4. 任务确认策略

**问题**: 任务丢失或重复执行

**解决方案**:
```python
# celery_app.conf.update(
#     task_acks_late=True,              # 任务完成后才确认
#     task_reject_on_worker_lost=True,  # Worker崩溃时重新入队
#     worker_prefetch_multiplier=1,     # 一次只取一个任务
# )
```

---

## 📈 高级调优

### 场景 1: 高吞吐量需求

**目标**: 最大化任务处理速度

**配置**:
```python
celery_app.conf.update(
    worker_concurrency=16,              # 高并发
    worker_prefetch_multiplier=4,       # 批量预取
    worker_pool='gevent',               # 协程池
    task_acks_late=False,               # 快速确认
    worker_max_tasks_per_child=2000,    # 减少重启开销
)
```

**适用场景**: I/O 密集型任务，大量短任务

### 场景 2: 高可靠性需求

**目标**: 确保任务不丢失，可追踪

**配置**:
```python
celery_app.conf.update(
    worker_concurrency=4,               # 保守并发
    worker_prefetch_multiplier=1,       # 逐个处理
    task_acks_late=True,                # 完成后确认
    task_reject_on_worker_lost=True,    # 崩溃重试
    worker_max_tasks_per_child=500,     # 频繁重启防泄漏
    task_time_limit=3600,               # 1小时超时
    task_soft_time_limit=3300,          # 55分钟软超时
)
```

**适用场景**: 关键业务任务，长时任务

### 场景 3: 混合负载

**目标**: 平衡吞吐量和可靠性

**配置**:
```python
celery_app.conf.update(
    worker_concurrency=8,
    worker_prefetch_multiplier=2,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    worker_pool='prefork',              # 进程池
)
```

**使用多队列**:
```python
# 高优先级: 可靠性优先
@celery_app.task(queue="critical", acks_late=True)
def critical_task():
    pass

# 低优先级: 吞吐量优先
@celery_app.task(queue="batch", acks_late=False)
def batch_task():
    pass
```

---

## 🛠 性能测试

### 运行基准测试

```bash
# 1. 压力测试
cd backend && python tests/performance/test_celery_stress.py

# 2. 基准测试
cd backend && python tests/performance/benchmark_suite.py

# 3. 自动调优分析
cd backend && python tests/performance/worker_tuner.py
```

### 测试场景说明

#### 场景 1: 快速任务并发 (1000个)
- **目标**: 测试吞吐量
- **预期**: > 100 tasks/sec
- **优化方向**: 增加并发数

#### 场景 2: 长时任务并发 (50个)
- **目标**: 测试并发处理能力
- **预期**: 100% 成功率
- **优化方向**: 调整超时设置

#### 场景 3: 优先级队列
- **目标**: 验证调度策略
- **预期**: 高优先级先执行
- **优化方向**: 调整队列配置

#### 场景 4: 异常处理 (100个)
- **目标**: 测试重试机制
- **预期**: > 95% 最终成功率
- **优化方向**: 调整重试策略

#### 场景 5: 内存泄漏检测 (1000个)
- **目标**: 验证内存稳定性
- **预期**: 内存增长 < 50MB
- **优化方向**: 调整 max_tasks_per_child

---

## 📊 监控指标

### 关键 Prometheus 指标

```promql
# 任务吞吐量 (每秒)
rate(celery_task_completed_total[5m])

# 任务失败率
rate(celery_task_failed_total[5m]) / rate(celery_task_started_total[5m])

# P95 任务延迟
histogram_quantile(0.95, rate(celery_task_runtime_seconds_bucket[5m]))

# 队列长度
celery_queue_length

# Worker 内存使用
process_resident_memory_bytes{job="celery_worker"}

# Worker CPU 使用率
rate(process_cpu_seconds_total{job="celery_worker"}[5m])
```

### Grafana 仪表板

**导入仪表板 ID**: 12345 (Celery Official)

**关键图表**:
1. **任务执行趋势**: 成功率、失败率、吞吐量
2. **延迟分布**: P50, P95, P99 延迟
3. **资源使用**: CPU, 内存, 磁盘
4. **队列监控**: 各队列长度和积压
5. **Worker 状态**: 在线/离线，活跃任务数

---

## 🔍 故障排查

### 问题 1: 吞吐量低

**诊断**:
```bash
# 1. 检查 Worker 状态
docker exec sparkle_celery_worker celery -A app.core.celery_app status

# 2. 查看活跃任务
docker exec sparkle_celery_worker celery -A app.core.celery_app inspect active

# 3. 检查系统资源
docker stats sparkle_celery_worker
```

**解决方案**:
- 增加 `--concurrency`
- 检查任务是否阻塞
- 查看 Redis 延迟

### 问题 2: 内存泄漏

**诊断**:
```bash
# 监控内存变化
watch -n 5 'docker exec sparkle_celery_worker ps aux | grep celery'

# 检查任务统计
docker exec sparkle_celery_worker celery -A app.core.celery_app inspect stats
```

**解决方案**:
- 设置 `worker_max_tasks_per_child=500`
- 检查任务代码是否有全局变量累积
- 使用 `gc.collect()` 强制回收

### 问题 3: 任务卡死

**诊断**:
```bash
# 查看超时任务
docker exec sparkle_celery_worker celery -A app.core.celery_app inspect active

# 检查日志
docker logs sparkle_celery_worker --since 1h | grep ERROR
```

**解决方案**:
- 设置 `task_time_limit` 和 `task_soft_time_limit`
- 检查任务是否有死循环
- 使用超时装饰器

### 问题 4: Redis 连接问题

**诊断**:
```bash
# 测试 Redis 连接
docker exec sparkle_celery_worker redis-cli ping

# 检查连接数
docker exec sparkle_celery_worker redis-cli info clients
```

**解决方案**:
- 增加 Redis 连接池大小
- 检查网络延迟
- 配置连接重试

---

## 🎯 调优流程

### 步骤 1: 基准测试

```bash
# 1. 运行基准测试
cd backend && python tests/performance/benchmark_suite.py

# 2. 记录当前指标
# - 吞吐量: ___ tasks/sec
# - P95延迟: ___ ms
# - 失败率: ___ %
# - 内存使用: ___ MB
```

### 步骤 2: 分析瓶颈

```bash
# 1. 运行调优分析
cd backend && python tests/performance/worker_tuner.py

# 2. 查看建议
cat /tmp/celery_optimized_config.py
```

### 步骤 3: 应用优化

```python
# 根据建议修改配置
# celery_app.conf.update(
#     worker_concurrency=8,
#     worker_prefetch_multiplier=2,
#     ...
# )
```

### 步骤 4: 验证效果

```bash
# 重新运行基准测试
cd backend && python tests/performance/benchmark_suite.py

# 对比指标变化
```

### 步骤 5: 生产部署

```bash
# 1. 更新 Docker 配置
docker compose up -d --build celery_worker

# 2. 监控生产指标
make celery-flower  # 查看监控面板

# 3. 观察告警
# 检查 Prometheus 告警
```

---

## 📋 配置模板

### 低配环境 (2核4G)

```python
# celery_app.py
celery_app.conf.update(
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=500,
    task_acks_late=True,
    worker_pool='prefork',
)
```

### 标准环境 (4核8G)

```python
celery_app.conf.update(
    worker_concurrency=8,
    worker_prefetch_multiplier=2,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    worker_pool='prefork',
)
```

### 高配环境 (8核16G)

```python
celery_app.conf.update(
    worker_concurrency=16,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=2000,
    task_acks_late=False,
    worker_pool='gevent',
)
```

---

## 🚀 性能优化清单

### 必做优化
- [ ] 设置合适的并发数 (CPU × 2)
- [ ] 配置内存限制 (max_tasks_per_child)
- [ ] 启用任务超时保护
- [ ] 配置监控和告警

### 推荐优化
- [ ] 使用多队列分离优先级
- [ ] 调整预取策略
- [ ] 优化任务确认策略
- [ ] 配置自动重启

### 高级优化
- [ ] 使用 gevent 池 (I/O密集)
- [ ] 分布式 Worker 部署
- [ ] 任务结果后端优化
- [ ] Redis 连接池调优

---

## 📞 性能问题求助

**遇到性能问题时，提供以下信息**:

1. **运行诊断命令**:
   ```bash
   make celery-status
   make celery-logs-worker
   ```

2. **运行基准测试**:
   ```bash
   cd backend && python tests/performance/benchmark_suite.py
   ```

3. **检查监控**:
   - Flower: http://localhost:5555
   - Prometheus: http://localhost:9090

4. **分享报告**:
   - `/tmp/celery_stress_report.json`
   - `/tmp/benchmark_report.json`

---

**文档维护**: 请在性能优化后更新此文档
**最后更新**: 2026-01-03
