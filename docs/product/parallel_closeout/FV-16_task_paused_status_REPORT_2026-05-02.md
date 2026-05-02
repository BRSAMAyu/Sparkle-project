# FV-16 · 任务 PAUSED 状态 + 恢复工作流 · 完成报告

**Agent**: codex-agent-FV16
**Branch**: codex/FV-16-task-paused-status
**Date**: 2026-05-02
**Status**: COMPLETED

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | `pause_task(task_id, reason)` / `resume_task(task_id)` | ✅ | `backend/app/services/task_service.py:374` / `backend/app/services/task_service.py:433` 增加 ID 级服务入口。 |
| 2 | `TaskStatus` enum 加 `PAUSED` | ✅ | `backend/app/models/task.py:49` 与 `mobile/lib/shared/entities/task_model.dart:28` 均支持 PAUSED。 |
| 3 | 数据库迁移 | ✅ | `backend/alembic/versions/c21_20260502_task_paused_status.py:24` 为 PostgreSQL enum 追加 `PAUSED`。 |
| 4 | PAUSED → resume 显示恢复卡 | ✅ | `mobile/lib/features/task/presentation/screens/task_detail_screen.dart:142` 复用 `StaleRecoveryCard`，从 `pause_state.paused_at` 计算离开时间。 |
| 5 | 离开超过预期任务时长 50% 自动 PAUSED + 恢复提醒 | ✅ | `mobile/lib/features/task/presentation/screens/task_execution_screen.dart:249` 自动暂停；`mobile/lib/core/services/task_notification_scheduler.dart:181` 触发恢复提醒。 |
| 6 | 前端任务卡 pause 按钮 + paused 状态展示 | ✅ | `mobile/lib/features/task/presentation/widgets/task_card.dart:351` 增加 pause/resume 控件；`mobile/lib/features/task/presentation/screens/task_list_screen.dart:17` 增加 paused 筛选。 |
| 7 | Outcome：PAUSED 不算失败/成功，记录 `paused_count` | ✅ | `backend/app/services/task_service.py:339` 写入 `paused_count` 的中性 actual outcome，不调用成功/失败 self-model 分支。 |
| 8 | 单测 + 集成测 | ✅ | 新增 `backend/tests/test_plan_task_service_production.py` pause/resume 单测与 `backend/tests/api/test_task_quick_actions_api.py` API 集成测。 |

## 2. 文件变更清单

```text
backend/app/api/v1/tasks.py                        |  39 +-
backend/app/models/task.py                         |   1 +
backend/app/schemas/task.py                        |   6 +
backend/app/services/task_service.py               | 151 +++++++-
backend/alembic/versions/c21_20260502_task_paused_status.py | new
backend/tests/api/test_task_quick_actions_api.py   |  32 ++
backend/tests/test_plan_task_service_production.py | 406 +++++++++++++++++----
mobile/lib/core/network/api_endpoints.dart         |  16 +
mobile/lib/core/services/task_notification_scheduler.dart | 19 +
mobile/lib/features/task/**                        | pause/resume UI + recovery flow
mobile/lib/shared/entities/task_model.dart         |   2 +
mobile/lib/shared/entities/task_model.g.dart       |   1 +
mobile/lib/shared/utils/entity_card_payloads.dart  |   2 +
```

## 3. 测试证据

### 单测
```text
cd backend && pytest tests/test_plan_task_service_production.py -k "pause or resume"
3 passed, 52 deselected in 12.41s
```

### 集成测
```text
cd backend && pytest tests/api/test_task_quick_actions_api.py -k "pause_and_resume"
1 passed, 7 deselected in 7.60s
```

### Lint / 类型 / Guard
```text
cd backend && python3 -m py_compile app/models/task.py app/schemas/task.py app/services/task_service.py app/api/v1/tasks.py alembic/versions/c21_20260502_task_paused_status.py
PASS (no output)

cd mobile && flutter analyze --no-fatal-infos <FV16 touched dart files>
exit code 0; only info-level existing lint style items reported, no warnings/errors.
```

`cd backend && alembic heads` currently fails before reaching FV16 migrations because `backend/app/models/community_privacy.py` defines a declarative attribute named `metadata`, which SQLAlchemy reserves. This appears to be from another parallel FV card and needs architect integration before `make sync-db` can be replayed.

## 4. 用户视角变化

> 在任务执行中，用户现在能暂停一个任务、稍后从恢复卡继续，并且这个暂停不会被 Sparkle 当成失败。

具体场景：
- 之前：任务只有 start/stuck/complete/abandon，临时离开要么继续挂着，要么只能放弃。
- 之后：任务卡、长按菜单和执行页都能暂停/恢复；长时间退出执行页会自动暂停并发恢复提醒。

## 5. 与其他卡片的协调

- 与 FV-13 协调：本卡在移动端触发本地恢复提醒，未修改通知中心模型或 FV-13 的通知价值字段。
- 与其他移动 UI 卡片：只补齐 `TaskStatus.paused` 的必要 switch case，避免新增 enum 造成编译缺口。
- 留给 Architect：在其他并行迁移合并后重跑 Alembic heads / `make sync-db`。

## 6. 已知限制 / 后续

- `StaleRecoveryCard` 原文案来自 chat stale recovery，已复用交互组件；后续可在共享 design-system 层抽出更通用的 TaskRecoveryCard。
- 恢复提醒目前使用本地 smart push，服务端推送由 FV-13 通知域统一收口更合适。
- 当前工作区有大量其他 FV 分支的未提交变更，本报告的 diff stat 只覆盖 FV16 触及文件。

## 7. 验收命令一键回放

```bash
cd backend && pytest tests/test_plan_task_service_production.py -k "pause or resume"
cd backend && pytest tests/api/test_task_quick_actions_api.py -k "pause_and_resume"
cd backend && python3 -m py_compile app/models/task.py app/schemas/task.py app/services/task_service.py app/api/v1/tasks.py alembic/versions/c21_20260502_task_paused_status.py
cd mobile && flutter analyze --no-fatal-infos lib/shared/entities/task_model.dart lib/shared/utils/entity_card_payloads.dart lib/features/task/presentation/widgets/task_card.dart lib/features/task/presentation/screens/task_detail_screen.dart lib/features/task/presentation/screens/task_execution_screen.dart lib/features/task/presentation/screens/task_list_screen.dart lib/features/task/data/repositories/task_repository.dart lib/features/task/presentation/providers/task_provider.dart lib/core/services/task_notification_scheduler.dart lib/features/home/presentation/widgets/calendar/compact_task_card.dart lib/features/plan/presentation/screens/plan_detail_screen.dart lib/features/calendar/presentation/providers/calendar_provider.dart
```
