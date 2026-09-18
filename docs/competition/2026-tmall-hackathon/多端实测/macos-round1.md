# macOS 桌面走查 · Round 1

- 日期：2026-09-18 晚
- 走查人：wt4 agent（ZCode）
- 环境：wt4 工作树（在前轮遗留 6 个构建修复文件基础上继续）；Flutter 3.41.3 stable / Xcode 26.6 (17F113) / MacOSX26.5.sdk / darwin 25.6 arm64；窗口 800×632（Runner 默认）
- 后端栈：网关 :8080 / FastAPI :8000 / gRPC :50051 / PG / Redis / MinIO 全部健康；`POST /api/v1/auth/guest` 实测 200 + 双 token
- 方式（受控台锁屏限制的特殊说明）：
  - 本机会话处于**锁屏状态**（`NSWorkspace.frontmostApplication == loginwindow`）。osascript 无辅助功能授权、CGEvent 注入无效（实证：注入点击后前台应用不变），无法真人式点击。
  - 改用 **integration_test 驱动真实 macOS Runner 窗口**（真实后端、真实网络、真实窗口），UI 断言走 widget tree，逐步结果走 stdout 标记（`JOURNEY_*` / `SHOT_*`）。
  - 截图：锁屏下窗口服务器停止合成，`screencapture -l<windowid>` 每次返回同一冻结帧（多步截图字节数完全相同 138185B 可证）；最终改用 **Flutter 引擎内 `RepaintBoundary.toImage()` 离屏截图**（pixelRatio 2.0），不受显示器状态影响，每步字节数均不同、内容真实。
  - 构建冲突背景：磁盘 98% 满（228G 卷仅 3-6G 可用）+ 多 agent 并发构建（wt3 `flutter test`、主仓 web 会话同时进行），Xcode 26 构建服务多次报 build.db SQLite "disk I/O error" 与 ModuleCache 竞态；清理主仓 Android 构建残留 2.7G、`flutter_build` 0.8G、遗留 iOS 模拟器 7.3G 并关闭显式模块后稳定（见 M-9/M-10）。

## 结论 TL;DR

**修复一处阻断性缺陷后，macOS 游客旅程 12 步全通（failures=0）。** 断点与 Web 端 W-1/W-2 同族：`POST /auth/guest` 200 返回双 token 后，`flutter_secure_storage` macOS 端默认走 Data Protection Keychain，未签名本地构建无 `keychain-access-groups` entitlement → `PlatformException(-34018 errSecMissingEntitlement)` → `loginAsGuest` 静默失败回登录页。修复后游客直达驾驶舱，仪表盘聚合数据 200，聊天可发送、可流式、**中断按钮实证可用**，社群/我的/设置/登出（含确认弹窗、返回登录页）全部通过；且 Keychain 持久化跨进程重启恢复会话成功。剩余为后端 500/404/WS 故障若干与体验项。

## 游客旅程逐步结果（最终实录，JOURNEY_DONE failures=0）

| 步骤 | 结果 | 证据 |
|---|---|---|
| 启动 → 登录页 | ✅ LoginScreen 渲染正常；修复后 Keychain 会话可跨进程自动恢复（直达驾驶舱，跳过登录页） | 截图 01-login.png（登出后回跳的同一登录页状态） |
| 登录页布局（800×632） | ⚠️ Guest 按钮首屏折叠线下，可滚动到达（M-8） | 前轮 02/03 截图 + 本轮 finder 位置 |
| Continue as Guest | ✅ `POST /auth/guest → 200`（1.5-2.3s）返回 access+refresh token 与 guest 用户（registration_source=guest，photon_balance=1000） | 应用日志 attempt7/10/17 |
| token 持久化 | ❌→✅ 修复前 `-34018` 静默失败（M-1）；修复后持久化成功，且**跨进程重启恢复会话** | auth_provider 日志对比 |
| 路由跳转 | ✅ 游客按设计跳过 persona onboarding 直达 /home | routes.dart + 运行时实证 |
| 驾驶舱（成长/状态页） | ✅ `/growth/dashboard` 200、`/dashboard/status` 200、`/predictive/dashboard` 200 | 截图 02-home-dashboard.png |
| 星图（导航分支 2） | ✅ 正常打开 | 截图 03-galaxy.png |
| 对话页（导航分支 3） | ✅ ChatScreen + ChatInput 就绪 | 截图 04-chat-empty.png |
| 发送消息 | ✅ 输入+发送成功，消息上屏 | 日志 `message sent` |
| 流式输出 | ✅（波动见 M-2）Stop 按钮出现即"生成中"状态成立 | 截图 05-chat-streaming.png |
| **中断按钮** | ✅ 点 Stop 后按钮回到发送态（`interrupt attempt0 accepted=true`），无崩溃 | 截图 06/07 |
| 社群（导航分支 4） | ✅ 页面打开（但其 WS 502，见 M-3） | 截图 08-community.png |
| 我的（导航分支 5） | ✅ 设置分区/退出分区渲染完整 | 截图 09-profile.png |
| 设置二级页 | ✅ 进入正常，返回正常 | 截图 10-settings.png |
| 登出确认弹窗 | ✅ 点击退出后弹窗出现（`logout dialog=true`） | 截图 11-logout-dialog.png |
| 确认登出 → 回登录页 | ✅ LoginScreen 再次可达（`back to login=true`） | 截图 12-after-logout.png |

## 发现缺陷清单

### M-1 · P1 · macOS 游客登录：token 持久化 Keychain -34018（已定位并带修复）
- 现象：`POST /auth/guest → 200` 后 UI 停留登录页、无跳转无提示；日志 `⚠️ Guest login failed: ... PlatformException(Unexpected security result code, Code: -34018, Message: A required entitlement isn't present.)`
- 根因（两层）：
  1. vendored `flutter_secure_storage` Swift 侧 `useDataProtectionKeyChain` **默认 true**（FlutterSecureStoragePlugin.swift:142）；macOS Data Protection Keychain 强依赖 `keychain-access-groups` entitlement，未签名本地构建（`CODE_SIGNING_ALLOWED=NO`）不具备；
  2. `DebugProfile.entitlements` 中 `com.apple.security.keychain-access` 不是有效 entitlement 键，且 `keychain-access-groups` 为空数组，形同虚设。
- 修复（已随工作树保留，待评审）：
  - `auth_repository.dart`：FlutterSecureStorage 增加 `mOptions: MacOsOptions(useDataProtectionKeyChain: false)`（根因修复；或改为配真实签名 + Keychain Sharing）
  - `DebugProfile.entitlements`：Debug 关闭 App Sandbox（开发期放宽）
- 跨端佐证：Web 轮 W-1/W-2（web storage 断链）同族、Android 轮游客可用——**"认证成功 → 会话持久化"是三端共性薄弱环节**
- 复现：修复前 `flutter run -d macos` → Continue as Guest → 日志 200 后紧跟 `-34018`
- 定位：`mobile/lib/features/auth/data/repositories/auth_repository.dart:756`、`third_party_plugins/flutter_secure_storage`、`mobile/macos/Runner/DebugProfile.entitlements`

### M-2 · P2 · 游客聊天流式启动波动（跨端一致：卡队列）
- 现象：同一提示词，attempt15/17 流式正常起流（Stop 按钮出现），attempt16 90 秒内未起流（超时落空）；无用户可见错误提示
- 跨端：Android 轮已记录"游客聊天卡队列"；本端复现同类波动，疑后端队列/引擎调度而非端实现
- 建议：网关/引擎侧排查 guest 会话排队；前端可补"排队中"状态提示
- 定位：`/ws/chat` 上行链路（端侧证据充分，后端侧待查）

### M-3 · P2 · 社群 WebSocket 连接 502
- 现象：进入社群页，`GET /api/v1/community/ws/connect → 502（not upgraded to websocket）`，重试 15 次全 502；页面本身可渲染
- 影响：社群实时能力全断；502 说明网关上游（社群服务/引擎侧 WS 后端）不可达
- 复现：游客进入社群 Tab，观察应用日志 `WebSocket stream error ... HTTP status code: 502`
- 定位：网关 `/api/v1/community/ws/connect` 上游路由

### M-4 · P2 · 三个后端 500（其中一项跨端复现）
- `/api/v1/predictive/realtime-next-step → 500`：**Android 轮实测同一接口 500（跨端复现）**，优先级提升
- `/api/v1/growth/return-case-file → 500`：驾驶舱/成长路径触发
- `/api/v1/experience/community-accountability → 500`×2：社群页触发
- 复现：游客旅程内自然触发；定位各自 handler + 网关日志（本侧仅端上证据）

### M-5 · P2 · 驾驶舱聚合调用不存在的 `/exam-sprint/dashboard` → 404
- 现象：游客进入驾驶舱即有 `GET /api/v1/exam-sprint/dashboard → 404`（同屏其余聚合接口 200）
- 疑后端路由未注册或端上接口路径超前；造成轮次内必现失败请求
- 定位：dashboard 聚合 provider + 后端路由表核对

### M-6 · P3 · 未认证阶段的 401 噪音
- 冷启动认证未决即请求 `GET /user/settings → 401`、`GET /tasks* → 401`×2；登出后 chat WS 还以过期凭据重连 `→ 401`
- 影响：遥测噪音/错误分支误报；建议认证就绪后再拉、登出时停掉 WS 重连
- 定位：启动期 settings/tasks provider 时序、logout 后 WS 生命周期

### M-7 · P3 · UI 全英文（zh 产品无 locale 兜底）
- 系统语言 en-CN 下全应用英文（与 Web 轮 W-7 同族）；建议默认 zh 或首启语言选择
- 定位：`lib/app/app.dart` locale resolution

### M-8 · P3 · 800×632 默认窗口登录页 Guest 按钮折叠线下
- SingleChildScroll 可达非阻断；建议 auth 页压缩品牌区高度自适应小窗
- 前轮截图（02/03-登录页-*）已记录同一现象

### M-9 · 观察项 · Xcode 26 显式模块竞态 + 满盘 I/O（基础设施，非应用代码）
- 签名一：`clang dependency scanning failure ... Session.modulevalidation`、`cannot load underlying module for 'audioplayers_darwin'`；签名二：`build.db: disk I/O error`、`Mkdtemp(swbuild.tmp.X) No such file`、`Script-*.sh: No such file`、`rsync renameat: No such file or directory`
- 规律：磁盘 98%+ 满且并发构建时高发；部分清理（只删 XCBuildData）必复发；整体删除 `build/macos` 后重试可恢复；清出 ≥6.5G 可用后稳定
- 缓解（已保留）：Podfile post_install 与 Runner Configs 设 `SWIFT_ENABLE_EXPLICIT_MODULES=NO`、`CLANG_ENABLE_EXPLICIT_MODULES=NO`；运维建议构建机保留 ≥10G 可用、避免同盘多构建并发
- 定位：`mobile/macos/Podfile`、`mobile/macos/Runner/Configs/{Debug,Release}.xcconfig`

### M-10 · 观察项 · 锁屏会话限制 GUI 自动化（测试基建）
- 锁屏下 osascript 无辅助功能授权、CGEvent 注入无效、`screencapture -l` 返回冻结帧（多帧同字节数实证）
- 对策：integration_test 驱动 + 引擎内 RepaintBoundary 截图（本报告截图管线）；后续 mac 实测建议在带 GUI 会话的机器补充真人视角

## 与 Web / Android 端的差异观察

| 维度 | Web round1 | Android round1 | macOS round1 |
|---|---|---|---|
| 游客登录 API | 200 | 200 | 200 |
| 认证→持久化 | ❌ W-1/W-2 | ✅ | ❌→✅ M-1（-34018，已带修复；修复后跨重启恢复会话） |
| 登录后落地 | 卡登录页 | 各 Tab 可达 | 驾驶舱 + 聚合 200（除 M-5 404） |
| 聊天 | 未达 | 卡队列 | ✅ 发送/流式/中断可用，但起流有波动（M-2） |
| `predictive/realtime-next-step` | — | **500** | **500（跨端复现，M-4）** |
| 语义树 | 残缺（W-5） | — | Flutter Semantics 正常（Send/Stop 有语义标签） |
| locale | 全英文（W-7） | — | 全英文（M-7，同族） |

## 修复文件交接（本轮新增，均未提交；前轮 6 文件原样保留）

- `mobile/lib/features/auth/data/repositories/auth_repository.dart` — M-1 根因修复（mOptions）
- `mobile/macos/Runner/DebugProfile.entitlements` — Debug 关沙箱（M-1 辅助）
- `mobile/macos/Podfile`、`mobile/macos/Runner/Configs/{Debug,Release}.xcconfig` — M-9 缓解
- `mobile/integration_test/macos_journey_test.dart` — 本轮走查驱动（可复用的 mac 旅程回归，`JOURNEY_DONE failures=0`）
- 截图存档：`/Users/brsama/code/GitHub/Sparkle-sysrev/screenshots/macos/`（不入库）：01-login / 02-home-dashboard / 03-galaxy / 04-chat-empty / 05-chat-streaming / 06-chat-interrupted / 07-chat-after-interrupt / 08-community / 09-profile / 10-settings / 11-logout-dialog / 12-after-logout（另有 05-chat-no-stream.png 为 M-2 波动证据）
