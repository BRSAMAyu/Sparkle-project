# D-02 REPORT · Outcome Ledger 与 Evidence Type 正规化

- **Task**: D-02（stream DATA, risk high, reviewers_required=2, locks: outcome-ledger）
- **Status**: READY_FOR_REVIEW（R1 ACCEPT + R2 CHANGES 后**返修完成**，二次送审；未 commit/push；代码以 `changes.patch` 交付）
- **Base SHA**: `fedc6a8e`（worktree wt5）
- **改动形态**: 2 个新增代码模块 + 2 个新增测试文件（**92 项测试**，返修前 63）；**零 schema 变更、零写路径改动、零 Alembic 迁移**

---

## 0. R1+R2 返修记录（2026-09-19 第二轮，本节为返修增量）

R1 裁决 ACCEPT（附 C2-1/C2-2 文档项）；R2 DeepAudit 裁决 CHANGES（1×P1 + 5×P2 + 若干
P3）。合并裁决 = 全部 P1/P2 必修 + C2 文档项 + P3 酌情。逐项处置：

| # | 裁决项 | 处置 | 证据 |
|---|---|---|---|
| P1 | 跨流同刻 tie 分页重复（`_stream_anchor` 剥前缀比裸 UUID，同刻条件恒真） | **已修**：删除 `_stream_anchor`；各流 SQL keyset 改用**带前缀全局键** `'<source>:' \|\| id` 比较（`_stream_key_expr`），与 merged 全局排序严格同构；task 流内部续传锚点同步全局化 | 新增 6 项同刻回归（§5.1）全绿；变异「退回裸 id 比较」→ 6 项必红；live DB 真实同刻数据逐对验证恰一次（§7.1） |
| P2-1 | 证据验证只验归属不验来源（code 借 document ref 升 actual；无关旧文件/task:// 自己另一任务洗白） | **已修**：新增冻结映射 `EVIDENCE_KIND_REF_SCHEMES`（kind↔scheme 白名单，v1 仅 artifact/file×document://）；`task://`、`subtask://` 移出可解析集（指向行本身也是用户主张）；document:// 解析要求 **TaskDocument 显式挂载到被完成任务**（归属 ≠ 相关）；ref id 规范化为 canonical UUID | `TestEvidenceSourceConstraints` 9 项；变异「去 kind 配对门」「去关联性门」各必红 |
| P2-2 | StoredFile 生命周期被忽略（uploading/orphaned/revoked/erased 全算已验证） | **已修**：解析查询补 `status ∈ {uploaded, processed}` + `lifecycle_status='active'` + `erased_at IS NULL` + not_deleted | 参数化 4 状态 × 3 生命周期 + erased 共 8 项；变异「去生命周期过滤」→ 8 项必红 |
| P2-3 | focus 覆盖无时间方向（完成后的会话追溯升级） | **已修**：`_task_focus_sessions` 仅计入 `start_time < completed_at` 的会话（JOIN 比较，方言中立；跨完成窗口重叠的会话仍计入）；truth 单调性语义在 §4.3 说明 | `TestFocusTimeDirection` 3 项（含 start==completed 边界）；变异「去时间方向」→ 必红 |
| P2-4 / C2-2 | goal evidence 未映射且未声明（范围收缩零声明） | **文档已补**：§8 未做清单显式记录 goal 面排除决策（goals 是派生聚合面，入册即重复计数违反验收②；现无独立完成生产者，live 4 行；未来出现一等 goal-completion 生产者时 bump 版本走双人评审） | §8 决策记录 |
| P2-5 | 冻结纪律无测试牙齿（M1 改档位值全绿；M6 去 cohort 词全绿） | **已修**：契约测试逐 kind 钉死档位**值**（整表字面断言）；cohort 词表字面钉死 + 与 `leaderboard_service` 双向对照 | 变异 M1′/M6′ 复跑必红 |
| P2-6 | quiz/behavioral 流缺 `not_deleted_filter`（五流删除口径不一） | **已修**：两流 builder + `count_by_source` 均补；`_task_focus_sessions` 证据面同步补 | 删除口径测试扩展（task/focus/quiz/behavioral 四流一致）；变异「去 quiz 流过滤」必红 |
| C2-1 | REPORT §8①「outc_* 与 D-01 correlation.outcome_id 兼容」不成立（event_registry 强制 canonical UUID） | **文档已纠**：§2/§8① 改为已知限制——接线卡不得按原表述字面直填，需随 D-01 `evt_` 同款 follow-up（UUID 化包装或放宽校验） | §2/§8① + core 模块 docstring 同步修正 |
| P3-1 | quiz 流对脏 meta 整查询崩溃 | **已修**：`_safe_uuid_str` 降级（脏 task_id/node_id → 空关联，不 500） | `test_quiz_stream_survives_dirty_meta` |
| P3-6 | 充数断言 `assert service.query.__doc__ is not None` | **已删** | — |
| P3-4 | 「与 B-02 完全对齐」措辞过强 | **已改**：统一为「卡面四值 + B-02 demo 档合成词表」（core/测试 docstring 同步） | §4.2 |
| P3-3 | truth_coverage 截断语义 | **docstring 已明示**：total 与 ratio 均只反映截断窗内任务，无 truncated 标志（v2 需精确分布应改分组聚合 SQL） | 服务 docstring |
| P3-2 | 「quiz_passed/failed 代码路径在册」表述过强（无发射方） | **已改**：§3 注明「词表在册但**无生产者**（全库仅 FeedbackType 枚举与存储函数），quiz 接线卡应以 `trigger_task_id` 列为关联真源」 | §3 注 |

未处置（登记不修，超出本卡锁）：P3-5 消费点零接线（A-05/M-06/G-01 卡登记强制接线项）、
P3-7 主会话合入时确认无 `backend/app/gen/` 入库（本 worktree 现无该目录）、P3-8 import 期
断言的 fail-fast 设计（接受，在案）、P3-9 estimated/demo/unknown 生产者现状（与自报一致）。

**返修后基线**：92 项测试全绿（契约 36 + 服务 56）；R1 点名回归 5 套件 97 passed + 1 基线先在
失败（与 R1 独立复认一致，非本卡引入）；变异实验 9 组全部必红、全部还原（md5 校验）；
lint black(120)/ruff 全净。


## 1. 问题定义与起点事实

「完成 ≠ 点击」：今天的系统里，`tasks.status=COMPLETED` 的行与真实发生的成果之间没有机械区
分——用户点击完成即触发 mastery 上升、study_record 落库、outbox 发事件（GJ03 链 A）。跨模块的
outcome 视图不存在：task 完成在 `tasks`+`study_records`+`mastery_audit_log` 三处留痕，focus 在
`focus_sessions`，quiz 在 `expansion_feedback`，干预效果在 `behavioral_outcomes`——没有任何一个查
询面能把它们聚成「一个用户的真实成果流」，更没有去重（一次完成产生 N 行记录 = N 次计数）。

dev DB 只读实测（2026-09-19，起点事实）：

| 事实 | 数据 |
|---|---|
| `tasks` 完成行 | 378 COMPLETED（351 带 actual_minutes），`action_schema_version` 非 0 行（V3 行尚未生产） |
| `study_records` | 30 行 = task_complete 13（**11 行带 task_id = 完成管线回声**）+ error_review 12 + error_diagnosis 6 |
| `focus_sessions` | 2483 行（COMPLETED 2101 / INTERRUPTED 382），2292 行带 task_id |
| quiz 反馈（`expansion_feedback` meta source=quiz_*） | **0 行**（代码路径在册：GalaxyFeedbackService.collect_implicit_feedback，live 未触发） |
| `behavioral_outcomes` / `intervention_outcomes` / `intervention_strategy_outcomes` | 全 **0 行**（D-01 B2 断点继承：干预→outcome 存储面无真值） |
| 完成→回声链 | 378 个完成行中仅 11 个有 echo study_record（367 个完成连回声都没有——管线覆盖本身有断点） |

断点继承（D-01 REPORT §3 B1–B5 中与本卡相关项）：B1 `event_store` 0 行（读侧投影应走业务表——本
卡即此形态）；B2 outcome 三表 0 行（本卡以五源业务表为事实面，不依赖三表）；B3 decision_records
无 correlation（本卡 correlation 不链 decision_id）。

## 2. 方案形态：读模型，不是新表

**零 schema 变更**（卡面允许最小加法迁移，实际不需要）：账本 = 契约模块 + 服务层聚合查询。

```
backend/app/core/outcome_ledger.py        # 契约真源（stdlib-only + X-01 import）：词表/守卫/幂等键
backend/app/services/outcome_ledger_service.py  # 读模型服务：五流聚合 + keyset 分页 + 过滤/隔离
backend/tests/unit/test_outcome_ledger_contract.py    # 契约冻结 + 守卫（36 项）
backend/tests/services/test_outcome_ledger_service.py # 服务层守卫（27 项）
```

**五流不相交设计（去重的机制化）**：每个源的 standalone 谓词保证五条 outcome 流天然不相交，跨流
合并退化为纯排序拼接——keyset 分页精确、无重复计数、无跨流去重代码路径。唯一的同因合并规则落在
study_records 流的谓词上：`record_type='task_complete' AND task_id IS NOT NULL` 的行是完成管线
（TaskService.complete → GalaxyService.spark_node，GJ03 实证链）的**自动回声**，不进独立流，只作
为对应 task_completion outcome 的多源证据附着（`role=pipeline_echo`）。`task_complete` 且无
task_id 的行（live 有 1 行）保持独立 outcome。

**幂等**：读模型 + 确定性 `derive_outcome_id`（`outc_<sha256[:32]>`，D-01 `derive_event_id` 同款
派生风格）——同输入重复查询产完全相同条目与 id（测试钉住：
`test_same_cursor_returns_identical_page` / `test_requery_first_page_is_stable`）。无写入面即无写
侧幂等负担；语义边界与 D-01 同声明：覆盖「同一行重投递」，不覆盖「同一因果重执行产生新行」。
**已知限制（R1 C2-1 纠正）**：D-01 `CorrelationIds.__post_init__`（event_registry.py:477-487）
强制 correlation 值为 canonical UUID，`outc_<hash>` 直接填入 `correlation.outcome_id` 会被
`EventContractError` 拒收——与 D-01 自家 `evt_` 前缀同类限制；接线卡**不得**按「直接用 outc_*
id」字面执行，需随 evt_ 同款 follow-up 卡解决值域门（UUID 化包装或放宽校验）。

## 3. 五源映射表（work ①，冻结于 `FIVE_SOURCE_MAP`）

| 源（enum） | 物理表 | standalone 谓词 | truth 默认 | occurred_at | 关联键 |
|---|---|---|---|---|---|
| `task_completion` | tasks | status=COMPLETED AND 未删 | **逐条分级**（§4） | completed_at→created_at | task/plan/node |
| `study_record` | study_records | NOT(record_type='task_complete' AND task_id 非空) | actual | created_at | node |
| `focus_session` | focus_sessions | status=COMPLETED（INTERRUPTED 不是成果） | actual | end_time→created_at | task |
| `quiz_feedback` | expansion_feedback | meta_data->>'source' ∈ {quiz_passed, quiz_failed} | actual | created_at | node/task |
| `behavioral` | behavioral_outcomes | 全表（live 0 行，M-06 消费面） | actual | timestamp→created_at | intervention |

注：quiz 源 live 0 行且**词表在册但无生产者**（全库仅 `FeedbackType` 枚举与
`collect_implicit_feedback` 的存储函数，无任何发射方——R2 P3-2 纠正后表述）；生产者侧另有
meta/`trigger_task_id` 列双轨与 UUID 序列化坎，quiz 接线卡应以 `trigger_task_id` 列为关联真源
（R2 P3-1 登记）。behavioral 源为 M-06 Experience 的事实面预留，0 行时查询合法返回空。

## 4. Evidence 正规化与真相分级（work ②）

### 4.1 三映射表（冻结；X-01 `EVIDENCE_KINDS` 单一真源，import 期完整性断言）

| evidence_kind（X-01 词表） | 信任档位 | 可解析 ref scheme | 五源物化路径 | 升 actual 条件 |
|---|---|---|---|---|
| artifact / file | verifiable | `document://` | stored_files | 三重门全开（§4.3） |
| code | verifiable | **无**（v1 无解析器） | 无专表 | **机制性永不**（kind↔scheme 白名单，R2 P2-1） |
| quiz_result | verifiable | **无**（声明 ref 不算数） | quiz_feedback 源 | quiz 反馈行物化（按 meta.task_id 关联） |
| system_event | system | 无 | focus_session / study_record | 独立 focus 覆盖率规则（含时间方向，§4.3） |
| user_confirmation / self_report | user | 无 | 无（点击内断言） | 永不升 actual（档位值字面钉死，R2 P2-5） |

### 4.2 守卫：`classify_task_completion`（纯函数、确定性、无 LLM）

判定顺序（红测钉死，见 §5）：`completed_at` 缺失 → **unknown**；任一 verifiable kind 已验证 /
quiz 物化 → **actual**；独立 focus 覆盖分钟 ≥ `max(10, 0.5×actual_minutes)` → **actual**；其余一切
（无声明 / user 档 / 声明未解析 / 覆盖不足）→ **self_reported**。永不出 estimated/demo（那是消费
方对模型估计与 demo cohort 的标注语义）。

**分级哲学（本卡的核心判断，防「守卫失效」）**：
- **自动回声 ≠ 独立证据**：spark_node 在每次完成时无条件写 study_record——它的存在只证明「完成
  事件被服务器处理过」，不证明「工作真的发生」。若把它当独立证据，351/378 个带 actual_minutes
  的完成行全部自动变 actual，守卫形同虚设。因此 echo 证据 `role=pipeline_echo`，永不参与升级。
- **独立系统证据 = 与完成调用无自动因果、服务器记录的行为观察**：focus 计时（覆盖率门槛防「1
  分钟 focus 伪装 60 分钟完成」）、quiz 结果反馈、可解析 artifact/file ref。
- **声明不构成证明**：V3 行声明 artifact 但 ref 无法解析 → self_reported（不伪装 actual）；
  他人文件 ref 不构成我的证据（归属校验防跨用户注入升级，测试钉住）；**owner 内部同样成立**
  （R2 P2-1 返修）：无关旧文件、`task://` 指向自己的另一任务，都不构成有效证据——被指向行
  本身也只是用户主张，归属 ≠ 相关。
- TruthClass 词表 = **卡面四值（actual/self_reported/estimated/unknown）+ B-02 台账 demo 档的
  合成词表**（R2 P3-4 修正表述；B-02 inventory 另有 seed_namespace/pollution 等分类学，非单一
  权威五值真源），不造第二套。

### 4.3 证据解析三重门与 truth 时间语义（R2 P2-1/P2-2/P2-3 返修新增）

**document:// ref 的解析条件（`_resolve_declared_refs`，缺一不可）**：
1. kind↔scheme 白名单（`EVIDENCE_KIND_REF_SCHEMES` 冻结映射，import 期完整性断言）；
2. 文件归属本人 + 生命周期就绪：`status ∈ {uploaded, processed}` 且
   `lifecycle_status='active'` 且 `erased_at IS NULL` 且未软删
   （uploading/queued/processing/failed/archived/revoked/orphaned/erased 一律无效）；
3. **任务关联性**：`task_documents` 存在该文件到**被完成任务**的有效挂载
   （`TaskDocument.not_deleted_filter`）——「上传过任意文件」不能洗白之后的每次完成。

`task://`、`subtask://` 不再是可解析 scheme：它们指向的 Task/SubTask 行与声明本身同为用户
主张，「声明不构成证明」没有理由在 owner 内部失效。code kind 在出现代码解析器前对任何
scheme 恒不验证（机制保证而非君子协定）。

**truth_class 的时间语义（P2-3）**：账本是读模型、每次查询重算，truth 是**查询时点**的值：
- focus 证据只计入**完成时刻之前开始**的会话（`start_time < completed_at`；跨完成窗口重叠
  的会话仍计入）——完成后的会话不能追溯升级，同一 outcome_id 不会因「后来才计时」从
  self_reported 翻成 actual；
- 单调性：对 focus/quiz 物化证据，新证据只会升不会降（时间方向约束保证）；文件证据的
  生命周期撤销（revoked/erased/软删挂载）会使 actual **回落** self_reported——这是「证据
  失效即降级」的诚实记账语义，消费方（Aurora 事实面注入、WVPL 统计）不得把 truth 当不可逆
  快照缓存，应随查询重算或订阅失效事件；
- live 现状：`start_time > completed_at` 的完成任务 0 例（纯前瞻性守卫）。

**acceptance ① 的落点**：V3 行 completion_evidence **必需**（X-01 契约层已强制
`ActionPlanContract.validate` 拒绝空证据列表）；legacy 行**可选**（无证据完成合法，但分级为
self_reported）。无法证明时账本永不伪装 actual——即「完成 ≠ 点击」的机械保证。

## 5. 红绿证据（RED → GREEN）

- **RED（2026-09-19 实跑）**：契约测试先写先跑 → `ModuleNotFoundError: No module named
  'app.core.outcome_ledger'`（collection error，1 error）。
- **GREEN（返修后）**：`tests/unit/test_outcome_ledger_contract.py` **36 passed** +
  `tests/services/test_outcome_ledger_service.py` **56 passed**（共 92；首轮 63 → 返修 +29）。
- 守卫红测主断言：`test_no_evidence_complete_is_self_reported_not_actual`（无证据完成 →
  self_reported 而非 actual）；词表外 kind 脏数据不 crash 不升级；7 类声明×验证×quiz×focus 组合
  表驱动全覆盖；`test_classification_never_returns_estimated_or_demo_for_completions` 参数化扫描
  全组合钉死词表纪律。

### 5.1 同刻 tie 分页回归（R2 P1 返修新增，机制级）

旧 63 项测试的时间戳构造系统性避开同刻（`ts + timedelta(seconds=1)`）——「测试全绿但不变式
为假」的成因。返修新增同刻专项（时间戳**精确同值**构造）：

- `test_cross_stream_same_timestamp_walk_delivers_each_row_exactly_once`：五流各 2 行、两档
  时刻 5-way tie，limit=1 全量翻页 → 每条恰一次 + 全局序严格降序（页边界必然落在每个同刻
  条目上，覆盖全部「外流锚点 × 高前缀流」重复触发组合）；
- `test_tie_page_boundary_does_not_redeliver_task_stream` ×4 参数化：页边界锚点分别为
  study/quiz/focus/behavioral 流的同刻条目且同刻存在 task 行——下页不得重取 task（R2 复现链
  逐源钉死）；
- `test_tie_walk_matches_single_shot_full_query`：翻页全量 ≡ 一次性大页查询（不重不漏的等价
  性交叉验证；含游标不收敛断言，防死循环掩盖根因）；
- 证据来源/生命周期/时间方向/删除口径/冻结值回归见 §0 各行「证据」列。

### 迭代中发现的真 bug（live smoke 抓出，已修+回归钉住）

首版分页终止条件 `len(merged) > limit` 在**单流占优**时误判流尽：live PG 上 68 条 outcome 只翻到
50（merged==limit 恰好满页但 focus 流还有 16 行）。修复：各流取 `limit+1` 作「未取尽」探针，页
非空时游标恒取页末条目（keyset 不重不漏的不变式），空页深扫（truth 过滤整批滤掉）时用流原始续
传点。回归：`test_single_stream_dominant_walk_reaches_the_end`（30 条 limit=25 翻满）+
`test_exactly_full_page_has_no_cursor_when_exhausted`（恰好满页且流尽 → 不伪造下一页）。修后
live PG 全量翻页 **79/79 条、4 页、0 重复**。

## 6. 查询 API 与消费点（work ③）

服务层函数（按卡面不新增 HTTP 端点）：

```python
OutcomeLedgerService(db).query(          # → OutcomePage(items, next_cursor, source_counts)
    user_id=..., source=None,            # 五源过滤
    truth_class=None,                    # actual-only / self_reported-only（Aurora 事实面）
    since=None, until=None, limit=20,    # 时间窗 + keyset 分页（limit≤200）
    cursor=None, exclude_seed_cohort=False)  # B-02 F1 cohort 排除（fleet 级批扫用）
OutcomeLedgerService(db).count_by_source(user_id=..., ...)   # 各源计数（同 standalone 口径）
OutcomeLedgerService(db).truth_coverage(user_id=..., ...)    # {total, actual, self_reported, unknown, actual_ratio}
```

消费点文档（core 模块 docstring + 服务模块 docstring 双落点）：

| 消费方 | 接入方式 |
|---|---|
| **Aurora / Context Compiler（A-05）** | `query(truth_class=ACTUAL)` 取「已证实」近期 outcome 进决策上下文；self_reported 行不得当事实注入 |
| **Experience Memory（M-06）** | `query(source=BEHAVIORAL)` + `correlation.intervention_id`（behavioral_outcomes 事实面；表起行后即为策略学习输入） |
| **Galaxy（G-01/G-02）** | `query(source=STUDY_RECORD/FOCUS_SESSION)` + `correlation.node_id` 对齐掌握度链（GJ03：task→study_record→mastery_audit→outbox） |
| **North Star WVPL** | `truth_coverage` 的 actual 面（goal-linked outcome 判定不用完成点击面） |
| **G-01/G-02/A-05 后续卡** | 条目自带 `correlation{task_id, plan_id, node_id, intervention_id}`（canonical UUID），可直连 D-01 lineage 与 X-01 ref 体系 |

truth_class 过滤语义：非 task 源真相恒为 actual（服务器记录的行为观察），故 `!=actual` 过滤时非
task 流整流排除；task 流在 truth 过滤下按批推进（≤20 批 × limit，有界），页面不欠填、游标不跳页
（`test_truth_filter_pages_do_not_underfill_across_batches`：10 个 self_reported 之后翻到深处 1 个
actual）。

## 7. 验证记录（targeted，串行，sqlite 内存库 + dev PG 只读）

```
backend/tests/unit/test_outcome_ledger_contract.py              36 passed（RED→GREEN，返修+3 冻结值）
backend/tests/services/test_outcome_ledger_service.py           56 passed（返修+29：同刻/来源/生命周期/方向/删除/cohort）
回归：tests/unit/test_action_plan_contract.py                   29 passed（X-01 契约不受扰）
     tests/unit/test_action_plan_migration_sqlite.py             3 passed
     tests/test_action_plan_v3_integration.py                   25 passed
     tests/services/test_event_idempotency_isolation.py          9 passed（借 app/gen 后）
     tests/contract/test_event_registry_contract.py             31 passed + 1 failed（先在，见下）
lint：4 个交付文件 ruff + black(120) 全净（返修后复验）
变异实验（返修轮）：P1 退回裸 id 比较 / M1′ 档位值 / M6′ cohort 词 / P2-1′ kind 配对门 /
     P2-1b′ 关联性门 / P2-2′ 生命周期门 / P2-3′ 时间方向 / P2-6′ quiz 删除过滤 —— 9 组全红
     （针对性 -k 选择器），全部还原（md5 与返修后基线一致）
```

### 7.1 live PG 只读同刻验证（R2 P1 验收项，返修轮）

dev DB 只读 SELECT（docker exec sparkle_db psql，零写；修复语义以 SQL 复算）：

- **真实同刻对 1（跨流）**：用户 `72bfdfc4`（email）task `a7c89c79`（occurred=2026-04-18 09:00:00）
  与 **standalone** study_record `018d1b9c`（task_id NULL → 进 study 流）精确同刻。修复语义
  复算：该用户五流全局序 3 行、distinct 全局键 3、**每个锚点位置「严格在锚下方行数 =
  total − rn」违规 0**（任意页大小翻页每条恰一次）；新旧谓词在真数据上的直接对比：
  `task.id < 'study_record:018d…'` = **true**（旧实现会重取 task → 重复交付），
  `'task_completion:'||task.id < 'study_record:018d…'` = **false**（修复后正确排除）。
- **真实同刻对 2（流内 echo）**：用户 `771c64e7`（email）task `1fe56adb` 与 study_record
  `dbeb8435` 同刻，但后者 task_id 非空 = echo 行 → 不进独立流（`in_study_stream=false`），
  账本该时刻仅 1 行；同锚点不变式复算违规 0。旧实现在该对的隐患在 task 流**内部**续传锚点
  （同样已全局化修复）。
- 结论：live 2 对真实同刻数据经修复后分页各恰一次（计数级 + 机制级双重验证）。

**live PG 只读 smoke**（首轮，专用引擎 + `SET default_transaction_read_only=on` 硬保证，未写任何行）：
- 全部查询在真 PG 方言编译通过（UUID cast、JSONB `->>` 路径、coalesce、keyset、cohort 子查询）；
- focus 大户（seed cohort）79 条 outcome 全量翻页 4 页 0 重复，与 count_by_source 总和一致；
- **GJ03 链 A 用户实证**：task `e5f5a8b6`（D-01 REPORT §3 的样本任务）在账本中为
  truth=**self_reported**，其 echo study_record 以 `pipeline_echo` 证据附着（不重复计数）——20 分钟
  自报完成无独立证据，不伪装 actual；
- 同库 focus 大户的任务（12 个 focus 会话覆盖时长）分级为 actual——计时行为构成独立证据；
- `exclude_seed_cohort=True` 正确排除该 guest 用户（B-02 F1 词表生效）。

**已知先在失败（非本卡引入，已隔离证明）**：`test_truth_path_modules_never_read_client_telemetry
[app/state_aggregator/service.py]` ——移除本卡全部 4 个文件后单跑仍失败（wt5 基线即失败）：D-01
静态守卫扫描源码文本，而 `state_aggregator/service.py:530` 的**注释**提到 tracking_events（D-01
T1/T3 修复卡的文档留痕）。属 D-01 静态守卫已知盲区（其 REPORT §5 已声明「仅直接引用级」），移交
D-01 修复卡台账，本卡不修（不在 outcome-ledger 锁内）。

## 8. 改动清单

```
新增  backend/app/core/outcome_ledger.py                       # 契约：词表/三映射表/守卫/幂等键/条目类型
新增  backend/app/services/outcome_ledger_service.py           # 读模型：五流聚合/全局键 keyset/三重门解析/coverage
新增  backend/tests/unit/test_outcome_ledger_contract.py       # 36 项（词表+档位值+配对冻结/守卫红绿/幂等键/游标）
新增  backend/tests/services/test_outcome_ledger_service.py    # 56 项（五源/去重/同刻分页/来源约束/隔离/cohort）
产物  v3-output/D-02/REPORT.md + changes.patch + REVIEW_RECEIPT{,_2}.md
```

未做（显式）：

① 发 `outcome.recorded` 事件（D-01 词表 reserved，读模型不产事件；接线属后续写卡）。**已知
   限制（R1 C2-1 纠正原表述）**：届时 `correlation.outcome_id` **不能**直接填 `outc_*` id——
   `CorrelationIds` 强制 canonical UUID，需随 D-01 `evt_` 前缀同款 follow-up 卡解决值域门
   （UUID 化包装或放宽校验）后按卡面口径接线；

② `intervention_outcomes` / `intervention_strategy_outcomes` 两表入册（D-01 B2/B5 断点——先
   并轨再入册，避免 intervention_id 二义）；

③ **goal 面不入册（P2-4/C2-2 显式决策记录）**：卡面 Work ① 明列 goal evidence，本卡判定
   **排除**，理由：`goals` 表是派生聚合面（progress/mastery 自 task/focus 成果滚动，live 4
   行），goal 完成无独立生产者（`status='completed'` 为聚合状态），入册即与 task/focus 流
   重复计数、违反验收②「不重复计数」；correlation 亦无 goal_id 列。**解除条件**：未来出现
   一等的 goal-completion 生产者（独立事件/表），按第六源 bump
   `OUTCOME_LEDGER_SCHEMA_VERSION` 并过两位 reviewer；WVPL goal-linked 判定在那天之前用
   actual 面 task/focus outcome + plan.goal_id 由消费方自组合；

④ estimated/demo 分级的生产者（保留给 predictive/simulation 消费方标注）；

⑤ behavioral/quiz 源的物化写入路径（M-06/quiz 流程卡范围；quiz 生产者缺位 + meta/列双轨见
   §3 注）。

## 9. 风险与限制（如实）

1. **V3 证据面尚无真实数据**（`action_schema_version` 全 NULL）：artifact/file ref 解析与声明分级
   路径由 sqlite 测试覆盖，live 只有 legacy 面（focus 覆盖率/quiz/echo 规则已在 live 验证）。
2. **`code` kind v1 不可解析**（无专表）——**机制性**永不单独升 actual（kind↔scheme 白名单，
   R2 P2-1 后不再依赖君子协定）；诚实降级优于伪造。
3. **truth_coverage 的分类输入是逐任务计算**（focus 聚合 + quiz 存在性 + ref 解析），limit 上限
   2000；超窗静默截断（docstring 已明示，v2 应改分组聚合 SQL）；`tasks.completed_at` 无索引，
   超大用户量时需补索引（dev 规模无压力，读路径无锁风险）。
4. truth 过滤分页的批次推进上限 20 批——病态分布（前 20×limit 个完成全被滤掉）时空页+游标继续，
   极端下可能需多次翻页；有界工作换正确性，已在 docstring 声明。
5. 五源流不相交依赖 standalone 谓词的正确性——若未来新写入方给 study_records 造出新的「完成回
   声」record_type，需同步 bump `ECHO_STUDY_RECORD_TYPES`（冻结测试守护词表，改动需过两位
   reviewer）。
6. quiz/behavioral 源 0 行阶段，查询返回空是**真实状态**而非缺陷；M-06 起行后无需改账本。
7. **truth 是查询时点重算值**（§4.3）：focus/quiz 证据单调不降；文件证据生命周期撤销可使 actual
   回落 self_reported——消费方不得把 truth 当不可逆快照缓存。
8. **消费点零接线**（R2 P3-5 在案）：全仓无 import OutcomeLedgerService 的模块——「跨模块被查询」
   目前只在库层成立；A-05/M-06/G-01 卡需登记强制接线项，防读模型长期无消费者而语义漂移
   （P1 正是无消费者不变式腐烂的实例）。

## 10. 收工清理

删除：借用自主仓的 `backend/app/gen/` 符号链接（只读借入供回归 import，验证完即删，本轮同法）、
`/tmp/d02-rw-*` 与 `/tmp/d02-mut`（基线克隆/变异备份）、`backend/.pytest_cache`；
`PYTHONDONTWRITEBYTECODE=1` 全程开启（无新增 __pycache__ 残留需清）。
无进程/模拟器/浏览器；dev DB 全程只读（docker exec psql SELECT，零写）；未 commit/push、
未 stash/reset/clean/切分支（4 个交付文件全程 untracked）；工作树最终态 = 4 个新增未跟踪
文件 + 本目录产物（REPORT/patch/两份 REVIEW_RECEIPT）。
