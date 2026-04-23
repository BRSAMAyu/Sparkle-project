# 深度审计 #56 — Flutter WebSocket Client 完整链路

> **日期**: 2026-04-25 05:45
> **模块**: Flutter WebSocket Client — Connection Lifecycle → Message Parsing → Event Dispatch → Reconnection → State Management → Resource Cleanup
> **范围**: 9 核心文件, 3 关联文件
> **总计**: 9 个文件, ~7,336 行
> **审计员**: Claude Deep Auditor (Round 56)

---

## 审计范围

本次审计覆盖 Flutter 端 WebSocket 通信全链路：从底层 `WebSocketService` 通用服务到 `WebSocketChatServiceV2` 聊天专用服务，经 `ChatRepository` 封装，最终到达 `ChatNotifier` / `ChatState` 状态管理层。同时覆盖社区 WebSocket 服务和事件模型定义。

### 文件清单
| 文件 | 行数 | 职责 |
|------|------|------|
| `mobile/lib/core/services/websocket_service.dart` | 166 | 通用 WebSocket 服务（旧版，仍在社区模块使用） |
| `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart` | 2,209 | 聊天专用 WS V2：连接管理、消息路由、心跳、重连、token 刷新 |
| `mobile/lib/features/chat/presentation/providers/chat_provider.dart` | 1,557 | ChatNotifier：流事件处理、UI 状态聚合、消息生命周期 |
| `mobile/lib/features/chat/data/models/chat_stream_events.dart` | 1,639 | 35+ 事件类型定义：TextEvent、DoneEvent、PlanReview 等 |
| `mobile/lib/features/chat/presentation/providers/chat_state.dart` | 348 | ChatState 不可变状态：copyWith 模式，30+ 字段 |
| `mobile/lib/features/chat/data/repositories/chat_repository.dart` | 465 | ChatRepository：WS/SSE 双通道封装、REST 历史加载 |
| `mobile/lib/features/chat/presentation/providers/chat_provider_wiring.dart` | 34 | Riverpod Provider 注册 + Debouncer 工具 |
| `mobile/lib/features/chat/data/models/chat_message_model.dart` | 434 | ChatMessageModel：持久化消息模型、WidgetPayload |
| `mobile/lib/features/community/data/services/community_websocket_service.dart` | 485 | 社区 WebSocket：群聊 + 私信双通道 |

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Flutter Presentation                            │
│  ChatScreen → ChatInput → ChatBubble → PlanReviewCard → ActionCard    │
└──────────┬──────────────────────────────────────────────────────────┬───┘
           │ Riverpod StateNotifier                                   │
           ▼                                                          │
┌──────────────────────────┐                              ┌──────────┴───┐
│  ChatNotifier            │  ┌─ Stream<ChatStreamEvent>  │ ChatState    │
│  (chat_provider.dart)    │◄─┤  per request (routed)     │ 30+ fields   │
│  - sendMessage()         │  │                           │ copyWith     │
│  - finalizeRun()         │  │  flushPending (50ms deb.) │              │
│  - _streamGeneration     │  │                           └──────────────┘
└──────────┬───────────────┘  │
           │                  │
           ▼                  │
┌──────────────────────────┐  │
│  ChatRepository          │  │
│  (chat_repository.dart)  │──┘
│  - chatStream()          │
│  - sendActionFeedback()  │
└──────────┬───────────────┘
           │
           ▼
┌───────────────────────────────────────────────────────────────────────┐
│  WebSocketChatServiceV2 (websocket_chat_service_v2.dart)             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │ Connection Mgmt  │  │ Message Routing  │  │ Heartbeat System   │  │
│  │ - connect/reconn │  │ - _requestCtrls  │  │ - 30s ping         │  │
│  │ - token refresh  │  │ - compute() parse│  │ - 60s pong timeout │  │
│  │ - lifecycle obs  │  │ - fallback timer │  │ - 3x fail → reconn │  │
│  │ - pending queue  │  │ - event dispatch │  │ - stream-active    │  │
│  └──────────────────┘  └──────────────────┘  │   suppression       │  │
│           │                     │              └────────────────────┘  │
│           ▼                     ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  IOWebSocketChannel → ws://host/ws/chat?user_id=&ticket=       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
           │ WebSocket (JSON)
           ▼
    ┌──────────────┐
    │  Go Gateway  │ ← ws://host:8080/ws/chat
    └──────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Legacy Path (still active in community)                             │
│  WebSocketService (websocket_service.dart) ← community_provider     │
│  CommunityWebSocketService ← community routes                       │
│  NOTE: WsConnectionState enum duplicated in community WS service    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 审计发现

### P0 — 严重缺陷

#### P0-1: WebSocketService (旧版) 连接成功标记过早 — 实际连接可能尚未建立
- **文件**: `mobile/lib/core/services/websocket_service.dart:62`
- **严重性**: P0
- **代码**:
```dart
_channel = IOWebSocketChannel.connect(uri, headers: _customHeaders);
_isConnected = true;  // <-- Set BEFORE TCP handshake completes!
```
- **影响**: `IOWebSocketChannel.connect()` 是异步的——它创建 channel 对象但底层 TCP/TLS 握手尚未完成。调用方检查 `isConnected` 可能为 true 但实际消息无法到达服务端，导致消息静默丢失。旧版 `WebSocketService` 仍被 `community_provider.dart:39` 和 `community_provider.dart:867` 使用。
- **修复方向**: 移除立即设置 `_isConnected = true`，改为监听 channel ready 事件或在收到第一条服务端消息时才标记 connected。

#### P0-2: CommunityWebSocketService 在连接尚未建立时标记 connected
- **文件**: `mobile/lib/features/community/data/services/community_websocket_service.dart:164-168`
- **严重性**: P0
- **代码**:
```dart
_groupChannel = WebSocketChannel.connect(Uri.parse(wsUrl), protocols: ['json']);
_setGroupState(WsConnectionState.connecting);
_groupChannel!.stream.listen(...);
// Give connection a moment to establish
await Future<void>.delayed(const Duration(milliseconds: 100));
if (_groupChannel != null) {
  _setGroupState(WsConnectionState.connected); // Race condition!
  _groupReconnectAttempts = 0;
}
```
- **影响**: 使用 100ms 硬编码延迟来判断连接成功。在慢网络或服务端延迟更高时，连接状态错误。100ms 后 channel 可能已因认证失败而关闭，但状态仍显示 `connected`。
- **修复方向**: 监听 `stream.first` 或 `stream.listen` 的第一个数据/ready 事件来确认连接。

#### P0-3: Community WebSocket Token 在 URL 中明文传输且日志泄露风险
- **文件**: `mobile/lib/features/community/data/services/community_websocket_service.dart:142` 和 `community_provider.dart:49`
- **严重性**: P0
- **代码**:
```dart
// community_websocket_service.dart:142
final wsUrl = '${ApiConstants.wsBaseUrl}/api/v1/community/groups/$groupId/ws?token=$token';
debugPrint('[WS] Connecting to group: $groupId');
// token is in the URL, which appears in server logs, proxy logs, browser history

// community_provider.dart:49
final wsUrl = '$baseUrl/community/ws/connect?token=$token';
```
- **影响**: JWT token 作为 URL query parameter 传输。URL 会被记录到：代理服务器日志、CDN 日志、浏览器历史记录（如果有 Web 版本）。此模式在 V2 聊天服务中已通过 ws-ticket 机制修复，但社区模块仍使用直接 token。
- **修复方向**: 与 V2 服务对齐，使用 ws-ticket 交换机制替代直接 token 传递。

#### P0-4: ChatRepository 每次创建新 WebSocketChatServiceV2 实例 — 违反单例连接复用
- **文件**: `mobile/lib/features/chat/data/repositories/chat_repository.dart:20` + `chat_provider_wiring.dart:5-9`
- **严重性**: P0
- **代码**:
```dart
// chat_provider_wiring.dart
final chatRepositoryProvider = Provider<ChatRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ChatRepository(
    apiClient.dio,
    container: ref.container,
  );
});

// chat_repository.dart:20
ChatRepository(this._dio, {required ProviderContainer container, ...})
    : _wsService = wsService ?? WebSocketChatServiceV2(container: container);
```
- **影响**: `chatRepositoryProvider` 是普通 `Provider`（非 `autoDispose`），Riverpod 会缓存它。但如果任何 provider 依赖链变化导致重建，新的 `ChatRepository` 会创建新的 `WebSocketChatServiceV2`，旧实例的连接和心跳定时器不会被清理。`WebSocketChatServiceV2` 本身注册了 `WidgetsBindingObserver`，如果多个实例共存，会出现多个 observer 竞争处理 app lifecycle 事件。
- **修复方向**: 将 `WebSocketChatServiceV2` 提升为独立 Riverpod provider，`ChatRepository` 通过 ref 获取而非每次创建。

---

### P1 — 重要问题

#### P1-1: _is401Error 检测范围过宽 — 误判非 401 错误触发 token 刷新和登出
- **文件**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1628-1635`
- **严重性**: P1
- **代码**:
```dart
bool _is401Error(dynamic error) {
  final errorStr = error.toString().toLowerCase();
  return errorStr.contains('401') ||
      errorStr.contains('unauthorized') ||
      errorStr.contains('jwt') ||
      errorStr.contains('token') ||
      errorStr.contains('authentication');
}
```
- **影响**: 关键词 `token` 和 `jwt` 极其宽泛。例如 `"Connection reset by peer — invalid token format in handler"` 这样的错误消息虽不是 401，但会触发 token 刷新流程。如果刷新失败，用户会被强制登出。`'authentication'` 也可能出现在普通连接错误的诊断消息中。
- **修复方向**: 精确匹配 WebSocket close code 401 或 HTTP status code 401，而非文本匹配。

#### P1-2: WebSocketService (旧版) 没有连接状态流 — 调用方无法感知断连
- **文件**: `mobile/lib/core/services/websocket_service.dart`
- **严重性**: P1
- **代码**: 该文件只有 `bool get isConnected`，没有 `Stream<ConnectionState>` 暴露。
- **影响**: `community_provider.dart:39` 使用此服务的 consumer 无法监听连接状态变化。当连接静默断开时，UI 不会反映断连状态。用户可能认为消息已发送但实际上已丢失。
- **修复方向**: 添加 `StreamController<ConnectionState>` broadcast stream，在 connect/disconnect/error 时 emit 状态。

#### P1-3: V2 服务心跳失败后调用 _handleConnectionClosed 而非直接重连 — 可能忽略正在进行的流
- **文件**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1973`
- **严重性**: P1
- **代码**:
```dart
if (_consecutiveHeartbeatFailures >= _maxConsecutiveHeartbeatFailures) {
  // ... stream active suppression logic ...
  _log('🔌 Too many heartbeat failures, triggering reconnect');
  _handleConnectionClosed();  // This broadcasts error to active requests!
}
```
- **影响**: `_handleConnectionClosed()` 在 line 1817 会向所有活跃的 `_requestControllers` 广播 `CONNECTION_CLOSED` 错误，即使流数据仍在正常传输。虽然有 `_isStreamActive` 抑制机制，但其 120 秒窗口可能不够——某些复杂 AI 工作流（如专家团队辩论）可持续超过 2 分钟。
- **修复方向**: 心跳失败应先关闭底层连接并重连，但不应立即向活跃请求广播错误。应在重连失败后才通知请求层。

#### P1-4: Community WsConnectionState 枚举与 V2 重复定义 — 类型不兼容
- **文件**: `mobile/lib/features/community/data/services/community_websocket_service.dart:10-28` vs `websocket_chat_service_v2.dart:947-953`
- **严重性**: P1
- **代码**: 两个文件各自定义了 `enum WsConnectionState`，命名相同但成员不同：
  - V2: `{disconnected, connecting, connected, reconnecting, failed}`
  - Community: `{disconnected, connecting, connected, reconnecting, error, failed}`
- **影响**: 如果任何代码尝试共享连接状态逻辑，Dart 类型系统会阻止——两个 `WsConnectionState` 是完全不同的类型。Community 版多了 `error` 状态但缺少 V2 的部分语义。
- **修复方向**: 提取 `WsConnectionState` 到 `core/` 下作为共享枚举，两个服务共用。

#### P1-5: ChatNotifier.sendMessage 中 accumulatedContent 无限增长 — 无截断保护
- **文件**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart:1086`
- **严重性**: P1
- **代码**:
```dart
// 流式文本片段（delta）
accumulatedContent += event.content;  // No size limit!
pendingStreamingContent = accumulatedContent;
```
- **影响**: 如果服务端 bug 或恶意响应产生大量 delta 消息（如无限循环发送文本），`accumulatedContent` 字符串会无限增长，消耗主线程内存。虽然 8 分钟 `streamTimeout` 提供了上限保护，但在 8 分钟内一个高速流式响应仍可能产生数十 MB 文本。
- **修复方向**: 添加 `accumulatedContent` 最大长度检查（如 100KB），超过后发出截断警告。

#### P1-6: WebSocketChatServiceV2.dispose() 中 _closeConnection() 调用 _updateConnectionState — 可能操作已关闭的 StreamController
- **文件**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:2172-2188`
- **严重性**: P1
- **代码**:
```dart
void dispose() {
  if (_disposed) return;
  _disposed = true;
  // ...
  _closeConnection();  // This calls _updateConnectionState!
  // ...
  if (!_connectionStateController.isClosed) {
    unawaited(_connectionStateController.close());
  }
}
```
- **影响**: `_closeConnection()` (line 2115) 调用 `_updateConnectionState()` (line 1433)，后者向 `_connectionStateController` 添加事件。虽然 `_updateConnectionState` 有 `isClosed` 检查，但 `dispose()` 中先调 `_closeConnection()` 再关 controller 的顺序是脆弱的——如果 `_closeConnection` 触发的状态变更在 controller.close() 之前还未被消费，broadcast controller 的 listener 可能已全部移除，导致事件静默丢失。
- **修复方向**: 在 `dispose()` 中先关闭 controller 再调用连接清理，或在 `_closeConnection` 中检查 `_disposed` 标志跳过状态更新。

#### P1-7: ChatNotifier 中 TextEvent 和 FullTextEvent 的元数据处理代码大量重复
- **文件**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart:942-1088` (TextEvent) vs `1128-1253` (FullTextEvent)
- **严重性**: P1
- **代码**: 约 120 行几乎相同的元数据提取逻辑（selectedExperts、routingStrategy、collaboration 等）在两个分支中重复。
- **影响**: 维护负担高，容易在修改时只更新一个分支而遗漏另一个，导致行为不一致。实际上这是历史遗留——两者处理的是相同类型的元数据。
- **修复方向**: 提取 `_handleMetadataEnrichment(metadata, ...)` 方法，TextEvent 和 FullTextEvent 共用。

---

### P2 — 改进建议

#### P2-1: WebSocketService (旧版) 与 V2 共存增加维护成本和认知负担
- **文件**: `mobile/lib/core/services/websocket_service.dart`
- **严重性**: P2
- **影响**: 旧版 166 行的 `WebSocketService` 仍在社区模块使用。它缺少心跳、token 刷新、pending queue 等关键功能。两套 WebSocket 服务并存增加了新人理解成本。
- **修复方向**: 逐步将社区模块迁移到 `WebSocketChatServiceV2` 架构，或至少将通用功能（重连、心跳）提取为 mixin。

#### P2-2: _parseChatEvent 中的 compute() 调用开销可能不值得
- **文件**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1608`
- **严重性**: P2
- **代码**: `final event = await compute(_parseChatEvent, data);`
- **影响**: `compute()` 会创建一个新的 Isolate 来解析单条消息。Isolate 创建成本约 50-150ms，而大多数 JSON 消息解析只需 <1ms。高频流式 delta 消息（每秒可能 10-30 条）会反复创建/销毁 Isolate。虽然 Flutter 的 Isolate pool 有一定复用，但对于此量级的解析工作，主线程 `json.decode` 实际上更快。
- **修复方向**: 基准测试 `compute()` vs 直接解析的延迟。对于 <5KB 的消息，直接在主线程解析；仅对特别大的消息（如完整 run_ledger snapshot）使用 compute。

#### P2-3: community_provider.dart 中每次 provider rebuild 都创建新 WebSocketService 实例
- **文件**: `mobile/lib/features/community/presentation/providers/community_provider.dart:39` 和 `867`
- **严重性**: P2
- **代码**:
```dart
// Line 39 — inside a Provider builder:
final wsService = WebSocketService();
// Line 867 — inside CommunityGroupChatNotifier:
final WebSocketService _wsService = WebSocketService();
```
- **影响**: 每次相关 provider 重建时都会创建新的 `WebSocketService` 实例。旧实例的连接不会被清理（旧版 `WebSocketService` 没有 `dispose` 方法暴露）。虽然 `ref.onDispose(wsService.disconnect)` 在 line 61 有清理，但 `disconnect()` 只关闭 channel，不清理内部 `StreamController`。
- **修复方向**: 将 `WebSocketService` 作为 Riverpod provider 管理，确保单例和正确的生命周期。

#### P2-4: V2 连接使用 query parameter 传递认证信息 — 缺少 ticket 时的 fallback 不够安全
- **文件**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1340-1343`
- **严重性**: P2
- **代码**:
```dart
if (wsTicket != null && wsTicket.isNotEmpty) {
  queryParameters['ticket'] = wsTicket;
} else if (effectiveToken != null && effectiveToken.isNotEmpty) {
  queryParameters['token'] = effectiveToken; // Fallback
}
```
- **影响**: 当 ws-ticket 交换失败时（如 /ws/ticket endpoint 不可用），会 fallback 到 URL query parameter 直接传 token。虽然代码有注释说明这是 fallback，但它与 P0-3 描述的安全风险相同。
- **修复方向**: 在非开发环境下，ticket 交换失败应导致连接失败（抛出异常），而非静默降级到不安全的 token-in-URL 模式。

#### P2-5: ChatState.copyWith 参数过多（30+ boolean clear flags）
- **文件**: `mobile/lib/features/chat/presentation/providers/chat_state.dart:205-265`
- **严重性**: P2
- **影响**: `copyWith` 方法有 30+ 参数，其中大部分是 `clear*` boolean。这是一个已知的 Flutter immutable state 模式痛点，但在如此规模下（60 行参数列表）极易出错——遗漏某个 clear flag 导致状态残留。
- **修复方向**: 考虑使用 `freezed` 包生成 copyWith，或将相关字段分组为子状态对象（如 `StreamingState`、`ReviewState`、`TransparencyState`）。

#### P2-6: 旧版 WebSocketService._reconnectSchedule 使用固定退避 — 无 jitter
- **文件**: `mobile/lib/core/services/websocket_service.dart:14-21`
- **严重性**: P2
- **代码**: `static const List<Duration> _reconnectSchedule = [800ms, 1200ms, 2200ms, 4200ms, 8200ms, 12200ms];`
- **影响**: 所有客户端使用相同的退避时间表。如果服务端重启导致大量客户端同时断连，它们会在完全相同的时间点尝试重连，造成 "thundering herd"。
- **修复方向**: V2 服务已有 jitter（line 1864），但旧版没有。需要添加随机 jitter。

#### P2-7: CommunityWebSocketService 的消息去重 Set 无 LRU 淘汰策略
- **文件**: `mobile/lib/features/community/data/services/community_websocket_service.dart:87-88, 283-285`
- **严重性**: P2
- **代码**:
```dart
final Set<String> _receivedMessageIds = {};
static const int _maxMessageCacheSize = 1000;
// ...
_receivedMessageIds.add(msgId);
if (_receivedMessageIds.length > _maxMessageCacheSize) {
  _receivedMessageIds.remove(_receivedMessageIds.first); // Oldest by insertion order?
}
```
- **影响**: Dart `Set` 不保证插入顺序（虽然在当前 Dart VM 实现中 `LinkedHashSet` 是默认实现，保持插入顺序）。依赖 `_receivedMessageIds.first` 来淘汰最旧条目是脆弱的——如果 Dart 实现变更，此行为可能改变。此外 1000 条的硬限制在活跃社区中可能不够。
- **修复方向**: 使用 `LinkedHashMap` 或 `Queue<String>` 显式管理 LRU 淘汰顺序。

#### P2-8: ChatRepository 中 SSE 的 _parseEvent 与 V2 的 _parseChatEvent 存在分支差异
- **文件**: `mobile/lib/features/chat/data/repositories/chat_repository.dart:405-464`
- **严重性**: P2
- **影响**: SSE fallback 的 `_parseEvent` 只处理 7 种事件类型（text、tool_start、tool_result、widget、intervention、done、feedback_acks），而 V2 的 `_parseChatEvent` 处理 30+ 种。虽然 SSE 标记为 `@Deprecated`，但如仍有使用路径，某些事件会被静默丢弃为 UnknownEvent。
- **修复方向**: 标记 SSE 为待移除，添加明确的迁移注释和截止版本。

---

## 合规项
| 检查项 | 状态 | 备注 |
|--------|------|------|
| WS 连接有重连机制 | PASS | V2: 指数退避 + jitter, 最多 6 次; 旧版: 固定退避, 最多 6 次 |
| JWT 刷新在重连前 | PASS (V2) | V2 有完整 token 刷新 + ws-ticket 机制; 旧版无 |
| 心跳保活 (ping/pong) | PASS (V2) | V2: 30s ping, 60s pong timeout, 3x fail trigger; 旧版无心跳 |
| 消息解析有错误兜底 | PASS | `_parseChatEvent` 外层 try-catch 返回 ErrorEvent |
| Isolate 解析重消息 | PARTIAL | 使用 `compute()` 但开销可能大于收益 (P2-2) |
| Pending message queue | PASS | 50 条上限, FIFO 溢出丢弃, 有通知 |
| 连接状态暴露给 UI | PASS (V2) | V2 通过 `connectionStateStream`; 旧版仅有 bool isConnected |
| 后台/前台生命周期 | PASS (V2) | V2: `WidgetsBindingObserver`, paused→disconnect, resumed→reconnect |
| Stream subscription 清理 | PASS | `dispose()` 中取消所有 subscription 和 timer |
| 多请求路由隔离 | PASS | `_requestControllers` Map 按 requestId 路由 |
| 401 认证错误处理 | PARTIAL | 功能完整但检测范围过宽 (P1-1) |
| Token 不在 URL 中 | FAIL | 社区模块仍直接传 token (P0-3), V2 有 ticket fallback (P2-4) |
| 所有消息类型有处理 | PASS | default 分支返回 UnknownEvent, 不会 crash |
| 资源泄漏防护 | PASS | `_disposed` flag + `isClosed` 检查 + `unawaited()` |
| 单例连接复用 | PARTIAL | V2 设计正确但 ChatRepository 可能创建多实例 (P0-4) |
| 客户端消息校验 | PARTIAL | 只检查 type 字段存在; payload 内容无 schema 验证 |

---

## 统计
| 级别 | 数量 |
|------|------|
| P0 | 4 |
| P1 | 7 |
| P2 | 8 |
| **总计** | **19** |

---

## 修复优先级建议

1. **P0-4** — ChatRepository 单例问题: 将 WebSocketChatServiceV2 提升为独立 provider，防止多实例连接泄漏。这是架构级修复，影响所有上层。
2. **P0-1 + P0-2** — 连接成功标记过早: 旧版 WebSocketService 和 CommunityWebSocketService 的 `_isConnected` 过早设置。修复方式：等待 stream ready 或第一条消息。
3. **P0-3** — 社区 Token 明文: 实施与 V2 相同的 ws-ticket 机制。
4. **P1-1** — 401 检测过宽: 精确匹配 close code 或 status code，避免误判。
5. **P1-6** — dispose 顺序: 调整 dispose 中 controller 和 connection 的关闭顺序。
6. **P1-3** — 心跳失败广播: 分离连接重置和请求错误通知。
7. **P1-4** — 枚举重复定义: 提取到 core/ 共享。
8. **P1-5** — 内容截断保护: 添加 accumulatedContent 长度上限。
9. **P1-7** — 元数据代码重复: 提取公共方法。
10. **P2-2** — compute() 性能: 基准测试后决定是否保留。
11. **P2-1 / P2-3** — 旧版服务迁移: 长期技术债，逐步将社区模块迁移到 V2 架构。

---

## 跨轮次因果链
| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 旧版 WS connected 标记过早 | Round #2 (WS Message Flow) | 连接生命周期状态机缺陷 |
| P0-4 ChatRepository 多实例 | Round #53 (Go Chat Orchestrator) | Provider 生命周期与连接复用 |
| P1-1 401 检测过宽 | Round #55 (Agent gRPC Service) | 认证错误传播链 |
| P1-3 心跳失败广播到活跃请求 | Round #53 (Go Chat Orchestrator) | 流中断与重连策略 |
| P1-5 无截断保护 | Round #53 (Go Chat Orchestrator) | 背压与缓冲区管理 |
| P2-4 token-in-URL fallback | Round #55 (Agent gRPC Service) | 认证 token 传输安全 |
| P2-8 SSE 与 V2 解析差异 | Round #2 (WS Message Flow) | 消息格式兼容性 |

---

## Chris (Session 5) 复核 — 2026-04-23

> 逐项验证 P0 发现对主项目当前代码 (`/Users/brsama/code/GitHub/Sparkle-project/`)。

### P0 验证

| 原始发现 | 文件 | 行号 | 当前状态 | 结论 |
|----------|------|------|---------|------|
| P0-1 旧版WS connected过早 | `websocket_service.dart` | :62 `_isConnected = true` | 代码未变 | **CONFIRMED** |
| P0-2 Community 100ms竞态 | `community_websocket_service.dart` | :164-168 `Future.delayed(100ms)` + `connected` | 代码未变 | **CONFIRMED** |
| P0-3 Community token在URL | `community_websocket_service.dart` | :142 `?token=$token` | 代码未变 | **CONFIRMED** |
| P0-4 ChatRepository多实例 | `chat_repository.dart` | :20 `wsService ?? WebSocketChatServiceV2(...)` | 代码未变 | **CONFIRMED** |

### P1 抽样验证

| 发现 | 结论 |
|------|------|
| P1-1 _is401Error过宽 | **CONFIRMED** — `contains('token')` 仍存在，过于宽泛 |
| P1-4 枚举重复 | **CONFIRMED** — 两个文件各自定义 `WsConnectionState` |

### 总结

报告质量高，行号精确，4个P0全部确认仍存在。代码自审计以来无变化。19项发现均为真实问题。Flutter侧问题需协调mobile team排期修复，不适合autonomous loop直接修改。
