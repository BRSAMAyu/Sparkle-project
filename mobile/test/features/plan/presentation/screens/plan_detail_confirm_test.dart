import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/plan/data/models/plan_confirm_result.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/models/plan_phase_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_detail_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  group('PlanDetailScreen plan confirmation (CP-01)', () {
    testWidgets('pending sprint plan renders the confirm action',
        (tester) async {
      final repository = _ConfirmFakePlanRepository(plan: _sprintPlan());

      await _pumpPlanDetail(tester, repository);

      expect(find.byKey(const ValueKey('plan-confirm-button')), findsOneWidget);
      expect(find.text('确认这份计划'), findsOneWidget);
      expect(find.byKey(const ValueKey('plan-confirmed-badge')), findsNothing);
      expect(confirmCalls, isEmpty);

      await tester.pump(const Duration(seconds: 35));
    });

    testWidgets('growth plan does not render the confirm action',
        (tester) async {
      await _pumpPlanDetail(
        tester,
        _ConfirmFakePlanRepository(plan: _sprintPlan(type: PlanType.growth)),
      );

      expect(find.byKey(const ValueKey('plan-confirm-button')), findsNothing);
      expect(find.byKey(const ValueKey('plan-confirmed-badge')), findsNothing);

      await tester.pump(const Duration(seconds: 35));
    });

    testWidgets('tapping confirm calls API and flips to confirmed state',
        (tester) async {
      final repository = _ConfirmFakePlanRepository(
        plan: _sprintPlan(),
        confirmHandler: (planId) async {
          confirmCalls.add(planId);
          return PlanConfirmResult(
            planId: 'plan-1',
            alreadyConfirmed: false,
            confirmedAt: DateTime.utc(2026, 9, 21, 10),
          );
        },
      );

      await _pumpPlanDetail(tester, repository);

      await tester.tap(find.byKey(const ValueKey('plan-confirm-button')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      expect(confirmCalls, ['plan-1']);
      expect(
        find.byKey(const ValueKey('plan-confirmed-badge')),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey('plan-confirm-button')), findsNothing);
      // 成功反馈（snackbar）与已确认徽章（含确认时间）各出现一次。
      expect(find.text('计划已确认生效'), findsOneWidget);
      expect(find.textContaining('已确认 · '), findsOneWidget);

      await tester.pump(const Duration(seconds: 35));
    });

    testWidgets('already_confirmed response is idempotent, not an error',
        (tester) async {
      final repository = _ConfirmFakePlanRepository(
        plan: _sprintPlan(),
        confirmHandler: (planId) async {
          confirmCalls.add(planId);
          return PlanConfirmResult(
            planId: 'plan-1',
            alreadyConfirmed: true,
            confirmedAt: DateTime.utc(2026, 9, 20, 8, 30),
          );
        },
      );

      await _pumpPlanDetail(tester, repository);

      await tester.tap(find.byKey(const ValueKey('plan-confirm-button')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      expect(confirmCalls, ['plan-1']);
      expect(
        find.byKey(const ValueKey('plan-confirmed-badge')),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey('plan-confirm-button')), findsNothing);
      // 幂等语义：已确认时间戳照常呈现，且不弹错误反馈。
      expect(find.textContaining('已确认 · '), findsOneWidget);
      expect(find.textContaining('确认失败'), findsNothing);

      await tester.pump(const Duration(seconds: 35));
    });

    testWidgets('404 failure keeps the confirm action and shows error surface',
        (tester) async {
      final repository = _ConfirmFakePlanRepository(
        plan: _sprintPlan(),
        confirmHandler: (planId) async {
          confirmCalls.add(planId);
          throw Exception('Plan $planId not found');
        },
      );

      await _pumpPlanDetail(tester, repository);

      await tester.tap(find.byKey(const ValueKey('plan-confirm-button')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      expect(confirmCalls, ['plan-1']);
      // 错误面：错误反馈出现，确认动作保留（可重试），不转已确认态。
      expect(find.textContaining('确认失败'), findsOneWidget);
      expect(find.byKey(const ValueKey('plan-confirm-button')), findsOneWidget);
      expect(find.byKey(const ValueKey('plan-confirmed-badge')), findsNothing);

      await tester.pump(const Duration(seconds: 35));
    });
  });
}

final List<String> confirmCalls = <String>[];

Future<void> _pumpPlanDetail(
  WidgetTester tester,
  PlanRepository repository,
) async {
  tester.view.physicalSize = const Size(390, 1200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final router = GoRouter(
    initialLocation: '/plans/plan-1',
    routes: [
      GoRoute(
        path: '/plans/:planId',
        builder: (context, state) =>
          const PlanDetailScreen(planId: 'plan-1'),
      ),
    ],
  );
  addTearDown(router.dispose);
  addTearDown(confirmCalls.clear);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        planRepositoryProvider.overrideWithValue(repository),
      ],
      child: MaterialApp.router(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        routerConfig: router,
        locale: const Locale('zh'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
      ),
    ),
  );

  await tester.pump();
  await tester.pump(const Duration(milliseconds: 1200));
}

PlanModel _sprintPlan({PlanType type = PlanType.sprint}) {
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
    type: type,
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

class _ConfirmFakePlanRepository extends PlanRepository {
  _ConfirmFakePlanRepository({
    required this.plan,
    this.confirmHandler,
  }) : super(_NoopApiClient());

  final PlanModel plan;
  final Future<PlanConfirmResult> Function(String planId)? confirmHandler;

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
  Future<PlanConfirmResult> confirmPlan(String id) async =>
      await confirmHandler?.call(id) ??
      PlanConfirmResult(planId: id, alreadyConfirmed: false);

  @override
  Future<PlanPhaseBundle> getPlanPhases(String planId) async =>
      PlanPhaseBundle(
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
