// D-04 · statistics truth test suite (red → green).
//
// RED STATE (base SHA e56be400): this suite CANNOT pass against the unfixed
// repositories — `AgentStatsRepository` / `FocusStatsRepository` /
// `CapsuleStatsRepository` fabricate statistics inside `fetchFromApi` without
// performing any network I/O, and `HybridStatisticsRepository._putInWarmCache`
// persists those fabricated values into the Isar warm cache for 24h marked
// `isFullySynced = true`. Consequences proven below:
//   (a) offline / HTTP 500 / timeout never surface an error — fabricated data
//       is returned instead (honesty tests);
//   (b) server-provided values never reach the caller (lineage tests);
//   (c) fabricated values already persisted in the warm cache keep being
//       served (pollution tests).
//
// On the base SHA this file fails to compile (the repositories accept no HTTP
// client, which is the defect's shape); after D-04 every test must pass.
// Mutation guard: restoring a mock fallback inside any `fetchFromApi` while
// keeping the constructor makes the honesty/lineage tests fail again.
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/statistics/data/models/cached_statistics_model.dart';
import 'package:sparkle/core/statistics/domain/entities/statistics_entity.dart';
import 'package:sparkle/core/statistics/domain/entities/statistics_period.dart';
import 'package:sparkle/core/statistics/domain/repositories/statistics_repository.dart';
import 'package:sparkle/core/statistics/presentation/providers/agent_statistics_provider.dart';
import 'package:sparkle/core/statistics/presentation/providers/capsule_statistics_provider.dart';
import 'package:sparkle/core/statistics/presentation/providers/focus_statistics_provider.dart';

import '../../shared/isar_test_helper.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Isar isar;
  late LocalDatabase localDb;
  late Directory tempDir;

  setUpAll(initializeIsarCoreForTesting);

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('statistics_truth_test');
    isar = await Isar.open(
      [CachedStatisticsModelSchema],
      directory: tempDir.path,
    );
    localDb = LocalDatabase();
    localDb.isar = isar;
  });

  tearDown(() async {
    try {
      await isar.close(deleteFromDisk: true);
    } catch (_) {}
    try {
      await tempDir.delete(recursive: true);
    } catch (_) {}
  });

  group('D-04 honesty: failures surface instead of fabricated data', () {
    test('agent stats: connection error is rethrown, never replaced by mock', () async {
      final repo = AgentStatsRepository(database: localDb, dio: _offlineDio());
      await expectLater(
        repo.getStatistics(StatisticsPeriod.today, forceRefresh: true),
        throwsA(isA<DioException>()),
      );
    });

    test('agent stats: HTTP 500 is rethrown', () async {
      final repo = AgentStatsRepository(
        database: localDb,
        dio: _statusDio(500, {'detail': 'boom'}),
      );
      await expectLater(
        repo.getStatistics(StatisticsPeriod.today, forceRefresh: true),
        throwsA(isA<DioException>()),
      );
    });

    test('agent stats: timeout is rethrown', () async {
      final repo = AgentStatsRepository(
        database: localDb,
        dio: _timeoutDio(),
      );
      await expectLater(
        repo.getStatistics(StatisticsPeriod.today, forceRefresh: true),
        throwsA(isA<DioException>()),
      );
    });

    test('focus stats: connection error is rethrown, never replaced by mock', () async {
      final repo = FocusStatsRepository(database: localDb, dio: _offlineDio());
      await expectLater(
        repo.getStatistics(StatisticsPeriod.week, forceRefresh: true),
        throwsA(isA<DioException>()),
      );
    });

    test('capsule stats: connection error is rethrown, never replaced by mock', () async {
      final repo = CapsuleStatsRepository(database: localDb, dio: _offlineDio());
      await expectLater(
        repo.getStatistics(StatisticsPeriod.month, forceRefresh: true),
        throwsA(isA<DioException>()),
      );
    });

    test('agent stats: server-side degraded aggregation surfaces as unavailable', () async {
      final repo = AgentStatsRepository(
        database: localDb,
        dio: _jsonDio({
          'success': true,
          'data': {
            'period_days': 1,
            'overall': {
              'total_executions': 0,
              'avg_duration_ms': 0,
              'total_sessions': 0,
            },
            'by_agent': <String>[],
            'recent_executions': <String>[],
            'degraded': true,
          },
        }),
      );
      await expectLater(
        repo.getStatistics(StatisticsPeriod.today, forceRefresh: true),
        throwsA(isA<StatisticsSourceUnavailableException>()),
      );
    });
  });

  group('D-04 lineage: server values flow to the caller', () {
    test('agent stats reflect server aggregation, not fixed constants', () async {
      final repo = AgentStatsRepository(
        database: localDb,
        dio: _jsonDio(_agentOverviewPayload()),
      );
      final data = await repo.getStatistics(
        StatisticsPeriod.today,
        forceRefresh: true,
      );

      expect(data.totalCalls, 7);
      expect(data.averageResponseTime, 2345.0);
      expect(data.successRate, closeTo(0.42, 0.0001));
      expect(data.callsByAgent['math'], 7);
      expect(data.isFromCache, isFalse);
    });

    test('agent stats request uses the real route with period window', () async {
      final requests = <RequestOptions>[];
      final repo = AgentStatsRepository(
        database: localDb,
        dio: _recordingDio(requests, _agentOverviewPayload()),
      );
      await repo.getStatistics(StatisticsPeriod.week, forceRefresh: true);

      expect(requests, hasLength(1));
      expect(requests.first.path, '/agent-stats/user/overview');
      expect(requests.first.queryParameters['days'], 7);
    });

    test('focus today maps /focus/stats plus heatmap-derived streak', () async {
      final repo = FocusStatsRepository(
        database: localDb,
        dio: _routeDio((path) {
          switch (path) {
            case '/focus/stats':
              return {'total_minutes': 95, 'pomodoro_count': 3, 'today_date': '2026-09-20'};
            case '/focus/stats/heatmap':
              return {
                // today + yesterday, gap before → streak must be 2
                DateTime.now().toIso8601String().split('T')[0]: 95,
                DateTime.now()
                    .subtract(const Duration(days: 1))
                    .toIso8601String()
                    .split('T')[0]: 40,
              };
          }
          throw StateError('unexpected path $path');
        }),
      );
      final data = await repo.getStatistics(
        StatisticsPeriod.today,
        forceRefresh: true,
      );

      expect(data.totalMinutes, 95);
      expect(data.totalSessions, 3);
      expect(data.averageSessionDuration, closeTo(95 / 3, 0.01));
      expect(data.currentStreak, 2);
      expect(data.dailyData, hasLength(1));
      expect(data.dailyData.first.minutes, 95);
      expect(data.dailyData.first.sessions, 3);
      expect(data.longestSession, isNull); // no real source for this field
    });

    test('focus week maps /focus/stats/weekly with server streak', () async {
      final repo = FocusStatsRepository(
        database: localDb,
        dio: _routeDio((path) {
          expect(path, '/focus/stats/weekly');
          return {
            'period_start': '2026-09-14T00:00:00',
            'period_end': '2026-09-21T00:00:00',
            'total_minutes': 600,
            'session_count': 20,
            'avg_duration': 30,
            'best_day': null,
            'daily_breakdown': {
              '2026-09-14': 100,
              '2026-09-15': 200,
              '2026-09-16': 0,
              '2026-09-17': 0,
              '2026-09-18': 0,
              '2026-09-19': 0,
              '2026-09-20': 300,
            },
            'focus_type_distribution': {'pomodoro': 600},
            'streak_days': 4,
            'longest_streak': 9,
          };
        }),
      );
      final data = await repo.getStatistics(
        StatisticsPeriod.week,
        forceRefresh: true,
      );

      expect(data.totalMinutes, 600);
      expect(data.totalSessions, 20);
      expect(data.averageSessionDuration, 30.0);
      expect(data.currentStreak, 4);
      expect(data.dailyData, hasLength(7));
      expect(data.dailyData.first.date.day, 14);
      expect(data.dailyData.first.sessions, isNull); // per-day session count has no real source
    });

    test('focus year derives totals from the heatmap and marks unknowns null', () async {
      final repo = FocusStatsRepository(
        database: localDb,
        dio: _routeDio((path) {
          expect(path, '/focus/stats/heatmap');
          return {
            '2026-09-18': 60,
            '2026-09-19': 30,
            '2026-09-20': 45,
          };
        }),
      );
      final data = await repo.getStatistics(
        StatisticsPeriod.year,
        forceRefresh: true,
      );

      expect(data.totalMinutes, 135);
      expect(data.totalSessions, isNull); // heatmap carries minutes only
      expect(data.averageSessionDuration, isNull);
      expect(data.currentStreak, 3); // three consecutive non-zero days ending today
      expect(data.dailyData, hasLength(3));
    });

    test('capsule stats map real /capsules/stats fields with a UTC period window', () async {
      final requests = <RequestOptions>[];
      final repo = CapsuleStatsRepository(
        database: localDb,
        dio: _recordingDio(requests, {
          'total_received': 30,
          'total_read': 12,
          'total_favorited': 5,
          'total_feedback_given': 2,
          'average_rating_given': 4.5,
        }),
      );
      final data = await repo.getStatistics(
        StatisticsPeriod.month,
        forceRefresh: true,
      );

      expect(data.totalReceived, 30);
      expect(data.totalRead, 12);
      expect(data.totalFavorited, 5);
      expect(data.totalFeedbackGiven, 2);
      expect(data.averageRating, 4.5);

      expect(requests, hasLength(1));
      expect(requests.first.path, '/capsules/stats');
      final start = requests.first.queryParameters['start'] as String;
      final end = requests.first.queryParameters['end'] as String;
      // Period bounds must be sent as UTC ISO timestamps.
      expect(DateTime.parse(start).isUtc, isTrue);
      expect(DateTime.parse(end).isUtc, isTrue);
    });
  });

  group('D-04 pollution: legacy mock warm-cache entries never revive', () {
    test('legacy unversioned entry is purged and not served', () async {
      await _seedLegacyWarmEntry(
        isar,
        StatisticsType.agent,
        StatisticsPeriod.today,
        _legacyAgentMockPayload(),
      );

      final repo = AgentStatsRepository(
        database: localDb,
        dio: _jsonDio(_agentOverviewPayload()),
      );
      // forceRefresh NOT set: an unfixed repository would serve the cached
      // mock (totalCalls == 38). The fixed repository purges the legacy
      // entry and falls through to the real API.
      final data = await repo.getStatistics(StatisticsPeriod.today);

      expect(data.totalCalls, 7);
      expect(data.totalCalls, isNot(38));

      final remaining = await isar.cachedStatisticsModels.where().findAll();
      expect(
        remaining.where((CachedStatisticsModel e) => e.metadata == null),
        isEmpty,
        reason: 'legacy mock entries must be physically deleted',
      );
    });

    test('legacy entry is not served as stale fallback on API failure', () async {
      await _seedLegacyWarmEntry(
        isar,
        StatisticsType.agent,
        StatisticsPeriod.today,
        _legacyAgentMockPayload(),
      );

      final repo = AgentStatsRepository(database: localDb, dio: _offlineDio());
      await expectLater(
        repo.getStatistics(StatisticsPeriod.today, forceRefresh: true),
        throwsA(isA<DioException>()),
        reason: 'stale fallback must never resurrect legacy mock data',
      );
    });
  });

  group('D-04 provenance: cache semantics are truthful', () {
    test('fresh API success writes versioned metadata and isFullySynced=true', () async {
      final repo = AgentStatsRepository(
        database: localDb,
        dio: _jsonDio(_agentOverviewPayload()),
      );
      await repo.getStatistics(StatisticsPeriod.today, forceRefresh: true);

      final entry = await isar.cachedStatisticsModels.where().findAll();
      expect(entry, hasLength(1));
      expect(entry.first.isFullySynced, isTrue);
      final metadata = entry.first.metadata;
      expect(metadata, isNotNull);
      final decoded = jsonDecode(metadata!) as Map<String, dynamic>;
      expect(
        decoded['schemaVersion'],
        CachedStatisticsModel.currentCacheSchemaVersion,
      );
      expect(decoded['source'], 'real-api');
    });

    test('warm-cache hit marks entity as from-cache with original timestamp', () async {
      final repo = AgentStatsRepository(
        database: localDb,
        dio: _jsonDio(_agentOverviewPayload()),
      );
      final fresh = await repo.getStatistics(
        StatisticsPeriod.today,
        forceRefresh: true,
      );

      // New instance → empty hot cache → warm (Isar) path.
      final repo2 = AgentStatsRepository(
        database: localDb,
        dio: _offlineDio(), // must not be reached
      );
      final cached = await repo2.getStatistics(StatisticsPeriod.today);

      expect(cached.isFromCache, isTrue);
      expect(cached.lastRefreshedAt, fresh.lastRefreshedAt);
      expect(cached.totalCalls, 7);
    });

    test('API failure after success returns last-known-real marked from cache', () async {
      final handler = _SwitchableHandler(_agentOverviewPayload());
      final repo = AgentStatsRepository(
        database: localDb,
        dio: _handlerDio(handler),
      );
      await repo.getStatistics(StatisticsPeriod.today, forceRefresh: true);

      handler.failNow = true;
      final data = await repo.getStatistics(
        StatisticsPeriod.today,
        forceRefresh: true,
      );

      expect(data.isFromCache, isTrue);
      expect(data.totalCalls, 7);
    });
  });

  group('D-04 notifier: failure keeps last-known-real visible', () {
    test('AgentStatistics.load preserves previous data on error', () async {
      final fake = _SwitchingAgentRepo(localDb);
      final container = ProviderContainer(
        overrides: [
          agentStatsRepositoryProvider.overrideWith((ref) => fake),
        ],
      );
      addTearDown(container.dispose);

      final sub = container.listen(agentStatisticsProvider, (_, __) {});
      addTearDown(sub.close);

      final notifier = container.read(agentStatisticsProvider.notifier);
      await notifier.load(StatisticsPeriod.today);
      var state = container.read(agentStatisticsProvider);
      expect(state.hasError, isFalse);
      expect(state.data?.totalCalls, 7);

      fake.failNow = true;
      await notifier.refresh();
      state = container.read(agentStatisticsProvider);

      expect(state.hasError, isTrue);
      expect(state.errorMessage, isNotNull);
      expect(state.data, isNotNull, reason: 'last-known-real must survive a failed reload');
      expect(state.data!.totalCalls, 7);
    });
  });
}

// ============================================
// Helpers
// ============================================

Map<String, dynamic> _agentOverviewPayload() => {
      'success': true,
      'data': {
        'period_days': 1,
        'overall': {
          'total_executions': 7,
          'avg_duration_ms': 2345,
          'total_sessions': 3,
        },
        'by_agent': [
          {
            'agent_type': 'math',
            'count': 7,
            'avg_duration_ms': 2000,
            'max_duration_ms': 4000,
            'success_rate': 42.0,
          },
        ],
        'recent_executions': <String>[],
      },
    };

/// Payload exactly as the old mock serializer would have written it into the
/// warm cache (fixed 0.95 success rate, 38 calls — the production pollution).
Map<String, dynamic> _legacyAgentMockPayload() => {
      'id': 'agent_today_1758336000000',
      'type': 'agent',
      'period': 'today',
      'lastRefreshedAt': DateTime.now().toIso8601String(),
      'isFromCache': false,
      'totalCalls': 38,
      'averageResponseTime': 1250.0,
      'totalTokens': 19000,
      'successRate': 0.95,
      'callsByAgent': {
        'tutor': 15,
        'coder': 10,
        'writer': 8,
        'analyzer': 5,
      },
    };

Future<void> _seedLegacyWarmEntry(
  Isar isar,
  StatisticsType type,
  StatisticsPeriod period,
  Map<String, dynamic> mockPayload,
) async {
  final entry = CachedStatisticsModel()
    ..cacheKey = CachedStatisticsModel.generateKey(type: type, period: period)
    ..type = type
    ..period = period
    ..periodStart = period.getStartTime()
    ..periodEnd = period.getEndTime()
    ..jsonData = utf8.encode(jsonEncode(mockPayload))
    ..createdAt = DateTime.now()
    ..lastAccessedAt = DateTime.now()
    ..ttlSeconds = 86400
    ..priority = CachePriority.normal
    ..isFullySynced = true // mock data was cached as "fully synced" — the defect
    // metadata deliberately left null: legacy entries carry no version marker.
    ..metadata = null;
  await isar.writeTxn(() async {
    await isar.cachedStatisticsModels.put(entry);
  });
}

Dio _baseDio(HttpClientAdapter adapter) => Dio(
      BaseOptions(
        baseUrl: 'https://sparkle.test/api/v1',
        connectTimeout: const Duration(seconds: 5),
        receiveTimeout: const Duration(seconds: 5),
      ),
    )..httpClientAdapter = adapter;

Dio _offlineDio() => _handlerDio(_OfflineHandler());

Dio _timeoutDio() => _handlerDio(_TimeoutHandler());

Dio _statusDio(int status, Map<String, dynamic> body) =>
    _handlerDio(_StaticHandler(status, body));

Dio _jsonDio(Map<String, dynamic> body) => _handlerDio(_StaticHandler(200, body));

Dio _recordingDio(List<RequestOptions> sink, Map<String, dynamic> body) =>
    _handlerDio(_RecordingHandler(sink, _StaticHandler(200, body)));

Dio _routeDio(Map<String, dynamic> Function(String path) router) =>
    _handlerDio(_RoutingHandler(router));

Dio _handlerDio(_StubHandler handler) => _baseDio(_StubAdapter(handler));

abstract class _StubHandler {
  Future<ResponseBody> handle(RequestOptions options);
}

class _OfflineHandler implements _StubHandler {
  @override
  Future<ResponseBody> handle(RequestOptions options) async {
    throw DioException.connectionError(
      requestOptions: options,
      reason: 'simulated offline (D-04 test)',
    );
  }
}

class _TimeoutHandler implements _StubHandler {
  @override
  Future<ResponseBody> handle(RequestOptions options) async {
    throw DioException.connectionTimeout(
      timeout: const Duration(seconds: 5),
      requestOptions: options,
      error: 'simulated timeout (D-04 test)',
    );
  }
}

class _StaticHandler implements _StubHandler {
  _StaticHandler(this.status, this.body);
  final int status;
  final Map<String, dynamic> body;

  @override
  Future<ResponseBody> handle(RequestOptions options) async => ResponseBody.fromString(
        jsonEncode(body),
        status,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      );
}

class _RecordingHandler implements _StubHandler {
  _RecordingHandler(this.sink, this.inner);
  final List<RequestOptions> sink;
  final _StubHandler inner;

  @override
  Future<ResponseBody> handle(RequestOptions options) {
    sink.add(options);
    return inner.handle(options);
  }
}

class _RoutingHandler implements _StubHandler {
  _RoutingHandler(this.router);
  final Map<String, dynamic> Function(String path) router;

  @override
  Future<ResponseBody> handle(RequestOptions options) async =>
      ResponseBody.fromString(
        jsonEncode(router(options.path)),
        200,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      );
}

class _SwitchableHandler implements _StubHandler {
  _SwitchableHandler(this.body);
  final Map<String, dynamic> body;
  bool failNow = false;

  @override
  Future<ResponseBody> handle(RequestOptions options) async {
    if (failNow) {
      throw DioException.connectionError(
        requestOptions: options,
        reason: 'switched offline (D-04 test)',
      );
    }
    return _StaticHandler(200, body).handle(options);
  }
}

class _StubAdapter implements HttpClientAdapter {
  _StubAdapter(this._handler);
  final _StubHandler _handler;
  bool _closed = false;

  @override
  void close({bool force = false}) => _closed = true;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (_closed) {
      throw StateError('adapter closed');
    }
    return _handler.handle(options);
  }
}

/// Agent stats repository whose transport switches from healthy to failing;
/// exercises the notifier's error path without any network.
class _SwitchingAgentRepo extends AgentStatsRepository {
  _SwitchingAgentRepo(LocalDatabase database)
      : super(database: database, dio: _handlerDio(_SwitchableHandler(_agentOverviewPayload())));

  bool failNow = false;

  @override
  Future<AgentStatisticsData> getStatistics(
    StatisticsPeriod period, {
    bool forceRefresh = false,
    int ttlSeconds = 300,
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    if (failNow) {
      throw DioException.connectionError(
        requestOptions: RequestOptions(path: '/agent-stats/user/overview'),
        reason: 'switched offline (D-04 test)',
      );
    }
    return fetchFromApi(period, customStart: customStart, customEnd: customEnd);
  }
}
