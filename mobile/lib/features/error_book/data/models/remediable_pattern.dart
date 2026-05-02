class RemediablePattern {
  const RemediablePattern({
    required this.id,
    required this.errorType,
    required this.errorTypeLabel,
    required this.errorCount,
    required this.confidence,
    required this.averageMastery,
    required this.suggestedDurationMinutes,
    required this.representativeErrorId,
    required this.errorIds,
    required this.lastSeenAt,
    this.knowledgeNodeId,
    this.knowledgeNodeName,
    this.subjectCode,
    this.chapter,
    this.rootCauseSummary,
  });

  factory RemediablePattern.fromJson(Map<String, dynamic> json) =>
      RemediablePattern(
        id: json['id']?.toString() ?? '',
        knowledgeNodeId: _nullableString(json['knowledge_node_id']),
        knowledgeNodeName: _nullableString(json['knowledge_node_name']),
        errorType: json['error_type']?.toString() ?? 'other',
        errorTypeLabel: json['error_type_label']?.toString() ?? '',
        subjectCode: _nullableString(json['subject_code']),
        chapter: _nullableString(json['chapter']),
        errorCount: _intFromJson(json['error_count']),
        confidence: _doubleFromJson(json['confidence']),
        averageMastery: _doubleFromJson(json['average_mastery']),
        suggestedDurationMinutes:
            _intFromJson(json['suggested_duration_minutes']),
        rootCauseSummary: _nullableString(json['root_cause_summary']),
        representativeErrorId:
            json['representative_error_id']?.toString() ?? '',
        errorIds: _stringList(json['error_ids']),
        lastSeenAt: DateTime.tryParse(json['last_seen_at']?.toString() ?? '') ??
            DateTime.now(),
      );

  final String id;
  final String? knowledgeNodeId;
  final String? knowledgeNodeName;
  final String errorType;
  final String errorTypeLabel;
  final String? subjectCode;
  final String? chapter;
  final int errorCount;
  final double confidence;
  final double averageMastery;
  final int suggestedDurationMinutes;
  final String? rootCauseSummary;
  final String representativeErrorId;
  final List<String> errorIds;
  final DateTime lastSeenAt;

  String get displayFocus => knowledgeNodeName?.trim().isNotEmpty ?? false
      ? knowledgeNodeName!
      : (chapter?.trim().isNotEmpty ?? false)
          ? chapter!
          : errorTypeLabel;
}

class StructuredRemediationStep {
  const StructuredRemediationStep({
    required this.order,
    required this.title,
    required this.instruction,
    required this.durationMinutes,
    required this.checkpoint,
  });

  factory StructuredRemediationStep.fromJson(Map<String, dynamic> json) =>
      StructuredRemediationStep(
        order: _intFromJson(json['order']),
        title: json['title']?.toString() ?? '',
        instruction: json['instruction']?.toString() ?? '',
        durationMinutes: _intFromJson(json['duration_minutes']),
        checkpoint: json['checkpoint']?.toString() ?? '',
      );

  final int order;
  final String title;
  final String instruction;
  final int durationMinutes;
  final String checkpoint;
}

class RemedialTaskTemplate {
  const RemedialTaskTemplate({
    required this.patternId,
    required this.title,
    required this.objective,
    required this.estimatedMinutes,
    required this.difficulty,
    required this.errorType,
    required this.successCriteria,
    required this.minimumOutput,
    required this.structuredSteps,
    required this.guideJson,
    required this.taskPayload,
    this.knowledgeNodeId,
  });

  factory RemedialTaskTemplate.fromJson(Map<String, dynamic> json) =>
      RemedialTaskTemplate(
        patternId: json['pattern_id']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        objective: json['objective']?.toString() ?? '',
        estimatedMinutes: _intFromJson(json['estimated_minutes']),
        difficulty: _intFromJson(json['difficulty']),
        knowledgeNodeId: _nullableString(json['knowledge_node_id']),
        errorType: json['error_type']?.toString() ?? 'other',
        successCriteria: _stringList(json['success_criteria']),
        minimumOutput: json['minimum_output']?.toString() ?? '',
        structuredSteps: (json['structured_steps'] as List? ?? const [])
            .whereType<Map<dynamic, dynamic>>()
            .map(
              (item) => StructuredRemediationStep.fromJson(
                Map<String, dynamic>.from(item),
              ),
            )
            .toList(),
        guideJson: _mapFromJson(json['guide_json']),
        taskPayload: _mapFromJson(json['task_payload']),
      );

  final String patternId;
  final String title;
  final String objective;
  final int estimatedMinutes;
  final int difficulty;
  final String? knowledgeNodeId;
  final String errorType;
  final List<String> successCriteria;
  final String minimumOutput;
  final List<StructuredRemediationStep> structuredSteps;
  final Map<String, dynamic> guideJson;
  final Map<String, dynamic> taskPayload;
}

String? _nullableString(Object? value) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? null : text;
}

int _intFromJson(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? 0;
  return 0;
}

double _doubleFromJson(Object? value) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? 0;
  return 0;
}

List<String> _stringList(Object? value) {
  if (value is! List) return const <String>[];
  return value.map((item) => item.toString()).toList();
}

Map<String, dynamic> _mapFromJson(Object? value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return const <String, dynamic>{};
}
