// A-6 regression test: the goal detail page must render the target-date chip
// without crashing when `target_date` is null.
//
// Field evidence (android-round1.md A-6, screenshot 39): the page rendered
//   NoSuchMethodError: Class 'AppLocalizationsEn' has no instance getter
//   'goalDetailNoTargetDate'
// because `_buildTargetDateChip` typed its `l10n` parameter `dynamic`, which
// bypassed static resolution for the goalDetail* getters that then lived in
// the goal_detail_l10n.dart extension. The fix types the parameter as
// AppLocalizations; since the L10N-ZH batch the goalDetail* copy lives
// directly on AppLocalizations as arb keys, so the getters resolve statically
// even without any extension.
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/goal/presentation/screens/goal_detail_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class _StubApiClient implements ApiClient {

  _StubApiClient(this.goalDetailPayload);
  final Map<String, dynamic> goalDetailPayload;

  @override
  Dio get dio => Dio();

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    if (path.contains('/experience/goal-detail/')) {
      return Response<T>(
        data: goalDetailPayload as T?,
        requestOptions: RequestOptions(path: path),
      );
    }
    // Every other endpoint surfaces as a provider error, which the goal
    // detail page renders as an empty slot (by design).
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? headers,
    Map<String, dynamic>? queryParameters,
  }) =>
      const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      const Stream<SSEEvent>.empty();

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed: $path');
  }
}

void main() {
  setUpAll(() async {
    // The goal detail header renders the plan-health band whose provider
    // reads ViewStorageService; tests must initialize it like app startup.
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
  });

  testWidgets(
      'goal with null target_date renders the "No date set" chip instead of '
      'NoSuchMethodError', (tester) async {
    final stub = _StubApiClient(<String, dynamic>{
      'goal': <String, dynamic>{
        'id': 'g1',
        'title': 'Data structures midterm sprint',
        'goal_type': 'exam',
        'status': 'active',
        // A-6 crash path: no target date.
        'target_date': null,
        'mastery': 0.42,
        'progress': 0.6,
        'priority': 'high',
      },
      'minimum_acceptance_criteria': <String, dynamic>{},
      'plan_health': <String, dynamic>{},
      'current_phase': <String, dynamic>{},
      'todays_minimal_next_step': <String, dynamic>{},
      'knowledge_bottlenecks': <dynamic>[],
      'accountability_status': <String, dynamic>{},
      'related_sources': <dynamic>[],
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiClientProvider.overrideWithValue(stub),
        ],
        child: MaterialApp(
          theme: ThemeData(extensions: [SparkleThemeExtension.light()]),
          locale: const Locale('en'),
          supportedLocales: const [Locale('en'), Locale('zh')],
          localizationsDelegates: const [AppLocalizations.delegate],
          home: const GoalDetailScreen(goalId: 'g1'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('No date set'),
      findsOneWidget,
      reason:
          'The null target-date chip must render its localized label; a '
          'NoSuchMethodError here means the goalDetail* extension getters '
          'are being resolved dynamically again (A-6 regression)',
    );
    expect(
      find.text('Data structures midterm sprint'),
      findsOneWidget,
      reason: 'The page must render the actual goal header',
    );
  });

  // S-04：Goal trajectory 的社群证据面——采纳回执正常渲染，撤回态如实标示。
  testWidgets(
      'community evidence receipts render adopted and retracted states',
      (tester) async {
    final stub = _StubApiClient(<String, dynamic>{
      'goal': <String, dynamic>{
        'id': 'g-s04',
        'title': 'Portfolio sprint with peer evidence',
        'goal_type': 'project',
        'status': 'active',
        'target_date': null,
        'mastery': 0.5,
        'progress': 0.4,
        'priority': 'high',
      },
      'minimum_acceptance_criteria': <String, dynamic>{},
      'plan_health': <String, dynamic>{},
      'current_phase': <String, dynamic>{},
      'todays_minimal_next_step': <String, dynamic>{},
      'knowledge_bottlenecks': <dynamic>[],
      'accountability_status': <String, dynamic>{},
      'related_sources': <dynamic>[],
      'community_evidence': <dynamic>[
        <String, dynamic>{
          'kind': 'peer_feedback',
          'feedback_id': 'fb-1',
          'shared_resource_id': 'sr-1',
          'verdict': 'helpful',
          'peer_alias': 'A study peer',
          'adopted_at': '2026-09-24T10:00:00',
          'status': 'adopted',
        },
        <String, dynamic>{
          'kind': 'peer_feedback',
          'feedback_id': 'fb-2',
          'shared_resource_id': 'sr-2',
          'verdict': 'applied',
          'adopted_at': '2026-09-23T10:00:00',
          'status': 'retracted',
          'retracted_at': '2026-09-24T11:00:00',
        },
      ],
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiClientProvider.overrideWithValue(stub),
        ],
        child: MaterialApp(
          theme: ThemeData(extensions: [SparkleThemeExtension.light()]),
          locale: const Locale('en'),
          supportedLocales: const [Locale('en'), Locale('zh')],
          localizationsDelegates: const [AppLocalizations.delegate],
          home: const GoalDetailScreen(goalId: 'g-s04'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // 证据卡位于页面中段：先滚动到可见（ListView 懒构建，折叠下方不挂载）。
    await tester.scrollUntilVisible(
      find.text('Community evidence'),
      160,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('Community evidence'), findsOneWidget);
    expect(
      find.text("A study peer's feedback adopted as outcome evidence"),
      findsOneWidget,
    );
    expect(
      find.text('The underlying share was retracted'),
      findsOneWidget,
    );
  });

  testWidgets(
      'goal with an upcoming target_date renders the raw date without '
      'crashing', (tester) async {
    final stub = _StubApiClient(<String, dynamic>{
      'goal': <String, dynamic>{
        'id': 'g2',
        'title': 'Linear algebra problem set',
        'goal_type': 'exam',
        'status': 'active',
        'target_date': '2099-12-31',
        'mastery': 0.3,
        'progress': 0.2,
        'priority': 'normal',
      },
      'minimum_acceptance_criteria': <String, dynamic>{},
      'plan_health': <String, dynamic>{},
      'current_phase': <String, dynamic>{},
      'todays_minimal_next_step': <String, dynamic>{},
      'knowledge_bottlenecks': <dynamic>[],
      'accountability_status': <String, dynamic>{},
      'related_sources': <dynamic>[],
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiClientProvider.overrideWithValue(stub),
        ],
        child: MaterialApp(
          theme: ThemeData(extensions: [SparkleThemeExtension.light()]),
          locale: const Locale('en'),
          supportedLocales: const [Locale('en'), Locale('zh')],
          localizationsDelegates: const [AppLocalizations.delegate],
          home: const GoalDetailScreen(goalId: 'g2'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('2099-12-31'), findsOneWidget);
  });
}
