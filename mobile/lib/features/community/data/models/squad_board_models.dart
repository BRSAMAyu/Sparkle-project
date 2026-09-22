/// D-COMM-4：小队榜（`GET /community/squads/{id}/leaderboard`）模型。
///
/// 后端契约（app/schemas/community_squad_board.py）：口径唯一来自
/// D-COMM-3 冲刺完成度聚合（sprint_task_ledger，BP-4 单一事实源）；
/// rank 为并列名次（竞赛排名 1,1,3——客户端如实渲染，不重排不去重）；
/// 成员 <3 人时 board_valid=false / self_view_only=true——客户端切自我锚
/// 视图（设计裁决），本模型仅承载标记，不擅自渲染残缺榜。
/// 手写 fromJson（只读视图契约，不进 build_runner）。
class SquadLeaderboardEntry {
  const SquadLeaderboardEntry({
    required this.rank,
    required this.userId,
    required this.completionRate,
    required this.hasLedgerData,
    required this.percentile,
    this.displayName,
    this.taskTotal = 0,
    this.taskCompleted = 0,
  });

  factory SquadLeaderboardEntry.fromJson(Map<String, dynamic> json) =>
      SquadLeaderboardEntry(
        rank: (json['rank'] as num?)?.toInt() ?? 0,
        userId: json['user_id'] as String? ?? '',
        displayName: json['display_name'] as String?,
        taskTotal: (json['task_total'] as num?)?.toInt() ?? 0,
        taskCompleted: (json['task_completed'] as num?)?.toInt() ?? 0,
        completionRate: (json['completion_rate'] as num?)?.toDouble() ?? 0.0,
        hasLedgerData: json['has_ledger_data'] == true,
        percentile: (json['percentile'] as num?)?.toInt() ?? 0,
      );

  /// 并列名次（完成度键全同的成员同名次：1,1,3 如实）。
  final int rank;
  final String userId;

  /// 昵称或用户名（缺失为 null——渲染回退到「成员」占位由 l10n 提供，
  /// 模型不造假名）。
  final String? displayName;
  final int taskTotal;
  final int taskCompleted;

  /// 冲刺完成率 0.0-1.0（sprint-completion 口径）。
  final double completionRate;

  /// 账本是否非空（空数据诚实语义：false = 无账本数据，0% 是真零）。
  final bool hasLedgerData;

  /// 名次区间：完成度严格低于该成员的队员占比（D21 区间展示）。
  final int percentile;
}

class SquadLeaderboard {
  const SquadLeaderboard({
    required this.squadId,
    required this.memberCount,
    required this.sprintActive,
    required this.boardValid,
    required this.selfViewOnly,
    required this.entries,
    this.myRank,
  });

  factory SquadLeaderboard.fromJson(Map<String, dynamic> json) {
    final entries = (json['entries'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(SquadLeaderboardEntry.fromJson)
        .toList();
    return SquadLeaderboard(
      squadId: json['squad_id'] as String? ?? '',
      memberCount: (json['member_count'] as num?)?.toInt() ?? 0,
      sprintActive: json['sprint_active'] == true,
      boardValid: json['board_valid'] == true,
      selfViewOnly: json['self_view_only'] == true,
      myRank: (json['my_rank'] as num?)?.toInt(),
      entries: entries,
    );
  }

  final String squadId;
  final int memberCount;

  /// 是否仍在冲刺周期内（deadline 未过）。
  final bool sprintActive;

  /// 榜单是否成立（成员数 ≥ 3）。
  final bool boardValid;

  /// 成员不足 3 人时为 true——客户端切自我锚视图（设计裁决）。
  final bool selfViewOnly;

  /// 请求者名次（成员必在榜上；降级时为自我锚位置，降级视图不渲染）。
  final int? myRank;
  final List<SquadLeaderboardEntry> entries;
}
