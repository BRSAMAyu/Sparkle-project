class StrategyEvidenceModel {
  const StrategyEvidenceModel({
    required this.reason,
    required this.weight,
    required this.source,
  });

  factory StrategyEvidenceModel.fromJson(Map<String, dynamic> json) =>
      StrategyEvidenceModel(
        reason: _asString(json['reason']),
        weight: _asDouble(json['weight'], fallback: 1),
        source: _asString(json['source'], fallback: 'counter_evidence'),
      );

  final String reason;
  final double weight;
  final String source;
}

class StrategyBeliefView {
  const StrategyBeliefView({
    required this.strategyId,
    required this.title,
    required this.confidence,
    required this.counterEvidence,
  });

  factory StrategyBeliefView.fromJson(Map<String, dynamic> json) =>
      StrategyBeliefView(
        strategyId: _asString(json['strategy_id']),
        title: _asString(json['title']),
        confidence: _asDouble(json['confidence']),
        counterEvidence: _asList(json['counter_evidence'])
            .whereType<Map<dynamic, dynamic>>()
            .map((item) => StrategyEvidenceModel.fromJson(
                  Map<String, dynamic>.from(item),
                ))
            .toList(growable: false),
      );

  final String strategyId;
  final String title;
  final double confidence;
  final List<StrategyEvidenceModel> counterEvidence;

  bool get shouldTrigger => confidence < 0.4 && counterEvidence.isNotEmpty;
}

class AlternativeStrategyModel {
  const AlternativeStrategyModel({
    required this.strategyId,
    required this.title,
    required this.description,
    required this.confidence,
    required this.estimatedLift,
    required this.why,
  });

  factory AlternativeStrategyModel.fromJson(Map<String, dynamic> json) =>
      AlternativeStrategyModel(
        strategyId: _asString(json['strategy_id']),
        title: _asString(json['title']),
        description: _asString(json['description']),
        confidence: _asDouble(json['confidence']),
        estimatedLift: _asDouble(json['estimated_lift']),
        why: _asString(json['why']),
      );

  final String strategyId;
  final String title;
  final String description;
  final double confidence;
  final double estimatedLift;
  final String why;
}

class StrategySuggestionBundle {
  const StrategySuggestionBundle({
    required this.goalId,
    required this.currentStrategyId,
    required this.currentStrategyTitle,
    required this.confidence,
    required this.counterEvidence,
    required this.alternatives,
  });

  factory StrategySuggestionBundle.fromJson(Map<String, dynamic> json) =>
      StrategySuggestionBundle(
        goalId: _asString(json['goal_id']),
        currentStrategyId: _asString(json['current_strategy_id']),
        currentStrategyTitle: _asString(json['current_strategy_title']),
        confidence: _asDouble(json['confidence']),
        counterEvidence: _asList(json['counter_evidence'])
            .whereType<Map<dynamic, dynamic>>()
            .map((item) => StrategyEvidenceModel.fromJson(
                  Map<String, dynamic>.from(item),
                ))
            .toList(growable: false),
        alternatives: _asList(json['alternatives'])
            .whereType<Map<dynamic, dynamic>>()
            .map((item) => AlternativeStrategyModel.fromJson(
                  Map<String, dynamic>.from(item),
                ))
            .toList(growable: false),
      );

  final String goalId;
  final String currentStrategyId;
  final String currentStrategyTitle;
  final double confidence;
  final List<StrategyEvidenceModel> counterEvidence;
  final List<AlternativeStrategyModel> alternatives;
}

class StrategyMigrationResult {
  const StrategyMigrationResult({
    required this.goalId,
    required this.previousStrategyId,
    required this.newStrategyId,
    required this.newStrategyTitle,
    required this.migratedAt,
  });

  factory StrategyMigrationResult.fromJson(Map<String, dynamic> json) =>
      StrategyMigrationResult(
        goalId: _asString(json['goal_id']),
        previousStrategyId: _asString(json['previous_strategy_id']),
        newStrategyId: _asString(json['new_strategy_id']),
        newStrategyTitle: _asString(json['new_strategy_title']),
        migratedAt: _asString(json['migrated_at']),
      );

  final String goalId;
  final String previousStrategyId;
  final String newStrategyId;
  final String newStrategyTitle;
  final String migratedAt;
}

List<dynamic> _asList(dynamic value) => value is List ? value : const [];

String _asString(dynamic value, {String fallback = ''}) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? fallback : text;
}

double _asDouble(dynamic value, {double fallback = 0}) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? fallback;
  return fallback;
}
