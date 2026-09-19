# B-06 REVIEW_RECEIPT（第一路独立 Reviewer · 逐项实证路线）

- **Reviewer**: R1（深算/逐项实证；第二路 Reviewer 负责交叉复核路线）
- **日期**: 2026-09-19
- **被审对象**: 主仓 `/Users/brsama/code/GitHub/Sparkle-project` @ `566517a2`（工作树只读）之 `v3-output/B-06/`（ENTITY_MAP.md、entity_map.csv、COMPLETION_RECEIPT.md）
- **被审基线**: B-06 任务基 `f01f4ae8`；实测代码漂移 `f01f4ae8..566517a2` 不触及本次验证涉及的任何 models/aurora/conflict_resolver/context_pack 文件（diff 仅 13 个无关 service/gateway 文件），验证对基线有效
- **方法**: 权威路径逐条落盘验证（24 概念 × 全部 authority_path）、live DB 只读 SQL 重跑（`docker exec sparkle_db psql` 仅 SELECT，28 张表）、8 组 D-* 双方实现 file:line 取证、2 个 no-authority 全仓负搜索（py/go/dart/sql/proto + DB 表名）、三系统反证 grep、与 DECISIONS_V3.md / KNOWN_CODE_DEBT_LEDGER.md 交叉

---

## 0. 总 Verdict：**CHANGES**（一处事实错误须修，其余全部验证通过）

24 概念映射、8 组 D-* 重复真源、2 个 no-authority 结论、三系统单一 owner **全部实证成立**；唯一必须修正项是 ENTITY_MAP.md §1.2 对 `aurora_calibration_receipt` 登记状态的错误表述（E1，本文件系 V3-0 锁定的 architecture-map，下游以此为准，不允许留可证伪错误）。E2 为措辞精度建议，随 E1 一并修。

---

## 1. 逐概念权威 owner 验证（24/24 通过）

CSV 全部 `authority_path` 逐条在磁盘上验证存在。注意 CSV 同单元格内 `;` 后的裸文件名（如 `plan.py`）继承首个路径的目录前缀（`backend/app/models/`），简写解析后全部命中。抽查行号声明逐字核对：

| CSV 声明 | 实测 | 结果 |
|---|---|---|
| `user.py:73` flame_level | `backend/app/models/user.py:73` `flame_level = Column(Integer, default=1…)` | ✓ 精确命中 |
| `card_protocol.py:388` InterventionRecord | `backend/app/models/card_protocol.py:387` class / `:388` `__tablename__="intervention_records"` | ✓ |
| `execution_intent.py:64` TrustLevel | `backend/app/models/execution_intent.py:63` class TrustLevel，RAW/VALIDATED/TRUSTED 在 :66-68 | ✓（±1 行内） |
| `galaxy_service.py:97` `_write_mastery_outbox_event` | :97 函数定义 | ✓ |
| `galaxy_service.py:142` `outbox_events` fallback | :142 `if await self._table_exists("outbox_events"):` | ✓ |
| ContextPack/ContextPackBuilder | `app/core/context_pack.py:1087/:1170` | ✓ |
| ContextBuilderMixin | `orchestration/context_builder.py:63` | ✓ |
| `models/memory.py` 版本链 version+replaced_by_id+retracted_at | memory.py:24/26/38 三字段齐备 + 唯一版本索引 | ✓ |

曾出现 3 个假阴性（`orchestration/situation_brief.py`、`aurora/privacy.py`、`orchestration/graph_rag.py`）经查均真实存在（`backend/app/orchestration/situation_brief.py`、`backend/app/aurora/privacy.py`、`backend/app/orchestration/graph_rag.py`），为Reviewer 首轮脚本的 `-name` 全路径误用，**非 CSV 错误**。

## 2. SQL 实测（28 表重跑，全部成立，含快照漂移）

| 表 | B-06 记载 | 2026-09-19 重跑 | 判定 |
|---|---|---|---|
| tasks | 1089 | 1219 | ✓ 量级一致（B-01/B-05 在跑，增长方向合理） |
| plans | 357 | 399 | ✓ |
| goals | 4 | 4 | ✓ 精确 |
| cards / task_occurrences | 0 / 0 | 0 / 0 | ✓ 精确（协议就绪未放量核心证据成立） |
| memory_preferences | 59 | 89 | ✓ 同数量级 |
| user_preferences_center | 216 | 248 | ✓ |
| memory_goals | 7 | 12 | ✓ |
| episodic_memories | 209（166+43） | 235（direct_capture=183 + inferred_extraction=52，DISTINCT lane 仅此两个） | ✓ 结构一致 |
| decision_records | 947 | 2492 | ✓ 同数量级（活跃账本，2.6x 日漂移反而佐证"最活跃"） |
| event_outbox | 102 | 106 | ✓ |
| user_state_snapshots | 0 | 0 | ✓ 精确 |
| execution_intents / execution_records | 0 | 0 / 0 | ✓ |
| intervention_records | 1 | 1 | ✓ 精确 |
| conflict_resolution_records / unresolved_conflicts | 0 / 0 | 0 / 0 | ✓ |
| understanding_depth_daily | 149 | 149 | ✓ 精确 |
| intervention_outcomes / behavioral_outcomes / distilled_strategy_cache | 表存在 | 0 行，表在 | ✓ |
| user_library_subscriptions / user_consumables | 表存在 | 1 / 1 | ✓ |
| `outbox_events` 已从 live DB 消失 | 是 | `information_schema.tables` 0 命中 | ✓ |
| 总表数 | 236 | 236 | ✓ 精确 |

## 3. 八组 D-* 重复真源逐组验证（8/8 双方确证，非"历史表误判"）

| 组 | 甲方（file:line） | 乙方（file:line） | 同语义双源判定 |
|---|---|---|---|
| D-PREF | `models/memory.py:16` memory_preferences（版本链+证据字段） | `models/user_preferences.py:15` UserPreferencesCenter | ✓ 双方均 live（89 vs 248 行）；D3 止血证据 `context_pack.py:1410` `preference_dual_source_keys` 在；"并存+审计"定性正确 |
| D-CTX | `core/context_pack.py:1170` ContextPackBuilder | `orchestration/context_builder.py:63` ContextBuilderMixin | ✓ 引用计数实测 **5 vs 1**（pack: standard_workflow/context_focus/api chat/plan_review_service/memory_eval；mixin: 仅 orchestrator.py:262），与 receipt 声明一致 |
| D-INT | `models/card_protocol.py:387` InterventionRecord（cards 域，0 行） | `models/intervention.py:13/:54/:77` Request/AuditLog/Feedback + `intervention_outcome.py:13` | ✓ 卡协议侧是**前瞻目标态**而非历史表（live 路径是 intervention.py），Worker 定性"目标形态 vs 今日 live"正确 |
| D-STATE | `models/user_state.py:12` user_state_snapshots（0 行） | `state_aggregator/schema.py:34` StateFieldEnvelope；另有 `ltm_daily_snapshot.py:10`、`models/aurora_stage31.py:13` daily_behavior_vector、`working_memory/service.py:183` build_snapshot——五方全部在 | ✓ 见 E2 措辞修正 |
| D-TASK | `models/task.py:63/:172` tasks/subtasks（1219 行） | `card_protocol.py:202/:308` cards/task_occurrences（0 行）；`community.py:400` group_tasks；`memory.py:45` memory_goals；`job.py:43` jobs | ✓ 五方全在；受治理迁移（债账 #4）而非腐化，定性正确 |
| D-CONF | `services/conflict_resolver_service.py`（Stage20，import aurora_stage20 :12，ConflictResolutionRecord :233/:301） | `services/layer_conflict_resolver.py`（import five_layer_contract）、`services/memory_conflict_resolver.py`（语义键，作用于 memory 模型） | ✓ 三者职责域确实不同（memory lane 仲裁 / 五层间 / 语义键），Worker"非同职责重复、但命名诱导第四个"的判断准确 |
| D-OUTBOX | `gateway/internal/db/query.sql:136-162`（INSERT/SELECT/UPDATE/DELETE `event_outbox`，经 SQLC `db.InsertOutboxEntry` 被 `cqrs/outbox/repository.go:76` 消费）+ `galaxy_service.py:97` 写入端 | `galaxy_service.py:142-150` `outbox_events` 遗留 fallback（表已不存在→死代码） | ✓ 权威/废弃方向正确 |
| D-ENTITLE | `models/user.py:73` users.flame_level | `models/seed_content.py:261` user_library_subscriptions、`models/shop.py:158` user_consumables | ✓ 另实测 `user_service.py:208` `is_pro=user.flame_level >= 3` 与 `agent_grpc_service.py:272` 快照链仍在——正是 DECISIONS_V3 D17 要求拆除的对象，Worker 标记正确 |

## 4. 两个 no-authority 概念负搜索（2/2 成立）

- **UserWorldSnapshot**: `UserWorldSnapshot|user_world_snapshot|user_world` 在 backend/mobile/gateway/proto 的 py/go/dart/sql/proto 全 0 命中；DB 无 `%user_world%` 表（唯一含 world 的表 `goal_world_graph_snapshots` 属 AGE 图域目标世界快照，非本概念）。契约出处 `v3/02_core_systems/USER_WORLD_MODEL.md:22` 仅为设计文档。✓ 无实现。
- **Experience Memory 聚合体**: `ExperienceMemory|experience_memory` 代码 0 命中；`MEMORY_V3.md:51` §5 仅为设计。最近似资产 `orchestration/experience_packets.py` 头注自述"intentionally aggregate existing systems instead of creating another state store"（每轮瞬态契约，非持久聚合存储）。✓ 无权威存储，Worker"在既有资产上聚合而非新造"的定位正确。

## 5. Aurora / Agent Runtime / Action 单一 owner 反证（3/3 维持）

- **Aurora**: `backend/app/aurora/` 全包在位（engine.py；runtime_v1/ 完整 27 文件含 decision_loop.py 84K、l0_rules~l4_async、correction_feedback.py；policies/）。决策账本 `aurora_stage20.py:16 aurora_judgment_records`、`:95 routing_decision_log` 唯一。反证：全仓无 `*controller*`/`*adaptive*` 目录、services 无 Controller 类；`orchestration/dual_core_router.py` 属编排侧 prompt 参数调制（DualCoreDecision/cognitive_adjustments），消费方是 orchestrator/routing_engine，不构成第二 Adaptive Control owner。✓
- **Agent Runtime**: `ExecutionIntentStatus`（execution_intent.py:47-61）含 DRAFT/QUEUED/RUNNING/WAITING_APPROVAL/SUCCEEDED/PARTIAL/FAILED/CANCELED/TIMED_OUT/HANDED_BACK 全枚举；生产构造点仅 `services/execution_service.py` 一处（唯一写者）。OpenClaw 确为枚举值（ExecutorType :30）+ `execution_router.py:49-69` 开关门（settings OPENCLAW_ENABLED=False）+ `services/openclaw/url_guard.py` 治理，无第二 run 账本。✓（与 D16 一致）
- **Action**: `ExecutionMode` HUMAN/AGENT/HYBRID（execution_intent.py:22-27）+ TrustLevel，单一分配协议成立。✓（与 D13 一致）

## 6. 错误与修正项（逐条）

- **E1（必须修，事实错误）**: ENTITY_MAP.md §1.2 OBSERVATION 行"D2 修复后登记表含 llm_extractor/**aurora_calibration_receipt** 等"。实测 `conflict_resolver_service.py:72-79` 登记表仅 6 键（direct_capture/user_confirmed/llm_extractor/llm_extraction/inferred_extraction/working_memory），**不含** aurora_calibration_receipt；d1d4 文档 :45/:49/:55 明确该 lane 恰是"未登记 lane 落 unknown(0) 最低档"的红线测试用例（`_priority("aurora_calibration_receipt") == 0`）。更值得注意：`aurora/runtime_v1/correction_feedback.py:427` 至今仍在写入 `source_lane="aurora_calibration_receipt"`——按 D2 新约（:51"新增 lane 必须同步登记"）这是一处**活的未登记 lane 写入**（dev DB 当前 0 行，未爆量）。本文件是锁定的 architecture-map，下游 V3 Memory 任务会据它推导 lane 仲裁语义，此句必须改为"登记表含 llm_extractor 等 6 lane；aurora_calibration_receipt 为 written-but-unregistered，落 unknown(0)，且 correction_feedback.py:427 仍在写（须登记或停写）"。
- **E2（建议修，措辞精度）**: CSV D-STATE"user_state_snapshots 表与写入方脱节"。实测写入方存在且确实写该表并 commit（`state_estimator_service.py:30-38` db.add+commit），但**全仓无生产调用方**（孤儿写入路径，故表 0 行）。真实语义是"写入方与 live 流量脱节/写入方未被接线"。建议改写；"先查消费者再决定补写或废弃、V3 前禁双写"的行动项本身正确，保留。
- **E3（备注，无需改）**: §1.1 Run"状态机与 AGENT_RUNTIME.md 几乎一一对应，含 HANDED_BACK"——"几乎"恰当。差异明细：代码多 DRAFT/HANDED_BACK，V3 文档多 EXECUTING/AWAITING_USER/UNKNOWN_OUTCOME，拼写 CANCELED vs CANCELLED。下游实现 V3 Run State Machine 时须显式 reconcile，地图不需改。
- **O1（交叉发现，非 B-06 之过）**: `user_service.py:208` `is_pro = user.flame_level >= 3` 与 `agent_grpc_service.py:272` 快照链仍是活的 D17 拆除对象，但 KNOWN_CODE_DEBT_LEDGER **无任何 flame_level/is_pro/entitlement 条目**——B-06 CSV 已标"flame_level 仍为 users 列即债务标记"，建议随本修把该条补进债账（或在 D-ENTITLE 迁移卡承接）。
- **O2**: memory_admin.py:286 `POST /inferred/revoke`、KNOWN_SOURCE_LANES 注册提示（:454）、`working_memory/schema.py:26` consolidated_to_l1_id、f01f4ae8 即 RAG 注入位置修复 commit——§4 复用资产清单抽验全部属实。

## 7. 与 DECISIONS_V3.md / KNOWN_CODE_DEBT_LEDGER.md 交叉

- D09 四分法 ↔ §1 结构一致；D13 execution_mode 一级属性 ↔ ExecutionIntent.execution_mode 在位；D16 Agent Runtime 唯一 ↔ §1.5/§5 结论一致；D17 拆 `is_pro=flame_level>=3` ↔ D-ENTITLE 方向一致（见 O1 债账缺口）。
- 债账 #4/#6（card_protocol mid-flight）↔ D-TASK/D-INT"跟随 shadow 验证收敛"一致，无冲突。
- 未发现 B-06 结论与两份治理文档的任何冲突点（E1 为与 d1d4 修复事实的冲突，已在 §6 处理）。

## 8. 复核纪律声明

主仓全程只读；DB 仅 SELECT（28 表计数 + 2 次information_schema/DISTINCT 查询）；未起进程/模拟器/构建；无 /tmp 产物；本 receipt 为唯一持久产出（落于 wt8，随 worktree 生命周期管理）。
