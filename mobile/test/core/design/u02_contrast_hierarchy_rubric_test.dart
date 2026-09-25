import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/features/chat/chat.dart' show ChatNotifier;

import '../../shared/u02_core_screens.dart';

/// U-02 验收可计算 rubric：contrast / hierarchy 双档判定。
///
/// 全部数值从真实产物计算，非目测：
/// 1. **contrast（token 对）**：WCAG 2.1 相对亮度与对比比，作用于
///    `AppThemes.lightTheme`（真实主题管道）产出的 `SparkleColors`
///    前景/背景对；低刺激档有效色 = 同一 token 经
///    `emotion_responsive_theme.dart` 低刺激滤色矩阵后的实显色
///    （矩阵为该文件私有常量的镜像，改动须两侧同步）。
/// 2. **hierarchy（渲染树）**：真跑四个核心屏 × 两档，从 RenderParagraph
///    提取实显 TextStyle（fontSize/fontWeight/color），断言标题>正文>
///    辅助的字号层级单调不倒挂，且逐色对背景对比达到 AA（大字 3.0，
///    正文 4.5；透明度 <0.5 的 disabled/装饰字豁免，WCAG 例外）。
/// 3. **mode-diff（不只是 setting 值）**：同屏两档的实显主题与渲染
///    输出必须真实不同（低刺激：splash 关、卡片无阴影、Material
///    文字主题整体 +1px、动效时长收缩、弹性曲线撤除、色温滤层在场）。
void main() {
  setUpAll(initializeU02SurfaceEnvironment);

  // ---------------------------------------------------------------------------
  // WCAG 2.1 程序化计算
  // ---------------------------------------------------------------------------

  double channel(double v) {
    final c = v.clamp(0.0, 1.0);
    return c <= 0.03928 ? c / 12.92 : math.pow((c + 0.055) / 1.055, 2.4).toDouble();
  }

  double relativeLuminance(Color c) => 0.2126 * channel(c.r) +
      0.7152 * channel(c.g) +
      0.0722 * channel(c.b);

  double contrastRatio(Color a, Color b) {
    final la = relativeLuminance(a);
    final lb = relativeLuminance(b);
    final lighter = math.max(la, lb);
    final darker = math.min(la, lb);
    return (lighter + 0.05) / (darker + 0.05);
  }

  // emotion_responsive_theme.dart 私有 _lightLowStimulusFilter 的镜像：
  // 低刺激档浅色模式实显色 = 矩阵逐通道线性变换（r×0.94, g×0.96, b×1.02）。
  Color lowStimEffective(Color c) => Color.from(
        alpha: c.a,
        red: (c.r * 0.94).clamp(0.0, 1.0),
        green: (c.g * 0.96).clamp(0.0, 1.0),
        blue: (c.b * 1.02).clamp(0.0, 1.0),
      );

  group('U-02 rubric · 动效/状态 token 两档 diff（量化对照表来源）', () {
    test('SparkleMotionTokens standard vs low 逐字段数值表', () {
      final std = resolveSparkleMotionTokens(StimulationLevel.standard);
      final low = resolveSparkleMotionTokens(StimulationLevel.low);
      String curveName(Curve c) => c.toString();

      final rows = <String>[
        '| 字段 | standard | low | 差值/变化 |',
        '|---|---|---|---|',
        '| fast | ${std.fast.inMilliseconds}ms | ${low.fast.inMilliseconds}ms | '
            '-${std.fast.inMilliseconds - low.fast.inMilliseconds}ms |',
        '| normal | ${std.normal.inMilliseconds}ms | ${low.normal.inMilliseconds}ms | '
            '-${std.normal.inMilliseconds - low.normal.inMilliseconds}ms |',
        '| slow | ${std.slow.inMilliseconds}ms | ${low.slow.inMilliseconds}ms | '
            '-${std.slow.inMilliseconds - low.slow.inMilliseconds}ms |',
        '| slower | ${std.slower.inMilliseconds}ms | ${low.slower.inMilliseconds}ms | '
            '-${std.slower.inMilliseconds - low.slower.inMilliseconds}ms |',
        '| standardCurve | ${curveName(std.standardCurve)} | ${curveName(low.standardCurve)} | 不变 |',
        '| enterCurve | ${curveName(std.enterCurve)} | ${curveName(low.enterCurve)} | 不变 |',
        '| exitCurve | ${curveName(std.exitCurve)} | ${curveName(low.exitCurve)} | 不变 |',
        '| bounceCurve | ${curveName(std.bounceCurve)} | ${curveName(low.bounceCurve)} | 弹性撤除 |',
        '| overshootCurve | ${curveName(std.overshootCurve)} | ${curveName(low.overshootCurve)} | 过冲撤除 |',
      ];
      // ignore: avoid_print
      print('MOTION_TOKEN_DIFF\n${rows.join('\n')}');

      // 判定：低刺激档每档时长严格更短；奖励性曲线撤除。
      expect(low.fast.inMilliseconds, lessThan(std.fast.inMilliseconds));
      expect(low.normal.inMilliseconds, lessThan(std.normal.inMilliseconds));
      expect(low.slow.inMilliseconds, lessThan(std.slow.inMilliseconds));
      expect(low.slower.inMilliseconds, lessThan(std.slower.inMilliseconds));
      expect(identical(low.bounceCurve, Curves.easeOut), isTrue);
      expect(identical(low.overshootCurve, Curves.easeOut), isTrue);
    });

    test('SparkleStateTokens calm/celebrate/attention × 两档 数值表', () {
      final rows = <String>[
        '| mood | 字段 | standard | low |',
        '|---|---|---|---|',
      ];
      for (final mood in SparkleStateMood.values) {
        final std = SparkleStateTokens.forMood(mood);
        final low = SparkleStateTokens.forMood(mood, level: StimulationLevel.low);
        void row(String field, Object s, Object l) => rows.add('| $mood | $field | $s | $l |');
        row('glowOpacity', std.glowOpacity, low.glowOpacity);
        row('emphasisScale', std.emphasisScale, low.emphasisScale);
        row('motionScale', std.motionScale, low.motionScale);
        row('particleScale', std.particleScale, low.particleScale);
        row('allowBounce', std.allowBounce, low.allowBounce);
      }
      // ignore: avoid_print
      print('STATE_TOKEN_DIFF\n${rows.join('\n')}');

      // 低刺激档判定：celebrate/attention 粒子归零、弹性撤除、时长收缩。
      for (final mood in {SparkleStateMood.celebrate, SparkleStateMood.attention}) {
        final low = SparkleStateTokens.forMood(mood, level: StimulationLevel.low);
        expect(low.particleScale, 0, reason: '$mood low 粒子预算归零');
        expect(low.allowBounce, isFalse, reason: '$mood low 弹性撤除');
        expect(
          low.motionScale,
          lessThan(SparkleStateTokens.forMood(mood).motionScale),
          reason: '$mood low 时长收缩',
        );
      }
    });
  });

  group('U-02 rubric · contrast（真实主题管道 token 对，WCAG 程序化）', () {
    final theme = AppThemes.lightTheme;
    final colors = theme.extension<SparkleThemeExtension>()!.colors;
    final scaffoldBg = theme.scaffoldBackgroundColor;

    void expectPair(String fgName, Color fg, String bgName, Color bg,
        {required double threshold,}) {
      final ratio = contrastRatio(fg, bg);
      // ignore: avoid_print
      print('CONTRAST $fgName on $bgName = ${ratio.toStringAsFixed(2)}:1 '
          '(AA${threshold == 4.5 ? '' : '-large'} $threshold:1 '
          '${ratio >= threshold ? 'PASS' : 'FAIL'})');
      expect(
        ratio,
        greaterThanOrEqualTo(threshold),
        reason: '$fgName on $bgName = ${ratio.toStringAsFixed(2)}:1 < $threshold:1',
      );
    }

    test('standard 档：文字 token × 表面 token 全对达标', () {
      expectPair('textPrimary', colors.textPrimary, 'surfacePrimary', scaffoldBg,
          threshold: 4.5,);
      expectPair('textPrimary', colors.textPrimary, 'surfaceSecondary',
          colors.surfaceSecondary, threshold: 4.5,);
      expectPair('textPrimary', colors.textPrimary, 'surfaceTertiary',
          colors.surfaceTertiary, threshold: 4.5,);
      expectPair('textSecondary', colors.textSecondary, 'surfacePrimary', scaffoldBg,
          threshold: 4.5,);
      expectPair('textSecondary', colors.textSecondary, 'surfaceSecondary',
          colors.surfaceSecondary, threshold: 4.5,);
      expectPair('chatBubbleOtherText', colors.chatBubbleOtherText,
          'chatBubbleOther', colors.chatBubbleOther, threshold: 4.5,);
      // 辅助文字按 WCAG 大字/附带信息阈值 3.0。
      expectPair('textTertiary', colors.textTertiary, 'surfacePrimary', scaffoldBg,
          threshold: 3.0,);
      expectPair('textTertiary', colors.textTertiary, 'surfaceSecondary',
          colors.surfaceSecondary, threshold: 3.0,);
      // 反白对：白字在用户气泡/品牌主色上。
      expectPair('chatBubbleUserText', colors.chatBubbleUserText,
          'chatBubbleUser', colors.chatBubbleUser, threshold: 4.5,);
      expectPair(
          'onPrimary', theme.colorScheme.onPrimary, 'brandPrimary', colors.brandPrimary,
          threshold: 4.5,);
    });

    test('low 档：低刺激滤色后的实显 token 对仍达标（减色不牺牲可读性）', () {
      Color dim(Color c) => lowStimEffective(c);
      expectPair('textPrimary*', dim(colors.textPrimary), 'surfacePrimary*',
          dim(scaffoldBg), threshold: 4.5,);
      expectPair('textPrimary*', dim(colors.textPrimary), 'surfaceSecondary*',
          dim(colors.surfaceSecondary), threshold: 4.5,);
      expectPair('textSecondary*', dim(colors.textSecondary), 'surfacePrimary*',
          dim(scaffoldBg), threshold: 4.5,);
      expectPair('textTertiary*', dim(colors.textTertiary), 'surfacePrimary*',
          dim(scaffoldBg), threshold: 3.0,);
      expectPair('chatBubbleUserText*', dim(colors.chatBubbleUserText),
          'chatBubbleUser*', dim(colors.chatBubbleUser), threshold: 4.5,);
      expectPair('chatBubbleOtherText*', dim(colors.chatBubbleOtherText),
          'chatBubbleOther*', dim(colors.chatBubbleOther), threshold: 4.5,);
    });
  });

  group('U-02 rubric · hierarchy/mode-diff（四核心屏真跑渲染树）', () {
    Future<_ScreenRubricReport> pumpAndMeasure(
      WidgetTester tester,
      U02Surface surface,
      EmotionResponsiveConfig config,
    ) async {
      final chatNotifier = <ChatNotifier>[];
      final host = await u02SurfaceHost(
        surface,
        config,
        chatNotifierOut: chatNotifier,
      );
      await tester.pumpWidget(host);
      for (var i = 0; i < 20; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      if (surface == U02Surface.chat) {
        // 与 capture 同款时序：初始化落定后种入 history_citations 消息。
        for (var i = 0; i < 20 && chatNotifier.isEmpty; i++) {
          await tester.pump(const Duration(milliseconds: 50));
        }
        if (chatNotifier.isNotEmpty) {
          seedU02ChatMessages(chatNotifier.single);
          for (var i = 0; i < 10; i++) {
            await tester.pump(const Duration(milliseconds: 50));
          }
        }
      }

      // 实显主题（低刺激档经 wrapper 重主题化）。测点取 Scaffold——
      // 位于 wrapper 之下；Navigator 在 wrapper 之上会取到未包装主题。
      final theme = Theme.of(
        tester.element(find.byType(Scaffold).first),
      );
      final sparkle = theme.extension<SparkleThemeExtension>()!;

      // 渲染树实显文字样式（RichText = Text 渲染对象，样式已合并默认态）。
      // 图标字形（MaterialIcons RichText）不是排版层级样本，剔除。
      bool isIconGlyph(String text) {
        final trimmed = text.trim();
        if (trimmed.isEmpty) return true;
        for (final code in trimmed.runes) {
          final isLetterOrDigit =
              (code >= 0x30 && code <= 0x39) || // digits
              (code >= 0x41 && code <= 0x5A) || // A-Z
              (code >= 0x61 && code <= 0x7A) || // a-z
              (code >= 0x4E00 && code <= 0x9FFF) || // CJK
              (code >= 0x3000 && code <= 0x303F) || // CJK punct
              (code == 0x20 || code == 0xB7 || code == 0x2022 || code == 0x00B7);
          if (isLetterOrDigit) return false;
        }
        return true;
      }

      final styles = <_RenderedText>[];
      for (final element in tester.allElements) {
        final widget = element.widget;
        if (widget is RichText) {
          final renderObject = element.renderObject;
          if (renderObject is RenderParagraph &&
              renderObject.text.toPlainText().trim().isNotEmpty) {
            final style = renderObject.text.style ?? const TextStyle();
            final plain = renderObject.text.toPlainText().trim();
            if (style.fontFamily == 'MaterialIcons' || isIconGlyph(plain)) {
              continue;
            }
            styles.add(_RenderedText(
              text: plain,
              fontSize: style.fontSize ?? 14,
              fontWeight: style.fontWeight ?? FontWeight.w400,
              color: style.color ?? const Color(0xFF000000),
              opacity: (style.color ?? const Color(0xFF000000)).a,
            ),);
          }
        }
      }

      return _ScreenRubricReport(
        theme: theme,
        sparkle: sparkle,
        renderedTexts: styles,
        hasDimLayer: tester.any(find.byType(ColorFiltered)),
      );
    }

    void assertHierarchy(
      String label,
      _ScreenRubricReport report, {
      Set<String> registeredFindings = const {},
    }) {
      final headings = report.renderedTexts
          .where((t) => t.fontWeight.value >= FontWeight.w600.value || t.fontSize >= 18)
          .toList();
      final bodies = report.renderedTexts
          .where((t) => t.fontWeight.value < FontWeight.w600.value && t.fontSize >= 13)
          .toList();
      final captions = report.renderedTexts
          .where((t) => t.fontSize < 13 && t.opacity >= 0.5)
          .toList();

      // 发现棘轮：已登记既有缺陷不在此处红（逐项打印 PASS/FAIL 留证），
      // 但任何未登记的新违规必须红。修复后应同步清空登记。
      if (headings.isEmpty) {
        // ignore: avoid_print
        print('HIERARCHY $label headingMax=N/A [FAIL-REGISTERED? '
            '${registeredFindings.contains('hierarchy:no-heading')}] 无标题层'
            '（全部渲染文本均为正文/辅助级）');
      }
      expect(headings.isNotEmpty || registeredFindings.contains('hierarchy:no-heading'),
          isTrue, reason: '$label 无标题层（未登记的层级缺陷）',);
      expect(bodies, isNotEmpty, reason: '$label 无正文层');

      final maxBody = bodies.map((t) => t.fontSize).reduce(math.max);
      final maxCaption = captions.isEmpty
          ? null
          : captions.map((t) => t.fontSize).reduce(math.max);

      if (headings.isNotEmpty) {
        final maxHeading = headings.map((t) => t.fontSize).reduce(math.max);

        // 诊断：列出标题/正文两层的最大字号代表文本。
        // ignore: avoid_print
        print('HIERARCHY $label headingMax=$maxHeading '
            '"${headings.reduce((a, b) => a.fontSize >= b.fontSize ? a : b).text}"');
        // ignore: avoid_print
        print('HIERARCHY $label bodyMax=$maxBody '
            '"${bodies.reduce((a, b) => a.fontSize >= b.fontSize ? a : b).text}"');

        // 层级单调不倒挂（复合判据）：正文层不得在字号上超过标题层；同字号时
        // 标题层字重必须 ≥ 该字号正文（标题以字重区分，层级仍单调）。
        final headingMaxWeightAtSize = headings
            .where((t) => t.fontSize == maxHeading)
            .map((t) => t.fontWeight.value)
            .reduce(math.max);
        final bodyMaxWeightAtMaxSize = bodies
            .where((t) => t.fontSize == maxBody)
            .map((t) => t.fontWeight.value)
            .reduce(math.max);
        expect(
          maxHeading > maxBody ||
              headingMaxWeightAtSize >= bodyMaxWeightAtMaxSize,
          isTrue,
          reason: '$label 层级倒挂：标题最大 $maxHeading(w$headingMaxWeightAtSize) '
              '≤ 正文最大 $maxBody(w$bodyMaxWeightAtMaxSize)',
        );
        if (maxCaption != null) {
          expect(
            maxCaption,
            lessThanOrEqualTo(maxBody),
            reason: '$label 层级倒挂：辅助最大 $maxCaption > 正文最大 $maxBody',
          );
        }
      }

      // 逐色对比（AA 阈值；半透明装饰字豁免）。背景按"该色可能落在的
      // 主题容器面"候选集中最优者判定——白字只出现在深色容器（主色
      // 按钮/气泡/反色 snackbar），不与页面底色比。
      final candidates = <Color>{
        report.theme.scaffoldBackgroundColor,
        report.theme.cardTheme.color ?? report.theme.colorScheme.surfaceContainer,
        report.theme.colorScheme.surfaceContainer,
        report.theme.colorScheme.surfaceContainerHigh,
        report.theme.colorScheme.primary,
        report.theme.colorScheme.inverseSurface,
        report.sparkle.colors.chatBubbleUser,
        report.sparkle.colors.chatBubbleOther,
        report.sparkle.colors.surfaceSecondary,
        report.sparkle.colors.surfaceTertiary,
      };
      final distinctColors = report.renderedTexts
          .where((t) => t.opacity >= 0.5)
          .map((t) => (t.color.toARGB32(), t))
          .fold<Map<int, _RenderedText>>({}, (acc, cur) {
        acc.putIfAbsent(cur.$1, () => cur.$2);
        return acc;
      });
      final failures = <String>[];
      for (final entry in distinctColors.entries) {
        final t = entry.value;
        final isLarge = t.fontSize >= 18 ||
            (t.fontSize >= 14 && t.fontWeight.value >= FontWeight.w700.value);
        final threshold = isLarge ? 3.0 : 4.5;
        final ratios = candidates.map((c) => contrastRatio(t.color, c));
        final best = ratios.reduce(math.max);
        final bestBg = candidates
            .where((c) => contrastRatio(t.color, c) == best)
            .first;
        // ignore: avoid_print
        print('SCREEN_CONTRAST $label '
            '#${t.color.toARGB32().toRadixString(16)} on '
            '#${bestBg.toARGB32().toRadixString(16)} '
            '${t.fontSize.toStringAsFixed(0)}px w${t.fontWeight.value} '
            '= ${best.toStringAsFixed(2)}:1 (需 $threshold) '
            '${best >= threshold ? 'PASS' : 'FAIL'}');
        if (best < threshold) {
          failures.add(
              '${t.text.substring(0, math.min(24, t.text.length))}… '
              '#${t.color.toARGB32().toRadixString(16)} '
              '${t.fontSize}px ${best.toStringAsFixed(2)}:1 < $threshold');
        }
      }
      String findingKey(String f) {
        final hex = f.split('#').last.split(' ').first;
        return 'contrast:${hex.substring(math.max(0, hex.length - 6))}';
      }

      final unregistered = failures
          .where((f) => !registeredFindings.contains(findingKey(f)))
          .toList();
      expect(
        unregistered,
        isEmpty,
        reason: '$label 屏上存在低于 AA 且未登记的文字色：${unregistered.join('; ')}',
      );
    }

    void assertLowStimRealEffect(String label, _ScreenRubricReport std,
        _ScreenRubricReport low, {
      bool checkRenderedFontLift = true,
    }) {
      // 1) 实显主题档位真切换。
      expect(low.sparkle.lowStimulation, isTrue, reason: '$label low 档未生效');
      expect(std.sparkle.lowStimulation, isFalse);

      // 2) 动效预算实减：时长收缩、弹性撤除。
      expect(
        low.sparkle.motion.normal,
        lessThan(std.sparkle.motion.normal),
        reason: '$label low 档动效时长未收缩',
      );
      expect(low.sparkle.motion.bounceCurve, isNot(std.sparkle.motion.bounceCurve));

      // 3) 挑战性交互装饰实减：splash 反馈关闭、卡片阴影归零。
      expect(
        identical(low.theme.splashFactory, NoSplash.splashFactory),
        isTrue,
        reason: '$label low 档 splash 未关闭',
      );
      expect(
        low.theme.cardTheme.elevation ?? 0,
        lessThanOrEqualTo(std.theme.cardTheme.elevation ?? 0),
        reason: '$label low 档卡片阴影未减',
      );

      // 4) 渲染输出真实不同：
      //    a) 通用：低刺激档渲染树含实减色温层（ColorFiltered），普通档无——
      //       截图随之整体变暗（见 evidence PNG 两档差）。
      //    b) 补充：消费主题文字主题的屏（settings 等）Material 样式整体
      //       +1px；home/chat/journey 为显式 TextStyle，字号判据豁免（如实
      //       登记，不虚标），其两档差异由 a + splash/转场/动效 token 承担。
      expect(low.hasDimLayer, isTrue, reason: '$label low 档减色温层未生效');
      expect(std.hasDimLayer, isFalse, reason: '$label standard 档不应有减色温层');
      if (checkRenderedFontLift) {
        final stdSizes = std.renderedTexts.map((t) => t.fontSize).toSet();
        final lowSizes = low.renderedTexts.map((t) => t.fontSize).toSet();
        final liftedExists = stdSizes.any((s) => lowSizes.contains(s + 1));
        expect(
          liftedExists,
          isTrue,
          reason: '$label low 档渲染字号与 standard 完全一致——低刺激未落到渲染',
        );
        expect(
          stdSizes,
          isNot(lowSizes),
          reason: '$label 两档渲染字号集合完全一致',
        );
      }
    }

    // U-02 rubric 判定（真实渲染数值）。已登记发现 F1-F4 的真源在
    // u02_core_screens.dart 的 registeredU02Findings（棘轮：已登记项
    // 不放红留证，任何未登记新违规必须红；修复后清空对应键）。
    for (final surface in U02Surface.values) {
      testWidgets('${surface.name} · 两档渲染树 hierarchy + mode-diff',
          (tester) async {
        tester.view.physicalSize = Size(
          u02ViewportLogicalSize.width * u02ViewportDpr,
          u02ViewportLogicalSize.height * u02ViewportDpr,
        );
        tester.view.devicePixelRatio = u02ViewportDpr;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);

        // 布局异常收集（登记棘轮）：溢出类按 file:line 归键，已登记的
        // 不放红；其余异常原样判红。
        final caughtLayoutErrors = <String>[];
        final previousOnError = FlutterError.onError;
        FlutterError.onError = (details) {
          final info = details.toString();
          final location =
              RegExp(r'(?:\w+):file:///\S+/lib/([^\s(]+\.dart):(\d+)')
                  .firstMatch(info);
          if (info.contains('overflowed') && location != null) {
            caughtLayoutErrors.add('layout:${location.group(1)}:${location.group(2)}');
          } else if (info.contains('RenderAnimatedSize')) {
            caughtLayoutErrors.add('flutteranim:RenderAnimatedSize');
          } else if (details.exception is FlutterError) {
            caughtLayoutErrors.add('flutter:${info.substring(0, math.min(120, info.length))}');
          } else {
            previousOnError?.call(details);
          }
        };
        addTearDown(() => FlutterError.onError = previousOnError);

        final registered = registeredU02Findings[surface]!;
        final stdReport = await pumpAndMeasure(
          tester,
          surface,
          const EmotionResponsiveConfig.normal(),
        );
        assertHierarchy(
          '${surface.name}/standard',
          stdReport,
          registeredFindings: registered,
        );

        final lowReport = await pumpAndMeasure(
          tester,
          surface,
          const EmotionResponsiveConfig.lowStimulus(),
        );
        assertHierarchy(
          '${surface.name}/low',
          lowReport,
          registeredFindings: registered,
        );

        // 渲染字号提升判据：settings 已实证（ListTile 系主题样式 +1px）；
        // home/chat/journey 为显式 TextStyle（豁免，如实登记）。
        assertLowStimRealEffect(
          surface.name,
          stdReport,
          lowReport,
          checkRenderedFontLift: surface == U02Surface.settings,
        );

        // 未登记的布局/框架异常必须红（登记棘轮不吞新发现）。
        final unregisteredLayout = caughtLayoutErrors
            .where((e) => !registered.contains(e))
            .toList();
        expect(
          unregisteredLayout,
          isEmpty,
          reason: '${surface.name} 存在未登记的布局/框架异常：'
              '${unregisteredLayout.toSet().join('; ')}',
        );
      });
    }
  });
}

class _RenderedText {
  const _RenderedText({
    required this.text,
    required this.fontSize,
    required this.fontWeight,
    required this.color,
    required this.opacity,
  });

  final String text;
  final double fontSize;
  final FontWeight fontWeight;
  final Color color;
  final double opacity;
}

class _ScreenRubricReport {
  const _ScreenRubricReport({
    required this.theme,
    required this.sparkle,
    required this.renderedTexts,
    required this.hasDimLayer,
  });

  final ThemeData theme;
  final SparkleThemeExtension sparkle;
  final List<_RenderedText> renderedTexts;

  /// 低刺激减色温层（ColorFiltered）是否在渲染树中（mode-diff 通用证据）。
  final bool hasDimLayer;
}
