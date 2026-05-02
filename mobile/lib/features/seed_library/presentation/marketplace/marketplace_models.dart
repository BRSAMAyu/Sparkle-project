class MarketplaceSkillCard {
  const MarketplaceSkillCard({
    required this.skillId,
    required this.name,
    required this.description,
    required this.domain,
    required this.goalType,
    required this.version,
    required this.status,
    required this.evidenceGrade,
    required this.successRate,
    required this.qualityScore,
    required this.adoptionCount,
    required this.expectedOutcome,
    required this.contraindications,
  });

  factory MarketplaceSkillCard.fromJson(Map<String, dynamic> json) =>
      MarketplaceSkillCard(
        skillId: json['skill_id'] as String? ?? '',
        name: json['name'] as String? ?? 'Skill',
        description: json['description'] as String? ?? '',
        domain: json['domain'] as String? ?? '',
        goalType: json['goal_type'] as String? ?? '',
        version: (json['version'] as num?)?.toInt() ?? 1,
        status: json['status'] as String? ?? 'draft',
        evidenceGrade: (json['evidence_grade'] as num?)?.toInt() ?? 0,
        successRate: (json['success_rate'] as num?)?.toDouble() ?? 0,
        qualityScore: (json['quality_score'] as num?)?.toDouble() ?? 0,
        adoptionCount: (json['adoption_count'] as num?)?.toInt() ?? 0,
        expectedOutcome: json['expected_outcome'] as String? ?? '',
        contraindications: (json['contraindications'] as List<dynamic>? ?? [])
            .map((item) => item.toString())
            .toList(),
      );

  final String skillId;
  final String name;
  final String description;
  final String domain;
  final String goalType;
  final int version;
  final String status;
  final int evidenceGrade;
  final double successRate;
  final double qualityScore;
  final int adoptionCount;
  final String expectedOutcome;
  final List<String> contraindications;
}

class MarketplacePackCard {
  const MarketplacePackCard({
    required this.packId,
    required this.name,
    required this.description,
    required this.domain,
    required this.version,
    required this.status,
    required this.qualityScore,
    required this.skillIds,
    required this.adoptionCount,
  });

  factory MarketplacePackCard.fromJson(Map<String, dynamic> json) =>
      MarketplacePackCard(
        packId: json['pack_id'] as String? ?? '',
        name: json['name'] as String? ?? 'Pack',
        description: json['description'] as String? ?? '',
        domain: json['domain'] as String? ?? '',
        version: (json['version'] as num?)?.toInt() ?? 1,
        status: json['status'] as String? ?? 'draft',
        qualityScore: (json['quality_score'] as num?)?.toDouble() ?? 0,
        adoptionCount: (json['adoption_count'] as num?)?.toInt() ?? 0,
        skillIds: (json['skill_ids'] as List<dynamic>? ?? [])
            .map((item) => item.toString())
            .toList(),
      );

  final String packId;
  final String name;
  final String description;
  final String domain;
  final int version;
  final String status;
  final double qualityScore;
  final int adoptionCount;
  final List<String> skillIds;
}

class MarketplacePreview {
  const MarketplacePreview({
    required this.assetId,
    required this.assetType,
    required this.version,
    required this.willAffect,
    required this.qualityScore,
    required this.requiresExplicitConfirm,
    required this.payload,
  });

  factory MarketplacePreview.fromJson(Map<String, dynamic> json) =>
      MarketplacePreview(
        assetId: json['asset_id'] as String? ?? '',
        assetType: json['asset_type'] as String? ?? '',
        version: (json['version'] as num?)?.toInt() ?? 1,
        willAffect: (json['will_affect'] as List<dynamic>? ?? [])
            .map((item) => item.toString())
            .toList(),
        qualityScore: (json['quality_score'] as num?)?.toDouble() ?? 0,
        requiresExplicitConfirm:
            json['requires_explicit_confirm'] as bool? ?? true,
        payload: json,
      );

  final String assetId;
  final String assetType;
  final int version;
  final List<String> willAffect;
  final double qualityScore;
  final bool requiresExplicitConfirm;
  final Map<String, dynamic> payload;
}

class MarketplaceAdoption {
  const MarketplaceAdoption({
    required this.id,
    required this.assetId,
    required this.assetType,
    required this.status,
  });

  factory MarketplaceAdoption.fromJson(Map<String, dynamic> json) =>
      MarketplaceAdoption(
        id: json['id'] as String? ?? '',
        assetId: json['asset_id'] as String? ?? '',
        assetType: json['asset_type'] as String? ?? '',
        status: json['status'] as String? ?? '',
      );

  final String id;
  final String assetId;
  final String assetType;
  final String status;
}
