# Reviewer B — C03: 任务卡点(stuck)→卡点帮助面板→Aurora诊断内容
Timestamp: 2026-04-25T23:50:00+08:00
Chain Index: 10 (Round 2 re-audit)

## Chain Flow Summary
用户在任务执行中点击"卡住了"按钮，弹出 StuckHelpSheet bottom sheet。该 sheet 读取任务预生成的 guideJson 中的诊断内容（micro_teaching / stuck_help 字段），展示两步帮扶（诊断问题 + 精准修复）。用户也可以点击"和Sparkle聊聊"跳转 chat，此时 decision_loop 检测到 stuck stage 并生成 diagnostic 类型回复。

## Critical Issues 🔴
None found.

## Major Issues 🟡
**`mobile/lib/features/task/presentation/screens/task_execution_screen.dart:468-478`**: "和Sparkle聊聊"跳转 chat 时用 `chat_mode=study_plan` + `prompt`，但没有携带当前 task 的上下文（如 task_id、sprint_pack_node_id）。Expected: chat 打开后 Aurora 知道用户是在哪个任务上卡住了。Actual: 只有 `prompt` 文本（含任务标题），Aurora 通过 prompt 文本猜测上下文，可能丢失结构化信息。Severity 降为 🟡 因为 prompt 里包含了任务标题，但缺少 node_id 等结构化引用。

## Minor Issues 🟢
None found.

## Working Well ✅
- **`backend/app/orchestration/task_card_generator.py:563-617`**: `_build_stuck_help()` 在任务创建时就预生成了高质量诊断内容（diagnosis_question + diagnosis_options + targeted_fix + check_question），并根据模板类型适配不同场景（流程追踪/对比表/通用）。
- **`mobile/lib/features/task/presentation/widgets/stuck_help_sheet.dart:393-437`**: `_readMicroTeaching()` 容错地读取多个可能的字段名（micro_teaching / stuck_micro_teaching / aurora_stuck_help / stuck_help / diagnostic_help），确保兼容不同命名。
- **`stuck_help_sheet.dart:27-32`**: 三级 fallback 策略合理：microTeaching → fallbackLevels → genericSuggestions。
- **`backend/app/aurora/runtime_v1/decision_loop.py:641-644`**: stuck 检测逻辑清晰，`STUCK_TASK_STAGE_TOKENS = {"stuck", "blocked"}`。
- **`decision_loop.py:728-734`**: stuck 场景的标准层契约要求 must_include `mistake_diagnosis` 和 `one_targeted_fix`，确保诊断内容不空洞。
- **`task_execution_screen.dart:575-594`**: stuck 帮助按钮有 FAB 浮动按钮入口，可见性好。

## Files Examined
- `backend/app/aurora/runtime_v1/decision_loop.py` (lines 51, 87, 93, 120-126, 630-644, 658-659, 724-734, 984-991, 1255-1259)
- `backend/app/aurora/runtime_v1/service.py` (lines 602-632)
- `backend/app/orchestration/task_card_generator.py` (lines 240-290, 563-617)
- `mobile/lib/features/task/presentation/widgets/stuck_help_sheet.dart` (full file, 479 lines)
- `mobile/lib/features/task/presentation/providers/task_provider.dart` (lines 570-650)
- `mobile/lib/features/task/presentation/screens/task_execution_screen.dart` (lines 445-504, 575-594)

## Confidence: High — 所有 key_files 已亲自读取，关键代码行号已确认。
