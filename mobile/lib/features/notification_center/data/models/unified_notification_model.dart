import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/utils/formatters.dart';

/// Unified notification model combining system and intervention notifications
class UnifiedNotification {
  UnifiedNotification({
    required this.id,
    required this.sourceType,
    required this.title,
    required this.content,
    required this.priority,
    required this.isRead,
    required this.createdAt,
    this.type,
    this.readAt,
    this.metadata = const {},
  });

  factory UnifiedNotification.fromJson(Map<String, dynamic> json) =>
      UnifiedNotification(
        id: json['id'] as String,
        sourceType: _normalizeSourceType(
          json['source_type'] as String?,
          json['type'] as String?,
        ),
        title: json['title'] as String,
        content: json['content'] as String,
        type: json['type'] as String?,
        priority: json['priority'] as String? ?? 'medium',
        isRead: json['is_read'] as bool? ?? false,
        createdAt: DateTime.parse(json['created_at'] as String),
        readAt: json['read_at'] != null
            ? DateTime.parse(json['read_at'] as String)
            : null,
        metadata: _normalizeMetadata(json),
      );
  final String id;
  final String sourceType; // 'system' or 'intervention'
  final String title;
  final String content;
  final String? type;
  final String priority; // 'low', 'medium', 'high'
  final bool isRead;
  final DateTime createdAt;
  final DateTime? readAt;
  final Map<String, dynamic> metadata;

  static String _normalizeSourceType(String? sourceType, String? type) {
    if (sourceType == 'intervention') {
      return 'intervention';
    }
    final normalizedType = (type ?? '').trim().toLowerCase();
    if (normalizedType == 'intervention' ||
        normalizedType == 'intervention_push') {
      return 'intervention';
    }
    return sourceType ?? 'system';
  }

  static Map<String, dynamic> _normalizeMetadata(Map<String, dynamic> json) {
    final metadata = json['metadata'];
    if (metadata is Map<String, dynamic>) {
      return metadata;
    }
    if (metadata is Map) {
      return Map<String, dynamic>.from(metadata);
    }
    final data = json['data'];
    if (data is Map<String, dynamic>) {
      return data;
    }
    if (data is Map) {
      return Map<String, dynamic>.from(data);
    }
    return const {};
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'source_type': sourceType,
        'title': title,
        'content': content,
        if (type != null) 'type': type,
        'priority': priority,
        'is_read': isRead,
        'created_at': createdAt.toIso8601String(),
        if (readAt != null) 'read_at': readAt!.toIso8601String(),
        'metadata': metadata,
      };

  /// Get icon based on notification type
  String get icon {
    if (sourceType == 'intervention') {
      switch (intentType) {
        case 'micro_restart':
          return '🪜';
        case 'concept_gap_focus':
          return '🧠';
        case 'overload_lighten_path':
          return '🌿';
        case 'plan_path_soft_replan':
          return '🧭';
        case 'recover_self_efficacy':
          return '✨';
        default:
          return '⚠️';
      }
    }

    if (sourceType == 'push') {
      switch (pushCategory) {
        case 'commitment_follow_up':
          return '⏰';
        case 'engagement_recovery':
          return '🌱';
        default:
          return '📨';
      }
    }

    // System notification icons
    switch (type) {
      case 'plan_archived':
      case 'plan_deleted':
      case 'plan_restored':
        return '📋';
      case 'settings_updated':
        return '⚙️';
      case 'memory_cleanup':
        return '🧹';
      case 'achievement':
        return '🏆';
      default:
        return '🔔';
    }
  }

  /// Get relative time (e.g., "5 minutes ago")
  String get relativeTime => Formatters.formatRelativeTime(createdAt);

  /// Get priority color
  int get priorityColor {
    switch (priority) {
      case 'high':
        return 0xFFFF5252; // Red
      case 'medium':
        return 0xFFFFB74D; // Orange
      case 'low':
      default:
        return 0xFF81C784; // Green
    }
  }

  /// Check if notification is from today
  bool get isToday {
    final now = DateTime.now();
    return createdAt.year == now.year &&
        createdAt.month == now.month &&
        createdAt.day == now.day;
  }

  /// Check if notification is from this week
  bool get isThisWeek {
    final now = DateTime.now();
    final weekAgo = now.subtract(const Duration(days: 7));
    return createdAt.isAfter(weekAgo);
  }

  bool get isIntervention => sourceType == 'intervention';
  bool get isPush => sourceType == 'push';
  bool get isAccountabilityStruggleAlert =>
      type == 'accountability_struggle_alert' ||
      metadata['kind'] == 'accountability_struggle_alert';

  String? get intentType => metadata['intent_type'] as String?;

  String? get suggestedStep =>
      metadata['suggested_step'] as String? ??
      _contextVariables['suggested_step'] as String?;

  String? get planId => metadata['plan_id'] as String?;

  String? get recordId => metadata['record_id'] as String?;

  String? get deliveryChannel => metadata['delivery_channel'] as String?;
  String? get pushCategory => metadata['category'] as String?;
  String? get evidenceToken => metadata['evidence_token'] as String?;
  String? get retractableUntil => metadata['retractable_until'] as String?;
  String? get pushStatus => metadata['push_status'] as String?;

  String? get interactionState =>
      metadata['client_intervention_state'] as String? ??
      metadata['acceptance_status'] as String? ??
      metadata['status'] as String?;

  String? get outcomeStatus => metadata['outcome_status'] as String?;

  Map<String, dynamic> get outcomeEvidence {
    final raw = metadata['outcome_evidence'];
    if (raw is Map<String, dynamic>) {
      return raw;
    }
    if (raw is Map) {
      return Map<String, dynamic>.from(raw);
    }
    return const {};
  }

  Map<String, dynamic> get parameterCompilation {
    final raw = metadata['parameter_compilation'];
    if (raw is Map<String, dynamic>) {
      return raw;
    }
    if (raw is Map) {
      return Map<String, dynamic>.from(raw);
    }
    return const {};
  }

  bool get canAcceptIntervention =>
      isIntervention &&
      interactionState != 'accepted' &&
      interactionState != 'acted' &&
      interactionState != 'dismissed';

  bool get canActOnIntervention =>
      isIntervention &&
      interactionState != 'acted' &&
      interactionState != 'dismissed';

  bool get canDisablePushCategory => isPush && pushCategory != null;

  bool get canSendAccountabilityEncouragement =>
      isAccountabilityStruggleAlert &&
      metadata['encouragement_status'] != 'sent';

  String? get accountabilityTargetName => metadata['target_name'] as String?;

  String get accountabilityEncouragementLabel {
    final action = metadata['primary_action'];
    if (action is Map<String, dynamic>) {
      final label = action['label'] as String?;
      if (label != null && label.trim().isNotEmpty) {
        return label.trim();
      }
    }
    return I18nService.instance.isChinese ? '发个鼓励' : 'Send encouragement';
  }

  String get previewText {
    final step = suggestedStep;
    if (isIntervention && step != null && step.trim().isNotEmpty) {
      return I18nService.instance.isChinese ? '$content\n建议动作：$step' : '$content\nSuggested action: $step';
    }
    return content;
  }

  Map<String, dynamic> get _contextVariables {
    final raw = metadata['context_variables'];
    if (raw is Map<String, dynamic>) {
      return raw;
    }
    if (raw is Map) {
      return Map<String, dynamic>.from(raw);
    }
    return const {};
  }

  UnifiedNotification copyWith({
    String? id,
    String? sourceType,
    String? title,
    String? content,
    String? type,
    String? priority,
    bool? isRead,
    DateTime? createdAt,
    DateTime? readAt,
    Map<String, dynamic>? metadata,
  }) =>
      UnifiedNotification(
        id: id ?? this.id,
        sourceType: sourceType ?? this.sourceType,
        title: title ?? this.title,
        content: content ?? this.content,
        type: type ?? this.type,
        priority: priority ?? this.priority,
        isRead: isRead ?? this.isRead,
        createdAt: createdAt ?? this.createdAt,
        readAt: readAt ?? this.readAt,
        metadata: metadata ?? this.metadata,
      );
}
