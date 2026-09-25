// M6-08 regression tests: the dashboard error auto-retry must back off
// exponentially and be capped, instead of hammering the three dashboard
// endpoints every 5 seconds forever while offline.
//
// Locks (retryBackoffSchedule injected with a fast table):
//   1. Consecutive auto-retry delays follow the escalated schedule
//      (pre-fix: a fixed 5s delay on every failure).
//   2. The delay is capped at the last schedule entry.
//   3. A successful fetch resets the budget: a fresh failure retries from
//      the first step again.
import 'dart:async';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

class _ScriptedDashboardRepository extends DashboardRepository {
  _ScriptedDashboardRepository() : super(_UnusedApiClient());

  final List<DateTime> statusCalls = <DateTime>[];
  bool failNext = true;

  @override
  Future<Map<String, dynamic>> getDashboardStatus() async {
    statusCalls.add(DateTime.now());
    if (failNext) {
      throw Exception('dashboard offline');
    }
    return <String, dynamic>{};
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

ProviderContainer _containerWith(
  _ScriptedDashboardRepository repo,
  List<Duration> schedule,
) {
  final container = ProviderContainer(
    overrides: [
      dashboardProvider.overrideWith(
        (ref) => DashboardNotifier(repo, retryBackoffSchedule: schedule),
      ),
    ],
  );
  return container;
}

Future<void> _waitFor(
  Duration max,
  bool Function() condition,
) async {
  final deadline = DateTime.now().add(max);
  while (!condition()) {
    if (DateTime.now().isAfter(deadline)) {
      fail('Condition not met within ${max.inMilliseconds}ms');
    }
    await Future<void>.delayed(const Duration(milliseconds: 20));
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('auto-retry delays escalate and cap at the last schedule entry',
      () async {
    final repo = _ScriptedDashboardRepository();
    const schedule = <Duration>[
      Duration(milliseconds: 80),
      Duration(milliseconds: 200),
      Duration(milliseconds: 500),
      Duration(milliseconds: 1200),
    ];
    final container = _containerWith(repo, schedule);
    addTearDown(container.dispose);

    // StateNotifierProvider is lazy: read the notifier once so the
    // notifier (and its constructor-triggered initial fetch) exists.
    container.read(dashboardProvider.notifier);

    // Initial fetch + 4 auto-retries: 0, 80, 280, 780, 1980 (~2s total).
    await _waitFor(
      const Duration(seconds: 6),
      () => repo.statusCalls.length >= 5,
    );
    await Future<void>.delayed(const Duration(milliseconds: 50));

    final deltas = <int>[
      for (var i = 1; i < repo.statusCalls.length; i++)
        repo.statusCalls[i].difference(repo.statusCalls[i - 1]).inMilliseconds,
    ];
    expect(
      deltas.length,
      greaterThanOrEqualTo(4),
      reason: 'Expected at least 4 retry deltas, got: $deltas',
    );

    bool inWindow(int value, int loMs, Duration expected) =>
        value >= expected.inMilliseconds - loMs &&
        value < expected.inMilliseconds + loMs + 400;
    // Escalation: each retry honours its own (larger) schedule entry.
    expect(inWindow(deltas[0], 30, schedule[0]), isTrue,
        reason: 'retry 1 delta ${deltas[0]}ms must match ~80ms',);
    expect(inWindow(deltas[1], 30, schedule[1]), isTrue,
        reason: 'retry 2 delta ${deltas[1]}ms must match ~200ms',);
    expect(inWindow(deltas[2], 30, schedule[2]), isTrue,
        reason: 'retry 3 delta ${deltas[2]}ms must match ~500ms',);
    expect(inWindow(deltas[3], 30, schedule[3]), isTrue,
        reason: 'retry 4 delta ${deltas[3]}ms must match ~1200ms',);
    // Cap: the 5th retry (if reached) stays at the last entry instead of
    // growing further; with only 4 entries it can never exceed it.
    for (final delta in deltas.skip(4)) {
      expect(
        inWindow(delta, 30, schedule.last),
        isTrue,
        reason: 'retry deltas must stay capped at ~1200ms, got $deltas',
      );
    }
  });

  test('a successful fetch resets the retry budget', () {
    // CI 慢机三度击穿墙钟阈（250/300/380 都不够）——按本文件注释预留的
    // 第三档判据改 fakeAsync 时钟注入：判别边界=250ms 假时钟（80 档必然
    // 已触发、400 档必然未触发），墙钟开销彻底退出判据。
    late _ScriptedDashboardRepository repo;
    late ProviderContainer container;

    FakeAsync().run((async) {
      const schedule = <Duration>[
        Duration(milliseconds: 80),
        Duration(milliseconds: 400),
        Duration(milliseconds: 400),
        Duration(milliseconds: 400),
      ];
      repo = _ScriptedDashboardRepository();
      // 构造 notifier（惰性 provider）→ 初始 fetch 失败 → 80ms 重试入队。
      container = _containerWith(repo, schedule)
        ..read(dashboardProvider.notifier);
      async.flushMicrotasks();
      expect(repo.statusCalls.length, 1, reason: '初始 fetch 应立即失败一次');

      // 250ms 假时钟内：80ms 档重试必须已发生（调度本身在工作）。
      async.elapse(const Duration(milliseconds: 250));
      expect(repo.statusCalls.length, 2,
          reason: '第一档 ~80ms 重试应在 250ms 假时钟内发生',);

      // 让升级档（400ms）触发并成功 → 预算重置。
      repo.failNext = false;
      async.elapse(const Duration(milliseconds: 450));
      expect(container.read(dashboardProvider).error, isNull,
          reason: '重试成功后 error 应清空',);
      expect(repo.statusCalls.length, 3);

      // 成功后的新失败：手动 fetch 立即失败 → 若预算已重置，重试回 80ms 档。
      repo.failNext = true;
      unawaited(container.read(dashboardProvider.notifier).fetchData());
      async.flushMicrotasks();
      final before = repo.statusCalls.length;
      expect(before, 4, reason: '手动 fetch 应立即记一次失败调用');

      // 判别核心：250ms 假时钟边界。预算已重置 → 80ms 档已触发（before+1）；
      // 未重置 → 还在等 400ms 档定时器（仍 before）。
      async.elapse(const Duration(milliseconds: 250));
      expect(repo.statusCalls.length, before + 1,
          reason: '成功后的新失败必须从第一档（~80ms）重试；'
              '250ms 内未重试说明预算未重置（仍在 400ms 升级档）',);

      container.dispose();
    });
  });
}
