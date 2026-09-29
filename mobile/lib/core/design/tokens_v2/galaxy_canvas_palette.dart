/// 星图画布身份色板（V4-G04 单一名源收敛）。
///
/// **口径（风格面走查裁决，V4-G04 diff 叙证 §星图 canvas 专项）**：
/// 星图是全风格恒暗的沉浸证据路径（`GalaxyScreen._useDarkGalaxyTheme` 恒
/// true 的既有产品身份：深空底 + 发光节点）。画布绘制面与其浮层 chrome 的
/// 深空海军色阶因此**风格稳定**——classic/paperDay/dusk/quiet 四档下同一
/// 组值，内部对比（节点/边/标签/徽章 vs 画布）逐对由
/// `test/core/design/g04_family_four_style_test.dart` A 组机检钉住
/// （正文标签 ≥4.5:1、图形线/环 ≥3:1）。
///
/// 与 `SectorConfig`（领域数据色板，7 领域 × 深/浅双档）分工：
/// - 本文件只收敛「深空画布身份」色阶（此前散落 11 个文件的 40+ 处匿名
///   `Color(0x…)` 字面量，值逐位保留）；
/// - 领域语义色留在 `sector_config.dart` 既有 owner，不重复收编。
///
/// 落位 `core/design/tokens_v2/`（色值定义归设计层，`pixel_preview_theme`
/// 同判例）：色值定义不落 `features/**`——`check_ui_design_tokens_ratchet`
/// 对 features 新增字面量文件零容忍（只降不升），收敛式新色板在 features/
/// 下无法合法落棘轮；本文件是「画布身份色定义源」而非令牌槽扩展。
///
/// 不进 `DS.*` 语义槽的原因：这些值是「恒暗画布」身份锚而非
/// 风格自适应语义（自适应语义一律走 `DS.*` / `Theme.of`，见各消费点）；
/// 提升为全仓令牌槽属发布面决策（Q08 类），本卡以单一名源 + 机检守卫
/// 替代，登记进 V4-G04 limitations 与预登记挑战。
library;

import 'package:flutter/material.dart';

/// 星图画布身份色板（全部 const，值与收敛前字面量逐位相等）。
abstract final class GalaxyCanvasPalette {
  // ------------------------------------------------------------------
  // 深空画布底（painter backdrop / screen scaffold）
  // ------------------------------------------------------------------

  /// 画布基调（painter backdrop 主色，原 `StarMapPainter._darkBackground`）。
  static const Color canvasBase = Color(0xFF0A0E17);

  /// 画布径向渐变中心（原 `_darkRadial`）。
  static const Color canvasRadial = Color(0xFF0D1525);

  /// 屏级脚手架底（原 galaxy_screen / painter 星点遮蔽底 `0xFF060A12`）。
  static const Color canvasShell = Color(0xFF060A12);

  /// 画布浅档底（painter 亮分支 API 面；`_useDarkGalaxyTheme` 恒暗下
  /// 不可达，保留以兼容 painter 双档签名）。
  static const Color canvasBaseLight = Color(0xFFF5F6F8);

  /// 画布浅档径向（同上，不可达保留）。
  static const Color canvasRadialLight = Color(0xFFEBEDF2);

  // ------------------------------------------------------------------
  // 浮层 chrome 面板（恒暗深空玻璃面）
  // ------------------------------------------------------------------

  /// 主 chrome 面板（galaxy_screen 深色 colorScheme surface、legend 底）。
  static const Color chromePanel = Color(0xFF101929);

  /// chrome 面板高透明变体（legend `0xCC101929` / `0xE6101929`）。
  static const Color chromePanelBarrier = Color(0xCC101929);
  static const Color chromePanelLegend = Color(0xE6101929);

  /// 空白区长按菜单底（原 galaxy_screen `0xFF0C1626`）。
  static const Color menuPanel = Color(0xFF0C1626);

  /// 控件/横幅/设置 sheet 的玻璃底（原 `0xAA0F1726`/`0xCC0F1728`/
  /// `0xEE0E1523`/`0xAA101A2B`）。
  static const Color glassPanelControls = Color(0xAA0F1726);
  static const Color glassPanelBanner = Color(0xCC0F1728);
  static const Color glassPanelSettings = Color(0xEE0E1523);
  static const Color glassPanelMiniMap = Color(0xAA101A2B);

  /// 迷你图视口轨/滑块（节点预览卡暗底已改走主题 colorScheme.surface，
  /// V4-G04：dusk 外挂面不再漏 classic 藏青）。
  static const Color miniMapTrack = Color(0xFF152238);
  static const Color miniMapViewport = Color(0xFF88B4FF);

  /// 迷你图/画布浅档变体（亮分支 API 面，不可达保留）。
  static const Color miniMapTrackLight = Color(0xFFEFF3F8);
  static const Color miniMapViewportLight = Color(0xFF3563DA);

  /// 草稿审查屏底与渐变档（原 `0xFF050914`/`0xFF07111F`/`0xFF0C1830`）。
  static const Color draftScaffold = Color(0xFF050914);
  static const Color draftGradientLow = Color(0xFF07111F);
  static const Color draftGradientHigh = Color(0xFF0C1830);

  /// 上传浮层面板底（原 `0xFF0A1320`/`0xFF0B1523`/`0xFF04111F`）。
  static const Color uploadPanelVeil = Color(0xFF0A1320);
  static const Color uploadPanel = Color(0xFF0B1523);
  static const Color uploadPanelDeep = Color(0xFF04111F);

  // ------------------------------------------------------------------
  // 画布内墨与描边（painter 标签/发丝线）
  // ------------------------------------------------------------------

  /// 扇区标签暖墨 / 冷墨（painter 标签双族墨色）。
  static const Color labelInkWarm = Color(0xFFFFF4E6);
  static const Color labelInkCool = Color(0xFFE6F0FF);

  /// 星点墨浅档（painter 星层亮分支 API 面，不可达保留；
  /// 原 `0xFF6E6354`/`0xFF526173`）。
  static const Color starInkLightWarm = Color(0xFF6E6354);
  static const Color starInkLightCool = Color(0xFF526173);

  /// 低重要度节点灰基（painter `_nodeCanvasColor` lerp 基料）。
  static const Color dimNodeBase = Color(0xFF3A404A);
  static const Color dimNodeBaseLight = Color(0xFFB8BFC8);

  /// 暗角墨（painter vignette；原 dark 分支 `DS.neutral900` = classic dark
  /// textPrimary `0xFFF4F1EB`。V4-G04 钉死：DS.neutral900 随 profile 变，
  /// 会让恒暗画布在浅色档漏进深墨暗角——画布身份恒定，墨随之钉死）。
  static const Color vignetteInk = Color(0xFFF4F1EB);

  /// 暗角墨浅档（painter 亮分支 API 面，不可达保留；原 `0xFFCBD2DD`）。
  static const Color vignetteInkLight = Color(0xFFCBD2DD);

  /// 节点 mastery 角标遮蔽点底（原 painter `0xFF060A12` 同 canvasShell）。
  static const Color masteryDotVeil = canvasShell;

  // ------------------------------------------------------------------
  // 画布内功能强调（预测/庆祝/风险/状态）
  // ------------------------------------------------------------------

  /// 预测高亮金（预测边描边 + 高掌握节点 lerp 基料）。
  static const Color predictionGold = Color(0xFFFFD166);

  /// 预测风险环：高 / 中 / 低。
  static const Color riskHigh = Color(0xFFFF7B54);
  static const Color riskMedium = Color(0xFFFFC857);
  static const Color riskLow = Color(0xFF59D98E);

  /// 近期错误脉冲红（节点错误光环）。
  static const Color errorPulse = Color(0xFFFF4444);

  /// 空白区庆祝金（原 galaxy_screen `0xFFFFD700`）。
  static const Color celebrationGold = Color(0xFFFFD700);

  /// 控件发光蓝（controls `0xFF78A7FF`/`0xFF2A5BD7`、settings `0xFF6B8CFF`、
  /// 屏级晶格 `0xFF7CA9FF`/`0xFF3A67DA`）。
  static const Color glowBlueDark = Color(0xFF78A7FF);
  static const Color glowBlueLight = Color(0xFF2A5BD7);
  static const Color glowBlueSettings = Color(0xFF6B8CFF);
  static const Color glowBlueAmbient = Color(0xFF7CA9FF);
  static const Color glowBlueAmbientLight = Color(0xFF3A67DA);

  /// 上传/抽取链路青（进度、状态点，恒暗画布上的功能强调）。
  static const Color pipelineCyan = Color(0xFF7BE7FF);

  /// 画布内性能状态（最优/降级/危急，监测徽章用）。
  static const Color perfOptimal = Color(0xFF4CAF50);
  static const Color perfDegraded = Color(0xFFFFA726);
  static const Color perfCritical = Color(0xFFF44336);

  /// 扇区指示 chip 面板底（galaxy_controls `0xCC101722`）与横幅浅档墨
  /// （`0xFF111827`）。
  static const Color sectorChipPanel = Color(0xCC101722);
  static const Color bannerInkLight = Color(0xFF111827);

  /// HUD 横幅渐变档（galaxy_screen `0xE6223658`/`0xE6142038`）与缩放药丸底
  /// （`0xD9101A2C`）。
  static const Color hudBannerTop = Color(0xE6223658);
  static const Color hudBannerBottom = Color(0xE6142038);
  static const Color zoomPillPanel = Color(0xD9101A2C);

  /// 主 CTA 深墨（neutral0 按钮上的前景，原 galaxy_screen `0xFF182238`）。
  static const Color onSurfaceButtonInk = Color(0xFF182238);

  /// HUD 卡浅档墨（亮分支 API 面，不可达保留；原 `0xFF101828`）。
  static const Color hudInkLight = Color(0xFF101828);

  // ------------------------------------------------------------------
  // 掌握度节点四档（painter `galaxyMasteryNodeColor` 同值；恒暗档为
  // 生产档，浅档为 API 面保留）
  // ------------------------------------------------------------------

  static const Color masteryLow = Color(0xFF77808C);
  static const Color masteryLowLight = Color(0xFF9AA3AD);
  static const Color masteryMid = Color(0xFF73B7FF);
  static const Color masteryMidLight = Color(0xFF4F9FE8);
  static const Color masteryHigh = Color(0xFF8FE6B0);
  static const Color masteryHighLight = Color(0xFF4BC77E);
  static const Color masteryFull = Color(0xFF2EF28A);
  static const Color masteryFullLight = Color(0xFF16A85A);
}
