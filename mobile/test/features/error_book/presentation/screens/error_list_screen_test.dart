import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/data/repositories/error_book_repository.dart';
import 'package:sparkle/features/error_book/presentation/screens/error_list_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('error book empty state includes action entry', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          errorBookRepositoryProvider.overrideWithValue(
            _FakeErrorBookRepository(),
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const ErrorListScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('还没有错题记录'), findsOneWidget);
    expect(find.text('添加第一道错题'), findsOneWidget);
  });

  testWidgets(
      'error list shows guidance when an analyzed error has no node link',
      (WidgetTester tester) async {
    const hint = '暂时没有关联到知识节点。补充学科/章节，或先到 Galaxy 关联课程后再分析，星图就能同步这道错题。';

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          errorBookRepositoryProvider.overrideWithValue(
            _FakeErrorBookRepository(
              items: [
                ErrorRecord(
                  id: 'error-without-node',
                  questionText:
                      'Choose the correct tense: He ___ to school yesterday.',
                  userAnswer: 'go',
                  correctAnswer: 'went',
                  subject: 'english',
                  masteryLevel: 0.2,
                  reviewCount: 0,
                  createdAt: DateTime(2026, 4, 26, 9),
                  updatedAt: DateTime(2026, 4, 26, 9),
                  latestAnalysis: ErrorAnalysis(
                    errorType: 'concept_confusion',
                    errorTypeLabel: '语法规则混淆',
                    rootCause: '时态判断错误',
                    correctApproach: '根据 yesterday 选择过去式',
                    studySuggestion: '复习一般过去时',
                    linkingHint: ErrorLinkingHint(
                      code: 'missing_knowledge_links',
                      message: hint,
                      action: 'add_subject_or_link_course',
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const ErrorListScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text(hint), findsOneWidget);
    expect(find.byIcon(Icons.account_tree_outlined), findsOneWidget);
  });
}

class _FakeErrorBookRepository extends ErrorBookRepository {
  _FakeErrorBookRepository({this.items = const <ErrorRecord>[]}) : super(Dio());

  final List<ErrorRecord> items;

  @override
  Future<ErrorListResponse> getErrors({
    String? subject,
    String? chapter,
    String? nodeId,
    bool? needReview,
    String? keyword,
    double? masteryMin,
    double? masteryMax,
    CognitiveDimension? cognitiveDimension,
    int page = 1,
    int pageSize = 20,
  }) async =>
      ErrorListResponse(
        items: items,
        total: items.length,
        page: page,
        pageSize: pageSize,
        hasNext: false,
      );

  @override
  Future<ReviewStats> getStats() async => const ReviewStats(
        totalErrors: 0,
        masteredCount: 0,
        needReviewCount: 0,
        reviewStreakDays: 0,
        subjectDistribution: <String, int>{},
      );
}
