import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/data/repositories/error_book_repository.dart';
import 'package:sparkle/features/error_book/presentation/screens/error_list_screen.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';
import '../../../../shared/i18n_test_helper.dart';

/// N9（A-SPEC2 改造 #2，top10 #2 error_book 部分）验收：
/// 列表错误态不再双份裸异常直出（存量 `{error}` 插值 + raw error 第二份），
/// 改人话模板 + 保留安全分类话术与重试。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets('列表加载失败：人话模板 + 分类话术，原始异常文本不进 UI',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          errorBookRepositoryProvider.overrideWithValue(
            _ThrowingErrorBookRepository(),
          ),
        ],
        child: testMaterialApp(home: const ErrorListScreen()),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 人话模板（发生了什么+影响+重试指引）。
    expect(
      find.text('错题内容暂时加载不了。你的错题没有丢，点重试再试一次。'),
      findsWidgets,
    );
    // 原始异常细节不进 UI（含旧 `{error}` 模板形态）。
    expect(find.textContaining('boom-detector'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    expect(find.textContaining('加载失败:'), findsNothing);
    // 重试入口保留。
    expect(find.text('重试'), findsWidgets);
  });
}

class _ThrowingErrorBookRepository extends ErrorBookRepository {
  _ThrowingErrorBookRepository() : super(Dio());

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
      throw Exception('boom-detector- internals');

  @override
  Future<ReviewStats> getStats() async => const ReviewStats(
        totalErrors: 0,
        masteredCount: 0,
        needReviewCount: 0,
        reviewStreakDays: 0,
        subjectDistribution: <String, int>{},
      );
}
