# C-03 · Context 硬过滤→语义检索 Pipeline — 执行报告

- worktree：`Sparkle-sysrev/wt4`；base = HEAD **0ea1e198**（M-07 ACCEPT merge 后；未 commit/push，
  final SHA = base，全部改动见 `changes.patch`，11 文件 +2207 行，reverse-apply 校验一致）
- gate V3-2 ｜ stream CONTEXT ｜ risk high ｜ locks: context-retrieval ｜ depends: C-02✓ / M-03✓（均在树）
- 状态：**READY_FOR_REVIEW**
- 真实 LLM / embedding 调用 **0 次**（全合成向量/纯函数；venv 只读借用 sparkle-cosmos）

## 0. 六句总结

形态：单一权威模块 `backend/app/services/context_retrieval_pipeline.py`——knowledge 权限预筛纯函数
`prefilter_knowledge_candidates`（封闭 source_type 词表与 rag_indexing 写方 parity、冻结 6 个
`knowledge:*` reason code、维度顺序 identity→lifecycle 钉死、fail-closed 矩阵）+ 硬过滤→rerank
管道 `run_hard_filter_pipeline(_async)`（memory 通道**委托 M-03** `prefilter_candidates` 同语义同
version、knowledge 通道走本卡滤芯；rerank_fn 只见合法候选；缺上下文 fail-loud；报告 key 集冻结，
C-02 manifest 同纪律）。修复的实漏（基线无权限检查，变异实验即红态）：①galaxy
`_execute_hybrid_search` 把 RRF 融合候选（含**他人 personal chunk 正文**）直送远程 rerank 模型
（内容外泄+预算浪费）；②graph_rag `_redis_hybrid_search` 的内联布尔检查 fail-open（user_id 缺失
放行/无检索用户放行/无归因无指标/私有方法不可复用）——两处均收敛为候选池前置滤芯（RRF 融合与
rerank 之前）。memory 侧不加线只加守卫：W-M（sqlite 集成）钉死 M-03 在 `context_pack.build` 的
接线——wrong-user/revoked 记忆绝不进 rank 输入与语义门控 embedding 调用。变异 5/5 红（去掉过滤
三种形态 + fail-open 回归两种），全部逐字节还原复绿。性能：1000 memory+1000 knowledge（2000
候选）全管道 **8.2ms**、4000 候选 34.2ms，per-candidate 8.1-8.6µs **线性**（ratio 1.00x，bound
3x）；token 前后/逐阶段延迟/砍除归因随管道报告结构化落日志 + Prometheus
`sparkle_knowledge_prefilter_rejections_total{dimension,reason}`。

## 1. 接续盘点（前任 19:07 宿主重启阵亡 → 本段判定与处置）

前任已完成核心实现（全部经本段逐行评审后**沿用**）；本段补齐验证/修复/交付。

| 前任产物 | 判定 | 处置 |
|---|---|---|
| `services/context_retrieval_pipeline.py`（~740 行：滤芯+管道+冻结词表+报告权威） | **完成（合格）**——设计纪律与 M-03/C-02 对齐，docstring 完整 | 保留；本段仅修 `_resolve_ranked_sync` raise 前未消费 coroutine 的 RuntimeWarning（`raw.close()`） |
| `tests/unit/test_context_retrieval_pipeline.py`（29 tests） | 完成（合格） | 保留；black 26.x hug-parens 归一一处 |
| `tests/unit/test_context_hard_filter_wiring.py`（7 tests：W-K1/W-K2/W-M × 行为+AST） | 完成（合格；AST 钉法沿用 C-02 常量假守卫剪枝） | 保留，零改动 |
| `tests/unit/test_context_retrieval_pipeline_perf.py`（1000+ 合成稳定性+线性断言） | 完成（合格） | 保留；C408 修（dict()→字面量，本段引入语法错当场修复复绿） |
| 4 处接线 diff（business_metrics/redis_search_client/graph_rag/retrieval_service）+ devtools 脚本 + README | 完成但**含 2 处 lint 实错**：`retrieval_service.py` 闭包注解 `list[Any]` 而 `Any` 未 import（F821，被 `from __future__ import annotations` 掩盖为潜伏错）；import 序 I001 | 保留 + 本段修：补 `from typing import Any`、import 排序、脚本 B905（zip strict=） |
| `test_graphrag_hybrid_retrieval.py` 夹具失败（前任未处理） | 本段甄别：合成 doc 缺 source_type/user_id + 调用未传 user_id → 落入本卡 fail-closed 收紧面（生产写方恒写 source_type、graph_rag 四个内部调用点恒传 user_id，grep 实证） | 夹具适配（M-03 §4 先例，非守卫弱化），该测意图是 embedding 故障降级非权限行为 |
| REPORT.md / changes.patch / 变异实验 / 回归 / lint / 性能剖面数据 | **未做** | 本段全部完成（见 §4-§6） |

原则执行：无删除/重写前任合格工作；本段实质改动 = 2 处代码修复（Any import + coroutine close）+
1 处夹具适配 + 4 处 lint 归一 + 验证与交付。

## 2. 解决的真实问题（基线实证）

Redis RAG 索引（`idx:knowledge@{ver}`）是**跨用户共享索引**：galaxy dense 面 `vector="*"` 全库 KNN、
BM25 面无用户谓词——命中天然含他人 personal chunk。基线（0ea1e198）两处消费面均无法守住
「invalid candidate 绝不送给 model」：

1. **galaxy `retrieval_service._execute_hybrid_search`（无任何权限检查）**：RRF 融合后直接把全部
   候选正文送远程 rerank 模型——他人 personal chunk 的**文档正文离开系统边界**（发送到 rerank
   供应商），同时浪费 rerank 预算。变异 M-K1 即复原此基线态 → 行为+AST 双红（红→绿证据）。
2. **graph_rag `_redis_hybrid_search`（fail-open 内联检查）**：`_redis_doc_matches_user` 对
   `user_id` 缺失的 doc 放行（`not doc_user_id → True`）、无检索用户放行（`not user_id → True`）、
   词表外 source_type 放行；无逐候选拒绝归因、无指标、无复用面。变异 M-F1/M-F2 复原两个
   fail-open 分支 → 单测红。
3. **memory 侧边界（M-03 已接线，本卡守卫）**：`context_pack.build` 的 M-03 预筛在 rank/语义门控
   （embedding 调用点）之前——本卡 W-M 以 sqlite 集成测试 + spy（rank_items 入参 / batch_embeddings
   入参文本）钉死该边界，变异 M-M（`if False:` 禁用形态）→ 行为+AST 双红。

## 3. 设计（核心决策）

### 3.1 单一权威模块 + 依赖方向

`context_retrieval_pipeline.py`（`KNOWLEDGE_PERMISSION_FILTER_VERSION = "context-v3.c03.knowledge.v1"`、
`PIPELINE_SCHEMA_VERSION = "context_retrieval_pipeline.v1"`）：

- **knowledge 权限预筛**：纯函数 `prefilter_knowledge_candidates(candidates, ctx)`（零 I/O）。
  - 身份判定固定子顺序：source_type 词表 →（共享 node_description 放行）→ 无检索主体 → 群组 →
    个人 → 无归属；**lifecycle 仅在候选携带该字段时可判**（BM25 面带、dense 面重建索引前不带；
    缺失放行——删除即时可见性由 E-05 key 失效拥有，本层不凭缺失砍合法候选，docstring 登记）。
  - **fail-closed 收紧三处**（旧内联检查为 fail-open，测试逐条钉住）：无归属 document chunk
    （writer 不变量被破坏）、无检索用户（无可校验主体即无放行依据）、source_type 词表外
    （写方 parity 守卫钉死 `KNOWLEDGE_SOURCE_TYPES == {node_description, document_chunk}`，
    rag_indexing 加第三写方必红）。
  - **reason 封闭词表冻结**：6 个 `knowledge:*` code 逐字冻结（`test_reason_codes_frozen`）；
    维度顺序 identity→lifecycle 钉死（首失败维度独占归因，M-03 同构）；`Rejection` 数据类直接
    复用 M-03（rejections 形状单一事实源，D-06/O-02 无第二套解析）；`KnowledgeFilterResult`
    与 M-03 `PrefilterResult` 字段集逐字对齐（`test_result_shape_parity_with_m03`）。
- **管道核心**：`run_hard_filter_pipeline(_async)`——同步/异步面共用 `_run_channel_filters`（滤芯
  纯函数，两面语义逐字节一致，async 测试钉死）；memory 通道委托 M-03（同 allowed、同 metric
  payload、同 version 原样——`test_pipeline_memory_channel_delegates_to_m03`），**不重写任何
  M-03 规则**；跨通道合法列表恒 memory→knowledge 确定性顺序；rerank_fn 只见合法候选；
  `_validate_channel_contexts` fail-loud（给候选不给上下文 → ValueError，绝不静默当全合法）。
- **观测**：报告顶层/通道/rerank key 集冻结（`PIPELINE_REPORT_KEYS`/`CHANNEL_REPORT_KEYS`/
  `RERANK_REPORT_KEYS`），序列化唯一权威 `build_pipeline_report`（C-02 `assemble_manifest` 同
  纪律）；token 前后（`tokens_before/after/saved`，len//4 降级估算与 context_pack 同型）、逐通道
  延迟、rerank 延迟、rerank skipped 全携带；Prometheus
  `sparkle_knowledge_prefilter_rejections_total{dimension,reason}`（计数失败静默——指标永不破坏
  检索，M-03 同约定）+ loguru 结构化两线（滤芯逐次 / 管道汇总）。

### 3.2 接线面（两处新接线 + 一处兼容收敛；全 rerank 调用点盘点闭合）

| 面 | 接线 | 形态 |
|---|---|---|
| galaxy `_execute_hybrid_search` | RRF 融合后、远程 rerank 前 | async 管道（`_rerank_legal` 闭包保留原 timeout/fallback/指标语义，只换输入为合法候选）；BM25 面 return_fields 补 4 个身份字段（缺失即 fail-closed，见 §3.1） |
| graph_rag `_redis_hybrid_search` | dense/BM25 两路候选、RRF 融合与 `_rerank_hybrid_results` 之前 | 滤芯直调两处（allowed 子集进 fusion/rerank） |
| graph_rag `_redis_doc_matches_user`（HyDE probe 等） | 布尔兼容面 | 收敛为滤芯单候选判定（语义收紧见 docstring），新代码一律批量面 |

**刻意不接线（盘点闭合，非遗漏）**：`_pgvector_fallback`/`semantic_search_nodes`（候选是
KnowledgeNode 共享知识图节点，权限中性）；`document_vector/lexical_search` 与 pg_hybrid 文档检索
（SQL 谓词 `user_id == user_id OR 可访问群组` 已是 pool 前过滤，接滤芯=双写规则）；`_keyword_fallback`
（SQL KnowledgeNode 面，无 rerank 调用）。全仓 `rerank_service.rerank` 调用点共 4 处，逐一核过。

### 3.3 galaxy 路径的 group 语义（如实登记）

`_execute_hybrid_search` 构造 `KnowledgeAccessContext(user_id=...)` **不带群组集**（调用方未请求
群组 scope）→ group chunk fail-closed 砍（`knowledge:group_inaccessible`）。这与既有装配面行为
一致：group chunk 的 parent_id=file_id 本就不在 KnowledgeNode 装配集（该路径第 6 步按 parent_id
查 KnowledgeNode）。未来 galaxy 群组检索需求出现时，从调用方解析群组集传入即可（ctx 已有字段）。

## 4. 变异实验（5/5 红；每轮还原逐字节校验）

| # | 变异 | 红 | 锁定测试 |
|---|---|---|---|
| M-K1 | galaxy 管道绕过（融合候选直送 rerank——即基线态） | **2** | W-K1 行为（FOREIGN-SECRET-CONTENT 进 rerank 断言）+ W-K1 AST |
| M-K2 | graph_rag 两处滤芯调用→透传 | **2** | W-K2 行为（wrong-user/unattributed 进 fusion）+ W-K2 AST |
| M-M | context_pack M-03 接线 `if False:` **禁用形态** | **2** | W-M 行为（wrong-user/revoked 进 rank+embedding）+ W-M AST（C-02 常量假守卫剪枝捕获禁用形态） |
| M-F1 | 滤芯 no_user_context 回退 fail-open（旧内联检查语义） | 1 | test_no_user_context_fail_closed_for_document_chunks |
| M-F2 | 滤芯 unattributed 回退 fail-open（旧 `not doc_user_id→True` 语义） | 1 | test_unattributed_document_chunk_fail_closed |

每轮变异后 `cmp` 备份逐字节校验还原一致；`git status` 恢复交付原状（M-M 一度漏还原，本段自查
发现后立即恢复并复核 context_pack 与 HEAD diff 为空——已在过程内纠正，最终树状态干净）。

## 5. 性能证据（卡面验收「1000+ memory synthetic 下仍稳定」）

合成工厂：memory=真实 M-03 预筛（wrong-user/revoked/superseded/expired 四类非法，40%）+
knowledge=本卡滤芯（wrong-user/group-inaccessible/unattributed/lifecycle 四类非法，40%）；
rerank=合成向量余弦排序（**真实 LLM/embedding 0 次**）；确定性 seed=20260919；best-of-3。
**正确性随规模不漂移**：每档断言 rerank 输入非法候选恒 0、合法计数与构造 split 精确一致、
`user:wrong_user`/`knowledge:wrong_user` 计数逐档锁定。

测试版（含全部断言，`tests/unit/test_context_retrieval_pipeline_perf.py`）：

```
candidates  filter_ms  rerank_ms   total_ms  per_cand_us
      200       1.401      0.067      1.706         8.53
      500       3.439      0.168      4.155         8.31
     1000       6.837      0.324      8.206         8.21      <- 1000 memory + 1000 knowledge
     2000      13.573      0.652     16.271         8.14
     4000      28.105      1.602     34.242         8.56
linearity ratio (per-candidate us @2000scale / @100scale) = 1.00x (bound: 3x)
```

- 1000+ memory 档（2000 总候选）全管道 **8.2ms**（预算上界 5s，余量 600×）；4000 候选 34.2ms
  （上界 10s）。绝对预算 + 无超线性（ratio 1.00x ≤ 3x）双断言在测试内永久钉死。
- 独立复跑版：`scripts/devtools/c03_pipeline_perf_profile.py --scales 100,250,500,1000,2000`
  （同 seed 同工厂，观测输出 8.13-8.53µs/candidate，与测试版一致）。

## 6. 回归与 lint

| 套件 | 结果 | 备注 |
|---|---|---|
| C-03 新增三文件 | **37✓**（29 单测 + 7 接线守卫 + 1 性能） | |
| test_graphrag_hybrid_retrieval | 4✓ | 1 处夹具适配（§1），适配后绿 |
| M-03 套件（prefilter 单测+集成）+ C-02 套件（sources/contract/pack_sources）+ retrieval_fallback/keyword/intent + graphrag cache_key/trace_store + rag_cite_chain | **159✓** | 前置卡语义零回归 |
| context 家族（pack/conflicts/feedback/personalized_ranking/ranking/rollout/budget/focusing/ranker 等 -k 全集） | **155✓** | |
| tests/unit/orchestrator/ 全目录 | **125✓** | 与 C-02 轮同基数 |
| galaxy 域（concurrency/sprint_mastery/task_coupling）+ spine_degradation + budget_manager | 10✓ 3✗ | 3✗ 为 **预存**：`/tmp` 克隆基线（HEAD 0ea1e198 零改动）同样失败，asyncpg dev DB 密码认证（M-03 §9 同类环境性） |
| lint | 新文件 black(26.3.1)+ruff clean；modified 文件**本卡 hunk 干净** | business_metrics/graph_rag/retrieval_service 整文件存在 black 26.x **基线漂移**（HEAD 版本本身 fail，含 M-03 块单引号风格），不在本卡 hunk 内不整理（C-02 同裁决）；graph_rag:41 F401 为 HEAD 预存；scripts/ 无 black 配置，devtools 脚本随邻居 120 列风格 |

## 7. 改动清单（changes.patch 11 文件）

- 新增 `backend/app/services/context_retrieval_pipeline.py`（权威模块：滤芯+管道+冻结词表）
- 新增 `backend/tests/unit/test_context_retrieval_pipeline.py`（29）/ `test_context_hard_filter_wiring.py`（7）/ `test_context_retrieval_pipeline_perf.py`（1）
- 新增 `scripts/devtools/c03_pipeline_perf_profile.py`（剖面独立复跑版；README 登记）
- 修改 `backend/app/services/galaxy/retrieval_service.py`（管道接线 + BM25 身份字段 + Any import/import 序修复）
- 修改 `backend/app/orchestration/graph_rag.py`（两路滤芯前置 + 布尔面收敛）
- 修改 `backend/app/core/redis_search_client.py`（schema+RETURN 增 `lifecycle_status`，dense 面可判性）
- 修改 `backend/app/core/business_metrics.py`（`KNOWLEDGE_PREFILTER_REJECTIONS_TOTAL`）
- 修改 `backend/tests/unit/test_graphrag_hybrid_retrieval.py`（夹具身份字段适配）

复现（backend/ 下）：
```
SECRET_KEY="test-secret-key-for-pytest-only-0123456789abcdef" python3.11 -m pytest \
  tests/unit/test_context_retrieval_pipeline.py tests/unit/test_context_hard_filter_wiring.py \
  tests/unit/test_context_retrieval_pipeline_perf.py -q          # 37 passed
# 变异复现（任一守卫面）：按 §4 单文件改动 → 仅跑 wiring/单测 → 红；还原复绿
```

## 8. 边界与遗留（如实）

1. **redis 索引 schema 的 lifecycle 字段需重建索引才在 dense 面生效**：`TagField("$.lifecycle_status")`
   加入 schema 与 RETURN 后，既有索引（无该字段）dense 命中返回空 → 滤芯按「该传输面不可判」
   放行（identity 维度不受影响；BM25 面已带）。重建入口 `scripts/devtools/rebuild_embedding_index.py`
   （E-05）；删除即时可见性本就由 E-05 key 失效 + knowledge_version 语义缓存失效拥有（本层不重建）。
2. **galaxy hybrid 路径报告只落日志**（redis hybrid 无 telemetry 表，同 C-02 orchestrator 面边界）；
   逐通道 tokens/延迟/归因在 loguru INFO 两线可观测，Prometheus 恒可用。
3. **galaxy 路径 group 候选 fail-closed**：调用链无群组解析上下文（§3.3）——群组知识检索功能上线
   时需从调用方传入 allowed_group_ids。
4. **memory 通道接线归 M-03 所有**：本卡对 context_pack 只加守卫（W-M）不加线；routing_engine/
   aurora signal_aggregator 两处确定性路由面按 M-03 R2 裁决属 M-04 域，本卡不动。
5. 预存失败（非本卡）：galaxy_concurrency 3 例 dev DB 密码认证（基线克隆重证）；graph_rag:41
   F401（HEAD 在）；business_metrics/graph_rag/retrieval_service 整文件 black 26.x 基线漂移。
6. context_pack.py 最终与 HEAD 零 diff（本段变异实验一度改动，已恢复并校验）。

## 9. 收工清理

- /tmp 自清：`/tmp/c03-baseline`（基线克隆，含 gen 符号链接）、`/tmp/mk1|mk2|mm|mf-backup.py`、
  `/tmp/bm_head.py|gr_head.py|rs_head.py` 已删除；无进程/模拟器/浏览器；无 /tmp 残留探针。
- venv 只读借用（PYTHONDONTWRITEBYTECODE=1）；dev DB 未触碰；主仓只读；未 commit/push。
- 交付：`v3-output/C-03/{REPORT.md, changes.patch}`；`backend/app/gen/`（gitignored）按 C-02 R2-F6
  先例保留在交付树以保测试可 collect。
- 收工 `git status --short` 与交付清单比对一致（6 M tracked + 5 untracked + v3-output/C-03）。
