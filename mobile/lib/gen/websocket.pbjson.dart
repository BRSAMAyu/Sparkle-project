// This is a generated file - do not edit.
//
// Generated from websocket.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports
// ignore_for_file: unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

@$core.Deprecated('Use webSocketMessageDescriptor instead')
const WebSocketMessage$json = {
  '1': 'WebSocketMessage',
  '2': [
    {'1': 'version', '3': 1, '4': 1, '5': 9, '10': 'version'},
    {'1': 'type', '3': 2, '4': 1, '5': 9, '10': 'type'},
    {'1': 'payload', '3': 3, '4': 1, '5': 12, '10': 'payload'},
    {'1': 'trace_id', '3': 4, '4': 1, '5': 9, '10': 'traceId'},
    {'1': 'request_id', '3': 5, '4': 1, '5': 9, '10': 'requestId'},
    {
      '1': 'event_time',
      '3': 7,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'eventTime'
    },
  ],
  '9': [
    {'1': 6, '2': 7},
  ],
  '10': ['timestamp'],
};

/// Descriptor for `WebSocketMessage`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List webSocketMessageDescriptor = $convert.base64Decode(
    'ChBXZWJTb2NrZXRNZXNzYWdlEhgKB3ZlcnNpb24YASABKAlSB3ZlcnNpb24SEgoEdHlwZRgCIA'
    'EoCVIEdHlwZRIYCgdwYXlsb2FkGAMgASgMUgdwYXlsb2FkEhkKCHRyYWNlX2lkGAQgASgJUgd0'
    'cmFjZUlkEh0KCnJlcXVlc3RfaWQYBSABKAlSCXJlcXVlc3RJZBI5CgpldmVudF90aW1lGAcgAS'
    'gLMhouZ29vZ2xlLnByb3RvYnVmLlRpbWVzdGFtcFIJZXZlbnRUaW1lSgQIBhAHUgl0aW1lc3Rh'
    'bXA=');

@$core.Deprecated('Use chatMessageDescriptor instead')
const ChatMessage$json = {
  '1': 'ChatMessage',
  '2': [
    {'1': 'session_id', '3': 1, '4': 1, '5': 9, '10': 'sessionId'},
    {'1': 'user_id', '3': 2, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'message', '3': 3, '4': 1, '5': 9, '10': 'message'},
    {
      '1': 'tool_calls',
      '3': 4,
      '4': 3,
      '5': 11,
      '6': '.agent.v1.ToolCall',
      '10': 'toolCalls'
    },
  ],
};

/// Descriptor for `ChatMessage`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List chatMessageDescriptor = $convert.base64Decode(
    'CgtDaGF0TWVzc2FnZRIdCgpzZXNzaW9uX2lkGAEgASgJUglzZXNzaW9uSWQSFwoHdXNlcl9pZB'
    'gCIAEoCVIGdXNlcklkEhgKB21lc3NhZ2UYAyABKAlSB21lc3NhZ2USMQoKdG9vbF9jYWxscxgE'
    'IAMoCzISLmFnZW50LnYxLlRvb2xDYWxsUgl0b29sQ2FsbHM=');

@$core.Deprecated('Use updateNodeMasteryRequestDescriptor instead')
const UpdateNodeMasteryRequest$json = {
  '1': 'UpdateNodeMasteryRequest',
  '2': [
    {'1': 'node_id', '3': 1, '4': 1, '5': 9, '10': 'nodeId'},
    {'1': 'mastery', '3': 2, '4': 1, '5': 5, '10': 'mastery'},
    {'1': 'request_id', '3': 4, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'revision', '3': 5, '4': 1, '5': 5, '10': 'revision'},
    {
      '1': 'event_time',
      '3': 6,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'eventTime'
    },
  ],
  '9': [
    {'1': 3, '2': 4},
  ],
  '10': ['timestamp'],
};

/// Descriptor for `UpdateNodeMasteryRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List updateNodeMasteryRequestDescriptor = $convert.base64Decode(
    'ChhVcGRhdGVOb2RlTWFzdGVyeVJlcXVlc3QSFwoHbm9kZV9pZBgBIAEoCVIGbm9kZUlkEhgKB2'
    '1hc3RlcnkYAiABKAVSB21hc3RlcnkSHQoKcmVxdWVzdF9pZBgEIAEoCVIJcmVxdWVzdElkEhoK'
    'CHJldmlzaW9uGAUgASgFUghyZXZpc2lvbhI5CgpldmVudF90aW1lGAYgASgLMhouZ29vZ2xlLn'
    'Byb3RvYnVmLlRpbWVzdGFtcFIJZXZlbnRUaW1lSgQIAxAEUgl0aW1lc3RhbXA=');

@$core.Deprecated('Use interventionPushMessageDescriptor instead')
const InterventionPushMessage$json = {
  '1': 'InterventionPushMessage',
  '2': [
    {'1': 'intervention_id', '3': 1, '4': 1, '5': 9, '10': 'interventionId'},
    {'1': 'level', '3': 2, '4': 1, '5': 9, '10': 'level'},
    {
      '1': 'content',
      '3': 3,
      '4': 1,
      '5': 11,
      '6': '.sparkle.ws.InterventionContent',
      '10': 'content'
    },
    {
      '1': 'actions',
      '3': 4,
      '4': 3,
      '5': 11,
      '6': '.sparkle.ws.InterventionAction',
      '10': 'actions'
    },
    {'1': 'expires_at', '3': 5, '4': 1, '5': 3, '10': 'expiresAt'},
  ],
};

/// Descriptor for `InterventionPushMessage`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List interventionPushMessageDescriptor = $convert.base64Decode(
    'ChdJbnRlcnZlbnRpb25QdXNoTWVzc2FnZRInCg9pbnRlcnZlbnRpb25faWQYASABKAlSDmludG'
    'VydmVudGlvbklkEhQKBWxldmVsGAIgASgJUgVsZXZlbBI5Cgdjb250ZW50GAMgASgLMh8uc3Bh'
    'cmtsZS53cy5JbnRlcnZlbnRpb25Db250ZW50Ugdjb250ZW50EjgKB2FjdGlvbnMYBCADKAsyHi'
    '5zcGFya2xlLndzLkludGVydmVudGlvbkFjdGlvblIHYWN0aW9ucxIdCgpleHBpcmVzX2F0GAUg'
    'ASgDUglleHBpcmVzQXQ=');

@$core.Deprecated('Use interventionContentDescriptor instead')
const InterventionContent$json = {
  '1': 'InterventionContent',
  '2': [
    {'1': 'rendered_message', '3': 1, '4': 1, '5': 9, '10': 'renderedMessage'},
    {'1': 'intent_type', '3': 2, '4': 1, '5': 9, '10': 'intentType'},
    {'1': 'template_id', '3': 3, '4': 1, '5': 9, '10': 'templateId'},
    {
      '1': 'scaffolding_level',
      '3': 4,
      '4': 1,
      '5': 5,
      '10': 'scaffoldingLevel'
    },
    {
      '1': 'context_variables',
      '3': 5,
      '4': 3,
      '5': 11,
      '6': '.sparkle.ws.InterventionContent.ContextVariablesEntry',
      '10': 'contextVariables'
    },
  ],
  '3': [InterventionContent_ContextVariablesEntry$json],
};

@$core.Deprecated('Use interventionContentDescriptor instead')
const InterventionContent_ContextVariablesEntry$json = {
  '1': 'ContextVariablesEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `InterventionContent`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List interventionContentDescriptor = $convert.base64Decode(
    'ChNJbnRlcnZlbnRpb25Db250ZW50EikKEHJlbmRlcmVkX21lc3NhZ2UYASABKAlSD3JlbmRlcm'
    'VkTWVzc2FnZRIfCgtpbnRlbnRfdHlwZRgCIAEoCVIKaW50ZW50VHlwZRIfCgt0ZW1wbGF0ZV9p'
    'ZBgDIAEoCVIKdGVtcGxhdGVJZBIrChFzY2FmZm9sZGluZ19sZXZlbBgEIAEoBVIQc2NhZmZvbG'
    'RpbmdMZXZlbBJiChFjb250ZXh0X3ZhcmlhYmxlcxgFIAMoCzI1LnNwYXJrbGUud3MuSW50ZXJ2'
    'ZW50aW9uQ29udGVudC5Db250ZXh0VmFyaWFibGVzRW50cnlSEGNvbnRleHRWYXJpYWJsZXMaQw'
    'oVQ29udGV4dFZhcmlhYmxlc0VudHJ5EhAKA2tleRgBIAEoCVIDa2V5EhQKBXZhbHVlGAIgASgJ'
    'UgV2YWx1ZToCOAE=');

@$core.Deprecated('Use interventionActionDescriptor instead')
const InterventionAction$json = {
  '1': 'InterventionAction',
  '2': [
    {'1': 'id', '3': 1, '4': 1, '5': 9, '10': 'id'},
    {'1': 'label', '3': 2, '4': 1, '5': 9, '10': 'label'},
    {'1': 'type', '3': 3, '4': 1, '5': 9, '10': 'type'},
  ],
};

/// Descriptor for `InterventionAction`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List interventionActionDescriptor = $convert.base64Decode(
    'ChJJbnRlcnZlbnRpb25BY3Rpb24SDgoCaWQYASABKAlSAmlkEhQKBWxhYmVsGAIgASgJUgVsYW'
    'JlbBISCgR0eXBlGAMgASgJUgR0eXBl');
