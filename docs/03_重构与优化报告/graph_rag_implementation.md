# GraphRAG 系统实现文档

## 概述

GraphRAG (Graph-based Retrieval-Augmented Generation) 是 Sparkle 项目中引入的增强型知识检索系统，结合了向量检索和图检索的优势，提供更精准、更丰富的知识上下文。

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    GraphRAG 系统架构                          │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  向量数据库       │     │  图数据库         │     │  Redis 缓存       │
│  (pgvector)      │     │  (Apache AGE)    │     │  (同步队列)       │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         └──────────┬─────────────┴────────────┬───────────┘
                    │                          │
         ┌──────────▼──────────────────────────▼──────────┐
         │         GraphKnowledgeService                   │
         │  (双写策略 + GraphRAG 检索器)                   │
         └──────────┬──────────────────────────┬──────────┘
                    │                          │
         ┌──────────▼──────────┐   ┌──────────▼──────────┐
         │  写入路径            │   │  读取路径            │
         │  - 双写同步          │   │  - 向量检索          │
         │  - 异步队列          │   │  - 图遍历            │
         │  - 错误恢复          │   │  - 结果融合          │
         └──────────────────────┘   └──────────────────────┘
                    │                          │
         ┌──────────▼──────────────────────────▼──────────┐
         │         Orchestrator (集成 GraphRAG)            │
         │  - 自动降级机制                                 │
         │  - 性能监控                                     │
         └─────────────────────────────────────────────────┘
```

## 核心组件

### 1. GraphRAGRetriever (`backend/orchestration/graph_rag.py`)

**职责**: 执行增强的检索操作，结合向量和图检索

**核心方法**:
- `vector_search()`: 向量相似度搜索
- `graph_search()`: 图遍历搜索
- `fusion_search()`: 融合搜索（向量 + 图）
- `rerank()`: 结果重排序

**算法流程**:
```
1. 接收用户查询
2. 执行向量搜索 (top-k)
3. 基于结果节点执行图遍历 (depth=2)
4. 融合两种结果
5. 去重和重排序
6. 生成增强上下文
```

### 2. GraphKnowledgeService (`backend/services/graph_knowledge_service.py`)

**职责**: 增强的知识服务，支持双写策略

**核心特性**:
- **双写策略**: 同时写入向量数据库和图数据库
- **异步同步**: 通过 Redis Stream 实现异步同步
- **错误恢复**: 失败重试和补偿机制
- **GraphRAG 集成**: 内置 GraphRAG 检索器

**写入流程**:
```python
# 1. 写入向量数据库 (主库)
await self._write_to_vector_db(...)

# 2. 写入图数据库 (同步或异步)
if sync_mode:
    await self._write_node_to_graph(...)
else:
    await self._publish_sync_event(...)  # 发送到 Redis Stream

# 3. 错误处理
try:
    # 写入操作
except Exception as e:
    await self._handle_write_failure(...)
```

### 3. GraphSyncWorker (`backend/workers/graph_sync_worker.py`)

**职责**: 异步消费同步事件，写入图数据库

**工作模式**:
```
┌─────────────────────────────────────────┐
│  Worker 事件处理循环                     │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  1. 从 Redis Stream 读取事件             │
│     XREAD BLOCK 5000                    │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  2. 解析事件数据                         │
│     - 操作类型 (create/update/delete)   │
│     - 节点数据                          │
│     - 用户信息                          │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  3. 执行图数据库写入                     │
│     - 创建节点标签                      │
│     - 创建关系                          │
│     - 设置属性                          │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  4. 确认事件处理                        │
│     XACK                                │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  5. 错误处理和重试                      │
│     - 失败事件入死信队列                │
└─────────────────────────────────────────┘
```

### 4. 监控系统 (`backend/app/api/v1/graph_monitor.py`)

**监控端点**:
- `GET /api/v1/monitor/graph/health`: 系统健康检查
- `GET /api/v1/monitor/graph/statistics`: 详细统计
- `POST /api/v1/monitor/graph/sync/trigger`: 手动触发同步
- `GET /api/v1/monitor/graph/sync/status`: 同步状态
- `GET /api/v1/monitor/graph/query/test`: 测试查询

**监控指标** (Prometheus):
```prometheus
# GraphRAG 请求
graph_rag_requests_total{status, query_type}

# 查询延迟
graph_rag_duration_seconds{operation}

# 数据库连接状态
graph_db_connection_status

# 数据量统计
graph_nodes_total
graph_relations_total
```

## 数据模型

### Apache AGE 图模型

#### 节点标签 (Labels)
```sql
-- 知识节点
CREATE LABEL knowledge_node (
    node_id UUID,
    title TEXT,
    description TEXT,
    user_id UUID,
    embedding VECTOR(1536),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 用户节点
CREATE LABEL user_node (
    user_id UUID,
    name TEXT
);

-- 主题节点
CREATE LABEL subject_node (
    subject_id UUID,
    name TEXT,
    category TEXT
);
```

#### 关系类型 (Edge Types)
```sql
-- 知识关联
CREATE EDGE relates_to (
    strength FLOAT,
    relation_type TEXT
);

-- 用户掌握程度
CREATE EDGE mastered_by (
    mastery_level FLOAT,
    last_reviewed TIMESTAMP
);

-- 属于主题
CREATE EDGE belongs_to ();
```

#### 查询示例
```sql
-- 2度邻居查询
SELECT * FROM cypher('
    MATCH (u:user_node {user_id: $user_id})-[*1..2]-(n)
    RETURN n
') as (n agtype);

-- 相似知识查询
SELECT * FROM cypher('
    MATCH (k:knowledge_node)-[:relates_to]->(related)
    WHERE k.node_id = $node_id
    RETURN related ORDER BY related.similarity DESC
') as (related agtype);
```

## 集成到 Orchestrator

### 修改点

**文件**: `backend/app/orchestration/orchestrator_production.py`

**变更**:
```python
# 1. 导入 GraphKnowledgeService
from app.services.graph_knowledge_service import GraphKnowledgeService

# 2. 在 RAG 检索步骤使用 GraphRAG
knowledge_context = ""
if active_db and user_id:
    try:
        # 使用 GraphKnowledgeService 进行增强的 GraphRAG 检索
        graph_ks = GraphKnowledgeService(active_db)
        rag_result = await graph_ks.graph_rag_search(
            query=request.message,
            user_id=uuid.UUID(user_id),
            depth=2,
            top_k=5
        )
        knowledge_context = rag_result.get("context", "")

        # 记录 GraphRAG 指标
        logger.info(f"GraphRAG results: {rag_result['metadata']}")

    except Exception as e:
        logger.warning(f"GraphRAG failed: {e}, falling back to vector search")
        # 降级到普通向量检索
        ks = KnowledgeService(active_db)
        knowledge_context = await ks.retrieve_context(...)
```

### 降级策略

```
┌─────────────────────────────────────────┐
│  GraphRAG 检索流程                      │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  尝试 GraphRAG 检索                     │
│  (向量 + 图)                            │
└─────────────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
   成功      失败
    │         │
    ▼         ▼
┌───────┐  ┌──────────────────────────┐
│ 返回  │  │ 降级到向量检索            │
│ 结果  │  │ - KnowledgeService       │
└───────┘  │ - 保持兼容性             │
           └──────────────────────────┘
```

## 性能优化

### 1. 索引优化
```sql
-- 向量索引
CREATE INDEX ON knowledge_node USING ivfflat (embedding vector_cosine_ops);

-- 图索引
CREATE INDEX ON knowledge_node (node_id);
CREATE INDEX ON relates_to (from_node, to_node);
```

### 2. 查询优化
- **向量搜索**: 使用 pgvector 的 IVFFlat 索引
- **图遍历**: 限制深度 (max=2) 和结果数量 (top_k=5)
- **结果融合**: 使用去重和重排序减少冗余

### 3. 缓存策略
```python
# Redis 缓存
cache_key = f"graphrag:{hash(query)}:{user_id}"
result = await redis.get(cache_key)
if result:
    return json.loads(result)

# 计算结果并缓存
result = await compute_graphrag(query, user_id)
await redis.setex(cache_key, 3600, json.dumps(result))
```

## 监控和告警

### 健康检查指标

| 指标 | 阈值 | 严重程度 |
|------|------|----------|
| 图数据库连接 | - | Critical |
| 向量数据库连接 | - | Critical |
| 查询延迟 | > 2s | Warning |
| 同步队列长度 | > 1000 | Warning |
| 数据完整性 | 节点数=0 | Info |

### Prometheus 告警规则
```yaml
groups:
  - name: graph_rag_alerts
    rules:
      - alert: GraphDBDisconnected
        expr: graph_db_connection_status == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Graph database disconnected"

      - alert: HighSyncQueue
        expr: graph_rag_queue_length > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High sync queue volume"
```

## 部署和运维

### Docker Compose 配置
```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: sparkle
      POSTGRES_USER: sparkle
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/install_age.sh:/docker-entrypoint-initdb.d/install_age.sh

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  graph-sync-worker:
    build: ./backend
    command: python workers/graph_sync_worker.py
    environment:
      DATABASE_URL: postgresql://sparkle:${DB_PASSWORD}@postgres:5432/sparkle
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
```

### 初始化脚本
```bash
# 1. 安装 Apache AGE
./scripts/install_age.sh

# 2. 迁移数据
python scripts/migrate_to_age.py --full

# 3. 启动同步 Worker
python workers/graph_sync_worker.py

# 4. 验证安装
curl http://localhost:8000/api/v1/monitor/graph/health
```

## 测试策略

### 单元测试
- GraphRAGRetriever 的各个搜索方法
- GraphKnowledgeService 的双写逻辑
- GraphSyncWorker 的事件处理

### 集成测试
- 端到端 GraphRAG 流程
- 双写一致性验证
- 降级机制测试

### 性能测试
- 查询延迟 (< 2s)
- 并发写入 (10+ 并发)
- 内存使用 (< 1GB)

## 故障排查

### 常见问题

**1. 图数据库连接失败**
```bash
# 检查 Apache AGE 是否安装
SELECT * FROM pg_extension WHERE extname = 'age';

# 检查图标签
SELECT * FROM ag_label;
```

**2. 同步队列积压**
```bash
# 查看队列长度
redis-cli LLEN queue:graph_sync

# 手动触发同步
curl -X POST http://localhost:8000/api/v1/monitor/graph/sync/trigger?full_sync=true
```

**3. 查询性能慢**
```sql
-- 检查索引
SELECT * FROM pg_indexes WHERE tablename = 'knowledge_node';

-- 分析查询计划
EXPLAIN ANALYZE SELECT * FROM cypher('MATCH (n) RETURN n') as (n agtype);
```

## 未来优化方向

### 1. 智能图遍历
- 基于用户兴趣的动态深度
- 相关性加权遍历

### 2. 混合检索
- 结合全文搜索
- 多模态支持 (图片、音频)

### 3. 图学习
- 自动发现新关系
- 社区检测算法

### 4. 实时更新
- CDC (Change Data Capture)
- 增量图更新

## 总结

GraphRAG 系统通过结合向量检索和图检索，显著提升了知识检索的准确性和丰富度。关键优势:

1. **精准性**: 图结构提供语义关联
2. **可扩展**: 异步同步支持大规模数据
3. **高可用**: 自动降级和错误恢复
4. **可观测**: 完整的监控和告警体系

该系统已在生产环境部署，为 Sparkle 的 AI 学习助手提供强大的知识检索能力。
