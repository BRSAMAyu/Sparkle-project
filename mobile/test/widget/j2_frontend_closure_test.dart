import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/features/calendar/data/datasources/calendar_remote_datasource.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/data/repositories/calendar_repository.dart';
import 'package:sparkle/features/calendar/presentation/providers/calendar_provider.dart';
import 'package:sparkle/features/calendar/presentation/screens/daily_detail_screen.dart';
import 'package:sparkle/features/focus/presentation/widgets/exit_confirmation_dialog.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/screens/task_list_screen.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  group('J2 frontend closure', () {
    testWidgets('task list filters completed and in-progress tasks stably',
        (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);
      final container = ProviderContainer();
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: testMaterialApp(
            theme: AppThemes.lightTheme,
            darkTheme: AppThemes.darkTheme,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: const TaskListScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('理工课复盘 - 用自己的话讲清楚积分换元'), findsOneWidget);

      container.read(taskFilterProvider.notifier).state =
          TaskFilterOptions.completed;
      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.text('理工总结 - 线性代数错题回看'), findsOneWidget);
      expect(find.text('理工课复盘 - 用自己的话讲清楚积分换元'), findsNothing);

      container.read(taskFilterProvider.notifier).state =
          TaskFilterOptions.inProgress;
      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.text('理工课复盘 - 用自己的话讲清楚积分换元'), findsOneWidget);
      expect(find.text('理工总结 - 线性代数错题回看'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('tool shell sheet stays bottom aligned with close affordance',
        (tester) async {
      SharedPreferences.setMockInitialValues({});

      await tester.pumpWidget(
        MaterialApp(
          theme: AppThemes.lightTheme,
          darkTheme: AppThemes.darkTheme,
          home: Scaffold(
            body: SizedBox.expand(
              child: ToolShell(
                surface: ToolSurface.sheet,
                icon: Icons.calculate_rounded,
                title: '计算器',
                subtitle: '用于快速计算与草稿推演',
                accentColor: DS.info,
                body: const SizedBox(
                  height: 600,
                  child: Column(
                    children: [
                      Text('sheet-body'),
                      SizedBox(height: 400),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      final align = tester.widget<Align>(
        find.byWidgetPredicate(
          (widget) =>
              widget is Align &&
              widget.alignment == Alignment.bottomCenter,
        ),
      );

      expect(align.alignment, Alignment.bottomCenter);
      expect(find.byIcon(Icons.close_rounded), findsOneWidget);
      expect(find.text('sheet-body'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('exit confirmation remains single-step and actionable',
        (tester) async {
      var confirmed = 0;
      var cancelled = 0;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppThemes.lightTheme,
          darkTheme: AppThemes.darkTheme,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: const Locale('zh'),
          home: Scaffold(
            body: ExitConfirmationDialog(
              elapsedMinutes: 18,
              onConfirmExit: () => confirmed++,
              onCancel: () => cancelled++,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.byType(TextButton), findsNothing);
      expect(find.textContaining('18'), findsOneWidget);

      await tester.tap(find.text('确定退出'));
      await tester.pumpAndSettle();

      expect(confirmed, 1);
      expect(cancelled, 0);
      expect(tester.takeException(), isNull);
    });

    testWidgets('daily detail routes task-linked events to existing task edit',
        (tester) async {
      final date = DateTime(2026, 3, 25, 9);

      await _pumpDailyDetailHarness(
        tester,
        date: date,
        events: [
          _event(
            id: 'task-event',
            title: '关联任务日程',
            start: date,
            end: date.add(const Duration(hours: 1)),
            taskId: 'task-1',
          ),
        ],
      );

      await tester.ensureVisible(find.text('关联任务日程'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('关联任务日程'));
      await tester.pumpAndSettle();

      expect(find.text('task-route:task-1'), findsOneWidget);
      expect(find.text('编辑日程'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('daily detail keeps normal events in event edit flow',
        (tester) async {
      final date = DateTime(2026, 3, 25, 9);

      await _pumpDailyDetailHarness(
        tester,
        date: date,
        events: [
          _event(
            id: 'manual-event',
            title: '普通日程',
            start: date,
            end: date.add(const Duration(hours: 2)),
          ),
        ],
      );

      await tester.ensureVisible(find.text('普通日程'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('普通日程'));
      await tester.pumpAndSettle();

      expect(find.text('编辑日程'), findsOneWidget);
      expect(find.text('标题'), findsOneWidget);
      expect(find.text('保存'), findsOneWidget);
      expect(find.textContaining('task-route:'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('daily detail active plan card routes to plan detail',
        (tester) async {
      final date = DateTime(2026, 3, 25, 9);

      await _pumpDailyDetailHarness(
        tester,
        date: date,
        events: const [],
        plans: [
          _plan(
            id: 'plan-1',
            name: '系统化复习计划',
            createdAt: date.subtract(const Duration(days: 2)),
            targetDate: date.add(const Duration(days: 7)),
          ),
        ],
      );

      await tester.tap(find.text('系统化复习计划'));
      await tester.pumpAndSettle();

      expect(find.text('plan-route:plan-1'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}

Future<void> _pumpDailyDetailHarness(
  WidgetTester tester, {
  required DateTime date,
  required List<CalendarEventModel> events,
  List<PlanModel>? plans,
}) async {
  DemoDataService.isDemoMode = true;
  addTearDown(() => DemoDataService.isDemoMode = false);

  final router = GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => DailyDetailScreen(date: date),
      ),
      GoRoute(
        path: '/tasks/new',
        builder: (context, state) => Scaffold(
          body: Center(
            child: Text('task-route:${state.uri.queryParameters['taskId']}'),
          ),
        ),
      ),
      GoRoute(
        path: '/plans/:id',
        builder: (context, state) => Scaffold(
          body: Center(
            child: Text('plan-route:${state.pathParameters['id']}'),
          ),
        ),
      ),
    ],
  );
  addTearDown(router.dispose);

  final task = _task(
    id: 'task-1',
    title: 'J2 任务样例',
    dueDate: date,
  );

  final container = ProviderContainer(
    overrides: [
      calendarProvider.overrideWith(
        (ref) => _StaticCalendarNotifier(events),
      ),
      taskListProvider.overrideWith(
        (ref) => _StaticTaskListNotifier([task]),
      ),
      planListProvider.overrideWith(
        (ref) => _StaticPlanListNotifier(plans ?? const []),
      ),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp.router(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        routerConfig: router,
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
      ),
    ),
  );

  await tester.pumpAndSettle();
}

CalendarEventModel _event({
  required String id,
  required String title,
  required DateTime start,
  required DateTime end,
  String? taskId,
}) =>
    CalendarEventModel(
      id: id,
      title: title,
      startTime: start,
      endTime: end,
      createdAt: start,
      updatedAt: start,
      taskId: taskId,
    );

TaskModel _task({
  required String id,
  required String title,
  required DateTime dueDate,
}) =>
    TaskModel(
      id: id,
      userId: 'user-1',
      title: title,
      type: TaskType.learning,
      tags: const ['j2'],
      estimatedMinutes: 30,
      difficulty: 2,
      energyCost: 2,
      status: TaskStatus.pending,
      priority: 2,
      dueDate: dueDate,
      createdAt: dueDate.subtract(const Duration(days: 1)),
      updatedAt: dueDate,
    );

PlanModel _plan({
  required String id,
  required String name,
  required DateTime createdAt,
  required DateTime targetDate,
}) =>
    PlanModel(
      id: id,
      userId: 'user-1',
      name: name,
      type: PlanType.growth,
      dailyAvailableMinutes: 45,
      masteryLevel: 0.36,
      progress: 0.42,
      isActive: true,
      createdAt: createdAt,
      updatedAt: createdAt,
      targetDate: targetDate,
    );

class _StaticCalendarNotifier extends CalendarNotifier {
  _StaticCalendarNotifier(List<CalendarEventModel> events)
      : super(_UnusedCalendarRepository()) {
    state = CalendarState(events: events);
  }

  @override
  Future<void> loadEvents() async {}

  @override
  Future<void> updateEvent(CalendarEventModel event) async {
    state = state.copyWith(
      events: [
        for (final current in state.events)
          if (current.id == event.id) event else current,
      ],
    );
  }
}

class _StaticTaskListNotifier extends TaskNotifier {
  _StaticTaskListNotifier(List<TaskModel> tasks)
      : super(
          _UnusedTaskRepository(),
          _UnusedTaskNotificationScheduler(),
          _UnusedRef(),
        ) {
    state = TaskListState(tasks: tasks, todayTasks: tasks);
  }

  @override
  Future<void> loadTasks({TaskFilter? filter}) async {}

  @override
  Future<void> loadTodayTasks() async {}

  @override
  Future<void> loadRecommendedTasks() async {}

  @override
  Future<void> refreshTasks() async {}
}

class _StaticPlanListNotifier extends PlanNotifier {
  _StaticPlanListNotifier(List<PlanModel> plans)
      : super(_UnusedPlanRepository(), _UnusedRef()) {
    state = PlanListState(
      plans: plans,
      activePlans: plans.where((plan) => plan.isActive).toList(),
    );
  }

  @override
  Future<void> loadPlans({PlanType? type}) async {}

  @override
  Future<void> loadActivePlans() async {}

  @override
  Future<void> refresh() async {}
}

class _UnusedCalendarRepository extends CalendarRepository {
  _UnusedCalendarRepository()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          CalendarRemoteDataSource(_UnusedApiClient()),
        );
}

class _UnusedTaskRepository extends TaskRepository {
  _UnusedTaskRepository() : super(_UnusedApiClient());
}

class _UnusedPlanRepository extends PlanRepository {
  _UnusedPlanRepository() : super(_UnusedApiClient());
}

class _UnusedTaskNotificationScheduler extends TaskNotificationScheduler {
  _UnusedTaskNotificationScheduler()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
