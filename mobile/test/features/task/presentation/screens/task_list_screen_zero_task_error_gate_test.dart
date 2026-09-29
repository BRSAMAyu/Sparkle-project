import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/list_read_cache.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/screens/task_list_screen.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';
import '../../../../shared/i18n_test_helper.dart';

/// FIX-587：零任务新用户任务列表页 = 显式空态引导，不是错误态。
///
/// 缺陷机制（Q01 双线实证的客户端定谳）：
/// - TaskNotifier 构造器并行跑 loadTodayTasks/loadRecommendedTasks/loadTasks，
///   三者共享同一个 error 位；任一兄弟 load（today/recommended）失败一次，
///   error 被置位后【粘滞】——loadTasks 自身成功也不清除（成功路径不写
///   error 位）。
/// - 屏幕全页错误门 `error != null && tasks.isEmpty` 无法区分「列表自身
///   失败」与「列表成功为空但兄弟失败」——零任务新用户被全页错误态阻断
///   创建路径（空 ≠ 错误）。
/// - 修复：列表域错误位分离（listError 只由 loadTasks 写/清），全页错误门
///   只认列表自身失败；兄弟失败降级为非阻断提示（SnackBar/横幅）。
///
/// 本文件三测均为真实 TaskNotifier（构造器并行 + _runWithErrorHandling 真
/// 跑），仅仓库/调度器/ref 打桩；Completer 控制完成次序以钉死两种时序。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets('T1 对照：三读全成功且空 = 空态引导，不是错误态', (tester) async {
    final repo = _ScriptedTaskRepository();
    // 缺省桩：三读全部立即成功且为空（网关 /tasks* 全 200 空载荷的客户端
    // 等价形；后端 /tasks 返回 {data: [], meta}，/today、/recommended 返回 []）。
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          taskListProvider.overrideWith(
            (ref) => TaskNotifier(repo, _NoopTaskNotificationScheduler(), _FakeRef()),
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const TaskListScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 显式空态引导（含新建任务入口），无全页错误。
    expect(find.text('今天还没有待办事项'), findsOneWidget);
    expect(find.text('创建第一项任务'), findsOneWidget);
    expect(find.byType(CustomErrorWidget), findsNothing);
    // 合法空列表不得置任何 error 位。
    expect(repo.attachedNotifier?.state.error, isNull);
    expect(repo.attachedNotifier?.state.listError, isNull);

    await _drainErrorSnackBar(tester);
  });

  testWidgets('T2 复现（败先序）：today 失败一次 + 列表成功为空 → 空态引导非全页错误', (
    tester,
  ) async {
    final repo = _ScriptedTaskRepository()
      // today 立即失败（服务类错误，走 categorizeUiError → server），
      // 列表与 recommended 立即成功为空。
      ..todayOutcome = _Outcome.fail('getTodayTasks 500');
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          taskListProvider.overrideWith(
            (ref) {
              final notifier = TaskNotifier(
                repo,
                _NoopTaskNotificationScheduler(),
                _FakeRef(),
              );
              repo.attachedNotifier = notifier;
              return notifier;
            },
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const TaskListScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 修复语义：列表自身成功 + 空 = 空态引导（创建入口可达），
    // 兄弟失败不升格为全页错误。
    expect(find.text('今天还没有待办事项'), findsOneWidget);
    expect(find.text('创建第一项任务'), findsOneWidget);
    expect(find.byType(CustomErrorWidget), findsNothing);
    // 兄弟失败信号保留在共享 error 位（非阻断提示仍可见），
    // 列表域 listError 保持干净——两语义已分离。
    expect(repo.attachedNotifier?.state.error, isNotNull);
    expect(repo.attachedNotifier?.state.tasks, isEmpty);
    expect(repo.attachedNotifier?.state.listError, isNull);
    // 非阻断提示：兄弟失败经 SnackBar 出人话 + 重试动作（非全页拦截）。
    expect(find.textContaining('服务器出现问题'), findsOneWidget);

    await _drainErrorSnackBar(tester);
  });

  testWidgets('T3 复现（败后序·粘滞竞态）：列表先成功后 today 失败 → 空态引导非全页错误', (
    tester,
  ) async {
    final listGate =
        Completer<CacheAwareResult<PaginatedResponse<TaskModel>>>();
    final todayGate = Completer<CacheAwareResult<List<TaskModel>>>();
    final repo = _ScriptedTaskRepository()
      ..listFuture = listGate.future
      ..todayFuture = todayGate.future;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          taskListProvider.overrideWith(
            (ref) {
              final notifier = TaskNotifier(
                repo,
                _NoopTaskNotificationScheduler(),
                _FakeRef(),
              );
              repo.attachedNotifier = notifier;
              return notifier;
            },
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const TaskListScreen(),
        ),
      ),
    );
    await tester.pump(); // 构造器三读发出，全部悬在 gate 上。

    // ① 列表先成功（空页）——修前此刻已渲染空态。
    listGate.complete(
      CacheAwareResult(
        PaginatedResponse<TaskModel>(
          items: const [],
          total: 0,
          page: 1,
          pageSize: 50,
        ),
      ),
    );
    await tester.pump();

    // ② today 后失败——共享 error 位置位且粘滞（loadTasks 成功不清）。
    todayGate.completeError(Exception('getTodayTasks 500'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 修前状态画像（缺陷核心）：error != null && tasks.isEmpty
    // → 旧门渲染全页错误态阻断创建路径；修复后 = 空态引导。
    expect(repo.attachedNotifier?.state.error, isNotNull);
    expect(repo.attachedNotifier?.state.tasks, isEmpty);
    expect(repo.attachedNotifier?.state.listError, isNull);
    expect(find.text('今天还没有待办事项'), findsOneWidget);
    expect(find.text('创建第一项任务'), findsOneWidget);
    expect(find.byType(CustomErrorWidget), findsNothing);
    // 非阻断提示：兄弟失败经 SnackBar 出人话 + 重试动作（非全页拦截）。
    expect(find.textContaining('服务器出现问题'), findsOneWidget);

    await _drainErrorSnackBar(tester);
  });
}

/// T2/T3 中兄弟失败会经屏幕监听器弹错误 SnackBar（4s 时长），
/// 测试结束前排干其计时器，避免 pending-timer 误报。
Future<void> _drainErrorSnackBar(WidgetTester tester) async {
  await tester.pump(const Duration(seconds: 5));
}

enum _OutcomeKind { successEmpty, fail }

class _Outcome {
  _Outcome.fail(this.message) : kind = _OutcomeKind.fail;
  const _Outcome.successEmpty()
      : kind = _OutcomeKind.successEmpty,
        message = null;
  final _OutcomeKind kind;
  final String? message;
}

/// 脚本化仓库：只桩 TaskNotifier 消费的三个读法（getTasksCached /
/// getTodayTasksCached / getRecommendedTasks），其余不触。
class _ScriptedTaskRepository extends TaskRepository {
  _ScriptedTaskRepository() : super(_NoopApiClient());

  /// 屏幕挂载后由 overrideWith 闭包回填，供断言读 state。
  TaskNotifier? attachedNotifier;

  Future<CacheAwareResult<PaginatedResponse<TaskModel>>>? listFuture;
  Future<CacheAwareResult<List<TaskModel>>>? todayFuture;
  _Outcome todayOutcome = const _Outcome.successEmpty();

  @override
  Future<CacheAwareResult<PaginatedResponse<TaskModel>>> getTasksCached({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async {
    final scripted = listFuture;
    if (scripted != null) return scripted;
    return CacheAwareResult(
      PaginatedResponse<TaskModel>(
        items: const [],
        total: 0,
        page: page,
        pageSize: pageSize,
      ),
    );
  }

  @override
  Future<CacheAwareResult<List<TaskModel>>> getTodayTasksCached() async {
    final scripted = todayFuture;
    if (scripted != null) return scripted;
    if (todayOutcome.kind == _OutcomeKind.fail) {
      throw Exception(todayOutcome.message);
    }
    return const CacheAwareResult([]);
  }

  @override
  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async =>
      const [];
}

class _NoopTaskNotificationScheduler extends TaskNotificationScheduler {
  _NoopTaskNotificationScheduler()
      : super(
          NotificationService(_FakeRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_FakeRef());
}

class _FakeRef implements Ref {
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
