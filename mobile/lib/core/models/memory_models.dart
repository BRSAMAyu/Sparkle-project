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
    this.sourceLabel,
    this.sourceType,
    this.explanation,
    this.adjustable = false,
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
        sourceLabel: json['source_label'] as String?,
        sourceType: json['source_type'] as String?,
        explanation: json['explanation'] as String?,
        adjustable: json['adjustable'] as bool? ?? false,
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
  final String? sourceLabel;
  final String? sourceType;
  final String? explanation;
  final bool adjustable;
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
    this.sourceLane,
    this.subjectType,
    this.occurredAt,
    this.dueAt,
    this.resolvedAt,
    this.importanceScore,
    this.confidence,
    this.evidenceToken,
    this.decayPolicy,
    this.declarationLabel,
    this.updatedAt,
    this.retractedAt,
    this.revokedAt,
  });

  factory EpisodicMemoryItem.fromJson(Map<String, dynamic> json) =>
      EpisodicMemoryItem(
        id: json['id'] as String? ?? '',
        summary: json['summary'] as String? ?? '',
        sourceType: json['source_type'] as String? ?? '',
        sourceId: json['source_id'] as String?,
        sourceLane: json['source_lane'] as String?,
        subjectType: json['subject_type'] as String?,
        occurredAt: _parseDate(json['occurred_at']),
        dueAt: _parseDate(json['due_at']),
        resolvedAt: _parseDate(json['resolved_at']),
        importanceScore: (json['importance_score'] as num?)?.toDouble(),
        confidence: (json['confidence'] as num?)?.toDouble(),
        evidenceToken: json['evidence_token'] as String?,
        decayPolicy: json['decay_policy'] as String?,
        declarationLabel: json['declaration_label'] as String?,
        updatedAt: _parseDate(json['updated_at']),
        evidenceMissing: json['evidence_missing'] as bool? ?? false,
        evidenceRefs: _parseEvidenceRefs(json['evidence_refs']),
        evidenceScore: (json['evidence_score'] as num?)?.toDouble() ?? 0.0,
        correctionCount: json['correction_count'] as int? ?? 0,
        retractedAt: _parseDate(json['retracted_at']),
        revokedAt: _parseDate(json['revoked_at']),
      );

  final String id;
  final String summary;
  final String sourceType;
  final String? sourceId;
  final String? sourceLane;
  final String? subjectType;
  final DateTime? occurredAt;
  final DateTime? dueAt;
  final DateTime? resolvedAt;
  final double? importanceScore;
  final double? confidence;
  final String? evidenceToken;
  final String? decayPolicy;
  final String? declarationLabel;
  final DateTime? updatedAt;
  final bool evidenceMissing;
  final List<EvidenceRefModel> evidenceRefs;
  final double evidenceScore;
  final int correctionCount;
  final DateTime? retractedAt;
  final DateTime? revokedAt;
}

class PendingCommitmentItem {
  PendingCommitmentItem({
    required this.id,
    required this.summary,
    required this.dueAt,
    required this.subjectType,
    this.evidenceToken,
    this.resolvedAt,
  });

  factory PendingCommitmentItem.fromJson(Map<String, dynamic> json) =>
      PendingCommitmentItem(
        id: json['id'] as String? ?? '',
        summary: json['summary'] as String? ?? '',
        dueAt: _parseDate(json['due_at']) ??
            DateTime.fromMillisecondsSinceEpoch(0),
        subjectType: json['subject_type'] as String? ?? 'commitment',
        evidenceToken: json['evidence_token'] as String?,
        resolvedAt: _parseDate(json['resolved_at']),
      );

  final String id;
  final String summary;
  final DateTime dueAt;
  final String subjectType;
  final String? evidenceToken;
  final DateTime? resolvedAt;
}

class RecentSceneSummaryItem {
  RecentSceneSummaryItem({
    required this.sceneId,
    required this.title,
    required this.timeStart,
    required this.timeEnd,
    required this.memberCount,
    required this.qualityScore,
  });

  factory RecentSceneSummaryItem.fromJson(Map<String, dynamic> json) =>
      RecentSceneSummaryItem(
        sceneId: json['scene_id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        timeStart:
            _parseDate(json['time_start']) ?? DateTime.fromMillisecondsSinceEpoch(0),
        timeEnd:
            _parseDate(json['time_end']) ?? DateTime.fromMillisecondsSinceEpoch(0),
        memberCount: json['member_count'] as int? ?? 0,
        qualityScore: (json['quality_score'] as num?)?.toDouble() ?? 0.0,
      );

  final String sceneId;
  final String title;
  final DateTime timeStart;
  final DateTime timeEnd;
  final int memberCount;
  final double qualityScore;
}

class ForesightConfidenceItem {
  ForesightConfidenceItem({
    required this.dim,
    required this.confidence,
  });

  factory ForesightConfidenceItem.fromJson(Map<String, dynamic> json) =>
      ForesightConfidenceItem(
        dim: json['dim'] as String? ?? '',
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      );

  final String dim;
  final double confidence;
}

class ForesightHintSummaryItem {
  ForesightHintSummaryItem({
    required this.deviationCount,
    required this.attractorConfidences,
    this.hintText,
    this.generatedAt,
  });

  factory ForesightHintSummaryItem.fromJson(Map<String, dynamic> json) =>
      ForesightHintSummaryItem(
        hintText: json['hint_text'] as String?,
        generatedAt: _parseDate(json['generated_at']),
        deviationCount: json['deviation_count'] as int? ?? 0,
        attractorConfidences:
            (json['attractor_confidences'] as List<dynamic>? ?? [])
                .whereType<Map<String, dynamic>>()
                .map(ForesightConfidenceItem.fromJson)
                .toList(),
      );

  final String? hintText;
  final DateTime? generatedAt;
  final int deviationCount;
  final List<ForesightConfidenceItem> attractorConfidences;
}

class UnresolvedConflictCandidate {
  UnresolvedConflictCandidate({
    required this.summary,
    required this.lane,
    this.recordId,
    this.evidenceToken,
  });

  factory UnresolvedConflictCandidate.fromJson(Map<String, dynamic> json) =>
      UnresolvedConflictCandidate(
        recordId: json['record_id'] as String?,
        summary: json['summary'] as String? ?? '',
        lane: json['lane'] as String? ?? '',
        evidenceToken: json['evidence_token'] as String?,
      );

  final String? recordId;
  final String summary;
  final String lane;
  final String? evidenceToken;
}

class UnresolvedConflictItem {
  UnresolvedConflictItem({
    required this.id,
    required this.conflictKey,
    required this.status,
    required this.leftCandidate,
    required this.rightCandidate,
    this.selectedSide,
    this.resolutionReason,
    this.surfacedAt,
    this.resolvedAt,
  });

  factory UnresolvedConflictItem.fromJson(Map<String, dynamic> json) =>
      UnresolvedConflictItem(
        id: json['id'] as String? ?? '',
        conflictKey: json['conflict_key'] as String? ?? '',
        status: json['status'] as String? ?? 'pending_user',
        selectedSide: json['selected_side'] as String?,
        resolutionReason: json['resolution_reason'] as String?,
        surfacedAt: _parseDate(json['surfaced_at']),
        resolvedAt: _parseDate(json['resolved_at']),
        leftCandidate: UnresolvedConflictCandidate.fromJson(
          (json['left_candidate'] as Map<String, dynamic>? ?? const {}),
        ),
        rightCandidate: UnresolvedConflictCandidate.fromJson(
          (json['right_candidate'] as Map<String, dynamic>? ?? const {}),
        ),
      );

  final String id;
  final String conflictKey;
  final String status;
  final String? selectedSide;
  final String? resolutionReason;
  final DateTime? surfacedAt;
  final DateTime? resolvedAt;
  final UnresolvedConflictCandidate leftCandidate;
  final UnresolvedConflictCandidate rightCandidate;
}

class WorkingMemoryItem {
  WorkingMemoryItem({
    required this.id,
    required this.summary,
    required this.subjectType,
    required this.mentionCount,
    required this.salienceScore,
    required this.sourceTurnIds,
    required this.evidenceToken,
    required this.confirmationStatus,
    required this.rejected,
    required this.lastSeenAt,
    this.consolidatedToL1Id,
  });

  factory WorkingMemoryItem.fromJson(Map<String, dynamic> json) =>
      WorkingMemoryItem(
        id: json['id'] as String? ?? '',
        summary: json['summary'] as String? ?? '',
        subjectType: json['subject_type'] as String? ?? 'self',
        mentionCount: json['mention_count'] as int? ?? 0,
        salienceScore: (json['salience_score'] as num?)?.toDouble() ?? 0.0,
        sourceTurnIds: (json['source_turn_ids'] as List<dynamic>? ?? [])
            .whereType<String>()
            .toList(),
        evidenceToken: json['evidence_token'] as String? ?? '',
        confirmationStatus: json['confirmation_status'] as String? ?? 'none',
        consolidatedToL1Id: json['consolidated_to_l1_id'] as String?,
        rejected: json['rejected'] as bool? ?? false,
        lastSeenAt: _parseDate(json['last_seen_at']) ??
            DateTime.fromMillisecondsSinceEpoch(0),
      );

  final String id;
  final String summary;
  final String subjectType;
  final int mentionCount;
  final double salienceScore;
  final List<String> sourceTurnIds;
  final String evidenceToken;
  final String confirmationStatus;
  final String? consolidatedToL1Id;
  final bool rejected;
  final DateTime lastSeenAt;
}

class WorkingMemorySessionModel {
  WorkingMemorySessionModel({
    required this.sessionId,
    required this.items,
  });

  factory WorkingMemorySessionModel.fromJson(Map<String, dynamic> json) =>
      WorkingMemorySessionModel(
        sessionId: json['session_id'] as String?,
        items: (json['items'] as List<dynamic>? ?? [])
            .whereType<Map<String, dynamic>>()
            .map(WorkingMemoryItem.fromJson)
            .toList(),
      );

  final String? sessionId;
  final List<WorkingMemoryItem> items;
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
    required this.allowInferredEpisodic,
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
        allowInferredEpisodic: json['allow_inferred_episodic'] as bool? ?? true,
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
  final bool allowInferredEpisodic;
  final String captureLevel;
  final List<String> blockedPrefKeys;
  final List<String> blockedSources;

  Map<String, dynamic> toJson() => {
        'enabled': enabled,
        'allow_preferences': allowPreferences,
        'allow_goals': allowGoals,
        'allow_episodic': allowEpisodic,
        'allow_inferred_episodic': allowInferredEpisodic,
        'capture_level': captureLevel,
        'blocked_pref_keys': blockedPrefKeys,
        'blocked_sources': blockedSources,
      };
}

class PushOptInSettingsModel {
  PushOptInSettingsModel({
    required this.enabled,
    required this.allowCommitmentFollowUp,
    required this.allowEngagementRecovery,
    required this.quietHoursStart,
    required this.quietHoursEnd,
    required this.timezone,
  });

  factory PushOptInSettingsModel.fromJson(Map<String, dynamic> json) =>
      PushOptInSettingsModel(
        enabled: json['enabled'] as bool? ?? false,
        allowCommitmentFollowUp:
            json['allow_commitment_follow_up'] as bool? ?? false,
        allowEngagementRecovery:
            json['allow_engagement_recovery'] as bool? ?? false,
        quietHoursStart: json['quiet_hours_start'] as String? ?? '22:00',
        quietHoursEnd: json['quiet_hours_end'] as String? ?? '08:00',
        timezone: json['timezone'] as String? ?? 'Asia/Shanghai',
      );

  final bool enabled;
  final bool allowCommitmentFollowUp;
  final bool allowEngagementRecovery;
  final String quietHoursStart;
  final String quietHoursEnd;
  final String timezone;

  Map<String, dynamic> toJson() => {
        'enabled': enabled,
        'allow_commitment_follow_up': allowCommitmentFollowUp,
        'allow_engagement_recovery': allowEngagementRecovery,
        'quiet_hours_start': quietHoursStart,
        'quiet_hours_end': quietHoursEnd,
        'timezone': timezone,
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
    const payloadKeys = [
      'event',
      'chat_turn',
      'state',
      'error',
      'practice_outcome',
      'concept',
      'strategy',
      'task',
      'summary',
    ];
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
