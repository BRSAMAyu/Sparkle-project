# M-03 REVIEW_RECEIPT — 第一路独立 Reviewer

- reviewer: R1（M-03 risk=high 需 2 Reviewer 之路 1）
- date: 2026-09-19
- 对象: wt4 未 commit 改动（9 文件 +1704/-6，基线 43942d23）+ v3-output/M-03/ 交付物
- 方式: 全量代码审读 + stash 红态亲手复现 + 测试实跑（串行）+ 基座迁移重叠比对 + patch 逐项核对
- 环境: 磁盘 19G 可用、swap 空闲 1.68G、load ~4.9（开工门禁通过）；全程 LIGHT，无模拟器/浏览器

## 0. Worker 自报逐条重验结果

| # | 自报 | 重验 | 结论 |
|---|---|---|---|
| 1 | 单一权威模块 701 行、纯函数核心+唯一异步适配器、封闭词表、M-01 委托、固定求值顺序 | 逐行读 `memory_retrieval_prefilter.py`：词表全部 `MappingProxyType/frozenset` 封闭；`derive_status/derive_scope/classify_episodic_class` 均自 M-01 契约导入、零重复定义；`prefilter_candidates` 零 I/O，`build_retrieval_context` 是唯一 async 边界（settings 读失败→默认放行，best-effort） | **属实** |
| 2 | 双接线点 + metrics | `context_manager.py:384-389`（`_get_past_session_memory` 内，importance/confidence/created_at 重排**前**，覆盖 :240 缓存命中刷新与 :288 全新构建两调用点，整块 try fail-closed）；`context_pack.py:1272-1283`（三族拉取后、rank/语义门控前；`pref_history` 刻意不过滤）；`business_metrics.py:240` 注册 `sparkle_memory_prefilter_rejections_total{dimension,reason}` + loguru + pack `metadata["memory_prefilter"]` | **属实** |
| 3 | 红绿 + 58/58 + 回归 | 亲手复现：stash 两接线文件 → 集成 **5 failed**，其中两个指定红断言逐字命中（`superseded row leaked: [...'SUPERSEDED-episodic'...]` 真 DB 实漏、`wrong-user row leaked: ['REVOKED','WRONG-USER','STAGE-LEGAL']`）；`stash pop` → **5 passed**。单测 53 + 集成 5 = 58 passed。回归抽样 5 文件全过（context_manager 3 / past_session_ranking 4 / h6 4 / context_pack 5）。声称的唯一预存失败 `test_two_consecutive_sessions_prompt_includes_inferred_memory` 在接线态与全 stash 基线态**同样失败**（LLM demo-mode 环境性），预存性重证属实 | **属实** |
| 4 | 基座迁移零重叠 | `git diff --name-only 6f488636..43942d23` = 20 文件（action_plan/task 域 + E-01/X-01 文档 + fleet state）；与 M-03 的 6 个 tracked 改动文件 `comm -12` 交集为**空** | **属实** |
| 5 | patch +1704/-6、9 文件、无密钥、reverse-apply | `git apply --numstat` = 9 files +1704 -6；`git apply --check --reverse` **PASS**（patch 与工作区在基 43942d23 上严格一致）；密钥扫描零命中（唯一 grep 命中为注释 "ta**sk-**shape axis" 误报） | **属实** |
| 6 | 遗留三项 | 见 §2.F2（第三项"其余读侧消费者"清单不完整）；sensitivity/task_type 今日零行为经代码证实（`sensitivity_of_record` 恒返 normal、`scope_of_record` 恒置 task_type=None + 对应单测）；settings 缓存时效登记 M-07 合理（每 pack 构建点查 settings 唯一索引，代价可接受） | **大部分属实，见 F2** |

## 1. 预筛器设计专项（复核点 1）

- **固定求值顺序语义成立**：user→status→ttl→scope→purpose→sensitivity 与 MEMORY_V3 §3 步骤 1-5 对映（revoked 归 status 维度、reason `status:revoked`，不重复设维）。`or` 短路链使首个失败维度独占归因，指标确定性有测试钉住（`test_evaluation_order_user_owns_rejection_before_status`：wrong-user+revoked 双违例行断言 dimension=="user"）。user 先于 status 合理——身份越界是最重归因，且与 pipeline 序号一致。
- **lattice 测试是组合完备而非抽样**：`test_scope_compatibility_matrix_is_total_and_closed` 断言矩阵键集 == SCOPE_LEVELS × 3 态全叉积（封闭结构验收）；`test_scope_matrix_parity` 以 5×3 双层参数化逐格构造 (descriptor, ctx)，先 sanity 断言求值器确实落入目标态、再断言裁决与表一致（15 例）。global 的 match/mismatch 两格如实标注"结构不可达、死但安全"并断言恒真。session fail-closed、未知 level fail-closed、无锚点 scoped 记录按 user-global 放行均单测锁定。
- **M-01 委托无重复定义**：status 优先级（revoked>superseded>retracted>archived>expired>resolved）完全复用契约 `_STATUS_PRECEDENCE`；本模块只加 TTL/purpose/sensitivity 语义。
- 附带确认：3 个既有测试的夹具改动是**加强**而非弱化——mock 行补真实 `user_id`（真实 DB 行必有），`past_session_ranking` 还顺手修正了 `user_id=None` 的类型违例调用。

## 2. 发现的问题

### F1（轻微，必修）：M-03 新引入 ruff I001
`context_manager.py:30` 新增 import 排在 `memory_service` 之后，isort 要求 `memory_retrieval_prefilter` 先于 `memory_service`（"memory_r" < "memory_s"）。基线 stash 后 ruff **通过**、接线后触发 I001——即此 violation 是本卡新引入。报告 §4 的 "ruff all passed" 仅对 4 个新文件成立，未披露此点。修复=两行互换。
（black 噪音：context_manager 与 business_metrics 经 stash 对照确认为**基线预存**，报告该条声明属实；4 个新文件 black clean。）

### F2（中等，必修）：§6.4 "其余读侧消费者"清单不完整，且漏掉 LLM 邻接度最高的一条
全仓 grep `list_recent_episodic/list_active_goals/list_preference_records` 消费者，报告已列 state_aggregator / router_context_reader / task_reflection / memory_eval / API 列表，但**漏了**：

1. **`orchestration/context_builder.py:591` `_attach_stage34_memory_context`（:1038 在主聊天 payload 组装链调用）**：独立拉 `list_recent_episodic(limit=12)` 取 top5 写入 `payload["episodic_memories"]` 与 `cognitive_context["episodic_memories"]`，`prompts.py:3506-3516` 将其渲染进系统提示词（section 权重默认 medium）。此路径今天仍会注入：superseded 行（红测已证 list_recent_episodic SQL 不过滤 superseded_by_id）、过期 due_at+7d 承诺、`allow_episodic=false` 用户的 episodic——即卡片验收"illegal candidate 在 semantic retrieval 前为 0"在两条指定路径上成立，但在**主聊天面经 stage34 平行注入并不成立**。两条指定路径的接线本身无错（漏接≠错），但报告声称"如实"列遗留而漏掉最关键一条，必须补记。
2. **`orchestration/routing_engine.py:2530` SignalAggregator → `aurora/signal_aggregator.py:_collect_memory`**：拉 goals/preferences/recent_episodic 进 stage4 路由 snapshot（budget 4000 tokens），同样未过滤未披露。

**要求**：(a) REPORT §6.4/§7 补记上述两路径（stage34 须显式写明"今日仍绕过预筛，superseded/expired/allow_episodic=false 候选可经 stage34 进提示词"）；(b) 交由协调者裁决：stage34 接线在本卡返工内完成（`apply_memory_prefilter` 为纯函数，单调用点约 5 行）或登记为 M-04 首项——两者皆可，但**合入前记录必须存在**。

### F3（不阻塞，记录）：descriptor.goal_id 语义褶皱
`scope_of_record` 把 goal 级记录的 `linked_task_id` 同时填入 `descriptor.goal_id` 与 `descriptor.task_id`；`LEVEL_ANCHOR_KEYS["goal"]` 含 `goal_id`——未来若有 ctx 以 `goal_ids` 约束，实际比对到的是记录的 **task** 锚。今日无调用方传 goal_ids（context_pack 只传 plan_id，context_manager 不传锚），零影响；M-04 接线 goal-id 约束时需先裁决该字段语义（改名或补真 goal 锚）。

## 3. 实测记录（串行，SECRET_KEY/JWT_SECRET=test）

```
tests/unit/test_memory_retrieval_prefilter.py        53 passed (0.31s)
tests/unit/test_memory_prefilter_integration.py       5 passed (2.9s)   [stash 后 5 failed → pop 后恢复]
tests/test_context_manager.py                         3 passed
tests/unit/test_past_session_memory_ranking.py        4 passed
tests/aurora/test_h6_dialogue_quality_audit.py        4 passed
tests/unit/test_context_pack.py                       5 passed
test_two_consecutive_sessions_prompt_includes_inferred_memory   接线态 FAIL = 基线态 FAIL（预存重证）
black: 4 文件 unchanged；context_manager/business_metrics 预存噪音 stash 对照属实
ruff: 新文件 clean；context_manager I001 = 本卡新引入（F1）
```
注：wt4 无 `app/gen`，review 期间以符号链接借用主仓生成物（只读），收工已撤除。

## 4. 结论

代码本体质量高：单一权威模块、封闭词表、M-01 委托干净、组合完备的 lattice 测试、真实 DB 红绿证据、零迁移、零行为回归（夹具均为加强）。两条指定路径的接线与 metrics/观测面完全符合自报。判 **CHANGES** 仅因两件小事：F1 一行 import 顺序修复；F2 报告遗留清单补记 + stage34 处置裁决（接线或登记，二者择一）。不涉及设计返工，预计返工量 < 30 分钟。

VERDICT: CHANGES

五句总结：(1) M-03 的两处接线、58/58 测试、真 DB 红绿链（含 superseded SQL 实漏与 wrong-user 两红的亲手复现）、基座零重叠与 patch +1704/-6 reverse-apply 全部重验属实。(2) 预筛器设计合格：求值顺序有测试钉住、lattice 15 格组合完备非抽样、M-01 委托零重复定义。(3) 但报告 §6.4 遗漏了 LLM 邻接度最高的未接线读路径——stage34 `context_builder` 的 episodic 注入仍会让 superseded/expired/权限关闭的候选进入聊天提示词，routing SignalAggregator 同漏。(4) 另有本卡新引入的一行 ruff I001 未披露。(5) 返工仅限：补记录、修 import、对 stage34 作"本卡接线或登记 M-04"的裁决，代码设计无需返工。
