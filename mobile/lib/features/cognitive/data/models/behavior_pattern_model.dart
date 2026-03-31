enum PatternType {
  cognitive('cognitive'),
  emotional('emotional'),
  execution('execution'),
  unknown('unknown');

  const PatternType(this.code);

  final String code;

  static PatternType fromJson(Object? value) {
    final normalized = value?.toString().trim().toLowerCase() ?? '';
    return PatternType.values.firstWhere(
      (type) => type.code == normalized,
      orElse: () => PatternType.unknown,
    );
  }
}

class BehaviorPatternModel {
  BehaviorPatternModel({
    required this.id,
    required this.userId,
    required this.patternName,
    required this.patternType,
    required this.confidenceScore,
    required this.frequency,
    required this.isArchived,
    required this.createdAt,
    required this.updatedAt,
    this.description,
    this.solutionText,
    this.evidenceIds,
    this.lastObservedAt,
    this.lastDecayAt,
  });

  factory BehaviorPatternModel.fromJson(Map<String, dynamic> json) =>
      BehaviorPatternModel(
        id: json['id']?.toString() ?? '',
        userId: json['user_id']?.toString() ?? '',
        patternName: json['pattern_name']?.toString() ?? '',
        patternType: PatternType.fromJson(json['pattern_type']),
        description: json['description']?.toString(),
        solutionText: json['solution_text']?.toString(),
        evidenceIds: (json['evidence_ids'] as List<dynamic>?)
            ?.map((item) => item.toString())
            .toList(),
        confidenceScore: (json['confidence_score'] as num?)?.toDouble() ?? 0.0,
        frequency: (json['frequency'] as num?)?.toInt() ?? 0,
        isArchived: json['is_archived'] == true,
        lastObservedAt: json['last_observed_at'] == null
            ? null
            : DateTime.tryParse(json['last_observed_at'].toString()),
        lastDecayAt: json['last_decay_at'] == null
            ? null
            : DateTime.tryParse(json['last_decay_at'].toString()),
        createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ??
            DateTime.now(),
        updatedAt: DateTime.tryParse(json['updated_at']?.toString() ?? '') ??
            DateTime.now(),
      );

  final String id;
  final String userId;
  final String patternName;
  final PatternType patternType;
  final String? description;
  final String? solutionText;
  final List<String>? evidenceIds;
  final double confidenceScore;
  final int frequency;
  final bool isArchived;
  final DateTime? lastObservedAt;
  final DateTime? lastDecayAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'pattern_name': patternName,
        'pattern_type': patternType.code,
        'description': description,
        'solution_text': solutionText,
        'evidence_ids': evidenceIds,
        'confidence_score': confidenceScore,
        'frequency': frequency,
        'is_archived': isArchived,
        'last_observed_at': lastObservedAt?.toIso8601String(),
        'last_decay_at': lastDecayAt?.toIso8601String(),
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt.toIso8601String(),
      };
}
