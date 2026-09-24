// J-08 Goal Completion → Reflection → Trajectory closed-loop test.
//
// Covers the goal-detail step completion moment end to end:
//   1. completing today's minimal step opens the light celebration overlay
//      (trajectory framing: step → goal, not minutes/streak);
//   2. the one-question micro-reflection writes into the EXISTING task
//      feedback chain (POST /tasks/{id}/feedback, category enum shared with
//      TaskFeedbackDialog / reflection summary);
//   3. the trajectory hooks fire on the existing chains (galaxy refresh
//      trigger + complete_task event into the app event stream);
//   4. the cancel path leaves everything untouched (no celebration, no
//      completion POST).
//
// No new storage is involved anywhere — every write consumed here already
// existed (task complete, task feedback, galaxy trigger, events ingest).
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/features/goal/presentation/screens/goal_detail_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class _RecordingStubApiClient implements ApiClient {
  _RecordingStubApiClient(this.goalDetailPayload);

  final Map<String, dynamic> goalDetailPayload;
  final List<MapEntry<String, Object?>> posts = [];

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
    throw UnimplementedError('Not stubbed GET: $path');
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
    posts.add(MapEntry(path, data));
    return Response<T>(
      data: <String, dynamic>{'success': true} as T?,
      requestOptions: RequestOptions(path: path),
    );
  }

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed PUT: $path');
  }

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed PATCH: $path');
  }

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed DELETE: $path');
  }
}

/// Records complete_task events instead of hitting the network — proves the
/// completion event is written into the existing event-stream chain.
class _RecordingEventStreamService extends AppEventStreamService {
  _RecordingEventStreamService(super.ref, super.apiClient);

  final List<({String entityId, String actionType, String source})> recorded =
      [];

  @override
  Future<void> recordEntityExecution({
    required String entityType,
    required String entityId,
    required String actionType,
    required String source,
    Map<String, dynamic>? payload,
  }) async {
    final entry = (
      entityId: entityId,
      actionType: actionType,
      source: source,
    );
    recorded.add(entry);
  }
}

Map<String, dynamic> _goalPayload() => <String, dynamic>{
      'goal': <String, dynamic>{
        'id': 'g1',
        'title': '数据结构期中冲刺',
        'goal_type': 'exam',
        'status': 'active',
        'target_date': '2099-12-31',
        'mastery': 0.4,
        'progress': 0.5,
        'priority': 'high',
      },
      'minimum_acceptance_criteria': <String, dynamic>{},
      'plan_health': <String, dynamic>{},
      'current_phase': <String, dynamic>{},
      'todays_minimal_next_step': <String, dynamic>{
        'task_id': 't1',
        'title': '完成第 3 章习题',
        'type': 'learning',
        'estimated_minutes': 40,
      },
      'knowledge_bottlenecks': <dynamic>[],
      'accountability_status': <String, dynamic>{},
      'related_sources': <dynamic>[],
    };

Widget _host(_RecordingStubApiClient stub) => ProviderScope(
      overrides: [
        apiClientProvider.overrideWithValue(stub),
        appEventStreamServiceProvider.overrideWith(
          (ref) => _RecordingEventStreamService(ref, stub),
        ),
      ],
      child: MaterialApp(
        theme: ThemeData(extensions: [SparkleThemeExtension.light()]),
        locale: const Locale('en'),
        supportedLocales: const [Locale('en'), Locale('zh')],
        localizationsDelegates: const [AppLocalizations.delegate],
        home: const GoalDetailScreen(goalId: 'g1'),
      ),
    );

void main() {
  setUpAll(() async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
  });

  testWidgets(
      'completing the daily step opens celebration with trajectory framing, '
      'saves one-tap reflection and fires trajectory hooks', (tester) async {
    final stub = _RecordingStubApiClient(_goalPayload());
    await tester.pumpWidget(_host(stub));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Step card complete button (OutlinedButton, distinct from criteria
    // FilledButton); the step card sits below the fold in the default test
    // viewport, so bring it into view first.
    final completeButton = find.widgetWithText(OutlinedButton, 'Complete');
    await tester.ensureVisible(completeButton);
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(completeButton);
    await tester.pump(const Duration(milliseconds: 300));

    // Confirm dialog.
    await tester.tap(
      find.descendant(
        of: find.byType(AlertDialog),
        matching: find.text('Complete'),
      ),
    );
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));

    // 1) Celebration overlay with trajectory framing (step → goal).
    final overlay = find.byKey(const Key('goal-step-celebration'));
    expect(overlay, findsOneWidget);
    expect(find.text('Step done'), findsOneWidget);
    expect(
      find.text('From idea to outcome: “数据结构期中冲刺” just moved forward.'),
      findsOneWidget,
    );
    expect(
      find.descendant(of: overlay, matching: find.text('完成第 3 章习题')),
      findsOneWidget,
      reason: 'the completed step title must appear inside the celebration '
          '(outcome) — the same title also renders on the step card behind',
    );

    // 2) One-question micro-reflection writes into the existing feedback
    //    chain with the shared category enum.
    await tester.tap(find.text('Still hard'));
    await tester.pump(const Duration(milliseconds: 300));

    final feedbackPosts = stub.posts
        .where((entry) => entry.key == '/tasks/t1/feedback')
        .toList();
    expect(
      feedbackPosts,
      hasLength(1),
      reason: 'reflection must reuse the existing task feedback endpoint',
    );
    expect(
      (feedbackPosts.single.value as Map<String, dynamic>)['category'],
      'too_difficult',
    );
    expect(find.text('Noted — it will shape what comes next'), findsOneWidget);

    // Continue closes the celebration.
    await tester.tap(find.text('Next'));
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byKey(const Key('goal-step-celebration')), findsNothing);

    // 3) Trajectory hooks on existing chains: completion POST happened once,
    //    galaxy trigger incremented, complete_task event recorded.
    expect(
      stub.posts.where((entry) => entry.key == '/tasks/t1/complete'),
      hasLength(1),
    );
    final container = ProviderScope.containerOf(
      tester.element(find.byType(GoalDetailScreen)),
    );
    expect(
      container.read(galaxyRefreshTriggerProvider),
      1,
    );
    final events =
        container.read(appEventStreamServiceProvider);
    expect(events, isA<_RecordingEventStreamService>());
    expect(
      (events as _RecordingEventStreamService).recorded,
      contains(
        const (
          entityId: 't1',
          actionType: 'complete_task',
          source: 'goal_detail',
        ),
      ),
    );
  });

  testWidgets('cancel path leaves completion state untouched',
      (tester) async {
    final stub = _RecordingStubApiClient(_goalPayload());
    await tester.pumpWidget(_host(stub));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    final completeButton = find.widgetWithText(OutlinedButton, 'Complete');
    await tester.ensureVisible(completeButton);
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(completeButton);
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(
      find.descendant(
        of: find.byType(AlertDialog),
        matching: find.text('Cancel'),
      ),
    );
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byKey(const Key('goal-step-celebration')), findsNothing);
    expect(
      stub.posts.where((entry) => entry.key == '/tasks/t1/complete'),
      isEmpty,
    );
  });
}
