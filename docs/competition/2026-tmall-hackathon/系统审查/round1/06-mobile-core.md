# 全系统审查·第一轮 — 06 移动端·核心体验链

- 审查员：6 号（Flutter Mobile 核心链路）
- 基线：main@90daac8a（冻结 worktree `Sparkle-sysrev/wt6`）
- 切片：启动 → 引导 → 登录 → 首页 → 聊天 → 任务 → 设置；core/（router、网络、WS、design、存储）逐文件深读；features 限 splash/onboarding/auth/home/chat/task/settings（其余 35 个 features 归 7 号）
- 方法：风险导向。逐行读 `app/routes.dart`、`core/network/*`、`core/services/websocket_service.dart`、`features/chat/data/services/websocket_chat_service_v2.dart`（2695 行）、`chat_provider.dart`（2049 行）、`chat_screen.dart`（4041 行关键段）、`task_provider.dart`、`dashboard_provider.dart`、`auth_provider.dart`、splash/onboarding/task_list/dashboard 等 screen，佐以 grep 扫描（硬编码颜色/字号/中文串、Timer/mounted/dispose）与 flutter analyze/test 实测。

---

## 1. 总评

核心体验链的**业务代码质量高于典型参赛项目水准**：聊天流式链路（请求代际守卫、防抖 flush、terminal fallback、401 单飞刷新、离线持久化队列）设计相当扎实；路由守卫、dashboard 错误态、任务乐观更新三态同步均有像样实现。真正的问题集中在三处：**（a）protobuf 生成链路的运行时/插件版本配对断裂**——冻结基线上 `mobile/lib/gen` 无法用任何可用 protoc_plugin 编译，核心链路 45 个测试套件全部因编译失败不可运行，且 CI 的 flutter-test job 根本没有生成 gen 的步骤，这是移动端"能不能跑起来"级别的问题；**（b）两条 WebSocket 客户端中较老的一条（core/services/websocket_service.dart，服务离线同步引擎与社区）重连机制有双重调度与预算耗尽缺陷**；**（c）任务完成乐观更新的 catch 粒度过粗**——服务端已成功后本地后置步骤异常会被误标为"同步失败"并可触发重复完成。深链丢失、onboarding 竞态、dashboard 无退避重试等为 P2；令牌/i18n 卫生问题为 P3 打磨项。

---

## 2. 发现表

| ID | 严重度 | file:line | 触发场景 | 证据摘录 | 建议修复 |
|----|--------|-----------|----------|----------|----------|
| M6-01 | **P1** | `mobile/.github/workflows/ci.yml:404-406`；`docker/proto-toolchain.Dockerfile:44`；`mobile/pubspec.lock:1411-1417`；`mobile/pubspec.yaml:91,133-148` | 干净 checkout 上运行 `flutter test`（CI flutter-test job 或本地复现）：`mobile/lib/gen/` 是 gitignore 的构建产物（`git check-ignore mobile/lib/gen/websocket.pb.dart` 命中），ci.yml 的 flutter-test job 只跑 `flutter pub get` + `flutter test --coverage`，**没有 proto-gen 步骤**；即使补跑 `make proto-gen`，钉版工具链 `protoc_plugin 22.3.0`（pubspec 声明依赖 `protobuf: ^4.1.0`）生成的代码调用 `PbList<T>()` 构造与 `toProto3Json:` 参数，而基线 pubspec.lock 锁定 **protobuf 6.0.0**——6.0.0 changelog 明确 "Hide PbList and PbMap constructors"、WKT 库 "required for protoc_plugin-25.0.0"；换用本地可用的新版插件（25.0.0/25.1.0）生成后，产物引用 `$_createMessage`，该 API 仅在 protobuf **6.1.0** 存在（6.1.0 changelog："Make BuilderInfo methods accept GeneratedMessage Function() typed closures"），对 6.0.0 同样编译失败。实测三种配对全部失败，`+101 -45` 三次恒定，45 个失败全部是 `lib/gen/*.pb.dart` / `sync_engine.dart` 编译错误（如 `lib/gen/agent_service.pb.dart:5104 Couldn't find constructor 'PbList'`、`sync_engine.dart:270 Timestamp/*1*/ can't be assigned to Timestamp/*2*/`——同一 app 内两份 Timestamp 类）。审查任务书称"protobuf 6.1.0 override 已在（编译已通）"，**该 override 不在冻结树内**：pubspec.yaml 的 dependency_overrides 无 protobuf 条目，lock 为 6.0.0 | 见下方 diff-1 | 短期：`dependency_overrides: protobuf: 6.1.0` + Dockerfile 升 `protoc_plugin 25.x` + ci.yml flutter-test job 增加 proto-gen 步骤（gen 为 gitignore 产物，CI 干净机器上必须生成）；长期：在 `make proto-gen` 后加 `check-generated` 门禁（脚本已存在） |
| M6-02 | **P1** | `mobile/lib/core/services/websocket_service.dart:97-107,118-134` | 该 WS 客户端服务离线同步引擎（`core/offline/sync_engine.dart:17`，挂载于 app.dart `deferredSyncBootstrapProvider`）与社区流。缺陷一：onError 与 onDone（`cancelOnError: false` 时先后都会触发）各自调用 `_scheduleReconnect()`，而 `_scheduleReconnect` 直接 `_reconnectTimer = Timer(...)` 覆盖旧句柄未先 cancel → 每次断线产生两个等长 Timer，双双触发 `_connectInternal()`，重连预算（`_maxReconnectAttempts = 6`）按 2 倍速消耗且连接反复重建；缺陷二：`_reconnectAttempts = 0` 只在第 97 行"收到一条消息"时复位，连接成功本身不复位 → 连接恢复但服务器静默（同步链路常态是等 outbox，无推送）时 attempts 保持高值，之后 2 次真实断线即触达上限**永久放弃重连**，且无任何 UI/状态暴露 failed | `onError: (Object error) { ... _scheduleReconnect(); }` + `onDone: () { ... _scheduleReconnect(); }`；`_reconnectTimer = Timer(delay, () { _reconnectAttempts++; _connectInternal(); });`；`_reconnectAttempts = 0; // Reset on success`（位于消息回调内） | 见下方 diff-2；或直接用 `websocket_chat_service_v2.dart` 的成熟实现替换该类 |
| M6-03 | **P1** | `mobile/lib/features/task/presentation/providers/task_provider.dart:519-561`（retryCompleteTask 同构：596-656） | 用户完成任务：`_taskRepository.completeTask` 成功后，`return result` 之前还要 `await` 两个本地后置步骤（`:519 consumeForExecution`、`:526 recordEntityExecution`）。任一抛异常即落入 catch，把本地任务标为 `syncStatus: failed` + `syncError`，UI 呈现"同步失败/重试"——但**服务端任务实际已完成**。用户点重试 → `retryCompleteTask` 再次调用 `_taskRepository.completeTask` → 服务端二次完成（学习时长/星火值等重复计入风险，取决于后端幂等性） | `final linkedPrediction = await _ref.read(predictionAttributionServiceProvider).consumeForExecution(...); await _ref.read(appEventStreamServiceProvider).recordEntityExecution(...); return result; } catch (e) { ... _updateTask(id, (task) => task.copyWith(syncStatus: TaskSyncStatus.failed, ...)); return null; }` | 见下方 diff-3：服务端调用成功后立即标记 synced 并返回结果，后置归因/埋点移出 try 或各自 try/catch 吞掉 |
| M6-04 | **P1** | `mobile/lib/app/routes.dart:118-123` | 冷启动/热启动时 auth 尚在 `isLoading`，此时到达的受保护深链（推送跳转 `/chat?session_id=x`、任务提醒 `/task/xxx`）被 redirect 无条件改写到 `'/'`（splash），原始 path 与全部 query 参数丢弃；加载完成后 refresh 只能落到 `/home`，深链功能失效 | `if (isLoading) { if (isOnAuth) return null; return isOnSplash ? null : '/'; }` | 见下方 diff-4：重定向到 splash 时用查询参数或 sessionStorage 保留原 URI，加载完成后还原目标 |
| M6-05 | P2 | `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1727-1746` | `IOWebSocketChannel.connect` 是异步握手，代码立即 `_updateConnectionState(connected); _reconnectAttempts = 0; _startHeartbeat();`。服务器不可达时 UI 先短暂显示"已连接"、消息进 sink 缓冲，随后 onError 才转入重连排队；`isConnected` 在该窗口为真也使 `sendMessage` 走直发分支 | `_channel = IOWebSocketChannel.connect(wsUri, ...); ... _updateConnectionState(WsConnectionState.connected); _reconnectAttempts = 0; _startHeartbeat();` | await `channel.ready`（web_socket_channel ≥2.2）后再置 connected；超时/异常落入 `_handleConnectionError` |
| M6-06 | P2 | `mobile/lib/features/auth/presentation/providers/auth_provider.dart:46,94-98` | 存储的 token 被服务端吊销后冷启动：`_resetInvalidStoredSession` 意图清除用户，但 `copyWith` 对 user 做空值合并（`user: user ?? this.user`），`user: null` 传不进去 → `isAuthenticated=false` 而 `user` 残留。`currentUserProvider`（dashboard_screen.dart:1041、private_chat_screen.dart:90、learning_portfolio_provider.dart:10 等消费）在此窗口返回过期用户 | `AuthState(... user: user ?? this.user ...)` 与 `state = state.copyWith(isLoading: false, isAuthenticated: false, user: null)` | copyWith 增加 `clearUser` 标志位（参照同文件 `clearError` 模式） |
| M6-07 | P2 | `mobile/lib/features/user/presentation/providers/settings_provider.dart:941-949` + `mobile/lib/app/routes.dart:114` | `onboardingCompletedProvider` 初始恒为 `false`，`syncForUser` 异步读 SharedPreferences/网络；router redirect 用 `ref.read` 同步取值。auth isLoading 翻转的瞬间 onboarding 状态多半还没同步完 → 老用户（已完成引导、本地存 true）被闪重定向到 persona onboarding，同步完成后 refreshListenable 再弹回 /home（闪烁、偶发停留在引导页直到网络返回） | `OnboardingCompletedNotifier(this._ref) : super(false) { _ref.listen<AuthState>(...unawaited(syncForUser(next.user)); }); ... }` | 引入"未决"三态（null=加载中），redirect 对 null 不做 onboarding 分支跳转 |
| M6-08 | P2 | `mobile/lib/features/home/presentation/providers/dashboard_provider.dart:666-670` | 首页数据加载失败后 `Future.delayed(5s)` 自动重试一次，重试仍失败则再次排程——**固定 5 秒、无退避、无上限**的无限轮询；离线时每 5 秒打满 dashboard/growth/predictive 三个请求 | `Future.delayed(const Duration(seconds: 5), () { if (mounted && state.error != null) { fetchData(); } });` | 加指数退避 + 最大次数，重试计数在成功时复位 |
| M6-09 | P2 | `mobile/lib/features/chat/presentation/providers/chat_provider.dart:829-843` + `websocket_chat_service_v2.dart:1746-1755` | 前一条消息流式生成中用户再发新消息：`sendMessage` 直接 `cancelActiveRun('new_message')` 并 `_streamGeneration++`，旧流在下一事件到达时静默 break——旧回复的已累积文本被 `finalizeRun` 丢弃（`shouldPreserveMessage` 对纯文本为 false），用户视角是上一条回复"凭空消失"；同时 WS 层连接级 pending flush 与每请求控制器在断线重连后（`_restorePendingFromDb`）可能对同一 request_id 重发，服务端幂等兜底但客户端无去重 | `if (state.isSending) { cancelActiveRun(reason: 'new_message'); }` | 将已积累的部分文本以"（中断）"消息保留，或在 UI 明示上一请求已取消 |
| M6-10 | P2 | `mobile/lib/core/services/websocket_service.dart:79,156` 与 `lib/gen/websocket.pb.dart` 的契约 | sync_engine 以二进制 Protobuf 发送 mastery 更新（`WebSocketMessage.fromBuffer`/`writeToBuffer`），而 `send()` 同一方法又接受 JSON Map——协议双轨依赖调用方自律；且二进制解析失败时把原始字节直接 `_controller.add(data)` 广播，消费方类型判断缺失即崩 | `final msg = WebSocketMessage.fromBuffer(data); _controller.add(msg); ... _controller.add(data);` | 解析失败时记日志并丢弃，不要广播原始字节 |
| M6-11 | P3 | `mobile/lib/features/chat/presentation/widgets/action_card.dart:607,636,691,705`；`expert_roundtable_widget.dart:272,277`；`profile_front_door_card.dart:46-47,419-420`；`features/home/presentation/widgets/exam_sprint_dashboard_card.dart:258,265`；`layers/background_layer.dart:55-57,69-70,225`；`effect_layer.dart:60`；`visual_renderer.dart:201`；`features/task/presentation/widgets/task_feedback_dialog.dart:380-382,476-500` | 核心链路 28 处硬编码 `Color(0xFF…)`，违反 AGENTS.md "UI 消费 core/design 令牌"规范；深色模式/高对比度/色盲模式下这些颜色不随主题变换 | `Color(0xFFFFA726), Color(0xFFFF7043), Color(0xFF8D4E1D)` 等 | 收敛进 `DS.*` 语义色令牌 |
| M6-12 | P3 | `mobile/lib/features/home/presentation/widgets/multi_goal_dashboard_card.dart:250,264,381`；`today_growth_status_card.dart:243`；`notification_list_screen.dart:48`；`features/task/presentation/screens/task_detail_screen.dart:523`；`task_create_screen.dart:696` | 核心链路 UI 存在 `zh ? '采用建议' : 'Use suggestion'` 式手写双语三元串，绕过 AppLocalizations arb 管线；arb 新增语言即漏翻 | `label: zh ? '采用建议' : 'Use suggestion'` | 迁入 arb 并 regen |
| M6-13 | P3 | `mobile/lib/features/splash/presentation/screens/splash_screen.dart:113,128`；`features/onboarding/presentation/screens/interactive_onboarding_screen.dart:280-557`（11 处）；`features/auth/presentation/screens/register_screen.dart:260` 等（auth/splash/onboarding/settings 共 32 处 `fontSize: <字面量>`） | 硬编码字号不随无障碍 fontScale 语义缩放（app.dart 的 TextScaler 线性缩放可作用，但不走设计令牌的排版档位） | `fontSize: 34`（splash 标题） | 使用 design 令牌排版档（DS.fontSize* 或 Theme.textTheme） |
| M6-14 | P3 | `mobile/lib/core/network/api_interceptor.dart:230-235` | debug 模式 LoggingInterceptor 完整打印请求体——登录/注册请求的明文密码进入日志（演示录屏/日志外泄风险） | `if (options.data != null) { _logger.d('Data: ${options.data}'); }` | 对 `/auth` 路径脱敏或只打印键集合 |
| M6-15 | P3 | `mobile/lib/features/task/presentation/providers/task_provider.dart:141` + `task_list_screen.dart:329-332` | `_runWithErrorHandling` 把 `e.toString()` 存进 state.error；任务列表页空态时把该原始串直接塞进 `CustomErrorWidget.page(message: state.error!)`——英文 Dio 堆栈首行直接呈现给中文用户 | `state = state.copyWith(isLoading: false, error: e.toString());` … `message: state.error!` | 经 `AppFailureMapper.from(e).userMessage` 归一（仓库内已有该设施，chat/auth 均在用） |
| M6-16 | P3 | `mobile/lib/features/task/presentation/providers/task_provider.dart:473-477` | `completeTask` 在请求发出**前**取消提醒；若后续完成失败，提醒已被取消且不重排，任务留在今日列表但再无通知 | `try { await _notificationScheduler.cancelTaskReminders(id); } catch (_) {}` | 移到服务端确认成功后再取消，失败路径重排 |
| M6-17 | P3 | `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:2012` | pong 判定为整串相等 `data == '{"type":"pong"}'`；网关若在 pong 中附加字段（时间戳等）则不被识别 → 心跳超时假阳性（有 3 次阈值 + 流活跃 120s 抑制兜底，故仅 P3） | `if (data == '{"type":"pong"}' || data == '{"type": "pong"}')` | 前缀/包含匹配或 JSON 解析 type 字段 |
| M6-18 | P3 | `mobile/lib/core/network/api_client.dart:108,188` | SSE 错误事件用字符串插值拼 JSON（`'{"message": "${e.message ?? "Connection lost"}"...}'`），message 含引号/反斜杠时下游 `jsonData` 解析为 null，错误信息丢失 | `data: '{"message": "${e.message ?? "Connection lost"}", ...}'` | 用 `json.encode(Map)` 构造 |

### P0/P1 修复建议（diff，未落地，仅建议）

**diff-1（M6-01：protobuf 工具链配对 + CI gen 步骤）**

```yaml
# mobile/pubspec.yaml（dependency_overrides 段新增）
dependency_overrides:
  protobuf: 6.1.0          # 与 protoc_plugin 25.x 配对；6.0.0 与任何可用插件都无法编译

# docker/proto-toolchain.Dockerfile
- RUN dart pub global activate protoc_plugin 22.3.0 \
+ RUN dart pub global activate protoc_plugin 25.1.0 \

# .github/workflows/ci.yml flutter-test job（Get Dependencies 之前）
      - name: Generate Dart Proto Code
        run: make proto-tools-build && make proto-gen
```

**diff-2（M6-02：core WebSocketService 重连）**

```dart
  void _scheduleReconnect() {
    if (_isManualDisconnect) return;
+   _cancelReconnectTimer();            // onError+onDone 双触发时不再叠加 Timer
    if (_reconnectAttempts >= _maxReconnectAttempts) {
      debugPrint('WebSocket max reconnect attempts reached');
      return;
    }
    final index = _reconnectAttempts.clamp(0, _maxReconnectAttempts - 1);
    final delay = _reconnectSchedule[index];
    _reconnectTimer = Timer(delay, () {
      _reconnectAttempts++;
      _connectInternal();
    });
  }

  void _connectInternal() {
    ...
    _channel!.stream.listen(
      (data) {
        ...
-       _reconnectAttempts = 0; // Reset on success   （从消息回调中移除）
      },
      ...
  }
+ // 连接建立即复位（IOWebSocketChannel.ready 可用时 await ready 后调用）
+ void _markConnected() { _isConnected = true; _reconnectAttempts = 0; }
```

**diff-3（M6-03：任务完成后置步骤隔离）**

```dart
      final result = await _taskRepository.completeTask(id, minutes, note);
      final updatedTask = TaskModel.fromJson(result.task);
      _updateTask(id, (task) => updatedTask.copyWith(syncStatus: TaskSyncStatus.synced));
      _ref.read(galaxyRefreshTriggerProvider.notifier).state++;
+     // 服务端已完成：此后步骤只影响归因/埋点，失败不得改变任务同步状态
+     try {
+       final linkedPrediction = await _ref
+           .read(predictionAttributionServiceProvider)
+           .consumeForExecution(executionType: 'task', entityType: 'task', entityId: id);
+       await _ref.read(appEventStreamServiceProvider).recordEntityExecution(...);
+     } catch (e) {
+       debugPrint('[Task] post-completion attribution failed (server state kept): $e');
+     }
      return result;
```

**diff-4（M6-04：loading 期深链保留）**

```dart
    redirect: (context, state) {
      final authState = ref.read(authProvider);
      final isAuthenticated = authState.isAuthenticated;
      final isLoading = authState.isLoading;
      final isOnSplash = state.uri.path == '/';
      ...
      if (isLoading) {
        if (isOnAuth) return null;
        if (isOnSplash) return null;
+       // 保留原始深链，加载完成后由 splash 分支还原
+       final target = state.uri.toString();
+       return '/?redirect=${Uri.encodeComponent(target)}';
      }
      ...
+     // splash 上的还原分支（isAuthenticated 后）：
+     if (isAuthenticated && isOnSplash) {
+       final pending = state.uri.queryParameters['redirect'];
+       if (pending != null && pending.startsWith('/') && !pending.startsWith('//')) {
+         return pending;                       // 还原深链
+       }
+       return '/home';
+     }
```

---

## 3. 验证良好清单

**聊天流式链路（websocket_chat_service_v2.dart + chat_provider.dart）**
- 重连为 6 档指数退避（800ms→12.2s）+ 0-250ms jitter，timer 先 cancel 后重建，max 达限广播 `MAX_RETRIES_EXCEEDED` 并对 pending 消息逐一 `markFailed`（M6-02 缺陷仅存在于 core 侧老服务，此实现无此问题）
- 心跳 ping/pong（30s 间隔、60s 超时、连续 3 次失败才重连），且"流式接收活跃 + 120s 内有数据"时抑制心跳重连，避免打断正在生成的回复（`_handleHeartbeatFailure` P0 修复注释）
- 每请求独立 `StreamController<ChatStreamEvent>`，按 `request_id` 精确路由，单请求时允许空 request_id 回退路由；`_incomingMessageChain` 串行化入站处理保证 delta 顺序；>12KB 大帧走 `compute` isolate 解析，小帧直解——中文多字节经 `json.decode` 字符串整体解码，无截断风险
- terminal fallback：FullTextEvent 后 2s 无 Done 则合成 DoneEvent 防止 UI 永久挂起；ContinueEvent 保持请求开放
- 401 单飞刷新：`_refreshCompleter` 并发等待、超过 `_max401Retries` 才登出、登出前对 pending 消息广播 `MESSAGES_LOST`（每条消息有明确终态）
- 离线队列：Isar 持久化（可跨进程存活）+ 内存上限 50 条溢出策略（最旧报 `PENDING_QUEUE_OVERFLOW` 给对应流）+ 重连后 DB restore 与 flush 解耦（restore 失败仍 flush）
- 生命周期：后台断连并关闭流、前台恢复重连（attempts 清零）；`dispose` 对 reconnect/heartbeat/terminalFallback 三类 Timer、全部 controller、订阅完整清理，且幂等
- chat_provider：`_streamGeneration` 请求代际守卫 + `isCurrentRequest()` 双检查（事件循环与 catch/finally 均查）；8 分钟流式超时（超时发 `STREAM_TIMEOUT` retryable 事件）；状态更新经 `_streamDebouncer` 防抖合帧，Done 即时 flush；`sawTerminalEvent` 保证 finalizeRun 幂等；失败流不保留裸部分文本（注释明确防"partial+full 重复消息"）；`finally` 兜底复位 isSending
- chat_screen：`reverse: true` ListView 天然维持底部；新消息/最新助手消息新增 widget 时 `_scrollToBottom`；错误经 `AppFeedback.error` 呈现 + 10s 自动清除（清除前校验错误未变）；全部 `listenManual` 移入 initState（注释明确修复过 build 内监听）；AnimationController/FocusNode 全部 dispose

**网络层**
- AuthInterceptor：token 刷新单飞（Completer 并发等待）、auth/login/refresh 路径豁免防循环、无 refresh token 的 401 不触发登出循环、重试走无 auth 拦截器的独立 Dio（SSL pinning 保留）
- RetryInterceptor：502/503/504 指数退避（500ms×2^n）+ cancel 不重试
- api_client SSE：`utf8.decoder` chunked 转换，跨块中文多字节安全；`\n\n` 与 `\r\n\r\n` 双分隔符解析

**路由**
- 未登录访问受保护页 → `/login`；已登录访问 auth/splash → `/home`；persona onboarding 与 modeling 豁免/回流分支闭环（无死循环）；`errorBuilder` 未知路由兜底页 + 回首页按钮；`refreshListenable` 正确桥接 authProvider/onboarding 变化（避免 redirect 内 watch 的反模式）；`/legal/terms|privacy` 均已注册且在公开白名单

**任务**
- 乐观更新带 `syncStatus` 三态（pending/synced/failed）+ 列表页 retry 入口（task_list_screen.dart:418,536 `retryCompleteTask`）+ 删除撤销（`recentlyDeletedTask`）；quick actions（snooze/skip/tooHard）后置日历与提醒同步；T15 withdraw drafting 已确认不在代码路径（未发现回归）

**首页/引导/启动**
- DashboardState 提供 `.loading()/.error()` 构造器，dashboard_screen.dart:201 对 error+loading 有专门 UI，SparkleRefreshIndicator 支持手动刷新；错误态自动重试一次（虽为 M6-08 无退避）
- splash/onboarding 动画控制器全部 dispose、async 后 `mounted` 检查齐全；onboarding 页进度持久化恢复（`_restorePage`）
- main.dart：启动异常兜底 App（不白屏）、ErrorWidget.builder 品牌化替换、FlutterError/platformDispatcher 双通道崩溃上报、deferred warmup 不阻塞首帧

**i18n 卫生**
- 核心链路 provider 层全面走 `I18nService.instance.l10n` / `context.l10n` / `S.*`；auth 屏（login/register/forgot/reset）错误经 `AppFeedback.error + UserFacingError.from(e) + errorCode` 呈现，无裸异常直出；未发现核心链路 Text() 直写中文（仅 M6-12 所列 zh/en 三元串）

---

## 4. 测试执行记录

环境：worktree `wt6`（main@90daac8a），`flutter pub get` 正常（protobuf 按 lock 解析为 6.0.0；**pubspec.yaml 无 protobuf override**，与任务书"6.1.0 override 已在"不符）。

1. `flutter analyze`（gen/ 缺失，刚 clone 状态）：**lib/ 下 4 个 error**（`sync_engine.dart:267,275` undefined `UpdateNodeMasteryRequest`/`WebSocketMessage`；`websocket_service.dart:79,156` undefined `WebSocketMessage`）——gen 为 gitignore 构建产物，属环境缺生成，不是基线代码缺陷。
2. `make proto-gen`（docker 镜像不存在；host 回退，本机 protoc_plugin 为缓存最新版）生成 gen 后重跑 analyze：**lib/ 0 error，137 warning**（几乎全部 unused_import / deprecated groupValue），全仓 6794 issues（大头来自 vendored `third_party_plugins/`，与移动端切片无关）。
3. `flutter test test/core test/features/chat test/features/task test/features/auth test/features/settings test/features/onboarding`：**`+101 -45: Some tests failed`**。三轮验证（换 protoc_plugin 22.3.0 / 加 WKT 重生成）失败数恒定 45，抽查错误全部是 `lib/gen/*.pb.dart` 与 `sync_engine.dart` 的**编译错误**（`PbList` 构造、`toProto3Json`、双 Timestamp 类型冲突），**零业务逻辑失败**。分目录：core +95/-15、chat +6/-18、task +0/-7、auth +0/-2、settings +0/-2、onboarding +0/-1（0-pass 目录为整套编译失败）。
4. 根因定位（交叉证据）：protobuf-6.0.0 CHANGELOG "Hide PbList constructors… Add well-known proto types… required for protoc_plugin-25.0.0"；protobuf-6.1.0 CHANGELOG "Make BuilderInfo methods accept GeneratedMessage Function() typed closures"；protoc_plugin-22.3.0 pubspec 依赖 `protobuf: ^4.1.0`；protoc_plugin-25.0.0 依赖 `protobuf: ^6.0.0` 但其产物（`$_createMessage`）仅 6.1.0 支持 → **基线锁定的 6.0.0 与 Dockerfile 钉的 22.3.0 以及本地全部可用插件（22.3.0/25.0.0/25.1.0）均无法配对编译**。修复路径见 diff-1。
5. 复现约束说明：为修复编译而把 protobuf 升至 6.1.0 需改 pubspec（本次审查禁改代码），故 45 个编译失败套件中的业务逻辑断言（chat WS v2 / chat provider / task provider 各测试的意图）未能实际执行，留待 override 落地后回归。

---
*报告生成：审查员 6 号｜2026-09-18｜基线 90daac8a*
