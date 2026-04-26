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

133/133 tests passing:
- M1 控制链路: 12 tests
- M2 资料闭环: 5 tests
- M3 错因驱动: 4 tests
- P0-1 FirstMinuteSnapshot: 14 tests
- P0-2 StaleStateGuard: 6 tests
- P0-3 ActionableStatePacket: 7 tests
- P1-1 AchievementReinforcement: 6 tests
- P1-2 AuroraWakeEligibility: 7 tests
- P1-3 PredictedReplyOption: 8 tests
- P1-4 RecallOpportunity: 10 tests
- P1-5 SparkleSelfModel: 9 tests
- P1-6 CommunitySignal: 9 tests
- PolicyEngine rules: 6 tests
- P2 Spine integration: 17 tests
- P3 Production wiring: 5 tests
- Layer 3 SignalRanker: 8 tests

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

## P1-1: AchievementReinforcementConsumer

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

### 架构原则检查清单

- [x] 每个 Signal 都绑定一个用户可见变化
- [x] Directive 是结构化参数，不是 prompt 片段
- [x] Audit 验证输出是否满足约束
- [x] Receipt 短、具体、可纠正
- [x] 社群信号不直接写个人状态
- [x] 成就是不直接改长期人格

---

*（每次 stage 完成后更新此文档）*
