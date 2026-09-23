import 'package:dio/dio.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/api_timeouts.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/statistics/data/statistics_data.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';
import 'package:sparkle/core/statistics/presentation/providers/statistics_provider.dart';

part 'agent_statistics_provider.g.dart';

/// Agent statistics entity
///
/// Field semantics follow the backend `/agent-stats/user/overview`
/// aggregation over `agent_execution_stats` (B-02 lineage INV-04). Fields
/// with no real data source are `null` — never a fabricated constant.
class AgentStatisticsData extends StatisticsEntity {

  AgentStatisticsData({
    required this.id,
    required this.period,
    required this.lastRefreshedAt,
    required this.isFromCache,
    required this.totalCalls,
    required this.averageResponseTime,
    required this.successRate,
    required this.callsByAgent,
  });
  @override
  final String id;

  @override
  final StatisticsType type = StatisticsType.agent;

  @override
  final StatisticsPeriod period;

  @override
  final DateTime lastRefreshedAt;

  @override
  final bool isFromCache;

  /// Total agent executions in the period
  /// (server: `overall.total_executions`)
  final int totalCalls;

  /// Average execution duration in milliseconds
  /// (server: `overall.avg_duration_ms`)
  final double averageResponseTime;

  /// Share of successful executions (0-1), weighted by per-agent counts.
  /// Null when the server has no executions in the window (unknown).
  final double? successRate;

  /// Executions per agent type (server: `by_agent[].agent_type/count`)
  final Map<String, int> callsByAgent;

  @override
  double getPrimaryValue() => totalCalls.toDouble();

  @override
  double? calculateChange(StatisticsEntity? previous) {
    if (previous == null || previous is! AgentStatisticsData) {
      return null;
    }
    if (previous.totalCalls == 0) {
      return totalCalls > 0 ? 100.0 : 0.0;
    }
    return ((totalCalls - previous.totalCalls) / previous.totalCalls) * 100;
  }

  AgentStatisticsData copyWith({
    String? id,
    StatisticsPeriod? period,
    DateTime? lastRefreshedAt,
    bool? isFromCache,
    int? totalCalls,
    double? averageResponseTime,
    double? successRate,
    Map<String, int>? callsByAgent,
  }) => AgentStatisticsData(
    id: id ?? this.id,
    period: period ?? this.period,
    lastRefreshedAt: lastRefreshedAt ?? this.lastRefreshedAt,
    isFromCache: isFromCache ?? this.isFromCache,
    totalCalls: totalCalls ?? this.totalCalls,
    averageResponseTime: averageResponseTime ?? this.averageResponseTime,
    successRate: successRate ?? this.successRate,
    callsByAgent: callsByAgent ?? this.callsByAgent,
  );
}

/// Repository for agent statistics.
///
/// Data source: `GET /agent-stats/user/overview?days=<window>` — a real
/// aggregation over the `agent_execution_stats` table served by the FastAPI
/// engine behind the gateway. There is no client-side fallback: transport
/// failures propagate, and a server-reported degraded aggregation surfaces
/// as [StatisticsSourceUnavailableException] (D-04).
class AgentStatsRepository extends HybridStatisticsRepository<AgentStatisticsData> {
  AgentStatsRepository({required super.database, super.cacheConfig, Dio? dio})
      : dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: ApiEndpoints.baseUrl,
                // N37 单一事实源：core/network/api_timeouts.dart（数值守恒 10s/30s）。
                connectTimeout: ApiTimeouts.defaultConnectTimeout,
                receiveTimeout: ApiTimeouts.defaultReceiveTimeout,
              ),
            );

  /// HTTP client used for statistics fetches. Production wiring passes the
  /// shared authenticated client (`ApiClient.dio`); tests inject a stub.
  final Dio dio;

  @override
  StatisticsType get type => StatisticsType.agent;

  @override
  Future<AgentStatisticsData> fetchFromApi(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    final days = period.windowDays(customStart: customStart, customEnd: customEnd);
    final response = await dio.get<dynamic>(
      ApiEndpoints.agentStatsUserOverview,
      queryParameters: <String, dynamic>{'days': days},
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchAgentStats',
    );

    if (payload['degraded'] == true) {
      // The server could not aggregate (missing stats dependency). Report it
      // honestly instead of rendering zeros that look like real usage.
      throw const StatisticsSourceUnavailableException(
        'agent statistics source degraded on server',
      );
    }

    final overall = (payload['overall'] as Map).cast<String, dynamic>();
    final byAgent = (payload['by_agent'] as List? ?? <dynamic>[])
        .whereType<Map<dynamic, dynamic>>()
        .map((row) => row.cast<String, dynamic>())
        .toList();

    final now = DateTime.now();
    return AgentStatisticsData(
      id: 'agent_${period.name}_${now.millisecondsSinceEpoch}',
      period: period,
      lastRefreshedAt: now,
      isFromCache: false,
      totalCalls: (overall['total_executions'] as num?)?.toInt() ?? 0,
      averageResponseTime:
          (overall['avg_duration_ms'] as num?)?.toDouble() ?? 0.0,
      successRate: _weightedSuccessRate(byAgent),
      callsByAgent: {
        for (final row in byAgent)
          row['agent_type'] as String: (row['count'] as num?)?.toInt() ?? 0,
      },
    );
  }

  /// Aggregate per-agent success rates (0-100, by count) into an overall
  /// success share (0-1). Null when no executions exist in the window.
  static double? _weightedSuccessRate(List<Map<String, dynamic>> byAgent) {
    var totalCount = 0;
    var successCount = 0.0;
    for (final row in byAgent) {
      final count = (row['count'] as num?)?.toInt() ?? 0;
      if (count <= 0) continue;
      final ratePercent = (row['success_rate'] as num?)?.toDouble() ?? 0.0;
      totalCount += count;
      successCount += count * (ratePercent / 100.0);
    }
    if (totalCount == 0) return null;
    return successCount / totalCount;
  }

  @override
  AgentStatisticsData deserializeEntity(Map<String, dynamic> json) =>
      AgentStatisticsData(
        id: json['id'] as String,
        period: StatisticsPeriodExt.fromCode(json['period'] as String),
        lastRefreshedAt: DateTime.parse(json['lastRefreshedAt'] as String),
        isFromCache: json['isFromCache'] as bool,
        totalCalls: json['totalCalls'] as int,
        averageResponseTime: (json['averageResponseTime'] as num).toDouble(),
        successRate: (json['successRate'] as num?)?.toDouble(),
        callsByAgent: Map<String, int>.from(json['callsByAgent'] as Map),
      );

  @override
  Map<String, dynamic> serializeEntity(AgentStatisticsData entity) => {
      'id': entity.id,
      'type': entity.type.code,
      'period': entity.period.name,
      'lastRefreshedAt': entity.lastRefreshedAt.toIso8601String(),
      'isFromCache': entity.isFromCache,
      'totalCalls': entity.totalCalls,
      'averageResponseTime': entity.averageResponseTime,
      'successRate': entity.successRate,
      'callsByAgent': entity.callsByAgent,
    };

  @override
  AgentStatisticsData markFromCache(AgentStatisticsData entity) =>
      entity.isFromCache ? entity : entity.copyWith(isFromCache: true);
}

/// Provider for agent statistics repository
@riverpod
AgentStatsRepository agentStatsRepository(AgentStatsRepositoryRef ref) {
  final database = ref.watch(localDatabaseProvider);
  return AgentStatsRepository(
    database: database,
    // Shared authenticated transport (auth/retry/logging/pinning stack).
    dio: ref.watch(apiClientProvider).dio,
  );
}

/// Provider for agent statistics state
@riverpod
class AgentStatistics extends _$AgentStatistics {
  @override
  StatisticsState<AgentStatisticsData> build() => const StatisticsState.initial();

  Future<void> load(
    StatisticsPeriod period, {
    bool forceRefresh = false,
  }) async {
    // Keep the last-known-real snapshot across the reload so an offline
    // reload can display "data as of <lastRefreshedAt>" instead of blanking
    // the screen (D-04 honest failure semantics).
    final previous = state;
    state = StatisticsState<AgentStatisticsData>.loading(period: period);

    final repository = ref.read(agentStatsRepositoryProvider);
    try {
      final data = await repository.getStatistics(
        period,
        forceRefresh: forceRefresh,
      );
      state = state.withData(data, newPeriod: period);
    } catch (e) {
      state = previous.withError('Failed to load: $e');
    }
  }

  Future<void> refresh() async {
    final period = state.lastPeriod ?? StatisticsPeriod.today;
    await load(period, forceRefresh: true);
  }

  Future<void> clearCache() async {
    final repository = ref.read(agentStatsRepositoryProvider);
    await repository.clearCache();
    state = const StatisticsState.initial();
  }
}
