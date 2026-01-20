class EvidenceRefModel {
  EvidenceRefModel({
    required this.type,
    required this.id,
    this.schemaVersion,
    this.userDeleted = false,
  });

  factory EvidenceRefModel.fromJson(Map<String, dynamic> json) =>
      EvidenceRefModel(
        type: json['type'] as String? ?? '',
        id: json['id'] as String? ?? '',
        schemaVersion: json['schema_version'] as String?,
        userDeleted: json['user_deleted'] as bool? ?? false,
      );

  final String type;
  final String id;
  final String? schemaVersion;
  final bool userDeleted;

  Map<String, dynamic> toJson() => {
        'type': type,
        'id': id,
        'schema_version': schemaVersion,
        'user_deleted': userDeleted,
      };
}

class MemoryPreferenceItem {
  MemoryPreferenceItem({
    required this.id,
    required this.prefKey,
    required this.prefValue,
    required this.version,
    required this.evidenceMissing,
    required this.evidenceRefs,
    required this.evidenceScore,
    required this.correctionCount,
    this.confidence,
    this.updatedAt,
    this.retractedAt,
  });

  factory MemoryPreferenceItem.fromJson(Map<String, dynamic> json) =>
      MemoryPreferenceItem(
        id: json['id'] as String? ?? '',
        prefKey: json['pref_key'] as String? ?? '',
        prefValue: json['pref_value'],
        version: json['version'] as int? ?? 0,
        confidence: (json['confidence'] as num?)?.toDouble(),
        updatedAt: _parseDate(json['updated_at']),
        evidenceMissing: json['evidence_missing'] as bool? ?? false,
        evidenceRefs: _parseEvidenceRefs(json['evidence_refs']),
        evidenceScore: (json['evidence_score'] as num?)?.toDouble() ?? 0.0,
        correctionCount: json['correction_count'] as int? ?? 0,
        retractedAt: _parseDate(json['retracted_at']),
      );

  final String id;
  final String prefKey;
  final dynamic prefValue;
  final int version;
  final double? confidence;
  final DateTime? updatedAt;
  final bool evidenceMissing;
  final List<EvidenceRefModel> evidenceRefs;
  final double evidenceScore;
  final int correctionCount;
  final DateTime? retractedAt;
}

class MemoryPreferenceHistoryItem {
  MemoryPreferenceHistoryItem({
    required this.id,
    required this.prefKey,
    required this.prefValue,
    required this.version,
    required this.evidenceMissing,
    required this.evidenceRefs,
    required this.evidenceScore,
    required this.correctionCount,
    this.confidence,
    this.replacedById,
    this.createdAt,
    this.updatedAt,
    this.retractedAt,
  });

  factory MemoryPreferenceHistoryItem.fromJson(Map<String, dynamic> json) =>
      MemoryPreferenceHistoryItem(
        id: json['id'] as String? ?? '',
        prefKey: json['pref_key'] as String? ?? '',
        prefValue: json['pref_value'],
        version: json['version'] as int? ?? 0,
        confidence: (json['confidence'] as num?)?.toDouble(),
        replacedById: json['replaced_by_id'] as String?,
        createdAt: _parseDate(json['created_at']),
        updatedAt: _parseDate(json['updated_at']),
        evidenceMissing: json['evidence_missing'] as bool? ?? false,
        evidenceRefs: _parseEvidenceRefs(json['evidence_refs']),
        evidenceScore: (json['evidence_score'] as num?)?.toDouble() ?? 0.0,
        correctionCount: json['correction_count'] as int? ?? 0,
        retractedAt: _parseDate(json['retracted_at']),
      );

  final String id;
  final String prefKey;
  final dynamic prefValue;
  final int version;
  final double? confidence;
  final String? replacedById;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final bool evidenceMissing;
  final List<EvidenceRefModel> evidenceRefs;
  final double evidenceScore;
  final int correctionCount;
  final DateTime? retractedAt;
}

class MemoryGoalItem {
  MemoryGoalItem({
    required this.id,
    required this.title,
    required this.status,
    required this.evidenceMissing,
    required this.evidenceRefs,
    required this.evidenceScore,
    required this.correctionCount,
    this.targetDate,
    this.expiresAt,
    this.updatedAt,
    this.retractedAt,
  });

  factory MemoryGoalItem.fromJson(Map<String, dynamic> json) => MemoryGoalItem(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        status: json['status'] as String? ?? '',
        targetDate: _parseDate(json['target_date']),
        expiresAt: _parseDate(json['expires_at']),
        updatedAt: _parseDate(json['updated_at']),
        evidenceMissing: json['evidence_missing'] as bool? ?? false,
        evidenceRefs: _parseEvidenceRefs(json['evidence_refs']),
        evidenceScore: (json['evidence_score'] as num?)?.toDouble() ?? 0.0,
        correctionCount: json['correction_count'] as int? ?? 0,
        retractedAt: _parseDate(json['retracted_at']),
      );

  final String id;
  final String title;
  final String status;
  final DateTime? targetDate;
  final DateTime? expiresAt;
  final DateTime? updatedAt;
  final bool evidenceMissing;
  final List<EvidenceRefModel> evidenceRefs;
  final double evidenceScore;
  final int correctionCount;
  final DateTime? retractedAt;
}

class EpisodicMemoryItem {
  EpisodicMemoryItem({
    required this.id,
    required this.summary,
    required this.sourceType,
    required this.evidenceMissing,
    required this.evidenceRefs,
    required this.evidenceScore,
    required this.correctionCount,
    this.sourceId,
    this.occurredAt,
    this.importanceScore,
    this.updatedAt,
    this.retractedAt,
  });

  factory EpisodicMemoryItem.fromJson(Map<String, dynamic> json) =>
      EpisodicMemoryItem(
        id: json['id'] as String? ?? '',
        summary: json['summary'] as String? ?? '',
        sourceType: json['source_type'] as String? ?? '',
        sourceId: json['source_id'] as String?,
        occurredAt: _parseDate(json['occurred_at']),
        importanceScore: (json['importance_score'] as num?)?.toDouble(),
        updatedAt: _parseDate(json['updated_at']),
        evidenceMissing: json['evidence_missing'] as bool? ?? false,
        evidenceRefs: _parseEvidenceRefs(json['evidence_refs']),
        evidenceScore: (json['evidence_score'] as num?)?.toDouble() ?? 0.0,
        correctionCount: json['correction_count'] as int? ?? 0,
        retractedAt: _parseDate(json['retracted_at']),
      );

  final String id;
  final String summary;
  final String sourceType;
  final String? sourceId;
  final DateTime? occurredAt;
  final double? importanceScore;
  final DateTime? updatedAt;
  final bool evidenceMissing;
  final List<EvidenceRefModel> evidenceRefs;
  final double evidenceScore;
  final int correctionCount;
  final DateTime? retractedAt;
}

class MemoryCorrectionResult {
  MemoryCorrectionResult({
    required this.id,
    required this.evidenceRefs,
    required this.evidenceMissing,
    required this.evidenceScore,
    required this.correctionCount,
    this.confidence,
    this.retractedAt,
  });

  factory MemoryCorrectionResult.fromJson(Map<String, dynamic> json) =>
      MemoryCorrectionResult(
        id: json['id'] as String? ?? '',
        evidenceRefs: _parseEvidenceRefs(json['evidence_refs']),
        evidenceMissing: json['evidence_missing'] as bool? ?? false,
        evidenceScore: (json['evidence_score'] as num?)?.toDouble() ?? 0.0,
        correctionCount: json['correction_count'] as int? ?? 0,
        confidence: (json['confidence'] as num?)?.toDouble(),
        retractedAt: _parseDate(json['retracted_at']),
      );

  final String id;
  final List<EvidenceRefModel> evidenceRefs;
  final bool evidenceMissing;
  final double evidenceScore;
  final int correctionCount;
  final double? confidence;
  final DateTime? retractedAt;
}

class MemorySettingsModel {
  MemorySettingsModel({
    required this.enabled,
    required this.allowPreferences,
    required this.allowGoals,
    required this.allowEpisodic,
    required this.captureLevel,
    required this.blockedPrefKeys,
    required this.blockedSources,
  });

  factory MemorySettingsModel.fromJson(Map<String, dynamic> json) =>
      MemorySettingsModel(
        enabled: json['enabled'] as bool? ?? true,
        allowPreferences: json['allow_preferences'] as bool? ?? true,
        allowGoals: json['allow_goals'] as bool? ?? true,
        allowEpisodic: json['allow_episodic'] as bool? ?? true,
        captureLevel: json['capture_level'] as String? ?? 'medium',
        blockedPrefKeys: (json['blocked_pref_keys'] as List<dynamic>? ?? [])
            .whereType<String>()
            .toList(),
        blockedSources: (json['blocked_sources'] as List<dynamic>? ?? [])
            .whereType<String>()
            .toList(),
      );

  final bool enabled;
  final bool allowPreferences;
  final bool allowGoals;
  final bool allowEpisodic;
  final String captureLevel;
  final List<String> blockedPrefKeys;
  final List<String> blockedSources;

  Map<String, dynamic> toJson() => {
        'enabled': enabled,
        'allow_preferences': allowPreferences,
        'allow_goals': allowGoals,
        'allow_episodic': allowEpisodic,
        'capture_level': captureLevel,
        'blocked_pref_keys': blockedPrefKeys,
        'blocked_sources': blockedSources,
      };
}

class EvidenceResolveItem {
  EvidenceResolveItem({
    required this.type,
    required this.id,
    required this.status,
    this.redactionReason,
    this.payload,
  });

  factory EvidenceResolveItem.fromJson(Map<String, dynamic> json) {
    final payload = <String, dynamic>{};
    const payloadKeys = ['event', 'state', 'error', 'concept', 'strategy', 'task', 'summary'];
    for (final key in payloadKeys) {
      if (json[key] != null) {
        payload[key] = json[key] as Map<String, dynamic>;
      }
    }
    return EvidenceResolveItem(
      type: json['type'] as String? ?? '',
      id: json['id'] as String? ?? '',
      status: json['status'] as String? ?? '',
      redactionReason: json['redaction_reason'] as String?,
      payload: payload.isEmpty ? null : payload,
    );
  }

  final String type;
  final String id;
  final String status;
  final String? redactionReason;
  final Map<String, dynamic>? payload;
}

DateTime? _parseDate(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value;
  }
  return DateTime.tryParse(value.toString());
}

List<EvidenceRefModel> _parseEvidenceRefs(dynamic value) {
  if (value is List) {
    return value
        .whereType<Map<String, dynamic>>()
        .map(EvidenceRefModel.fromJson)
        .toList();
  }
  return [];
}
