import 'package:dio/dio.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/statistics/data/statistics_data.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';
import 'package:sparkle/core/statistics/presentation/providers/statistics_provider.dart';

part 'capsule_statistics_provider.g.dart';

/// Capsule statistics entity
///
/// Field semantics mirror the backend `/capsules/stats` aggregation over
/// `curiosity_capsules` / `capsule_favorites` / `capsule_feedbacks` for the
/// requested period window (B-02 lineage INV-03). Fields with no real data
/// source are absent or `null` — never a fabricated constant.
class CapsuleStatisticsData extends StatisticsEntity {

  CapsuleStatisticsData({
    required this.id,
    required this.period,
    required this.lastRefreshedAt,
    required this.isFromCache,
    required this.totalReceived,
    required this.totalRead,
    required this.totalFavorited,
    required this.totalFeedbackGiven,
    required this.averageRating,
  });
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

  /// Capsules received (created) in the period
  /// (server: `total_received`)
  final int totalReceived;

  /// Capsules read in the period (server: `total_read`)
  final int totalRead;

  /// Capsules favorited in the period (server: `total_favorited`)
  final int totalFavorited;

  /// Feedback submissions in the period (server: `total_feedback_given`)
  final int totalFeedbackGiven;

  /// Average star rating given in the period.
  /// Null when no rated feedback exists in the window (unknown).
  final double? averageRating;

  @override
  double getPrimaryValue() => totalRead.toDouble();

  @override
  double? calculateChange(StatisticsEntity? previous) {
    if (previous == null || previous is! CapsuleStatisticsData) {
      return null;
    }
    if (previous.totalRead == 0) {
      return totalRead > 0 ? 100.0 : 0.0;
    }
    return ((totalRead - previous.totalRead) / previous.totalRead) * 100;
  }

  CapsuleStatisticsData copyWith({
    String? id,
    StatisticsPeriod? period,
    DateTime? lastRefreshedAt,
    bool? isFromCache,
    int? totalReceived,
    int? totalRead,
    int? totalFavorited,
    int? totalFeedbackGiven,
    double? averageRating,
  }) => CapsuleStatisticsData(
    id: id ?? this.id,
    period: period ?? this.period,
    lastRefreshedAt: lastRefreshedAt ?? this.lastRefreshedAt,
    isFromCache: isFromCache ?? this.isFromCache,
    totalReceived: totalReceived ?? this.totalReceived,
    totalRead: totalRead ?? this.totalRead,
    totalFavorited: totalFavorited ?? this.totalFavorited,
    totalFeedbackGiven: totalFeedbackGiven ?? this.totalFeedbackGiven,
    averageRating: averageRating ?? this.averageRating,
  );
}

/// Repository for capsule statistics.
///
/// Data source: `GET /capsules/stats?start=<utc-iso>&end=<utc-iso>` — a real
/// per-user DB aggregation scoped to the requested period window. There is
/// no client-side fallback: transport failures propagate (D-04).
class CapsuleStatsRepository extends HybridStatisticsRepository<CapsuleStatisticsData> {
  CapsuleStatsRepository({required super.database, super.cacheConfig, Dio? dio})
      : dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: ApiEndpoints.baseUrl,
                connectTimeout: const Duration(seconds: 10),
                receiveTimeout: const Duration(seconds: 30),
              ),
            );

  /// HTTP client used for statistics fetches. Production wiring passes the
  /// shared authenticated client (`ApiClient.dio`); tests inject a stub.
  final Dio dio;

  @override
  StatisticsType get type => StatisticsType.capsule;

  @override
  Future<CapsuleStatisticsData> fetchFromApi(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    // The backend aggregates on created_at, stored as naive UTC — send the
    // period bounds as UTC ISO timestamps so the window matches what the
    // user sees locally.
    final response = await dio.get<dynamic>(
      ApiEndpoints.capsuleStats,
      queryParameters: <String, dynamic>{
        'start': period
            .getStartTime(customStart: customStart)
            .toUtc()
            .toIso8601String(),
        'end': period
            .getEndTime(customEnd: customEnd)
            .toUtc()
            .toIso8601String(),
      },
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchCapsuleStats',
    );

    final now = DateTime.now();
    return CapsuleStatisticsData(
      id: 'capsule_${period.name}_${now.millisecondsSinceEpoch}',
      period: period,
      lastRefreshedAt: now,
      isFromCache: false,
      totalReceived: (payload['total_received'] as num?)?.toInt() ?? 0,
      totalRead: (payload['total_read'] as num?)?.toInt() ?? 0,
      totalFavorited: (payload['total_favorited'] as num?)?.toInt() ?? 0,
      totalFeedbackGiven: (payload['total_feedback_given'] as num?)?.toInt() ?? 0,
      averageRating: (payload['average_rating_given'] as num?)?.toDouble(),
    );
  }

  @override
  CapsuleStatisticsData deserializeEntity(Map<String, dynamic> json) =>
      CapsuleStatisticsData(
        id: json['id'] as String,
        period: StatisticsPeriodExt.fromCode(json['period'] as String),
        lastRefreshedAt: DateTime.parse(json['lastRefreshedAt'] as String),
        isFromCache: json['isFromCache'] as bool,
        totalReceived: json['totalReceived'] as int,
        totalRead: json['totalRead'] as int,
        totalFavorited: json['totalFavorited'] as int,
        totalFeedbackGiven: json['totalFeedbackGiven'] as int,
        averageRating: (json['averageRating'] as num?)?.toDouble(),
      );

  @override
  Map<String, dynamic> serializeEntity(CapsuleStatisticsData entity) => {
      'id': entity.id,
      'type': entity.type.code,
      'period': entity.period.name,
      'lastRefreshedAt': entity.lastRefreshedAt.toIso8601String(),
      'isFromCache': entity.isFromCache,
      'totalReceived': entity.totalReceived,
      'totalRead': entity.totalRead,
      'totalFavorited': entity.totalFavorited,
      'totalFeedbackGiven': entity.totalFeedbackGiven,
      'averageRating': entity.averageRating,
    };

  @override
  CapsuleStatisticsData markFromCache(CapsuleStatisticsData entity) =>
      entity.isFromCache ? entity : entity.copyWith(isFromCache: true);
}

/// Provider for capsule statistics repository
@riverpod
CapsuleStatsRepository capsuleStatsRepository(CapsuleStatsRepositoryRef ref) {
  final database = ref.watch(localDatabaseProvider);
  return CapsuleStatsRepository(
    database: database,
    // Shared authenticated transport (auth/retry/logging/pinning stack).
    dio: ref.watch(apiClientProvider).dio,
  );
}

/// Provider for capsule statistics state
@riverpod
class CapsuleStatistics extends _$CapsuleStatistics {
  @override
  StatisticsState<CapsuleStatisticsData> build() => const StatisticsState.initial();

  Future<void> load(
    StatisticsPeriod period, {
    bool forceRefresh = false,
  }) async {
    // Keep the last-known-real snapshot across the reload so an offline
    // reload can display "data as of <lastRefreshedAt>" (D-04).
    final previous = state;
    state = StatisticsState<CapsuleStatisticsData>.loading(period: period);

    final repository = ref.read(capsuleStatsRepositoryProvider);
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
    final repository = ref.read(capsuleStatsRepositoryProvider);
    await repository.clearCache();
    state = const StatisticsState.initial();
  }
}
