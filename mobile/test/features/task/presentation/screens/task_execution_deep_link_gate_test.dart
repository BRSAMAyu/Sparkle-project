import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/screens/task_execution_deep_link_gate.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import '../../../../shared/i18n_test_helper.dart';

/// V4-U14 · 任务深链闸（卡验收 3：「通知落真实对象，已删对象提示而非空白」）。
///
/// 一正一反：
/// - 正（快路径）：active 已是目标 id → 零仓储调用直进执行屏（应用内
///   既有路径零差量）；
/// - 正（服务端确证）：仓储 getTask 命中 → active 被设为目标任务，落
///   真实对象；
/// - 反（已删对象）：仓储 404 类确证 → 「已删除或不存在」面；残留的
///   active 旧任务**绝不**被渲染（不吞深链、不渲染错误任务、不空白）；
/// - 反（无法确认）：网络类异常 → 「暂时无法确认」可重试面（不凭空
///   宣布已删除），重试按钮回环可用。
class _MockScheduler extends Mock implements TaskNotificationScheduler {}

/// 手写仓储桩：getTask 按队列逐次应答（TaskModel=命中；Exception=抛出）。
/// 不用 mockito——非空 Future 返回值在 verify/再桩定场景下有 Null 子类型
/// 与「stub 响应内不可再 when」的形制坑（本卡实测），手写桩让调用计数
/// 与传参可精确断言。
class FakeTaskRepository implements TaskRepository {
  FakeTaskRepository(this._responses);

  /// 每次消费队首；只有一项时恒定应答（重试场景复用同一应答）。
  final List<Object> _responses;
  int getTaskCalls = 0;
  final List<String> requestedIds = <String>[];

  @override
  Future<TaskModel> getTask(String id) {
    getTaskCalls++;
    requestedIds.add(id);
    final response = _responses.length > 1
        ? _responses.removeAt(0)
        : _responses.first;
    if (response is TaskModel) {
      return Future<TaskModel>.value(response);
    }
    // 仅收 Exception（由闸分类 lexicon 后落对应面）；as 收窄同时满足
    // only_throw_errors。
    throw response as Exception;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      super.noSuchMethod(invocation);
}

/// 深链目标 id（闸传给仓储的 id 需与桩应答一致，可精确断言）。
const _stubbedTaskId = '88888888-8888-8888-8888-888888888888';

TaskModel _task(String id, String title) => TaskModel(
      id: id,
      userId: 'user-1',
      title: title,
      type: TaskType.learning,
      tags: const [],
      estimatedMinutes: 25,
      difficulty: 1,
      energyCost: 1,
      priority: 0,
      status: TaskStatus.pending,
      createdAt: DateTime.parse('2026-09-01'),
      updatedAt: DateTime.parse('2026-09-01'),
    );

Future<ProviderContainer> pumpGate(
  WidgetTester tester, {
  required String taskId,
  required FakeTaskRepository repo,
  Widget Function(String? origin, String? interventionId)? screenBuilder,
  TaskModel? activeTask,
}) async {
  final container = ProviderContainer(
    overrides: [
      taskRepositoryProvider.overrideWithValue(repo),
      // TaskNotifier（taskListProvider）构造时依赖调度器；测试不触发
      // 通知插件，注入桩件（列表自加载在桩仓储下空转）。
      taskNotificationSchedulerProvider.overrideWithValue(_MockScheduler()),
      if (activeTask != null)
        activeTaskProvider.overrideWith((ref) => activeTask),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: testMaterialApp(
        home: TaskExecutionDeepLinkGate(
          taskId: taskId,
          screenBuilder:
              screenBuilder ??
              (origin, interventionId) => const Text(
                'EXEC_SCREEN_STUB',
                key: ValueKey('exec-screen-stub'),
              ),
        ),
      ),
    ),
  );
  // initState 的 postFrameCallback 驱动 resolveTarget。
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 50));
  return container;
}

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('正·快路径：active 已是目标 id → 零仓储调用直进执行屏', (
    tester,
  ) async {
    final repo = FakeTaskRepository([Exception('unused: fast path')]);
    final active = _task('task-active', '当前任务');

    await pumpGate(
      tester,
      taskId: 'task-active',
      repo: repo,
      activeTask: active,
    );

    expect(find.byKey(const ValueKey('exec-screen-stub')), findsOneWidget);
    expect(find.text('当前任务'), findsNothing); // 执行屏由桩屏替代呈现
    // 快路径不得发起仓储调用。
    expect(repo.getTaskCalls, 0);
  });

  testWidgets('正·服务端确证命中：active 被设为目标任务（落真实对象）', (tester) async {
    final target = _task(_stubbedTaskId, '通知里的任务');
    final repo = FakeTaskRepository([target]);
    // 深链前 active 残留另一个任务（回归面：不得渲染错误任务）。
    final stale = _task('22222222-2222-2222-2222-222222222222', '旧任务');

    final container = await pumpGate(
      tester,
      taskId: _stubbedTaskId,
      repo: repo,
      activeTask: stale,
    );

    expect(find.byKey(const ValueKey('exec-screen-stub')), findsOneWidget);
    expect(
      container.read(activeTaskProvider)?.id,
      _stubbedTaskId,
    );
    expect(find.text('旧任务'), findsNothing);
  });

  testWidgets('反·已删对象：404 确证 → 已删除面；不渲染残留任务也不空白', (tester) async {
    final repo = FakeTaskRepository([Exception('Task not found')]);
    final stale = _task('22222222-2222-2222-2222-222222222222', '旧任务');

    await pumpGate(
      tester,
      taskId: _stubbedTaskId,
      repo: repo,
      activeTask: stale,
    );

    expect(
      find.byKey(const ValueKey('object-unavailable-title')),
      findsOneWidget,
    );
    expect(find.text('内容已删除或不存在'), findsOneWidget);
    // 不空白：面内有可理解的解释与出口。
    expect(
      find.byKey(const ValueKey('object-unavailable-body')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('object-unavailable-primary')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('object-unavailable-back-home')),
      findsOneWidget,
    );
    // 绝不渲染残留任务（不吞深链）。
    expect(find.text('旧任务'), findsNothing);
  });

  testWidgets('反·无法确认：网络类异常 → 可重试面（不凭空宣布已删除）', (tester) async {
    final repo = FakeTaskRepository([
      Exception('SocketException: no route'),
      Exception('Connection refused'),
    ]);
    final stale = _task('22222222-2222-2222-2222-222222222222', '旧任务');

    await pumpGate(
      tester,
      taskId: _stubbedTaskId,
      repo: repo,
      activeTask: stale,
    );

    expect(find.text('暂时无法确认'), findsOneWidget);
    expect(find.text('内容已删除或不存在'), findsNothing);
    expect(find.text('旧任务'), findsNothing);

    // 重试回环：队列第二个应答（仍失败）→ 回到可重试面（不假成功、不空白）。
    await tester.tap(find.text('重试'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('暂时无法确认'), findsOneWidget);
  });

  testWidgets('已删面出口：列表出口与回首页按钮存在且语义可读', (tester) async {
    final repo = FakeTaskRepository([Exception('Task not found')]);

    await pumpGate(
      tester,
      taskId: _stubbedTaskId,
      repo: repo,
    );

    expect(find.text('查看任务列表'), findsOneWidget);
    expect(find.text('回到首页'), findsOneWidget);
  });
}
