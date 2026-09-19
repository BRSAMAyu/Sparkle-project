# B-03 跨端 Journey Simulator Harness 基线 —— 实测报告

> 任务卡 B-03（stream BASELINE，gate V3-0，risk medium，resource HEAVY）
> worktree：/Users/brsama/code/GitHub/Sparkle-sysrev/wt7 @ 4c963ef4（禁 commit，交付 changes.patch）
> 日期：2026-09-19 ｜ 执行：Sparkle FieldTest（真机实测员）

## 0. 一句话结论

三平台 harness 均可重复启动并如实留证：macOS GJ01 访客 journey **PASS**（12 截图+日志+退出码 0）；Web GJ01S 最小壳 **PASS**，GJ01 全程被一个**产品级注册缺陷**诚实阻断（后端 200 建号成功、App 误报网络错误卡死，已五连复现并定界到 Flutter Web Dart 侧）；Android 最小壳 **PASS（4/4，含崩溃断言）**——期间揪出并修复了「App 启动即崩（Isar 原生库缺失）」的高危产品缺陷，经真实 UI 验证（截图+logcat 双通道）。失败路径全部返回非零退出码，simulator 未绕过 UI。

## 1. 交付物

| 交付物 | 路径 | 状态 |
|---|---|---|
| Harness 使用手册 | `v3-output/B-03/HARNESS.md` | 已交付（含三平台启动手册+本机环境坑） |
| Run 产物索引 | `v3-output/B-03/EVIDENCE_INDEX.md` | 已收口（含 Web 注册缺陷定界专节） |
| Harness 脚本（演进） | `scripts/devtools/journey_harness/` | 已修复+扩展 |
| 变更补丁 | `v3-output/B-03/changes.patch` | 收工生成 |
| 本报告 | `v3-output/B-03/REPORT.md` | 本文件 |

## 2. 三平台状态（GJ01 最小壳）

| 平台 | 状态 | 证据 run | 说明 |
|---|---|---|---|
| macOS | **PASS** | `gj01_macos_20260919_131219_432f` | 完整访客 journey（登录页→首页→星图→对话流式/中断→社群→我的→设置→登出），12 张引擎帧截图，耗时 2m15s，退出码 0 |
| Web | **PASS（最小壳）/ FAIL（GJ01 全程，产品缺陷）** | `gj01s_web_20260919_143734_7410` / `gj01_web_20260919_141821_84dc` | 最小壳 4 步 PASS；GJ01 卡 `submit_register`——网关 200 建号成功但 App 停留注册页误报网络错误，5 连复现，见 §4 |
| Android | **PASS（含产品修复）** | `gj01_android_20260919_153033_72b3` | 4/4 步（install→launch→logcat→启动崩溃断言）；截图为真实产品 UI（访客驾驶舱五 Tab 全渲染）。首轮实测发现 App 启动即崩（IsarError），已修复并经 UI 验证，见 §4.4 |

## 3. Harness 修复清单（前员骨架上的演进）

1. `MacosDriver.start()`：`CompletedProcess` 误用导致任何 macOS run 必挂 —— 修复（取 `.stdout`）。
2. GJ01 定义缺 `macos`/`android` backend 步骤（`steps_for()` KeyError）—— 补齐。
3. `macos_journey_test.dart` 截图路径硬编码到 worktree 外且忽略 `JOURNEY_SHOT_DEST` —— 改为 dart-define 注入 + worktree 内默认值（空间纪律修复）。
4. Web locale 不确定性：Chrome `--lang` 不影响 `navigator.languages`，App 跟随宿主语言渲染 —— driver 增加 `--accept-lang=en-US`；journey 步骤文本与实际渲染对齐。
5. `runner.py`：`driver.start()` 失败原先抛裸异常不留 run 证据 —— 现在 FAIL step + manifest 落盘 + 退出码 1；db_assert 异常同样落盘。
6. `AndroidDriver`：默认包名与真实 applicationId 不符；activity 类名不符 —— 改为 `cmd package resolve-activity` 动态解析；截图改 raw bytes 单次捕获并校验。
7. `BaseDriver` 增加 `self.state` 运行期上下文（`note_account` 等步骤跨步共享账号信息，供 journey 级 DB 断言渲染）——前员中断前 14:00:05 落盘的修复，本轮验证生效（`135945` FAIL → `141821` 连过 9 步）。
8. macOS 构建环境修复（非代码，gitignored shim）：`mobile/macos/Flutter/Flutter-{Debug,Release}.xcconfig` 按 wt6 同构补建；flutter SDK 缓存 `dartaotruntime` 缺失经恢复修复。
9. journey 级 `db_assert` 增加 `backends` 作用域：访客 journey 不应执行 email 注册通道的 DB 断言（`130919` 的误杀→修复）。
10. dart 测试 fresh-user 防降级：未见登录页即记 failure（`130919` 发现的残留登录态静默跳步问题）。
11. `AndroidDriver` 包名/入口 activity 改为安装后 `aapt2 dump badging` 从 APK 本体解析（`150134` 暴露硬编码包名错）。
12. `AndroidDriver` 新增 `assert_logcat_absent` 步骤（启动崩溃诚实判定，防「错误屏也算前台」假阳性——`150517` 实测抓到 IsarError 崩溃）；launch 等待改轮询窗口焦点（`152540` 黑屏教训）；adb 输出宽松解码（logcat 非 UTF-8 字节）。
13. `runner` manifest.device 在 start 后补写实况 serial（`151006` 修复并回归验证）。

## 4. 产品级线索（非 harness 缺陷）

### 4.1 【Web·高】邮箱注册「静默假失败」：后端 200 建号成功，App 误报网络错误并卡死

- **用户场景**：新用户在 Web 端注册。填表→勾选协议→点注册。
- **观察**：注册请求 POST `/api/v1/auth/register` → 网关 **200**（账号真实入库，proxy trace 留存完整响应体）；App 同秒播错误音效并弹 SnackBar **「网络连接不稳定，这次请求没有完整送达。」**，停留注册页，永不进入 onboarding；表单确认密码框被清空。
- **定界**（5 连复现 + 同会话探针对照，证据 `evidence/web_register_defect_probes_20260919/`）：
  - 网关侧：proxy trace 显示完整合法 JSON 响应（token+user）已写入 socket；
  - 传输侧：同浏览器页面内 `fetch` 复刻同请求 → 200 全量 body；`XHR`（dio web 同通道）→ 正常收到业务响应——传输层完全健康；
  - 客户端侧：`Runtime.exceptionThrown` 无 JS 异常 → 异常被 Dart catch 吞掉；错误映射链 `AppFailureMapper.fromDio` 将 `DioExceptionType.unknown`（非离线特征）归为 `NetworkFailure` → 误导文案；
  - 后端侧：API lane 直连同 endpoint 恒定成功。
  - **层位锁定：Flutter Web 客户端 Dart 侧**（dio web 适配器/响应处理/saveTokens web 路径三者之一），精确异常点需 debug 构建落出。
- **用户影响**：注册转化链路在 Web 端断裂——用户被告知网络故障，重试必撞「用户名已存在」，且全程无「账号其实已建好，请登录」引导。次级发现：确认密码不匹配/为空时 POST 照发（提交后该字段被清空），客户端校验与后端约束不对齐。
- **关联历史**：web-round1 W-1/W-2（登录 200 后会话断裂）同属「auth 成功响应在 web 客户端处理失败」家族；本次为 register 通道的回归/残留面。
- **建议**：单开诊断卡，用 `flutter run -d chrome --profile`（非 release）或 dart-snapshot 调试落出异常栈；优先复查 `TokenResponse.fromJson`/`saveTokens`/`UserModel.fromJson` 对 register 响应的处理在 web release 下的行为差异。

### 4.2 【AI·中】GJ08 纠错记忆落库超时（两连败）

- API lane 下纠正信息回复正常，但「第1-6章记忆」240s 内未落库（`gj08_api_105812`/`110447`，`db_probes.jsonl` 留存探针 SQL）。候选根因方向：记忆异步管道（Celery/证据融合）慢或失败。建议单开诊断卡。

### 4.3 【环境·舰队级】Android 构建工具链三连坑（本机）

1. 默认 Temurin **JDK 25** 被 Kotlin 编译器拒绝（`JavaVersion.parse` 不认识 25）→ 需 JDK 17/21。
2. `~/.gradle` 是指向外置卷 `/Volumes/移动E/MacCache/gradle` 的符号链接，该卷上 kotlin-dsl 脚本插桩目录创建在 gradle 守护进程下**稳定失败**（同路径 shell mkdir 正常，疑外置卷 FS/TCC 对 JVM 进程的行为）→ `GRADLE_USER_HOME` 指到本机盘规避。
3. `mobile/android/gradle.properties` 默认 `-Xmx8G -XX:MaxMetaspaceSize=4G`，在 16GB 物理内存整机上属事故级配置（2026-09-19 内存事故同配方），建议入库调低或按机器内存自适应。

### 4.4 【Android·高→已修复】App 启动即崩：vendored isar_flutter_libs 丢失 Android 原生库

- **用户场景**：真实用户在 Android 设备上打开 Sparkle。
- **观察**（run `gj01_android_20260919_150517_ef3f` 截图 + logcat）：App 启动即渲染错误屏 `IsarError: Could not initialize IsarCore library for processor architecture "android_arm64" ... dlopen failed: library "libisar.so" not found`，栈自 `main.dart:80 → LocalDatabase.init → Isar.open`——**首屏即死，产品完全不可用**。且 harness 首版「进程前台判定」给出 PASS：崩溃错误屏也算前台，假阳性被截图目视揪出。
- **根因**（已实锤）：`.gitignore:11` 的全局 `*.so` 规则在 vendoring 时**静默吞掉**了 `android/src/main/jniLibs/` 下四个 ABI 的 `libisar.so`（同包内 macOS `libisar.dylib` 与 iOS `libisar.a` 不匹配该规则故入库）——上游 pub 包 3.1.0+1 本身自带这些 .so。`main.dart` 无条件 `LocalDatabase().init()`，web 有 stub、macOS 有 dylib，Android 无兜底 → 必崩。
- **修复**：自上游 isar_flutter_libs 3.1.0+1 官方 tarball 恢复 `jniLibs/{arm64-v8a,armeabi-v7a,x86,x86_64}/libisar.so`（共 ~4.2MB）；`.gitignore` 增加定点白名单 `!mobile/third_party_plugins/isar_flutter_libs/android/src/main/jniLibs/**/*.so` 防复发。
- **验证**（run `gj01_android_20260919_153033_72b3`，双通道）：截图显示真实产品 UI（访客驾驶舱、Aurora AI 面板、理解度卡、目标/任务卡、五 Tab 全渲染）；logcat 无 `IsarError/FATAL`，且可见 `/auth/guest, status: ok`、网关回包 `accepted: true`（启动→访客登录→网络回环全通）。
- **防回归**：harness 新增 journey 步骤 `assert_logcat_absent`（可声明 pattern，默认盯 `FATAL ERROR DURING STARTUP`/`IsarError`），已入 GJ01 android backend——「错误屏也算前台」的假阳性从机制上堵死。
- **防复发**：harness 新增 journey 步骤 `assert_logcat_absent`（可声明 pattern，默认盯 `FATAL ERROR DURING STARTUP`/`IsarError`），已入 GJ01 android backend——「错误屏也算前台」的假阳性从机制上堵死；`.gitignore` 白名单已随补丁交付。

## 5. 阻塞与取舍

- **Web GJ01 全 18 步**被产品缺陷 §4.1 阻断（注册后不跳转）：验收以 GJ01S 最小壳 PASS + 缺陷五连复现取证为准。修复需 debug 构建落异常栈，超出本轮 harness 任务边界，建议单开诊断卡。
- **Android UI 步进**（find/tap/type）维持 unsupported 声明（Flutter 语义树需无障碍服务激活）；最小壳已含崩溃断言兜住「启动即死」类假阳性。
- GJ04/GJ08 仅 API lane（前员完成）；web/android lane 需上述缺陷先修。
- macOS journey 为访客切片，不含邮箱注册步（GJ01S 描述与 §3.4 已诚实声明）。

## 6. 内存与清理（HEAVY 纪律执行记录）

- 阶段顺序 macOS（前员）→ Web → Android 严格串行；每阶段前查 swap/load：本轮 Web 期 swap free 1.67G/load 4.9，Android 构建期 swap free 1.73G/load 4.8，**模拟器启动等待门**曾因构建后 swap free 1186M <1.2G 主动推迟（杀 gradle 守护进程后恢复至 1339M 才放行）；load 峰值 12.19（1min 瞬时，未持续，5min 均 9.8 未触发熔断）。
- Gradle 堆按纪律临时 `-Xmx2g`，构建后 `git checkout` 还原（changes.patch 不含 gradle.properties）。
- 收工清单：删 `mobile/build`、`mobile/.dart_tool`；杀 gradle daemon/adb/模拟器（driver finish 已自动 emu kill，收工再验）；/tmp 自清（JDK 21、b03_gradle_home ~2.4G、探针目录与脚本——探针证据已先归档 `evidence/web_register_defect_probes_20260919/`）。
- 模拟器收工确认：`ps` 无 qemu/emulator 进程。
