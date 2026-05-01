import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';

class AuroraCoreSessionEntryReason {
  const AuroraCoreSessionEntryReason({
    required this.triggerSource,
    required this.observedSignals,
    required this.suggestedAgendaPreview,
    required this.whyNow,
    required this.estimatedMinutes,
  });

  factory AuroraCoreSessionEntryReason.fromJson(Map<String, dynamic> json) {
    return AuroraCoreSessionEntryReason(
      triggerSource: json['trigger_source'] as String? ?? 'user_initiated',
      observedSignals: (json['observed_signals'] as List<dynamic>? ?? const [])
          .map((e) => '$e')
          .where((e) => e.trim().isNotEmpty)
          .toList(),
      suggestedAgendaPreview:
          (json['suggested_agenda_preview'] as List<dynamic>? ?? const [])
              .map((e) => '$e')
              .where((e) => e.trim().isNotEmpty)
              .toList(),
      whyNow: json['why_now'] as String? ?? '',
      estimatedMinutes: (json['estimated_minutes'] as num?)?.toInt() ?? 4,
    );
  }

  factory AuroraCoreSessionEntryReason.fromSnapshot({
    required AuroraControlSurfaceSnapshot snapshot,
    required String triggerSource,
    List<String> extraSignals = const [],
    List<String> agendaPreview = const [],
  }) {
    final wake = snapshot.wakeEligibility;
    final signals = <String>[
      snapshot.summary,
      ...snapshot.facets.expand((facet) => facet.signals.take(2)),
      ...extraSignals,
    ].where((item) => item.trim().isNotEmpty).take(5).toList();
    final agenda = <String>[
      if (wake.suggestedScope.trim().isNotEmpty) wake.suggestedScope,
      ...agendaPreview,
      if (snapshot.topPredictedGroup?.question.trim().isNotEmpty ?? false)
        snapshot.topPredictedGroup!.question,
    ].where((item) => item.trim().isNotEmpty).take(4).toList();
    final why = switch (snapshot.overallStatus) {
      'risk_found' => '已经出现可能影响接下来行动的风险信号',
      'needs_confirm' => '有几个判断还没有被你确认，继续推进前最好先对齐',
      'calibration_available' => '现在有足够信号做一次短校准',
      _ => '状态发生了变化，适合现在确认一下',
    };
    return AuroraCoreSessionEntryReason(
      triggerSource: triggerSource,
      observedSignals: signals.isEmpty ? [snapshot.overallStatus] : signals,
      suggestedAgendaPreview:
          agenda.isEmpty ? const ['确认我观察到的信号', '校准接下来的策略'] : agenda,
      whyNow: why,
      estimatedMinutes: (wake.estimatedDurationSec / 60).round().clamp(1, 10),
    );
  }

  final String triggerSource;
  final List<String> observedSignals;
  final List<String> suggestedAgendaPreview;
  final String whyNow;
  final int estimatedMinutes;

  Map<String, dynamic> toJson() => {
        'trigger_source': triggerSource,
        'observed_signals': observedSignals,
        'suggested_agenda_preview': suggestedAgendaPreview,
        'why_now': whyNow,
        'estimated_minutes': estimatedMinutes,
      };
}

class AuroraCoreMessage {
  const AuroraCoreMessage({
    required this.role,
    required this.content,
    required this.stage,
    required this.timestamp,
    this.optionId,
    this.semanticValue,
    this.isFreeform = false,
  });

  factory AuroraCoreMessage.fromJson(Map<String, dynamic> json) {
    return AuroraCoreMessage(
      role: json['role'] as String? ?? 'aurora',
      content: json['content'] as String? ?? '',
      stage: json['stage'] as String? ?? 'declare',
      timestamp: json['timestamp'] as String? ?? '',
      optionId: json['option_id'] as String?,
      semanticValue: json['semantic_value'] as String?,
      isFreeform: json['is_freeform'] as bool? ?? false,
    );
  }

  final String role; // aurora | user
  final String content;
  final String stage;
  final String timestamp;
  final String? optionId;
  final String? semanticValue;
  final bool isFreeform;

  bool get isAurora => role == 'aurora';
  bool get isUser => role == 'user';

  Map<String, dynamic> toJson() => {
        'role': role,
        'content': content,
        'stage': stage,
        'timestamp': timestamp,
        'option_id': optionId,
        'semantic_value': semanticValue,
        'is_freeform': isFreeform,
      };
}

class AuroraCalibrationResult {
  const AuroraCalibrationResult({
    required this.updatesApplied,
    required this.summary,
    required this.userVisibleSummary,
    required this.scopeCompleted,
    required this.strategyChanges,
    required this.statePatches,
    required this.nextChanges,
    required this.sessionId,
    required this.completedAt,
  });

  factory AuroraCalibrationResult.fromJson(Map<String, dynamic> json) {
    return AuroraCalibrationResult(
      updatesApplied: (json['updates_applied'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .toList(),
      summary: json['summary'] as String? ?? '',
      userVisibleSummary: (json['user_visible_summary'] as String?) ??
          (json['summary'] as String?) ??
          '',
      scopeCompleted: json['scope_completed'] as String? ?? '',
      strategyChanges: (json['strategy_changes'] as List<dynamic>? ?? const [])
          .map((e) => '$e')
          .where((e) => e.isNotEmpty)
          .toList(),
      statePatches: (json['state_patches'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .toList(),
      nextChanges: (json['next_changes'] as List<dynamic>? ?? const [])
          .map((e) => '$e')
          .where((e) => e.isNotEmpty)
          .toList(),
      sessionId: json['session_id'] as String? ?? '',
      completedAt: json['completed_at'] as String? ?? '',
    );
  }

  final List<Map<String, dynamic>> updatesApplied;
  final String summary;
  final String userVisibleSummary;
  final String scopeCompleted;
  final List<String> strategyChanges;
  final List<Map<String, dynamic>> statePatches;
  final List<String> nextChanges;
  final String sessionId;
  final String completedAt;

  Map<String, dynamic> toJson() => {
        'updates_applied': updatesApplied,
        'summary': summary,
        'user_visible_summary': userVisibleSummary,
        'scope_completed': scopeCompleted,
        'strategy_changes': strategyChanges,
        'state_patches': statePatches,
        'next_changes': nextChanges,
        'session_id': sessionId,
        'completed_at': completedAt,
      };
}

class AuroraCoreSession {
  const AuroraCoreSession({
    required this.sessionId,
    required this.userId,
    required this.conversationId,
    required this.surface,
    required this.status,
    required this.stage,
    required this.scope,
    required this.sessionType,
    required this.entryReason,
    required this.resumeToken,
    required this.messages,
    required this.calibrationResult,
    required this.userTurnCount,
    required this.auroraMessageCount,
    required this.pendingOptionGroups,
    required this.createdAt,
    required this.lastActivityAt,
    required this.expiresAt,
  });

  factory AuroraCoreSession.fromJson(Map<String, dynamic> json) {
    final rawMessages = json['messages'] as List<dynamic>? ?? const [];
    final rawResult = json['calibration_result'];
    final rawGroups =
        json['pending_option_groups'] as List<dynamic>? ?? const [];
    final rawEntryReason = json['entry_reason'];
    return AuroraCoreSession(
      sessionId: json['session_id'] as String? ?? '',
      userId: json['user_id'] as String? ?? '',
      conversationId: json['conversation_id'] as String?,
      surface: json['surface'] as String? ?? 'aurora_modeling',
      status: json['status'] as String? ?? 'active',
      stage: json['stage'] as String? ?? 'declare',
      scope: json['scope'] as String? ?? '',
      sessionType: json['session_type'] as String? ?? 'user_initiated',
      entryReason: rawEntryReason is Map<String, dynamic>
          ? AuroraCoreSessionEntryReason.fromJson(rawEntryReason)
          : rawEntryReason is Map
              ? AuroraCoreSessionEntryReason.fromJson(
                  Map<String, dynamic>.from(rawEntryReason),
                )
              : null,
      resumeToken: json['resume_token'] as String? ?? '',
      messages: rawMessages
          .whereType<Map<String, dynamic>>()
          .map(AuroraCoreMessage.fromJson)
          .toList(),
      calibrationResult: rawResult is Map<String, dynamic>
          ? AuroraCalibrationResult.fromJson(rawResult)
          : null,
      userTurnCount: (json['user_turn_count'] as num?)?.toInt() ?? 0,
      auroraMessageCount: (json['aurora_message_count'] as num?)?.toInt() ?? 0,
      pendingOptionGroups: rawGroups
          .whereType<Map<String, dynamic>>()
          .map(AuroraPredictedReplyGroup.fromJson)
          .toList(),
      createdAt: json['created_at'] as String? ?? '',
      lastActivityAt: json['last_activity_at'] as String? ?? '',
      expiresAt: json['expires_at'] as String? ?? '',
    );
  }

  final String sessionId;
  final String userId;
  final String? conversationId;
  final String surface;
  final String status; // active | completed | abandoned | expired
  final String stage;
  final String scope;
  final String sessionType;
  final AuroraCoreSessionEntryReason? entryReason;
  final String resumeToken;
  final List<AuroraCoreMessage> messages;
  final AuroraCalibrationResult? calibrationResult;
  final int userTurnCount;
  final int auroraMessageCount;
  final List<AuroraPredictedReplyGroup> pendingOptionGroups;
  final String createdAt;
  final String lastActivityAt;
  final String expiresAt;

  bool get isActive => status == 'active';
  bool get isPaused => status == 'paused';
  bool get isCompleted => status == 'completed';
  bool get isAbandoned => status == 'abandoned';
  bool get isExpired => status == 'expired';
  bool get isResumable => (isActive || isPaused) && resumeToken.isNotEmpty;
  bool get canInteract => isActive;
  bool get isExited => isCompleted || isAbandoned || isExpired;

  /// Aurora messages only (for display in session view).
  List<AuroraCoreMessage> get auroraMessages =>
      messages.where((m) => m.isAurora).toList();

  /// The latest Aurora message.
  AuroraCoreMessage? get latestAuroraMessage =>
      auroraMessages.isNotEmpty ? auroraMessages.last : null;

  /// Top pending option group (if any).
  AuroraPredictedReplyGroup? get topOptionGroup =>
      pendingOptionGroups.isNotEmpty ? pendingOptionGroups.first : null;

  int get turnsRemaining => (6 - userTurnCount).clamp(0, 6);

  Map<String, dynamic> toJson() => {
        'session_id': sessionId,
        'user_id': userId,
        'conversation_id': conversationId,
        'surface': surface,
        'status': status,
        'stage': stage,
        'scope': scope,
        'session_type': sessionType,
        'entry_reason': entryReason?.toJson(),
        'resume_token': resumeToken,
        'messages': messages.map((message) => message.toJson()).toList(),
        'calibration_result': calibrationResult?.toJson(),
        'user_turn_count': userTurnCount,
        'aurora_message_count': auroraMessageCount,
        'pending_option_groups':
            pendingOptionGroups.map((group) => group.toJson()).toList(),
        'created_at': createdAt,
        'last_activity_at': lastActivityAt,
        'expires_at': expiresAt,
      };
}
