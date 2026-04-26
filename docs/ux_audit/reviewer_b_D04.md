# Reviewer B — D04: 日历→Aurora感知——AI教练知道用户日程吗
Timestamp: 2026-04-26T01:30:00+08:00
Chain Index: 18 (Round 3 — D-chain audit)

## Chain Flow Summary
用户在 Flutter 创建/编辑任务时，`CalendarRepository.syncTaskLinkedEvent` 自动在 `CalendarEvent` 表创建对应日历事件。`ContextManager._get_calendar_context` 查询该表，提取 `upcoming_deadlines`（仅 task_id/plan_id 关联事件）、`time_blocks_today`、`workload_density`、`exam_urgency` 四维数据。`prompts.py:_format_calendar_context_lines` 将其渲染为【时间约束】section 注入 Aurora prompt。Kill switch 默认 "live"（`settings.py:345`），calendar 数据默认流入 prompt。Dashboard wake tokens 含 time 类（schedule/deadline/days_remaining 等）。

## Critical Issues 🔴
None found.

## Major Issues 🟡
**`backend/app/orchestration/adaptive_replanner.py` + `backend/app/orchestration/planning_workflow.py`**: 自动化计划生成和自适应压缩完全不引用 calendar context。`adaptive_replanner.py` 的 `should_compress` 仅看 `completion_rate < 0.5 && days_left <= 5`，不看用户当日是否有考试/上课冲突。`planning_workflow.py` 生成每日任务 spec 时不参考 `time_blocks_today`（用户可用时间段）。Expected: 计划生成考虑用户当日实际可用时间，压缩决策考虑考试/上课冲突。Actual: Aurora 在 chat 中能看到【时间约束】并口头上建议调整，但自动生成的计划完全忽略日历。用户看到"今天有考试"却仍收到满负荷计划，只能手动调整。Evidence: `adaptive_replanner.py` 和 `planning_workflow.py` 中零 calendar 相关引用（grep 确认）。

## Minor Issues 🟢
**`backend/app/aurora/runtime_v1/service.py`**: 每日启动个性化消息（C09）构建时不参考 calendar context，不主动提及"今天你有 X 小时可用"或"今天有考试"。对 chat 交互影响较小（Aurora 在后续对话中能看到 calendar），但首屏启动消息缺失时间上下文。

## Working Well ✅
- **`backend/app/core/context_manager.py:513-584`**: `_get_calendar_context` 实现完整——查询 today + week 事件，推导可用时间段和工作密度，kill switch 检查，空数据时优雅返回空 dict。
- **`backend/app/orchestration/prompts.py:3007-3042`**: `_format_calendar_context_lines` 渲染清晰——任务密度、近 7 天截止、今日可用时间段、考试倒计时，每项格式化合理。
- **`prompts.py:3332-3342`**: 双路径渲染——有完整数据时渲染【时间约束】，仅有 exam_urgency 时降级渲染【考试紧迫度】，确保紧急考试信息不丢失。
- **`mobile/lib/features/calendar/data/repositories/calendar_repository.dart:229-244`**: `syncTaskLinkedEvent` 自动双向同步任务到日历事件，用户无需手动创建。
- **`settings.py:345`**: Kill switch 默认 "live"，calendar 数据默认启用。

## Files Examined
- `backend/app/core/context_manager.py` (lines 513-584)
- `backend/app/orchestration/prompts.py` (lines 3007-3050, 3325-3342)
- `backend/app/orchestration/adaptive_replanner.py` (full file grep — zero calendar references)
- `backend/app/orchestration/planning_workflow.py` (full file grep — zero calendar references)
- `backend/app/aurora/runtime_v1/service.py` (grep for calendar — only hardcoded string)
- `backend/app/aurora/runtime_v1/dashboard.py` (lines 80-109, time wake tokens)
- `backend/app/config/settings.py` (line 345, default "live")
- `backend/app/services/aurora_stage40_calendar_kill_switch_service.py` (kill switch binding)
- `mobile/lib/features/calendar/data/repositories/calendar_repository.dart` (lines 225-244)
- `backend/app/api/v1/calendar.py` (CRUD endpoints verified)

## Confidence: High — calendar 数据流入 prompt 已完整追踪；planning/adaptive 不引用 calendar 已通过 grep 确认零匹配。
