class AuroraDailyStartupMessage {
  const AuroraDailyStartupMessage({
    required this.message,
    required this.todayFocus,
    required this.estimatedMinutes,
    required this.adjustmentReason,
  });

  factory AuroraDailyStartupMessage.fromJson(Map<String, dynamic> json) =>
      AuroraDailyStartupMessage(
        message: _asString(json['message']),
        todayFocus: _asString(json['today_focus']),
        estimatedMinutes: _asInt(json['estimated_minutes']),
        adjustmentReason: _asString(json['adjustment_reason']),
      );

  final String message;
  final String todayFocus;
  final int estimatedMinutes;
  final String adjustmentReason;
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
