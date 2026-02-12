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

/// Feedback enums for response quality.
class FeedbackType extends $pb.ProtobufEnum {
  static const FeedbackType FEEDBACK_TYPE_UP =
      FeedbackType._(0, _omitEnumNames ? '' : 'FEEDBACK_TYPE_UP');
  static const FeedbackType FEEDBACK_TYPE_DOWN =
      FeedbackType._(1, _omitEnumNames ? '' : 'FEEDBACK_TYPE_DOWN');

  static const $core.List<FeedbackType> values = <FeedbackType>[
    FEEDBACK_TYPE_UP,
    FEEDBACK_TYPE_DOWN,
  ];

  static final $core.List<FeedbackType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 1);
  static FeedbackType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const FeedbackType._(super.value, super.name);
}

class FeedbackReason extends $pb.ProtobufEnum {
  static const FeedbackReason FEEDBACK_REASON_UNSPECIFIED =
      FeedbackReason._(0, _omitEnumNames ? '' : 'FEEDBACK_REASON_UNSPECIFIED');
  static const FeedbackReason FEEDBACK_REASON_INACCURATE =
      FeedbackReason._(1, _omitEnumNames ? '' : 'FEEDBACK_REASON_INACCURATE');
  static const FeedbackReason FEEDBACK_REASON_INCOMPLETE =
      FeedbackReason._(2, _omitEnumNames ? '' : 'FEEDBACK_REASON_INCOMPLETE');
  static const FeedbackReason FEEDBACK_REASON_VERBOSE =
      FeedbackReason._(3, _omitEnumNames ? '' : 'FEEDBACK_REASON_VERBOSE');
  static const FeedbackReason FEEDBACK_REASON_FORMATTING =
      FeedbackReason._(4, _omitEnumNames ? '' : 'FEEDBACK_REASON_FORMATTING');
  static const FeedbackReason FEEDBACK_REASON_MISALIGNED =
      FeedbackReason._(5, _omitEnumNames ? '' : 'FEEDBACK_REASON_MISALIGNED');
  static const FeedbackReason FEEDBACK_REASON_TOO_HARD =
      FeedbackReason._(6, _omitEnumNames ? '' : 'FEEDBACK_REASON_TOO_HARD');
  static const FeedbackReason FEEDBACK_REASON_TOO_SIMPLE =
      FeedbackReason._(7, _omitEnumNames ? '' : 'FEEDBACK_REASON_TOO_SIMPLE');

  static const $core.List<FeedbackReason> values = <FeedbackReason>[
    FEEDBACK_REASON_UNSPECIFIED,
    FEEDBACK_REASON_INACCURATE,
    FEEDBACK_REASON_INCOMPLETE,
    FEEDBACK_REASON_VERBOSE,
    FEEDBACK_REASON_FORMATTING,
    FEEDBACK_REASON_MISALIGNED,
    FEEDBACK_REASON_TOO_HARD,
    FEEDBACK_REASON_TOO_SIMPLE,
  ];

  static final $core.List<FeedbackReason?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 7);
  static FeedbackReason? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const FeedbackReason._(super.value, super.name);
}

/// User decision on a plan review
class PlanReviewDecision extends $pb.ProtobufEnum {
  static const PlanReviewDecision PLAN_REVIEW_DECISION_UNSPECIFIED =
      PlanReviewDecision._(
          0, _omitEnumNames ? '' : 'PLAN_REVIEW_DECISION_UNSPECIFIED');
  static const PlanReviewDecision APPROVE =
      PlanReviewDecision._(1, _omitEnumNames ? '' : 'APPROVE');
  static const PlanReviewDecision REJECT =
      PlanReviewDecision._(2, _omitEnumNames ? '' : 'REJECT');
  static const PlanReviewDecision MODIFY =
      PlanReviewDecision._(3, _omitEnumNames ? '' : 'MODIFY');
  static const PlanReviewDecision ACKNOWLEDGE =
      PlanReviewDecision._(4, _omitEnumNames ? '' : 'ACKNOWLEDGE');

  static const $core.List<PlanReviewDecision> values = <PlanReviewDecision>[
    PLAN_REVIEW_DECISION_UNSPECIFIED,
    APPROVE,
    REJECT,
    MODIFY,
    ACKNOWLEDGE,
  ];

  static final $core.List<PlanReviewDecision?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 4);
  static PlanReviewDecision? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const PlanReviewDecision._(super.value, super.name);
}

class ContentReviewFeedbackType extends $pb.ProtobufEnum {
  static const ContentReviewFeedbackType SATISFIED =
      ContentReviewFeedbackType._(0, _omitEnumNames ? '' : 'SATISFIED');
  static const ContentReviewFeedbackType UNSATISFIED =
      ContentReviewFeedbackType._(1, _omitEnumNames ? '' : 'UNSATISFIED');
  static const ContentReviewFeedbackType MODIFIED =
      ContentReviewFeedbackType._(2, _omitEnumNames ? '' : 'MODIFIED');
  static const ContentReviewFeedbackType REPORTED_ERROR =
      ContentReviewFeedbackType._(3, _omitEnumNames ? '' : 'REPORTED_ERROR');
  static const ContentReviewFeedbackType SKIPPED =
      ContentReviewFeedbackType._(4, _omitEnumNames ? '' : 'SKIPPED');

  static const $core.List<ContentReviewFeedbackType> values =
      <ContentReviewFeedbackType>[
    SATISFIED,
    UNSATISFIED,
    MODIFIED,
    REPORTED_ERROR,
    SKIPPED,
  ];

  static final $core.List<ContentReviewFeedbackType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 4);
  static ContentReviewFeedbackType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const ContentReviewFeedbackType._(super.value, super.name);
}

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

class ErrorCode extends $pb.ProtobufEnum {
  static const ErrorCode ERROR_CODE_UNSPECIFIED =
      ErrorCode._(0, _omitEnumNames ? '' : 'ERROR_CODE_UNSPECIFIED');
  static const ErrorCode ERROR_CODE_UNKNOWN =
      ErrorCode._(1, _omitEnumNames ? '' : 'ERROR_CODE_UNKNOWN');
  static const ErrorCode ERROR_CODE_INVALID_ARGUMENT =
      ErrorCode._(2, _omitEnumNames ? '' : 'ERROR_CODE_INVALID_ARGUMENT');
  static const ErrorCode ERROR_CODE_UNAUTHORIZED =
      ErrorCode._(3, _omitEnumNames ? '' : 'ERROR_CODE_UNAUTHORIZED');
  static const ErrorCode ERROR_CODE_FORBIDDEN =
      ErrorCode._(4, _omitEnumNames ? '' : 'ERROR_CODE_FORBIDDEN');
  static const ErrorCode ERROR_CODE_NOT_FOUND =
      ErrorCode._(5, _omitEnumNames ? '' : 'ERROR_CODE_NOT_FOUND');
  static const ErrorCode ERROR_CODE_CONFLICT =
      ErrorCode._(6, _omitEnumNames ? '' : 'ERROR_CODE_CONFLICT');
  static const ErrorCode ERROR_CODE_RATE_LIMITED =
      ErrorCode._(7, _omitEnumNames ? '' : 'ERROR_CODE_RATE_LIMITED');
  static const ErrorCode ERROR_CODE_UNAVAILABLE =
      ErrorCode._(8, _omitEnumNames ? '' : 'ERROR_CODE_UNAVAILABLE');
  static const ErrorCode ERROR_CODE_TIMEOUT =
      ErrorCode._(9, _omitEnumNames ? '' : 'ERROR_CODE_TIMEOUT');
  static const ErrorCode ERROR_CODE_INTERNAL =
      ErrorCode._(10, _omitEnumNames ? '' : 'ERROR_CODE_INTERNAL');

  static const $core.List<ErrorCode> values = <ErrorCode>[
    ERROR_CODE_UNSPECIFIED,
    ERROR_CODE_UNKNOWN,
    ERROR_CODE_INVALID_ARGUMENT,
    ERROR_CODE_UNAUTHORIZED,
    ERROR_CODE_FORBIDDEN,
    ERROR_CODE_NOT_FOUND,
    ERROR_CODE_CONFLICT,
    ERROR_CODE_RATE_LIMITED,
    ERROR_CODE_UNAVAILABLE,
    ERROR_CODE_TIMEOUT,
    ERROR_CODE_INTERNAL,
  ];

  static final $core.List<ErrorCode?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 10);
  static ErrorCode? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const ErrorCode._(super.value, super.name);
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
  static const AgentStatus_State IDLE =
      AgentStatus_State._(5, _omitEnumNames ? '' : 'IDLE');

  static const $core.List<AgentStatus_State> values = <AgentStatus_State>[
    UNKNOWN,
    THINKING,
    SEARCHING,
    EXECUTING_TOOL,
    GENERATING,
    IDLE,
  ];

  static final $core.List<AgentStatus_State?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 5);
  static AgentStatus_State? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const AgentStatus_State._(super.value, super.name);
}

const $core.bool _omitEnumNames =
    $core.bool.fromEnvironment('protobuf.omit_enum_names');
