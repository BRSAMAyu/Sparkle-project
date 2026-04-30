import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/models/plan_phase_model.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/learning_portfolio_provider.dart';
import 'package:sparkle/features/plan/presentation/screens/exam_sprint_setup_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/learning_portfolio_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_detail_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/sprint_completion_screen.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
import 'package:sparkle/features/task/data/models/execution_record_model.dart';
import 'package:sparkle/features/task/data/models/execution_template_model.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/screens/task_detail_screen.dart';
import 'package:sparkle/features/task/presentation/screens/task_execution_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import '../shared/i18n_test_helper.dart';

class _PreloadedLearningPortfolioNotifier extends LearningPortfolioNotifier {
  _PreloadedLearningPortfolioNotifier(this._result);

  final LearningPortfolioResult _result;

  @override
  Future<LearningPortfolioResult> build() async => _result;
}

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  group('H7 closed-loop sprint UI validation', () {
    testWidgets(
      'setup flows into plan detail and task detail with sprint pack context',
      (tester) async {
        await _useTallSurface(tester);
        final harness = _MutableSprintHarness.intakeAndPlan();

        await tester.pumpWidget(_buildRouterApp(
          initialLocation: '/exam-sprint/setup',
          planRepository: harness.planRepository,
          taskRepository: harness.taskRepository,
          examSprintRepository: harness.examSprintRepository,
        ));
        await _pumpTransitions(tester);

        await tester.enterText(
          find.byType(TextFormField).first,
          '计算机网络',
        );
        await tester.tap(find.text('生成我的第一天任务'));
        await _pumpTransitions(tester, cycles: 4);

        expect(find.text('初步评估已完成'), findsOneWidget);
        expect(find.text('冲刺生存包'), findsOneWidget);

        await tester.tap(find.text('查看整个计划'));
        await _pumpTransitions(tester, cycles: 4);

        expect(find.text('7 天冲刺模式'), findsOneWidget);
        expect(find.text('Sprint Pack 节点'), findsOneWidget);
        expect(find.text('TCP 三次握手'), findsWidgets);
        expect(find.text('拥塞控制'), findsWidgets);
        expect(find.text('retrieval_drill'), findsWidgets);
        expect(find.text('process_trace_card'), findsWidgets);

        await tester.tap(
          find.byKey(
            const ValueKey(
              'plan-task-card-00000000-0000-4000-8000-000000000002',
            ),
          ),
        );
        await _pumpTransitions(tester, cycles: 4);

        expect(find.byType(TaskDetailScreen), findsOneWidget);
        expect(find.byKey(const ValueKey('task-protocol-kind-chip')),
            findsOneWidget);
        expect(find.text('process_trace_card'), findsWidgets);
      },
    );

    testWidgets(
      'sprint pack node dot turns green after task completion',
      (tester) async {
        await _useTallSurface(tester);
        final harness = _MutableSprintHarness.intakeAndPlan();
        final completedHarness = _MutableSprintHarness.intakeAndPlan(
          firstTaskStatus: TaskStatus.completed,
        );

        await tester.pumpWidget(_buildRouterApp(
          initialLocation: '/plans/${harness.planId}',
          planRepository: harness.planRepository,
          taskRepository: harness.taskRepository,
          examSprintRepository: harness.examSprintRepository,
        ));
        await _pumpTransitions(tester);

        final initialColor = _dotColor(
          tester,
          const ValueKey(
            'sprint-pack-node-dot-00000000-0000-4000-8000-000000000001',
          ),
        );

        await tester.pumpWidget(_buildRouterApp(
          initialLocation: '/plans/${completedHarness.planId}',
          planRepository: completedHarness.planRepository,
          taskRepository: completedHarness.taskRepository,
          examSprintRepository: completedHarness.examSprintRepository,
        ));
        await _pumpTransitions(tester);

        final completedColor = _dotColor(
          tester,
          const ValueKey(
            'sprint-pack-node-dot-00000000-0000-4000-8000-000000000001',
          ),
        );

        expect(completedColor, isNot(initialColor));
      },
    );

    testWidgets(
      'stuck help shows Aurora diagnosis and continue closes cleanly',
      (tester) async {
        await _useTallSurface(tester);
        final task = _taskExecutionFixture();

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              activeTaskProvider.overrideWith((ref) => task),
            ],
            child: testMaterialApp(
              theme: AppThemes.lightTheme,
              home: const TaskExecutionScreen(),
            ),
          ),
        );
        await _pumpTransitions(tester, cycles: 2);

        await tester.tap(find.byKey(const Key('stuck-help-fab')));
        await _pumpTransitions(tester, cycles: 4);

        expect(find.text('Aurora 两步帮扶'), findsOneWidget);
        expect(find.text('你是卡在状态迁移，还是卡在报文作用？'), findsOneWidget);
        expect(find.text('先只画一条边：LISTEN 收到 SYN 后进入 SYN_RCVD。'), findsOneWidget);

        await tester.tap(find.byKey(const Key('stuck-help-continue-button')));
        await _pumpTransitions(tester, cycles: 4);

        expect(find.text('Aurora 两步帮扶'), findsNothing);
        expect(find.text(task.title), findsWidgets);
        expect(find.text('完成任务'), findsOneWidget);
      },
    );

    testWidgets(
      'adaptive compression shows one task 35 minute recovery banner',
      (tester) async {
        await _useTallSurface(tester);
        final harness = _MutableSprintHarness.compressedPlan();

        await tester.pumpWidget(_buildRouterApp(
          initialLocation: '/plans/${harness.planId}',
          planRepository: harness.planRepository,
          taskRepository: harness.taskRepository,
          examSprintRepository: harness.examSprintRepository,
        ));
        await _pumpTransitions(tester);

        expect(find.byKey(const ValueKey('plan-adaptive-compression-banner')),
            findsOneWidget);
        expect(find.text('已为你精简今日计划'), findsOneWidget);
        expect(find.textContaining('1 个任务 / 35 分钟'), findsOneWidget);
        expect(find.text('compressed_recovery'), findsWidgets);
      },
    );

    testWidgets(
      'completed sprint auto-navigates to summary and portfolio shows completed state',
      (tester) async {
        await _useTallSurface(tester);
        final harness = _MutableSprintHarness.completedSprint();
        final portfolio = _portfolio(
          planId: harness.planId,
          masteredNodesCount: 9,
          status: 'completed',
          completedAt: DateTime.utc(2026, 5, 1),
        );

        await tester.pumpWidget(_buildRouterApp(
          initialLocation: '/plans/${harness.planId}',
          planRepository: harness.planRepository,
          taskRepository: harness.taskRepository,
          examSprintRepository: harness.examSprintRepository,
          preloadedPortfolio: portfolio,
        ));
        await _pumpTransitions(tester, cycles: 4);
        await tester.pump(const Duration(milliseconds: 950));

        expect(find.byType(SprintCompletionScreen), findsOneWidget);
        expect(find.text('你的 7 天备考成果'), findsOneWidget);
        expect(find.text('9'), findsOneWidget);
        expect(find.text('3'), findsOneWidget);
        expect(find.byType(SparkleConfetti), findsOneWidget);

        await tester.pumpWidget(_buildRouterApp(
          initialLocation: '/exam-sprint/portfolio',
          planRepository: harness.planRepository,
          taskRepository: harness.taskRepository,
          examSprintRepository: harness.examSprintRepository,
          preloadedPortfolio: portfolio,
        ));
        await _pumpTransitions(tester, cycles: 8);

        expect(find.byType(LearningPortfolioScreen), findsOneWidget);
        expect(find.text('已完成'), findsWidgets);
        expect(find.text('2026-05-01（已完成，7天冲刺）'), findsOneWidget);
        expect(find.text('掌握度 9%'), findsOneWidget);
      },
    );
  });
}

Future<void> _useTallSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(900, 1800));
  addTearDown(() => tester.binding.setSurfaceSize(null));
}

Future<void> _pumpTransitions(
  WidgetTester tester, {
  int cycles = 3,
  Duration step = const Duration(milliseconds: 250),
}) async {
  for (var index = 0; index < cycles; index++) {
    await tester.pump(step);
  }
}

Widget _buildRouterApp({
  required String initialLocation,
  required PlanRepository planRepository,
  required TaskRepository taskRepository,
  required ExamSprintRepository examSprintRepository,
  LearningPortfolioResult? preloadedPortfolio,
}) {
  final router = GoRouter(
    initialLocation: initialLocation,
    routes: [
      GoRoute(
        path: '/exam-sprint/setup',
        builder: (context, state) => const ExamSprintSetupScreen(),
      ),
      GoRoute(
        path: '/plans/:id',
        builder: (context, state) =>
            PlanDetailScreen(planId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/tasks/:id',
        builder: (context, state) =>
            TaskDetailScreen(taskId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/tasks/:id/execute',
        builder: (context, state) => const TaskExecutionScreen(),
      ),
      GoRoute(
        path: '/exam-sprint/completion',
        builder: (context, state) {
          final extra = state.extra;
          final extraMap = extra is Map ? extra : const <String, dynamic>{};
          return SprintCompletionScreen(
            planId: state.uri.queryParameters['plan_id'] ?? '',
            subjectName: state.uri.queryParameters['subject'] ?? '',
            initialSummary: extraMap['summary'] as SprintCompletionSummary?,
          );
        },
      ),
      GoRoute(
        path: '/exam-sprint/portfolio',
        builder: (context, state) => const LearningPortfolioScreen(),
      ),
    ],
  );

  return ProviderScope(
    overrides: [
      planRepositoryProvider.overrideWithValue(planRepository),
      taskRepositoryProvider.overrideWithValue(taskRepository),
      examSprintRepositoryProvider.overrideWithValue(examSprintRepository),
      currentUserProvider.overrideWithValue(_mockUser()),
      if (preloadedPortfolio != null)
        learningPortfolioProvider.overrideWith(() => _PreloadedLearningPortfolioNotifier(preloadedPortfolio)),
    ],
    child: MaterialApp.router(
      theme: AppThemes.lightTheme,
      routerConfig: router,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: const Locale('zh'),
    ),
  );
}

Color _dotColor(WidgetTester tester, Key key) {
  final widget = tester.widget<Container>(find.byKey(key));
  final decoration = widget.decoration as BoxDecoration;
  return decoration.color!;
}

TaskModel _taskExecutionFixture() {
  final now = DateTime.utc(2026, 4, 25);
  return TaskModel(
    id: 'local-task',
    userId: 'user-1',
    planId: 'plan-execution',
    title: '画出 TCP 状态迁移',
    type: TaskType.learning,
    tags: const ['exam_sprint', 'day:1'],
    estimatedMinutes: 20,
    difficulty: 2,
    energyCost: 1,
    status: TaskStatus.inProgress,
    priority: 1,
    createdAt: now,
    updatedAt: now,
    guideJson: const <String, dynamic>{
      'stuck_help': {
        'diagnosis_question': '你是卡在状态迁移，还是卡在报文作用？',
        'diagnosis_options': ['状态迁移', '报文作用'],
        'targeted_fix': '先只画一条边：LISTEN 收到 SYN 后进入 SYN_RCVD。',
        'check_question': '下一个问题：SYN_RCVD 收到 ACK 之后会去哪里？',
      },
      'success_criteria': ['能闭卷说出 LISTEN -> SYN_RCVD -> ESTABLISHED'],
    },
    guideContent: '先把状态转移画顺，再去背每个报文的意义。',
    successCriteria: '能闭卷说出 LISTEN -> SYN_RCVD -> ESTABLISHED',
  );
}

UserModel _mockUser() {
  final now = DateTime.utc(2026, 4, 25, 9);
  return UserModel(
    id: 'user-1',
    username: 'tester',
    email: 'tester@example.com',
    flameLevel: 1,
    flameBrightness: 0.5,
    depthPreference: 0.5,
    curiosityPreference: 0.5,
    isActive: true,
    createdAt: now,
    updatedAt: now,
  );
}

class _MutableSprintHarness {
  _MutableSprintHarness({
    required this.planId,
    required this.planRepository,
    required this.taskRepository,
    required this.examSprintRepository,
    required void Function(String taskId) onMarkTaskCompleted,
  }) : _onMarkTaskCompleted = onMarkTaskCompleted;

  final String planId;
  final _FakePlanRepository planRepository;
  final _FakeTaskRepository taskRepository;
  final _FakeExamSprintRepository examSprintRepository;
  final void Function(String taskId) _onMarkTaskCompleted;

  void markTaskCompleted(String taskId) => _onMarkTaskCompleted(taskId);

  static _MutableSprintHarness intakeAndPlan({
    TaskStatus firstTaskStatus = TaskStatus.pending,
  }) {
    final planId = 'plan-sprint-intake';
    final tasks = <TaskModel>[
      _buildTask(
        id: '00000000-0000-4000-8000-000000000001',
        title: 'Day 1 · 画出 TCP 三次握手',
        status: firstTaskStatus,
        estimatedMinutes: 25,
        orderIndex: 1000,
        taskKind: 'retrieval_drill',
        primaryNodeLabel: 'TCP 三次握手',
      ),
      _buildTask(
        id: '00000000-0000-4000-8000-000000000002',
        title: 'Day 1 · 解释拥塞控制四阶段',
        status: TaskStatus.inProgress,
        estimatedMinutes: 30,
        orderIndex: 1001,
        taskKind: 'process_trace_card',
        cardTemplateId: 'process_trace_card',
        primaryNodeLabel: '拥塞控制',
      ),
    ];
    final plan = _buildPlan(
      id: planId,
      name: '计算机网络 7 天冲刺',
      tasks: tasks,
      highlightDay: 1,
      recommendation: '今天先拿下 TCP 三次握手和拥塞控制两条主线。',
      sourceMetadata: _examSprintMetadata(
        daysLeft: 7,
        packName: '冲刺生存包',
      ),
    );
    return _buildHarness(
      planId: planId,
      initialPlan: plan,
      intakeResult: _intakeResult(planId: planId),
      portfolio: _portfolio(
        planId: planId,
        masteredNodesCount: 2,
        status: 'active',
      ),
      completionResult: const SprintCompletionCheckResult(completed: false),
    );
  }

  static _MutableSprintHarness compressedPlan() {
    final planId = 'plan-compressed';
    final task = _buildTask(
      id: '00000000-0000-4000-8000-000000000003',
      title: 'Day 4 · 压缩保底 - 网络层路由',
      status: TaskStatus.pending,
      estimatedMinutes: 35,
      orderIndex: 4000,
      taskKind: 'compressed_recovery',
      primaryNodeLabel: '网络层路由',
      compressed: true,
      compressionReason: '前一天完成率只有 40%，低于 50%，而距离考试只剩 4 天。',
    );
    final plan = _buildPlan(
      id: planId,
      name: '计算机网络压缩冲刺',
      tasks: [task],
      highlightDay: 4,
      recommendation: '今天先保底，不扩写整章。',
      sourceMetadata: {
        ..._examSprintMetadata(daysLeft: 4, packName: '冲刺生存包'),
        'adaptive_compressions': {
          '4': {
            'compressed': true,
            'compression_reason': '前一天完成率只有 40%，低于 50%，而距离考试只剩 4 天。',
          },
        },
      },
    );
    return _buildHarness(
      planId: planId,
      initialPlan: plan,
      intakeResult: _intakeResult(planId: planId),
      portfolio: _portfolio(
        planId: planId,
        masteredNodesCount: 1,
        status: 'active',
      ),
      completionResult: const SprintCompletionCheckResult(completed: false),
    );
  }

  static _MutableSprintHarness completedSprint() {
    final planId = 'plan-completed';
    final tasks = List<TaskModel>.generate(7, (index) {
      final day = index + 1;
      return _buildTask(
        id: '00000000-0000-4000-8000-00000000010$day',
        title: 'Day $day · 核心节点回收',
        status: TaskStatus.completed,
        estimatedMinutes: 20,
        orderIndex: day * 1000,
        taskKind: 'retrieval_drill',
        primaryNodeLabel: '节点 $day',
        completedAt: DateTime.utc(2026, 5, day),
      ).copyWith(syncStatus: TaskSyncStatus.synced);
    });
    final plan = _buildPlan(
      id: planId,
      name: '计算机网络结营冲刺',
      tasks: tasks,
      highlightDay: 7,
      recommendation: '今天已经全部收官。',
      sourceMetadata: _examSprintMetadata(daysLeft: 7, packName: '冲刺生存包'),
      progress: 1,
    );
    return _buildHarness(
      planId: planId,
      initialPlan: plan,
      intakeResult: _intakeResult(planId: planId),
      portfolio: _portfolio(
        planId: planId,
        masteredNodesCount: 9,
        status: 'completed',
        completedAt: DateTime.utc(2026, 5, 1),
      ),
      completionResult: const SprintCompletionCheckResult(
        completed: true,
        summary: SprintCompletionSummary(
          masteredNodesCount: 9,
          repairedErrorsCount: 3,
          completedTasksCount: 7,
          strongestArea: 'TCP 状态迁移',
          growthArea: '路由选择',
        ),
      ),
    );
  }

  static _MutableSprintHarness _buildHarness({
    required String planId,
    required PlanModel initialPlan,
    required ExamSprintIntakeResult intakeResult,
    required LearningPortfolioResult portfolio,
    required SprintCompletionCheckResult completionResult,
  }) {
    var currentPlan = initialPlan;
    final taskMap = <String, TaskModel>{
      for (final task in currentPlan.tasks ?? const <TaskModel>[])
        task.id: task,
    };
    var intakeSubmitted = initialPlan.id != 'plan-sprint-intake' ? true : false;

    PlanModel rebuildPlan() => _buildPlan(
          id: currentPlan.id,
          name: currentPlan.name,
          tasks: taskMap.values.toList()
            ..sort((a, b) => a.orderIndex.compareTo(b.orderIndex)),
          highlightDay: currentPlan.dayHighlights?.day ?? 1,
          recommendation:
              currentPlan.dayHighlights?.recommendation ?? '先把主线接上。',
          sourceMetadata: currentPlan.sourceMetadata,
          progress: taskMap.values.isEmpty
              ? currentPlan.progress
              : taskMap.values
                      .where((task) => task.status == TaskStatus.completed)
                      .length /
                  taskMap.length,
        );

    final planRepository = _FakePlanRepository(
      getPlan: (id) async {
        currentPlan = rebuildPlan();
        return currentPlan;
      },
      getPlans: ({PlanType? type, bool? isActive}) async {
        if (!intakeSubmitted) return const <PlanModel>[];
        currentPlan = rebuildPlan();
        return [currentPlan];
      },
    );
    final taskRepository = _FakeTaskRepository(taskMap);
    final examSprintRepository = _FakeExamSprintRepository(
      onSubmitIntake: () async {
        intakeSubmitted = true;
        return intakeResult;
      },
      onCheckCompletion: (_) async => completionResult,
      onFetchPortfolio: ({String? userId}) async => portfolio,
    );

    return _MutableSprintHarness(
      planId: planId,
      planRepository: planRepository,
      taskRepository: taskRepository,
      examSprintRepository: examSprintRepository,
      onMarkTaskCompleted: (taskId) {
        final task = taskMap[taskId];
        if (task == null) return;
        taskMap[taskId] = task.copyWith(
          status: TaskStatus.completed,
          completedAt: DateTime.utc(2026, 4, 25, 12),
        );
        currentPlan = rebuildPlan();
      },
    );
  }
}

TaskModel _buildTask({
  required String id,
  required String title,
  required TaskStatus status,
  required int estimatedMinutes,
  required int orderIndex,
  required String taskKind,
  String? cardTemplateId,
  required String primaryNodeLabel,
  bool compressed = false,
  String? compressionReason,
  DateTime? completedAt,
}) {
  final now = DateTime.utc(2026, 4, 25, 9);
  return TaskModel(
    id: id,
    userId: 'user-1',
    planId: 'plan',
    title: title,
    type: TaskType.learning,
    tags: [
      'exam_sprint',
      'day:${orderIndex ~/ 1000}',
      if (compressed) 'adaptive_compressed',
    ],
    estimatedMinutes: estimatedMinutes,
    difficulty: compressed ? 1 : 2,
    energyCost: 1,
    status: status,
    priority: 1,
    orderIndex: orderIndex,
    createdAt: now,
    updatedAt: now,
    completedAt: completedAt,
    guideJson: {
      'task_kind': taskKind,
      if (cardTemplateId != null) 'task_card_template_id': cardTemplateId,
      'subject_strategy': {
        'primary_node_label': primaryNodeLabel,
      },
      if (compressed) 'compressed': true,
      if (compressionReason != null) 'compression_reason': compressionReason,
      'daily_spec': {
        'task_kind': taskKind,
        if (cardTemplateId != null) 'task_card_template_id': cardTemplateId,
        'primary_target': primaryNodeLabel,
        if (compressed) 'compressed': true,
      },
    },
    guideContent: '把 $primaryNodeLabel 讲清楚。',
    successCriteria: '能独立复述 $primaryNodeLabel。',
  );
}

PlanModel _buildPlan({
  required String id,
  required String name,
  required List<TaskModel> tasks,
  required int highlightDay,
  required String recommendation,
  required Map<String, dynamic>? sourceMetadata,
  double progress = 0.25,
}) {
  final now = DateTime.utc(2026, 4, 25, 9);
  return PlanModel(
    id: id,
    userId: 'user-1',
    name: name,
    type: PlanType.sprint,
    dailyAvailableMinutes: 90,
    masteryLevel: 0.45,
    progress: progress,
    isActive: true,
    createdAt: now,
    updatedAt: now,
    subject: '计算机网络',
    sourceMetadata: sourceMetadata,
    tasks:
        tasks.map((task) => task.copyWith(planId: id)).toList(growable: false),
    dayHighlights: PlanDayHighlights(
      day: highlightDay,
      recommendation: recommendation,
      tasks: tasks
          .where((task) => task.orderIndex ~/ 1000 == highlightDay)
          .map((task) => task.copyWith(planId: id))
          .toList(growable: false),
    ),
  );
}

Map<String, dynamic> _examSprintMetadata({
  required int daysLeft,
  required String packName,
}) {
  return {
    'exam_sprint_intake': {
      'goal_model': {
        'days_left': daysLeft,
        'target_mode': 'pass',
      },
      'selected_pack': {
        'pack_name': packName,
      },
      'strategy_preview': {
        'sprint_mode': 'seven_day_survival',
      },
    },
  };
}

ExamSprintIntakeResult _intakeResult({required String planId}) {
  return ExamSprintIntakeResult(
    planningSessionId: 'planning-session-1',
    conversationId: 'conversation-1',
    userModel: ExamSprintUserModel(
      subject: '计算机网络',
      examScope: '传输层与网络层高频题',
      knowledgeBaseline: '基础薄弱但能回忆部分主干概念',
      currentLevel: 48,
      weakChapters: const <String>['传输层'],
      dailyStudyMinutes: 90,
      availableMaterials: const <String>['课堂讲义'],
      scopeFileIds: const <String>[],
      scopeFileNames: const <String>[],
      planningSessionId: 'planning-session-1',
      conversationId: 'conversation-1',
    ),
    goalModel: ExamSprintGoalModel(
      examDate: DateTime.utc(2026, 5, 2),
      daysLeft: 7,
      targetMode: 'pass',
      estimatedScoreNow: 48,
      targetScoreHint: 60,
      recommendedMode: 'pass',
    ),
    selectedPack: ExamSprintPackSelection(
      packId: 'pack-cn-v1',
      packName: '冲刺生存包',
      selectionType: 'subject_fit',
      reason: '优先保住高频保底点。',
    ),
    initialAssessment: ExamSprintAssessment(
      passProbability: 0.64,
      recommendedMode: 'pass',
      recommendedModeLabel: '先过',
      summary: '你现在的基础足够走 7 天冲刺，先把高频保底点接上。',
    ),
    strategyPreview: ExamSprintStrategyPreview(
      sprintMode: 'seven_day_survival',
      dailyCommitmentRange: '80-100 分钟',
      firstDayFocus: '先用两张卡接住 TCP 三次握手和拥塞控制。',
      firstDayOutput: '完成 2 张 Sprint Pack 卡片并留下一版闭卷复述。',
    ),
    launch: ExamSprintLaunchPayload(
      planId: planId,
      planName: '计算机网络 7 天冲刺',
      firstDayTaskIds: const <String>[
        '00000000-0000-4000-8000-000000000001',
      ],
      planRoute: '/plans/$planId',
      recommendedTaskId: '00000000-0000-4000-8000-000000000001',
      recommendedTaskRoute: '/tasks/00000000-0000-4000-8000-000000000001',
    ),
  );
}

LearningPortfolioResult _portfolio({
  required String planId,
  required int masteredNodesCount,
  required String status,
  DateTime? completedAt,
}) {
  return LearningPortfolioResult(
    entries: <LearningPortfolioEntry>[
      LearningPortfolioEntry(
        planId: planId,
        planName: '计算机网络 7 天冲刺',
        subject: '计算机网络',
        sprintMode: 'seven_day_survival',
        status: status,
        masteredNodesCount: masteredNodesCount,
        progress: status == 'completed' ? 1 : 0.35,
        strongestArea: 'TCP 状态迁移',
        growthArea: '路由选择',
        completedAt: completedAt,
        targetDate: DateTime.utc(2026, 5, 1),
        weakestPoints: const <String>['路由选择'],
        proudNodes: const <String>['TCP 状态迁移'],
      ),
    ],
    totalMasteredNodes: masteredNodesCount,
    activeCount: status == 'active' ? 1 : 0,
    completedCount: status == 'completed' ? 1 : 0,
    plannedCount: 0,
  );
}

class _FakePlanRepository extends PlanRepository {
  _FakePlanRepository({
    required Future<PlanModel> Function(String id) getPlan,
    required Future<List<PlanModel>> Function({
      PlanType? type,
      bool? isActive,
    }) getPlans,
  })  : _getPlan = getPlan,
        _getPlans = getPlans,
        super(_NoopApiClient());

  final Future<PlanModel> Function(String id) _getPlan;
  final Future<List<PlanModel>> Function({
    PlanType? type,
    bool? isActive,
  }) _getPlans;

  @override
  Future<PlanModel> getPlan(String id) => _getPlan(id);

  @override
  Future<List<PlanModel>> getPlans({PlanType? type, bool? isActive}) =>
      _getPlans(type: type, isActive: isActive);

  @override
  Future<List<PlanModel>> getActivePlans() => getPlans(isActive: true);

  @override
  Future<PlanPhaseBundle> getPlanPhases(String planId) async => PlanPhaseBundle(
        planCardId: null,
        currentPhaseCardId: null,
        progressMode: 'legacy',
        weightedProgress: null,
        phases: const [],
      );
}

class _FakeTaskRepository extends TaskRepository {
  _FakeTaskRepository(this.tasksById) : super(_NoopApiClient());

  final Map<String, TaskModel> tasksById;

  List<TaskModel> get _tasks => tasksById.values.toList()
    ..sort((a, b) => a.orderIndex.compareTo(b.orderIndex));

  @override
  Future<PaginatedResponse<TaskModel>> getTasks({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 10,
  }) async =>
      PaginatedResponse(
        items: _tasks,
        total: _tasks.length,
        page: page,
        pageSize: pageSize,
      );

  @override
  Future<List<TaskModel>> getTodayTasks() async => _tasks;

  @override
  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async =>
      _tasks.take(limit).toList(growable: false);

  @override
  Future<TaskModel> getTask(String id) async => tasksById[id]!;

  @override
  Future<TaskModel> startTask(String id) async {
    final task = tasksById[id]!;
    final updated = task.copyWith(status: TaskStatus.inProgress);
    tasksById[id] = updated;
    return updated;
  }

  @override
  Future<List<ExecutionIntentModel>> listExecutionIntents(
          String taskId) async =>
      const <ExecutionIntentModel>[];

  @override
  Future<ExecutionRecordModel> getExecutionRecord(String executionId) async {
    throw UnimplementedError();
  }

  @override
  Future<List<ExecutionTemplateModel>> listExecutionTemplates(
    String taskId,
  ) async =>
      const <ExecutionTemplateModel>[];
}

class _FakeExamSprintRepository extends ExamSprintRepository {
  _FakeExamSprintRepository({
    required this.onSubmitIntake,
    required this.onCheckCompletion,
    required this.onFetchPortfolio,
  }) : super(_NoopApiClient());

  final Future<ExamSprintIntakeResult> Function() onSubmitIntake;
  final Future<SprintCompletionCheckResult> Function(String planId)
      onCheckCompletion;
  final Future<LearningPortfolioResult> Function({String? userId})
      onFetchPortfolio;

  @override
  Future<ExamSprintIntakeResult> submitIntake(
    ExamSprintIntakeRequest request,
  ) =>
      onSubmitIntake();

  @override
  Future<SprintCompletionCheckResult> checkSprintCompletion(String planId) =>
      onCheckCompletion(planId);

  @override
  Future<LearningPortfolioResult> fetchLearningPortfolio({
    String? userId,
    int page = 1,
    int pageSize = 20,
  }) =>
      onFetchPortfolio(userId: userId);
}

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
