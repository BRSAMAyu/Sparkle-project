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
    {'1': 'timestamp', '3': 6, '4': 1, '5': 3, '10': 'timestamp'},
  ],
};

/// Descriptor for `WebSocketMessage`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List webSocketMessageDescriptor = $convert.base64Decode(
    'ChBXZWJTb2NrZXRNZXNzYWdlEhgKB3ZlcnNpb24YASABKAlSB3ZlcnNpb24SEgoEdHlwZRgCIA'
    'EoCVIEdHlwZRIYCgdwYXlsb2FkGAMgASgMUgdwYXlsb2FkEhkKCHRyYWNlX2lkGAQgASgJUgd0'
    'cmFjZUlkEh0KCnJlcXVlc3RfaWQYBSABKAlSCXJlcXVlc3RJZBIcCgl0aW1lc3RhbXAYBiABKA'
    'NSCXRpbWVzdGFtcA==');

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
    {'1': 'timestamp', '3': 3, '4': 1, '5': 3, '10': 'timestamp'},
    {'1': 'request_id', '3': 4, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'revision', '3': 5, '4': 1, '5': 5, '10': 'revision'},
  ],
};

/// Descriptor for `UpdateNodeMasteryRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List updateNodeMasteryRequestDescriptor = $convert.base64Decode(
    'ChhVcGRhdGVOb2RlTWFzdGVyeVJlcXVlc3QSFwoHbm9kZV9pZBgBIAEoCVIGbm9kZUlkEhgKB2'
    '1hc3RlcnkYAiABKAVSB21hc3RlcnkSHAoJdGltZXN0YW1wGAMgASgDUgl0aW1lc3RhbXASHQoK'
    'cmVxdWVzdF9pZBgEIAEoCVIJcmVxdWVzdElkEhoKCHJldmlzaW9uGAUgASgFUghyZXZpc2lvbg'
    '==');
