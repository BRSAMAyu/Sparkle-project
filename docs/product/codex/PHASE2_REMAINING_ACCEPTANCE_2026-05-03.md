# Phase 2 Remaining Acceptance Matrix — 2026-05-03

## Scope

本轮只验收用户列出的 8 个 Phase 2 剩余项，并把状态从“待办”重新校准为“已实现 / 已接线 / 待人工视觉验收”。重点不是再开新方向，而是确认这些能力是否已经进入用户可见主路径。

## Acceptance Matrix

| Item | Status | Evidence |
|---|---|---|
| KG-005 错因到任务模板闭环 | Accepted | `ErrorPatternTemplateService` 已存在；`/errors/remediable-patterns`、`/error-book/remediable-patterns`、generate/accept template API 已接入；ErrorBook 与 Insights 均展示 `RemediablePatternsCard`。 |
| KG-009 “为什么学这个” priority reasoning | Accepted | `TaskPriorityService` 已存在；`GET /tasks/{task_id}/priority-reasoning` 已接入；移动端 `WhyThisTodayPanel` 已进入 task card、task detail、execution screen。 |
| GOAL-012 策略迁移 UI | Accepted | `StrategyBeliefService` + `/cognitive/alternative-strategies` + `/cognitive/strategies/migrate` 已接入；目标详情页展示 `StrategyMigrationWizard`。本轮修复了 deprecated `RadioListTile` warning，改为高影响策略候选卡。 |
| GOAL 创建向导 | Accepted | `GoalCreationWizardScreen`、`GoalRoutes.create`、`POST /goals/decompose-preview`、`POST /goals` 已接入。本轮修复嵌入式 `onCreated` 回调后仍自动路由导致测试超时的问题。 |
| COM-011 社群目标关联 | Accepted | `find_users_with_similar_goals` + `/community/goals/{goal_id}/similar-pursuers` 已接入；目标详情页展示 `SimilarGoalPursuersCard`。 |
| TASK-014 Directive 审计 UI | Accepted | `RecentDirectiveAuditService` + `/insights/recent-directives` 已接入；移动端 `DirectiveAuditScreen` 已挂到 Insights routes。 |
| Source 生命周期 badge | Accepted | `SourceLifecycleBadgeGroup` 已进入 task card、task detail、execution screen；后端 task detail 返回 `bound_sources` with `lifecycle_status`。 |
| 社群资料质量显示 | Accepted | 社群 resource quality 后端排序/隐藏/反馈已接入；移动端 `SharedResourceCard` 展示 quality score、adoption count 和质量徽章。 |

## Fixes Applied In This Pass

- 修复 `mobile/lib/features/plan/presentation/screens/sprint_screen.dart` 中 `_NoActiveSprintView` 缺少类闭合括号导致的全局 Flutter 编译失败。
- 修复 `mobile/lib/features/user/presentation/screens/security_log_screen.dart` 中 `build()` 方法闭合问题导致的类嵌套解析错误。
- 将 `StrategyMigrationWizard` 的候选策略选择从 deprecated `RadioListTile.groupValue/onChanged` 改为自绘候选卡，避免 Flutter 3.32+ warning。
- 修复 `GoalCreationWizardScreen` 在传入 `onCreated` 回调时仍自动导航导致 widget test `pumpAndSettle` 超时的问题。

## Verification

Backend:

```bash
cd backend && python3 -m py_compile app/api/v1/error_book.py app/services/error_pattern_template_service.py app/services/task_priority_service.py app/api/v1/tasks.py app/api/v1/goals.py app/services/strategy_belief_service.py app/api/v1/cognitive.py app/api/v1/insights.py app/services/directive_audit_service.py app/api/v1/community.py app/services/community_service.py
cd backend && .venv/bin/python -m pytest tests/services/test_error_pattern_template_service.py tests/test_api/test_error_pattern_template_api.py tests/api/test_task_priority_reasoning_api.py tests/services/test_goal_strategy_services.py tests/unit/test_com011_similar_goal_pursuers.py tests/api/test_p2_06_source_and_directive_audit.py tests/test_fv22_resource_quality.py -q
```

Result: `50 passed`.

Mobile:

```bash
cd mobile && flutter test test/features/goal/presentation/goal_creation_wizard_screen_test.dart test/features/cognitive/presentation/strategy_migration_wizard_test.dart test/widget/p2_06_lifecycle_directive_audit_test.dart test/widget/remediable_patterns_card_test.dart test/widget/shared_resource_card_test.dart test/features/task/presentation/widgets/why_this_today_panel_test.dart
cd mobile && flutter analyze --no-fatal-infos lib/features/cognitive/presentation/widgets/strategy_migration_wizard.dart lib/features/goal/presentation/screens/goal_creation_wizard_screen.dart lib/features/plan/presentation/screens/sprint_screen.dart lib/features/user/presentation/screens/security_log_screen.dart
```

Result: widget tests `12 passed`; analyzer has no errors/warnings, info-only style findings remain.

## Remaining Risk

这些项目已达到代码级验收，但仍需要真实设备视觉验收：目标详情、任务执行页、Insights 决策日志、ErrorBook、社群资料卡在小屏幕、深色模式、中文长文案下的排版。该风险属于产品 QA，不再是 Phase 2 功能缺口。
