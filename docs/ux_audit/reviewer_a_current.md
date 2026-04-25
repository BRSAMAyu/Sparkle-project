# Reviewer A — D03: 专注模式→计划/任务联动——专注完成是否更新任务进度
Timestamp: 2026-04-26T01:45:00+08:00
Chain Index: 11

## 自我审查声明

本报告所有发现已通过亲自阅读源代码确认。关键验证：(1) `mindfulness_provider.dart` 的 `stop()` 方法 grep `invalidate|taskListProvider` 结果为 0 — 确认无 provider invalidation；(2) `focus_service.py:174-186` 事件 payload 不含 `task_id` — 确认事件无法被 task 消费者关联；(3) `plans.py:1391` `total_minutes_spent` 硬编码为 0 — 确认专注时长未集成到计划进度。

## Chain Flow Summary

用户从任务详情进入专注模式（mindfulness_mode_screen 接收 taskId），计时器本地运行（Timer.periodic），完成后 `mindfulness_provider.stop()` 调用 `focusStatisticsProvider.saveSession()` 记录会话（含 task_id）到后端 API。后端 `focus_service.log_session()` 创建 FocusSession 记录、计算 Galaxy mastery boost、发布 `focus.session.completed` EventBus 事件。但专注完成**不触发任何任务进度更新**，不 invalidation 任务 provider。

## Critical Issues 🔴

**1. `focus_service.py:174-186`: `focus.session.completed` 事件不含 `task_id`，且无消费者将专注时长转为任务进度**

后端发布 `focus.session.completed` 事件（line 174-186），payload 包含 `session_id`、`duration_minutes`、`mastery_updates`，但**不包含 `task_id`**。即使有消费者监听此事件，也无法将专注会话关联到具体任务。

同时，`event_bus.py` 中无任何 `focus` 相关的事件类定义。grep `focus|FocusSession` 在 event_bus.py 结果为 0。这意味着专注完成是一个**数据孤岛** — 记录了，但不被任何下游系统消费。

Expected: 专注完成一个番茄钟后，对应任务的进度（time_spent / progress）应该更新，用户在任务列表看到实际投入时间。Actual: 专注完成只记录 FocusSession 行，任务进度不变。

**2. `plans.py:1391`: `total_minutes_spent` 硬编码为 0，专注时长未集成到计划进度**

```python
"total_minutes_spent": 0,  # Would be calculated from focus sessions
```

这行注释直接说明：专注时长本应从 FocusSession 汇总计算，但此集成**未实现**。计划进度页无法显示用户在某个冲刺上实际投入的时间。

Expected: 计划页显示"已投入 45 分钟"（从 FocusSession 汇总）。Actual: 永远显示 0。

## Major Issues 🟡

**3. `mindfulness_provider.dart`: 专注完成后不 invalidation 任何 task provider**

grep `invalidate|taskListProvider` 在 mindfulness_provider.dart 结果为 0。专注完成后，任务列表页、任务详情页的 provider 不会被刷新。如果后端确实更新了某些关联数据（如 mastery），用户需要手动离开再返回才能看到变化。

## Minor Issues 🟢

None found.

## Working Well ✅

**专注会话记录** (`mindfulness_provider.dart:296-306`):
- `saveSession()` 正确传递 `taskId`（line 303）和 `taskTitle`（line 304）
- 后端 `focus_service.log_session()` 正确创建 FocusSession 记录（含 `task_id` 字段）
- 返回值包含 `mastery_updates`（Galaxy 掌握度提升）和 `flame_earned`（火苗奖励）

**专注会话完成 UI** (`mindfulness_mode_screen.dart:224-236`):
- 有 mastery 更新时显示 `showFocusSessionSummaryDialog`（line 225-230）
- 无更新时显示 `AppFeedback.info`（line 232-233）
- 完成后 `context.pop()` 返回上一页（line 235）

**Galaxy mastery 集成** (`focus_service.py`):
- 如果 task 关联 Galaxy node，专注完成会触发 mastery boost（line 165-171）
- mastery_updates 返回给前端并在 dialog 中展示

**离线保存降级** (`mindfulness_provider.dart:358-359`):
- 如果后端同步失败，显示"专注记录已离线保存，稍后会自动重试同步"
- `savedLocally` 标记区分本地 vs 远程保存状态

## Files Examined

1. `mobile/lib/features/focus/presentation/providers/mindfulness_provider.dart` (lines 285-399, stop() with saveSession + event recording)
2. `mobile/lib/features/focus/presentation/screens/mindfulness_mode_screen.dart` (lines 200-238, exit flow + result handling)
3. `mobile/lib/features/focus/data/repositories/focus_repository.dart` (lines 67-102, saveSession with task_id)
4. `mobile/lib/features/focus/data/models/focus_session_model.dart` (taskId field in session model)
5. `backend/app/api/v1/focus.py` (lines 47-78, log_focus_session endpoint)
6. `backend/app/services/focus_service.py` (lines 165-190, mastery boost + event bus publish)
7. `backend/app/core/event_bus.py` (no focus-related event classes defined)
8. `backend/app/api/v1/plans.py` (line 1391, hardcoded total_minutes_spent = 0)

## Confidence: High — 端到端链路完整追踪。核心问题明确：专注完成 → FocusSession 记录 → mastery boost → EventBus 事件（无 task_id），但 → 任务进度 的链路完全断裂。这是产品级集成缺口而非 bug。
