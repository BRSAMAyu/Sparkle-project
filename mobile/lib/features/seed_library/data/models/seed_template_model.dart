library;

import 'dart:convert';

class SeedTemplatePack {
  SeedTemplatePack({
    required this.id,
    required this.scenarioType,
    required this.name,
    required this.visibility,
    required this.status,
    this.description,
    this.ownerId,
    this.language = 'zh',
    this.tags = const [],
    this.qualityScore,
    this.adoptionScore,
    this.safetyScore,
  });

  factory SeedTemplatePack.fromJson(Map<String, dynamic> json) {
    final tagsRaw = json['tags'];
    return SeedTemplatePack(
      id: (json['id'] ?? '').toString(),
      scenarioType: (json['scenario_type'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      description: json['description'] as String?,
      ownerId: json['owner_id'] as String?,
      visibility: (json['visibility'] ?? 'private').toString(),
      status: (json['status'] ?? 'draft').toString(),
      language: (json['language'] ?? 'zh').toString(),
      tags: tagsRaw is List ? tagsRaw.map((e) => '$e').toList() : const [],
      qualityScore: _asDouble(json['quality_score']),
      adoptionScore: _asDouble(json['adoption_score']),
      safetyScore: _asDouble(json['safety_score']),
    );
  }

  final String id;
  final String scenarioType;
  final String name;
  final String? description;
  final String? ownerId;
  final String visibility;
  final String status;
  final String language;
  final List<String> tags;
  final double? qualityScore;
  final double? adoptionScore;
  final double? safetyScore;
}

class SeedTemplateListItem {
  SeedTemplateListItem({
    required this.id,
    required this.packId,
    required this.name,
    required this.templateRole,
    this.currentVersionId,
    this.forkedFromTemplateId,
    this.ownerId,
    this.isOfficial = false,
    this.isFeatured = false,
  });

  factory SeedTemplateListItem.fromJson(Map<String, dynamic> json) =>
      SeedTemplateListItem(
        id: (json['id'] ?? '').toString(),
        packId: (json['pack_id'] ?? '').toString(),
        name: (json['name'] ?? '').toString(),
        templateRole: (json['template_role'] ?? 'default').toString(),
        currentVersionId: json['current_version_id'] as String?,
        forkedFromTemplateId: json['forked_from_template_id'] as String?,
        ownerId: json['owner_id'] as String?,
        isOfficial: json['is_official'] == true,
        isFeatured: json['is_featured'] == true,
      );

  final String id;
  final String packId;
  final String name;
  final String templateRole;
  final String? currentVersionId;
  final String? forkedFromTemplateId;
  final String? ownerId;
  final bool isOfficial;
  final bool isFeatured;
}

class SeedTemplateVersion {
  SeedTemplateVersion({
    required this.id,
    required this.templateId,
    required this.versionNo,
    required this.status,
    required this.body,
    this.changeLog,
    this.variablesSchema,
    this.promotionState,
    this.qualityGateReport,
    this.moderationReport,
  });

  factory SeedTemplateVersion.fromJson(Map<String, dynamic> json) =>
      SeedTemplateVersion(
        id: (json['id'] ?? '').toString(),
        templateId: (json['template_id'] ?? '').toString(),
        versionNo: (json['version_no'] as num?)?.toInt() ?? 1,
        status: (json['status'] ?? 'draft').toString(),
        body: (json['body'] ?? '').toString(),
        changeLog: json['change_log'] as String?,
        variablesSchema: json['variables_schema'] as Map<String, dynamic>?,
        promotionState: json['promotion_state']?.toString(),
        qualityGateReport: json['quality_gate_report'] as Map<String, dynamic>?,
        moderationReport: json['moderation_report'] as Map<String, dynamic>?,
      );

  final String id;
  final String templateId;
  final int versionNo;
  final String status;
  final String body;
  final String? changeLog;
  final Map<String, dynamic>? variablesSchema;
  final String? promotionState;
  final Map<String, dynamic>? qualityGateReport;
  final Map<String, dynamic>? moderationReport;
}

class SeedTemplateDetail {
  SeedTemplateDetail({
    required this.id,
    required this.packId,
    required this.name,
    required this.templateRole,
    this.currentVersionId,
    this.currentVersion,
    this.forkedFromTemplateId,
    this.ownerId,
    this.isOfficial = false,
    this.isFeatured = false,
  });

  factory SeedTemplateDetail.fromJson(Map<String, dynamic> json) {
    final currentVersionRaw = json['current_version'];
    return SeedTemplateDetail(
      id: (json['id'] ?? '').toString(),
      packId: (json['pack_id'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      templateRole: (json['template_role'] ?? 'default').toString(),
      currentVersionId: json['current_version_id'] as String?,
      forkedFromTemplateId: json['forked_from_template_id'] as String?,
      ownerId: json['owner_id'] as String?,
      isOfficial: json['is_official'] == true,
      isFeatured: json['is_featured'] == true,
      currentVersion: currentVersionRaw is Map<String, dynamic>
          ? SeedTemplateVersion.fromJson(currentVersionRaw)
          : null,
    );
  }

  final String id;
  final String packId;
  final String name;
  final String templateRole;
  final String? currentVersionId;
  final SeedTemplateVersion? currentVersion;
  final String? forkedFromTemplateId;
  final String? ownerId;
  final bool isOfficial;
  final bool isFeatured;
}

class SeedTemplateSubscription {
  SeedTemplateSubscription({
    required this.id,
    required this.templateId,
    required this.userId,
    required this.priority,
    required this.isEnabled,
  });

  factory SeedTemplateSubscription.fromJson(Map<String, dynamic> json) =>
      SeedTemplateSubscription(
        id: (json['id'] ?? '').toString(),
        templateId: (json['template_id'] ?? '').toString(),
        userId: (json['user_id'] ?? '').toString(),
        priority: (json['priority'] as num?)?.toInt() ?? 0,
        isEnabled: json['is_enabled'] != false,
      );

  final String id;
  final String templateId;
  final String userId;
  final int priority;
  final bool isEnabled;
}

class SeedTemplateInstantiateResult {
  SeedTemplateInstantiateResult({
    required this.templateId,
    required this.templateVersionId,
    required this.seedTemplatePack,
    required this.seedTemplateSource,
    required this.renderedBody,
    this.unresolvedVariables = const [],
    this.metadata = const {},
  });

  factory SeedTemplateInstantiateResult.fromJson(Map<String, dynamic> json) =>
      SeedTemplateInstantiateResult(
        templateId: (json['template_id'] ?? '').toString(),
        templateVersionId: (json['template_version_id'] ?? '').toString(),
        seedTemplatePack: (json['seed_template_pack'] ?? '').toString(),
        seedTemplateSource: (json['seed_template_source'] ?? '').toString(),
        renderedBody: (json['rendered_body'] ?? '').toString(),
        unresolvedVariables: (json['unresolved_variables'] is List)
            ? (json['unresolved_variables'] as List).map((e) => '$e').toList()
            : const [],
        metadata: _normalizeMetadata(json['metadata']),
      );

  final String templateId;
  final String templateVersionId;
  final String seedTemplatePack;
  final String seedTemplateSource;
  final String renderedBody;
  final List<String> unresolvedVariables;
  final Map<String, dynamic> metadata;
}

double? _asDouble(dynamic value) {
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value);
  }
  return null;
}

Map<String, dynamic> _normalizeMetadata(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is String && value.isNotEmpty) {
    try {
      final decoded = jsonDecode(value);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
    } catch (_) {}
  }
  return const <String, dynamic>{};
}
