class AuroraComebackContext {
  const AuroraComebackContext({
    required this.comebackKind,
    required this.title,
    required this.message,
    required this.shouldShowMessage,
    required this.lastActiveAt,
    required this.inactiveMinutes,
    required this.daysAway,
    required this.daysRemaining,
    required this.subject,
    required this.nextTaskTitle,
    required this.recentTaskSummary,
    required this.lightRestartSuggestion,
    required this.planId,
    required this.conversationId,
    required this.lastMessageId,
    required this.topicSummary,
    required this.pendingQuestion,
    required this.activeCoreSession,
    required this.resumeToken,
    required this.unfinishedItems,
    required this.calendarNote,
    this.goalState = const AuroraComebackGoalState.empty(),
    this.planExpired = false,
    this.staleFocus = false,
    this.nextTaskOverdueDays = 0,
  });

  const AuroraComebackContext.empty()
      : comebackKind = '',
        title = '',
        message = '',
        shouldShowMessage = false,
        lastActiveAt = '',
        inactiveMinutes = 0,
        daysAway = 0,
        daysRemaining = 0,
        subject = '',
        nextTaskTitle = '',
        recentTaskSummary = '',
        lightRestartSuggestion = '',
        planId = '',
        conversationId = '',
        lastMessageId = '',
        topicSummary = '',
        pendingQuestion = '',
        activeCoreSession = const <String, dynamic>{},
        resumeToken = '',
        unfinishedItems = const [],
        calendarNote = '',
        goalState = const AuroraComebackGoalState.empty(),
        planExpired = false,
        staleFocus = false,
        nextTaskOverdueDays = 0;

  factory AuroraComebackContext.fromJson(Map<String, dynamic> json) =>
      AuroraComebackContext(
        comebackKind: _asString(json['comeback_kind']),
        title: _asString(json['title']),
        message: _asString(json['message']),
        shouldShowMessage: _asBool(json['should_show_message']),
        lastActiveAt: _asString(json['last_active_at']),
        inactiveMinutes: _asInt(json['inactive_minutes']),
        daysAway: _asInt(json['days_away']),
        daysRemaining: _asInt(json['days_remaining']),
        subject: _asString(json['subject']),
        nextTaskTitle: _asString(json['next_task_title']),
        recentTaskSummary: _asString(json['recent_task_summary']),
        lightRestartSuggestion: _asString(json['light_restart_suggestion']),
        planId: _asString(json['plan_id']),
        conversationId: _asString(json['conversation_id']),
        lastMessageId: _asString(json['last_message_id']),
        topicSummary: _asString(json['topic_summary']),
        pendingQuestion: _asString(json['pending_question']),
        activeCoreSession: _asStringMap(json['active_core_session']),
        resumeToken: _asString(json['resume_token']),
        unfinishedItems: _asItems(json['unfinished_items']),
        calendarNote: _asString(json['calendar_note']),
        goalState: AuroraComebackGoalState.fromJson(json['goal_state']),
        planExpired: _asBool(json['plan_expired']),
        staleFocus: _asBool(json['stale_focus']),
        nextTaskOverdueDays: _asInt(json['next_task_overdue_days']),
      );

  final String comebackKind;
  final String title;
  final String message;
  final bool shouldShowMessage;
  final String lastActiveAt;
  final int inactiveMinutes;
  final int daysAway;
  final int daysRemaining;
  final String subject;
  final String nextTaskTitle;
  final String recentTaskSummary;
  final String lightRestartSuggestion;
  final String planId;
  final String conversationId;
  final String lastMessageId;
  final String topicSummary;
  final String pendingQuestion;
  final Map<String, dynamic> activeCoreSession;
  final String resumeToken;
  final List<AuroraComebackItem> unfinishedItems;
  final String calendarNote;

  /// 用户真实目标状态（引擎读侧真源投影，A-07）。空对象 = 引擎无目标可呈报。
  final AuroraComebackGoalState goalState;

  /// 计划原定窗口已结束——UI 不得按"当前计划"口吻呈报。
  final bool planExpired;

  /// 焦点任务已陈旧（逾期 ≥3 天或计划过期）——不得呈现为"当前最优步"。
  final bool staleFocus;
  final int nextTaskOverdueDays;

  bool get hasContent =>
      message.isNotEmpty ||
      conversationId.isNotEmpty ||
      resumeToken.isNotEmpty ||
      unfinishedItems.isNotEmpty;

  bool get shouldShowBanner =>
      shouldShowMessage || resumeToken.isNotEmpty || unfinishedItems.isNotEmpty;

  bool get hasActiveCoreSession =>
      resumeToken.isNotEmpty || activeCoreSession.isNotEmpty;
}

class AuroraComebackGoalState {
  const AuroraComebackGoalState({
    required this.goalId,
    required this.title,
    required this.status,
    required this.progress,
    required this.ledgerCompleted,
    required this.ledgerTotal,
  });

  const AuroraComebackGoalState.empty()
      : goalId = '',
        title = '',
        status = '',
        progress = null,
        ledgerCompleted = 0,
        ledgerTotal = 0;

  factory AuroraComebackGoalState.fromJson(dynamic raw) {
    if (raw is! Map) {
      return const AuroraComebackGoalState.empty();
    }
    final json = Map<String, dynamic>.from(raw);
    final ledger = json['ledger'];
    final ledgerMap = ledger is Map<String, dynamic>
        ? ledger
        : ledger is Map
            ? Map<String, dynamic>.from(ledger)
            : const <String, dynamic>{};
    final progress = json['progress'];
    return AuroraComebackGoalState(
      goalId: _asString(json['goal_id']),
      title: _asString(json['title']),
      status: _asString(json['status']),
      progress: progress is num ? progress.toDouble() : null,
      ledgerCompleted: _asInt(ledgerMap['completed']),
      ledgerTotal: _asInt(ledgerMap['total']),
    );
  }

  final String goalId;
  final String title;
  final String status;

  /// 目标真源 progress 读数（可能因上游写入链路停在 0，如实呈报）。
  final double? progress;

  /// 任务账本口径的诚实进度（completed/total），与任务板同行同数。
  final int ledgerCompleted;
  final int ledgerTotal;

  bool get hasContent => goalId.isNotEmpty || title.isNotEmpty;

  bool get hasLedger => ledgerTotal > 0;
}

class AuroraComebackItem {
  const AuroraComebackItem({
    required this.type,
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    required this.route,
    required this.resumeToken,
  });

  factory AuroraComebackItem.fromJson(Map<String, dynamic> json) =>
      AuroraComebackItem(
        type: _asString(json['type']),
        title: _asString(json['title']),
        subtitle: _asString(json['subtitle']),
        actionLabel: _asString(json['action_label']),
        route: _asString(json['route']),
        resumeToken: _asString(json['resume_token']),
      );

  final String type;
  final String title;
  final String subtitle;
  final String actionLabel;
  final String route;
  final String resumeToken;
}

String _asString(dynamic value) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? '' : text;
}

int _asInt(dynamic value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value) ?? 0;
  }
  return 0;
}

bool _asBool(dynamic value) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  if (value is String) {
    final normalized = value.trim().toLowerCase();
    return normalized == 'true' || normalized == '1' || normalized == 'yes';
  }
  return false;
}

Map<String, dynamic> _asStringMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return Map<String, dynamic>.from(value);
  }
  if (value is Map) {
    return Map<String, dynamic>.from(value);
  }
  return const <String, dynamic>{};
}

List<AuroraComebackItem> _asItems(dynamic value) {
  if (value is! List) {
    return const [];
  }
  return value
      .whereType<Map<Object?, Object?>>()
      .map(
        (item) => AuroraComebackItem.fromJson(
          Map<String, dynamic>.from(item),
        ),
      )
      .where((item) => item.title.isNotEmpty || item.subtitle.isNotEmpty)
      .toList(growable: false);
}
