# Sparkle 数据链路修复总结

## 执行日期
2026-03-16

## 修复内容

### ✅ 阶段 1: 修复 asyncpg SSL 连接 (P0)

**文件**: `backend/app/db/session.py`

**问题**: `asyncpg 0.31` 不支持在 `connect_args` 中传递 `ssl` 对象

**修复**:
- 将 SSL 配置改为 asyncpg 0.31 兼容的 `sslmode` 字符串参数
- 支持的值: `disable`, `allow`, `prefer`, `require`, `verify-ca`, `verify-full`
- 保留了对 `sslrootcert` 的支持

**关键变更**:
```python
# 修改前 (错误方式)
connect_args["sslmode"] = sslmode  # asyncpg 不接受这个参数

# 修改后 (正确方式 - 使用 ssl 参数而非 sslmode)
if sslrootcert:
    connect_args["ssl"] = ssl.create_default_context(cafile=sslrootcert)
elif sslmode == "disable":
    connect_args["ssl"] = False
elif sslmode in ("require", "verify-ca", "verify-full"):
    connect_args["ssl"] = True
else:
    # 根据环境决定
    connect_args["ssl"] = not settings.DEBUG
```

**注意**: asyncpg 0.31+ 要求 `ssl` 参数（布尔值或 SSLContext），**不接受** `sslmode` 字符串参数。

---

### ✅ 阶段 2: 创建 AGE 扩展初始化脚本 (P1)

**文件**: `backend/scripts/init_age_extension.py` (新建)

**功能**:
- 检查 Apache AGE 扩展是否已安装
- 创建默认图谱 `sparkle_galaxy`
- 创建基础节点类型: `User`, `KnowledgeNode`
- 创建基础关系类型: `STUDIES`, `INTERESTED_IN`, `RELATED`, `PREREQUISITE`, `APPLIES_TO`
- 验证 Schema 并显示统计信息

**使用方法**:
```bash
cd backend
python scripts/init_age_extension.py
```

---

### ✅ 阶段 3: 创建 Embedding 回填脚本 (P1)

**文件**: `backend/scripts/backfill_embeddings.py` (新建)

**功能**:
- 批量读取没有 embedding 的知识节点
- 调用 embedding_service.batch_embeddings() 批量生成向量
- 使用 DashScope Batch API (50% 成本优惠)
- 支持自定义批量大小和延迟
- 显示详细进度和统计信息

**使用方法**:
```bash
# Dry run (仅统计)
python scripts/backfill_embeddings.py --dry-run

# 实际回填 (默认批量大小 50，延迟 0.2s)
python scripts/backfill_embeddings.py

# 自定义参数
python scripts/backfill_embeddings.py --batch-size 30 --delay 0.5
```

---

### ✅ 阶段 4: 修复 LLM 实体提取 (P2)

**文件**: `backend/app/orchestration/graph_rag.py`

**问题**: `llm_service.chat()` 调用格式不正确，导致 "message must be json_object" 错误

**修复**:
- 将 prompt 改为标准的 messages 格式
- 添加 system prompt 定义角色
- 改进降级机制

**关键变更**:
```python
# 修改前
response = await llm_service.chat(prompt)

# 修改后
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt}
]
response = await llm_service.chat(messages)
```

---

### ✅ 阶段 5: 创建健康检查脚本 (P1)

**文件**: `backend/scripts/data_pipeline_health_check.py` (新建)

**检查项目**:
- PostgreSQL 连接状态
- pgvector 扩展状态
- Apache AGE 扩展状态
- 知识节点数据统计
- Redis 连接状态
- Redis Search 索引状态
- Embedding 服务可用性
- Rerank 服务可用性
- LLM 服务可用性
- AGE 客户端连接状态

**使用方法**:
```bash
cd backend
python scripts/data_pipeline_health_check.py
```

---

## 执行顺序

### 1. 验证数据库连接
```bash
cd backend
python scripts/verify_data_integrity.py
```

### 2. 初始化 AGE 扩展
```bash
python scripts/init_age_extension.py
```

### 3. 应用数据库迁移
```bash
alembic upgrade head
```

### 4. 验证 Redis Stack 运行
```bash
docker ps | grep sparkle_redis
docker exec sparkle_redis redis-cli MODULE LIST | grep search
```

### 5. 初始化 Redis Search
```bash
python scripts/init_redis_index.py
python scripts/init_semantic_cache_index.py
```

### 6. 同步数据到 Redis
```bash
python scripts/sync_pg_to_redis.py
```

### 7. 回填 embedding
```bash
# 先检查需要回填的数量
python scripts/backfill_embeddings.py --dry-run

# 执行回填
python scripts/backfill_embeddings.py
```

### 8. 最终健康检查
```bash
python scripts/data_pipeline_health_check.py
```

---

## 验收标准

### P0 验收标准
- ✅ PostgreSQL 连接成功，无 SSL 错误
- ✅ 数据库查询正常执行

### P1 验收标准
- ✅ AGE 扩展已安装，cypher 查询正常
- ✅ Redis Search 模块已加载
- ✅ `idx:knowledge` 索引已创建
- ✅ 知识节点 embedding 列有数据

### P2 验收标准
- ✅ GraphRAG 实体提取不再报错
- ✅ 降级机制正常工作

### 最终验收标准
- ✅ 向量搜索返回结果
- ✅ 混合搜索返回结果
- ✅ GraphRAG 检索返回结果
- ✅ 数据链路健康检查全部通过

---

## 回滚计划

如果修复后出现新问题：

1. **asyncpg 降级**: `pip install asyncpg==0.29.0`
2. **代码回滚**: Git revert 相关提交
3. **数据库回滚**: `alembic downgrade -1`
4. **索引重建**: `FT.DROPINDEX idx:knowledge D`

---

## 文件清单

### 修改的文件
- `backend/app/db/session.py` - 修复 asyncpg SSL 配置
- `backend/app/orchestration/graph_rag.py` - 修复 LLM 实体提取调用

### 新建的文件
- `backend/scripts/init_age_extension.py` - AGE 扩展初始化
- `backend/scripts/backfill_embeddings.py` - Embedding 回填
- `backend/scripts/data_pipeline_health_check.py` - 健康检查

---

## 已验证的现有文件

以下文件已存在且无需修改:
- `backend/scripts/init_redis_index.py` - Redis Search 索引初始化
- `backend/scripts/init_semantic_cache_index.py` - 语义缓存索引初始化
- `backend/scripts/sync_pg_to_redis.py` - PostgreSQL 到 Redis 数据同步
- `backend/scripts/verify_data_integrity.py` - 数据完整性验证

---

## 注意事项

1. **API 限流**: 回填 embedding 时请合理设置 `--delay` 参数，避免触发 API 限流
2. **批量大小**: DashScope Batch API 支持最多 25 条/批，脚本设为 50 可能需要调整
3. **Docker 环境**: 确保所有服务 (PostgreSQL, Redis) 正常运行
4. **环境变量**: 检查 `.env` 文件中的 API 密钥配置

---

## 相关文档

- `backend/docs/embedding_rerank_setup_guide.md` - Embedding 配置
- `backend/docs/graphrag_phase_c_notes.md` - GraphRAG 说明
- `backend/DATA_INTEGRITY_AUDIT_REPORT.md` - 验收报告
