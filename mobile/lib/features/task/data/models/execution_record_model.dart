class ExecutionRecordModel {
  const ExecutionRecordModel({
    required this.id,
    required this.executionIntentId,
    required this.trustLevel,
    required this.artifacts,
    this.qualityScore,
    this.parsedOutput,
    this.durationMs,
    this.validationPassed,
    this.validationTotal,
    this.approvalRequested,
    this.errorCategory,
    this.errorMessage,
  });

  factory ExecutionRecordModel.fromJson(Map<String, dynamic> json) =>
      ExecutionRecordModel(
        id: json['id'] as String? ?? '',
        executionIntentId: json['execution_intent_id'] as String? ?? '',
        trustLevel: json['trust_level'] as String? ?? 'raw',
        qualityScore: (json['quality_score'] as num?)?.toDouble(),
        parsedOutput: json['parsed_output'] as Map<String, dynamic>?,
        artifacts: (json['artifacts'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .toList(),
        durationMs: json['duration_ms'] as int?,
        validationPassed: json['validation_passed'] as int?,
        validationTotal: json['validation_total'] as int?,
        approvalRequested: json['approval_requested'] as int?,
        errorCategory: json['error_category'] as String?,
        errorMessage: json['error_message'] as String?,
      );

  final String id;
  final String executionIntentId;
  final String trustLevel;
  final double? qualityScore;
  final Map<String, dynamic>? parsedOutput;
  final List<Map<String, dynamic>> artifacts;
  final int? durationMs;
  final int? validationPassed;
  final int? validationTotal;
  final int? approvalRequested;
  final String? errorCategory;
  final String? errorMessage;

  bool get hasStructuredOutput =>
      parsedOutput != null && parsedOutput!.isNotEmpty;

  String get trustLabel {
    switch (trustLevel) {
      case 'trusted':
        return '可信结果';
      case 'validated':
        return '已校验';
      case 'raw':
      default:
        return '原始结果';
    }
  }
}
