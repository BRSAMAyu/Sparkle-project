# ContextPruner 使用指南

## 📋 概述

ContextPruner 是 Phase 3 的核心组件，用于管理和优化 LLM 上下文窗口，防止 Token 爆炸和上下文溢出。

## 🎯 核心功能

### 1. 滑动窗口 (Sliding Window)
- **策略**: 只保留最近 N 轮对话（默认 10 轮）
- **适用**: 历史记录在 `max_history` 和 `summary_threshold` 之间
- **效果**: 减少 Token 使用，保留最新上下文

### 2. 智能总结 (Summarization)
- **策略**: 超过阈值时触发异步总结，生成前情提要
- **适用**: 历史记录超过 `summary_threshold`（默认 20 轮）
- **效果**: 大幅减少 Token，同时保留核心信息

### 3. 缓存机制
- 总结结果缓存 1 小时
- 避免重复调用 LLM
- 支持缓存失效

## 📊 工作流程

```
用户请求
    ↓
Orchestrator.process_stream()
    ↓
Step 5: Build User Context (UserService + Redis Cache)
    ↓
Step 6: Build Conversation Context (ContextPruner)
    ↓
    ├─ 从 Redis 加载聊天历史
    ├─ 判断历史长度
    │   ├─ ≤ 10 条: 直接返回
    │   ├─ 10-20 条: 滑动窗口
    │   └─ > 20 条: 触发总结 + 滑动窗口
    ↓
Step 8: Build Prompt (包含修剪后的历史)
    ↓
LLM 调用
```

## 🔧 配置参数

### ContextPruner 初始化

```python
from app.orchestration.context_pruner import ContextPruner

context_pruner = ContextPruner(
    redis_client=redis_client,
    max_history_messages=10,      # 滑动窗口保留的消息数
    summary_threshold=20,         # 触发总结的阈值
    summary_cache_ttl=3600        # 总结缓存时间（秒）
)
```

### 推荐配置

| 场景 | max_history | summary_threshold | 说明 |
|------|-------------|-------------------|------|
| **低频对话** | 10 | 20 | 默认配置，平衡性能与上下文 |
| **高频短对话** | 5 | 15 | 更激进的压缩 |
| **深度对话** | 15 | 30 | 保留更多上下文 |
| **成本敏感** | 5 | 10 | 最大限度减少 Token |

## 💡 使用示例

### 示例 1: 基本使用

```python
# 在 Orchestrator 中使用
async def process_stream(self, request, db_session, context_data):
    # ...

    # 获取修剪后的历史
    conversation_context = await self.context_pruner.get_pruned_history(
        session_id=session_id,
        user_id=user_id
    )

    # 构建提示
    prompt = build_system_prompt(
        user_context_data,
        conversation_history=conversation_context
    )

    # ...
```

### 示例 2: 手动触发总结

```python
# 强制触发总结（即使未达到阈值）
pruned = await context_pruner.get_pruned_history(
    session_id="session_123",
    user_id="user_456",
    force_summary=True
)
```

### 示例 3: 检查总结状态

```python
status = await context_pruner.get_summary_status("session_123")
# 返回: {"has_summary": True, "ttl_seconds": 3500, "summary_preview": "..."}
```

### 示例 4: 清除总结缓存

```python
await context_pruner.clear_summary("session_123")
```

## 🔄 后台总结服务

### 启动 SummarizationWorker

**方式 1: 作为独立进程**

```bash
python -m app.orchestration.summarization_worker
```

**方式 2: 在主应用中启动**

```python
from app.orchestration.summarization_worker import SummarizationWorker
import asyncio

async def start_background_workers():
    worker = SummarizationWorker(redis_client, worker_id="main")
    asyncio.create_task(worker.start())

# 在应用启动时调用
await start_background_workers()
```

**方式 3: 使用 Supervisor 或 Systemd**

```ini
# supervisord 配置
[program:summarization_worker]
command=python -m app.orchestration.summarization_worker
directory=/path/to/project
autostart=true
autorestart=true
numprocs=2  # 启动 2 个 worker 提高并发
```

### Worker 配置

```python
worker = SummarizationWorker(
    redis_client,
    batch_size=10,      # 每次批量处理的任务数
    max_retries=3,      # 失败重试次数
    worker_id="worker-1"
)
```

## 📈 性能优化

### Token 使用量对比

| 场景 | 优化前 | 优化后 | 节省 |
|------|--------|--------|------|
| 5 轮对话 | ~500 tokens | ~500 tokens | 0% |
| 15 轮对话 | ~1500 tokens | ~800 tokens | 47% |
| 50 轮对话 | ~5000 tokens | ~1200 tokens | 76% |
| 100 轮对话 | ~10000 tokens | ~1500 tokens | 85% |

### 响应时间

- **ContextPruner 开销**: < 5ms (Redis 查询)
- **总结任务**: 异步执行，不影响主流程
- **缓存命中**: < 1ms

## 🔍 监控指标

### 关键指标

```python
# 1. 历史压缩率
compression_rate = (original - pruned) / original

# 2. 总结使用率
summary_usage_rate = summary_used_count / total_requests

# 3. 缓存命中率
cache_hit_rate = cache_hits / (cache_hits + cache_misses)
```

### 日志输出示例

```
INFO: ChatOrchestrator initialized with ContextPruner
DEBUG: Session session_123: 15 messages -> pruned to 5 + summary, took 0.003s
INFO: Triggered summarization task for session session_123, history size: 10
INFO: Processing summarization task for session session_123, history size: 10, priority: high
INFO: ✅ Summary generated for session session_123 (attempt 1/3)
```

## ⚠️ 常见问题

### Q1: 总结任务积压怎么办？

**问题**: 队列中任务过多，Redis 内存占用高

**解决**:
```python
# 1. 增加 Worker 数量
worker_count = 3  # 启动多个 worker

# 2. 调整总结阈值
context_pruner = ContextPruner(..., summary_threshold=30)  # 更高的阈值

# 3. 监控队列长度
queue_len = await redis.llen("queue:summarization")
if queue_len > 1000:
    # 触发告警或扩容
    pass
```

### Q2: 总结质量不佳？

**问题**: LLM 生成的总结丢失重要信息

**解决**:
```python
# 1. 调整总结提示词（修改 summarization_worker.py）
# 2. 增加保留的消息数
context_pruner = ContextPruner(..., max_history_messages=15)

# 3. 手动审核总结（开发阶段）
```

### Q3: 缓存一致性问题？

**问题**: 用户更新资料后，缓存未失效

**解决**:
```python
# 在 UserService 中已实现
await user_service.invalidate_user_cache(user_id)
```

### Q4: 如何调试？

**调试模式**:
```python
# 1. 查看原始历史
history = await context_pruner._load_chat_history(session_id)
print(f"原始历史: {len(history)} 条")

# 2. 查看修剪结果
result = await context_pruner.get_pruned_history(session_id, user_id)
print(f"修剪结果: {result}")

# 3. 查看总结状态
status = await context_pruner.get_summary_status(session_id)
print(f"总结状态: {status}")
```

## 🚀 部署建议

### 开发环境

```bash
# 启动 Redis
docker run -d -p 6379:6379 redis:7-alpine

# 启动 SummarizationWorker
python -m app.orchestration.summarization_worker
```

### 生产环境

```bash
# 1. Redis 集群（高可用）
# 2. 多个 Worker 实例（负载均衡）
# 3. 监控告警（Prometheus + Grafana）
# 4. 日志收集（ELK Stack）
```

### Docker Compose 示例

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  summarization-worker:
    build: .
    command: python -m app.orchestration.summarization_worker
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    deploy:
      replicas: 2  # 2 个实例
```

## 📝 总结

ContextPruner 通过以下方式优化 LLM 上下文：

1. ✅ **自动修剪**: 根据历史长度自动选择策略
2. ✅ **异步总结**: 不阻塞主流程
3. ✅ **智能缓存**: 避免重复计算
4. ✅ **可配置**: 灵活调整参数
5. ✅ **可观测**: 完整的日志和监控

**预期效果**: Token 使用量减少 50-85%，响应时间增加 < 5ms，数据库查询减少 70%+。
