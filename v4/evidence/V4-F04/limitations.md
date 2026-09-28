# V4-F04 — limitations

## 范围与边界

1. **槽位升级只动一档**：宽度 ≥1200（含 1280×720 桌面窗口）从手机底栏升级
   为常驻侧栏；360/800×600/平板档槽位与升级前一致（测试钉死）。1280×720
   上的可见性提升来自该升级——审查时勿把「1280 底栏消失」当回归。
2. **无真机/模拟器运行**：全部为 widget-test 泵证据（卡面 risk normal 无
   heavy 要求）；截图为 Ahem 测试字体块（真实文案在语义 txt）；触觉/音效
   仅保留调用时语义，未做感官实测（V4_DONE 边界照抄）。
3. **语义 dump 口径变更**：F02 采集器用的 `semanticsOwner.rootSemanticsNode`
   在本机 Flutter 3.41.3 widget-test 泵内恒为 null（F02 同口径复跑亦然），
   F04 改元素树口径（RenderSemanticsAnnotations + RenderParagraph），
   label/value/isButton/rect 字段覆盖等价；口径差异已注记在采集器头注释。
4. **Desktop 侧栏为 extended rail，非自绘 sidebar**：替换的是旧
   NavigationDrawer 内嵌误用（组件语义纠正）；品牌头/宽度权威保留。与
   参考图的桌面形态（若有）不做像素级对照——参考图是提案不是验收源。
5. **键盘布局 = 显式钉契约 + 测试举证，非行为改写**：Scaffold
   `resizeToAvoidBottomInset: true` 与 Flutter 默认一致（classic 行为零
   差量）；「替换键盘布局」按 no_duplicate_rule 以差量举证落（键盘 inset
   消费契约反例钉死），未引入键盘时隐藏底栏之类的新行为。
6. **U-07 契约钉匹配器更新**：`NavigationDestination(` → `ShellDestination(`
   （计数恒 5）。铁律本体未动；这是实现细节匹配器随授权内重构的必然同步，
   不是放宽。审查者可对照 diff 确认原匹配器在新源码上恒 0（组件化后构造点
   迁至 shell_nav_surfaces.dart）。

## 已知限制

- **像素装饰沿仅底栏有**：rail/桌面侧栏未加像素装饰（preview 档下侧栏
  视觉 = 既有 Material3 rail + 像素色板）。Shell 像素面刻意最小化以守住
  classic 零差量构造性；后续页面家族卡若要侧栏像素化，须按 N2 体例随
  调用点重新举证。
- **测试镜像路由非真 routes.dart**：deep-link/Back 证据用五分支镜像路由
  （真实 route ID + 真实嵌套形态 /plans/:id），app/routes.dart 本体在测试
  进程内不可用（auth/splash redirect 链依赖网络桩面）；routes.dart 零触碰
  由 diff 自证，两者合并构成完整证据。
- **`tester.view.viewInsets` 键盘注入是测试代理**，非系统键盘真机行为；
  真机键盘（iOS keyboard inset/toolbar）未验证。
- **l10n 无新键**：语义独立通过既有 label 同源字符串落（semanticsLabel =
  label 当前同源）；「语义名与视觉名分叉」的真实场景（如语音朗读名 ≠ 视觉
  名）留待后续卡需要时引入新 l10n 键。

## 审查挑战点预登记（给独立审查）

- **C1（候选）**：`resolveShellNavSlot` 宽度主导后，物理上不存在的形态
  （如 1200×400 超宽条带）会得 sideNav——宽度主导是有意裁决（桌面窗口
  优先），极端纵横比未做第四档；如需 shortestSide 下限闸，请挑战并给形态。
- **C2（候选）**：桌面档 `NavigationRail.extended` 的 `minExtendedWidth =
  sidebarWidth` 与外层 `SizedBox(width: sidebarWidth)` 同源同值——若未来
  sidebarWidth 响应式分档（wide=360）两边是否恒等？现取同函数同调用点，
  恒等成立；分叉时测试 `shell_responsive_layout_test` 的 1280 档会先红。
- **C3（候选）**：`ShellNavBadgeIcon` 角标色从 `DS.semanticError`（单例读）
  改为 `Theme.of(context).colorScheme.error`——生产路径两者同源同值
  （AppThemes 将 colors.semanticError 原样写入 colorScheme.error，见
  design_system.dart `_buildThemeData`），测试泵内后者可判定性更好；如
  主张存在 ThemeManager 单例与挂载 theme 失联的产线场景，请挑战并给复现。
- **C4（候选）**：语义 dump 元素树口径 vs F02 的 SemanticsNode 口径——
  本机 rootSemanticsNode 恒 null 的断言可由审查者以 F02 采集器复跑验证
  （证据包同口径文件 F02 pixel_story_*_semantics.txt 本机复跑也会得
  「(无语义根)」）；若审查环境可产出真根，请以该口径重出 F04 dump 对照。
