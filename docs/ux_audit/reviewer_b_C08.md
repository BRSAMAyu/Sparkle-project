# Reviewer B — C08: 用户≥3天未活跃→comeback消息出现在chat首屏
Timestamp: 2026-04-26T00:58:00+08:00
Chain Index: 15 (Round 2 re-audit)

## Chain Flow Summary
用户打开 app 进入 chat 页时，`chat_screen.dart` 调用 `_hydrateComebackMessage()`（如果 `_canShowAuroraOpenerOver` 返回 true）。该函数通过 `auroraDailyStartupRepositoryProvider.getComebackContext()` 调用后端 `get_comeback_context` API。后端检查 `user.last_login_at` 与当前时间的差值，如果 >= 3 天且有活跃冲刺计划，构建个性化 comeback 消息（含天数、剩余天数、下次任务、保底方案）。前端收到后通过 `chatProvider.showComebackMessage` 插入聊天消息，并自动选择对应的计划 session。

## Critical Issues 🔴
None found.

## Major Issues 🟡
**`backend/app/aurora/runtime_v1/service.py:306-310`**: Comeback 检测基于 `user.last_login_at`，不是真实的最后活跃时间。Expected: 基于用户最后一次在 app 中的有意义操作（如完成任务、发送 chat 消息）。Actual: 基于 `last_login_at`，这个字段通常只在 JWT 认证时更新，可能不代表真实的活跃间隔。如果用户在 app 内活跃但未重新认证，`last_login_at` 不会更新，导致 comeback 消息在用户实际上每天都活跃的情况下也出现。Severity 降为 🟡 因为大多数场景下用户多日不打开 app 时确实会重新登录。

## Minor Issues 🟢
None found.

## Working Well ✅
- **`backend/app/aurora/runtime_v1/service.py:282-361`**: `get_comeback_context` 逻辑完善——检查用户活跃状态、查找活跃计划、计算剩余天数、找下一个未完成任务、生成个性化消息。
- **`mobile/lib/features/chat/presentation/screens/chat_screen.dart:440-488`**: `_hydrateComebackMessage` 有完整的去重逻辑（signature check line 459-463），5秒超时保护（line 451），多层 `_canShowAuroraOpenerOver` 检查防止在已有消息时覆盖。
- **`chat_screen.dart:465-474`**: 如果用户没有选中计划，自动切换到 comeback 关联的计划 session。
- **`mobile/lib/features/chat/presentation/providers/chat_provider.dart:775-795`**: `showComebackMessage` 正确清理已有的 comeback 消息再插入新的，使用 `comeback_` 前缀 ID 便于识别。
- **`chat_screen.dart:496`**: comeback 消息不会被通用欢迎消息覆盖。

## Files Examined
- `backend/app/aurora/runtime_v1/service.py` (lines 282-361, 1724-1770)
- `backend/app/api/v1/aurora.py` (comeback endpoint via grep)
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart` (lines 440-496)
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart` (lines 775-795)
- `mobile/lib/features/aurora/data/repositories/aurora_daily_startup_repository.dart` (verified via grep)

## Confidence: High — 后端 comeback 检测和前端展示的完整链路已确认。
