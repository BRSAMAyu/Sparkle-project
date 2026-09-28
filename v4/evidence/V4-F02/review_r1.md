# V4-F02 独立审查 receipt（R1）

- 审查会话：wtF02R1（未参与 F02 实现）· 2026-09-28
- 审查对象：分支 `agent/v4/f02` @ `89f66c13`（基线 `5575e38b` = 开卡时 main HEAD，`git log` 核验一致；分支形态 = 基线 + 恰 1 个 feat 提交）
- 审查方式：只读 diff 全量扫描 + 5 个源码/5 个测试文件逐行审 + 亲跑全部复跑项 + 三轮受控变异（改后即 `git checkout` 还原，工作树零残留，最终 `git status` 干净）
- **总裁决：PASS（一审通过）**——卡面三条验收全部有机器可失败断言背书且经变异实证判别力；classic 零差量 / RF-06 冲突面 / 五 Tab 路由三条红线全过；NOT_RUN 声明如实。CHALLENGED 1 项（措辞级）+ 注记 3 项，均非阻断。合并后照常走集成 SHA 复验。

## 1. 逐项核验记录（本审实跑命令与结果）

### 1.1 红线核验（最重）

| # | 声称 | 审核查证（命令/方法/结果） | 结果 |
|---|---|---|---|
| 1 | RF-06 冲突面零触碰 | `git diff --name-only 5575e38b..89f66c13` 全量 = 24 文件：7 产品码（全部**新增**于 `mobile/lib/core/design/pixel/`）+ 5 测试（全部新增于 `test/core/design/pixel/`）+ tasks.json（V4-F02 状态 3 字段 + 尾行 EOF）+ 11 evidence。`grep` 全量 diff：dashboard_screen / compact_status_bar / task_execution_screen / features/ / 路由文件**零命中** | **CONFIRMED** |
| 2 | 五 Tab 路由合同零触碰 | `kPixelStateStoryRouteName` 仅在 `pixel_state_story_page.dart` 定义（命名种子）；`grep -rn "PixelStateStoryPage\|kPixelStateStoryRouteName" lib/` 在 pixel 目录外**零命中**——未注册任何路由，`lib/core/navigation/` 零改动 | **CONFIRMED** |
| 3 | classic 降级 22dp = 既有发布语言 | `grep "BorderRadius.circular(22)" lib/core/design/design_system.dart` = 既有 CardTheme/button theme（line 227/396）；F02 `pixel_frame.dart` classic 降级 radius 恒 22.0（`pixel != null ? 0.0 : 22.0`）；classic 圆角不吸附（`PixelOutlineGeometry.stair` radius>0 分支原样 addRRect），像素语言不越界改写 classic 行为 | **CONFIRMED** |
| 4 | classic 零差量（组件面守护 + 发布面结构成立） | 组件级 3 条降级测试亲跑通过：geometry classic（radius=22、stairSteps=0、无 PixelSuccessBadge）、PrimaryAction classic（radius=18=既有 list/dialog 语言、可点击、无 PixelOutlinePainter/PixelSuccessBadge 渗漏）、state（PixelStateVisual.of classic → outline=none）。发布面：组件**零调用点**（`grep` pixel 导入仅限自身目录+测试），classic 零差量自动成立；F01 的 41 槽断言文件 `pixel_preview_theme.dart`/`theme_manager.dart` 不在本卡 diff（theme 通道未被触碰） | **CONFIRMED**（守护范围注记见 N2） |
| 5 | 无第二套令牌/颜色字面量 | 新目录 `grep "Color(0x"` 零命中；颜色全经 `context.sparkleTheme.colors` 既有语义槽（state 族 colorOf 函数表 = neutral300/textSecondary/semanticWarning/semanticError/semanticSuccess 五既有槽）；`grep "DS.spacing2"` 零命中（半格档首跑 FAIL 已修史与 test_results.json failures_fixed round 3 一致）；UI-TOKENS/SPACING-RHYTHM 守卫本审亲跑 PASS | **CONFIRMED** |
| 6 | 生成文件零触碰 | diff 无 `gen/`、`.g.dart`、l10n 文件；run_manifest gen_note（worktree 自行 cp 复制 gitignored 目录、l10n 误触再生成已还原）与 diff 实况相符 | **CONFIRMED** |

### 1.2 验收①（DPR 五档「主要轮廓稳定，文字不点阵化」）

| # | 声称 | 审核查证 | 结果 |
|---|---|---|---|
| 7 | 口径机器化：顶点物理对齐 + 阶梯步数 DPR 无关 + 逻辑盒恒等 | 逐行审 `pixel_geometry.dart`：`snapToPhysicalGrid`（round(v·dpr)/dpr）、`snapLengthToPhysical`（线宽=物理整数倍，≥1px）、stair 顶点全经吸附、`stairSteps = floor(cut/pixelStep)`（与 dpr 无参数耦合）、`physicalBoundsDeviation` ≤4×0.5px 自检量。五档纯几何用例 + widget 渲染用例 + 文字用例（fontSize 逻辑值跨档恒等、文本盒恒等、无 RawImage、无 Transform 祖先）+ classic 降级 = 9 用例亲跑通过 | **CONFIRMED**（判见预登记①） |
| 8 | 断言真值（改了会不会红） | 本审抽 **dpr=1.25 与 dpr=3.0 两档**做双向变异：(a) 实现变异——`snapToPhysicalGrid` 去吸附（恒等返回）→ 两档**均红**（顶点物理对齐断言 line 126 失败）；(b) 断言变异——`stairSteps` 期望 4→5（仅 1.25 档改）→ 1.25 **红**、3.0 **绿**（未改档不受累）。每轮变异后 `git checkout` 还原 | **CONFIRMED**（断言双向可失败） |

### 1.3 验收②（四态区分 + 无成功动效）

| # | 声称 | 审核查证 | 结果 |
|---|---|---|---|
| 9 | 四元组（令牌槽/字形/轮廓/动效）互异 | `PixelStateSpec.forState` 五态 switch 表逐行审：cancelled=neutral300/block/单线/false、unknown=textSecondary/help_outline/虚线/false、conflict=semanticWarning/call_split/双线/false、failed=semanticError/close/实心切角/false、success=semanticSuccess/check/实心切角/**true**。两两互异断言 + 轮廓四形各占一档 + 双 profile 渲染色逐对不等 + 语义标签互异（11 用例亲跑通过） | **CONFIRMED**（判见预登记②） |
| 10 | 「失败态绝不渲染成功动效」反例钉 + 活性 | 四非成功态各一条反例（无 PixelSuccessBadge 类型 / 无 check·check_circle 字形 / 无「已完成」语义 / celebrates=false）；控制组 = 含成功徽章的树同一查找器 `findsNWidgets(2)` 必须命中（计数钉死）。**加测本审变异**：`PixelRunState.cancelled → celebrates: true` → **5 用例红**（celebrates 唯一性、四元组互异、cancelled 反例、paperDay/dusk 渲染、故事页成功元素计数），还原后全绿——反例钉真实可失败 | **CONFIRMED** |
| 11 | 读屏语义不重复 | `PixelStateBadge` = `Semantics(container, label) + ExcludeSemantics(child)`（显式 label 单一来源）；失败史 round 2（label「已取消\n已取消」拼接重复）为测试如实暴露后修复，非放水；三档语义 dump 字节恒等（sha256 `93e6d7b3…` ×3，87 节点/档）= 「同状态跨档同语义」直接证据，label 为真实中文 | **CONFIRMED** |

### 1.4 验收③（装饰不吞点击 + 键盘/读屏可定位）

| # | 声称 | 审核查证 | 结果 |
|---|---|---|---|
| 12 | PixelFrame 装饰层 IgnorePointer+ExcludeSemantics | 实现面：`Positioned.fill(IgnorePointer(ExcludeSemantics(CustomPaint…)))`（pixel_frame.dart:70-88）；行为面：切角装饰叠按钮 `tapAt` 仍达（taps=1）；**控制组 (d)**：同几何加吞手势 GestureDetector → taps=0（证明 (a) 的 tap 断言有判别力，防测试自证）；实现面断言（装饰层祖先链含 IgnorePointer/ExcludeSemantics）在库。6 用例亲跑通过 | **CONFIRMED** |
| 13 | Tab/Semantics 可定位 | Tab 两击按序聚焦两个 CTA（注入 FocusNode `same()` 断言）+ `PixelFocusRingPainter` 出现；ring = 轮廓外侧 2dp 环（IgnorePointer+ExcludeSemantics 装饰）；receipt 纠正/仅本次/删除三操作 `getSemantics` tap 动作非零 + 语义定位 tap 真实触发 onCorrect；**控制组 (e)**：回调全空时同断言判 0；CTA 语义 button 标志 + 唯一 focus 挂载（TextButton 内部 Focus 持有，失败史 round 1 如实记录「child into parent of itself」修复） | **CONFIRMED** |

### 1.5 CTA 锁存窗（预登记④）

| # | 项 | 审查判断 | 结果 |
|---|---|---|---|
| 14 | 不可中断 `Future.delayed` 行为边界 | 锁存窗 = `stateMotion.press`（F01 令牌默认 80ms）+ 受控 loading 双禁写面；窗内 `onPressed: null`（按钮禁用，fail-closed）、窗结束 `mounted` 守卫解锁；onPressed 抛异常走 `finally` 仍解锁；dispose 后 future 空完成无害。最坏情形 = 前一次 press 后 ≤80ms 内合法点击被忽略——良性偏保守。测试 pump 120ms 走完窗（失败史 round 4 = fake-async 纪律修正，实现语义未动） | **CONFIRMED** |
| 15 | 「可取消需求升级」声明合理性 | 合理：80ms 窗无资源泄漏、无状态悬挂，cancellable Timer 属按需升级；登记在 limitations「已知取舍」并注明升级条件，符合最小实现纪律 | **CONFIRMED** |

### 1.6 复跑（全部本审亲跑，与 run_manifest.json 逐项对表）

| 命令（cwd wtF02/mobile 除守卫） | 本审结果 | manifest 声称 | 对表 |
|---|---|---|---|
| `flutter test test/core/design/pixel/` | **+34 All passed** | 34/34 | 一致 |
| `flutter test test/core/design` | **+160 All passed** | 160/160（126 既有+34 新增） | 一致 |
| `flutter test test/app test/widget/a11y_semantic_labels_test.dart test/widget_test.dart` | **+45 ~1 All passed** | +45 ~1 | 一致（~1 归源见 C1） |
| `flutter analyze --no-pub lib/core/design/pixel test/core/design/pixel` | No issues found (4.0s) | 同 | 一致 |
| `check_ui_design_tokens_ratchet.py` | PASS color=225/275, fontSize=634/727 (184 files) | 同 | 逐字一致 |
| `check_spacing_rhythm_ratchet.py` | PASS spacingHalfStep=1591/1623 (321 files) | 同 | 逐字一致 |
| `check_dl_spec_ratchet.py` | PASS 15 dims（coldColorLiteral=87/90 等） | 同 | 一致 |
| `check_typography_rhythm_ratchet.py` | PASS sub12=232/234, w900=6/6 | 同 | 一致 |
| 证据 sha256（3 PNG + 3 semantics.txt） | `shasum -a 256` 与 manifest artifacts 六条全等 | 同 | 一致 |
| 语义 dump 节点数 | 87 行/档 ×3（字节恒等） | 87 节点/档 | 一致 |
| toolchain | Flutter 3.41.3 stable rev 48c32af034 / darwin 25.6.0 arm64 | 同 | 一致 |

### 1.7 NOT_RUN 如实性

| # | 项 | 审查判断 | 结果 |
|---|---|---|---|
| 16 | 真机 DPR 呈现 / 60Hz 帧统计 | 如实：本机无真机/模拟器（device_scope 明记）；tester.view 五档注入覆盖的是**几何/布局/文本契约**而非物理屏抗锯齿——limitations §1 明确「物理屏字形渲染未测不得声称」，与 DESIGN_SYSTEM「frame 统计在 profile/release 测」口径一致 | **CONFIRMED** |
| 17 | tester 字体 Ahem 方块 | 如实：亲阅 `pixel_story_paperDay.png`——中文均呈方块、轮廓/阶梯角/状态形状/色板/布局清晰可辨；limitations §2 声明「截图有效面 = 轮廓/色板/状态形状/布局」，中文真实字形归设备面，语义树 dump 不受影响（真实中文 label）。无以方块截图冒充字形验证 | **CONFIRMED** |
| 18 | sparkle-coordination-v2 租约 NOT_RUN | 如实：`git remote -v` 仅 `origin`（GitHub Sparkle-project），无该私有远端；以 diff 自证冲突面（§1.1 #1 本审独立复核同结论），并留「有远端配置的会话补登」交接 | **CONFIRMED** |

## 2. 预登记挑战点逐判（实现方 limitations.md「审查挑战点预登记」）

- **① DPR「轮廓稳定」口径——CONFIRMED（采纳实现方口径，不要求补 golden）**。「顶点物理对齐 + 阶梯步数 DPR 无关 + 逻辑盒恒等」是 DESIGN_SYSTEM.md「stroke 中心与填充边缘各自对齐物理像素；布局保持逻辑 dp 连续，不用 Transform」的忠实机器化，且比逐像素 golden 更强（不变量跨宿主稳定）；卡面「主要轮廓稳定」由三不变量联合覆盖、「文字不点阵化」由系统字体路径四断言（逻辑 fontSize/文本盒恒等、无 RawImage、无 Transform 祖先）覆盖。golden 跨宿主字体/抗锯齿不稳的拒绝理由成立（Ahem 环境 + 无 CJK，golden 只会钉住方块）；若将来补 golden 应只在真机面——同意该建议。注：dpr=1 档物理网格与逻辑网格重合，对「去吸附」变异天然不敏感（本审实测 1.25/3.0 均红），判别力由非整数档承担，属口径固有性质非缺陷（N3）。
- **② 非成功态动效维=静态——CONFIRMED（口径一致，实现方未擅改也未越口径）**。DESIGN_SYSTEM.md 只禁「错误、撤回和未知不能用庆祝视觉」+ 要求「相同状态同语义」，未要求非成功态各配微动效；卡面「均有区分且无成功动效」的「区分」由令牌/字形/轮廓三维承担且本审变异实证互异断言有效。「静态是特性」读法与合同原文一致；「若裁决需要微动效应先改 DESIGN_SYSTEM.md 再改码」的顺序声明正确。
- **③ 控制组有效性——CONFIRMED**。三控制组齐全且方向正确：吞手势层必吞（taps=0）、成功树必命中（findsNWidgets(2) 计数钉死）、空回调必无 tap（=0）。本审以 cancelled→celebrates 变异实证反例面 5 用例齐红——控制组本身不被实现变化误伤的担忧不成立（计数钉死是**有意的**漂移哨兵，注释言明）。判别力证明充分，非测试自证。
- **④ CTA 锁存窗——CONFIRMED**（§1.5 #14/15）。行为边界清楚、fail-closed、「可取消升级」登记合理。
- 附：limitations.md 预登记 #4（`PixelOutlinePainter.paint()` 读 `platformDispatcher.views.first.devicePixelRatio`，多视图下 first 未必本视图）——代码与登记一致，当前 App 单视图无影响，留待多视图卡处理，可接受（N4）。

## 3. CHALLENGED（1 项，非阻断）+ 注记（3 项）

- **C1｜「~1」归源措辞不准**：run_manifest.json #8 称「~1 为既有 tearDownAll 挂起残记」。本核查证：flutter test 输出中 `~` = **skip 计数**，该 ~1 实为 `test/widget_test.dart:69` 的 `skip: true` 既有用例（main 基线同款，不在本卡 diff）；`(tearDownAll)` 只是 runner 的套件收尾阶段行名。材料事实（既有残记、与基线同口径、非本卡引入）正确，仅归源命名不准。后续 evidence 引用请写「~1 = test/widget_test.dart 既有 skip 用例」。不影响任何验收结论。
- **N1（F01 C2 关联核验）**：F01 一审 C2（initialize 越界守卫直接用例）在本卡 diff 中未见补测——该债归 F01 台账不在本卡范围，仅提示集成复验时勿误记为本卡责任。
- **N2（classic 零差量守护范围注记，沿 F01 N1 体例）**：F02 的 classic 降级断言（radius 22/18、stairSteps=0、无渗漏）守护的是**组件降级路径行为**；22/18 常量写在新码内，断言对「常量自身选错」不敏感（self-referential）。发布面零差量由结构性事实背书：组件零调用点 + diff 零触碰既有文件（theme 通道 41 槽断言未被本卡触碰）。后续页面家族替换卡接入组件时，零差量主张须随调用点重新举证，不得沿用本卡组件级断言。
- **N3（dpr=1 档判别力注记）**：见预登记①判——五档判别力由 1.25/1.5/3 非整数档承担，dpr=1 档对吸附变异天然钝感，属口径固有，无需行动。
- **N4（故事页聚合注记）**：故事页同视口含 2 个 `PixelPrimaryAction`（成功对照「再来一次」+ 透传演示）——preview 聚合面非产品页面，「单视口最多一个强主 CTA」合同约束产品组合；后续页面家族卡不得以故事页为布局先例。

## 4. 裁决与后续

- **V4-F02 判 PASS**：一审通过，允许按舰队流程进入集成 SHA 复验；`review_receipt.json` 维持 PENDING 不由本审改写（本 receipt 即一审记录）。
- 合并前无附加条件；C1/N1–N4 随本 receipt 在案，不阻塞任何卡面验收项。
- 集成复验提醒：集成 SHA 上重跑 §1.6 全表（新套件 + design 160 + analyze + 四守卫，约 1 分钟）+ §1.1 红线 grep 即可覆盖全部机器可验面；真机 DPR 呈现/帧统计/Ahem 字形补偿面按 NOT_RUN 台账留给设备面卡。

—— wtF02R1，2026-09-28（本文件即独立审查凭证；审查会话未参与 89f66c13 实现）
