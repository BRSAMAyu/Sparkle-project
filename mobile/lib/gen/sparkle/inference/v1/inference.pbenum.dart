// This is a generated file - do not edit.
//
// Generated from sparkle/inference/v1/inference.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

class TaskType extends $pb.ProtobufEnum {
  static const TaskType TASK_TYPE_UNSPECIFIED =
      TaskType._(0, _omitEnumNames ? '' : 'TASK_TYPE_UNSPECIFIED');
  static const TaskType SHORT_INFERENCE =
      TaskType._(1, _omitEnumNames ? '' : 'SHORT_INFERENCE');
  static const TaskType HEAVY_JOB =
      TaskType._(2, _omitEnumNames ? '' : 'HEAVY_JOB');
  static const TaskType SIGNAL_EXTRACTION =
      TaskType._(3, _omitEnumNames ? '' : 'SIGNAL_EXTRACTION');
  static const TaskType OCR = TaskType._(4, _omitEnumNames ? '' : 'OCR');
  static const TaskType TRANSLATE =
      TaskType._(5, _omitEnumNames ? '' : 'TRANSLATE');
  static const TaskType EMBEDDING =
      TaskType._(6, _omitEnumNames ? '' : 'EMBEDDING');
  static const TaskType RERANK = TaskType._(7, _omitEnumNames ? '' : 'RERANK');
  static const TaskType PREDICT_NEXT_ACTIONS =
      TaskType._(8, _omitEnumNames ? '' : 'PREDICT_NEXT_ACTIONS');
  static const TaskType VERIFY_PLAN =
      TaskType._(9, _omitEnumNames ? '' : 'VERIFY_PLAN');

  static const $core.List<TaskType> values = <TaskType>[
    TASK_TYPE_UNSPECIFIED,
    SHORT_INFERENCE,
    HEAVY_JOB,
    SIGNAL_EXTRACTION,
    OCR,
    TRANSLATE,
    EMBEDDING,
    RERANK,
    PREDICT_NEXT_ACTIONS,
    VERIFY_PLAN,
  ];

  static final $core.List<TaskType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 9);
  static TaskType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const TaskType._(super.value, super.name);
}

class Priority extends $pb.ProtobufEnum {
  static const Priority PRIORITY_UNSPECIFIED =
      Priority._(0, _omitEnumNames ? '' : 'PRIORITY_UNSPECIFIED');
  static const Priority P0 = Priority._(1, _omitEnumNames ? '' : 'P0');
  static const Priority P1 = Priority._(2, _omitEnumNames ? '' : 'P1');
  static const Priority P2 = Priority._(3, _omitEnumNames ? '' : 'P2');

  static const $core.List<Priority> values = <Priority>[
    PRIORITY_UNSPECIFIED,
    P0,
    P1,
    P2,
  ];

  static final $core.List<Priority?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 3);
  static Priority? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const Priority._(super.value, super.name);
}

class ResponseFormat extends $pb.ProtobufEnum {
  static const ResponseFormat RESPONSE_FORMAT_UNSPECIFIED =
      ResponseFormat._(0, _omitEnumNames ? '' : 'RESPONSE_FORMAT_UNSPECIFIED');
  static const ResponseFormat JSON_OBJECT =
      ResponseFormat._(1, _omitEnumNames ? '' : 'JSON_OBJECT');
  static const ResponseFormat TEXT =
      ResponseFormat._(2, _omitEnumNames ? '' : 'TEXT');

  static const $core.List<ResponseFormat> values = <ResponseFormat>[
    RESPONSE_FORMAT_UNSPECIFIED,
    JSON_OBJECT,
    TEXT,
  ];

  static final $core.List<ResponseFormat?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 2);
  static ResponseFormat? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const ResponseFormat._(super.value, super.name);
}

class ErrorReason extends $pb.ProtobufEnum {
  static const ErrorReason ERROR_REASON_UNSPECIFIED =
      ErrorReason._(0, _omitEnumNames ? '' : 'ERROR_REASON_UNSPECIFIED');
  static const ErrorReason QUOTA_EXCEEDED =
      ErrorReason._(1, _omitEnumNames ? '' : 'QUOTA_EXCEEDED');
  static const ErrorReason PROVIDER_UNAVAILABLE =
      ErrorReason._(2, _omitEnumNames ? '' : 'PROVIDER_UNAVAILABLE');
  static const ErrorReason SCHEMA_VIOLATION =
      ErrorReason._(3, _omitEnumNames ? '' : 'SCHEMA_VIOLATION');
  static const ErrorReason BUDGET_EXHAUSTED =
      ErrorReason._(4, _omitEnumNames ? '' : 'BUDGET_EXHAUSTED');
  static const ErrorReason TIMEOUT =
      ErrorReason._(5, _omitEnumNames ? '' : 'TIMEOUT');

  static const $core.List<ErrorReason> values = <ErrorReason>[
    ERROR_REASON_UNSPECIFIED,
    QUOTA_EXCEEDED,
    PROVIDER_UNAVAILABLE,
    SCHEMA_VIOLATION,
    BUDGET_EXHAUSTED,
    TIMEOUT,
  ];

  static final $core.List<ErrorReason?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 5);
  static ErrorReason? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const ErrorReason._(super.value, super.name);
}

const $core.bool _omitEnumNames =
    $core.bool.fromEnvironment('protobuf.omit_enum_names');
