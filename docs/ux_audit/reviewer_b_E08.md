# Reviewer B — E08: WebSocket断线重连——移动端恢复机制
Timestamp: 2026-04-26T11:35:00+08:00
Chain Index: 25 (Round 4 — E-chain audit)

## Chain Flow Summary
WebSocket 连接由 `WebsocketChatServiceV2` 管理。断线时 `_onDone` 触发 `_triggerReconnect`，使用 6 级退避调度（800ms→1200ms→2200ms→4200ms→8200ms→12200ms + 250ms jitter），最多 6 次重试。重连成功后 `chat_screen.dart:220-227` 调用 `loadConversationHistory` 重新加载消息。连接状态通过 `WsConnectionState` enum 流式传播到 UI——`reconnecting` 时显示 loading toast，`connected` 时显示 success toast，`failed` 时显示 error toast。超过 6 次重试后丢弃 pending messages 并通知用户。

## Critical Issues 🔴
None found.

## Major Issues 🟡
None found.

## Minor Issues 🟢
**`mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1955-1971`**: 超过 max reconnect attempts（6 次）后，pending messages 被丢弃并通知用户（"有 N 条未发送消息因网络连接失败被丢弃"）。但用户无法重试这些被丢弃的消息——`_failPendingMessages` 将它们标记为失败后没有重试入口。Expected: 用户在恢复网络后能重新发送被丢弃的消息。Actual: 被丢弃的消息永久丢失，用户需要重新输入。影响有限——用户收到明确提示后可重新输入，但体验不够流畅。

## Working Well ✅
- **`websocket_chat_service_v2.dart:1089-1097`**: 6 级退避调度合理——800ms 起步，最大 12.2s，有 250ms jitter 防惊群。总等待时间 ~30s 后放弃。
- **`websocket_chat_service_v2.dart:1946-1994`**: `_triggerReconnect` 实现完整——状态管理（reconnecting/failed）、jitter、attempt counter、消息丢弃通知。
- **`chat_screen.dart:211-233`**: 三态 UI 反馈完善——reconnecting→loading toast, connected→success toast + 历史重载, failed→error toast。
- **`chat_screen.dart:220-227`**: 重连成功后主动调用 `loadConversationHistory` 补偿断线期间可能丢失的消息。
- **`chat_screen.dart:1769-1784`**: `retryLastMessage` 方法支持用户手动重试最后一条失败消息。
- **`websocket_chat_service_v2.dart:2089-2097`**: Heartbeat 监控——stream active 时抑制心跳重连，过多心跳失败才触发重连，避免误判。
- **`websocket_chat_service_v2.dart:2193-2202`**: `manualReconnect` 允许用户手动触发重连（重置 attempt counter），提供恢复手段。

## Files Examined
- `mobile/lib/core/services/websocket_service.dart` (167 lines — base service)
- `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart` (lines 1085-1097, 1940-1994)
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart` (lines 63-71, 105-111, 1769-1784)
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart` (lines 205-234)
- `mobile/lib/features/chat/data/repositories/chat_repository.dart` (lines 66-73)

## Confidence: High — 重连退避、UI 反馈、历史补偿全链路已通过代码确认。
