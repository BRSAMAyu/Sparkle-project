# SPEC-C 收工报告 — #4 galaxy 错误态人话 + #6 chat 等待期持续源裁 1

> Worker：A 纵队设计语言线（worktree wt178，基线 575c267b）
> 规范依据：`v3-output/A-SPEC-V1_1/REPORT.md` §4 N3/N4、§5 清单 #4/#6
> 交付物：本报告 + `changes.patch`（同目录）。零 commit / 零 push / 零凭据。

---

## 一、实现清单（逐条对照验收自证）

### #4 galaxy 错误态人话（N4）

改什么：`'$_loadError'` 裸异常直出退役；error→人话映射先局部函数（后续收 lexicon）；retry action 保留。

| # | 改动 | 落点 | 对照验收 |
|---|---|---|---|
| 4-1 | 存储类型 `Object? _loadError` → `GalaxyError?`（赋值同步改为存 `next.lastError` 整对象，不再预拆 `.message`） | `galaxy_screen.dart:158`（原 `Object?` 声明）、`:407`（原 `_loadError = next.lastError!.message`） | 卡面「+158 存储类型」；`Instance of ...` 风险在类型层消除 |
| 4-2 | 局部映射函数 `_galaxyLoadErrorMessage(AppLocalizations, GalaxyError?)`：按 `GalaxyErrorType`（network / circuitBreakerOpen / unknown）三档映射人话模板；零新依赖（仅既有 enum switch + l10n getter） | `galaxy_screen.dart`（`_StatusPanel` 前文件私有函数） | 「error→人话映射先局部函数后收 lexicon」 |
| 4-3 | 错误面板 `message:` 改走映射函数；`title: galaxyLoadFailedTitle` 与 `actionLabel: retry / onAction: _loadGraph` 原样保留 | `galaxy_screen.dart:2870` 一带（原 `message: '$_loadError'`） | 「人话模板（星图加载失败，你的数据没有丢级）+ 保留既有 retry action」 |
| 4-4 | l10n 三 key 双语（独立前缀 `galaxyErrorHuman`，插 `app_zh.arb`/`app_en.arb` 文件尾部连续块）+ `flutter gen-l10n` 重生成三个 `app_localizations*.dart` | arb 尾部块（见「冲突面申报」） | 「人话文案走 l10n（双语+gen-l10n）」 |

人话模板（zh，en 同构见 arb）：
- 默认（unknown）：`星图出了点小状况，暂时加载不了。你的数据没有丢，稍后再试一次。`
- 网络（network）：`网络好像不太顺畅，星图暂时加载不了。你的数据没有丢，稍后再试一次。`
- 服务（circuitBreakerOpen）：`星图服务正忙，暂时加载不了。你的数据没有丢，稍后再试一次。`

验收自证（测试见第三节）：
- **Object 值不出现于 Text**：新增 widget test 注入 `GalaxyError.unknown('Exception: SocketException: Connection refused ...')` 级裸异常文本，断言 `find.textContaining('SocketException'/'Connection refused'/'Exception')` 全部 `findsNothing`；类型收窄后 `'$_loadError'` 插值点已清零（`git grep "\$_loadError"` = 0 处）。
- **快照断言文案为人话模板输出**：unknown → `galaxyErrorHumanDefault` 精确 `find.text` 命中；circuitBreakerOpen → `galaxyErrorHumanService` 命中且 network/default 模板不串档。

### #6 chat 等待期持续源裁 1（N3 呼吸禁令）

改什么：`_ReasoningBreathOverlay` 由 3s `repeat(reverse: true)` 常驻呼吸改为 320ms（M3）`forward()` 单次入场脉冲 + 静止定帧；阶段胶囊（事件窗口内 700ms repeat）成为唯一持续源。

| # | 改动 | 落点 | 对照验收 |
|---|---|---|---|
| 6-1 | `_controller` 时长 `Duration(seconds: 3)` → `Duration(milliseconds: 320)`；`repeat(reverse: true)` → `forward()`（一次性，完成即 complete、ticker 归零） | `chat_screen.dart:3845-3849`（原行号） | N3 实现无关口径：不再存在 `repeat(reverse: true)` 持续源；§5.3 特效层「单次入场 M3」同制（#8 DayZero 先例） |
| 6-2 | 入场透明度 0.03→0.08 一次到位后静止定帧（lerp 结构不变，仅驱动方式改单次）；reduce-motion 分支 `SizedBox.shrink()` 逐字保留 | `chat_screen.dart` `_ReasoningBreathOverlayState.build` | 「reduce-motion 行为不回退」（挂载点 `:1435-1440` 未动） |
| 6-3 | 挂载点条件 `!chatPureMode && _shouldShowReasoningAtmosphere(...)` 与阶段胶囊（`chat_run_phase_indicator.dart` 700ms repeat + reduce-motion 对点静止门控）均未触碰 | `chat_screen.dart:1435-1440`、`chat_run_phase_indicator.dart` | 「阶段胶囊脉冲（事件窗口内）为唯一持续源」——窗口语义原样 |

验收自证：
- **等待态活跃 repeat 源计数=1**：新 widget test（`test/widget/chat_wait_pulse_source_test.dart`）将真实 `ChatScreen` 置入等待窗（`runPhase=sending` + `aiStatus=THINKING` + streaming 空），入场窗口内活跃 frame 源 ≥2（胶囊+入场脉冲），越过 320ms 后 `transientCallbackCount == 1`（旧实现此处为 2，即本验收的判别点）。
- **reduce-motion 不回退**：`accessibleNavigation` 置真后，呼吸层子树零 `AnimatedBuilder`/零 `DecoratedBox`（构建即 `SizedBox.shrink`，与改前行为逐字一致），胶囊照常在。

---

## 二、冲突面声明（逐 worktree）

| 邻卡 | 面 | 本卡触碰 | 结论 |
|---|---|---|---|
| wt176 | `sprint_screen.dart` + provider | 未触碰 | 零重叠 |
| wt177 | `exam_sprint_dashboard_card.dart` | 未触碰 | 零重叠 |
| wt170 / wt172 | backend | 未触碰（本卡纯 mobile） | 零重叠 |
| wt175 | 纯只读巡检 | 未触碰 | 零重叠 |
| 共享面 | `mobile/lib/l10n/app_zh.arb` / `app_en.arb`（wt176/wt177 也会加 key） | **有触碰，如实申报**：只追加 key，前缀 `galaxyErrorHuman`（3 key + 3 个 `@` 元数据，zh/en 各 6 行），物理位置为两文件**末尾收尾 `}` 之前的连续块**（`redeemCode*` 块之后）；未改动任何既有 key、未插中部 | 前缀独立 + 尾部连续块 → apply --3way 冲突概率最低；若与他卡尾部追加仍狭路相逢，冲突块小且语义独立，主会话手工并档即可 |
| 共享面 | `lib/l10n/app_localizations*.dart`（gen-l10n 产物） | 仅 `flutter gen-l10n` 重生成（追加 3 getter/抽象成员）；若主会话合入时他卡已重生成，重跑 `flutter gen-l10n` 即收敛 | 声明为机械产物 |

本卡实际改动文件全集（`git status`）：
1. `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`
2. `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
3. `mobile/lib/l10n/app_zh.arb`（尾部 +6 行）
4. `mobile/lib/l10n/app_en.arb`（尾部 +6 行）
5. `mobile/lib/l10n/app_localizations.dart` / `app_localizations_zh.dart` / `app_localizations_en.dart`（gen-l10n 产物）
6. `mobile/test/features/galaxy/widget/galaxy_screen_test.dart`（更新存量 1 断言 + 新增 2 验收例）
7. `mobile/test/widget/chat_wait_pulse_source_test.dart`（新增）

---

## 三、回归对比数据（对比法：基线克隆 → 改后）

方法：`git clone <wt178> /tmp/spec-c-baseline`（HEAD=575c267b 干净基线，不触碰本树），两批**同一定向集**分别跑 `flutter test`：

定向集（两屏现有测试 + 本卡新增）：
- `test/features/galaxy/widget/galaxy_screen_test.dart`
- `test/widget/chat_scroll_test.dart`（真实 ChatScreen 挂载 harness）
- `test/widget/chat_wait_pulse_source_test.dart`（本卡新增）
- `test/features/chat/presentation/widgets/chat_run_phase_indicator_test.dart`（唯一持续源本体，未触碰证明）
- `test/widget/modeling_chat_screen_test.dart`

**结果（2026-09-23，flutter test --concurrency=1，串行单批）**：

| 批 | 树 | 文件 | 结果 |
|---|---|---|---|
| 基线批 | `/tmp/spec-c-baseline`（HEAD 575c267b 干净克隆） | 存量 4 文件（galaxy_screen / chat_scroll / chat_run_phase_indicator / modeling_chat_screen） | **+23：全部通过** |
| 改后批 | wt178 工作树 | 同上 4 文件 + 新增 `chat_wait_pulse_source_test.dart` | **+27：全部通过** |

- 净变化 = **+4 个新增验收用例，0 失败 / 0 回归**（galaxy 2 例 + chat 2 例）。
- 存量「GalaxyScreen shows retry state and reloads after retry」在改后批通过（其唯一改动断言 = 本卡行为变更本身，见第四节第 1 条）。
- 环境前置：`mobile/lib/gen/`（gitignore 的 protobuf 生成物）按 GALAXY-TEST-ISO 先例从主仓只读复制进两棵树，否则 flutter test 编译不过；不入 patch。
- 运行纪律：两批均在「flutter_tester/flutter_tools 进程=0 且 swap 空闲 ≥1.2G 且 load<8」窗口内串行执行，未与他卡测试并发。

**#6 验收断言的可判别性说明**（为何不用裸 transientCallbackCount 总数）：chat 屏在非等待态也存在既有氛围 ticker（`_BlinkingCursor` 等，本卡不触碰），绝对计数随时序波动。故改用两个噪声免疫断言：①「入场终止性」——入场脉冲结束后活跃 frame 源计数必须下降（旧 repeat(reverse) 永不下降，必失败）；②「静止定帧」——间隔 800ms 两次采样呼吸层渐变 alpha 逐位相等（旧 3s repeat 持续摆动，必失败）；③`hasScheduledFrame == true` 证明等待窗内仍有持续源（胶囊），①②证明呼吸层不在其中——三者合起来即「等待态活跃 repeat 源恰为胶囊 1 个」。

**调试过程副产物（登记防复踩）**：
1. ChatScreen 首帧 post-frame 的 `switchPlanSession → cancelActiveRun` 会复位外部预设的 runPhase——等待态类测试必须在 init settle 后重入等待窗。
2. 手动 `ProviderContainer` + `addTearDown(container.dispose)` 会在 teardown 阶段落额外 Timer 触发 `timersPending` 不变量；用 `ProviderScope` + `tester.state<ConsumerState>(...).ref` 取 notifier 即可（ChatScreen 现有绿色测试同款）。
3. 系统级 `disableAnimations` 下个别 `AnimatedSize` 会触发 performLayout 内 markNeedsLayout 断言（存量怪癖，与本卡无关）；reduce-motion 用例在 FlutterError.onError 层吸收该类异常、其余照常转发。


---

## 四、诚实申报

1. **存量测试断言有 1 处有意修改**：`galaxy_screen_test.dart`「GalaxyScreen shows retry state and reloads after retry」首断言 `find.textContaining('galaxy 500') findsOneWidget` → `findsNothing` + 人话模板 `findsOneWidget`。该断言编码的正是本卡要消灭的裸异常直出行为（N4 存量靶），属预期行为变更，非回归；重试流后半段断言（loadCalls==2、重试后原文消失）原样保留。
2. **`_loadError` 现存整 `GalaxyError` 对象而非 `.message` 字符串**：映射函数只读 `error.type`（enum switch），不读 `message` 原文——原文路径在编译期不可能到达用户文案。
3. **`_ReasoningBreathOverlay` 保留组件本体（未删）**：采纳 SPEC「删除**或**改单次入场脉冲」的后一支；氛围层保留 0.08 静止定帧（与 C-G3 被砍裁决一致——氛围层维持现状，仅裁持续源）。
4. **胶囊的 reduce-motion 现状未改**：`chat_run_phase_indicator` 在 reduce-motion 下 controller 仍 repeat 但对点静止（`pulse: null` 门控）——属既有实现、N3 等待窗豁免件，本卡按验收「不回退」对待，未扩刀；若守卫扩「长周期 repeat 模式」扫描，该处属需白名单登记的存量合法件（SPEC N3 已预留白名单条款）。
5. **worktree 内执行过 `flutter pub get`**（测试前置），`.dart_tool/` 已在收工清理清单。
6. 测试等待期遵守 HEAVY 门：swap 门未开期间未启动任何 `flutter test`；基线批与改后批串行执行。

---

## 五、守卫与规范核查

| 守卫 | 结果 |
|---|---|
| `check_dl_spec_ratchet.py` | PASS——offLadderDuration 184/184（320ms 为正典集，零新增）、gradientLiteral 303/303、breathingController 1/1、errorCopyOops 6/6，ratchet 只平不升 |
| `check_ux_component_convention.py` | PASS——rawButton 19/19、colorLiteral 100/100 等 |
| `check_l10n_regen_parity.py` | OK——11205 template keys == abstract members；zh/en 子类完整（含新增 3 key） |
| `check_i18n_coverage.py` | PASS |
| `check_ui_design_tokens_ratchet.py` | PASS |
| 裸异常机检面 | `'$_loadError'` 插值清零；映射函数可平移为 lexicon 条目（N4 预留） |

---

## 六、收工核查

- [x] 交付物仅 `v3-output/SPEC-C/REPORT.md` + `changes.patch`；零 commit / 零 push / 零凭据
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean 类树操作（基线走 `git clone` 到 /tmp，天然 HEAD 基线）
- [x] /tmp 收工自清（`/tmp/spec-c-baseline`、patch 中间件）
- [x] worktree 内 `mobile/build`、`.dart_tool`、flutter 测试进程收工清理
- [x] l10n arb 改动 = 尾部连续块 + 独立前缀，已逐 key 申报
