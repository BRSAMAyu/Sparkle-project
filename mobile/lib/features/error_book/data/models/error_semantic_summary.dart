class ErrorSemanticSummary {
  ErrorSemanticSummary({
    required this.errorId,
    this.rootCause,
    this.linkedConcepts = const [],
    this.strategies = const [],
    this.similarErrors = const [],
  });

  factory ErrorSemanticSummary.fromJson(Map<String, dynamic> json) => ErrorSemanticSummary(
      errorId: json['error_id'] as String,
      rootCause: json['root_cause'] as String?,
      linkedConcepts: _parseConcepts(json['linked_concepts']),
      strategies: _parseStrategies(json['strategies']),
      similarErrors: _parseSimilarErrors(json['similar_errors']),
    );

  final String errorId;
  final String? rootCause;
  final List<ConceptBrief> linkedConcepts;
  final List<StrategyBrief> strategies;
  final List<SimilarErrorBrief> similarErrors;

  static List<ConceptBrief> _parseConcepts(dynamic raw) {
    if (raw is! List) return [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(ConceptBrief.fromJson)
        .toList();
  }

  static List<StrategyBrief> _parseStrategies(dynamic raw) {
    if (raw is! List) return [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(StrategyBrief.fromJson)
        .toList();
  }

  static List<SimilarErrorBrief> _parseSimilarErrors(dynamic raw) {
    if (raw is! List) return [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(SimilarErrorBrief.fromJson)
        .toList();
  }
}

class ConceptBrief {
  ConceptBrief({
    required this.id,
    required this.name,
    this.description,
  });

  factory ConceptBrief.fromJson(Map<String, dynamic> json) => ConceptBrief(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
    );

  final String id;
  final String name;
  final String? description;
}

class StrategyBrief {
  StrategyBrief({
    required this.id,
    required this.title,
    this.description,
    this.subjectCode,
    this.tags = const [],
  });

  factory StrategyBrief.fromJson(Map<String, dynamic> json) => StrategyBrief(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String?,
      subjectCode: json['subject_code'] as String?,
      tags: (json['tags'] as List?)?.whereType<String>().toList() ?? const [],
    );

  final String id;
  final String title;
  final String? description;
  final String? subjectCode;
  final List<String> tags;
}

class SimilarErrorBrief {
  SimilarErrorBrief({
    required this.id,
    required this.subjectCode,
    this.rootCause,
    this.createdAt,
  });

  factory SimilarErrorBrief.fromJson(Map<String, dynamic> json) => SimilarErrorBrief(
      id: json['id'] as String,
      subjectCode: json['subject_code'] as String? ?? '',
      rootCause: json['root_cause'] as String?,
      createdAt: json['created_at'] as String?,
    );

  final String id;
  final String subjectCode;
  final String? rootCause;
  final String? createdAt;
}
