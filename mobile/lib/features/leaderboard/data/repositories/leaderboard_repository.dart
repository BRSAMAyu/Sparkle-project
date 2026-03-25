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
      final myEntry = LeaderboardEntry(
        rank: 5,
        userId: DemoDataService.demoUserId,
        username: 'Mika',
        avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=${DemoDataService.demoAvatarSeed}',
        score: 750.0,
        scoreLabel: '750 XP',
        isMe: true,
        change: 2,
        stats: {'tasks_completed': 18, 'streak_days': 7},
        badge: 'steady_climber',
      );
      final entries = <LeaderboardEntry>[
        LeaderboardEntry(
          rank: 1,
          userId: 'user_alice',
          username: 'Lena_Words',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Alice',
          score: 980.0,
          scoreLabel: '980 XP',
          change: 1,
          stats: {'tasks_completed': 26, 'streak_days': 12},
          badge: 'top_streak',
        ),
        LeaderboardEntry(
          rank: 2,
          userId: 'user_charlie',
          username: 'Mori_Creative',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Carol',
          score: 920.0,
          scoreLabel: '920 XP',
          change: -1,
          stats: {'tasks_completed': 24, 'streak_days': 10},
          badge: 'consistent',
        ),
        LeaderboardEntry(
          rank: 3,
          userId: 'user_emma',
          username: 'Rina_Path',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Emma',
          score: 880.0,
          scoreLabel: '880 XP',
          change: 0,
          stats: {'tasks_completed': 22, 'streak_days': 9},
          badge: 'focus_master',
        ),
        LeaderboardEntry(
          rank: 4,
          userId: 'user_david',
          username: 'Nora_Reset',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=David',
          score: 810.0,
          scoreLabel: '810 XP',
          change: 1,
          stats: {'tasks_completed': 20, 'streak_days': 8},
        ),
        myEntry,
        LeaderboardEntry(
          rank: 6,
          userId: 'user_bob',
          username: 'Owen_Field',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Bob',
          score: 710.0,
          scoreLabel: '710 XP',
          change: -1,
          stats: {'tasks_completed': 17, 'streak_days': 6},
        ),
      ];
      return LeaderboardData(
        type: type,
        title: '${type.value.capitalize()} Leaderboard',
        period: period,
        entries: entries.take(limit).skip(offset).toList(),
        totalParticipants: 42,
        lastUpdated: DateTime.now(),
        myRank: myEntry.rank,
        myScore: myEntry.score,
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
      final nearbyUsers = [
        LeaderboardEntry(
          rank: 3,
          userId: 'user_emma',
          username: 'Rina_Path',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Emma',
          score: 880.0,
          scoreLabel: '880 XP',
          change: 0,
        ),
        LeaderboardEntry(
          rank: 4,
          userId: 'user_david',
          username: 'Nora_Reset',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=David',
          score: 810.0,
          scoreLabel: '810 XP',
          change: 1,
        ),
        LeaderboardEntry(
          rank: 5,
          userId: DemoDataService.demoUserId,
          username: 'Mika',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=${DemoDataService.demoAvatarSeed}',
          score: 750.0,
          scoreLabel: '750 XP',
          change: 2,
          isMe: true,
        ),
        LeaderboardEntry(
          rank: 6,
          userId: 'user_bob',
          username: 'Owen_Field',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Bob',
          score: 710.0,
          scoreLabel: '710 XP',
          change: -1,
        ),
      ];
      return MyRankState(
        rank: 5,
        score: 750.0,
        scoreLabel: '750 XP',
        totalParticipants: 100,
        percentile: 95.0,
        changeFromLastPeriod: 2,
        nearbyUsers: nearbyUsers,
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
          userId: 'user_alice',
          username: 'Lena_Words',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Alice',
          score: 980.0,
          scoreLabel: '980 XP',
          change: 0,
        ),
        LeaderboardEntry(
          rank: 2,
          userId: 'user_charlie',
          username: 'Mori_Creative',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Carol',
          score: 920.0,
          scoreLabel: '920 XP',
          change: 1,
        ),
        LeaderboardEntry(
          rank: 3,
          userId: 'user_emma',
          username: 'Rina_Path',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Emma',
          score: 880.0,
          scoreLabel: '880 XP',
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
          entries: [
            LeaderboardEntry(rank: 1, userId: 'user_alice', username: 'Lena_Words', score: 980.0, scoreLabel: '980 XP'),
            LeaderboardEntry(rank: 2, userId: 'user_charlie', username: 'Mori_Creative', score: 920.0, scoreLabel: '920 XP'),
            LeaderboardEntry(rank: 3, userId: 'user_emma', username: 'Rina_Path', score: 880.0, scoreLabel: '880 XP'),
          ],
          totalParticipants: 42,
          lastUpdated: DateTime.now(),
        ),
        LeaderboardType.friends: LeaderboardData(
          type: LeaderboardType.friends,
          title: 'Friends Leaderboard',
          period: LeaderboardPeriod.allTime,
          entries: [
            LeaderboardEntry(rank: 1, userId: 'friend_1', username: 'Lena_Words', score: 980.0, scoreLabel: '980 XP'),
            LeaderboardEntry(rank: 2, userId: 'friend_3', username: 'Mori_Creative', score: 920.0, scoreLabel: '920 XP'),
            LeaderboardEntry(rank: 3, userId: DemoDataService.demoUserId, username: 'Mika', score: 750.0, scoreLabel: '750 XP', isMe: true),
          ],
          totalParticipants: 6,
          lastUpdated: DateTime.now(),
        ),
        LeaderboardType.weekly: LeaderboardData(
          type: LeaderboardType.weekly,
          title: 'Weekly Leaderboard',
          period: LeaderboardPeriod.weekly,
          entries: [
            LeaderboardEntry(rank: 1, userId: 'user_emma', username: 'Rina_Path', score: 320.0, scoreLabel: '320 XP'),
            LeaderboardEntry(rank: 2, userId: DemoDataService.demoUserId, username: 'Mika', score: 300.0, scoreLabel: '300 XP', isMe: true),
            LeaderboardEntry(rank: 3, userId: 'user_david', username: 'Nora_Reset', score: 260.0, scoreLabel: '260 XP'),
          ],
          totalParticipants: 18,
          lastUpdated: DateTime.now(),
        ),
        LeaderboardType.streak: LeaderboardData(
          type: LeaderboardType.streak,
          title: 'Streak Leaderboard',
          period: LeaderboardPeriod.daily,
          entries: [
            LeaderboardEntry(rank: 1, userId: 'user_alice', username: 'Lena_Words', score: 12.0, scoreLabel: '12 days'),
            LeaderboardEntry(rank: 2, userId: DemoDataService.demoUserId, username: 'Mika', score: 7.0, scoreLabel: '7 days', isMe: true),
          ],
          totalParticipants: 12,
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
