// V4-G01 · 首页/目标/任务/日历家族 正文对比度四风格逐对复算。
//
// F06 判例（pixel_a11y_f06_test 验收①E±）同口径移植到本家族实际用色
// 组合：15 对独立复算（classic 深/浅画布 + 3 像素档画布 + 三档 Primary
// CTA 的 accent 容器对 + 档案掌握度药丸/细节 chip 容器对），阈值按
// ACCESSIBILITY_ASSETS：正文 ≥4.5:1。E- 控制组：禁用灰判负（探针有
// 判别力，防测试自证）。
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';

/// WCAG 2.1 相对亮度对比度（与 a11y_contrast_test / F06 同公式）。
double contrastRatio(Color a, Color b) {
  double channel(double c) {
    final sRGB = c / 255.0;
    return sRGB <= 0.03928
        ? sRGB / 12.92
        : math.pow((sRGB + 0.055) / 1.055, 2.4).toDouble();
  }

  final l1 = 0.2126 * channel(a.r * 255.0) +
      0.7152 * channel(a.g * 255.0) +
      0.0722 * channel(a.b * 255.0);
  final l2 = 0.2126 * channel(b.r * 255.0) +
      0.7152 * channel(b.g * 255.0) +
      0.0722 * channel(b.b * 255.0);
  final lighter = math.max(l1, l2);
  final darker = math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

void main() {
  group('G01 家族正文对比度 · 四风格逐对复算（F06 判例 15 对）', () {
    final cases = <String, ({Color fg, Color bg})>{
      // ── 家族画布正文（dashboard/task/goal 面正文与次级文本）──
      'classic-light textPrimary/canvas': (
        fg: SparkleColors.light().textPrimary,
        bg: SparkleColors.light().surfacePrimary,
      ),
      'classic-light textSecondary/canvas': (
        fg: SparkleColors.light().textSecondary,
        bg: SparkleColors.light().surfacePrimary,
      ),
      'classic-dark textPrimary/canvas': (
        fg: SparkleColors.dark().textPrimary,
        bg: SparkleColors.dark().surfacePrimary,
      ),
      'classic-dark textSecondary/canvas': (
        fg: SparkleColors.dark().textSecondary,
        bg: SparkleColors.dark().surfacePrimary,
      ),
      'paperDay ink/canvas': (
        fg: pixelPreviewColors(PixelPreviewProfile.paperDay).textPrimary,
        bg: pixelPreviewColors(PixelPreviewProfile.paperDay).surfacePrimary,
      ),
      'paperDay muted/canvas': (
        fg: pixelPreviewColors(PixelPreviewProfile.paperDay).textSecondary,
        bg: pixelPreviewColors(PixelPreviewProfile.paperDay).surfaceSecondary,
      ),
      'dusk ink/surface': (
        fg: pixelPreviewColors(PixelPreviewProfile.dusk).textPrimary,
        bg: pixelPreviewColors(PixelPreviewProfile.dusk).surfacePrimary,
      ),
      'dusk muted/surface': (
        fg: pixelPreviewColors(PixelPreviewProfile.dusk).textSecondary,
        bg: pixelPreviewColors(PixelPreviewProfile.dusk).surfaceSecondary,
      ),
      'quiet ink/canvas': (
        fg: pixelPreviewColors(PixelPreviewProfile.quiet).textPrimary,
        bg: pixelPreviewColors(PixelPreviewProfile.quiet).surfacePrimary,
      ),
      'quiet muted/canvas': (
        fg: pixelPreviewColors(PixelPreviewProfile.quiet).textSecondary,
        bg: pixelPreviewColors(PixelPreviewProfile.quiet).surfaceSecondary,
      ),
      // ── 家族主 CTA：accent 容器上的 on-accent 墨（任务卡完成钮 /
      //    档案空态 CTA 等单主行动）──
      'paperDay onAccent/accent': (
        fg: PixelProfileTheme.forProfile(PixelPreviewProfile.paperDay)
            .accentInk,
        bg: pixelPreviewColors(PixelPreviewProfile.paperDay).brandPrimary,
      ),
      'dusk onAccent/accent': (
        fg: PixelProfileTheme.forProfile(PixelPreviewProfile.dusk).accentInk,
        bg: pixelPreviewColors(PixelPreviewProfile.dusk).brandPrimary,
      ),
      'quiet onAccent/accent': (
        fg: PixelProfileTheme.forProfile(PixelPreviewProfile.quiet).accentInk,
        bg: pixelPreviewColors(PixelPreviewProfile.quiet).brandPrimary,
      ),
      // ── 家族容器对（G01 令牌化后的档案面掌握度药丸/细节 chip）──
      'paperDay success/successTintPill (portfolio)': (
        fg: pixelPreviewColors(PixelPreviewProfile.paperDay).semanticSuccess,
        bg: Color.alphaBlend(
          pixelPreviewColors(PixelPreviewProfile.paperDay).semanticSuccess
              .withValues(alpha: 0.10),
          pixelPreviewColors(PixelPreviewProfile.paperDay).surfaceSecondary,
        ),
      ),
      'dusk warning/warningTintChip (portfolio)': (
        fg: pixelPreviewColors(PixelPreviewProfile.dusk).semanticWarning,
        bg: Color.alphaBlend(
          pixelPreviewColors(PixelPreviewProfile.dusk).semanticWarning
              .withValues(alpha: 0.08),
          pixelPreviewColors(PixelPreviewProfile.dusk).surfaceTertiary,
        ),
      ),
    };

    test('E+：全部家族正文/关键部件组合 ≥4.5:1（${cases.length} 对）', () {
      expect(cases.length, 15, reason: 'F06 判例：15 对独立复算');
      for (final entry in cases.entries) {
        final ratio = contrastRatio(entry.value.fg, entry.value.bg);
        expect(
          ratio,
          greaterThanOrEqualTo(4.5),
          reason: '${entry.key} = ${ratio.toStringAsFixed(2)}:1，正文须 ≥4.5:1',
        );
      }
    });

    test('E-：禁用灰在浅画布被同一探针判负（探针有判别力）', () {
      // textDisabled（classic-light #A49B90）在画布 ≈2.5:1——禁用态豁免，
      // 但不得混入正文；探针必须能判负，否则 E+ 无判别力。
      final ratio = contrastRatio(
        SparkleColors.light().textDisabled,
        SparkleColors.light().surfacePrimary,
      );
      expect(
        ratio,
        lessThan(4.5),
        reason: '禁用灰控制组必须被 4.5:1 探针判负',
      );
    });

    test('E2+：四档 brandPrimary 大字/图形线 ≥3:1（大字与关键图形阈值）', () {
      for (final profile in PixelPreviewProfile.values) {
        if (profile == PixelPreviewProfile.classic) {
          // classic 走既有发布主题（深/浅两侧），图形线阈值同查。
          for (final colors in [
            SparkleColors.light(),
            SparkleColors.dark(),
          ]) {
            final ratio = contrastRatio(
              colors.brandPrimary,
              colors.surfacePrimary,
            );
            expect(
              ratio,
              greaterThanOrEqualTo(3.0),
              reason:
                  'classic ${colors.brightness} brandPrimary 大字线 = '
                  '${ratio.toStringAsFixed(2)}:1（须 ≥3:1）',
            );
          }
          continue;
        }
        final colors = pixelPreviewColors(profile);
        final ratio = contrastRatio(colors.brandPrimary, colors.surfacePrimary);
        expect(
          ratio,
          greaterThanOrEqualTo(3.0),
          reason:
              '$profile brandPrimary 大字线 = ${ratio.toStringAsFixed(2)}:1'
              '（须 ≥3:1）',
        );
      }
    });
  });
}
