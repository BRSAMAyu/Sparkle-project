import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/list_read_cache.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/features/calendar/data/datasources/calendar_remote_datasource.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/data/repositories/calendar_repository.dart';
import 'package:sparkle/features/calendar/presentation/screens/calendar_stats_screen.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';

import '../../../../shared/i18n_test_helper.dart';

/// V4-U08 · 证据采集：日历页改日程的键盘/按钮路径 + 统一行动语义。
///
/// 常规跑 `flutter test`：执行真实渲染断言（待办任务带「改期」按钮、
/// 终态任务不带、点击按钮进入标准日期选择器——拖拽之外的键盘/按钮
/// 替代入口），不写文件——套件全绿且无副作用。设 `U08_EVIDENCE_DIR=<绝对路径>` 时额外写出（路径见 v4/evidence/V4-U08/run_manifest.json）：
///   u08_calendar_reschedule_button.png
///   u08_calendar_reschedule_button_semantics.txt
///
/// 语义 dump 口径与 U05/F04 证据测试同款（元素树 RenderParagraph）。
String _dumpSemanticsFromElements(Element rootElement) {
  final buf = StringBuffer();
  void visit(Element el) {
    final ro = el.renderObject;
    if (ro is RenderParagraph) {
      final text = ro.text.toPlainText();
      if (text.trim().isNotEmpty) {
        final rect = ro.localToGlobal(Offset.zero) & ro.size;
        buf.writeln('- label="$text" rect=$rect');
      }
    }
    el.visitChildren(visit);
  }

  visit(rootElement);
  return buf.toString();
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 全链路静默假 API：证据容器整体禁真网——后台链路（如提醒配置同步）
/// 拿到空响应自行走异常/降级路径，不触发认证拦截器的安全存储/设备身份
/// 读取（headless 环境无插件实现）。
class _SilentApiClient implements ApiClient {
  Response<T> _empty<T>(String path) => Response<T>(
        requestOptions: RequestOptions(path: path),
      );

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 只读假任务仓储：一枚待办 + 一枚已完成，均落在「今天」（默认选中日），
/// 供日历 agenda 同屏对照「待办可改期 / 终态不可改期」。
class _EvidenceTaskRepository extends TaskRepository {
  _EvidenceTaskRepository() : super(_UnusedApiClient());

  final DateTime today = DateTime.now();

  TaskModel _task(String id, TaskStatus status) => TaskModel(
        id: id,
        userId: 'user-1',
        title: id == 'task-open' ? '未完成任务：算法错题重练' : '已完成任务：英语听力',
        type: TaskType.learning,
        tags: const [],
        estimatedMinutes: 30,
        difficulty: 2,
        energyCost: 1,
        priority: 1,
        status: status,
        createdAt: DateTime(2026),
        updatedAt: DateTime(2026),
        dueDate: DateTime(today.year, today.month, today.day),
      );

  @override
  Future<PaginatedResponse<TaskModel>> getTasks({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      PaginatedResponse<TaskModel>(
        items: [
          _task('task-open', TaskStatus.pending),
          _task('task-done', TaskStatus.completed),
        ],
        total: 2,
        page: 1,
        pageSize: pageSize,
      );

  @override
  Future<CacheAwareResult<PaginatedResponse<TaskModel>>> getTasksCached({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      CacheAwareResult(
        PaginatedResponse<TaskModel>(
          items: [
            _task('task-open', TaskStatus.pending),
            _task('task-done', TaskStatus.completed),
          ],
          total: 2,
          page: 1,
          pageSize: pageSize,
        ),
      );

  @override
  Future<CacheAwareResult<List<TaskModel>>> getTodayTasksCached() async =>
      const CacheAwareResult<List<TaskModel>>(<TaskModel>[]);

  @override
  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async =>
      <TaskModel>[];

  @override
  Future<List<TaskModel>> getTasksByDateRange(
    DateTime start,
    DateTime end,
  ) async => [
        _task('task-open', TaskStatus.pending),
        _task('task-done', TaskStatus.completed),
      ];

  /// 改期确认按钮的真实闭环会走到 updateTask——返回更新后的模型，
  /// 不打网络（基类实现会碰被禁用的 _UnusedApiClient）。
  TaskUpdate? lastUpdate;

  @override
  Future<TaskModel> updateTask(String id, TaskUpdate task) async {
    lastUpdate = task;
    return _task(id, TaskStatus.pending).copyWith(
      dueDate: task.dueDate ?? _task(id, TaskStatus.pending).dueDate,
    );
  }
}

class _EvidenceCalendarRepository extends CalendarRepository {
  _EvidenceCalendarRepository()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          CalendarRemoteDataSource(_UnusedApiClient()),
        );

  @override
  Future<List<CalendarEventModel>> getEvents({
    DateTime? startDate,
    DateTime? endDate,
    bool forceRemote = false,
  }) async =>
      const <CalendarEventModel>[];

  @override
  Future<CalendarEventModel?> syncTaskLinkedEvent(TaskModel task) async =>
      null;

  @override
  Future<void> removeTaskLinkedEvent(String taskId) async {}
}

class _StubScheduler extends TaskNotificationScheduler {
  _StubScheduler()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );

  @override
  Future<List<int>> scheduleTaskReminders(
    TaskModel task, {
    TaskReminderConfig? config,
  }) async =>
      const <int>[];

  @override
  Future<List<int>> rescheduleTaskReminders(
    TaskModel task, {
    TaskReminderConfig? config,
  }) async =>
      const <int>[];

  @override
  Future<void> cancelTaskReminders(String taskId) async {}
}

class _StaticDashboardNotifier extends DashboardNotifier {
  _StaticDashboardNotifier(Ref _) : super(_UnusedDashboardRepo());

  @override
  Future<void> fetchData() async {}
}

class _UnusedDashboardRepo extends DashboardRepository {
  _UnusedDashboardRepo() : super(_UnusedApiClient());
}

class _StaticPlanNotifier extends PlanNotifier {
  _StaticPlanNotifier(Ref ref) : super(_UnusedPlanRepo(), ref);

  @override
  Future<void> loadPlans({PlanType? type}) async {}

  @override
  Future<void> loadActivePlans() async {}
}

class _UnusedPlanRepo extends PlanRepository {
  _UnusedPlanRepo() : super(_UnusedApiClient());
}

Future<void> _capture(
  WidgetTester tester,
  String outPath,
  String semanticsPath,
) async {
  await tester.runAsync(() async {
    final outDir = io.Directory(io.File(outPath).parent.path);
    if (!outDir.existsSync()) {
      outDir.createSync(recursive: true);
    }
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(const ValueKey('u08-evidence-root')),
    );
    final image = await boundary.toImage(pixelRatio: 2.0);
    final bytes = await image.toByteData(format: ImageByteFormat.png);
    io.File(outPath).writeAsBytesSync(bytes!.buffer.asUint8List());
    final rootElement = tester.binding.rootElement;
    final buf = StringBuffer(
      rootElement == null
          ? '(无元素根)'
          : _dumpSemanticsFromElements(rootElement),
    );
    // 关键语义节点（图标按钮的语义名不在 RenderParagraph 文本里，
    // 用 SemanticsData 显式落盘：读屏名 + 几何 + 可用动作）。
    final rescheduleFinder = find.byKey(
      const ValueKey('calendar-reschedule-task-open'),
    );
    final node = rescheduleFinder.evaluate().isNotEmpty
        ? tester.getSemantics(rescheduleFinder.first)
        : null;
    final data = node?.getSemanticsData();
    buf
      ..writeln()
      ..writeln('## V4-U08 关键语义节点（SemanticsData）')
      ..writeln(
        data == null
            ? '- 节点=日历改期按钮 未找到（异常，需复核）'
            : '- 节点=日历改期按钮 label="${data.label}" rect=${data.rect} '
                'actions=${data.actions}',
      );
    io.File(semanticsPath).writeAsStringSync(buf.toString());
  });
}

void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(const {});
    // 证据采集 runAsync 打开真实事件循环——后台链路（认证拦截器读安全
    // 存储）会触发平台通道。打桩：读令牌返回空，请求方按离线路径自行
    // 降级，不影响日历 agenda 渲染面（与 U05 证据测试同款打桩）。
    TestWidgetsFlutterBinding.ensureInitialized().defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      (call) async => null,
    );
  });

  testWidgets('日历 agenda：待办带「改期」键盘/按钮入口，终态任务不带',
      (tester) async {
    tester.view.physicalSize = const Size(1170, 2100);
    tester.view.devicePixelRatio = 3.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final container = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWithValue(_SilentApiClient()),
        taskRepositoryProvider.overrideWithValue(_EvidenceTaskRepository()),
        calendarRepositoryProvider
            .overrideWithValue(_EvidenceCalendarRepository()),
        taskNotificationSchedulerProvider.overrideWithValue(_StubScheduler()),
        dashboardProvider.overrideWith(_StaticDashboardNotifier.new),
        planListProvider.overrideWith(_StaticPlanNotifier.new),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: RepaintBoundary(
          key: const ValueKey('u08-evidence-root'),
          child: MaterialApp(
            theme: AppThemes.lightTheme,
            locale: const Locale('zh'),
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: const Scaffold(body: CalendarStatsScreen()),
          ),
        ),
      ),
    );
    // 等初始月加载与入场动画落定。
    await tester.pump();
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(tester.takeException(), isNull);

    // 正面：待办任务的 agenda 卡带「改期」按钮（键盘/按钮路径存在，
    // 不再只有拖拽）。
    final rescheduleButton = find.byKey(
      const ValueKey('calendar-reschedule-task-open'),
    );
    expect(rescheduleButton, findsOneWidget);
    expect(
      find.bySemanticsLabel('改期'),
      findsWidgets,
      reason: '改期入口有显式语义名（读屏可达、键盘可操作）',
    );

    // 反面：终态任务（已完成）不提供改期。
    expect(
      find.byKey(const ValueKey('calendar-reschedule-task-done')),
      findsNothing,
      reason: '完成/放弃是终态，不开放改期动作',
    );

    final dir = io.Platform.environment['U08_EVIDENCE_DIR'];
    if (dir != null && dir.isNotEmpty) {
      // 先拍 agenda 待办卡的「改期」入口原始态（终态卡无按钮同屏可对照）；
      // 语义树仅 capture 期需要，测试结束前 dispose（flutter_test 校验）。
      final semantics = tester.ensureSemantics();
      await _capture(
        tester,
        '$dir/u08_calendar_reschedule_button.png',
        '$dir/u08_calendar_reschedule_button_semantics.txt',
      );
      semantics.dispose();
    }

    // 键盘/按钮路径可用性：点击按钮 → 标准 showDatePicker（可键盘导航
    // 的普通控件），证明存在拖拽之外的完整改期路径。
    await tester.tap(rescheduleButton);
    await tester.pumpAndSettle(const Duration(milliseconds: 300));
    expect(
      find.byType(CalendarDatePicker),
      findsOneWidget,
      reason: '改期按钮打开标准日期选择器（键盘/按钮路径闭环）',
    );
    // 确认 → 走同一写入链（provider 侧写入由 unified_action_semantics_test
    // 钉）；确认按钮文案随本地化（zh=确定）。
    final confirm = find.text('确定').evaluate().isNotEmpty
        ? find.text('确定')
        : find.text('OK');
    await tester.tap(confirm);
    await tester.pumpAndSettle(const Duration(milliseconds: 300));
    expect(tester.takeException(), isNull);
  });
}
