# 🚀 Celery 快速启动指南

**状态**: ✅ 基础设施就绪 (数据库 + Redis 已运行)

---

## 📊 当前状态

```bash
# 已运行的服务
✅ sparkle_db      (PostgreSQL + pgvector) - localhost:5432
✅ sparkle_redis   (Redis) - localhost:6379
```

---

## 🎯 下一步 (3个步骤)

### 步骤 1: 构建 Backend 镜像 (如果尚未构建)

```bash
cd backend
docker build -t sparkle_backend .
cd ..
```

### 步骤 2: 启动 Celery 服务

```bash
make celery-up
```

**这将启动**:
- ✅ `sparkle_celery_worker` - 任务执行器 (并发数: 2)
- ✅ `sparkle_celery_beat` - 定时任务调度器
- ✅ `sparkle_flower` - 监控面板 (http://localhost:5555)

### 步骤 3: 验证系统

```bash
# 检查服务状态
make celery-status

# 查看 Worker 日志
make celery-logs-worker

# 打开 Flower 监控
make celery-flower
```

---

## 📋 完整启动流程

### 方式 A: 一键启动 (推荐)

```bash
# 1. 启动基础设施
make dev-up

# 2. 构建 Backend 镜像
cd backend && docker build -t sparkle_backend . && cd ..

# 3. 启动 Celery
make celery-up

# 4. 验证
make celery-status
open http://localhost:5555
```

### 方式 B: 使用启动脚本

```bash
# 1. 启动基础设施
make dev-up

# 2. 使用脚本启动 Celery
bash scripts/devtools/start_celery.sh
```

---

## 🔍 验证 Celery 是否正常工作

### 1. 检查容器状态

```bash
docker ps --filter "name=sparkle" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**预期输出**:
```
NAME                    STATUS          PORTS
sparkle_db              Up 5 minutes    0.0.0.0:5432->5432/tcp
sparkle_redis           Up 5 minutes    0.0.0.0:6379->6379/tcp
sparkle_celery_worker   Up X seconds    (no ports)
sparkle_celery_beat     Up X seconds    (no ports)
sparkle_flower          Up X seconds    0.0.0.0:5555->5555/tcp
```

### 2. 测试任务队列

```bash
# 进入 Worker 容器
docker exec -it sparkle_celery_worker bash

# 在容器内测试
python -c "from app.core.celery_app import celery_app; print(list(celery_app.tasks.keys()))"

# 应该看到任务列表:
# ['generate_node_embedding', 'analyze_error_batch', 'record_token_usage', ...]
```

### 3. 访问监控面板

打开浏览器: http://localhost:5555

**应该看到**:
- ✅ Workers 标签页显示在线 Worker
- ✅ Tasks 标签页显示任务历史
- ✅ Queues 标签页显示队列状态

---

## 🛠 常用命令速查

| 命令 | 功能 |
|------|------|
| `make celery-up` | 启动 Celery 服务 |
| `make celery-status` | 查看服务状态 |
| `make celery-logs-worker` | Worker 日志 |
| `make celery-logs-beat` | Beat 日志 |
| `make celery-flower` | 打开监控面板 |
| `make celery-restart` | 重启服务 |
| `make celery-flush` | 清空队列 |
| `make celery-stop` | 停止服务 |

---

## 🧪 测试任务执行

### 创建测试任务

```bash
# 进入 Python 环境
cd backend
python

# 在 Python 解释器中:
from app.core.celery_tasks import health_check_task
result = health_check_task.apply_async()
print(f"Task ID: {result.id}")
print(f"Status: {result.status}")

# 等待几秒后检查结果
import time
time.sleep(5)
result.get()  # 应该返回健康检查结果
```

### 在 Flower 中观察

1. 打开 http://localhost:5555
2. 点击 "Tasks" 标签页
3. 应该看到 `health_check_task` 的执行记录

---

## 🔧 故障排查

### 问题 1: Worker 无法启动

```bash
# 检查 Redis 连接
docker exec sparkle_redis redis-cli ping

# 检查 Backend 镜像是否存在
docker images | grep sparkle_backend

# 手动启动 Worker 查看详细错误
docker run -it --rm --network sparkle-flutter_default \
  -v $(pwd)/backend:/app \
  sparkle_backend celery -A app.core.celery_app worker -l info
```

### 问题 2: Flower 无法访问

```bash
# 检查 Flower 容器
docker ps | grep flower

# 查看 Flower 日志
docker logs sparkle_flower

# 检查端口占用
lsof -i :5555
```

### 问题 3: 任务不执行

```bash
# 检查 Redis 队列
docker exec sparkle_redis redis-cli -n 1 LLEN celery

# 检查 Worker 是否在线
docker exec sparkle_celery_worker celery -A app.core.celery_app status

# 查看 Worker 活动
docker exec sparkle_celery_worker celery -A app.core.celery_app inspect active
```

---

## 📊 监控指标

### Flower 监控面板

访问: http://localhost:5555

**关键指标**:
- **Workers**: 在线/离线状态
- **Tasks**: 成功/失败率
- **Queues**: 队列长度
- **Performance**: 任务执行时间

### Redis 监控

```bash
# 查看 Redis 内存使用
docker exec sparkle_redis redis-cli INFO memory

# 查看 Celery 相关键
docker exec sparkle_redis redis-cli -n 1 KEYS '*'
```

---

## 🎯 下一步开发

### 测试集成

1. **测试 ErrorBook 服务**:
   ```bash
   # 创建错误记录，观察后台任务
   cd backend && python test_error_book.py
   ```

2. **测试 Galaxy 服务**:
   ```bash
   # 创建节点，观察 Embedding 生成
   cd backend && python test_galaxy.py
   ```

3. **测试 Orchestrator**:
   ```bash
   # 发起聊天，观察状态机执行
   cd backend && python test_orchestrator.py
   ```

### 性能调优

根据实际负载调整:
- Worker 并发数 (`--concurrency=4`)
- 任务重试次数 (`max_retries=5`)
- 队列优先级策略

---

## 📚 相关文档

- 📖 [完整部署指南](./docs/CELERY_DEPLOYMENT_GUIDE.md)
- 📊 [实施总结](./CELERY_IMPLEMENTATION_SUMMARY.md)
- ✅ [验证清单](./VERIFICATION.md)
- 🔧 [环境检查脚本](./backend/scripts/setup_celery.py)

---

## 🎉 快速验证清单

- [ ] 数据库和 Redis 运行 (`make dev-up`)
- [ ] Backend 镜像构建完成
- [ ] Celery 服务启动 (`make celery-up`)
- [ ] Flower 面板可访问 (http://localhost:5555)
- [ ] Worker 日志无错误
- [ ] 测试任务执行成功

---

**状态**: ✅ Week 2 完成，等待 Week 3 测试
**下一步**: 构建 Backend 镜像 → 启动 Celery → 验证监控
