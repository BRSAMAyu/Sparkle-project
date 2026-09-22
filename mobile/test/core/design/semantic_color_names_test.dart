import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';

/// SPEC v1.0 §1 语义别名层映射回归（B2-2）。
///
/// 红线：语义名是纯别名转发，必须在全部四个主题变体上与 owner 字段
/// 逐一同实例（`same`）——任何「顺手改值」都会在这里破绿。
void main() {
  final variants = <String, SparkleColors>{
    'light': SparkleColors.light(),
    'dark': SparkleColors.dark(),
    'lightHighContrast': SparkleColors.light(highContrast: true),
    'darkHighContrast': SparkleColors.dark(highContrast: true),
    'lightColorBlind': SparkleColors.light(colorBlindFriendly: true),
    'darkColorBlind': SparkleColors.dark(colorBlindFriendly: true),
  };

  group('表面阶语义别名（SPEC §1.2）', () {
    test('S0–S3 精确转发到 owner 字段（全部变体、同实例）', () {
      variants.forEach((name, c) {
        expect(c.surface.canvas, same(c.surfaceAmbient), reason: '$name S0');
        expect(c.surface.base, same(c.surfacePrimary), reason: '$name S1');
        expect(c.surface.raised, same(c.surfaceSecondary), reason: '$name S2');
        expect(c.surface.elevated, same(c.surfaceTertiary), reason: '$name S3');
      });
    });

    test('light 阶现值仍钉在 A1.6 seed 锚（防映射层顺手改值）', () {
      final c = SparkleColors.light();
      expect(c.surface.canvas, const Color(0xFFFCF8F3));
      expect(c.surface.base, const Color(0xFFF8F4EF));
      expect(c.surface.raised, const Color(0xFFF1EBE4));
      expect(c.surface.elevated, const Color(0xFFE7DED4));
    });
  });

  group('文字阶语义别名（SPEC §1.3）', () {
    test('primary/secondary/disabled 精确转发（全部变体）', () {
      variants.forEach((name, c) {
        expect(c.text.primary, same(c.textPrimary), reason: name);
        expect(c.text.secondary, same(c.textSecondary), reason: name);
        expect(c.text.disabled, same(c.textDisabled), reason: name);
      });
    });

    test('tertiary 现映射最近 owner 值 textSecondary（TODO B2-3 定标）', () {
      variants.forEach((name, c) {
        expect(c.text.tertiary, same(c.textSecondary), reason: name);
      });
    });
  });

  group('唯一交互 accent 与语义槽（SPEC §1.4/§1.5）', () {
    test('accent = brandPrimary（全部变体），且 ≠ brandSecondary', () {
      variants.forEach((name, c) {
        expect(c.accent, same(c.brandPrimary), reason: name);
        expect(c.accent, isNot(same(c.brandSecondary)), reason: name);
      });
    });

    test('success/warning/error/info 精确转发，focus 现=accent 兼任', () {
      variants.forEach((name, c) {
        expect(c.success, same(c.semanticSuccess), reason: name);
        expect(c.warning, same(c.semanticWarning), reason: name);
        expect(c.error, same(c.semanticError), reason: name);
        expect(c.info, same(c.semanticInfo), reason: name);
        expect(c.focus, same(c.brandPrimary), reason: '$name focus TODO(B2-3)');
      });
    });

    test('light 语义槽现值与 SPEC §1.5 batch-1 校准值一致（Dart 侧锚点）', () {
      final c = SparkleColors.light();
      expect(c.accent, const Color(0xFF825D49)); // §1.4.1 5.31:1
      expect(c.success, const Color(0xFF456E52));
      expect(c.warning, const Color(0xFF7D5C26));
      expect(c.error, const Color(0xFFA0483E));
      expect(c.info, const Color(0xFF48678D)); // 唯一冷色槽
    });
  });
}
