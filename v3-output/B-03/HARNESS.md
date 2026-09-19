# B-03 跨端 Journey Simulator Harness —— 使用手册（基线 v1）

> 任务卡 B-03「跨端 Journey Simulator Harness 基线」交付。
> Harness 代码：`scripts/devtools/journey_harness/`（与主仓同构路径，合入后全仓可用）。
> 每次 run 的产物索引见同目录 `EVIDENCE_INDEX.md`；完成度与取舍见 `REPORT.md`。

## 0. 设计红线（验收条款的落实方式）

1. **Simulator 不得绕过 UI**（v3/05_metrics_eval/USER_SIMULATION.md Ban 条款）：
   - `web` backend：真实 Chrome（headless）+ CDP。元素定位只读**语义树**（`flt-semantics`，即读屏软件所见），点击走 `Input.dispatchMouseEvent` 真实鼠标事件，输入走 `Input.insertText` 真实输入通道。**不注入 Dart、不调用内部 API 改状态**；唯一允许的 URL 直达是 journey 显式声明的入口（等价用户手输 URL）。
   - `macos` backend：`flutter test integration_test/macos_journey_test.dart -d macos`（finder 级真实点击/输入，真实后端、真实窗口、引擎帧截图）。
   - `android` backend：boot AVD → `adb install` → `am start` 真实启动；**基线不做 UI 步进**（诚实声明，见 §4）。
   - `api` backend 是唯一非 UI 通道，仅作为后端连通性冒烟；其 run 在 manifest.summary 标注 `non-ui lane`，**不得冒充 UI 实测**。
2. **失败必须非零退出**：任一步骤 FAIL、DB 断言 FAIL、环境不可用（找不到 Chrome/AVD/Flutter 工具链）→ 进程退出码 1。`driver.start()` 失败同样写入 FAIL step 并落盘 run_manifest——**"没找到模拟器"永远是 FAIL，不是 PASS**。
3. **每次 run 留证**：run 目录含 `run_manifest.json`（build SHA/device/time/build metadata）、`steps.json`（逐步 PASS/FAIL）、`screenshots/*.png`、`api_log.jsonl`、`db_probes.jsonl`（只读 SELECT）。

## 1. 统一入口

```bash
cd scripts/devtools/journey_harness

python3 run_journey.py --list                     # 列出 journeys 与各 backend 步骤数
python3 run_journey.py --journey GJ01 --backend macos
python3 run_journey.py --journey GJ01 --backend web  --app-url http://127.0.0.1:8437/
python3 run_journey.py --journey GJ01 --backend android --apk <apk路径>
python3 run_journey.py --journey GJ01 --backend api      # 冒烟（non-ui lane）
echo $?                                           # 0=PASS，1=FAIL（含环境不可用）
```

一键脚本（等价封装，推荐 CI/复跑用）：

| 平台 | 脚本 | 说明 |
|---|---|---|
| macOS | `scripts/devtools/journey_harness/run_macos_journey.sh` | 无前置，直接跑 |
| Web | `scripts/devtools/journey_harness/run_web_gj01.sh [port]` | 前置：`mobile/build/web` 已构建（§3.1） |
| Android | `scripts/devtools/journey_harness/run_android_shell.sh [apk路径]` | 无 APK 时自动 `flutter build apk --debug` |

## 2. 产物路径约定（每次 run 一个目录）

```
v3-output/B-03/evidence/<journey>_<backend>_<YYYYMMDD>_<HHMMSS>_<4hex>/
├── run_manifest.json     # run 唯一事实源（验收字段见下）
├── steps.json            # 逐步 PASS/FAIL + detail + duration_ms + artifacts
├── journey_definition.json  # 本次 run 用的 journey 定义快照（可复现）
├── screenshots/          # 每步 UI 现场（web/macos/android）；失败步自动补拍 FAIL_*
├── api_log.jsonl         # HTTP/WS 请求-响应留存（api=直驱；web=CDP 网络事件）
├── db_probes.jsonl       # 只读 DB 探针（docker exec psql，SELECT-only，主仓 DB 只读纪律）
└── macos_journey_run.log / <name>.log   # 平台运行日志引用
```

`run_manifest.json` 必含字段（对应任务卡验收）：

- `base_sha` / `final_sha`：worktree HEAD；dirty 时 final_sha 带 `-dirty(N files, not committed by design)` 后缀（本任务禁 commit，dirty 是常态且被显式声明）
- `device`：macOS=`flutter test -d macos`；Web=Chrome 版本/viewport/headless；Android=`AVD:<名> serial=<serial>`
- `started_at` / `finished_at`：UTC ISO 时间
- `app_build`：pubspec name/version；web 附 `web_built_at`、`served_url`；android 附 apk 路径；macos 附 test_file
- `gateway`、`steps[]`、`ok`、`summary`

## 3. 各平台「GJ01 最小壳」启动手册

### 3.1 macOS（复用既有 macos_journey_test.dart，访客 journey）

前置：Flutter 工具链 + macOS 桌面目标（`flutter devices` 可见 `macOS (desktop)`）。

```bash
cd <repo根>
bash scripts/devtools/journey_harness/run_macos_journey.sh
```

内容：登录页 → 以访客身份继续 → Cockpit 首页 → 星图 → 对话（发送/流式/中断）→ 社群 → 我的 → 设置 → 登出 → 回登录页。文本定位 zh/en 双语自适应；截图经引擎 RepaintBoundary 直取（锁屏也能拍），默认落到本次 run 的 `screenshots/`（由 `--dart-define=JOURNEY_SHOT_DEST` 注入，测试文件内已支持）。

判据：`flutter test` 退出码 0 **且** 输出含 `JOURNEY_DONE failures=0`；否则非零退出。

### 3.2 Web（Chrome + CDP 真实 UI journey，GJ01 全 18 步）

前置（一次性构建，注意内存纪律）：

```bash
cd <repo根>/mobile
flutter build web --release --dart-define=API_BASE_URL=http://localhost:8080
# 构建期间不要并行任何 Gradle/模拟器/其他 flutter 任务（HEAVY 串行纪律）
```

运行（脚本起静态服务器 → 跑 journey）：

```bash
cd <repo根>
bash scripts/devtools/journey_harness/run_web_gj01.sh 8437
```

内容：注册（双密码+条款勾选）→ Persona Guide onboarding 5 步 → 建模对话 → Skip 进五 Tab 壳 → 回 Cockpit 首页。全部经语义树定位 + 真实鼠标/键盘事件。

**基线现状（2026-09-19）**：
- GJ01S 最小壳（`--journey GJ01S --backend web`）PASS：App 启动 → 登录页语义树可达 → 注册表单可输入 → 返回登录页。
- GJ01 全 18 步在 `submit_register` 诚实 FAIL：**产品缺陷**——注册在网关 200 成功后 App 停留注册页，SnackBar 误报「网络连接不稳定」。已五连复现并定界到 Flutter Web 客户端 Dart 侧（网关/代理/传输层均排除），证据链见 `EVIDENCE_INDEX.md` 专节。该缺陷修复前，Web 端 GJ01 验收以 GJ01S 最小壳 + 缺陷取证为准。

已知坑（已内建处理）：
- **locale**：driver 以 `--accept-lang=en-US` 启动 Chrome 固定 App 语言（仅 `--lang` 不影响 `navigator.languages`，曾致 zh 界面对不上 en 步骤定义）。后续 journey 文本统一按 zh 书写（App 跟随宿主 locale 的行为已由步骤文本对齐）。
- **SPA 路由刷新**：`serve_web.py` 对未知路径回退 index.html。
- headless CanvasKit 需 `--enable-unsafe-swiftshader`（driver 已带）。

### 3.3 Android（最小壳：boot → install → launch → 取证）

前置：Android SDK + AVD（默认 `Medium_Phone_API_36.1`，可用 `AVD_NAME` 环境变量覆盖）；APK（无则脚本自动构建，**传绝对路径**——驱动不解析相对路径）：

```bash
cd <repo根>/mobile
flutter build apk --debug --dart-define=API_BASE_URL=http://10.0.2.2:8080
```

**本机构建环境前提（2026-09-19 实测踩坑记录）**：
1. **JDK 版本**：本机默认 Temurin JDK 25 会被 Kotlin 编译器拒绝（`JavaVersion.parse: IllegalArgumentException: 25.0.2`）。需 JDK 17/21：`JAVA_HOME=<jdk21路径> flutter build apk ...`。
2. **gradle 用户主目录**：`~/.gradle` 是指向外置卷（`/Volumes/移动E/MacCache/gradle`）的符号链接，该卷的 kotlin-dsl 脚本插桩目录创建在守护进程下反复失败（shell 同路径 mkdir 正常，疑外置卷 FS/TCC 行为）。可靠规避：`GRADLE_USER_HOME=/tmp/b03_gradle_home`（首次全新下载依赖约 1-2GB）。
3. **堆纪律**：`mobile/android/gradle.properties` 默认 `-Xmx8G`，16GB 机器上构建前临时降为 `-Xmx2g -XX:MaxMetaspaceSize=1g`（HEAVY 纪律），构建后还原。

运行：

```bash
cd <repo根>
bash scripts/devtools/journey_harness/run_android_shell.sh /绝对路径/app-debug.apk
```

**基线现状（2026-09-19）**：4 步全过（install→launch→logcat→`no_startup_fatal_errors`），最终证据 `gj01_android_20260919_153033_72b3`：
- 包名/launcher activity 由 `aapt2 dump badging` 从 APK 本体解析（`com.sparkle.app`），不猜；
- 启动判定三层：进程前台（dumpsys activities）+ **窗口焦点**（mCurrentFocus，防黑屏假阳性）+ **logcat 启动崩溃特征断言**（journey 声明 pattern，防「错误屏也算前台」假阳性——本轮实测真的抓到过 IsarError 启动崩溃，见 REPORT §4.4）；
- UI 步进仍按下方 §3.4 声明 unsupported。

任一失败 → 非零退出。

### 3.4 明确 unsupported 的部分（诚实声明）

| 能力 | 平台 | 状态 | 原因 |
|---|---|---|---|
| GJ01 邮箱注册+onboarding 全 UI 步进 | macOS | 本轮未跑全量 | 复用的 `macos_journey_test.dart` 是访客 journey（登录页→首页→聊天→登出），不含邮箱注册/onboarding 步；见 §5 TODO |
| GJ01 UI 步进（find/tap/type） | Android | `ui_steps: unsupported` | Flutter 语义树在 Android 按需构建，需无障碍服务激活；`adb uiautomator` 看不到 Flutter 节点。基线只验「可启动+前台+取证」，不做坐标盲点冒充 |

平台完全不支持时（如目标机器无 macOS 桌面目标），driver 在 `start()` 阶段即 StepFailure → 退出码 1，并在错误信息中说明原因——**不支持 ≠ 静默 PASS**。

## 4. 统一化现状（任务卡 work#2 对照）

| 项 | 现状 |
|---|---|
| persona reset | journey 内注册全新 `%RUN%` 唯一账号实现隔离；macos 测试内 `SharedPreferences.clear()` 保证从登录页起步。统一 persona library 注入留 TODO（v3/05_metrics_eval/persona_library.json 已存在可接） |
| trace capture | web=CDP Network 事件→api_log.jsonl；api=直驱留存；android=logcat 快照；macos=flutter test 全量日志 |
| 截图路径 | 统一落 `v3-output/B-03/evidence/<run_id>/screenshots/`，前缀序号，失败步自动补拍 |
| 网络切换 | 未内建（web 可经 CDP `Network.emulateNetworkConditions`，android 可 `adb shell cmd connectivity airplane-mode enable`，接口已预留 driver 扩展位）。基线未用，见 TODO |
| test clock | 未内建（受控时钟推进属 USER_SIMULATION longitudinal 阶段） |
| build metadata | run_manifest.json：SHA/device/time/build（§2） |

## 5. 已知 TODO（下轮演进）

1. Android UI 步进：接 Flutter Android 无障碍（`flutter build apk` 默认关闭 semantics；可用 `FlutterDriver`/integration_test on-device 或开启 TalkBack 后 uiautomator）跑真实 GJ01。
2. macOS 全量注册 journey：把 web 版 18 步移植为 dart finder 版或接入统一语义层。
3. 网络切换/飞行模式/慢网作为 journey 可声明步骤（`args.network: "offline"`）。
4. persona library 与 test clock 接入 loader。
5. GJ04/GJ08 扩 web/android backend（api lane 已通，见 EVIDENCE_INDEX）。

## 6. HEAVY 内存纪律（跑 harness 的 agent 必读）

一次只跑一个平台，顺序 macOS → Web → Android；每阶段前查 `sysctl vm.swapusage`（swap 空闲 <1.2G 转文档阶段；<800M 立即杀当前平台进程）；Gradle 一律 `-Xmx2g`；flutter 命令串行；浏览器单实例；阶段间杀净上一平台进程；收工杀模拟器/gradle daemon/浏览器/serve，删 `mobile/build`、`.dart_tool`（AGENTS.md 清单）。
