import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';

/// SPEC v1.0 §1 语义别名层映射回归（B2-2 建立，B2-3a 扩 tertiary 定标锚点）。
///
/// 红线：语义名是纯别名转发，必须在全部六个主题变体上与 owner 字段
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
    test('primary/secondary/tertiary/disabled 精确转发（全部变体）', () {
      variants.forEach((name, c) {
        expect(c.text.primary, same(c.textPrimary), reason: name);
        expect(c.text.secondary, same(c.textSecondary), reason: name);
        expect(c.text.tertiary, same(c.textTertiary), reason: name);
        expect(c.text.disabled, same(c.textDisabled), reason: name);
      });
    });

    test('textTertiary B2-3a 定标锚点（六变体 Dart 侧钉值）', () {
      // 定标：≥4.5:1 on S0/S1，强调度严格介于 textSecondary 与 textDisabled
      // 之间（计算过程见 v3-output/B2-3A/REPORT.md 回执①）。
      expect(SparkleColors.light().textTertiary, const Color(0xFF736F62));
      expect(
        SparkleColors.light(highContrast: true).textTertiary,
        const Color(0xFF404040),
      );
      expect(
        SparkleColors.light(colorBlindFriendly: true).textTertiary,
        const Color(0xFF707070),
      );
      expect(SparkleColors.dark().textTertiary, const Color(0xFF878375));
      expect(
        SparkleColors.dark(highContrast: true).textTertiary,
        const Color(0xFFCCCCCC),
      );
      expect(
        SparkleColors.dark(colorBlindFriendly: true).textTertiary,
        const Color(0xFF878375),
      );
    });

    test('neutralOutline = Colors.grey 语义收编快照（0xFF9E9E9E，六变体恒等）', () {
      variants.forEach((name, c) {
        expect(c.neutralOutline, const Color(0xFF9E9E9E), reason: name);
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

    test('success/warning/error/info 精确转发，focus 裁决维持 accent 兼任', () {
      variants.forEach((name, c) {
        expect(c.success, same(c.semanticSuccess), reason: name);
        expect(c.warning, same(c.semanticWarning), reason: name);
        expect(c.error, same(c.semanticError), reason: name);
        expect(c.info, same(c.semanticInfo), reason: name);
        // B2-3a 裁决：全 app 无焦点环渲染点，focus 维持 brandPrimary 兼任
        // （扫描证据与建议见 v3-output/B2-3A/REPORT.md 回执②）。
        expect(c.focus, same(c.brandPrimary), reason: name);
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
