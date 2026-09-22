import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/leaderboard/data/models/self_anchor_model.dart';
import 'package:sparkle/features/leaderboard/data/repositories/self_anchor_repository.dart';
import 'package:sparkle/features/leaderboard/leaderboard_routes.dart';
import 'package:sparkle/features/leaderboard/presentation/providers/self_anchor_provider.dart';
import 'package:sparkle/features/leaderboard/presentation/screens/self_anchor_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('SelfAnchorScreen (D-COMM-1)', () {
    testWidgets('data state renders window summary and 7-day series honestly',
        (tester) async {
      await _pumpSelfAnchor(
        tester,
        repository: _FakeSelfAnchorRepository(_dataView()),
        initialLocation: LeaderboardRoutes.selfAnchor,
      );

      // 必达项①：窗口合计摘要（真源数字 + 掌握度增量）。
      expect(
        find.byKey(const ValueKey('self-anchor-summary-card')),
        findsOneWidget,
      );
      expect(find.text('15'), findsOneWidget);
      expect(find.text('冲刺任务'), findsOneWidget);
      expect(find.text('掌握度 +2.4'), findsOneWidget);

      // 必达项②：每日柱状序列（7 列，旧→新）。
      expect(
        find.byKey(const ValueKey('self-anchor-series-card')),
        findsOneWidget,
      );
      // 零值日如实不画数值标签（诚实零），非零日逐一可见。
      expect(find.text('0'), findsNothing);
      expect(find.text('2'), findsOneWidget);
      expect(find.text('3'), findsOneWidget);
      expect(find.text('4'), findsOneWidget);
      expect(find.text('5'), findsOneWidget);
      // 今日（窗口末日）日期列标签。
      expect(find.text('9/22'), findsOneWidget);
      // 无社交比较元素（D-COMM-1：只跟自己的历史比）。
      expect(find.text('排行榜'), findsNothing);
    });

    testWidgets('empty ledger data shows guide, never a fake chart',
        (tester) async {
      await _pumpSelfAnchor(
        tester,
        repository: _FakeSelfAnchorRepository(_emptyView()),
        initialLocation: LeaderboardRoutes.selfAnchor,
      );

      expect(
        find.byKey(const ValueKey('self-anchor-empty-state')),
        findsOneWidget,
      );
      expect(find.text('这几天还没有记录'), findsOneWidget);
      expect(find.text('去看我的冲刺'), findsOneWidget);
      // 诚实空态：不渲染摘要与假零柱状图。
      expect(
        find.byKey(const ValueKey('self-anchor-summary-card')),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('self-anchor-series-card')),
        findsNothing,
      );
    });

    testWidgets('repository failure surfaces honest error with retry',
        (tester) async {
      final repository = _FakeSelfAnchorRepository.error(Exception('boom'));

      await _pumpSelfAnchor(
        tester,
        repository: repository,
        initialLocation: LeaderboardRoutes.selfAnchor,
      );

      expect(find.textContaining('自我锚加载失败'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('self-anchor-summary-card')),
        findsNothing,
      );

      // 重试可达数据态。
      repository.failure = null;
      repository.view = _dataView();
      await tester.tap(find.byKey(const ValueKey('self-anchor-retry-button')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));

      expect(
        find.byKey(const ValueKey('self-anchor-summary-card')),
        findsOneWidget,
      );
    });

    testWidgets('route /leaderboards/self-anchor is registered and reachable',
        (tester) async {
      // router 生命周期由 _pumpSelfAnchor 统一回收，避免二次 dispose。
      final router = GoRouter(
        initialLocation: '/leaderboards/self-anchor',
        routes: LeaderboardRoutes.routes,
      );

      await _pumpSelfAnchor(
        tester,
        repository: _FakeSelfAnchorRepository(_dataView()),
        routerOverride: router,
      );

      expect(find.byType(SelfAnchorScreen), findsOneWidget);
      expect(
        find.byKey(const ValueKey('self-anchor-summary-card')),
        findsOneWidget,
      );
    });
  });
}

SelfAnchorView _dataView() {
  DateTime day(int d) => DateTime.utc(2026, 9, 16 + d);
  const counts = [2, 0, 3, 1, 0, 4, 5];
  return SelfAnchorView(
    windowStart: day(0),
    windowEnd: day(6),
    series: [
      for (var i = 0; i < counts.length; i++)
        SelfAnchorDayPoint(
          date: day(i),
          tasksCompleted: counts[i],
          masteryDelta: i * 0.4,
        ),
    ],
    totalTasksCompleted: 15,
    totalMasteryDelta: 2.4,
    hasAnyData: true,
  );
}

SelfAnchorView _emptyView() {
  final today = DateTime.utc(2026, 9, 22);
  return SelfAnchorView(
    windowStart: today.subtract(const Duration(days: 6)),
    windowEnd: today,
    series: [
      for (var i = 6; i >= 0; i--)
        SelfAnchorDayPoint(
          date: today.subtract(Duration(days: i)),
          tasksCompleted: 0,
          masteryDelta: 0,
        ),
    ],
    totalTasksCompleted: 0,
    totalMasteryDelta: 0,
    hasAnyData: false,
  );
}

Future<void> _pumpSelfAnchor(
  WidgetTester tester, {
  required SelfAnchorRepository repository,
  GoRouter? routerOverride,
  String? initialLocation,
}) async {
  tester.view.physicalSize = const Size(390, 1200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final router = routerOverride ??
      GoRouter(
        initialLocation: initialLocation ?? LeaderboardRoutes.selfAnchor,
        routes: LeaderboardRoutes.routes,
      );
  if (routerOverride == null) {
    addTearDown(router.dispose);
  }

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        selfAnchorRepositoryProvider.overrideWithValue(repository),
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
  await tester.pump(const Duration(milliseconds: 600));
}

class _FakeSelfAnchorRepository extends SelfAnchorRepository {
  _FakeSelfAnchorRepository(this.view) : super(_UnusedApiClient());

  _FakeSelfAnchorRepository.error(this.failure) : view = null, super(_UnusedApiClient());

  SelfAnchorView? view;
  Exception? failure;
  int callCount = 0;

  @override
  Future<SelfAnchorView> getSelfAnchor() async {
    callCount++;
    final currentFailure = failure;
    if (currentFailure != null) {
      throw currentFailure;
    }
    return view!;
  }
}

class _UnusedApiClient extends ApiClient {
  _UnusedApiClient() : super(_UnusedRef());
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
