// This is a generated file - do not edit.
//
// Generated from agent_service.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

class FinishReason extends $pb.ProtobufEnum {
  static const FinishReason NULL =
      FinishReason._(0, _omitEnumNames ? '' : 'NULL');
  static const FinishReason STOP =
      FinishReason._(1, _omitEnumNames ? '' : 'STOP');
  static const FinishReason LENGTH =
      FinishReason._(2, _omitEnumNames ? '' : 'LENGTH');
  static const FinishReason TOOL_CALLS =
      FinishReason._(3, _omitEnumNames ? '' : 'TOOL_CALLS');
  static const FinishReason CONTENT_FILTER =
      FinishReason._(4, _omitEnumNames ? '' : 'CONTENT_FILTER');
  static const FinishReason ERROR =
      FinishReason._(5, _omitEnumNames ? '' : 'ERROR');

  static const $core.List<FinishReason> values = <FinishReason>[
    NULL,
    STOP,
    LENGTH,
    TOOL_CALLS,
    CONTENT_FILTER,
    ERROR,
  ];

  static final $core.List<FinishReason?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 5);
  static FinishReason? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const FinishReason._(super.value, super.name);
}

class InterventionLevel extends $pb.ProtobufEnum {
  static const InterventionLevel SILENT_MARKER =
      InterventionLevel._(0, _omitEnumNames ? '' : 'SILENT_MARKER');
  static const InterventionLevel TOAST =
      InterventionLevel._(1, _omitEnumNames ? '' : 'TOAST');
  static const InterventionLevel CARD =
      InterventionLevel._(2, _omitEnumNames ? '' : 'CARD');
  static const InterventionLevel FULL_SCREEN_MODAL =
      InterventionLevel._(3, _omitEnumNames ? '' : 'FULL_SCREEN_MODAL');

  static const $core.List<InterventionLevel> values = <InterventionLevel>[
    SILENT_MARKER,
    TOAST,
    CARD,
    FULL_SCREEN_MODAL,
  ];

  static final $core.List<InterventionLevel?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 3);
  static InterventionLevel? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const InterventionLevel._(super.value, super.name);
}

/// AgentType defines the different types of specialized agents in the system.
class AgentType extends $pb.ProtobufEnum {
  static const AgentType AGENT_UNKNOWN =
      AgentType._(0, _omitEnumNames ? '' : 'AGENT_UNKNOWN');
  static const AgentType ORCHESTRATOR =
      AgentType._(1, _omitEnumNames ? '' : 'ORCHESTRATOR');
  static const AgentType KNOWLEDGE =
      AgentType._(2, _omitEnumNames ? '' : 'KNOWLEDGE');
  static const AgentType MATH = AgentType._(3, _omitEnumNames ? '' : 'MATH');
  static const AgentType CODE = AgentType._(4, _omitEnumNames ? '' : 'CODE');
  static const AgentType DATA_ANALYSIS =
      AgentType._(5, _omitEnumNames ? '' : 'DATA_ANALYSIS');
  static const AgentType TRANSLATION =
      AgentType._(6, _omitEnumNames ? '' : 'TRANSLATION');
  static const AgentType IMAGE = AgentType._(7, _omitEnumNames ? '' : 'IMAGE');
  static const AgentType AUDIO = AgentType._(8, _omitEnumNames ? '' : 'AUDIO');
  static const AgentType WRITING =
      AgentType._(9, _omitEnumNames ? '' : 'WRITING');
  static const AgentType REASONING =
      AgentType._(10, _omitEnumNames ? '' : 'REASONING');

  static const $core.List<AgentType> values = <AgentType>[
    AGENT_UNKNOWN,
    ORCHESTRATOR,
    KNOWLEDGE,
    MATH,
    CODE,
    DATA_ANALYSIS,
    TRANSLATION,
    IMAGE,
    AUDIO,
    WRITING,
    REASONING,
  ];

  static final $core.List<AgentType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 10);
  static AgentType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const AgentType._(super.value, super.name);
}

class AgentStatus_State extends $pb.ProtobufEnum {
  static const AgentStatus_State UNKNOWN =
      AgentStatus_State._(0, _omitEnumNames ? '' : 'UNKNOWN');
  static const AgentStatus_State THINKING =
      AgentStatus_State._(1, _omitEnumNames ? '' : 'THINKING');
  static const AgentStatus_State SEARCHING =
      AgentStatus_State._(2, _omitEnumNames ? '' : 'SEARCHING');
  static const AgentStatus_State EXECUTING_TOOL =
      AgentStatus_State._(3, _omitEnumNames ? '' : 'EXECUTING_TOOL');
  static const AgentStatus_State GENERATING =
      AgentStatus_State._(4, _omitEnumNames ? '' : 'GENERATING');

  static const $core.List<AgentStatus_State> values = <AgentStatus_State>[
    UNKNOWN,
    THINKING,
    SEARCHING,
    EXECUTING_TOOL,
    GENERATING,
  ];

  static final $core.List<AgentStatus_State?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 4);
  static AgentStatus_State? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const AgentStatus_State._(super.value, super.name);
}

const $core.bool _omitEnumNames =
    $core.bool.fromEnvironment('protobuf.omit_enum_names');
