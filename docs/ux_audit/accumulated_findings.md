# Sparkle UX Audit — Accumulated Findings

> **Purpose**: All validated UX issues found across the full system audit.
> **Updated by**: Validator agent after each review cycle.
> **Status**: 2 / 20 chains audited

---

<!-- FINDINGS APPENDED BELOW BY VALIDATOR -->

---
## Round 1 — 2026-04-25
*Reviewer A: C01 — 冷启动建模→计划生成→首个任务可见 | Reviewer B: C06 — Galaxy节点点击→节点详情→开始复习进入chat携带context*

> **Note**: C02–C05 原始发现已被后续 reviewer 轮次覆盖丢失。C03/C04/C05 在 audit_state.json 标记 "done" 但无验证过的发现。需 architect 安排重新审查。

### C01: 冷启动建模→计划生成→首个任务可见 (Reviewer A)

**Critical Issues 🔴**
- **`planning_workflow.py:770` + `orchestrator.py:652-654` + `modeling_chat_screen.dart:729-732`**: 建模→规划桥接始终需要两轮"开始规划"才能产生 plan_id。第一轮：`from_modeling_complete=True` 导致 `fast_track_context` 保持 None（orchestrator.py:652 跳过 build、669 不注入），session 进入 AWAITING_CONFIRM（planning_workflow.py:770），返回策略提案无 plan_id。Mobile 端 line 731 抛异常"计划已经开始生成，但入口还没准备好"。第二轮："开始规划"匹配 PLANNING_CONFIRM_PATTERNS（line 58），触发 _handle_generating 成功。**影响：每个冷启动用户必现报错**。
- **`modeling_chat_screen.dart:744-748`**: 报错文案"计划生成遇到问题：Exception: 计划已经开始生成..."，实际是正常流程中间态。用户看到"遇到问题"以为失败。Expected: 显示"正在准备计划，点击确认"CTA。Actual: 错误卡片标题"计划生成没成功"（line 908-945）。

**Major Issues 🟡**
- **`modeling_chat_screen.dart:741` + `plan_routes.dart:163`**: 成功生成后 `context.go('/plans/{id}')`。plan_routes.dart:163 用 `parentNavigatorKey: navigatorKey`（root navigator），在 StatefulShellRoute 之外，底部 tab bar 消失。PlanDetailScreen:92 的 `context.pop()` 回到 root redirect → `/home`，断开了建模上下文。
- **`modeling_chat_screen.dart:738-740`**: 仅 invalidate `planDetailProvider` + `planListProvider`，遗漏 `learningPortfolioProvider`。用户导航到学习档案页看到旧数据。

**Minor Issues 🟢**
- **`modeling_chat_screen.dart:888-895`**: 第一轮加载文案"正在生成你的第一份冲刺计划"+"马上就会带你进入任务页"——但第一轮必定失败，设定错误预期。
- **`modeling_chat_screen.dart:615-624`**: `_finish()` 跳过路径直接 `context.go('/home')` 或 `/chat`，planning session 留在 AWAITING_CONFIRM 状态，无恢复机制。

**Working Well ✅**: Aurora 建模对话多轮追踪正确（conversationId、stream events、modeling_complete 检测）；plan_detail_screen 加载骨架屏、错误重试、自动检测冲刺完成均有；错误恢复 UI 有重试按钮。

---

### C06: Galaxy节点点击→节点详情→开始复习进入chat携带context (Reviewer B)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`chat_screen.dart`（全文件 grep `review_node` 无匹配）**: 复习 session 与普通 chat UI 完全相同，无 review header/banner/indicator。`chat_mode='study_plan'` 仅影响 prompt starters（line 1746），不影响 UI 布局。用户多轮对话后无法辨别自己在复习哪个节点。
- **`node_detail_sheet.dart:129-132` + `service.py:765-777`**: `initial_context` 仅包含 `{review_node, node_label}`，不传 mastery、学习次数、错题列表。后端 `_review_focus_from_context()` 也仅读 `review_node` 和 `node_label`。Aurora 无法基于掌握度定制复习内容。

**Minor Issues 🟢**
- **`node_detail_sheet.dart:342-348`**: "开始复习"按钮在 mastery=0 时仍可用且文案不变。Sheet 在 mastery=0 时显示"尚未学习"（line 278），但按钮未做条件适配（应显示"开始学习"）。
- **`node_detail_sheet.dart:206-254`**: Sheet 仅渲染节点名称、ID、掌握度百分比、统计 chips、错题预览。API 返回的 `description` 和 `keywords` 字段未被渲染（grep `description|keywords` 无匹配）。

**Working Well ✅**: 端到端导航链路完整（NodeDetailSheet → GoRouter → routes.dart query+extra 合并 → ChatScreen → WebSocket → Aurora `_review_focus_from_context()`）；Aurora 自动检测复习模式生成定点复习首条消息；0 mastery 友好处理（"尚未学习"而非"0%"）；Sheet 有 loading/error/retry 状态。

---

### Confirmed by Both Reviewers
无交叉确认（不同 chain）
