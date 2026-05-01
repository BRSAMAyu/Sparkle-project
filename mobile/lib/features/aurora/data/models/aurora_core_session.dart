import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';

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
}

class AuroraCalibrationResult {
  const AuroraCalibrationResult({
    required this.updatesApplied,
    required this.summary,
    required this.scopeCompleted,
    required this.strategyChanges,
    required this.sessionId,
    required this.completedAt,
  });

  factory AuroraCalibrationResult.fromJson(Map<String, dynamic> json) {
    return AuroraCalibrationResult(
      updatesApplied: (json['updates_applied'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .toList(),
      summary: json['summary'] as String? ?? '',
      scopeCompleted: json['scope_completed'] as String? ?? '',
      strategyChanges: (json['strategy_changes'] as List<dynamic>? ?? const [])
          .map((e) => '$e')
          .where((e) => e.isNotEmpty)
          .toList(),
      sessionId: json['session_id'] as String? ?? '',
      completedAt: json['completed_at'] as String? ?? '',
    );
  }

  final List<Map<String, dynamic>> updatesApplied;
  final String summary;
  final String scopeCompleted;
  final List<String> strategyChanges;
  final String sessionId;
  final String completedAt;
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
    final rawGroups = json['pending_option_groups'] as List<dynamic>? ?? const [];
    return AuroraCoreSession(
      sessionId: json['session_id'] as String? ?? '',
      userId: json['user_id'] as String? ?? '',
      conversationId: json['conversation_id'] as String?,
      surface: json['surface'] as String? ?? 'aurora_modeling',
      status: json['status'] as String? ?? 'active',
      stage: json['stage'] as String? ?? 'declare',
      scope: json['scope'] as String? ?? '',
      sessionType: json['session_type'] as String? ?? 'user_initiated',
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
  final List<AuroraCoreMessage> messages;
  final AuroraCalibrationResult? calibrationResult;
  final int userTurnCount;
  final int auroraMessageCount;
  final List<AuroraPredictedReplyGroup> pendingOptionGroups;
  final String createdAt;
  final String lastActivityAt;
  final String expiresAt;

  bool get isActive => status == 'active';
  bool get isCompleted => status == 'completed';
  bool get isAbandoned => status == 'abandoned';
  bool get isExited => status != 'active';

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
}
