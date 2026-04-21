class SkillActivationConditionModel {
  SkillActivationConditionModel({
    required this.kind,
    required this.value,
  });

  factory SkillActivationConditionModel.fromJson(Map<String, dynamic> json) =>
      SkillActivationConditionModel(
        kind: json['kind'] as String? ?? '',
        value: (json['value'] as List<dynamic>? ?? [])
            .map((item) => item.toString())
            .toList(),
      );

  final String kind;
  final List<String> value;

  Map<String, dynamic> toJson() => {
        'kind': kind,
        'value': value,
      };
}

class SkillItemModel {
  SkillItemModel({
    required this.id,
    required this.name,
    required this.patternTemplate,
    required this.activationConditions,
    required this.examples,
    required this.privacyLevel,
    required this.usageCount,
    required this.active,
    this.lastActivatedAt,
    this.forkedFromShareId,
    this.forkedAt,
    this.sharedCatalogId,
  });

  factory SkillItemModel.fromJson(Map<String, dynamic> json) => SkillItemModel(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        patternTemplate: json['pattern_template'] as String? ?? '',
        activationConditions:
            (json['activation_conditions'] as List<dynamic>? ?? [])
                .whereType<Map<String, dynamic>>()
                .map(SkillActivationConditionModel.fromJson)
                .toList(),
        examples: (json['examples'] as List<dynamic>? ?? [])
            .map((item) => item.toString())
            .toList(),
        privacyLevel: json['privacy_level'] as String? ?? 'private',
        usageCount: json['usage_count'] as int? ?? 0,
        active: json['active'] as bool? ?? false,
        lastActivatedAt: _parseDate(json['last_activated_at']),
        forkedFromShareId: json['forked_from_share_id'] as String?,
        forkedAt: _parseDate(json['forked_at']),
        sharedCatalogId: json['shared_catalog_id'] as String?,
      );

  final String id;
  final String name;
  final String patternTemplate;
  final List<SkillActivationConditionModel> activationConditions;
  final List<String> examples;
  final String privacyLevel;
  final int usageCount;
  final bool active;
  final DateTime? lastActivatedAt;
  final String? forkedFromShareId;
  final DateTime? forkedAt;
  final String? sharedCatalogId;

  bool get isForked => (forkedFromShareId ?? '').isNotEmpty;
  bool get isShared =>
      (sharedCatalogId ?? '').isNotEmpty || privacyLevel == 'shared';
}

class SharedSkillItemModel {
  SharedSkillItemModel({
    required this.id,
    required this.name,
    required this.patternTemplate,
    required this.activationConditions,
    required this.examples,
    required this.authorLabel,
    this.publishedAt,
  });

  factory SharedSkillItemModel.fromJson(Map<String, dynamic> json) =>
      SharedSkillItemModel(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        patternTemplate: json['pattern_template'] as String? ?? '',
        activationConditions:
            (json['activation_conditions'] as List<dynamic>? ?? [])
                .whereType<Map<String, dynamic>>()
                .map(SkillActivationConditionModel.fromJson)
                .toList(),
        examples: (json['examples'] as List<dynamic>? ?? [])
            .map((item) => item.toString())
            .toList(),
        authorLabel: json['author_label'] as String? ?? 'anonymous',
        publishedAt: _parseDate(json['published_at']),
      );

  final String id;
  final String name;
  final String patternTemplate;
  final List<SkillActivationConditionModel> activationConditions;
  final List<String> examples;
  final String authorLabel;
  final DateTime? publishedAt;
}

class SkillDraftModel {
  SkillDraftModel({
    required this.name,
    required this.patternTemplate,
    required this.activationConditions,
    required this.examples,
  });

  factory SkillDraftModel.fromJson(Map<String, dynamic> json) =>
      SkillDraftModel(
        name: json['name'] as String? ?? '',
        patternTemplate: json['pattern_template'] as String? ?? '',
        activationConditions:
            (json['activation_conditions'] as List<dynamic>? ?? [])
                .whereType<Map<String, dynamic>>()
                .map(SkillActivationConditionModel.fromJson)
                .toList(),
        examples: (json['examples'] as List<dynamic>? ?? [])
            .map((item) => item.toString())
            .toList(),
      );

  final String name;
  final String patternTemplate;
  final List<SkillActivationConditionModel> activationConditions;
  final List<String> examples;

  Map<String, dynamic> toCreatePayload({bool active = true}) => {
        'name': name,
        'pattern_template': patternTemplate,
        'activation_conditions':
            activationConditions.map((item) => item.toJson()).toList(),
        'examples': examples,
        'active': active,
      };
}

DateTime? _parseDate(dynamic raw) {
  if (raw is! String || raw.isEmpty) {
    return null;
  }
  return DateTime.tryParse(raw);
}
