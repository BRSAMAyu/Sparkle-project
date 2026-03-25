# Sparkle 后端数据链路验收报告

**验收日期**: 2026-03-16
**验收范围**: RAG、Embedding、Reranking、Redis Search、PostgreSQL pgvector、读写分离
**验收人**: Claude (AI 架构师)

---

## 📊 总体评估

**通过率**: 5/9 (55.6%)
**状态**: ⚠️ **部分通过，存在关键问题需修复**

---

## ✅ 正常运行的功能 (5/9)

### 1. ✅ Redis 连接
- **状态**: 正常
- **延迟**: <10ms
- **内存使用**: 973.94K
- **问题**: Redis Search 模块未加载

### 2. ✅ Embedding 服务
- **状态**: 正常
- **延迟**: 293ms
- **维度**: 1024 (符合配置)
- **Provider**: DashScope (阿里云)

### 3. ✅ Rerank 服务
- **状态**: 正常
- **延迟**: 278ms
- **Provider**: DashScope
- **功能**: 正确排序相关结果

### 4. ✅ GraphRAG 检索流程
- **状态**: 框架正常
- **延迟**: 658ms
- **问题**: 无数据导致返回空结果，但流程完整

### 5. ✅ 缓存一致性
- **状态**: 正常
- **Redis 缓存读写一致**

---

## ❌ 存在问题的功能 (4/9)

### 1. ❌ PostgreSQL 连接 (关键问题)
**错误**: `connect() got an unexpected keyword argument 'sslmode'`

**根因分析**:
- asyncpg 0.31.0 版本中 `connect()` 函数不接受 `sslmode` 参数
- 代码位置: `app/db/session.py:_get_engine_kwargs()`
- 问题代码试图将 `sslmode` 传递给 asyncpg 的 `connect_args`

**影响**: 所有数据库操作失败

**修复方案**:
```python
# app/db/session.py line 29-65
# 当前错误代码:
if sslmode:
    if sslmode == "disable":
        connect_args["ssl"] = False
    elif sslmode in ("require", "verify-ca", "verify-full"):
        connect_args["ssl"] = True

# asyncpg 0.31.0 不支持在 connect_args 中传递 sslmode
# 需要使用 create_engine 的 connect_args 参数或 URL 参数
```

**建议修复**:
1. 将 SSL 配置添加到 DATABASE_URL 查询参数中
2. 或使用 `create_async_engine` 的 `connect_args` 适配 asyncpg 0.31+

### 2. ❌ 向量搜索 (数据问题)
**问题**: 数据库中没有带向量的知识节点

**根因**:
- `knowledge_nodes` 表存在且可访问
- 但 `embedding` 列全部为 NULL
- 需要运行 embedding 生成任务

**修复方案**:
```bash
# 1. 检查是否有知识节点
SELECT COUNT(*) FROM knowledge_nodes;

# 2. 为现有节点生成 embedding
python scripts/backfill_embeddings.py

# 3. 或在创建节点时自动生成 embedding (已有代码但未执行)
```

### 3. ❌ Redis 混合搜索 (配置问题)
**问题**: Redis Search 索引不存在

**根因**:
- Redis 未安装 RediSearch 模块
- 或索引未初始化

**修复方案**:
```bash
# 方案1: 使用带 RediSearch 的 Redis 镜像
docker run -d -p 6379:6379 redislabs/redisearch:latest

# 方案2: 初始化索引
python scripts/init_redis_index.py
python scripts/init_semantic_cache_index.py

# 方案3: 使用 Redis Stack (推荐)
docker run -d -p 6379:6379 redis/redis-stack-server:latest
```

### 4. ❌ 读写分离 (架构问题)
**问题**: 未配置读副本

**根因**:
- 代码中没有 `DATABASE_READ_REPLICA_URL` 配置
- 所有读写操作都在主库
- 无读副本相关代码

**当前状态**: 单数据库架构
**影响**: 高负载下可能影响性能
**优先级**: 中 (可根据实际负载决定)

---

## ⚠️ 警告与风险

### 1. AGE (Apache AGE) 图数据库
**警告**: `function cypher(unknown, unknown) does not exist`

**问题**: PostgreSQL 未安装 AGE 扩展或未启用
**影响**: GraphRAG 的图检索功能无法使用
**修复**:
```sql
CREATE EXTENSION age;
LOAD 'age';
SELECT age.initialize();
```

### 2. Redis Search 模块
**警告**: Redis Search 模块未加载

**影响**:
- 语义缓存不可用
- 混合搜索降级为纯向量搜索
- 性能可能下降

### 3. LLM 服务调用错误
**错误**: `message must be json_object`

**问题**: GraphRAG 实体提取时 LLM 调用格式错误
**影响**: 实体提取失败，但降级到简单关键词提取
**优先级**: 低 (有降级方案)

---

## 🔧 优先修复清单

### 🔴 P0 (立即修复)
1. **修复 asyncpg SSL 连接问题** (app/db/session.py)
   - 影响: 所有数据库操作
   - 修复时间: 30分钟

### 🟡 P1 (今日修复)
2. **初始化 Redis Search 索引**
   - 影响: 混合搜索、语义缓存
   - 修复时间: 15分钟

3. **回填知识节点 embedding**
   - 影响: 向量搜索
   - 修复时间: 1小时

### 🟢 P2 (本周完成)
4. **安装/启用 PostgreSQL AGE 扩展**
   - 影响: 图检索功能
   - 修复时间: 30分钟

5. **修复 LLM 实体提取调用格式**
   - 影响: GraphRAG 实体提取准确性
   - 修复时间: 20分钟

### ⚪ P3 (可选优化)
6. **实现读写分离** (架构级改造)
   - 影响: 高并发性能
   - 修复时间: 2-3天

---

## 📈 数据链路健康度评分

| 维度 | 评分 | 说明 |
|------|------|------|
| **可用性** | 4/10 | PostgreSQL 连接失败导致核心功能不可用 |
| **完整性** | 7/10 | Embedding/Rerank 服务正常，但数据缺失 |
| **性能** | 6/10 | 服务响应时间正常，但缺乏优化 |
| **可靠性** | 5/10 | 有降级方案，但核心路径不稳定 |
| **可扩展性** | 4/10 | 无读写分离，高并发下可能瓶颈 |

**综合评分**: **5.2/10** (需要关注)

---

## 🎯 建议行动计划

### 立即行动 (今天)
1. 修复 asyncpg 连接问题
2. 验证数据库连接
3. 初始化 Redis Search 索引

### 短期计划 (本周)
1. 回填历史数据 embedding
2. 启用 PostgreSQL AGE 扩展
3. 修复 LLM 调用格式
4. 完善监控和告警

### 中期计划 (本月)
1. 评估读写分离需求
2. 优化向量检索性能
3. 实施缓存预热策略

---

## 📝 附件

### 测试环境
- Python: 3.11
- asyncpg: 0.31.0
- Redis: (未知版本，无 Search 模块)
- PostgreSQL: (连接失败，无法获取版本)

### 配置参数
- EMBEDDING_DIM: 1024
- RERANK_TIMEOUT_SECONDS: 2.5
- REDIS_HYBRID_TIMEOUT_SECONDS: 2.0
- ENABLE_REDIS_HYBRID_FALLBACK: False
- GRAPHRAG_CACHE_TTL_SECONDS: 120

---

**报告生成时间**: 2026-03-16 10:37:53 UTC
**下次验收建议**: 修复 P0/P1 问题后重新验收
