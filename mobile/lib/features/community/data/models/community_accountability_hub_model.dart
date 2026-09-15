class CommunityAccountabilityHub {
  const CommunityAccountabilityHub({
    required this.myCommitments,
    required this.partnerProgress,
    required this.sharedGoals,
    required this.squadRisks,
    required this.helpable,
  });

  factory CommunityAccountabilityHub.fromJson(Map<String, dynamic> json) =>
      CommunityAccountabilityHub(
        myCommitments: _list(json['my_commitments'])
            .map(CommitmentCardPayload.fromJson)
            .toList(growable: false),
        partnerProgress: _list(json['partner_progress'])
            .map(PartnerProgressItem.fromJson)
            .toList(growable: false),
        sharedGoals: _list(json['shared_goals'])
            .map(SharedGoalItem.fromJson)
            .toList(growable: false),
        squadRisks: _list(json['squad_risks'])
            .map(SquadRiskItem.fromJson)
            .toList(growable: false),
        helpable: _list(json['helpable'])
            .map(HelpableItem.fromJson)
            .toList(growable: false),
      );

  final List<CommitmentCardPayload> myCommitments;
  final List<PartnerProgressItem> partnerProgress;
  final List<SharedGoalItem> sharedGoals;
  final List<SquadRiskItem> squadRisks;
  final List<HelpableItem> helpable;

  bool get isEmpty =>
      myCommitments.isEmpty &&
      partnerProgress.isEmpty &&
      sharedGoals.isEmpty &&
      squadRisks.isEmpty &&
      helpable.isEmpty;

  CommunityAccountabilityHub copyWith({
    List<CommitmentCardPayload>? myCommitments,
    List<PartnerProgressItem>? partnerProgress,
    List<SharedGoalItem>? sharedGoals,
    List<SquadRiskItem>? squadRisks,
    List<HelpableItem>? helpable,
  }) =>
      CommunityAccountabilityHub(
        myCommitments: myCommitments ?? this.myCommitments,
        partnerProgress: partnerProgress ?? this.partnerProgress,
        sharedGoals: sharedGoals ?? this.sharedGoals,
        squadRisks: squadRisks ?? this.squadRisks,
        helpable: helpable ?? this.helpable,
      );
}

class CommitmentCardPayload {
  const CommitmentCardPayload({
    required this.id,
    required this.summary,
    required this.progress,
    required this.status,
    required this.allowPartnerReminders,
    this.dueAt,
    this.witnessNames = const [],
    this.successCriteria = const [],
    this.milestones = const [],
    this.evidenceRefs = const [],
  });

  factory CommitmentCardPayload.fromJson(Map<String, dynamic> json) =>
      CommitmentCardPayload(
        id: json['id']?.toString() ?? '',
        summary: json['summary']?.toString() ?? '',
        dueAt: _date(json['due_at']),
        witnessNames: _stringList(json['witness_names']),
        progress: _double(json['progress']).clamp(0.0, 1.0),
        status: json['status']?.toString() ?? 'active',
        successCriteria: _stringList(json['success_criteria']),
        milestones: _stringList(json['milestones']),
        evidenceRefs: _stringList(json['evidence_refs']),
        allowPartnerReminders: json['allow_partner_reminders'] != false,
      );

  final String id;
  final String summary;
  final DateTime? dueAt;
  final List<String> witnessNames;
  final double progress;
  final String status;
  final List<String> successCriteria;
  final List<String> milestones;
  final List<String> evidenceRefs;
  final bool allowPartnerReminders;

  CommitmentCardPayload copyWith({
    bool? allowPartnerReminders,
    double? progress,
    String? status,
  }) =>
      CommitmentCardPayload(
        id: id,
        summary: summary,
        dueAt: dueAt,
        witnessNames: witnessNames,
        progress: progress ?? this.progress,
        status: status ?? this.status,
        successCriteria: successCriteria,
        milestones: milestones,
        evidenceRefs: evidenceRefs,
        allowPartnerReminders:
            allowPartnerReminders ?? this.allowPartnerReminders,
      );
}

class PartnerProgressItem {
  const PartnerProgressItem({
    required this.partnershipId,
    required this.partnerId,
    required this.partnerName,
    required this.goalSummary,
    required this.todayDone,
    required this.myTodayDone,
    required this.weeklyProgress,
    this.lastCheckinAt,
  });

  factory PartnerProgressItem.fromJson(Map<String, dynamic> json) =>
      PartnerProgressItem(
        partnershipId: json['partnership_id']?.toString() ?? '',
        partnerId: json['partner_id']?.toString() ?? '',
        partnerName: json['partner_name']?.toString() ?? '',
        goalSummary: json['goal_summary']?.toString() ?? '',
        todayDone: json['today_done'] == true,
        myTodayDone: json['my_today_done'] == true,
        weeklyProgress: _double(json['weekly_progress']).clamp(0.0, 1.0),
        lastCheckinAt: _date(json['last_checkin_at']),
      );

  final String partnershipId;
  final String partnerId;
  final String partnerName;
  final String goalSummary;
  final bool todayDone;
  final bool myTodayDone;
  final double weeklyProgress;
  final DateTime? lastCheckinAt;
}

class SharedGoalItem {
  const SharedGoalItem({
    required this.id,
    required this.title,
    required this.progress,
    required this.memberNames,
    required this.status,
  });

  factory SharedGoalItem.fromJson(Map<String, dynamic> json) => SharedGoalItem(
        id: json['id']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        progress: _double(json['progress']).clamp(0.0, 1.0),
        memberNames: _stringList(json['member_names']),
        status: json['status']?.toString() ?? 'active',
      );

  final String id;
  final String title;
  final double progress;
  final List<String> memberNames;
  final String status;
}

class SquadRiskItem {
  const SquadRiskItem({
    required this.partnershipId,
    required this.memberName,
    required this.reason,
    required this.severity,
    required this.suggestedAction,
  });

  factory SquadRiskItem.fromJson(Map<String, dynamic> json) => SquadRiskItem(
        partnershipId: json['partnership_id']?.toString() ?? '',
        memberName: json['member_name']?.toString() ?? '',
        reason: json['reason']?.toString() ?? '',
        severity: json['severity']?.toString() ?? 'medium',
        suggestedAction:
            json['suggested_action']?.toString() ?? 'send_gentle_checkin',
      );

  final String partnershipId;
  final String memberName;
  final String reason;
  final String severity;
  final String suggestedAction;
}

class HelpableItem {
  const HelpableItem({
    required this.partnershipId,
    required this.memberName,
    required this.need,
    required this.action,
  });

  factory HelpableItem.fromJson(Map<String, dynamic> json) => HelpableItem(
        partnershipId: json['partnership_id']?.toString() ?? '',
        memberName: json['member_name']?.toString() ?? '',
        need: json['need']?.toString() ?? '',
        action: json['action']?.toString() ?? 'encourage',
      );

  final String partnershipId;
  final String memberName;
  final String need;
  final String action;
}

List<Map<String, dynamic>> _list(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<Map<dynamic, dynamic>>()
      .map(Map<String, dynamic>.from)
      .toList(growable: false);
}

List<String> _stringList(Object? value) {
  if (value is! List) return const [];
  return value.map((item) => item.toString()).toList(growable: false);
}

DateTime? _date(Object? value) {
  if (value == null) return null;
  return DateTime.tryParse(value.toString());
}

double _double(Object? value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}
