import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/dio_provider.dart';
import 'package:sparkle/features/leaderboard/data/repositories/leaderboard_repository.dart';

// ========== Leaderboard Types ==========

enum LeaderboardType {
  global('global'),
  friends('friends'),
  group('group'),
  subject('subject'),
  weekly('weekly'),
  streak('streak');

  const LeaderboardType(this.value);
  final String value;

  static LeaderboardType fromString(String value) => LeaderboardType.values.firstWhere(
      (type) => type.value == value,
      orElse: () => LeaderboardType.global,
    );
}

enum LeaderboardPeriod {
  allTime('all_time'),
  weekly('weekly'),
  monthly('monthly'),
  daily('daily');

  const LeaderboardPeriod(this.value);
  final String value;

  static LeaderboardPeriod fromString(String value) => LeaderboardPeriod.values.firstWhere(
      (type) => type.value == value,
      orElse: () => LeaderboardPeriod.allTime,
    );
}

// ========== Leaderboard State ==========

class LeaderboardEntry {

  factory LeaderboardEntry.fromJson(Map<String, dynamic> json) {
    return LeaderboardEntry(
      rank: json['rank'] as int,
      userId: json['user_id'] as String,
      username: json['username'] as String,
      avatarUrl: json['avatar_url'] as String?,
      score: (json['score'] as num).toDouble(),
      scoreLabel: json['score_label'] as String,
      isMe: json['is_me'] as bool? ?? false,
      change: json['change'] as int?,
      stats: json['stats'] as Map<String, dynamic>? ?? {},
      badge: json['badge'] as String?,
    );
  }
  LeaderboardEntry({
    required this.rank,
    required this.userId,
    required this.username,
    required this.score,
    required this.scoreLabel,
    this.avatarUrl,
    this.isMe = false,
    this.change,
    this.stats = const {},
    this.badge,
  });

  final int rank;
  final String userId;
  final String username;
  final String? avatarUrl;
  final double score;
  final String scoreLabel;
  final bool isMe;
  final int? change;
  final Map<String, dynamic> stats;
  final String? badge;

  Map<String, dynamic> toJson() => {
      'rank': rank,
      'user_id': userId,
      'username': username,
      'avatar_url': avatarUrl,
      'score': score,
      'score_label': scoreLabel,
      'is_me': isMe,
      'change': change,
      'stats': stats,
      'badge': badge,
    };
}

class LeaderboardData {

  factory LeaderboardData.fromJson(Map<String, dynamic> json) {
    return LeaderboardData(
      type: LeaderboardType.fromString(json['type'] as String),
      title: json['title'] as String,
      entries: (json['entries'] as List<dynamic>)
          .map((e) => LeaderboardEntry.fromJson(e as Map<String, dynamic>))
          .toList(),
      myRank: json['my_rank'] as int?,
      myScore: json['my_score'] as double?,
      lastUpdated: DateTime.parse(json['last_updated'] as String),
      totalParticipants: json['total_participants'] as int,
      period: LeaderboardPeriod.fromString(json['period'] as String? ?? 'all_time'),
    );
  }
  LeaderboardData({
    required this.type,
    required this.title,
    required this.entries,
    required this.lastUpdated, required this.totalParticipants, required this.period, this.myRank,
    this.myScore,
  });

  final LeaderboardType type;
  final String title;
  final List<LeaderboardEntry> entries;
  final int? myRank;
  final double? myScore;
  final DateTime lastUpdated;
  final int totalParticipants;
  final LeaderboardPeriod period;
}

class LeaderboardState {
  LeaderboardState({
    required this.leaderboards,
    this.isLoading = false,
    this.error,
    this.lastUpdated,
  });

  LeaderboardState.loading()
      : leaderboards = {},
        isLoading = true,
        error = null,
        lastUpdated = null;

  LeaderboardState.error(String errorMessage)
      : leaderboards = {},
        isLoading = false,
        error = errorMessage,
        lastUpdated = null;

  final Map<LeaderboardType, LeaderboardData> leaderboards;
  final bool isLoading;
  final String? error;
  final DateTime? lastUpdated;

  LeaderboardState copyWith({
    Map<LeaderboardType, LeaderboardData>? leaderboards,
    bool? isLoading,
    String? error,
    DateTime? lastUpdated,
  }) =>
      LeaderboardState(
        leaderboards: leaderboards ?? this.leaderboards,
        isLoading: isLoading ?? this.isLoading,
        error: error ?? this.error,
        lastUpdated: lastUpdated ?? this.lastUpdated,
      );

  LeaderboardData? getLeaderboard(LeaderboardType type) => leaderboards[type];
}

class MyRankState {

  MyRankState.loading()
      : rank = null,
        score = null,
        scoreLabel = null,
        totalParticipants = null,
        percentile = null,
        changeFromLastPeriod = null,
        nearbyUsers = const [],
        isLoading = true,
        error = null;

  MyRankState.error(String errorMessage)
      : rank = null,
        score = null,
        scoreLabel = null,
        totalParticipants = null,
        percentile = null,
        changeFromLastPeriod = null,
        nearbyUsers = const [],
        isLoading = false,
        error = errorMessage;
  MyRankState({
    this.rank,
    this.score,
    this.scoreLabel,
    this.totalParticipants,
    this.percentile,
    this.changeFromLastPeriod,
    this.nearbyUsers = const [],
    this.isLoading = false,
    this.error,
  });

  final int? rank;
  final double? score;
  final String? scoreLabel;
  final int? totalParticipants;
  final double? percentile;
  final int? changeFromLastPeriod;
  final List<LeaderboardEntry> nearbyUsers;
  final bool isLoading;
  final String? error;
}

// ========== Providers ==========

/// Leaderboard Repository Provider
final leaderboardRepositoryProvider = Provider<LeaderboardRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return LeaderboardRepository(apiClient);
});

/// Main Leaderboard Provider
final leaderboardProvider =
    StateNotifierProvider<LeaderboardNotifier, LeaderboardState>(
  (ref) => LeaderboardNotifier(ref.watch(leaderboardRepositoryProvider)),
);

/// My Rank Provider
final myRankProvider =
    StateNotifierProvider<MyRankNotifier, MyRankState>(
  (ref) => MyRankNotifier(ref.watch(leaderboardRepositoryProvider)),
);

// ========== Notifiers ==========

class LeaderboardNotifier extends StateNotifier<LeaderboardState> {
  LeaderboardNotifier(this._repository) : super(LeaderboardState.loading());

  final LeaderboardRepository _repository;

  /// Load all leaderboards
  Future<void> loadAllLeaderboards() async {
    try {
      state = LeaderboardState.loading();

      final types = [
        LeaderboardType.global,
        LeaderboardType.friends,
        LeaderboardType.weekly,
        LeaderboardType.streak,
      ];

      final results = await Future.wait(
        types.map((type) => _repository.getLeaderboard(
          type: type,
          period: LeaderboardPeriod.allTime,
        ),),
      );

      final leaderboards = <LeaderboardType, LeaderboardData>{};
      for (var i = 0; i < types.length; i++) {
        leaderboards[types[i]] = results[i];
      }

      state = LeaderboardState(
        leaderboards: leaderboards,
        lastUpdated: DateTime.now(),
      );
    } catch (e) {
      debugPrint('Error loading leaderboards: $e');
      state = LeaderboardState.error(e.toString());
    }
  }

  /// Load specific leaderboard
  Future<void> loadLeaderboard(
    LeaderboardType type, {
    LeaderboardPeriod? period,
    int limit = 50,
    String? subjectId,
    String? groupId,
  }) async {
    try {
      final leaderboard = await _repository.getLeaderboard(
        type: type,
        period: period ?? LeaderboardPeriod.allTime,
        limit: limit,
        subjectId: subjectId,
        groupId: groupId,
      );

      final newLeaderboards = Map<LeaderboardType, LeaderboardData>.from(state.leaderboards);
      newLeaderboards[type] = leaderboard;

      state = state.copyWith(leaderboards: newLeaderboards);
    } catch (e) {
      debugPrint('Error loading leaderboard $type: $e');
    }
  }

  /// Refresh current leaderboard
  Future<void> refresh(LeaderboardType type) async {
    await loadLeaderboard(type);
  }

  /// Get leaderboard data
  LeaderboardData? getData(LeaderboardType type) => state.leaderboards[type];
}

class MyRankNotifier extends StateNotifier<MyRankState> {
  MyRankNotifier(this._repository) : super(MyRankState.loading());

  final LeaderboardRepository _repository;

  /// Load my rank for a specific leaderboard
  Future<void> loadMyRank(
    LeaderboardType type, {
    LeaderboardPeriod? period,
  }) async {
    try {
      state = MyRankState.loading();

      final myRank = await _repository.getMyRank(
        type: type,
        period: period ?? LeaderboardPeriod.allTime,
      );

      state = MyRankState(
        rank: myRank.rank,
        score: myRank.score,
        scoreLabel: myRank.scoreLabel,
        totalParticipants: myRank.totalParticipants,
        percentile: myRank.percentile,
        changeFromLastPeriod: myRank.changeFromLastPeriod,
        nearbyUsers: myRank.nearbyUsers,
      );
    } catch (e) {
      debugPrint('Error loading my rank: $e');
      state = MyRankState.error(e.toString());
    }
  }

  /// Refresh my rank
  Future<void> refresh() async {
    // Reuse the last type that was loaded
    // For simplicity, we're not tracking the last type here
    // In production, you'd want to cache this
  }
}
