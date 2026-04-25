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

void main() {
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
        child: MaterialApp(
          theme: AppThemes.lightTheme,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: const Locale('zh'),
          home: const ErrorListScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('还没有错题记录'), findsOneWidget);
    expect(find.text('添加第一道错题'), findsOneWidget);
  });
}

class _FakeErrorBookRepository extends ErrorBookRepository {
  _FakeErrorBookRepository() : super(Dio());

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
        items: const <ErrorRecord>[],
        total: 0,
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
