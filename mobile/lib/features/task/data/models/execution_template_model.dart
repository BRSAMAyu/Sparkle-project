import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';

ExecutionMode _parseTemplateExecutionMode(String? value) {
  switch (value) {
    case 'human':
      return ExecutionMode.human;
    case 'agent':
      return ExecutionMode.agent;
    case 'hybrid':
      return ExecutionMode.hybrid;
    default:
      return ExecutionMode.unknown;
  }
}

class ExecutionTemplateModel {
  const ExecutionTemplateModel({
    required this.templateId,
    required this.name,
    required this.description,
    required this.executionMode,
    required this.targetEnv,
    required this.matchScore,
    required this.matchReasons,
    this.requiredNodeCommand,
  });

  factory ExecutionTemplateModel.fromJson(Map<String, dynamic> json) =>
      ExecutionTemplateModel(
        templateId: json['template_id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        description: json['description'] as String? ?? '',
        executionMode:
            _parseTemplateExecutionMode(json['execution_mode'] as String?),
        targetEnv: json['target_env'] as String? ?? '',
        matchScore: (json['match_score'] as num?)?.toDouble() ?? 0,
        matchReasons: (json['match_reasons'] as List<dynamic>? ?? const [])
            .whereType<String>()
            .toList(),
        requiredNodeCommand: json['required_node_command'] as String?,
      );

  final String templateId;
  final String name;
  final String description;
  final ExecutionMode executionMode;
  final String targetEnv;
  final double matchScore;
  final List<String> matchReasons;
  final String? requiredNodeCommand;

  String get modeLabel {
    switch (executionMode) {
      case ExecutionMode.human:
        return 'Manual';
      case ExecutionMode.agent:
        return 'AI';
      case ExecutionMode.hybrid:
        return 'Hybrid';
      case ExecutionMode.unknown:
        return 'Unknown';
    }
  }
}
