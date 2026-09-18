# 全系统审查·第一轮修复波 — 06 修复报告（移动端·核心体验链）

- 修复员：6 号｜2026-09-18｜基线 90daac8a（worktree `wt6`）
- 测试环境：Flutter 3.41.3；protobuf override **仅本地**（`dependency_overrides: protobuf: ^6.1.0` + 以 protoc_plugin 25.1.0 重新生成 `mobile/lib/gen`），**pubspec.yaml / pubspec.lock 已按约定排除在 patch 之外**（M6-01 归协调者，main 已有该修复）。

---

## 已修 ID

### M6-02（P1）core WebSocketService 重连双重调度 + 预算不复位

- **修复**：`mobile/lib/core/services/websocket_service.dart`
  - `:150-156` `_scheduleReconnect` 排程前先 `_cancelReconnectTimer()`——onError/onDone（及握手失败）对同一次断线只保留单一 Timer，预算不再倍速消耗。
  - `:75-97` `_connectInternal` 改为 `channel.ready.then(...)`：握手完成即置 `_isConnected = true` 并复位 `_reconnectAttempts = 0`（原逻辑只在收到首条消息时复位，静默连接下预算保持耗尽→2 次断线即永久放弃）；`ready` 失败走 `_scheduleReconnect`，并以 `identical(_channel, channel)` 防陈旧回调。
  - 消息回调内原 `_reconnectAttempts = 0`（"Reset on success"）移除。
- **测试**：`mobile/test/core/services/websocket_service_test.dart`
  - `a single failed connect schedules exactly one reconnect timer and does not leak an unhandled handshake error`
  - `three consecutive drops of silent connections still trigger a 4th reconnect from the first backoff step (budget resets on connect)`
- **红证据**（基线代码）：
  - 测试 1：`Expected: <2> / Actual: <3>`——单次连接失败后 800ms 窗口内出现 3 条 "Connecting"（initial + 双重调度），且 `runZonedGuarded` 需兜住 `channel.ready` 未消费的 unhandled exception。
  - 测试 2：重连 attempt 序列 `Attempt: 1, 2, 3` 递增（预算不复位），`everyElement(contains('(Attempt: 1)'))` 失败。
- **绿证据**：修复后 `flutter test test/core/services/websocket_service_test.dart` → `+3: All tests passed!`（含 M6-10 用例）。

### M6-03（P1）completeTask 后置步骤异常误标 `syncStatus: failed` + 重试二次完成

- **修复**：`mobile/lib/features/task/presentation/providers/task_provider.dart`
  - `:492-516` `completeTask` 主 try 内服务端成功即置 `synced` 并 `return result`；归因消费、执行埋点、galaxy/plan/portfolio/achievement/dashboard 刷新全部移入 `:531-586 _runPostCompletionSteps`，其中任何异常仅 `debugPrint`（"server state kept"），不触碰任务同步状态。
  - `:616-623` `retryCompleteTask` 幂等跳过：本地任务 `status == completed && syncStatus == synced` 直接返回，不再调用服务端完成接口（消除重复完成/重复奖励风险）；`:645` 成功路径同样复用隔离的后置步骤。
- **测试**：`mobile/test/features/task/presentation/providers/task_complete_sync_test.dart`
  - `server success keeps syncStatus synced when post-completion attribution throws`
  - `retryCompleteTask is idempotent for already-synced completions`
- **红证据**（基线代码，假仓库/假归因服务注入）：
  - 测试 1：`Expected: not null / Actual: <null>`——归因抛异常落入外层 catch，`completeTask` 返回 null 且任务被标 failed；
  - 测试 2：`Expected: <1> / Actual: <2>`——重试把服务端完成接口又调了一次。
- **绿证据**：修复后该文件 `+3: All tests passed!`（含 M6-16 用例）；绿跑日志可见 `[Task] post-completion steps failed for task-1 (server state kept): ...`，证明隔离生效。
- 注：首轮红跑曾因测试自身 JSON 枚举 wire 值写错（`learning` vs `LEARNING`）污染证据，已修正后重新走完整红→绿（stash lib 还原基线取得上述红输出）。

### M6-04（P1）auth loading 期深链被改写为 '/'（path+query 全丢）

- **修复**：`mobile/lib/app/routes.dart`
  - `:49` / `:53-64` 新增 `_kPendingRedirectQuery`/`_kReturnToQuery` 参数名与 `_safePendingRedirect`（仅接受站内绝对路径、拒绝 `//` 开头，防开放重定向）。
  - `:139-151` loading 分支：受保护深链不再改写为 `'/'`，而是 `return '/?redirect=<Uri.encodeComponent(原URI)>'` 经 splash 中转；auth 页与 splash 本身维持 `null`。
  - `:153-162` unauth 分支：去 `/login` 时携带 `return_to`（splash 中转的深链先解包），登录后可还原。
  - `:164-171` authenticated + splash/auth 分支：优先还原暂存深链，无参时维持原 `/home`。
- **测试**：`mobile/test/app/router_deep_link_test.dart`
  - `preserves deep link path and query while auth state is loading, then restores it after authentication resolves`
  - `unauthenticated deep link carries return_to on the login location`
- **红证据**（基线代码，stash routes.dart 取得）：
  - 测试 1：loading 期 `queryParameters['redirect']` → `Expected: '/chat?session_id=deep-link-42' / Actual: <null>`（深链被改写为 '/' 且全部丢失）；认证完成后落 `/home` 而非 `/chat`。
  - 测试 2：`/login` 上 `return_to` → `Expected: '/chat?session_id=deep-link-42' / Actual: <null>`。
- **绿证据**：修复后 `flutter test test/app/router_deep_link_test.dart` → `+2: All tests passed!`。

### M6-16（P3）完成请求发出前就取消提醒

- **修复**：`mobile/lib/features/task/presentation/providers/task_provider.dart`
  - `completeTask` 顶部的 `_notificationScheduler.cancelTaskReminders(id)` 前置取消删除；移至 `:539-544 _runPostCompletionSteps` 开头（服务端确认成功后才取消；失败路径任务仍开放、提醒保留；重试成功路径同样生效）。
- **测试**：`task_complete_sync_test.dart` `does not cancel reminders when the server completion fails`（记录型 `_StubScheduler`）。
- **红证据**：`Expected: <0> / Actual: <1>`——服务端完成失败（DioException connectionError）提醒仍被取消。
- **绿证据**：修复后该用例通过；成功路径取消行为由 M6-03 测试 1 覆盖（修复后 cancel 恰好 1 次且发生在成功后）。

### M6-06（P2）吊销会话无法清除残留 user

- **修复**：`mobile/lib/features/auth/presentation/providers/auth_provider.dart`
  - `:40,47` `copyWith` 新增 `clearUser` 标志（沿用 `clearError` 模式），`user: clearUser ? null : (user ?? this.user)`；
  - `:97-105` `_resetInvalidStoredSession` 改用 `clearUser: true`，被吊销会话不再残留过期用户（`currentUserProvider` 消费方不再读到旧身份）。
- **测试**：`mobile/test/features/auth/presentation/providers/auth_state_clear_user_test.dart`
  - `clearUser flag drops the stale user on revoked sessions`（另一用例锁定 null-merge 语义未被破坏）。
- **红证据**：编译红——`No named parameter with the name 'clearUser'`（基线无该能力）。
- **绿证据**：修复后 `+2: All tests passed!`。

### M6-10（P3）二进制帧解析失败广播原始字节

- **修复**：`mobile/lib/core/services/websocket_service.dart:102-110`——protobuf 解析失败不再 `_controller.add(data)` 广播原始字节（消费方只认 WebSocketMessage/JSON Map，广播只会让下游崩），改为记日志丢弃；文本/JSON 路径不变。
- **测试**：`websocket_service_test.dart` `drops unparseable binary frames instead of broadcasting raw bytes`（服务端发 `0x00 0xFF ...` 垃圾帧 + 合法 JSON 文本帧）。
- **红证据**：`Expected: empty / Actual: [[0, 255, 19, 55, 222, 173]]`——原始字节被广播进 stream。
- **绿证据**：修复后通过，且 JSON 文本帧（`type: pong`）仍正常投递。

### M6-14（P3）debug 日志明文打印登录密码

- **修复**：`mobile/lib/core/network/api_interceptor.dart:217-273`
  - `LoggingInterceptor` 支持注入 `Logger`；新增 `_sensitiveBodyFields`（password/token 系 12 个键）与 `sanitizeBodyForLog`（敏感键值打码为 `***`；非 Map 请求体一律不再打印）；`onRequest` 打印前先脱敏。
- **测试**：`mobile/test/core/network/logging_interceptor_redaction_test.dart` `passwords never appear in request logs`（注入内存 Output 断言日志全文）。
- **红证据**：编译红——基线无 `logger` 注入参数（该能力不存在，无法在不改产线代码的前提下构造观测点）。
- **绿证据**：修复后通过：日志含 `alice`（非敏感字段保留可调试性）、不含明文密码。

---

## 测试结果汇总（修复波新增 9 个用例 + 回归）

- 新增/扩展测试文件（全部随 patch 提交）：
  - `mobile/test/core/services/websocket_service_test.dart`（3 用例）
  - `mobile/test/features/task/presentation/providers/task_complete_sync_test.dart`（3 用例）
  - `mobile/test/app/router_deep_link_test.dart`（2 用例）
  - `mobile/test/features/auth/presentation/providers/auth_state_clear_user_test.dart`（2 用例）
  - `mobile/test/core/network/logging_interceptor_redaction_test.dart`（1 用例）
- 修复波全量绿跑：`flutter test test/core/services/websocket_service_test.dart test/features/task/presentation/providers/task_complete_sync_test.dart test/core/network/logging_interceptor_redaction_test.dart test/features/auth/presentation/providers/auth_state_clear_user_test.dart` → **+9: All tests passed!**
- 回归（与基线 stash 对照，**零新增失败**）：
  - `test/app test/features/task test/core/services` → +180 -5（5 个失败与基线逐一同名：main_actions_smoke×2、router_smoke 'loads critical secondary routes'、task_list_screen retry 用例、why_this_today_panel）。
  - `test/unit test/core test/widget/cold_start_route_transition_test.dart test/widget/full_route_coverage_test.dart` → +407 -2（websocket_chat_service_v2 的 token 透传用例、shared_state_widgets 的 CustomErrorWidget retry 用例，均为基线固有）。
- `flutter analyze`（5 个被改 lib 文件）：0 error / 0 warning；仅 7 条 info 且与基线逐一相同（行号平移）。

---

## 剩余清单（本轮未修）

| ID | 严重度 | 摘要 | 未修原因 |
|----|--------|------|----------|
| M6-05 | P2 | websocket_chat_service_v2 握手前置 connected（应 await `channel.ready`） | 涉及 v2 聊天 WS 状态机与 45 个基线编译失败后刚恢复的测试面，回归成本高；本波余力优先给了同目录低风险项 |
| M6-07 | P2 | onboarding 状态无"未决"三态，老用户闪跳引导页 | 需改 OnboardingCompletedNotifier 语义 + router 双分支，波及 settings/user 目录联动测试 |
| M6-08 | P2 | dashboard 失败后固定 5s 无退避无限重试 | home 目录，需指数退避+上限设计，留下一波 |
| M6-09 | P2 | 流式中新消息取消旧流致部分回复"凭空消失" | chat_provider 核心流式语义，改动需产品确认保留形态 |
| M6-11~13 | P3 | 硬编码颜色/双语三元串/字号档位收敛到 design 令牌与 arb | 纯打磨，量大（28+6+32 处），建议专项批处理 |
| M6-15 | P3 | `e.toString()` 直出任务列表错误组件 | 需接 AppFailureMapper 并核对 task_list 文案断言 |
| M6-17 | P3 | pong 整串相等判定（网关附加字段即心跳假阳性） | v2 服务，已有 3 次阈值兜底 |
| M6-18 | P3 | SSE 错误事件字符串拼 JSON | 建议与 M6-05 一并处理 |

## 新发现

1. **`channel.ready` 未消费即 unhandled exception**（web_socket_channel 3.0.3，已在 M6-02 修复中一并处理）：基线 `IOWebSocketChannel.connect` 从不 await `ready`，握手失败（如连接拒绝）的错误成为未处理异步异常直接击穿调用方 zone（flutter test 中直接判死测试）。修复以 `ready.catchError` 消费并纳入 M6-02 用例 1 锁定。**建议 v2 聊天 WS（M6-05）一并核查同类问题。**
2. **dart:io 的 `HttpServer.close(force: true)` 断不开已完成 WebSocket 升级的连接**（升级后 socket 脱离 HttpServer 连接管理）——测试基建经验：模拟"异常断连"需走连接失败路径或 TCP 代理，直接 force-close 无效。已记录于 websocket_service_test 注释。
3. **M6-01 工具链根因补充**：使基线 gen 可编译的最小配对是 protobuf **6.1.0** + protoc_plugin **25.1.0**（25.0.0 产物缺 `$_createMessage`）。本 worktree 已按此重新生成 gen（gitignore 产物，不入 patch）；`docker/proto-toolchain.Dockerfile` 仍钉 22.3.0，CI proto-gen 步骤仍缺——请协调者在 main 的 M6-01 修复中核对这两点。
4. **LoggingInterceptor 行为变化**：非 Map 请求体现在完全不打 Data 日志（原先原样打印）。这是防泄漏的保守取向；如需保留，请明确白名单后再放开。

---
*修复报告：修复员 6 号｜2026-09-18｜patch 见同目录 `06-fixes.patch`*
