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

336/336 tests passing:
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

## 当前状态: v2.0 Source Layer IN PROGRESS

**336/336 tests passing** | **9/9 directive types active** | **Shadow learning loop active** | **2 divine moments implemented**

### v1.1 完成任务
- [x] P0-1: Achievement → PolicyEngine (3-tier rules + soft difficulty + shadow learning)
- [x] P0-2: CommunityDirective + SkillDirective v1
- [x] P0-4: Outcome → PolicyEffectLedger + self-correction loop
- [x] P0-3: Task card 8-field protocol (why_this_task, materials_protocol, stuck_protocol, updates_after_completion)
- [x] P0-6: ExamSprintPolicy + D-7→D-0 (5 phases + mastery mapping + node priority scoring)
- [x] P0-1b: Achievement quality cross-check (Rule A: quality_ok, Rule B: declining_accuracy, Rule C: overrun/pressure)
- [x] P0-7: Divine moments (admit misjudgment + remember time)
- [x] Opus review fixes (C-1, C-3, W-1, W-2)

### v2.0 进展
- [x] P0-5: SourceAsset / SourceSlice / SourceTray wrapper types (10 tests)
- [x] Skill extraction triggers — auto-extract effective strategies (7 tests)

### v2.0 剩余
- [x] SourceAsset ↔ RetrievalDirective integration
- [ ] Community commitment loop (Divine Moment 6 completion)
- [ ] Notification service integration (recall activation)

---

*(每次 stage 完成后更新此文档)*
