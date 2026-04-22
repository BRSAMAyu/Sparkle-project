# 深度审计：Galaxy Knowledge Graph 完整链路

> 日期：2026-04-22 01:45
> 范围：`galaxy_service.py` 节点写入/读取 → `structure_service.py` 边管理 → `stats_service.py` 掌握度计算 → `retrieval_service.py` 语义搜索 → `galaxy_event_consumer.py` 事件消费 → `galaxy_handler.go` Go 网关 → Flutter Galaxy 模块 → Proto 定义 → DB schema（7 张核心表 + 索引）→ 上下文注入

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: Galaxy 事件消费器 handler 异常被吞没，知识图谱静默丢失更新
- **位置**: `backend/app/services/galaxy_event_consumer.py:170-171`
- **问题**: `_handle_error_created` 等 handler 在 try-except 中捕获所有异常后仅 log，不 re-raise。EventBus 的 `_consume_loop` 看到的是 handler 成功返回，于是执行 XACK 确认消息
  ```python
  # :170-171 — 异常被吞没
  except Exception as e:
      logger.error(f"Failed to handle error_created: {e}")
      # 没有 re-raise，EventBus 认为 handler 成功 → XACK → 消息永久丢失
  ```
- **对比**: `_handle_node_updated`（:185-262）同样无异常回滚保护，db.commit() 失败时事件已被 ACK
- **影响**: task.completed / error_created / SimulationGapRevealed 等事件触发的知识图谱掌握度更新静默丢失，用户完成任务后对应知识节点不更新掌握度
- **修复**: (1) handler 异常时 re-raise 让 EventBus DLQ 机制生效 (2) 或在 handler 内部实现独立的重试+回滚

#### P0-2: 知识图谱数据完全未注入 AI 对话上下文，Cognitive Core 对用户知识状态"盲视"
- **位置**: `backend/app/core/context_pack.py:405-805` (ContextPackBuilder.build) + `backend/app/orchestration/orchestrator.py:66` (未使用的 import)
- **问题**: ContextPackBuilder 构建的上下文中包含 preferences、goals、episodic_memories、plan_context，但**完全没有** galaxy/knowledge graph 数据
  ```python
  # context_pack.py — build() 方法包含的段:
  # ✅ preferences → memory_service.list_preference_records()
  # ✅ goals → memory_service.list_active_goals()
  # ✅ episodic → memory_service.list_recent_episodic()
  # ✅ plan_context → plan_context_builder
  # ❌ galaxy → 无任何调用
  ```
- **验证**: `orchestrator.py:66` 有 `from app.models.galaxy import KnowledgeNode` import 但标记 `# noqa: F401`（未使用）；`galaxy_service.py:559-598` 有 `build_evidence_pack()` 方法但从未在聊天流中被调用
- **影响**: AI 在对话中完全不知道用户学过什么、掌握度如何、哪些知识节点薄弱。这使 Dual-Core 架构中 Cognitive Core 的"Cognitive Prism"功能名存实亡——AI 无法基于知识图谱提供个性化指导
- **修复**: (1) 在 ContextPackBuilder 中添加 galaxy 段：提取用户最近学习的节点 + 掌握度分布 + 薄弱点 (2) 在 prompts.py 中添加知识图谱渲染模板

---

### P1 — 重要问题（5 项）

#### P1-1: knowledge_nodes.embedding 无 HNSW 索引，语义搜索全表扫描
- **位置**: `backend/gateway/internal/db/schema.sql:2216` (embedding 列定义) vs 缺少 HNSW 索引
- **问题**: `knowledge_nodes` 表有 `embedding vector(1024)` 列，但无 HNSW 索引
  ```sql
  -- schema.sql 中 cognitive_fragments 有 HNSW 索引:
  CREATE INDEX idx_cognitive_fragments_embedding_hnsw
  ON cognitive_fragments USING hnsw (embedding vector_cosine_ops);

  -- 但 knowledge_nodes 无对应索引
  ```
- **对比**: `retrieval_service.py:466-487` 使用 `KnowledgeNode.embedding.cosine_distance(query_embedding)` 做语义搜索，每次查询为顺序扫描
- **影响**: 知识图谱语义搜索 O(N) 复杂度，随节点数增长查询时间线性退化
- **修复**: 添加 `CREATE INDEX idx_knowledge_nodes_embedding_hnsw ON knowledge_nodes USING hnsw (embedding vector_cosine_ops) WHERE embedding IS NOT NULL`

#### P1-2: Go Gateway 未校验 mastery 值范围，可写入非法数据
- **位置**: `backend/gateway/internal/handler/galaxy_handler.go:143-217`
- **问题**: `UpdateMastery` handler 从 JSON 解析 mastery 值后直接转发到 Python，未校验范围
  ```go
  var req struct {
      Mastery int    `json:"mastery"`
      Reason  string `json:"reason"`
  }
  // 无: if req.Mastery < 0 || req.Mastery > 100 { return error }
  ```
- **影响**: 客户端可提交 mastery=-100 或 mastery=999，破坏掌握度计算逻辑和 BKT 模型参数
- **修复**: 在 Go handler 中添加 `req.Mastery` 范围校验 [0, 100]

#### P1-3: 边创建不校验源/目标节点存在性，可产生孤立边
- **位置**: `backend/app/services/galaxy/structure_service.py:83-91`
- **问题**: `create_edge()` 直接创建 NodeRelation 记录，未检查 source_id 和 target_id 是否存在
  ```python
  async def create_edge(self, user_id, source_id, target_id, relation_type):
      edge = NodeRelation(source_node_id=source_id, target_node_id=target_id, ...)
      self.db.add(edge)
      await self.db.commit()  # 依赖 FK 约束报错而非主动校验
  ```
- **影响**: 虽然有 FK 约束会阻止无效写入（报 500 而非 400），但缺乏用户友好的错误提示；无 FK 约束的场景可产生孤立记录
- **修复**: 添加节点存在性检查，返回 400 + 明确错误信息

#### P1-4: knowledge_nodes.name 无索引，关键词搜索性能差
- **位置**: `schema.sql:2206` (name 列) 无 trigram 或 btree 索引
- **问题**: `retrieval_service.py` 的 `keyword_search()` 按 name 搜索，无对应索引
- **修复**: 添加 `CREATE INDEX ix_knowledge_nodes_name_trgm ON knowledge_nodes USING gin(name gin_trgm_ops)` 或普通 btree 索引

#### P1-5: Plan → Galaxy 更新使用 Celery fire-and-forget，无完成确认
- **位置**: `backend/app/core/celery_app.py:519-662` (update_knowledge_galaxy task) + `backend/app/services/milestone_handler.py:140-150`
- **问题**: 里程碑完成时通过 Celery 异步更新知识图谱，max_retries=2，失败后无后续处理
  ```python
  # milestone_handler.py:140-150
  celery_app.send_task(
      "update_knowledge_galaxy",
      args=(str(user_id), str(plan_id), trigger_type),
      queue="default",
  )
  # 无回调、无状态追踪、无失败告警
  ```
- **影响**: Celery worker 异常或队列积压时，计划完成后的知识图谱更新永久丢失
- **修复**: 添加 Celery 任务状态追踪 + 失败告警

---

### P2 — 改进建议（3 项）

#### P2-1: AGE 图数据库已配置但未使用，架构与文档不一致
- **位置**: `schema.sql:30-49` (AGE extension + sparkle_galaxy schema) + `CLAUDE.md` ("Graph: Apache AGE")
- **问题**: CLAUDE.md 声明使用 "Apache AGE (sparkle_galaxy schema)" 做图查询，但实际所有图谱操作使用 PostgreSQL 关系表 + pgvector。AGE 扩展已加载且创建了 APPLICATION/APPLIES_TO/INTERESTED_IN 标签表，但从未被查询
- **影响**: 图遍历能力受限（仅支持直接邻居查询，无递归遍历）；文档与实现不一致
- **修复**: (1) 如计划使用 AGE：迁移核心遍历逻辑到 Cypher (2) 如不使用：移除 AGE 依赖，更新文档

#### P2-2: Go Gateway Galaxy 路由重复注册
- **位置**: `galaxy_handler.go:58-98`
- **问题**: 同时注册 `/node/:id/spark` 和 `/nodes/:id/spark`（单数+复数形式），相同 handler 绑定两次
- **修复**: 统一为复数形式 `/nodes/:id/...`

#### P2-3: user_node_status.node_id 缺失 FK 约束
- **位置**: `schema.sql:4257`
- **问题**: `user_node_status.node_id` 无 `REFERENCES knowledge_nodes(id)` 外键约束，删除知识节点后孤立状态记录残留
- **修复**: 添加 FK 约束 + ON DELETE CASCADE

---

### 合规项（5 项）

1. **掌握度更新乐观锁** ✅ — `galaxy_service.py:673-731` 使用 CTE + `FOR UPDATE` + revision 号实现原子更新，冲突时返回 `{success: False, reason: "conflict"}`
2. **事件 Outbox 模式** ✅ — `_write_mastery_outbox_event()` 使用 `event_sequence_counters` + `event_outbox` 双表保证事件有序持久化
3. **双写策略** ✅ — 掌握度变更同时写入 Redis Event Bus（实时）+ event_outbox（持久化）
4. **FK 约束** ✅ — `node_relations` 表的 source/target 均有 FK 到 `knowledge_nodes(id)`；`mastery_audit_log` 有 FK + ON DELETE CASCADE
5. **Flutter 兼容** ✅ — `GalaxyGraphResponse` 同时返回 `relations` 和 `edges` 字段（Flutter 期望 `edges`），节点模型字段映射完整

---

## 数据流图

```
Plan 里程碑完成 / Task 完成 / 错题创建
  │
  ├── [路径 A: Celery 异步] (plan → galaxy)
  │   ├── milestone_handler.py → celery_app.send_task("update_knowledge_galaxy")
  │   └── celery_app.py:519-662 → _extract_plan_concepts() → create_node/update_mastery
  │       ⚠️ fire-and-forget, 无完成确认 (P1-5)
  │
  ├── [路径 B: Event Bus] (task/error → galaxy)
  │   ├── task.completed / error_created → Redis Stream
  │   ├── galaxy_event_consumer.py → _handle_task_completed / _handle_error_created
  │   │   ├── 调用 stats_service.spark_node() → 更新掌握度
  │   │   ├── 调用 galaxy_service.update_node_mastery()
  │   │   └── ⚠️ 异常被吞没 → XACK → 数据丢失 (P0-1)
  │   └── 成功时:
  │       ├── → KnowledgeNodeUpdated → Redis Event Bus
  │       └── → event_outbox (持久化) ✅
  │
  ├── [路径 C: 直接 API] (用户手动)
  │   ├── Flutter → Go Gateway (galaxy_handler.go)
  │   │   ├── POST /nodes/:id/spark → SparkNode
  │   │   ├── POST /nodes/:id/mastery → UpdateMastery ⚠️ 无范围校验 (P1-2)
  │   │   └── GET /graph /search /nodes/:id → ProxyToBackend
  │   └── Go → Python galaxy_service.py
  │
  ↓ 知识图谱数据已写入 DB
  │
  ├── [写入存储]
  │   ├── knowledge_nodes (节点 + embedding) ⚠️ 无 HNSW 索引 (P1-1)
  │   ├── node_relations (边) ⚠️ 创建无校验 (P1-3)
  │   ├── user_node_status (掌握度 + BKT) ✅ 乐观锁保护
  │   └── mastery_audit_log (审计日志) ✅ 完整索引
  │
  ├── [读取路径 — AI 对话]
  │   ├── ContextPackBuilder.build()
  │   │   ├── ✅ preferences, goals, episodic
  │   │   └── ❌ 无 galaxy 数据 (P0-2)
  │   ├── orchestrator.py
  │   │   └── ❌ KnowledgeNode import 未使用 (P0-2)
  │   └── build_evidence_pack() 存在但未调用 (P0-2)
  │
  ├── [读取路径 — Flutter Galaxy 地图]
  │   ├── GET /galaxy/graph → GalaxyService.get_galaxy_graph()
  │   │   └── GraphStructureService + GalaxyStatsService → nodes + edges + stats
  │   ├── GET /galaxy/search → hybrid_search()
  │   │   └── Redis Search hybrid (BM25 + vector) / fallback pgvector ⚠️ 无 HNSW
  │   └── Flutter galaxy_model.dart → 字段映射完整 ✅
  │
  ↓
  用户看到: Galaxy 地图可视化 ✅  AI 看到: 零知识图谱信息 ❌
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 事件消费器吞没异常 | handler re-raise + EventBus DLQ 生效 | 低（~10 行 Python） |
| P0-2 | 知识图谱未注入 AI 上下文 | ContextPackBuilder 添加 galaxy 段 + prompts.py 渲染 | 中（~60 行 Python） |
| P1-1 | knowledge_nodes 无 HNSW 索引 | 添加 HNSW 索引 | 低（1 条 DDL） |
| P1-2 | mastery 无范围校验 | Go handler 添加 [0,100] 校验 | 低（~5 行 Go） |
| P1-3 | 边创建无节点存在性校验 | 添加 existence check | 低（~10 行 Python） |
| P1-4 | knowledge_nodes.name 无索引 | 添加 trigram 或 btree 索引 | 低（1 条 DDL） |
| P1-5 | Celery fire-and-forget | 添加状态追踪 + 失败告警 | 中（~40 行 Python） |
