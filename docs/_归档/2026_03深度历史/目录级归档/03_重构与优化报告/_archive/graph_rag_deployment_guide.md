# GraphRAG 快速部署指南

## 前置要求

- PostgreSQL 16+
- Apache AGE 扩展
- Redis 7+
- Python 3.9+

## 步骤 1: 安装 Apache AGE

### Linux (Ubuntu/Debian)
```bash
# 安装依赖
sudo apt-get update
sudo apt-get install -y postgresql-server-dev-16 build-essential

# 下载并安装 Apache AGE
git clone https://github.com/apache/age.git
cd age
make install

# 重启 PostgreSQL
sudo systemctl restart postgresql

# 验证安装
psql -U postgres -c "CREATE EXTENSION age;"
```

### Docker 方式
```dockerfile
# 在 Dockerfile 中添加
RUN apt-get update && apt-get install -y \
    postgresql-server-dev-16 \
    build-essential \
    git

RUN git clone https://github.com/apache/age.git && \
    cd age && \
    make install
```

## 步骤 2: 配置数据库

### 2.1 创建数据库和用户
```sql
-- 连接到 PostgreSQL
psql -U postgres

-- 创建数据库
CREATE DATABASE sparkle;

-- 创建用户
CREATE USER sparkle WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE sparkle TO sparkle;

-- 启用 AGE 扩展
\c sparkle
CREATE EXTENSION age;
```

### 2.2 创建图模式
```sql
-- 连接到 sparkle 数据库
\c sparkle

-- 创建图
SELECT create_graph('knowledge_graph');

-- 创建节点标签
SELECT create_vlabel('knowledge_graph', 'knowledge_node');
SELECT create_vlabel('knowledge_graph', 'user_node');
SELECT create_vlabel('knowledge_graph', 'subject_node');

-- 创建关系类型
SELECT create_elabel('knowledge_graph', 'relates_to');
SELECT create_elabel('knowledge_graph', 'mastered_by');
SELECT create_elabel('knowledge_graph', 'belongs_to');
```

## 步骤 3: 环境配置

### 3.1 创建 .env 文件
```bash
cd backend
cp .env.example .env
```

### 3.2 配置 GraphRAG 相关参数
```env
# 数据库配置
DATABASE_URL=postgresql://sparkle:your_password@localhost:5432/sparkle

# Redis 配置
REDIS_URL=redis://localhost:6379

# GraphRAG 配置
GRAPH_DB_ENABLED=true
GRAPH_DB_SYNC_MODE=async  # async 或 sync
GRAPH_DB_MAX_DEPTH=2
GRAPH_DB_TOP_K=5

# 监控配置
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
```

## 步骤 4: 数据迁移

### 4.1 全量迁移（首次部署）
```bash
cd backend
python scripts/migrate_to_age.py --full --batch-size=1000
```

### 4.2 增量迁移（已有数据）
```bash
python scripts/migrate_to_age.py --incremental --since="2025-12-27"
```

### 4.3 验证迁移
```bash
# 检查节点数量
python -c "
from backend.services.graph_knowledge_service import GraphKnowledgeService
from backend.app.db.session import get_db_session
import asyncio

async def check():
    async with get_db_session() as db:
        ks = GraphKnowledgeService(db)
        stats = await ks.get_graph_statistics()
        print(f'Nodes: {stats[\"total_nodes\"]}')
        print(f'Relations: {stats[\"total_relations\"]}')

asyncio.run(check())
"
```

## 步骤 5: 启动服务

### 5.1 启动同步 Worker
```bash
# 方式 1: 直接运行
cd backend
python workers/graph_sync_worker.py

# 方式 2: 使用 systemd
sudo tee /etc/systemd/system/graph-sync-worker.service <<EOF
[Unit]
Description=Graph Sync Worker
After=network.target

[Service]
Type=simple
User=sparkle
WorkingDirectory=/opt/sparkle/backend
ExecStart=/usr/bin/python workers/graph_sync_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now graph-sync-worker
```

### 5.2 启动主服务
```bash
# 方式 1: 开发模式
cd backend
python main.py

# 方式 2: Docker
docker-compose up -d
```

### 5.3 验证服务
```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# GraphRAG 健康检查
curl http://localhost:8000/api/v1/monitor/graph/health

# 统计信息
curl http://localhost:8000/api/v1/monitor/graph/statistics
```

## 步骤 6: 监控配置

### 6.1 Prometheus 配置
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'sparkle-graphrag'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/monitor/graph/prometheus/metrics'
    scrape_interval: 15s
```

### 6.2 Grafana 仪表板
导入 Dashboard ID: `graphrag-monitoring` 或使用以下 JSON:

```json
{
  "dashboard": {
    "title": "GraphRAG Monitoring",
    "panels": [
      {
        "title": "Graph DB Connection",
        "targets": [{"expr": "graph_db_connection_status"}]
      },
      {
        "title": "Query Duration",
        "targets": [{"expr": "histogram_quantile(0.95, graph_rag_duration_seconds)"}]
      },
      {
        "title": "Node Count",
        "targets": [{"expr": "graph_nodes_total"}]
      }
    ]
  }
}
```

## 步骤 7: 测试验证

### 7.1 功能测试
```bash
# 测试查询
curl "http://localhost:8000/api/v1/monitor/graph/query/test?query=机器学习&depth=2&top_k=3"

# 预期输出
{
  "status": "success",
  "duration_ms": "< 2000",
  "result": {
    "context": "...",
    "metadata": {
      "vector_count": 3,
      "graph_count": 5,
      "fusion_count": 7
    }
  }
}
```

### 7.2 性能测试
```bash
# 使用 Apache Bench 进行压力测试
ab -n 100 -c 10 "http://localhost:8000/api/v1/monitor/graph/query/test?query=test"

# 预期结果
# - 平均响应时间 < 2s
# - 100% 成功率
```

### 7.3 故障注入测试
```bash
# 1. 停止图数据库
sudo systemctl stop postgresql

# 2. 验证降级机制
curl http://localhost:8000/api/v1/monitor/graph/health
# 应该返回 degraded 状态，但服务仍可用

# 3. 恢复数据库
sudo systemctl start postgresql
```

## 常见问题

### Q1: Apache AGE 扩展加载失败
```bash
# 检查扩展是否安装
ls /usr/lib/postgresql/16/lib/age*

# 手动加载
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS age;"
```

### Q2: 同步 Worker 无响应
```bash
# 检查 Redis 连接
redis-cli PING

# 查看 Worker 日志
journalctl -u graph-sync-worker -f

# 检查同步队列
redis-cli LLEN queue:graph_sync
```

### Q3: 查询性能慢
```sql
-- 检查索引
SELECT * FROM pg_indexes WHERE schemaname = 'age_catalog';

-- 重建索引
REINDEX INDEX knowledge_node_embedding_idx;
```

## 回滚方案

如果 GraphRAG 出现严重问题，可以快速回滚到纯向量检索:

```bash
# 1. 修改配置
echo "GRAPH_DB_ENABLED=false" >> .env

# 2. 重启服务
systemctl restart sparkle-api

# 3. 验证
# Orchestrator 会自动降级到 KnowledgeService
```

## 性能基准

| 指标 | 目标值 | 实际值 |
|------|--------|--------|
| 向量检索延迟 | < 500ms | ~200ms |
| 图遍历延迟 | < 1s | ~500ms |
| 融合搜索延迟 | < 2s | ~800ms |
| 并发查询 (10) | < 3s avg | ~1.5s |
| 内存使用 | < 1GB | ~500MB |

## 监控告警

### 关键告警规则
```yaml
# 严重告警
- GraphDBDisconnected: 立即处理
- HighMemoryUsage: 30分钟内处理

# 警告告警
- HighSyncQueue: 2小时内处理
- SlowQuery: 24小时内优化
```

## 下一步

1. ✅ 验证所有服务正常运行
2. ✅ 检查监控仪表板
3. ✅ 运行完整测试套件
4. ✅ 配置生产环境告警
5. ✅ 建立运维文档

## 技术支持

如遇到问题，请检查:
1. 日志文件: `/var/log/sparkle/`
2. 监控端点: `/api/v1/monitor/graph/health/detailed`
3. 数据库连接: `psql -U sparkle -c "SELECT * FROM ag_graph;"`

---

**版本**: v1.0
**更新日期**: 2025-12-27
**维护团队**: Sparkle Backend Team
