import 'package:flutter/foundation.dart';

@immutable
class UnderstandingSnapshot {
  const UnderstandingSnapshot({
    required this.active,
    required this.status,
    required this.summary,
    required this.confidence,
    required this.evidence,
    required this.memoryClaims,
    required this.openQuestions,
    this.energyLevel,
    this.nextStepLabel,
    this.updatedAt,
  });

  factory UnderstandingSnapshot.fromJson(Map<String, dynamic> json) {
    final nextStep = _map(json['next_step_suggestion']);
    return UnderstandingSnapshot(
      active: _bool(json['active']),
      status: _string(json['status'], fallback: 'sensing'),
      summary: _string(json['summary']),
      confidence: _unit(json['confidence']),
      energyLevel: _nullableString(json['energy_level']),
      evidence: _list(json['evidence'])
          .map(_readableLine)
          .where(_notEmpty)
          .toList(growable: false),
      memoryClaims: _list(json['memory_claims'])
          .map(_readableLine)
          .where(_notEmpty)
          .toList(growable: false),
      openQuestions: _list(json['open_questions'])
          .map(_map)
          .whereType<Map<String, dynamic>>()
          .map((item) => _string(item['question']))
          .where(_notEmpty)
          .toList(growable: false),
      nextStepLabel: _nullableString(
          nextStep?['label'] ?? nextStep?['title'] ?? nextStep?['summary']),
      updatedAt: DateTime.tryParse(_string(json['updated_at'])),
    );
  }

  final bool active;
  final String status;
  final String summary;
  final double confidence;
  final String? energyLevel;
  final List<String> evidence;
  final List<String> memoryClaims;
  final List<String> openQuestions;
  final String? nextStepLabel;
  final DateTime? updatedAt;
}

@immutable
class ExperienceGrowthDashboard {
  const ExperienceGrowthDashboard({
    required this.streakQuality,
    required this.learningDashboard,
    required this.modelUpdateReceipts,
    this.weeklyNarrative,
  });

  factory ExperienceGrowthDashboard.fromJson(Map<String, dynamic> json) =>
      ExperienceGrowthDashboard(
        streakQuality:
            StreakQuality.fromJson(_map(json['streak_quality']) ?? const {}),
        learningDashboard: LearningDashboardSnapshot.fromJson(
          _map(json['learning_dashboard']) ?? const {},
        ),
        weeklyNarrative:
            _nullableString(_map(json['weekly_narrative'])?['body']),
        modelUpdateReceipts: _list(json['model_update_receipts'])
            .map(_readableLine)
            .where(_notEmpty)
            .toList(growable: false),
      );

  final StreakQuality streakQuality;
  final LearningDashboardSnapshot learningDashboard;
  final String? weeklyNarrative;
  final List<String> modelUpdateReceipts;
}

@immutable
class StreakQuality {
  const StreakQuality({
    required this.score,
    required this.currentStreak,
    required this.label,
    required this.evidence,
  });

  factory StreakQuality.fromJson(Map<String, dynamic> json) => StreakQuality(
        score: _unit(json['score']),
        currentStreak: _int(json['current_streak']),
        label: _string(json['label']),
        evidence: _list(json['evidence'])
            .map(_readableLine)
            .where(_notEmpty)
            .toList(growable: false),
      );

  final double score;
  final int currentStreak;
  final String label;
  final List<String> evidence;
}

@immutable
class LearningDashboardSnapshot {
  const LearningDashboardSnapshot({
    required this.focusMinutes7d,
    required this.tasksTotal,
    required this.tasksCompleted,
    required this.tasksStuck,
    required this.tasksPaused,
    required this.completionRate,
  });

  factory LearningDashboardSnapshot.fromJson(Map<String, dynamic> json) =>
      LearningDashboardSnapshot(
        focusMinutes7d: _int(json['focus_minutes_7d']),
        tasksTotal: _int(json['tasks_total']),
        tasksCompleted: _int(json['tasks_completed']),
        tasksStuck: _int(json['tasks_stuck']),
        tasksPaused: _int(json['tasks_paused']),
        completionRate: _unit(json['completion_rate']),
      );

  final int focusMinutes7d;
  final int tasksTotal;
  final int tasksCompleted;
  final int tasksStuck;
  final int tasksPaused;
  final double completionRate;
}

@immutable
class GoalDetailSnapshot {
  const GoalDetailSnapshot({
    required this.active,
    required this.title,
    required this.progress,
    required this.criteria,
    required this.graphNodes,
    this.goalId,
    this.nextTaskTitle,
    this.whyThisMatters,
  });

  factory GoalDetailSnapshot.fromJson(Map<String, dynamic> json) {
    final goal = _map(json['goal']);
    final plan = _map(json['plan']);
    final progress = _map(json['progress']);
    final nextTask = _map(json['next_task']);
    final graph = _map(json['goal_graph']);
    return GoalDetailSnapshot(
      active: _bool(json['active']),
      goalId: _nullableString(
        goal?['id'] ??
            goal?['goal_id'] ??
            goal?['uuid'] ??
            json['goal_id'] ??
            json['id'],
      ),
      title: _string(
        goal?['title'] ?? plan?['name'],
        fallback: 'Current goal',
      ),
      progress:
          _unit(progress?['overall'] ?? goal?['progress'] ?? plan?['progress']),
      criteria: _list(json['minimum_acceptance_criteria'])
          .map(_readableLine)
          .where(_notEmpty)
          .toList(growable: false),
      graphNodes: _list(graph?['nodes'])
          .map(_readableLine)
          .where(_notEmpty)
          .toList(growable: false),
      nextTaskTitle: _nullableString(nextTask?['title']),
      whyThisMatters: _nullableString(json['why_this_matters']),
    );
  }

  final bool active;
  final String? goalId;
  final String title;
  final double progress;
  final List<String> criteria;
  final List<String> graphNodes;
  final String? nextTaskTitle;
  final String? whyThisMatters;
}

@immutable
class CommunityAccountabilitySnapshot {
  const CommunityAccountabilitySnapshot({
    required this.active,
    required this.headline,
    required this.summary,
    required this.suggestedActions,
  });

  factory CommunityAccountabilitySnapshot.fromJson(Map<String, dynamic> json) =>
      CommunityAccountabilitySnapshot(
        active: _bool(json['active']),
        headline: _string(json['headline'], fallback: 'Accountability'),
        summary: _string(json['summary']),
        suggestedActions: _list(json['suggested_actions'])
            .map(_readableLine)
            .where(_notEmpty)
            .toList(growable: false),
      );

  final bool active;
  final String headline;
  final String summary;
  final List<String> suggestedActions;
}

Map<String, dynamic>? _map(Object? value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return null;
}

List<Object?> _list(Object? value) => value is List ? value : const [];

String _string(Object? value, {String fallback = ''}) {
  final text = value?.toString().trim() ?? '';
  return text.isEmpty ? fallback : text;
}

String? _nullableString(Object? value) {
  final text = _string(value);
  return text.isEmpty ? null : text;
}

bool _bool(Object? value) =>
    value == true || value?.toString().toLowerCase() == 'true';

int _int(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double _unit(Object? value) {
  final numeric = value is num
      ? value.toDouble()
      : double.tryParse(value?.toString() ?? '') ?? 0;
  return numeric.clamp(0, 1).toDouble();
}

bool _notEmpty(String value) => value.trim().isNotEmpty;

String _readableLine(Object? value) {
  final map = _map(value);
  if (map == null) return _string(value);
  return _string(
    map['label'] ??
        map['title'] ??
        map['summary'] ??
        map['question'] ??
        map['claim'] ??
        map['text'] ??
        map['node_label'] ??
        map['node_id'],
  );
}
