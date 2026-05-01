# Sparkle Roadmap v3 — Codex 持续推进交接文档

> **创建日期**: 2026-04-29
> **创建者**: Claude (审查者角色)
> **用途**: Codex agent 持续推进 Roadmap v3 所有剩余任务的完整交接
> **路线图**: `docs/product/SPARKLE_ROADMAP_v3_2026-04-28.md`
> **跟踪器**: `docs/product/SPARKLE_ROADMAP_v3_TRACKER_2026-04-28.md`
> **审查报告**: `docs/product/SPARKLE_AUDIT_R1_SIGNAL_FLOW_2026-04-29.md` — **3 P0 Critical 接线缺口**

---

## 1. 当前完成状态

### Phase 0: 生产基础设施硬化 — ✅ 100% 完成 (18/18 tasks)

由 Claude + Codex 分两轮完成。最新提交: `276bce8b`, `d74b569c`

| 子项 | 状态 | 提交 |
|------|------|------|
| 0.1 TLS/HTTPS (5 tasks) | ✅ | `32b91521` |
| 0.2 Sentry (6 tasks) | ✅ | `32b91521` + `276bce8b` |
| 0.3 秘钥校验 (4 tasks) | ✅ | `32b91521` |
| 0.4 安全加固 (5 tasks) | ✅ | `276bce8b` |
| 0.5 Email SMTP (3 tasks) | ✅ | `276bce8b` |

### Phase 1: 核心闭环关闭 — 72% 完成 (18/25 tasks)

| 子项 | 完成度 | 关键提交 |
|------|--------|----------|
| 1.1 Breakpoint #5 Push | 4/6 | `a9ec2ac3` — 后端完成, **Flutter 推送跳转未做** |
| 1.2 Breakpoint #6 Adjustments | 5/6 | `a9ec2ac3` — 后端完成, **Flutter WebSocket 传递未做** |
| 1.3 Breakpoint #7 Verification | 6/6 | `a9ec2ac3` + `93b72fd4` — 全部完成 |
| 1.4 Outcome 回流 | 2/3 | `e1812b92` — Grafana dashboard 未完成 |
| 1.5 Card Protocol | 0/6 | **全部未开始** |

### Phase 2-7: 全部未开始

---

## 2. Phase 1 代码质量审查发现

> **✅ 全部已由 Codex 修复 (commit `2428d022`)**

### 2.1 outcome_recorder.py — 死代码残留 (P2)

**文件**: `backend/app/signals/outcome_recorder.py`
**问题**: `_attribute()` 方法中 lines 189-196 和 229-246 有**重复的 harmful/needs_confirmation 检查**。第一组检查在前面，第二组永远不会执行（死代码）。
**修复**: 删除 lines 229-246 的重复代码块。

### 2.2 outcome_tracker.py — Redis 非原子操作 (P2)

**文件**: `backend/app/signals/outcome_tracker.py`
**问题**: `register_expected()` 中的 `lpush + ltrim + expire` 是三个独立 Redis 命令，非原子。如果在 lpush 和 ltrim 之间崩溃，列表可能超过限制。
**修复**: 使用 `redis.pipeline()` 包裹这三个操作，与 push_scheduler.py 中的 `_enqueue_trigger()` 保持一致。

### 2.3 learning_guard.py — 冗余分支 (P3)

**文件**: `backend/app/signals/learning_guard.py`
**问题**: `should_learn()` 方法 lines 56-57 检查 `inconclusive/needs_confirmation`，但 line 59 已经对所有未匹配的情况返回 False，所以 lines 56-57 是冗余的。
**修复**: 删除 lines 56-57，保持逻辑不变。

### 2.4 push_scheduler.py — user_id UUID 类型安全 (P3)

**文件**: `backend/app/services/push_scheduler.py` line 141
**问题**: `uuid.UUID(user_id)` — 如果 Redis key 中的 user_id 格式异常，会抛出 `ValueError` 导致整个 queue 处理中断。
**修复**: 添加 try-except 包裹 UUID 转换，格式异常时 skip 并 log warning。

### 2.5 测试覆盖缺口 (P2)

以下方法缺少单元测试：
- `outcome_recorder.py`: `build_self_correction_receipt()`, `get_recent_policy_effects()`, `get_insufficient_count_for_policy()`
- `outcome_tracker.py`: `verify_pending()`, `get_pending_count()`
- `learning_guard.py`: `check_insufficient_streak()`, `get_guard_verdict()`
- `push_scheduler.py`: `process_recall_queue()`

---

## 3. 待完成任务优先级排序

### 第一优先级：Phase 1 收尾 (6 tasks)

| # | Task ID | 任务 | 文件 | 类型 | 复杂度 |
|---|---------|------|------|------|--------|
| 1 | T1.5.1 | card_service.py 完善 Card CRUD + CardEdge 关系 | `backend/app/services/card_service.py` | Python | L2 |
| 2 | T1.5.2 | planning_workflow Card 写入 (双写 Card + Plan) | `backend/app/orchestration/planning_workflow.py` | Python | L3 |
| 3 | T1.5.3 | TaskOccurrence 从 Card 生成 | `backend/app/services/task_service.py` | Python | L2 |
| 4 | T1.5.4 | InterventionRecord 记录 | `backend/app/services/intervention_service.py` | Python | L2 |
| 5 | T1.5.5 | Flutter Card 模型适配 | `mobile/lib/features/plan/` | Dart | L2 |
| 6 | T1.5.6 | 双写一致性校验脚本 | `scripts/verify_card_plan_consistency.py` | Python | L2 |

**并行可选 (Flutter 侧，可与 Phase 2 并行)**:
- T1.1.4: JPush 内容增强 (`mobile/lib/core/services/push_config.dart`)
- T1.1.5: Flutter 推送跳转 (`mobile/lib/features/notification_center/`)
- T1.2.5: Flutter WebSocket 传递 structured_adjustments (`mobile/lib/features/chat/`)
- T1.4.3: Outcome Grafana dashboard (`monitoring/grafana-dashboards/`)

### 第二优先级：Phase 2 Spine 深化 (18 tasks)

**重要发现**: Phase 2 的核心基础设施**已经存在**。以下模块在 `backend/app/signals/` 下已实现：

| 已有模块 | 文件 | 状态 |
|----------|------|------|
| SignalRanker | `backend/app/signals/signal_ranker.py` | 已实现 |
| MultiGoalArbitrator | `backend/app/signals/multi_goal_arbitrator.py` | 已实现 |
| CausalTraceStore | `backend/app/signals/causal_trace_store.py` | 已实现 |
| SpineQualityGuard | `backend/app/signals/spine_quality_guard.py` | 已实现 |
| SpineOrchestrator | `backend/app/signals/spine_orchestrator.py` | 已实现 |

**这意味着 Phase 2 的 T2.1.1-T2.1.6 (Signal Ranking) 大部分可能只需验证+补齐测试，而非从零实现。**

Codex 在执行 Phase 2 任务时，**必须先读现有代码**再决定是新建还是增强。

#### Phase 2 详细任务

| # | Task ID | 任务 | 说明 |
|---|---------|------|------|
| 7 | T2.1.1 | signal_ranking.py 增强/验证 | 先读现有 `signal_ranker.py`，确认排序维度是否完整 |
| 8 | T2.1.2 | policy_arbitration.py 增强/验证 | 先读现有 `multi_goal_arbitrator.py` |
| 9 | T2.1.3 | state_register.py | Actionable State Register — 可能需要新建 |
| 10 | T2.1.4 | orchestrator 主链接入 | 确认 spine_orchestrator 已正确连接 |
| 11 | T2.1.5 | orphan_detector.py | 孤儿信号检测 — 可能需要新建 |
| 12 | T2.1.6 | Prometheus metrics 补齐 | signal_to_state_rate 等 |
| 13 | T2.2.1 | 9 类 directive audit 补齐 | 每个 directive 消费点的 audit 检查 |
| 14 | T2.2.2 | UserVisibleReceipt | 关键变化的 receipt 生成 |
| 15 | T2.2.3 | context_receipt_bar.dart 增强 | Flutter 侧 |
| 16 | T2.3.1 | causal_trace.py 统一存储 | 分层存储策略 |
| 17 | T2.3.2 | Go Gateway trace_id 传递 | request_context middleware |
| 18 | T2.3.3 | Flutter trace_id 上报 | 关键行为带 trace_id |
| 19 | T2.3.4 | **Spine Timeline API** | `GET /api/v1/spine/timeline/{user_id}/{goal_id}` — **新建** |
| 20 | T2.3.5 | causal_timeline_panel.dart 从 API 加载 | Flutter 侧 |
| 21 | T2.4.1-T2.4.6 | 降级与恢复主链 (6 tasks) | Redis/LLM/RAG 降级 + Snapshot + Rehydration + ReturnCaseFile |

### 第三优先级：Phase 3 Aurora↔Spine 收敛 (Phase 2 完成后)

详见路线图文档 `docs/product/SPARKLE_ROADMAP_v3_2026-04-28.md` Phase 3 部分。

---

## 4. 关键架构约束 (Codex 必须遵守)

### 4.1 Spine 数据流

```
RawEvent → ActionableSignal → SignalRanking → StateRegister → PolicyArbitration → Directives → Actuation → Outcome → Attribution
```

所有 Spine 模块在 `backend/app/signals/` 下。核心编排器是 `spine_orchestrator.py`。

### 4.2 双写规则 (Card Protocol 迁移期间)

Card Protocol 迁移期间必须保持**向后兼容**：
- 新计划同时写入 Card 表和 Plan 表
- Card → CardEdge 关系正确建立
- TaskOccurrence 从 Card 生成，同时保留旧 Task 逻辑
- 最终由一致性校验脚本验证

### 4.3 Kill Switch 协议

所有新功能必须支持 tri-state: `off → shadow → live`。
参考: `backend/app/core/kill_switch.py`

### 4.4 测试要求

- 每个 task 必须有对应测试
- Python: `backend/tests/unit/` 下新建测试文件
- Flutter: `mobile/test/` 下新建测试
- 测试命名: `test_{feature_name}.py`
- 所有测试必须通过: `cd backend && pytest tests/unit/test_{file} -v`

### 4.5 文件修改范围

- 修改现有文件前**先读**该文件全部内容
- 不修改 proto 文件（除非明确要求）
- 不修改 generated code（`backend/gateway/gen/`, `backend/app/gen/`, `mobile/lib/gen/`）
- 不添加新的 .env 变量（除非在 settings.py 和 .env.example 同步更新）

---

## 5. Git 约定

### 5.1 分支

当前工作在 detached HEAD 上，但变更会合并到 `gpt_pro方案推进` 分支。
Codex 应在当前分支上直接提交。

### 5.2 Commit 消息格式

```
feat(spine): 简述
fix(phase0): 简述
docs(tracker): 简述
```

### 5.3 如何识别 Claude 的更改

Claude 的提交在 git log 中有 `Co-Authored-By: Claude` 标记。
主要提交历史：

```
d74b569c — Phase 0 tracker update
276bce8b — Phase 0 completion (CORS/Sentry/MinIO/Grafana/SMTP)
31c18235 — Phase 1 tracker update
93b72fd4 — Phase 1 audit fixes (dedup outcome_recorder, async record_sent)
e1812b92 — Phase 1 metrics + Grafana dashboard
a9ec2ac3 — Phase 1 breakpoints #5/#6/#7
32b91521 — Phase 0 initial hardening
```

---

## 6. 验证流程

每个 task 完成后，Codex 应运行：

```bash
# Python 测试
cd backend && pytest tests/unit/test_{relevant_file} -v

# Go 测试 (如果修改了 Go 代码)
cd backend/gateway && go test ./...

# Flutter 分析 (如果修改了 Dart 代码)
cd mobile && flutter analyze lib/{modified_path}

# 全量 Python 测试 (提交前)
cd backend && pytest tests/unit/ -x -q
```

---

## 7. 推荐的 Codex 执行顺序

> **🔴 2026-04-29 审查更新**: 发现 3 个 P0 Critical 接线缺口，优先级提升到所有其他任务之前。

```
Step 0: P0 Critical 接线修复 (审查发现 — 最高优先级)
        │ C-01-FIX: OutcomeTracker → 接线到生产代码
        │ C-02-FIX: structured_adjustments → 注入 prompts.py
        │ C-03-FIX: multi_agent_adapter → 传入 Spine context
        ↓
Step 1: Phase 1 收尾 — Card Protocol (T1.5.1-T1.5.6)
        ↓ 先完成 Card 双写，这是后续 Phase 2-3 的基础

Step 2: P1 High 接线修复 (审查发现)
        │ H-01-FIX: 6 EventBus 事件接入 Spine
        │ H-03-FIX: Spine 降级 Prometheus counter + 告警
        ↓

Step 3: Phase 2.1 — Signal Ranking 验证/增强 (T2.1.1-T2.1.6)
        ↓ 先确认已有代码是否满足需求

Step 4: Phase 2.2 — Directive Audit (T2.2.1-T2.2.3)
        ↓

Step 5: Phase 2.4 — 降级与恢复 (T2.4.1-T2.4.6)
        ↓

Step 6: Phase 3 Aurora↔Spine 收敛 (含 H-02-FIX Aurora→Spine 反馈接线)
        ↓

Step 7+: Phase 4-7 (见路线图文档)
```

**注意**: T2.3.4 (Timeline API) 和 T2.3.5 (Causal Timeline Panel) 已确认存在，无需实现。
**注意**: T1.4.3 (Outcome Grafana dashboard) 已确认完成 (sparkle-spine-outcome.json)。
```

---

## 8. 现有未提交文件说明

以下文件在工作树中是未提交的（不是本次工作产物，不要动）：

```
M  mobile/lib/l10n/app_localizations*.dart     — i18n 自动生成
?? backend/app/signals/Sparkle 项目全面问题与改进清单.md
?? docs/engineering/i18n_*.md                  — i18n 清理计划
?? docs/product/SPARKLE_I18N_FIX_PROGRESS_*.md
?? docs/product/advanced_improvement_guide/
?? docs/product/critical_files/
?? docs/product/愿景验收清单/
```

---

## 9. 关键文件索引

### Phase 1 核心文件 (Claude 创建/修改)

| 文件 | 作用 | 测试文件 |
|------|------|----------|
| `backend/app/signals/outcome_tracker.py` | Expected/actual outcome 注册与验证 | `tests/unit/test_verification_loop.py` |
| `backend/app/signals/outcome_recorder.py` | 干预结果记录 + 因果归因 | 同上 |
| `backend/app/signals/learning_guard.py` | 学习守卫 (防止错误学习) | 同上 |
| `backend/app/services/push_scheduler.py` | 行为驱动推送调度 | `tests/unit/test_behavior_driven_push.py` |
| `backend/app/core/business_metrics.py` | Prometheus 指标定义 | — |
| `monitoring/grafana-dashboards/sparkle-spine-outcome.json` | Grafana dashboard | — |

### Spine 已有基础设施 (Phase 2 需要验证/增强)

| 文件 | 作用 |
|------|------|
| `backend/app/signals/spine_orchestrator.py` | Spine 主编排器 |
| `backend/app/signals/signal_ranker.py` | 信号排序 |
| `backend/app/signals/multi_goal_arbitrator.py` | 多目标仲裁 |
| `backend/app/signals/causal_trace_store.py` | CausalTrace 存储 |
| `backend/app/signals/spine_quality_guard.py` | 质量守卫 |
| `backend/app/signals/types.py` | 数据类型定义 (CausalTrace, OutcomeRecord, PolicyEffectEntry) |

### Card Protocol 相关

| 文件 | 作用 |
|------|------|
| `backend/app/services/card_service.py` | Card CRUD (待完善) |
| DB tables: cards, card_edges, task_occurrences, planning_artifacts, intervention_records | Alembic 迁移已存在 |
| `docs/product/SPARKLE_CARD_PROTOCOL_TAXONOMY_2026-04-02.md` | Card 分类法文档 |

---

## 10. Tracker 更新约定

每完成一个 task 后，更新 `docs/product/SPARKLE_ROADMAP_v3_TRACKER_2026-04-28.md`：
- 将 `⬜ 未开始` 改为 `✅ 完成`
- 填写负责人和备注
- 更新 `最后更新` 日期
- 在提交日志中添加新行
- 如果发现代码质量问题，添加到审查日志表

---

> **最终提醒**: 先读代码再动手。Phase 2 的大部分基础设施已存在，盲从路线图"新建"会导致重复代码。验证 → 增强 → 测试 → 提交。
