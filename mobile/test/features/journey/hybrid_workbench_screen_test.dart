import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/agent_run_command_service.dart';
import 'package:sparkle/core/services/agent_run_read_service.dart';
import 'package:sparkle/features/journey/data/models/hybrid_journey_models.dart';
import 'package:sparkle/features/journey/data/repositories/hybrid_journey_repository.dart';
import 'package:sparkle/features/journey/presentation/screens/hybrid_workbench_screen.dart';

import '../../shared/i18n_test_helper.dart';

/// V4-U04 · 运行工作台行为契约（FIX535 入口接线；一正一反）：
/// ① 「轮到谁」逐步骤 ownership 可见（我来做/带我做/交给 Sparkle）；
/// ② 旅程 run 恢复走**同一段 run**（fetchState 按 runId 幂等回放，绝不 start
///    新 run——中断/跨端恢复不重复生成工件）；
/// ③ human 步骤只有用户本人确认推进（幂等键确定性推导；step_replay=true 呈现
///    「已确认过」而非报错；命令面只有 confirm/cancel，无 agent 代推进）；
/// ④ 取消显式确认（user_cancelled 终态，不伪装成功）；
/// ⑤ 诚实失败：读面失败呈现错误 + 重试，不伪造可用状态。
class _FakeRepository implements HybridJourneyRepository {
  _FakeRepository(this.fetchStatePayload);

  final Map<String, dynamic> fetchStatePayload;

  final List<String> fetchStateRunIds = <String>[];
  final List<String> startKeys = <String>[];
  int startCalls = 0;

  @override
  Future<HybridJourneyPayload> start({
    required String idempotencyKey,
    String? taskId,
  }) async {
    startCalls += 1;
    startKeys.add(idempotencyKey);
    return HybridJourneyPayload.fromJson(fetchStatePayload);
  }

  @override
  Future<HybridJourneyPayload> submitJudgment({
    required String runId,
    required List<String> selectedRefs,
    required String idempotencyKey,
    String? focusNote,
  }) async =>
      HybridJourneyPayload.fromJson(fetchStatePayload);

  @override
  Future<HybridJourneyPayload> confirmOutcome({
    required String runId,
    required String idempotencyKey,
    String? note,
  }) async =>
      HybridJourneyPayload.fromJson(fetchStatePayload);

  @override
  Future<HybridJourneyPayload?> fetchState({required String runId}) async {
    fetchStateRunIds.add(runId);
    return HybridJourneyPayload.fromJson(fetchStatePayload);
  }
}

class _FakeCommandService implements AgentRunCommandService {
  _FakeCommandService({this.stepReplay = false});

  final List<Map<String, Object?>> completeCalls = <Map<String, Object?>>[];
  final List<Map<String, Object?>> cancelCalls = <Map<String, Object?>>[];
  bool stepReplay;

  @override
  Future<Map<String, dynamic>> completeStep(
    String runId,
    String stepId, {
    required String idempotencyKey,
    String action = 'confirm',
    String? note,
  }) async {
    completeCalls.add(<String, Object?>{
      'run_id': runId,
      'step_id': stepId,
      'idempotency_key': idempotencyKey,
      'action': action,
    });
    return <String, dynamic>{
      'step_replay': stepReplay,
      'run': <String, dynamic>{},
    };
  }

  @override
  Future<Map<String, dynamic>> cancelRun(
    String runId, {
    String? idempotencyKey,
  }) async {
    cancelCalls.add(<String, Object?>{
      'run_id': runId,
      'idempotency_key': idempotencyKey,
    });
    return <String, dynamic>{
      'run': <String, dynamic>{'run_id': runId, 'status': 'CANCELLED'},
    };
  }
}

Map<String, dynamic> _step(
  String stepId,
  int ordinal,
  String owner,
  bool completed,
) =>
    <String, dynamic>{
      'step_id': stepId,
      'ordinal': ordinal,
      'owner': owner,
      'completed': completed,
      'label': stepId,
    };

Map<String, dynamic> _awaiting(String stepId, int ordinal, String owner) =>
    <String, dynamic>{
      'step_id': stepId,
      'ordinal': ordinal,
      'owner': owner,
      'state': 'awaiting',
      'label': stepId,
      'prompt': '这一步需要你',
      'artifacts': <dynamic>[],
    };

AgentRunView journeyRunAwaitingOutcome() => AgentRunView.fromJson(
      <String, dynamic>{
        'run_id': 'run-j1',
        'status': 'AWAITING_USER',
        'is_terminal': false,
        'objective': 'Hybrid 旅程：掌握树遍历 —— 材料研判与带引用交付',
        'kind': 'system',
        'trace_id': 'hybrid_journey',
        'task_id': 'task-1',
        'steps': <dynamic>[
          _step('prep', 1, 'agent', true),
          _step('judgment', 2, 'human', true),
          _step('execute_check', 3, 'agent', true),
          _step('outcome', 4, 'hybrid', false),
        ],
        'awaiting_step': _awaiting('outcome', 4, 'hybrid'),
      },
    );

AgentRunView genericRunAwaitingHuman() => AgentRunView.fromJson(
      <String, dynamic>{
        'run_id': 'run-g1',
        'status': 'AWAITING_USER',
        'is_terminal': false,
        'objective': '比较多份资料，重排后两周计划',
        'kind': 'openclaw',
        'steps': <dynamic>[
          _step('step-1', 1, 'agent', true),
          _step('step-2', 2, 'human', false),
        ],
        'awaiting_step': _awaiting('step-2', 2, 'human'),
      },
    );

AgentRunView genericRunExpiredHuman() => AgentRunView.fromJson(
      <String, dynamic>{
        'run_id': 'run-g1',
        'status': 'AWAITING_USER',
        'is_terminal': false,
        'objective': '比较多份资料，重排后两周计划',
        'kind': 'openclaw',
        'steps': <dynamic>[
          _step('step-1', 1, 'agent', true),
          _step('step-2', 2, 'human', false),
        ],
        'awaiting_step': <String, dynamic>{
          'step_id': 'step-2',
          'ordinal': 2,
          'owner': 'human',
          'state': 'expired',
          'label': 'step-2',
          'prompt': '这一步需要你',
          'artifacts': <dynamic>[],
        },
      },
    );

Map<String, dynamic> _awaitingJudgmentPayload() => <String, dynamic>{
      'version': 'hybrid_journey.v1',
      'run': <String, dynamic>{
        'run_id': 'run-j1',
        'status': 'AWAITING_USER',
        'steps': <dynamic>[
          _step('prep', 1, 'agent', true),
          _step('judgment', 2, 'human', false),
        ],
        'awaiting_step': _awaiting('judgment', 2, 'human'),
      },
      'goal': <String, dynamic>{'goal_id': 'g1', 'title': '掌握树遍历'},
      'task': <String, dynamic>{'id': 'task-1', 'title': '写综述'},
      'artifacts': <dynamic>[],
      'citations': <dynamic>[],
    };

Widget _harness(
  WidgetTester tester, {
  required List<AgentRunView> runs,
  required _FakeRepository repository,
  required _FakeCommandService command,
  Object? loadError,
  String? initialRunId,
  void Function()? onFetch,
}) {
  final container = ProviderContainer(
    overrides: [
      activeAgentRunsProvider.overrideWith((ref) {
        onFetch?.call();
        if (loadError != null) {
          return Future<List<AgentRunView>>.error(loadError);
        }
        return Future.value(runs);
      }),
      agentRunCommandServiceProvider.overrideWithValue(command),
      hybridJourneyRepositoryProvider.overrideWithValue(repository),
    ],
  );
  addTearDown(container.dispose);
  return testMaterialApp(
    home: UncontrolledProviderScope(
      container: container,
      child: HybridWorkbenchScreen(initialRunId: initialRunId),
    ),
  );
}

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('正：运行卡逐步骤 ownership 可见；旅程 run 给恢复入口（继续旅程），'
      'generic run 的 human awaiting 步给统一确认卡（轮到你）', (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final command = _FakeCommandService();
    await tester.pumpWidget(_harness(
      tester,
      runs: [journeyRunAwaitingOutcome(), genericRunAwaitingHuman()],
      repository: repository,
      command: command,
    ),);
    await tester.pumpAndSettle();

    // 两段 run 都列出（沿用 OpenClaw Run ID 的同一读面）。
    expect(find.byKey(const Key('workbench_run_card_run-j1')), findsOneWidget);
    expect(find.byKey(const Key('workbench_run_card_run-g1')), findsOneWidget);
    // ownership 词表可见（我来做/带我做/交给 Sparkle）。
    expect(find.textContaining('交给 Sparkle'), findsWidgets);
    expect(find.textContaining('我来做'), findsWidgets);
    expect(find.textContaining('带我做'), findsWidgets);
    // 旅程 run → 恢复入口；generic run → 统一 awaiting-step 确认卡。
    expect(
      find.byKey(const Key('workbench_resume_journey_run-j1')),
      findsOneWidget,
    );
    expect(find.text('确认，继续'), findsOneWidget);
    // awaiting 高亮：工作台步骤 chip + 统一确认卡的「轮到你了」。
    expect(find.textContaining('轮到你'), findsWidgets);
  });

  testWidgets('正：继续旅程按 runId 幂等回放同一段 run——fetchState 有调用、'
      'start 零调用（中断/跨端恢复不新建 run）', (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final command = _FakeCommandService();
    await tester.pumpWidget(_harness(
      tester,
      runs: [journeyRunAwaitingOutcome()],
      repository: repository,
      command: command,
    ),);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('workbench_resume_journey_run-j1')));
    await tester.pumpAndSettle();

    expect(repository.fetchStateRunIds, ['run-j1']);
    expect(repository.startCalls, 0);
    // sheet 打开并渲染旅程面（同一 HybridJourneySheet，不建第二页面）。
    expect(find.byKey(const Key('hybrid-journey-ready')), findsOneWidget);
  });

  testWidgets('反：无进行中运行 → 空态诚实提示，绝不自动发起旅程（start 零调用）',
      (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final command = _FakeCommandService();
    await tester.pumpWidget(_harness(
      tester,
      runs: const [],
      repository: repository,
      command: command,
    ),);
    await tester.pumpAndSettle();

    expect(find.textContaining('没有进行中的运行'), findsOneWidget);
    expect(repository.startCalls, 0);
    expect(command.completeCalls, isEmpty);
    expect(command.cancelCalls, isEmpty);
  });

  testWidgets('反：读面失败 → 诚实错误 + 重试入口，不伪造可用运行列表',
      (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final command = _FakeCommandService();
    await tester.pumpWidget(_harness(
      tester,
      runs: const [],
      loadError: Exception('network down'),
      repository: repository,
      command: command,
    ),);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('workbench_error')), findsOneWidget);
    expect(find.byKey(const Key('workbench_run_card_run-j1')), findsNothing);
  });

  testWidgets('正：human awaiting 步只能用户确认推进——confirm 携带确定性幂等键；'
      'step_replay=true 呈现「已确认过」而非报错', (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final command = _FakeCommandService(stepReplay: true);
    await tester.pumpWidget(_harness(
      tester,
      runs: [genericRunAwaitingHuman()],
      repository: repository,
      command: command,
    ),);
    await tester.pumpAndSettle();

    expect(command.completeCalls, isEmpty);
    await tester.tap(find.text('确认，继续'));
    await tester.pumpAndSettle();

    // 唯一命令面是用户 confirm（无 agent 代推进路径）；幂等键确定性推导。
    expect(command.completeCalls, hasLength(1));
    expect(command.completeCalls.single['run_id'], 'run-g1');
    expect(command.completeCalls.single['step_id'], 'step-2');
    expect(command.completeCalls.single['idempotency_key'],
        'x07:run-g1:step-2:confirm',);
    expect(command.completeCalls.single['action'], 'confirm');
    // 幂等回放：诚实提示「已确认过」，不是错误、不伪装首次成功。
    expect(find.byKey(const Key('workbench_replay_notice')), findsOneWidget);
    expect(command.cancelCalls, isEmpty);
  });

  testWidgets('正：取消需显式确认；确认后走 user_cancelled（幂等键确定性推导）',
      (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final command = _FakeCommandService();
    await tester.pumpWidget(_harness(
      tester,
      runs: [genericRunAwaitingHuman()],
      repository: repository,
      command: command,
    ),);
    await tester.pumpAndSettle();

    await tester
        .tap(find.byKey(const Key('workbench_cancel_run_run-g1')));
    await tester.pumpAndSettle();
    // 对话框先拦截：未确认前零命令。
    expect(command.cancelCalls, isEmpty);

    await tester.tap(find.byKey(const Key('workbench_cancel_confirm_yes')));
    await tester.pumpAndSettle();

    expect(command.cancelCalls, hasLength(1));
    expect(command.cancelCalls.single['run_id'], 'run-g1');
    expect(command.cancelCalls.single['idempotency_key'],
        'x07:run-g1:step-2:cancel',);
  });

  testWidgets('正：重建（模拟重开 App）后恢复仍指向同一段 run——幂等键逐字一致，'
      '不产生第二次新调用形态', (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final command = _FakeCommandService();
    await tester.pumpWidget(_harness(
      tester,
      runs: [genericRunAwaitingHuman()],
      repository: repository,
      command: command,
    ),);
    await tester.pumpAndSettle();
    await tester.tap(find.text('确认，继续'));
    await tester.pumpAndSettle();
    final firstKey = command.completeCalls.single['idempotency_key'];

    // 模拟进程销毁重开：全新 screen 实例 + 全新 provider 容器。
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpAndSettle();
    final repository2 = _FakeRepository(_awaitingJudgmentPayload());
    final command2 = _FakeCommandService();
    await tester.pumpWidget(_harness(
      tester,
      runs: [genericRunAwaitingHuman()],
      repository: repository2,
      command: command2,
    ),);
    await tester.pumpAndSettle();
    await tester.tap(find.text('确认，继续'));
    await tester.pumpAndSettle();

    expect(command2.completeCalls.single['idempotency_key'], firstKey);
  });

  testWidgets('正：深链 run_id 进入即恢复同一段旅程（冷启动/跨端恢复锚点）',
      (tester) async {
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final command = _FakeCommandService();
    await tester.pumpWidget(_harness(
      tester,
      runs: const [],
      repository: repository,
      command: command,
      initialRunId: 'run-j1',
    ),);
    await tester.pumpAndSettle();

    expect(repository.fetchStateRunIds, ['run-j1']);
    expect(repository.startCalls, 0);
    expect(find.byKey(const Key('hybrid-journey-ready')), findsOneWidget);
  });

  testWidgets('正：expired 步态卡内「刷新」重查 run 读面——绝不误触取消'
      '（一审 R-2 接线勘误的固定断言）', (tester) async {
    var fetchCount = 0;
    final repository = _FakeRepository(_awaitingJudgmentPayload());
    final command = _FakeCommandService();
    await tester.pumpWidget(_harness(
      tester,
      runs: [genericRunExpiredHuman()],
      repository: repository,
      command: command,
      onFetch: () => fetchCount++,
    ),);
    await tester.pumpAndSettle();

    // expired 态：无确认入口，给「刷新」（重查服务端实际状态）。
    expect(find.text('确认，继续'), findsNothing);
    expect(find.text('刷新结果'), findsOneWidget);
    expect(fetchCount, 1);

    await tester.tap(find.text('刷新结果'));
    await tester.pumpAndSettle();

    // 刷新 = 读面重查（客户端非 runtime owner，零本地状态可改）；语义勘误：
    // 不再打开「取消这段运行？」对话框，也不产生任何命令面调用。
    expect(fetchCount, 2);
    expect(find.byKey(const Key('workbench_cancel_confirm_yes')), findsNothing);
    expect(command.cancelCalls, isEmpty);
    expect(command.completeCalls, isEmpty);
    expect(repository.startCalls, 0);
    // 刷新后 run 卡仍在（读面回放同一段 run）。
    expect(find.byKey(const Key('workbench_run_card_run-g1')), findsOneWidget);
  });
}
