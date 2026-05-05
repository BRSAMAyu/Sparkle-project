import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/i18n_service.dart';

/// 6-state band model matching backend get_status_band_summary().
enum AuroraBandStatus {
  sensing,
  calibrated,
  riskFound,
  needsConfirm,
  calibrationAvailable,
  coolingDown;

  /// Protocol value sent to backend (snake_case, matching API format).
  String get protocolValue => switch (this) {
        AuroraBandStatus.sensing => 'sensing',
        AuroraBandStatus.calibrated => 'calibrated',
        AuroraBandStatus.riskFound => 'risk_found',
        AuroraBandStatus.needsConfirm => 'needs_confirm',
        AuroraBandStatus.calibrationAvailable => 'calibration_available',
        AuroraBandStatus.coolingDown => 'cooling_down',
      };
}

/// Typed model for GET /aurora/spine/status-band response.
class SpineStatusBand {
  final bool strategyRisk;
  final bool materialAware;
  final bool executionRisk;
  final bool staleGuard;
  final String bandSeverity; // none/info/warning/critical
  final AuroraBandStatus bandStatus;
  final String bandLabel;
  final String bandSummary;
  final String bandEnergy; // L0/L1/L2/L3
  final List<CorrectionOption> correctionOptions;
  final int? cooldownRemainingSeconds;
  final bool cooldownCanOverride;

  const SpineStatusBand({
    required this.strategyRisk,
    required this.materialAware,
    required this.executionRisk,
    required this.staleGuard,
    required this.bandSeverity,
    required this.bandStatus,
    required this.bandLabel,
    required this.bandSummary,
    required this.bandEnergy,
    required this.correctionOptions,
    required this.cooldownRemainingSeconds,
    required this.cooldownCanOverride,
  });

  factory SpineStatusBand.fromJson(Map<String, dynamic> json) {
    final zh = I18nService.instance.isChinese;
    return SpineStatusBand(
      strategyRisk: json['strategy_risk'] as bool? ?? false,
      materialAware: json['material_aware'] as bool? ?? false,
      executionRisk: json['execution_risk'] as bool? ?? false,
      staleGuard: json['stale_guard'] as bool? ?? false,
      bandSeverity: json['band_severity'] as String? ?? 'none',
      bandStatus: _parseBandStatus(json['band_status'] as String?),
      bandLabel: json['band_label'] as String? ?? (zh ? '轻量感知中' : 'Lightweight Sensing'),
      bandSummary: json['band_summary'] as String? ?? '',
      bandEnergy: json['band_energy'] as String? ?? 'L0',
      correctionOptions: _parseCorrectionOptions(json['correction_options']),
      cooldownRemainingSeconds: json['cooldown_remaining_seconds'] as int?,
      cooldownCanOverride: json['cooldown_can_override'] as bool? ?? false,
    );
  }

  static AuroraBandStatus _parseBandStatus(String? raw) => switch (raw) {
      'sensing' => AuroraBandStatus.sensing,
      'calibrated' => AuroraBandStatus.calibrated,
      'risk_found' => AuroraBandStatus.riskFound,
      'needs_confirm' => AuroraBandStatus.needsConfirm,
      'calibration_available' => AuroraBandStatus.calibrationAvailable,
      'cooling_down' => AuroraBandStatus.coolingDown,
      _ => AuroraBandStatus.sensing,
    };

  static List<CorrectionOption> _parseCorrectionOptions(dynamic raw) {
    if (raw is! List) return const [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(CorrectionOption.fromJson)
        .toList();
  }
}

class CorrectionOption {
  final String label;
  final String semanticValue;
  final bool isFreeform;
  final bool isDisconfirming;

  const CorrectionOption({
    required this.label,
    required this.semanticValue,
    required this.isFreeform,
    required this.isDisconfirming,
  });

  factory CorrectionOption.fromJson(Map<String, dynamic> json) =>
      CorrectionOption(
        label: json['label'] as String? ?? '',
        semanticValue: json['semantic_value'] as String? ?? '',
        isFreeform: json['is_freeform'] as bool? ?? false,
        isDisconfirming: json['is_disconfirming'] as bool? ?? false,
      );
}

// ── Provider ──────────────────────────────────────────────────────────────

final spineStatusBandProvider =
    FutureProvider<SpineStatusBand?>((ref) async {
  try {
    final api = ref.read(apiClientProvider);
    final response = await api.get<Map<String, dynamic>>(
      ApiEndpoints.auroraSpineStatusBand,
    );
    final data = response.data;
    if (data == null) return null;
    return SpineStatusBand.fromJson(data);
  } on DioException {
    return null;
  } catch (e, st) {
    debugPrint('spineStatusBandProvider unexpected error: $e\n$st');
    return null;
  }
});
