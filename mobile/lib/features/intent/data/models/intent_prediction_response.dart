/// Intent Prediction Response Model
///
/// Response model for the /prediction/intent/predict API endpoint
library;

import 'package:sparkle/features/intent/data/models/intent_data.dart';

/// Intent prediction response from backend API
class IntentPredictionResponse {
  const IntentPredictionResponse({
    required this.intentType,
    required this.confidence,
    required this.executionMode, required this.modeConfidence, this.suggestedActions = const [],
    this.suggestedTools = const [],
  });

  factory IntentPredictionResponse.fromJson(Map<String, dynamic> json) =>
      IntentPredictionResponse(
        intentType: json['intent_type'] as String? ?? 'unknown',
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
        suggestedActions: (json['suggested_actions'] as List?)
                ?.map((e) => e as String)
                .toList() ??
            [],
        suggestedTools: (json['suggested_tools'] as List?)
                ?.map((e) => e as String)
                .toList() ??
            [],
        executionMode: json['execution_mode'] as String? ?? 'direct',
        modeConfidence:
            (json['mode_confidence'] as num?)?.toDouble() ?? 0.0,
      );

  /// Predicted intent type (e.g., 'task_management', 'knowledge_query')
  final String intentType;

  /// Confidence score (0.0 - 1.0)
  final double confidence;

  /// Suggested actions based on predicted intent
  final List<String> suggestedActions;

  /// Suggested tools that might be used
  final List<String> suggestedTools;

  /// Predicted execution mode ('direct' or 'langgraph')
  final String executionMode;

  /// Confidence in the execution mode prediction
  final double modeConfidence;

  /// Convert to IntentData for compatibility with existing intent system
  IntentData toIntentData({required String content}) => IntentData(
        type: intentType,
        confidence: confidence,
        content: content,
        agentRole: _inferAgentRole(intentType),
      );

  /// Infer agent role from intent type
  static String? _inferAgentRole(String intentType) {
    switch (intentType) {
      case 'task_management':
      case 'time_planning':
        return 'orchestrator';
      case 'knowledge_query':
      case 'learning':
        return 'galaxy_guide';
      case 'reflection':
        return 'study_buddy';
      case 'social':
        return 'orchestrator';
      case 'tool_call':
        return 'orchestrator';
      default:
        return null;
    }
  }

  @override
  String toString() =>
      'IntentPredictionResponse(intentType: $intentType, confidence: $confidence, executionMode: $executionMode)';
}
