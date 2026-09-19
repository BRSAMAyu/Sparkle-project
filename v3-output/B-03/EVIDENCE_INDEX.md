# B-03 EVIDENCE INDEX —— 每次 run 的产物索引

> 目录：`v3-output/B-03/evidence/<run_id>/`
> 每个 run 目录含 `run_manifest.json`（SHA/device/time/build metadata）、`steps.json`、`screenshots/`、`api_log.jsonl`、`db_probes.jsonl`（如有）。
> 段落约定：UI lane = 真实界面操作；non-ui lane = API/WS 直驱（不冒充 UI 实测）；env-fix = 环境修复迭代的失败 run（亦是证据）。

## 前员遗留（2026-09-19 上午，同 worktree 4c963ef4）

| run_id | backend | 结果 | 摘要 |
|---|---|---|---|
| gj01_api_20260919_105012_c463 | api (non-ui) | FAIL | register 请求体格式错（首跑参数拼装 bug，随后修复） |
| gj01_api_20260919_105034_38ef | api (non-ui) | **PASS** | 注册→onboarding→dashboard/status 全通 + DB 断言 `users.registration_source='email'` 命中；user_id=ee00bc13…（DB 只读探针留存） |
| gj04_api_20260919_105051_ff8b | api (non-ui) | **PASS** | 「我卡住了」→ 澄清 → rescope 全通，含回复关键词断言 |
| gj04_api_20260919_105445_a8a7 | api (non-ui) | **PASS** | 同上复跑（稳定性验证） |
| gj08_api_20260919_105812_871d | api (non-ui) | FAIL | 记忆落库 240s 超时（`wait_memory_landed`）——候选产品级线索：纠错记忆异步落库慢/失败，转 REPORT |
| gj08_api_20260919_110447_7f0f | api (non-ui) | FAIL | 同上复跑确认（两连败，非偶发网络抖动） |
| gj01_web_20260919_111325_d253 | web (UI) | FAIL | `open_app_login` 超时：App 渲染中文界面（见 `screenshots/01-FAIL_open_app_login.png`），journey 定义为英文文本。根因=Chrome `--lang` 不影响 `navigator.languages`；已修（`--accept-lang=en-US`），待重跑 |

## 本轮（B-03 基线续作，2026-09-19 下午）

| run_id | backend | 结果 | 摘要 |
|---|---|---|---|
| gj01_macos_20260919_124249_f491 | macos | FAIL (env-fix) | harness 自身缺陷暴露：MacosDriver.start() 取 `.stdout` 失效（CompletedProcess 误用）。验证了「start 失败→落盘 FAIL manifest→退出码 1」机制生效 |
| gj01_macos_20260919_124408_89ab | macos | FAIL (env-fix) | macOS 构建失败：`macos/Flutter/Flutter-Debug.xcconfig` 等 gitignored shim 缺失（worktree 全新检出）。已按 wt6 同构补建 shim 后重跑 |
| gj01_macos_20260919_124705_a06c | macos | FAIL (env-fix) | Flutter SDK 缓存地雷：`dartaotruntime` 是指向 wt7/.toolshim（已被清理）的断链符号链接——某前员曾改共享 SDK 未复原。已从 `.orig.macho` 真身恢复（Dart 3.11.1 arm64 验证通过） |
| gj01_macos_20260919_124955_6133 | macos | FAIL (env-fix) | 同上断链余波（构建在恢复前启动）。恢复后消除 |
| gj01_macos_20260919_125111_1201 | macos | PASS*（12 截图全步通过） | journey 全步 PASS 但 flutter test 报 FAIL：App main() 安装生产 `ErrorWidget.builder` 触发 flutter_test 收尾卫生检查。已修（测试内捕获并在 finally 还原，不削弱任何 journey 断言） |
| gj01_macos_20260919_125619_3774 | macos | FAIL (env-flake) | **遮挡敏感性**：macOS App 窗口被宿主桌面判为 backgrounded 后帧流停摆，测试僵死至被人工杀掉（flutter test 内部 15min 超时会兜底非零退出）。重跑即恢复；已记录为已知环境约束（要求活跃控制台） |
| gj01_macos_20260919_130919_9507 | macos | FAIL（诚实判定生效） | journey 12 步全过（11 截图）但 journey 级 DB 断言 `users_row_email_source` FAIL——该断言属 email 注册通道，macOS 是访客 journey 不落 email 注册行。已给 db_assert 增加 `backends` 作用域。**另发现**：本 run 因上一次僵死 run 残留 guest 登录态而静默跳过登录页（降级通过被 DB 断言意外拦截）——已修 dart 测试：fresh-user journey 未见登录页即记 failure |
| **gj01_macos_20260919_131219_432f** | **macos** | **PASS（最终证据）** | 完整访客 journey：登录页→以访客身份继续→Cockpit 首页→星图→对话（发送/AI 流式/中断）→社群→我的→设置→登出→回登录页。12 张引擎帧截图 + 全量运行日志；耗时 2m15s；base_sha=4c963ef4；manifest 字段齐全；退出码 0 |

### macOS 通道附注
- 截图为引擎 RepaintBoundary 直取帧（`02-home-dashboard` 等可看到真实数据与中文 UI；`05-chat-streaming` 可见停止按钮=流式中）。
- 环境修复产出的 gitignored 文件（worktree 内，随 worktree 回收）：`mobile/macos/Flutter/Flutter-{Debug,Release}.xcconfig`（shim，两行 include）、`mobile/macos/Flutter/ephemeral/`、`mobile/macos/Pods/`。共享 SDK `/opt/homebrew/share/flutter/bin/cache/dart-sdk/bin/dartaotruntime` 已从 `.orig.macho` 恢复为真身（舰队级隐患，详见 REPORT §4）。

## 续作第二轮（2026-09-19 下午，断点接续，同 worktree 4c963ef4）

| run_id | backend | 结果 | 摘要 |
|---|---|---|---|
| gj01_web_20260919_135945_c7e0 | web (UI) | FAIL (env-fix) | 前员中断前最后一跑：locale 修复生效（注册页正确渲染），但 `note_account` 步炸 `WebDriver has no attribute 'state'`。根因=BaseDriver 未初始化 `self.state`；前员已于 14:00:05 把初始化补进 base.py（修复落盘未验证）。本轮复现通过 |
| gj01_web_20260919_111312_605b | web (UI) | FAIL (env-fix，无 manifest) | 前员 locale 排查期的失败 run（同 111325） |
| gj01_web_20260919_132158_2a21 | web (UI) | FAIL (env-fix) | 前员首轮中文 journey：`open_app_login` 等 'Continue as Guest' 120s 超时——journey 文本与 App 实际 locale 不匹配的修正迭代 |
| gj01s_web_20260919_135925_49d2 | web (UI) | PASS | 前员的 GJ01S 最小壳先导跑（4 步过）；因 GJ01 全程缺陷尚未定界，继续完善后由 143734 取代为验收证据 |
| gj01_web_20260919_140012_6da6 | web (UI) | FAIL (env-fix) | base.py 修复后首轮：连过注册表单，`submit_register` FAIL（'学习目标' 超时）——Web 注册缺陷首次以完整步骤暴露 |
| **gj01_web_20260919_141821_84dc** | web (UI) | FAIL（诚实判定生效） | `note_account` 修复后连过 9 步，`submit_register` FAIL：注册 POST → 网关 200，但 UI 停留注册页不进 onboarding。**产品级缺陷定界，见下方专节** |
| **gj01s_web_20260919_143734_7410** | **web (UI)** | **PASS（验收证据）** | GJ01 最小壳 4 步全过：App 启动 → 登录页语义树可达 → 注册表单可输入 → 返回登录页；退出码 0 |

### Web 端注册缺陷定界专节（gj01_web_141821 的 5 连复现 + 探针链）

现象：真实 UI 注册提交 → 网关 200（账号**实际已创建**）→ App 播错误音效（`error.ogg`，同秒加载）→ SnackBar「网络连接不稳定，这次请求没有完整送达。」→ 停留注册页，永不进入 onboarding。确认密码框在失败后被清空（其余字段保留）。

定界证据（`evidence/web_register_defect_probes_20260919/`）：

| 探针 | 结论 |
|---|---|
| proxy trace（serve_web.py SPARKLE_PROXY_TRACE） | 网关返回完整合法 2470B JSON（含 token+user），代理已完整写入 socket |
| 页面内 `fetch` 复刻注册请求 | 200 + 全量 body——代理↔浏览器传输健康 |
| 页面内 `XHR` 复刻（dio web 通道） | 收到真实响应（400=复用已注册用户名的业务响应）——XHR 通道健康 |
| Runtime.exceptionThrown + 全 console 捕获 | 无 JS 异常——异常被 Dart 侧 catch 吞掉（release 构建不打印） |
| 语义树逐秒轮询（T+1..5s） | SnackBar 仅存活约 4s；除误导性网络文案外无其他错误信息 |
| API 直连（curl + api lane） | 同 endpoint 同 body 直连 8080 恒定成功 |

根因层位：**Flutter Web 客户端 Dart 侧**（ dio 适配/响应后处理链），非网关、非代理、非传输层。错误映射链：`AppFailureMapper.fromDio` 将 `DioExceptionType.unknown`（非离线特征）归为 `NetworkFailure` → 用户看到误导性「网络不稳定」。精确异常点需 debug 构建或 Dio 日志级联才能落出，建议单开诊断卡（候选：dio web adapter 对该响应的处理、`saveTokens`→web SharedPreferences 路径、`UserModel.fromJson` 响应解析）。

用户实际影响（按严重度）：注册在服务端成功但用户被告知网络故障 → 用户重试必撞「用户名已存在」，且全程无「账号其实已建好，请登录」的引导 → **注册转化链路在 Web 端断裂**。次级发现：密码确认框不匹配时 POST 照发（提交后字段清空行为），客户端表单校验与后端约束不对齐。

## Android 通道（2026-09-19 下午接续）

| run_id | backend | 结果 | 摘要 |
|---|---|---|---|
| gj01_android_20260919_145914_0721 | android | FAIL (env-fix) | APK 相对路径未被驱动解析（fail-fast，未启模拟器即非零退出）——驱动应报绝对路径要求，本轮改传绝对路径 |
| gj01_android_20260919_150134_17f4 | android | FAIL (env-fix) | AVD boot + install PASS 后 launch 失败：驱动硬编码包名 `com.example.sparkle` 与真实 applicationId `com.sparkle.app` 不符。**修复**：驱动改为安装后用 `aapt2 dump badging` 从 APK 本体解析 package/launchable-activity，不再猜 |
| gj01_android_20260919_150517_ef3f | android | PASS*（前台判定通过） | 4 步中 3 步通过；**截图目视发现 App 实为启动即崩错误屏**（IsarError，见 REPORT §4.4）——「前台判定」必要但不充分，暴露 harness 盲区 |
| gj01_android_20260919_151006_3781 | android | PASS* | runner 修复回归验证：manifest.device 记录实况 serial=emulator-5554 |
| gj01_android_20260919_151736_b86a | android | FAIL (env-fix) | Isar 修复后重跑：崩溃断言首次引入，但 logcat 落盘用错 EvidenceCollector API（save_text）——修复驱动代码后重跑 |
| gj01_android_20260919_152144_8073 | android | FAIL (env-fix) | logcat 出现非 UTF-8 字节致严格解码崩——**修复**：adb 输出改 `errors="replace"` 宽松解码 |
| gj01_android_20260919_152540_bd06 | android | PASS* | 修复后重跑：install/launch/logcat 全过 + 新增 `no_startup_fatal_errors` 断言（logcat 无 IsarError/FATAL）通过；截图为黑屏（debug 首帧 8s 未渲染完）→ **修复**：launch 等待改为轮询窗口焦点（mCurrentFocus 含本包名）再截图 |
| **gj01_android_20260919_153033_72b3** | **android** | **PASS（最终证据）** | 4/4 全过（含崩溃断言）；截图为**真实产品 UI**：访客会话「访客体验cde3」、Aurora 轻量感知、理解度 75% 卡片、目标/任务指挥台、五 Tab 全渲染；logcat 可见 `/auth/guest, status: ok` 且网关回包 accepted——Isar 修复经真实 UI 验证成立 |

### Android 通道附注（修复链）
- 产品修复：`mobile/third_party_plugins/isar_flutter_libs/android/src/main/jniLibs/{arm64-v8a,armeabi-v7a,x86,x86_64}/libisar.so`（自上游 isar_flutter_libs 3.1.0+1 官方 tarball 恢复，共 ~4.2MB；macOS dylib 与 iOS xcframework 此前已入库，唯 Android .so 被剥）。修复经 `153033_72b3` 截图+logcat 双通道验证。
- harness 演进：badging 解析包名（150134）、`assert_logcat_absent` 启动崩溃断言（journey 步骤级）、窗口焦点就绪轮询（152540 黑屏教训）、adb 输出宽松解码（logcat 非 UTF-8 字节）、manifest.device 记实况 serial（151006）。
- 环境修复（gitignored/本机，不入 patch）：JDK 21（Temurin 25 被 Kotlin 拒绝）、`GRADLE_USER_HOME=/tmp/b03_gradle_home`（外置卷 ~/.gradle 符号链接上守护进程建目录反复失败）、gradle 堆临时降 2g（构建后已还原）。
