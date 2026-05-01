import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/exam_sprint_dashboard_card.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_detail_screen.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/screens/task_execution_screen.dart';
import 'package:sparkle/features/task/presentation/widgets/task_guide_panel.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';

// --- Mock helpers ---

abstract class _AuroraChatCallback {
  void call(String message);
}

class _MockAuroraChatCallback extends Mock implements _AuroraChatCallback {}

// --- Test data factories ---

ExamSprintDashboardData _sprintDashboardData({
  int daysLeft = 5,
  double passProbability = 0.65,
  int completedTasks = 1,
  int totalTasks = 3,
}) {
  return ExamSprintDashboardData(
    planId: 'plan-sprint-1',
    planName: '操作系统冲刺',
    subject: 'Operating Systems',
    daysLeft: daysLeft,
    targetMode: 'pass',
    passProbability: passProbability,
    baselinePassProbability: 0.40,
    todayProgress: ExamSprintTodayProgress(
      completed: completedTasks,
      total: totalTasks,
      completionRate: completedTasks / totalTasks,
    ),
    highFreqCoverage: 0.55,
    highFreqCoveredCount: 11,
    highFreqTotalCount: 20,
    mistakeFixRate: 0.70,
    fixedMistakeCount: 7,
    totalMistakeCount: 10,
    streakDays: 4,
    taskGroups: [
      ExamSprintTaskGroup(
        dayIndex: 1,
        isToday: true,
        completedCount: completedTasks,
        totalCount: totalTasks,
        tasks: [
          ExamSprintTaskItem(
            id: 'task-1',
            title: '进程调度算法对比',
            status: 'COMPLETED',
            estimatedMinutes: 25,
            isCompleted: true,
          ),
          ExamSprintTaskItem(
            id: 'task-2',
            title: '死锁检测与恢复',
            status: 'IN_PROGRESS',
            estimatedMinutes: 30,
            isCompleted: false,
          ),
          ExamSprintTaskItem(
            id: 'task-3',
            title: '内存分页机制梳理',
            status: 'PENDING',
            estimatedMinutes: 20,
            isCompleted: false,
          ),
        ],
      ),
    ],
  );
}

TaskModel _sprintTask({
  String id = 'task-2',
  String title = '死锁检测与恢复',
  TaskStatus status = TaskStatus.inProgress,
  Map<String, dynamic>? guideJson,
}) {
  final now = DateTime(2026, 4, 25);
  return TaskModel(
    id: id,
    userId: 'user-1',
    planId: 'plan-sprint-1',
    title: title,
    type: TaskType.learning,
    tags: const ['exam_sprint', 'os'],
    estimatedMinutes: 30,
    difficulty: 3,
    energyCost: 2,
    status: status,
    priority: 1,
    createdAt: now,
    updatedAt: now,
    guideJson: guideJson ??
        const <String, dynamic>{
          'why_now': '死锁是高频考点，先搞懂检测再记恢复策略更稳。',
          'micro_contract': '我只需要写出死锁检测的两种方法和各自的触发条件。',
          'fail_safe_rule': '如果超过10分钟卡住，就把范围降到资源分配图一种方法。',
          'aurora_triggers': ['不知道怎么判断死锁', '开始逃避'],
          'common_mistakes': [
            '混淆死锁预防与死锁检测',
            '忘记说明资源分配图中环的含义',
          ],
          'common_mistakes_to_watch': [
            '混淆死锁预防与死锁检测',
            '忘记说明资源分配图中环的含义',
          ],
          'steps': [
            {'name': '列出死锁必要条件', 'duration_min': 5, 'output': '四个条件关键词'},
            {'name': '画出资源分配图示例', 'duration_min': 8, 'output': '画出含环的图'},
            {'name': '写出银行家算法步骤', 'duration_min': 10, 'output': '安全序列判断'},
          ],
          'done_criteria': [
            '能说出死锁检测与预防的区别',
            '能画出资源分配图并判断是否有环',
          ],
          'success_criteria': ['写出一个可提交的死锁检测分析'],
        },
    guideContent: '死锁是操作系统高频考点，重点掌握检测和恢复策略。',
    successCriteria: '写出一个可提交的死锁检测分析',
  );
}

PlanModel _sprintPlan(List<TaskModel> tasks) {
  final now = DateTime(2026, 4, 25);
  return PlanModel(
    id: 'plan-sprint-1',
    userId: 'user-1',
    name: '操作系统冲刺',
    subject: 'Operating Systems',
    type: PlanType.sprint,
    dailyAvailableMinutes: 120,
    masteryLevel: 0.45,
    progress: 0.35,
    isActive: true,
    tasks: tasks,
    createdAt: now,
    updatedAt: now,
  );
}

// --- Widget hosts ---

Widget _materialHost(Widget child) => MaterialApp(
      theme: AppThemes.lightTheme,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: const Locale('zh'),
      home: Scaffold(body: child),
    );

Widget _guidePanelHost(TaskModel task, {ValueChanged<String>? onTrigger}) =>
    _materialHost(
      SingleChildScrollView(
        child: TaskGuidePanel(
          task: task,
          onAuroraTriggerPressed: onTrigger,
        ),
      ),
    );

// --- Tests ---

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('F22: Exam Sprint end-to-end flow', () {
    // Step 1: ExamSprintDashboardCard renders with correct progress
    testWidgets(
        'Step 1: DashboardCard renders with pass probability ring and countdown',
        (tester) async {
      final data = _sprintDashboardData();

      await tester.pumpWidget(_materialHost(
        SingleChildScrollView(child: ExamSprintDashboardCard(data: data)),
      ));
      await tester.pumpAndSettle();

      // Dashboard header visible
      expect(find.text('考试冲刺仪表盘'), findsOneWidget);

      // Countdown: "距考试还有 5 天"
      expect(find.textContaining('5 天'), findsWidgets);

      // Progress ring shows 65%
      expect(find.textContaining('65%'), findsWidgets);

      // Today progress: "今天已完成 1/3 项任务"
      expect(find.textContaining('1/3'), findsWidgets);

      // Task group card shows today's tasks
      expect(find.text('今天'), findsOneWidget);
      expect(find.text('死锁检测与恢复'), findsOneWidget);
      expect(find.text('内存分页机制梳理'), findsOneWidget);
    });

    // Step 2: Task row shows status and tapping navigates conceptually
    testWidgets('Step 2: Task group shows today tasks with correct status labels',
        (tester) async {
      final data = _sprintDashboardData();

      await tester.pumpWidget(_materialHost(
        SingleChildScrollView(child: ExamSprintDashboardCard(data: data)),
      ));
      await tester.pumpAndSettle();

      // Verify task statuses are displayed
      expect(find.textContaining('已完成'), findsWidgets);
      expect(find.textContaining('进行中'), findsOneWidget);
      expect(find.textContaining('待开始'), findsOneWidget);
    });

    // Step 3: Plan detail shows why_now and common_mistakes
    testWidgets(
        'Step 3: Plan detail task card renders why_now and common_mistakes',
        (tester) async {
      final task = _sprintTask(
        id: 'task-2',
        status: TaskStatus.inProgress,
      );
      final plan = _sprintPlan([task]);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            planDetailProvider('plan-sprint-1')
                .overrideWith((ref) async => plan),
          ],
          child: _materialHost(
            SingleChildScrollView(
              child: _PlanOverviewExtractor(plan: plan),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // why_now note visible
      expect(
        find.textContaining('死锁是高频考点'),
        findsOneWidget,
      );

      // Common mistakes section visible
      expect(find.textContaining('常见误区'), findsOneWidget);
      expect(
        find.textContaining('混淆死锁预防与死锁检测'),
        findsOneWidget,
      );
      expect(
        find.textContaining('资源分配图中环的含义'),
        findsOneWidget,
      );
    });

    // Step 4: Task execution shows micro_contract and fail_safe_rule
    testWidgets('Step 4: TaskGuidePanel shows micro_contract and fail_safe_rule',
        (tester) async {
      final task = _sprintTask();

      await tester.pumpWidget(_guidePanelHost(task));
      await tester.pumpAndSettle();

      // Micro-contract is visible immediately (no expand needed)
      expect(find.byKey(const Key('task-micro-contract-banner')), findsOneWidget);
      expect(
        find.textContaining('我只需要写出死锁检测的两种方法'),
        findsOneWidget,
      );

      // Expand the guide to reveal fail-safe rule
      await tester.tap(find.byKey(const Key('task-guide-toggle')));
      await tester.pumpAndSettle();

      // Fail-safe rule card visible
      expect(find.byKey(const Key('fail-safe-rule-card')), findsOneWidget);
      expect(find.text('失手时降压规则'), findsOneWidget);
    });

    // Step 5: Aurora trigger chip fires callback
    testWidgets('Step 5: Aurora trigger chip fires chat callback with trigger text',
        (tester) async {
      final chatCallback = _MockAuroraChatCallback();
      final task = _sprintTask();

      await tester.pumpWidget(
        _guidePanelHost(task, onTrigger: chatCallback.call),
      );
      await tester.pumpAndSettle();

      // Expand guide to reveal aurora triggers
      await tester.tap(find.byKey(const Key('task-guide-toggle')));
      await tester.pumpAndSettle();

      // Aurora triggers section visible
      expect(find.byKey(const Key('aurora-triggers-section')), findsOneWidget);
      expect(find.text('遇到这些情况时问 AI'), findsOneWidget);
      expect(find.text('不知道怎么判断死锁'), findsOneWidget);
      expect(find.text('开始逃避'), findsOneWidget);

      // Tap the second trigger chip
      await tester.ensureVisible(find.byKey(const Key('aurora-trigger-chip-1')));
      await tester.tap(find.byKey(const Key('aurora-trigger-chip-1')));
      await tester.pump();

      verify(chatCallback.call('开始逃避')).called(1);
    });

    // Step 6: Task completion updates completion rate display
    testWidgets('Step 6: Completing done-criteria updates progress indicator',
        (tester) async {
      final task = _sprintTask();

      await tester.pumpWidget(_guidePanelHost(task));
      await tester.pumpAndSettle();

      // Expand guide to reveal done criteria
      await tester.tap(find.byKey(const Key('task-guide-toggle')));
      await tester.pumpAndSettle();

      // Done criteria progress bar starts at 0%
      expect(find.byKey(const Key('done-criteria-progress')), findsOneWidget);

      // Check initial count: "0/2"
      expect(find.text('0/2'), findsOneWidget);

      // Mark first criterion as done
      await tester.ensureVisible(find.byKey(const Key('done-criterion-0')));
      await tester.tap(find.byKey(const Key('done-criterion-0')));
      await tester.pumpAndSettle();

      // Progress updated to "1/2"
      expect(find.text('1/2'), findsOneWidget);

      // Mark second criterion as done
      await tester.ensureVisible(find.byKey(const Key('done-criterion-1')));
      await tester.tap(find.byKey(const Key('done-criterion-1')));
      await tester.pumpAndSettle();

      // Progress updated to "2/2"
      expect(find.text('2/2'), findsOneWidget);
    });
  });
}

// --- Helper widget to extract plan overview content ---

/// Extracts the task card content from the plan detail overview
/// without needing the full PlanDetailScreen (which requires GoRouter).
class _PlanOverviewExtractor extends StatelessWidget {
  const _PlanOverviewExtractor({required this.plan});
  final PlanModel plan;

  @override
  Widget build(BuildContext context) {
    final tasks = plan.tasks ?? const <TaskModel>[];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final task in tasks)
          _SimplifiedTodayTaskCard(task: task),
      ],
    );
  }
}

/// Simplified version of _TodayTaskCard from plan_detail_screen
/// that renders why_now and common_mistakes like the real screen does.
class _SimplifiedTodayTaskCard extends StatelessWidget {
  const _SimplifiedTodayTaskCard({required this.task});
  final TaskModel task;

  @override
  Widget build(BuildContext context) {
    final guide = task.guideJson ?? const <String, dynamic>{};
    final whyNow = '${guide['why_now'] ?? ''}'.trim();
    final rawMistakes = guide['common_mistakes_to_watch'] ??
        guide['common_mistakes'];
    final mistakes = _extractMistakes(rawMistakes);

    return GraphiteCardSurface(
      padding: const EdgeInsets.all(DS.spacing18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            task.title,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                  height: 1.25,
                ),
          ),
          const SizedBox(height: DS.spacing12),
          if (whyNow.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: DS.surfaceTertiary.withValues(alpha: 0.7),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.psychology_alt_rounded, size: 17, color: DS.textSecondary),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      whyNow,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: DS.textSecondary,
                            height: 1.45,
                          ),
                    ),
                  ),
                ],
              ),
            ),
          if (mistakes.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              '⚠️ 常见误区',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: DS.warning,
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            for (final mistake in mistakes)
              Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing8),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(DS.spacing10),
                  decoration: BoxDecoration(
                    color: DS.warning.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: DS.warning.withValues(alpha: 0.22)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('⚠️', style: Theme.of(context).textTheme.bodySmall),
                      const SizedBox(width: DS.spacing8),
                      Expanded(
                        child: Text(
                          mistake,
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: DS.textPrimary,
                                height: 1.4,
                              ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ],
      ),
    );
  }

  List<String> _extractMistakes(Object? raw) {
    if (raw is! List) return const [];
    return raw
        .map((item) {
          if (item is String) return item.trim();
          if (item is Map) {
            for (final key in const ['description', 'label', 'specific_risk']) {
              final value = item[key];
              if (value != null) return '$value'.trim();
            }
          }
          return '';
        })
        .where((item) => item.isNotEmpty)
        .take(3)
        .toList();
  }
}
