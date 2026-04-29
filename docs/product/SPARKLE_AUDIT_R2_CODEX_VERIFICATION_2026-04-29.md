# Sparkle 深度审查报告 #2 — Codex R1 验收 + 接线缺口复查

> **审查日期**: 2026-04-29
> **审查者**: Claude (审查角色)
> **范围**: 验收 Codex 完成的 T1.1.4/T1.1.5/T1.2.5 + 复查 P0 接线缺口修复状态
> **前置**: [`SPARKLE_AUDIT_R1_SIGNAL_FLOW_2026-04-29.md`](SPARKLE_AUDIT_R1_SIGNAL_FLOW_2026-04-29.md)

---

## 审查 #1 P0 接线缺口复查

| Task | 状态 | 说明 |
|------|------|------|
| C-01: OutcomeTracker 接线 | ❌ **未修** | `register_expected` 仍然只在测试中被调用, `verify_pending` 仍无 scheduler job |
| C-02: structured_adjustments 注入 prompt | ✅ **已通过** | 通过 `DualCoreDecision.prompt_instruction` property 自动转为文本, 经 `dual_core_instruction` 参数注入 system prompt |
| C-03: multi_agent_adapter Spine context | ❌ **未修** | 两个 `build_system_prompt` 调用仍不传 `spine_response_directive` 等参数; `orchestrator_production.py` 正确传了但 adapter 没跟上 |

**C-02 修正说明**: 审查 #1 中判断"structured_adjustments 从未到达 LLM prompt"是**部分错误的**。实际情况是 `prompt_instruction` property 已经包含 structured_adjustments 文本渲染，只是这个路径在初次审查时被忽略。但 `multi_agent_adapter` 路径确实缺失。

---

## Codex 完成任务验收

### T1.1.4 JPush 内容增强 — ✅ 验收通过

- `JPushPayload` dataclass 包含 `goal_context` + `suggested_action` 字段
- `_prepare_extras()` 正确序列化到 JPush extras (Android + iOS)
- 单元测试覆盖序列化逻辑

### T1.1.5 Flutter 推送跳转 — ✅ 验收通过

- `PushNavigationService` 正确解析 `recall_type`、`deep_link`、`goal_context`、`suggested_action`
- 支持 task/plan/chat entity 路由 + recall 专用路由
- `_routeFromSuggestedAction()` 处理 action metadata 导航

### T1.2.5 Flutter WebSocket 传递 — ⚠️ 90% 通过

- **数据管道完整**: WebSocket → Provider → ChatMessageModel → UX envelope
- **UI 渲染不完整**: `structured_cognitive_adjustments` 数组被存储但没有专用 widget 遍历渲染
  - evolution_card 渲染 `one_key_adjustment` 等单个字段，但不循环 `structured_cognitive_adjustments` 列表
  - 建议：Phase 4 活体验打磨时添加专用 CognitiveAdjustmentChip 列表 widget

---

## 新发现：审查 #1 遗漏的 P0 问题

### C-04 (新发现): orchestrator_production.py 已正确传 Spine context，但 adapter 未跟进

**文件**: `backend/app/orchestration/orchestrator_production.py` lines 1157-1159 vs `multi_agent_adapter.py` lines 258-271, 454-467
**性质**: C-03 的细化 — production orchestrator 已经做了正确的事，但 multi_agent_adapter 是独立的 code path 没有同步
**修复**: 在 multi_agent_adapter.py 的两个 `build_system_prompt` 调用中，参照 `orchestrator_production.py` 的参数列表传入 `spine_response_directive`, `spine_chronicle_summary`, `spine_fatigue_context`

---

## Tracker 状态更新建议

| Item | 更新 |
|------|------|
| C-01-FIX | 保持 🔴 — 仍未修 |
| C-02-FIX | 更新为 ✅ — 通过 prompt_instruction property 已修复 |
| C-03-FIX | 保持 🔴 — 仍未修 |
| T1.2.5 | 保持 ✅ — 数据管道完整, UI 渲染缺口留到 Phase 4 |
| M-01-FIX (Flutter 解析) | 更新为 ✅ — T1.2.5 已完成 Flutter 侧解析 |

---

> **总结**: 3 个 P0 中 1 个已修复 (C-02)，2 个仍未修 (C-01 OutcomeTracker 接线, C-03 multi_agent_adapter)。Codex 的 3 个新任务全部验收通过。下一步仍应优先修复 C-01 和 C-03。
