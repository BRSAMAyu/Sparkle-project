import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/data/repositories/error_book_repository.dart';
import 'package:sparkle/features/error_book/presentation/screens/error_list_screen.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';
import '../../../../shared/i18n_test_helper.dart';

/// SEARCH-EMPTY（N28-③/④）：错题搜索无结果两态区分回归钉。
///
/// 「搜了没有」必须显示 EmptyState.noResults 专用态（回显关键词+清空搜索
/// 动作），禁再读作「还没有错题记录」空库态——误导会诱发误建重复错题。
void main() {
  setUp(setUpI18nForTesting);

  ErrorRecord errorWith(String question) => ErrorRecord(
        id: 'error-$question',
        questionText: question,
        userAnswer: 'B',
        correctAnswer: 'A',
        subject: 'math',
        masteryLevel: 0.4,
        reviewCount: 0,
        createdAt: DateTime(2026, 4, 26, 9),
        updatedAt: DateTime(2026, 4, 26, 9),
      );

  Future<void> pumpScreen(
    WidgetTester tester, {
    required _KeywordFilteringErrorBookRepository repo,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [errorBookRepositoryProvider.overrideWithValue(repo)],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const ErrorListScreen(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
  }

  testWidgets(
      'search zero-hit shows dedicated noResults state with clear action, '
      'not the empty-library state', (tester) async {
    final repo = _KeywordFilteringErrorBookRepository(
      items: [errorWith('dirichlet 边界条件')],
    );
    await pumpScreen(tester, repo: repo);

    // 搜过之前：正常列表显示条目，两种空态都不出现。
    expect(find.text('dirichlet 边界条件'), findsOneWidget);

    // 打开搜索并输入不存在的关键词（300ms Timer 防抖放行后列表刷新）。
    await tester.tap(find.byIcon(Icons.search));
    await tester.pump();
    await tester.enterText(find.byType(TextField), '不存在的关键词');
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 200));

    // 两态区分：无结果专用态回显关键词并提供清空搜索；空库态不出现。
    expect(find.text('没有找到与“不存在的关键词”相关的内容'), findsOneWidget);
    expect(find.text('清空搜索'), findsOneWidget);
    expect(find.text('还没有错题记录'), findsNothing);
    expect(find.text('添加第一道错题'), findsNothing);

    // clear 钮可达：清词回到搜过之前（条目回归，专用态消失）。
    await tester.tap(find.text('清空搜索'));
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.text('dirichlet 边界条件'), findsOneWidget);
    expect(find.text('没有找到与“不存在的关键词”相关的内容'), findsNothing);
  });

  testWidgets(
      'empty library without search keeps the empty-library state '
      '(没搜过 ≠ 搜了没有)', (tester) async {
    await pumpScreen(
      tester,
      repo: _KeywordFilteringErrorBookRepository(),
    );

    expect(find.text('还没有错题记录'), findsOneWidget);
    expect(find.text('添加第一道错题'), findsOneWidget);
    expect(find.text('清空搜索'), findsNothing);
  });
}

/// 按 keyword 过滤的替身——服务端 ILIKE 语义的最小等价（不命中返回空页）。
class _KeywordFilteringErrorBookRepository extends ErrorBookRepository {
  _KeywordFilteringErrorBookRepository({this.items = const <ErrorRecord>[]})
      : super(Dio());

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
  }) async {
    final trimmed = keyword?.trim() ?? '';
    final matched = trimmed.isEmpty
        ? items
        : items
            .where(
              (item) => item.questionText
                  .toLowerCase()
                  .contains(trimmed.toLowerCase()),
            )
            .toList();
    return ErrorListResponse(
      items: matched,
      total: matched.length,
      page: page,
      pageSize: pageSize,
      hasNext: false,
    );
  }

  @override
  Future<ReviewStats> getStats() async => const ReviewStats(
        totalErrors: 0,
        masteredCount: 0,
        needReviewCount: 0,
        reviewStreakDays: 0,
        subjectDistribution: <String, int>{},
      );
}
