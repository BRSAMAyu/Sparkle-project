# U-09 REPORT — L5 三端视觉/交互一致性 Diff（headless 段 + 截图矩阵交接）

- **Worker**: wt390（stream=UX，HEAVY，卡 U-09，deps B-03/B-04/U-06/U-08 全 done）
- **Worktree**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt390-u09-tri`（base `d105aa57`）
- **Base SHA**: `d105aa57` / **Final SHA**: 见本卡单提交（分支 `wt390-u09-tri` HEAD）
- **Status**: **READY_FOR_REVIEW**（headless 段全绿；真机截图矩阵段转 HUMAN_INBOX+主会话，不伪造截图）
- **环境现实声明**: worker 无浏览器/模拟器权限——按卡的两段交付执行；①headless 契约测试+代码级修复（本提交）；②45 行截图矩阵清单与 diff report 模板就绪待真机批次。

---

## 1. 平台分支审计清单（mobile/lib 全量 kIsWeb/Platform/defaultTargetPlatform 扫描）

| 文件 | 分支形态 | 审计结论 |
|---|---|---|
| `core/constants/api_constants.dart` | kIsWeb → android/iOS → 桌面 fallback localhost | 契约测试 C2 三目标钉死；web 段 VM 不可测（kIsWeb 编译期常量），允许差异登记 |
| `core/storage/token_storage_{io,web}.dart` | 条件导入（dart.library.html） | session 双后端契约测试 C4 钉死（web-round1 W-1/W-2 修复延续，无回归） |
| `core/utils/responsive_utils.dart` | **dart:io Platform（缺陷，已修）** | 与 app 其余平台分支不同源、宿主相关、不可测——红测 C3 修复 |
| `core/design/design_system.dart` | pageTransitionsTheme 按 TargetPlatform | iOS=Cupertino/其余=FadeForwards；允许差异登记（不砍平台能力） |
| `core/design/adaptive/emotion_responsive_theme.dart` | NoTransitionsBuilder 全平台覆盖 | 一致，无断裂 |
| `core/services/sensory_feedback_service.dart` / `bgm_service.dart` | iOS/Android 门控 | 触觉/音频移动硬件约定，允许差异登记 |
| `core/services/http_client_pinning_io.dart` 等条件导入族 | `_io`/`_web` 变体 | 既有先例模式，无断裂 |
| `core/state/*`（U-06 四件套） | **零平台分支** | canonical 状态语义天然三端同源——契约测试 C1 的主体 |
| `firebase_options.dart` / `client_observability_service.dart` / `performance_monitor.dart` | 观测性打点 | 非渲染/交互面，不影响一致性 |

## 2. 修复项红绿（红测先行）

### 修① 平台判定接缝（唯一真实代码缺陷）
- 文件：`mobile/lib/core/utils/responsive_utils.dart`
- 根因：`isMobilePlatform`/`isDesktopPlatform` 读 `dart:io Platform.isIOS/isMacOS`——判定取决于**宿主机器**而非目标平台；与 `api_constants.dart` 等按 `defaultTargetPlatform` 分支的其余代码不同源，且任何平台模拟测试无法钉住。交付平台集上两者取值一致 → 零生产行为变化，只恢复同源与可测性。
- 红：`git stash` 修复后 C3 定向真跑 → `Expected: true / Actual: <false>`（android 目标在 macOS 宿主被判非移动端）。
- 绿：修复后 C3 → `00:00 +1: All tests passed!`。
- 消费面：全仓 grep 零业务消费方（潜在 API 使用者获得一致语义），无回归面。

### 修② 视觉基线 harness 的 macos 平台段缺失
- 文件：`scripts/devtools/visual_baseline/naming.py`（`PLATFORMS += macos`）
- 根因：U-09 三端=Android/Web/macOS，但 B-04 命名注册表只认 android/web/ios——真机段按卡口径采集的 macos 截图会 NamingError，无法过 `manifest/verify` 链。
- 红：`test_matrix.py::TestMacosPlatformSegment` 实现前 `ModuleNotFoundError` + `NamingError`（当场真跑红）。
- 绿：实现后全包 pytest 48/48。

## 3. 契约测试清单（`mobile/test/widget/u09_platform_render_contract_test.dart`，11 用例全绿）

| 契约 | 断言 |
|---|---|
| C1 状态管线三端渲染 | canonical 相位（loading/longRunning/offline/reconnecting/errorRecoverable/errorTerminal/authExpired/permissionDenied/conflict/awaitingUser/empty 共 11 相位）在 android/iOS/macOS 目标下渲染指纹（全部可见文案+可操作动作标签）逐字一致；失败族必有下一步按钮（600ms 升格时点统一取样） |
| C2 URL/网端 | android=10.0.2.2 模拟器别名 / iOS=localhost / macOS=localhost fallback；WS scheme 全平台不变式（只允许 ws/wss） |
| C3 平台判定接缝 | ResponsiveUtils 与 defaultTargetPlatform 同源（修①的锁） |
| C4 session | TokenStorage io 后端（SecureTokenStorage）与 web 后端（TokenStorageWeb）对同一脚本序列（miss→write→overwrite→delete→再 delete）产生同一可见状态 |
| C5 keyboard | enter-to-send 是用户偏好非平台分支：三端 textInputAction=send + receiveAction 真发送；偏好关闭三端同回落 newline |
| C6 layout overflow | canonical home（dashboard harness 同一 persona/goal/task 样本）在 MULTIPLATFORM 三端 viewport（android 360×800@3、macOS 小窗 800×600@2/正常 1280×800@2、web 双宽 1280×720/360×720）真实泵入零 overflow + workspace 锚点滚动可达（wt296 全展开 slot 基线） |
| C7 允许差异登记表 | platformDivergences 非空、逐条 point/platforms/reason 齐备、session/URL/转场三类差异在案 |

夹具：`mobile/test/shared/canonical_state_fixture.dart`——三端共用 canonical state（persona=Dashboard Test demo 账号/goal=plan-1/task=task-1，与 B-04 states.py 注册表同一对齐口径），含 canonical viewport 与 platformDivergences 机器可读登记表。

## 4. 允许差异 reason 清单（权威文档已入 `v3/04_ux/MULTIPLATFORM.md`）

| 差异点 | 平台 | reason |
|---|---|---|
| 导航转场 pageTransitionsTheme | iOS=Cupertino/其余=FadeForwards/fuchsia=框架默认 | iOS 边缘滑返是系统能力，不为一致而砍平台能力；fuchsia 非交付目标 |
| 触觉/音频后端 | 桌面/web 静默降级 | 移动硬件能力，桌面/web 无硬件约定 |
| API/WS 默认主机 | android=10.0.2.2 | 模拟器宿主回环别名；dart-define 覆盖时三端一致 |
| token 存储后端 | web=localStorage | secure storage web 并发写静默丢失实证（W-1/W-2）；竞赛口径可接受，升级路径已登记 |
| 键盘 IME 动作按钮视觉 | android/iOS | 系统渲染；行为契约由 C5 钉死 |

## 5. 截图矩阵交接清单（真机段，转 HUMAN_INBOX+主会话）

- 可执行清单：`v3-output/U-09/SCREENSHOT_MATRIX.md`——9 canonical surfaces × 3 平台 × 各端 viewport = **45 行**（android 1080×2400@3；web 1280×720+360×720；macOS 800×600@2+1280×800@2），每行含采集入口（B-04 states.py 同源）+ 通用断言点（核心层级/文案/状态语义）+ 逐张命名模板。
- diff report 模板：`v3-output/U-09/DIFF_REPORT.md`——A/B issue 记录格式 + 允许差异预登记表 + 提交物 checklist（manifest/verify/coverage 链沿用 B-04 harness）。
- 生成命令（可复跑）：`python3 scripts/devtools/visual_baseline/visual_baseline.py matrix --build-sha8 $(git rev-parse --short=8 HEAD)`；`... report-template -o v3-output/U-09/DIFF_REPORT.md`。
- 真机批次断言点：每张图核对「核心层级结构/核心文案/状态语义（22 相位代表面）+ 逐面补充断言点（matrix.py `_SURFACE_ASSERTIONS`）」。

## 6. 质量门（当场真跑证据）

| 门 | 结果 |
|---|---|
| 契约测试（本卡新文件，定向真跑） | **11/11 绿**（`flutter test ... --concurrency=1`） |
| 邻域回归（定向真跑 3 批） | state coverage+view 37 绿；matrix+U-08 semantics 19 绿；chat_input echo+dashboard structure 7 绿 |
| 红测演示 | C3 stash 修复 → 红（Expected:true/Actual:false）→ pop → 绿；python macos 段红→绿 |
| flutter analyze | **E0=0**，全量 601 = base 601 零漂移（新文件零 issue） |
| 守卫 | **84/84 exit 0**（worktree 缺 gitignored 生成物：mobile/lib/gen、backend app/gateway gen 从主仓 cp -RL 补齐后全绿；AQ/BG/K/Z 均因生成物缺失，非代码回归） |
| 冷 mypy | **1103 = 基线 1103 零漂移**（本卡零 backend 源码改动） |
| ruff（visual_baseline 包） | All checks passed；pytest 48/48（12 新 + 36 存量） |
| swap 门 | 14.5G used/837M free，但 memory pressure level=1、free≈63%（>1.2G 余量口径）→ 按 wt365 先例定向真跑全程 `--concurrency=1`、单文件/批 |

## 7. 改动清单（全部）

- `mobile/lib/core/utils/responsive_utils.dart`（修①平台判定接缝，-2/+17）
- `mobile/test/shared/canonical_state_fixture.dart`（新，canonical 夹具+允许差异登记表）
- `mobile/test/widget/u09_platform_render_contract_test.dart`（新，11 契约用例）
- `scripts/devtools/visual_baseline/naming.py`（修②macos 平台段）
- `scripts/devtools/visual_baseline/matrix.py`（新，45 行矩阵生成器）
- `scripts/devtools/visual_baseline/tests/test_matrix.py`（新，12 用例）
- `scripts/devtools/visual_baseline/visual_baseline.py`（matrix/report-template 子命令接线）
- `v3/04_ux/MULTIPLATFORM.md`（允许差异登记表+两段交付分界，权威文档）
- `v3-output/U-09/SCREENSHOT_MATRIX.md` + `DIFF_REPORT.md`（真机段交接件）

## 8. DEFERRED / 移交

- 真机截图矩阵 45 张采集 + diff report 填写：**HUMAN_INBOX + 主会话**（本 worker 无浏览器/模拟器；不伪造视觉证据）。清单与模板已就绪（§5）。
- web 端 kIsWeb 分支（token 存储 web 后端实装、web baseUrl）VM 不可翻转：真机 web 段由截图矩阵+web-round1 既有证据覆盖，契约测试以几何近似+静态审计补偿，已在 C7/夹具登记。
- 存量观察（不属本卡平台断裂，移交 UX owner）：StagedSurfaceLoader 的 longRunning 退路用 `TextButton.icon` 而 SurfaceStateView 动作行用 `SparkleButton`——按钮组件不同源，三端一致无碍，属设计系统收敛面（U-01 inventory 口径）。

## 9. Forbidden 自查

- 未重建真源：canonical 语义=U-06 SurfacePhase；采集/命名= B-04 harness；业务样本=dashboard harness——全部复用。
- 未用 mock 冒充：契约测试用 harness 静态注入（既有惯例）；截图零伪造（未采集=未交付）。
- 未为一致砍平台能力：Cupertino 转场/触觉等平台约定差异全部显式登记 reason 而非抹平。
- 未只凭静态阅读宣称 UX 通过：headless 段全部真实泵入渲染树断言；真机段诚实转交。
