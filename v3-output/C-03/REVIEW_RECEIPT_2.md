# C-03 · R2 深层验收回执（DeepAudit / 第二验收员）

- 审查对象：`Sparkle-sysrev/wt4` @ HEAD 0ea1e198（6 M + 5 untracked + v3-output/C-03）
- 审查员：R2（wt4 独占；接续 R1 之后独立复审）
- 日期：2026-09-19 ｜ 用时约 1h ｜ venv 只读借用 sparkle-cosmos；真实 LLM/embedding 0 次
- 方法：逐行读核心模块+四处接线+全部 37 新测试 → 外送面全仓 grep 闭合 → 6 组独立变异（5 必红 + 1 预期绿缺口证实）→ /tmp 克隆基线归因 → 主仓 820c0203 合入预演

## 总 Verdict：**ACCEPT**

核心怀疑面（过滤语义正确性 / 外送面覆盖 / 性能断言真实性 / fail-closed 粒度 / 观测冻结 / 主链接线）全部实证通过，未发现「测试全绿但产品语义已错」级缺陷。1 条 P2（观测发射无守卫——补充建议，不阻塞合入）+ 2 条 P3。

---

## 风险面 1：过滤语义正确性 — **PASS**

| 检查项 | 结论 | 证据 |
|---|---|---|
| 与 M-03 固定顺序同构 | ✅ | M-03 `FILTER_DIMENSIONS` user→status→…（身份先于状态）；C-03 `KNOWLEDGE_FILTER_DIMENSIONS` identity→lifecycle 同构。`test_filter_dimensions_order_is_pinned` + M-03 侧 order 测试双向钉死。两滤芯处理不相交候选集（memory 记录 vs knowledge chunk），无顺序冲突。 |
| 串联归因可区分 | ✅ | reason 前缀分离（`knowledge:*` vs M-03 `user:*`/`status:*` 等）；两个独立 Counter（`KNOWLEDGE_PREFILTER_REJECTIONS_TOTAL` / `MEMORY_PREFILTER_REJECTIONS_TOTAL`）；管道报告按 channel 分节，memory 通道 version 原样携带 M-03 版本（`test_pipeline_memory_channel_delegates_to_m03` 断言）。perf 测试同时断言 `user:wrong_user` 与 `knowledge:wrong_user` 计数并存不串。 |
| 外送面全量盘点（rerank/embedding/LLM） | ✅ 无第三条绕行路径 | **rerank 远程调用点全仓恰 4 处**（grep 实证）：galaxy:345（本卡接线，滤后）；galaxy:477 `_pgvector_fallback`（候选=`semantic_search_ranked_nodes` 纯 KnowledgeNode 查询，SQL 已核，权限中性）；galaxy:780 `document_hybrid_search`（SQL 谓词 `or_(DocumentChunk.user_id==user_id, GroupMember.id.isnot(None))` 已核，pool 前过滤）；graph_rag:1201 `_rerank_hybrid_results`（唯一调用方 1815 = 滤后融合结果，grep 闭合）。**embedding 内容外送**：context_pack:1070（M-03 守卫 W-M 钉）、file_processing_orchestrator:178（写方授权面）、community_service:3284（跨用户 Goal 社区发现——产品预期的社区共享面，SQL Goal 域非 RAG 索引，非本卡漏点）、plan_matching:219（自有 plan）。检索路径 `get_embedding` 均只嵌 query 文本。**LLM 消费 chunk 正文**：graph_rag fused_context（滤后池）、SearchAgent（galaxy 滤后）、material_retrieval_tools（SQL 域）。 |
| 写方 parity | ✅ | `rag_indexing_service` 是 RAG 索引唯一写方（三个 key builder 无其他调用方，grep 实证）。node_description 恒无身份字段（→SHARED 放行正确）；personal chunk 恒带 user_id 无 group_id；group chunk 两者皆带且滤芯 group 判定优先（`test_group_scope_beats_user_match` 钉死——与旧内联检查判定序一致，成员可见性不被上传者 user_id 干扰）。 |
| galaxy 修复真实性 | ✅ | 基线（HEAD）`_execute_hybrid_search` 确无任何权限检查，融合候选正文直送远程 rerank。他人 personal chunk 的 parent_id=file_id 不在 KnowledgeNode 装配集——**基线最终结果也丢弃它们但正文已离境**，故修复无用户可见检索回归（只消除外泄+预算浪费），报告 §2/§3.3 论述与代码一致。 |

## 风险面 2：性能断言真实性 — **PASS**

- `test_context_retrieval_pipeline_perf.py` 是**测试内永久可重跑**的断言（非一次性脚本输出）：绝对预算（2000 候选 <5s、4000 <10s）+ 线性比（per-cand @2000/@100 ≤3x）+ **正确性随规模不漂移**（每档 rerank 输入非法候选恒 0、合法计数与构造 split 精确一致）三重钉死。
- 本机复跑剖面：200/500/1000/2000/4000 候选 = 1.79/4.26/**8.60**/17.18/**34.88ms**，per-cand 8.52-8.95µs，ratio **0.97x**——与 REPORT 的 8.2/34.2ms/ratio 1.00x 同噪声带内一致。合成向量 rerank、seed 固定、best-of-3，方法学健全。
- 「过滤前全量加载 vs 流式」：候选池在检索层已被 paging 截断（galaxy limit×10/面；graph_rag max(top_k×4)），滤芯面对的是有界列表；4000 档是压力上界而非生产规模。无 SQL-in-filter（滤芯纯函数）。

## 风险面 3：fail-closed 边界 — **PASS（粒度合理，无过紧误杀）**

- **redis 不可用/索引缺失**：`search()` 返回 None → galaxy `vec_docs=[]`/graph_rag `getattr(None,"docs",[])`→空列表 → 滤芯零输入零砍 → 各自降级路径（pgvector_fallback=KnowledgeNode 中性 / keyword_fallback SQL 域）——通道级降级不误杀。
- **维度不匹配**：E-05 版本化索引隔离；滤芯不触向量。N/A。
- **lifecycle 缺失（既有索引未重建）**：放行（传输面不可判）——不凭缺失砍合法候选；删除即时可见性归 E-05 key 失效。已在 REPORT §8.1 如实登记（含重建入口）。注意 graph_rag BM25 面在 HEAD 就已 RETURN lifecycle_status，说明「RETURN 非索引字段返回空而非报错」是既有生产验证行为，登记可信。
- **身份字段缺失**：source_type 缺失→`unknown_source_type` 砍（fail-closed）。唯一写方恒写 source_type + E-05 版本前缀隔离老 key——过紧风险不成立。测试夹具适配（test_graphrag_hybrid_retrieval 补 source_type/user_id）与写方不变量对齐，非守卫弱化（diff 已核：测试意图 embedding 故障降级保持）。
- **no_user_context**：主链 retrieve(user_id) 恒有主体；galaxy user_id_uuid 必填。收紧方向正确。
- **过紧误杀排查**：galaxy group 候选 fail-closed 经查**无用户可见回归**（基线装配面本就丢弃）；node_description 共享面不受任何收紧影响。

## 风险面 4：观测形状冻结 — **PASS（含 1 条 P2 缺口）**

- 报告 key 集：`PIPELINE_REPORT_KEYS`/`CHANNEL_REPORT_KEYS`/`RERANK_REPORT_KEYS` 常量冻结测试 + 行为级 `set(report)==set(KEYS)` 双钉；变异 M-R2d（注入 extra key）→ 2 红，实证。
- Label 词表封闭性：dimension 取值集 = {identity, lifecycle}（`test_filter_dimensions_order_is_pinned` tuple 等式钉死）；reason 6 值逐字冻结（`test_reason_codes_frozen`）。新增维度/reason 必动冻结测试，不静默；`dimension_counts` 用 `.get(key,0)+1` 兜底，即使 enum 扩展也不丢计数。基数 = 2×6=12 序列，封闭。
- **缺口（P2，见发现 1）**：Counter 的 inc() 发射本身无契约测试。

## 风险面 5：接线完整性（主链生效路径）— **PASS**

- 主聊天链 knowledge 候选池路径实证：`orchestrator.py:1929` / `standard_workflow.py:1185` → `GraphRAGRetriever.retrieve()` → multi-hop（base:973/concept:997）与 fastpath（1508/1606）**全部经 `_vector_search_scoped`** → `vector_search` → `_redis_hybrid_search`——滤芯在 dense/BM25 两路、RRF 融合与 rerank 之前。graph_rag 路径群组上下文有解析（`_resolve_group_scope`→allowed_group_ids），群组知识在主链可用（与 galaxy 路径的 fail-closed 不同，边界登记准确）。
- memory 通道主链走 context_pack（M-03 拥有），本卡 W-M 行为+AST 守卫钉住该边界（wrong-user/revoked 不进 rank 输入与语义门控 embedding 调用）；context_pack.py 与 HEAD **零 diff**（已核）。卡面「candidate pool 前」在两个通道的天然池边界各自满足，架构主张（不重建权威真源）与实现一致。
- HyDE probe（`_probe_query_chunk_similarity`）经 `_redis_doc_matches_user` 布尔兼容面收敛到同一滤芯（语义收紧已 docstring 登记）。

## 风险面 6：测试语义与变异验证 — **PASS**

37 新测试 + graphrag 4 测试全绿复跑（41 passed, 3.00s）。R2 独立变异 6 组（每组单文件粒度，/tmp cp 备份，还原后 `cmp` 逐字节校验，最终树状态=交付态）：

| # | 变异 | 结果 | 锁定测试 |
|---|---|---|---|
| M-R2a | 滤芯维度顺序交换（lifecycle→identity） | **1 红** | test_identity_owns_attribution_when_both_dimensions_fail |
| M-R2b | group_inaccessible 检查旁路（return None） | **4 红** | test_group_chunk_group_scoping / test_group_scope_beats_user_match / test_counts_and_input_count / **W-K1 行为级**（群组 chunk 进 rerank 被抓） |
| M-R2c | galaxy 管道调用→直送 rerank（基线态复原） | **2 红** | W-K1 行为 + W-K1 AST |
| M-R2f | graph_rag 两处滤芯→透传 | **2 红** | W-K2 行为 + W-K2 AST |
| M-R2d | build_pipeline_report 注入额外 key | **2 红** | test_pipeline_report_shape_and_tokens / test_build_pipeline_report_is_sole_serialization_authority |
| M-R2e | 删除 Prometheus inc() | **37 全绿（预期）** | 无——P2 缺口实证 |

- AST 钉法（常量假守卫剪枝）经 M-R2c/M-R2f 的 AST 侧红验证机制有效（与 R1 的 M-M `if False:` 实验互补）。
- galaxy_concurrency 3✗ 预存归因：/tmp 克隆基线（HEAD 0ea1e198 零改动 + gen symlink）复跑同样 3✗（asyncpg InvalidPasswordError user "postgres"）——与工作树逐字同名 3 例，环境性归因**成立**。

## 风险面 7：合入预演 — **PASS**

- `changes.patch` 对树 `git apply --check --reverse` 通过（patch 与交付树逐字节一致）。
- 主仓 820c0203（含 FIX-07 Ledger）`git apply --3way --check`：6 个修改文件全部 cleanly，5 个新文件 direct apply（新文件常态）；无文件交集冲突；--check 不落盘，主仓只读未动。

---

## 发现清单

### P2-1 · Prometheus 发射无契约守卫（Observability gap；不阻塞合入，建议随下一卡补）
- **发现**：`KNOWLEDGE_PREFILTER_REJECTIONS_TOTAL.labels(...).inc()`（context_retrieval_pipeline.py:301）无任何测试断言。变异 M-R2e 删除该行 → 37 新测试全绿。
- **执行链**：重构/搬运代码时静默丢失指标发射 → 计数器永久为 0 → 「他人 chunk 被砍」这一安全正向信号不可见，且无人察觉。
- **为何隐藏**：词表冻结测试守的是「取值域」，不是「发射行为」；报告声称「Prometheus 恒可用」的属性一半无守卫。
- **证据**：grep 全仓无测试引用该 Counter；M-R2e 实测。
- **修复**：单测中 `read_counter_value` before/after `prefilter_knowledge_candidates`，断言 labels(dimension,reason) 精确递增（一条测试即可）。

### P3-1 · 布尔兼容面把「本地探针跳过」计入 prefilter 拒绝指标 + 逐候选 INFO 日志
- HyDE probe（graph_rag:1354-1356）循环调 `knowledge_candidate_permitted` → 每个被砍 doc 一次 `inc()` + 一条 INFO 日志。探针只读本地 vector_score、无模型边界——这些计数与「候选池 prefilter 拦截」在指标上不可区分（语义轻微混淆），且每次主链 retrieve 最多 5 条单候选 INFO 日志。建议：probe 处一次批量调用滤芯，或 metric 文档注明含 probe 归因；非正确性问题。

### P3-2 · 已登记遗留复核确认（无新增遗漏）
- lifecycle dense 面需重建索引（登记 §8.1，重建入口在，删除可见性归 E-05 拥有——接受）；
- galaxy 路径 group fail-closed（登记 §3.3/§8.3，经查基线装配面本就丢弃 group chunk，无用户可见回归——接受）；
- galaxy hybrid 报告仅落日志（redis hybrid 无 telemetry 表，同 C-02 边界——接受）。
- 架构注记（非缺陷）：双通道管道入口（memory+knowledge 联合）目前仅 galaxy 接线实际使用 knowledge 单通道；主链两通道在各自天然池边界过滤（M-03 context_pack / C-03 graph_rag），联合顺序保证为库级+测试级。与模块 docstring 声明一致。

## 逐声称核验摘要

| Worker 声称 | R2 核验 |
|---|---|
| invalid 绝不送 model（5/5 变异红） | ✅ 复验：R2 独立 5 组必红变异全中（含行为级） |
| 外送面全量闭合（4 处 rerank 调用点） | ✅ grep 实证恰 4 处 + embedding/LLM 面逐一核过，无第三路径 |
| 观测冻结 | ✅ key 集/词表/顺序三冻结有测试；❗inc 发射无守卫（P2-1） |
| 性能 8.2ms/34.2ms 线性 ratio 钉死 | ✅ 复跑 8.60/34.88ms ratio 0.97x，断言在测试内永久可重跑 |
| 回归 480+ 全绿；galaxy_concurrency 3✗ 预存 | ✅ 41 例复跑绿；3✗ 基线克隆重证（asyncpg 密码） |
| 遗留边界登记 | ✅ 三条登记经独立核查属实且无遗漏新增 |
| 接续盘点（前任产物沿用+2 修复+1 夹具适配） | ✅ Any import 修复/graph_rag BM25 return_fields 等在 diff 中核实；context_pack 零 diff 属实 |

## 收工清理

- /tmp 自清：`/tmp/r2-c03-backup/`（变异备份）、`/tmp/r2-c03-baseline/`（基线克隆）已删除；无进程/模拟器/浏览器残留。
- 变异全部还原并 `cmp` 逐字节校验；`git status --short` = 交付原状（6 M + 5 untracked + v3-output/C-03）。
- 主仓只读（--check 不落盘）；dev DB 未触碰；未 commit/push。

**总 Verdict：ACCEPT**（P2-1 为合入后补充建议；禁止假通过声明——以上每项 Verdict 均附可复现证据）。
