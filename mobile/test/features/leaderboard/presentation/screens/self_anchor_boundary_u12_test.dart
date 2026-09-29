import 'dart:io';

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
import 'package:sparkle/l10n/app_localizations.dart';

import '../../../../shared/i18n_test_helper.dart';

/// V4-U12 自我锚边界钉（SCREEN_FAMILIES「小队/自我锚/光子/成就」家族）。
///
/// - N9 一致性（勘误面）：失败面走人话固定模板，异常细节（Object）零直出；
///   泄漏通道在 arb 源关闭（该键无 {error} 占位、调用面无实参）。
/// - D-COMM-1 家族语义反钉：排行榜域路由面 = 自我锚唯一产品面，
///   全站综合榜不复活（路由表词表钉）。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('正例：失败面人话固定模板 + 异常细节零直出 + 重试可达数据态', (tester) async {
    final repository =
        _FakeSelfAnchorRepository.error(Exception('boom-secret'));
    await _pumpSelfAnchor(tester, repository: repository);

    expect(find.text('自我锚加载失败。你的数据没有丢，稍后再试一次。'), findsOneWidget);
    expect(find.textContaining('boom-secret'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);

    // 重试可达数据态（失败不夺走出口）。
    repository
      ..failure = null
      ..view = _dataView();
    await tester.tap(find.byKey(const ValueKey('self-anchor-retry-button')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));

    expect(
      find.byKey(const ValueKey('self-anchor-summary-card')),
      findsOneWidget,
    );
  });

  test('反例钉（通道关闭）：arb 源该键零 {error} 占位，调用面零实参', () {
    // arb 源：zh/en 两份模板均不得再携带 {error} 占位。
    for (final file in ['lib/l10n/app_zh.arb', 'lib/l10n/app_en.arb']) {
      final source = File(file).readAsStringSync();
      final keyLine = source.split('\n').firstWhere(
            (line) => line.contains('"leaderboardSelfAnchorLoadFailed"'),
          );
      expect(
        keyLine.contains('{error}'),
        isFalse,
        reason: '$file 的 leaderboardSelfAnchorLoadFailed 不得再携带 {error} 占位',
      );
    }

    // 调用面：leaderboard 域内 l10n 调用零原始异常实参（N9 dim2 通道不再新增）。
    final screenSource = File(
      'lib/features/leaderboard/presentation/screens/self_anchor_screen.dart',
    ).readAsStringSync();
    expect(
      RegExp(r'leaderboardSelfAnchorLoadFailed\(\s*\w').hasMatch(screenSource),
      isFalse,
      reason: '自我锚失败面必须以无参 getter 消费人话模板',
    );
  });

  test('家族语义反钉：排行榜域唯一路由面 = 自我锚，全站综合榜不复活', () {
    final routes = LeaderboardRoutes.routes.whereType<GoRoute>().toList();
    expect(routes, hasLength(1));
    expect(routes.single.path, LeaderboardRoutes.selfAnchor);
    expect(routes.single.path, '/leaderboards/self-anchor');

    // 词表钉：leaderboard 域源码零全站榜面词（global 榜/photon 榜/综合榜）。
    // 注释里的 D-COMM-1 裁决记录行不计（先剥 // 注释再扫）。
    final offenders = <String>[];
    _walkDartFiles(Directory('lib/features/leaderboard')).forEach((file) {
      final code = file
          .readAsLinesSync()
          .map((line) => line.split('//').first)
          .join('\n');
      if (code.contains('photon_weekly') ||
          code.contains('global_board') ||
          code.contains('全站')) {
        offenders.add(file.path);
      }
    });
    expect(offenders, isEmpty);
  });
}

// ========== harness ==========

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

Future<void> _pumpSelfAnchor(
  WidgetTester tester, {
  required SelfAnchorRepository repository,
}) async {
  tester.view.physicalSize = const Size(390, 1200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final router = GoRouter(
    initialLocation: LeaderboardRoutes.selfAnchor,
    routes: LeaderboardRoutes.routes,
  );
  addTearDown(router.dispose);

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

  _FakeSelfAnchorRepository.error(this.failure)
      : view = null,
        super(_UnusedApiClient());

  SelfAnchorView? view;
  Exception? failure;

  @override
  Future<SelfAnchorView> getSelfAnchor() async {
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

Iterable<File> _walkDartFiles(Directory dir) sync* {
  if (!dir.existsSync()) {
    return;
  }
  for (final entity in dir.listSync(recursive: true)) {
    if (entity is File && entity.path.endsWith('.dart')) {
      yield entity;
    }
  }
}
