import 'package:sparkle/shared/utils/entity_card_payloads.dart';

class PredictionActionData {
  PredictionActionData({
    required this.id,
    required this.label,
    required this.actionType,
    required this.targetRoute,
    required this.suggestedPrompt,
    this.resourceType,
    this.resourceId,
    this.surface,
  });

  final String id;
  final String label;
  final String actionType;
  final String targetRoute;
  final String suggestedPrompt;
  final String? resourceType;
  final String? resourceId;
  final String? surface;

  factory PredictionActionData.fromJson(Map<String, dynamic> json) =>
      PredictionActionData(
        id: json['id']?.toString() ?? '',
        label: json['label']?.toString() ?? '',
        actionType: json['action_type']?.toString() ?? '',
        targetRoute: json['target_route']?.toString() ?? '/chat',
        suggestedPrompt: json['suggested_prompt']?.toString() ?? '',
        resourceType: json['resource_type']?.toString(),
        resourceId: json['resource_id']?.toString(),
        surface: json['surface']?.toString(),
      );
}

class PredictionInsightData {
  PredictionInsightData({
    required this.predictionId,
    required this.horizon,
    required this.title,
    required this.summary,
    required this.confidence,
    required this.predictedActionType,
    required this.predictedWindow,
    required this.reasons,
    required this.suggestedPrompt,
    required this.predictionSource,
    required this.predictionTier,
    required this.fallbackUsed,
    required this.explanations,
    required this.recommendedActions,
    required this.trackingCandidateId,
    required this.trackingActionType,
    this.surface,
    this.generatedAt,
    this.entityCard,
  });

  final String predictionId;
  final String horizon;
  final String title;
  final String summary;
  final double confidence;
  final String predictedActionType;
  final String predictedWindow;
  final List<String> reasons;
  final String suggestedPrompt;
  final String predictionSource;
  final String predictionTier;
  final bool fallbackUsed;
  final Map<String, List<String>> explanations;
  final List<PredictionActionData> recommendedActions;
  final String trackingCandidateId;
  final String trackingActionType;
  final String? surface;
  final DateTime? generatedAt;
  final EntityCardPayload? entityCard;

  List<String> get allExplanationLines => [
        ...?explanations['recent_24h'],
        ...?explanations['recent_7d'],
        ...?explanations['profile'],
        ...?explanations['plan'],
        ...?explanations['focus'],
      ];

  factory PredictionInsightData.fromJson(Map<String, dynamic> json) {
    final tracking = (json['tracking'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
    final explanationsMap = (json['explanations'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
    return PredictionInsightData(
      predictionId: json['prediction_id']?.toString() ?? '',
      horizon: json['horizon']?.toString() ?? 'realtime',
      title: json['title']?.toString() ?? '',
      summary: json['summary']?.toString() ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      predictedActionType: json['predicted_action_type']?.toString() ?? '',
      predictedWindow: json['predicted_window']?.toString() ?? '',
      reasons: ((json['reasons'] as List<dynamic>?) ?? const [])
          .map((item) => item.toString())
          .toList(),
      suggestedPrompt: json['suggested_prompt']?.toString() ?? '',
      predictionSource: json['prediction_source']?.toString() ?? 'rules',
      predictionTier: json['prediction_tier']?.toString() ?? 'rules',
      fallbackUsed: json['fallback_used'] as bool? ?? false,
      explanations: {
        for (final entry in explanationsMap.entries)
          entry.key: ((entry.value as List<dynamic>?) ?? const [])
              .map((item) => item.toString())
              .toList(),
      },
      recommendedActions:
          ((json['recommended_actions'] as List<dynamic>?) ?? const [])
              .map(
                (item) =>
                    PredictionActionData.fromJson(item as Map<String, dynamic>),
              )
              .toList(),
      trackingCandidateId: tracking['candidate_id']?.toString() ??
          json['prediction_id']?.toString() ??
          '',
      trackingActionType: tracking['action_type']?.toString() ??
          json['predicted_action_type']?.toString() ??
          'continue_chat',
      surface: json['surface']?.toString(),
      generatedAt: DateTime.tryParse(json['generated_at']?.toString() ?? ''),
      entityCard: json['entity_card'] is Map<String, dynamic>
          ? EntityCardPayload.fromRaw(
              {'entity_card': json['entity_card'] as Map<String, dynamic>},
              fallbackType: 'prediction',
            )
          : null,
    );
  }
}
