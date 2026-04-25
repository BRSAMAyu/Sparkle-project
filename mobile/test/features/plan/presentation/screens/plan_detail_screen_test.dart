import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/models/plan_phase_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_detail_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';

void main() {
  group('PlanDetailScreen common mistakes', () {
    testWidgets('renders three common mistake cards from guide json',
        (tester) async {
      final plan = _planWithMistakes([
        {'description': '把协议层功能互相套错。'},
        {'description': '只背结论，不会用题目条件触发判断。'},
        {'description': '看到熟悉关键词就跳步，漏掉边界条件。'},
      ]);

      await _pumpPlanDetail(tester, plan);

      expect(find.text('⚠️ 常见误区'), findsOneWidget);
      expect(_commonMistakeCards(), findsNWidgets(3));
      expect(find.text('把协议层功能互相套错。'), findsOneWidget);
      expect(find.text('只背结论，不会用题目条件触发判断。'), findsOneWidget);
      expect(find.text('看到熟悉关键词就跳步，漏掉边界条件。'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('does not render the common mistakes section for an empty list',
        (tester) async {
      final plan = _planWithMistakes(const []);

      await _pumpPlanDetail(tester, plan);

      expect(find.text('⚠️ 常见误区'), findsNothing);
      expect(_commonMistakeCards(), findsNothing);
      expect(tester.takeException(), isNull);
    });
  });
}

Finder _commonMistakeCards() => find.byWidgetPredicate((widget) {
      final key = widget.key;
      return key is ValueKey<String> &&
          key.value.startsWith('plan-common-mistake-card-');
    });

Future<void> _pumpPlanDetail(WidgetTester tester, PlanModel plan) async {
  tester.view.physicalSize = const Size(390, 1200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

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
}

PlanModel _planWithMistakes(List<dynamic> commonMistakesToWatch) {
  final now = DateTime.utc(2026, 4, 25);
  final task = TaskModel(
    id: 'task-1',
    userId: 'user-1',
    planId: 'plan-1',
    title: '拿下 TCP 确认号',
    type: TaskType.learning,
    tags: const ['day:1'],
    estimatedMinutes: 30,
    difficulty: 2,
    energyCost: 1,
    guideJson: {
      'why_now': '现在先处理它，是为了把今天的学习推进变成一个看得见的输出。',
      'common_mistakes_to_watch': commonMistakesToWatch,
    },
    status: TaskStatus.pending,
    priority: 1,
    orderIndex: 1000,
    createdAt: now,
    updatedAt: now,
  );

  return PlanModel(
    id: 'plan-1',
    userId: 'user-1',
    name: '计算机网络冲刺',
    type: PlanType.sprint,
    dailyAvailableMinutes: 45,
    masteryLevel: 0.4,
    progress: 0.2,
    isActive: true,
    createdAt: now,
    updatedAt: now,
    description: '今天先稳住高频节点。',
    subject: '计算机网络',
    tasks: [task],
    dayHighlights: PlanDayHighlights(
      day: 1,
      recommendation: '今天优先拿下 TCP 确认号。',
      tasks: [task],
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
  T read<T>(ProviderListenable<T> provider) {
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported read for $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
