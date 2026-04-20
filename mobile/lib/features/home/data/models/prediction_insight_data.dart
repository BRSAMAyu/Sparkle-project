import 'package:sparkle/shared/utils/entity_card_payloads.dart';

Map<String, dynamic>? _asStringKeyedMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map) {
    try {
      return Map<String, dynamic>.from(value);
    } catch (_) {
      return null;
    }
  }
  return null;
}

List<dynamic> _asDynamicList(dynamic value) {
  if (value is List<dynamic>) {
    return value;
  }
  if (value is List) {
    return List<dynamic>.from(value);
  }
  return const <dynamic>[];
}

double _asDouble(dynamic value, {double fallback = 0}) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value) ?? fallback;
  }
  return fallback;
}

bool _asBool(dynamic value, {bool fallback = false}) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  if (value is String) {
    switch (value.trim().toLowerCase()) {
      case 'true':
      case '1':
      case 'yes':
      case 'y':
        return true;
      case 'false':
      case '0':
      case 'no':
      case 'n':
        return false;
      default:
        return fallback;
    }
  }
  return fallback;
}

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

  final String id;
  final String label;
  final String actionType;
  final String targetRoute;
  final String suggestedPrompt;
  final String? resourceType;
  final String? resourceId;
  final String? surface;
}

class WithinCategoryPreferenceData {
  WithinCategoryPreferenceData({
    required this.claimScope,
    required this.surface,
    required this.requestCategory,
    required this.preferredTool,
    required this.confidence,
    required this.supportCount,
    required this.shadowRecords,
    required this.divergenceRate,
  });

  factory WithinCategoryPreferenceData.fromJson(Map<String, dynamic> json) =>
      WithinCategoryPreferenceData(
        claimScope: json['claim_scope']?.toString() ?? 'within_category_only',
        surface: json['surface']?.toString() ?? '',
        requestCategory: json['request_category']?.toString() ?? '',
        preferredTool: json['preferred_tool']?.toString() ?? '',
        confidence: _asDouble(json['confidence']),
        supportCount: json['support_count'] is int
            ? json['support_count'] as int
            : int.tryParse(json['support_count']?.toString() ?? '') ?? 0,
        shadowRecords: json['shadow_records'] is int
            ? json['shadow_records'] as int
            : int.tryParse(json['shadow_records']?.toString() ?? '') ?? 0,
        divergenceRate: _asDouble(json['divergence_rate']),
      );

  final String claimScope;
  final String surface;
  final String requestCategory;
  final String preferredTool;
  final double confidence;
  final int supportCount;
  final int shadowRecords;
  final double divergenceRate;
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
    this.withinCategoryPreference,
  });

  factory PredictionInsightData.fromJson(Map<String, dynamic> json) {
    final tracking =
        _asStringKeyedMap(json['tracking']) ?? const <String, dynamic>{};
    final explanationsMap =
        _asStringKeyedMap(json['explanations']) ?? const <String, dynamic>{};
    final entityCardMap = _asStringKeyedMap(json['entity_card']);
    final withinCategoryPreferenceMap =
        _asStringKeyedMap(json['within_category_preference']);
    return PredictionInsightData(
      predictionId: json['prediction_id']?.toString() ?? '',
      horizon: json['horizon']?.toString() ?? 'realtime',
      title: json['title']?.toString() ?? '',
      summary: json['summary']?.toString() ?? '',
      confidence: _asDouble(json['confidence']),
      predictedActionType: json['predicted_action_type']?.toString() ?? '',
      predictedWindow: json['predicted_window']?.toString() ?? '',
      reasons: _asDynamicList(json['reasons'])
          .map((item) => item.toString())
          .toList(),
      suggestedPrompt: json['suggested_prompt']?.toString() ?? '',
      predictionSource: json['prediction_source']?.toString() ?? 'rules',
      predictionTier: json['prediction_tier']?.toString() ?? 'rules',
      fallbackUsed: _asBool(json['fallback_used']),
      explanations: {
        for (final entry in explanationsMap.entries)
          entry.key: _asDynamicList(entry.value)
              .map((item) => item.toString())
              .toList(),
      },
      recommendedActions: _asDynamicList(json['recommended_actions'])
          .map(_asStringKeyedMap)
          .whereType<Map<String, dynamic>>()
          .map(PredictionActionData.fromJson)
          .toList(),
      trackingCandidateId: tracking['candidate_id']?.toString() ??
          json['prediction_id']?.toString() ??
          '',
      trackingActionType: tracking['action_type']?.toString() ??
          json['predicted_action_type']?.toString() ??
          'continue_chat',
      surface: json['surface']?.toString(),
      generatedAt: DateTime.tryParse(json['generated_at']?.toString() ?? ''),
      entityCard: entityCardMap != null
          ? EntityCardPayload.fromRaw(
              {'entity_card': entityCardMap},
              fallbackType: 'prediction',
            )
          : null,
      withinCategoryPreference: withinCategoryPreferenceMap != null
          ? WithinCategoryPreferenceData.fromJson(withinCategoryPreferenceMap)
          : null,
    );
  }

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
  final WithinCategoryPreferenceData? withinCategoryPreference;

  List<String> get allExplanationLines => [
        ...?explanations['recent_24h'],
        ...?explanations['recent_7d'],
        ...?explanations['profile'],
        ...?explanations['plan'],
        ...?explanations['focus'],
      ];
}
