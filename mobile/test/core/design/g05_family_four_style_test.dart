// V4-G05 · 洞察/复盘/报告家族四风格商业化完备守卫。
//
// 常规跑 `flutter test`：执行全部真实断言（对比度逐对复算 / 修复点
// widget 级钉 / reduce-motion 等价 / 200% 文本 / 三读面×四风格语义钉），
// 不写文件。设 `G05_EVIDENCE_DIR=<abs dir>` 时额外落盘四风格×读面的
// 成对证据（PNG + 语义文本树，F05 成对截图纪律；同一 ThemeManager 管道、
// 同一冻结 seed）。
//
// 判例与纪律来源：
// - 真实主题管道宿主 = F05 style_preview_test_harness（ThemeManager 单例
//   → AppThemes.lightTheme 每 rebuild 重估；切档即真实 live re-theme）；
// - 对比度以「最终计算颜色」逐对复算（F06 判例：ACCESSIBILITY_ASSETS
//   正文 ≥4.5:1、大字/非文字关键部件 ≥3:1），非设计稿推断；
// - reduce-motion 等价 = S01 判例（低动态偏好下图表直落终态 + 控制组
//   证明动画通道真实存在）。
import 'dart:io' as io;
import 'dart:math' as math;
import 'dart:ui' show ImageByteFormat;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/charts/engagement_heatmap.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';
import 'package:sparkle/features/cognitive/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/i_cognitive_repository.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/cognitive/presentation/screens/pattern_list_screen.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/insights/data/models/evidence_insight_card.dart';
import 'package:sparkle/features/insights/presentation/providers/evidence_insight_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/evidence_insight_card.dart';
import 'package:sparkle/features/insights/presentation/widgets/evidence_insight_section.dart';
import 'package:sparkle/features/insights/presentation/widgets/risk_observation_card.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/presentation/screens/learning_report_screen.dart';
import 'package:sparkle/features/report/presentation/widgets/mastery_radar_chart.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/reviews/presentation/screens/review_plan_hub_screen.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import '../../shared/i18n_test_helper.dart';
import 'style_preview/style_preview_test_harness.dart';

/// 冻结 seed 版本（证据可复现锚；证据清单登记进 run_manifest）。
const String kG05SeedVersion = 'g05-seed-2026-09-29-v1';

/// 首报里程碑已解锁旗（真实键式 mirofish_milestone_v1:firstReport）：
/// G05 宿主 freshThemeManager 的 setMockInitialValues 会覆盖 setUp 的
/// 通道 mock，使庆祝对话框真实弹出并吸收拖拽——报告宿主预置此旗从
/// 源头消弹（scrollUntilMounted 的角落点 barrier 为冗余保险）。
const Map<String, Object> kG05MilestonePrefs = <String, Object>{
  'mirofish_milestone_v1:firstReport': true,
};

// ---------------------------------------------------------------------------
// 冻结 seed（与 U13 证据采集同源口径：合法 schema 卡 + 认知定式 + 报告）。
// ---------------------------------------------------------------------------

EvidenceInsightCardData g05SeedCard() =>
    EvidenceInsightCardData.fromJson(<String, dynamic>{
      'id': 'interventions_that_helped:rescope:recall_gap',
      'kind': 'interventions_that_helped',
      'window_days': 30,
      'fact': <String, dynamic>{
        'intervention_type': 'rescope',
        'friction_tag': 'recall_gap',
        'n_exposed': 3,
        'n_accepted': 2,
        'n_observed': 2,
        'n_positive': 2,
        'n_negative': 0,
      },
      'interpretation': <String, dynamic>{
        'evidence_strength': 'accumulated',
        'direction': 'positive_association',
        'causal': false,
      },
      'uncertainty': <String, dynamic>{
        'qualifiers': <String>['correlation_not_causation', 'small_sample'],
        'samples': 2,
        'outcome_samples_raw': 3,
        'duplicate_outcome_samples_dropped': 1,
        'not_yet_observed': 1,
        'withdrawn_refs_excluded': 2,
      },
      'understanding': <String, dynamic>{
        'claim_allowed': false,
        'band': 'incomplete_evidence',
        'samples': 2,
        'missing': 0,
        'censored': 1,
      },
      'next_step': <String, dynamic>{
        'observation_id': 'interventions_that_helped:rescope:recall_gap',
        'user_can_reject': true,
        'reject_penalty': 'none',
      },
      'evidence': <dynamic>[
        <String, dynamic>{
          'label_key': 'evidence_directive_log',
          'deep_link': '/learning/insights/directives',
          'refs': <String>['d1', 'd2'],
        },
      ],
      'implication': <String, dynamic>{
        'action_key': 'review_directives',
        'deep_link': '/learning/insights/directives',
      },
    });

List<BehaviorPatternModel> g05SeedPatterns() => <BehaviorPatternModel>[
      BehaviorPatternModel(
        id: 'bp-g05-1',
        userId: 'u1',
        patternName: '计划乐观偏差',
        patternType: PatternType.cognitive,
        confidenceScore: 0.73,
        frequency: 3,
        description: '计划耗时经常低于实际耗时。',
        solutionText: '把估算乘以 1.5 再排期。',
        isArchived: false,
        createdAt: DateTime(2026, 3, 15),
        updatedAt: DateTime(2026, 3, 20),
      ),
    ];

LearningReport g05SeedReport() => const LearningReport(
      reportId: 'report-g05',
      markdown: '# 本周总结',
      sections: <String>['summary'],
      mastery: <LearningMasteryDatum>[
        LearningMasteryDatum(
          nodeName: '特征值',
          masteryScore: 82,
          nodeId: 'node-1',
          relatedErrorCount: 3,
        ),
        LearningMasteryDatum(nodeName: '特征向量', masteryScore: 76),
        LearningMasteryDatum(nodeName: '行列式', masteryScore: 58),
        LearningMasteryDatum(nodeName: '线性变换', masteryScore: 71),
      ],
    );

// ---------------------------------------------------------------------------
// 对比度复算工具（WCAG 2.x 相对亮度；与 F01 pixel_preview_theme_test 同公式）。
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

// ---------------------------------------------------------------------------
// 宿主：F05 同机制真实主题管道（ThemeManager 单例 → AppThemes.lightTheme），
// 扩展 router 形态与 MediaQuery 注入（reduce-motion 判定面）；G05 不生产
// 任何颜色/字号字面量。
// ---------------------------------------------------------------------------

Future<void> pumpProfileHost(
  WidgetTester tester,
  Widget child, {
  PixelPreviewProfile profile = PixelPreviewProfile.classic,
  GlobalKey? repaintKey,
  bool disableAnimations = false,
  GoRouter? router,
  Map<String, Object> initialPrefs = const <String, Object>{},
  List<Override> providerOverrides = const <Override>[],
  int settleMs = 700,
}) async {
  final manager = await freshThemeManager(initialPrefs: initialPrefs);
  await manager.setPixelPreviewProfile(profile);
  final mediaQuery = MediaQueryData(disableAnimations: disableAnimations);
  Widget tree;
  if (router != null) {
    tree = MaterialApp.router(
      routerConfig: router,
      theme: AppThemes.lightTheme,
      locale: const Locale('zh'),
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      builder: (context, navigator) => MediaQuery(
        data: mediaQuery,
        child: navigator ?? const SizedBox(),
      ),
    );
  } else {
    tree = MaterialApp(
      theme: AppThemes.lightTheme,
      builder: (context, navigator) => MediaQuery(
        data: mediaQuery,
        child: navigator ?? const SizedBox(),
      ),
      locale: const Locale('zh'),
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: child,
    );
  }
  if (providerOverrides.isNotEmpty) {
    tree = ProviderScope(overrides: providerOverrides, child: tree);
  }
  if (repaintKey != null) {
    tree = RepaintBoundary(key: repaintKey, child: tree);
  }
  await tester.pumpWidget(
    // ThemeManager 每 rebuild 重估主题（app.dart 同机制，F05 宿主同款）。
    AnimatedBuilder(
      animation: ThemeManager(),
      builder: (context, _) => tree,
    ),
  );
  // F05 同款固定时长泵：两拍覆盖主题过渡；settleMs=0 冻结首帧
  // （reduce-motion 控制组用：动画中段态可观察）。
  await tester.pump(const Duration(milliseconds: 200));
  if (settleMs > 0) {
    await tester.pump(Duration(milliseconds: settleMs));
  }
}

/// 证据落盘钩子（G05_EVIDENCE_DIR 存在时写 PNG + 语义文本树；常规跑零副作用）。
Future<void> writeG05Evidence(
  WidgetTester tester,
  GlobalKey repaintKey,
  String basename,
) async {
  final dir = io.Platform.environment['G05_EVIDENCE_DIR'];
  if (dir == null || dir.isEmpty) {
    return;
  }
  await tester.runAsync(() async {
    final outDir = io.Directory(dir);
    if (!outDir.existsSync()) {
      outDir.createSync(recursive: true);
    }
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(repaintKey),
    );
    final image = await boundary.toImage(pixelRatio: 2.0);
    final bytes = await image.toByteData(format: ImageByteFormat.png);
    io.File('${outDir.path}/$basename.png')
        .writeAsBytesSync(bytes!.buffer.asUint8List());
    final buffer = StringBuffer()
      ..writeln('seed=$kG05SeedVersion basename=$basename');
    void visit(Element element) {
      final widget = element.widget;
      if (widget is Text) {
        buffer.writeln(widget.data ?? widget.textSpan?.toPlainText());
      }
      element.visitChildren(visit);
    }

    visit(tester.binding.rootElement!);
    io.File('${outDir.path}/$basename${'_semantics.txt'}')
        .writeAsStringSync(buffer.toString());
  });
}


/// 雷达子树域内的图例断言（同屏同名静态行不干扰）。
Finder radarLegendOf(WidgetTester tester, String text) => find.descendant(
      of: find.byType(MasteryRadarChart),
      matching: find.text(text),
    );

/// 有界滚动直到组件挂载（报告面为懒构建长页；100ms 泵让拖拽弹道推进）。
/// 未挂载返回 false。
///
/// 首报里程碑庆祝对话框以 kG05MilestonePrefs 从源头消弹（G05 宿主
/// freshThemeManager 的 setMockInitialValues 会覆盖 setUp 的通道 mock）；
/// 此处不做 barrier 补偿——树内常驻 ModalBarrier 会让角落补点每轮多泵
/// 300ms，把雷达展开动画（400ms）在退出前老化为终值，破坏 C 组挂载帧
/// 观察。
Future<bool> scrollUntilMounted(
  WidgetTester tester,
  Finder finder, {
  int maxDrags = 40,
}) async {
  // 路由过渡完成后主滚动器才在册（实测 ≥300ms；此泵在雷达挂载前，
  // 不老化其展开动画）。
  await tester.pump(const Duration(milliseconds: 300));
  final vertical = find.byWidgetPredicate(
    (widget) =>
        widget is Scrollable && widget.axisDirection == AxisDirection.down,
  ).first;
  for (var i = 0; i < maxDrags && finder.evaluate().isEmpty; i++) {
    await tester.drag(vertical, const Offset(0, -300));
    await tester.pump(const Duration(milliseconds: 100));
  }
  return finder.evaluate().isNotEmpty;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    setUpI18nForTesting();
    // runAsync 真异步窗口（证据落盘）内不触平台通道：secure_storage 返回空、
    // SharedPreferences 返回空库（鉴权/历史缓存读取 fail-closed 降级）。
    TestWidgetsFlutterBinding.ensureInitialized().defaultBinaryMessenger
      ..setMockMethodCallHandler(
        const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
        (call) async => null,
      )
      ..setMockMethodCallHandler(
        const MethodChannel('plugins.flutter.io/shared_preferences'),
        (call) async => switch (call.method) {
          'getAll' => <String, Object>{
            'flutter.mirofish_milestone_v1:firstReport': true,
          },
          _ => true,
        },
      );
  });

  tearDown(tearDownI18n);

  // =========================================================================
  // A组 · 四风格对比度逐对复算（F06 判例：最终计算颜色；token 公式层）。
  // 每对 = 家族面实际消费的令牌公式；任一风格跌破阈值即红（调色板锚值
  // 漂移或修复点回退都会在此失败）。
  // =========================================================================
  group('A｜四风格对比度逐对复算（ACCESSIBILITY_ASSETS 阈值）', () {
    test('家族面修复对四风格逐对 ≥阈值（文本 4.5 / 图形 3.0）', () async {
      final failures = <String>[];
      for (final profile in PixelPreviewProfile.values) {
        SharedPreferences.setMockInitialValues(<String, Object>{});
        final manager = ThemeManager();
        await manager.reset();
        await manager.initialize();
        await manager.setPixelPreviewProfile(profile);
        final colors = manager.themeForBrightness(Brightness.light).colors;
        final cs = AppThemes.lightTheme.colorScheme;

        void check(String name, Color fg, Color bg, double threshold) {
          final ratio = contrastRatio(fg, bg);
          if (ratio < threshold) {
            failures.add(
              '$profile/$name=${ratio.toStringAsFixed(2)}<$threshold',
            );
          }
        }

        final pageBg = colors.surfaceAmbient;
        final glass = blendOver(colors.glassBackground, pageBg);
        final s1 = colors.surfacePrimary;
        final s2 = colors.surfaceSecondary;
        final s3 = colors.surfaceTertiary;

        // 认知定式卡（pattern_list_screen）。
        check('认知描述 textSecondary/glass', colors.textSecondary, glass, 4.5);
        check('认知页脚 textTertiary/glass', colors.textTertiary, glass, 4.5);
        check(
          '认知方案 success on success@20/255/glass',
          colors.semanticSuccess,
          blendOver(
            colors.semanticSuccess.withValues(alpha: 20 / 255),
            glass,
          ),
          4.5,
        );
        check(
          '认知类型标签 textSecondary/glass',
          colors.textSecondary,
          glass,
          4.5,
        );
        check(
          '认知类型图标 brandSecondary/glass',
          colors.brandSecondary,
          glass,
          3.0,
        );
        check('认知类型图标 info/glass', colors.semanticInfo, glass, 3.0);
        check('认知定式名 brandPrimary/glass', colors.brandPrimary, glass, 4.5);

        // 证据洞察卡（evidence_insight_card 要素标签 chip）。
        check(
          '证据chip brand on brand@0.05/s2',
          colors.brandPrimary,
          blendOver(colors.brandPrimary.withValues(alpha: 0.05), s2),
          4.5,
        );

        // 报告面（雷达 + 趋势 + 明细 pill + 部分数据 pill）。
        final chartBg = blendOver(
          cs.surfaceContainerHighest.withValues(alpha: 0.46),
          s1,
        );
        check('趋势主系列 cs.primary/chartBg', cs.primary, chartBg, 3.0);
        check(
          '趋势次系列 warning/chartBg',
          colors.semanticWarning,
          chartBg,
          3.0,
        );
        check(
          '雷达对比系列 textSecondary/chartBg',
          colors.textSecondary,
          chartBg,
          3.0,
        );
        check('雷达主系列 brand/s3', colors.brandPrimary, s3, 3.0);
        for (final entry in {
          'success': colors.semanticSuccess,
          'warning': colors.semanticWarning,
          'info': colors.semanticInfo,
        }.entries) {
          check(
            '掌握度pill ${entry.key} on @0.05/s2',
            entry.value,
            blendOver(entry.value.withValues(alpha: 0.05), s2),
            4.5,
          );
        }
        check(
          '部分pill warning on @0.05/s1',
          colors.semanticWarning,
          blendOver(colors.semanticWarning.withValues(alpha: 0.05), s1),
          4.5,
        );

        // 风险观察卡（全强度语义色 on 0.1 tint/s1）。
        for (final entry in {
          'low': colors.semanticSuccess,
          'medium': colors.brandPrimary,
          'high': colors.semanticError,
        }.entries) {
          check(
            '风险徽章 ${entry.key} on @0.1/s1',
            entry.value,
            blendOver(entry.value.withValues(alpha: 0.1), s1),
            4.5,
          );
        }
        check('风险副标题 textSecondary/s1', colors.textSecondary, s1, 4.5);

        // 热力图（insights 预测面消费；core/design 组件）。
        check('热力图标题图标 brand/s1', colors.brandPrimary, s1, 3.0);
        check('热力图高 success/s1', colors.semanticSuccess, s1, 3.0);

        // 复盘 hub（全令牌面抽查对）。
        check(
          'hub 副标题 textSecondary/surfacePanel',
          colors.textSecondary,
          colors.surfacePanel,
          4.5,
        );

        // 指令审计结果 pill（0.05 tint）。
        for (final entry in {
          'success': colors.semanticSuccess,
          'warning': colors.semanticWarning,
        }.entries) {
          check(
            '审计pill ${entry.key} on @0.05/s2',
            entry.value,
            blendOver(entry.value.withValues(alpha: 0.05), s2),
            4.5,
          );
        }

        // -- V4-G05 续扫（未触碰屏 + 触碰屏遗留点；公式 = 修复后代码）--
        final overlayCard = colors.surfaceOverlay;
        final pageSurface = colors.surfaceAmbient;

        // 概览 hero pill（info 文本 on info@0.1/card）。
        check(
          '概览hero pill info on @0.1/card',
          colors.semanticInfo,
          blendOver(colors.semanticInfo.withValues(alpha: 0.1), overlayCard),
          4.5,
        );
        // 指令审计时间线图标（info on info@0.1/card）。
        check(
          '审计时间线图标 info on @0.1/card',
          colors.semanticInfo,
          blendOver(colors.semanticInfo.withValues(alpha: 0.1), overlayCard),
          3.0,
        );
        // 概览模块卡图标（accent on accent@0.12/panel，全强度图标面）+
        // 推荐 pill（修复后：文本 textSecondary，tint 0.12 不变承载色彩）。
        final moduleAccents = <String, Color>{
          'cs.primary': cs.primary,
          'cs.tertiary': cs.tertiary,
          'info': colors.semanticInfo,
          'success': colors.semanticSuccess,
        };
        for (final entry in moduleAccents.entries) {
          check(
            '模块图标 ${entry.key} on @0.12/panel',
            entry.value,
            blendOver(entry.value.withValues(alpha: 0.12), colors.surfacePanel),
            3.0,
          );
          check(
            '推荐pill textPrimary on ${entry.key}@0.12/highlight',
            colors.textPrimary,
            blendOver(
              entry.value.withValues(alpha: 0.12),
              blendOver(
                entry.value.withValues(alpha: 0.05),
                colors.surfacePanel,
              ),
            ),
            4.5,
          );
        }
        // 成长编年史：入口图标（修复后 @0.05 circle/card；pattern_discovered
        // 用 secondaryDark 同源变暗档）+ 状态 pill（修复后：文本
        // textPrimary，tint 0.12 承载色彩）。secondaryDark = brandSecondary
        // 亮度 ∓0.15（DS 同式，随档亮度方向翻转）。
        Color secondaryDarkOf(Color base) {
          final dark = colors.brightness == Brightness.dark;
          final hsl = HSLColor.fromColor(base);
          final shifted = (hsl.lightness + (dark ? 0.15 : -0.15))
              .clamp(0.0, 1.0);
          return hsl.withLightness(shifted).toColor();
        }

        final chronicleAccents = <String, Color>{
          'cs.primary': cs.primary,
          'secondaryDark(cs.secondary)':
              secondaryDarkOf(cs.secondary),
          'cs.tertiary': cs.tertiary,
          'cs.error': cs.error,
        };
        for (final entry in chronicleAccents.entries) {
          check(
            '编年史图标 ${entry.key} on @0.05/card',
            entry.value,
            blendOver(entry.value.withValues(alpha: 0.05), overlayCard),
            3.0,
          );
          check(
            '编年史pill textPrimary on ${entry.key}@0.12/card',
            colors.textPrimary,
            blendOver(entry.value.withValues(alpha: 0.12), overlayCard),
            4.5,
          );
        }
        // 学习仪表盘弱点雷达：主系列描线 on 卡面。
        check(
          '仪表盘雷达主系列 cs.primary/card',
          cs.primary,
          overlayCard,
          3.0,
        );
        // 学习路径时间轴节点图标（statusColor on @0.2/card）。
        for (final entry in {
          'info': colors.semanticInfo,
          'success': colors.semanticSuccess,
          'error': colors.semanticError,
          'warning': colors.semanticWarning,
        }.entries) {
          check(
            '路径节点图标 ${entry.key} on @0.2/card',
            entry.value,
            blendOver(entry.value.withValues(alpha: 0.2), overlayCard),
            3.0,
          );
        }
        // 胶囊任务状态 pill（修复后 @0.05/s2）+ 失败框（修复后 @0.05/s2）。
        for (final entry in {
          'textSecondary': colors.textSecondary,
          'info': colors.semanticInfo,
          'success': colors.semanticSuccess,
          'error': colors.semanticError,
        }.entries) {
          check(
            '任务pill ${entry.key} on @0.05/s2',
            entry.value,
            blendOver(entry.value.withValues(alpha: 0.05), s2),
            4.5,
          );
        }
        check(
          '任务失败文本 error on @0.05/s2',
          colors.semanticError,
          blendOver(colors.semanticError.withValues(alpha: 0.05), s2),
          4.5,
        );
        // 胶囊详情深度 pill（修复后 @0.05/card）+ 选中筛选 chip（brand@0.05/s2）。
        for (final entry in {
          'info': colors.semanticInfo,
          'warning': colors.semanticWarning,
          'success': colors.semanticSuccess,
        }.entries) {
          check(
            '深度pill ${entry.key} on @0.05/card',
            entry.value,
            blendOver(entry.value.withValues(alpha: 0.05), overlayCard),
            4.5,
          );
        }
        check(
          '筛选chip brand on @0.05/s2',
          colors.brandPrimary,
          blendOver(colors.brandPrimary.withValues(alpha: 0.05), s2),
          4.5,
        );
        // 复盘 hub hero 渐变上的标题/副标题（修复后止点 brand@0.08 /
        // info@0.05）。
        for (final entry in {
          'brand@0.08': blendOver(
            colors.brandPrimary.withValues(alpha: 0.08),
            pageSurface,
          ),
          'info@0.05': blendOver(
            colors.semanticInfo.withValues(alpha: 0.05),
            pageSurface,
          ),
        }.entries) {
          check('hub hero 标题 on ${entry.key}', colors.textPrimary, entry.value, 4.5);
          check(
            'hub hero 副标题 on ${entry.key}',
            colors.textSecondary,
            entry.value,
            4.5,
          );
        }
        // 好奇胶囊 Tab 选中指示（修复后：tint 0.14 填充 + 全强度
        // capsuleAccent 描边作选中边界）。边界对（描边 vs s2 外侧）≥3:1。
        // capsuleAccent = brandSecondary 亮度 -0.05（light 档，DS 同式）。
        final capsuleAccent = HSLColor.fromColor(colors.brandSecondary)
            .withLightness(
              (HSLColor.fromColor(colors.brandSecondary).lightness - 0.05)
                  .clamp(0.0, 1.0),
            )
            .toColor();
        check(
          '胶囊tab指示边框 capsuleAccent vs s2',
          capsuleAccent,
          s2,
          3.0,
        );
        // 选中 tab 标签墨（textPrimary on capsuleAccent@0.14/s2 tint 底）
        // 仍需正文 4.5:1。
        check(
          '胶囊tab选中标签 textPrimary on capsuleAccent@0.14/s2',
          colors.textPrimary,
          blendOver(capsuleAccent.withValues(alpha: 0.14), s2),
          4.5,
        );
        // 报告面遗留修复点：徽章/标签/对比标签（修复后文本 textSecondary，
        // tint 结构不变）。
        final reportAccents = <String, Color>{
          'cs.primary': cs.primary,
          'cs.error': cs.error,
          'info': colors.semanticInfo,
          'success': colors.semanticSuccess,
          'warning': colors.semanticWarning,
          'brand': colors.brandPrimary,
        };
        for (final entry in reportAccents.entries) {
          check(
            '报告横幅图标 ${entry.key} on @0.14/card',
            entry.value,
            blendOver(entry.value.withValues(alpha: 0.14), overlayCard),
            3.0,
          );
          check(
            '报告徽章文本 textPrimary on ${entry.key}@0.12/@0.08',
            colors.textPrimary,
            blendOver(
              entry.value.withValues(alpha: 0.12),
              blendOver(entry.value.withValues(alpha: 0.08), overlayCard),
            ),
            4.5,
          );
        }
        // 报告 stat 单位文本（修复后 textPrimary on color@0.08/card）。
        for (final entry in {
          'info': colors.semanticInfo,
          'success': colors.semanticSuccess,
          'brand': colors.brandPrimary,
        }.entries) {
          check(
            '报告stat单位 textPrimary on ${entry.key}@0.08/card',
            colors.textPrimary,
            blendOver(entry.value.withValues(alpha: 0.08), overlayCard),
            4.5,
          );
        }
        // 报告图例 chip：textSecondary 文本 on warning/brand@0.1 底。
        for (final entry in {
          'warning': colors.semanticWarning,
          'brand': colors.brandPrimary,
        }.entries) {
          check(
            '图例文本 textSecondary on ${entry.key}@0.1/s1',
            colors.textSecondary,
            blendOver(entry.value.withValues(alpha: 0.1), s1),
            4.5,
          );
        }
        // 提示气泡图标（认知模块、home 消费）：info on info@0.1/ambient。
        check(
          '提示气泡图标 info on @0.1/ambient',
          colors.semanticInfo,
          blendOver(colors.semanticInfo.withValues(alpha: 0.1), pageSurface),
          3.0,
        );
      }
      expect(failures, isEmpty, reason: '对比度跌破阈值：$failures');
    });

    test('对照探针（活性）：修复前的呈现公式在 classic 确实低于阈值', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{});
      final manager = ThemeManager();
      await manager.reset();
      await manager.initialize();
      // classic（preview 关）——修复前的存量缺陷档。
      final colors = manager.themeForBrightness(Brightness.light).colors;
      final cs = AppThemes.lightTheme.colorScheme;
      final glass = blendOver(colors.glassBackground, colors.surfaceAmbient);
      final s1 = colors.surfacePrimary;
      final s2 = colors.surfaceSecondary;

      // 旧呈现公式逐一复核仍低于阈值（证明守卫可失败、非恒绿灯）。
      expect(
        contrastRatio(
          blendOver(
            colors.brandPrimary.withValues(alpha: 200 / 255),
            glass,
          ),
          glass,
        ),
        lessThan(4.5),
        reason: '旧描述正文 brand@200 应低于 4.5',
      );
      expect(
        contrastRatio(
          blendOver(
            colors.brandPrimary.withValues(alpha: 100 / 255),
            glass,
          ),
          glass,
        ),
        lessThan(4.5),
        reason: '旧页脚 brand@100 应低于 4.5',
      );
      expect(
        contrastRatio(
          colors.semanticSuccess,
          blendOver(
            colors.semanticSuccess.withValues(alpha: 0.12),
            s2,
          ),
        ),
        lessThan(4.5),
        reason: '旧 0.12 tint pill（classic success）应低于 4.5',
      );
      expect(
        contrastRatio(
          blendOver(cs.outline.withValues(alpha: 0.7), s1),
          s1,
        ),
        lessThan(3.0),
        reason: '旧雷达对比系列 outline@0.7 应低于 3.0',
      );
      expect(
        contrastRatio(
          blendOver(colors.semanticSuccess.withValues(alpha: 0.7), s1),
          s1,
        ),
        lessThan(3.0),
        reason: '旧风险图标 shade600（0.7 alpha）应低于 3.0',
      );
      // V4-G05 续扫修复点的对照探针（旧呈现公式在 classic 确实失败）。
      expect(
        contrastRatio(
          cs.secondary,
          blendOver(cs.secondary.withValues(alpha: 0.14), s1),
        ),
        lessThan(3.0),
        reason: '旧编年史入口图标 0.14 tint（cs.secondary）应低于 3.0',
      );
      expect(
        contrastRatio(
          colors.semanticError,
          blendOver(colors.semanticError.withValues(alpha: 0.15), s2),
        ),
        lessThan(4.5),
        reason: '旧任务状态 pill 0.15 tint（error 文本）应低于 4.5',
      );
      expect(
        contrastRatio(
          colors.brandPrimary,
          blendOver(colors.brandPrimary.withValues(alpha: 0.12), s2),
        ),
        lessThan(4.5),
        reason: '旧选中筛选 chip 0.12 tint（brand 文本）应低于 4.5',
      );
      expect(
        contrastRatio(
          colors.textSecondary,
          blendOver(
            colors.brandPrimary.withValues(alpha: 0.16),
            colors.surfaceAmbient,
          ),
        ),
        lessThan(4.5),
        reason: '旧 hub hero brand@0.16 止点上的副标题应低于 4.5',
      );
      final oldCapsuleAccent = HSLColor.fromColor(colors.brandSecondary)
          .withLightness(
            (HSLColor.fromColor(colors.brandSecondary).lightness - 0.05)
                .clamp(0.0, 1.0),
          )
          .toColor();
      expect(
        contrastRatio(
          blendOver(oldCapsuleAccent.withValues(alpha: 0.14), s2),
          s2,
        ),
        lessThan(3.0),
        reason: '旧胶囊 tab 选中指示 0.14 tint 应远低于 3.0',
      );
      expect(
        contrastRatio(
          blendOver(
            cs.primary.withValues(alpha: 0.12),
            blendOver(cs.primary.withValues(alpha: 0.08), s1),
          ),
          cs.primary,
        ),
        lessThan(4.5),
        reason: '旧报告徽章 accent 文本于嵌套 tint 应低于 4.5',
      );
    });
  });

  // =========================================================================
  // B组 · 修复点 widget 级钉（真实挂载读回最终呈现；revert 即红）。
  // =========================================================================
  group('B｜修复点 widget 级钉（classic 管道）', () {
    testWidgets('认知定式卡：描述/页脚/方案/类型标签走语义文本槽', (tester) async {
      final repaintKey = GlobalKey();
      final router = GoRouter(
        initialLocation: '/cognitive/patterns',
        routes: [
          GoRoute(
            path: '/cognitive/patterns',
            builder: (_, __) => const PatternListScreen(),
          ),
          GoRoute(
            path: '/focus',
            builder: (_, __) => const Scaffold(body: Text('FOCUS')),
          ),
        ],
      );
      await pumpProfileHost(
        tester,
        const SizedBox.shrink(),
        router: router,
        repaintKey: repaintKey,
        providerOverrides: [
          cognitiveProvider.overrideWith(
            (ref) => _SeededCognitiveNotifier(g05SeedPatterns()),
          ),
          apiClientProvider.overrideWithValue(_G05NoopApiClient()),
        ],
      );

      // 描述正文 = textSecondary（非 brand@200 透明度压文字）。
      final description = tester.widget<Text>(
        find.text('计划耗时经常低于实际耗时。'),
      );
      expect(description.style?.color, DS.textSecondary);
      // 方案文本 = textPrimary（G03 四风格对比度复算升位：success 轻档
      // 合成底仅 2.12-2.88:1，关键正文走 textPrimary 全档 ≥8.07:1；
      // 语义色保留在灯泡图标——取代 G05 首版 success 全强度钉）。
      final solution = tester.widget<Text>(
        find.textContaining('把估算乘以 1.5'),
      );
      expect(solution.style?.color, DS.textPrimary);
      // 页脚时间戳 = textSecondary（G03 复算升位：brandPrimary@0.392 衰减
      // 文字五档 1.71-2.38:1 全崩，脚注走 textSecondary 全档 ≥4.85:1——
      // 取代 G05 首版 textTertiary 定标槽）。
      final footer = tester.widget<Text>(find.textContaining('发现于'));
      expect(footer.style?.color, DS.textSecondary);
      // 类型标签 = textSecondary（类型色只承载图标）。
      final typeLabel = tester.widget<Text>(
        find.text(S.patternTypeCognitive),
      );
      expect(typeLabel.style?.color, DS.textSecondary);
      expect(tester.takeException(), isNull);

      await writeG05Evidence(
        tester,
        repaintKey,
        'g05_pattern_card_classic_360x800',
      );
    });

    testWidgets('证据洞察卡：要素标签 chip 底 0.05（回退 0.08 即红）', (tester) async {
      final repaintKey = GlobalKey();
      await pumpProfileHost(
        tester,
        SingleChildScrollView(
          child: EvidenceInsightCardWidget(card: g05SeedCard()),
        ),
        repaintKey: repaintKey,
      );
      final expected = DS.brandPrimary.withValues(alpha: 0.05);
      final chip = tester.widgetList<Container>(
        find.byWidgetPredicate(
          (widget) =>
              widget is Container &&
              widget.decoration is BoxDecoration &&
              (widget.decoration as BoxDecoration).color == expected,
        ),
      );
      expect(chip, isNotEmpty, reason: '要素标签 chip 应为 brand@0.05 底');
      expect(tester.takeException(), isNull);

      await writeG05Evidence(
        tester,
        repaintKey,
        'g05_evidence_card_classic_360x800',
      );
    });

    testWidgets('风险观察卡：徽章文本全强度语义色 + 副标题 textSecondary',
        (tester) async {
      await pumpProfileHost(
        tester,
        const SingleChildScrollView(
          child: RiskObservationCard(
            data: <String, dynamic>{
              'risk_level': 'low',
              'intervention_suggestions': <String>['先完成当前任务'],
            },
          ),
        ),
      );
      // 低风险徽章文本 = 全强度 success（非 shade600 透明度压色）。
      final badge = tester.widget<Text>(find.text('低风险'));
      expect(badge.style?.color, DS.success);
      expect(tester.takeException(), isNull);
    });

    testWidgets('热力图：标题/统计图标全强度 brand（非 shade600）', (tester) async {
      final now = DateTime(2026, 9, 20);
      await pumpProfileHost(
        tester,
        SingleChildScrollView(
          child: EngagementHeatmap(
            data: <DateTime, double>{
              DateTime(now.year, now.month, now.day): 0.8,
            },
            daysToShow: 21,
          ),
        ),
      );
      final fullStrength = tester.widgetList<Icon>(
        find.byWidgetPredicate(
          (widget) => widget is Icon && widget.color == DS.brandPrimary,
        ),
      );
      expect(
        fullStrength.length,
        greaterThanOrEqualTo(2),
        reason: '标题图标 + 统计图标应为全强度 brandPrimary',
      );
      final faded = tester.widgetList<Icon>(
        find.byWidgetPredicate(
          (widget) =>
              widget is Icon &&
              widget.color == DS.brandPrimary.withValues(alpha: 0.7),
        ),
      );
      expect(faded, isEmpty, reason: '不应再有 0.7 透明度压色图标');
      expect(tester.takeException(), isNull);
    });
  });

  // =========================================================================
  // C组 · reduce-motion 等价（S01 判例：低动态直落终态 + 控制组活性）。
  // =========================================================================
  group('C｜报告面 reduce-motion 等价', () {
    GoRouter reportRouter() => GoRouter(
          initialLocation: '/learning-report',
          routes: [
            GoRoute(
              path: '/learning-report',
              builder: (_, __) => LearningReportScreen(report: g05SeedReport()),
            ),
            GoRoute(
              path: '/galaxy',
              builder: (_, __) => const Scaffold(body: Text('GALAXY_HOME')),
            ),
            GoRoute(
              path: '/galaxy/node/:id',
              builder: (_, __) => const Scaffold(body: Text('NODE_OK')),
            ),
          ],
        );

    Finder radarLegend(String text) => find.descendant(
          of: find.byType(MasteryRadarChart),
          matching: find.text(text),
        );

    testWidgets('reduce-motion：雷达挂载即终值（不跑展开动画）', (tester) async {
      // U13 同款 360 逻辑宽视口（800 宽下拖拽起点会落到内容列外导致
      // hit-test miss，无法滚动）。
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(360, 800) * 2.0;
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
      });
      await pumpProfileHost(
        tester,
        const SizedBox.shrink(),
        router: reportRouter(),
        disableAnimations: true,
        settleMs: 0,
        initialPrefs: kG05MilestonePrefs,
        providerOverrides: [
          apiClientProvider.overrideWithValue(_G05NoopApiClient()),
        ],
      );
      // 滚动至雷达（懒构建挂载即触发一次建帧）；低动态偏好下雷达展开
      // 直落终态——挂载后图例立即是终值 82%（Duration.zero）。
      expect(
        await scrollUntilMounted(tester, find.byType(MasteryRadarChart)),
        isTrue,
      );
      expect(radarLegend('特征值 82%'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('控制组：无 reduce-motion 时动画通道真实存在（挂载帧非终值）',
        (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(360, 800) * 2.0;
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
      });
      await pumpProfileHost(
        tester,
        const SizedBox.shrink(),
        router: reportRouter(),
        settleMs: 0,
        initialPrefs: kG05MilestonePrefs,
        providerOverrides: [
          apiClientProvider.overrideWithValue(_G05NoopApiClient()),
        ],
      );
      // 控制点（挂载帧观察）：scrollUntilMounted 在雷达挂载后 ≤100ms
      // 退出——雷达展开动画（durationSlow=400ms）仍在早段，scoped 图例
      // 为中段值（实测挂载帧 49%），证明动画通道真实存在（reduce-motion
      // 关；对照 reduce-motion 组挂载即终值的 Duration.zero 直落分支）。
      expect(
        await scrollUntilMounted(tester, find.byType(MasteryRadarChart)),
        isTrue,
      );
      expect(find.byType(MasteryRadarChart), findsOneWidget);
      expect(
        radarLegend('特征值 82%'),
        findsNothing,
        reason: '无 reduce-motion 时雷达展开动画在跑，挂载帧非终值',
      );
      // 落定后终态出现（与 reduce-motion 落定终态等价，S01 判例）。
      await tester.pumpAndSettle();
      expect(radarLegend('特征值 82%'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  // =========================================================================
  // D组 · 200% 文本（SCREEN_FAMILIES 检查表 + F01 判例）。
  // =========================================================================
  group('D｜200% 文本：三读面无溢出/无异常', () {
    testWidgets('认知定式卡 200%（paperDay）无异常、定式名在册', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(360, 1600) * 2.0;
      tester.view.platformDispatcher.textScaleFactorTestValue = 2.0;
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
        tester.view.platformDispatcher.clearTextScaleFactorTestValue();
      });
      final router = GoRouter(
        initialLocation: '/cognitive/patterns',
        routes: [
          GoRoute(
            path: '/cognitive/patterns',
            builder: (_, __) => const PatternListScreen(),
          ),
          GoRoute(
            path: '/focus',
            builder: (_, __) => const Scaffold(body: Text('FOCUS')),
          ),
        ],
      );
      await pumpProfileHost(
        tester,
        const SizedBox.shrink(),
        profile: PixelPreviewProfile.paperDay,
        router: router,
        providerOverrides: [
          cognitiveProvider.overrideWith(
            (ref) => _SeededCognitiveNotifier(g05SeedPatterns()),
          ),
          apiClientProvider.overrideWithValue(_G05NoopApiClient()),
        ],
      );
      expect(tester.takeException(), isNull, reason: '200% 下认知卡无溢出异常');
      expect(find.textContaining('计划乐观偏差'), findsWidgets);
    });

    testWidgets('报告面 200%（dusk）无异常、定义行可读', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(360, 3200) * 2.0;
      tester.view.platformDispatcher.textScaleFactorTestValue = 2.0;
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
        tester.view.platformDispatcher.clearTextScaleFactorTestValue();
      });
      final router = GoRouter(
        initialLocation: '/learning-report',
        routes: [
          GoRoute(
            path: '/learning-report',
            builder: (_, __) => LearningReportScreen(report: g05SeedReport()),
          ),
          GoRoute(
            path: '/galaxy',
            builder: (_, __) => const Scaffold(body: Text('GALAXY_HOME')),
          ),
        ],
      );
      await pumpProfileHost(
        tester,
        const SizedBox.shrink(),
        profile: PixelPreviewProfile.dusk,
        router: router,
        providerOverrides: [
          apiClientProvider.overrideWithValue(_G05NoopApiClient()),
        ],
      );
      expect(tester.takeException(), isNull, reason: '200% 下报告面无溢出异常');
      expect(find.textContaining('掌握度＝星图能力节点的证据融合值'), findsWidgets);
    });

    testWidgets('证据洞察卡 200%（quiet）无异常、要素行在册', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(360, 1600) * 2.0;
      tester.view.platformDispatcher.textScaleFactorTestValue = 2.0;
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
        tester.view.platformDispatcher.clearTextScaleFactorTestValue();
      });
      await pumpProfileHost(
        tester,
        SingleChildScrollView(
          child: EvidenceInsightCardWidget(card: g05SeedCard()),
        ),
        profile: PixelPreviewProfile.quiet,
      );
      expect(tester.takeException(), isNull, reason: '200% 下证据卡无溢出异常');
      expect(find.textContaining('样本＝去重后方向观察 2 条'), findsOneWidget);
    });
  });

  // =========================================================================
  // E组 · 三读面×四风格语义钉 + 状态覆盖（无数据 / 复盘 hub 空态）。
  // =========================================================================
  group('E｜三读面×四风格语义钉（每风格 golden 语义面）', () {
    for (final profile in PixelPreviewProfile.values) {
      testWidgets('$profile：证据洞察卡诚实行全量呈现', (tester) async {
        tester.view.devicePixelRatio = 2.0;
        tester.view.physicalSize = const Size(360, 800) * 2.0;
        addTearDown(() {
          tester.view.resetDevicePixelRatio();
          tester.view.resetPhysicalSize();
        });
        final repaintKey = GlobalKey();
        await pumpProfileHost(
          tester,
          SingleChildScrollView(
            child: EvidenceInsightCardWidget(card: g05SeedCard()),
          ),
          profile: profile,
          repaintKey: repaintKey,
        );
        // 撤回排除 / 理解档 / 样本量定义 / 零惩罚可拒绝行，四风格逐字一致。
        expect(find.textContaining('已排除 2 条'), findsOneWidget);
        expect(find.textContaining('证据不足：1 条结果未到期'), findsOneWidget);
        expect(find.textContaining('样本＝去重后方向观察 2 条'), findsOneWidget);
        expect(find.textContaining('可以忽略'), findsOneWidget);
        expect(
          find.textContaining('%'),
          findsNothing,
          reason: 'D-07 卡契约禁百分比，四风格呈现面均不引入',
        );
        expect(tester.takeException(), isNull);
        await writeG05Evidence(
          tester,
          repaintKey,
          'g05_evidence_card_${profile.name}_360x800',
        );
      });

      testWidgets('$profile：报告面定义行与认知观察档', (tester) async {
        tester.view.devicePixelRatio = 2.0;
        tester.view.physicalSize = const Size(360, 800) * 2.0;
        addTearDown(() {
          tester.view.resetDevicePixelRatio();
          tester.view.resetPhysicalSize();
        });
        final repaintKey = GlobalKey();
        final router = GoRouter(
          initialLocation: '/learning-report',
          routes: [
            GoRoute(
              path: '/learning-report',
              builder: (_, __) =>
                  LearningReportScreen(report: g05SeedReport()),
            ),
            GoRoute(
              path: '/cognitive/patterns',
              builder: (_, __) => const PatternListScreen(),
            ),
            GoRoute(
              path: '/galaxy',
              builder: (_, __) => const Scaffold(body: Text('GALAXY_HOME')),
            ),
            GoRoute(
              path: '/focus',
              builder: (_, __) => const Scaffold(body: Text('FOCUS')),
            ),
          ],
        );
        await pumpProfileHost(
          tester,
          const SizedBox.shrink(),
          profile: profile,
          router: router,
          repaintKey: repaintKey,
          initialPrefs: kG05MilestonePrefs,
          providerOverrides: [
            apiClientProvider.overrideWithValue(_G05NoopApiClient()),
            cognitiveProvider.overrideWith(
              (ref) => _SeededCognitiveNotifier(g05SeedPatterns()),
            ),
          ],
        );
        // 报告面为懒构建长页（U13 同款固定泵 + 有界滚动，pumpAndSettle
        // 在本面不落定——面内存在真实重复动画）。
        await tester.pump(const Duration(milliseconds: 150));
        await tester.pump(const Duration(milliseconds: 350));
        // 掌握度定义行在首屏之下、雷达之上：先滚到定义行断言（懒构建
        // ——滚过即拆），再继续滚到雷达。
        expect(
          await scrollUntilMounted(
            tester,
            find.textContaining('掌握度＝星图能力节点的证据融合值'),
          ),
          isTrue,
        );
        expect(find.textContaining('掌握度＝星图能力节点的证据融合值'), findsOneWidget);
        expect(
          await scrollUntilMounted(tester, find.byType(MasteryRadarChart)),
          isTrue,
        );
        await tester.pumpAndSettle();
        // 雷达图例终值（域取雷达子树，同名静态行不干扰）+ 轴读数说明随行。
        expect(radarLegendOf(tester, '特征值 82%'), findsOneWidget);
        expect(find.textContaining('图上每个轴是一条 0–100 的证据融合掌握度读数'), findsOneWidget);
        // 认知读面：观察档由真实计数派生（同宿主第二入口）。
        router.go('/cognitive/patterns');
        await tester.pump(const Duration(milliseconds: 100));
        await tester.pumpAndSettle();
        expect(find.text('多次观察到'), findsOneWidget);
        expect(find.textContaining('置信'), findsNothing);
        expect(tester.takeException(), isNull);
        await writeG05Evidence(
          tester,
          repaintKey,
          'g05_report_${profile.name}_360x800',
        );
      });
    }

    testWidgets('无数据态：feed 合法零卡 → 显式「还没有可分析的行为记录」（dusk 抽查）',
        (tester) async {
      final repaintKey = GlobalKey();
      await pumpProfileHost(
        tester,
        const SingleChildScrollView(child: EvidenceInsightSection()),
        profile: PixelPreviewProfile.dusk,
        repaintKey: repaintKey,
        providerOverrides: [
          evidenceInsightFeedProvider.overrideWith(
            (ref) async => EvidenceInsightFeedData.fromJson(
              <String, dynamic>{
                'presentation_schema': 'insight.presentation.v1',
                'cards': <dynamic>[],
              },
            ),
          ),
        ],
      );
      expect(find.textContaining('还没有可分析的行为记录'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await writeG05Evidence(
        tester,
        repaintKey,
        'g05_evidence_nodata_dusk_360x800',
      );
    });

    testWidgets('复盘 hub 空态（quiet 抽查）：标题/今日清单/夜间复盘在册',
        (tester) async {
      final repaintKey = GlobalKey();
      await pumpProfileHost(
        tester,
        const ReviewPlanHubScreen(),
        profile: PixelPreviewProfile.quiet,
        repaintKey: repaintKey,
        providerOverrides: [
          apiClientProvider.overrideWithValue(_G05NoopApiClient()),
          todayReviewListProvider.overrideWith((ref) async => const []),
          nightlyReviewProvider.overrideWith((ref) async => null),
          dashboardProvider.overrideWith((ref) => _StaticDashboardNotifier()),
          planListProvider.overrideWith((ref) => _StaticPlanNotifier()),
          taskListProvider.overrideWith((ref) => _StaticTaskNotifier()),
        ],
      );
      expect(find.text(S.reviewPlanHubTitle), findsOneWidget);
      expect(find.text(S.reviewPlanHubNoDueErrors), findsOneWidget);
      expect(find.text(S.reviewPlanHubNoNightlyReview), findsOneWidget);
      // V4-G05 hero 渐变止点钉（回退 0.16/0.1 即红）：textSecondary 副标题
      // 于 brand@0.16 止点 classic 4.37:1 <4.5:1，0.08 起四风格达标。
      final heroContainer = tester.widgetList<Container>(
        find.byWidgetPredicate(
          (widget) =>
              widget is Container &&
              widget.decoration is BoxDecoration &&
              (widget.decoration as BoxDecoration).gradient
                  is LinearGradient &&
              ((widget.decoration as BoxDecoration).gradient!
                      as LinearGradient)
                  .colors
                  .contains(DS.brandPrimary.withValues(alpha: 0.08)),
        ),
      );
      expect(
        heroContainer,
        isNotEmpty,
        reason: 'hero 渐变应为 brand@0.08 → info@0.05（修复后止点）',
      );
      expect(tester.takeException(), isNull);
      await writeG05Evidence(
        tester,
        repaintKey,
        'g05_review_hub_quiet_360x800',
      );
    });
  });
}

// ---------------------------------------------------------------------------
// 测试替身（离线合同；与 U13/review hub 测试同口径）。
// ---------------------------------------------------------------------------

class _G05NoopApiClient extends Fake implements ApiClient {}

class _UnusedApiClient extends Fake implements ApiClient {}

class _SeededCognitiveNotifier extends CognitiveNotifier {
  _SeededCognitiveNotifier(List<BehaviorPatternModel> patterns)
      : _seed = patterns,
        super(_EmptyRepo());

  final List<BehaviorPatternModel> _seed;

  @override
  Future<void> loadPatterns() async {
    state = CognitiveState(patterns: _seed);
  }
}

class _EmptyRepo implements ICognitiveRepository {
  @override
  Future<CognitiveFragmentModel> createFragment(
    CognitiveFragmentCreate data,
  ) async =>
      throw UnimplementedError();

  @override
  Future<List<CognitiveFragmentModel>> getFragments({
    int? limit,
    int? skip,
  }) async =>
      const [];

  @override
  Future<List<BehaviorPatternModel>> getBehaviorPatterns() async => const [];
}

class _StaticDashboardNotifier extends DashboardNotifier {
  _StaticDashboardNotifier() : super(_UnusedDashboardRepository()) {
    state = DashboardState(
      weather: WeatherData(type: 'sunny', condition: 'clear'),
      flame: FlameData(level: 1, brightness: 0.5, todayFocusMinutes: 0),
      sprint: null,
      nextActions: const [],
      cognitive: CognitiveData(status: 'empty'),
    );
  }

  @override
  Future<void> fetchData() async {}
}

class _UnusedDashboardRepository extends DashboardRepository {
  _UnusedDashboardRepository() : super(_UnusedApiClient());
}

class _StaticPlanNotifier extends PlanNotifier {
  _StaticPlanNotifier() : super(_UnusedPlanRepository(), _UnusedRef());

  @override
  Future<void> loadPlans({PlanType? type}) async {}

  @override
  Future<void> loadActivePlans() async {}

  @override
  Future<void> refresh() async {}
}

class _UnusedPlanRepository extends Fake implements PlanRepository {}

class _StaticTaskNotifier extends TaskNotifier {
  _StaticTaskNotifier()
      : super(
          _UnusedTaskRepository(),
          _UnusedTaskNotificationScheduler(),
          _UnusedRef(),
        ) {
    state = TaskListState();
  }

  @override
  Future<void> loadTasks({TaskFilter? filter}) async {}

  @override
  Future<void> loadTodayTasks() async {}

  @override
  Future<void> loadRecommendedTasks() async {}

  @override
  Future<void> refreshTasks() async {}
}

class _UnusedTaskRepository extends Fake implements TaskRepository {}

class _UnusedTaskNotificationScheduler extends Fake
    implements TaskNotificationScheduler {}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
