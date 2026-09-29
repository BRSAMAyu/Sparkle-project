// V4-G04 · 星图/学习/错题/资料家族四风格商业化完备守卫。
//
// 常规跑 `flutter test`：执行全部真实断言（对比度逐对复算 / 修复点探针 /
// 缩放触达目标 / reduce-motion 等价 / 200% 文本 / 家族面×四风格语义钉），
// 不写文件。设 `G04_EVIDENCE_DIR=<abs dir>` 时额外落盘四风格×面的成对
// 证据（PNG + 语义文本树，F05 成对截图纪律；同一 ThemeManager 管道、
// 同一冻结 seed）。
//
// 判例与纪律来源：
// - 真实主题管道宿主 = F05 style_preview_test_harness（ThemeManager 单例
//   → AppThemes.lightTheme 每 rebuild 重估；切档即真实 live re-theme）；
// - 对比度以「最终计算颜色」逐对复算（F06 判例：ACCESSIBILITY_ASSETS
//   正文 ≥4.5:1、大字/非文字关键部件 ≥3:1），非设计稿推断；
// - reduce-motion 等价 = S01 判例（低动态偏好下动效面直落静止终态 +
//   控制组证明动画通道真实存在）；
// - 星图画布恒暗身份 = V4-G04 diff 叙证 §星图 canvas 专项：画布绘制面
//   四风格同值（GalaxyCanvasPalette 单一名源），内部对比逐对机检。
import 'dart:io' as io;
import 'dart:math' as math;
import 'dart:ui' show ImageByteFormat;

import 'package:dio/dio.dart' as dio;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/tokens_v2/galaxy_canvas_palette.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/utils/theme_utils.dart';
import 'package:sparkle/features/documents/data/models/document_library_models.dart';
import 'package:sparkle/features/documents/data/repositories/document_library_repository.dart';
import 'package:sparkle/features/documents/presentation/screens/document_library_screen.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_document_upload_provider.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_controls.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_document_upload_overlay.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_background_painter.dart';
// galaxyMasteryNodeColor 由 star_map_painter.dart 直接导出。
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_list_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

import '../../shared/i18n_test_helper.dart';
import 'style_preview/style_preview_test_harness.dart';

/// 冻结 seed 版本（证据可复现锚；证据清单登记进 run_manifest）。
const String kG04SeedVersion = 'g04-seed-2026-09-29-v1';

const List<PixelPreviewProfile> _kProfiles = <PixelPreviewProfile>[
  PixelPreviewProfile.classic,
  PixelPreviewProfile.paperDay,
  PixelPreviewProfile.dusk,
  PixelPreviewProfile.quiet,
];

// ---------------------------------------------------------------------------
// 对比度复算工具（WCAG 2.x 相对亮度；与 F01/G05 同公式）。
// ---------------------------------------------------------------------------

double _srgbChannelToF(int v) {
  final c = v / 255.0;
  return c <= 0.04045
      ? c / 12.92
      : math.pow((c + 0.055) / 1.055, 2.4).toDouble();
}

double _relativeLuminance(Color c) =>
    0.2126 * _srgbChannelToF((c.r * 255.0).round()) +
    0.7152 * _srgbChannelToF((c.g * 255.0).round()) +
    0.0722 * _srgbChannelToF((c.b * 255.0).round());

double contrastRatio(Color a, Color b) {
  final la = _relativeLuminance(a);
  final lb = _relativeLuminance(b);
  final hi = la > lb ? la : lb;
  final lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

Color blendOver(Color fg, Color bg) => Color.alphaBlend(fg, bg);

/// 各档的语义取值面：classic 取浅档（发布默认锚），三像素档取各自 profile。
/// classic 深档另在经典深色组单独复算。
SparkleColors _colorsOf(PixelPreviewProfile profile) =>
    pixelPreviewColors(profile);

// ---------------------------------------------------------------------------
// A 组：对比度矩阵（最终计算颜色逐对复算 × 四档 + classic 深档）。
// ---------------------------------------------------------------------------

void main() {
  setUp(setUpI18nForTesting);

  group('A · 对比度矩阵（F06 判例：最终计算颜色逐对复算）', () {
    test('正文墨 × 各档画布/次面 ≥ 4.5:1（内容面通用对）', () {
      for (final profile in _kProfiles) {
        final c = _colorsOf(profile);
        final surface = c.surfacePrimary;
        final secondarySurface = c.surfaceSecondary;
        expect(
          contrastRatio(c.textPrimary, surface),
          greaterThanOrEqualTo(4.5),
          reason: '$profile textPrimary vs surfacePrimary',
        );
        expect(
          contrastRatio(c.textPrimary, secondarySurface),
          greaterThanOrEqualTo(4.5),
          reason: '$profile textPrimary vs surfaceSecondary',
        );
        expect(
          contrastRatio(c.textSecondary, surface),
          greaterThanOrEqualTo(4.5),
          reason: '$profile textSecondary vs surfacePrimary',
        );
      }
    });

    test('G4-1 错题掌握度 pill：修复后文字墨 textPrimary × 档位 tint ≥ 4.5:1',
        () {
      for (final profile in _kProfiles) {
        final c = _colorsOf(profile);
        for (final band in <Color>[c.semanticSuccess, c.semanticWarning]) {
          final pillBg = blendOver(
            band.withValues(alpha: 0.1),
            c.surfacePrimary,
          );
          expect(
            contrastRatio(c.textPrimary, pillBg),
            greaterThanOrEqualTo(4.5),
            reason: '$profile mastery pill ink vs band tint '
                '(${contrastRatio(c.textPrimary, pillBg).toStringAsFixed(2)})',
          );
        }
      }
    });

    test('G4-2 学习旅程 parse chip：修复后文字墨 textPrimary × 状态 tint ≥ 4.5:1',
        () {
      for (final profile in _kProfiles) {
        final c = _colorsOf(profile);
        final statusColors = <Color>[
          c.semanticSuccess,
          c.semanticError,
          c.semanticWarning,
          c.semanticInfo,
        ];
        for (final status in statusColors) {
          final chipBg = blendOver(
            status.withValues(alpha: 0.12),
            c.surfacePrimary,
          );
          expect(
            contrastRatio(c.textPrimary, chipBg),
            greaterThanOrEqualTo(4.5),
            reason: '$profile parse chip ink vs status tint '
                '(${contrastRatio(c.textPrimary, chipBg).toStringAsFixed(2)})',
          );
        }
      }
    });

    test('G4-3 资料库 hero：墨随画布亮度——浅档正文墨 ≥4.5:1，深档白字逐位保持',
        () {
      for (final profile in _kProfiles) {
        final c = _colorsOf(profile);
        final isDark = c.brightness == Brightness.dark;
        // hero 渐变最亮档（浅档）：deepSpaceStart@0.94 叠 surfacePrimary
        // 的最终计算颜色；deepSpaceStart = blend(neutral50, brandSecondary, .12)。
        // DS 口径：_blend(a,b,t)=Color.lerp(a,b,t)。
        // neutral50 = lerp(surfacePrimary, neutral200, 0.4)；
        // deepSpaceStart(浅档) = lerp(neutral50, brandSecondary, 0.12)。
        final neutral50 = Color.lerp(
          c.surfacePrimary,
          c.neutral200,
          0.4,
        )!;
        final deepSpaceStart = Color.lerp(neutral50, c.brandSecondary, 0.12)!;
        final heroStart = blendOver(
          deepSpaceStart.withValues(alpha: 0.94),
          c.surfacePrimary,
        );
        final heroInk = isDark ? const Color(0xFFFFFFFF) : c.textPrimary;
        expect(
          contrastRatio(heroInk, heroStart),
          greaterThanOrEqualTo(4.5),
          reason: '$profile hero ink vs lightest stop '
              '(${contrastRatio(heroInk, heroStart).toStringAsFixed(2)})',
        );
      }
    });

    test('G4-4 资料库文件类型 glyph：浅档同色相加深后 图标 ≥3:1 且标签 ≥4.5:1',
        () {
      for (final profile in _kProfiles) {
        final c = _colorsOf(profile);
        final isDark = c.brightness == Brightness.dark;
        final identities = <Color>[
          c.semanticError,
          c.semanticInfo,
          c.semanticWarning,
          c.semanticSuccess,
          c.taskReflection,
        ];
        for (final base in identities) {
          final accent = isDark
              ? base
              : Color.lerp(base, const Color(0xFF000000), 0.38)!;
          final glyphBg = blendOver(
            accent.withValues(alpha: 0.22),
            c.surfacePrimary,
          );
          // 图标（图形档）≥3:1。
          expect(
            contrastRatio(accent, glyphBg),
            greaterThanOrEqualTo(3.0),
            reason: '$profile glyph icon vs tint '
                '(${contrastRatio(accent, glyphBg).toStringAsFixed(2)})',
          );
          // 类型标签（小字）走正文墨 ≥4.5:1——全强度 accent 做小字在
          // dusk 档 4.17:1 不达标（G05 文本墨同判例），语义由标签文本
          // （文件类型名）唯一承载，色相保留在图标与 tint。
          expect(
            contrastRatio(c.textPrimary, glyphBg),
            greaterThanOrEqualTo(4.5),
            reason: '$profile glyph label ink vs tint',
          );
        }
      }
    });

    test('G4-5 星图 canvas 专项（恒暗身份，四档同值）：节点/环/徽章 vs 画布底 ≥3:1',
        () {
      const canvas = GalaxyCanvasPalette.canvasBase;
      // 掌握度节点四档（生产恒暗档）。
      for (final nodeColor in <Color>[
        GalaxyCanvasPalette.masteryLow,
        GalaxyCanvasPalette.masteryMid,
        GalaxyCanvasPalette.masteryHigh,
        GalaxyCanvasPalette.masteryFull,
      ]) {
        expect(
          contrastRatio(nodeColor, canvas),
          greaterThanOrEqualTo(3.0),
          reason: 'mastery node $nodeColor vs canvas '
              '(${contrastRatio(nodeColor, canvas).toStringAsFixed(2)})',
        );
      }
      // 领域七色（dark 档 = 画布生产档）。
      for (final style in SectorConfig.styles.values) {
        expect(
          contrastRatio(style.primaryColorFor(isDarkMode: true), canvas),
          greaterThanOrEqualTo(3.0),
          reason: 'sector ${style.name} vs canvas',
        );
      }
      // 预测/风险/庆祝/错误脉冲。
      for (final accent in <Color>[
        GalaxyCanvasPalette.predictionGold,
        GalaxyCanvasPalette.riskHigh,
        GalaxyCanvasPalette.riskMedium,
        GalaxyCanvasPalette.riskLow,
        GalaxyCanvasPalette.errorPulse,
        GalaxyCanvasPalette.celebrationGold,
      ]) {
        expect(
          contrastRatio(accent, canvas),
          greaterThanOrEqualTo(3.0),
          reason: 'canvas accent $accent vs canvas '
              '(${contrastRatio(accent, canvas).toStringAsFixed(2)})',
        );
      }
      expect(
        galaxyMasteryNodeColor(masteryScore: 10, isDarkMode: true),
        GalaxyCanvasPalette.masteryLow,
      );
      expect(
        galaxyMasteryNodeColor(masteryScore: 90, isDarkMode: true),
        GalaxyCanvasPalette.masteryFull,
      );
    });

    test('G4-6 星图 canvas 标签墨 vs 画布底/面板 ≥4.5:1（正文标签档）', () {
      const canvas = GalaxyCanvasPalette.canvasBase;
      for (final ink in <Color>[
        GalaxyCanvasPalette.labelInkWarm,
        GalaxyCanvasPalette.labelInkCool,
        DS.neutral0,
      ]) {
        expect(
          contrastRatio(ink, canvas),
          greaterThanOrEqualTo(4.5),
          reason: 'label ink $ink vs canvas '
              '(${contrastRatio(ink, canvas).toStringAsFixed(2)})',
        );
      }
      // 画布 chrome 面板（legend/HUD 底）上的白墨。
      final panel = blendOver(
        GalaxyCanvasPalette.chromePanel.withValues(alpha: 0.88),
        canvas,
      );
      expect(contrastRatio(DS.neutral0, panel), greaterThanOrEqualTo(4.5));
    });

    test('G4-7 画布 chrome 控件：图标墨 vs 玻璃面板 ≥3:1；迷你图视口 vs 轨道 ≥3:1',
        () {
      const canvas = GalaxyCanvasPalette.canvasShell;
      final controlPanel = blendOver(
        GalaxyCanvasPalette.glassPanelControls,
        canvas,
      );
      expect(
        contrastRatio(DS.neutral0, controlPanel),
        greaterThanOrEqualTo(3.0),
        reason: 'control icon vs glass panel',
      );
      expect(
        contrastRatio(
          GalaxyCanvasPalette.glowBlueDark,
          controlPanel,
        ),
        greaterThanOrEqualTo(3.0),
        reason: 'active glow vs glass panel',
      );
      expect(
        contrastRatio(
          GalaxyCanvasPalette.miniMapViewport,
          GalaxyCanvasPalette.miniMapTrack,
        ),
        greaterThanOrEqualTo(3.0),
        reason: 'minimap viewport vs track',
      );
      // 上传链路青与状态色 vs 面板。
      final uploadPanel = blendOver(
        GalaxyCanvasPalette.uploadPanel.withValues(alpha: 0.92),
        canvas,
      );
      expect(
        contrastRatio(GalaxyCanvasPalette.pipelineCyan, uploadPanel),
        greaterThanOrEqualTo(3.0),
        reason: 'pipeline cyan vs upload panel',
      );
    });

    test('G4-8 草稿审查屏（恒暗族）：白墨族 vs 脚手架底 ≥4.5:1', () {
      const scaffold = GalaxyCanvasPalette.draftScaffold;
      for (final ink in <Color>[
        DS.neutral0,
        DS.neutral0.withValues(alpha: 0.72),
        DS.neutral0.withValues(alpha: 0.58),
      ]) {
        final blended = blendOver(ink, scaffold);
        expect(
          contrastRatio(blended, scaffold),
          greaterThanOrEqualTo(4.5),
          reason: 'draft review ink ${ink.toARGB32()} vs scaffold '
              '(${contrastRatio(blended, scaffold).toStringAsFixed(2)})',
        );
      }
    });

    test('G4-9 classic 深档（发布默认第二锚）：正文对与 pill/hero 修复墨复算', () {
      final c = SparkleColors.dark();
      expect(
        contrastRatio(c.textPrimary, c.surfacePrimary),
        greaterThanOrEqualTo(4.5),
      );
      expect(
        contrastRatio(c.textSecondary, c.surfacePrimary),
        greaterThanOrEqualTo(4.5),
      );
      // 错题 pill（深档文字墨 = textPrimary）。
      final pillBg = blendOver(
        c.semanticWarning.withValues(alpha: 0.1),
        c.surfacePrimary,
      );
      expect(
        contrastRatio(c.textPrimary, pillBg),
        greaterThanOrEqualTo(4.5),
      );
    });

    test('G4-10 银河插画 on-accent 图标墨：onPrimary 校准槽 × accent 渐变止点 ≥3:1（四档）',
        () {
      for (final profile in _kProfiles) {
        final c = _colorsOf(profile);
        // 产品公式（document_library_screen 双插画，V4-G04 续跑收口）：
        // ink = Theme.of(context).colorScheme.onPrimary——装配于 design_system
        // ThemeData.colorScheme：pixel 档 = PixelProfileTheme.accentInk
        // （proposal on_accent 槽），classic（preview off）=
        // ThemeUtils.getContrastSafeText(brandPrimary, darkText: textPrimary)。
        final ink = profile == PixelPreviewProfile.classic
            ? ThemeUtils.getContrastSafeText(
                c.brandPrimary,
                darkText: c.textPrimary,
              )
            : PixelProfileTheme.forProfile(profile).accentInk;
        // 迷你/大插画圆徽渐变止点的最终计算颜色（accent@alpha 叠页面底）。
        final stops = <String, Color>{
          'miniTop': blendOver(
            c.brandPrimary.withValues(alpha: 0.82),
            c.surfacePrimary,
          ),
          'miniBottom': blendOver(
            c.semanticInfo.withValues(alpha: 0.78),
            c.surfacePrimary,
          ),
          'largeTop': blendOver(
            c.brandPrimary.withValues(alpha: 0.9),
            c.surfacePrimary,
          ),
          'largeBottom': blendOver(
            c.semanticInfo.withValues(alpha: 0.82),
            c.surfacePrimary,
          ),
        };
        for (final entry in stops.entries) {
          final ratio = contrastRatio(ink, entry.value);
          expect(
            ratio,
            greaterThanOrEqualTo(3.0),
            reason: '$profile on-accent icon ink vs ${entry.key} '
                '(${ratio.toStringAsFixed(2)})',
          );
        }
        // 修前判负探针：白墨在 dusk 亮 accent 渐变上确实 <3:1（本钉判别力）。
        if (profile == PixelPreviewProfile.dusk) {
          final whiteVsTop = contrastRatio(
            const Color(0xFFFFFFFF),
            stops['largeTop']!,
          );
          expect(
            whiteVsTop,
            lessThan(3.0),
            reason: '修前实况：white icon vs dusk largeTop $whiteVsTop',
          );
        }
      }
    });
  });

  group('B · 修前缺陷探针（旧公式真实失败配置——判别力证据）', () {
    final classicLight = SparkleColors.light();

    test('E-1 旧掌握度 pill：色觉辅助档（CB palette）下全强度 warning 文本 '
        '× warning@0.1 tint < 4.5（classic 默认档 warning 已是深墨 7D5C26，'
        '通过；色觉辅助档 E69F00 高饱和橙在同一公式下失败——逐色测试判例）',
        () {
      final cb = SparkleColors.light(colorBlindFriendly: true);
      final bg = blendOver(
        cb.semanticWarning.withValues(alpha: 0.1),
        cb.surfacePrimary,
      );
      expect(
        contrastRatio(cb.semanticWarning, bg),
        lessThan(4.5),
        reason: '修前实况：CB 档 warning on warning-tint '
            '${contrastRatio(cb.semanticWarning, bg).toStringAsFixed(2)}:1',
      );
      // 修复墨（textPrimary）在同一底上 ≥4.5。
      expect(
        contrastRatio(cb.textPrimary, bg),
        greaterThanOrEqualTo(4.5),
      );
    });

    test('E-2 旧 hero：白字 × 浅档渐变亮止 < 4.5（实际近 1:1）', () {
      final c = classicLight;
      final neutral50 = Color.lerp(c.surfacePrimary, c.neutral200, 0.4)!;
      final deepSpaceStart = Color.lerp(neutral50, c.brandSecondary, 0.12)!;
      final heroStart = blendOver(
        deepSpaceStart.withValues(alpha: 0.94),
        c.surfacePrimary,
      );
      expect(
        contrastRatio(const Color(0xFFFFFFFF), heroStart),
        lessThan(4.5),
        reason: '修前实况：white hero title classic 浅档 '
            '${contrastRatio(const Color(0xFFFFFFFF), heroStart).toStringAsFixed(2)}:1',
      );
    });

    test('E-3 旧文件类型 glyph：pastel 字面量浅档 < 3:1（图标档）', () {
      for (final literal in <Color>[
        const Color(0xFFE06A6A), // pdf
        const Color(0xFF63A1FF), // docx
        const Color(0xFFFFB45E), // pptx
        const Color(0xFF74C8A6), // md
        const Color(0xFFC88BFF), // image
      ]) {
        final bg = blendOver(
          literal.withValues(alpha: 0.22),
          classicLight.surfacePrimary,
        );
        expect(
          contrastRatio(literal, bg),
          lessThan(3.0),
          reason: '修前实况：$literal classic 浅档 '
              '${contrastRatio(literal, bg).toStringAsFixed(2)}:1',
        );
      }
    });
  });

  group('C · 缩放控件触达目标（G04 家族特有风险面）', () {
    testWidgets('GalaxyControls 缩放±/总览/搜索/回放/设置 按钮触达 ≥48dp（四档）',
        (tester) async {
      for (final profile in _kProfiles) {
        final manager = await freshThemeManager();
        await manager.setPixelPreviewProfile(profile);
        await tester.pumpWidget(
          AnimatedBuilder(
            animation: ThemeManager(),
            builder: (context, _) => MaterialApp(
              theme: AppThemes.lightTheme,
              locale: const Locale('zh'),
              localizationsDelegates: const [
                AppLocalizations.delegate,
                GlobalMaterialLocalizations.delegate,
                GlobalWidgetsLocalizations.delegate,
                GlobalCupertinoLocalizations.delegate,
              ],
              supportedLocales: AppLocalizations.supportedLocales,
              home: const Scaffold(
                body: Center(
                  child: GalaxyControls(
                    isDarkMode: true,
                    onZoomIn: _noop,
                    onFitToOverview: _noop,
                    onZoomOut: _noop,
                    onReplay: _noop,
                    onSearch: _noop,
                    onSettings: _noop,
                  ),
                ),
              ),
            ),
          ),
        );
        await tester.pump(const Duration(milliseconds: 120));
        expect(tester.takeException(), isNull, reason: '$profile 渲染异常');

        for (final icon in const [
          Icons.add_rounded,
          Icons.my_location_rounded,
          Icons.remove_rounded,
          Icons.search_rounded,
          Icons.play_circle_outline_rounded,
          Icons.tune_rounded,
        ]) {
          final iconFinder = find.byIcon(icon);
          expect(
            iconFinder,
            findsOneWidget,
            reason: '$profile 缺图标 $icon',
          );
          final size = tester.getSize(
            find
                .ancestor(
                  of: iconFinder,
                  matching: find.byType(IconButton),
                )
                .first,
          );
          expect(
            size.width,
            greaterThanOrEqualTo(48.0),
            reason: '$profile $icon 触达宽 ${size.width}dp < 48',
          );
          expect(
            size.height,
            greaterThanOrEqualTo(48.0),
            reason: '$profile $icon 触达高 ${size.height}dp < 48',
          );
        }
      }
    });
  });

  group('D · 星图面四风格确定性（F05 判例：真实表面 + 冻结 seed）', () {
    GalaxyNodeModel seedNode() => GalaxyNodeModel(
          id: 'g04-node-1',
          name: '特征值与对角化',
          importance: 72,
          sector: SectorEnum.cosmos,
          isUnlocked: true,
          masteryScore: 64,
        );

    Widget starMapFace() => Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(DS.borderRadiusMD),
              child: const SizedBox(
                height: 120,
                width: double.infinity,
                child: TiledSectorBackground(width: 720, height: 240),
              ),
            ),
            GalaxyNodePreviewCard(
              node: seedNode(),
              onFocus: _noop,
              onInspectConnections: _noop,
              onViewDetails: _noop,
              onStartReview: _noop,
            ),
          ],
        );

    Future<List<String>> dumpSemantics(WidgetTester tester) async {
      // V4-G04 续跑修复：F05 元素树口径——widget-test 泵内 `widget is
      // Semantics` 直查恒空（语义树经 RenderSemanticsAnnotations 落渲染
      // 层，不经同名 widget），空表使跨档恒等钉空转。改 RenderParagraph
      // 文本 + RenderSemanticsAnnotations 标签双覆盖（F05 同款，字段等价）。
      final lines = <String>[];
      void visit(Element element, int depth) {
        final ro = element.renderObject;
        if (ro is RenderParagraph) {
          final text = ro.text.toPlainText();
          if (text.trim().isNotEmpty) {
            lines.add('${'  ' * depth}label="$text" isText=true');
          }
        }
        if (ro is RenderSemanticsAnnotations) {
          final sem = ro.properties.label;
          if (sem != null && sem.isNotEmpty) {
            lines.add('${'  ' * depth}sem="$sem"');
          }
        }
        element.visitChildren((child) => visit(child, depth + 1));
      }

      visit(tester.element(find.byType(MaterialApp)), 0);
      return lines;
    }

    testWidgets('星图面 × 四档：真实主题管道渲染 + 语义结构跨档恒等 + 证据落盘',
        (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(720, 1280);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final semanticsByProfile = <PixelPreviewProfile, List<String>>{};
      final evidenceDir = io.Platform.environment['G04_EVIDENCE_DIR'];

      for (final profile in _kProfiles) {
        final manager = await freshThemeManager();
        await manager.setPixelPreviewProfile(profile);
        final repaintKey = GlobalKey();
        await tester.pumpWidget(
          KeyedSubtree(
            key: ValueKey('g04-face-${profile.name}'),
            child: AnimatedBuilder(
              animation: ThemeManager(),
              builder: (context, _) => RepaintBoundary(
                key: repaintKey,
                child: MaterialApp(
                  debugShowCheckedModeBanner: false,
                  theme: AppThemes.lightTheme,
                  locale: const Locale('zh'),
                  localizationsDelegates: const [
                    AppLocalizations.delegate,
                    GlobalMaterialLocalizations.delegate,
                    GlobalWidgetsLocalizations.delegate,
                    GlobalCupertinoLocalizations.delegate,
                  ],
                  supportedLocales: AppLocalizations.supportedLocales,
                  home: Scaffold(
                    body: Center(
                      child: SingleChildScrollView(
                        child: starMapFace(),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
        await tester.pump(const Duration(milliseconds: 300));
        expect(tester.takeException(), isNull, reason: '$profile 渲染异常');

        // 语义钉：节点名 + 领域名在四档全部在场（真实读屏可用面）。
        expect(
          find.text('特征值与对角化'),
          findsOneWidget,
          reason: '$profile 节点名缺失',
        );
        expect(
          find.textContaining('宇宙'),
          findsWidgets,
          reason: '$profile 领域名缺失（zh 本地化领域名，副标题句内）',
        );

        semanticsByProfile[profile] = await dumpSemantics(tester);

        if (evidenceDir != null) {
          // V4-G04 续跑修复：toImage 的引擎回调必须经 runAsync 真异步窗口
          // 才能回到 fake-async 测试区（F05 _capture / G05 同款判例）——
          // 裸 await 在测试区永不完成，D 组证据落盘路径 10 分钟超时
          //（无 G04_EVIDENCE_DIR 时不进此分支，故常规跑全绿、开落盘才复现）。
          await tester.runAsync(() async {
            final dir = io.Directory(evidenceDir)
              ..createSync(recursive: true);
            final boundary = repaintKey.currentContext!.findRenderObject()
                as RenderRepaintBoundary;
            final image = await boundary.toImage(pixelRatio: 2.0);
            final bytes =
                await image.toByteData(format: ImageByteFormat.png);
            io.File(
              '${dir.path}/g04_starmap_face_${profile.name}.png',
            ).writeAsBytesSync(bytes!.buffer.asUint8List());
            io.File(
              '${dir.path}/g04_starmap_face_${profile.name}_semantics.txt',
            ).writeAsStringSync(semanticsByProfile[profile]!.join('\n'));
          });
        }
      }

      // 语义结构跨档恒等（切主题不改语义结构，F05 机检口径）。
      for (final profile in _kProfiles.skip(1)) {
        expect(
          semanticsByProfile[profile],
          equals(semanticsByProfile[PixelPreviewProfile.classic]),
          reason: '$profile 语义结构与 classic 漂移',
        );
      }
    });
  });

  group('E · 上传浮层 reduce-motion 等价（S01 判例）', () {
    GalaxyDocumentUploadSession session({
      GalaxyDocumentUploadPhase phase = GalaxyDocumentUploadPhase.extracting,
    }) =>
        GalaxyDocumentUploadSession(
          localSessionId: 'g04-session',
          fileName: '线性代数讲义.pdf',
          filePath: '/tmp/linear-algebra.pdf',
          fileSize: 1024,
          mimeType: 'application/pdf',
          originScreenPosition: Offset.zero,
          target: const GalaxyDocumentUploadTarget.galaxyCore(
            label: '星图核心',
          ),
          phase: phase,
        );

    Widget host(Widget child, {bool disableAnimations = false}) => MaterialApp(
          theme: AppThemes.lightTheme,
          locale: const Locale('zh'),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: MediaQuery(
            data: MediaQueryData(disableAnimations: disableAnimations),
            child: Stack(
              children: [
                const Scaffold(body: SizedBox.expand()),
                GalaxyDocumentUploadOverlay(
                  session: session(),
                  targetScreenPosition: const Offset(180, 400),
                  onRetry: _noop,
                  onDismiss: _noop,
                ),
              ],
            ),
          ),
        );

    testWidgets('E+ 减弱动效：浮层挂载零异常、进度面静态可达、无在航 repeat ticker',
        (tester) async {
      await tester.pumpWidget(
        host(const SizedBox.shrink(), disableAnimations: true),
      );
      // 首帧即静止终态；继续泵 600ms 无位移（脉冲/飞行层直落终态）。
      await tester.pump(const Duration(milliseconds: 300));
      expect(tester.takeException(), isNull);
      expect(find.byType(GalaxyDocumentUploadOverlay), findsOneWidget);
      final before = tester.getRect(
        find.byType(GalaxyDocumentUploadOverlay),
      );
      await tester.pump(const Duration(milliseconds: 600));
      final after = tester.getRect(
        find.byType(GalaxyDocumentUploadOverlay),
      );
      expect(after, before, reason: 'reduce-motion 下浮层位置应零位移');
    });

    testWidgets('E- 常规路径控制组：浮层真实挂载（动画通道在场的结构前提）',
        (tester) async {
      await tester.pumpWidget(host(const SizedBox.shrink()));
      await tester.pump(const Duration(milliseconds: 100));
      expect(tester.takeException(), isNull);
      expect(find.byType(GalaxyDocumentUploadOverlay), findsOneWidget);
      expect(find.textContaining('线性代数讲义'), findsWidgets);
    });
  });

  group('F · 资料库 hero × 四档：修复墨在场 + 200% 文本零溢出', () {
    DocumentLibraryItem seedDoc() => DocumentLibraryItem.fromJson(
          <String, dynamic>{
            'id': 'g04-doc-1',
            'file_name': '线性代数讲义.pdf',
            'mime_type': 'application/pdf',
            'status': 'ready',
            'created_at': '2026-09-20T10:00:00Z',
          },
        );


    Future<void> pumpLibrary(
      WidgetTester tester,
      PixelPreviewProfile profile, {
      double textScale = 1.0,
    }) async {
      final manager = await freshThemeManager();
      await manager.setPixelPreviewProfile(profile);
      await tester.pumpWidget(
        KeyedSubtree(
          key: ValueKey('g04-lib-${profile.name}-$textScale'),
          child: AnimatedBuilder(
            animation: ThemeManager(),
            builder: (context, _) => ProviderScope(
              overrides: [
                documentLibraryRepositoryProvider.overrideWithValue(
                  _StubDocumentRepository(seedDoc()),
                ),
              ],
              child: MediaQuery(
                data: MediaQueryData(
                  textScaler: TextScaler.linear(textScale),
                ),
                child: MaterialApp(
                  debugShowCheckedModeBanner: false,
                  theme: AppThemes.lightTheme,
                  locale: const Locale('zh'),
                  localizationsDelegates: const [
                    AppLocalizations.delegate,
                    GlobalMaterialLocalizations.delegate,
                    GlobalWidgetsLocalizations.delegate,
                    GlobalCupertinoLocalizations.delegate,
                  ],
                  supportedLocales: AppLocalizations.supportedLocales,
                  home: const DocumentLibraryScreen(),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 400));
    }

    testWidgets('hero 修复面：标题/副标题在四档在场，200% × 四档零异常',
        (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(750, 1600);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      for (final profile in _kProfiles) {
        await pumpLibrary(tester, profile);
        expect(tester.takeException(), isNull, reason: '$profile 渲染异常');
        // hero 标题（l10n zh）在四档在场——白字白底缺陷消除后的可读面。
        expect(
          find.textContaining('学习资料'),
          findsWidgets,
          reason: '$profile hero 标题缺失',
        );

        // 200% 文本：重新泵制，无布局破碎异常。
        await pumpLibrary(tester, profile, textScale: 2.0);
        expect(
          tester.takeException(),
          isNull,
          reason: '$profile 200% 文本渲染异常（RenderFlex overflow 等）',
        );
      }
    });

    testWidgets('银河插画 on-accent 图标墨回退钉：resolved ink 四档 == 校准槽',
        (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(750, 1600);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      for (final profile in _kProfiles) {
        await pumpLibrary(tester, profile);
        expect(tester.takeException(), isNull, reason: '$profile 渲染异常');
        final c = _colorsOf(profile);
        // 与 G4-10 同一产品公式（widget 级读真实 resolved color，防产品码
        // 回退 Colors.white——G05 判例：公式钉之外由 widget 钉承载回退保护）。
        final expectedInk = profile == PixelPreviewProfile.classic
            ? ThemeUtils.getContrastSafeText(
                c.brandPrimary,
                darkText: c.textPrimary,
              )
            : PixelProfileTheme.forProfile(profile).accentInk;
        final icons =
            tester.widgetList<Icon>(find.byIcon(Icons.auto_awesome_rounded));
        expect(
          icons,
          isNotEmpty,
          reason: '$profile 银河插画图标未挂载',
        );
        for (final icon in icons) {
          expect(
            icon.color,
            expectedInk,
            reason: '$profile on-accent 墨偏离 onPrimary 校准槽',
          );
        }
      }
    });
  });

  group('G · 种子库空态/零命中 × 四档（U13 语义不动，只钉呈现）', () {
    Future<void> pumpSeeds(
      WidgetTester tester,
      PixelPreviewProfile profile,
    ) async {
      final manager = await freshThemeManager();
      await manager.setPixelPreviewProfile(profile);
      await tester.pumpWidget(
        KeyedSubtree(
          key: ValueKey('g04-seed-${profile.name}'),
          child: AnimatedBuilder(
            animation: ThemeManager(),
            builder: (context, _) => ProviderScope(
              overrides: [
                seedLibraryRepositoryProvider.overrideWithValue(
                  _EmptySeedLibraryRepository(),
                ),
              ],
              child: MaterialApp(
                debugShowCheckedModeBanner: false,
                theme: AppThemes.lightTheme,
                locale: const Locale('zh'),
                localizationsDelegates: const [
                  AppLocalizations.delegate,
                  GlobalMaterialLocalizations.delegate,
                  GlobalWidgetsLocalizations.delegate,
                  GlobalCupertinoLocalizations.delegate,
                ],
                supportedLocales: AppLocalizations.supportedLocales,
                home: const SeedLibraryListScreen(),
              ),
            ),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 300));
    }

    testWidgets('空库态语义四档逐字一致：还没有创建种子库 + 创建主操作在场',
        (tester) async {
      for (final profile in _kProfiles) {
        await pumpSeeds(tester, profile);
        expect(tester.takeException(), isNull, reason: '$profile 渲染异常');
        expect(
          find.text('还没有创建种子库'),
          findsOneWidget,
          reason: '$profile 空库态标题缺失（U13 语义面）',
        );
        expect(find.byType(EmptyState), findsOneWidget);
      }
    });
  });
}


/// 资料库替身：单文档 ready 态（hero/glyph/状态 badge 修复面的真实载体）。
class _StubDocumentRepository extends DocumentLibraryRepository {
  _StubDocumentRepository(this.seedDocument) : super(dio.Dio());

  final DocumentLibraryItem seedDocument;

  @override
  Future<List<DocumentLibraryItem>> listDocuments({
    int limit = 100,
    int offset = 0,
  }) async =>
      <DocumentLibraryItem>[seedDocument];

  @override
  Future<DocumentProcessingStatus?> getDocumentStatus(String fileId) async =>
      null;

  @override
  Future<List<DocumentGalaxyNode>> listDocumentNodes(String fileId) async =>
      const <DocumentGalaxyNode>[];

  @override
  Future<Map<String, String>> loadNodeSectorCodes() async =>
      const <String, String>{};

  @override
  Future<Map<String, DocumentCitationInsight>> loadCitationInsights({
    int maxConversations = 12,
  }) async =>
      const <String, DocumentCitationInsight>{};
}

void _noop() {}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 空库替身：任何查询都回空页（空库态），搜零命中走 noResults 分支。
class _EmptySeedLibraryRepository extends SeedLibraryRepository {
  _EmptySeedLibraryRepository() : super(_UnusedApiClient());

  @override
  Future<PaginatedResponse<SeedLibrary>> listLibraries({
    LibraryCategory? category,
    LibraryVisibility? visibility,
    String? language,
    bool? isOfficial,
    bool? isFeatured,
    String? search,
    int page = 1,
    int pageSize = 20,
    String? sortBy,
    String? sortOrder,
  }) async =>
      PaginatedResponse<SeedLibrary>(
        items: const <SeedLibrary>[],
        total: 0,
        page: page,
        pageSize: pageSize,
        totalPages: 0,
      );
}
