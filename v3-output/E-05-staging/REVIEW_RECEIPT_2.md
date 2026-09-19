# E-05 Review Receipt — 第二路 Reviewer（DeepAudit 深层审计）

- reviewer: DeepAudit #2（E-05 risk=high 双审制；第一路标准验收已 ACCEPT）
- date: 2026-09-19 ｜ 审计对象: `Sparkle-sysrev/wt5 @ 57c87a8e`（未 commit diff + `v3-output/E-05/`）｜ 本收据: wt6
- 方法：wt5 全量 diff 精读（embedding/semantic_cache/rag_indexing/redis_search/retrieval/source_lifecycle/rebuild 脚本）＋ 链路推演（版本竞态/重建窗口/回滚/failover）＋ 定向 pytest（串行单文件）＋ /tmp 无副作用探针 1 个（mock 供应商，零网络零 DB 零 Redis 写）＋ dev Redis 只读观察
- 验证记录：`test_embedding_fail_closed.py` 12 passed；`test_semantic_cache_version_isolation.py` 3 passed（dev Redis）；`test_rag_indexing_service.py` 4 passed。测试 diff 断言只增强未弱化。
- 纪律：未改 Worker 代码、未跑 alembic、未写任何生产 key、真实 embed 0 次（配额未动）；探针在 /tmp/e05_review（已清理）。

## 深层审计发现（按任务书 6 焦点）

### D1 [P1·确认缺陷] failover 向量的版本戳取主供应商身份——版本溯源不变量被备用路径击穿
- **执行链**：`batch_embeddings` 供应商循环（dashscope 失败→siliconflow 成功，circuit breaker threshold=5/60s、open 30s 会拉长该窗口）→ 返回 siliconflow（`Qwen/Qwen3-Embedding-4B`）向量 → 所有写点（`file_processing_orchestrator.py:200`、`knowledge_integration_service.py:290`、`expansion_service.py:412`、`seed_library_service.py`×3、`galaxy_service.py:3466`）打 `embedding_model=embedding_service.current_embedding_version()`——该串**只读主供应商配置**（`_active_model_name` 无条件走 primary）。
- **动态证实**：mock dashscope 失败 + siliconflow 成功 → `PROVENANCE MISMATCH: True`（siliconflow 向量将打上 `dashscope/...` 戳）。两个 key 在生产 .env 均已配置。
- **后果**：① DB 溯源永久错误（直到重嵌）；② 跨模型向量混入同一版本 KNN——正是本卡要消灭的"相似度静默变垃圾"，在 failover 窗口重新打开；③ Redis embedding 缓存键按主供应商 token 命名，被备模型向量污染 300s（主供应商恢复后仍命中污染向量）。附加：`_siliconflow_embeddings` 不接收 `text_type`，即使同模型 failover 也系统性偏移向量空间（query/document 非对称性丢失）。
- **触发**：dashscope 短暂故障（5 次/60s 即熔断 30s）+ siliconflow 可用——标准故障场景。潜伏期：即时；影响持续到 rebuild。
- **修复**：`batch_embeddings` 返回实际服务供应商（或 resolved 版本串），写点与缓存键按实际来源打标；异模型 failover 可选直接 fail-closed。

### D2 [P1·确认缺陷] `knowledge:version:v1` 30s Redis 缓存在删除/写入路径均不失效——语义缓存删除隔离有 ≤30s 陈旧窗口
- **执行链**：`hybrid_search → _get_knowledge_version`（retrieval_service.py:136，TTL=`KNOWLEDGE_VERSION_CACHE_TTL_SECONDS=30`）→ 删除文档/节点后该 key 仍是旧版本 → 30s 内的 galaxy 检索（search_agent / knowledge_service 生产调用面）以旧版本组键 → **exact 与语义相似命中删除前写入的缓存条目** → 已删内容继续出答案。
- **证据**：该 key 全仓唯一引用点即 retrieval_service.py:136；`SourceLifecycleService.invalidate_source_retrieval`（source_lifecycle.py:227-240）删 chunk key + `galaxy:node_source_documents:*` + `graphrag:*` 但**不删它**；写路径同样不删。Worker 的 delete-isolation 测试直接调 `_compute_knowledge_version()`（test L222/289）**绕过了缓存层**——测试绿但生产语义不满足验收⑥"三路同时即时不可见"。
- **回答任务书焦点 1**：缓存失效是惰性；版本缓存兜底 30s（语义缓存条目本身 TTL 3600s，但版本隔离使其在版本 bump 后不可达——可达性窗口就是这 30s）。版本算法本身（行数+max(updated_at)，BaseModel onupdate）对软删/硬删/改内容均能变化，无碰撞疑点。
- **修复**：`invalidate_source_retrieval` 与 chunk/node 写点 `DEL knowledge:version:v1`（一行级修复）。

### D3 [P2·确认缺陷] 瞬时 embedding 故障的降级结果被语义缓存固化 1 小时
- `_execute_hybrid_search` 捕获一切 embedding 异常 → `_keyword_fallback`（词法）→ `get_with_lock` 把**降级结果**按正常结果缓存（TTL 3600，无降级标记）→ 供应商恢复后同查询继续命中降级答案最长 1h。缓存值无 mode 字段，无法提前失效或识别。
- **修复**：factory 返回携带降级标记则跳过缓存或短 TTL。

### D4 [P2·确认（预存边，焦点 4 范围内）] 删除与迟到的索引写入竞态 → 已删文件 chunk 永久残留 Redis（无 TTL）
- `index_document_chunks` 用可能过期的内存态 `file_record.lifecycle_status` 把关；Celery 处理中文件被并发删除（`invalidate_source_retrieval` 的 SCAN-DELETE 先跑完，索引写后到）→ 版本化 key 写入后**无人再删**（JSON.SET 无 TTL，graph_rag 生命周期过滤读的是文档自身字段=active）。pgvector/词法路径有 DB 谓词兜底，唯 Redis KNN 链路泄漏，直到该文件下次重建。非 E-05 引入，但验收⑥的并发版本未覆盖（测试为顺序执行）。
- **修复**：RAG JSON 文档加 TTL，或写入前 fresh SELECT 复查 lifecycle，或写后复核。

### D5 [P2·结构风险（焦点 2/5）] 模型切换 rebuild 窗口：旧版本行被硬排除 + Redis 新命名空间全程为空，无信号
- lenient（现默认）下 NULL→current 的**补标 rebuild 无召回缺口**（NULL 参与检索）——25/157 存量行安全。但**换模型** rebuild：旧版本行被 `_embedding_version_filter` 无条件排除，逐批重嵌期间向量召回只剩已处理行；且脚本的 Redis 重建在**全部 DB 重嵌之后**才跑（files_touched 循环在表循环外）→ 整个 rebuild 期间版本化 Redis 索引（KNN+BM25 同索引）为空 → galaxy Redis hybrid 双路皆空 → 全量走 pgvector fallback + keyword。症状是静默召回塌缩（无"因版本排除"指标）。切回旧模型的 rollback 同类：切换期间新写的数据切回后不可见（未丢，rebuild 可救），runbook 第 2 步覆盖但未言明。
- **运维要求**：换模型必须"先 rebuild 后切流量"，或过渡期双读；建议暴露 excluded-by-version 行数指标。

### D6 [P3] `--prune-legacy` 实际删除所有非当前版本 key（含文档声称保留的"旧版本回滚资产"），且不清理其它版本化索引（僵尸空索引累积）；脚本帮助文本与 runbook 行为不符。另：alembic downgrade 演练期间在跑应用会因 ORM 引用已删列而**响亮失败**（可接受，需知悉）。

### D7 [P3·预存，E-05 放大] `semantic_cache:keys` SET 只增不减（过期/SREM 均不清理成员），超 200 随机采样 → 长期运行语义命中率向 0 衰减 + 每次查找最多 200 次串行 GET。全局 knowledge_version（每用户写入都 bump）+ ev 入键放大 key 家族增速。建议周期性对账清理。

### D8 [P3] 工具 payload 的 `retrieval_mode=hybrid_lexical_vector` 只反映 key 配置不反映实际执行——供应商故障期（key 在、调用败）payload 谎报 hybrid（日志/指标有记录，agent 可见的结构化信号错）。

### 已核实无问题（对应任务书其余问点）
- **维度中途变更（焦点 3）**：列是 `Vector(1024)` 定型——错维写入/查询响亮报错，无静默混维；Redis 索引按版本建 DIM。注意换非 1024 模型需改列迁移而非仅 rebuild（runbook 未提）。
- **缓存投毒自愈（焦点 3）**：零向量/错维 embedding 缓存条目按 miss → 首次成功即覆写，无每请求重复放大。语义缓存 JSON 损坏条目跳过不放大。
- **并发首启动 ensure_index（焦点 2）**：`already exists` 捕获幂等；索引建前的 JSON 写会被建索引时回填。无缺陷。但 dev Redis 现存 `idx:knowledge@dashscope_text_embedding_v4_1024`（默认配置进程所建、num_docs=0、无任何 sparkle:* key）实证**配置漂移会静默分区命名空间**——生产纪律=全员同 .env。
- **DEMO_MODE×embedding（焦点 6）**：矩阵干净。唯一 embedding 零向量路径已删；llm_service/stt 的 demo 是文本/语音域，不产假向量；rerank 失败→RRF 有日志+指标非静默。
- **嵌套重试风暴（预存）**：get_embedding×batch_embeddings 双 tenacity（最多 18 次供应商调用、~24s）在断供首发期拖慢语义缓存读——HEAD 既有，E-05 的 NotConfigured 不重试已是改善。

## 结论
Worker 的工程质量和披露诚实度高（R1 已验项不重复质疑），fail-closed/隔离/基准等主线交付成立。但深层审计在**版本化机制自身的两条旁路**上发现生产可达的确认缺陷：D1（failover 击穿版本戳——本卡核心不变量）与 D2（删除后 ≤30s 语义缓存陈旧窗口——直接违背验收⑥"即时不可见"）。两者都是局部小修复（版本戳按实际供应商；删 version 缓存 key）。D3/D4 建议同批修，D5 转运维 runbook 约束，D6-D8 记 follow-up。

VERDICT: CHANGES
