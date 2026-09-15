import 'package:flutter/material.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/active_bottleneck_alert.dart';
import 'package:sparkle/features/home/presentation/widgets/daily_context_line.dart';
import 'package:sparkle/features/home/presentation/widgets/next_action_prompt.dart';
import 'package:sparkle/features/home/presentation/widgets/today_growth_status_card.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await ThemeManager().reset();
  });

  testWidgets('TodayGrowthStatusCard shows skeleton without data', (
    tester,
  ) async {
    await _pumpWithTheme(
      tester,
      const TodayGrowthStatusCard(isLoading: true),
    );

    expect(
      find.byKey(const ValueKey('today-growth-status-skeleton')),
      findsOneWidget,
    );
  });

  testWidgets('DailyContextLine renders the morning context sentence', (
    tester,
  ) async {
    await _pumpWithTheme(
      tester,
      const DailyContextLine(
        text: '考前 3 天，今天主攻热力学，你昨天打下了一半基础。',
      ),
    );

    expect(find.textContaining('考前 3 天'), findsOneWidget);
    expect(find.textContaining('热力学'), findsOneWidget);
  });

  testWidgets('DailyContextLine has a non-empty fallback', (
    tester,
  ) async {
    await _pumpWithTheme(
      tester,
      const DailyContextLine(),
    );

    expect(find.textContaining('早上好'), findsOneWidget);
    expect(find.textContaining('一小步'), findsOneWidget);
  });

  testWidgets('TodayGrowthStatusCard uses success tone when all done', (
    tester,
  ) async {
    await _pumpWithTheme(
      tester,
      TodayGrowthStatusCard(
        state: _growthState(tasksTotal: 3, tasksCompleted: 3),
      ),
    );

    final progress = tester.widget<CircularProgressIndicator>(
      find.byKey(const ValueKey('today-growth-progress')),
    );
    final valueColor = progress.valueColor as AlwaysStoppedAnimation<Color>;

    expect(progress.value, 1);
    expect(valueColor.value, DS.success);
    expect(find.textContaining('今天收束得很漂亮'), findsOneWidget);
  });

  testWidgets('ActiveBottleneckAlert does not render when empty', (
    tester,
  ) async {
    await _pumpWithTheme(
      tester,
      const ActiveBottleneckAlert(),
    );

    expect(
      find.byKey(const ValueKey('active-bottleneck-alert')),
      findsNothing,
    );
  });

  testWidgets('ActiveBottleneckAlert uses non-judgmental language', (
    tester,
  ) async {
    await _pumpWithTheme(
      tester,
      const ActiveBottleneckAlert(
        bottleneck: HomeBottleneck(
          id: 'b1',
          topic: '热力学过程',
          severity: 'high',
        ),
      ),
    );

    expect(find.textContaining('不是你的问题'), findsOneWidget);
    expect(find.textContaining('路径需要调整'), findsOneWidget);
    expect(find.textContaining('失败'), findsNothing);
  });

  testWidgets('NextActionPrompt start button navigates to task', (
    tester,
  ) async {
    final routed = <String>[];
    const task = HomeGrowthTask(
      id: 'task-1',
      title: '整理错题里的热力学过程',
      priority: 5,
      isCompleted: false,
    );
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => Scaffold(
            body: NextActionPrompt(
              task: task,
              onStart: (task) => context.push('/tasks/${task.id}'),
            ),
          ),
        ),
        GoRoute(
          path: '/tasks/:id',
          builder: (context, state) {
            final id = state.pathParameters['id']!;
            routed.add('/tasks/$id');
            return Scaffold(body: Text('task:$id'));
          },
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      MaterialApp.router(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        routerConfig: router,
        locale: const Locale('zh'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
            ),
    );

    await tester.tap(find.text('开始'));
    await tester.pumpAndSettle();

    expect(find.text('task:task-1'), findsOneWidget);
    expect(routed, ['/tasks/task-1']);
  });
}

Future<void> _pumpWithTheme(
  WidgetTester tester,
  Widget child,
) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: AppThemes.lightTheme,
      darkTheme: AppThemes.darkTheme,
      home: Scaffold(body: child),
    ),
  );
  await tester.pump();
}

HomeGrowthState _growthState({
  required int tasksTotal,
  required int tasksCompleted,
}) =>
    HomeGrowthState(
      activePlan: const HomeActivePlanStatus(
        id: 'plan-1',
        name: '物理基础强化',
        healthScore: 0.82,
        currentPhase: '基础强化',
      ),
      planHealth: 0.82,
      tasksTotal: tasksTotal,
      tasksCompleted: tasksCompleted,
      streak: 7,
      nextAction: const HomeGrowthTask(
        id: 'task-1',
        title: '完成热力学过程练习',
        priority: 5,
        isCompleted: false,
      ),
      currentPhase: '基础强化',
    );
