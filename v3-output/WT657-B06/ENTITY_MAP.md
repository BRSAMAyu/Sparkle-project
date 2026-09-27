# ENTITY_MAP — V3 概念 → 现有权威实现映射（B-06 round-1，wt657）

> **后续任务必须引用本文件**：为 V3 概动工前先在此查既有权威实体，禁止为 V3 新术语新建平行存储/服务（BASELINE_V2_V2_5 铁律「先映射与复用，禁止平行服务」）。
> 机器可读版：同目录 `ENTITY_MAP.json`。枚举/状态机三面值集对账不在本表重复——见 wt534 基线 [B06_ENTITY_TRUTH_BASELINE.md](../../06_agent_fleet/B06_ENTITY_TRUTH_BASELINE.md) 与常驻守卫 `scripts/guards/check_enum_value_set_parity.py`（ENUM-PARITY，76 族）。
> 基线 SHA `8a0a868f`（main），行号以该基线为准。方法：只读静态审计，file:line 亲证，零产品码改动。

## 0. 存储真源链（总纲）

**存储真源** = backend SQLAlchemy model + Alembic 迁移（schema 唯一入口）→ `schema.sql` 自动导出 → 网关 sqlc 只读派生。**REST wire 真源** = backend Pydantic；**gRPC wire 真源** = proto（buf；三语言 `gen/` 全 gitignore）。mobile Dart model = 手工镜像，值集对账由 ENUM-PARITY 常驻守卫覆盖（`scripts/rule_guard_manifest.tsv:90`）。

## 1. 四分法（USER_WORLD_MODEL）→ 现有实体

### State（业务真值）

| 概念 | 权威实体 | 判定 |
|---|---|---|
| Goal | `models/goal.py` goals | reuse |
| Plan | `models/plan.py` plans；`plan_state.py` plan_states；`plan_execution_record.py` | reuse |
| Task/Action | `models/task.py` tasks+subtasks；`execution_intent.py`；`action_proposal.py`(+transitions)；`card_protocol.py` planning_artifacts/task_occurrences | reuse |
| Schedule | `models/calendar_event.py` calendar_events；`execution_schedule.py` | reuse |
| Artifact | `card_protocol.py` planning_artifacts；`hybrid_journey.py`；`file_storage.py` stored_files | reuse |
| Run | `models/agent_run.py` agent_runs+agent_run_transitions | reuse |
| Membership | `models/community.py` group_members；`achievement.py` study_buddies | reuse |
| Milestone | 无独立实体（plan_states 内嵌语义） | no-authority（需要时属 extend） |

### Memory（五记录类型）

**唯一权威** = `services/memory_epistemic_contract.py`（M-01）：五类型 derive 自既有列，docstring 明言 **no second store**。

| 类型 | 存储 | 判定 |
|---|---|---|
| FACT/OBSERVATION/HYPOTHESIS/EXPERIENCE | `models/memory.py:94` episodic_memories | reuse |
| CONFIRMED_PREFERENCE | `memory.py:20` memory_preferences + `:55` memory_goals（表成员身份承载） | reuse |
| correction/supersede | `memory.py:173` memory_corrections + memory_evolution | reuse |
| 瞬态 | `working_memory/`（Redis 会话级；契约禁止污染长期表） | reuse |
| 唯一写入方 | `services/memory_service.py:142` MemoryService = episodic_memories 全仓唯一构造点（grep 亲证） | 单源成立 |
| lane 档位仲裁 | `services/conflict_resolver_service.py` KNOWN_SOURCE_LANES（M-01 显式委托） | 单源成立 |

`cognitive_fragments`（`models/cognitive.py:28`）是输入碎片（经 `unified_analysis_service` 管线），**不是**第二记忆存储。

### Knowledge

| 概念 | 权威实体 | 判定 |
|---|---|---|
| document/chunk/embedding | `models/document_chunks.py`（写方 `document_service.py`+`rag_indexing_service.py`） | reuse |
| knowledge node | `models/galaxy.py` knowledge_nodes/node_relations/knowledge_node_documents/user_node_status/node_expansion_queue（写方 `galaxy_service.py`/`galaxy_event_consumer.py`） | reuse |
| citation | 无独立实体——provenance 由 document_chunks 溯源列 + knowledge_node_documents 承载 | no-authority（如需显式 Citation 对象属 extend） |
| 检索 | `orchestration/graph_rag.py`（Redis 向量+图混合） | reuse |

### Events

**唯一权威** = `core/event_registry.py`（D-01：事件名封闭词表 + 信封契约 + telemetry 边界）。free-string 事件名 = 契约违规。

| 面 | 载体 | 说明 |
|---|---|---|
| 集成总线 | event_outbox（迁移 `5f2b9b3c0e6f`；网关 RW 授权 `c17_20260502` :37-46） | 引擎事务内写、7 天 cleanup、只承载集成通知 |
| 持久日志 | event_store（迁移 `9c4d7e8f1a2b`:25 建表；无 ORM model） | gateway `cqrs/outbox/repository.go:183-197` 由 publisher 原子落库；Python 零直用——单向流健康 |
| 客户端遥测 | `models/event.py:15` tracking_events | D-01 判 **non-truth**，禁作业务真源 |
| 持久生命周期 | `intervention_lifecycle.py`（刻意区别于会消失的 outbox） | reuse |
| run 审计 | `agent_run.py:218` transitions（与 outbox 同事务 append-only） | reuse |
| 判定/路由留痕 | `aurora_stage20.py` aurora_judgment_records(充分性)+routing_decision_log(路由)；`decision_record.py`(module=ai\|push\|task 通用留痕) | 三表三面，不互为副本 |

## 2. 卡面十二概念 → 权威 owner

| 概念 | 权威 owner（file） | 判定 |
|---|---|---|
| UserState | 多 plane：PG 快照 `user_state.py:15`（写方 `state_estimator_service.py:203`，telemetry-derived，读侧需 V3-FIX-14 waiver 先例 `core/plan_context.py:291`）；活装配 `state_aggregator/service.py:162` → UserStateV1（`proto/user_state.proto:304`，20 字段 AQ 守卫）；路由信念 Redis `evidence/fusion_engine.py:38-43`（TTL 7d）；Aurora 在场态 Redis `aurora/runtime_v1/state.py:412`（TTL 24h）；人格动力学 PG `aurora_stage31.py` | reuse（多 plane 各有声明边界） |
| 五层模型 | 分布式：raw=UnifiedEvidence+server events；projection=`app/profile/projection_contract.py` M1/M2（UserInsightState）；inference=M3+BeliefState；shadow=`safe_experiment.py` assignment_mode=shadow（BE 守卫在位）；correction=memory_corrections+conflict_resolver+`aurora/runtime_v1/correction_feedback.py`。不变量（inference/shadow 不写回 raw、correction 走 supersede）由 M-01 guard+MemoryService 写路径执行 | reuse (distributed) |
| Aurora | 控制决策唯一权威 = `core/aurora_decision.py` A-01 契约（四边界显式：C-01 装配/X-01 任务结构/X-02 分配/A-01 控制决策）；路由面 `aurora/engine.py`；在场面 `aurora/runtime_v1/`（L2 经契约桥接 `l2_intervention.py:19-39`，spine 真通道已接 `signals/spine_orchestrator.py:2699`） | **无双权威** ✅ |
| Memory | M-01 契约 + memory_* 表（上文） | reuse |
| RAG | document_chunks + knowledge_nodes + graph_rag | reuse |
| Task | tasks/subtasks；结构=X-01 action_plan.v1（tasks V3 列） | reuse |
| Plan | plans/plan_states（枚举存储基分裂见 wt534 §2.3，观察） | reuse |
| Event | D-01 + outbox/store/lifecycle（上文） | reuse |
| Attempt | `agent_run.py:98` attempt 列 + :46 活跃 run 唯一索引 + `idempotency_key.py` + execution_audit_log——V2 幂等/receipt/attempt ledger 既有实现满足 | reuse |
| Run | `services/agent_run_service.py` X-05 = run 状态机**唯一写入权威**（12 值封闭迁移图 `core/run_state_machine.py`）；RunLedgerStore 保持 chat 观测定位（:33 显式声明，非双源） | **无双权威** ✅ |
| Permission | 统一概念 **no-authority**；组件：DB 级 RBAC `c17` 迁移角色授权（表级权限单一事实）、`galaxy.py:63` galaxy_user_permissions（协作）、X-02 allocation（human/agent/hybrid）、`intervention.py` user_intervention_settings | no-authority / components reuse |
| Outbox | 引擎写 event_outbox（D-01 词表）→ gateway publisher 落 event_store + 发 Redis streams | reuse |

## 3. NORTH_STAR 八台机器映射（摘要）

| 机器 | 判定 | 权威位置 |
|---|---|---|
| UserWorldModel | reuse | 四分法全表（§1） |
| ContextCompiler | reuse | `core/context_pack.py` + context_pack_runs 等 + M-07 memory_epoch |
| ConflictResolver | reuse | `services/conflict_resolver_service.py` |
| ExperienceMemory | reuse | `core/experience_memory.py` + intervention/community_strategy_outcomes |
| AuroraPolicy | reuse | aurora_policy_patches + `aurora/intervention_policy.py` + policy_loader |
| Human–AI Allocation | reuse | X-02 `services/action_allocation_policy.py` |
| OutcomeLedger | reuse | `core/outcome_ledger.py` + intervention_outcome/behavioral_outcomes |
| TrustLayer | partial | 组件在位（audit_log/compliance/research_consent/C-07/BE 影子守卫）；统一 Trust 面属后续卡，本卡不宣称完成 |

## 4. 重复真源扫描结论（profile/memory/run/task）

- **task：🔴 新登记 V3-FIX-355** — gateway 任务 CQRS 投影族（`task:view:*`/`user:tasks:*`/`user:task:stats:*`）**双投影器零读面**：`worker/task_sync.go:189-348`（live 消费 `cqrs:stream:task`，setup.go:396/:462 运行中）与 `cqrs/projection/handlers.go:287-560`（event_store 重放路径，setup.go:387 注册）两套独立实现写同一批 Redis 键；全仓无任何读消费者（gateway handler/service 零读取；唯一 `Get` 在 task_sync.go:403 是投影自维护；引擎/mobile 不触此键——`scripts/devtools/audit_community_readmodel.py:272` 也只 SCAN 计数）。任务真实读面 = 引擎 REST + gateway `user_context.go` 直读 PG。写侧成本持续发生、投影陈旧无检测面、后续任务误当真源消费即引入第二任务真源。
- **run**：双轨已声明（agent_run_service.py:33），wt534 在册，非新发现。
- **profile**：无同概念双写。user_learning_profiles 写 `tasks/learning_profile_refresh.py:96`（V3-FIX-340 已接线）→ 读 `simulation/seed_extractor.py` 单链；UserInsightState/understanding_*/aurora_stage31 各面消费者不相交。
- **memory**：单写入方成立（上文）。
- **user_state**：五 plane 边界靠声明，无跨面一致性测试——观测级（不登记）。
- **enum 空档（wt534 遗留）**：已由 ENUM-PARITY 守卫封堵（76 族），不再开放。

## 5. 观测项（未达登记门槛）

1. `AuroraDecision` 同名双类：`aurora/runtime_v1/decision_loop.py:225`（会话动作面）vs `core/aurora_decision.py`（A-01 契约面）。同名异面、桥接已声明——对 Agent 是导航隐患，非所有权分裂。
2. user_state 五 plane 无跨面一致性测试（边界靠 waiver 注释/契约声明）。
3. `decision_records`（含 preferences_snapshot 通用留痕）与 A-01 契约记录面并存，用途不同。
4. Milestone 无独立实体；Citation 无独立实体——后续需要时按 extend 走新契约，勿复用组件表冒充。
5. event_store 无 Python ORM 面（gateway 专用持久日志）——单向流健康，仅记录形态。

## 6. 权威判据链（读写双方证据）

每条「谁写谁读」均以 grep+file:line 亲证（写入方构造点、读取方 select/Get 全扫）：

- 双写扫描：`grep -rn 'EntityClass(' app/` 逐实体定位构造点；零写/零读判定为全仓（backend+gateway+mobile+scripts+tests_e2e）grep。
- V3-FIX-355 零读面：`grep -rn 'task:view\|user:tasks\|user:task:stats' gateway/ --include='*.go'` 仅命中写侧两文件+reset；引擎/mobile/scripts 零命中。
- Aurora/Runtime/Action：A-01 契约头注四边界声明（core/aurora_decision.py:15-30）+ 消费面接线亲证（l2_intervention/spine_orchestrator/action_allocation_policy）。
