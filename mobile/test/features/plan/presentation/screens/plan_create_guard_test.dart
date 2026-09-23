import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_create_screen.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/task.dart';

import '../../../../shared/i18n_test_helper.dart';

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

class _NoopTaskRepository extends TaskRepository {
  _NoopTaskRepository() : super(_NoopApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// TaskNotifier 建造器即拉取三类任务列表——guard 测试用空实现替身。
class _IdleTaskNotifier extends TaskNotifier {
  _IdleTaskNotifier()
      : super(
          _NoopTaskRepository(),
          TaskNotificationScheduler(
            NotificationService(_UnusedRef(), autoInitialize: false),
            TaskNotificationIdMapper(),
          ),
          _UnusedRef(),
        );

  @override
  Future<void> loadTodayTasks() async {}

  @override
  Future<void> loadRecommendedTasks() async {}

  @override
  Future<void> loadTasks({TaskFilter? filter}) async {}
}

/// N27（A-SPEC5 v1.5）脏态保护回归（plan_create 屏）：
/// Stepper 5 步中播种的种子任务不算用户劳动；用户在任意步输入后返回必确认。
/// 原返回键/第 0 步取消键 context.pop() 硬 pop 绕过守卫，已改 maybePop。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<void> pumpPlanCreate(WidgetTester tester) async {
    tester.view
      ..physicalSize = const Size(800, 2400)
      ..devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final router = GoRouter(
      initialLocation: '/start',
      routes: [
        GoRoute(
          path: '/start',
          builder: (_, __) => const Scaffold(body: Text('起点')),
        ),
        GoRoute(
          path: '/plans/new',
          builder: (_, __) => const PlanCreateScreen(),
        ),
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          taskListProvider.overrideWith((ref) => _IdleTaskNotifier()),
        ],
        child: testMaterialApp(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();
    unawaited(router.push('/plans/new'));
    await tester.pumpAndSettle();
  }

  testWidgets('未做修改返回（含播种默认值）不弹确认，直接放行', (tester) async {
    await pumpPlanCreate(tester);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    expect(find.byType(PlanCreateScreen), findsNothing,
        reason: '未修改时返回直接放行（基线比对，播种内容不算脏）',);
    expect(find.text('起点'), findsOneWidget);
    expect(find.text('放弃更改？'), findsNothing);
  });

  testWidgets('输入计划名后返回必确认，「继续编辑」留下、「放弃更改」放行', (tester) async {
    await pumpPlanCreate(tester);

    await tester.enterText(find.byType(TextFormField).first, '高数冲刺计划');
    await tester.pump();

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    expect(find.text('放弃更改？'), findsOneWidget,
        reason: '半填计划返回必须确认（输入是劳动）',);

    await tester.tap(find.text('继续编辑'));
    await tester.pumpAndSettle();
    expect(find.byType(PlanCreateScreen), findsOneWidget);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    await tester.tap(find.text('放弃更改'));
    await tester.pumpAndSettle();

    expect(find.byType(PlanCreateScreen), findsNothing);
    expect(find.text('起点'), findsOneWidget);
  });
}
