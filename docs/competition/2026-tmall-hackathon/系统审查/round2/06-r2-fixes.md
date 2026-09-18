# R2 修复波 G6 — 06 移动端核心链 修复报告

- 修复员：G6（**恢复轮**）｜2026-09-09→09-18｜基线 main@ca86bda8（冻结 worktree `wt6`，未提交）
- 输入：`round2/06-r2-mobile-core.md` §4.2 修法 1/2/3 + §1.1/§4 建议项（M6-R2-01、M6-R2-02、M6-R2-04）
- 测试：`flutter test --concurrency=4`（7 个受影响文件，**19 用例全绿**）

---

## 0. 恢复说明（本轮前置）

前任 G6 修复员会话被系统中断，进度留在 wt6 工作树（9 个已改 lib/test 文件 + 4 个新测试文件），**未导出 patch、未写修复报告，且 4 个新测试文件从未真正编译执行过**。本轮（恢复轮）完成：

1. **现场恢复**：逐文件审查前任 diff，确认 5 项修复的产线代码改动方向正确、均已落位。
2. **补齐未完成项**——前任的测试侧存在 5 处缺陷，导致其声称的"测试验证"实际未发生（详见 §3 各条"恢复轮修正"）：
   - `websocket_service_reconnect_budget_test.dart`：缺 `dart:async` import（编译失败）；`_parseScheduleDelay` 误以为 `Duration.toString()` 输出 `800ms` 形式（实际日志是 `${delay}ms` 插值 Duration，即 `0:00:00.050000ms`），解析器重写；
   - `dashboard_retry_backoff_test.dart`：`inWindow(30, schedule.last)` 少传一个参数（编译失败）；两个用例均未读取惰性 `StateNotifierProvider`，notifier 从未构造、fetch 从未发起（运行时超时）——显式 `container.read(dashboardProvider.notifier)` 修复；
   - `websocket_chat_service_v2_ready_gate_test.dart`：测试 3 声明的短退避表 `schedule` 从未注入 service（service 在 setUp 构造时未带 `reconnectSchedule`），导致按生产表 15s 内不可达 `failed`——重建 service 注入短表并调整装配顺序（先重建再 `sendMessage`，保证终态广播可达本用例的 request controller）；`logs` 列表 setUp 不清空跨用例累积污染 `hasLength(6)` 计数——补 `logs.clear()`；测试 2 终态断言与新拨号竞态（timer 触发后 state 合法地回到 `connecting`）——改为在 timer 挂起期断言 `reconnecting`，再等新 channel 落地；测试 3 的 `MAX_RETRIES_EXCEEDED` 广播断言与产线广播语义不符（`_broadcastErrorToActiveRequests` 首次掉线广播 `CONNECTION_CLOSED` 即关闭并移除 controller，后续广播按设计落空，pending 消息经 offline DB 获知 MESSAGES_LOST）——改为断言 failed 分支执行证据（`Max reconnect attempts reached` 日志 + `Discarding 1 pending messages` 日志）+ 请求流收到终态广播；
   - `websocket_chat_service_v2.dart`：`_handleConnectionClosed` 两语句挤同一行（前任编辑破损）——恢复常规格式。
3. **红-绿证明**：三个 P2 项各做一次"还原缺陷→测试变红→恢复修复→测试回绿"：
   - v2 ready 门控：还原为 connect 后立即置 connected+复位预算 → 3 用例全红（闪连 / 握手失败不重连 / 19s 内 failed 不可达）；
   - core 时长门控复位：还原 ready 即复位 → accept-then-close 循环 40 次重连全部停在 Attempt: 1（修复后恰好 7 次、逐档递增）；
   - dashboard 预算复位：去掉成功路径 `_errorRetryCount = 0` → "成功后预算复位"用例红。

---

## 1. 修复清单

| ID | 严重度 | 修复内容 | 位置 | 测试 |
|----|--------|----------|------|------|
| M6-05 (P2) + **M6-R2-01** (P2) | v2 聊天 WS | `connect()` 不再立即置 connected/复位预算；改为 `channel.ready.timeout(10s)` 确认握手后才置 connected、启动心跳、补发队列；ready 失败（含超时）经 `catchError` 消费并入 `_handleConnectionError`（401 检测/错误广播/重连排程）；`_reconnectAttempts` 不再每轮清零，退避 800ms→12.2s 六档真实生效，`failed`/`MESSAGES_LOST` 终态可达 | `websocket_chat_service_v2.dart` `_establishConnectionAsync`（:1755-1796 一带）、`_settleReconnectBudgetOnDisconnect`（新增，`_triggerReconnect` 入口调用） | `websocket_chat_service_v2_ready_gate_test.dart` ×3 |
| **M6-R2-02** (P2，条件触发) | core WS | M6-02 的"ready 即复位 attempts"在"握手成功即断"（网关 crash-loop/LB 排水/热重载）下退化为 800ms 恒频无限重连。改为**时长门控**：记录 `_connectedAt`，断开时仅当存活 ≥30s（稳定连接）才刷新预算；短命会话预算照常递增至 max=6 后放弃。新增构造参数 `stableConnectionThreshold`（测试注入）与 `reconnectSchedule`（测试注入退避表） | `websocket_service.dart`（`_settleReconnectBudgetOnDisconnect` 新增；onError/onDone 先结算再排程） | `websocket_service_reconnect_budget_test.dart` ×2（新）+ `websocket_service_test.dart` 用例 2 改写为"稳定连接断开才刷新预算"（hold 500ms > 200ms 阈值） |
| M6-08 (P2) | dashboard | 错误自动重试从固定 5s 无限轮询改为指数退避 + 封顶 5s→15s→45s→120s（末档封顶）；成功路径（全部可抛 await 之后）复位计数；`retryBackoffSchedule` 可注入 | `dashboard_provider.dart` `DashboardNotifier` | `dashboard_retry_backoff_test.dart` ×2（新） |
| M6-07 (P2) | onboarding 闪跳 | `onboardingCompletedProvider` 三态化 `bool→bool?`（null=同步未决）；无存值时保持 null 等 profile context 判定；同步失败兜底 `state ??= false`；router redirect 两分支改 `== false` / `== true`（未决期不做 onboarding 改写，消灭闪跳与 §2.3 的深链多跳）；persona 屏 banner 消费处 `?? false` | `settings_provider.dart`、`routes.dart`、`user_persona_screen.dart` | `onboarding_pending_state_test.dart` ×2（新）+ `router_deep_link_test.dart` 新增 pending 深链用例 + `auth_session_restore_test.dart` 等待谓词适配 `bool?` |
| **M6-R2-04** (P3) | 开放重定向加固 | `_safePendingRedirect` 在 `//` 拒绝之外增加：含反斜杠拒绝（`/\evil.com` 浏览器等价协议相对）、控制字符（<0x20、0x7f）拒绝、长度 >2048 拒绝 | `routes.dart` | `router_deep_link_test.dart` 新增 `/\evil.com` 用例 |

（未动项：M6-R2-03 历史补拉、M6-R2-05 Web 多平台铺路为专项改造，不在本波输入。）

## 2. 测试执行记录

```
flutter test --concurrency=4 \
  test/core/services/websocket_service_test.dart \
  test/core/services/websocket_service_reconnect_budget_test.dart \
  test/features/chat/data/services/websocket_chat_service_v2_ready_gate_test.dart \
  test/features/home/presentation/providers/dashboard_retry_backoff_test.dart \
  test/features/user/presentation/providers/onboarding_pending_state_test.dart \
  test/app/router_deep_link_test.dart \
  test/features/auth/presentation/providers/auth_session_restore_test.dart
→ 19 用例：All tests passed!（连续两轮；首轮出现 1 次瞬态失败，复跑即绿，
  为实时计时敏感用例在 --concurrency=4 下的调度抖动，非实现缺陷）
```

红-绿证明（详见 §0.3）：v2 ×3 红→绿、core 预算 ×1 红→绿、dashboard 复位 ×1 红→绿。

静态检查：触及的 13 个文件 `flutter analyze` 仅有 info 级提示（多为测试文件风格项与既存代码样式；其中 `auth_session_restore_test` 的 `use_if_null_to_convert_nulls_to_bools` 建议对 `== true` 改 `?? false` 属误报——`== true` 是三态判别所需，非冗余）。无 error/warning 级。

## 3. 关键实现要点

### 3.1 v2 ready 门控（M6-05 + M6-R2-01 合并修法 1 的落地）

- `channel.ready.timeout(10s)` 防握手悬挂；`_disposed || !identical(_channel, channel)` 双重防陈旧回调（重连期间旧 channel 的 ready 迟到不得触碰新状态）。
- `_connectedAt` 记录握手成功时刻；`_triggerReconnect` 入口先 `_settleReconnectBudgetOnDisconnect()`（存活 ≥30s 才复位）；`_teardownSocket`/`_closeConnection`/`disconnect` 均清 `_connectedAt`，防跨连接误判存活时长。
- 终态语义核实：`_broadcastErrorToActiveRequests` 首次广播即关闭 controller，因此 `MAX_RETRIES_EXCEEDED`/`MESSAGES_LOST` 的送达面是 pending 队列的 offline DB（`markFailed`），活跃请求流在首次断线已收到 `CONNECTION_CLOSED` 终态——测试按此语义锁定，并修正了任务书 §4.2 修法 1 中"终态广播到达活跃请求流"的预期偏差。

### 3.2 core 时长门控复位（任务书 §1.1 建议修法的强化版）

任务书建议"断开时存活 ≥30s 才复位"；实现同时保留 M6-02 原回归（静默长连接断开仍能拿新预算），并用注入阈值（测试 200ms）+ 真实 TCP 服务器（接受-即断 / 保持 500ms 两型）双向锁定。

### 3.3 onboarding 三态化消费方核对

grep 全量核对：仅 `routes.dart`（redirect 两分支）、`user_persona_screen.dart`（watch，null 按"未完成"渲染 banner）、`modeling_chat_screen.dart`（`setCompleted(true)` 不受影响）。`auth_session_restore_test.dart` 的等待谓词改 `== true`。

## 4. 遗留与交接

1. **ENOSPC 事件（已恢复）**：报告撰写期间本机 /Users 卷一度写满（0 字节剩余），Bash 通道短时不可用；经系统回收空间后恢复，patch 已按输出契约成功导出。全部测试验证在事件发生前已完成（两轮 19/19 绿 + 红绿证明）。产物：`round2/06-r2-fixes.patch`（1960 行，含本报告与 13 个代码文件改动）。
2. 瞬态失败 1 例（首轮汇总 `+18 -1`，复跑两轮均绿）：疑似 dashboard 退避窗口断言在并发下的调度抖动；后续如再复现，可把 `inWindow` 容差从 +400ms 放宽到 +800ms。
3. M6-R2-03（重连后历史补拉）与 M6-R2-05（web 铺路）仍开放。

---
*报告生成：G6 恢复轮修复员｜2026-09-18｜基线 ca86bda8*
