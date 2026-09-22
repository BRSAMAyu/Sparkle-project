/// D-COMM-4：共学自习室（`/community/squads/{id}/study-room/*`）模型。
///
/// 后端契约（app/schemas/community_study_room.py）：
/// - 在场 = study_room_sessions 的进出记录（口径词典「在场」，时长仅展示）；
/// - in_room：有开放会话即在室；is_stale：在室但心跳超阈值（崩溃恢复线索，
///   非惩罚——展示层只作弱提示，不作状态降级）；
/// - 时长分钟粒度、地板取整；「今日累计」按成员本地日界（服务端算好，
///   客户端不自算不换算）。
/// 手写 fromJson（只读视图契约，不进 build_runner）。
class StudyRoomPresenceEntry {
  const StudyRoomPresenceEntry({
    required this.userId,
    required this.inRoom,
    required this.isStale,
    required this.currentSessionMinutes,
    required this.todayMinutes,
    this.displayName,
    this.role,
  });

  factory StudyRoomPresenceEntry.fromJson(Map<String, dynamic> json) =>
      StudyRoomPresenceEntry(
        userId: json['user_id'] as String? ?? '',
        displayName: json['display_name'] as String?,
        role: json['role'] as String?,
        inRoom: json['in_room'] == true,
        isStale: json['is_stale'] == true,
        currentSessionMinutes:
            (json['current_session_minutes'] as num?)?.toInt() ?? 0,
        todayMinutes: (json['today_minutes'] as num?)?.toInt() ?? 0,
      );

  final String userId;

  /// 昵称或用户名（缺失为 null，展示层回退 l10n 占位）。
  final String? displayName;
  final String? role;

  /// 是否在室（有开放会话）。
  final bool inRoom;

  /// 在室但心跳超阈值（崩溃恢复线索，非惩罚）。
  final bool isStale;
  final int currentSessionMinutes;

  /// 今日累计自习分钟数（成员本地日界，跨会话求和）。
  final int todayMinutes;
}

class StudyRoomPresence {
  const StudyRoomPresence({
    required this.groupId,
    required this.memberCount,
    required this.inRoomCount,
    required this.members,
  });

  factory StudyRoomPresence.fromJson(Map<String, dynamic> json) {
    final members = (json['members'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(StudyRoomPresenceEntry.fromJson)
        .toList();
    return StudyRoomPresence(
      groupId: json['group_id'] as String? ?? '',
      memberCount: (json['member_count'] as num?)?.toInt() ?? 0,
      inRoomCount: (json['in_room_count'] as num?)?.toInt() ?? 0,
      members: members,
    );
  }

  final String groupId;
  final int memberCount;

  /// 当前在室人数。
  final int inRoomCount;
  final List<StudyRoomPresenceEntry> members;
}

/// 本人自习室状态（心跳端点的诚实上报：不在场时 in_room=false，
/// 绝不自动重开——本模型只读，进出以显式按钮为准）。
class StudyRoomMyStatus {
  const StudyRoomMyStatus({
    required this.inRoom,
    required this.todayMinutes,
  });

  factory StudyRoomMyStatus.fromJson(Map<String, dynamic> json) =>
      StudyRoomMyStatus(
        inRoom: json['in_room'] == true,
        todayMinutes: (json['today_minutes'] as num?)?.toInt() ?? 0,
      );

  final bool inRoom;

  /// 今日累计自习分钟数（本地日界）。
  final int todayMinutes;
}
