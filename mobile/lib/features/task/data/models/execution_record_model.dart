class ExecutionRecordModel {
  const ExecutionRecordModel({
    required this.id,
    required this.executionIntentId,
    required this.trustLevel,
    required this.artifacts,
    required this.toolCallsCount,
    this.qualityScore,
    this.parsedOutput,
    this.durationMs,
    this.validationPassed,
    this.validationTotal,
    this.approvalRequested,
    this.errorCategory,
    this.errorMessage,
    this.resultPreview,
    this.qualityWarnings = const [],
    this.replaySteps = const [],
    this.comparisonSummary,
    this.selfVerification,
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
        toolCallsCount: json['tool_calls_count'] as int? ?? 0,
        durationMs: json['duration_ms'] as int?,
        validationPassed: json['validation_passed'] as int?,
        validationTotal: json['validation_total'] as int?,
        approvalRequested: json['approval_requested'] as int?,
        errorCategory: json['error_category'] as String?,
        errorMessage: json['error_message'] as String?,
        resultPreview: json['result_preview'] is Map
            ? Map<String, dynamic>.from(json['result_preview'] as Map)
            : null,
        qualityWarnings: (json['quality_warnings'] as List<dynamic>? ?? const [])
            .whereType<Map<dynamic, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList(),
        replaySteps: (json['replay_steps'] as List<dynamic>? ?? const [])
            .whereType<Map<dynamic, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList(),
        comparisonSummary: json['comparison_summary'] is Map
            ? Map<String, dynamic>.from(json['comparison_summary'] as Map)
            : null,
        selfVerification: json['self_verification'] is Map
            ? Map<String, dynamic>.from(json['self_verification'] as Map)
            : null,
      );

  final String id;
  final String executionIntentId;
  final String trustLevel;
  final double? qualityScore;
  final Map<String, dynamic>? parsedOutput;
  final List<Map<String, dynamic>> artifacts;
  final int toolCallsCount;
  final int? durationMs;
  final int? validationPassed;
  final int? validationTotal;
  final int? approvalRequested;
  final String? errorCategory;
  final String? errorMessage;
  final Map<String, dynamic>? resultPreview;
  final List<Map<String, dynamic>> qualityWarnings;
  final List<Map<String, dynamic>> replaySteps;
  final Map<String, dynamic>? comparisonSummary;
  final Map<String, dynamic>? selfVerification;

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
