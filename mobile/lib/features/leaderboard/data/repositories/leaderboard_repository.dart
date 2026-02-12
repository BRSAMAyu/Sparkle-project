import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/leaderboard/presentation/providers/leaderboard_provider.dart';

/// String extension for capitalization
extension StringCapitalize on String {
  String capitalize() {
    if (isEmpty) return this;
    return this[0].toUpperCase() + substring(1);
  }
}

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
    if (DemoDataService.isDemoMode) {
      // Return mock leaderboard data for demo mode
      return LeaderboardData(
        type: type,
        title: 'Demo ${type.value.capitalize()} Leaderboard',
        period: period,
        entries: List.generate(10, (i) => LeaderboardEntry(
          rank: i + 1,
          userId: 'user-$i',
          username: 'Demo User ${i + 1}',
          score: (1000 - (i * 50)).toDouble(),
          scoreLabel: '${1000 - (i * 50)} XP',
          avatarUrl: null,
          change: i % 3 == 0 ? 1 : (i % 3 == 1 ? -1 : 0),
        )),
        totalParticipants: 100,
        lastUpdated: DateTime.now(),
      );
    }

    final queryParams = {
      'type': type.value,
      'limit': limit.toString(),
      'offset': offset.toString(),
      'period': period.value,
      if (subjectId != null) 'subject_id': subjectId,
      if (groupId != null) 'group_id': groupId,
    };

    final response = await _apiClient.get<Map<String, dynamic>>(
      '/leaderboards',
      queryParameters: queryParams,
    );

    final payload = ApiResponseParser.unwrapMap(response.data, action: 'getLeaderboard');
    final data = payload['data'] as Map<String, dynamic>?;
    if (data == null) {
      throw Exception('getLeaderboard: data field is missing');
    }

    return LeaderboardData.fromJson(data);
  }

  /// Get my rank
  Future<MyRankState> getMyRank({
    required LeaderboardType type,
    LeaderboardPeriod? period,
  }) async {
    if (DemoDataService.isDemoMode) {
      // Return mock rank data for demo mode
      return MyRankState(
        rank: 5,
        score: 750.0,
        scoreLabel: '750 XP',
        totalParticipants: 100,
        percentile: 95.0,
        changeFromLastPeriod: 2,
        nearbyUsers: List.generate(5, (i) => LeaderboardEntry(
          rank: 3 + i,
          userId: 'user-$i',
          username: 'Nearby User ${i + 1}',
          score: (850 - (i * 50)).toDouble(),
          scoreLabel: '${850 - (i * 50)} XP',
          avatarUrl: null,
          change: 0,
        )),
      );
    }

    final queryParams = {
      'type': type.value,
      if (period != null) 'period': period.value,
    };

    final response = await _apiClient.get<Map<String, dynamic>>(
      '/leaderboards/my-rank',
      queryParameters: queryParams,
    );

    final payload = ApiResponseParser.unwrapMap(response.data, action: 'getMyRank');
    final data = payload['data'] as Map<String, dynamic>?;

    if (data == null) {
      throw Exception('getMyRank: data field is missing');
    }

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
  }

  /// Get top three for podium display
  Future<List<LeaderboardEntry>> getTopThree(LeaderboardType type) async {
    if (DemoDataService.isDemoMode) {
      // Return mock top three for demo mode
      return [
        LeaderboardEntry(
          rank: 1,
          userId: 'user-1',
          username: 'Demo Champion',
          score: 1000.0,
          scoreLabel: '1000 XP',
          avatarUrl: null,
          change: 0,
        ),
        LeaderboardEntry(
          rank: 2,
          userId: 'user-2',
          username: 'Demo Second',
          score: 950.0,
          scoreLabel: '950 XP',
          avatarUrl: null,
          change: 1,
        ),
        LeaderboardEntry(
          rank: 3,
          userId: 'user-3',
          username: 'Demo Third',
          score: 900.0,
          scoreLabel: '900 XP',
          avatarUrl: null,
          change: -1,
        ),
      ];
    }

    final response = await _apiClient.get<Map<String, dynamic>>(
      '/leaderboards/top-three/${type.value}',
    );

    final payload = ApiResponseParser.unwrapMap(response.data, action: 'getTopThree');
    final data = payload['data'] as Map<String, dynamic>?;

    if (data == null) {
      throw Exception('getTopThree: data field is missing');
    }

    final entries = <LeaderboardEntry>[];

    for (final key in ['first', 'second', 'third']) {
      final entryData = data[key];
      if (entryData != null) {
        entries.add(LeaderboardEntry.fromJson(entryData as Map<String, dynamic>));
      }
    }

    return entries;
  }

  /// Get leaderboard summary
  Future<Map<LeaderboardType, LeaderboardData>> getSummary() async {
    if (DemoDataService.isDemoMode) {
      // Return mock summary for demo mode
      return {
        LeaderboardType.global: LeaderboardData(
          type: LeaderboardType.global,
          title: 'Global Leaderboard',
          period: LeaderboardPeriod.allTime,
          entries: [],
          totalParticipants: 100,
          lastUpdated: DateTime.now(),
        ),
        LeaderboardType.friends: LeaderboardData(
          type: LeaderboardType.friends,
          title: 'Friends Leaderboard',
          period: LeaderboardPeriod.allTime,
          entries: [],
          totalParticipants: 25,
          lastUpdated: DateTime.now(),
        ),
        LeaderboardType.weekly: LeaderboardData(
          type: LeaderboardType.weekly,
          title: 'Weekly Leaderboard',
          period: LeaderboardPeriod.weekly,
          entries: [],
          totalParticipants: 50,
          lastUpdated: DateTime.now(),
        ),
      };
    }

    final response = await _apiClient.get<Map<String, dynamic>>('/leaderboards/summary');

    final payload = ApiResponseParser.unwrapMap(response.data, action: 'getSummary');
    final data = payload['data'] as Map<String, dynamic>?;

    if (data == null) {
      throw Exception('getSummary: data field is missing');
    }

    final summary = <LeaderboardType, LeaderboardData>{};

    for (final key in ['global', 'friends', 'weekly', 'streak']) {
      final leaderboardData = data[key];
      if (leaderboardData != null) {
        summary[LeaderboardType.fromString(key)] =
            LeaderboardData.fromJson(leaderboardData as Map<String, dynamic>);
      }
    }

    return summary;
  }

  /// Refresh leaderboard cache
  Future<bool> refreshCache({LeaderboardType? type}) async {
    if (DemoDataService.isDemoMode) {
      // Return success for demo mode
      return true;
    }

    final queryParams = {
      if (type != null) 'type': type.value,
    };

    final response = await _apiClient.post<Map<String, dynamic>>(
      '/leaderboards/refresh-cache',
      queryParameters: queryParams,
    );

    final payload = ApiResponseParser.unwrapMap(response.data, action: 'refreshCache');
    return payload['success'] == true;
  }
}
