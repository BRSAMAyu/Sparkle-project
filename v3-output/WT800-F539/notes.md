# WT800-F539 — V3-FIX-539 macOS 桌面注册提交 tap「系统性无效零反馈」根治

> 2026-09-28 ｜ worker wt800 ｜ worktree `Sparkle-sysrev/wt800-f539`（分支 `agent/node-b/wt800/f539`，base=main@86818d0d，含 V3-FIX-507 闭账）
> 约束遵守：未 flutter run 真机/模拟器（widget 测试面验证）；未触碰运行栈与 ns001；未 push；未改台账（闭账归主会话）。台账行内「J-02 残留工作关联」以驱动侧加固响应（见 §7，披露未真机复验）。

## 1. 根因链（证据复核 + widget 探针实证）

J-02（wt792）实测签名：注册表单填完、tap 提交 ×2 → 无导航、无错误词（TEXTDUMP n=13）、零日志，6/6 复现；同屏「登录」等按钮 tap 有效。wt436 已证明 J-01 同签名是「驱动误点 AppBar 标题」假阳性 + 键盘链真缺陷（均已修），且 J-02 驱动已改用 `sparkleButtonFinder`（SparkleButton 祖先作用域）规避标题陷阱——所以 J-02 的 tap 确实点在真实提交钮上，需新根因。

**根因 = 几何折叠线 × 驱动盲 tap × 单通道瞬态反馈 三因子叠加，非 hit-test/手势/焦点层缺陷：**

```
800x600 逻辑桌面窗（1600x1200 物理 @2x，J-02 实测几何）
  ↑ 注册表单填完后（驱动 enterText 四字段、不滚动）：
  │   ToS tile   rect y≈533-589  → 完整在视口内 → 盲 tap 命中 → 勾上 ✓
  │   Privacy tile rect y≈589-645 → 中心在折叠线下 → 盲 tap 静默 miss（warnIfMissed:false）
  │     → _acceptedPrivacy 恒 false，零告警零状态变化（探针测试1 实证）
  ↑ 驱动 ensureVisible 后 tap 真实提交钮 → _submit 正常执行：
  │   validate() 通过 → consent 守卫 `!_acceptedPrivacy` → AppFeedback.info
  │   → 唯一反馈 = 2.5s 瞬态 snackbar（视口底部）→ return，无任何日志
  ↑ 驱动等 12s 才 dumpTexts/错误词扫描 → toast 早已消失
  → 屏面与 tap 前完全一致：「tap 无效 + 零反馈 + 零日志」，6/6 系统性
    （驱动每次都盲 tap checkbox → 每次都漏勾 → 确定性复现）
```

widget 探针实证（`register_screen_f539_consent_deadend_test.dart` 测试1，800x600 同几何）：盲 tap 后 `Checkbox(ToS).value=true`、`Checkbox(Privacy).value=false`——机理钉死。**该缺陷是真实产品缺陷而非纯 harness 假阳性**：真实 800x600 桌面用户同样会把 Privacy tile 看不见/漏勾，提交后只看到 2.5s toast，错过即「死按钮」，且无任何指向性恢复路径。

## 2. 假设排除表

| # | 假设（排查线索 ①②③） | 排除/证实 | 证据 |
|---|---|---|---|
| H1 | 全局手势/hit-test 被装饰层吞（stripe/遮罩） | **排除** | GraphiteScaffold/SparklePageScaffold 无 Overlay 装饰层；同屏「登录」钮 tap 有效（J-02 实测） |
| H2 | SparkleStaggerItem 入场动画位移/透明导致命中错位 | **排除** | stagger 走 AnimatedSlide/Scale/Opacity，均随变换参与 hit-test；Opacity=0 在 Flutter 中仍可命中（不拦）；动画 ~500ms 内完成，tap 远晚于此。且登录屏无 stagger 也能复现同签名的 J-01 键盘链问题——非共性因子 |
| H3 | SparkleButton `_handlePressed` 静默吞（disabled/loading/onPressed null） | **排除** | onTap 与 disabled 同源于 `authState.isLoading`；isLoading 恒 false（注册屏无在途请求），6/6 确定性不成立 |
| H4 | `_submit` isLoading 防重入守卫吞掉提交 | **排除** | 同 H4 逻辑——`ref.read(authProvider).isLoading` 在注册屏为 false；该守卫是 W-4 双 POST 防护，保留 |
| H5 | 表单校验静默失败（validator 报错但驱动没看到） | **部分排除** | 校验失败有内联错误文案（N25 三段制），且四字段由 enterText 直写 controller 必过校验；O3 测试链已绿 |
| H6 | 平台层（macOS 鼠标事件链）tap 未达 | **排除**（widget 面内） | 探针证明同屏 tile0 tap 命中并翻转状态——事件派发链完好，问题在目标不可达（折叠线下）而非事件不达 |
| H7 | **折叠线几何 × 盲 tap × 瞬态反馈**（本文根因） | **证实** | 探针测试1（盲 tap 后 ToS=勾/Privacy=漏）+ 测试2（拦截后 toast 外零持久指示）+ J-02 六跑全走同一驱动脉络 |

## 3. 修法（唯一产品码文件 `mobile/lib/features/auth/presentation/screens/register_screen.dart`）

1. **滚动到因**：consent 区（两块协议 tile + 两个查看钮）包入带 `_consentSectionKey` 的嵌套 Column（保持外层 `CrossAxisAlignment.stretch` 视觉语义）；`_submit` 被 consent 守卫拦截时 `Scrollable.ensureVisible`（250ms easeOutCubic，alignment 0.15）滚到协议区——用户/驱动获得指向性恢复路径。
2. **持久内联错误**：拦截时置 `_consentError=true`，协议区底部渲染带 `ValueKey('consentInlineError')` 的错误文案（复用既有 `authTermsRequired` 词条，零新增 l10n key）；**toast 消失后仍在**，勾齐双协议即清。
3. **tile 高亮**：拦截后未勾 tile 低错误色底（`DS.error.withValues(alpha:0.08)`），在因可见。
4. **瞬态 toast 保留**（AppFeedback.info 原样）——它是唯一即时通道；本修把单通道扩为「即时 + 持久 + 在因 + 可恢复」。

防御性排除说明：任务线索提到的「显式 MouseRegion / onFocus 校验前置」未采用——InkWell 桌面默认 click 光标已存在，且 H6 证明事件链完好，MouseRegion 属无靶加固；onFocus 前置校验会违反 N25「未提交不提前报错」三段制契约，不动。

## 4. 红→绿实录

测试：`mobile/test/features/auth/register_screen_f539_consent_deadend_test.dart`（新，3 测，完整复刻 J-02 驱动脉络：800x600 几何 / enterText 不滚动 / 盲 tap tiles warnIfMissed:false / ensureVisible+tap 提交 / 12s 扫描窗等价时钟序列）。

命令：`cd mobile && flutter test test/features/auth/register_screen_f539_consent_deadend_test.dart`

- **探针（机理钉死，恒绿）**：盲 tap 后 ToS 勾上、Privacy 静默漏勾（`Checkbox.value` 断言）。
- **修前红 ×2**：`consent 拦截后必须有滚动到因`——`tileFullyInViewport(0)` 期望 true 实得 false（拦截后协议区不滚动）；`内联错误随补勾清除`——byKey finder 无匹配对象（内联错误不存在，定义性红）。瞬态性另证：toast 文案在驱动 12s 扫描窗等价时钟后仅剩 0 个匹配（旧单通道）。
- **修后绿（3/3）**：滚动到因双 tile 完整入视口 ✓；toast 消失后持久内联仍在（同文案从 2 通道回落 1 = toast 已逝的实证）✓；补勾 Privacy → 内联清除 → 再提交 `registerCalls==1` + 失败 snackbar 可见 ✓。

既有契约同步：`register_screen_o3_submit_test.dart` 拦截反馈断言 `findsOneWidget → findsNWidgets(2)`（单通道→双通道契约更新，注明 V3-FIX-539，**非删断言**）。

## 5. 触达面与静态面

- `cd mobile && flutter test test/features/auth` → **62 passed, 0 failed**（含 a5 overflow 布局回归、O3 键盘链红绿、N25 校验时序——嵌套 Column 改动零布局回归）。
- `flutter analyze` → **No issues found**（13 处新增 info 已收敛：unawaited(ensureVisible) + 12 处 require_trailing_commas dart fix）。
- RegisterScreen 引用面 grep：仅 J-02 integration_test 与 no_network_http_overrides，无其他测试触达。

## 6. 确证边界（如实）

- **widget 测试面确证**：几何折叠线、盲 tap 静默 miss、consent 守卫拦截路径、修复后滚动+持久反馈，全部在 800x600（=J-02 实测逻辑几何）AutomatedTestBinding 下实证。
- **未确证**：LiveTestWidgetsFlutterBinding（integration_test 真机 macOS）下的端到端恢复——`warnIfMissed` miss 判定、真实时钟 toast 消失时点与假时钟 pump 序列的等价性未经真机复跑。J-02 重跑（残留工作）应走纯 UI 注册路径验证；若仍 bounce，驱动侧 TEXTDUMP 现在能看到内联错误（持久在因），归因不再盲。
- J-02 截图名 register 内容为登录屏：`shot()` 取「root 起深度优先第一个 RepaintBoundary」= 栈底路由（login）而非栈顶（register）——**harness 采集缺陷**（证据失真，非产品缺陷；本卡不修，提请集成会话登记/归属 harness 卡）。

## 7. 驱动侧加固（同 commit，披露未真机复验）

`mobile/integration_test/j02_fastpath_journey_test.dart` r2 段：盲 tap 每 tile 前 `ensureVisible + pump(400ms)`（部分可见不够——tap 打 tile 中心，探针证明 tile1 部分可见时中心仍在折叠线下；revealFinder 的 presentInViewport 判定同样不足，故用 ensureVisible 全可见语义）。这与 submit 钮的 ensureVisible 同契约；FIX-539 修复后即使漏勾，驱动也能从持久内联错误直接归因。

## 8. 改动清单

- `mobile/lib/features/auth/presentation/screens/register_screen.dart`（唯一产品码：_consentSectionKey/_consentError 两状态、_flagConsentMissing、consent 区嵌套 Column+tileColor+内联错误、onChanged 勾齐清除、_submit 拦截分支挂 _flagConsentMissing）
- `mobile/test/features/auth/register_screen_f539_consent_deadend_test.dart`（新，3 测：机理探针 + 两红绿锚）
- `mobile/test/features/auth/register_screen_o3_submit_test.dart`（拦截反馈 1→2 通道契约同步）
- `mobile/integration_test/j02_fastpath_journey_test.dart`（r2 盲 tap 前 ensureVisible，harness 加固）
- worktree 注：`mobile/lib/gen/` 为 gitignored 生成物，自主 checkout 同 HEAD 复制以供编译，不入 commit。
