# 全系统审查·第二轮（R2）— 06 移动端·核心体验链

- 审查员：6 号（R2 复审）｜2026-09-18｜基线 main@ca86bda8（冻结 worktree `wt6`，R1 修复已集成）
- 切片：同 R1——启动 → 引导 → 登录 → 首页 → 聊天 → 任务 → 设置核心链；本轮聚焦 ①R1 修复验证 ②运行时/集成视角（启动流推演、路由矩阵、Web 编译探针、WS×provider 集成层）③F6 移交专项
- 环境：Flutter 3.41.3；`pubspec.yaml` 已锁 `dependency_overrides: protobuf: ^6.1.0`（package_config 实际解析 6.1.0）；`mobile/lib/gen` 为 25.1.0 插件产物，全部测试可编译执行。

---

## 1. 修复验证结论（06-fixes.md 7 项）

**结论：7 项全部落地且与修复报告描述一致，5 个新测试文件 11 用例全绿；但 M6-02 的"ready 即复位 attempts"修法在"握手成功后服务端立即断开"场景会退化为 800ms 恒频无限重连（见 §1.1 与发现表 M6-R2-02）。**

| ID | 落地位置核对 | 判定 |
|----|--------------|------|
| M6-02 (P1) | `core/services/websocket_service.dart:140-159` `_scheduleReconnect` 先 `_cancelReconnectTimer()`；`:80-95` `channel.ready.then` 握手成功置 `_isConnected=true` 并复位 attempts、`catchError` 走重连且 `identical(_channel, channel)` 防陈旧回调；`:97` 消息回调内旧复位已移除 | ✅ 落地，附带保留 ⚠️（§1.1） |
| M6-03 (P1) | `task_provider.dart:492-516` 服务端成功即置 synced 并 return；`:530-586` `_runPostCompletionSteps` 自带 try/catch（只 debugPrint，不触碰同步状态）；`retryCompleteTask:616-623` 对 completed+synced 幂等跳过 | ✅ 落地 |
| M6-04 (P1) | `app/routes.dart:48-66` 参数名与 `_safePendingRedirect`（拒绝空串/`//` 开头）；`:139-150` loading 期深链经 `/?redirect=` 中转；`:153-161` unauth 去 `/login` 带 `return_to`；`:164-170` authed+splash/auth 优先还原 | ✅ 落地 |
| M6-06 (P2) | `auth_provider.dart:40,47` `clearUser` 标志；`:97-105` `_resetInvalidStoredSession` 使用之 | ✅ 落地 |
| M6-10 (P3) | `websocket_service.dart:99-108` 二进制解析失败记日志丢弃，不再广播原始字节 | ✅ 落地 |
| M6-14 (P3) | `api_interceptor.dart:213-272` 可注入 Logger + `_sensitiveBodyFields`（12 键）+ `sanitizeBodyForLog`，`onRequest` 打印前脱敏、非 Map 请求体不打印 | ✅ 落地 |
| M6-16 (P3) | `task_provider.dart` 提醒取消移入 `_runPostCompletionSteps` 开头（服务端确认后才取消；该 try 内还单独包了 cancel 的 catch） | ✅ 落地 |

测试：`flutter test --concurrency=4` 五文件（websocket_service / task_complete_sync / logging_interceptor_redaction / auth_state_clear_user / router_deep_link）→ **+11: All tests passed!**

### 1.1 M6-02 修法复查：ready 复位在"握手成功即断开"场景的重连风暴

**答案：会。该场景下复位→断开→复位循环成立，退避永不升级、max-attempts 守卫失效。**

推演（`websocket_service.dart:49-138`）：Timer 回调 `_reconnectAttempts++` 后进 `_connectInternal` → 新握手成功 → `ready.then` 把 attempts 复位 0 → 服务端立即发 close → onDone → `_scheduleReconnect` 读到 attempts=0 → 永远取 `_reconnectSchedule[0]`=800ms → 无限循环（周期 ≈ 800ms + 握手耗时）。attempts 只有在 ready 失败（握手被拒，如连接拒绝/502）路径才保留递增。

触发面：网关 crash-loop（进程接受 TCP+升级后即死）、LB 优雅排水、服务端热重载——"接受升级然后立刻断"在真实运维里并不罕见。与修复前的缺陷对比：修好了"静默连接耗尽预算→永久放弃"，却把"接受即断"从"3 次后永久放弃（旧双调度下）"变成了"800ms 恒频无限打"。速率有界但时长无界，手机端可持续数小时。

**建议修法（时长门控复位，一处改动同时保住两个场景）**：记录握手成功时刻，断开时仅当"本次连接存活 ≥ 30s"才复位预算：

```dart
  DateTime? _connectedAt;                     // 新增
  // ready.then:
  _isConnected = true;
  _connectedAt = DateTime.now();
  _reconnectAttempts = 0;
  // onError/onDone 内、调用 _scheduleReconnect 前：
  final up = _connectedAt == null ? Duration.zero : DateTime.now().difference(_connectedAt!);
  if (up >= const Duration(seconds: 30)) _reconnectAttempts = 0; // 稳定连接断开才给新预算
  _scheduleReconnect();
```

静默连接存活必然 >30s → 断开时预算新鲜（保留本次修复的收益）；接受即断的会话存活 <30s → 预算照常递增到 6 后停止。注意 v2 聊天 WS 存在同构缺陷且更重（见 M6-R2-01），建议一并修。

---

## 2. 启动流推演与路由重定向矩阵复核

### 2.1 启动流分支枚举（main → splash → 守卫 → 落地）

Splash 为纯展示屏（`splash_screen.dart` 无任何自主跳转），启动流的状态机完全由 `routes.dart` redirect 驱动，`refreshListenable` 桥接 authProvider/onboardingCompletedProvider——结构上消除了"splash 定时器与守卫赛跑"类缺陷。

| 分支 | 链路 | 终态 | 判定 |
|------|------|------|------|
| 冷启动·无会话 | `/`(loading) → loading 完成 isAuthenticated=false → `/login` | `/login` | ✅ |
| 冷启动·有效会话 | `/`(loading) → authed → `/home`（onboarding 未决时先弹 persona，见 M6-07 残留） | `/home`/persona | ✅ |
| 冷启动·吊销 token | checkAuthStatus → getCurrentUser 抛 → `_resetInvalidStoredSession`（clearUser 已生效）→ `/login` | `/login`，`currentUserProvider` 无残留旧身份 | ✅（M6-06 修复后） |
| 热恢复·会话有效 | 前台恢复，auth 已决，redirect 直放当前页 | 原页面 | ✅ |
| 登出态 | `logout()` → `state = AuthState()`（isLoading=false 默认）→ 当前页 → `/login?return_to=<当前页>`；再登录由 redirect 还原 | `/login` 携 return_to | ✅ |
| token 过期（运行中） | 401 → AuthInterceptor 单飞刷新 → 刷新失败登出 → 同上 | `/login` | ✅ |
| 深链冷启动·authed | `/task/1`(loading) → `/?redirect=/task/1` → authed → pending 还原 `/task/1` | `/task/1` | ✅（M6-04） |
| 深链冷启动·unauth | → `/login?return_to=/task/1` → 登录成功（login 屏不主动 go，注释明确交 router redirect）→ redirect 在 `/login?return_to=` 上还原 | `/task/1` | ✅ |
| 深链冷启动·未完成引导 | 还原 `/task/1` 后 onboarding=false → personaOnboarding；引导完成后去 `/home` | persona（深链让位于引导，一次性，无循环） | ✅ 可接受 |
| 访客 | registrationSource='guest' → 跳过 onboarding 分支 → `/home` | `/home` | ✅ |

### 2.2 重定向矩阵（location × authState，24 组合）

枚举变量：isLoading / isAuthenticated / onboardingCompleted / guest / location（`/`、受保护页、auth 页、persona、modeling、legal、未知路由、带 redirect/return_to 参数的变体）。关键结论：

- **无死循环（双层保险实证）**：go_router 13.2.5（pubspec.lock 实际版本）`configuration.dart:361/395` 对"redirect 输出 == 输入 location"直接终止；`:491-497` 连续 redirect 超 `redirectLimit=5` 或重复落点抛 `GoException('redirect loop detected')` → 落 errorBuilder 兜底页。手工构造自嵌套 `/?redirect=%2F%3Fredirect%3D...` 最坏落在错误页，不会挂死。
- **无丢失**：loading 期所有非 splash/auth location 均带参中转；unauth 落 `/login` 时 splash 中转参数先解包再随行；authed 在 splash/auth 上 pending 优先于 `/home` 兜底（`routes.dart:164-170`）。
- **参数自嵌套/空值边界**：`/?redirect=/` → pending='/' → 还原 '/' → 再 redirect '/home'，收敛；`/?redirect=`（空）→ pending=null → '/home'；`return_to=/login` → authed 上先还原 '/login' 再二次 redirect '/home'，收敛。
- **24 组合逐项过审未发现死循环/丢失/死落地**；完整的 per-combination 表已在推演中核过，无新增缺陷需登记（`/\evil.com` 绕过见 M6-R2-05，属加固项）。

### 2.3 与 M6-07 残留的交互

M6-07（onboarding 二态闪跳）未修，且与 M6-04 新增了一个轻微交互：authed+splash 的 pending 还原分支先于 onboarding 分支执行，老用户在 onboarding 未同步完成窗口内还原的深链会随即被改写到 persona，同步完成后弹回 `/home`——比修复前多了一跳，但仍收敛，深链在引导完成后不还原。修 M6-07 三态化后此交互自动消解（见 §4 修法 2）。

---

## 3. Web 编译探针结论

`flutter build web --debug`（Flutter 3.41.3，完整日志 `/tmp/wt6_webbuild.log`，退出码 1）：**失败，且失败点不在原生插件，而在第一方 Isar 生成代码。**

### 3.1 精确失败清单

**墙 1（致命，dart2js 编译期）：41 个 `The integer literal ... can't be represented exactly in JavaScript`，全部来自 isar_generator 产出的 63 位集合 ID 字面量（`Isar.fastHash`），分布在 7 个第一方生成文件：**

| 文件 | 错误数 |
|------|--------|
| `lib/core/offline/local_database.g.dart` | 12 |
| `lib/core/offline/models/vocab_word.g.dart` | 6 |
| `lib/core/offline/models/translation_record.g.dart` | 6 |
| `lib/core/offline/models/offline_chat_message.g.dart` | 5 |
| `lib/core/offline/models/focus_session_record.g.dart` | 5 |
| `lib/core/statistics/data/models/cached_statistics_model.g.dart` | 4 |
| `lib/core/analytics/models/user_analytics_event.g.dart` | 4 |

protobuf（6.1.0 + 25.1.0 产物）、`gen/`、vendored file_picker/fluwx 等均未报错。构建在 dart2js 阶段终止，**无体积可记录**。

**墙 2（修完墙 1 后必撞）：vendored `isar_flutter_libs` 3.1.0+1 只有 android/ios/linux/macos/windows 目录，无 web 实现且基于 dart:ffi；wasm dry-run 已报 16 处 `dart:ffi can't be imported when compiling to Wasm`（package:isar ×12、package:ffi ×4）。`jpush_flutter` 同样仅 android/ios。**

### 3.2 多平台铺路改造建议（按成本递增）

1. **最小解锁（推荐先行）**：这 7 个 `.g.dart` 由 build_runner（isar_generator）生成——不是 proto gen 域，可改生成输入。isar_generator 的集合 ID 是对集合名做 `Isar.fastHash` 的结果，给每个 `@collection` 加 `@Name('<候选短名>')`（离线脚本枚举到 |hash| < 2^53 的名字即可），重新 build_runner 生成后 41 个字面量全部 JS-safe。代价：集合名变化 = 既有 native 库迁移/重建（参赛演示阶段可接受，dev 环境直接清库）。
2. **jpush/push 服务**：`unified_push_service.dart`/`jpush_service.dart` 走标准条件导入（`push_service_io.dart` / `push_service_stub.dart`，web 桩 no-op）。lib/ 下直接 `import 'dart:io'`/`dart:ffi` 的文件共 41 个（`http_client_pinning_io.dart` 已是条件导入范式可照抄），逐一过闸。
3. **结构性（大工程，多平台立项再评估）**：Isar 模型用 `part 'x.g.dart'`，**part 无法条件导入**，所以"web 上不编译 Isar"只能通过在 `LocalDatabase` 门面后做 io/web 双实现（web 用 IndexedDB/Hive/内存桩、跨门面只传 DTO）实现——offline 队列/sync_engine/统计缓存全在 Isar 上，属专项改造。建议多平台演示先走"web 只读演示构建 + 骨架桩"路线。

---

## 4. 复审发现表（R2 新增）

| ID | 严重度 | file:line | 触发场景 | 证据摘录 | 建议修复 |
|----|--------|-----------|----------|----------|----------|
| M6-R2-01 | **P2** | `websocket_chat_service_v2.dart:1743`（对照 `:2276-2320`） | 服务端持续不可达：`_triggerReconnect` 递增 attempts（→1）→ timer 触发 `_establishConnection` → `_establishConnectionAsync` 在 `connect()` 后立即 `_reconnectAttempts = 0` → 握手失败经 stream onError 回 `_triggerReconnect` 又从 0 递增到 1 → 退避永远停在 `schedule[0]`=800ms+jitter；`>= _maxReconnectAttempts`(:2276) 永不满足，`failed` 状态与 `MESSAGES_LOST`/`MAX_RETRIES_EXCEEDED` 终态广播全部不可达 | `_channel = IOWebSocketChannel.connect(...); ... _updateConnectionState(WsConnectionState.connected); _reconnectAttempts = 0;`（连接未握手即复位） | 与 M6-05 合并修（见 §5 修法 1）：复位挪到握手确认之后。这正是 M6-02 在 core 服务修掉的同构缺陷——v2 侧因复位点在 connect 后而更重 |
| M6-R2-02 | **P2**（条件触发） | `websocket_service.dart:80-95`（M6-02 修复引入的复位点） | 网关 crash-loop/LB 排水："握手成功→立即断开"反复发生：ready 复位 attempts→onDone 调度 800ms→再握手→再复位，退避永不升级、max=6 永不触达 | `channel.ready.then((_) { ... _reconnectAttempts = 0; })` + onDone `_scheduleReconnect()` 读到的恒为 0 | 时长门控复位（§1.1 diff）：断开时仅当连接存活 ≥30s 才复位预算；静默长连接与快速失败两场景同时正确 |
| M6-R2-03 | P3 | `chat_provider.dart:71-75` | 断线重连成功后 chat_provider 只把 `wsConnectionState` 镜像进 state，**无历史消息补拉**：离线窗口内服务端完成并持久化的助手回复，用户停留在当前会话时永远看不到（重进会话才随 loadConversation 出现）；用户自己发的消息由离线队列 flush 保障，不对称 | `_chatRepository.connectionStateStream.listen((connectionState) { state = state.copyWith(wsConnectionState: connectionState); })` | reconnecting→connected 迁移且有当前 conversationId 时，按最后一条消息时间戳/id 增量拉取一次会话历史并按 id 去重合并 |
| M6-R2-04 | P3 | `app/routes.dart:56-66` `_safePendingRedirect` | 防开放重定向校验只拒绝 `//` 前缀，`/\evil.com`（反斜杠）可通过；GoRouter 场景实际危害仅落在 errorBuilder（13.2.5 pushState 无法跨源、环路保护已实证），但属廉价加固点 | `if (!pending.startsWith('/') \|\| pending.startsWith('//')) return null;` | 增加 `pending.contains('\\')` 与控制字符拒绝；顺带考虑限制长度（防超长 URL 塞爆浏览器地址栏） |
| M6-R2-05 | P2（多平台阻塞） | §3.1 所列 7 个 `.g.dart` + vendored isar/jpush 无 web 实现 | `flutter build web` 无法出包 | 41 个 64 位整数字面量硬错误 + dart:ffi | §3.2 改造路线（@Name 短名重生成 → 条件导入闸 → LocalDatabase 门面） |

### 4.1 F6 移交 4 条逐条诊断

| 移交项 | 诊断结论 |
|--------|----------|
| 1. `channel.ready` 未消费 → unhandled exception（建议 v2 一并核查） | core 服务：已在 M6-02 修复中闭环（`ready.catchError` 消费 + 测试用例锁定，本次复跑通过）。**v2：确认存在且未修**——`websocket_chat_service_v2.dart` 全文无任何 `.ready` 引用（grep 实证），握手失败的异常沿 `ready` future 未消费路径泄漏（stream onError 是另一条已处理的通道）；并入 M6-R2-01/M6-05 的修法 1 一起处理（`await channel.ready` 超时包装 + catchError → `_handleConnectionError`） |
| 2. `HttpServer.close(force:true)` 断不开已升级 WS 连接 | 诊断属实（升级后 socket 脱离 HttpServer 连接管理，dart:io 语义如此）。纯测试基建经验，无需改产线代码；建议后续为 v2 重连测试搭 TCP 代理式断连工装时引用该注释 |
| 3. M6-01 工具链配对核对（Dockerfile 22.3.0 / CI gen 缺失） | **main 已闭环**：`docker/proto-toolchain.Dockerfile:44-46` 已钉 `protoc_plugin 25.1.0` 并附配对说明注释；`ci.yml` 的 proto 相关 job 均有 `make proto-tools-build && make proto-gen`（:46/:166/:402/:568/:620/:623）；mobile pubspec 锁 `protobuf: ^6.1.0` 且实际解析 6.1.0。三条要素齐备，无需再动 |
| 4. LoggingInterceptor 非 Map 请求体不再打印 | 诊断：行为变化影响面=文件上传（`file_upload_service.dart:231`、`auth_repository.dart:296`、`document_repository.dart:27` 三处 FormData/MultipartFile），上传体本就含 PII 风险（文件名），不打印是合理保守取向，无功能影响。维持现状；如需可观测性，后续白名单打印 FormData 的字段名+文件名（不含内容）即可 |

### 4.2 剩余清单（10 项）挑 3 个最高价值修法（R2 修复波输入）

**修法 1 — M6-05（P2）+ M6-R2-01（合并为一次改动，`websocket_chat_service_v2.dart`）**

```dart
      // 现状（:1741-1743）：
      //   _updateConnectionState(WsConnectionState.connected);
      //   _reconnectAttempts = 0;
      // 改为握手确认后再置态/复位；失败并入既有 _handleConnectionError：
      unawaited(
        _channel!.ready.timeout(const Duration(seconds: 10)).then((_) {
          if (_disposed || !identical(_channel, channel)) return;
          _updateConnectionState(WsConnectionState.connected);
          _reconnectAttempts = 0;
        }).catchError((Object e) {
          if (_disposed || !identical(_channel, channel)) return;
          _handleConnectionError(e);   // 复用 401 检测/错误广播/重连排程
        }),
      );
```

收益：a) UI 不再闪"已连接"（M6-05 原始诉求）；b) ready 异常被消费（F6 移交 1）；c) `_reconnectAttempts` 不再每轮清零，退避 800ms→12.2s 六档真实生效，持续宕机时可达 `failed` 终态并触发 pending 的 `MESSAGES_LOST`。测试：fake channel factory 暴露可控 ready 的 Completer，锁定三断言（未 ready 前 state≠connected / ready 失败走重连且 attempts 递增 / 连续失败退避时长单调上升）。

**修法 2 — M6-07（P2）：onboarding 三态化**

```dart
// settings_provider.dart
class OnboardingCompletedNotifier extends StateNotifier<bool?> {   // bool → bool?
  OnboardingCompletedNotifier(this._ref) : super(null) { ... }     // null = 未决
  Future<void> syncForUser(UserModel? user) async {
    if (user == null) { state = false; return; }
    ...  // 各同步分支照旧在拿到结果时置 bool；网络失败路径置 false 前可先保持 null
  }
}
```

```dart
// routes.dart redirect（:135, :172-184）
final onboardingCompleted = ref.read(onboardingCompletedProvider); // bool?
// 未决期间不做 onboarding 相关改写，维持当前落地页（消灭闪跳与 2.3 节的深链多跳）：
if (isAuthenticated && !isGuestUser && onboardingCompleted == false && ...) return persona;
if (isAuthenticated && (onboardingCompleted == true || isGuestUser) && isOnPersonaOnboarding) return '/home';
```

消费方核对（已 grep）：仅 `routes.dart`（redirect 两处）、`user_persona_screen.dart:58`（watch，null 需按"加载中"渲染）、`modeling_chat_screen.dart:618,678`（`setCompleted(true)` 不受影响）。router 对 `bool?` 无感知成本，redirect 中 null 走"不跳转"即天然正确。

**修法 3 — M6-08（P2）：dashboard 失败重试退避+封顶（`dashboard_provider.dart:664-670`）**

```dart
      state = DashboardState.error(failure.userMessage, failure: failure);
      // 指数退避 + 封顶；成功路径在 fetchData 开头 _dashboardRetryCount = 0
      final attempt = (_dashboardRetryCount++).clamp(0, 3);
      final delay = const [5, 15, 45, 120][attempt];
      Future.delayed(Duration(seconds: delay), () {
        if (mounted && state.error != null) fetchData();
      });
```

`fetchData()` 成功路径首行复位 `_dashboardRetryCount = 0`；离线时最坏 2 分钟一次而非恒 5 秒打满 dashboard/growth/predictive 三接口。

（未入选说明：M6-09 需产品确认保留形态；M6-11~13 量大纯打磨；M6-15/17/18 低危有兜底——维持 R1 排序。）

---

## 5. 测试执行记录

环境：worktree `wt6`（main@ca86bda8），`flutter pub get` 正常，protobuf 解析 6.1.0，`lib/gen` 已生成。

1. 修复波 5 文件：`flutter test --concurrency=4 test/core/services/websocket_service_test.dart test/features/task/presentation/providers/task_complete_sync_test.dart test/core/network/logging_interceptor_redaction_test.dart test/features/auth/presentation/providers/auth_state_clear_user_test.dart test/app/router_deep_link_test.dart` → **+11: All tests passed!**（M6-02×2+M6-10×1、M6-03×2+M6-16×1、M6-14×1、M6-06×2、M6-04×2）
2. 路由回归：`flutter test --concurrency=4 test/app` → **+23 -3**；3 个失败与 R1 基线噪音逐一同名（router_smoke 'loads critical secondary routes'、main_actions_smoke×2），**零新增失败**。
3. Web 探针：`flutter build web --debug` → 退出码 1；41 个 dart2js 整数字面量错误（§3.1 清单）+ 16 处 wasm ffi 警告；完整日志 `/tmp/wt6_webbuild.log`（会话产物，不入库）。
4. 静态核对：`go_router 13.2.5` redirect 环路保护源码（configuration.dart:361/395/491-497）；v2 无 `.ready` 引用（grep 实证）；`return_to` 在 lib 内除 routes.dart 外无消费方（还原完全依赖 router redirect，login 屏注释明确该契约）。

## 6. 基线噪音确认（未重报）

insights overview、router_smoke 'loads critical secondary routes'、main_actions_smoke×2 为基线红；T32 room UI 测试缺失已知——本轮均未列入发现表。

---
*报告生成：审查员 6 号（R2）｜2026-09-18｜基线 ca86bda8*
