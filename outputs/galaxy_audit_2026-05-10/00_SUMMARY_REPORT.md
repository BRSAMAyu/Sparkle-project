# Knowledge Galaxy (知识星图) 全面审计汇总报告

> **日期**: 2026-05-10
> **覆盖**: Flutter UI/UX · Python 后端 · Go Gateway · Proto · DB · 事件总线 · 跨层集成
> **详细报告**: 同目录下 `01_` ~ `05_` 共 5 份子报告

---

## 一、总体统计

| 层级 | 报告文件 | P0 | P1 | P2 | P3 | 合计 |
|------|---------|----|----|----|----|------|
| Flutter UI/UX | `01_flutter_uiux_audit.md` | 1 | 4 | 7 | 5 | **17** |
| Python 后端 | `02_python_backend_audit.md` | 2 | 8 | 16 | 15 | **41** |
| Go/Proto/DB | `03_gateway_proto_db_audit.md` | 3 | 8 | 11 | 7 | **29** |
| 跨层集成 | `04_cross_layer_integration_audit.md` | 0 | 2 | 2 | 0 | **4** |
| 事件/掌握度链 | `05_event_mastery_chain_audit.md` | 0 | 1 | 4 | 2 | **7** |
| | | **6** | **23** | **40** | **29** | **98** |

---

## 二、必须立即修复的 P0 问题（6 项）

### P0-1: SQL 注入 — keyword_search 用户输入直接拼入 ILIKE

- **文件**: `backend/app/services/galaxy/retrieval_service.py:589-594`
- **问题**: `query` 参数直接拼入 `f"%{query}%"` ILIKE 和 `jsonb_path_exists` 正则，可注入任意 SQL
- **影响**: 任何用户搜索请求都可以执行任意 SQL
- **修复**:
```python
# Before (漏洞):
KnowledgeNode.name.ilike(f"%{query}%")
# After (安全):
ilike_pattern = f"%{query.replace('%', '\\%').replace('_', '\\_')}%"
KnowledgeNode.name.ilike(ilike_pattern)
# 或者用 bindparam
```

### P0-2: 掌握度重复更新 — spark_node + feedback_service 双写

- **文件**: `backend/app/services/galaxy/stats_service.py:56` 和 `backend/app/services/galaxy/feedback_service.py:254-256, 330-342`
- **问题**: 任务完成时 `feedback_service.batch_update_from_task` 调用 `stats_service.spark_node()`（已更新掌握度），随后 `_update_mastery_from_feedback` 又加 +8 分，造成双倍掌握度增长
- **影响**: 所有任务完成时的掌握度增长被人为膨胀
- **修复**: 在 `batch_update_from_task` 中移除对 `_update_mastery_from_feedback` 的调用，或添加去重标记

### P0-3: Go RecordStudy 写入不存在的列 — 每次 CQRS 学习记录必失败

- **文件**: `backend/gateway/internal/service/galaxy_command.go:343-355`
- **问题**: INSERT 语句使用 `duration_minutes`, `performance_score` 列，但 `study_records` 表实际列名是 `study_minutes`, `mastery_delta`, `record_type`，导致 SQL 错误
- **影响**: Go CQRS 路径的所有学习记录静默失败
- **修复**:
```sql
INSERT INTO study_records (id, user_id, node_id, study_minutes, mastery_delta, record_type, task_id, initial_mastery, created_at, updated_at)
VALUES ($1, $2, $3, $4, $5, 'study', $6, $7, NOW(), NOW())
```

### P0-4: Galaxy gRPC Client 无重连/重试 — 网络闪断后永久瘫痪

- **文件**: `backend/gateway/internal/galaxy/client.go:22-56`
- **问题**: 与 agent client（有 retry/circuit breaker）不同，galaxy client 没有任何重连、重试、熔断机制。`WithBlock()` 更导致启动时若 Python 服务未就绪则 Gateway 卡死
- **影响**: 一次网络抖动就永久禁用所有 galaxy gRPC 路径
- **修复**: 添加 retry policy + 移除 `WithBlock()`，参照 `agent/client.go` 的模式

### P0-5: 协作星图并发安全 — module-level dict 无锁保护

- **文件**: `backend/app/services/galaxy_grpc_service.py:36-73`
- **问题**: `_active_collaborative_sessions` 是模块级 `OrderedDict`，prune + store 操作非原子。并发请求可触发 `RuntimeError: dictionary changed size during iteration`
- **修复**: 添加 `asyncio.Lock`，替换 `datetime.utcnow()` 为 `datetime.now(UTC)`

### P0-6: gRPC GetNodeDetail 掌握度 × 100 溢出

- **文件**: `backend/app/services/galaxy_grpc_service.py:318`
- **问题**: `int(stats.mastery_score * 100)` — `stats.mastery_score` 已经是 0-100 刻度，再乘 100 变成 0-10000
- **影响**: 所有节点详情请求返回错误的掌握度（85 → 8500）
- **我亲自验证**: `UserNodeStatus.mastery_score` 在 DB 中存储 0-100，`spark_node` 的 `MAX_MASTERY` 也是 100
- **修复**: `mastery=int(stats.mastery_score)` （移除 `* 100`）

---

## 三、高优先级 P1 问题（21 项）

### 数据正确性

| # | 问题 | 文件:行号 | 要点 |
|---|------|----------|------|
| P1-1 | **Go mastery scale 0-1 vs 0-100 不匹配** | `galaxy_sync.go:375` | Worker clamp `(0, 1)` 而 DB 用 0-100，所有 Redis 投影掌握度归为 0 或 1 |
| P1-2 | **Perfectionist 成就永远无法触发** | `stats_service.py:187-193` | 100% 时发的是 `NODE_MASTERED` 而非 `HIDDEN_TRIGGER("PERFECTIONIST")`，且 `spark_node` 不发布 `galaxy.node.updated` 事件 → AchievementEventConsumer 的 Perfectionist 路径永远不可达 |
| P1-3 | **LikePost 幽灵事件** | `community_command.go:119-158` | `ON CONFLICT DO NOTHING` 跳过插入但仍发布 `PostLiked` 事件 → 点赞计数虚增 |
| P1-4 | **node_relations 无唯一约束** | `galaxy_command.go:291-298`, `schema.sql:3785-3798` | `ON CONFLICT DO NOTHING` 无实际约束 → 重复关系边 → BFS 路径错误 |
| P1-5 | **GetUserGalaxy tags 始终为空** | `galaxy_grpc_service.py:236, 350` | `getattr(node, 'tags', [])` 但 KnowledgeNode 字段名是 `keywords`，不是 `tags` |
| P1-6 | **GetNodeDetail tags 同上** | `galaxy_grpc_service.py:320` | `node.tags or []` → `KnowledgeNode` 无 `tags` 属性 → 始终 `[]` |
| P1-7 | **SearchNodes mastery 始终为 0** | `galaxy_grpc_service.py:349` | `mastery=0` 硬编码，未查询 UserNodeStatus |
| P1-8 | **GetGalaxyStats 错误计算 avg_mastery** | `galaxy_grpc_service.py:478` | `mastered_count / total_nodes * 100` 是「已掌握节点百分比」不是「平均掌握度」 |
| P1-9 | **_get_or_create_status 竞态条件** | `stats_service.py:454-469` | 无锁 read-then-write，并发请求可导致 IntegrityError 崩溃 |
| P1-10 | **feedback_service 掌握度用 int() 截断** | `feedback_service.py:256` | `int(old_mastery + score * 10)` 截断不一致，与 spark_node 的公式完全不同 |

### 跨层集成新增发现

| # | 问题 | 文件:行号 | 要点 |
|---|------|----------|------|
| P1-22 | **GetUserGalaxy gRPC 返回所有节点 mastery=0** | `galaxy_grpc_service.py:235` | `getattr(node, 'mastery', 0)` 取不到值因为 `NodeWithStatus` 的掌握度在 `.user_status.mastery_score`，不在 `.mastery`。Go gRPC 路径下所有节点显示 0% 掌握度 |
| P1-23 | **文档导入的节点无 embedding — 语义搜索不可见** | `galaxy_service.py:461-593` | `create_nodes_from_document` 传 `generate_embedding=False` 且未调度后台 embedding 任务。通过文档上传创建的所有知识节点在语义搜索中完全不可见 |

### 安全/路由

| # | 问题 | 文件:行号 | 要点 |
|---|------|----------|------|
| P1-11 | **Community GetFeed 无认证** | `community.go:31` | `GET /feed` 在未保护路由组，任何人可访问 |
| P1-12 | **GalaxyRoutes force-unwrap 崩溃** | `galaxy_routes.dart:50` | `state.pathParameters['id']!` 无 null 检查 |
| P1-13 | **GalaxyNodeModel.fromJson null ID 崩溃** | `galaxy_model.dart:193` | `json['id'] as String` 无 null 保护 |
| P1-14 | **Community CQRS handler 死代码** | `community.go` + `setup.go` | CQRS handler 从未注册，所有写操作绕过 Go 直接走 Python REST |
| P1-15 | **NewGalaxyHandler 返回 nil → 空指针崩溃** | `galaxy_handler.go:41-45` + `setup.go:284` | URL 解析失败返回 nil，调用方不检查 |

### UI/UX 功能缺陷

| # | 问题 | 文件:行号 | 要点 |
|---|------|----------|------|
| P1-16 | **SharedResourceCard 10+ 硬编码中英文字符串** | `shared_resource_card.dart:29-223` | 使用 `I18nService.instance.isChinese ? '中文' : 'English'` 而非 ARB l10n |
| P1-17 | **CommunityInsight 每次重建重新请求 API** | `node_detail_sheet.dart:1619` | FutureBuilder 在 `build()` 中创建新 Future |
| P1-18 | **GroupKnowledgeBase _openFile 无错误处理** | `group_knowledge_base_view.dart:121-132` | API 调用无 try/catch，网络失败显示红屏 |
| P1-19 | **Galaxy user_id 无 UUID 格式验证** | `backend/app/api/v1/galaxy.py:182-200` | JWT 提供的 user_id 未验证格式 |
| P1-20 | **spark_node 审计日志/事件静默吞错** | `stats_service.py:81-128` | 6 个独立 try/except 只记 warning，无 metrics，持久故障不可见 |
| P1-21 | **Unbounded BFS DoS** | `galaxy_grpc_service.py:364-427` | GetLearningPath 无深度/节点数限制，恶意图可触发数百次 DB 查询 |

---

## 四、中优先级 P2 问题（38 项，分类摘要）

### 跨层数据一致 (7 项)

| # | 问题 | 关键文件 |
|---|------|---------|
| 1 | Proto mastery 是 `int32` 但 DB 是 `float` → 小数精度丢失 | `galaxy_service.proto:63` |
| 2 | Redis 投影无 TTL → 无限内存增长 | `galaxy_sync.go:192,266,323` |
| 3 | mastery 投影基于缓存值计算 delta 而非重读 DB → 投影漂移 | `galaxy_sync.go:374-375` |
| 4 | Community like count 非原子 read-modify-write → 并发丢增量 | `community_sync.go:211-253` |
| 5 | RecordStudy 不检查 `is_unlocked` → 锁定节点可被学习 | `galaxy_command.go:365-374` |
| 6 | SparkNode 使用 `context.Background()` → 丢失取消/链路追踪 | `galaxy_handler.go:192` |
| 7 | `predict_next_node` 只查 source→target 边，忽略反向 | `stats_service.py:304-310` |

### 性能 (8 项)

| # | 问题 | 关键文件 |
|---|------|---------|
| 1 | BFS 每节点单独 DB 查询 (N+1) | `galaxy_grpc_service.py:393-397` |
| 2 | predict_next_node N+1 查询 | `stats_service.py:315-347` |
| 3 | auto_link_nodes N+1 关键词匹配 | `expansion_service.py:1025-1044` |
| 4 | semantic_cache `clear_all` 用 `KEYS` (O(N) 阻塞) | `semantic_cache_service.py:476-477` |
| 5 | `_find_similar_cache_key` 加载全部 embedding 候选 | `semantic_cache_service.py:196-212` |
| 6 | Galaxy 缓存失效每次 SCAN 全库 | `galaxy_handler.go:353-378` |
| 7 | Duplicate node/nodes 路由注册（双倍路由数） | `galaxy_handler.go:72-134` |
| 8 | study_records 缺复合索引 `(user_id, node_id)` | `schema.sql:16108-16118` |

### 事件/掌握度链 (5 项)

| # | 问题 | 关键文件 |
|---|------|---------|
| 1 | 错题掌握度扣减防护仅靠注释，无程序化强制 | `galaxy_event_consumer.py:77-86` |
| 2 | 来源追加(provenance append)不幂等 | `galaxy_event_consumer.py:112-136` |
| 3 | DLQ 无自动重试/对账 | `event_bus.py:886-932` |
| 4 | ReviewUrgency 过期加成在 clamp 之后失效 | `review_urgency_service.py:76-84` |
| 5 | ReviewUrgency `score_status` 始终 `is_recommended=False` | `review_urgency_service.py:88` |

### Flutter UI/UX (7 项)

| # | 问题 | 关键文件 |
|---|------|---------|
| 1 | GalaxyGraphResponse.fromJson `nodes` 无 null fallback | `galaxy_model.dart:526` |
| 2 | LearningPathScreen 硬编码标题 | `learning_path_screen.dart:19` |
| 3 | Category 切换重复加载 | `group_knowledge_base_view.dart:60-69` |
| 4 | deselectNode 绕过 copyWith | `galaxy_provider.dart:806-833` |
| 5 | _parseMasteryFromSubtitle int.parse 可抛异常 | `node_share_card.dart:391-397` |
| 6 | 3 份重复的 _iconForMime/_typeLabel/_formatSize | `group_knowledge_base_view.dart` |
| 7 | 节点详情显示原始 UUID | `node_detail_sheet.dart:343-349` |

### Python 其他 (5 项)

| # | 问题 | 关键文件 |
|---|------|---------|
| 1 | `_PGVECTOR_RUNTIME_ENABLED` 模块级全局无同步 | `retrieval_service.py:39,58-62` |
| 2 | `semantic_cache` 默认阈值 1.0 (精确匹配) | `semantic_cache_service.py:322` |
| 3 | DocumentService 有 3 个重复方法定义(死代码) | `document_service.py:505 vs 1264` |
| 4 | `datetime.utcnow` 已弃用 (Python 3.12+) | `galaxy.py:69-70, 88-89` |
| 5 | `total_minutes` 冗余列永不更新 | `galaxy.py:243 vs 244` |

### DB Schema (6 项)

| # | 问题 | 关键文件 |
|---|------|---------|
| 1 | `community_signal` 用 `json` 而非 `jsonb` | `schema.sql:3292` |
| 2 | 缺 `(user_id, created_at DESC)` 复合索引 | `schema.sql:16108-16118` |
| 3 | `post_likes` 可能缺 `(user_id, post_id)` 唯一约束 | `community_command.go:123-131` |

---

## 五、修复路线图（推荐顺序）

### Phase 1 — 数据安全（1-2 天）

| 优先级 | 修复项 | 涉及文件 |
|--------|-------|---------|
| P0-1 | SQL 注入参数化 | `retrieval_service.py` |
| P0-3 | RecordStudy SQL 列名修正 | `galaxy_command.go` |
| P0-6 | GetNodeDetail mastery 去掉 `* 100` | `galaxy_grpc_service.py` |
| P1-1 | galaxy_sync.go clamp `(0,1)` → `(0,100)` | `galaxy_sync.go` |
| P1-5/6 | `tags` → `keywords` 属性名修正 | `galaxy_grpc_service.py` |
| P1-7 | SearchNodes 查询 UserNodeStatus | `galaxy_grpc_service.py` |
| P1-22 | GetUserGalaxy mastery 从 `node.user_status.mastery_score` 取值 | `galaxy_grpc_service.py` |
| P1-11 | Community GetFeed 加认证 | `community.go` |

### Phase 2 — 掌握度正确性（2-3 天）

| 优先级 | 修复项 | 涉及文件 |
|--------|-------|---------|
| P0-2 | 去除 feedback_service 双重掌握度更新 | `feedback_service.py` |
| P1-2 | Perfectionist 改用 HIDDEN_TRIGGER 或发布 `galaxy.node.updated` | `stats_service.py` |
| P1-9 | `_get_or_create_status` 加 IntegrityError 处理 | `stats_service.py` |
| P1-4/5 | 添加 `node_relations` 唯一约束 | `schema.sql` |
| P1-3 | LikePost 检查 RowsAffected | `community_command.go` |
| P1-8 | avg_mastery 改为实际平均值 | `galaxy_grpc_service.py` |
| P1-23 | 文档导入节点添加后台 embedding 生成 | `galaxy_service.py` |

### Phase 3 — 可靠性 & 性能（3-5 天）

| 优先级 | 修复项 | 涉及文件 |
|--------|-------|---------|
| P0-4 | Galaxy gRPC client 添加 retry/reconnect | `galaxy/client.go` |
| P0-5 | 协作星图添加 asyncio.Lock | `galaxy_grpc_service.py` |
| P1-21 | BFS 添加深度/节点数限制 | `galaxy_grpc_service.py` |
| P1-14 | 决定 community CQRS 去留 | `community.go` / `setup.go` |
| P2 | Redis 投影添加 TTL | `galaxy_sync.go` |
| P2 | N+1 查询批量化 | `galaxy_grpc_service.py`, `stats_service.py`, `expansion_service.py` |

### Phase 4 — Flutter UI/UX 修复（2-3 天）

| 优先级 | 修复项 | 涉及文件 |
|--------|-------|---------|
| P1-12 | GalaxyRoutes null safety | `galaxy_routes.dart` |
| P1-13 | GalaxyNodeModel null id 保护 | `galaxy_model.dart` |
| P1-16 | SharedResourceCard l10n 规范化 | `shared_resource_card.dart` |
| P1-17 | CommunityInsight Future 缓存 | `node_detail_sheet.dart` |
| P1-18 | _openFile 错误处理 | `group_knowledge_base_view.dart` |
| P2 | 代码去重 + 死代码清理 | 多个文件 |

---

## 六、关键跨层数据流验证结果

### 掌握度 (Mastery) 刻度不一致 — 最严重的一致性问题

| 层级 | 刻度 | 问题 |
|------|------|------|
| DB `UserNodeStatus.mastery_score` | 0-100 (Float) | ✅ 源头 |
| Python `spark_node` | 0-100 (clamp) | ✅ 正确 |
| Python `feedback_service` | 0-100 (int截断) | ⚠️ int() 截断不一致 |
| Go `galaxy_command.go` | 0-100 (clamp) | ✅ 正确 |
| Go `galaxy_sync.go` worker | **0-1** (clamp) | ❌ **BUG** |
| gRPC `UpdateNodeMastery` | int() 截断 | ⚠️ 小数丢失 |
| gRPC `GetUserGalaxy` line 235 | `getattr(node,'mastery',0)` → **0** | ❌ **BUG** — 始终返回 0（取错属性） |
| gRPC `GetNodeDetail` line 318 | `* 100` | ❌ **BUG** — 8500 |
| gRPC `SearchNodes` line 349 | 硬编码 0 | ❌ **BUG** |
| Proto field | `int32` | ⚠️ 应为 `double` |
| Flutter `GalaxyNodeModel` | 0-100 (fromJson) | ✅ 正确（如果 gRPC 不乘错） |

### 事件链完整性

```
任务完成 → spark_node() 更新掌握度 ✅
         → event_bus: node_mastery_updated ✅
         → AchievementEngine: NODE_UNLOCKED / NODE_MASTERED ✅
         → AchievementEngine: NODE_MASTERED (>= 100) ❌ 应为 HIDDEN_TRIGGER
         → galaxy.node.updated 事件? ❌ 未发布 → Perfectionist 不可达

错题创建 → ErrorBookMasterySyncService 同步扣减掌握度 ✅
         → db.commit() 后发布 pending_events ✅
         → event_bus: node_mastery_updated ✅
         → event_bus: error_created ✅
         → GalaxyEventConsumer._handle_error_created() 不修改掌握度 ✅ (但仅靠注释保护)
```

---

## 七、审计覆盖范围

### 已审查文件清单

**Flutter (11 文件)**: galaxy_screen.dart, node_detail_sheet.dart, galaxy_provider.dart, galaxy_model.dart, galaxy_routes.dart, enhanced_galaxy_repository.dart, compact_knowledge_node.dart, group_knowledge_base_view.dart, shared_resource_card.dart, node_share_card.dart, learning_report_share_card.dart, learning_path_screen.dart, learning_path_dialog.dart

**Python (25+ 文件)**: galaxy_service.py, stats_service.py, retrieval_service.py, structure_service.py, collaborative_service.py, review_urgency_service.py, feedback_service.py, ontology_generator.py, rag_router.py, knowledge_service.py, document_service.py, embedding_service.py, semantic_cache_service.py, rerank_service.py, expansion_service.py, galaxy_event_consumer.py, achievement_event_consumer.py, community_signal_bridge.py, error_book_mastery_sync_service.py, error_replan_bridge.py, galaxy_grpc_service.py, galaxy.py (model), galaxy.py (API), config_rag_strategy.py

**Go (10+ 文件)**: galaxy_handler.go, galaxy/client.go, galaxy_command.go, galaxy_sync.go, community.go, community_command.go, community_sync.go, agent/client.go, websocket_proxy.go, setup.go

**Proto + DB**: galaxy_service.proto, schema.sql

---

## 八、子报告索引

| 文件 | 内容 | 问题数 |
|------|------|--------|
| `01_flutter_uiux_audit.md` | Flutter Galaxy UI/UX 全链路审计 | 17 |
| `02_python_backend_audit.md` | Python 后端服务/RAG/事件/数据模型审计 | 41 |
| `03_gateway_proto_db_audit.md` | Go Gateway/Proto/DB Schema/CQRS 审计 | 29 |
| `04_cross_layer_integration_audit.md` | 跨层数据流一致性验证（5条完整链路） | 4 |
| `05_event_mastery_chain_audit.md` | 掌握度事件链完整追踪 | 7 |
