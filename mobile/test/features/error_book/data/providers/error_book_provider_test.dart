import 'package:dio/dio.dart';
import 'package:sparkle/core/offline/list_read_cache.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/models/remediable_pattern.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/data/repositories/error_book_repository.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  // submitReview invalidates plan/task providers whose rebuilds run real
  // Dio error paths; their observability hook reads SharedPreferences, which
  // must be mocked to keep these unit tests hermetic.
  SharedPreferences.setMockInitialValues(const <String, Object>{});

  group('ErrorOperations galaxy refresh', () {
    late ProviderContainer container;

    setUp(() {
      container = ProviderContainer(
        overrides: [
          errorBookRepositoryProvider.overrideWithValue(
            _FakeErrorBookRepository(),
          ),
          notificationServiceProvider.overrideWith(
            _TestNotificationService.new,
          ),
        ],
      );
    });

    tearDown(() {
      container.dispose();
    });

    test('submitReview increments galaxyRefreshTriggerProvider', () async {
      final triggerBefore = container.read(galaxyRefreshTriggerProvider);

      await container.read(errorOperationsProvider.notifier).submitReview(
            errorId: 'err-1',
            performance: 'remembered',
          );

      final triggerAfter = container.read(galaxyRefreshTriggerProvider);

      expect(triggerAfter, triggerBefore + 1);
    });

    test('createError increments galaxyRefreshTriggerProvider', () async {
      final triggerBefore = container.read(galaxyRefreshTriggerProvider);

      await container.read(errorOperationsProvider.notifier).createError(
            questionText: 'What is 2+2?',
            subject: 'math',
          );

      final triggerAfter = container.read(galaxyRefreshTriggerProvider);

      expect(triggerAfter, triggerBefore + 1);
    });
  });

  group('F7-01 real API failure surfaces error state', () {
    late ProviderContainer container;

    setUp(() {
      DemoDataService.isDemoMode = false;
      container = ProviderContainer(
        overrides: [
          errorBookRepositoryProvider.overrideWithValue(
            _ThrowingErrorBookRepository(),
          ),
        ],
      );
    });

    tearDown(() {
      container.dispose();
      DemoDataService.isDemoMode = false;
    });

    test('errorList enters error state instead of demo records', () async {
      await expectLater(
        container.read(errorListProvider(const ErrorListQuery()).future),
        throwsA(isA<Exception>()),
      );

      final state = container.read(errorListProvider(const ErrorListQuery()));
      expect(state.hasError, isTrue);
      expect(state.hasValue, isFalse);
    });

    test('todayReviewList enters error state instead of demo records',
        () async {
      await expectLater(
        container.read(todayReviewListProvider.future),
        throwsA(isA<Exception>()),
      );

      final state = container.read(todayReviewListProvider);
      expect(state.hasError, isTrue);
      expect(state.hasValue, isFalse);
    });

    test('errorStats enters error state instead of demo stats', () async {
      await expectLater(
        container.read(errorStatsProvider.future),
        throwsA(isA<Exception>()),
      );

      final state = container.read(errorStatsProvider);
      expect(state.hasError, isTrue);
      expect(state.hasValue, isFalse);
    });

    test('remediablePatterns enters error state instead of empty fallback',
        () async {
      await expectLater(
        container.read(remediablePatternsProvider.future),
        throwsA(isA<Exception>()),
      );

      final state = container.read(remediablePatternsProvider);
      expect(state.hasError, isTrue);
      expect(state.hasValue, isFalse);
    });
  });

  group('F7-01 explicit demo mode keeps serving demo data', () {
    late ProviderContainer container;

    setUp(() {
      // Repository would throw even in demo mode: the demo branch must
      // short-circuit before any real request is attempted.
      DemoDataService.isDemoMode = true;
      container = ProviderContainer(
        overrides: [
          errorBookRepositoryProvider.overrideWithValue(
            _ThrowingErrorBookRepository(),
          ),
        ],
      );
    });

    tearDown(() {
      container.dispose();
      DemoDataService.isDemoMode = false;
    });

    test('errorList serves demo records in demo mode', () async {
      // N34：provider 返回缓存感知结果，demo 分支 fromCache=false。
      final result = await container
          .read(errorListProvider(const ErrorListQuery()).future);

      expect(result.fromCache, isFalse);
      expect(result.data.items, isNotEmpty);
      expect(
        result.data.items.every((item) => item.id.startsWith('error_')),
        isTrue,
      );
    });

    test('todayReviewList serves demo review records in demo mode', () async {
      final items = await container.read(todayReviewListProvider.future);

      expect(
        items.map((item) => item.id),
        containsAll(<String>['demo_review_1', 'demo_review_2']),
      );
    });

    test('errorStats serves demo stats in demo mode', () async {
      final stats = await container.read(errorStatsProvider.future);

      expect(stats.totalErrors, greaterThan(0));
      expect(stats.subjectDistribution, isNotEmpty);
    });
  });
}

class _FakeErrorBookRepository extends ErrorBookRepository {
  _FakeErrorBookRepository() : super(Dio());

  @override
  Future<ErrorRecord> submitReview({
    required String errorId,
    required String performance,
    int? timeSpentSeconds,
  }) async =>
      ErrorRecord(
        id: errorId,
        questionText: 'test',
        userAnswer: '',
        correctAnswer: '',
        subject: 'math',
        masteryLevel: 0.5,
        reviewCount: 1,
        createdAt: DateTime(2026, 4, 26),
        updatedAt: DateTime(2026, 4, 26),
      );

  @override
  Future<ErrorRecord> createError({
    required String questionText,
    required String subject,
    String? userAnswer,
    String? correctAnswer,
    String? chapter,
    String? questionImageUrl,
  }) async =>
      ErrorRecord(
        id: 'new-err',
        questionText: questionText,
        userAnswer: userAnswer ?? '',
        correctAnswer: correctAnswer ?? '',
        subject: subject,
        masteryLevel: 0,
        reviewCount: 0,
        createdAt: DateTime(2026, 4, 26),
        updatedAt: DateTime(2026, 4, 26),
      );
}

/// Repository whose read methods always fail, simulating an offline device /
/// backend 5xx / gateway timeout on the real API path.
class _ThrowingErrorBookRepository extends ErrorBookRepository {
  _ThrowingErrorBookRepository() : super(Dio());

  static const _failure = 'network unavailable';

  // N34：provider 走缓存感知读——fake 覆盖 Cached 变体（真实请求零依赖）。
  @override
  Future<CacheAwareResult<ErrorListResponse>> getErrorsCached({
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
      throw Exception(_failure);

  @override
  Future<CacheAwareResult<ErrorListResponse>> getTodayReviewListCached({
    int page = 1,
    int pageSize = 20,
  }) async =>
      throw Exception(_failure);

  @override
  Future<CacheAwareResult<ReviewStats>> getStatsCached() async =>
      throw Exception(_failure);

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
      throw Exception(_failure);

  @override
  Future<ErrorListResponse> getTodayReviewList({
    int page = 1,
    int pageSize = 20,
  }) async =>
      throw Exception(_failure);

  @override
  Future<ReviewStats> getStats() async => throw Exception(_failure);

  @override
  Future<List<RemediablePattern>> getRemediablePatterns({
    int limit = 3,
    int lookbackDays = 14,
  }) async =>
      throw Exception(_failure);
}

class _TestNotificationService extends NotificationService {
  _TestNotificationService(super.ref) : super(autoInitialize: false);

  @override
  Future<NotificationPermissionStatus> checkPermissionStatus() async =>
      NotificationPermissionStatus.denied(reason: 'test');

  @override
  Future<bool> requestPermission() async => false;
}
