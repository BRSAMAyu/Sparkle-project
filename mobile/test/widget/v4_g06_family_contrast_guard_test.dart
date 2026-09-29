// V4-G06 · 小队/自我锚/光子/成就 家族四风格对比度守卫钉（CI 可失败）。
//
// 规格权威：v4/02_design/ACCESSIBILITY_ASSETS.md（正文 ≥4.5:1，大字/非
// 文字关键部件 ≥3:1）+ SCREEN_FAMILIES.md「小队/自我锚/光子/成就」行
// （L19：先行动再装饰 / self-anchor 非排行 / 兑换不暗示付费 / 真实账本
// 可关庆祝 / 像素网格同一 / Shop HIDDEN 不开）。
//
// 判例：pixel_a11y_f06_test / G01 家族对比度复算 / G02 家族守卫（WCAG 2.x
// 相对亮度公式；半透明面按 alpha 解析合成到最近不透明宿主面后计算）。
//
// 钉住的都是本家族修过的真实缺陷配对（详见各 case 注）：
//   · streak 日历格数字墨（按实际格底实算，含 weak=success×warning 中间色）
//   · 成就解锁弹窗固定美术渐变双端墨（ThemeUtils.getContrastSafeTextOnGradient）
//   · 弹窗内圆图标（rarity identity 色对 neutral0 浅底，非文字 ≥3:1）
//   · 庆祝可关文案（DS.surfacePrimary 卡面承诺——milestone/contract 修复）
//   · 光子账本：warning 墨压 warningLight（访客横幅）
//   · 火堆等级徽标墨（brandPrimary 实心底实算）
//   · 小队 hub 渐变图标墨 / 地图状态 chip 墨（textSecondary 对详情面板）
// E- 控制组：禁用灰/旧缺陷配对必须判负（探针有判别力，防测试自证）。
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/utils/theme_utils.dart';

double _srgbChannelToF(double c) {
  final v = c / 255.0;
  return v <= 0.04045
      ? v / 12.92
      : math.pow((v + 0.055) / 1.055, 2.4).toDouble();
}

double contrastRatio(Color a, Color b) {
  double lum(Color c) =>
      0.2126 * _srgbChannelToF(c.r * 255.0) +
      0.7152 * _srgbChannelToF(c.g * 255.0) +
      0.0722 * _srgbChannelToF(c.b * 255.0);
  final la = lum(a);
  final lb = lum(b);
  final hi = la > lb ? la : lb;
  final lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

const List<PixelPreviewProfile> _profiles = <PixelPreviewProfile>[
  PixelPreviewProfile.paperDay,
  PixelPreviewProfile.dusk,
  PixelPreviewProfile.quiet,
];

/// classic 双亮度（classic 不是像素档，浅/深各算一档，F05 口径）。
final Map<String, SparkleColors> _allProfiles = <String, SparkleColors>{
  'classic-light': SparkleColors.light(),
  'classic-dark': SparkleColors.dark(),
  for (final p in _profiles) p.name: pixelPreviewColors(p),
};

void main() {
  group('G06 家族对比度守卫 · 四风格逐对复算（ACCESSIBILITY_ASSETS 阈值）', () {
    test('streak 日历格数字墨 ≥4.5:1（按实际格底实算，含 weak 中间色）', () {
      _allProfiles.forEach((name, c) {
        final bgs = <String, Color>{
          'active': c.semanticSuccess,
          'weak': Color.lerp(c.semanticSuccess, c.semanticWarning, 0.5)!,
          'frozen': c.semanticWarning,
        };
        for (final entry in bgs.entries) {
          // 运行时口径：DS.onColor(baseColor) == getContrastSafeText(bg)。
          final ink = ThemeUtils.getContrastSafeText(entry.value);
          final ratio = contrastRatio(ink, entry.value);
          expect(
            ratio,
            greaterThanOrEqualTo(4.5),
            reason: '$name streak ${entry.key} 格底墨/底 $ratio',
          );
        }
      });
    });

    test('E- 控制组：禁用灰压画布必须判负（探针判别力）', () {
      _allProfiles.forEach((name, c) {
        final ratio = contrastRatio(c.textDisabled, c.surfacePrimary);
        expect(
          ratio,
          lessThan(4.5),
          reason: '$name textDisabled/surfacePrimary=$ratio 应低于正文阈值',
        );
      });
    });

    test('成就解锁弹窗固定美术渐变双端墨 ≥4.5:1（三稀有度，四档同值）', () {
      // 庆祝卡=固定美术底（milestone 豁免同款）：渐变双端收敛为稀有度
      // 身份色系（端点亮度同侧），与 achievement_unlock_dialog
      // ._getRarityColors 同源。随档语义色退出填充位——classic-light 的
      // warning/brandSecondary/info 端曾使三稀有度全部无公共墨色
      // （2.95/4.499/4.02:1），旧配对在 E- 控制组钉死。
      const gold = Color(0xFFFFD700); // DS.rarityRare
      const purple = Color(0xFF9B59B6); // DS.rarityEpic
      const coral = Color(0xFFFF6B6B); // DS.rarityLegendary
      final gradients = <String, (Color, Color)>{
        'rare(gold→deepGold)': (gold, Color.lerp(gold, Colors.black, 0.25)!),
        'epic(purple→deepPurple)': (
          purple,
          Color.lerp(purple, Colors.black, 0.35)!,
        ),
        'legendary(coral→lightCoral)': (
          coral,
          Color.lerp(coral, Colors.white, 0.3)!,
        ),
      };
      for (final MapEntry(key: label, value: ends) in gradients.entries) {
        final ink = ThemeUtils.getContrastSafeTextOnGradient(
          ends.$1,
          ends.$2,
        );
        final minRatio = ThemeUtils.minContrastOnGradient(
          ink,
          ends.$1,
          ends.$2,
        );
        expect(
          minRatio,
          greaterThanOrEqualTo(4.5),
          reason: '弹窗 $label 双端墨下界 $minRatio',
        );
      }
    });

    test('E- 控制组：旧随档语义渐变端配对必须判负（无公共墨色的实证）', () {
      // classic-light 旧第二端（warning/brandSecondary/info）与固定
      // identity 端的最好公共墨下界——全部低于正文 4.5:1。
      final impossiblePairs = <String, (Color, Color)>{
        'rare×classic-light(gold→warning#8B4500)': (
          const Color(0xFFFFD700),
          const Color(0xFF8B4500),
        ),
        'epic×classic-light(purple→sky#56B4E9)': (
          const Color(0xFF9B59B6),
          const Color(0xFF56B4E9),
        ),
        'legendary×classic-light(coral→info#0072B2)': (
          const Color(0xFFFF6B6B),
          const Color(0xFF0072B2),
        ),
      };
      for (final MapEntry(key: label, value: ends) in impossiblePairs.entries) {
        final ink = ThemeUtils.getContrastSafeTextOnGradient(
          ends.$1,
          ends.$2,
        );
        final minRatio = ThemeUtils.minContrastOnGradient(
          ink,
          ends.$1,
          ends.$2,
        );
        expect(
          minRatio,
          lessThan(4.5),
          reason: '$label 最好公共墨下界 $minRatio 应低于正文阈值',
        );
      }
    });

    test('弹窗内圆图标墨 ≥3:1（非文字关键部件，恒浅底，双白实测）', () {
      // 图标=DS.onColor(DS.neutral0)：neutral0 暗档 #F4F1EB / 亮档白。
      const darkVariant = Color(0xFFF4F1EB);
      const lightVariant = Colors.white;
      final ink = ThemeUtils.getContrastSafeText(darkVariant);
      expect(contrastRatio(ink, darkVariant), greaterThanOrEqualTo(3.0),
          reason: '内圆图标（暗档 neutral0）',);
      expect(contrastRatio(ink, lightVariant), greaterThanOrEqualTo(3.0),
          reason: '内圆图标（亮档 neutral0）',);
      // E-：旧 rare 图标 identity 色（rarityRareText）对暗档内圆 2.89:1。
      expect(
        contrastRatio(const Color(0xFFB8860B), darkVariant),
        lessThan(3.0),
        reason: '旧 rare 图标配对应低于非文字阈值',
      );
    });

    test('庆祝可关文案承诺 ≥4.5:1（DS.surfacePrimary 卡面，黑纱不垫底）', () {
      // milestone/contract 修复后的运行时承诺：庆祝标签垫 surfacePrimary
      // 卡面（不再裸压 40% 黑纱），四档按卡面实算达标。
      _allProfiles.forEach((name, c) {
        final ink = ThemeUtils.getContrastSafeText(c.surfacePrimary);
        final ratio = contrastRatio(ink, c.surfacePrimary);
        expect(ratio, greaterThanOrEqualTo(4.5), reason: '$name 庆祝标签');
      });
    });

    test('光子账本：warning 墨压 warningLight ≥4.5:1（访客横幅按底实算）', () {
      _allProfiles.forEach((name, c) {
        // warningLight 运行时口径（design_system）：warning 向白偏移
        // （暗档 0.15 / 亮档 0.2）。
        final bg = Color.lerp(
          c.semanticWarning,
          const Color(0xFFFFFFFF),
          c.brightness == Brightness.dark ? 0.15 : 0.2,
        )!;
        final ink = ThemeUtils.getContrastSafeText(bg);
        final ratio = contrastRatio(ink, bg);
        expect(ratio, greaterThanOrEqualTo(4.5), reason: '$name 访客横幅');
      });
    });

    test('火堆等级徽标墨 ≥4.5:1（brandPrimary 实心底实算，修复前 1.0–1.7:1）', () {
      _allProfiles.forEach((name, c) {
        final badgeBg = Color.alphaBlend(
          c.brandPrimary.withValues(alpha: 0.9),
          c.surfacePrimary,
        );
        final ink = ThemeUtils.getContrastSafeText(badgeBg);
        final ratio = contrastRatio(ink, badgeBg);
        expect(ratio, greaterThanOrEqualTo(4.5), reason: '$name 火堆徽标');
      });
    });

    test('E- 控制组：修复前火堆徽标配对（火色压 brandPrimary 底）必须判负', () {
      _allProfiles.forEach((name, c) {
        final badgeBg = Color.alphaBlend(
          c.brandPrimary.withValues(alpha: 0.9),
          c.surfacePrimary,
        );
        final ratio = contrastRatio(c.semanticWarning, badgeBg);
        expect(
          ratio,
          lessThan(4.5),
          reason: '$name 旧配对 warning/badgeBg=$ratio 应低于正文阈值',
        );
      });
    });

    test('小队 hub 渐变图标墨 ≥3:1（非文字，渐变最难端 brandPrimary）', () {
      _allProfiles.forEach((name, c) {
        // 运行时口径：getContrastSafeText(DS.brandPrimary)（最难端）。
        final ink = ThemeUtils.getContrastSafeText(c.brandPrimary);
        final ratio = contrastRatio(ink, c.brandPrimary);
        expect(ratio, greaterThanOrEqualTo(3.0), reason: '$name hub 图标');
      });
    });

    test('地图详情面板状态 chip 墨 ≥4.5:1（textSecondary 对 deepSpace 面板）', () {
      _allProfiles.forEach((name, c) {
        // deepSpaceStart 运行时口径（design_system）：暗档=galaxy 混合，
        // 亮档=neutral50 混 brandSecondary 12%。
        final isDark = c.brightness == Brightness.dark;
        final panel = isDark
            ? Color.lerp(c.galaxyBackground, c.surfaceAmbient, 0.5)!
            : Color.lerp(const Color(0xFFFAFAFA), c.brandSecondary, 0.12)!;
        final ratio = contrastRatio(c.textSecondary, panel);
        expect(ratio, greaterThanOrEqualTo(4.5), reason: '$name 状态 chip');
      });
    });
  });
}
