# C-03 · R1 标准验收回执（Standard Acceptance / 第一验收员）

- 审查对象：`Sparkle-sysrev/wt4` @ HEAD **0ea1e198**（6 M tracked + 5 untracked + v3-output/C-03；未 commit/push，final SHA = base）
- 审查员：R1（wt4 独占；与 R2 DeepAudit 独立双验收，R2 已判 ACCEPT 见 `REVIEW_RECEIPT_2.md`）
- 日期：2026-09-19 ｜ 真实 LLM/embedding 0 次 ｜ dev DB 只读（galaxy_concurrency 仅失败于 auth，无成功连接）｜ 主仓只读（--check 不落盘）
- 方法：patch/树逐字节比对 + 全 hunk 逐行读 + 6 批测试实跑（含全部失败基线归因）+ 性能实跑记录 + 契约并排比对 + 主仓 820c0203 合入预演 + wt8/wt9 冲突预测

## 总 Verdict：**ACCEPT**

R1 标准面（改动面 / 测试实跑 / 卡面 Acceptance / 契约一致性 / 合入预演）全部 PASS，0 必修项。
R2 的 P2-1 复核确认成立（非阻塞）。新增 1 条 R1 观察项（预存失败登记建议，非本卡引入）。

---

## R1-1 改动面核对 — **PASS**

| 检查项 | 结论 | 证据 |
|---|---|---|
| patch ↔ 树逐字节一致 | ✅ | `git apply --check --reverse changes.patch` PASS |
| status/diff 与自报一致 | ✅ | `git status --short` = 6 M + 5 untracked + v3-output/C-03，与 REPORT §7 清单逐文件同名（11 文件 = patch 内 11 个 diff header） |
| 无密钥 / 主仓绝对路径 / 夹带 | ✅ | patch 全文扫描 `/Users/`、`/home/`、`sk-`、key/password 赋值——唯一命中 `hashed_password="t"` 为测试夹具占位假值（test_context_hard_filter_wiring 内 User 构造），非泄密 |
| 接续员回滚 black 误排后 diff 最小面 | ✅ | 6 个 M 文件合计 **+89/−31、18 个 hunk**，逐 hunk 核过全部实质：business_metrics（Counter 定义 11 行）/ redis_search_client（schema TagField + RETURN 各 1 处）/ graph_rag（import + 布尔面收敛 + 两路滤芯前置）/ retrieval_service（Any import + BM25 补 4 身份字段 + `_rerank_legal` 闭包接线）/ 测试夹具（补 source_type/user_id 并加注释）/ README（1 行登记）。**无任何格式化噪声 hunk** |
| 仓库整洁规范 | ✅ | 一次性剖面脚本落 `scripts/devtools/` 且 README 已登记；报告落 `v3-output/C-03/` |

## R1-2 测试实跑 — **PASS（全部失败均基线归因复认）**

实跑命令见文末清单。结果矩阵：

| 套件 | 结果 | 备注 |
|---|---|---|
| C-03 新增 37（29 单测 + 7 接线守卫 + 1 性能） | **37✓ 3.42s** | 与 REPORT/自报一致 |
| M-03 prefilter（单测+集成）+ C-02（sources/contract/pack_sources）+ graphrag hybrid 4 | **122✓ 11.2s** | 夹具适配后 graphrag 4✓ 含内 |
| retrieval_fallback / keyword / intent + graphrag cache_key / trace_store + rag_cite_chain | **41✓ 10.2s** | |
| context 家族全 `-k "context"`（全 tests/unit 树） | **347✓ + 1✗** | 见 R1 观察 1：✗ 为预存（基线克隆同因），非 REPORT 自报范围所涵盖 |
| tests/unit/orchestrator 全目录 | **125✓ 11.7s** | 与 C-02 轮同基数 ✓ |
| galaxy 域（concurrency/sprint_mastery/task_coupling）+ spine_degradation_metrics + context_budget_manager | **10✓ + 3✗** | 3✗ = galaxy_concurrency 三例，**基线归因复认成立** |
| 性能（含 37 内复跑单列 -v） | **✓** | 见 R1-3 |

**galaxy_concurrency 3✗ 预存归因复认（/tmp 克隆基线法）**：`git archive HEAD(0ea1e198)` → `/tmp/c03r1-baseline`（零改动 + gen 符号链接）重跑同文件 → **同 3 例失败、同错误**（`asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "postgres"`）。环境性预存，非本卡引入。R2 结论独立复认一致。

## R1-3 卡面 Acceptance 逐项对照 — **PASS**

> 卡 `v3/07_tasks/cards/C-03.md`：① invalid candidate 绝不送给 model；过滤后 token/latency 可观测。② 1000+ memory synthetic 下仍稳定。

| 卡面条目 | Verdict | 证据 |
|---|---|---|
| invalid 绝不送给 model | ✅ | 三道守卫测试全绿（本席实跑）：W-K1 行为（galaxy rerank 只见合法候选）+ W-K2 行为（graphrag 融合前滤除）+ W-M（sqlite 集成 + spy：wrong-user/revoked 记忆不进 rank 输入与语义门控 embedding 调用）；性能测试内正确性钉（每档 rerank 输入非法恒 0、合法计数与构造 split 精确一致）随规模复跑。接线变异证据（R1 前任 5/5 红 + R2 独立 6 组）本席复核测试存在性与断言语义属实（`test_wk1_*`/`test_wk2_*`/`test_wm_*` 行为级+AST 级逐条读到）。 |
| token/latency 可观测 | ✅ | `CHANNEL_REPORT_KEYS` 含 tokens_before/after + latency_ms；`PIPELINE_REPORT_KEYS` 含 total_latency_ms + tokens_before/after/saved；key 集冻结测试（`test_report_key_sets_frozen`）全绿；loguru 两线（滤芯逐次 :313 / 管道汇总）与 Prometheus `sparkle_knowledge_prefilter_rejections_total{dimension,reason}` 代码实证 + **运行时探针实发**（1 次拒绝后 counter value = 1.0）。 |
| 1000+ memory synthetic 稳定 | ✅ | 本机实跑（记录）：**2000 总候选（1000 memory + 1000 knowledge）全管道 8.41ms**（预算 <5s）；**4000 总候选 33.71ms**（<10s）；线性比 **0.94x**（bound 3x）——与 REPORT（8.206/34.242ms、1.00x）及 R2（8.60/34.88ms、0.97x）同噪声带。规模语义已核（perf 测试 SCALES=每档双通道各 N，报告 candidates 列为总量 2N，REPORT 表格标注自洽无虚报）。 |
| Required evidence（base/final SHA / targeted tests / integration / receipt） | ✅ | SHA=0ea1e198 双向一致；targeted+回归 6 批实跑；W-M 为 sqlite 集成级；双验收回执齐（本篇 + R2）。 |
| Forbidden 四条 | ✅ | 未重建权威真源（memory 通道委托 M-03 原样、`context_pack.py` 与 HEAD 零 diff——git status 实证）；性能方法学如实声明合成向量（非 mock 冒充行为面，滤芯走真实实现）；行为级+集成级测试非纯静态阅读；改动方向为 fail-open→fail-closed 收紧，无守卫弱化（夹具适配与 rag_indexing 写方不变量对齐，diff 逐行核过）。 |

## R1-4 契约一致性 — **PASS**

| 检查项 | 结论 | 证据 |
|---|---|---|
| `KnowledgeFilterResult` ↔ M-03 `PrefilterResult` 字段集 | ✅ 逐字对齐 | 并排比对 `memory_retrieval_prefilter.py:291`（allowed/rejections/input_count/dimension_counts/reason_counts + allowed_count + to_metric_payload{version,input_count,allowed_count,dimension_counts,reason_counts}）——C-03 同字段集同 payload key 集，仅 version 常量不同；`test_result_shape_parity_with_m03` 存在全绿 |
| Rejection 形状单一事实源 | ✅ | C-03 直接 import M-03 的 `Rejection`（record_id/dimension/reason/detail），未造第二数据类 |
| reason/维度封闭词表风格 | ✅ | 6 个 `knowledge:*` code 逐字冻结（`test_reason_codes_frozen`）+ 维度序 identity→lifecycle tuple 等式钉死 + source_type 写方 parity（`test_source_type_vocabulary_pinned`）——与 M-03 的 `user:*`/`status:*`/`ttl:*` 前缀分离、独立 Counter（MEMORY_/KNOWLEDGE_PREFILTER_REJECTIONS_TOTAL 同构定义于 business_metrics.py 相邻位置），**不另造口径** |
| 管道报告 key 冻结纪律 | ✅ | `PIPELINE_REPORT_KEYS`/`CHANNEL_REPORT_KEYS`/`RERANK_REPORT_KEYS` 三常量 + `build_pipeline_report` 唯一权威序列化——与 C-02 `MANIFEST_TOP_LEVEL_KEYS`/`assemble_manifest`（`orchestration/context_sources.py:262/316`）同纪律同构，冻结测试存在全绿 |

## R1-5 R2 P2-1 快速复核 — **CONFIRMED（非阻塞，已记入已知边界）**

- grep `tests/` 全树：无任何测试引用 `KNOWLEDGE_PREFILTER_REJECTIONS_TOTAL`/`sparkle_knowledge_prefilter` → **inc() 发射确无测试钉住**，R2 判断正确。
- 补充运行时探针（R2 未做）：真实调用 `prefilter_knowledge_candidates` 一次后 `REGISTRY.get_sample_value(...)` = **1.0**——发射功能当下正常，缺的只是回归守卫（重构搬运时可能静默丢失且无测试报警）。
- 定级复核：同意 P2（非阻塞）；建议随下一卡补一条 `read_counter_value` before/after 断言即可。

## R1-6 合入预演与在途卡冲突预测 — **PASS**

**主仓 820c0203**（实证 HEAD=820c0203b935…）：`git apply --3way --check changes.patch` → **6 个修改文件全部 cleanly**（逐文件 "Applied patch … cleanly"），5 个新文件走 direct application（新文件常态）——**无冲突，--check 未落盘，主仓只读未动**。

**与在途卡文件重叠预测**：

| 在途卡 | 触碰面 | 与 C-03 交集 | 预测 |
|---|---|---|---|
| E-02（wt8，llm 面） | standard_workflow / llm_router / **core/metrics.py**（非 business_metrics）/ retrieval_intent / llm/fallback / llm_service + 2 新文件 | **无文件交集** | 无冲突 |
| M-04（wt9，orchestration/记忆面） | **business_metrics.py** / conflict_resolver / memory_epistemic_contract / memory_inferred_write_lane / memory_invalidation_pipeline + 1 新测试 | **business_metrics.py 重叠** | 见下 |

**business_metrics.py 冲突形态预测**：C-03 与 M-04 两 patch 基于**同一基线 blob（e6c1e647）**、在**同一锚点**（`MEMORY_PREFILTER_REJECTIONS_TOTAL` 定义块之后、`EVIDENCE_MISSING_CURRENT` 之前）各自插入独立 Counter 块——C-03 插 `KNOWLEDGE_PREFILTER_REJECTIONS_TOTAL`（+11 行），M-04 插 `MEMORY_CONFLICT_RESOLUTIONS_TOTAL` + `MEMORY_EPISTEMIC_GUARD_SKIPS_TOTAL`（+22 行）。**后合入者 `--3way` 必在该锚点产生 content conflict**：单 hunk、纯插入竞争、无行级交织。两块内容互不引用（不同 metric 名、无共享状态、`get_or_create_metric` 注册表天然兼容两者）——**语义冲突风险为零**；人工解决 = 两段都保留（先后顺序无关），解决后 `python3.11 -c "import app.core.business_metrics"` + prefilter 计数相关测试 smoke 即可。合入窗口建议主会话按本预测预留一次手工 resolve。

---

## R1 观察项（非阻塞）

1. **预存失败台账建议**：`tests/unit/services/test_user_insight_compiler.py::test_profile_context_service_compiles_canonical_user_insight_state_with_expanded_signal_families`（断言 `state.temporal_patterns["calendar"]["recurring_windows"]` → `assert []`）。本席用全树 `-k "context"` 扫出（REPORT 自报家族范围未涵盖该文件）；**基线克隆逐字同因复现 → 预存、非 C-03 引入**（user_insight_compiler 模块与 C-03 触碰面零交集）。建议主会话与 galaxy_concurrency 3✗ 并列登记预存失败台账，避免后续验收员重复归因。
2. R2 P2-1（counter 发射无守卫测试）维持 P2 非阻塞，见 R1-5。

## 实跑命令清单（backend/ 下，`SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest`）

```
# R1-2 六批
pytest tests/unit/test_context_retrieval_pipeline.py tests/unit/test_context_hard_filter_wiring.py tests/unit/test_context_retrieval_pipeline_perf.py -q        # 37✓
pytest tests/unit/test_memory_retrieval_prefilter.py tests/unit/test_memory_prefilter_integration.py tests/unit/test_context_sources.py tests/unit/test_context_source_contract.py tests/unit/test_context_pack_sources.py tests/unit/test_graphrag_hybrid_retrieval.py -q   # 122✓
pytest tests/unit/test_retrieval_fallback.py tests/unit/test_retrieval_keyword_search.py tests/unit/test_retrieval_intent_classifier.py tests/unit/test_graphrag_cache_key.py tests/unit/test_graphrag_trace_store.py tests/unit/test_rag_cite_chain.py -q   # 41✓
pytest tests/unit -k "context and not context_retrieval_pipeline" -q                                                                                            # 347✓ 1✗(预存)
pytest tests/unit/orchestrator -q                                                                                                                               # 125✓
pytest tests/unit/test_galaxy_concurrency.py tests/unit/test_sprint_galaxy_mastery.py tests/unit/test_task_galaxy_coupling.py tests/unit/test_spine_degradation_metrics.py tests/unit/test_context_budget_manager.py -q   # 10✓ 3✗(预存)
# 基线归因（/tmp git archive 克隆 + gen 符号链接）
pytest tests/unit/test_galaxy_concurrency.py tests/unit/services/test_user_insight_compiler.py::<该例> -q   # 3✗+1✗ 同因复现
# 性能（本机数字已记录）
pytest tests/unit/test_context_retrieval_pipeline_perf.py -v -s    # 8.41ms@2000 / 33.71ms@4000 / 0.94x PASS
# P2-1 探针
python3.11 -c "...REGISTRY.get_sample_value('sparkle_knowledge_prefilter_rejections_total',...)"   # 1 次拒绝后 =1.0
# 合入预演（主仓，只读）
git -C Sparkle-project apply --3way --check wt4/v3-output/C-03/changes.patch   # PASS
# 改动面
git apply --check --reverse wt4/v3-output/C-03/changes.patch                   # PASS
```

## 收工清理

- `/tmp/c03r1-baseline`（基线克隆）已删除；无进程/模拟器/浏览器残留；变异实验未做（R2 已覆盖，本席仅守测试存在性，未触碰交付树）。
- wt4 树未改动（只读审查 + 本回执写入）；未 commit/push；主仓与 dev DB 只读。

**总 Verdict：ACCEPT**（R1 标准面全绿；0 必修；P2-1 与预存失败台账为合入后建议；禁止假通过——以上每项 Verdict 均附本席实跑证据）。
