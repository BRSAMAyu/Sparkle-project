# V4-F04 — diff_or_evidence_only

## 结论一句话

`mobile/lib/core/navigation/shell/` 新增 Shell 组件族（导航槽位解析 `resolveShellNavSlot` / 图标语义独立的目的地模型 `ShellDestination` / 三档共享呈现件：角标图标 + 像素档装饰沿 + 底栏）并把 `ResponsiveScaffold` 重构为宽度档三档呈现（手机底栏 / 平板 rail / 桌面常驻侧栏=extended rail 替换旧 NavigationDrawer 内嵌误用）；五 Tab 路由合同（`app/routes.dart`）与 RF-06 冲突面零触碰，classic（preview off）零差量由调用点断言重新举证（F02 N2 注记落实）。三验收面 + classic 零差量面共 29 个可失败测试（每面一正一反）钉死：`flutter test test/core/navigation/` 36/36、`test/core/design/` 160/160、shell 触达契约钉 17/17 全绿；`flutter analyze` 零 issue；四条设计棘轮守卫（UI-TOKENS/SPACING/TYPO/DL-SPEC）全 PASS。UI 证据 = 三验收尺寸 + 像素 preview 档四张顶页截图与语义 dump（`shell_evidence_test.dart` 按需落盘，Ahem 测试字体块 + 语义 txt 承载真实文案）。

## 差量明细（相对 base 71553984 = 开卡时 main HEAD）

产品码（2 改 + 4 新增，全部 Shell 层；`app/routes.dart`、`design_system.dart`、`theme_manager.dart`、`pixel/` 族零触碰）：

- `mobile/lib/core/navigation/shell/shell_nav_slot.dart`（新，48 行）—
  `ShellNavSlot{bottomBar,sideRail,sideNav}` + 纯函数 `resolveShellNavSlot(Size)`。
  断点唯一权威 = `LayoutBreakpoints`（768/1200，不造第二权威）。与旧
  `ResponsiveSystem.categorizeSize`（shortestSide 主导）的唯一行为差：
  width ≥ 1200 一律桌面侧栏——旧分类把 1280×720 桌面窗口（shortestSide
  720 < 768）停在手机底栏，桌面档形同虚设。360×800 与 800×600 档位不变；
  横屏手机保持底栏（与 `ResponsiveSystem.resolve` 同口径）。
- `mobile/lib/core/navigation/shell/shell_destination.dart`（新，46 行）—
  目的地语义数据模型：`semanticsLabel` 显式携带（图标语义独立——可访问
  名称不派生自字形/码点），`badgeCount/badgeSemanticsLabel/badgeOverflowLabel`
  角标三件。三档呈现面消费同一模型（组件化升级面）。
- `mobile/lib/core/navigation/shell/shell_nav_surfaces.dart`（新，194 行）—
  `ShellNavBadgeIcon`（自 shell_navigation 原样迁出的角标图标，三档共用）、
  `PixelShellTopEdge`（像素 preview 档底栏顶部 2dp 装饰沿：`PixelProfileTheme.of
  == null` 渲染 `SizedBox.shrink`，classic 零装饰节点构造性成立；复用 F02
  `snapLengthToPhysical` 物理对齐，IgnorePointer+ExcludeSemantics 与
  PixelFrame 同制）、`ShellBottomBar`（NavigationBar + 装饰沿；tooltip 取
  显式 semanticsLabel）。依赖面只 import design 叶子文件，零 import 环。
- `mobile/lib/core/navigation/shell/shell.dart`（新，barrel）。
- `mobile/lib/core/design/responsive_widgets.dart`（改）— `ResponsiveScaffold`
  三档重构：`resolveShellNavSlot` 驱动；底栏档 `ShellBottomBar`；平板档
  `NavigationRail(labelType: all)` + `SafeArea`（无 inset 时零填充）；
  桌面档 `extended: true` NavigationRail + 品牌头 + `ResponsiveSpacing.sidebarWidth`
  （既有宽度权威），替换旧「NavigationDrawer 内嵌定宽 SizedBox」的组件
  语义误用；三档 Scaffold 显式 `resizeToAvoidBottomInset: true`（键盘合同
  可 grep 锚点）。`destinations` 参数类型 `List<NavigationDestination>` →
  `List<ShellDestination>`（唯一调用方 = shell_navigation，已同步）。
- `mobile/lib/core/navigation/shell_navigation.dart`（改）— 目的地构造改
  `ShellDestination` 模型（l10n 同源；社群角标三件迁移）；`_buildBadgedIcon`
  迁至共享件；`design_system.dart` 伞 import 改直连 import（DS 唯一使用点
  已随角标迁出）。badge「进入即清」、成就/社群事件监听、PrimaryScrollController
  等行为面逐行保留。

测试（新增 `mobile/test/core/navigation/shell/` 7 文件，29 用例，每验收面一正一反）：

- `shell_nav_slot_test.dart`（11）— 三验收尺寸 + 真实形态 + 断点边界反例
  （1199/767 差 1px 必红；1200×600 宽度主导）。
- `shell_responsive_layout_test.dart`（4）— 验收面 2：360/800×600/1280×720
  下五主操作目的地可见可点、错误探针（ERROR_PROBE）在视口内；反例钉
  800×600 不得误升 rail、1280×720 不得停留底栏、平板档不因升级回退。
- `shell_deep_link_back_test.dart`（3）— 验收面 1：旧深链 `/plans/plan-42`
  （镜像 PlanRoutes.shellRoutes 的嵌套子路由）直达同一对象；切 Tab 往返
  分支栈保留（反例：重置即红）；push 入栈后系统返回（popRoute）弹回分支
  根、再深链幂等直达。
- `shell_accessibility_test.dart`（3）— 验收面 3：文本 200% 无越界异常且
  五目的地+错误探针可见；键盘 286dp inset 下置底输入框停在键盘上方
  （反例钉死 inset 消费链回退即红（F04 一审 N1 勘误：外层单点回退不红，双点才红））、底栏不越界；
  分支根 popRoute 不被 shell 误吞。
- `shell_classic_zero_delta_test.dart`（4）— classic 调用点举证（F02 N2）：
  装饰沿 classic 渲染 shrink 零 CustomPaint、全壳无像素绘制层渗漏、底栏
  结构 = 单一 NavigationBar 五目的地且 tooltip/label 同源 l10n；反例对照 =
  pixel preview 档装饰沿必现（证明 classic 断言非恒真）；装饰沿
  IgnorePointer 命中穿透 + 语义树完好。
- `shell_evidence_test.dart`（4）— 证据采集（常规跑只断言真实渲染，设
  `SHELL_EVIDENCE_DIR` 才落盘）：三验收尺寸 + 像素档顶页截图与语义 dump。
- `shell_test_harness.dart` — 公共泵制（真 shell + 五分支路由镜像真实
  route ID；网络面死桩）。

既有测试（1 改）：

- `mobile/test/widget/nav_decontextualization_contract_test.dart` — U-07
  「五 Tab 铁律」源码钉的匹配器从 `NavigationDestination(`（呈现组件构造）
  改为 `ShellDestination(`（语义模型构造），计数恒 5、铁律本体不变；
  原匹配器在新组件化口径下恒 0，属实现细节匹配器随重构更新（卡面授权：
  「替换导航视觉…组件化升级」），非验收阈值放宽。

## 验收逐条落（卡面原文 → 证据）

1. **「全部旧深链能到同一对象、Back 不丢上下文」** — `app/routes.dart` 零
   触碰（diff 无路由文件）；StatefulShellRoute.indexedStack 分支栈语义由
   `shell_deep_link_back_test.dart` 3 用例钉死（深链直达同一占位对象、
   切 Tab 往返上下文保留、系统返回弹回分支根后深链幂等）。
2. **「360宽/800×600/1280×720下主操作和错误可见」** — `shell_nav_slot_test`
   11 用例钉槽位映射 + `shell_responsive_layout_test` 4 用例钉三尺寸下五
   目的地可见可点、错误探针在视口内；1280×720 升级为桌面常驻侧栏（卡面
   「桌面侧栏」替换点）；截图 + 语义 dump 见本目录。
3. **「系统返回、文本200%、键盘打开不越界」** — `shell_accessibility_test`
   3 用例：200% 文本零越界异常、键盘 inset 被消费（置底输入框恒在键盘
   上方，契约回退即红）、分支根系统返回不误吞。

## 红线自证（diff 逐面）

- 五 Tab 路由合同：`git diff 71553984 -- mobile/lib/app/routes.dart` 为空；
  U-07 五 Tab 铁律钉（计数 5）通过。
- RF-06 组员冲突面（dashboard_screen / compact_status_bar / task_execution_screen）：
  diff 不含 features/ 任何文件。
- classic 零差量（F01）：theme 通道（design_system.dart / theme_manager.dart /
  tokens_v2/）零触碰；像素只经 `PixelShellTopEdge` 装饰沿进入 Shell 且
  classic 渲染 shrink——调用点断言见 `shell_classic_zero_delta_test.dart`
  （N2 注记「随调用点重新举证」落实）。底栏本体在 classic 下与升级前同为
  单一 NavigationBar（五目的地、同 l10n 标签、同角标视觉参数）。
- 已知授权内 classic 可见差量（卡面「替换导航视觉/桌面侧栏」本体，非像素
  通道）：width ≥ 1200 的窗口从底栏变常驻侧栏；平板/桌面档新增 SafeArea
  （无 inset 设备零填充）与角标可见性对齐（原仅底栏有角标）。
