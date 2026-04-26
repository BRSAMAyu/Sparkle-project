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

## 当前测试覆盖

48/48 tests passing:
- M1 控制链路: 12 tests
- M2 资料闭环: 5 tests
- M3 错因驱动: 4 tests
- P0-1 FirstMinuteSnapshot: 14 tests
- P0-2 StaleStateGuard: 6 tests
- P0-3 ActionableStatePacket: 7 tests

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

### 缺失的核心对象

| 对象 | 需要新建 | 依赖 |
|------|---------|------|
| ActionableSignal | ✅ 新模块 | EventBus |
| ActionableStatePacket | ✅ 新模块 | ActionableSignal |
| PolicyDecision | ✅ 新模块 | ActionableStatePacket |
| ExecutionDirective | ✅ 新模块 | PolicyDecision |
| DirectiveApplicationAudit | ✅ 新模块 | ExecutionDirective |
| UserVisibleReceipt | ✅ 新模块 | PolicyDecision |
| CausalTrace | ✅ 新模块 | 全部上述 |

### 架构原则检查清单

- [ ] 每个 Signal 都绑定一个用户可见变化
- [ ] Directive 是结构化参数，不是 prompt 片段
- [ ] Audit 验证输出是否满足约束
- [ ] Receipt 短、具体、可纠正
- [ ] 社群信号不直接写个人状态
- [ ] 成就是不直接改长期人格

---

*（每次 stage 完成后更新此文档）*
