# 📋 数据链路修复命令速查表

## 完整修复流程

```bash
# 进入 backend 目录
cd backend

# 1. 验证数据库连接
python scripts/verify_data_integrity.py

# 2. 初始化 AGE 扩展
python scripts/init_age_extension.py

# 3. 应用数据库迁移
alembic upgrade head

# 4. 验证 Redis Stack
docker exec sparkle_redis redis-cli MODULE LIST | grep search

# 5. 初始化 Redis Search
python scripts/init_redis_index.py
python scripts/init_semantic_cache_index.py

# 6. 同步数据到 Redis
python scripts/sync_pg_to_redis.py

# 7. 回填 Embedding
python scripts/backfill_embeddings.py --dry-run  # 先检查
python scripts/backfill_embeddings.py           # 执行回填

# 8. 最终健康检查
python scripts/data_pipeline_health_check.py
```

---

## 单独命令

### 数据库相关

```bash
# 验证数据库连接
python scripts/verify_data_integrity.py

# 应用数据库迁移
alembic upgrade head

# 回滚最近的迁移
alembic downgrade -1

# 查看迁移历史
alembic history

# 查看当前迁移版本
alembic current
```

### AGE 扩展相关

```bash
# 初始化 AGE 扩展
python scripts/init_age_extension.py

# 初始化图谱 Schema
python scripts/init_graph_schema.py
```

### Redis 相关

```bash
# 验证 Redis Stack 模块
docker exec sparkle_redis redis-cli MODULE LIST

# 初始化知识节点索引
python scripts/init_redis_index.py

# 初始化语义缓存索引
python scripts/init_semantic_cache_index.py

# 同步 PostgreSQL 数据到 Redis
python scripts/sync_pg_to_redis.py

# 清空 Redis 数据
docker exec sparkle_redis redis-cli FLUSHALL
```

### Embedding 相关

```bash
# 检查需要回填的节点数量
python scripts/backfill_embeddings.py --dry-run

# 回填 embedding (默认批量大小 50，延迟 0.2s)
python scripts/backfill_embeddings.py

# 自定义批量大小和延迟
python scripts/backfill_embeddings.py --batch-size 25 --delay 0.5
```

### 健康检查

```bash
# 完整数据链路健康检查
python scripts/data_pipeline_health_check.py

# 数据完整性验证
python scripts/verify_data_integrity.py
```

---

## Docker 命令

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 重启特定服务
docker compose restart db
docker compose restart redis

# 查看服务状态
docker compose ps

# 查看服务日志
docker compose logs -f db
docker compose logs -f redis

# 进入 PostgreSQL 容器
docker exec -it sparkle_db psql -U sparkle

# 进入 Redis 容器
docker exec -it sparkle_redis redis-cli

# 重建特定服务
docker compose up -d --force-recreate redis
```

---

## PostgreSQL 查询

```bash
# 连接到数据库
docker exec -it sparkle_db psql -U sparkle -d sparkle

# 查看所有表
\dt

# 查看知识节点数量
SELECT COUNT(*) FROM knowledge_nodes;

# 查看有 embedding 的节点数量
SELECT COUNT(*) FROM knowledge_nodes WHERE embedding IS NOT NULL;

# 查看扩展
SELECT * FROM pg_extension WHERE extname IN ('vector', 'age');

# 查看 AGE 图谱
SELECT * FROM ag_graph;

# 退出
\q
```

---

## Redis 命令

```bash
# 连接到 Redis
docker exec -it sparkle_redis redis-cli

# 查看所有键
KEYS *

# 查看索引信息
FT.INFO idx:knowledge
FT.INFO idx:embeddings

# 搜索测试
FT.SEARCH idx:knowledge "Python" LIMIT 0 5

# 查看内存使用
INFO memory

# 清空数据
FLUSHALL

# 退出
exit
```

---

## 故障排除命令

```bash
# 检查 asyncpg 版本
pip show asyncpg

# 降级 asyncpg (如果需要)
pip install asyncpg==0.29.0

# 检查 Python 版本
python --version

# 检查环境变量
cat .env | grep -E "(DATABASE_URL|REDIS_URL|DASHSCOPE_API_KEY)"

# 测试数据库连接
docker exec sparkle_db pg_isready -U sparkle

# 测试 Redis 连接
docker exec sparkle_redis redis-cli PING
```

---

## 快速诊断

```bash
# 一键检查所有服务状态
docker compose ps && \
echo "--- PostgreSQL ---" && \
docker exec sparkle_db pg_isready -U sparkle && \
echo "--- Redis ---" && \
docker exec sparkle_redis redis-cli PING && \
echo "--- Python ---" && \
python --version
```

---

## 文件位置

```
backend/
├── app/
│   ├── db/
│   │   └── session.py              # asyncpg SSL 修复
│   └── orchestration/
│       └── graph_rag.py            # LLM 实体提取修复
├── scripts/
│   ├── init_age_extension.py       # AGE 扩展初始化 (新建)
│   ├── backfill_embeddings.py      # Embedding 回填 (新建)
│   ├── data_pipeline_health_check.py  # 健康检查 (新建)
│   ├── init_redis_index.py         # Redis 索引初始化
│   ├── init_semantic_cache_index.py
│   ├── sync_pg_to_redis.py         # 数据同步
│   └── verify_data_integrity.py    # 数据验证
└── DATA_PIPELINE_REPAIR_SUMMARY.md # 修复总结
```

---

## 环境变量检查清单

```bash
# 必需的环境变量
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
DASHSCOPE_API_KEY=sk-...
```

---

## 时间估算

| 步骤 | 预计时间 |
|------|---------|
| 验证数据库连接 | 5s |
| 初始化 AGE 扩展 | 10s |
| 应用数据库迁移 | 15s |
| 初始化 Redis Search | 5s |
| 同步数据到 Redis | 30s-2min (取决于数据量) |
| 回填 Embedding | 2-10min (取决于节点数量) |
| 健康检查 | 10s |
| **总计** | **3-15min** |
