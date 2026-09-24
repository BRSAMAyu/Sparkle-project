// F-9（WT324 实测）· 进度口径一致性回归。
//
// 现场证据：多目标看板「100%」（health/timeFraction 百分比）vs cockpit
// chip「0/1」（/tasks/today 选择流，在 1/4 与 0/1 间漂移）vs 任务面板
// 「今日 1 项·已完成 0」（due-today 过滤）——而任务账本真相是 4 项完成 1。
//
// 本卡裁决：进度数字的权威真源 = 任务账本（taskListProvider，GET /tasks），
// 唯一派生点 = task_board_provider.dart 的 ledgerProgressOf。三处消费面
// （cockpit 进度 chip / 多目标看板 goal 行 / 任务板头部汇总）对同一状态
// 必须给出同一数字；/tasks/today 选择流与 due-today 过滤不得再派生进度。
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/multi_goal_dashboard_card.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/task_board_card.dart';
import 'package:sparkle/features/home/presentation/widgets/today_cockpit_card.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

import '../../shared/i18n_test_helper.dart';
import 'dashboard_test_harness.dart';

TaskModel ledgerTask(
  String id, {
  String? planId = 'goal-1',
  TaskStatus status = TaskStatus.pending,
  DateTime? dueDate,
}) {
  final now = DateTime(2026, 4, 8, 9);
  return TaskModel(
    id: id,
    userId: 'user-1',
    title: 'task-$id',
    type: TaskType.learning,
    tags: const [],
    estimatedMinutes: 25,
    difficulty: 1,
    energyCost: 1,
    status: status,
    priority: 1,
    createdAt: now,
    updatedAt: now,
    planId: planId,
    dueDate: dueDate,
  );
}

/// F-9 证据状态：goal-1 名下 4 项任务、完成 1；只有 1 项到期日在今天
/// （旧 due-today 口径会显示「1 项·已完成 0」）。
List<TaskModel> evidenceLedger() {
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  return [
    ledgerTask('t1', status: TaskStatus.completed, dueDate: today),
    ledgerTask('t2', dueDate: today),
    ledgerTask('t3', dueDate: today.subtract(const Duration(days: 1))),
    ledgerTask('t4'),
  ];
}

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ledgerProgressOf（口径单一定义点）', () {
    test('total=非 abandoned，completed 只数 completed', () {
      final progress = ledgerProgressOf([
        ledgerTask('a', status: TaskStatus.completed),
        ledgerTask('b'),
        ledgerTask('c', status: TaskStatus.inProgress),
        ledgerTask('d', status: TaskStatus.abandoned),
      ]);
      expect(progress.totalCount, 3, reason: 'abandoned 不计入总量');
      expect(progress.completedCount, 1);
    });

    test('planId 过滤：只统计该目标名下的任务', () {
      final progress = ledgerProgressOf(
        [
          ledgerTask('a', status: TaskStatus.completed),
          ledgerTask('b'),
          ledgerTask('c', planId: 'goal-2'),
          ledgerTask('d', planId: null),
        ],
        planId: 'goal-1',
      );
      expect(progress.totalCount, 2);
      expect(progress.completedCount, 1);
    });

    test('空账本给出 0/0（调用面以 total>0 决定是否渲染）', () {
      const progress = TaskLedgerProgress.empty();
      expect(progress.totalCount, 0);
      expect(progress.completedCount, 0);
    });
  });

  group('三处消费面对同一状态给出同一数字（F-9 验收）', () {
    testWidgets('cockpit chip / 多目标 goal 行 / 任务板头部 同屏同数',
        (tester) async {
      await initializeDashboardTestEnvironment();
      // 覆盖一律走 harness 的 extraOverrides（追加式、同 provider 后写胜出）：
      // harness 自带内层 ProviderScope（含 taskListProvider 样例夹具），外层
      // 再包 ProviderScope 会被内层遮蔽——本验收首跑即踩中（账本读到样例
      // 夹具而非证据账本，chip/头部全错数）。
      await tester.pumpWidget(
        buildDashboardWidgetHarness(
          extraOverrides: [
            // cockpit 的目标上下文（选中 goal-1）。
            multiGoalOverviewProvider.overrideWith(
              (ref) async => const MultiGoalOverview(
                goals: [
                  ActiveGoalSnapshot(
                    id: 'goal-1',
                    title: 'Final Sprint',
                    goalType: 'exam',
                    healthScore: 0.7,
                    weeklyConflictCount: 0,
                  ),
                ],
                selectedGoalId: 'goal-1',
              ),
            ),
            // /tasks/today 选择流的「漂移快照」（现场 0/1 态）：
            // 进度 chip 不得再消费它。
            homeGrowthStateProvider.overrideWith(
              (ref) async => const HomeGrowthState(
                planHealth: 0.8,
                tasksTotal: 1,
                tasksCompleted: 0,
                streak: 0,
                nextAction: HomeGrowthTask(
                  id: 't2',
                  title: 'Read chapter 3',
                  priority: 4,
                  isCompleted: false,
                ),
              ),
            ),
            // 任务账本：4 项完成 1（真相），计划键 = goal-1。
            // （后写胜出：压过 harness 默认样例夹具。）
            staticTaskListOverride(evidenceLedger()),
          ],
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TodayCockpitCard(),
              TaskBoardCard(),
              MultiGoalDashboardCard(
                overview: MultiGoalOverview(
                  goals: [
                    ActiveGoalSnapshot(
                      id: 'goal-1',
                      title: 'Final Sprint',
                      goalType: 'exam',
                      healthScore: 0.7,
                      weeklyConflictCount: 0,
                    ),
                  ],
                  selectedGoalId: 'goal-1',
                ),
              ),
            ],
          ),
        ),
      );
      // 动画卡面（DashboardEntrance/AnimatedSize）分帧落位。
      for (var i = 0; i < 10; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }

      // 1) cockpit 进度 chip 与多目标 goal 行：均为账本口径 1/4。
      expect(find.text('1/4'), findsNWidgets(2),
          reason: 'cockpit chip 与 goal 行必须与账本真相同数（1 完成/共 4 项）',);
      // 2) 任务板头部：全账本进度（不再是 due-today 的「1 项·已完成 0」）。
      // 折叠默认态下 header 与 collapsed preview 各渲染一次 summary（产品形态）。
      expect(find.text('4 tasks · 1 done'), findsNWidgets(2));
      expect(find.text('1 tasks · 0 done'), findsNothing,
          reason: 'due-today 派生的进度口径必须退场（F-9 三处打架的来源之一）',);
      // 漂移锁：/tasks/today 快照数字（0/1）不得出现在任何进度位。
      expect(find.text('0/1'), findsNothing,
          reason: '选择流快照（0/1）不得再渲染为进度（WT324 F-9 漂移证据）',);
    });
  });
}
