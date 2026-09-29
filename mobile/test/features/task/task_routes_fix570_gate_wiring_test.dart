import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mockito/mockito.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/screens/task_execution_deep_link_gate.dart';
import 'package:sparkle/features/task/task_routes.dart';
import 'package:sparkle/shared/entities/task_model.dart';

import '../../shared/i18n_test_helper.dart';

/// V3-FIX-570 ① · U14 一审 CH-1 路由接线测试钉。
///
/// U14 的深链闸测试（task_execution_deep_link_gate_test.dart）直泵闸
/// widget，full_route_coverage_test.dart 只查路径存在——两者都不经过
/// `TaskRoutes.routes` 的 pageBuilder。若集成合并把 task_routes.dart:94
/// 的 `TaskExecutionDeepLinkGate` 还原为直连执行屏（删 gate 调用），
/// 此前无任何测试变红。
///
/// 本钉从路由表真实装配 GoRouter 并落深链 `/tasks/:id/execute`，断言：
/// 1. 树中是**闸**（不是裸执行屏）——mutation（gate 调用删除）即红；
/// 2. 闸携带路径参数 `:id` 与查询参数 origin / intervention_id——
///    「路由忽略 :id」的 U14 前缺陷形态即红；
/// 3. 闸真实消费仓储确证路径（404 → 已删除面）：该面只有闸能产出，
///    接线断了它就不存在（第二重红面）。
class _MockScheduler extends Mock implements TaskNotificationScheduler {}

/// 手写仓储桩（与 task_execution_deep_link_gate_test.dart 同形制）：
/// 恒答 404 类异常——闸落「已删除面」，不泵真实执行屏（轻量装配面）。
class _NotFoundTaskRepository implements TaskRepository {
  int getTaskCalls = 0;
  final List<String> requestedIds = <String>[];

  @override
  Future<TaskModel> getTask(String id) {
    getTaskCalls++;
    requestedIds.add(id);
    throw Exception('Task not found');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      super.noSuchMethod(invocation);
}

/// 深链目标 id（UUID 形态：闸走服务端确证路径，而非本地-only 分支）。
const _stubbedTaskId = '88888888-8888-8888-8888-888888888888';

Future<ProviderContainer> _pumpExecutionDeepLink(
  WidgetTester tester, {
  required _NotFoundTaskRepository repo,
}) async {
  final container = ProviderContainer(
    overrides: [
      taskRepositoryProvider.overrideWithValue(repo),
      // TaskNotifier 构造依赖调度器；测试不触发通知插件，注入桩件。
      taskNotificationSchedulerProvider.overrideWithValue(_MockScheduler()),
    ],
  );
  addTearDown(container.dispose);

  final router = GoRouter(
    // TaskRoutes 全部挂 parentNavigatorKey: navigatorKey（全局根键），
    // 路由表脱离 app/routes.dart 独立装配时必须传同一根键。
    navigatorKey: navigatorKey,
    initialLocation:
        '/tasks/$_stubbedTaskId/execute?origin=push&intervention_id=int-42',
    routes: TaskRoutes.routes,
  );
  addTearDown(router.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: testMaterialApp(routerConfig: router),
    ),
  );
  // 过场页动画 + 闸 initState 的 postFrameCallback（resolveTarget）+
  // 仓储确证异步落面。
  await tester.pump(const Duration(milliseconds: 50));
  await tester.pump(const Duration(milliseconds: 50));
  await tester.pump(const Duration(milliseconds: 200));
  return container;
}

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();
  // 路由装配面含 SceneAudioScope → BgmService/环境床读偏好：mock 空偏好，
  // BGM 缺省关闭，装配零真实音频副作用（音频平台通道不被触碰）。
  SharedPreferences.setMockInitialValues(<String, Object>{});

  testWidgets(
      'FIX-570①接线钉：/tasks/:id/execute 路由产物经深链闸，'
      '闸消费 :id 与 origin/intervention_id（删 gate 调用必红）', (tester) async {
    final repo = _NotFoundTaskRepository();

    await _pumpExecutionDeepLink(tester, repo: repo);

    // 1) 树中是闸本身——接线若还原为直连执行屏，此处 findsNothing 即红。
    final gateFinder = find.byType(TaskExecutionDeepLinkGate);
    expect(gateFinder, findsOneWidget);

    // 2) 闸携带完整深链参数（:id + 查询参数）——「路由忽略 :id」即红。
    final gate = tester.widget<TaskExecutionDeepLinkGate>(gateFinder);
    expect(gate.taskId, _stubbedTaskId);
    expect(gate.origin, 'push');
    expect(gate.interventionId, 'int-42');
    // 失效深链出口走列表（TaskRoutes.home），由路由侧约定而非闸内私设。
    expect(gate.missingReplacementRoute, TaskRoutes.home);

    // 3) 闸真实解析目标：仓储被以 :id 调用，404 → 已删除面。
    //    该面只有闸能产出——接线断了它不存在（第二重红面）。
    expect(repo.getTaskCalls, 1);
    expect(repo.requestedIds.single, _stubbedTaskId);
    expect(
      find.byKey(const ValueKey('object-unavailable-title')),
      findsOneWidget,
    );
    expect(find.text('内容已删除或不存在'), findsOneWidget);
  });
}
