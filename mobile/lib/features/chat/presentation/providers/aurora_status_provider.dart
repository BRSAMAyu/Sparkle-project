import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

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
    required this.surface,
    required this.updatedAt,
    required this.facets,
    required this.wakeEligibility,
    required this.fetchedAt,
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
      surface: json['surface'] as String?,
      updatedAt: _tryParseDateTime(json['updated_at']),
      facets: rawFacets
          .whereType<Map<String, dynamic>>()
          .map(AuroraFacetSnapshot.fromJson)
          .toList(),
      wakeEligibility: AuroraWakeEligibility.fromJson(rawWake),
      fetchedAt: DateTime.now(),
    );
  }

  final bool auroraActive;
  final bool runtimeEnabled;
  final String overallStatus; // 6-state: sensing/calibrated/risk_found/needs_confirm/calibration_available/cooling_down
  final String energyLevel;   // L0-L3
  final String summary;
  final int readyCount;
  final int activeCount;
  final int totalCount;
  final String? conversationId;
  final String? requestedConversationId;
  final String sceneAlignment;
  final String? surface;
  final DateTime? updatedAt;
  final List<AuroraFacetSnapshot> facets;
  final AuroraWakeEligibility wakeEligibility;
  final DateTime fetchedAt;

  bool get isRecalibrating => overallStatus == 'risk_found';
  bool get isReady => overallStatus == 'calibrated';
  bool get isCoolingDown => overallStatus == 'cooling_down';
  bool get needsConfirm => overallStatus == 'needs_confirm';
  bool get canCalibrate => overallStatus == 'calibration_available';
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
      cooldownRemainingMin: (json['cooldown_remaining_min'] as num?)?.toInt() ?? 0,
      wakeReasons: (json['wake_reasons'] as List<dynamic>? ?? const []).map((e) => '$e').toList(),
      recommendedSessionType: json['recommended_session_type'] as String? ?? 'strategy_recalibration',
      estimatedDurationSec: (json['estimated_duration_sec'] as num?)?.toInt() ?? 240,
      suggestedScope: json['suggested_scope'] as String? ?? '',
      fallbackIfUnavailable: json['fallback_if_unavailable'] as String? ?? 'quick_calibration',
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
