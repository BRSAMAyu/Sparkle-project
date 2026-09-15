class AuroraCalibrationCard {
  const AuroraCalibrationCard({
    required this.id,
    required this.title,
    required this.statement,
    required this.confidence,
    required this.confidenceLabel,
    required this.needsConfirmation,
    required this.evidence,
    this.evidenceSummary,
    this.planId,
    this.source,
    this.lastObservedAt,
  });

  factory AuroraCalibrationCard.fromJson(Map<String, dynamic> json) {
    final evidenceRaw = json['evidence'];
    final evidence = evidenceRaw is List
        ? evidenceRaw
            .map((item) => item?.toString() ?? '')
            .where((item) => item.trim().isNotEmpty)
            .toList()
        : const <String>[];

    return AuroraCalibrationCard(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      statement: json['statement']?.toString() ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      confidenceLabel: json['confidence_label']?.toString() ?? '0%',
      needsConfirmation: json['needs_confirmation'] == true,
      evidence: evidence,
      evidenceSummary: json['evidence_summary']?.toString(),
      planId: json['plan_id']?.toString(),
      source: json['source']?.toString(),
      lastObservedAt: json['last_observed_at']?.toString(),
    );
  }

  final String id;
  final String title;
  final String statement;
  final double confidence;
  final String confidenceLabel;
  final bool needsConfirmation;
  final List<String> evidence;
  final String? evidenceSummary;
  final String? planId;
  final String? source;
  final String? lastObservedAt;
}

class AuroraCalibrationSurface {
  const AuroraCalibrationSurface({
    required this.items,
    required this.state,
    required this.label,
  });

  factory AuroraCalibrationSurface.fromJson(Map<String, dynamic> json) {
    final surface = json['surface'] is Map<String, dynamic>
        ? json['surface'] as Map<String, dynamic>
        : <String, dynamic>{};
    final itemsRaw = json['items'];
    final items = itemsRaw is List
        ? itemsRaw
            .whereType<Map<Object?, Object?>>()
            .map(
              (item) => AuroraCalibrationCard.fromJson(
                Map<String, dynamic>.from(item),
              ),
            )
            .where((item) => item.id.isNotEmpty)
            .toList()
        : const <AuroraCalibrationCard>[];

    return AuroraCalibrationSurface(
      items: items,
      state: surface['state']?.toString() ?? 'observing',
      label: surface['label']?.toString() ?? 'Aurora · 观察中',
    );
  }

  final List<AuroraCalibrationCard> items;
  final String state;
  final String label;

  bool get hasItems => items.isNotEmpty;
}

enum AuroraCalibrationResponse {
  confirm('confirm'),
  incorrect('incorrect'),
  mute('mute');

  const AuroraCalibrationResponse(this.apiValue);

  final String apiValue;
}
