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

  test('a successful fetch resets the retry budget', () async {
    final repo = _ScriptedDashboardRepository();
    const schedule = <Duration>[
      Duration(milliseconds: 80),
      Duration(milliseconds: 400),
      Duration(milliseconds: 400),
      Duration(milliseconds: 400),
    ];
    final container = _containerWith(repo, schedule);
    addTearDown(container.dispose);

    // Lazy provider: construct the notifier to start the initial fetch.
    container.read(dashboardProvider.notifier);

    // Failure #1 → auto-retry (~80ms) fails → let a retry succeed so the
    // budget resets.
    await _waitFor(
      const Duration(seconds: 4),
      () => repo.statusCalls.length >= 2,
    );
    repo.failNext = false;
    await _waitFor(
      const Duration(seconds: 4),
      () => container.read(dashboardProvider).error == null,
    );

    // Fresh failure after success must retry from the FIRST step (~80ms),
    // not the escalated second step (~400ms).
    repo.failNext = true;
    await container.read(dashboardProvider.notifier).fetchData();
    final before = repo.statusCalls.length;
    await _waitFor(
      const Duration(seconds: 4),
      () => repo.statusCalls.length >= before + 1,
    );

    final retryDelta = repo.statusCalls
        .last
        .difference(repo.statusCalls[repo.statusCalls.length - 2])
        .inMilliseconds;
    expect(
      retryDelta,
      lessThan(250),
      reason:
          'After a success the next failure must be retried from the first '
          'backoff step (~80ms); got ${retryDelta}ms (budget was not reset)',
    );
  });
}
