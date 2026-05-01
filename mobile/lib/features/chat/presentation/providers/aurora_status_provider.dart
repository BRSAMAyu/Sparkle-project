import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

// ── Predicted Reply Option models ─────────────────────────────────────────────

class AuroraModelWriteEffect {
  const AuroraModelWriteEffect({
    required this.target,
    required this.fieldKey,
    required this.fieldValue,
    required this.operation,
    required this.requiresPersistence,
  });

  factory AuroraModelWriteEffect.fromJson(Map<String, dynamic> json) {
    return AuroraModelWriteEffect(
      target: json['target'] as String? ?? 'none',
      fieldKey: json['field_key'] as String? ?? '',
      fieldValue: json['field_value'],
      operation: json['operation'] as String? ?? 'set',
      requiresPersistence: json['requires_persistence'] as bool? ?? true,
    );
  }

  final String target;
  final String fieldKey;
  final dynamic fieldValue;
  final String operation;
  final bool requiresPersistence;

  Map<String, dynamic> toJson() => {
        'target': target,
        'field_key': fieldKey,
        'field_value': fieldValue,
        'operation': operation,
        'requires_persistence': requiresPersistence,
      };
}

class AuroraPredictedReplyOption {
  const AuroraPredictedReplyOption({
    required this.id,
    required this.label,
    required this.semanticValue,
    required this.replyType,
    required this.confidence,
    required this.modelWriteEffect,
    required this.isDisconfirming,
    required this.isFreeform,
    required this.contextSource,
    required this.telemetryId,
  });

  factory AuroraPredictedReplyOption.fromJson(Map<String, dynamic> json) {
    final rawEffect = json['model_write_effect'];
    return AuroraPredictedReplyOption(
      id: json['id'] as String? ?? '',
      label: json['label'] as String? ?? '',
      semanticValue: json['semantic_value'] as String? ?? '',
      replyType: json['reply_type'] as String? ?? 'assumption_check',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      modelWriteEffect: rawEffect is Map<String, dynamic>
          ? AuroraModelWriteEffect.fromJson(rawEffect)
          : rawEffect is Map
              ? AuroraModelWriteEffect.fromJson(
                  Map<String, dynamic>.from(rawEffect))
              : null,
      isDisconfirming: json['is_disconfirming'] as bool? ?? false,
      isFreeform: json['is_freeform'] as bool? ?? false,
      contextSource: json['context_source'] as String? ?? '',
      telemetryId: json['telemetry_id'] as String? ?? '',
    );
  }

  final String id;
  final String label;
  final String semanticValue;
  final String
      replyType; // fact_confirm | assumption_check | strategy_choice | relational_signal | freeform
  final double confidence;
  final AuroraModelWriteEffect? modelWriteEffect;
  final bool isDisconfirming;
  final bool isFreeform;
  final String contextSource;
  final String telemetryId;

  Map<String, dynamic> toJson() => {
        'id': id,
        'label': label,
        'semantic_value': semanticValue,
        'reply_type': replyType,
        'confidence': confidence,
        'model_write_effect': modelWriteEffect?.toJson(),
        'is_disconfirming': isDisconfirming,
        'is_freeform': isFreeform,
        'context_source': contextSource,
        'telemetry_id': telemetryId,
      };
}

class AuroraPredictedReplyGroup {
  const AuroraPredictedReplyGroup({
    required this.groupId,
    required this.question,
    required this.questionType,
    required this.contextNote,
    required this.options,
  });

  factory AuroraPredictedReplyGroup.fromJson(Map<String, dynamic> json) {
    final rawOptions = json['options'] as List<dynamic>? ?? const [];
    return AuroraPredictedReplyGroup(
      groupId: json['group_id'] as String? ?? '',
      question: json['question'] as String? ?? '',
      questionType: json['question_type'] as String? ?? 'assumption_check',
      contextNote: json['context_note'] as String? ?? '',
      options: rawOptions
          .whereType<Map<String, dynamic>>()
          .map(AuroraPredictedReplyOption.fromJson)
          .toList(),
    );
  }

  final String groupId;
  final String question;
  final String questionType;
  final String contextNote;
  final List<AuroraPredictedReplyOption> options;

  /// Primary options (non-freeform), sorted by confidence descending.
  List<AuroraPredictedReplyOption> get primaryOptions =>
      options.where((o) => !o.isFreeform).toList()
        ..sort((a, b) => b.confidence.compareTo(a.confidence));

  /// The freeform correction option (always last).
  AuroraPredictedReplyOption? get freeformOption =>
      options.where((o) => o.isFreeform).firstOrNull;

  Map<String, dynamic> toJson() => {
        'group_id': groupId,
        'question': question,
        'question_type': questionType,
        'context_note': contextNote,
        'options': options.map((option) => option.toJson()).toList(),
      };
}

// ── Existing models ───────────────────────────────────────────────────────────

class AuroraFacetSnapshot {
  const AuroraFacetSnapshot({
    required this.key,
    required this.label,
    required this.status,
    required this.summary,
    required this.confidence,
    required this.freshnessSeconds,
    required this.signalCount,
    required this.signals,
    required this.meta,
  });

  factory AuroraFacetSnapshot.fromJson(Map<String, dynamic> json) {
    final rawSignals = json['signals'] as List<dynamic>? ?? const [];
    final rawMeta = json['meta'];
    return AuroraFacetSnapshot(
      key: json['key'] as String? ?? '',
      label: json['label'] as String? ?? '',
      status: json['status'] as String? ?? 'missing',
      summary: json['summary'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble(),
      freshnessSeconds: (json['freshness_seconds'] as num?)?.toInt(),
      signalCount: (json['signal_count'] as num?)?.toInt() ?? 0,
      signals: rawSignals
          .map((item) => '$item')
          .where((item) => item.isNotEmpty)
          .toList(),
      meta: rawMeta is Map<String, dynamic>
          ? rawMeta
          : rawMeta is Map
              ? Map<String, dynamic>.from(rawMeta)
              : const <String, dynamic>{},
    );
  }

  final String key;
  final String label;
  final String status;
  final String summary;
  final double? confidence;
  final int? freshnessSeconds;
  final int signalCount;
  final List<String> signals;
  final Map<String, dynamic> meta;

  bool get isReady => status == 'ready';
  bool get isRecalibrating => status == 'recalibrating';
  bool get isActive => status != 'missing';
}

class AuroraControlSurfaceSnapshot {
  const AuroraControlSurfaceSnapshot({
    required this.auroraActive,
    required this.runtimeEnabled,
    required this.overallStatus,
    required this.energyLevel,
    required this.summary,
    required this.readyCount,
    required this.activeCount,
    required this.totalCount,
    required this.conversationId,
    required this.requestedConversationId,
    required this.sceneAlignment,
    required this.timeContext,
    required this.surface,
    required this.updatedAt,
    required this.facets,
    required this.wakeEligibility,
    required this.predictedReplyOptions,
    required this.fetchedAt,
    this.lastCorrectionEffect = const AuroraCorrectionEffect.empty(),
    this.taskHealth = const AuroraTaskHealth.empty(),
    this.statusEvidenceChain = const [],
    this.memoryReferences = const [],
    this.nextStepSuggestion = '',
    this.selfEvaluation = const AuroraSelfEvaluation.empty(),
  });

  factory AuroraControlSurfaceSnapshot.fromJson(Map<String, dynamic> json) {
    final progress = json['progress'] is Map<String, dynamic>
        ? json['progress'] as Map<String, dynamic>
        : json['progress'] is Map
            ? Map<String, dynamic>.from(json['progress'] as Map)
            : const <String, dynamic>{};
    final rawFacets = json['facets'] as List<dynamic>? ?? const [];
    final rawWake = json['wake_eligibility'] is Map<String, dynamic>
        ? json['wake_eligibility'] as Map<String, dynamic>
        : json['wake_eligibility'] is Map
            ? Map<String, dynamic>.from(json['wake_eligibility'] as Map)
            : const <String, dynamic>{};
    final rawOptions =
        json['predicted_reply_options'] as List<dynamic>? ?? const [];
    final rawEvidence =
        json['status_evidence_chain'] as List<dynamic>? ?? const [];
    final rawMemory = json['memory_references'] as List<dynamic>? ?? const [];
    return AuroraControlSurfaceSnapshot(
      auroraActive: json['aurora_active'] as bool? ?? false,
      runtimeEnabled: json['runtime_enabled'] as bool? ?? false,
      overallStatus: json['overall_status'] as String? ?? 'sensing',
      energyLevel: json['energy_level'] as String? ?? 'L0',
      summary: json['summary'] as String? ?? '',
      readyCount: (progress['ready_count'] as num?)?.toInt() ?? 0,
      activeCount: (progress['active_count'] as num?)?.toInt() ?? 0,
      totalCount: (progress['total'] as num?)?.toInt() ?? rawFacets.length,
      conversationId: json['conversation_id'] as String?,
      requestedConversationId: json['requested_conversation_id'] as String?,
      sceneAlignment: json['scene_alignment'] as String? ?? 'matched',
      timeContext: AuroraTimeContext.fromJson(json['time_context']),
      lastCorrectionEffect:
          AuroraCorrectionEffect.fromJson(json['last_correction_effect']),
      surface: json['surface'] as String?,
      updatedAt: _tryParseDateTime(json['updated_at']),
      facets: rawFacets
          .whereType<Map<String, dynamic>>()
          .map(AuroraFacetSnapshot.fromJson)
          .toList(),
      wakeEligibility: AuroraWakeEligibility.fromJson(rawWake),
      predictedReplyOptions: rawOptions
          .whereType<Map<String, dynamic>>()
          .map(AuroraPredictedReplyGroup.fromJson)
          .toList(),
      fetchedAt: DateTime.now(),
      taskHealth: AuroraTaskHealth.fromJson(json['task_health']),
      statusEvidenceChain: rawEvidence
          .map((item) => '$item'.trim())
          .where((item) => item.isNotEmpty)
          .toList(),
      memoryReferences: rawMemory
          .map((item) => '$item'.trim())
          .where((item) => item.isNotEmpty)
          .toList(),
      nextStepSuggestion: json['next_step_suggestion'] as String? ?? '',
      selfEvaluation: AuroraSelfEvaluation.fromJson(json['self_evaluation']),
    );
  }

  final bool auroraActive;
  final bool runtimeEnabled;
  final String
      overallStatus; // 6-state: sensing/calibrated/risk_found/needs_confirm/calibration_available/cooling_down
  final String energyLevel; // L0-L3
  final String summary;
  final int readyCount;
  final int activeCount;
  final int totalCount;
  final String? conversationId;
  final String? requestedConversationId;
  final String sceneAlignment;
  final AuroraTimeContext timeContext;
  final AuroraCorrectionEffect lastCorrectionEffect;
  final String? surface;
  final DateTime? updatedAt;
  final List<AuroraFacetSnapshot> facets;
  final AuroraWakeEligibility wakeEligibility;
  final List<AuroraPredictedReplyGroup> predictedReplyOptions;
  final DateTime fetchedAt;
  final AuroraTaskHealth taskHealth;
  final List<String> statusEvidenceChain;
  final List<String> memoryReferences;
  final String nextStepSuggestion;
  final AuroraSelfEvaluation selfEvaluation;

  bool get isRecalibrating => overallStatus == 'risk_found';
  bool get isReady => overallStatus == 'calibrated';
  bool get isCoolingDown => overallStatus == 'cooling_down';
  bool get needsConfirm => overallStatus == 'needs_confirm';
  bool get canCalibrate => overallStatus == 'calibration_available';

  /// Returns the top predicted reply group for quick access, or null.
  AuroraPredictedReplyGroup? get topPredictedGroup =>
      predictedReplyOptions.isNotEmpty ? predictedReplyOptions.first : null;

  AuroraControlSurfaceSnapshot copyWith({
    AuroraCorrectionEffect? lastCorrectionEffect,
    DateTime? fetchedAt,
  }) =>
      AuroraControlSurfaceSnapshot(
        auroraActive: auroraActive,
        runtimeEnabled: runtimeEnabled,
        overallStatus: overallStatus,
        energyLevel: energyLevel,
        summary: summary,
        readyCount: readyCount,
        activeCount: activeCount,
        totalCount: totalCount,
        conversationId: conversationId,
        requestedConversationId: requestedConversationId,
        sceneAlignment: sceneAlignment,
        timeContext: timeContext,
        lastCorrectionEffect: lastCorrectionEffect ?? this.lastCorrectionEffect,
        surface: surface,
        updatedAt: updatedAt,
        facets: facets,
        wakeEligibility: wakeEligibility,
        predictedReplyOptions: predictedReplyOptions,
        fetchedAt: fetchedAt ?? this.fetchedAt,
        taskHealth: taskHealth,
        statusEvidenceChain: statusEvidenceChain,
        memoryReferences: memoryReferences,
        nextStepSuggestion: nextStepSuggestion,
        selfEvaluation: selfEvaluation,
      );
}

class AuroraTaskHealth {
  const AuroraTaskHealth({
    required this.visible,
    required this.status,
    required this.severity,
    required this.label,
    required this.subtitle,
    required this.trendLabel,
    required this.totalCount,
    required this.issueCount,
    required this.receipt,
  });

  const AuroraTaskHealth.empty()
      : visible = false,
        status = '',
        severity = 'neutral',
        label = '',
        subtitle = '',
        trendLabel = '',
        totalCount = 0,
        issueCount = 0,
        receipt = const <String, dynamic>{};

  factory AuroraTaskHealth.fromJson(dynamic raw) {
    final json = raw is Map<String, dynamic>
        ? raw
        : raw is Map
            ? Map<String, dynamic>.from(raw)
            : const <String, dynamic>{};
    final rawReceipt = json['receipt'];
    return AuroraTaskHealth(
      visible: json['visible'] as bool? ?? false,
      status: json['status'] as String? ?? '',
      severity: json['severity'] as String? ?? 'neutral',
      label: json['label'] as String? ?? '',
      subtitle: json['subtitle'] as String? ?? '',
      trendLabel: json['trend_label'] as String? ?? '',
      totalCount: (json['total_count'] as num?)?.toInt() ?? 0,
      issueCount: (json['issue_count'] as num?)?.toInt() ?? 0,
      receipt: rawReceipt is Map<String, dynamic>
          ? rawReceipt
          : rawReceipt is Map
              ? Map<String, dynamic>.from(rawReceipt)
              : const <String, dynamic>{},
    );
  }

  final bool visible;
  final String status;
  final String severity;
  final String label;
  final String subtitle;
  final String trendLabel;
  final int totalCount;
  final int issueCount;
  final Map<String, dynamic> receipt;

  bool get needsAttention => status == 'needs_attention';
}

class AuroraCorrectionEffect {
  const AuroraCorrectionEffect({
    required this.visible,
    required this.semanticValue,
    required this.action,
    required this.affectedStateKeys,
    required this.updatedAt,
  });

  const AuroraCorrectionEffect.empty()
      : visible = false,
        semanticValue = '',
        action = '',
        affectedStateKeys = const [],
        updatedAt = null;

  factory AuroraCorrectionEffect.fromJson(dynamic raw) {
    final json = raw is Map<String, dynamic>
        ? raw
        : raw is Map
            ? Map<String, dynamic>.from(raw)
            : const <String, dynamic>{};
    return AuroraCorrectionEffect(
      visible: json['visible'] as bool? ?? false,
      semanticValue: json['semantic_value'] as String? ?? '',
      action: json['action'] as String? ?? '',
      affectedStateKeys:
          (json['affected_state_keys'] as List<dynamic>? ?? const [])
              .map((item) => '$item')
              .where((item) => item.isNotEmpty)
              .toList(growable: false),
      updatedAt: _tryParseDateTime(json['updated_at']),
    );
  }

  final bool visible;
  final String semanticValue;
  final String action;
  final List<String> affectedStateKeys;
  final DateTime? updatedAt;
}

class AuroraSelfEvaluation {
  const AuroraSelfEvaluation({
    required this.confidence,
    required this.why,
    required this.risk,
  });

  const AuroraSelfEvaluation.empty()
      : confidence = null,
        why = '',
        risk = '';

  factory AuroraSelfEvaluation.fromJson(dynamic raw) {
    final json = raw is Map<String, dynamic>
        ? raw
        : raw is Map
            ? Map<String, dynamic>.from(raw)
            : const <String, dynamic>{};
    return AuroraSelfEvaluation(
      confidence: (json['confidence'] as num?)?.toDouble(),
      why: json['why'] as String? ?? '',
      risk: json['risk'] as String? ?? '',
    );
  }

  final double? confidence;
  final String why;
  final String risk;

  bool get hasContent =>
      confidence != null || why.trim().isNotEmpty || risk.trim().isNotEmpty;
}

class AuroraTimeContext {
  const AuroraTimeContext({
    required this.visible,
    required this.kind,
    required this.severity,
    required this.label,
    required this.subtitle,
    required this.action,
    required this.conflict,
  });

  factory AuroraTimeContext.fromJson(dynamic raw) {
    final json = raw is Map<String, dynamic>
        ? raw
        : raw is Map
            ? Map<String, dynamic>.from(raw)
            : const <String, dynamic>{};
    final rawConflict = json['conflict'];
    return AuroraTimeContext(
      visible: json['visible'] as bool? ?? false,
      kind: json['kind'] as String? ?? '',
      severity: json['severity'] as String? ?? 'neutral',
      label: json['label'] as String? ?? '',
      subtitle: json['subtitle'] as String? ?? '',
      action: json['action'] as String? ?? '',
      conflict: rawConflict is Map<String, dynamic>
          ? rawConflict
          : rawConflict is Map
              ? Map<String, dynamic>.from(rawConflict)
              : const <String, dynamic>{},
    );
  }

  final bool visible;
  final String kind;
  final String severity;
  final String label;
  final String subtitle;
  final String action;
  final Map<String, dynamic> conflict;

  bool get hasConflict => kind == 'time_conflict' || conflict.isNotEmpty;
}

class AuroraWakeEligibility {
  const AuroraWakeEligibility({
    required this.canUserWake,
    required this.userQuotaRemaining,
    required this.cooldownStatus,
    required this.cooldownRemainingMin,
    required this.wakeReasons,
    required this.recommendedSessionType,
    required this.estimatedDurationSec,
    required this.suggestedScope,
    required this.fallbackIfUnavailable,
  });

  factory AuroraWakeEligibility.fromJson(Map<String, dynamic> json) {
    return AuroraWakeEligibility(
      canUserWake: json['can_user_wake'] as bool? ?? false,
      userQuotaRemaining: (json['user_quota_remaining'] as num?)?.toInt() ?? 0,
      cooldownStatus: json['cooldown_status'] as String? ?? 'available',
      cooldownRemainingMin:
          (json['cooldown_remaining_min'] as num?)?.toInt() ?? 0,
      wakeReasons: (json['wake_reasons'] as List<dynamic>? ?? const [])
          .map((e) => '$e')
          .toList(),
      recommendedSessionType: json['recommended_session_type'] as String? ??
          'strategy_recalibration',
      estimatedDurationSec:
          (json['estimated_duration_sec'] as num?)?.toInt() ?? 240,
      suggestedScope: json['suggested_scope'] as String? ?? '',
      fallbackIfUnavailable:
          json['fallback_if_unavailable'] as String? ?? 'quick_calibration',
    );
  }

  final bool canUserWake;
  final int userQuotaRemaining;
  final String cooldownStatus; // available | cooling_down | exhausted
  final int cooldownRemainingMin;
  final List<String> wakeReasons;
  final String recommendedSessionType;
  final int estimatedDurationSec;
  final String suggestedScope;
  final String fallbackIfUnavailable;
}

DateTime? _tryParseDateTime(dynamic raw) {
  final text = raw?.toString().trim();
  if (text == null || text.isEmpty) {
    return null;
  }
  return DateTime.tryParse(text);
}

class AuroraStatusNotifier
    extends StateNotifier<AuroraControlSurfaceSnapshot?> {
  AuroraStatusNotifier(this._apiClient) : super(null);

  final ApiClient _apiClient;
  Timer? _refreshTimer;
  String? _conversationId;

  static const _refreshInterval = Duration(seconds: 10);

  Future<void> refresh({String? conversationId}) async {
    if (conversationId != null) {
      _conversationId =
          conversationId.trim().isEmpty ? null : conversationId.trim();
    }
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.auroraControlSurface,
        queryParameters: _conversationId == null
            ? null
            : <String, dynamic>{'conversation_id': _conversationId},
      );
      final data = response.data;
      if (data == null || data.isEmpty) {
        return;
      }
      state = AuroraControlSurfaceSnapshot.fromJson(data);
    } catch (_) {
      // Keep the most recent successful snapshot visible.
    }
  }

  void markCorrectionEffective({
    required String semanticValue,
    String action = 'disconfirmed',
    List<String> affectedStateKeys = const <String>[],
  }) {
    final current = state;
    if (current == null) return;
    state = current.copyWith(
      lastCorrectionEffect: AuroraCorrectionEffect(
        visible: true,
        semanticValue: semanticValue,
        action: action,
        affectedStateKeys: affectedStateKeys,
        updatedAt: DateTime.now(),
      ),
      fetchedAt: DateTime.now(),
    );
  }

  void startPeriodicRefresh({String? conversationId}) {
    _refreshTimer?.cancel();
    if (conversationId != null) {
      _conversationId =
          conversationId.trim().isEmpty ? null : conversationId.trim();
    }
    unawaited(refresh());
    _refreshTimer =
        Timer.periodic(_refreshInterval, (_) => unawaited(refresh()));
  }

  void stopPeriodicRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = null;
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }
}

final auroraStatusProvider =
    StateNotifierProvider<AuroraStatusNotifier, AuroraControlSurfaceSnapshot?>(
  (ref) => AuroraStatusNotifier(ref.read(apiClientProvider)),
);
