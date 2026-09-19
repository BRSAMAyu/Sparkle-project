# B-06 · ENTITY_MAP — V3 核心实体映射与重复真源审计

- Worker: B-06 (BASELINE / high / LIGHT)
- Base SHA: `f01f4ae8` (final 工作树未 commit，同基线)
- 方法：worktree 静态勘察 + 主仓 dev DB 只读查证（`docker exec sparkle_db psql` 仅 SELECT；236 表）
- 机器可读版：同目录 `entity_map.csv`（24 概念 × 8 列）
- 本文件是 V3-0 锁定的 architecture-map 依据；后续任务引用概念→实现时**必须以此为准**，禁止另起映射。

---

## 0. 一句话结论

V3 四分法（State / Memory / Knowledge / Events）与 Aurora / Agent Runtime / Action 在当前代码中**全部存在唯一权威 owner，无需新造系统**；真正的缺口只有两个 no-authority 概念（Experience Memory 聚合体、UserWorldSnapshot 快照）和四组重复真源（D-PREF / D-CTX / D-INT / D-STATE），全部应走"迁移/收敛"而非重写。

## 1. 概念 → 权威实现映射（四分法验收）

### 1.1 Current State（业务真值）
| V3 概念 | 权威实现 | 备注 |
|---|---|---|
| Goal | `goals`（`backend/app/models/goal.py`） | live 4 行 |
| Plan / Milestone | `plans` / `plan_states` / `planning_artifacts`（`models/plan.py`） | live 357 行 |
| Action / Task | `tasks` + `subtasks`（`models/task.py`）为**今日真值**；`cards` + `task_occurrences`（`models/card_protocol.py`）为协议化目标形态，**已建表 0 行**（card_protocol legacy 迁移 mid-flight，见 KNOWN_CODE_DEBT_LEDGER #4/#6） | 见 D-TASK |
| Schedule | `calendar_events` / `execution_schedules` | — |
| Run | `execution_intents` + `execution_records`（状态机与 `v3/02_core_systems/AGENT_RUNTIME.md` 几乎一一对应，含 `HANDED_BACK`） | 协议就绪未放量 |
| Membership/约束 | `groups` 系 + `plan quota/policy` 服务 | — |

### 1.2 Memory
| V3 概念 | 权威实现 |
|---|---|
| FACT / CONFIRMED_PREFERENCE | `memory_preferences`、`memory_goals`（版本链 version+replaced_by_id+retracted_at） |
| OBSERVATION | `episodic_memories`，`source_lane` 分 lane（live：`direct_capture`=166、`inferred_extraction`=43；D2 修复后登记表含 llm_extractor/aurora_calibration_receipt 等） |
| HYPOTHESIS | inferred lane 承载，但**未显式标注 epistemic class**——V3 加字段而非新表 |
| EXPERIENCE | ⚠ 无权威存储（见 §3 缺口） |
| 瞬态（working memory） | `backend/app/working_memory/`（Redis，`consolidated_to_l1_id` 指向 episodic）——符合"瞬态不污染长期 Memory"铁律 |
| 纠正 | `memory_corrections` + `aurora/runtime_v1/correction_feedback.py` + `memory_admin.py /inferred/revoke` |
| 五层 epistemic（raw evidence→projection→inference→shadow→correction） | 不是一张表：`five_layer_learning_contract.py`（constitutional/session/episode/profile/system 契约+forbidden_writes 铁律）+ `unified_evidence.py`（raw）+ `UserInsightCompiler→UserInsightState`（**canonical profile 事实所有权**，见 `profile_truth_compiler.py` 头注）+ `shadow_prediction_service.py`（shadow）+ correction 链 |

### 1.3 Knowledge
`document_chunks` + `knowledge_nodes`/`knowledge_node_documents`/`node_relations`/`semantic_links`/`strategy_nodes` + `graph_rag.py`。与 User Memory 物理分表，符合隔离要求。RAG 检索链（rag_indexing/rerank/embedding/semantic_cache）直接复用；`f01f4ae8` 刚修注入位置，勿回退。

### 1.4 Events
`event_store`（CQRS 追加）+ `event_outbox`（relay 权威，live 102 行）+ `tracking_events` + `chat_messages` + `decision_records`（live 947 行，最活跃的决策事件账）+ `execution_audit_log` + `memory_corrections`。V3 需要的是面向 decision 的**读侧投影**，不是新事件存储。

### 1.5 Aurora / Agent Runtime / Action — 单一 owner 确认（验收项 2）
- **Aurora**：唯一 owner = `backend/app/aurora/`（engine.py 路由/降级 + runtime_v1/decision_loop.py + l0~l4 干预分层 + policies/）。决不另造 Controller 服务。决策账本 = `aurora_judgment_records` + `routing_decision_log`。
- **Agent Runtime**：唯一 run truth = `execution_intents`。OpenClaw 仅是 `ExecutorType.OPENCLAW` 枚举值（有 url_guard 治理），不是第二账本/第二权限系统——保持此格局。
- **Action**：proposal/execution 分配的唯一协议 = `ExecutionIntent`（`execution_mode` HUMAN/AGENT/HYBRID + `TrustLevel` RAW/VALIDATED/TRUSTED）。V3 Human-Agent Allocation 扩展此字段而非新建分配服务。
- **Permission/隔离**：网关鉴权 + `permission_service` + `aurora/privacy.py` + `privacy_budget_ledger`；确定性边界（权限/TTL/幂等/审计）已脱离模型自由裁量，符合 NORTH_STAR §5。

## 2. 重复真源审计（迁移而非重写）

| # | 概念 | 多实现 | 权威真源 | 应废弃/收敛方 | 迁移路径 |
|---|---|---|---|---|---|
| D-PREF | 用户偏好 | `memory_preferences`（证据化、版本链）vs `user_preferences_center`（explicit/inferred/traits JSON，live 216 行 vs 59 行） | **暂双源并存、可审计**——37806718 (D3) 已把 context_pack 的静默遮蔽改为并存+`preference_dual_source_keys` 审计键 | 无立即废弃方；`user_settings`/`push_preferences`/`notification_preferences` 是域内设置非偏好真源，勿混 | 版本链写/读语义统一属 V3（d1d4 审计 §6.2 步骤 4）：以 memory_preferences 版本链为记录层、user_preferences_center 为投影层 |
| D-CTX | 上下文装配 | `app/core/context_pack.py::ContextPackBuilder`（5 个消费者+落表+预算）vs `orchestration/context_builder.py::ContextBuilderMixin`（orchestrator/plan_review 使用，平行装配） | `ContextPack`（有 `context_pack_runs`/`context_budget_profiles` 表与 telemetry） | ContextBuilderMixin 的平行装配路径 | V3 Context Compiler 以 ContextPack 为唯一契约；orchestrator 改为消费 ContextPack，保留 ContextBuilderMixin 内的 stage 适配器作数据源 |
| D-INT | 干预记录 | `card_protocol.InterventionRecord`（cards 域，0 行）vs `intervention.py` 的 InterventionRequest/AuditLog/Feedback + `intervention_outcomes` | 待定：card_protocol 是目标形态但 shadow 未完成；intervention.py 是今日 live 路径 | 都不立即废弃 | 跟随 card_protocol legacy 迁移收敛（债账 #4），V3 期间只经 `intervention_service` 写，禁止第三入口 |
| D-STATE | 用户状态 | `user_state_snapshots`（表 0 行）vs `state_aggregator.StateFieldEnvelope`（20 个类型化字段）vs `ltm_daily_snapshots` vs `daily_behavior_vector` vs working_memory snapshot | `state_aggregator`（schema.py 是唯一类型化契约） | `user_state_snapshots` 表与写入方**脱节**——先查消费者再决定补写或废弃，V3 前禁止双写 | UserWorldSnapshot（V3）以 state_aggregator 字段为骨架合成 |
| D-TASK | 任务 | `tasks`(1089 行 live) vs `cards`+`task_occurrences`(0 行) vs `group_tasks`(社群域) vs `memory_goals`(7 行记忆域) vs `jobs`(celery) | 今日真值=`tasks`；card_protocol 为目标协议 | 无（两态并存是受治理的迁移，非腐化） | card_protocol shadow 验证通过后切流；V3 Smallest Useful Step 落在 task_occurrences 上 |
| D-CONF | 冲突裁决 | `conflict_resolver_service.py`(Stage20 lane 仲裁) vs `layer_conflict_resolver.py`(五层间) vs `memory_conflict_resolver.py`(语义键) | Stage20 为 memory lane 仲裁权威（D1-D4 已修） | 两个窄域 resolver 非同职责重复，但**命名易诱导 V3 Agent 造第四个**——V3 Conflict Resolver 一律扩展 Stage20 比较键 | 统一入口 facade 属低优选项 |
| D-OUTBOX | 事件外发 | `event_outbox`（权威）vs `outbox_events`（遗留） | `event_outbox`（live 102 行；遗留表已从 live DB 消失） | `galaxy_service.py:142` 的 `outbox_events` fallback 成死代码 | 删 fallback 分支（随 V3 清理，不阻塞） |
| D-ENTITLE | 权益 | `users.flame_level`（user.py:73）vs `user_library_subscriptions`/`user_consumables` | subscription/consumable 表 | flame_level 保留为展示层字段，禁作权益判据（V3 规则明文） | 渐进迁移判定点 |

## 3. V3 缺口（no-authority，需新建但须先证明现有对象不能扩展）

1. **Experience Memory 聚合体**：`MEMORY_V3.md §5` 的（情境签名→干预→结果→反馈→边界）payload 无单一存储。最接近资产：`learning/distiller.py+strategy_store.py`（`distilled_strategy_cache`，source_trajectory_type="user_success"）、`intervention_strategy_outcomes`、`behavioral_outcomes`、`nightly_reviews`、`orchestration/experience_packets.py`。V3 应在此之上聚合，**不是**新造平行学习系统。
2. **UserWorldSnapshot**：Context Compiler 的结构化快照输入不存在聚合体；扩展点 = `context_pack.py` 装配 + `state_aggregator` 字段 + `situation_brief.py`。
3. **Trajectory / Golden Journey 读模型**：事件源已在 event_store，轨迹状态已在 plan_states——V3 只需读侧视图。

## 4. V2.5 已落地数据飞轮资产（V3 直接复用的地基，勿重建）

| 资产 | 实现 | V3 用法 |
|---|---|---|
| episodic 三 lane | `episodic_memories.source_lane` + `memory_inferred_write_lane.py`（`inferred_extraction` lane 带语义键/去重/撤回）+ `KNOWN_SOURCE_LANES` 优先级登记（D2 修复后 unknown lane 落最低档） | Memory Record 的 epistemic class 与证据强度直接映射；V3 新 lane 必须登记 |
| ConflictResolver | `conflict_resolver_service.py` Stage20：确定性裁决+`ConflictResolutionRecord` 审计+`unresolved_conflicts` pending_user 队列；37806718 修 D1(死门)/D2(lane 兜底)/D3(双源遮蔽)/D4(decay) | V3 Resolution Tuple 在其比较键上扩展；`unresolved_conflicts` 即 V3 "ask once" 机制 |
| 理解深度表 | `understanding_depth_daily`（live 149 行）+ `understanding_depth_metric_service.py` | V3 Understanding Dimensions（Coverage/Correctness/Utility…）的数据基座；替代单一"理解度 %" |
| memory 治理 API | `api/v1/memory_settings.py`（用户级设置）、`memory_admin.py`（stats/health/jobs/**inferred revoke**）、`preferences.py`（preview/effectiveness）、`profile_transparency.py`、`memory_rank_policies`/`user_memory_settings` | V3 P5 Trust Layer 与"你告诉我的/观察到的/不确定的/有效方法"四分区页面的现成后端 |
| galaxy outbox | `event_outbox`（gateway CQRS relay，live 102 行）+ `galaxy_service._write_mastery_outbox_event` | 跨端 mastery 同步通道直接复用 |
| 五层契约 | `five_layer_learning_contract.py`（promotion_thresholds/forbidden_writes/reason_taxonomy）+ `layer_conflict_resolver` | V3 "inference 不写回 raw fact / correction 走 supersede" 的既有机制化实现 |
| Context 预算与可观测 | `context_budget_profiles` + `context_pack_runs` + `context_pack_telemetry_service` + semantic gating | V3 Context Compiler 的 budget policy 与 observability 直接挂接 |
| 执行协议 | `ExecutionIntent`（mode/trust/timeout/success_criteria）+ `idempotency_keys` + `execution_audit_log` | V3 Action Proposal 与 Run contract 的骨架，仅缺 normalized args hash 等字段级扩展 |

## 5. 铁律重申（给后续 V3 Agent）

- 找不到概念 ≠ 建新表：先按本文件路径证明现有对象不能扩展（ENTITY_MAP.md 契约同款规则）。
- `raw evidence→…→correction` 铁律已机制化：任何"让推断直接改事实层"的 PR 都违反 `forbidden_writes` 契约。
- 不要引入第三套 preference/task/run/intervention 写入口。
- V3 期间所有 State 写经 service 层，所有跨端同步经 `event_outbox`。
