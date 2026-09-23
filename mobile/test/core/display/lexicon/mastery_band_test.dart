import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/display/lexicon/mastery_band.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

/// N12（A-SPEC2 改造 #1）：掌握度分档唯一 owner 的验收测试。
///
/// 1. 0.8/0.5 阈值单源（边界钉住）；
/// 2. 同输入同色（色槽投影确定）；
/// 3. 负向断言：error 色槽在掌握度位永不出现；
/// 4. 档位人话 zh/en 双语。
void main() {
  final zh = AppLocalizationsZh();
  final en = AppLocalizationsEn();

  group('masteryBandOf 阈值单源（0.8/0.5）', () {
    test('边界值分档正确', () {
      expect(masteryBandOf(0.0), MasteryBand.low);
      expect(masteryBandOf(0.49), MasteryBand.low);
      expect(masteryBandOf(0.5), MasteryBand.mid);
      expect(masteryBandOf(0.79), MasteryBand.mid);
      expect(masteryBandOf(0.8), MasteryBand.high);
      expect(masteryBandOf(1.0), MasteryBand.high);
    });
  });

  group('masteryBandColor 同输入同色', () {
    test('高=success / 中=warning / 低=warning', () {
      expect(masteryBandColor(0.9), DS.semanticSuccess);
      expect(masteryBandColor(0.6), DS.semanticWarning);
      expect(masteryBandColor(0.3), DS.semanticWarning);
    });

    test('负向断言：error 色槽在掌握度位不再出现（存量 <0.5→error 已迁移）', () {
      const samples = [0.0, 0.2, 0.3, 0.49, 0.5, 0.6, 0.79, 0.8, 0.95, 1.0];
      for (final mastery in samples) {
        expect(
          masteryBandColor(mastery),
          isNot(DS.semanticError),
          reason: 'mastery=$mastery 不应落在 error 槽',
        );
      }
    });
  });

  group('masteryBandLabel 档位人话', () {
    test('zh：已掌握 / 巩固中 / 还在学', () {
      expect(masteryBandLabel(0.9, zh), '已掌握');
      expect(masteryBandLabel(0.6, zh), '巩固中');
      expect(masteryBandLabel(0.3, zh), '还在学');
    });

    test('en：Mastered / Getting there / Still learning', () {
      expect(masteryBandLabel(0.9, en), 'Mastered');
      expect(masteryBandLabel(0.6, en), 'Getting there');
      expect(masteryBandLabel(0.3, en), 'Still learning');
    });
  });
}
