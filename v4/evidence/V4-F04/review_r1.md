# V4-F04 独立审查 receipt（R1）

- 审查会话：wtF04R1（未参与 F04 实现）· 2026-09-28
- 审查对象：分支 `agent/v4/f04` @ `202fc67b`（基线 `71553984` = 开卡时 main HEAD；
  分支形态 = 基线 + 恰 1 个 feat 提交；worktree `/Users/brsama/code/GitHub/wtF04`，
  Flutter 3.41.3 stable / darwin arm64，与 run_manifest 一致）
- 审查方式：只读 diff 全量扫描 + 全部产品码/测试文件逐行审 + 亲跑全部复跑项 +
  受控变异 3 轮（U-07 删 Tab / 键盘契约单点 / 键盘契约双点，改后即 `git checkout`
  还原）+ 独立构造 C1/C3 审查用例（跑完即删，工作树零残留，终态 `git status` 干净）
- **总裁决：PASS（一审通过）**——卡面三条验收全部有机器可失败断言背书且关键断言
  经变异实证判别力；五 Tab 路由合同 / 发布主题通道 / RF-06 冲突面 / l10n 四条红线
  零触碰全过；classic 零差量按 F02-N2 体例随调用点重新举证成立。CHALLENGED 1 项
  （措辞级，非阻断）+ 注记 3 项。合并后照常走集成 SHA 复验。

## 1. 逐项核验记录（本审实跑命令与结果）

### 1.1 红线核验（最重）

| # | 声称 | 审核查证（命令/方法/结果） | 结果 |
|---|---|---|---|
| 1 | 五 Tab 路由合同零触碰 | `git diff 71553984 202fc67b -- mobile/lib/app/routes.dart` = **0 行**；全量 diff 28 文件逐一过目：产品码仅 shell 族 4 新增 + responsive_widgets/shell_navigation 2 改，无任何路由文件 | **CONFIRMED** |
| 2 | RF-06 冲突面零触碰 | 全量 diff `grep`：`features/` 零命中；dashboard_screen / compact_status_bar / task_execution_screen 零命中 | **CONFIRMED** |
| 3 | theme 通道零触碰 | `git diff … -- mobile/lib/core/design/design_system.dart mobile/lib/core/design/theme_manager.dart mobile/lib/core/design/tokens_v2/ mobile/lib/core/design/pixel/ mobile/lib/l10n/` = **0 行**；l10n 零新键（diff 无 l10n 文件，语义独立经既有 label 同源字符串落） | **CONFIRMED** |
| 4 | 产物 sha256 | 8 个 PNG/semantics 逐一 `shasum -a 256` 与 run_manifest **全吻合** | **CONFIRMED** |
| 5 | 锁租约 | sparkle-coordination-v2 远端本机未配置（`git remote` 核实），租约 NOT_RUN 如实登记；冲突面以 diff 自证（上两条）替代 | **CONFIRMED**（与卡标准允许的替代证法一致） |

### 1.2 审查靶 1：五 Tab 铁律（冻结点）

| # | 项 | 审查判断 | 结果 |
|---|---|---|---|
| 6 | 匹配器更新非放宽 | 旧匹配器 `NavigationDestination(` 在新 shell_navigation.dart **恒 0**（实测计数 0；构造点已迁 shell_nav_surfaces.dart:174 唯一一处 1:1 映射）——保留旧匹配器只会对一切形态恒红，更新是必然同步而非放宽。新匹配器 `ShellDestination(` 实测 = **恰 5** | **CONFIRMED** |
| 7 | 新匹配器牙齿（变异实测） | 删除第 5 个 ShellDestination 构造 4 Tab 形态 → `nav_decontextualization_contract_test` **红**（`Actual: <4>`，「五 Tab 铁律：底部目的地数量不得增减」）；`git checkout` 还原后全绿。4/5/6 Tab 均不可逃逸 | **CONFIRMED** |
| 8 | 铁律本体未动 | diff 仅换匹配器字符串 + 3 行注释；`expect(count, 5)` 原样 | **CONFIRMED** |

### 1.3 审查靶 2：三档布局与断点权威

| # | 项 | 审查判断 | 结果 |
|---|---|---|---|
| 9 | 断点唯一权威 | shell_nav_slot.dart 只 import `design/breakpoints.dart` 的 LayoutBreakpoints（768/1200），零新常量；宽窄语义与注释一致 | **CONFIRMED** |
| 10 | 槽位 11 测抽 3 档边界亲跑 | `flutter test test/core/navigation/shell/` 亲跑 **+29 全绿**（含 nav_slot 11：360×800/800×600/1280×720 三验收尺寸 + 768×1024/1024×768/1440×900/1920×1080/844×390 真实形态 + 1199×800/767×1024 差 1px 反例 + 1200×600 宽度主导） | **CONFIRMED** |
| 11 | 1280 档升级非回归 | 升级前旧分类 1280×720（shortestSide 720<768）停底栏（base `_buildMobileLayout` 实读证实）；新宽度主导升常驻侧栏 = 卡面「桌面侧栏」授权本体；responsive_layout_test 反例钉「800×600 不误升 rail」「1280 不停留底栏」「平板不回退」 | **CONFIRMED** |

### 1.4 审查靶 3：classic 零差量调用点举证（F02-N2）

| # | 项 | 审查判断 | 结果 |
|---|---|---|---|
| 12 | 4 测真实性 | shell_classic_zero_delta_test 逐行审 + 亲跑通过：(a) classic 装饰沿子树零 CustomPaint 且 Size.zero；(b) 全壳 classic 无 `_PixelEdgePainter`、底栏 = 单一 NavigationBar 五目的地、label/tooltip 同源 l10n（zh 表实测）；(c) pixel preview 档装饰沿必现（classic 断言非恒真的对照面）；(d) 装饰沿 tapAt 命中穿透 + 语义树完好 | **CONFIRMED** |
| 13 | 像素只经装饰沿进入 Shell | 生产 shell 族 grep：pixel import 仅 shell_nav_surfaces.dart 的 pixel_geometry/pixel_preview_theme（均只被 PixelShellTopEdge 消费）；responsive_widgets/shell_navigation/shell_destination 零 pixel 依赖；classic 路径 `PixelProfileTheme.of == null → SizedBox.shrink` 构造性成立 | **CONFIRMED** |
| 14 | classic 与升级前底栏逐位 | base `_buildMobileLayout` = 裸 NavigationBar；新 ShellBottomBar classic = 同一 NavigationBar（+零尺寸 shrink）， selectedIndex/onDestinationSelected/五目的地/角标视觉参数逐位保留（_buildBadgedIcon 原样迁出比对） | **CONFIRMED** |
| 15 | pixel 语义 dump 与 classic 字节恒等 | 两 txt sha256 同为 `c80580dd…` —— 与装饰沿 ExcludeSemantics 零语义一致，构成「像素沿零语义渗漏」旁证（PNG 承载像素差异面） | **CONFIRMED**（正向注记 N2） |

### 1.5 审查靶 4：C3 角标色改道（独立构造断言亲验）

本审构造独立用例（未入库，跑完即删）实测 4 断言全绿：

- classic light/dark：角标 Container decoration color == `Theme.of(context).colorScheme.error`
  == `DS.semanticError` == `ThemeManager().themeForBrightness(…).colors.semanticError`
  ——四方 `.value` 逐位相等；
- 像素 preview 档（paperDay）：`AppThemes.lightTheme.colorScheme.error` 槽**仍** =
  semanticError（`_buildThemeData` design_system.dart:128 `error: colors.semanticError`
  无条件映射；pixelAccentInk 只改 onPrimary/onSecondary/onError，不改 error 本体）；
- 生产同源判定：`DS.semanticError` getter（design_system.dart:632）与色槽构建读同一
  `ThemeManager` 单例解析的同一 `colors` 对象——同源同值成立；改道为 context 读，
  测试泵可判定性更好，非行为改写。

**C3 判决：ACCEPT（同源改道成立，生产逐位一致亲验通过）。**
「ThemeManager 单例与挂载 theme 失联」场景：MaterialApp theme 即 AppThemes（同一
单例解析），无第二主题源；shell 子树无局部 Theme 覆写，未发现失联复现路径。

### 1.6 审查靶 5：深链 + Back 契约（3 测语义）

- 深链 `/plans/plan-42`（镜像 PlanRoutes 嵌套形态）直达同一占位对象、非错误页；
- 切 Tab 往返后仍在嵌套对象上（反例：分支栈被重置即红）；
- `routerDelegate.popRoute()`（系统返回同路）弹嵌套页回分支根，再深链幂等直达；
  accessibility 面补「分支根 popRoute 返回 false 不被误吞」。
- 档位无关性：goBranch/StatefulShellRoute.indexedStack 与呈现档正交；三测在 360 底栏
  档钉语义，responsive 测试另证 768/1280 档切 Tab 可达（注记 N3）。
- `app/routes.dart` 本体测试进程内不可用（auth/splash 网络桩链）已在 limitations
  如实登记，路由零触碰由 diff 自证，两者合并构成证据。

**判决：CONFIRMED。**

### 1.7 审查靶 6：200% 字阶 + 键盘 + 系统返回（no_duplicate_rule 差量举证真实性）

- 200%：亲跑通过（零越界异常、五目的地、探针可见）；
- 键盘：`resizeToAvoidBottomInset: true` 三档显式 = 可 grep 契约锚点，与 Flutter
  默认一致（行为零差量，no_duplicate_rule「差量举证不重写」属实——base 代码未显式
  写该参数）；键盘测试断言置底输入框 bottom ≤ 800−286；
- **变异实测**：外层锚点单点回退 false → **不红**（嵌套分支 Scaffold 默认仍消费
  inset）；外层+内容面双点回退 → **红**（`Expected ≤514.5, Actual 720`）。验收行为
  「键盘打开不越界」在系统级被真实钉死；但 diff_or_evidence_only.md:57 与
  shell_accessibility_test.dart 头注「`resizeToAvoidBottomInset` 契约回退即红」的
  单点归因过强——见 CHALLENGED-N1。
- 系统返回：分支根 popRoute 交还系统，亲跑通过。

### 1.8 审查靶 7：C4 语义 dump 口径（独立复核）

- 本审以证据包内 F02 采集器（pixel_story_evidence_test.dart）本机复跑：
  `PIXEL_STORY_EVIDENCE_DIR=/tmp/... flutter test …` → 三档
  pixel_story_*_semantics.txt **均得「(无语义根)」**（各 14 字节）——limitations
  「rootSemanticsNode 本机恒 null、F02 同口径复跑亦然」**独立复现成立**；
- F04 元素树口径字段覆盖：RenderSemanticsAnnotations（label/value/isButton/rect）+
  RenderParagraph（文本标签），与 F02 SemanticsNode 口径字段等价（shell 场景无
  缺失字段）；已入库 dump 内容真实：360 档五标签 y≈770（底栏）、1280 档 x=80
  （侧栏）、ERROR_PROBE 恒在视口内，与各档位几何一致；口径变更已注记于采集器
  头注释。

**C4 判决：ACCEPT（口径变更正当、可复现、字段等价）。**
注：已入库的 F02 dump 含真实语义树（产出环境与本机不同），属环境差异如实注记，
不构成 F04 证据缺陷。

### 1.9 审查靶 8：复跑对表（全部本审亲跑）

| 命令（cwd wtF04/mobile 除守卫） | 本审结果 | manifest 声称 | 对表 |
|---|---|---|---|
| `flutter test test/core/navigation/shell/` | **+29 All passed** | 29/29（11+4+3+3+4+4） | 一致 |
| `flutter test test/core/navigation/` | **+36 All passed** | 36/36 | 一致 |
| `flutter test test/core/design/` | **+160 All passed** | 160/160 | 一致 |
| U-07 + achievement_single_channel + unread_message_count_notifier | **+17 All passed** | 17/17 | 一致 |
| `flutter analyze --no-pub` | No issues found (11.1s) | 0 issue | 一致 |
| check_ui_design_tokens_ratchet.py | PASS color=225/275, fontSize=634/727 | 同 | 逐字一致 |
| check_spacing_rhythm_ratchet.py | PASS spacingHalfStep=1591/1623 | 同 | 逐字一致 |
| check_typography_rhythm_ratchet.py | PASS sub12=232/234, w800=0/0, w900=6/6 | 同 | 逐字一致 |
| check_dl_spec_ratchet.py | PASS 15 dims 全降不升 | 同 | 一致 |
| C1/C3 独立审查用例（临时） | +4 All passed | —（本审新增） | 见 1.5/1.10 |

### 1.10 审查靶 2 补：C1 极端纵横比独立构造亲跑

本审构造 1200×400 用例（未入库）：`resolveShellNavSlot(Size(1200,400)) = sideNav`；
壳零布局异常（takeException null）；品牌头 + rail 实测 280×288 装入 400 高视口；
五目的地图标全在树、home 位在视口内、galaxy 位 tap 命中链路完好。
（首跑我方断言误找 `home_outlined`——选中态渲染 filled `Icons.home`，修正后通过；
非实现缺陷。）

**C1 判决：ACCEPT（宽度主导为有意裁决且极端形态功能完好，无需第四档
shortestSide 闸）。** 1200×400 非真实桌面/设备形态；即便出现也得到可用侧栏而非
破损布局，升级前该形态同样停底栏但桌面档形同虚设的问题已被授权修正。

### 1.11 C2 侧栏宽度双写点同源性

`_buildSideNavLayout` 中 `sidebarWidth` 为**单局部变量**（responsive_widgets.dart:112）
同时供 `SizedBox(width:)` 与 `minExtendedWidth:`——同函数同调用点，恒等由构造成立；
宽度权威仍是既有 `ResponsiveSpacing.sidebarWidth`（280/300/320/360 分档未动）。
未来分叉路径：单边改动导致 rail 期望宽 > SizedBox 宽 → 溢出异常 → 1280 档测试
（含 takeException 断言）红。**C2 判决：ACCEPT。**

## 2. C1–C4 逐判汇总

| 项 | 判决 | 一句话依据 |
|---|---|---|
| C1 宽度主导（1200×400 得 sideNav） | **ACCEPT** | 亲跑零异常、五目的地可用；裁决已登记，无需第四档 |
| C2 侧栏宽度双写点 | **ACCEPT** | 单局部变量双消费，同源恒等构造性成立 |
| C3 角标色改道 | **ACCEPT** | 逐位一致亲验（light/dark/preview 三断言）；同源同一 colors 对象 |
| C4 语义 dump 口径 | **ACCEPT** | F02 采集器本机复跑「(无语义根)」独立复现；字段覆盖等价 |

## 3. CHALLENGED 与注记

- **CHALLENGED-N1（措辞级，非阻断）**：diff_or_evidence_only.md:57 与
  shell_accessibility_test.dart 头注的「`resizeToAvoidBottomInset` 契约回退即红」
  归因过强——实测外层锚点单点回退**不红**（嵌套分支 Scaffold 默认仍消费 inset），
  双点（外层+内容面）回退才红。验收行为本身钉死无疑；建议销账时把该句勘误为
  「inset 消费链回退即红」或注明反例粒度为系统级。不要求阻断合并。
- 注记 N2：classic/pixel 360 档语义 dump 字节恒等（sha 同）= 装饰沿零语义旁证。
- 注记 N3：深链/Back 三测在 360 底栏档钉语义；档位无关性由 goBranch 呈现正交 +
  responsive 测试在 768/1280 档的切 Tab 可达共同构成，非独立逐档重钉。
- 注记 N4：U-07 契约钉所在文件其余测试（LABS/leaderboard/计划→日历）零改动通过。

## 4. 结论

V4-F04 五 Tab Shell 与响应式布局升级：**PASS（一审通过）**。卡面三条验收（深链/
Back、三尺寸主操作与错误可见、200%/键盘/系统返回）全部机器断言背书且关键断言
经变异实证；四条红线零触碰；classic 零差量按 N2 体例随调用点举证成立；C1–C4 预
登记挑战全部 ACCEPT。自报完成不算完成——本 receipt 落账后 V4-F04 具备
DONE_REVIEWED 销账条件，合并后照常走集成 SHA 复验。

- 审查人：wtF04R1（独立未参与会话）
- 审查完成时刻：2026-09-28（本机）
- 本 receipt 提交：`docs(v4): F04 一审 receipt`（agent/v4/f04，不 push）
