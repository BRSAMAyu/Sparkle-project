// J-08 Goal Trajectory card + star-map outcome evidence same-source tests.
//
// Covers:
//   1. the goal-detail trajectory card renders the full "idea → outcome"
//      chain from GET /journey/trajectory (idea motivation, milestone
//      reached, ledger-verified outcome with evidence count, reflection
//      echo, galaxy nodes lit) — value narrative = evidence & outcomes,
//      never minutes/streak;
//   2. the SAME outcome id is presented on both mobile faces: the goal
//      trajectory face (/journey/trajectory galaxy ring) and the star map
//      face (GalaxyNodeModel.graph_event_sources → outcomeEvidenceIds) —
//      data-level same-source assertion;
//   3. GalaxyNodeModel parses graph_event_sources defensively (missing /
//      malformed entries degrade to empty without throwing).
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/goal/presentation/providers/goal_trajectory_provider.dart';
import 'package:sparkle/features/goal/presentation/screens/goal_detail_screen.dart';
import 'package:sparkle/features/goal/presentation/widgets/goal_trajectory_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

/// The outcome id shared by BOTH faces in these fixtures — the same-source
/// pin (backend derives it via derive_outcome_id; both read sides project it
/// without alteration).
const String _sharedOutcomeId = 'outc_3f9a2b7c4d5e6f8081a2b3c4d5e6f708';

class _StubApiClient implements ApiClient {
  _StubApiClient(this.goalDetailPayload, this.trajectoryPayload);

  final Map<String, dynamic> goalDetailPayload;
  final Map<String, dynamic> trajectoryPayload;

  @override
  Dio get dio => Dio();

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    if (path.contains('/journey/trajectory')) {
      return Response<T>(
        data: trajectoryPayload as T?,
        requestOptions: RequestOptions(path: path),
      );
    }
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
    throw UnimplementedError('Not stubbed POST: $path');
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
      'todays_minimal_next_step': <String, dynamic>{},
      'knowledge_bottlenecks': <dynamic>[],
      'accountability_status': <String, dynamic>{},
      'related_sources': <dynamic>[],
    };

Map<String, dynamic> _trajectoryPayload() => <String, dynamic>{
      'version': 'goal_trajectory.v1',
      'idea': <String, dynamic>{
        'goal_id': 'g1',
        'title': '数据结构期中冲刺',
        'goal_type': 'exam',
        'status': 'active',
        'motivation': '期中考进前 30%',
        'created_at': '2026-09-20T10:00:00',
      },
      'milestones': <dynamic>[
        <String, dynamic>{
          'milestone_id': 'm1',
          'title': '画出二叉树遍历图',
          'reached': true,
          'task_id': 't1',
          'outcome_id': _sharedOutcomeId,
        },
        <String, dynamic>{
          'milestone_id': 'm2',
          'title': '完成一组真题',
          'reached': false,
          'task_id': 't2',
          'outcome_id': null,
        },
      ],
      'outcomes': <dynamic>[
        <String, dynamic>{
          'outcome_id': _sharedOutcomeId,
          'outcome_key': 'task_completion:t1',
          'task_id': 't1',
          'task_title': '画出二叉树遍历图',
          'polarity': 'positive',
          'ledger_truth': 'actual',
          'ledger_verified': true,
          'evidence_count': 2,
          'occurred_at': '2026-09-24T12:00:00',
        },
      ],
      'artifacts': <dynamic>[],
      'reflections': <dynamic>[
        <String, dynamic>{
          'feedback_id': 'f1',
          'task_id': 't1',
          'category': 'too_difficult',
          'stuck_point': '递归边界条件总是写错',
          'effective_method': '先画递归树',
          'adjustment_intention': '下次先写边界用例',
          'memory_id': 'mem-1',
          'submitted_at': '2026-09-24T12:05:00',
        },
      ],
      'experience_candidates': <dynamic>[
        <String, dynamic>{
          'id': 'mem-1',
          'user_id': 'u1',
          'summary': '任务《画出二叉树遍历图》反思；卡点：递归边界条件',
          'occurred_at': '2026-09-24T12:05:00',
          'source_type': 'reflection',
          'source_lane': 'direct_capture',
          'epistemic_class': null,
        },
      ],
      'galaxy': <dynamic>[
        <String, dynamic>{
          'node_id': 'n1',
          'node_name': '二叉树',
          'mastery': 30.0,
          'is_unlocked': true,
          'graph_event_sources': <dynamic>[
            <String, dynamic>{
              'event_type': 'outcome.recorded',
              'source_type': 'outcome_ledger',
              'reference_id': _sharedOutcomeId,
              'label': 'positive',
              'recorded_at': '2026-09-24T12:00:00',
            },
          ],
          'outcome_ids': <dynamic>[_sharedOutcomeId],
        },
      ],
      'value_summary': <String, dynamic>{
        'milestones_reached': 1,
        'milestones_total': 2,
        'outcomes_formed': 1,
        'outcomes_record_kept': 0,
        'artifacts': 0,
        'reflections': 1,
        'experience_candidates': 1,
        'galaxy_nodes_lit': 1,
      },
    };

/// Star-map face fixture: the same node as served by GET /galaxy/graph —
/// `graph_event_sources` carries the SAME outcome id as the trajectory face.
Map<String, dynamic> _starMapNodePayload() => <String, dynamic>{
      'id': 'n1',
      'name': '二叉树',
      'importance_level': 3,
      'sector_code': 'WISDOM',
      'is_seed': false,
      'tags': <dynamic>['tree'],
      'graph_event_sources': <dynamic>[
        <String, dynamic>{
          'event_type': 'outcome.recorded',
          'source_type': 'outcome_ledger',
          'reference_id': _sharedOutcomeId,
          'label': 'positive',
          'recorded_at': '2026-09-24T12:00:00',
        },
        <String, dynamic>{
          'event_type': 'task.completed',
          'source_type': 'spark',
          'reference_id': 't1',
          'recorded_at': '2026-09-24T11:59:00',
        },
      ],
    };

Widget _host(_StubApiClient stub) => ProviderScope(
      overrides: [apiClientProvider.overrideWithValue(stub)],
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
      'trajectory card renders the idea → outcome chain with an '
      'evidence/outcome value narrative and no minutes/streak',
      (tester) async {
    final stub = _StubApiClient(_goalPayload(), _trajectoryPayload());
    await tester.pumpWidget(_host(stub));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Full chain rendered on the Goal page.
    expect(find.text('From idea to outcome'), findsOneWidget);
    expect(
      find.textContaining('期中考进前 30%'),
      findsOneWidget,
      reason: 'idea motivation (the "idea" ring) must be visible',
    );
    expect(
      find.textContaining('Reached'),
      findsOneWidget,
      reason: 'milestone reached state comes from the real task row',
    );
    expect(
      find.textContaining('2 real evidence items'),
      findsOneWidget,
      reason: 'outcome row shows the real evidence count',
    );
    expect(
      find.textContaining('Reflection: 递归边界条件总是写错'),
      findsOneWidget,
      reason: 'reflection row echoes the user-submitted stuck point',
    );
    expect(find.textContaining('Evidence lit 1 star nodes'), findsOneWidget);
    expect(
      find.text('1 outcomes · 1 reflections · 1 growth memories'),
      findsOneWidget,
      reason: 'value narrative headline counts outcomes/reflections — '
          'not minutes or streaks',
    );

    // Work #3 guard: no minutes/streak narrative inside the trajectory card
    // (minute figures may exist elsewhere on the screen — the trajectory
    // card itself must not carry them).
    final cardTexts = tester
        .widgetList<Text>(
          find.descendant(
            of: find.byType(GoalTrajectoryCard),
            matching: find.byType(Text),
          ),
        )
        .map((text) => text.data ?? '')
        .join('\n');
    expect(
      cardTexts.contains('minutes'),
      isFalse,
      reason: 'trajectory card must not narrate minutes',
    );
    expect(
      cardTexts.toLowerCase().contains('streak'),
      isFalse,
      reason: 'trajectory card must not narrate streaks',
    );
  });

  test(
      'same outcome id is presented on both mobile faces (goal trajectory '
      'and star map node) — data-level same-source assertion', () async {
    final stub = _StubApiClient(_goalPayload(), _trajectoryPayload());
    final container = ProviderContainer(
      overrides: [apiClientProvider.overrideWithValue(stub)],
    );
    addTearDown(container.dispose);

    // Goal page face.
    final trajectory =
        await container.read(goalTrajectoryProvider('g1').future);
    final trajectoryOutcomeIds =
        trajectory.galaxy.expand((node) => node.outcomeIds).toSet();

    // Star map face (the payload shape served by GET /galaxy/graph).
    final starNode = GalaxyNodeModel.fromJson(_starMapNodePayload());
    final starOutcomeIds = starNode.outcomeEvidenceIds.toSet();

    expect(trajectoryOutcomeIds, contains(_sharedOutcomeId));
    expect(starOutcomeIds, contains(_sharedOutcomeId));
    expect(
      trajectoryOutcomeIds.intersection(starOutcomeIds),
      contains(_sharedOutcomeId),
      reason: 'the same outcome must be presented on both faces; each face '
          'projects it from its own backend read side without alteration',
    );
  });

  test('GalaxyNodeModel parses graph_event_sources defensively', () {
    // Malformed entries are dropped without throwing; outcome filter only
    // admits outcome_ledger rows.
    final node = GalaxyNodeModel.fromJson(<String, dynamic>{
      'id': 'n2',
      'name': '图',
      'graph_event_sources': <dynamic>[
        'garbage',
        <String, dynamic>{'source_type': 'outcome_ledger'},
      ],
    });
    expect(
      node.outcomeEvidenceIds,
      isEmpty,
      reason: 'outcome rows without reference_id degrade to empty',
    );

    // Missing field entirely → empty, never null-crash.
    final bare = GalaxyNodeModel.fromJson(<String, dynamic>{'id': 'n3'});
    expect(bare.graphEventSources, isEmpty);
    expect(bare.outcomeEvidenceIds, isEmpty);
  });
}
