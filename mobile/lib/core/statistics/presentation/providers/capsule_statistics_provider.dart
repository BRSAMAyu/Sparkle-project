import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/statistics/data/statistics_data.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';
import 'package:sparkle/core/statistics/presentation/providers/statistics_provider.dart';

part 'capsule_statistics_provider.g.dart';

/// Capsule statistics entity
class CapsuleStatisticsData extends StatisticsEntity {
  @override
  final String id;

  @override
  final StatisticsType type = StatisticsType.capsule;

  @override
  final StatisticsPeriod period;

  @override
  final DateTime lastRefreshedAt;

  @override
  final bool isFromCache;

  /// Total capsules opened
  final int totalOpened;

  /// Total capsules collected
  final int totalCollected;

  /// Capsules shared
  final int totalShared;

  /// Average engagement score
  final double averageEngagement;

  /// Breakdown by capsule category
  final Map<String, int> byCategory;

  @override
  double getPrimaryValue() => totalOpened.toDouble();

  const CapsuleStatisticsData({
    required this.id,
    required this.period,
    required this.lastRefreshedAt,
    required this.isFromCache,
    required this.totalOpened,
    required this.totalCollected,
    required this.totalShared,
    required this.averageEngagement,
    required this.byCategory,
  });

  @override
  double? calculateChange(StatisticsEntity? previous) {
    if (previous == null || previous is! CapsuleStatisticsData) {
      return null;
    }
    if (previous.totalOpened == 0) {
      return totalOpened > 0 ? 100.0 : 0.0;
    }
    return ((totalOpened - previous.totalOpened) / previous.totalOpened) * 100;
  }

  CapsuleStatisticsData copyWith({
    String? id,
    StatisticsPeriod? period,
    DateTime? lastRefreshedAt,
    bool? isFromCache,
    int? totalOpened,
    int? totalCollected,
    int? totalShared,
    double? averageEngagement,
    Map<String, int>? byCategory,
  }) {
    return CapsuleStatisticsData(
      id: id ?? this.id,
      period: period ?? this.period,
      lastRefreshedAt: lastRefreshedAt ?? this.lastRefreshedAt,
      isFromCache: isFromCache ?? this.isFromCache,
      totalOpened: totalOpened ?? this.totalOpened,
      totalCollected: totalCollected ?? this.totalCollected,
      totalShared: totalShared ?? this.totalShared,
      averageEngagement: averageEngagement ?? this.averageEngagement,
      byCategory: byCategory ?? this.byCategory,
    );
  }
}

/// Repository for capsule statistics
class CapsuleStatsRepository extends HybridStatisticsRepository<CapsuleStatisticsData> {
  CapsuleStatsRepository({required super.database, super.cacheConfig});

  @override
  StatisticsType get type => StatisticsType.capsule;

  @override
  Future<CapsuleStatisticsData> fetchFromApi(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    final now = DateTime.now();
    final mockData = CapsuleStatisticsData(
      id: 'capsule_${period.name}_${now.millisecondsSinceEpoch}',
      period: period,
      lastRefreshedAt: now,
      isFromCache: false,
      totalOpened: _generateMockOpened(period),
      totalCollected: _generateMockCollected(period),
      totalShared: _generateMockShared(period),
      averageEngagement: 4.2,
      byCategory: const {
        'science': 8,
        'history': 5,
        'art': 6,
        'technology': 10,
      },
    );
    return mockData;
  }

  @override
  CapsuleStatisticsData deserializeEntity(Map<String, dynamic> json) {
    return CapsuleStatisticsData(
      id: json['id'] as String,
      period: StatisticsPeriodExt.fromCode(json['period'] as String),
      lastRefreshedAt: DateTime.parse(json['lastRefreshedAt'] as String),
      isFromCache: json['isFromCache'] as bool,
      totalOpened: json['totalOpened'] as int,
      totalCollected: json['totalCollected'] as int,
      totalShared: json['totalShared'] as int,
      averageEngagement: json['averageEngagement'] as double,
      byCategory: Map<String, int>.from(json['byCategory'] as Map),
    );
  }

  @override
  Map<String, dynamic> serializeEntity(CapsuleStatisticsData entity) {
    return {
      'id': entity.id,
      'type': entity.type.code,
      'period': entity.period.name,
      'lastRefreshedAt': entity.lastRefreshedAt.toIso8601String(),
      'isFromCache': entity.isFromCache,
      'totalOpened': entity.totalOpened,
      'totalCollected': entity.totalCollected,
      'totalShared': entity.totalShared,
      'averageEngagement': entity.averageEngagement,
      'byCategory': entity.byCategory,
    };
  }

  int _generateMockOpened(StatisticsPeriod period) {
    switch (period) {
      case StatisticsPeriod.today:
        return 12;
      case StatisticsPeriod.week:
        return 55;
      case StatisticsPeriod.month:
        return 220;
      case StatisticsPeriod.year:
        return 2640;
      case StatisticsPeriod.custom:
        return 30;
    }
  }

  int _generateMockCollected(StatisticsPeriod period) {
    return (_generateMockOpened(period) * 1.5).toInt();
  }

  int _generateMockShared(StatisticsPeriod period) {
    return (_generateMockOpened(period) * 0.3).toInt();
  }
}

/// Provider for capsule statistics repository
@riverpod
CapsuleStatsRepository capsuleStatsRepository(CapsuleStatsRepositoryRef ref) {
  final database = ref.watch(localDatabaseProvider);
  return CapsuleStatsRepository(database: database);
}

/// Provider for capsule statistics state
@riverpod
class CapsuleStatistics extends _$CapsuleStatistics {
  @override
  StatisticsState<CapsuleStatisticsData> build() {
    return const StatisticsState.initial();
  }

  Future<void> load(
    StatisticsPeriod period, {
    bool forceRefresh = false,
  }) async {
    state = StatisticsState<CapsuleStatisticsData>.loading(period: period);

    final repository = ref.read(capsuleStatsRepositoryProvider);
    try {
      final data = await repository.getStatistics(
        period,
        forceRefresh: forceRefresh,
      );
      state = state.withData(data, period: period);
    } catch (e) {
      state = state.withError('加载失败: ${e.toString()}');
    }
  }

  Future<void> refresh() async {
    final period = state.lastPeriod ?? StatisticsPeriod.today;
    await load(period, forceRefresh: true);
  }

  Future<void> clearCache() async {
    final repository = ref.read(capsuleStatsRepositoryProvider);
    await repository.clearCache();
    state = const StatisticsState.initial();
  }
}
