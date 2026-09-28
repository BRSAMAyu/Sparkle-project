import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/agent_run_read_service.dart';
import 'package:sparkle/features/journey/data/repositories/hybrid_journey_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/screens/task_execution_screen.dart';
import 'package:sparkle/shared/entities/task_model.dart';

import '../../../../shared/i18n_test_helper.dart';

/// V4-U04 一审 C-1 · 任务执行屏**整屏 pump** 固化断言。
///
/// 一审探针（临时文件，用后即删）证实：整屏 pump `TaskExecutionScreen` +
/// 读面 stub → `hybrid_journey_entry_section` 真实上树、无 run 时给
/// `journey_entry_start`（非 resume）、零异常。本文件把该探针固化为永久
/// 断言——FIX535 挂载点被移除/条件破坏时此处必红，不再依赖临时探针。
///
/// 注意：区块渲染条件是「读取完成」（读取中不闪占位，设计行为），而真实
/// Dio 在 fake-async 永不完成——故必须 override `agentRunReadServiceProvider`
/// 才能看到该区块（一审 CH-3 记录的现存整屏测试实际看不到区块的原因）。
class _FakeReadService implements AgentRunReadService {
  _FakeReadService(this.runs);

  final List<AgentRunView> runs;

  @override
  Future<AgentRunView?> fetchRun(String runId) async => null;

  @override
  Future<List<AgentRunView>> fetchActiveRuns({String? taskId}) async {
    // 与后端 `GET /runs?active=true&task_id=` 同契约：task_id 过滤在服务端。
    final filtered = taskId == null
        ? runs
        : runs.where((r) => r.taskId == taskId).toList(growable: false);
    return filtered;
  }
}

class _UnusedRepository implements HybridJourneyRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

AgentRunView _journeyRun(String runId, String taskId) => AgentRunView.fromJson(
      <String, dynamic>{
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
      },
    );

TaskModel _localTask() {
  final now = DateTime(2026);
  return TaskModel(
    id: 'local-task',
    userId: 'user-1',
    title: '整理错题原因',
    type: TaskType.learning,
    tags: const ['math'],
    estimatedMinutes: 15,
    difficulty: 2,
    energyCost: 1,
    status: TaskStatus.inProgress,
    priority: 1,
    createdAt: now,
    updatedAt: now,
    guideContent: '先找到题目要求，再写出你自己的第一版答案。',
    guideJson: const <String, dynamic>{},
    successCriteria: '写出一个可提交的结论',
  );
}

Widget _host(TaskModel task, AgentRunReadService readService) => ProviderScope(
      overrides: [
        activeTaskProvider.overrideWith((ref) => task),
        agentRunReadServiceProvider.overrideWithValue(readService),
        // 入口区块 build 不触碰仓库；挂仓以证明整屏 pump 无隐藏依赖。
        hybridJourneyRepositoryProvider.overrideWithValue(_UnusedRepository()),
      ],
      child: testMaterialApp(
        theme: AppThemes.lightTheme,
        home: const TaskExecutionScreen(),
      ),
    );

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<void> pumpScreen(WidgetTester tester, Widget host) async {
    await tester.pumpWidget(host);
    // 整屏有持续动画（widget-test 存量失配），不能 pumpAndSettle——有限帧
    // 推进至读面 Future 完成并渲染。
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump(const Duration(milliseconds: 200));
  }

  testWidgets(
      '整屏 pump：Hybrid 旅程入口区块真实上树于任务执行屏——无进行中 run 给启动入口'
      '（一审 C-1：挂载点永久断言，探针固化）', (tester) async {
    await pumpScreen(
      tester,
      _host(_localTask(), _FakeReadService(const <AgentRunView>[])),
    );

    // 挂载点真实上树（不是注释声明）。
    expect(
      find.byKey(const Key('hybrid_journey_entry_section')),
      findsOneWidget,
    );
    // 无本任务进行中 run → 启动入口（非续跑态，不伪造继续状态）。
    expect(find.byKey(const Key('journey_entry_start')), findsOneWidget);
    expect(find.byKey(const Key('journey_entry_resume')), findsNothing);
    // 整屏渲染零异常（挂载不破坏既有任务执行面）。
    expect(tester.takeException(), isNull);
  });

  testWidgets(
      '整屏 pump：本任务有进行中旅程 run → 同一挂载点渲染续跑入口'
      '（读面数据流入挂载区块，runId 续跑同一段 run）', (tester) async {
    await pumpScreen(
      tester,
      _host(
        _localTask(),
        _FakeReadService(
          <AgentRunView>[_journeyRun('run-j1', 'local-task')],
        ),
      ),
    );

    expect(
      find.byKey(const Key('hybrid_journey_entry_section')),
      findsOneWidget,
    );
    expect(find.byKey(const Key('journey_entry_resume')), findsOneWidget);
    expect(find.byKey(const Key('journey_entry_start')), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
