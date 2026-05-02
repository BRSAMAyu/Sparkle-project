import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';

final streakQualityProvider =
    FutureProvider<StreakQualitySnapshot>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient.get<Map<String, dynamic>>(
    '/experience/streak-quality',
  );
  final payload = response.data;
  if (payload == null) {
    throw StateError('streak quality response is empty');
  }
  return StreakQualitySnapshot.fromJson(payload);
});

class StreakQualitySnapshot {
  const StreakQualitySnapshot({
    required this.currentStreak,
    required this.qualityStreak,
    required this.todayQuality,
    required this.weeklyQualityTrend,
    this.celebrationTrigger,
  });

  factory StreakQualitySnapshot.fromJson(Map<String, dynamic> json) =>
      StreakQualitySnapshot(
        currentStreak: _asInt(json['current_streak']),
        qualityStreak: _asInt(json['quality_streak']),
        todayQuality: StreakQuality.fromJson(
          _asMap(json['today_quality']),
        ),
        weeklyQualityTrend: _asList(json['weekly_quality_trend'])
            .map(StreakQualityTrendPoint.fromJson)
            .toList(growable: false),
        celebrationTrigger: json['celebration_trigger'] == null
            ? null
            : StreakCelebrationTrigger.fromJson(
                _asMap(json['celebration_trigger']),
              ),
      );

  final int currentStreak;
  final int qualityStreak;
  final StreakQuality todayQuality;
  final List<StreakQualityTrendPoint> weeklyQualityTrend;
  final StreakCelebrationTrigger? celebrationTrigger;
}

class StreakQuality {
  const StreakQuality({
    required this.effectiveMinutes,
    required this.coreTasksCompleted,
    required this.difficultBreakthroughs,
    required this.planConsistency,
    required this.recoveryScore,
    required this.qualityScore,
    required this.isQualityDay,
  });

  factory StreakQuality.fromJson(Map<String, dynamic> json) => StreakQuality(
        effectiveMinutes: _asInt(json['effective_minutes']),
        coreTasksCompleted: _asInt(json['core_tasks_completed']),
        difficultBreakthroughs: _asInt(json['difficult_breakthroughs']),
        planConsistency: _asDouble(json['plan_consistency']),
        recoveryScore: _asDouble(json['recovery_score']),
        qualityScore: _asDouble(json['quality_score']),
        isQualityDay: json['is_quality_day'] == true,
      );

  final int effectiveMinutes;
  final int coreTasksCompleted;
  final int difficultBreakthroughs;
  final double planConsistency;
  final double recoveryScore;
  final double qualityScore;
  final bool isQualityDay;
}

class StreakQualityTrendPoint {
  const StreakQualityTrendPoint({
    required this.date,
    required this.qualityScore,
    required this.breakdown,
  });

  factory StreakQualityTrendPoint.fromJson(Map<String, dynamic> json) =>
      StreakQualityTrendPoint(
        date: DateTime.tryParse('${json['date']}'),
        qualityScore: _asDouble(json['quality_score']),
        breakdown: StreakQuality.fromJson(_asMap(json['breakdown'])),
      );

  final DateTime? date;
  final double qualityScore;
  final StreakQuality breakdown;
}

class StreakCelebrationTrigger {
  const StreakCelebrationTrigger({
    required this.reason,
    required this.evidence,
    required this.suggestedMessage,
  });

  factory StreakCelebrationTrigger.fromJson(Map<String, dynamic> json) =>
      StreakCelebrationTrigger(
        reason: '${json['reason'] ?? ''}',
        evidence: '${json['evidence'] ?? ''}',
        suggestedMessage: '${json['suggested_message'] ?? ''}',
      );

  final String reason;
  final String evidence;
  final String suggestedMessage;
}

Map<String, dynamic> _asMap(Object? value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return const <String, dynamic>{};
}

List<Map<String, dynamic>> _asList(Object? value) {
  if (value is List) {
    return value
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList(growable: false);
  }
  return const <Map<String, dynamic>>[];
}

int _asInt(Object? value) {
  if (value is int) return value;
  if (value is num) return value.round();
  return int.tryParse('$value') ?? 0;
}

double _asDouble(Object? value) {
  if (value is double) return value.clamp(0.0, 1.0);
  if (value is num) return value.toDouble().clamp(0.0, 1.0);
  return (double.tryParse('$value') ?? 0.0).clamp(0.0, 1.0);
}
