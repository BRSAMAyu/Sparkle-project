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
