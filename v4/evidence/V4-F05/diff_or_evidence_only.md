# V4-F05 — diff_or_evidence_only

## 结论一句话

`mobile/lib/core/design/style_preview/` 新增三文件：`StylePreviewPage`（真实 Flutter 内部预览页：四档切换器经 F01 唯一编程入口 `ThemeManager.setPixelPreviewProfile` live 换装 + 「同一状态流」四步封闭流控制器 + 五面画廊）、`style_preview_faces.dart`（首页/卡住 sheet/记忆/长回答/星图五面 = **真实表面组件 + 冻结 seed**，非重绘非 HTML 移植）、`style_preview_seed.dart`（确定性 seed + F03 冻结文案表驱动的流步投影）；入口为「我的」页 flag 门控开发者入口（`AppFeatureFlags.enableStylePreview` **默认 false**——preview 不隐性全量上线），五 Tab 路由合同、F01 主题通道、F03 适配器、RF-06 冲突面零触碰。三条卡验收 13 个可失败测试（每面一正一反）+ 证据采集 27 用例钉死：`flutter test test/core/design/style_preview/` 40/40、`test/core/design/` 200/200、导航域 + U-07 契约钉 42/42 全绿；`flutter analyze` 本卡零 issue（全仓仅剩 1 条 F03 遗留 info，干净基线复跑同现）；六条守卫（UI-TOKENS/SPACING/TYPO/DL-SPEC/I18N/N18）全 PASS。UI 证据 = 五面 × 4 档（classic + paperDay/dusk/quiet）+ 整页 × 4 档 + 卡住 sheet 顶层 × 4 档共 28 张截图与语义 dump（同 worktree/同 build/同 seed `seed-2026-09-28-v1`；单面语义 dump 跨四档 sha256 恒等——切主题不改语义结构的机检自证）。

## 差量明细（相对 base 8458d3c7 = 开卡时 main HEAD）

产品码（3 新增 + 2 修改，共约 870 行；`app/routes.dart`、`design_system.dart`、`theme_manager.dart`、`tokens_v2/`、`core/experience/` 零触碰）：

- `mobile/lib/core/design/style_preview/style_preview_seed.dart`（新，约 210 行）—
  `kStylePreviewSeedVersion='seed-2026-09-28-v1'` + `StylePreviewFlowStep`
  四步封闭流（文案逐字取 F03 冻结表 `kExperienceCopyTable` 既有键：
  `state.syncing`/`task.committed`/`memory.saved`/`err.version_conflict`）
  + `StylePreviewFlowFrame`（呈现投影：success 仅 committed、memory 仅
  高亮、conflict 失败族——F03 分层路由的消费面而非复制品）+ 五面冻结
  seed（卡住干预 map、记忆证据、长回答 markdown、星图节点）。
- `mobile/lib/core/design/style_preview/style_preview_faces.dart`（新，约 400 行）—
  五面真实组件装配：首页 = 真实 `TodayCockpitCard`（`todayCockpitProvider`
  钉 seed VM，按流步 ValueKey 重挂）；卡住 sheet = 真实 `TaskStuckCard`
  内嵌 + 真实 `showModalBottomSheet` 打开入口（sheet 形态本体）；
  记忆 = 真实 `MemoryEvidenceBadge` + `EvidenceQuickPeek`；长回答 = 真实
  `SparkleMarkdown`（聊天气泡同款内容渲染器）；星图 = 真实
  `TiledSectorBackground` + `GalaxyNodePreviewCard`。零颜色/字号字面量
  （全走 `context.sparkle`/Theme 管道）。
- `mobile/lib/core/design/style_preview/style_preview_page.dart`（新，约 260 行）—
  `StylePreviewPage`（AppBar 提案常显「PROPOSED · 未批准」+ SegmentedButton
  四档切换器 + 状态流推进器 + 五面卡；AnimatedBuilder(ThemeManager) 与
  app.dart 根部 themeManagerProvider 同机制 live re-theme）+
  `StylePreviewEntry`（gate：flag 关 → `SizedBox.shrink` 零节点，flag 开 →
  开发者入口 tile；独立组件以便反例测试直接钉 gate 行为）。
- `mobile/lib/core/constants/app_constants.dart`（改，+5 行）—
  `enableStylePreview = false`（默认关；批准转正时随决策改开）。
- `mobile/lib/features/user/presentation/screens/profile_screen.dart`
  （改，+5 行）— 设置区尾部消费 `const StylePreviewEntry()`（卡面红线
  「preview 入口可加设置页/开发者入口」的落点；flag 关时发布面零节点零
  差量）。

测试（新增 `mobile/test/core/design/style_preview/` 5 文件，40 用例）：

- `style_preview_test_harness.dart` — 公共泵制（AnimatedBuilder(ThemeManager)
  → MaterialApp(AppThemes.lightTheme) 真实主题管道；`settlePreview` 固定
  时长泵——preview 面 runActive 步含真实骨架 shimmer 无限动画，
  pumpAndSettle 永不落定，产品真实行为，非测试绕行）；State 探针
  （重挂计数）。
- `style_preview_switching_test.dart`（10）— 验收 1 + 验收 2 + 切换状态
  全生命周期：classic_gate 组（flag 默认关反例 / flag 开进页正例 /
  classic 稳定主题可用）+ switching 组（四档 live 切换 / 回退 classic
  逐槽复原反例 / State 探针跨档存活 / 外源 prefs 零触碰 / 持久化复原 /
  纯本地无第二写入面）。
- `style_preview_faces_test.dart`（3）— 验收 3 机制面：五面真实组件 +
  seed 断言；真实 bottomSheet 开/关；同一状态流四步推进（success 徽章
  仅 committed 步反例 + memory 高亮不拿成功面孔反例 + 重放幂等）。
- `style_preview_evidence_test.dart`（27）— 证据采集（env 门控落盘）：
  整页 × 4 档 + 单面 × 5 面 × 4 档 + sheet 顶层 × 4 档。

## 验收逐条落（卡面原文 → 证据）

1. **「设计未批准时稳定主题仍可用，preview不隐性全量上线」** — 入口 flag
   默认 false（反例测试钉 gate 零节点）；页面在 classic 下正常渲染且无
   `PixelProfileTheme` 扩展（稳定主题路径零差量）；页头「PROPOSED · 未
   批准」常显（不冒充已定版）；TOKENS.proposal.json status 未被改写。
2. **「切主题不重启run/清数据/改token用量」** — 切档只经 F01 唯一编程
   入口（仅 pixel 通道键 + notifyListeners）；State 探针 + 页面流步跨三
   档存活（重挂即红）；外源 prefs 键（模拟用量/账号面）零触碰；回退
   classic 后色板/亮度/colorScheme 逐槽 = 干净基线且像素扩展卸载；
   切档路径无第二持久化面、无网络残留。
3. **「五面状态截图附相同build与数据seed」** — 28 张截图全部出自同一
   worktree（flutter 3.41.3 stable @ base 8458d3c7）、同一冻结 seed
   （`seed-2026-09-28-v1`）、同一组面构建器（页内同源）；面 canonical
   流步映射与逐文件 sha256 见 run_manifest.json。

## 红线自证（diff 逐面）

- 五 Tab 路由合同：`git diff 8458d3c7 -- mobile/lib/app/routes.dart` 为空；
  U-07 五 Tab 铁律钉（计数恒 5）通过；preview 入口在「我的」页设置区，
  不新增导航目的地。
- RF-06 冲突面（dashboard_screen/compact_status_bar/task_execution_screen）：
  diff 不含其任何文件；features/ 仅 profile_screen.dart +5 行入口消费。
- classic 零差量（F01）：theme 通道（design_system.dart/theme_manager.dart/
  tokens_v2/）零触碰；默认 flag 关 → 发布面零节点；classic 档测试断言
  无像素扩展挂载。
- F03 适配器（CH-4）：`core/experience/` 零触碰，只读 import 冻结文案表；
  preview 面零事件流订阅、零网络调用、零新增投递路径（CH-4 守门声明见
  run_manifest.json）。
- 不碰 .env/proto/迁移：diff 无此类文件。
