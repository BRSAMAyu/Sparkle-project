# Reviewer A — E13: 呼吸练习→任务/专注集成
Timestamp: 2026-04-26T13:15:00+08:00
Chain Index: 21

## Chain Flow Summary
呼吸练习有两种实现：(1) BreathingTool（工具页面，独立呼吸工具）和 (2) MindfulnessModeScreen（正念专注模式，绑定任务）。正念模式有完整的后端同步链路（focus_statistics_provider.saveSession → 后端focus_service → achievement_engine），但独立的BreathingTool完成时**仅显示本地toast、不保存任何数据、不通知后端**。Aurora完全无法感知用户做了呼吸练习（除非走正念模式）。

## Critical Issues 🔴

**mobile/lib/features/tools/presentation/widgets/breathing_tool.dart:584-618 (_handleCompletion)**: BreathingTool完成时仅做三件事：(1) 触觉反馈 `SensoryFeedbackService.emit`，(2) TTS播报"练习完成"，(3) 本地toast `AppFeedback.success`。不保存任何数据到后端、不发布EventBus事件、不调用任何API。Expected: 完成记录持久化，至少记录到专注统计。Actual: 关掉屏幕后数据完全消失，用户做100次呼吸练习也不会在任何统计页面看到痕迹。Evidence: `_handleCompletion`方法无任何网络请求或本地持久化调用（除`_clearPersistedSession`清除会话状态）。

## Major Issues 🟡

**mobile/lib/features/tools/presentation/widgets/breathing_tool.dart (全文)**: BreathingTool是一个完全独立的本地工具，与Sparkle的任何后端系统零集成。behavior_signal_collector.py中无"breathing"相关代码，后端无"breathing"关键词。Expected: 呼吸练习完成数据被behavior_signal_collector捕获，流入context_manager供Aurora感知用户情绪/压力状态。Actual: 后端完全不知道呼吸练习的存在。Aurora无法根据用户是否做过呼吸练习调整建议或语气。

**mobile/lib/features/tools/presentation/widgets/breathing_tool.dart:620-639 (_stopBreathing)**: 用户手动停止练习（不等到完成）时，数据同样完全丢失。Expected: 部分完成的练习也应记录（如已做3分钟/5分钟目标）。Actual: `_stopBreathing`直接清空所有状态，无任何数据留存。

## Minor Issues 🟢

None found — the gap is structural, not polish-level.

## Working Well ✅

- **MindfulnessModeScreen** (正念模式)有完整的数据流：mindfulness_provider.stop() → focus_statistics_provider.saveSession() → 后端focus_service → process_event(STUDY_MINUTES_ACCUMULATED) → achievement_engine → WebSocket通知。正念模式完成后的专注记录、mastery更新、成就触发全部通畅。
- **MindfulnessModeScreen 会话持久化**：SharedPreferences存储活跃会话（start_time、pause状态、interruption列表），app切后台回来可恢复。
- **MindfulnessModeScreen 退出流程**：退出时显示FocusSessionSummaryDialog（含flame奖励和mastery更新），然后`context.pop()`返回上一页。
- **MindfulnessModeScreen 中断检测**：didChangeAppLifecycleState检测app切换，recordInterruption记录中断次数，>3次标记为'interrupted'。
- **BreathingTool 本地功能完善**：3种呼吸模式(4-7-8/方块/舒缓)、4种时长(1/3/5/8分钟)、TTS语音引导、暂停/恢复、后台完成通知、触觉反馈、SharedPreferences持久化活跃会话。
- **BreathingTool 后台完成通知**：didChangeAppLifecycleState在切后台时通过notification_service调度完成通知，用户可在通知栏看到"呼吸练习完成"。

## Files Examined
- mobile/lib/features/tools/presentation/widgets/breathing_tool.dart (full, 884 lines)
- mobile/lib/features/focus/presentation/screens/mindfulness_mode_screen.dart (full, 581 lines)
- mobile/lib/features/focus/presentation/providers/mindfulness_provider.dart (full, 581 lines)
- backend/app/services/focus_service.py (lines 110-160, achievement integration)
- backend/app/services/behavior_signal_collector.py (grep for "breathing/breath" — zero matches)
- backend/app/orchestration/ux_envelope.py (line 1420, mindfulness route reference)
- mobile/lib/features/focus/presentation/providers/focus_statistics_provider.dart (referenced by mindfulness_provider)
- mobile/lib/features/focus/focus_routes.dart

## Confidence: High — read all relevant source files in full, confirmed zero backend integration for BreathingTool, confirmed MindfulnessModeScreen has complete data flow.
