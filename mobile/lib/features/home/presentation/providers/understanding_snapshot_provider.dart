import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

enum UnderstandingCorrectionScope {
  memoryClaim('memory_claim'),
  routingPolicy('routing_policy'),
  taskGranularity('task_granularity'),
  planRisk('plan_risk'),
  knowledgeBottleneck('knowledge_bottleneck'),
  wakePolicy('wake_policy');

  const UnderstandingCorrectionScope(this.apiValue);

  final String apiValue;
}

class UnderstandingClaim {
  const UnderstandingClaim({
    required this.claimId,
    required this.claim,
    required this.confidence,
    required this.confidenceLabel,
    required this.evidenceSummary,
    required this.scope,
    required this.userCanCorrect,
  });

  factory UnderstandingClaim.fromJson(Map<String, dynamic> json) =>
      UnderstandingClaim(
        claimId: json['claim_id'] as String? ?? '',
        claim: json['claim'] as String? ?? '',
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
        confidenceLabel: json['confidence_label'] as String? ?? 'low',
        evidenceSummary: json['evidence_summary'] as String? ?? '',
        scope: json['scope'] as String? ?? '',
        userCanCorrect: json['user_can_correct'] as bool? ?? true,
      );

  final String claimId;
  final String claim;
  final double confidence;
  final String confidenceLabel;
  final String evidenceSummary;
  final String scope;
  final bool userCanCorrect;
}

class RecentlyCorrectedUnderstanding {
  const RecentlyCorrectedUnderstanding({
    required this.claim,
    required this.correction,
    required this.effectOnPolicy,
  });

  factory RecentlyCorrectedUnderstanding.fromJson(Map<String, dynamic> json) =>
      RecentlyCorrectedUnderstanding(
        claim: json['claim'] as String? ?? '',
        correction: json['correction'] as String? ?? '',
        effectOnPolicy: (json['effect_on_policy'] as List<dynamic>? ?? const [])
            .map((item) => '$item')
            .where((item) => item.isNotEmpty)
            .toList(),
      );

  final String claim;
  final String correction;
  final List<String> effectOnPolicy;
}

class MemoryDeclaration {
  const MemoryDeclaration({
    required this.type,
    required this.content,
    required this.persistence,
  });

  factory MemoryDeclaration.fromJson(Map<String, dynamic> json) =>
      MemoryDeclaration(
        type: json['type'] as String? ?? '',
        content: json['content'] as String? ?? '',
        persistence: json['persistence'] as String? ?? '',
      );

  final String type;
  final String content;
  final String persistence;
}

class EnvelopeStyleSnapshot {
  const EnvelopeStyleSnapshot({
    required this.currentTone,
    required this.currentVerbosity,
    required this.reasonForStyle,
  });

  const EnvelopeStyleSnapshot.empty()
      : currentTone = '',
        currentVerbosity = '',
        reasonForStyle = '';

  factory EnvelopeStyleSnapshot.fromJson(dynamic raw) {
    final json = raw is Map<String, dynamic>
        ? raw
        : raw is Map
            ? Map<String, dynamic>.from(raw)
            : const <String, dynamic>{};
    return EnvelopeStyleSnapshot(
      currentTone: json['current_tone'] as String? ?? '',
      currentVerbosity: json['current_verbosity'] as String? ?? '',
      reasonForStyle: json['reason_for_style'] as String? ?? '',
    );
  }

  final String currentTone;
  final String currentVerbosity;
  final String reasonForStyle;
}

class UnderstandingSnapshot {
  const UnderstandingSnapshot({
    required this.claims,
    required this.recentlyCorrected,
    required this.memoryDeclarations,
    required this.envelopeStyle,
    required this.lastUpdateTime,
    required this.totalClaims,
    required this.highConfidenceRatio,
  });

  factory UnderstandingSnapshot.fromJson(Map<String, dynamic> json) {
    final rawClaims = json['claims'] as List<dynamic>? ?? const [];
    final rawCorrected =
        json['recently_corrected'] as List<dynamic>? ?? const [];
    final rawMemory = json['memory_declarations'] as List<dynamic>? ?? const [];
    return UnderstandingSnapshot(
      claims: rawClaims
          .whereType<Map<String, dynamic>>()
          .map(UnderstandingClaim.fromJson)
          .toList(),
      recentlyCorrected: rawCorrected
          .whereType<Map<String, dynamic>>()
          .map(RecentlyCorrectedUnderstanding.fromJson)
          .toList(),
      memoryDeclarations: rawMemory
          .whereType<Map<String, dynamic>>()
          .map(MemoryDeclaration.fromJson)
          .toList(),
      envelopeStyle: EnvelopeStyleSnapshot.fromJson(json['envelope_style']),
      lastUpdateTime:
          DateTime.tryParse(json['last_update_time'] as String? ?? ''),
      totalClaims: (json['total_claims'] as num?)?.toInt() ?? rawClaims.length,
      highConfidenceRatio:
          (json['high_confidence_ratio'] as num?)?.toDouble() ?? 0,
    );
  }

  final List<UnderstandingClaim> claims;
  final List<RecentlyCorrectedUnderstanding> recentlyCorrected;
  final List<MemoryDeclaration> memoryDeclarations;
  final EnvelopeStyleSnapshot envelopeStyle;
  final DateTime? lastUpdateTime;
  final int totalClaims;
  final double highConfidenceRatio;

  bool get isEmpty =>
      claims.isEmpty &&
      recentlyCorrected.isEmpty &&
      memoryDeclarations.isEmpty &&
      envelopeStyle.currentTone.isEmpty;
}

class UnderstandingSnapshotNotifier
    extends AsyncNotifier<UnderstandingSnapshot?> {
  @override
  Future<UnderstandingSnapshot?> build() => _fetch();

  Future<UnderstandingSnapshot?> _fetch() async {
    final api = ref.read(apiClientProvider);
    final response =
        await api.get<Map<String, dynamic>>(ApiEndpoints.understandingSnapshot);
    final data = response.data;
    if (data == null) return null;
    return UnderstandingSnapshot.fromJson(data);
  }

  Future<List<String>> correctClaim({
    required UnderstandingClaim claim,
    required String correction,
    required UnderstandingCorrectionScope scope,
  }) async {
    final api = ref.read(apiClientProvider);
    final response = await api.post<Map<String, dynamic>>(
      ApiEndpoints.understandingSnapshotCorrections,
      data: {
        'claim': claim.claim,
        'correction': correction,
        'effect_scope': scope.apiValue,
      },
    );
    final effects =
        (response.data?['effect_on_policy'] as List<dynamic>? ?? const [])
            .map((item) => '$item')
            .where((item) => item.isNotEmpty)
            .toList();
    state =
        const AsyncLoading<UnderstandingSnapshot?>().copyWithPrevious(state);
    state = await AsyncValue.guard(_fetch);
    return effects;
  }
}

final understandingSnapshotProvider = AsyncNotifierProvider<
    UnderstandingSnapshotNotifier, UnderstandingSnapshot?>(
  UnderstandingSnapshotNotifier.new,
);
