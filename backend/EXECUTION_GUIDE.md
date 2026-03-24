# 🚀 Sparkle 数据链路修复执行指南

## 前置检查

```bash
# 1. 确认 Docker 服务运行
docker compose ps

# 2. 确认 Python 环境 (需要 Python 3.10+)
python --version

# 3. 进入 backend 目录
cd backend
```

---

## 修复流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    开始数据链路修复                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 修复 asyncpg SSL 连接 (已完成)                          │
│   文件: app/db/session.py                                        │
│   状态: ✅ 代码已修改                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 验证数据库连接                                           │
│   命令: python scripts/verify_data_integrity.py                 │
│   预期: PostgreSQL 连接成功                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 初始化 AGE 扩展                                          │
│   命令: python scripts/init_age_extension.py                   │
│   预期: 创建图谱 sparkle_galaxy 和基础 Schema                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: 应用数据库迁移                                           │
│   命令: alembic upgrade head                                    │
│   预期: 所有迁移已应用                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: 验证 Redis Stack                                         │
│   命令: docker exec sparkle_redis redis-cli MODULE LIST          │
│   预期: search 模块已加载                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: 初始化 Redis Search                                      │
│   命令: python scripts/init_redis_index.py                     │
│         python scripts/init_semantic_cache_index.py            │
│   预期: idx:knowledge 和 idx:embeddings 索引已创建              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 7: 同步数据到 Redis                                         │
│   命令: python scripts/sync_pg_to_redis.py                     │
│   预期: 知识节点数据已同步到 Redis                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 8: 回填 Embedding                                           │
│   命令: python scripts/backfill_embeddings.py                  │
│   预期: 所有知识节点都有 embedding 向量                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 9: 最终健康检查                                             │
│   命令: python scripts/data_pipeline_health_check.py           │
│   预期: 所有检查项通过                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    🎉 修复完成！                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 快速执行命令

```bash
# 一键执行所有步骤 (复制粘贴整个块)
cd backend && \
echo "=== Step 1: 验证数据库连接 ===" && \
python scripts/verify_data_integrity.py && \
echo -e "\n=== Step 2: 初始化 AGE 扩展 ===" && \
python scripts/init_age_extension.py && \
echo -e "\n=== Step 3: 应用数据库迁移 ===" && \
alembic upgrade head && \
echo -e "\n=== Step 4: 验证 Redis Stack ===" && \
docker exec sparkle_redis redis-cli MODULE LIST | grep search && \
echo -e "\n=== Step 5: 初始化 Redis Search ===" && \
python scripts/init_redis_index.py && \
python scripts/init_semantic_cache_index.py && \
echo -e "\n=== Step 6: 同步数据到 Redis ===" && \
python scripts/sync_pg_to_redis.py && \
echo -e "\n=== Step 7: 回填 Embedding ===" && \
python scripts/backfill_embeddings.py && \
echo -e "\n=== Step 8: 最终健康检查 ===" && \
python scripts/data_pipeline_health_check.py
```

---

## 分步详细说明

### Step 1: 验证数据库连接

```bash
python scripts/verify_data_integrity.py
```

**输出示例**:
```
🔍 验证 PostgreSQL 连接...
✅ PostgreSQL 连接成功: PostgreSQL 15.x...
✅ pgvector 扩展已安装
✅ knowledge_nodes 表存在
```

**如果失败**:
- 检查 Docker 容器状态: `docker compose ps`
- 检查数据库配置: `.env` 文件中的 `DATABASE_URL`

---

### Step 2: 初始化 AGE 扩展

```bash
python scripts/init_age_extension.py
```

**输出示例**:
```
🔍 检查 Apache AGE 扩展状态
✅ Apache AGE 扩展已安装
   版本: 1.5.0

🚀 初始化 AGE 图谱 Schema
✅ AGE 客户端已连接
[1/3] 创建默认图谱...
   ✅ 图谱 'sparkle_galaxy' 已创建
[2/3] 创建基础节点类型...
   ✅ 节点类型: User
   ✅ 节点类型: KnowledgeNode
[3/3] 创建基础关系类型...
   ✅ 关系类型: STUDIES
   ✅ 关系类型: INTERESTED_IN
```

**如果失败**:
- AGE 未安装: 需要在 docker-compose.yml 中添加 AGE 扩展
- 参考: https://age.apache.org/install

---

### Step 3: 应用数据库迁移

```bash
alembic upgrade head
```

**输出示例**:
```
INFO  [alembic.runtime.migration] Running upgrade -> xxx_add_embedding_column
```

**如果失败**:
- 检查迁移文件: `backend/alembic/versions/`
- 手动检查数据库: `docker exec -it sparkle_db psql -U sparkle -c "\dt"`

---

### Step 4: 验证 Redis Stack

```bash
docker exec sparkle_redis redis-cli MODULE LIST | grep search
```

**预期输出**:
```
search
```

**如果失败**:
- 检查 Redis 镜像: 需要使用 `redis/redis-stack-server:latest`
- 重建容器: `docker compose up -d --force-recreate redis`

---

### Step 5: 初始化 Redis Search

```bash
python scripts/init_redis_index.py
python scripts/init_semantic_cache_index.py
```

**输出示例**:
```
Connecting to Redis...
Index 'idx:knowledge' already exists. Dropping to update schema...
Creating index 'idx:knowledge'...
Index 'idx:knowledge' created successfully!
```

---

### Step 6: 同步数据到 Redis

```bash
python scripts/sync_pg_to_redis.py
```

**输出示例**:
```
🚀 Starting PG -> Redis Sync...
✅ Redis connected.
📦 Fetching KnowledgeNodes from DB...
📊 Found 150 nodes with descriptions.
🔄 Synced 100 chunks...
🔄 Synced 200 chunks...
✅ Sync complete! Total chunks indexed: 234
```

---

### Step 7: 回填 Embedding

```bash
# 先检查需要回填的数量
python scripts/backfill_embeddings.py --dry-run

# 执行回填
python scripts/backfill_embeddings.py
```

**输出示例**:
```
🚀 开始回填知识节点 Embedding
📊 节点统计:
   总节点数: 150
   需要 embedding: 150

⚙️  配置:
   批量大小: 50
   延迟: 0.2s

🔄 处理批次 1 (50 个节点)...
   ✅ 已更新: 50 个节点
🔄 处理批次 2 (50 个节点)...
   ✅ 已更新: 50 个节点
🔄 处理批次 3 (50 个节点)...
   ✅ 已更新: 50 个节点

📊 回填完成统计
总节点数: 150
需要处理: 150
已更新: 150
错误: 0
耗时: 45.23s
平均: 0.301s/节点
```

---

### Step 8: 最终健康检查

```bash
python scripts/data_pipeline_health_check.py
```

**输出示例**:
```
🔍 数据链路健康检查

============================================================
📊 检查结果摘要
============================================================

通过率: 10/10 (100%)

✅ PostgreSQL 连接 (0.023s)
   ℹ️  版本: PostgreSQL 15.x...

✅ pgvector 扩展 (0.015s)
   ℹ️  已安装 (版本: 0.5.0)

✅ Apache AGE 扩展 (0.034s)
   ℹ️  已安装 (版本: 1.5.0)
   ℹ️  默认图谱 'sparkle_galaxy' 存在

✅ 知识节点数据 (0.028s)
   ℹ️  总节点数: 150
   ℹ️  有 embedding: 150 (100.0%)
   ℹ️  有描述: 150 (100.0%)

✅ Redis 连接 (0.012s)
   ℹ️  连接成功
   ℹ️  内存使用: 45.2M
   ℹ️  已加载模块: 8 个

✅ Redis Search 索引 (0.018s)
   ℹ️  idx:knowledge 存在 (文档数: 234)

✅ Embedding 服务 (1.234s)
   ℹ️  正常 (维度: 1024)

✅ Rerank 服务 (0.876s)
   ℹ️  正常 (返回: 2 条)

✅ LLM 服务 (1.456s)
   ℹ️  正常 (响应: 42 字符)

✅ AGE 客户端 (0.045s)
   ℹ️  连接正常
   ℹ️  图谱中的节点: 150

============================================================
🎉 数据链路健康检查通过！
============================================================
```

---

## 故障排除

### 问题 1: asyncpg SSL 连接失败

**错误信息**: `connect() got an unexpected keyword argument 'sslmode'`

**解决方案**: 已通过修改 `app/db/session.py` 修复

---

### 问题 2: AGE 扩展未安装

**错误信息**: `Apache AGE 扩展未安装`

**解决方案**: 在 docker-compose.yml 中添加 AGE 扩展配置

```yaml
services:
  db:
    image: postgres:15
    command:
      - postgres
      - -c
      - shared_preload_libraries=age
```

---

### 问题 3: Redis Search 模块未加载

**错误信息**: `Redis Search 模块未加载`

**解决方案**: 确保使用 Redis Stack 镜像

```yaml
services:
  redis:
    image: redis/redis-stack-server:latest
```

---

### 问题 4: Embedding API 限流

**错误信息**: `DashScope API rate limit exceeded`

**解决方案**: 增加延迟参数

```bash
python scripts/backfill_embeddings.py --batch-size 25 --delay 1.0
```

---

## 验证清单

- [ ] PostgreSQL 连接成功
- [ ] pgvector 扩展已安装
- [ ] AGE 扩展已安装
- [ ] AGE 图谱已创建
- [ ] Redis Search 模块已加载
- [ ] Redis Search 索引已创建
- [ ] 数据已同步到 Redis
- [ ] 知识节点 embedding 已回填
- [ ] Embedding 服务正常
- [ ] Rerank 服务正常
- [ ] LLM 服务正常
- [ ] 健康检查全部通过

---

## 相关文档

- `DATA_PIPELINE_REPAIR_SUMMARY.md` - 修复总结
- `DATA_INTEGRITY_AUDIT_REPORT.md` - 验收报告
- `docs/embedding_rerank_setup_guide.md` - Embedding 配置
- `docs/graphrag_phase_c_notes.md` - GraphRAG 说明
