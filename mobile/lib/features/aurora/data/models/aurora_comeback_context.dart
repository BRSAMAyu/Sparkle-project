class AuroraComebackContext {
  const AuroraComebackContext({
    required this.title,
    required this.message,
    required this.daysAway,
    required this.daysRemaining,
    required this.subject,
    required this.nextTaskTitle,
    required this.recentTaskSummary,
    required this.lightRestartSuggestion,
    required this.planId,
  });

  const AuroraComebackContext.empty()
      : title = '',
        message = '',
        daysAway = 0,
        daysRemaining = 0,
        subject = '',
        nextTaskTitle = '',
        recentTaskSummary = '',
        lightRestartSuggestion = '',
        planId = '';

  factory AuroraComebackContext.fromJson(Map<String, dynamic> json) =>
      AuroraComebackContext(
        title: _asString(json['title']),
        message: _asString(json['message']),
        daysAway: _asInt(json['days_away']),
        daysRemaining: _asInt(json['days_remaining']),
        subject: _asString(json['subject']),
        nextTaskTitle: _asString(json['next_task_title']),
        recentTaskSummary: _asString(json['recent_task_summary']),
        lightRestartSuggestion: _asString(json['light_restart_suggestion']),
        planId: _asString(json['plan_id']),
      );

  final String title;
  final String message;
  final int daysAway;
  final int daysRemaining;
  final String subject;
  final String nextTaskTitle;
  final String recentTaskSummary;
  final String lightRestartSuggestion;
  final String planId;

  bool get hasContent => message.isNotEmpty;
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
