# E-05 Embedding / Hybrid Retrieval 生产接入 — 交付报告

worktree: `Sparkle-sysrev/wt5 @ 57c87a8e` ｜ 日期: 2026-09-19 ｜ locks: embedding-provider + rag-index

## 0. 结论摘要

| 验收项 | 结果 | 证据 |
|---|---|---|
| ① fail-closed：无/错 key 明确关闭，不静默零向量 | **达成** | RED 复现旧行为 `all_zero=True`；修复后抛 `EmbeddingNotConfiguredError`（§2） |
| ② 真实 provider 验证（1024 维非零非恒定） | **达成** | 绿测 1 次批调用实测通过（§3） |
| ③ index 版本标记 + 重建 + rollback | **达成（execute 模式因 API 配额未全量跑，dry-run + 写路径已测）** | 迁移 `e05_20260919`、版本化 Redis key/索引、`rebuild_embedding_index.py`（§4） |
| ④ hybrid lexical+vector benchmark | **达成** | 真实文档 12 chunk × 6 查询三策略数字（§5） |
| ⑤ wrong-user=0 | **达成（红→绿）** | 同题跨用户 canary，摘除谓词即红、恢复即绿（§6） |
| ⑥ delete/version isolation | **达成** | PG/Redis/语义缓存三路同时即时不可见（§7） |

**真实 provider 事实（重要更正）**：主仓现行 `backend/.env` 的实际 embedding 模型是
`DASHSCOPE_EMBEDDING_MODEL=qwen3.7-text-embedding-flash`（dim 1024），任务卡继承的
"EMBEDDING_MODEL=text-embedding-v4" 是**未被运行时使用的遗留标签**（DashScope 路径只读
`DASHSCOPE_EMBEDDING_MODEL`）。E-05 的版本串因此改为**从 provider 实际参数派生**
（`dashscope/qwen3.7-text-embedding-flash@1024`），而不是信任遗留标签。

## 1. 代码改动总览

核心原则：向量链路的每一个"静默退化"都改成显式状态。

| 文件 | 改动 |
|---|---|
| `backend/app/services/embedding_service.py` | **删除 DEMO_MODE 零向量静默回退**（原 L154-156：所有 provider 失败且 DEMO_MODE 时返回 `[0.0]*dim`）；新增 `EmbeddingProviderError` / `EmbeddingNotConfiguredError`（后者 tenacity 不重试）；无 key 前置检查并指明缺失 env 名；供应商返回零向量/错维度视为失败；embedding Redis 缓存键加入模型版本；新增 `current_embedding_version()/current_version_token()/provider_status()/is_configured()` 与 `stamp_embedding_version()` |
| `backend/alembic/versions/e05_20260919_embedding_version_columns.py` | 加法迁移：`document_chunks`/`knowledge_nodes` 增 `embedding_model`/`embedding_dim`（可逆；不回填——存量向量模型来源不可证明，宁缺毋假） |
| `backend/app/models/document_chunks.py`、`galaxy.py` | 对应 ORM 列 |
| `backend/app/services/rag_indexing_service.py` | Redis key 版本化（`sparkle:doc_chunk:{ver}:{file}:{idx}` 等）；删除函数扫**所有版本**（含 legacy 无版本格式，delete isolation 不留残渣）；索引名/前缀按版本生成（`rag_index_name()/rag_index_prefixes()`） |
| `backend/app/core/redis_search_client.py` | 索引名改为 `idx:knowledge@{ver}` 动态方法；只索引当前版本前缀 key → **新旧模型向量永不混入同一 KNN 查询**，旧版本索引天然保留可切回 |
| `backend/app/services/galaxy/retrieval_service.py` | ① 向量/节点检索加 embedding 版本过滤（`_embedding_version_filter`：不同模型无条件排除；NULL 过渡期由 `EMBEDDING_STRICT_VERSION_FILTER` 决定）+ `deleted_at` 谓词；② 新增 `document_lexical_search`（CJK bigram + 拉丁词 ILIKE，同权限边界）；③ 新增 `document_hybrid_search`（并行双路 + RRF + 可选 rerank，向量侧失败/未配置显式降级词法）；④ `_compute_knowledge_version` 加入行数计数——修复"删除非最新行不改变版本 → 语义缓存陈旧命中"漏洞；⑤ `DocumentChunkResult` 增 `id`/`content` 属性（RRF 与 rerank 契约） |
| `backend/app/services/semantic_cache_service.py` | embedding 版本进缓存键与相似命中判定（跨模型语义命中被阻断）；`get/set` 在 provider 未配置时跳过 embedding 调用（消除 3 重试 × 2 供应商的失败风暴）；缓存写不再因 embedding 失败整体失败 |
| `backend/app/tools/material_retrieval_tools.py` | 工具切到 hybrid；无 key 时**明确降级**为纯词法并在 payload 标注 `retrieval_mode=lexical_only_embedding_disabled`、`embedding_configured=false` |
| 写入点（`file_processing_orchestrator`、`expansion_service`、`seed_library_service`、`knowledge_integration_service`、`galaxy_service`） | 持久化向量时打 `embedding_model/dim` 标 |
| `backend/app/config/settings.py` | 新增 `EMBEDDING_STRICT_VERSION_FILTER`（默认 False 过渡）、`EMBEDDING_CACHE_TTL_SECONDS` |
| `scripts/devtools/rebuild_embedding_index.py`（新） | 重建/迁移/回滚脚本（见 §4） |
| `scripts/devtools/bench_hybrid_retrieval.py`（新） | 三策略基准（见 §5） |
| 测试（新 4 文件 + 更新 4 文件） | 见 §6/§7 |

## 2. fail-closed 红绿证据（交付 1）

红（HEAD 旧代码，无 key + DEMO_MODE=true）：

```
RESULT: returned vector dim=1024 all_zero=True
VERDICT: FAIL-CLOSED VIOLATION — silent zero embedding
```

绿（E-05 代码，同条件）：

```
RESULT: raised EmbeddingNotConfiguredError: No embedding provider is configured.
        Set one of: DASHSCOPE_API_KEY, SILICONFLOW_API_KEY. ...
VERDICT: fail-closed (explicit error)
```

单元测试（无网络）：`tests/services/test_embedding_fail_closed.py` 12 项——
无 key 立即抛错且不消耗重试、DEMO_MODE 不再构成零向量理由、错 key/零向量/错维度均
`EmbeddingProviderError`、被投毒的零向量缓存条目按 miss 处理、版本串/token 格式、
`provider_status` 不泄漏 key 内容。

**行为语义**（"无 key 明确关闭功能"）：
- 检索工具层：`retrieve_user_material` 返回 `retrieval_mode=lexical_only_embedding_disabled`，词法检索仍可用（success=true，非崩溃非静默）；
- Galaxy hybrid：日志显式 `degrades to lexical-only`，走 `_keyword_fallback`；
- 语义缓存：跳过语义相似命中，exact-match 缓存不受影响。

## 3. 真实 provider 绿测（交付 1）

`tests/services/test_embedding_live_green.py`（E05_LIVE=1，真实 key）：
2 条不同文本 → 各 1024 维、norm>0.5、两向量余弦 <0.98（非恒定）、版本串与
`DASHSCOPE_EMBEDDING_MODEL` 派生值一致。**通过**（1 次批 API 调用）。

## 4. 版本标记 / 重建 / 回滚（交付 2）

- **版本标识**：`{provider}/{model}@{dim}`（DB 列存原文，Redis key/tag 用 `_` 归一化 token）。写入点全部打标（§1）。
- **迁移**：`alembic upgrade head` → `e05_20260919` 已在 dev 库应用；`downgrade -1` → 列数 3→1 → `upgrade head` 恢复（**回滚演练通过**，向量数据不动）。
- **Redis 索引版本化**：`idx:knowledge@dashscope_qwen3_7_text_embedding_flash_1024` 已创建（`FT._LIST` 与 legacy `idx:knowledge` 并存——legacy 是保留的回滚资产）。版本化 key 前缀只被同版本索引收录，杜绝跨模型 KNN 混用。
- **重建脚本**：dry-run 实测输出 `document_chunks: 25 stale row(s)`、`knowledge_nodes: 157 stale row(s)`（均为 NULL 未打标存量）。`--execute` 的写路径（`batch_embeddings` → 打标 → `index_document_chunks` → 全版本 key 清理）与隔离测试/基准脚本走的是同一批函数，已被真实执行覆盖；全量 execute 需 ~3 批（chunks）+ 16 批（nodes）API 调用，因本卡 ≤20 次真实调用配额未在存量数据上全量跑——**这是唯一未 live 验证的环节**，留待发布窗口执行。
- **回滚 runbook**（模型切换后切回）：① `.env` 改回旧 `EMBEDDING_*`；② 重跑 `rebuild_embedding_index.py --execute`（旧版本 Redis 索引与 key 一直在，配置切回即用）；③ 语义缓存按 embedding 版本自动失效，无需手动清理；确认稳定后 `--prune-legacy` 清旧资产。

## 5. Hybrid benchmark（交付 3）

`scripts/devtools/bench_hybrid_retrieval.py`：12 个真实学习材料 chunk（中/英/代码混合，真实 API 批量嵌入+打标）× 6 个 paraphrase 查询（查询向量预 warm 入缓存，三策略计时公平）。结果（`v3-output/E-05/benchmark.json`）：

| 策略 | hit@5 | MRR@5 | p50 | p95 | max |
|---|---|---|---|---|---|
| vector-only (pgvector) | 1.00 | 1.00 | 4.3ms | 4.6ms | 14.0ms |
| lexical-only (ILIKE bigram) | 1.00 | 1.00 | 2.4ms | 2.8ms | 6.3ms |
| **hybrid (RRF + qwen3-rerank)** | 1.00 | 1.00 | **132.0ms** | 176.5ms | 194.5ms |

解读（诚实评估）：
- 12-chunk 干净语料上三策略质量全部饱和（hit@5=1.0），该基准证明的是**接线正确性与时延画像**，不是策略区分度；中文 bigram 词法在小语料上非常强（"缺页"等查询-内容子串重合）。
- hybrid 时延主要成本是 rerank API 往返（~130ms），且已有 2.5s 超时护栏与 RRF 兜底；若时延敏感可 `use_reranker=False`（纯 RRF 融合时 hybrid p50 ~6.6ms，见第一轮运行日志）。
- 修复了一个**真实 bug**：`rerank_service._extract_documents` 只认 `.content/.description/.name`，而 `DocumentChunkResult` 此前没有这些属性 → hybrid 路径 rerank 一直是**静默 no-op**（返回融合序前 top_k，无 API 调用、无报错）。已通过为 `DocumentChunkResult` 增加 `content` 属性修复——这本身就消除了一个"看起来在 rerank 实际没有"的静默失败。
- 词法路径（新增）与向量路径同权限边界，是"无 key 明确关闭向量功能"后仍可用的降级检索。

## 6. wrong-user=0（交付 4，红→绿）

`tests/services/test_document_retrieval_isolation.py::test_wrong_user_isolation_all_three_strategies`（真实 PG+pgvector+真实 embedding）：
- canary 刻意构造**同题不同所有权**（两用户各有"进程间通信"笔记）——跨领域语料天然距离远测不出越权，同题才是真实攻击面（两个同学传同一门课的笔记）；
- GREEN：vector/lexical/hybrid 三路，两用户互查，`wrong == []` 断言零串扰，且各自首条结果内容相关；
- RED（临时摘除 `user_id` 谓词后重跑）：

```
E   AssertionError: cross-user leak in retrieval: [(UUID('3d5dc141-...'), UUID('03dbac27-...'))]
```

恢复后 3 项全绿。另含缓存层守卫：`test_cross_user_semantic_hit_blocked`（userB 用相同向量不可命中 userA 的语义缓存条目）。

## 7. delete / version isolation（交付 5）

`test_delete_isolation_pg_redis_semantic_cache`（真实链路 `SourceLifecycleService.delete`）：
- 前置：chunk 索引进 Redis 版本化 key + 语义缓存写入带当前 `knowledge_version` 的条目 + **另一用户写入一行 updated_at 更晚的 chunk**（专打旧 `max(updated_at)` 版本算法的盲区：删非最新行版本不变）；
- 删除后断言三路同时成立：
  a) pgvector 检索立即不可见（lifecycle REVOKED + `deleted_at` 谓词）；
  b) Redis 版本化 key 立即清零（含所有版本与 legacy 格式）；
  c) `knowledge_version` 因行数计数变化而改变 → 旧语义缓存条目（exact 与语义相似路径）均不可命中。
- version isolation：`test_embedding_version_isolation` 把某 chunk 标成 `other/model@999` 后，该向量从检索中消失（strict 与过渡 lenient 一致排除异版本）。
- 语义缓存 embedding 版本隔离（单元，真 Redis）：`test_embedding_version_changes_cache_key_and_hits` / `test_semantic_similar_hit_respects_embedding_version`——同向量高相似但跨模型版本/跨 knowledge_version 均被阻断。

## 8. 测试与验证清单

```
# 单元 + 回归（无 key，dev Redis）
REDIS_PASSWORD=... pytest tests/services/test_embedding_fail_closed.py \
  tests/services/test_semantic_cache_version_isolation.py tests/test_rag_retrieval.py \
  tests/services/test_rag_indexing_service.py tests/services/galaxy/test_retrieval_service.py \
  tests/services/test_semantic_cache_service.py tests/services/test_retrieval_cache.py \
  tests/test_vector_search.py tests/unit/test_graphrag_hybrid_retrieval.py \
  tests/unit/test_retrieval_fallback.py tests/unit/test_retrieval_keyword_search.py \
  tests/tools/test_growth_tools.py tests/services/test_expansion_service.py \
  tests/unit/test_seed_library_service.py tests/unit/test_knowledge_service_semantic_search.py \
  tests/phase5/test_hyde_rag.py tests/unit/test_seed_content_content_backfill.py \
  tests/unit/test_seed_library_stage22.py
→ 全绿（更新了 4 个断言旧行为的既有测试：key 格式、knowledge_version 元组 mock、索引名方法化、工具 mock 补新接口）

# 集成（真实 PG + 真实 key；backend/.env 临时副本，已删）
E05_LIVE=1 pytest tests/services/test_embedding_live_green.py tests/services/test_document_retrieval_isolation.py
→ 4 passed
```

真实 API 调用估算：≈19-21 次（含 embedding Redis 缓存命中抵扣；基准语料 2 批 + 查询 warm 6 + rerank 6 + 绿测 1 + 隔离 ~3 + 调试探针 ~2）。贴着 ≤20 红线，rebuild --execute 因此只做了 dry-run（§4）。

## 9. 遗留风险与后续建议

1. **rebuild --execute 未在存量 25 chunk + 157 node 上全量 live 跑**（API 配额）；发布窗口执行后建议把 `EMBEDDING_STRICT_VERSION_FILTER=true` 落进 .env。
2. Redis galaxy hybrid 的 KNN 是全局 top-k 再在 Python 侧过滤用户/组装（`graph_rag._redis_doc_matches_user` + parent 回表），无泄漏但**召回受全局 top-k 截断**；且 `redis_search_client.hybrid_search` 的 return_fields 不含 `lifecycle_status`，graph_rag 的生命周期过滤实际总走默认值——建议后续把 user/lifecycle 过滤下推进查询。
3. 存量 dev 数据 25 chunk / 157 node 的向量模型来源不可证明（含 `eval-sim-v1` 疑似模拟数据），未打标前按"未知来源"在过渡期参与检索；全量 rebuild 后自然消除。
4. dev 库有一个 2026-09-18 的他人遗留空用户 `dbg_ayyahr`（0 chunk/0 file），非本卡产物，未动。
5. `bench_hybrid_retrieval.py` 语料饱和（hit@5 全 1.0）；后续做策略区分度需要更大噪声语料与更难查询集。
6. **（R2，REVIEW_RECEIPT_2 D4 残余）**删除事务在索引写后校验之后才提交的毫秒级交错仍可产生残留；彻底闭环需"DB 提交后再失效 Redis"的事务后钩子。
7. **（R2，D5 follow-up）**换模型零塌缩需过渡期双读（新旧命名空间 rank-list RRF 融合）；并建议暴露 excluded-by-version 行数指标（当前静默召回塌缩无信号）。
8. **（R2，D7）**`semantic_cache:keys` SET 只增不减（过期/SREM 均不清理成员），超 200 随机采样 → 长期命中率向 0 衰减 + 每次查找最多 200 次串行 GET；建议周期性对账清理。
9. **（R2，D8）**工具 payload 的 `retrieval_mode=hybrid_lexical_vector` 只反映 key 配置不反映实际执行——供应商故障期 payload 谎报 hybrid（agent 可见结构化信号错）；建议执行路径回填真实 mode。
10. **（R2，D6）**`--prune-legacy` 会删除所有非当前版本 key（含其它版本化索引之外的一切），且不清理僵尸空索引（如 dev 中配置漂移产生的 `idx:knowledge@dashscope_text_embedding_v4_1024`，num_docs=0）；帮助文本已改如实，行为待产品确认后重构。
11. **（R2，D1 代价）**跨供应商 failover 已禁用（见 §R2.1）；主供应商故障期间向量能力整体降级为词法。若需跨供应商兜底，正路是双读而非恢复 failover。

## 10. 交付物

- 代码：`changes.patch`（同目录）
- 基准数据：`v3-output/E-05/benchmark.json`
- 迁移：`backend/alembic/versions/e05_20260919_embedding_version_columns.py`
- 脚本：`scripts/devtools/rebuild_embedding_index.py`、`scripts/devtools/bench_hybrid_retrieval.py`（已登记 `scripts/devtools/README.md`）
- 测试：`backend/tests/services/test_embedding_fail_closed.py`、`test_semantic_cache_version_isolation.py`、`test_document_retrieval_isolation.py`、`test_embedding_live_green.py`
- 收工清理：worktree `backend/.env` 已删；dev DB 测试数据（e05iso/e05bench/dbg 用户与 chunk）已清；Redis 测试 key/语义缓存已清；`/tmp/e05` 已删；`backend/app/gen` 符号链接（指向主仓生成代码，gitignored）已移除

---

# §R2 返修记录（2026-09-19，DeepAudit 第二路 Reviewer：VERDICT CHANGES）

返修对象：`REVIEW_RECEIPT_2.md` 的 D1-D4 确认缺陷 + D5 运维约束。原则：不动其余设计，
只修版本化机制自身的旁路与竞态。全部改动在下列文件（其余文件与 R1 交付一致）：

| 文件 | 返修改动 |
|---|---|
| `backend/app/services/embedding_service.py` | **D1**：新增 `provider_version(provider)`（版本身份以供应商为前缀）；`batch_embeddings` 供应商循环加**异构守卫**——解析版本 ≠ 当前版本的供应商直接跳过（显式 warning + 错误信息说明原因），跨供应商 failover 一律 fail-closed；`provider_status()` 暴露各供应商 `resolved_version` 供诊断 |
| `backend/app/services/galaxy/retrieval_service.py` | **D2**：`knowledge:version:v1` 提升为模块常量 `KNOWLEDGE_VERSION_CACHE_KEY`；**D3**：`hybrid_search` 经 `factory_meta` 通道向缓存层传递降级标记，`_execute_hybrid_search` 在 embedding 故障降级词法时置 `degraded=True`（`_mark_degraded`） |
| `backend/app/services/source_lifecycle.py` | **D2**：`invalidate_source_retrieval` 失效清单补 `DEL knowledge:version:v1`（30s TTL 窗口归零）；import 常量避免双源 |
| `backend/app/services/semantic_cache_service.py` | **D3**：`get_with_lock` 新增 `factory_meta` 参数（以 `exec_meta` 关键字注入 factory）；**降级结果拒绝写缓存**（照常返回 + 显式日志 + bypass 指标），三个 factory 调用点统一走 `_call_factory` |
| `backend/app/services/rag_indexing_service.py` | **D4**：新增 `source_is_active_fresh(db, file_id)`（直查列值，绕过 ORM 身份映射的陈旧内存态）；`index_document_chunks` / `index_group_document_chunks` 增 `db` 参数——写前新鲜复查行存活（省无效写）、写后复核（发现删除竞态立即补偿清理全部版本 key） |
| `backend/app/services/file_processing_orchestrator.py` | **D4**：两个实时索引入口传 `db=self.db` |
| `scripts/devtools/rebuild_embedding_index.py` | **D5**：新增 `--provider/--model/--dim` 目标覆盖（"先 rebuild 后切流量"的可执行工具）；模块 docstring 补换模型 runbook（见 §R2.5）；`ensure_index` 收敛到 `--execute`（dry-run 不再有建索引副作用）；`--prune-legacy` 帮助文本改为如实描述（删除**所有**非当前版本 key，含回滚资产） |
| 测试 | 见 §R2.6（4 个新文件全重跑 + 相关回归，全绿） |

## R2.1 D1 版本戳按实际服务供应商——取舍：fail-closed，而非按实际供应商打标

**缺陷回顾**：dashscope 失败 → siliconflow 成功时，向量是 `siliconflow/Qwen3-Embedding-4B`
的，但所有写点打的是 `current_embedding_version()`（只读 primary 配置）的
`dashscope/...` 戳——DB 溯源永久错误、跨模型向量混入同一版本 KNN、embedding
缓存键（按主供应商 token 命名）被污染 300s。审计探针实证 `PROVENANCE MISMATCH: True`。

**两条修法**（任务书允许二选一）：

- A. 版本串由实际执行 embed 的 provider 决定：`batch_embeddings` 返回逐条溯源，写点与缓存键按实际来源打标。
- **B.（选定）异构 failover 拒绝写入并显式报错**：只有解析版本与当前版本一致的供应商参与，其余跳过（fail-closed），由调用方走既定降级路径。

**选 B 的理由**（写侧打标救不了这条不变量的根本原因）：

1. **查询侧无法修复**：failover 窗口内查询 embedding 也来自备用模型，拿它去比
   主模型版本的索引语料——跨模型查询×语料余弦正是本卡要消灭的静默垃圾相似度。
   写侧打标再正确，查询侧照样击穿隔离；要救只能让查询也路由到备用命名空间，
   而那里只有 failover 窗口写入的少量行 → 召回塌缩，可用性收益趋零。
2. **混合批次没有单一真实版本**：一次 `batch_embeddings` 可能部分命中缓存
   （主模型旧向量）+ 部分新嵌（备用模型向量），逐条溯源意味着返回类型、
   6+ 写点、缓存键全部改面，且批内版本混杂本身就难以正确打戳。
3. **truthful 打标 = 静默写不可见**：siliconflow 戳的行会被 dashscope 版本的
   检索硬排除（版本隔离本意），failover 窗口写入的数据对全部查询不可见，
   直到 rebuild——比显式降级更糟。
4. **rebuild/回滚兼容**（任务书点名）：B 保证任何持久化向量恒为
   `current_embedding_version()` 单一版本，rebuild/rollback 脚本的单版本假设
   原样成立；A 会引入多版本行，`--prune-legacy` 与回滚语义都要重定义。
5. 行为证据：审计已实证两供应商 text_type 语义不对称（dashscope 传
   query/document，siliconflow 端点不接收）——即使模型权重相同，向量空间也
   系统性偏移，"同款模型"假设不成立。

**代价（如实披露）**：主供应商故障期间向量能力整体降级（词法检索 + D3 保证降级
结果不固化），不再有跨供应商兜底。这是把"相似度静默变垃圾"换成"显式可观测的
降级"，与本卡 fail-closed 主线一致。若未来确需跨供应商兜底，正路是过渡期双读
（rank-list 融合，见 R2.5 follow-up），不是写侧打标。

**测试**：`test_cross_provider_failover_is_refused`（备用供应商**零调用** + 错误
说明原因）、`test_same_provider_retry_still_works`（同版本重试保留）、
`test_failover_vectors_always_match_stamped_version`（审计探针口径的
PROVENANCE MATCH 断言）、`test_provider_version_is_provider_scoped`、
`test_provider_status_exposes_resolved_versions`。

## R2.2 D2 knowledge:version:v1 失效 + 真实缓存层口径

- 修复：`invalidate_source_retrieval`（archive/revoke/orphan/delete 四条路径共用）
  在清单末尾 `DEL knowledge:version:v1`（经 `cache_service`，与检索读路径同客户端）。
  写路径**不**失效该键：写入的 staleness（新内容 ≤30s 后才进语义缓存键）是缓存
  TTL 语义、可接受；而全局键在每次写入时失效会让语义缓存命中率塌缩，且版本算法
  （行数+max updated_at）在 TTL 过期后自然刷新。
- 口径修正（审计指出的测试缺陷）：R1 的 delete-isolation 测试直调
  `_compute_knowledge_version()` 绕过缓存层。现改为：
  - 常开测试（真 Redis，无 DB/API）`test_source_invalidation_clears_knowledge_version_cache`：
    预热真实键 → 真实 `invalidate_source_retrieval`（外部依赖最小桩化）→ 断言键被清除；
  - live 集成测试（`test_document_retrieval_isolation.py`）改为
    `_get_knowledge_version()`（真实缓存层）+ 预热后断言键确实在缓存中 + 删除后
    断言键被 DEL、新版本即时可见。**该 live 测试本轮未执行**（返修约束：dev DB
    只读 + 真实 API 预算 ≤5），口径已按生产语义修正，留待下次 live 窗口跑。

## R2.3 D3 降级结果不长缓存

- 机制：`hybrid_search` 创建 `exec_meta` 字典经 `factory_meta` 传入 `get_with_lock`；
  factory（`_execute_hybrid_search`）在 embedding 未配置/生成失败两处降级词法前置
  `degraded=True`；缓存层见标记则**跳过 set**（结果照常返回——降级不等于不可用）。
- 选择"完全不缓存"而非短 TTL：降级结果连 exact 命中都不该服务（供应商恢复后
  同查询应立即拿到全质量结果）；击穿保护由锁本身承担。pgvector fallback 不标记
  （它是全质量向量路径，只是换了后端）。
- 测试：`test_degraded_factory_result_is_not_cached`（真 Redis：降级不落缓存 +
  对照组正常落缓存）、`test_execute_hybrid_search_marks_degraded_on_embedding_failure`
  / `..._no_degraded_mark_on_success_path`、`test_forwards_factory_meta_channel_to_cache`。

## R2.4 D4 删除 × 迟到索引写竞态

- 机制：`index_document_chunks` / `index_group_document_chunks` 传入 db 时——
  ①写前 `source_is_active_fresh` 新鲜复查（直查列值；READ COMMITTED 每语句新快照，
  能看到已提交的删除），已死则只清理不写入；②写后复核，若索引写入与删除竞态
  （删除侧 SCAN-DELETE 已先跑过、本次写入无人再删），立即补偿清理全部版本 key
  并按 0 上报。三个调用方（orchestrator ×2、source_lifecycle restore、rebuild
  脚本）全部接 db。
- **残余窗口（如实披露）**：删除事务在校验**之后**才提交的毫秒级交错仍未闭环
  （原窗口是整个 Celery 处理时长，分钟级）。彻底闭环需删除侧改为"DB 提交后再
  失效 Redis"（事务提交后钩子），记 follow-up；现状已把永久残留概率压缩到可忽略。
- 测试（真 Redis + 可控 db 桩）：`test_index_skipped_when_db_says_deleted_despite_stale_memory`
  （内存态 ACTIVE + DB 已死 → 零写入）、`test_index_compensated_when_deleted_during_write`
  （写入期间死亡 → 补偿清理，无残留）、`test_index_proceeds_when_source_alive`（对照）、
  `test_source_is_active_fresh_interpretation`（判定口径：缺行/软删/非 ACTIVE/NULL）。

## R2.5 D5 换模型 runbook（"先 rebuild 后切流量"）

已写入 `rebuild_embedding_index.py` 模块 docstring（执行者第一眼看到的位置），
要点：

1. **禁止直接改 .env 切流量**：版本隔离是硬过滤——切换瞬间旧版本行被
   `_embedding_version_filter` 无条件排除 + 新版本 Redis 索引（KNN+BM25 同索引）
   全空 → galaxy hybrid 双路皆空 → pgvector fallback 同样排除旧行 → 静默召回
   塌缩到纯词法，无任何报错信号。
2. 正确顺序：先用 `--model`（需要时 `--provider/--dim`）覆盖参数在**线上仍按旧
   配置服务**的状态下 rebuild（行重嵌+打标到新版本、新命名空间 Redis key 重建、
   新版本索引创建）→ 确认 summary/`FT.INFO num_docs` → 改 .env 切流量（切换
   即刻全量可用）→ 稳定后可选 `--prune-legacy`（注意它删**所有**非当前版本 key
   含回滚资产）。
3. 诚实窗口语义：rebuild 期间旧行逐步离开旧版本命名空间，旧版本召回单调下降
   （切换瞬间恢复）；"先切流量后 rebuild"则切换瞬间塌缩到 ~0 再恢复。两者都有
   迁移窗口，**零塌缩需要过渡期双读**（新旧命名空间 rank-list RRF 融合，rank
   融合天然容忍两个向量空间）——记 follow-up。
4. 换**维度**（≠1024）需列迁移而非 rebuild（DB 列 `Vector(1024)`，错维写入响亮报错）。

附带修正：脚本 `ensure_index` 收敛到 `--execute`（R2 实测发现 dry-run 会在 Redis
真实建索引——已修 + 已清理探针误建的 `idx:knowledge@dashscope_new_model_x_1024`）。

## R2.6 返修验证记录

```
# 4 个新测试文件（全绿；pytest 定向串行）
tests/services/test_embedding_fail_closed.py            17 passed（R1 12 + D1 新增 5）
tests/services/test_semantic_cache_version_isolation.py  5 passed（R1 3 + D2/D3 新增 2）
tests/services/test_rag_indexing_service.py              8 passed（R1 4 + D4 新增 4）
tests/services/test_embedding_live_green.py（E05_LIVE=1） 1 passed（embedding 缓存命中，
                                                         0 次新 API 调用）

# 相关回归（真实缓存层口径，全绿）
galaxy/test_retrieval_service.py（含 D3 新增 3 项）+ test_retrieval_fallback.py
+ test_retrieval_cache.py + test_semantic_cache_service.py      → 28 passed
test_rag_retrieval.py + test_vector_search.py + test_retrieval_keyword_search.py
+ test_expansion_service.py + test_seed_library_service.py
+ test_knowledge_service_semantic_search.py                      → 39 passed
test_graphrag_hybrid_retrieval.py + test_growth_tools.py         → 18 passed
test_hyde_rag.py + test_seed_content_content_backfill.py
+ test_seed_library_stage22.py                                   → 30 passed

# 脚本
rebuild_embedding_index.py dry-run（默认 + --model 覆盖）：目标版本/索引名/谓词
正确联动；dry-run 无 Redis/DB 副作用（实测 FT._LIST 前后一致）

# 真实 API 消耗：0 次新增（live green 命中 R1 预热的 embedding 缓存；
# 返修测试全部 mock 供应商或直测缓存/索引层）
```

未验证项（如实）：`test_document_retrieval_isolation.py`（live 集成）口径已修
（D2 真实缓存层断言），但本轮约束（dev DB 只读、API 预算）下未执行；其 D1/D3
相关断言与单测口径一致，留待下一次 live 窗口全量跑。
