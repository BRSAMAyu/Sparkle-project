import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/graphite_surfaces.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/galaxy/data/models/node_history_model.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/node_detail_sheet.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/models/plan_phase_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_detail_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';

void main() {
  testWidgets('chain A opens chat with review node context', (tester) async {
    Map<String, String>? chatQuery;
    Map<String, dynamic>? chatExtra;

    final history = GalaxyNodeHistory(
      nodeId: 'cn.tcp_flow',
      nodeLabel: 'TCP 流量控制',
      mastery: 0.65,
      studyCount: 3,
      lastStudiedAt: DateTime.utc(2026, 4, 24),
    );

    final router = GoRouter(
      navigatorKey: navigatorKey,
      initialLocation: '/',
      routes: <RouteBase>[
        GoRoute(
          path: '/',
          builder: (context, state) => Scaffold(
            body: Center(
              child: ElevatedButton(
                onPressed: () {
                  showModalBottomSheet<void>(
                    context: context,
                    builder: (_) => NodeDetailSheet(
                      nodeId: 'cn.tcp_flow',
                      nodeLabel: 'TCP 流量控制',
                      initialHistory: history,
                    ),
                  );
                },
                child: const Text('open-sheet'),
              ),
            ),
          ),
        ),
        GoRoute(
          path: '/chat',
          builder: (context, state) {
            chatQuery = state.uri.queryParameters;
            final extra = state.extra;
            chatExtra = extra is Map<String, dynamic> ? extra : null;
            return Scaffold(
              body: Text(
                'chat:${state.uri.queryParameters['review_node']}|${state.uri.queryParameters['node_label']}',
              ),
            );
          },
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('open-sheet'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('开始复习'));
    await tester.pumpAndSettle();

    expect(find.text('chat:cn.tcp_flow|TCP 流量控制'), findsOneWidget);
    expect(chatQuery?['chat_mode'], 'study_plan');
    expect(chatExtra?['initial_context'], <String, dynamic>{
      'review_node': 'cn.tcp_flow',
      'node_label': 'TCP 流量控制',
    });
  });

  testWidgets(
      'chain B renders next-day repair card first with orange treatment',
      (tester) async {
    await _useTallSurface(tester);
    final plan = _planWithNextDayRepairTask();
    final router = GoRouter(
      initialLocation: '/plans/${plan.id}',
      routes: [
        GoRoute(
          path: '/plans/:planId',
          builder: (context, state) => PlanDetailScreen(planId: plan.id),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          planRepositoryProvider.overrideWithValue(_FakePlanRepository(plan)),
        ],
        child: MaterialApp.router(
          theme: AppThemes.lightTheme,
          darkTheme: AppThemes.darkTheme,
          routerConfig: router,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
        ),
      ),
    );
    await tester.pumpAndSettle();

    final repairCard = tester.widget<GraphiteCardSurface>(
      find.byKey(const ValueKey('plan-task-card-task-repair')),
    );
    final repairOffset = tester.getTopLeft(find.text('修复昨日错题：TCP 滑动窗口机制'));
    final dayTwoNormalOffset = tester.getTopLeft(find.text('Day 2 · 常规刷题'));

    expect(repairCard.backgroundColor, DS.warning.withValues(alpha: 0.08));
    expect(repairOffset.dy, lessThan(dayTwoNormalOffset.dy));
  });

  testWidgets('chain D galaxy node color deepens after mastery increases',
      (tester) async {
    final mastery = ValueNotifier<int>(20);
    addTearDown(mastery.dispose);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Column(
            children: [
              ValueListenableBuilder<int>(
                valueListenable: mastery,
                builder: (context, value, child) => ColoredBox(
                  key: const ValueKey('galaxy-node-color'),
                  color: galaxyMasteryNodeColor(
                    masteryScore: value,
                    isDarkMode: false,
                  ),
                  child: const SizedBox(width: 24, height: 24),
                ),
              ),
              ElevatedButton(
                onPressed: () => mastery.value += 25,
                child: const Text('complete-task'),
              ),
            ],
          ),
        ),
      ),
    );

    final initialNode = tester.widget<ColoredBox>(
      find.byKey(const ValueKey('galaxy-node-color')),
    );
    expect(initialNode.color, const Color(0xFF9AA3AD));

    await tester.tap(find.text('complete-task'));
    await tester.pump();

    final updatedNode = tester.widget<ColoredBox>(
      find.byKey(const ValueKey('galaxy-node-color')),
    );
    expect(updatedNode.color, const Color(0xFF4F9FE8));
  });
}

Future<void> _useTallSurface(WidgetTester tester) async {
  tester.view.physicalSize = const Size(900, 1500);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

PlanModel _planWithNextDayRepairTask() {
  final now = DateTime.utc(2026, 4, 25);
  final dayOneTask = TaskModel(
    id: 'task-day1',
    userId: 'user-1',
    planId: 'plan-1',
    title: 'Day 1 · 常规复盘',
    type: TaskType.learning,
    tags: const ['day:1'],
    estimatedMinutes: 25,
    difficulty: 2,
    energyCost: 1,
    guideJson: const {'task_kind': 'retrieval_drill'},
    status: TaskStatus.pending,
    priority: 1,
    orderIndex: 1000,
    createdAt: now,
    updatedAt: now,
  );
  final repairTask = TaskModel(
    id: 'task-repair',
    userId: 'user-1',
    planId: 'plan-1',
    title: '修复昨日错题：TCP 滑动窗口机制',
    type: TaskType.errorFix,
    tags: const ['day:2', 'targeted_repair'],
    estimatedMinutes: 15,
    difficulty: 2,
    energyCost: 1,
    guideJson: const {
      'task_kind': 'targeted_repair',
      'daily_spec': {'task_kind': 'targeted_repair'},
    },
    status: TaskStatus.pending,
    priority: 100,
    orderIndex: 2000,
    createdAt: now,
    updatedAt: now,
  );
  final dayTwoNormal = TaskModel(
    id: 'task-day2-normal',
    userId: 'user-1',
    planId: 'plan-1',
    title: 'Day 2 · 常规刷题',
    type: TaskType.learning,
    tags: const ['day:2'],
    estimatedMinutes: 25,
    difficulty: 2,
    energyCost: 1,
    guideJson: const {'task_kind': 'retrieval_drill'},
    status: TaskStatus.pending,
    priority: 2,
    orderIndex: 2001,
    createdAt: now,
    updatedAt: now,
  );

  return PlanModel(
    id: 'plan-1',
    userId: 'user-1',
    name: '计算机网络冲刺',
    type: PlanType.sprint,
    dailyAvailableMinutes: 60,
    masteryLevel: 0.4,
    progress: 0.2,
    isActive: true,
    createdAt: now,
    updatedAt: now,
    description: '次日优先修复薄弱点。',
    subject: '计算机网络',
    tasks: [dayOneTask, repairTask, dayTwoNormal],
    dayHighlights: PlanDayHighlights(
      day: 2,
      recommendation: '明天优先修复今天暴露的错因。',
      tasks: [repairTask, dayTwoNormal],
    ),
  );
}

class _FakePlanRepository extends PlanRepository {
  _FakePlanRepository(this.plan) : super(_NoopApiClient());

  final PlanModel plan;

  @override
  Future<List<PlanModel>> getPlans({PlanType? type, bool? isActive}) async {
    if (type != null && plan.type != type) return const [];
    if (isActive != null && plan.isActive != isActive) return const [];
    return [plan];
  }

  @override
  Future<List<PlanModel>> getActivePlans() async =>
      plan.isActive ? [plan] : const [];

  @override
  Future<PlanModel> getPlan(String id) async => plan;

  @override
  Future<PlanPhaseBundle> getPlanPhases(String planId) async => PlanPhaseBundle(
        planCardId: null,
        currentPhaseCardId: null,
        progressMode: 'legacy',
        weightedProgress: null,
        phases: const [],
      );
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) => InterceptorsWrapper() as T;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
