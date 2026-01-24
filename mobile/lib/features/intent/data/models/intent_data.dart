/// Intent Data Models
///
/// Models for multi-intent detection and preview functionality
library;

import 'package:sparkle/features/intent/data/models/intent_entity.dart';

/// Detected intent in a user message
class IntentData {
  const IntentData({
    required this.type,
    required this.confidence,
    required this.content,
    this.agentRole,
    this.entities = const {},
  });

  factory IntentData.fromJson(Map<String, dynamic> json) {
    return IntentData(
      type: json['type'] as String,
      confidence: (json['confidence'] as num).toDouble(),
      content: json['content'] as String,
      agentRole: json['agent_role'] as String?,
      entities: json['entities'] as Map<String, dynamic>? ?? {},
    );
  }

  factory IntentData.fromEntity(IntentEntity entity) {
    return IntentData(
      type: entity.type,
      confidence: entity.confidence,
      content: entity.content,
      agentRole: entity.agentRole,
      entities: entity.entities,
    );
  }

  /// Intent type (e.g., 'knowledge_query', 'task_management', etc.)
  final String type;

  /// Confidence score (0.0 - 1.0)
  final double confidence;

  /// Extracted content related to this intent
  final String content;

  /// Which agent role should handle this intent
  final String? agentRole;

  /// Additional extracted entities
  final Map<String, dynamic> entities;

  IntentData copyWith({
    String? type,
    double? confidence,
    String? content,
    String? agentRole,
    Map<String, dynamic>? entities,
  }) {
    return IntentData(
      type: type ?? this.type,
      confidence: confidence ?? this.confidence,
      content: content ?? this.content,
      agentRole: agentRole ?? this.agentRole,
      entities: entities ?? this.entities,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'type': type,
      'confidence': confidence,
      'content': content,
      if (agentRole != null) 'agent_role': agentRole,
      if (entities.isNotEmpty) 'entities': entities,
    };
  }

  @override
  String toString() {
    return 'IntentData(type: $type, confidence: $confidence, content: $content, agentRole: $agentRole)';
  }
}

/// Response from intent preview API
class IntentPreviewResponse {
  const IntentPreviewResponse({
    required this.originalMessage,
    required this.detectedIntents,
    this.executionPlan,
    this.estimatedTime,
    this.suggestedAgentRoles,
  });

  factory IntentPreviewResponse.fromJson(Map<String, dynamic> json) {
    return IntentPreviewResponse(
      originalMessage: json['original_message'] as String,
      detectedIntents: (json['detected_intents'] as List)
          .map((e) => IntentData.fromJson(e as Map<String, dynamic>))
          .toList(),
      executionPlan: json['execution_plan'] as String?,
      estimatedTime: json['estimated_time'] as int?,
      suggestedAgentRoles: (json['suggested_agent_roles'] as List?)
          ?.map((e) => e as String)
          .toList(),
    );
  }

  /// The original user message
  final String originalMessage;

  /// List of detected intents
  final List<IntentData> detectedIntents;

  /// Generated execution plan
  final String? executionPlan;

  /// Estimated execution time in seconds
  final int? estimatedTime;

  /// Suggested agent roles for handling the detected intents
  final List<String>? suggestedAgentRoles;

  Map<String, dynamic> toJson() {
    return {
      'original_message': originalMessage,
      'detected_intents': detectedIntents.map((e) => e.toJson()).toList(),
      if (executionPlan != null) 'execution_plan': executionPlan,
      if (estimatedTime != null) 'estimated_time': estimatedTime,
      if (suggestedAgentRoles != null) 'suggested_agent_roles': suggestedAgentRoles,
    };
  }

  @override
  String toString() {
    return 'IntentPreviewResponse(originalMessage: $originalMessage, detectedIntents: $detectedIntents)';
  }
}

/// Intent execution request
class IntentExecuteRequest {
  const IntentExecuteRequest({
    required this.message,
    this.confirmIntents = true,
  });

  final String message;
  final bool confirmIntents;

  Map<String, dynamic> toJson() {
    return {
      'message': message,
      'confirm_intents': confirmIntents,
    };
  }
}

/// Intent execution response
class IntentExecuteResponse {
  const IntentExecuteResponse({
    required this.success,
    this.results,
    this.errorMessage,
  });

  factory IntentExecuteResponse.fromJson(Map<String, dynamic> json) {
    return IntentExecuteResponse(
      success: json['success'] as bool? ?? false,
      results: json['results'] as List<dynamic>?,
      errorMessage: json['error_message'] as String?,
    );
  }

  final bool success;
  final List<dynamic>? results;
  final String? errorMessage;
}

/// Available intent type metadata
class IntentTypeMetadata {
  const IntentTypeMetadata({
    required this.type,
    required this.label,
    required this.description,
    this.agentRole,
  });

  factory IntentTypeMetadata.fromJson(Map<String, dynamic> json) {
    return IntentTypeMetadata(
      type: json['type'] as String,
      label: json['label'] as String,
      description: json['description'] as String,
      agentRole: json['agent_role'] as String?,
    );
  }

  final String type;
  final String label;
  final String description;
  final String? agentRole;
}

/// Result from intent execution
class IntentExecuteResult {
  const IntentExecuteResult({
    required this.success,
    this.results,
    this.errorMessage,
  });

  factory IntentExecuteResult.fromJson(Map<String, dynamic> json) {
    return IntentExecuteResult(
      success: json['success'] as bool? ?? false,
      results: json['results'] as List<dynamic>?,
      errorMessage: json['error_message'] as String?,
    );
  }

  final bool success;
  final List<dynamic>? results;
  final String? errorMessage;
}

/// Response from analyze-and-execute endpoint
///
/// This endpoint handles the entire flow:
/// - Single intent or auto_execute=true: Returns execution_result
/// - Multi intent and auto_execute=false: Returns preview with needs_confirmation=true
class AnalyzeAndExecuteResponse {
  const AnalyzeAndExecuteResponse({
    required this.isSuccess,
    required this.isMultiIntent,
    required this.autoExecuted,
    this.preview,
    this.executionResult,
    this.needsConfirmation = false,
  });

  factory AnalyzeAndExecuteResponse.fromJson(Map<String, dynamic> json) {
    return AnalyzeAndExecuteResponse(
      isSuccess: json['success'] as bool? ?? false,
      isMultiIntent: json['is_multi_intent'] as bool? ?? false,
      autoExecuted: json['auto_executed'] as bool? ?? false,
      needsConfirmation: json['needs_confirmation'] as bool? ?? false,
      preview: json['preview'] != null
          ? IntentPreviewResponse.fromJson(json['preview'] as Map<String, dynamic>)
          : null,
      executionResult: json['execution_result'] != null
          ? IntentExecuteResult.fromJson(json['execution_result'] as Map<String, dynamic>)
          : null,
    );
  }

  final bool isSuccess;
  final bool isMultiIntent;
  final bool autoExecuted;
  final bool needsConfirmation;
  final IntentPreviewResponse? preview;
  final IntentExecuteResult? executionResult;
}
