import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

/// 6-state band model matching backend get_status_band_summary().
enum AuroraBandStatus {
  sensing,
  calibrated,
  riskFound,
  needsConfirm,
  calibrationAvailable,
  coolingDown,
}

/// Typed model for GET /aurora/spine/status-band response.
class SpineStatusBand {
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

  factory SpineStatusBand.fromJson(Map<String, dynamic> json) => SpineStatusBand(
      strategyRisk: json['strategy_risk'] as bool? ?? false,
      materialAware: json['material_aware'] as bool? ?? false,
      executionRisk: json['execution_risk'] as bool? ?? false,
      staleGuard: json['stale_guard'] as bool? ?? false,
      bandSeverity: json['band_severity'] as String? ?? 'none',
      bandStatus: _parseBandStatus(json['band_status'] as String?),
      bandLabel: json['band_label'] as String? ?? '轻量感知中',
      bandSummary: json['band_summary'] as String? ?? '',
      bandEnergy: json['band_energy'] as String? ?? 'L0',
      correctionOptions: _parseCorrectionOptions(json['correction_options']),
      cooldownRemainingSeconds: json['cooldown_remaining_seconds'] as int?,
      cooldownCanOverride: json['cooldown_can_override'] as bool? ?? false,
    );

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
  const CorrectionOption({
    required this.label,
    required this.semanticValue,
    required this.isFreeform,
    required this.isDisconfirming,
  });

  final String label;
  final String semanticValue;
  final bool isFreeform;
  final bool isDisconfirming;

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
    FutureProvider.autoDispose<SpineStatusBand?>((ref) async {
  try {
    final api = ref.read(apiClientProvider);
    final response = await api.get<Map<String, dynamic>>(
      ApiEndpoints.auroraSpineStatusBand,
    );
    final data = response.data;
    if (data == null) return null;
    return SpineStatusBand.fromJson(data);
  } catch (_) {
    return null;
  }
});
