# B-03 跨端 Journey Simulator Harness —— 使用手册（基线 v2）

> 任务卡 B-03「跨端 Journey Simulator Harness 基线」交付。
> Harness 代码：`scripts/devtools/journey_harness/`（与主仓同构路径，合入后全仓可用）。
> 每次 run 的产物索引见同目录 `EVIDENCE_INDEX.md`；完成度与取舍见 `REPORT.md`。
> v2（2026-09-27，wt654）：统一化收口——仿真/真实数据 schema 区分契约、persona
> library 接入、网络切换统一步、test clock 裁决块（详见 §4/§5）。

## 0. 设计红线（验收条款的落实方式）

1. **Simulator 不得绕过 UI**（v3/05_metrics_eval/USER_SIMULATION.md Ban 条款）：
   - `web` backend：真实 Chrome（headless）+ CDP。元素定位只读**语义树**（`flt-semantics`，即读屏软件所见），点击走 `Input.dispatchMouseEvent` 真实鼠标事件（语义节点 DOM click 为读屏用户激活通道），输入走 `Input.insertText` 真实输入通道。**不注入 Dart、不调用内部 API 改状态**；唯一允许的 URL 直达是 journey 显式声明的入口（等价用户手输 URL）。
   - `macos` backend：`flutter test integration_test/macos_journey_test.dart -d macos`（finder 级真实点击/输入，真实后端、真实窗口、引擎帧截图）。
   - `android` backend：boot AVD → `adb install` → `am start` 真实启动；**基线不做 UI 步进**（诚实声明，见 §4.4）。
   - `api` backend 是唯一非 UI 通道，仅作为后端连通性冒烟；其 run 在 manifest 的 `lane` 字段与 summary 双通道标注 `non-ui`，**不得冒充 UI 实测**。
2. **失败必须非零退出**：任一步骤 FAIL、DB 断言 FAIL、环境不可用（找不到 Chrome/AVD/Flutter 工具链）→ 进程退出码 1。`driver.start()` 失败同样写入 FAIL step 并落盘 run_manifest——**"没找到模拟器"永远是 FAIL，不是 PASS**（钉测试：`tests/test_harness_markers.py::test_cli_failure_exits_nonzero`）。
3. **每次 run 留证**：run 目录含 `run_manifest.json`（build SHA/device/time/build metadata）、`steps.json`（逐步 PASS/FAIL）、`screenshots/*.png`、`api_log.jsonl`、`db_probes.jsonl`（只读 SELECT）。
4. **仿真数据与真实数据必须可区分**（schema/标记层面；B-03 v2 新增红线，FIX-330/333 同族纪律）：见 §1 区分契约。

## 1. 仿真-真实数据区分契约（schema/标记层面；机器可核对）

模拟器产出的每一份 run 证据都**自标识为仿真数据**，与真实驱动（ns001 JOURNEY，
`backend/tests/northstar_eval/real_drive.py`）的证据在 schema 字符串层面互斥：

| 数据族 | 证据 schema（权威文件） | 落点 |
|---|---|---|
| 真实驱动 run（ns001，M 系列等） | `sparkle.northstar.real-drive.run.v1` / `.step.v1`（`real_drive.py`） | `v3-output/NORTHSTAR-LOOP1/evidence/`、/tmp 运行态 |
| 仿真 run（本 harness） | `sparkle.journey.simulator.run.v1` / `.step.v1`（`harness/models.py`） | 每 run 目录 `run_manifest.json` / `steps.json` |

- `run_manifest.json` 顶部字段：`schema` + `lane`（`simulator-ui`=web/android/macos 真实 UI 通道；`simulator-nonui`=api 冒烟）+ `persona` + `clock`。
- `steps.json` 带 envelope：`{"schema": "sparkle.journey.simulator.step.v1", "run_id", "journey_id", "backend", "lane", "ok", "steps": [...]}`（v1 为裸数组，v2 起 envelope；聚合/统计按 schema 字段分流，仿真 run 永不计入真实驱动口径）。
- **账号命名约定**（数据层面第三重可区分）：仿真账号一律 `jh_` 前缀（journey harness）；真实驱动账号 `northstar_` 前缀；示例/demo 账号走产品 DEMO 通道。仿真账号经产品公开 API 真实注册（UI 通道的前提），但其证据永远带 simulator schema，不冒充真实用户数据。
- 互斥性由钉测试守护：`tests/test_harness_markers.py::test_simulator_schema_distinct_from_real_drive_schema` 直接对账 `real_drive.py` 源码里的 schema 常量。

## 2. 统一入口

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

## 3. 产物路径约定（每次 run 一个目录）

```
v3-output/B-03/evidence/<journey>_<backend>_<YYYYMMDD>_<HHMMSS>_<4hex>/
├── run_manifest.json     # run 唯一事实源（验收字段见下）；schema/lane 自标识仿真数据（§1）
├── steps.json            # simulator.step.v1 envelope + 逐步 PASS/FAIL + detail + duration_ms + artifacts
├── journey_definition.json  # 本次 run 用的 journey 定义快照（含 persona，可复现）
├── screenshots/          # 每步 UI 现场（web/macos/android）；失败步自动补拍 FAIL_*
├── api_log.jsonl         # HTTP/WS 请求-响应留存（api=直驱；web=CDP 网络事件+网络切换记录）
├── db_probes.jsonl       # 只读 DB 探针（docker exec psql，SELECT-only，主仓 DB 只读纪律）
└── macos_journey_run.log / <name>.log   # 平台运行日志引用
```

`run_manifest.json` 必含字段（对应任务卡验收）：

- `schema` / `lane`：仿真数据自标识（§1 区分契约）
- `base_sha` / `final_sha`：worktree HEAD；dirty 时 final_sha 带 `-dirty(N files, not committed by design)` 后缀（基线期 dirty 是常态且被显式声明）
- `device`：macOS=`flutter test -d macos`；Web=Chrome 版本/viewport/headless；Android=`AVD:<名> serial=<serial>`
- `started_at` / `finished_at`：UTC ISO 时间
- `persona`：journey 声明的 test persona 全量（persona_library 快照；未声明 = `{}`）
- `clock`：时钟模式声明（`wall` + 受控时钟推进 unsupported + 原因，§5）
- `app_build`：pubspec name/version；web 附 `web_built_at`、`served_url`；android 附 apk 路径；macos 附 test_file
- `gateway`、`steps[]`、`ok`、`summary`

## 4. 各平台「GJ01 最小壳」启动手册

### 4.1 macOS（复用既有 macos_journey_test.dart，访客 journey）

前置：Flutter 工具链 + macOS 桌面目标（`flutter devices` 可见 `macOS (desktop)`）。

```bash
cd <repo根>
bash scripts/devtools/journey_harness/run_macos_journey.sh
```

内容：登录页 → 以访客身份继续 → Cockpit 首页 → 星图 → 对话（发送/流式/中断）→ 社群 → 我的 → 设置 → 登出 → 回登录页。文本定位 zh/en 双语自适应；截图经引擎 RepaintBoundary 直取（锁屏也能拍），默认落到本次 run 的 `screenshots/`（由 `--dart-define=JOURNEY_SHOT_DEST` 注入，测试文件内已支持）。

判据：`flutter test` 退出码 0 **且** 输出含 `JOURNEY_DONE failures=0`；否则非零退出。

### 4.2 Web（Chrome + CDP 真实 UI journey，GJ01 全 18 步）

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

**基线现状**：
- GJ01S 最小壳（`--journey GJ01S --backend web`）PASS（2026-09-19 实测）：App 启动 → 登录页语义树可达 → 注册表单可输入 → 返回登录页。
- GJ01 全 18 步曾在 `submit_register` 诚实 FAIL（**产品缺陷**：注册网关 200 后 App 误报网络错误卡死，五连复现定界 Flutter Web Dart 侧，登记 V3-FIX-17）。**该缺陷已修**（FIXED@77b3cb31，wt490：fromDio unknown 三态映射 + register 成功判定=2xx+user 体可解析，125 测绿），Web GJ01 全程运行级复验列入待验清单（v2 变更后需活栈复跑）。

已知坑（已内建处理）：
- **locale**：driver 以 `--accept-lang=en-US` 启动 Chrome 固定 App 语言（仅 `--lang` 不影响 `navigator.languages`，曾致 zh 界面对不上 en 步骤定义）。后续 journey 文本统一按 zh 书写（App 跟随宿主 locale 的行为已由步骤文本对齐）。
- **SPA 路由刷新**：`serve_web.py` 对未知路径回退 index.html。
- headless CanvasKit 需 `--enable-unsafe-swiftshader`（driver 已带）。

### 4.3 Android（最小壳：boot → install → launch → 取证）

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
- UI 步进仍按下方 §4.4 声明 unsupported。

任一失败 → 非零退出。

### 4.4 明确 unsupported 的部分（诚实声明）

| 能力 | 平台 | 状态 | 原因 |
|---|---|---|---|
| GJ01 邮箱注册+onboarding 全 UI 步进 | macOS | 本轮未跑全量 | 复用的 `macos_journey_test.dart` 是访客 journey（登录页→首页→聊天→登出），不含邮箱注册/onboarding 步；见 §6 TODO |
| GJ01 UI 步进（find/tap/type） | Android | `ui_steps: unsupported` | Flutter 语义树在 Android 按需构建，需无障碍服务激活；`adb uiautomator` 看不到 Flutter 节点。基线只验「可启动+前台+取证」，不做坐标盲点冒充 |
| `set_network` slow/限速 | android | unsupported | 非 root Android 无干净限速 seam（offline/online=飞行模式可用） |
| `set_network`（全部档位） | macOS | unsupported | flutter test 进程内无网络 seam；OS 级断网会撕裂宿主工具链与后端连通；待进程级网络注入（Toxiproxy 类）增量 |
| `set_network`（全部档位） | api | unsupported | non-ui lane localhost 回环无用户侧网络可切；网络损伤语义属 UI 通道 |
| 受控测试时钟推进 | 全部 | unsupported | 产品无时钟 seam（real_drive.py 时间语义裁决方案 c：跨进程假钟撕裂 JWT/DB/Redis 时钟一致性并伪造证据时间戳）；longitudinal Day-N 只允许真实跨日 |

平台完全不支持时（如目标机器无 macOS 桌面目标），driver 在 `start()` 阶段即 StepFailure → 退出码 1，并在错误信息中说明原因——**不支持 ≠ 静默 PASS**。

## 5. 统一化现状（任务卡 work#2 对照）

| 项 | 现状 |
|---|---|
| 仿真/真实区分 | **schema/标记层互斥**（§1）：`run_manifest.schema`=sparkle.journey.simulator.run.v1、`lane`=simulator-ui/nonui、`steps.json` envelope=simulator.step.v1、账号 `jh_` 前缀约定；钉测试对账 real_drive.py 权威 schema |
| persona reset | 每 run 全新 `%RUN%` 唯一账号（api/web 步内注册）；macos 测试内 `SharedPreferences.clear()` 从登录页起步。**persona library 已接入**：journey 声明 `"persona": "<id>"`（GJ01/GJ08=P04，GJ04=P01），loader 加载期校验解析（未知 id=加载失败），run_manifest.persona + journey_definition 快照留档。persona 驱动步参数化=下轮增量 |
| trace capture | web=CDP Network 事件→api_log.jsonl；api=直驱留存；android=logcat 快照；macos=flutter test 全量日志 |
| 截图路径 | 统一落 `v3-output/B-03/evidence/<run_id>/screenshots/`，前缀序号，失败步自动补拍 |
| 网络切换 | **已内建统一 action `set_network`**：web=CDP `Network.emulateNetworkConditions`（offline/online/slow，DevTools Slow-3G 同源档，可覆盖 latency/带宽）；android=系统飞行模式 `cmd connectivity airplane-mode`（offline/online，回读 `airplane_mode_on` 确认生效）；macos/api=诚实 unsupported（§4.4 有原因）。模拟生命周期=driver 进程生命周期（web 每 run 临时 profile Chrome、android 每 run boot/杀 AVD），不跨 run 泄漏。journey 内声明示例：`{"name": "go_offline", "action": "set_network", "args": {"mode": "offline"}}` |
| test clock | **裁决块统一**：`run_manifest.clock`=`{"mode": "wall", "controlled_advance": "unsupported", "reason": …}`（产品无时钟 seam，裁决权威=real_drive.py 时间语义裁决方案 c）。钉测试守护：擅自实现受控时钟必先推翻该裁决并改测试，不允许静默引入 |
| build metadata | run_manifest.json：schema/lane/SHA/device/time/persona/clock/build（§3） |

## 6. 已知 TODO（下轮演进）

1. Android UI 步进：接 Flutter Android 无障碍（`flutter build apk` 默认关闭 semantics；可用 `FlutterDriver`/integration_test on-device 或开启 TalkBack 后 uiautomator）跑真实 GJ01。
2. macOS 全量注册 journey：把 web 版 18 步移植为 dart finder 版或接入统一语义层。
3. persona 驱动步参数化：journey 步骤 args 引用 persona 字段（如 `{{persona.goal}}` 注入 onboarding goal），当前 persona 仅声明+留档。
4. macOS 进程级网络注入（Toxiproxy 类）解锁 set_network 慢网/断网档。
5. GJ04/GJ08 扩 web/android backend（api lane 已通，见 EVIDENCE_INDEX）。
6. GJ01 Web 全程运行级复验（V3-FIX-17 已修，见 §4.2）——列入活栈待验清单。

## 7. HEAVY 内存纪律（跑 harness 的 agent 必读）

一次只跑一个平台，顺序 macOS → Web → Android；每阶段前查 `sysctl vm.swapusage`（swap 空闲 <1.2G 转文档阶段；<800M 立即杀当前平台进程）；Gradle 一律 `-Xmx2g`；flutter 命令串行；浏览器单实例；阶段间杀净上一平台进程；收工杀模拟器/gradle daemon/浏览器/serve，删 `mobile/build`、`.dart_tool`（AGENTS.md 清单）。

## 8. 盘点与复用关系（work#1，v2 刷新 @2026-09-27）

| 既有面 | 与本 harness 的关系 |
|---|---|
| `mobile/integration_test/macos_journey_test.dart` | macOS 权威真 UI journey（finder 级），MacosDriver 直接复用不重建 |
| `mobile/test/widget/u09_platform_render_contract_test.dart` + `visual_baseline/` | headless 渲染契约/截图矩阵链（U-09），与 harness 互补：渲染指纹一致性归它，跨端 journey 行为归 harness |
| `tests_e2e/`（pytest API 层 E2E） | API 层跨层测试线；harness api lane 是 journey 语义的冒烟切片，不合并两套 |
| `scripts/journey_smoke.sh` + CI journey-smoke job | 后端 stage35 旅程冒烟（backend/tests），与本 harness 无代码交集，仅同名 |
| CI simulation-benchmark job（`backend/scripts/run_simulation_benchmark`） | 后端仿真基准，非 UI journey 基建，无交集 |
| `backend/app/services/simulation/seed_extractor.py`（SeedExtractor） | **产品功能**（AI 仿真训练的种子推荐），不是测试仿真器——重名不同物，harness 不依赖也不重建它 |
| `backend/tests/northstar_eval/real_drive.py`（ns001 真实驱动） | 真实驱动权威仪器；harness 只读参照其证据 schema 精神（§1 互斥契约），不改其文件、不碰 /tmp 运行态 |
| `scripts/devtools/q02_run_golden_journeys.py` | 早期 golden journey 驱动（G 服评测线）；harness 是其跨端 UI 化后继，api lane 模式复用自 acceptance_memory_revival 一族 |
