# A-01 · Aurora Runtime → AuroraDecisionContract 映射表

> 基线：origin/main @ `cba29db1`（含 B-06/C-01/C-02/C-03/X-01/X-02/D-02/M-01..M-04/M-07 与 FIX 家族全部合入）。
> 契约真源：`backend/app/core/aurora_decision.py`（`aurora_decision.v1`，冻结纪律见模块 docstring）。
> 本表是「映射产出」，不是重建指令——每行给出：**现状 / 契约角色 / 升级路径**。
> 现状分类：`决策点`＝已产出控制决策（但多为内部形状）；`sidecar`＝元数据/观测旁路；
> `守卫`＝边界/安全组件（不产决策，约束决策）；`待升级`＝有决策语义但未显式化。

## 0. 阅读指南

**契约四边界**（详见 `app/core/aurora_decision.py` 模块 docstring）：

| 面 | 契约 | 归属 |
|---|---|---|
| 证据装配（装了什么/为何/降级） | C-01 `decision_context.v1` | ContextPack/DecisionContext |
| 任务结构（outcome/step/evidence/ownership） | X-01 `action_plan.v1` | tasks 表 V3 列 |
| 执行分配（谁执行/供给 vetting） | X-02 `allocation.v1.1` | decide_allocation/vet_agent_offer |
| **控制决策（选什么干预/为何/哪档认知/或为何不行动）** | **A-01 `aurora_decision.v1`** | AuroraDecisionContract |

**命名消歧**（强制，C-01 对 SituationBrief 同款纪律）：
`app.aurora.runtime_v1.decision_loop.AuroraDecision` = LLM 决策环的 **harness 执行决策**
（emit_message/wait/schedule_wake/update_harness/update_state/soft_return_topic/drop_thread）；
`app.core.aurora_decision.AuroraDecisionContract` = **控制决策面契约**。两者同名近义、
分属执行面/控制面，禁止互相替换或混用。runtime 对象升级路径见 §2 R-08。

**状态图例**：✅ 本卡已接线（示范）；🔵 契约天然对齐（读侧即可投影，无需改造）；
🟡 A-04 接线日升级（联合决策面）；⚪ 非决策组件（守卫/基础设施，仅登记管辖关系）。

---

## 1. backend/app/aurora（核心包，22 组件）

| # | 组件 | 现状 | 契约角色（aurora_decision.v1 映射） | 升级路径 |
|---|------|------|--------------------------------------|----------|
| A-01 | `engine.py` · AuroraEngine（materiality_check / decide_backbone_route / dispatch_trigger / safe_route） | 决策点 | stay=**no_action**+`materiality_below_threshold`；transition=目录内干预（rescope 族）；`DecisionMechanism` → cognition_tier 判据；tier=inline/nearline/long_horizon 不等于认知档，勿混用 | 🟡 A-04：`safe_route` 产出 TransitionDecisionRecord 的同时投影一份 AuroraDecisionContract（stay/transition 二值最易投影，作第二个接线点） |
| A-02 | `context.py` · AuroraDecisionContext / AuroraTier / AuroraAsyncFlags | sidecar（输入 bundle） | 运行时输入侧；与 C-01 DecisionContext 是**两个输入面**（前者=路由 helpers 的 trigger bundle，后者=pack 决策面）；`snapshot.snapshot_hash` → `input_context_hash` 候选 | 🔵 读侧对齐：snapshot_hash 直接填 `input_context_hash`（无需改本文件） |
| A-03 | `decision_fns/backbone.py` · decide_backbone_route / RoutingMode | 决策点 | DIRECT/WORKFLOW/TASK_ASSISTANT 三分流 → execute/co_execute/explain 族的粗分类候选 | 🟡 与 A-01 engine 同日接线（同一决策的两半） |
| A-04 | `decision_fns/materiality.py` · check_materiality | 决策点（门控） | sufficiency 门：不过阈值 ⇒ 唯一合法出口是 `no_action`+`materiality_below_threshold` | 🔵 已有词表成员，接线只需投影 |
| A-05 | `decision_fns/triggers.py` · dispatch_trigger | sidecar | 触发点/预算/优先级元数据 → `trigger_point`（契约信息字段，不封闭）+ latency class | ⚪ 无需升级 |
| A-06 | `decision_fns/escalation.py` · detect_escalation（WS-B.2 三触发器） | 决策点 | direct→workflow 升格 = execute 族升格；EscalationVerdict.confidence → uncertainties（低置信时 `insufficient_context`） | 🟡 第二优先接线候选（纯函数、无 IO，比 L2 还轻） |
| A-07 | `decision_fns/fallback.py` · build_fallback_decision | 决策点（降级） | 一切内部异常出口 → `rule_fallback` 档 + `policy_gap` 不确定性（X-02 E1 同款） | 🔵 词表已就位 |
| A-08 | `schemas/`（primitives+enums：TransitionDecisionRecord / DecisionBasis / DecisionMechanism / ImpactClass / InitiationType / UXIntent / AuroraPresenceLevel…） | 决策点（记录层，Gate 0 冻结） | **记录面与契约面互补**：TransitionDecisionRecord=持久化/审计事件；AuroraDecisionContract=控制语义。evidence_refs 在记录层是自由串（如 `"aurora_route"`）——契约层拒绝裸 token（封闭 scheme），这正是本卡要堵的洞 | 🟡 A-04：`TransitionDecisionRecord.evidence_refs` 升级为契约 ref scheme（迁移期双写） |
| A-09 | `signal_aggregator.py` · SignalSnapshot | sidecar（输入装配） | 快照=决策输入；snapshot_hash 是 `input_context_hash` 真源 | 🔵 |
| A-10 | `policy_loader.py` + `policies/v1.0.yaml` · AuroraPolicyVersion | 真源（policy） | `PolicyPatchCandidate.scope` 白名单的真源归因（P2-2 勘误，与 yaml 事实一致）：parameter_write_authority 仅 {ux_intent, aurora_presence}；**capability_gate 仅在 writable_policy_scope 且只有 task_execution / meta_reflection 两个变体（2/4）**——变体级授权，非全局；顶层阈值面 {proactive_policy, materiality_threshold}；intervention_preference 为 AURORA_V3 §4 规格层来源（yaml 全文无）。A-04/L4 消费 capability_gate 时必须按变体判写权限 | ⚪ 契约白名单集合不变（6 面并集），归因文本已勘正 |
| A-11 | `core_session.py` · AuroraCoreSession（L3 建模会话状态机） | 决策点 | 会话进入（8 唤醒条件）=干预决策：`reflect`（belief_revision）/`clarify`（conflict_resolution）等；tier=`l3_full_core`；`model_conflict` 唤醒 → uncertainties `user_model_conflict` | 🟡 A-04（会话进入决策是高价值投影，但涉及 DB 会话状态，留联合接线日） |
| A-12 | `bayesian/`（learner / update） | 决策点（机制层） | `DecisionMechanism.BAYESIAN` 的支撑；产出置信 → uncertainties/置信度校准 | ⚪ 机制层，不直接产契约 |
| A-13 | `ledger.py` · AppendOnlyLedgerStore（InsightClaim/ProbeOutcome） | 真源（claim 账本） | claim 未探测 → uncertainties `unverified_inference` 的判定来源；ProbeOutcome → evidence_refs（`decision://`/`memory://`） | 🔵 |
| A-14 | `relationship_state.py` · SparkleRelationshipStateManager | sidecar（关系态） | 关系成熟度/沟通风格 = 输入投影（profile:// ref）；minimum_relationship_maturity 门控 proactive | 🔵 |
| A-15 | `profile_translator.py`（用户纠偏 → claim） | 决策点（纠偏链） | 纠偏传播 = `PolicyPatchCandidate`（scope=intervention_preference）+ `user_confirmed` 来源 | 🟡 A-04 |
| A-16 | `privacy.py`（PII redaction + AuroraPrivacyKillSwitchService） | 守卫 | 不产决策；约束：契约载荷必须经 redaction（rationale_summary/notes 落库前） | ⚪ |
| A-17 | `llm_bridge.py`（hybrid 决策 LLM 桥） | 基础设施 | LLM 通道：产出必须落规则 feasible set（X-02 语义层同款纪律），失败 → `rule_fallback` | ⚪ |
| A-18 | `predicted_reply_engine.py`（预测回复选项） | sidecar | 回复选项≠控制决策；选中选项携带的 model_write_effect 走 write_pipeline | ⚪ |
| A-19 | `growth_signal_contract.py`（ws-g1） | 契约（既有） | 独立小契约，与 aurora_decision.v1 并列不合并 | ⚪ |
| A-20 | `migration.py`（cutover cohort / route_dual_core_via_aurora / shadow divergence 记录） | 决策点（治理） | shadow cohort 的 Aurora 判定 = `governance_mode="shadow"` 契约；`decision_id` 确定性 ⇒ shadow/live 对比的锚点（替代现 ShadowHookObservation 的 ad-hoc 比较） | 🟡 A-04：ShadowHookObservation 增挂 decision_id 对 |
| A-21 | `tasks.py`（nearline/long-horizon Celery enqueue） | 基础设施 | 异步档执行面（≠认知档）；对应 AURORA_V3 决策环的 hand-off 段 | ⚪ |
| A-22 | `observability/`（metrics/benchmark/tiering） | sidecar | 指标面；AURORA_V3 §8 评测（latency/cost per decision）消费 decision_id 作维度 | 🔵 |

## 2. backend/app/aurora/runtime_v1（运行时，14 组件）

| # | 组件 | 现状 | 契约角色 | 升级路径 |
|---|------|------|----------|----------|
| R-01 | `l0_rules.py` · L0RuleEngine（deadline_pressure / quiet_hours） | 决策点 | deadline 信号=REMIND 族输入；quiet_hours ⇒ `no_action`+`quiet_hours`（词表已含）；tier=`l0_rules` | 🟡 第三接线候选（`no_action`+`quiet_hours` 是词表最短路径） |
| R-02 | `l1_light_aurora.py` · L1LightAurora / L1TurnResult | 决策点（逐轮感知） | L1TurnResult.should_escalate = 升格决策；retrieval_mode → RETRIEVE 族；tier=`l1_light` | 🟡 A-04（其输出已被 orchestrator L1 fast-path 消费，接线收益高） |
| R-03 | **`l2_intervention.py` · L2InterventionEngine** | **决策点 → 本卡示范接线** ✅ | 模式命中 → `rescope`（error_replan_bridge/adaptive_replan）/`pause`（reduce_load）；execution_mode=HYBRID（经 planning 管道+用户确认）；evidence=`signal://<state_key>`；tier=`l2_intervention`；无命中/冷却/空输入 → `no_action`+封闭原因码 | **已完成**：`check_escalation` 结果携带 `aurora_decision`；`decide()` 提供全结局契约视图（无副作用）；映射冻结于 `L2_INTERVENTION_TO_CATALOG`（wiring 测试强制全员覆盖） |
| R-04 | `l3_full_core.py`（L3 会话/唤醒条件） | 决策点 | 同 A-11（会话进入=干预决策；tier=`l3_full_core`） | 🟡 A-04 |
| R-05 | `l4_async.py`（PolicyUpdateCandidate） | 决策点（后台） | **PolicyPatchCandidate 的运行时生产者**（tier=`l4_async`）；shadow→simulation→guardrail 治理链与契约 `user_confirmed`/`expires_at` 对齐 | 🟡 A-04（候选结构对齐已在词表层完成） |
| R-06 | `energy_controller.py` · EnergyLevelDecider | 决策点（档位选择） | L0..L3 能量档 = **cognition_tier 的选择器**（决策「用哪档认知」本身是控制决策） | 🟡 A-04：EnergyDecision 投影为 tier 选择契约（或作为 AuroraDecisionContract.cognition_tier 的权威来源） |
| R-07 | `wake_policy.py` + `wake_scheduler.py` | 决策点（主动触达） | 主动唤醒 = `remind`/`schedule` 干预；quiet hours/预算门 ⇒ `no_action`+`quiet_hours`/`budget_exhausted` | 🟡 A-04（proactive precision 评测消费面） |
| R-08 | `decision_loop.py` · AuroraDecisionLoop / AuroraDecision（**harness 执行决策**） | 决策点（执行面） | **执行面，不是控制面**：action 词表（emit_message/wait/…）是 harness 协议；控制语义（该不该干预/为何）由外层（L1 门控+dashboard readout）持有 | 🟡 A-04：`decide()` 出口投影 AuroraDecisionContract（intervention 由 chat_directive/response_type 反查目录），消除同名近义的双义性 |
| R-09 | `service.py` · AuroraRuntimeV1Service / plan_turn | 决策点（编排）+治理入口 | stage38 kill switch `off` 短路 = **契约 off 态的定义处**（不构造实例）；`shadow` 判定 → governance_mode | 🔵 语义已对齐（off=absence）；A-04 在 plan_turn 出口统一挂契约 |
| R-10 | `chat_adapter.py` | 基础设施 | 聊天面适配；契约不经过它（控制决策在 adapter 之上产生） | ⚪ |
| R-11 | `dashboard.py` · DashboardReadout(+Builder) | sidecar（决策输入装配） | readout = decision_loop 的输入面（与 C-01 pack 的关系=AURORA 决策的第二输入面）；REQUIRED_MODELING_DOMAINS 与 FORBIDDEN_MODELING_DOMAINS 守卫保留 | 🔵 |
| R-12 | `correction_feedback.py` · CorrectionFeedbackProcessor | 决策点（纠偏） | 用户纠偏 → correction_types 载荷 → 同 A-15（PolicyPatchCandidate + user_confirmed） | 🟡 A-04 |
| R-13 | `telemetry.py` · AuroraDecisionTelemetryService | sidecar（遥测） | 契约的天然消费方：按 decision_id/intervention_type/tier 上报（AURORA_V3 §8） | 🔵 |
| R-14 | `write_pipeline.py` / `self_model.py` / `planning.py` / `checkpoint_runtime.py` / `aurora_spine_confluence.py` / `control_surface.py` / `reply_option_injector.py` / `user_preferences.py` / `state.py` / `models.py` / `persistence.py` / `skills.py` | 混合（写管线/状态/偏好面） | 写路径（InferenceClaim 等）受 Bounded Plasticity 约束——**契约只建议（PolicyPatchCandidate），写管线落效**（白名单 surface）；control_surface 的 hard bounds 是决策的输入约束 | ⚪（写管线在 A-04/A-06 演进，本卡不动） |

## 3. backend/app/orchestration（集成缝，6 组件）+ signals spine（1）

| # | 组件 | 现状 | 契约角色 | 升级路径 |
|---|------|------|----------|----------|
| O-01 | `routing_engine.py` · RoutingEngineMixin（aurora migration shadow hooks / L0 wiring / escalation detect / sufficiency judge） | 决策点（路由权威） | 路由决策=控制决策的入口缝；SufficiencyJudge 结果 → `insufficient_context` 不确定性/`clarify` 干预；多 kill switch（stage20/21/33/35/39 + dual_core_router）= 分段治理面 | 🟡 A-04：routing 决策统一挂契约（与 X-02 `routing.decision_recorded` 同族事件已存在，事件域零新增） |
| O-02 | `dual_core_router.py` · dual_core_router / DualCoreDecision | 决策点（legacy 权威） | legacy 双核决策真源；Aurora 经 migration.py 投影回此面（AuroraProjectedDualCoreResult）——**不重建**，契约与它并存至 cutover 完成 | ⚪（cutover 治理归 migration.py） |
| O-03 | `orchestrator.py` · ChatOrchestrator（`_attach_aurora_planning_sidecar` / aurora surfaces / correction processing） | 决策点（主管道集成） | planning sidecar 携带 `decision.to_payload()`（harness 面）——升级为附 `AuroraDecisionContract`；L1 fast-path 门控已消费 should_escalate | 🟡 A-04（sidecar_meta 增契约块；read 门走 `aurora_decision_from_dict`+validate） |
| O-04 | `context_builder.py`（ledger/profile/relationship/self_model 读） | sidecar（输入装配） | C-01 pack 装配侧；aurora 域读（claim/relationship）经 ref 进 evidence_refs（`memory://`/`profile://`） | 🔵 |
| O-05 | `adaptive_replanner.py` · AdaptiveReplanner | 决策点（重排） | L2 `error_replan_bridge`/`adaptive_replan` 的**执行器**（干预落地）；任务结构落 X-01，重排决策语义回填契约 | 🟡 A-04（L2 契约 → replanner 调用链打通后闭环可评测） |
| O-06 | `planning_workflow.py` · AuroraRuntimePlanningAdapter / `ux_envelope.py`（presence/ux_intent 面） | 决策点（规划/UX 面） | ux_intent/aurora_presence = policy patch 白名单 surface 的两个成员（policy 写路径）；UX envelope 消费 presence 决策 | ⚪→🟡 |
| S-01 | `signals/spine_orchestrator.py` · SpineOrchestrator（L1/L2 接线、InterventionEpisode、policy decision） | 决策点（spine 管道） | L2 升级检查的宿主（本卡示范接线的消费端）；`InterventionEpisode` ledger=干预剧集记录（与契约 decision_id 可关联）；`_policy_decide` 的 StrategyDecision=策略选择决策 | 🔵→🟡：`pipeline_context["l2_escalation"]["aurora_decision"]` **写后待 A-04 喂**——该键当前无生产读者（policy_engine.evaluate 只读 `spine:aurora_decisions:*` 通道，spine_aurora_bridge.feed_aurora_decision 未被 L2 喂入）；本卡已加 decision_id 结构化日志作最小观测点；A-04 喂通道 + episode↔decision_id 关联 |

## 4. 治理面（kill switch 家族 → 契约三态）

23 个 `aurora_*_kill_switch_service`（stage18/19/20/21/23/24/25/26/27/28/29/30/31/33/34/35/37/38/39/40 + dual_core_router + privacy + doc_context；P3-5 勘误：原计 22，实数 23）全部基于 `app/core/kill_switch.py` 的三态原语（off/shadow/live）。

**契约化规则（本卡定义，组件无需改动）**：

| kill switch 态 | 契约表现 |
|---|---|
| `off` | **不存在 AuroraDecisionContract 实例**（如 `AuroraRuntimeV1Service.plan_turn` 的 off 短路）——治理关闭不是一种决策（C-01 FIX-09 纪律的决策侧对偶） |
| `shadow` | 实例携带 `governance_mode="shadow"`；同输入同结论与 live 共享 `decision_id`（对比锚点） |
| `live` | 实例携带 `governance_mode="live"`；决策经既有管道实际生效 |

分段 kill switch（stage20/21/33/35/39 等）各自管辖其组件的态；**一份决策的 governance_mode 取其
生效路径上最严的档位**（任何一段 off ⇒ 整条链路不产 live 实例）。细则在 A-04 接线日落成硬规则。

## 5. 挂旗（今日不做，接线日处理）

- **M-04 R2 / F-6**：lane 守卫须类感知（lane guard 的 class-aware 判定）——属 **M-06/A-04 接线日**。
  本表 O-01（routing_engine 路由缝）与 R-08（decision_loop 出口）是受影响接线点，契约层无需改动
  （lane 类别不是 aurora_decision.v1 字段；如接线日需要，走 extend-only 追加可选尾字段）。
- **A-04 联合决策**（decision_context × action_plan × allocation × aurora_decision 四面联合）：
  本表所有 🟡 行是 A-04 的工作清单（按接线收益排序：engine/safe_route → escalation → L0/L1 →
  wake_policy → core_session → decision_loop 出口 → sidecar/telemetry）。

## 6. 覆盖统计

- 决策点（含待升级）：A-01/03/04/06/07/08/11/15/20（9）+ R-01..R-09（9）+ R-12 + O-01/02/03/05/06（5）+ S-01 = **25**（P3-5 勘误：原计 26，逐行实数 25）
- sidecar/输入装配：A-02/09/14/22 + R-11/13 + O-04 = 7
- 守卫/基础设施/写管线：A-05/16/17/21 + R-10/14 + A-10/12/13/18/19（真源/机制）= 11
- **合计 43 个表行组件 + §4 治理家族（23 个 kill switch 计 1 组）= 44，全部映射**；示范接线 1 处（R-03 L2，验收要求的最小证明）。
