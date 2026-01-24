import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/statistics/data/statistics_data.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';
import 'package:sparkle/core/statistics/presentation/providers/statistics_provider.dart';

part 'agent_statistics_provider.g.dart';

/// Agent statistics entity
class AgentStatisticsData extends StatisticsEntity {
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

  /// Total agent calls in the period
  final int totalCalls;

  /// Average response time in milliseconds
  final double averageResponseTime;

  /// Total tokens consumed
  final int totalTokens;

  /// Success rate (0-1)
  final double successRate;

  /// Breakdown by agent type
  final Map<String, int> callsByAgent;

  @override
  double getPrimaryValue() => totalCalls.toDouble();

  AgentStatisticsData({
    required this.id,
    required this.period,
    required this.lastRefreshedAt,
    required this.isFromCache,
    required this.totalCalls,
    required this.averageResponseTime,
    required this.totalTokens,
    required this.successRate,
    required this.callsByAgent,
  });

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
    int? totalTokens,
    double? successRate,
    Map<String, int>? callsByAgent,
  }) {
    return AgentStatisticsData(
      id: id ?? this.id,
      period: period ?? this.period,
      lastRefreshedAt: lastRefreshedAt ?? this.lastRefreshedAt,
      isFromCache: isFromCache ?? this.isFromCache,
      totalCalls: totalCalls ?? this.totalCalls,
      averageResponseTime: averageResponseTime ?? this.averageResponseTime,
      totalTokens: totalTokens ?? this.totalTokens,
      successRate: successRate ?? this.successRate,
      callsByAgent: callsByAgent ?? this.callsByAgent,
    );
  }
}

/// Repository for agent statistics
class AgentStatsRepository extends HybridStatisticsRepository<AgentStatisticsData> {
  AgentStatsRepository({required super.database, super.cacheConfig});

  @override
  StatisticsType get type => StatisticsType.agent;

  @override
  Future<AgentStatisticsData> fetchFromApi(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    final now = DateTime.now();
    final mockData = AgentStatisticsData(
      id: 'agent_${period.name}_${now.millisecondsSinceEpoch}',
      period: period,
      lastRefreshedAt: now,
      isFromCache: false,
      totalCalls: _generateMockCalls(period),
      averageResponseTime: 1250.0,
      totalTokens: _generateMockTokens(period),
      successRate: 0.95,
      callsByAgent: const {
        'tutor': 15,
        'coder': 10,
        'writer': 8,
        'analyzer': 5,
      },
    );
    return mockData;
  }

  @override
  AgentStatisticsData deserializeEntity(Map<String, dynamic> json) {
    return AgentStatisticsData(
      id: json['id'] as String,
      period: StatisticsPeriodExt.fromCode(json['period'] as String),
      lastRefreshedAt: DateTime.parse(json['lastRefreshedAt'] as String),
      isFromCache: json['isFromCache'] as bool,
      totalCalls: json['totalCalls'] as int,
      averageResponseTime: json['averageResponseTime'] as double,
      totalTokens: json['totalTokens'] as int,
      successRate: json['successRate'] as double,
      callsByAgent: Map<String, int>.from(json['callsByAgent'] as Map),
    );
  }

  @override
  Map<String, dynamic> serializeEntity(AgentStatisticsData entity) {
    return {
      'id': entity.id,
      'type': entity.type.code,
      'period': entity.period.name,
      'lastRefreshedAt': entity.lastRefreshedAt.toIso8601String(),
      'isFromCache': entity.isFromCache,
      'totalCalls': entity.totalCalls,
      'averageResponseTime': entity.averageResponseTime,
      'totalTokens': entity.totalTokens,
      'successRate': entity.successRate,
      'callsByAgent': entity.callsByAgent,
    };
  }

  int _generateMockCalls(StatisticsPeriod period) {
    switch (period) {
      case StatisticsPeriod.today:
        return 38;
      case StatisticsPeriod.week:
        return 180;
      case StatisticsPeriod.month:
        return 720;
      case StatisticsPeriod.year:
        return 8640;
      case StatisticsPeriod.custom:
        return 100;
    }
  }

  int _generateMockTokens(StatisticsPeriod period) {
    return _generateMockCalls(period) * 500;
  }
}

/// Provider for agent statistics repository
@riverpod
AgentStatsRepository agentStatsRepository(AgentStatsRepositoryRef ref) {
  final database = ref.watch(localDatabaseProvider);
  return AgentStatsRepository(database: database);
}

/// Provider for agent statistics state
@riverpod
class AgentStatistics extends _$AgentStatistics {
  @override
  StatisticsState<AgentStatisticsData> build() {
    return const StatisticsState.initial();
  }

  Future<void> load(
    StatisticsPeriod period, {
    bool forceRefresh = false,
  }) async {
    state = StatisticsState<AgentStatisticsData>.loading(period: period);

    final repository = ref.read(agentStatsRepositoryProvider);
    try {
      final data = await repository.getStatistics(
        period,
        forceRefresh: forceRefresh,
      );
      state = state.withData(data, newPeriod: period);
    } catch (e) {
      state = state.withError('加载失败: $e');
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
