import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/display/lexicon/mastery_band.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/presentation/widgets/error_card.dart';
import '../../../../shared/i18n_test_helper.dart';

/// N12（A-SPEC2 改造 #1）验收：error_card 掌握度位
/// 1. 档位人话为主、百分数次级；
/// 2. 渲染色：进度条 == 单一 owner `masteryBandColor` 的输出（同输入同色）；
///    档位文字墨 == textPrimary（V4-G04：档位语义由文案唯一承载，色相保留
///    在进度条/tint——全强度 success/warning 做小字在像素档不齐 4.5:1，
///    g04_family_four_style_test G4-1 同口径）；
/// 3. error 槽负向断言（测试与渲染读同一 ThemeManager 未初始化态 → light 主题）。
void main() {
  setUp(setUpI18nForTesting);

  for (final entry in <double, String>{
    0.9: '已掌握',
    0.6: '巩固中',
    0.3: '还在学',
  }.entries) {
    testWidgets('mastery ${entry.key} 显示档位「${entry.value}」+ 次级百分数',
        (tester) async {
      await tester.pumpWidget(
        _Harness(
          child: ErrorCard(error: _buildRecord(mastery: entry.key)),
        ),
      );
      await tester.pump();

      // 档位人话出现（主级）。
      expect(find.text(entry.value), findsOneWidget);
      // 百分数降为次级显示（仍保留）。
      expect(find.text('${(entry.key * 100).toInt()}%'), findsOneWidget);
      // 进度条颜色来自唯一 owner。
      final bar = tester.widget<LinearProgressIndicator>(
        find.byType(LinearProgressIndicator),
      );
      expect(bar.valueColor!.value, masteryBandColor(entry.key));
      // 档位文字墨走 textPrimary（V4-G04：语义由文案承载，见文件头注 2）。
      final bandText = tester.widget<Text>(find.text(entry.value));
      expect(bandText.style?.color, DS.textPrimary);
      // 负向断言：error 槽不参与掌握度位。
      expect(masteryBandColor(entry.key), isNot(DS.semanticError));
    });
  }
}

class _Harness extends StatelessWidget {
  const _Harness({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => testMaterialApp(
        home: Scaffold(
          body: Center(
            child: SizedBox(width: 420, child: child),
          ),
        ),
      );
}

ErrorRecord _buildRecord({required double mastery}) {
  final now = DateTime(2026, 9, 22, 12);
  return ErrorRecord(
    id: 'error-mastery-1',
    questionText: '某系统吸收热量后内能增加多少？',
    userAnswer: '0',
    correctAnswer: '根据热力学第一定律计算',
    subject: 'physics',
    masteryLevel: mastery,
    reviewCount: 2,
    createdAt: now,
    updatedAt: now,
  );
}
