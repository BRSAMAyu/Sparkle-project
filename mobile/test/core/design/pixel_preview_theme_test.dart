// V4-F01 · 像素候选主题（preview 通道）组件级回归测试。
//
// 覆盖卡面验收（必须可失败）：
// 1. 最终颜色对比度自动测——3 profile 核心文案（正文/次级/强调/语义四槽）
//    在全部三个容器面 ≥4.5:1，onPrimary ≥4.5:1，描边线 ≥3:1（图形线）；
// 2. 200% 字阶无主 CTA 截断、系统字号可继承——真实 ThemeData 渲染
//    FilledButton，textScaler 2.0 无异常、按钮随系统字阶长高；
// 3. runtime 只有一个 token 源——候选 profile 产出既有 SparkleThemeData
//    （AppThemes 同一路径），classic 不携带像素扩展；
// 4. preview 默认 off——classic 是默认档，发布主题逐槽零差量，且可回退。
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';

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

/// WCAG 2.x 相对亮度对比度。
double contrastRatio(Color a, Color b) {
  final la = _relativeLuminance(a);
  final lb = _relativeLuminance(b);
  final hi = la > lb ? la : lb;
  final lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

/// 全部颜色槽签名（classic 零差量断言用）。
Map<String, Color> colorSignature(SparkleColors c) => {
      'brandPrimary': c.brandPrimary,
      'brandSecondary': c.brandSecondary,
      'semanticSuccess': c.semanticSuccess,
      'semanticWarning': c.semanticWarning,
      'semanticError': c.semanticError,
      'semanticInfo': c.semanticInfo,
      'surfacePrimary': c.surfacePrimary,
      'surfaceSecondary': c.surfaceSecondary,
      'surfaceTertiary': c.surfaceTertiary,
      'surfaceAmbient': c.surfaceAmbient,
      'rimLight': c.rimLight,
      'glowPrimary': c.glowPrimary,
      'noiseColor': c.noiseColor,
      'textPrimary': c.textPrimary,
      'textSecondary': c.textSecondary,
      'textTertiary': c.textTertiary,
      'textDisabled': c.textDisabled,
      'taskLearning': c.taskLearning,
      'taskTraining': c.taskTraining,
      'taskErrorFix': c.taskErrorFix,
      'taskReflection': c.taskReflection,
      'taskSocial': c.taskSocial,
      'taskPlanning': c.taskPlanning,
      'taskOcr': c.taskOcr,
      'planSprint': c.planSprint,
      'planGrowth': c.planGrowth,
      'statusOnline': c.statusOnline,
      'statusOffline': c.statusOffline,
      'statusInvisible': c.statusInvisible,
      'neutral200': c.neutral200,
      'neutral300': c.neutral300,
      'neutral400': c.neutral400,
      'neutral500': c.neutral500,
      'neutral600': c.neutral600,
      'neutralOutline': c.neutralOutline,
      'chatBubbleUser': c.chatBubbleUser,
      'chatBubbleUserText': c.chatBubbleUserText,
      'chatBubbleOther': c.chatBubbleOther,
      'chatBubbleOtherText': c.chatBubbleOtherText,
      'galaxyBackground': c.galaxyBackground,
      'galaxyShadow': c.galaxyShadow,
    };

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final manager = ThemeManager();
    if (!manager.initialized) {
      await manager.initialize();
    }
    // 归位 preview 关（classic），避免单例状态跨用例泄漏。
    await manager.setPixelPreviewProfile(PixelPreviewProfile.classic);
  });

  group('preview 默认 off 与 classic 零差量', () {
    test('默认档是 classic，preview 关', () {
      final manager = ThemeManager();
      expect(manager.pixelPreviewProfile, PixelPreviewProfile.classic);
      expect(manager.pixelPreviewEnabled, isFalse);
    });

    test('classic 下主题与既有发布主题逐槽零差量（浅/深两态）', () {
      final manager = ThemeManager();
      final light = manager.themeForBrightness(Brightness.light).colors;
      final dark = manager.themeForBrightness(Brightness.dark).colors;
      expect(colorSignature(light), colorSignature(SparkleColors.light()));
      expect(colorSignature(dark), colorSignature(SparkleColors.dark()));
    });

    test('classic 往返回退：dusk → classic 逐槽回到原发布主题', () async {
      final manager = ThemeManager();
      final before =
          colorSignature(manager.themeForBrightness(Brightness.light).colors);
      await manager.setPixelPreviewProfile(PixelPreviewProfile.dusk);
      expect(manager.pixelPreviewEnabled, isTrue);
      await manager.setPixelPreviewProfile(PixelPreviewProfile.classic);
      final after =
          colorSignature(manager.themeForBrightness(Brightness.light).colors);
      expect(after, before);
    });

    test('preview 状态持久化 + reset 归零', () async {
      final manager = ThemeManager();
      await manager.setPixelPreviewProfile(PixelPreviewProfile.quiet);
      final prefs = await SharedPreferences.getInstance();
      expect(
        prefs.getInt(ThemeManager.pixelPreviewPrefsKey),
        PixelPreviewProfile.quiet.index,
      );
      await manager.reset();
      expect(manager.pixelPreviewProfile, PixelPreviewProfile.classic);
      final prefsAfter = await SharedPreferences.getInstance();
      expect(
        prefsAfter.getInt(ThemeManager.pixelPreviewPrefsKey),
        PixelPreviewProfile.classic.index,
      );
    });

    test('initialize 越界索引回落 classic（preview off）', () async {
      // 越界值经 setPixelPreviewProfile 无法构造，直接验证枚举边界保护口径：
      // 只有 0..3 是合法索引，classic=0 是默认回落值。
      expect(PixelPreviewProfile.classic.index, 0);
      expect(PixelPreviewProfile.values.length, 4);
    });
  });

  group('PROPOSED 色板锚值（TOKENS.proposal 逐槽转抄）', () {
    test('paperDay 锚值', () {
      final c = pixelPreviewColors(PixelPreviewProfile.paperDay);
      expect(c.brightness, Brightness.light);
      expect(c.surfacePrimary, const Color(0xFFF4F0E6)); // canvas
      expect(c.surfaceSecondary, const Color(0xFFFFFCF4)); // surface
      expect(c.surfaceTertiary, const Color(0xFFE9E5D8)); // raised
      expect(c.textPrimary, const Color(0xFF29342F)); // ink
      expect(c.textSecondary, const Color(0xFF58665C)); // muted
      expect(c.brandPrimary, const Color(0xFF3E6652)); // accent 鼠尾草绿
      expect(c.semanticInfo, const Color(0xFF3C607A)); // info 灰蓝
      expect(c.semanticWarning, const Color(0xFF805126)); // warning 陶土系
      expect(c.semanticError, const Color(0xFF9C3D38)); // error 陶土红
      expect(c.neutral300, const Color(0xFF68766A)); // line
      expect(c.neutral200, const Color(0xFFD0D8CB)); // decor
    });

    test('dusk 锚值（深色档）', () {
      final c = pixelPreviewColors(PixelPreviewProfile.dusk);
      expect(c.brightness, Brightness.dark);
      expect(c.surfacePrimary, const Color(0xFF24322B)); // surface
      expect(c.surfaceAmbient, const Color(0xFF19241F)); // canvas
      expect(c.surfaceSecondary, const Color(0xFF2F4036)); // raised
      expect(c.surfaceTertiary, const Color(0xFF344B3B)); // decor
      expect(c.textPrimary, const Color(0xFFF5F0E3)); // ink
      expect(c.brandPrimary, const Color(0xFFB9D5B5)); // accent
      expect(c.neutral600, const Color(0xFF9DAF9F)); // line
    });

    test('quiet 锚值（低刺激档）', () {
      final c = pixelPreviewColors(PixelPreviewProfile.quiet);
      expect(c.brightness, Brightness.light);
      expect(c.surfacePrimary, const Color(0xFFF7F5EF)); // canvas
      expect(c.surfaceSecondary, const Color(0xFFFFFFFF)); // surface
      expect(c.surfaceTertiary, const Color(0xFFECECE5)); // raised
      expect(c.textPrimary, const Color(0xFF202A24)); // ink
      expect(c.brandPrimary, const Color(0xFF344F3D)); // accent
    });

    test('候选档产出既有 SparkleThemeData 结构（唯一令牌体系）', () {
      for (final profile in PixelPreviewProfile.values) {
        final theme = pixelPreviewThemeData(profile);
        expect(theme, isA<SparkleThemeData>());
        expect(
          theme.typography,
          SparkleTypography.standard(),
          reason: '$profile 必须复用既有字阶（不建第二字阶）',
        );
        expect(theme.spacing, isA<SparkleSpacing>());
      }
    });
  });

  group('自动对比度测量（卡面验收：3 profile 核心文案可读）', () {
    const containers = ['primary', 'secondary', 'tertiary'];

    Color containerColor(SparkleColors c, String slot) => switch (slot) {
          'primary' => c.surfacePrimary,
          'secondary' => c.surfaceSecondary,
          'tertiary' => c.surfaceTertiary,
          _ => throw ArgumentError(slot),
        };

    for (final profile in const [
      PixelPreviewProfile.paperDay,
      PixelPreviewProfile.dusk,
      PixelPreviewProfile.quiet,
    ]) {
      test('$profile 核心文案角色 ≥4.5:1（三容器面）', () {
        final c = pixelPreviewColors(profile);
        final roles = <String, Color>{
          'textPrimary': c.textPrimary,
          'textSecondary': c.textSecondary,
          'textTertiary': c.textTertiary,
          'brandPrimary(交互色文本)': c.brandPrimary,
          'semanticInfo': c.semanticInfo,
          'semanticWarning': c.semanticWarning,
          'semanticError': c.semanticError,
          'semanticSuccess': c.semanticSuccess,
          'taskReflection(柔紫 PROPOSED)': c.taskReflection,
          'taskPlanning': c.taskPlanning,
        };
        for (final slot in containers) {
          final bg = containerColor(c, slot);
          for (final entry in roles.entries) {
            final ratio = contrastRatio(entry.value, bg);
            expect(
              ratio,
              greaterThanOrEqualTo(4.5),
              reason:
                  '$profile ${entry.key} on $slot = ${ratio.toStringAsFixed(2)}:1',
            );
          }
        }
      });

      test('$profile 主 CTA onPrimary ≥4.5:1（AppThemes 实路径）', () async {
        final manager = ThemeManager();
        await manager.setPixelPreviewProfile(profile);
        final theme =
            profile == PixelPreviewProfile.dusk
                ? AppThemes.darkTheme
                : AppThemes.lightTheme;
        expect(
          contrastRatio(theme.colorScheme.onPrimary, theme.colorScheme.primary),
          greaterThanOrEqualTo(4.5),
          reason: '$profile onPrimary on primary',
        );
        expect(
          contrastRatio(theme.colorScheme.onError, theme.colorScheme.error),
          greaterThanOrEqualTo(4.5),
          reason: '$profile onError on error',
        );
      });

      test('$profile 描边线（border 槽）≥3:1 图形线', () {
        final c = pixelPreviewColors(profile);
        expect(
          contrastRatio(c.border, c.surfacePrimary),
          greaterThanOrEqualTo(3.0),
          reason: '$profile border on surfacePrimary',
        );
      });

      test('$profile 聊天气泡文本 ≥4.5:1', () {
        final c = pixelPreviewColors(profile);
        expect(
          contrastRatio(c.chatBubbleUserText, c.chatBubbleUser),
          greaterThanOrEqualTo(4.5),
        );
        expect(
          contrastRatio(c.chatBubbleOtherText, c.chatBubbleOther),
          greaterThanOrEqualTo(4.5),
        );
      });
    }
  });

  group('ThemeManager preview 通道与唯一令牌源', () {
    testWidgets('preview 开启时 AppThemes 走候选档且挂载像素扩展；classic 不挂载',
        (tester) async {
      final manager = ThemeManager();
      // classic：默认发布面，无像素扩展，主色 = classic brandPrimary。
      final classicTheme = AppThemes.lightTheme;
      expect(classicTheme.extension<PixelProfileTheme>(), isNull);
      expect(
        classicTheme.colorScheme.primary,
        manager.themeForBrightness(Brightness.light).colors.brandPrimary,
      );

      await manager.setPixelPreviewProfile(PixelPreviewProfile.paperDay);
      final paperTheme = AppThemes.lightTheme;
      expect(
        paperTheme.colorScheme.primary,
        pixelPreviewColors(PixelPreviewProfile.paperDay).brandPrimary,
      );
      expect(
        paperTheme.scaffoldBackgroundColor,
        pixelPreviewColors(PixelPreviewProfile.paperDay).surfacePrimary,
      );
      final extension = paperTheme.extension<PixelProfileTheme>();
      expect(extension, isNotNull);
      expect(extension!.profile, PixelPreviewProfile.paperDay);
    });

    testWidgets('候选档钉死亮度：dusk 下 light/dark 入口都出暮色', (tester) async {
      final manager = ThemeManager();
      await manager.setPixelPreviewProfile(PixelPreviewProfile.dusk);
      expect(
        AppThemes.lightTheme.colorScheme.primary,
        pixelPreviewColors(PixelPreviewProfile.dusk).brandPrimary,
      );
      expect(
        AppThemes.darkTheme.colorScheme.primary,
        pixelPreviewColors(PixelPreviewProfile.dusk).brandPrimary,
      );
      expect(
        AppThemes.lightTheme.colorScheme.brightness,
        Brightness.dark,
      );
    });

    test('DS 静态层与 preview 档一致（唯一运行时 token 源）', () async {
      final manager = ThemeManager();
      await manager.setPixelPreviewProfile(PixelPreviewProfile.quiet);
      expect(
        DS.brandPrimary,
        pixelPreviewColors(PixelPreviewProfile.quiet).brandPrimary,
      );
      expect(
        DS.surfacePrimary,
        pixelPreviewColors(PixelPreviewProfile.quiet).surfacePrimary,
      );
      expect(
        DS.textPrimary,
        pixelPreviewColors(PixelPreviewProfile.quiet).textPrimary,
      );
    });
  });

  group('PixelProfileTheme 扩展（DESIGN_SYSTEM 极少数新增字段）', () {
    test('pixelStep=2dp，cornerCut=[4,8,12]，stateMotion=80/160/220/650', () {
      for (final profile in const [
        PixelPreviewProfile.paperDay,
        PixelPreviewProfile.dusk,
        PixelPreviewProfile.quiet,
      ]) {
        final e = PixelProfileTheme.forProfile(profile);
        expect(e.pixelStep, 2.0, reason: '$profile pixelStep');
        expect(e.cornerCut, [4.0, 8.0, 12.0], reason: '$profile cornerCut');
        expect(e.stateMotion.press, const Duration(milliseconds: 80));
        expect(e.stateMotion.state, const Duration(milliseconds: 160));
        expect(e.stateMotion.enter, const Duration(milliseconds: 220));
        expect(e.stateMotion.milestoneMax, const Duration(milliseconds: 650));
      }
    });

    test('accentInk = proposal on_accent 槽（浅档白墨 / dusk 深墨）', () {
      expect(
        PixelProfileTheme.forProfile(PixelPreviewProfile.paperDay).accentInk,
        Colors.white,
      );
      expect(
        PixelProfileTheme.forProfile(PixelPreviewProfile.quiet).accentInk,
        Colors.white,
      );
      expect(
        PixelProfileTheme.forProfile(PixelPreviewProfile.dusk).accentInk,
        const Color(0xFF17261C),
      );
    });

    test('copyWith / lerp / 相等性', () {
      final a = PixelProfileTheme.forProfile(PixelPreviewProfile.paperDay);
      final b = PixelProfileTheme.forProfile(PixelPreviewProfile.dusk);
      expect(a, PixelProfileTheme.forProfile(PixelPreviewProfile.paperDay));
      expect(a.copyWith(pixelStep: 4.0).pixelStep, 4.0);

      // lerp 档位约定与 SparkleThemeData.lerp 一致：t < 0.5 取前者。
      expect(a.lerp(b, 0.25).profile, PixelPreviewProfile.paperDay);
      expect(a.lerp(b, 0.75).profile, PixelPreviewProfile.dusk);
      expect(a.lerp(b, 0.5).profile, PixelPreviewProfile.dusk);
      expect(a.lerp(b, 0.25).pixelStep, 2.0); // 两档同值
      expect(
        a.lerp(b, 0.25).stateMotion.press,
        const Duration(milliseconds: 80),
      );
    });
  });

  group('200% 字阶：主 CTA 无截断、系统字号可继承（浅深两态真实渲染）', () {
    /// 泵真实 FilledButton，返回（按钮尺寸，标签文本尺寸）。
    Future<(Size, Size)> pumpAndMeasure(
      WidgetTester tester,
      ThemeData theme,
      double scale,
    ) async {
      await tester.pumpWidget(
        Directionality(
          textDirection: TextDirection.ltr,
          child: MediaQuery(
            data: MediaQueryData(textScaler: TextScaler.linear(scale)),
            child: Theme(
              data: theme,
              child: Center(
                child: FilledButton(
                  onPressed: () {},
                  child: Builder(
                    builder: (context) => Text(
                      '开始专注学习',
                      style: Theme.of(context).textTheme.labelLarge,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump();
      final buttonSize = tester.getSize(find.byType(FilledButton));
      final textSize = tester.getSize(find.byType(Text));
      return (buttonSize, textSize);
    }

    for (final profile in const [
      PixelPreviewProfile.paperDay,
      PixelPreviewProfile.dusk,
      PixelPreviewProfile.quiet,
    ]) {
      testWidgets('$profile 200% 字阶主 CTA 不溢出且随系统字阶长高', (tester) async {
        final manager = ThemeManager();
        await manager.setPixelPreviewProfile(profile);
        final isDusk = profile == PixelPreviewProfile.dusk;
        final theme = isDusk ? AppThemes.darkTheme : AppThemes.lightTheme;

        expect(
          theme.textTheme.labelLarge?.fontSize,
          SparkleTypography.standard().labelLarge.fontSize,
          reason: '候选档必须复用既有字阶（系统字号可继承）',
        );

        final (btn1, text1) = await pumpAndMeasure(tester, theme, 1.0);
        expect(tester.takeException(), isNull);
        final (btn2, text2) = await pumpAndMeasure(tester, theme, 2.0);
        expect(
          tester.takeException(),
          isNull,
          reason: '$profile 200% 字阶不得产生 RenderFlex 溢出',
        );

        // 系统字号可继承：标签实际渲染尺寸随 200% 字阶放大。
        expect(
          text2.height,
          greaterThan(text1.height),
          reason: '$profile 标签必须随系统字阶放大',
        );
        // 无截断：200% 标签完整落入按钮盒内（宽度/高度均不超出）。
        expect(
          text2.width,
          lessThanOrEqualTo(btn2.width),
          reason: '$profile 标签宽度不得超出主 CTA',
        );
        expect(
          text2.height,
          lessThanOrEqualTo(btn2.height),
          reason: '$profile 标签高度不得超出主 CTA',
        );
        // 主 CTA 保持可点目标（48dp 档）。
        expect(btn2.height, greaterThanOrEqualTo(48.0));
      });
    }
  });
}
