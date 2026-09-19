# E-05 Review Receipt — 第一路独立 Reviewer

- reviewer: 独立 Reviewer #1（E-05 risk=high 双审制）
- date: 2026-09-19 ｜ worktree: `Sparkle-sysrev/wt5 @ 57c87a8e`（未 commit）＋ `v3-output/E-05/`
- 方法：HEAD checkout 法独立复现 RED、只读核对主仓 `.env` 与 dev DB/Redis、独立跑测试、benchmark 对账、patch 逐文件比对、2 次真实 embed 探针（≤3 配额内，未输出任何 key）

## 逐项复核结果

### 1. Fail-closed 审查 — 通过
- **RED 独立复现**（`git show HEAD:...embedding_service.py` → /tmp 探针，无 key + DEMO_MODE=true）：`returned vector dim=1024 all_zero=True` —— 与 Worker 报告的红测输出逐字一致，旧行为真实存在。
- 新代码：无 key 前置检查抛 `EmbeddingNotConfiguredError` 且指明 `DASHSCOPE_API_KEY`/`SILICONFLOW_API_KEY`；tenacity `retry_if_not_exception_type` 确不重试（单测断言 spy 零调用）；DEMO_MODE 零向量回退整体删除。供应商返回错维度/零向量/条数不符在 provider 循环 try 内 raise → 被当作该 provider 失败 → 最终 `EmbeddingProviderError`，无任何占位向量出口。
- 缓存投毒：`get_embedding` 缓存命中校验 `isinstance(list) + len==dim + any(non-zero)`，全零条目按 miss 处理并覆盖（单测覆盖）。
- 降级路径均有显式标注：检索工具 `retrieval_mode=lexical_only_embedding_disabled` + `embedding_configured=false`（test_growth_tools.py:626-627 断言）；Redis hybrid 显式 warning 日志 → `_keyword_fallback`；语义缓存未配置时跳过语义相似路径（exact-match 保留）、写缓存不再因 embedding 失败整体失败。词法检索与向量检索权限谓词逐条比对一致（`user_id == user OR GroupMember`）。

### 2. 模型真相 — 通过
- 主仓 `.env`（只读）：`DASHSCOPE_EMBEDDING_MODEL=qwen3.7-text-embedding-flash`（L56）；`EMBEDDING_MODEL=text-embedding-v4`（L108）确为遗留标签——其唯一消费点 `llm_client.generate_embeddings` 无任何调用方。Worker 更正成立。
- 独立真实探针（fresh unique 文本，163ms 真实往返）：`dashscope/qwen3.7-text-embedding-flash@1024`，1024 维、norm=1.0、两文本 cos=0.74（非恒定）——模型身份与版本串派生逻辑与代码消费路径一致。
- 注：运行测试未加载 .env 时派生串为 `dashscope/text-embedding-v4@1024`（settings 默认值），生产以 .env 注入为准，无矛盾。

### 3. 测试 — 通过（2 个失败均已证明非 E-05 引入）
- `test_embedding_fail_closed.py` 12 passed；`test_semantic_cache_version_isolation.py` 3 passed（真 Redis）。
- 全量 `-k "embedding or retrieval or semantic_cache or isolation"`：**201 passed / 4 skipped / 2 failed**。失败逐一归因：
  - `test_com011_similar_goal_pursuers.py::test_embedding_failure_graceful_fallback`：用 `git archive HEAD` 到 /tmp 独立复跑，**HEAD 上同样失败**（`_ScalarVal` fake 缺 `.all()`，community_service 未被本卡触碰）——预存失败。
  - `test_adaptive_replanning_integration.py`：asyncpg 密码认证失败（环境问题；Reviewer 无 dev DB 写权限，不补跑）。
- 回归抽样 6 文件 44 passed；4 处既有测试更新均为追踪新行为（版本化 key、版本串含行数、动态索引名、工具 payload 新字段），无弱化断言。
- canary 逻辑亲读：两用户文档同入 `file_ids` 作用域 + 同题构造，摘除 user_id 谓词必然泄漏且断言（test:153）必然触发——红→绿机制真实可红。
- live green 测试通过（1 次调用，疑似命中 Worker 遗留缓存）；随后 fresh-text 探针补实。live 隔离测试未重跑（需写 dev DB，超出 Reviewer 权限），以代码审读 + Worker 证据采信。

### 4. Benchmark 复算 — 通过，表述诚实
- benchmark.json 内部一致：6 查询全部 rank=1 → hit@5/MRR@5=1.00；三策略 p50/p95/max 与报告表格逐项相符；meta 版本串与实测一致。
- 饱和性：per_query 返回集仅 1-2 条、查询-内容子串重合明显，hit@5 全 1.0 确系语料饱和；报告 §5/§9.5 已主动声明"证明接线正确性与时延画像，非策略区分度"——结论表述诚实。
- hybrid 132ms 主因 rerank API 往返、纯 RRF ~6.6ms 的解释与代码结构（wait_for 超时护栏 + 失败回退融合序）相符。

### 5. 版本隔离与迁移 — 通过
- e05 迁移（纯加法、可逆、不回填）与主仓文件逐字相同；dev DB 实测两表列齐备，`alembic_version=x01_20260919`——主仓链 `e05 → m01a → x01`（m01a 注明"E-05 已先行 apply e05"），e05 确在已应用链上。
- `rebuild_embedding_index.py` dry-run 独立复现：document_chunks 25 stale / knowledge_nodes 157 stale，与报告一致；dry-run 路径读前确认无写（`if not args.execute: continue` 先于 commit）；脚本自身无 key 时 fail-closed。`--execute` 未全量 live 跑已在 §4/§9.1 如实声明（配额约束），写路径函数与测试/基准同源。
- 修复确认：`_compute_knowledge_version` 加行数计数，堵住"删非最新行版本不变→语义缓存陈旧命中"；Redis delete 扫所有版本 + legacy 格式。语义缓存键/相似命中均带 embedding 版本。
- rerank 静默 no-op 真 bug 属实：`_extract_documents` 只认 `.content/.description/.name`，旧 `DocumentChunkResult` 三者皆无 → 融合序直接返回；加 `.content` property 修复属实。

### 6. patch 完整性 — 通过
- 28 文件 = 19 修改 + 9 新增；tracked 文件与 worktree diff 逐文件内容零差异；新文件嵌入内容与磁盘一致（含 REPORT.md/benchmark.json 自身）。
- 无 `.env`、无 `sk-*`/Bearer/长密钥赋值等模式命中；embedding 相关仅 `DASHSCOPE_API_KEY` 等环境变量名与 `"sk-invalid-key"`/`"sk-test"` 测试假值。

## 偏差与观察（均不阻塞）
1. **Redis 索引现状与报告 §4 不符**：现查 dev Redis 为 `idx:knowledge@dashscope_text_embedding_v4_1024` + legacy `idx:knowledge`，不存在报告所称的 `..._qwen3_7_text_embedding_flash_1024` 索引（疑被后续默认配置进程重建或收工清理时移除）。无实际风险：索引名按运行时配置派生、missing-index 自动 ensure_index 自愈；但发布窗口执行 rebuild 前应知悉此快照漂移。
2. 遗留常量 `RAG_INDEX_PREFIXES` 现仅被测试引用，建议后续标注 deprecated；`embedding_service.py` L59 行尾注释 `# text-embedding-v4` 已过时（实读 DASHSCOPE_EMBEDDING_MODEL）。
3. §9 遗留风险抽查属实：Redis hybrid KNN 全局 top-k 后 Python 侧过滤（graph_rag.py:1351）；`hybrid_search.return_fields` 确无 `lifecycle_status`，graph_rag.py:1713 恒走默认 "active"。

## 结论
Worker 自报 5 项全部经独立手段验证成立；红测真实、模型真相更正正确、测试绿区真实（2 个失败均为预存/环境）、benchmark 数字可复算且诚实声明局限、patch 干净完整。遗留风险披露充分。

VERDICT: ACCEPT
