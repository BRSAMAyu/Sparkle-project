import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/leaderboard/presentation/providers/leaderboard_provider.dart';

/// Leaderboard Repository
class LeaderboardRepository {
  LeaderboardRepository(this._apiClient);

  final ApiClient _apiClient;

  /// Get leaderboard
  Future<LeaderboardData> getLeaderboard({
    required LeaderboardType type,
    required LeaderboardPeriod period,
    int limit = 50,
    int offset = 0,
    String? subjectId,
    String? groupId,
  }) async {
    final queryParams = {
      'type': type.value,
      'limit': limit.toString(),
      'offset': offset.toString(),
      'period': period.value,
      if (subjectId != null) 'subject_id': subjectId,
      if (groupId != null) 'group_id': groupId,
    };

    final response = await _apiClient.get(
      '/leaderboards',
      queryParameters: queryParams,
    );

    if (response.data['success'] == true) {
      return LeaderboardData.fromJson(response.data['data'] as Map<String, dynamic>);
    } else {
      throw Exception(response.data['message'] ?? 'Failed to load leaderboard');
    }
  }

  /// Get my rank
  Future<MyRankState> getMyRank({
    required LeaderboardType type,
    LeaderboardPeriod? period,
  }) async {
    final queryParams = {
      'type': type.value,
      if (period != null) 'period': period.value,
    };

    final response = await _apiClient.get(
      '/leaderboards/my-rank',
      queryParameters: queryParams,
    );

    if (response.data['success'] == true) {
      final data = response.data['data'] as Map<String, dynamic>;

      final nearbyUsers = (data['nearby_users'] as List<dynamic>?)
              ?.map((e) => LeaderboardEntry.fromJson(e as Map<String, dynamic>))
              .toList() ?? [];

      return MyRankState(
        rank: data['rank'] as int?,
        score: data['score'] as double?,
        scoreLabel: data['score_label'] as String?,
        totalParticipants: data['total_participants'] as int?,
        percentile: data['percentile'] as double?,
        changeFromLastPeriod: data['change_from_last_period'] as int?,
        nearbyUsers: nearbyUsers,
      );
    } else {
      throw Exception(response.data['message'] ?? 'Failed to load my rank');
    }
  }

  /// Get top three for podium display
  Future<List<LeaderboardEntry>> getTopThree(LeaderboardType type) async {
    final response = await _apiClient.get(
      '/leaderboards/top-three/${type.value}',
    );

    if (response.data['success'] == true) {
      final data = response.data['data'] as Map<String, dynamic>;
      final entries = <LeaderboardEntry>[];

      for (final key in ['first', 'second', 'third']) {
        final entryData = data[key];
        if (entryData != null) {
          entries.add(LeaderboardEntry.fromJson(entryData as Map<String, dynamic>));
        }
      }

      return entries;
    } else {
      throw Exception(response.data['message'] ?? 'Failed to load top three');
    }
  }

  /// Get leaderboard summary
  Future<Map<LeaderboardType, LeaderboardData>> getSummary() async {
    final response = await _apiClient.get('/leaderboards/summary');

    if (response.data['success'] == true) {
      final data = response.data['data'] as Map<String, dynamic>;
      final summary = <LeaderboardType, LeaderboardData>{};

      for (final key in ['global', 'friends', 'weekly', 'streak']) {
        final leaderboardData = data[key];
        if (leaderboardData != null) {
          summary[LeaderboardType.fromString(key)] =
              LeaderboardData.fromJson(leaderboardData as Map<String, dynamic>);
        }
      }

      return summary;
    } else {
      throw Exception(response.data['message'] ?? 'Failed to load summary');
    }
  }

  /// Refresh leaderboard cache
  Future<bool> refreshCache({LeaderboardType? type}) async {
    final queryParams = {
      if (type != null) 'type': type.value,
    };

    final response = await _apiClient.post(
      '/leaderboards/refresh-cache',
      queryParameters: queryParams,
    );

    return response.data['success'] == true;
  }
}
