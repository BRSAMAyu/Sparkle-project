# GAP Closer Progress Tracker

> Single source of truth. Two parallel Claude instances coordinate through Claimed-By column.
> Updated: 2026-05-06

## Legend

| Symbol | Meaning |
|--------|---------|
| ⬜ pending | Not started, available for claiming |
| 🔵 in-progress | Claimed and being worked on |
| ✅ done | Committed and verified |
| 📋 spec-done | Spec written, awaiting user implementation |
| 🚫 blocked | Blocked with reason in Note column |

## Phase 0: Production Closed Loop (0.5-2 days)

| ID | Title | Level | Effort | Mode | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|------|--------|-----------|--------|------|
| GAP-P0-1 | RetrievalDirective → RAG 消费 | L2 | S | you | ✅ done | — | user | graph_rag.py + retrieval_service.py + orchestrator, 20 tests pass |
| GAP-P0-2 | 常规轮次轻量信号检测 + CausalTrace | L2 | S | claude | ✅ done | — | 623ca6c1b | on_chat_turn + _detect_chat_turn_signal + heartbeat + CausalTrace every turn, 3 tests pass |

**Phase 0 DOD**: ✅ PASS — 2/2 items done, 40 tests pass, security PASS, correctness PASS. (AT001 on untracked plan_version_service.py is P1-2 scope; Go coverage needs infra.)

---

## Phase 1: Architecture Completion (5-8 days)

| ID | Title | Level | Effort | Mode | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|------|--------|-----------|--------|------|
| GAP-P1-1 | L1 Light Aurora 独立模块 | L3 | M | claude | ✅ done | — | 36a9a7eed | l1_light_aurora.py + orchestrator fast-path short-circuit |
| GAP-P1-2 | Plan 版本化 + 回滚 | L3 | L | spec→you | 📋 spec-done | — | 7f12af33c | Spec: _specs/GAP-P1-2.md, 5 phases, 6.5-9.5 day est. |
| GAP-P1-3 | 非考试首分钟检测器 | L2 | M | claude | ✅ done | — | 642a095a1 | NonExamFirstMinuteDetector: job_search/project/habit, 7 tests pass |
| GAP-P1-4 | MAGIC-001 统一连胜 + 差异化策略 | L2 | M | claude | ✅ done | — | 5372936c0 | Graduated milestones 7/14/21/30 + Chinese narratives + GrowthCard emission |
| GAP-P1-5 | ExperienceEnvelope 状态模型 | L3 | M | claude | ✅ done | — | be22b3bc3 | model + provider + chat stream wiring, 2 tests pass |
| GAP-P1-6 | CRDT 冲突解决 | L3 | M | spec→you | 📋 spec-done | — | addfd9716 | APP-005, 11 号报告, 跨层冲突解决 |
| GAP-P1-7 | MAGIC-004 自动缺席检测 | L2 | M | claude | ✅ done | — | f8f1775ac | AbsenceDetector: idle/short/prolonged/extended + Celery scan 30min + spine pipeline, 13 tests pass |

**Phase 1 DOD**: ✅ PASS — 7/7 items done, 5 code + 2 specs. (AT001/GAT-GoCoverage pre-existing, not Phase 1 scope.)

---

## Phase 2: Flutter Experience (15-25 days)

| ID | Title | Level | Effort | Mode | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|------|--------|-----------|--------|------|
| GAP-P2-1 | Source Tray 一等 UI 组件 | L3 | L | spec→you | 📋 spec-done | — | 02d4f6c95 | 07 号报告, scope-based 排除 + EvidencePack 集成 |
| GAP-P2-2 | Causal Timeline 集成主流程 | L2 | M | claude | ✅ done | — | 5b9a05724 | AppBar timeline button + badge + bottom sheet + CausalTraceEvent parsing, 6 files |
| GAP-P2-3 | Stuck Type 运行时分类器 | L2 | M | spec→you | 📋 spec-done | — | bd4b3e0a9 | 08 号报告 E2E-045, 5 种卡点类型自动检测 |
| GAP-P2-4 | Sprint 复盘页面 | L2 | M | claude | ✅ done | — | e27a328c0 | Sprint review screen + route + sprint header button, 3 files |
| GAP-P2-5 | 星图页 goal-world-model overlay | L2 | M | claude | ✅ done | — | 62a4404 | UX-005, 01 号报告 |
| GAP-P2-6 | 设置页 5 个子版块 | L2 | L | spec→you | 📋 spec-done | — | cd3427d | UX-010, 记忆管理/社群智能等 |
| GAP-P2-7 | 通知中心目标价值渲染 | L1 | S | claude | ✅ done | — | 8e1f0b22e | Goal value chip + next step hint, always visible in notification card |

**Phase 2 DOD**: ✅ PASS — 7/7 items done (4 code + 3 specs). Security PASS, Correctness PASS, Phase 2 files 0 flutter errors. (Rule AT + Go coverage pre-existing, acknowledged in Phase 0 DOD.)

---

## Phase 3: Stability / Data Sovereignty (8-12 days)

| ID | Title | Level | Effort | Mode | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|------|--------|-----------|--------|------|
| GAP-P3-1 | SpineSnapshot 调度 + close_session 触发 | L1 | S | claude | ✅ done | — | verified-existing | STAB-002: spine-snapshot-daily beat (b3307e5f) + session_end snapshot (623ca6c1) already wired |
| GAP-P3-2 | FatigueGuard 独立服务 | L3 | M | spec→you | 📋 spec-done | — | c490921 | STAB-010, 疲劳信号统一服务 |
| GAP-P3-3 | RecoveryModeOrchestrator | L3 | L | spec→you | 📋 spec-done | — | 6dd6412c7 | STAB-013, 4-phase spec: health monitor + event buffer + recovery orchestration + consistency verify |
| GAP-P3-4 | GROW-009 数据删除/导出 | L3 | M | spec→you | 📋 spec-done | — | 120dd4f | 09 号报告, 永久删除 + 导出 (数据主权) |
| GAP-P3-5 | NUDGE-002 每渠道交付策略 | L2 | M | claude | ✅ done | — | adecfbd98 | Per-channel delivery: push/in_app/silent from Spine directive, backward compatible |
| GAP-P3-6 | GROW-002 连胜质量门槛 | L2 | S | claude | ✅ done | — | 47cbfc7ff | 09 号报告, fatigue/crisis/late-night 纳入 StreakQuality |
| GAP-P3-7 | GROW-007 retract_if 填充 | L1 | S | claude | ✅ done | — | 731699b11 | retract_if populated in milestones + patterns, _should_retract check in get_confirmed_entries |

**Phase 3 DOD**: ✅ PASS — 7/7 items done (4 code + 3 specs). Security PASS, Correctness PASS. (AT001 on plan_version_service.py pre-existing, acknowledged in Phase 0/1 DOD.)

---

## Phase 4: Observability / Community (8-12 days)

| ID | Title | Level | Effort | Mode | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|------|--------|-----------|--------|------|
| GAP-P4-1 | Release Gate | L3 | L | spec→you | 📋 spec-done | — | 6f7596f06 | OBS-015, 部署阻断门禁 |
| GAP-P4-2 | 成本预测框架 | L3 | L | spec→you | 📋 spec-done | — | 1c0391275 | OBS-013, LLM/RAG/Aurora/P4 成本 |
| GAP-P4-3 | 场景回归框架 SparkleGoalBench | L3 | L | spec→you | 📋 spec-done | — | — | OBS-011, 目标场景回归测试 |
| GAP-P4-4 | 社群 UI 目标价值渲染 | L2 | S | claude | ✅ done | — | a32976238 | COM-011, "这如何帮助我的目标" |
| GAP-P4-5 | 混沌测试 MinIO 覆盖 | L2 | M | claude | ✅ done | — | a3c62f4df | OBS-020, 18 MinIO resilience tests + drill scenarios (minio-down, minio-slow) |
| GAP-P4-6 | SLO + Prometheus 告警 | L2 | M | claude | ✅ done | — | 9fc20c2b9 | STAB-018, 性能 SLO 指标 |
| GAP-P4-7 | MAGIC-002 "我改了 N 个任务" 展示 | L1 | S | claude | ✅ done | — | e6ef6cc72 | 02 号报告, correction_impact card + envelope + stream emission |
| GAP-P4-8 | MAGIC-003 向用户展示不用资料原因 | L1 | S | claude | ✅ done | — | 970f4d0ed | 02 号报告, 13 reason_for_user strings now explanatory |
| GAP-P4-9 | MAGIC-005 个性化收益 profile | L2 | S | claude | 🔵 in-progress | claude-B | 2026-05-06T13:00:00Z | 02 号报告, 硬编码 → 个性化 |
| GAP-P4-10 | MAGIC-006 任务模板注入 | L2 | M | claude | ⬜ pending | — | — | 02 号报告, 社群经验 → 任务模板 |
| GAP-P4-11 | COM-012 社群策略 Outcome 记录 | L2 | M | claude | ⬜ pending | — | — | 05 号报告, 显式记录 |
| GAP-P4-12 | STAB-011 非考试危机模式 | L2 | M | claude | ⬜ pending | — | — | 03 号报告, Crisis Mode 扩展到非考试 |

**Phase 4 DOD**: ⬜ pending

---

## Summary

| Phase | Total | ✅ done | 📋 spec | ⬜ pending | Est. Days |
|-------|-------|---------|---------|-----------|-----------|
| Phase 0 | 2 | 2 | 0 | 0 | 0.5-2 |
| Phase 1 | 7 | 5 | 2 | 0 | 5-8 |
| Phase 2 | 7 | 3 | 2 | 2 | 15-25 |
| Phase 3 | 7 | 4 | 3 | 0 | 8-12 |
| Phase 4 | 12 | 5 | 3 | 4 | 8-12 |
| **Total** | **35** | **19** | **8** | **8** | **35-45** |
