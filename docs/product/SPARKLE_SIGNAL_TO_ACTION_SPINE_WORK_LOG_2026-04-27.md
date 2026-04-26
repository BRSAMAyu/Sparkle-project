# Signal-to-Action Spine — 工作日志

> **文档类型**: 按时间顺序的工作记录
> **起始日期**: 2026-04-27
> **分支**: `gpt_pro方案推进`
> **方案文档**: `SPARKLE_SIGNAL_TO_ACTION_SPINE_2026-04-27.md`

---

## 日志格式

每条记录包含：
- **时间**: 工作时间
- **阶段**: M1-Step1 / M1-Step2 / ...
- **动作**: 做了什么
- **文件**: 改动/创建了哪些文件
- **审查**: 自我审查结果
- **差距**: 距离方案完全体的差距
- **决策**: 关键设计决策及其原因

---

## 2026-04-27

### Phase: 项目启动 + 文档体系建立

**动作**:
- 保存完整方案至 `docs/product/SPARKLE_SIGNAL_TO_ACTION_SPINE_2026-04-27.md`
- 建立三文档体系：方案文档（已存在）、工作日志（本文件）、进度追踪
- 确认所有服务运行中 (API:8000, gRPC:50051, Gateway:8080, DB, Redis, MinIO)
- Flutter 构建通过，零编译错误
- 分支 `gpt_pro方案推进` 工作区干净

**差距**:
- 全部 3 个 Milestone 未开始
- 需要先探索现有代码结构，确定信号接入点

---

### Phase: M1 实现 (Steps 1-5)

**动作**:
- 创建 `backend/app/signals/` 模块（6个文件）
  - `types.py` — 7 个核心数据对象（dataclass）
  - `causal_trace_store.py` — Redis 持久化（trace/signal/directive）
  - `task_timeout_detector.py` — 固定规则：连续2次超时 → ActionableSignal
  - `policy_engine.py` — 规则表映射：signal → PolicyDecision + ExecutionDirective
  - `directive_applier.py` — 硬约束注入 + DirectiveApplicationAudit
  - `spine_orchestrator.py` — 全链路编排
- 修改 `backend/app/services/task_event_consumer.py` — 在 task.completed 处理中接入 Spine 管道
- 修改 `backend/app/orchestration/planning_workflow.py` — 消费 directive 约束 + audit
- 修改 `backend/app/api/v1/aurora.py` — 添加 Receipt GET/POST 端点
- 编写 12 个单元测试全部通过

**审查: Opus Agent 独立审查**
- 发现 4 个 CRITICAL 问题：
  1. C1: `_estimated_minutes_for_task` 未传递 `max_duration_min` → 改为直接使用 `apply_directive_to_task_spec`
  2. C2: `avoid_new_chapter` 和 `required_task_type` 从未强制执行 → 现在通过 `DirectiveApplier.apply_to_task_spec` 统一执行
  3. C3: `apply_directive_to_task_spec` 从未在真实代码路径调用（audit 从不触发）→ 已修复：planning_workflow 现在通过 SpineOrchestrator 走完整路径
  4. C4: GET receipt 返回 None 导致 Flutter 崩溃 → 改为返回 `{"active": false}`
- 修复后重测：12/12 通过
- WARNING 级别：W1 ActionableStatePacket 定义但未使用（后续 Milestone 填充）；W6 读取-修改-写入竞态（当前顺序执行安全）；W7 方法级 import 已移至模块顶部

**关键设计决策**:
- 第一版用固定规则而非 LLM 推断（符合方案 Step 2 指引）
- Directive 通过 `SpineOrchestrator.apply_directive_to_task_spec()` 消费，不是 prompt 片段（符合 C4）
- Audit 真实验证输出是否满足约束，不满足则记录 violation（符合 C5）
- Receipt 短、具体、可纠正，三个 action 按钮（符合 C6）
- 所有 spine 错误不阻塞主流程（try/except 包裹）

**差距**:
- M2 (资料闭环) 和 M3 (错因驱动) 未开始
- E2-E5 验收用例未覆盖
- ActionableStatePacket 在类型中定义但未在管道中使用
- 缺少 Prometheus 可观测性指标
- Receipt 消息可以更具产品感（当前是 reasoning 模板输出）

---

*（后续日志按时间追加）*
