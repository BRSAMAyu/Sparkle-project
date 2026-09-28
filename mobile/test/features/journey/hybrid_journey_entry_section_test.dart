import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/agent_run_read_service.dart';
import 'package:sparkle/features/journey/data/models/hybrid_journey_models.dart';
import 'package:sparkle/features/journey/data/repositories/hybrid_journey_repository.dart';
import 'package:sparkle/features/journey/presentation/widgets/hybrid_journey_entry_section.dart';

import '../../shared/i18n_test_helper.dart';

/// V4-U04 · 任务面 Hybrid 入口区块行为契约（FIX535：接到合法提案/运行面；
/// 一正一反）：
/// ① 有本任务进行中的旅程 run → 「继续一起推进」按 runId 续跑**同一段 run**
///    （fetchState 幂等回放，start 零调用——不重复生成工件）；
/// ② 没有 → 「和 Sparkle 一起推进」以任务锚定幂等键启动（跨端同键同 run）；
/// ③ 本区块只是入口：不预填、不代答、不携带任何审批写动作（不绕审批）；
/// ④ 读面失败 → 诚实错误，不伪造入口可用状态。
class _FakeRepository implements HybridJourneyRepository {
  _FakeRepository(this.payload);

  final Map<String, dynamic> payload;

  final List<String> fetchStateRunIds = <String>[];
  final List<String> startKeys = <String>[];
  final List<String?> startTaskIds = <String?>[];
  int startCalls = 0;

  @override
  Future<HybridJourneyPayload> start({
    required String idempotencyKey,
    String? taskId,
  }) async {
    startCalls += 1;
    startKeys.add(idempotencyKey);
    startTaskIds.add(taskId);
    return HybridJourneyPayload.fromJson(payload);
  }

  @override
  Future<HybridJourneyPayload> submitJudgment({
    required String runId,
    required List<String> selectedRefs,
    required String idempotencyKey,
    String? focusNote,
  }) async =>
      HybridJourneyPayload.fromJson(payload);

  @override
  Future<HybridJourneyPayload> confirmOutcome({
    required String runId,
    required String idempotencyKey,
    String? note,
  }) async =>
      HybridJourneyPayload.fromJson(payload);

  @override
  Future<HybridJourneyPayload?> fetchState({required String runId}) async {
    fetchStateRunIds.add(runId);
    return HybridJourneyPayload.fromJson(payload);
  }
}

class _FakeReadService implements AgentRunReadService {
  _FakeReadService({this.runs = const [], this.error});

  final List<AgentRunView> runs;
  final Exception? error;

  @override
  Future<AgentRunView?> fetchRun(String runId) async => null;

  @override
  Future<List<AgentRunView>> fetchActiveRuns({String? taskId}) async {
    final failure = error;
    if (failure != null) throw failure;
    // 与后端 `GET /runs?active=true&task_id=` 同契约：task_id 过滤在服务端；
    // 本 fake 忠实模拟该过滤（不把别任务的 run 冒充本任务运行）。
    final filtered = taskId == null
        ? runs
        : runs.where((r) => r.taskId == taskId).toList(growable: false);
    // 记录调用以证明客户端只再按 hybrid journey 标记过滤。
    return filtered;
  }
}

AgentRunView _journeyRun(String runId, String taskId) =>
    AgentRunView.fromJson(<String, dynamic>{
      'run_id': runId,
      'status': 'AWAITING_USER',
      'is_terminal': false,
      'objective': 'Hybrid 旅程：掌握树遍历 —— 材料研判与带引用交付',
      'kind': 'system',
      'trace_id': 'hybrid_journey',
      'task_id': taskId,
      'steps': <dynamic>[],
      'awaiting_step': <String, dynamic>{
        'step_id': 'judgment',
        'ordinal': 2,
        'owner': 'human',
        'state': 'awaiting',
      },
    });

AgentRunView _otherTraceRun(String runId, String taskId) =>
    AgentRunView.fromJson(<String, dynamic>{
      'run_id': runId,
      'status': 'RUNNING',
      'is_terminal': false,
      'objective': '别的链路 run',
      'kind': 'openclaw',
      'task_id': taskId,
      'steps': <dynamic>[],
    });

Map<String, dynamic> _awaitingJudgmentPayload() => <String, dynamic>{
      'version': 'hybrid_journey.v1',
      'run': <String, dynamic>{
        'run_id': 'run-j1',
        'status': 'AWAITING_USER',
        'steps': <dynamic>[],
        'awaiting_step': <String, dynamic>{
          'step_id': 'judgment',
          'ordinal': 2,
          'owner': 'human',
          'state': 'awaiting',
        },
      },
      'goal': <String, dynamic>{'goal_id': 'g1', 'title': '掌握树遍历'},
      'task': <String, dynamic>{'id': 'task-1', 'title': '写综述'},
      'artifacts': <dynamic>[],
      'citations': <dynamic>[],
    };

Widget _harness(
  WidgetTester tester, {
  required String taskId,
  required _FakeRepository repository,
  required _FakeReadService readService,
}) {
  final container = ProviderContainer(
    overrides: [
      agentRunReadServiceProvider.overrideWithValue(readService),
      hybridJourneyRepositoryProvider.overrideWithValue(repository),
    ],
  );
  addTearDown(container.dispose);
  return testMaterialApp(
    home: UncontrolledProviderScope(
      container: container,
      child: Scaffold(
        body: ListView(children: [HybridJourneyEntrySection(taskId: taskId)]),
      ),
    ),
  );
}

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('正：本任务有进行中旅程 run → 继续入口按 runId 幂等回放同一段 run'
      '（start 零调用，不重复生成工件）', (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final readService = _FakeReadService(
      runs: [
        _otherTraceRun('run-x', 'task-1'),
        _journeyRun('run-j1', 'task-1'),
      ],
    );
    await tester.pumpWidget(_harness(
      tester,
      taskId: 'task-1',
      repository: repository,
      readService: readService,
    ),);
    await tester.pumpAndSettle();

    expect(
      find.byKey(const Key('journey_entry_resume')),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const Key('journey_entry_resume')));
    await tester.pumpAndSettle();

    expect(repository.fetchStateRunIds, ['run-j1']);
    expect(repository.startCalls, 0);
  });

  testWidgets('反：本任务没有旅程 run（他任务/他链路不算）→ 只给启动入口；'
      '启动幂等键按任务锚定（跨端同键同 run），不携带任何审批写动作',
      (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final readService = _FakeReadService(
      runs: [
        _journeyRun('run-other-task', 'task-2'),
        _otherTraceRun('run-x', 'task-1'),
      ],
    );
    await tester.pumpWidget(_harness(
      tester,
      taskId: 'task-1',
      repository: repository,
      readService: readService,
    ),);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('journey_entry_resume')), findsNothing);
    expect(find.byKey(const Key('journey_entry_start')), findsOneWidget);

    await tester.tap(find.byKey(const Key('journey_entry_start')));
    await tester.pumpAndSettle();

    // 唯一写动作是「打开 sheet」；启动由 sheet 以任务锚定键发起（ judgment/
    // 审批门留在 sheet 内服务端），入口本身零审批写调用。
    expect(repository.startCalls, 1);
    expect(repository.startKeys, ['j06:start:task-1']);
    expect(repository.startTaskIds, ['task-1']);
    expect(repository.fetchStateRunIds, isEmpty);
  });

  testWidgets('反：读面失败 → 诚实错误文案 + 仍只给启动入口，不伪造继续状态',
      (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final readService = _FakeReadService(error: Exception('offline'));
    await tester.pumpWidget(_harness(
      tester,
      taskId: 'task-1',
      repository: repository,
      readService: readService,
    ),);
    await tester.pumpAndSettle();

    expect(find.textContaining('暂时连不上'), findsOneWidget);
    expect(find.byKey(const Key('journey_entry_resume')), findsNothing);
    expect(find.byKey(const Key('journey_entry_start')), findsOneWidget);
    expect(repository.startCalls, 0);
  });

  testWidgets('反：读取进行中不渲染区块（不闪占位、不伪造入口可用性）',
      (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    // 永不完成的 future 模拟读取中。
    final readService = _FakeReadService();
    final never = Completer<AgentRunView?>();
    final pending = never.future;
    final container = ProviderContainer(
      overrides: [
        agentRunReadServiceProvider.overrideWithValue(readService),
        hybridJourneyRepositoryProvider.overrideWithValue(repository),
        activeHybridJourneyRunForTaskProvider.overrideWith(
          (ref, arg) => pending,
        ),
      ],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(testMaterialApp(
      home: UncontrolledProviderScope(
        container: container,
        child: Scaffold(
          body: ListView(children: const [HybridJourneyEntrySection(taskId: 'task-1')]),
        ),
      ),
    ),);
    await tester.pump();

    expect(
      find.byKey(const Key('hybrid_journey_entry_section')),
      findsNothing,
    );
    expect(repository.startCalls, 0);
  });
}
