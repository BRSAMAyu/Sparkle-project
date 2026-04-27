# Signal-to-Action Spine — 进度追踪

> **文档类型**: Milestone/Step 状态追踪 + 差距分析
> **更新日期**: 2026-04-27
> **方案完全体**: `SPARKLE_SIGNAL_TO_ACTION_SPINE_2026-04-27.md`

---

## 总览

| Milestone | 状态 | 完成度 | 最后更新 |
|-----------|------|--------|---------|
| M1: 控制链路最小可运行 | ✅ 完成 | 5/5 steps | 2026-04-27 |
| M2: 资料闭环最小可运行 | ✅ 完成 | 3/3 steps | 2026-04-27 |
| M3: 错因驱动策略改变 | ✅ 完成 | 3/3 steps | 2026-04-27 |

---

## Milestone 1: 控制链路最小可运行

**目标**: 证明 Aurora 判断能改变任务卡

### Steps

| Step | 描述 | 状态 | 关键文件 | 审查 |
|------|------|------|---------|------|
| 1 | CausalTrace 骨架 + 记录基础设施 | ✅ DONE | `signals/types.py`, `signals/causal_trace_store.py` | Opus C1-C4 修复 |
| 2 | ActionableSignal 固定规则（任务超时） | ✅ DONE | `signals/task_timeout_detector.py` | Opus W2 修复 |
| 3 | ExecutionDirective 硬约束任务生成 | ✅ DONE | `signals/policy_engine.py`, `signals/directive_applier.py`, `planning_workflow.py` | Opus C2+C3 修复 |
| 4 | DirectiveApplicationAudit 验证闭环 | ✅ DONE | `signals/directive_applier.py::DirectiveAuditor` | Opus 确认审计真实验证 |
| 5 | UserVisibleReceipt 用户可感知回执 | ✅ DONE | `signals/spine_orchestrator.py`, `api/v1/aurora.py` | Opus C4 修复 |

### 验收标准 (E1)

- [x] 连续 2 张任务卡超时 → 产生 ActionableSignal: task_granularity_fit=too_large
- [x] 产生 PolicyDecision: recover_execution_rhythm
- [x] 产生 ExecutionDirective: max_task_duration_min <= 25
- [x] 下一张任务卡 duration <= 25
- [x] DirectiveApplicationAudit.applied = true
- [x] 用户看到 Receipt

---

## Milestone 2: 资料闭环最小可运行

**目标**: 证明资料不是 RAG 噪声，而是可控上下文资产

### Steps

| Step | 描述 | 状态 |
|------|------|------|
| 1 | SourceAsset + SourceSlice 模型 | ✅ 复用现有 DocumentChunk |
| 2 | RetrievalDirective + ContextPlan | ✅ MaterialSignalDetector + PolicyEngine 扩展 |
| 3 | ContextReceipt 前端展示 | ✅ 已有 ContextReceiptBar，spine override 注入 |

### 验收标准 (E3)

- [x] 上传课件 → 挂载到知识节点
- [x] 按需调用 → 不加载完整课件
- [x] ContextReceipt 显示用了什么/没用什么/为什么
- [x] Spine material directive → retrieval_mode override
- [x] PolicyEngine 扩展了 material_utilization 规则

---

## Milestone 3: 错因驱动策略改变

**目标**: 证明学习结果能改变后续策略

### Steps

| Step | 描述 | 状态 |
|------|------|------|
| 1 | MistakeSignal 检测 | ✅ DONE — `signals/mistake_signal.py` |
| 2 | KnowledgeStatePatch + PolicyDecision 联动 | ✅ DONE — PolicyEngine `knowledge_transfer/transfer_failure` 规则 |
| 3 | TaskCard regeneration 硬约束 | ✅ DONE — avoid_new_chapter + worked_example_then_drill |

### 验收标准 (E2)

- [x] 连续 3 次同题出错 → transfer_failure = true
- [x] avoid_new_chapter = true
- [x] required_task_type = worked_example_then_drill
- [x] 不能生成新章节任务

---

## P0-1: FirstMinuteSnapshot / ExamRescueDetector

**目标**: 新用户 60 秒内感到被理解

### Steps

| Step | 描述 | 状态 |
|------|------|------|
| 1 | ExamRescueDetector 正则匹配（deadline + baseline + subject） | ✅ DONE — `signals/exam_rescue_detector.py` |
| 2 | FirstMinuteSnapshot 数据结构 | ✅ DONE |
| 3 | PolicyEngine exam_rescue 规则 | ✅ DONE — `goal_mode/exam_rescue_detected` |
| 4 | 中文相对日期提取（明天/后天/下周） | ✅ DONE — Opus C1 修复 |
| 5 | 考试意图门控（防止非考试用户误入） | ✅ DONE — Opus C2 修复 |
| 6 | 英文学科名支持 | ✅ DONE — Opus C3 修复 |

### 验收标准 (E4)

- [x] "我 7 天后计网考试，零基础，想先别挂" → exam_rescue 判断
- [x] 不要求先完成完整表单
- [x] 给出低成本下一步（上传资料或诊断）
- [x] 给出可纠正选项
- [x] E2E pipeline: Detector → Signal → PolicyEngine → result

---

## P0-2: TimeContext + StaleStateGuard

**目标**: 用户离开后回来，系统不能假装时间没过去

### Steps

| Step | 描述 | 状态 |
|------|------|------|
| 1 | TimeContext 数据结构 | ✅ DONE — `signals/stale_state_guard.py` |
| 2 | StaleStateGuard 检测逻辑 | ✅ DONE — 60 分钟阈值 |
| 3 | TimeDeltaPacket 恢复选项 | ✅ DONE — 4 个标准选项 |

### 验收标准 (E5)

- [x] 用户开始任务后离开 2 小时 → TimeDeltaPacket
- [x] 系统询问任务状态
- [x] 提供选项：做完了 / 做一半 / 没开始 / 换小任务

---

## P0-3: ActionableStatePacket v1

**目标**: 下游模块消费结构化状态，不是自然语言 prompt

### Steps

| Step | 描述 | 状态 |
|------|------|------|
| 1 | ActionableStatePacketBuilder | ✅ DONE — `signals/state_packet_builder.py` |
| 2 | 从信号构建 top_states | ✅ DONE |
| 3 | 从 directive 构建 risk_flags | ✅ DONE |
| 4 | 瓶颈检测 | ✅ DONE |
| 5 | Goal frame 填充 | ✅ DONE |

### 验收标准

- [x] task_generator 和 response layer 消费结构化字段
- [x] 状态包从活跃信号和 directive 构建
- [x] 序列化/反序列化正确

---

## P1 总览

| P1 Item | 状态 | 完成度 | 最后更新 |
|---------|------|--------|---------|
| P1-1 AchievementReinforcementConsumer | ✅ 完成 | 6 tests | 2026-04-27 |
| P1-2 AuroraWakeEligibility | ✅ 完成 | 7 tests | 2026-04-27 |
| P1-3 PredictedReplyOption Engine | ✅ 完成 | 5 steps / 8 tests | 2026-04-27 |
| P1-4 RecallOpportunity | ✅ 完成 | 10 tests | 2026-04-27 |
| P1-5 SparkleSelfModel | ✅ 完成 | 6 steps / 9 tests | 2026-04-27 |
| P1-6 CommunitySignal v1 | ✅ 完成 | 9 tests | 2026-04-27 |

---

## 当前测试覆盖

600/600 tests passing:
- M1 控制链路: 12 tests
- M2 资料闭环: 5 tests
- M3 错因驱动: 4 tests
- P0-1 FirstMinuteSnapshot: 14 tests
- P0-2 StaleStateGuard: 6 tests
- P0-3 ActionableStatePacket: 7 tests
- P0-3 Task Card 8-Field Protocol: 9 tests (why_this_task + materials_protocol + stuck_protocol + updates_after_completion)
- P0-1b Quality Cross-Check: 6 tests (Rule A/B/C + no context + momentum_stalled unaffected)
- P1-1 AchievementReinforcement: 6 tests
- P1-2 AuroraWakeEligibility: 7 tests
- P1-3 PredictedReplyOption: 8 tests
- P1-4 RecallOpportunity: 10 tests
- P1-5 SparkleSelfModel: 9 tests
- P1-6 CommunitySignal: 9 tests
- PolicyEngine rules: 6 tests
- P2 Spine integration: 17 tests
- P3 Production wiring: 5 tests
- Layer 3 SignalRanker: 11 tests (9 standalone + 2 integration)
- Layer 4 StateRegister: 21 tests (16 standalone + 5 integration/edge)
- Layer 6 ResponseDirective: 7 tests (5 standalone + 2 integration)
- Layer 6 NotificationDirective: 8 tests (6 standalone + 2 integration)
- Layer 6 RetrievalDirective: 4 tests
- Layer 6 PlanDirective: 8 tests (6 standalone + 2 integration)
- Layer 6 ModelWriteDirective: 8 tests (7 standalone + 1 integration)
- Layer 6 UXDirective: 14 tests (11 standalone + 1 integration + 2 edge)
- Opus review regression tests: 3 tests (trace IDs, material_underutilized, ModelWriteEntry.from_dict)
- Layer 8 OutcomeRecorder: 10 tests (7 standalone + 2 integration + 1 serialization)
- Decision Realization Metrics: 8 tests (6 standalone + 2 integration)
- P4 Production directive consumption: 12 tests (3 prompt + 4 plan + 1 model-write + 1 retrieval + 1 retrieval-pipeline + 1 UX + 1 notification)
- P5 Causal Audit Timeline API: 8 tests (3 timeline CRUD + 1 timeline format + 1 state packet + 1 empty state + 1 metrics + 1 directive-by-id)
- E2E 7-Day Exam Sprint Acceptance: 6 tests (Day 0 rescue + Day 1-2 timeout + Day 3-4 error strategy + full causal trace + user correction + momentum stalled)
- v2.0 Closed Loops: 74+ tests (skill lifecycle 7, community loops 9, core session 9, goal type 8, growth chronicle 9, policy analytics 8, recall notification 7, relationship model 8, quality cross-check 6, ExamSprintPolicy 15, SourceTrayIntegration 6, soft difficulty + momentum 4+)
- P2-8 Notification Integration: 7 tests (build+store, cooldown, independent triggers, pre-exam template, task missed recovery, preference schema, Celery task registration)
- v2.4 SourceEffectiveness: 6 tests (record effective/insufficient/mixed, sorted retrieval, low-effect filter, trial threshold)
- v2.4 StrategyBelief Consumption: 4 tests (bias applied, not applied when effective, not applied low evidence, no beliefs)
- v2.4 PolicyExperiment Full Loop: 3 tests (create+trial, promotion after conclusion, shadow heuristic)
- v2.4 Skill Auto-Deprecation: 2 tests (no stale, with stale skill)
- v2.4 Belief Persistence: 2 tests (persist+load, empty on new user)
- v2.4 Outcome Integration: 2 tests (outcome→source effectiveness, outcome→experiment trial)
- v2.5 E2E Chain Repair: 7 tests (chronicle injection, fatigue injection, crisis injection, no-chronicle, correction→self_model, concurrency guard, metrics TTL)
- v2.6 GoalWorldGraph: 5 tests (create graph, update mastery, find bottleneck, suggest focus, add dependency)
- v2.6 MultiGoalArbitration: 10 tests (single goal, deadline urgent, bottleneck severity, user override, paused, conflicts, redis register/get, spine integration)
- v2.6 Spine Goal Integration: 3 tests (get graph none, focus empty, arbitrate no goals)
- v2.7 E2E Test Matrix: 10 tests (#4 no retrieval + receipt, #5 user requests source, #8 multi-goal conflict, #9 Redis degraded, #10 snapshot rehydration, #11 fatigue guard, #12 crisis mode)
- v2.5 E2E Chain Repair: 7 tests (chronicle injection, fatigue injection, crisis injection, no-chronicle, correction→self_model, concurrency guard, metrics TTL)

---

## Layer 6: RetrievalDirective

**目标**: 控制资料、RAG、知识星图如何进入上下文

### 核心功能

| 功能 | 说明 |
|------|------|
| `RetrievalDirective` 数据结构 | retrieval_mode / source_scope / must_load / may_load / do_not_load / token_budget / pollution_guard |
| `PolicyEngine.build_retrieval_directive()` | 从 PolicyDecision + signal 构建资料指令 |

### 触发映射

| 信号 | retrieval_mode | source_scope | pollution_guard |
|------|---------------|-------------|----------------|
| material_utilization/material_underutilized | targeted_source_rag | user_selected | strict |
| goal_mode/exam_rescue | task_bound_graph_rag | task_bound | strict |
| knowledge_transfer/transfer_failure | task_bound_graph_rag | task_bound | strict |
| recall_needed/pre_exam_silence | task_bound_graph_rag | task_bound | permissive |

### 验收标准

- [x] RetrievalDirective 包含 retrieval_mode / source_scope / pollution_guard / reason_for_user
- [x] material_underutilized → targeted_source_rag
- [x] exam_rescue → task_bound_graph_rag
- [x] transfer_failure → task_bound_graph_rag
- [x] 非 retrieval 相关信号 → 不生成 RetrievalDirective
- [x] 序列化正确

---

## Layer 6: NotificationDirective

**目标**: 8 层架构第 6 层 — 控制推送通知：是否允许、渠道、静默时间、触发条件、频率

### 核心功能

| 功能 | 说明 |
|------|------|
| `NotificationDirective` 数据结构 | allowed / channel / respect_quiet_hours / trigger / message_strategy / max_frequency |
| `PolicyEngine.build_notification_directive()` | 从 PolicyDecision + signal 构建通知指令 |
| `SpineOrchestrator.get_notification_directive()` | 供 notification service 消费 |

### 触发映射

| 信号 | trigger | message_strategy | max_frequency |
|------|---------|-----------------|---------------|
| recall_needed/undigested_material | undigested_material | low_effort_next_step | 1_per_day |
| recall_needed/task_not_started | first_task_not_started | low_effort_next_step | 1_per_day |
| recall_needed/task_missed | task_missed | recovery_offer | 2_per_day |
| recall_needed/pre_exam_silence | pre_exam_silence | quick_review_offer | 2_per_day |
| goal_mode/exam_rescue | exam_rescue_urgent | quick_review_offer | 2_per_day |

### 验收标准

- [x] NotificationDirective 包含 allowed / channel / respect_quiet_hours / trigger / message_strategy / max_frequency
- [x] recall_needed/undigested_material → trigger=undigested_material, max_frequency=1_per_day
- [x] recall_needed/task_missed → trigger=task_missed, message_strategy=recovery_offer
- [x] recall_needed/pre_exam_silence → trigger=pre_exam_silence, requires_user_confirmation=True
- [x] 非 recall_needed / 非 goal_mode 信号 → 不生成 NotificationDirective
- [x] goal_mode/exam_rescue → exam_rescue_urgent trigger
- [x] SpineOrchestrator pipeline 自动存储和读取
- [x] 序列化正确

---

## P2: SpineOrchestrator Full Wiring

**目标**: 所有 P0+P1 模块通过 SpineOrchestrator 统一入口接入 Signal → PolicyEngine → Directive → Trace 管线

### Integration Points

| Module | SpineOrchestrator 方法 | 状态 |
|--------|----------------------|------|
| ExamRescueDetector | `on_first_message()` | ✅ WIRED |
| StaleStateGuard | `on_user_return()` | ✅ WIRED |
| ActionableStatePacketBuilder | `build_state_packet()` | ✅ WIRED |
| SpineReplyOptionEngine | `generate_reply_options()` / `process_reply_selection()` | ✅ WIRED |
| SparkleSelfModelService | `record_strategy_outcome()` | ✅ WIRED |
| CommunitySignalDetector | `on_community_cohort_data()` / `on_community_resource_data()` | ✅ WIRED |
| AuroraWakeJudge | `check_aurora_wake()` | ✅ WIRED |
| AchievementReinforcementConsumer | `on_achievement_event()` | ✅ WIRED (prior) |
| RecallOpportunityDetector | `on_recall_check()` | ✅ WIRED (prior) |

---

## Layer 3: SignalRanker

**目标**: 8 层架构第 3 层 — 信号排序与冲突解决

### 排序维度

| 维度 | 权重 | 说明 |
|------|------|------|
| confidence | 0.4 | 信号可信度 |
| urgency (priority) | 0.3 | high=1.0 / medium=0.5 / low=0.2 |
| tier_inverse | 0.3 | 优先级层级越低分越高 |

### 9 层仲裁优先级

| Tier | 内容 | state_key |
|------|------|-----------|
| 1 | 安全 / 隐私 / 用户硬边界 | safety_boundary, user_correction |
| 2 | deadline 生存策略 | deadline_pressure, exam_rescue, recall_needed |
| 3 | 用户显式目标 | goal_mode |
| 4 | 直接行为证据 | task_granularity_fit, material_utilization |
| 5 | 学习结果与错因 | knowledge_transfer, community_cohort_pattern |
| 6 | 资料与知识星图 | retrieval_context, community_resource_recommendation |
| 7 | 成就 / 动机 | growth_momentum |
| 9 | 默认 | (其他) |

### 冲突规则

| 高优先级 | 低优先级 | 结果 |
|---------|---------|------|
| task_granularity_fit | growth_momentum | task_granularity_fit wins |
| knowledge_transfer | growth_momentum | knowledge_transfer wins |
| recall_needed | growth_momentum | recall wins |

### 验收标准

- [x] 空信号列表 → 空 result
- [x] 单信号 → 直接 ranked
- [x] exam_rescue (tier 2) 排在 growth_momentum (tier 7) 之前
- [x] max_signals 限制生效
- [x] 冲突检测 + 抑制正确
- [x] 综合评分排序正确
- [x] SpineOrchestrator.rank_signals() 委托到 SignalRanker

---

## Layer 4: StateRegister

**目标**: 8 层架构第 4 层 — 每用户持久化状态寄存器

### 核心功能

| 功能 | 说明 |
|------|------|
| `upsert_from_signal()` | 从信号更新或插入状态（高置信度覆盖） |
| `get_active_states()` | 获取所有非过期状态（按置信度排序） |
| `add_counter_evidence()` | 为状态添加反证 |
| `remove_state()` | 移除指定状态 |
| `expire_stale()` | 清理所有过期状态 |
| `clear_scope()` | 按作用域批量清除 |

### 存储格式

- `spine:state:{user_id}:{state_key}` → JSON StateEntry（TTL 自动过期）
- `spine:state_index:{user_id}` → Redis Set（活跃 state_key 索引）

### 验收标准

- [x] Signal → StateEntry 持久化
- [x] 高置信度信号覆盖低置信度状态（低置信度不覆盖 value）
- [x] TTL 过期自动清理
- [x] counter_evidence 可追加（上限 20 条）
- [x] scope 批量清除（turn/session/sprint）
- [x] Iron Rule 7: scope TTL clamp（turn ≤1h, sprint ≤168h, goal ≤720h）
- [x] 证据列表上限 20 条
- [x] StateEntry 完整字段（11 个字段匹配 Final Spec Section 4.1）
- [x] 21 个 state_key 的 can_affect 映射
- [x] SpineOrchestrator.on_task_completed 和 _run_signal_pipeline 自动持久化
- [x] 反序列化正确
- [x] Opus review: C-1/C-3/C-4 已修复

---

## Layer 6: ResponseDirective

**目标**: 8 层架构第 6 层 — 控制回复层的语气、长度、确认、避免项

### 核心功能

| 功能 | 说明 |
|------|------|
| `ResponseDirective` 数据结构 | tone / length / must_acknowledge / avoid / include_user_options |
| `PolicyEngine.build_response_directive()` | 从 PolicyDecision.soft_biases 派生 ResponseDirective |
| `SpineOrchestrator.get_response_directive()` | 供 response layer 消费 |

### 语气映射

| 信号 | tone | avoid |
|------|------|-------|
| task_granularity_fit | direct_but_reassuring | generic_encouragement |
| knowledge_transfer | encouraging_diagnostic | generic_encouragement, pressure_language |
| goal_mode/exam_rescue | calm_urgent | generic_encouragement |
| growth_momentum (status_band) | — 不生成 — | — |

### 验收标准

- [x] ResponseDirective 包含 tone / length / must_acknowledge / avoid / include_user_options
- [x] task_granularity_fit → tone=direct_but_reassuring, must_acknowledge=["recent_overrun"]
- [x] exam_rescue → tone=calm_urgent, must_acknowledge=["exam_situation"]
- [x] transfer_failure → tone=encouraging_diagnostic, avoid=["generic_encouragement", "pressure_language"]
- [x] growth_momentum (status_band) → 不生成 ResponseDirective
- [x] SpineOrchestrator pipeline 自动存储和读取
- [x] 序列化/反序列化正确

---

## Layer 6: PlanDirective

**目标**: 8 层架构第 6 层 — 控制计划和重规划

### 核心功能

| 功能 | 说明 |
|------|------|
| `PlanDirective` 数据结构 | plan_action / scope / constraints |
| `PolicyEngine.build_plan_directive()` | 从 signal 构建 PlanDirective |
| `SpineOrchestrator.get_plan_directive()` | 供 planning service 消费 |

### 触发映射

| 信号 | plan_action | scope | 约束 |
|------|------------|-------|------|
| recent_task_too_large | local_replan | next_48h | do_not_rebuild + insert_recovery |
| transfer_failure | local_replan | current_sprint | avoid_new_chapter + insert_practice |
| exam_rescue_detected | full_replan | current_sprint | preserve_deadline + prefer_high_yield |
| momentum_stalled | local_replan | next_48h | do_not_rebuild + insert_easy_win |
| task_missed | insert_task | next_48h | recovery_task + adjust_deadlines |

### 验收标准

- [x] task_granularity_fit → local_replan with recovery task
- [x] transfer_failure → local_replan with practice task
- [x] exam_rescue → full_replan with high yield
- [x] momentum_stalled → local_replan with easy win
- [x] task_missed → insert_task
- [x] 非匹配信号 → None
- [x] 序列化/反序列化正确
- [x] Spine pipeline 自动存储

---

## Layer 6: ModelWriteDirective

**目标**: 8 层架构第 6 层 — 控制写入哪个模型、写入多深

### 核心功能

| 功能 | 说明 |
|------|------|
| `ModelWriteEntry` 数据结构 | target_model / claim / scope / confidence / needs_user_confirmation / ttl |
| `ModelWriteDirective` 数据结构 | writes 列表（上限 5 条） |
| `PolicyEngine.build_model_write_directive()` | 从 signal 构建 ModelWriteDirective |
| `SpineOrchestrator.get_model_write_directive()` | 供 state_aggregator 消费 |

### 写入映射

| 信号 | writes |
|------|--------|
| recent_task_too_large | user_state + sparkle_self_model (degraded) |
| transfer_failure | user_state (knowledge consolidation) |
| exam_rescue_detected | user_state (needs confirmation) |
| momentum_high | sparkle_self_model (encouragement effective) |

### 验收标准

- [x] task_timeout → 2 writes, self_model has degraded confidence
- [x] transfer_failure → 1 write (user_state)
- [x] exam_rescue → 1 write needing user confirmation
- [x] momentum_high → self_model write
- [x] 非匹配信号 → None
- [x] writes 列表上限 5 条
- [x] ModelWriteEntry.from_dict 一致性
- [x] 序列化/反序列化正确
- [x] Spine pipeline 自动存储

---

## Layer 6: UXDirective

**目标**: 8 层架构第 6 层 — 控制状态带、回执、Aurora 可见性

### 核心功能

| 功能 | 说明 |
|------|------|
| `UXDirective` 数据结构 | status_band_state / show_context_receipt / show_strategy_receipt / predicted_reply_options / allow_full_aurora_wake |
| `PolicyEngine.build_ux_directive()` | 从 signal 构建 UXDirective，通过 reply engine 填充 predicted_reply_options |
| `SpineOrchestrator.get_ux_directive()` | 供 UX layer 消费 |

### 状态带映射

| 信号 | status_band_state | 说明 |
|------|-------------------|------|
| recent_task_too_large | risk_detected | 风险状态带 + 策略回执 |
| transfer_failure | risk_detected | 风险状态带 + 策略回执 |
| exam_rescue_detected | strategy_active | 策略激活 + Aurora 可唤醒 |
| momentum_high | milestone | 里程碑 |
| momentum_stalled | risk_detected | 风险 |
| undigested_material / task_not_started | normal | 上下文回执 |
| task_missed / pre_exam_silence | risk/strategy | 各有针对性 |
| material_underutilized | normal | 上下文回执 |
| cohort_mistake / shared_resource | normal | 内联提示 |

### 验收标准

- [x] task_timeout → risk_detected + strategy receipt
- [x] exam_rescue → strategy_active + aurora wake allowed
- [x] momentum_high → milestone
- [x] momentum_stalled → risk_detected
- [x] undigested_material → normal + context receipt
- [x] material_underutilized → normal + context receipt
- [x] pre_exam_silence → strategy_active
- [x] cohort_mistake → normal
- [x] predicted_reply_options 从 reply engine 填充（requires_user_confirmation）
- [x] 所有 claim 都有 UX 映射（无遗漏）
- [x] CausalTrace 包含所有二级 directive ID
- [x] 序列化/反序列化正确
- [x] Spine pipeline 自动存储

---

## Layer 8: Outcome & Causal Attribution

**目标**: 8 层架构第 8 层 — 记录干预结果，执行最小因果归因

### 核心功能

| 功能 | 说明 |
|------|------|
| `OutcomeRecord` 数据结构 | intervention / expected_outcome / actual_outcome / attribution / attribution_confidence / new_hypothesis / next_policy_suggestion |
| `OutcomeRecorder` | 记录干预结果，执行固定规则归因 |
| `SpineOrchestrator.record_outcome()` | 供外部调用记录干预结果 |

### 归因规则

| expected_outcome | effective 条件 | insufficient 条件 | 下一策略建议 |
|-----------------|---------------|------------------|------------|
| task_started_and_completed | completed=True | started=True, completed=False | evaluate_knowledge_barrier |
| user_response | user_responded=True | user_responded=False | reduce_frequency |
| behavioral_change | behavior_changed=True | behavior_changed=False | escalate_or_try_different |

### 验收标准

- [x] OutcomeRecord 包含完整归因字段
- [x] task completed → effective attribution (confidence ≥ 0.7)
- [x] task started but not completed → insufficient + hypothesis
- [x] user responded → effective
- [x] user not responded → insufficient + reduce_frequency
- [x] behavior changed → effective
- [x] unknown expected_outcome → inconclusive
- [x] unexpected outcome pattern → inconclusive with low confidence
- [x] OutcomeRecorder Redis 存储和检索
- [x] SpineOrchestrator 委托正确

---

## Decision Realization Score — 10 核心指标

**目标**: 验证 AI 判断是否真正改变了系统行动，并改善了结果 (Final Spec Section 22)

### 核心指标

| 指标 | 含义 | 公式 |
|------|------|------|
| signal_to_state_rate | 高价值信号进入状态的比例 | signals_entered_state / signals_generated |
| state_to_policy_rate | 状态触发策略裁决的比例 | policies_evaluated / signals_entered_state |
| policy_to_directive_rate | 策略变成 directive 的比例 | directives_generated / policies_evaluated |
| directive_application_rate | directive 被下游执行的比例 | directives_applied / directives_generated |
| output_change_rate | 执行后输出真正改变的比例 | outputs_changed / directives_applied |
| user_visible_receipt_rate | 用户感知到改变的比例 | receipts_shown / directives_applied |
| outcome_feedback_rate | 改变后记录结果的比例 | outcomes_recorded / directives_applied |
| intervention_effectiveness | 干预可能有效的比例 | effective_attributions / outcomes_recorded |
| retraction_rate | 系统撤销错误判断的比例 | retractions / receipts_shown |
| orphan_signal_count | 发出但无人消费的信号数量 | gauge (not ratio) |

### 验收标准

- [x] 10 个指标定义完整
- [x] SpineMetricsCollector 支持 increment / get_counter / snapshot / reset
- [x] Pipeline 自动采集：signal_generated / signal_entered_state / policy_evaluated / directive_generated / receipt_shown
- [x] apply_directive_to_task_spec 采集 directive_applied / outputs_changed
- [x] record_outcome 采集 outcomes_recorded / effective_attributions
- [x] handle_user_receipt_action 采集 retractions / outcomes (confirm/dismiss)
- [x] snapshot() 计算所有比例（零分母安全）
- [x] orphan_signal 在 policy 不匹配时递增
- [x] Opus review C1-C3 已修复

---

## P3: Production Event Handler Wiring

**目标**: SpineOrchestrator 方法接入生产代码的事件处理器

### Production Wiring Points

| Production Module | SpineOrchestrator 方法 | 状态 |
|------------------|----------------------|------|
| `achievement_event_consumer._handle_achievement_unlocked()` | `on_achievement_event()` | ✅ WIRED |
| `orchestrator.process_stream()` (first message) | `on_first_message()` | ✅ WIRED |
| `orchestrator.process_stream()` (user return ≥60min) | `on_user_return()` | ✅ WIRED |

### 验收标准

- [x] achievement unlocked → spine.on_achievement_event() 调用
- [x] 首条消息（conversation empty）→ spine.on_first_message() 检测考试救援
- [x] 用户返回（elapsed ≥60min）→ spine.on_user_return() 检测陈旧状态
- [x] 所有 spine 调用包裹在 try/except 中，不影响主流程
- [x] SpineOrchestrator 实例化使用 self.redis（orchestrator）/ cache_service.redis（consumer）

---

## P4: Production Directive Consumption Wiring

**目标**: Spine 输出的 7 类 Directive 被下游生产模块消费，驱动真实行为变化

### Directive Consumption Map

| Directive Type | Consumer Module | 状态 |
|---------------|----------------|------|
| ExecutionDirective | `planning_workflow.py` (task spec modification) | ✅ WIRED |
| ResponseDirective | `orchestrator_production.py` → `prompts.py` (tone/length/avoid injection) | ✅ WIRED |
| PlanDirective | `planning_workflow.py` (recovery/practice/easy-win task insertion) | ✅ WIRED |
| NotificationDirective | `notification_service` (push control) | ✅ STORED (Redis) |
| RetrievalDirective | `orchestrator_production.py` → RAG (top_k/depth by pollution_guard) | ✅ WIRED |
| UXDirective | frontend state (status band / receipt display) | ✅ STORED (Redis) |
| ModelWriteDirective | `spine_orchestrator._apply_model_writes()` → Redis user state | ✅ WIRED |

### 验收标准

- [x] ResponseDirective: tone/length/avoid/must_acknowledge 注入 build_system_prompt
- [x] PlanDirective: insert_recovery_task / insert_practice_task / insert_easy_win 任务前插
- [x] orchestrator_production 使用 get_response_directive() 独立获取
- [x] planning_workflow 使用 get_plan_directive() 独立获取
- [x] 所有消费点 try/except 包裹，spine 故障不影响主流程
- [x] Opus review: 修复 None-safe tasks 访问、移除冗余 Redis 读取、添加 debug logging
- [x] NotificationDirective: Redis store/fetch for notification scheduler consumption
- [x] RetrievalDirective: RAG pipeline integration (top_k/depth adjusted by pollution_guard/token_budget)
- [x] UXDirective: Redis store/fetch for frontend consumption
- [x] ModelWriteDirective: auto-apply high-confidence claims to Redis user state (confidence >= 0.7, no user_confirmation)

**目标**: 成就回流 — achievement → growth momentum → tone/nudge/challenge 调整

### Steps

| Step | 描述 | 状态 |
|------|------|------|
| 1 | AchievementMomentum 数据模型 | ✅ DONE |
| 2 | compute_momentum 动量计算（unlock+streak+progress 三因子） | ✅ DONE |
| 3 | momentum >= 0.7 → momentum_high signal（priority=low） | ✅ DONE |
| 4 | momentum <= 0.3 + in_progress → momentum_stalled signal（priority=medium） | ✅ DONE |
| 5 | 中间动量不生成信号（无行动意义） | ✅ DONE |
| 6 | 禁止写长期人格，scope=current_sprint | ✅ DONE |

### 验收标准

- [x] 成就解锁 → compute_momentum → ActionableSignal(growth_momentum)
- [x] 高动量 signal priority=low（不压过错误/超时信号）
- [x] 停滞 signal priority=medium（值得注意但不紧急）
- [x] 中等动量 → 不生成 signal
- [x] scope=current_sprint，不写长期人格
- [x] momentum_score 序列化正确

---

## P1-4: RecallOpportunity

**目标**: 主动召回 — 4 种触发条件下的目标导向召回

### Steps

| Step | 描述 | 状态 |
|------|------|------|
| 1 | RecallTrigger 数据模型 | ✅ DONE |
| 2 | undigested_material 检测（上传未诊断） | ✅ DONE |
| 3 | task_not_started 检测（1h 未启动） | ✅ DONE |
| 4 | task_missed 检测（错过 deadline） | ✅ DONE |
| 5 | pre_exam_silence 检测（考前 48h 沉默） | ✅ DONE |
| 6 | RecallTrigger → ActionableSignal 转换 | ✅ DONE |
| 7 | 冷却期机制 | ✅ DONE |

### 验收标准

- [x] 上传资料未诊断 → trigger(undigested_material)
- [x] 所有资料已诊断 → 不 trigger
- [x] 任务超 1h 未启动 → trigger(task_not_started)
- [x] 任务已启动 → 不 trigger
- [x] 任务错过 deadline → trigger(task_missed, urgency=high)
- [x] 考前 48h + 沉默 5h → trigger(pre_exam_silence)
- [x] 考前但活跃 → 不 trigger
- [x] to_actionable_signal 转换正确
- [x] 冷却期按 trigger_type 区分

---

## P1-3: PredictedReplyOption Engine

**目标**: 为确认问题生成语义快捷回答

### Steps

| Step | 描述 | 状态 |
|------|------|------|
| 1 | PredictedReplyOption + PredictedReplyQuestion 数据模型 | ✅ DONE |
| 2 | 4 类问题模板（事实确认/假设确认/策略选择/关系边界） | ✅ DONE |
| 3 | 每组选项强制含"都不对，我解释一下" | ✅ DONE |
| 4 | 用户选择 → 状态补丁处理 | ✅ DONE |
| 5 | Opus 审查：重命名 SpineReplyOptionEngine，修复 state_patch 类型 | ✅ DONE |

### 验收标准

- [x] 每组选项都含自由输入选项
- [x] 至少一个反驳选项
- [x] process_user_selection 返回状态补丁
- [x] 无模板的 state_key 返回 None

---

## P1-5: SparkleSelfModel

**目标**: 系统建模自己的策略效果

### Steps

| Step | 描述 | 状态 |
|------|------|------|
| 1 | SelfModelClaim 数据模型 | ✅ DONE |
| 2 | StrategyOutcome 数据模型 | ✅ DONE |
| 3 | SparkleSelfModelService（Redis 持久化） | ✅ DONE |
| 4 | 归因分析 (_attribute) | ✅ DONE |
| 5 | 置信度调整 + 反证记录 | ✅ DONE |
| 6 | 用户纠正记录 | ✅ DONE |

### 验收标准

- [x] 记录策略假设（claim）
- [x] 记录策略结果（outcome）
- [x] 归因分析：effective / completed_but_resented / insufficient / inconclusive
- [x] 置信度随结果调整
- [x] 用户纠正记录为高置信度 claim
- [x] Claims 列表有上限（50）

---

## 差距分析：距离完全体愿景

### 已有的基础设施（可复用）

| 系统 | 文件 | 状态 |
|------|------|------|
| EventBus | `backend/app/core/event_bus.py` | ✅ 运行中，支持 Redis Streams |
| AchievementEngine | `backend/app/services/achievement_engine.py` | ✅ 19 event types |
| TaskService | `backend/app/services/task_service.py` | 需确认超时检测 |
| PlanningWorkflow | `backend/app/orchestration/planning_workflow.py` | 需确认 directive 接入点 |
| AuroraRuntimeV1 | `backend/app/aurora/runtime_v1/` | ✅ 决策循环已运行 |
| Orchestrator | `backend/app/orchestration/orchestrator.py` | FSM 主控 |
| GalaxyService | `backend/app/services/galaxy_service.py` | 知识星图 |

### 已完成的 P0/P1 核心对象

| 对象 | 状态 | 关键文件 |
|------|------|---------|
| ActionableSignal | ✅ 完成 | `signals/types.py` |
| ActionableStatePacket | ✅ 完成 | `signals/types.py`, `signals/state_packet_builder.py` |
| PolicyDecision | ✅ 完成 | `signals/types.py`, `signals/policy_engine.py` |
| ExecutionDirective | ✅ 完成 | `signals/types.py`, `signals/policy_engine.py` |
| DirectiveApplicationAudit | ✅ 完成 | `signals/directive_applier.py` |
| UserVisibleReceipt | ✅ 完成 | `signals/spine_orchestrator.py` |
| CausalTrace | ✅ 完成 | `signals/types.py`, `signals/causal_trace_store.py` |
| PredictedReplyOption | ✅ 完成 | `signals/predicted_reply_options.py` |
| SparkleSelfModel | ✅ 完成 | `signals/self_model.py` |
| AchievementMomentum | ✅ 完成 | `signals/achievement_reinforcement.py` |
| RecallTrigger | ✅ 完成 | `signals/recall_opportunity.py` |
| SignalRanker + RankingResult | ✅ 完成 | `signals/signal_ranker.py` |
| StateRegister | ✅ 完成 | `signals/state_register.py` |
| StateEntry | ✅ 完成 | `signals/types.py` |
| ResponseDirective | ✅ 完成 | `signals/types.py`, `signals/policy_engine.py` |
| NotificationDirective | ✅ 完成 | `signals/types.py`, `signals/policy_engine.py` |
| PlanDirective | ✅ 完成 | `signals/types.py`, `signals/policy_engine.py` |
| ModelWriteDirective | ✅ 完成 | `signals/types.py`, `signals/policy_engine.py` |
| UXDirective | ✅ 完成 | `signals/types.py`, `signals/policy_engine.py` |
| OutcomeRecord | ✅ 完成 | `signals/types.py`, `signals/outcome_recorder.py` |
| SpineMetricsCollector | ✅ 完成 | `signals/spine_metrics.py` |

### 架构原则检查清单

- [x] 每个 Signal 都绑定一个用户可见变化
- [x] Directive 是结构化参数，不是 prompt 片段
- [x] Audit 验证输出是否满足约束
- [x] Receipt 短、具体、可纠正
- [x] 社群信号不直接写个人状态
- [x] 成就是不直接改长期人格

---

## P5: Causal Audit Timeline API

**目标**: REST API 端点暴露 spine 运行状态给前端和开发者

### API 端点

| Endpoint | 方法 | 说明 |
|----------|------|------|
| `/spine/timeline` | GET | 获取用户因果审计时间线 |
| `/spine/state` | GET | 获取当前 ActionableStatePacket |
| `/spine/metrics` | GET | 获取 Decision Realization Score 快照 |

### 验收标准

- [x] Timeline API 返回用户所有 trace（含 signal → policy → directive → audit → receipt 完整链路）
- [x] State API 返回当前 top_states + risk_flags + bottleneck + next_best_action
- [x] Metrics API 返回 10 个 DRS 指标
- [x] 空状态正确处理

---

## P6: E2E 7-Day Exam Sprint Acceptance Tests

**目标**: 从 Final Spec Section H 的 6 个神性场景中验证完整因果链

### 测试场景

| Test | 场景 | Iron Laws | 状态 |
|------|------|-----------|------|
| test_e2e_exam_sprint_full_causal_trace | 完整 Signal→Trace→Audit→Receipt→Outcome | 1-8 全覆盖 | ✅ PASS |
| test_e2e_exam_sprint_user_correction_flow | 用户纠正错误判断 | Iron Law 8, 用户主权 | ✅ PASS |
| test_e2e_exam_sprint_momentum_stalled_and_recovery | 成就停滞→策略调整 | growth_momentum→PlanDirective | ✅ PASS |

---

## P7: Closed Loop Completion (v1.1 Plan)

**目标**: 将 Causal Control Spine 从管道升级为活的闭环系统

### P7-1: Achievement → Adaptive Behavior (DONE)
- DirectiveApplier.apply_soft_difficulty() — soft_biases difficulty 微调
- prefer_easy_wins constraint — momentum_stalled 时 difficulty ≤ 2
- momentum_stalled hard constraints: max_task_duration_min=20, difficulty=low

### P7-2: CommunityDirective + SkillDirective (DONE)
- CommunityDirective — cohort_hint_shown / peer_context_mode / resource_quality_filter
- SkillDirective — skill_action (none/inject/extract/recommend) / extraction_trigger
- 9/9 directive types implemented, exported, pipeline-wired

### P7-3: Outcome → PolicyEffectLedger + Shadow Learning (DONE)
- PolicyEffectEntry — policy_key / attribution / user_feedback_signal / new_hypothesis
- OutcomeRecorder._write_policy_effect() — 自动写入 ledger
- _apply_shadow_learning() — 影子模式: 2次 insufficient + 看不懂 → switch_to_worked_example
- Pipeline: evaluate() 传入 recent_policy_effects

### 验收标准
- [x] Achievement momentum → task difficulty adjustment (soft + hard)
- [x] CommunityDirective: cohort_mistake → anonymous hint, resource → quality filter
- [x] SkillDirective: momentum_high → extract, transfer_failure → recommend
- [x] 9/9 directive types active
- [x] Outcome → PolicyEffectLedger auto-write
- [x] Shadow learning: repeated failure → strategy switch
- [x] Self-correction trace records outcome + hypothesis

---

## 当前状态: v2.7 COMPLETE — E2E Test Matrix Verified

**575/575 tests passing** | **9/9 directive types active** | **55+ public API exports** | **42 signal modules**

### v2.7 (E2E Test Matrix) — ALL 12 SCENARIOS COVERED
- [x] #1: First Minute Aha → exam rescue detection (test_e2e_exam_sprint_day0)
- [x] #2: 用户离开2h → Recovery Card (StaleStateGuard tests)
- [x] #3: 用户纠正 → 自我纠错 (test_e2e_exam_sprint_user_correction_flow)
- [x] #4: 普通概念问题 → 不调用课件 + ContextReceipt (TestE2EMatrixScenario4)
- [x] #5: 用户明确按课件讲 → SourceSlice retrieval (TestE2EMatrixScenario5)
- [x] #6: 七连胜 → Growth Card + 策略改变 (test_e2e_exam_sprint_momentum_stalled)
- [x] #7: 社区共性错因 → 任务模板改变 (CommunityLoopManager tests)
- [x] #8: 多目标冲突 → MultiGoalArbitration (TestE2EMatrixScenario8)
- [x] #9: Redis down → Degraded Mode (TestE2EMatrixScenario9)
- [x] #10: 老用户3月回归 → Snapshot Rehydration (TestE2EMatrixScenario10)
- [x] #11: 考前24h高频 → FatigueGuard (TestE2EMatrixScenario11)
- [x] #12: 零基础3天考试 → Crisis Mode (TestE2EMatrixScenario12)
- 10 new E2E integration tests added

### v2.6 (General Goal OS) — ALL COMPLETE
- [x] GoalWorldGraph — per-goal dependency/prerequisite graph with bottleneck detection + focus suggestions
- [x] MultiGoalArbitration — deadline/momentum/bottleneck priority scoring + time split + conflict detection
- [x] SpineOrchestrator delegation: get_goal_graph / get_goal_focus_suggestions / arbitrate_goals / register_goal
- [x] 23 new tests (5 graph CRUD/mastery/bottleneck/focus/dep + 10 arbitration + 3 spine integration)
- [x] User priority override (high/low/pause) respected in arbitration
- [x] Conflict detection: multiple_urgent_deadlines / bottleneck_goals / stalled_goals

### v2.9 (Production Wiring) — COMPLETE
- [x] ResponseDirective wired into real production path: orchestrator.py fetches → state.context_data → standard_workflow.py → build_system_prompt()
- [x] RetrievalDirective wired into RAG pipeline: overrides depth/mode in graph retrieval
- [x] GrowthChronicle wired: narrative summary fetched and injected into prompts
- [x] FatigueGuard wired: fatigue context injected when level >= medium
- [x] AuroraControlSignal envelope: unified pipeline output wrapping all directive IDs
- [x] AuroraAgendaItem type: structured multi-message Aurora session support
- [x] 5 new production wiring tests (directive serialization, chronicle injection, fatigue gating)
- [x] 600/600 tests passing

### v2.5 (E2E Chain Repair) — ALL COMPLETE
- [x] Chronicle → prompts injection: `build_system_prompt()` now accepts `spine_chronicle_summary` parameter
- [x] Fatigue/crisis → prompts injection: `build_system_prompt()` now accepts `spine_fatigue_context` parameter
- [x] `orchestrator_production.py` fetches chronicle (limit=3) and fatigue/crisis from Redis
- [x] `on_user_correction` → `self_model.record_user_correction()`: correction now flows to strategy learning
- [x] Pipeline concurrency guard: Redis NX lock prevents concurrent `_run_signal_pipeline` for same user
- [x] Metrics counter TTL: 7-day auto-expiry on each increment
- [x] Community cohort Celery task: `community_cohort_signal_task` + `scan_community_cohort_signals`
- [x] StateRegister expiry Celery task: `spine_expire_stale_states`
- [x] Skill auto-deprecation Celery task: `spine_auto_deprecate_skills`
- [x] Beat schedule: 5 new entries (snapshot daily, recall q4h, expire q6h, deprecate daily, community q8h)
- [x] 7 new tests (chronicle injection, fatigue injection, crisis injection, no-chronicle, correction→self_model, concurrency guard, metrics TTL)

### v2.5 Audit Findings (All Fixed)

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | Chronicle data invisible to AI | prompts.py had no chronicle reference | Added `spine_chronicle_summary` param + fetch in orchestrator_production |
| 2 | Corrections don't update strategy | on_user_correction skipped self_model | Added `self_model.record_user_correction()` call |
| 3 | Fatigue/crisis not in AI tone | FatigueGuard stored but never consumed | Added `spine_fatigue_context` param + fetch in orchestrator_production |
| 4 | Community signal dead flow | on_community_cohort_data() had zero callers | Created Celery task + beat schedule |
| 5 | 5 Celery tasks unscheduled | Methods existed but not in beat_schedule | Added all 5 to beat_schedule |
| 6 | Metrics counter infinite growth | No TTL on Redis counters | Added 7-day expiry on each increment |
| 7 | Concurrent pipeline data race | No lock on _run_signal_pipeline | Added Redis NX lock with 30s TTL |

### v2.4 (Learning Layer) — ALL COMPLETE
- [x] PolicyExperiment full loop: create → record_trial with real outcomes → suggest_promotions
- [x] StrategyBelief consumption: PolicyEngine.evaluate() accepts strategy_beliefs, applies Bayesian bias
- [x] Skill auto-deprecation: run_auto_deprecation() wired into pipeline
- [x] SourceEffectiveness tracking: SourceEffectivenessTracker records source→outcome mapping
- [x] record_outcome triggers experiment trial update + source effectiveness recording
- [x] Beliefs persist to Redis and reload across pipeline calls
- [x] _enrich_pipeline_post_policy: fixed experiment creation, added promotion suggestion check
- [x] 19 new tests (6 source effectiveness + 4 belief consumption + 3 experiment loop + 2 skill deprecation + 2 belief persistence + 2 outcome integration)
- [x] Dead method wiring: 7 divine moment + recovery methods wired into production paths
- [x] StateRegister MGET: batch loading replaces N+1 individual GETs
- [x] GrowthChronicle WATCH/MULTI: atomic writes prevent race conditions
- [x] Redis pipelining: batch deletes in StateRegister._remove_keys()
- [x] Circuit breaker: CircuitBreaker + resilient_redis_call (redis_resilience.py)
- [x] Degraded mode: all get_*_directive methods return None on Redis failure
- [x] API endpoints: GET /signals/envelope, POST /signals/receipt-action, GET /signals/context-receipt, GET /signals/metrics
- [x] SpineAuroraBridge MGET + pipelined writes
- [x] on_achievement_unlocked wired into achievement_event_consumer
- [x] on_user_correction wired into handle_user_receipt_action
- [x] build_recovery_card + recover_from_snapshot wired into on_user_return
- [x] build_context_receipt wired into _run_signal_pipeline
- [x] on_community_hint wired into on_community_cohort_data
- [x] build_experience_envelope exposed via API endpoint

### v2.3 (Production Hardening) — ALL COMPLETE
- [x] SpineSnapshot + Rehydration — Celery tasks (spine_snapshot_task + scan_spine_snapshots)
- [x] TraceCompaction — compress traces >50 into aggregated summaries (compact_old_traces)
- [x] RollingMetrics — get_rolling_metrics method
- [x] MultiGoalNamespace — goal_scoped_key + get_goal_scoped_states
- [x] Degraded Mode — CircuitBreaker + resilient_redis_call (redis_resilience.py)

### v2.2 Additional Production Wiring
- [x] GET /signals/envelope — ExperienceEnvelope API endpoint
- [x] POST /signals/receipt-action — user correction API (divine moment #2)
- [x] SpineReceiptCard — Flutter widget wired into chat_screen.dart
- [x] GrowthChronicle enhanced with weekly pattern detection
- [x] StateRegister protected with circuit breaker
- [x] Achievement event consumer spine wiring

### v2.1 COMPLETE
- [x] Deep audit conducted — identified 12 orphaned modules, 4 stub divine moments, Aurora↔Spine split
- [x] SpineAuroraBridge — bidirectional bridge (Spine→Aurora context, Aurora→Spine attribution)
- [x] Aurora decision_loop now consumes Spine directives, risk flags, outcomes, trust level
- [x] 12 orphaned modules registered in SpineOrchestrator.__init__
- [x] ExamSprintPolicy overlay wired into pipeline (deadline context persisted across turns)
- [x] `_enrich_pipeline_post_policy` — post-policy enrichment from all modules (7 hooks)
- [x] orchestrator_production.py — ExamSprint phase injection + receipt metadata + stale card
- [x] notification_service.py — `consume_spine_notification_directive` method
- [x] StaleRecoveryCard — Flutter widget with animation (divine moment #4)
- [x] chat_stream_events.dart — WebSocket event types for spine events
- [x] build_experience_envelope — unified experience output + E2E card aggregation test
- [x] FatigueGuard — pipeline-triggered fatigue detection (step 6 in enrichment)
- [x] CrisisMode — pipeline-triggered crisis detection for exam users (step 7 in enrichment)
- [x] SpineSnapshot + recovery — Celery tasks (spine_snapshot_task + scan_spine_snapshots)
- [x] ContextReceiptBar — Flutter widget for divine moment #3
- [x] MultiGoal namespace — goal_scoped_key + get_goal_scoped_states implemented

### P1: Living Experience Layer (ALL COMPLETE)
- [x] P1-1: Causal Timeline UI — TimelineCardRenderer (compact/expanded + user correction)
- [x] P1-2: Source Tray + RetrievalDirective integration (receipt builder + selection validation)
- [x] P1-3: Core Session Lifecycle (create/advance/pause/resume/complete)
- [x] P1-4: CommunityDirective v1 — 3 loops (cohort_mistake/partner_observation/resource_quality)
- [x] P1-5: SkillDirective v1 — inject/recommend/extract + worked-example-repair TCP
- [x] P1-6: Goal-Respectful Recall — notification builder + cooldown + user preferences

### P2: Self-Improving Learning Layer (ALL COMPLETE)
- [x] P2-1: PolicyAnalytics — strategy accuracy, degrading detection, confidence distribution
- [x] P2-2: PolicyExperiments — shadow A/B experiment framework with auto-conclusion
- [x] P2-3: Skill Lifecycle — promote/deprecate/auto-deprecate/health scoring
- [x] P2-4: LearningBase — Bayesian belief update + rule-based hybrid selection
- [x] P2-5: RelationshipModel — trust level, interaction style, strategy adjustment

### P3: General Goal OS Layer (ALL COMPLETE)
- [x] P3-1: GoalTypeAdapter — 6 goal types (exam/project/job_search/fitness/startup/general)
- [x] P3-2: GrowthChronicle — user-co-owned growth narrative (milestone/turning_point/pattern)
- [x] P3-3: ExternalIntegration — Calendar deadline pressure signals + tool activity bridge

### P4: Research-Grade (ALL COMPLETE)
- [x] CounterfactualEngine — baseline/rule/random methods for "what if no intervention"
- [x] UserSimulator — synthetic user profiles + Monte Carlo strategy comparison
- [x] DomainPackMarketplace — user-contributed strategy packs with validation + ranking

### Opus Review Fixes Applied
- [x] C-1: relationship_model.py 30-day TTL (Iron Law 5 compliance)
- [x] C-2: source_tray_integration.py inverted filter fix

### Notification Integration (COMPLETE)
- `recall_notification_task` — Celery task: single user → SpineOrchestrator.build_recall_notification() → NotificationService.create() push
- `scan_recall_notifications` — Celery task: scan active users with plans → dispatch per-trigger tasks
- 4 trigger types: undigested_material, task_not_started, task_missed, pre_exam_silence
- Cooldown enforced per trigger type via RecallNotificationBuilder
- PolicyEngine gates notification delivery
- Frontend retrieves via `spine.get_recall_notification(user_id)` from Redis

### Module Inventory (28 files in backend/app/signals/)
```
__init__.py                 — 46 public API exports
achievement_reinforcement.py — achievement → momentum signal
aurora_wake.py              — Aurora wake eligibility
causal_trace_store.py       — CausalTrace Redis store
community_loops.py          — 3 community feedback loops (P1-4)
community_signal.py         — community signal detection
core_session.py             — session lifecycle (P1-3)
directive_applier.py        — DirectiveApplier + DirectiveAuditor
exam_rescue_detector.py     — exam intent detection
exam_sprint_policy.py       — D-7→D-0 sprint strategy
external_integration.py     — Calendar + tool signals (P3-3)
goal_type_adapter.py        — 6 goal type profiles (P3-1)
growth_chronicle.py         — user-co-owned narrative (P3-2)
learning_base.py            — Bayesian + rule hybrid (P2-4)
material_signal.py          — material utilization signal
mistake_signal.py           — mistake pattern detection
outcome_recorder.py         — outcome recording + attribution
policy_analytics.py         — strategy effectiveness analysis (P2-1)
policy_engine.py            — deterministic rule arbitration
policy_experiments.py       — shadow A/B experiments (P2-2)
predicted_reply_options.py  — quick reply engine
recall_notification.py      — goal-respectful recall (P1-6)
recall_opportunity.py       — 4 recall trigger types
relationship_model.py       — user-AI relationship (P2-5)
self_model.py               — system self-modeling
signal_ranker.py            — signal ranking + conflict resolution
skill_extraction.py         — strategy → skill extraction
skill_lifecycle.py          — skill promote/deprecate (P2-3)
source_tray_integration.py  — SourceTray → Retrieval bridge
spine_metrics.py            — 10 Decision Realization metrics
spine_orchestrator.py       — full pipeline orchestrator
stale_state_guard.py        — stale state detection + recovery
state_packet_builder.py     — ActionableStatePacket builder
state_register.py           — per-user persistent state
task_timeout_detector.py    — task timeout detection
timeline_card_renderer.py   — timeline card rendering (P1-1)
types.py                    — 7 core data objects + all dataclasses
```

---

## Final Audit: Signal-to-Action Spine v2.0 COMPLETE

### Final Spec Coverage

| Section | Status | Notes |
|---------|--------|-------|
| P0-1: FirstMinuteSnapshot | ✅ | ExamRescueDetector + 14 tests |
| P0-2: TimeContext + StaleStateGuard | ✅ | 60-min threshold + 4 recovery options |
| P0-3: ActionableStatePacket v1 | ✅ | Structured fields for downstream |
| P0-4: ExecutionDirective | ✅ | 3 hard constraints (duration/chapter/type) |
| P0-5: RetrievalDirective / ContextPlan | ✅ | 5 retrieval modes + pollution_guard |
| P0-6: SourceAsset / SourceSlice | ✅ | SourceTrayState + relevance scoring |
| P0-7: ContextReceipt | ✅ | SourceTrayIntegration receipt builder |
| P0-8: DirectiveApplicationAudit | ✅ | DirectiveAuditor verifies constraints |
| P0-9: UserVisibleReceipt | ✅ | Short, specific, correctable |
| P0-10: CausalTrace | ✅ | Full chain: event→signal→policy→directive→audit→receipt |
| P1-1 through P1-6 | ✅ | All 6 items complete |
| P2-1 through P2-5 | ✅ | Self-improving learning layer |
| P3-1 through P3-3 | ✅ | General goal OS layer |
| P4: Research-grade | ✅ | Counterfactual + simulator + marketplace |

### 10 Iron Laws — All Covered by Tests

| Iron Law | Test Coverage |
|----------|--------------|
| 1. No-action signal is noise | SignalRanker filters + orphan_signal_count metric |
| 2. No-audit directive is hallucination | DirectiveAuditor constraint verification |
| 3. No-outcome action is not learning | OutcomeRecorder + shadow learning loop |
| 4. No-receipt personalization is invisible | UserVisibleReceipt with 3 correction actions |
| 5. Material must not pollute context | pollution_guard=strict + SourceTrayIntegration |
| 6. RAG is ContextPlan not switch | 5 retrieval modes + token_budget |
| 7. Sprint state must not become personality | scope TTL clamp + relationship 30-day TTL |
| 8. High-impact judgment must be correctable | handle_user_receipt_action + E2E correction |
| 9. Full Aurora not always-on | AuroraWakeJudge + quota/cooldown |
| 10. Sparkle must change action | E2E 7-day exam sprint acceptance |

### 6 Divine Moments — All Implemented

| Divine Moment | Implementation |
|---------------|---------------|
| 15.1: It sees my persistence | AchievementMomentum → momentum_high/low signal |
| 15.2: It admits misjudgment | handle_user_receipt_action("correct") → retraction + strategy switch |
| 15.3: It knows when not to use materials | RetrievalDirective pollution_guard + ContextReceipt |
| 15.4: It remembers time passed | StaleStateGuard → TimeDeltaPacket recovery options |
| 15.5: It prevents low-yield action | ExamSprintPolicy D-7→D-0 phases + avoid_new_chapter |
| 15.6: It turns community experience into strategy | CommunityLoopManager cohort_mistake → anonymous hint → verified task |

### Summary Statistics

```
623/623 tests passing
42 signal modules (excluding __init__.py)
57 public API exports (incl. AuroraControlSignal, AuroraAgendaItem, GoalWorldGraph, MultiGoalArbitrator, SourceEffectivenessTracker)
9/9 directive types active
10/10 Iron Laws tested
6/6 Divine Moments implemented
12/12 E2E test scenarios verified
8-layer architecture complete
v2.7 E2E Test Matrix: all 12 required scenarios have integration test coverage
v2.8 SignalRanker: 10 dimensions + 10 conflict rules + Iron Law compliance verified
v2.9 Production Wiring: ResponseDirective + RetrievalDirective + Chronicle + Fatigue wired into real production path
v2.9 AuroraControlSignal: unified envelope + AuroraAgendaItem for structured Aurora sessions
v3.0 Pipeline: which_directives gate + Aurora wake + all P1 tasks COMPLETE
v3.1 AuroraControlSignal + AuroraAgenda: 15 dedicated tests (5 envelope + 10 session), 615/615 total
v3.2 P0-3 complete: ActionableStatePacket 7/7 fields (time_context, execution_pattern, context_recommendation added), 8 new tests, 623/623 total
v4.0 P2 Batch 1 COMPLETE: state vocabulary (cognitive_load/affective_pressure) + model write roundtrip + learning persistence + retract_if, 656/656 total
```

### P1 Status — ALL COMPLETE

| P1 Task | Status | Key Change |
|---------|--------|-----------|
| P1-1 Causal Timeline UI | ✅ | TimelineCardRenderer |
| P1-2 Source Tray + RetrievalDirective | ✅ | compute_retrieval_plan + pollution guard |
| P1-3 Aurora Wake + Core Session | ✅ | Pipeline wake check + CoreSessionManager |
| P1-4 CommunityDirective 3 Loops | ✅ | CommunityLoopManager cohort/partner/resource |
| P1-5 SkillDirective v1 | ✅ | SkillLifecycleManager inject/extract/recommend |
| P1-6 Goal-Respectful Recall | ✅ | RecallNotificationBuilder + Celery scan |

---

*(每次 stage 完成后更新此文档)*
