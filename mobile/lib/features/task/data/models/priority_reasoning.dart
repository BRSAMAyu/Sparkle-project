class PrioritySignal {
  const PrioritySignal({
    required this.type,
    required this.weight,
    required this.detail,
    this.rawScore,
  });

  factory PrioritySignal.fromJson(Map<String, dynamic> json) => PrioritySignal(
        type: (json['type'] ?? '').toString(),
        weight: ((json['weight'] as num?) ?? 0).toDouble(),
        detail: (json['detail'] ?? '').toString(),
        rawScore: (json['raw_score'] as num?)?.toDouble(),
      );

  final String type;
  final double weight;
  final String detail;
  final double? rawScore;
}

class AlternativeOptionSkipped {
  const AlternativeOptionSkipped({
    required this.taskId,
    required this.title,
    required this.score,
    required this.reason,
  });

  factory AlternativeOptionSkipped.fromJson(Map<String, dynamic> json) =>
      AlternativeOptionSkipped(
        taskId: (json['task_id'] ?? '').toString(),
        title: (json['title'] ?? '').toString(),
        score: ((json['score'] as num?) ?? 0).toDouble(),
        reason: (json['reason'] ?? '').toString(),
      );

  final String taskId;
  final String title;
  final double score;
  final String reason;
}

class PriorityReasoning {
  const PriorityReasoning({
    required this.taskId,
    required this.generatedAt,
    required this.selectedScore,
    required this.primaryReason,
    required this.supportingSignals,
    required this.alternativeOptionsSkipped,
    this.taskUpdatedAt,
  });

  factory PriorityReasoning.fromJson(Map<String, dynamic> json) {
    DateTime parseDate(String key) =>
        DateTime.tryParse((json[key] ?? '').toString()) ?? DateTime.now();
    List<Map<String, dynamic>> readMapList(String key) =>
        (json[key] as List? ?? const [])
            .map(_asStringMap)
            .whereType<Map<String, dynamic>>()
            .toList();

    return PriorityReasoning(
      taskId: (json['task_id'] ?? '').toString(),
      generatedAt: parseDate('generated_at'),
      taskUpdatedAt: DateTime.tryParse(
        (json['task_updated_at'] ?? '').toString(),
      ),
      selectedScore: ((json['selected_score'] as num?) ?? 0).toDouble(),
      primaryReason: (json['primary_reason'] ?? '').toString(),
      supportingSignals: readMapList('supporting_signals')
          .map(PrioritySignal.fromJson)
          .toList(),
      alternativeOptionsSkipped: readMapList('alternative_options_skipped')
          .map(AlternativeOptionSkipped.fromJson)
          .toList(),
    );
  }

  static Map<String, dynamic>? _asStringMap(Object? value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map<Object?, Object?>) return Map<String, dynamic>.from(value);
    return null;
  }

  final String taskId;
  final DateTime generatedAt;
  final DateTime? taskUpdatedAt;
  final double selectedScore;
  final String primaryReason;
  final List<PrioritySignal> supportingSignals;
  final List<AlternativeOptionSkipped> alternativeOptionsSkipped;
}
