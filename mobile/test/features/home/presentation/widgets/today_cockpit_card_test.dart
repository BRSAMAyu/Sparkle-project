import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/today_cockpit_card.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

import '../../../../shared/i18n_test_helper.dart';
import '../../dashboard_test_harness.dart';

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  // J-03 验收锚点：
  // 1. 四态（no-goal / fresh / active / stalled）各有真实数据路径；
  // 2. 卡内唯一 primary CTA；
  // 3. 首屏（DashboardScreen 默认折叠配置）全页唯一 primary CTA。
  ActiveGoalSnapshot goal(String title) => ActiveGoalSnapshot(
        id: 'goal-1',
        title: title,
        goalType: 'exam',
        healthScore: 0.7,
        weeklyConflictCount: 0,
      );

  HomeGrowthState buildGrowth({
    HomeActivePlanStatus? plan,
    int total = 0,
    int completed = 0,
    HomeBottleneck? bottleneck,
    HomeGrowthTask? nextAction,
  }) =>
      HomeGrowthState(
        planHealth: plan?.healthScore ?? 0,
        tasksTotal: total,
        tasksCompleted: completed,
        streak: 0,
        activePlan: plan,
        activeBottleneck: bottleneck,
        nextAction: nextAction,
      );

  /// F-9：账本任务构造器（进度 chip 的真源是 taskListProvider 账本，
  /// planId 与 goal.id 同一 id 空间）。
  TaskModel ledgerTask(
    String id, {
    String planId = 'goal-1',
    TaskStatus status = TaskStatus.pending,
    DateTime? dueDate,
  }) =>
      TaskModel(
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
        createdAt: DateTime(2026, 4, 8, 9),
        updatedAt: DateTime(2026, 4, 8, 9),
        planId: planId,
        dueDate: dueDate,
      );

  Widget harness(
    Widget child, {
    MultiGoalOverview? goals,
    HomeGrowthState? growthState,
    List<Override> extraOverrides = const [],
  }) =>
      ProviderScope(
        overrides: [
          multiGoalOverviewProvider.overrideWith(
            (ref) async => goals ?? const MultiGoalOverview.empty(),
          ),
          homeGrowthStateProvider
              .overrideWith((ref) async => growthState ?? buildGrowth()),
        ],
        child: buildDashboardWidgetHarness(
          child: child,
          extraOverrides: extraOverrides,
        ),
      );

  Future<void> pumpCockpit(
    WidgetTester tester, {
    MultiGoalOverview? goals,
    HomeGrowthState? growthState,
    List<Override> extraOverrides = const [],
  }) async {
    await initializeDashboardTestEnvironment();
    await tester.pumpWidget(harness(
      const TodayCockpitCard(),
      goals: goals,
      growthState: growthState,
      extraOverrides: extraOverrides,
    ),);
    await tester.pumpAndSettle();
  }

  List<SparkleButton> primaryButtons(WidgetTester tester) => tester
      .widgetList<SparkleButton>(find.byType(SparkleButton))
      .where((button) => button.variant == ButtonVariant.primary)
      .toList();

  group('TodayCockpitCard states', () {
    testWidgets(
      'no-goal: set-first-goal headline with single primary CTA',
      (tester) async {
      await pumpCockpit(tester);

      expect(
          find.byKey(const ValueKey('today-cockpit-skeleton')),
          findsNothing,
        );
      // 唯一 primary：no-goal 态主 CTA = 「和 AI 定目标」。
      final primaries = primaryButtons(tester);
      expect(primaries, hasLength(1));
      expect(primaries.first.label, 'Start with AI');
      // 「我卡住了」次级入口存在。
      expect(find.text("I'm stuck"), findsOneWidget);
      // no-goal 目标起点 chips 存在。
      expect(find.text('Exam Sprint'), findsOneWidget);
    });

    testWidgets('fresh: pending task becomes headline and primary starts it',
        (tester) async {
      await pumpCockpit(
        tester,
        goals: MultiGoalOverview(
          goals: [goal('Pass the exam')],
          selectedGoalId: 'goal-1',
        ),
        growthState: buildGrowth(
          plan: const HomeActivePlanStatus(
            id: 'plan-1',
            name: 'Final Sprint',
            healthScore: 0.8,
          ),
          total: 3,
          nextAction: const HomeGrowthTask(
            id: 't1',
            title: 'Read chapter 3',
            priority: 4,
            isCompleted: false,
          ),
        ),
      );

      expect(find.text('Read chapter 3'), findsOneWidget);
      expect(find.text('Most worth doing today'), findsOneWidget);
      // harness 样例 dashboard 自带 daysToDeadline=3 → why 线取截止信号
      // （why 优先级：瓶颈 > 截止 > 停滞 > 健康度 > 余量）。
      expect(find.text('3 days until deadline'), findsOneWidget);
      final primaries = primaryButtons(tester);
      expect(primaries, hasLength(1));
      expect(primaries.first.label, 'Start Here');
    });

    testWidgets('fresh unarranged: plan with no today tasks offers arrange',
        (tester) async {
      await pumpCockpit(
        tester,
        goals: MultiGoalOverview(
          goals: [goal('Pass the exam')],
          selectedGoalId: 'goal-1',
        ),
        growthState: buildGrowth(
          plan: const HomeActivePlanStatus(
            id: 'plan-1',
            name: 'Final Sprint',
            healthScore: 0.8,
          ),
        ),
      );

      expect(find.text("Today isn't planned yet"), findsOneWidget);
      final primaries = primaryButtons(tester);
      expect(primaries, hasLength(1));
      expect(primaries.first.label, 'Plan today');
    });

    testWidgets('active: completed>0 switches eyebrow to keep-going',
        (tester) async {
      await pumpCockpit(
        tester,
        goals: MultiGoalOverview(
          goals: [goal('Pass the exam')],
          selectedGoalId: 'goal-1',
        ),
        growthState: buildGrowth(
          plan: const HomeActivePlanStatus(
            id: 'plan-1',
            name: 'Final Sprint',
            healthScore: 0.8,
          ),
          total: 3,
          completed: 1,
          nextAction: const HomeGrowthTask(
            id: 't2',
            title: 'Do exercise set 2',
            priority: 3,
            isCompleted: false,
          ),
        ),
        // F-9：进度 chip 真源 = 任务账本（planId=goal-1，3 项完成 1），
        // 与 growth（/tasks/today 选择流）脱钩。
        extraOverrides: [
          staticTaskListOverride([
            ledgerTask('a', status: TaskStatus.completed),
            ledgerTask('b'),
            ledgerTask('c'),
          ]),
        ],
      );

      expect(find.text('Keep going'), findsOneWidget);
      expect(find.text('Do exercise set 2'), findsOneWidget);
      expect(find.text('1/3'), findsOneWidget);
    });

    testWidgets('stalled by bottleneck: primary becomes unblock with why',
        (tester) async {
      await pumpCockpit(
        tester,
        goals: MultiGoalOverview(
          goals: [goal('Pass the exam')],
          selectedGoalId: 'goal-1',
        ),
        growthState: buildGrowth(
          plan: const HomeActivePlanStatus(
            id: 'plan-1',
            name: 'Final Sprint',
            healthScore: 0.8,
          ),
          total: 2,
          completed: 1,
          bottleneck: const HomeBottleneck(
            id: 'b1',
            topic: 'TCP congestion control',
            severity: 'high',
          ),
          nextAction: const HomeGrowthTask(
            id: 't1',
            title: 'Read chapter 3',
            priority: 4,
            isCompleted: false,
          ),
        ),
      );

      expect(find.text('Clear the blocker first'), findsOneWidget);
      expect(find.text('Stuck on "TCP congestion control"'), findsOneWidget);
      final primaries = primaryButtons(tester);
      expect(primaries, hasLength(1));
      expect(primaries.first.label, 'Unblock it');
    });

    testWidgets(
        'O1: example-plan context shows the example badge next to goal chip',
        (tester) async {
      // O1（J-01 实测红线）：种子（示例）上下文必须带声明，不可与真实数据
      // 混淆。示例计划 → 目标 chip 旁渲染「Example」badge。
      await pumpCockpit(
        tester,
        goals: MultiGoalOverview(
          goals: [goal('Data Structures Sprint')],
          selectedGoalId: 'goal-1',
        ),
        growthState: buildGrowth(
          plan: const HomeActivePlanStatus(
            id: 'plan-1',
            name: 'Data Structures Sprint',
            healthScore: 0.8,
            isExample: true,
          ),
          total: 2,
          completed: 1,
          bottleneck: const HomeBottleneck(
            id: 'b1',
            topic: 'Binary tree traversal',
            severity: 'high',
          ),
          nextAction: const HomeGrowthTask(
            id: 't1',
            title: 'Binary tree traversal',
            priority: 4,
            isCompleted: false,
          ),
        ),
      );

      // badge 存在（base 红：无任何示例标识）。
      expect(find.text('Example'), findsOneWidget);
      // 非示例上下文不渲染 badge —— 见下方分组中的对照测试。
    });

    testWidgets('O1: real-plan context renders no example badge',
        (tester) async {
      await pumpCockpit(
        tester,
        goals: MultiGoalOverview(
          goals: [goal('Pass the exam')],
          selectedGoalId: 'goal-1',
        ),
        growthState: buildGrowth(
          plan: const HomeActivePlanStatus(
            id: 'plan-1',
            name: 'Final Sprint',
            healthScore: 0.8,
          ),
          total: 2,
          completed: 1,
          bottleneck: const HomeBottleneck(
            id: 'b1',
            topic: 'TCP congestion control',
            severity: 'high',
          ),
        ),
      );

      expect(find.text('Example'), findsNothing);
    });

    testWidgets('loading: renders skeleton before data lands', (tester) async {
      await initializeDashboardTestEnvironment();
      final goalsCompleter = Completer<MultiGoalOverview>();
      final growthCompleter = Completer<HomeGrowthState>();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            multiGoalOverviewProvider
                .overrideWith((ref) => goalsCompleter.future),
            homeGrowthStateProvider
                .overrideWith((ref) => growthCompleter.future),
          ],
          child: buildDashboardWidgetHarness(child: const TodayCockpitCard()),
        ),
      );
      await tester.pump();

      expect(
          find.byKey(const ValueKey('today-cockpit-skeleton')),
          findsOneWidget,
        );

      // 数据落位后骨架退场（同时冲掉 pending timers）。
      goalsCompleter.complete(const MultiGoalOverview.empty());
      growthCompleter.complete(buildGrowth());
      await tester.pumpAndSettle();
      expect(
          find.byKey(const ValueKey('today-cockpit-skeleton')),
          findsNothing,
        );
      expect(find.text('Start with AI'), findsOneWidget);
    });
  });

  group('Dashboard screen primary CTA uniqueness', () {
    testWidgets('full home screen renders exactly one primary CTA',
        (tester) async {
      await initializeDashboardTestEnvironment();
      await tester.pumpWidget(buildDashboardTestHarness());
      await tester.pump();
      for (var i = 0; i < 12; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }

      final primaries = primaryButtons(tester);
      expect(primaries, hasLength(1));
      // 唯一 primary 属于 Today Cockpit 卡。
      expect(
        find.ancestor(
          of: find.byWidget(primaries.first),
          matching: find.byKey(const ValueKey('today-cockpit-card')),
        ),
        findsOneWidget,
      );
    });
  });
}
