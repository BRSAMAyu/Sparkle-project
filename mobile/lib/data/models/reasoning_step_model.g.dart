// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'reasoning_step_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ReasoningStep _$ReasoningStepFromJson(Map<String, dynamic> json) =>
    ReasoningStep(
      id: json['id'] as String,
      description: json['description'] as String,
      agent: $enumDecode(_$AgentTypeEnumMap, json['agent']),
      status: $enumDecode(_$StepStatusEnumMap, json['status']),
      toolOutput: json['toolOutput'] as String?,
      citations: (json['citations'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
      completedAt: json['completed_at'] == null
          ? null
          : DateTime.parse(json['completed_at'] as String),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$ReasoningStepToJson(ReasoningStep instance) =>
    <String, dynamic>{
      'id': instance.id,
      'description': instance.description,
      'agent': _$AgentTypeEnumMap[instance.agent]!,
      'status': _$StepStatusEnumMap[instance.status]!,
      'toolOutput': instance.toolOutput,
      'citations': instance.citations,
      'created_at': instance.createdAt?.toIso8601String(),
      'completed_at': instance.completedAt?.toIso8601String(),
      'metadata': instance.metadata,
    };

const _$AgentTypeEnumMap = {
  AgentType.orchestrator: 'orchestrator',
  AgentType.math: 'math',
  AgentType.code: 'code',
  AgentType.writing: 'writing',
  AgentType.science: 'science',
  AgentType.knowledge: 'knowledge',
  AgentType.search: 'search',
};

const _$StepStatusEnumMap = {
  StepStatus.pending: 'pending',
  StepStatus.inProgress: 'in_progress',
  StepStatus.completed: 'completed',
  StepStatus.failed: 'failed',
};
