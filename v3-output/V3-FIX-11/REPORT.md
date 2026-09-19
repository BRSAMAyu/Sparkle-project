# REPORT · V3-FIX-11（P0，台账最高优先级）：根治 Telemetry 渗入业务真值的三条链

- 执行: Apex Worker（wt2 @ 7ef808ee，M-01 ACCEPT 基线）
- 日期: 2026-09-19
- 约束遵守: 主仓与 sparkle_db 全程只读（DB 仅 SELECT）；无模拟器/浏览器/flutter/全库测试；pytest 定向串行；无 git commit/push；无新增 Alembic 迁移；venv 与 `app/gen`（主仓只读拷入供 import 链，wt4 先例）均建于 worktree 内、收工即删。

---

## 0. 结论速览

| 链 | 修复机制 | 红测证据 | 绿证据 | dev DB 推演 |
|---|---|---|---|---|
| T1（P1 请求即武装） | estimator 内建 per-user 防抖 + 遥测负载项硬上限 0.3 | 4 failed（50 噪声事件→load=1.0；7 伪造错题→1.0；连续 update_state 每次铸快照） | 21/21 新测全绿 | 快照表仍 0 行（休眠）；首个真实批次激活时 burst 每 5 分钟至多 1 次重算、load ≤0.3、interruptibility ≥0.7 |
| T3（P1 二跳 sentiment） | 拦截集单一常量真源（补齐 frustrated/overwhelmed）+ aggregator 过滤 behavior 源 sentiment | 3 failed（frustrated 明文落库；frustrated/overwhelmed 触发 emotional_block；遥测 happy 噪声可淹没真实 chat 信号） | 同上 | 24h 窗口内 166 guest 的 block 前后均 0，且窗口内遥测 sentiment 全部出通道（回退 server 侧 chat 分类） |
| T2（P2 seed 池污） | replanner 0.7 门 pattern 池按 registration_source 排除 guest/seed（V3-FIX-01 口径） | 1 failed（语句无 REGISTRATION_SOURCE 谓词） | 同上 | 池 172 → 5（167 条 seed 计划谬误 0.84 出门） |
| 守卫升级 | 两层静态扫描（直接引用零容忍 + 二跳 waiver 门），目录级覆盖 state_aggregator/ 与 services/evidence/，注释感知（字符串字面量仍扫，防动态 SQL 绕过） | 二跳测试红（3 文件引用遥测衍生表无 waiver） | 4/4 绿 + 双向探针实证能抓新违规 | — |

新增测试 21 个 + 既有定向回归 54 passed / 2 skipped（唯一失败 `test_c03_adaptive_replanner_wiring` 为**基线既有失败**，stash 验证与本卡无关）。

## 1. T1：请求即武装（estimator 同步触发 + 事件量饱和）

**根因**（D-01 R2 F4 实锤复核属实）：`api/v1/events.py:65-70` 每次遥测 POST 同步调 `estimator.update_state`；`cognitive_stream_worker.py:148-149` 每事件也调；`state_estimator_service.py` 的 `cognitive_load = min(1, wrong×0.15 + total×0.02)` —— 两项全由客户端遥测构成，纯量项 50 事件即饱和。

**修复**（`backend/app/services/state_estimator_service.py`，机制单一收口在 service 层，同时覆盖两个触发方）：
1. **防抖**：`update_state(user_id, tz, *, force=False)` 先查最新快照龄，`< STATE_ESTIMATOR_MIN_INTERVAL_SECONDS`（300s，常量真源在 `app/core/telemetry_boundary.py`）直接返回既有快照、不写库，`STATE_ESTIMATOR_RUNS{result="debounced"}` 可观测。单一遥测请求/事件无法再同步刷新用户状态；burst 至多每 5 分钟重算一次。`force=True` 留给未来服务端调度器。
2. **硬上限**：`cognitive_load = min(min(1, wrong×0.15+total×0.02), TELEMETRY_DERIVED_LOAD_CAP=0.3)`，代码内显式标注两项均遥测派生、方向保留只封顶；interruptibility 因此下界 0.7（focus 模式 0.5）。event_registry 域（wt4 D-01 未合入本分支，不可依赖）的服务端真值信号未来可在上限之上叠加，已注释说明。

**为何不改 events.py 本身**：防抖放 service 层是单一收口——只改端点会留下 worker 触发方仍每事件武装；异步派发（BackgroundTasks/create_task）与请求作用域 session 生命周期耦合且有竞态，弃用（卡允许"异步/**限频**"二选一，选限频，确定性可测）。

**红→绿**：`tests/unit/test_state_estimator_telemetry_bounds.py` 7 用例——修前 4 红（50×screen_view→1.0、7×quiz_wrong→1.0、3 错题 0.47>0.3、防抖缺失），修后全绿；合法挣扎信号（3 错题）方向保留（0→0.3 有界抬升）。

## 2. T3：二跳 sentiment 渗入 emotion_hint

**根因**（F3 复核属实）：worker 拦截集 `{anxious,depressed,burnout}` ⊅ aggregator emotional_block 触发集 `{anxious,frustrated,overwhelmed}`；`state_aggregator/service.py:524` 读 `cognitive_fragments.sentiment` 对 behavior 源（遥测流 worker 写入、seed 直写）全量计入。

**修复**：
1. **单一常量真源** `app/core/telemetry_boundary.py`：`EMOTIONAL_BLOCK_SENTIMENTS = {anxious, frustrated, overwhelmed}`；`TELEMETRY_SENSITIVE_SENTIMENTS = {anxious,depressed,burnout} ∪ 前者`。worker `SENSITIVE_SENTIMENTS` 改为引用；aggregator emotional_block 判定改为引用。防再漂移由不变量测试钉死（`EMOTIONAL_BLOCK ⊆ SENSITIVE` 且 worker 类属性 == 常量）。
2. **aggregator 侧过滤（选定"过滤"而非降权，确定性可测）**：sentiment 查询追加 `source_type NOT IN TELEMETRY_DERIVED_FRAGMENT_SOURCE_TYPES({'behavior'})`。capsule（用户自述闪念）与 interceptor 通道保留——用户自报情绪是合法信号（测试钉住：capsule frustrated 仍可触发 block）；server 侧 chat 关键词分类（用户原话）保留且不再被遥测噪声淹没（tie-break 红测实证修前遥测 happy 可压掉真实 frustrated）。
3. 生产侧拦截后 frustrated/overwhelmed/anxious 等全部进加密 sensitive 通道（`sensitive_tags_encrypted`），明文列对遥测关闭。

**红→绿**：`test_cognitive_stream_sentiment_intercept.py` 5 用例 + `test_state_aggregator_emotion_telemetry_filter.py` 4 用例（真实 sqlite 内存库）。修前 3+3 红。

## 3. T2：seed 群体占据 replanner 高置信池

**根因**（F5 复核属实）：`adaptive_replanner.CognitivePatternTrigger.build_adjustments` 0.7 门无 cohort 过滤；dev 库 166 条 seed「计划谬误」0.84（全部 `registration_source='guest'`）在门内。

**修复**：pattern 池查询 JOIN users 追加 `registration_source NOT IN EXCLUDED_COHORT_REGISTRATION_SOURCES(('guest','seed'))`——与 V3-FIX-01 全局榜同口径、同常量真源（telemetry_boundary）。既有谓词（confidence 门、archived 过滤）保留（回归测试钉住）。

**代码事实澄清**（receipt 建议的"fragments→patterns source 门"）：`BehaviorPatternService` 全部模式生产（Planning Optimism/Focus Decay/Blindspot）只读 Task/FocusSession/ErrorRecord，**从不读 CognitiveFragment**——fragments→patterns 在代码上不存在生产路径（仅 seed 的 evidence_ids 展示性关联）。因此源头门无可实施对象，本卡按 provenance 维度在读取面（决策门）落位，即 receipt 所列两选项中的"seed 模式排除"。

**红→绿**：`tests/services/test_adaptive_replanner_seed_cohort_filter.py` 2 用例（statement-capture + 编译断言，V3-FIX-01 同款模式）。修前 1 红。

## 4. 守卫升级（D-01 七模块扫描 → 二跳可见）

`tests/contract/test_telemetry_boundary_contract.py`，4 用例，选型**静态扫描 + waiver 门**（运行时断言只能证明单次读有界，看不见下一次渗透；源码扫描便宜、CI 可跑、报错信息可指导修复）：
- **Tier 1（直接引用，零容忍）**：truth-path 模块（`state_aggregator/` 与 `services/evidence/` **目录级**（落实 F12 静态清单批评）+ `core/context_pack.py` + `services/galaxy/stats_service.py`）不得出现 `TrackingEvent/tracking_events`。
- **Tier 2（二跳，waiver 门）**：上述集合 + 三个决策面消费方（nightly_review / adaptive_replanner / personalization/runtime_context_service）引用遥测衍生表（cognitive_fragments / user_state_snapshots / behavior_patterns 及模型名）必须同时满足：源文件带 `TELEMETRY_DERIVED_READ_WAIVER` 标记注释（含 bound 描述）**且**登记在测试内 `WAIVED_MODULES`（4 项，各自写明 filter/cap/debounce/gate bound）。新无 waiver 引用→红（附修复指引）；waiver 无引用→红（防死 waiver）；reason 无具名 bound→红。
- **注释感知**：tokenize 剥离 COMMENT 但**保留字符串字面量**——waiver 注释可以提及表名（本卡 4 处 waiver 均如此），而 `text("select ... from tracking_events")` 动态 SQL 仍可检出（F12 绕过类 2）。
- **探针双向实证**：在 state_aggregator/ 放临时文件引用 tracking_events → Tier1 抓到；在 services/evidence/ 放临时文件 select CognitiveFragment 无 waiver → Tier2 抓到；删除后全绿。

**D-01 合并时的对接说明**：wt4 的 `test_event_registry_contract.py` 七模块静态清单守卫未合入本分支（wt2 无 event_registry.py）；本守卫是其超集（同 Tier1 语义 + 目录级 + Tier2），D-01 合入后两守卫可并存，或由主会话将 D-01 的 TRUTH_PATH_MODULES 指向本文件（建议后者，避免双清单漂移）。

## 5. 定向回归（全部通过）

| 命令（均在 backend/ 下，`SECRET_KEY`/`OPENAI_API_KEY` 内联注入） | 结果 |
|---|---|
| 新增 5 文件（21 用例） | 21 passed |
| `test_state_estimator_service.py` `test_state_aggregator_service.py` `test_adaptive_replanner_{cognitive_trigger,evolution,stage34}.py` `test_evidence_resolve.py` | 29 passed, 1 pre-existing fail（见下） |
| `test_event_pipeline_integration.py` `test_sufficiency_judge_service.py` `test_decision_context_contract.py` | 18 passed, 2 skipped |
| `test_cognitive_service_regression.py` `test_structured_cognitive_adjustments.py` `test_r2p306_noop_throttle.py` `test_orchestrator_evolution_context.py` | 25 passed |
| `test_aggregator_schema_v1_5.py` `test_aggregator_schema_v1_12.py` `test_memory_jobs.py` | 9 passed |
| `test_client_telemetry_api.py` `test_idempotency_middleware.py` | 4 passed |
| 终态合并复跑（新 21 + 关键回归） | **54 passed, 2 skipped** |

既有失败隔离：`test_c03_adaptive_replanner_wiring.py::test_task_stuck_consumer_routes_to_adaptive_replanner_health_eval` 在**未改动基线**（git stash 后）同样失败（SimpleNamespace mock 无 scalars，task_stuck_signal_service 路径），与本卡无关，未触碰。

格式：新增文件 black(120) + ruff 全过；既有文件仅按 ruff isort 归位了一处 import（service.py），未重排任何未触碰代码（仓内基线本非 black-clean）。

## 6. dev DB 只读推演（sparkle 库，仅 SELECT，零写入）

1. **T2 池推演**：`behavior_patterns ⋈ users`，0.7 门 + 未归档：修前池 **172** → 追加 `registration_source NOT IN ('guest','seed')` 后 **5**（167 条 seed 模式出决策面，余 5 为真实 email 用户模式）。
2. **T3 窗口精确推演**（以库内最新 fragment 时间为参照 now，复刻 24h 窗口 + dominant 语义）：166 guest 窗口内仅有 behavior-positive 行 → 修前 block=0；修后窗口内遥测 sentiment 全部出通道（166/166 post_no_fragment_signal）→ emotion_hint 完全回退 server 侧 chat 分类。（无窗口粗算会误报"capsule anxious 反转 dominant"——seed capsule 写于 now-3d2h，本就在窗外；真实用户旧闪念同理老化出局。）
3. **T1 现状**：`user_state_snapshots` 仍 0 行（与 D-01 一致，休眠）；24h 窗口 tracking_events 仅 1 行测试污染。首个真实生产批次激活时：单批 50 事件 load ≤0.3、连续请求 5 分钟内至多 1 次重算——由单测钉死，无需写库验证。

## 7. 波及面与残留（只排查，未修改）

- **R1（低）**：`strain_index = min(1, wrong_ratio+0.2)` 未封顶——伪造全错比例可到 1.0。当前消费面：快照存档 + evidence resolve 展示 + nightly review 仅引用 id，**无决策消费方**，且 cognitive_load/interruptibility（真决策面）已封顶。建议后续卡随 strain 首个决策消费方出现时同法封顶。
- **R2（低，家族登记）**：persona_service / orchestration/context_builder / progress_narrative_service 也读 BehaviorPattern（persona 无 confidence 门；context_builder 经 `get_user_patterns(min_confidence=0.6)` 注入 LLM 提示上下文；progress_narrative 0.7 门）——全部 per-user 作用域，seed 模式只影响 seed 用户自己的展示/叙事，无跨用户污染；与 V3-FIX-07 同族，若要求 demo 一致性可开后续卡统一 cohort 过滤。
- **R3（信息）**：`evidence_health_service` / events.py `/evidence/resolve` 读 UserStateSnapshot 属**审计/解析面**（D-01 亦未列为 truth 模块），未纳入守卫扫描集；若后续其产出进入决策面，Tier2 扫描集需扩。
- **R4（信息）**：`cognitive_fragments.source_type='interceptor'` 当前无 live 写方（仅 seed 写过 neutral 166 行）——通道保留为服务器侧拦截预留。
- **R5（对接）**：D-01（wt4）合入时见 §4 对接说明；`EXCLUDED_COHORT_REGISTRATION_SOURCES` 未来若被第三处消费，可从 replanner/本模块提取为全局 cohort policy（当前两处引用不值得新抽象）。

## 8. 交付物与清理

- 代码：6 改 + 6 新（见 changes.patch，1097 行）——`app/core/telemetry_boundary.py`（常量真源）、`state_estimator_service.py`、`cognitive_stream_worker.py`、`state_aggregator/service.py`、`adaptive_replanner.py`、nightly_review/runtime_context（waiver 注释）、5 个测试文件。
- `v3-output/V3-FIX-11/REPORT.md` + `changes.patch`；未 commit/push。
- 清理：`backend/.venv`、`backend/app/gen`（主仓只读拷入）、`/tmp/req_noltzo.txt`、探针临时文件（已随验随删）、`__pycache__`（PYTHONDONTWRITEBYTECODE=1 全程）；无进程/模拟器/浏览器；dev DB 零写入。
