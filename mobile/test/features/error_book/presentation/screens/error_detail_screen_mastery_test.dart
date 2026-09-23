import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/display/lexicon/mastery_band.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/models/error_semantic_summary.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/data/repositories/error_book_repository.dart';
import 'package:sparkle/features/error_book/presentation/screens/error_detail_screen.dart';
import '../../../../shared/i18n_test_helper.dart';

/// N12 / N9（A-SPEC2 改造 #1+#2）验收：
/// - 掌握度徽章/统计卡取色与档位文案都来自单一 owner（mastery_band.dart）；
/// - 详情错误态=人话模板+安全分类话术，原始异常不再直出。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets('mastery 0.42（低档）：徽章+统计卡同色，档位人话为主、百分数次级',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          errorBookRepositoryProvider.overrideWithValue(
            _FakeErrorBookRepository(
              record: _buildRecord(mastery: 0.42),
            ),
          ),
        ],
        child: testMaterialApp(
          home: const ErrorDetailScreen(errorId: 'error-mastery-1'),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 档位人话出现两次：元数据徽章 + 复习统计卡（值位）。
    expect(find.text('还在学'), findsNWidgets(2));
    // 徽章次级百分数与统计卡口径行。
    expect(find.text('42%'), findsOneWidget);
    expect(find.text('掌握度 42%'), findsOneWidget);

    // 徽章容器描边色 == 单一 owner 输出的派生色（同输入同色）。
    final badgeContainer = tester.widget<Container>(
      find
          .ancestor(
            of: find.text('还在学').first,
            matching: find.byType(Container),
          )
          .first,
    );
    final decoration = badgeContainer.decoration! as BoxDecoration;
    expect(
      (decoration.border! as Border).top.color,
      masteryBandColor(0.42).withValues(alpha: 0.3),
    );

    // 负向断言：error 色槽不参与掌握度位（徽章描边/文字均来自 owner 色）。
    expect(masteryBandColor(0.42), isNot(DS.semanticError));
    expect(
      (decoration.border! as Border).top.color,
      isNot(DS.semanticError.withValues(alpha: 0.3)),
    );
  });

  testWidgets('详情加载失败：人话模板 + 安全分类话术，原始异常不进 UI',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          errorBookRepositoryProvider.overrideWithValue(
            _FakeErrorBookRepository(
              loadError: Exception('boom-detector- internals'),
            ),
          ),
        ],
        child: testMaterialApp(
          home: const ErrorDetailScreen(errorId: 'error-missing'),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 人话模板（发生了什么+影响+重试指引）。
    expect(
      find.text(
        '错题内容暂时加载不了。你的错题没有丢，点重试再试一次。',
      ),
      findsOneWidget,
    );
    // 原始异常细节不进 UI。
    expect(find.textContaining('boom-detector'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    // 重试入口保留。
    expect(find.text('重试'), findsOneWidget);
  });
}

class _FakeErrorBookRepository extends ErrorBookRepository {
  _FakeErrorBookRepository({
    this.record,
    this.loadError,
  }) : super(Dio());

  final ErrorRecord? record;
  final Exception? loadError;

  @override
  Future<ErrorRecord> getError(String errorId) async {
    final error = loadError;
    if (error != null) {
      throw error;
    }
    return record!;
  }

  @override
  Future<ErrorSemanticSummary> getSemanticSummary(String errorId) async =>
      ErrorSemanticSummary(errorId: errorId);
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
