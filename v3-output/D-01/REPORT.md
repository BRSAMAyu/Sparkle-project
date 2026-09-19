# D-01 REPORT · 统一 Event / Evidence Lineage Contract

- **Task**: D-01（stream DATA, gate V3-2, risk high, reviewers=2, locks: event-contract）
- **Status**: READY_FOR_REVIEW（未 commit/push；改动以 `changes.patch` 交付）
- **Base SHA**: `7251128e071b309ce7f893ddac9db06ce1680b77`（worktree wt4）
- **工作树最终态**: 3 个修改 + 3 个新增代码/测试文件 + 2 个产物文档

## 1. 问题定义与方案形态

事件域现状（B-06 §1.4 已勘 + 本次 dev DB 实测复核）：

| 事实 | 数据 |
|---|---|
| `event_outbox`（外发权威） | 106 行 = 101 × `galaxy.node.mastery_updated` + 5 × probe 残留（`run.*` / `task.status_changed`） |
| `event_store`（CQRS 追加） | **0 行**——SQLC 写入面在仓、无活跃调用方 |
| `decision_records` | 2870 行（push 2677 + ai 193），无 correlation ids |
| `intervention_requests` / `passive_signals` | 552 / 226（routing_outcome.v1 决策-信号对已互链） |
| `tracking_events`（telemetry） | 1 行 |
| `execution_audit_log` / `intervention_outcomes` / `behavioral_outcomes` / `user_state_snapshots` / `memory_corrections` | 全 0 |

三个缺口：①事件名是自由字符串（live 里 6 种事件名、仓内 3 个 Python 写入方各写各的 metadata）；②outbox 事件不带统一 correlation（galaxy 事件 payload 里没有引发它的 task_id，GJ 链在 outbox 环节断）；③telemetry 与真值边界没有机械守卫。

**方案**：不新建真源、不改表结构（零 Alembic）。新增单一权威模块 `backend/app/core/event_registry.py`（stdlib-only，C-01 同款风格）承载封闭事件名词表 + shared fields 契约；三个 Python outbox 写入方（galaxy_service / galaxy/stats_service / learning_asset_service）的 metadata 构造最小接线过 `build_event_metadata()`；契约 + 幂等 + 隔离 + telemetry 边界全部用测试钉死。

## 2. 契约要点（详见同目录 EVENT_REGISTRY.md）

- **词表**：33 个事件名封闭入册（live 27 / reserved 11 中已产 0 / observed_unregistered 5），按 flywheel 五阶段（interaction/decision/execution/outcome/state_update）编目；sha256 冻结在测试字面量里，改词表必须显式 bump。
- **shared fields**（落 `event_outbox.metadata` jsonb，零 schema 变更）：`event_id`（幂等键，`derive_event_id()` 从因果输入确定性派生 `evt_<sha256[:32]>`）/ `user_id`（隔离键，必填）/ `schema_version=event.v1` / `source`（封闭 enum，`client_telemetry`/`probe` 永远非真值）/ `service` / `occurred_at`（naive-UTC 强制）/ `correlation{intervention_id, action_id, run_id, outcome_id, task_id, session_id, message_id, decision_id, plan_id, node_id}`（全 canonical UUID）。
- **向后兼容**：`read_event_metadata()` 同时解析 v3 envelope 与 legacy `{"service":...}` 行（106 行存量全部可读，`is_v3_envelope=False` 降级识别）；Go 侧 `EventMetadata` unmarshal 对多余字段天然容忍（已核对 `types.go`）。
- **与 C-01 对齐**：correlation ids 即 `memory://`/`plan://` ref URI 指向的记录 id；`event.v1` 与 `decision_context.v1` 同版本语义。

## 3. GJ03 trace 实证（acceptance ①）——dev DB 只读 SQL

GJ03 = Existing user → Today → action → outcome。**链 A（action→outcome→state update）为完整闭环，全部真实行，无 mock**：

用户 `fc62a43c-82f8-43a5-b520-abe8fbd2ed15`，2026-09-19 02:00:58（UTC）：

| # | 环节 | 表/行 | 关键 ID 与时间戳 |
|---|---|---|---|
| 1 | UI action（任务完成） | `tasks` | task `e5f5a8b6-3ab4-4856-ba89-07ebb75c9bc8`「完成一项稳定任务」status=COMPLETED, completed_at=02:00:58.885, actual_minutes=20 |
| 2 | 执行副作用（学习记录） | `study_records` | `bd26a7a7-b20f-425b-a415-614502c4010c`，**task_id=e5f5a8b6**（因果键），record_type=task_complete, mastery_delta≈4.0，02:00:58.959 |
| 3 | 审计账 | `mastery_audit_log` | id=106, old=0→new=3, reason=task_complete, **request_id=e5f5a8b6**, 02:00:58.959 |
| 4 | 外发事件（权威） | `event_outbox` | `f3f5958c-a50c-4900-a08b-eb1d0442b0b6`，`galaxy.node.mastery_updated`，seq=1，payload{user_id, node_id=5e103872…, mastery=3}，02:00:58.960→published 02:00:59.052 |
| 5 | **state update** | `user_node_status` | (user fc62a43c × node 5e103872)：mastery 0→3.999…，study_count=1，total_study_minutes=20，last_study_at=02:00:58.959 |

ID 链完整度：task→study_record→audit_log 靠 `task_id` 全通；**断点在 #4**——存量 outbox payload/metadata 不带 task_id（这正是本卡接线修复的点，见 §5 改动；接线后新事件在 payload 与 metadata.correlation 双带 task_id，测试钉死）。

**链 B（interaction→decision）**：chat_session `e21ed924-9827-48e5-81d8-28fe2a36063c`（user 926aeac0，5 条消息，04:52:12 建）→ 双核路由决策 trace `dcr_d3142162ba4e41468c77d72c9703991f` + request_id `run_1789793561895526_0` → `intervention_requests` `97d5fba6-b2b5-4cd1-8513-e4463bfad4de`（schema=routing_outcome.v1, 04:52:43.017）↔ `passive_signals` 同 intervention_id 同秒（04:52:43.020，context 带 request_id/session_id/trace，`evaluation_due_at`+48h，`outcome_recorded=false`）。**断点在 outcome 腿**：`behavioral_outcomes`=0（评估期未到或 evaluator 未跑）。

### 断点清单（发现，未修——多为后续卡范围）

| # | 断点 | 证据 | 影响 |
|---|---|---|---|
| B1 | `event_store` 0 行：B-06 事件域成员无活跃写入方 | `SELECT count(*) FROM event_store` → 0 | "CQRS 追加存储"名存实亡；V3 读侧投影若指望它会扑空，应改投影 `event_outbox`+业务表 |
| B2 | `intervention_outcomes` / `execution_audit_log` 全 0 | 同上 | 干预→outcome 闭环在存储面无真值；链 B 的 outcome 腿因此必然断 |
| B3 | `decision_records` 无 correlation ids | 表结构只有 user_id/module/action/outcome(text) | 决策账无法机械回链 chat/run/intervention |
| B4 | outbox 存量 `run.*`/`task.status_changed` 5 行为 **probe 残留且生产者代码不在仓内**（`grep -r "run.awaiting_user"` 全仓+git 历史为空；plan_id=`plan-rt02-pg` 指向 rt02 探针；`sparkle_rt02_probe` 库有 89 行同构 outbox） | event_outbox 2026-09-17 15:19 五连发；其 payload 引用的 task `07269751…` 在 `tasks` 表不存在 | 探针数据写进了 live dev 库的权威外发表；且"task.status_changed 事件已发但任务行不存在"是效应未物化的反例。已收编入册为 observed_unregistered，建议主会话清理（红线外、<1G，可删） |
| B5 | `intervention_requests`（Phase 0，552 行）与 `intervention_records`（card 协议，1 行）双轨，仅靠 `diagnosis_payload.legacy_intervention_request_id` 弱链 | intervention_records 全表 1 行 | V3 干预事件（intervention.*）落地前必须先并轨，否则 correlation.intervention_id 二义 |
| B6 | 遗留 `gateway/internal/worker/outbox_relay.go` 仍指向已消失的 `outbox_events` 表（int64 id + status 列） | 代码 vs live schema（`event_outbox` uuid + published_at） | 死代码（D-OUTBOX 已裁决），本轮不删不改，登记待清 |

## 4. 幂等 + 隔离守卫（acceptance ②，红→绿证据）

- **RED**（2026-09-19 实跑记录）：移除 `app/core/event_registry.py` 后收集即失败——`ModuleNotFoundError: No module named 'app.core.event_registry'`，2 个测试文件 2 errors。
- **GREEN**：`tests/contract/test_event_registry_contract.py`（25 项）+ `tests/services/test_event_idempotency_isolation.py`（9 项）全绿。
- 幂等钉住的机制：
  - telemetry：同 event_id 重放（跨请求/同批/跨用户）→ 物理行恒为 1、下游 publish 恰好 1 次（RecordingBus 断言）；
  - outbox：`derive_event_id()` 同输入同 id、异输入异 id（seq/correlation 敏感性逐项断言）——**幂等语义仅覆盖"同一行重投递"**，不覆盖"同一因果重执行"（重执行烧新 seq → 新 id，R2 F9）；该键当前**零消费者**（唯一活跃消费者 Go publisher 按 Redis messageID 去重，且 Go `IsProcessed` 的 `uuid.Parse` 拒收 `evt_` 前缀——消费侧接线属后续卡，见 §8 与 registry docstring，R2 F1）；写入方落库 metadata 携带该键；
  - 词表：未注册名在 `require/classify/derive/build` 四个入口全部被拒。
- 隔离钉住的机制：`tracking_events.event_id` 全局唯一 → 用户 B 重放 A 的 event_id 记为 deduped 且不产生 B 名下行；`get_event(user, id)` 用户域过滤（B 拿 A 的 id 查询 → None）；state_estimator `_fetch_recent_events` 只见本 user 事件（3+2 事件注入后 A 的快照 derived_event_ids==3）。跨用户关联查询天然隔离：所有 correlation 消费必须先落 `user_id` 域（envelope 强制 user_id 必填 + 写入方测试断言）。

## 5. telemetry 边界（work ②，acceptance 支撑）——含 R2 返修更正

**契约面**：`source ∈ {client_telemetry, probe}` ⇒ `is_business_truth_eligible()==False`（代码强制，非注释约定）。

**渗透链清单**（R2 深审后重写：初版"V3 真值应只认 state_aggregator（实测不读 telemetry）"的断言**错误**——聚合器不直接读 tracking_events 表，但经派生表二跳读入遥测衍生数据。三链全部"发现不修"，移交修复卡）：

| # | 渗透链 | 机制与实测证据 | 级别 |
|---|---|---|---|
| **T1** | telemetry → `state_estimator_service` → `user_state_snapshots` → `nightly_review_service._latest_state`（API + scheduler_service 双入口）/ `personalization/runtime_context_service` / `plan_context` / `evidence_health_service` | **请求即武装，非"休眠待调度"**（R2 F4 更正）：`api/v1/events.py:65-70` 在**每次遥测 POST 上同步调用** `estimator.update_state`（cognitive_stream_worker 每事件亦调 :149）。污染阈值是结构性的：`cognitive_load = min(1, wrong×0.15 + total×0.02)`——纯事件量项在 **~50 事件/24h 即饱和到 1.0**，语义无关噪音（心跳/screen_view）即可把 interruptibility 压到 0，第一条真实生产遥测批次即激活。快照表 0 行只因 dev 仅有的 1 行遥测是测试直插（source='test'，绕过 API） | **P1（修复卡最高）** |
| **T2** | telemetry/seed → `cognitive_fragments` → `behavior_patterns` → `orchestration/adaptive_replanner`（MIN_CONFIDENCE=0.7 门）与 context_pack `include_behavior_patterns` | 门真实存在、遥测量小过不了门（R2 F5 定级 P2，降自初版）；**但池已污**：dev 库 behavior_patterns 338 行中 172 行 confidence≥0.7，其中 166 行为 guest_seed 注入的"计划谬误"模式（guest_seed_service.py:2215，confidence=0.84 在门内）——replanner 的"高置信行为模式"池当下即被 seed 群体占据。修复需同时覆盖 fragments→patterns 的 source 门 + seed 模式排除（confidence 或 provenance 维度） | **P2** |
| **T3** | telemetry/seed → `cognitive_stream_worker._create_fragment` → `cognitive_fragments.sentiment` → **`state_aggregator/service.py:524-533`（UserStateV1 权威世界状态）** `emotion_hint`/`emotional_block` | **R2 F3 新发现，本 REPORT 初版漏报**：聚合器读 24h 窗口内 fragment.sentiment（limit 20）算情绪分布；worker 的 SENSITIVE_SENTIMENTS 只拦 `{anxious, depressed, burnout}`（:86），而聚合器 emotional_block 触发集是 `{anxious, frustrated, overwhelmed}`——**frustrated/overwhelmed 不在拦截集**，客户端遥测 sentiment 可直达权威状态聚合器。live 佐证：cognitive_fragments 877 行中 830 行带 sentiment（neutral 332 / positive 166 / focused 166 / **anxious 166**——anxious 为 seed 注入，绕过 worker 的 nullify 逻辑，证明该通道已被恰是 emotional_block 触发值的 sentiment 大规模填充，seed 用户群的权威 emotion_hint 已被污染） | **P1（不低于 T1）** |

其余读路径（观察/估计面，可接受）：`idiographic_association_service`（Redis 流→个性关联分析，洞察面）；`predictive_service:1819`（engagement 预测，payload 明示 prediction_tier/fallback_used）；`evidence_health_service`（按 event_id+user_id 核对 telemetry 完整性，用户域过滤正确）。

**机械守卫与其盲区（诚实声明）**：`test_truth_path_modules_never_read_client_telemetry`（参数化 7 模块：state_aggregator service/schema、context_pack、evidence fusion 三件套、galaxy stats）——**仅直接引用级**：模块源码出现 `TrackingEvent`/`tracking_events` 即红；**派生表二跳（上表 T1/T2/T3 全部走二跳）对源码扫描恒绿不可见**，且清单是静态的（新文件需显式入册）。二跳链以发现清单移交修复卡，不以本守卫背书。守卫测试 docstring 已明示此范围（R2 F12）。另钉：telemetry 摄入服务（event_service）不得写 `event_outbox`（域隔离）。

## 6. 测试与验证记录（targeted，串行，sqlite 内存库，未触 dev DB）

```
tests/contract/test_event_registry_contract.py      32 passed（初版 25 + R2 返修新增 7：防御解析 6 + 豁免冻结 1）
tests/services/test_event_idempotency_isolation.py   9 passed
tests/unit/test_learning_assets.py                  35 passed（1 项 mock 补 user_id，见下）
tests/api/test_task_complete_galaxy_outbox.py        4 passed（galaxy outbox 回归）
tests/services/galaxy/                              29 passed（stats_service 回归）
合计 109 passed（另：contract/test_state_manager_contract 4 passed；integration/test_event_pipeline 2 skipped[需 SPARKLE_INTEGRATION]）
lint: 新文件 ruff+black(120) 全净（含返修改动）；4 个修改文件的存量 ruff/black 漂移经 baseline 对比确认先在（F841 best_candidate、I001 等均非本次引入），未扩散 reformat
```

- 运行环境：worktree 无 venv，只读借用 `sparkle-cosmos/backend/.venv`（Python 3.11.15，`PYTHONDONTWRITEBYTECODE=1`）；`backend/app/gen/`（gitignore 生成物）从主仓只读拷入供 galaxy_service 导入链，收工删除；SECRET_KEY 以环境变量注入（未建 .env，遵守磁盘纪律）。
- 对既有测试的唯一改动：`test_learning_assets.py` 的 expiry mock 原本缺 `user_id`（生产模型 NOT NULL FK）——补 `mock_asset.user_id = uuid4()` 使其满足契约，属补全 mock 而非放松守卫。

## 7. 改动清单

```
新增  backend/app/core/event_registry.py                       # 词表+shared fields+幂等键+telemetry 边界（单一权威；含 R2 返修：docstring 更正/豁免常量/防御解析）
新增  backend/tests/contract/test_event_registry_contract.py   # 词表冻结/契约规则/telemetry 边界守卫（32 项，含 R2 新增 7 项）
新增  backend/tests/services/test_event_idempotency_isolation.py  # 幂等+跨用户隔离+outbox envelope 落库（9 项）
修改  backend/app/services/galaxy/stats_service.py             # spark outbox 走 build_event_metadata + task_id 因果键（payload+correlation 双带）
修改  backend/app/services/galaxy_service.py                   # mastery outbox 走 build_event_metadata（node_id correlation）
修改  backend/app/services/learning_asset_service.py           # outbox 走 build_event_metadata；user_id 前置校验（不烧序号）；status_changed 调用点显式传 user_id
修改  backend/tests/unit/test_learning_assets.py               # 补全 mock user_id（1 行）
产物  v3-output/D-01/REPORT.md + EVENT_REGISTRY.md + changes.patch
```

未做（显式）：Go 侧 types.go 词表收编为 proto/跨层生成物（现有 Go 常量集已封闭且与 Python 侧重合名一致，跨层单一真源改造属后续卡）；`event_outbox` (aggregate_type, aggregate_id, sequence_number) 唯一索引（需 Alembic+live 迁移，风险登记——注意 R2 F1：确定性 event_id 当前零消费者，不能视为既有幂等覆盖）；B1–B6/T1–T2/T3 断点与渗透链修复（卡面明确"不修，列为发现"，移交修复卡）。

## 8. 风险与边界

- 接线后新 outbox 行 metadata 变大（~400B）；relay/投影消费方按 jsonb 整体读，无解析成本差异。
- `derive_event_id` 不做全局唯一存储约束——它是**潜在的**下游去重键而非主键；outbox 主键仍是行 uuid（未变）。**当前零消费者**（R2 F1）：唯一活跃消费方 Go publisher 用 Redis messageID 去重，且其 metadata 解码（`ToDomainEvent`→`EventMetadata`）在第一跳丢弃 event_id/schema_version/occurred_at/correlation{}；gateway `processed_events` 表经 `uuid.Parse` 拒收 `evt_` 前缀，接线前需先解决 id 格式/列语义——已在 registry docstring 如实记载。
- 词表 reserved 名禁止提前生产（C-01 同原则）；若 V3 后续卡启用 intervention.*/action.*，需按 §EVENT_REGISTRY 变更流程显式 bump 冻结哈希。
- R2 移交项（本卡不改，见 REVIEW_RECEIPT_2 §7 台账）：F6 Go 写入方第二 envelope 并存（读侧按 is_v3_envelope 过滤会静默排除全部 gateway 交互侧事件）、F7 outbox 每日清理 7 天留存 vs lineage 目的结构性冲突、F8 spark 链路业务 commit 与 outbox 写非原子（双 commit 窗口）、F2 真值门 fail-open（None/未知 source→True）+ ingest 不校验 source、F9 aggregate_id 未规范化进派生种子、T1/T2/T3 修复本体。

## 9. 收工清理

删除 `backend/app/gen/`（主仓拷贝）、本轮 `__pycache__`/`.pytest_cache`（如有）、`/tmp` 探针产物；无进程/模拟器/浏览器；venv 只读借用未写入；未 commit/push。

## 10. 返修记录（R2 DeepAudit CHANGES → 本轮小修，2026-09-19）

对 REVIEW_RECEIPT_2 §8 四项逐条处置（F2/F6/F7/F8 与 T1/T2/T3 修复本体不在本轮，已由台账卡接管）：

| # | Reviewer 要求 | 处置 | 落点 |
|---|---|---|---|
| 1 | REPORT §5 更正"state_aggregator 实测不读 telemetry"错误断言 + 补 T3 链 | **已改**：§5 重写为 T1/T2/T3 三渗透链清单。T1 更正为"请求即武装"（events.py:65-70 每次遥测 POST 同步触发 estimator，~50 事件/24h 纯量饱和 cognitive_load，P1）；T2 降 P2 但补记 seed 池已污（338 行中 172 行≥0.7 门内，166 行 seed 0.84）；T3 新链全文补录（aggregator 经 cognitive_fragments.sentiment 二跳读遥测衍生情绪，拦截集漏 frustrated/overwhelmed，830/877 行带 sentiment 含 166 seed anxious，P1）。七模块守卫补"仅直接引用级、二跳不可见、静态清单"诚实声明（§5 + 测试 docstring）。所有引用的行号/计数/拦截集均本轮独立复核（psql 只读 + 源码重读），与 R2 一致 | REPORT §5、§4；tests/contract 守卫 docstring |
| 2 | derive_event_id docstring 删除"gateway processed_events 可去重"失实声称（uuid.Parse 拒收 evt_ 前缀；实际去重键 Redis messageID） | **已改**：docstring 重写——幂等语义限定"同一行重投递"（不含同因重执行）；明记当前零消费者、Go 第一跳丢字段、processed_events 路线需先解决 id 格式；id 格式未动 | event_registry.py::derive_event_id；REPORT §4/§8 同步收紧；EVENT_REGISTRY.md §2 |
| 3 | asset 事件零 correlation 与自家规则对齐（补 correlation 或声明豁免类） | **已改**：选**豁免类**——asset 生命周期是聚合根事件，无上游 intervention/action/run/outcome/task 对象可链（aggregate_id+user_id 即全部 lineage），registry 内显式 `CORRELATION_EXEMPT_EVENT_NAMES`（含理由注释）+ 文档声明 + 冻结测试（豁免集精确集断言，新增豁免须显式） | event_registry.py 常量；EVENT_REGISTRY.md §2/§3；test_correlation_exempt_names_are_frozen |
| 4 | read_event_metadata 对畸形行防御（list 直传 TypeError 等） | **已改**：else 分支限 Mapping（非 Mapping 类型拒绝+warning 日志降级空视图）；str/bytes 输入 64KiB 上限、Mapping 输入 ~1MiB 近似上限（超限拒绝+记日志，不截断——截断的 JSON 不可解析且记内容会泄行数据）；json.loads 增捕 RecursionError（深嵌套）；新增 7 项防御测试（list/scalar/tuple/set 直传、JSON 数组串/非 UTF-8、超限串、超限 Mapping、10 万层深嵌套、cap 内合法行不受影响） | event_registry.py::read_event_metadata + MAX_* 常量；contract 测试 §4b |

**返修后验证**：contract 32 passed（原 25 + 新 7）；isolation 9 passed；回归抽样 learning_assets 35 / galaxy 29 / outbox API 4 全绿；新改文件 ruff+black(120) 净；changes.patch 已重导（含返修增量）。初版交付的其余内容（GJ03 链、B1–B6 断点、幂等/隔离守卫）未动。
