class GoalMilestoneDraft {
  const GoalMilestoneDraft({
    required this.id,
    required this.title,
    required this.description,
    required this.estimatedDays,
    required this.acceptanceCriteria,
  });

  factory GoalMilestoneDraft.fromJson(Map<String, dynamic> json) =>
      GoalMilestoneDraft(
        id: _asString(json['id'], fallback: 'm1'),
        title: _asString(json['title']),
        description: _asString(json['description']),
        estimatedDays: _asInt(json['estimated_days']) ?? 14,
        acceptanceCriteria: _asList(json['acceptance_criteria'])
            .map((item) => item.toString())
            .where((item) => item.trim().isNotEmpty)
            .toList(growable: false),
      );

  final String id;
  final String title;
  final String description;
  final int estimatedDays;
  final List<String> acceptanceCriteria;

  GoalMilestoneDraft copyWith({
    String? id,
    String? title,
    String? description,
    int? estimatedDays,
    List<String>? acceptanceCriteria,
  }) =>
      GoalMilestoneDraft(
        id: id ?? this.id,
        title: title ?? this.title,
        description: description ?? this.description,
        estimatedDays: estimatedDays ?? this.estimatedDays,
        acceptanceCriteria: acceptanceCriteria ?? this.acceptanceCriteria,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'description': description,
        'estimated_days': estimatedDays,
        'acceptance_criteria': acceptanceCriteria,
      };
}

class GoalDecompositionPreview {
  const GoalDecompositionPreview({
    required this.goalType,
    required this.timeHorizon,
    required this.suggestedTargetDate,
    required this.rationale,
    required this.milestones,
  });

  factory GoalDecompositionPreview.fromJson(Map<String, dynamic> json) =>
      GoalDecompositionPreview(
        goalType: _asString(json['goal_type']),
        timeHorizon: _asString(json['time_horizon']),
        suggestedTargetDate: _asString(json['suggested_target_date']),
        rationale: _asString(json['rationale']),
        milestones: _asList(json['milestones'])
            .whereType<Map<dynamic, dynamic>>()
            .map((item) => GoalMilestoneDraft.fromJson(
                  Map<String, dynamic>.from(item),
                ))
            .toList(growable: false),
      );

  final String goalType;
  final String timeHorizon;
  final String suggestedTargetDate;
  final String rationale;
  final List<GoalMilestoneDraft> milestones;
}

class CreatedGoal {
  const CreatedGoal({
    required this.id,
    required this.title,
    required this.goalType,
    required this.status,
  });

  factory CreatedGoal.fromJson(Map<String, dynamic> json) => CreatedGoal(
        id: _asString(json['id']),
        title: _asString(json['title']),
        goalType: _asString(json['goal_type']),
        status: _asString(json['status'], fallback: 'active'),
      );

  final String id;
  final String title;
  final String goalType;
  final String status;
}

List<dynamic> _asList(dynamic value) => value is List ? value : const [];

String _asString(dynamic value, {String fallback = ''}) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? fallback : text;
}

int? _asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value);
  return null;
}
