# D-01 REVIEW RECEIPT · Reviewer #2（DeepAudit 深层审计）

- Reviewer: 第二路 Reviewer（D-01 risk high 需 2 Reviewer；第一路已标准验收 ACCEPT）
- 日期: 2026-09-19
- 对象: wt4 未 commit 改动 + v3-output/D-01/（base 7251128e）
- 方法: 不重复标准验收。六焦点深层审计（幂等键碰撞面 / metadata 演化 / 写入方接线完备性 / 消费侧契约 / 守卫反绕过 / T1-T2 爆炸半径）+ 定向 pytest 独立实跑 + dev DB 只读量化 + registry 模块边界探针实测。
- 测试独立复跑：contract 25 + isolation 9 + regression 68 = **102 passed，与 worker/Reviewer#1 自报一致**。

## 0. 结论速览

代码逻辑本身（registry 模块、三写入方接线、测试）无缺陷；**裁定 CHANGES，全部为交付物准确性层面的小修**（REPORT §5 一处与代码矛盾的事实错误、新模块 docstring 一处错误的消费者声称、契约文档与自家接线方的一处自违反）。深层风险多为卡外/后续卡范围，已按 P0-P3 分级移交主会话。无 P0。

---

## 1. 幂等键碰撞面（焦点 1）

**F9 [P3｜契约缺口，当前写方安全]** derive 的输入集稳定性与碰撞构造：
- `event_registry.py:505` `str(aggregate_id)` **未做 UUID 规范化**（correlation 键有 `_canonical_uuid`，aggregate_id 没有）——实测同一 UUID 对象 vs 大写字符串派生出**不同** event_id。当前三写方全部传 UUID 对象，一致；未来写方传字符串形式即触发去重失效。
- `user_id` 不在派生种子内：非 UUID aggregate_id（如 probe 残留的 `plan-rt02-pg` 型 slug）+ 相同 seq 可跨用户构造同 id（实测 True）。当前三写方 aggregate_id 全局唯一或用户域，无现实碰撞。
- 输入集其余部分稳定：`sort_keys=True` 递归定序、seq 统一 `str()`、correlation canonical UUID、occurred_at 不入种子、None correlation 与缺省等价。
- **重放时 payload 变化**：telemetry 侧为**首写胜出、静默吞掉新数据**（`event_service.py:52-54`，仅记 `deduped`，不比较不合并不告警）；outbox 侧种子含 seq → 同因果重执行（如 Celery/客户端重试烧新 seq）派生**新** id = 重复事件。即 `derive_event_id` 的幂等语义只覆盖"同一行重投递"，不覆盖"同一因果重执行"——测试 `test_stats_service_spark_event_id_is_idempotent_per_causal_inputs` 的注释是诚实的，但 EVENT_REGISTRY.md §2 "同因同果重放得到同一 id" 的表述会让读者以为覆盖后者，建议措辞收紧。

**F1 [P2｜结构性：幂等键无任何消费者，且 docstring 双重失实]** 全仓 grep：`derive_event_id` / `read_event_metadata` / `is_business_truth_eligible` 生产调用面为**零**（仅 build_event_metadata 有 3 个写方）。event_outbox 的唯一活跃消费者是 Go `cqrs/outbox/publisher.go`，而：
- `types.go:189-204 ToDomainEvent` 把 metadata 解码进 `EventMetadata{trace_id,span_id,user_id,correlation_id,causation_id,source}`——**event_id / schema_version / occurred_at / correlation{} 对象在第一跳全部丢弃**，stream 消费者永远看不到幂等键与 lineage（galaxy 事件靠 payload 兜底带 task_id/node_id，learning_asset 事件兜底都没有）；
- `event_registry.py:494-497` docstring 声称 "gateway processed_events per-consumer-group table … can dedupe by this key"——实际 `cqrs/worker/base.go:313` 用的是 Redis `messageID`；且 `outbox/repository.go:291 IsProcessed` 先 `uuid.Parse(eventID)`，`evt_<hex>` 格式**根本进不去**该表（表列是 varchar(100)，是 Go 仓储层自加的 UUID 解析拒收）。
- 影响：D-01 头牌机制（幂等键）当前是**只写不读**；未来接线消费者的人若按 docstring 走 processed_events 路线会踩 uuid.Parse 坑。建议（小修）：修正 docstring，或在 EVENT_REGISTRY.md 明记"消费侧接线待后续卡，Go EventMetadata 需扩展 event_id/correlation 字段"。

## 2. metadata jsonb 膨胀与演化（焦点 2）

- **无单行累积膨胀**：correlation 是每行独立构造（≤10 键 ×36B UUID ≈ 400B/行），长会话只增行数不增单行体积；唯一无上界入口是 `extra` 透传（`build_event_metadata` 只查键碰撞不查大小）——契约层建议加尺寸护栏（P3）。
- **F10 [P3｜确认缺陷，读侧健壮性]** `read_event_metadata` 实测探针：JSON 数组**字符串**（`'[1,2]'`）优雅降级为空 view；但 Python **list 直传**（即 DB jsonb 数组行被查询层 decode 后传入）走 `dict(metadata)` → **未捕获 TypeError 崩溃**（实测复现）。这是唯一会炸而非降级的畸形形状（reviewer #1 测了非 JSON 串/None，未测此形）。深嵌套/超大行不遍历不炸；occurred_at 非法 → None；correlation 非标量值被 `str()` 成 repr 垃圾（不炸）。修法一行：`else` 分支加 `isinstance(metadata, Mapping)` 判断。
- 旧读者读新 metadata：Go 侧标准 Unmarshal 容忍未知字段（已核 + reviewer #1 已核）；Python `read_event_metadata` 未知键进 `raw` 不进视图字段——前向兼容 OK。

## 3. 写入方接线完备性（焦点 3）

全仓 grep（py + go + scripts）event_outbox 写入面盘点：

| 写入方 | 接线状态 | 判定 |
|---|---|---|
| galaxy_service / galaxy/stats_service / learning_asset_service | 已过 build_event_metadata | 卡内交付 ✓ |
| **Go gateway `cqrs/outbox/repository.go InsertWithTx`** | 写 Go 自有 EventMetadata（trace/span/user_id/correlation_id 单串/source），**无 event_id/schema_version/occurred_at/correlation{}** | **F6 [P2]：第四写入方，双 envelope 并存**。REPORT 已声明跨层统一属后续卡，但需明记读侧后果：Go 行 `is_v3_envelope=False`，任何按 v3 envelope 过滤的消费者会**静默排除全部 gateway 交互侧事件**（生产主体流量）。dev 库 106 行无 gateway 行属 dev 流量特性，不代表生产。 |
| cleanup_worker `_run_inbox_decay` | 经 learning_asset_service（已接线） | ✓ 无绕过 |
| scripts/ | 无直写 | ✓ |
| probe 残留 5 行 | 生产者不在仓（B4） | 已入册 observed_unregistered ✓ |

**F8 [P3｜R1 nit 定论 + 更深的既有问题]**：
- galaxy_service：外层 `update_node_mastery` try/except **rollback 后 re-raise**（galaxy_service.py:3434-3437），seq 烧毁与 INSERT 同事务 → build_event_metadata 抛错时整体回滚，**不存在"有 seq 无 metadata 半行"**；R1 nit 实际爆炸半径≈0。
- stats_service：调用方只 `logger.warning` 不回滚（stats_service.py:137-138），但 INSERT 原子带 metadata，半行同样不可能；最坏情形是 seq gap（Go publisher 按 created_at 拉 unpublished，不校验 seq 连续，现实影响为零）。**真正的既有缺陷在别处**：spark 链路业务状态 commit（:104）与 outbox 写 commit（:491）是**两个独立事务**——两 commit 之间崩溃 = study_record/user_node_status 已落库而事件腿永久丢失（outbox 模式核心保证在 spark 路径不成立，galaxy/learning_asset 路径均单事务成立）。D-01 把 metadata 构造放进该窗口只是轻微扩大了可抛面。失败仅 warning 无指标（观测缺口）。属既有债务，建议登记后续卡。

## 4. relay / 消费侧契约压力（焦点 4）

- **F7 [P2｜留存策略与 lineage 目的的结构性冲突]** `cleanup_outbox_events`（celery_schedule.py，**每日调度**）删除 published 且 >7 天的 event_outbox 行。D-01 把 correlation lineage 放进该表 → **GJ trace 的事件域腿只有 7 天存活期**；processed_events 记录比源行活得久，7 天后无法回放/对账。需显式决策：lineage 要么接受 7 天窗口，要么落 event_store（现 0 行）或业务表投影。
- 新 metadata 对 Go 消费者无毒性：user_id 恒 canonical UUID（`_canonical_uuid` 前置），未知字段被忽略——三写方不会造出 poison row。`publishBatch` 对 decode 失败行 `continue` 不标记不删除 = 永久重试 + 事件丢失，但触发条件（user_id 非 UUID）被契约前置挡死，登记为理论路径。
- B4 五行 probe 残留：**已全部 published**（实测 unpublished=0）——早已上过事件总线，现在删行只清表、撤不回任何下游投影影响；清理建议维持，但预期收益改为"防未来读者误读"而非"止损"。

## 5. telemetry 守卫反绕过（焦点 5）

**F12 [P2｜守卫的覆盖面诚实性问题]** 参数化 7 模块源码扫描的绕过面：
1. 静态清单——`state_aggregator/` 只扫 service.py+schema.py 两个文件，新增文件、`services/evidence/` 新模块不在册；建议改为**目录级扫描**（state_aggregator/、services/evidence/ 全目录）。
2. 字符串拼接 SQL / 动态 import / ORM relationship join 可绕过（理论路径，现实概率低）。
3. **最本质**：扫描只看 tracking_events/TrackingEvent 直接引用，**derived-table 二跳全部不可见**——而本卡自己确认的 T1（user_state_snapshots）、T2（cognitive_fragments/behavior_patterns）走的全是二跳，守卫对它们恒绿。守卫名（`..._never_read_client_telemetry`）承诺大于其实际能力，建议在测试 docstring 明示"仅直接引用级"。

**F2 [P2｜确认缺陷：真值门 fail-open]** `is_business_truth_eligible(None)` 与任意未知 source 串 → **True**（实测）。dev 库唯一 tracking_events 行 source=`'test'`（实测值，来自 `tests/integration/test_ltm_e2e.py:94` 直插——测试污染进 live 库，INV-15 家族新成员）→ 若未来消费者按 source 门控，该行与 106 行无 source 的 legacy 行（含 5 行 probe 残留）**全部默认真值合格**。且 telemetry ingest（event_service.py:31）对客户端上报的 source **零校验**（客户端可上报 source="server_service"）。建议后续卡：读侧 helper 改 fail-closed（非 envelope 行需显式白名单），ingest 侧校验 source enum。

**F3 [P1-修复卡｜确认：REPORT §5 的边界盘点漏了第三条渗透链 T3，且有一处事实错误]** 本审计核心新发现：
- `state_aggregator/service.py:524-533`（UserStateV1 权威世界状态）读 `CognitiveFragment.sentiment`（24h 窗口 limit 20）算 emotion_hint / emotional_block；
- `cognitive_stream_worker.py:189-231 _create_fragment` 把 telemetry 事件 payload 的 `sentiment` 写进 fragment——SENSITIVE_SENTIMENTS 只拦 {anxious, depressed, burnout}，而聚合器的 emotional_block 触发集是 {anxious, **frustrated**, **overwhelmed**}——后两个**不在拦截集**，客户端遥测 sentiment 可直达权威状态聚合器；
- REPORT §5 T1 行声称 "V3 真值应只认 state_aggregator（UserStateV1，**实测不读 telemetry**）"——**该断言错误**：聚合器不直接读 tracking_events 表，但经 cognitive_fragments 读 telemetry 衍生数据；七模块守卫对此恒绿（扫不到二跳）。
- live 佐证：cognitive_fragments 877 行中 830 行带 sentiment（neutral 332 / positive 166 / focused 166 / **anxious 166**——anxious 行为 seed 注入，绕过了 stream worker 的 nullify 逻辑，证明该通道已被恰好是 emotional_block 触发值的 sentiment 大规模填充，seed 用户群的权威 emotion_hint 已被污染）。
- 定级理由：这不是假设——通道、代码、数据三面俱在；但它与 T1/T2 同属"发现不修"族，进同一修复卡，**优先级应不低于 T1**。

## 6. T1/T2 爆炸半径（焦点 6）

**F4 [P1-修复卡｜T1 修正：不是"休眠待调度"，是"请求即武装"]** REPORT 称 T1 "live 表 0 行故休眠中，一旦 estimator 被调度…"——不准确：`api/v1/events.py` ingest 端点**每次遥测 POST 同步调用** `estimator.update_state`（cognitive_stream_worker 每事件亦调）。快照表 0 行只因 dev 仅有的 1 行遥测是测试直插（绕过了 API）。污染阈值与"翻十倍"无关，是结构性的：`cognitive_load = min(1, wrong×0.15 + total×0.02)`（state_estimator_service.py）——**纯事件量项在 ~50 事件/24h 即饱和到 1.0**，语义无关的遥测噪音（心跳/screen_view）即可把 interruptibility 压到 0，nightly_review/_latest_state（API + scheduler_service 双入口）与个性化随即消费。**第一条真实生产遥测批次即激活**。修复卡优先级：**P1，卡内最高**。

**F5 [P2-修复卡｜T2 修正：门存在但池已污]** replanner `MIN_CONFIDENCE=0.7` 门真实存在，遥测量小确实过不了门；但 dev 库 behavior_patterns 338 行中 **166 行 seed 注入的"计划谬误" confidence=0.84 已在门内**（guest_seed_service.py:2215）——replanner 的"高置信行为模式"池当下就被 seed 群体占据，T2 修复卡应同时覆盖：fragments→patterns 的 source 门 + seed 模式排除（confidence 或 provenance 维度）。优先级 **P2**（有门、观察型信号），低于 T1/T3。

## 7. 修复卡定级汇总（移交主会话）

| 项 | 级 | 一句话 |
|---|---|---|
| T1 telemetry→state_estimator→nightly_review | **P1** | 请求即激活，~50 事件/24h 饱和，无语义门 |
| T3 telemetry/seed→cognitive_fragments.sentiment→state_aggregator emotion_hint（本审计新发现） | **P1** | REPORT §5 断言错误须更正；frustrated/overwhelmed 不在拦截集 |
| F1 幂等键无消费者 + docstring 失实 + Go EventMetadata 丢字段 | P2 | 消费侧接线后续卡的前置事实 |
| F2 真值门 fail-open（None/未知 source→True）+ ingest 不校验 source | P2 | 读侧 helper fail-closed |
| F5 T2 行为模式池 seed 污染 | P2 | 0.84 seed 模式已在 replanner 门内 |
| F6 Go 写入方第二 envelope 并存 | P2 | 跨层统一后续卡，需先定 is_v3_envelope 语义 |
| F7 outbox 7 天清理 vs lineage 目的 | P2 | 需显式留存决策 |
| F8 spark 链路 outbox 与业务状态非原子（双 commit） | P3 | 既有债务登记 |
| F9/F10/F11/F12 derive 规范化不一致 / list 输入崩溃 / asset 事件零 correlation / 守卫覆盖面措辞 | P3 | 小修清单 |

## 8. 对 D-01 交付物本身的 CHANGES 清单（小修，无需重审全卡）

1. **REPORT §5**：更正 "state_aggregator…实测不读 telemetry" 断言；读路径盘点表补 T3 行（state_aggregator←cognitive_fragments.sentiment）。
2. **event_registry.py `derive_event_id` docstring**：删除/修正 "gateway processed_events … can dedupe by this key"（该表 Go 仓储层 uuid.Parse 拒收 evt_ 前缀；实际去重键是 Redis messageID）；顺带在 EVENT_REGISTRY.md §2 收紧"同因同果"表述（仅同行重投递）。
3. **EVENT_REGISTRY.md §2** 与 learning_asset 写方对齐：要么给 asset 事件补 correlation（如 task_id 可得时带上），要么把"EXECUTION 至少一条 correlation"规则标注 asset 例外（当前自家接线方零 correlation 违反自家规则，且无测试钉 ≥1 规则）。
4. （可选，一行修）`read_event_metadata` else 分支加 Mapping 判断，堵 list 输入 TypeError。

代码逻辑、测试、patch 完整性不持异议（测试 102 独立复跑全绿；上述 1-3 均为文档/注释/契约对齐，4 为单行防御）。

## 9. 收工清理

- 已删：`backend/app/gen/`（主仓只读拷入供 galaxy_service import 链，复跑测试后删除）；无 pytest cache / pycache 残留（PYTHONDONTWRITEBYTECODE=1 + no:cacheprovider）；无 /tmp 产物；无进程/模拟器/浏览器；未 commit/push；dev DB 全程只读（SELECT only）；工作树恢复交付原状（git status 与开工一致）。

VERDICT: CHANGES
