/// D-COMM-3：冲刺小队（`/community/squads*`）只读视图模型。
///
/// 后端契约（app/schemas/community_squad.py）：小队 = Group(type=SPRINT)
/// 的场景化门面，3-8 人，deadline 必填（冲刺周期既可见性窗口也是加入窗口）。
/// 手写 fromJson（一次性只读视图契约，对齐 SelfAnchorView 手写风格，
/// 不进 build_runner）。
class SquadListItem {
  const SquadListItem({
    required this.id,
    required this.name,
    required this.memberCount,
    required this.maxMembers,
    this.sprintGoal,
    this.deadline,
    this.daysRemaining,
    this.myRole,
  });

  factory SquadListItem.fromJson(Map<String, dynamic> json) => SquadListItem(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        sprintGoal: json['sprint_goal'] as String?,
        deadline: _parseDate(json['deadline']),
        daysRemaining: (json['days_remaining'] as num?)?.toInt(),
        memberCount: (json['member_count'] as num?)?.toInt() ?? 0,
        maxMembers: (json['max_members'] as num?)?.toInt() ?? 0,
        myRole: json['my_role'] as String?,
      );

  final String id;
  final String name;

  /// 冲刺目标（可空——缺失不渲染该行，不造占位文案）。
  final String? sprintGoal;

  /// 冲刺截止（可空；列表仅含冲刺周期内的小队，正常非空）。
  final DateTime? deadline;

  /// 距截止剩余天数（服务端口径，客户端不自算）。
  final int? daysRemaining;
  final int memberCount;
  final int maxMembers;

  /// 当前用户在小队中的角色（非成员为 null）。
  final String? myRole;
}

/// 冲刺小队详情（`GET /community/squads/{id}`）。
class SquadInfo {
  const SquadInfo({
    required this.id,
    required this.name,
    required this.memberCount,
    required this.maxMembers,
    required this.isPublic,
    required this.createdAt,
    this.description,
    this.focusTags = const [],
    this.deadline,
    this.sprintGoal,
    this.daysRemaining,
    this.myRole,
  });

  factory SquadInfo.fromJson(Map<String, dynamic> json) {
    final tags = (json['focus_tags'] as List<dynamic>? ?? const [])
        .whereType<String>()
        .toList();
    return SquadInfo(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      description: json['description'] as String?,
      focusTags: tags,
      deadline: _parseDate(json['deadline']),
      sprintGoal: json['sprint_goal'] as String?,
      maxMembers: (json['max_members'] as num?)?.toInt() ?? 0,
      isPublic: json['is_public'] == true,
      memberCount: (json['member_count'] as num?)?.toInt() ?? 0,
      daysRemaining: (json['days_remaining'] as num?)?.toInt(),
      myRole: json['my_role'] as String?,
      createdAt: _parseDate(json['created_at']),
    );
  }

  final String id;
  final String name;
  final String? description;
  final List<String> focusTags;
  final DateTime? deadline;
  final String? sprintGoal;
  final int maxMembers;
  final bool isPublic;
  final int memberCount;
  final int? daysRemaining;
  final String? myRole;
  final DateTime? createdAt;
}

DateTime? _parseDate(Object? raw) =>
    raw is String ? DateTime.tryParse(raw)?.toUtc() : null;

/// 创建冲刺小队的入参（deadline 必填，须为未来时间——服务端校验）。
class SquadCreateInput {
  const SquadCreateInput({
    required this.name,
    required this.deadline,
    this.sprintGoal,
  });

  final String name;
  final String? sprintGoal;
  final DateTime deadline;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'name': name,
        'deadline': deadline.toIso8601String(),
        if (sprintGoal != null && sprintGoal!.trim().isNotEmpty)
          'sprint_goal': sprintGoal!.trim(),
      };
}
