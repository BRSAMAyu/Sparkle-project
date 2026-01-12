//
//  Generated code. Do not modify.
//  source: agent_service.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

import 'google/protobuf/struct.pbjson.dart' as $1;
import 'google/protobuf/timestamp.pbjson.dart' as $2;

@$core.Deprecated('Use finishReasonDescriptor instead')
const FinishReason$json = {
  '1': 'FinishReason',
  '2': [
    {'1': 'NULL', '2': 0},
    {'1': 'STOP', '2': 1},
    {'1': 'LENGTH', '2': 2},
    {'1': 'TOOL_CALLS', '2': 3},
    {'1': 'CONTENT_FILTER', '2': 4},
    {'1': 'ERROR', '2': 5},
  ],
};

/// Descriptor for `FinishReason`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List finishReasonDescriptor = $convert.base64Decode(
    'CgxGaW5pc2hSZWFzb24SCAoETlVMTBAAEggKBFNUT1AQARIKCgZMRU5HVEgQAhIOCgpUT09MX0'
    'NBTExTEAMSEgoOQ09OVEVOVF9GSUxURVIQBBIJCgVFUlJPUhAF');

@$core.Deprecated('Use interventionLevelDescriptor instead')
const InterventionLevel$json = {
  '1': 'InterventionLevel',
  '2': [
    {'1': 'SILENT_MARKER', '2': 0},
    {'1': 'TOAST', '2': 1},
    {'1': 'CARD', '2': 2},
    {'1': 'FULL_SCREEN_MODAL', '2': 3},
  ],
};

/// Descriptor for `InterventionLevel`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List interventionLevelDescriptor = $convert.base64Decode(
    'ChFJbnRlcnZlbnRpb25MZXZlbBIRCg1TSUxFTlRfTUFSS0VSEAASCQoFVE9BU1QQARIICgRDQV'
    'JEEAISFQoRRlVMTF9TQ1JFRU5fTU9EQUwQAw==');

@$core.Deprecated('Use agentTypeDescriptor instead')
const AgentType$json = {
  '1': 'AgentType',
  '2': [
    {'1': 'AGENT_UNKNOWN', '2': 0},
    {'1': 'ORCHESTRATOR', '2': 1},
    {'1': 'KNOWLEDGE', '2': 2},
    {'1': 'MATH', '2': 3},
    {'1': 'CODE', '2': 4},
    {'1': 'DATA_ANALYSIS', '2': 5},
    {'1': 'TRANSLATION', '2': 6},
    {'1': 'IMAGE', '2': 7},
    {'1': 'AUDIO', '2': 8},
    {'1': 'WRITING', '2': 9},
    {'1': 'REASONING', '2': 10},
  ],
};

/// Descriptor for `AgentType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List agentTypeDescriptor = $convert.base64Decode(
    'CglBZ2VudFR5cGUSEQoNQUdFTlRfVU5LTk9XThAAEhAKDE9SQ0hFU1RSQVRPUhABEg0KCUtOT1'
    'dMRURHRRACEggKBE1BVEgQAxIICgRDT0RFEAQSEQoNREFUQV9BTkFMWVNJUxAFEg8KC1RSQU5T'
    'TEFUSU9OEAYSCQoFSU1BR0UQBxIJCgVBVURJTxAIEgsKB1dSSVRJTkcQCRINCglSRUFTT05JTk'
    'cQCg==');

@$core.Deprecated('Use chatRequestDescriptor instead')
const ChatRequest$json = {
  '1': 'ChatRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'session_id', '3': 2, '4': 1, '5': 9, '10': 'sessionId'},
    {'1': 'message', '3': 3, '4': 1, '5': 9, '9': 0, '10': 'message'},
    {'1': 'tool_result', '3': 7, '4': 1, '5': 11, '6': '.agent.v1.ToolResult', '9': 0, '10': 'toolResult'},
    {'1': 'user_profile', '3': 4, '4': 1, '5': 11, '6': '.agent.v1.UserProfile', '10': 'userProfile'},
    {'1': 'extra_context', '3': 5, '4': 1, '5': 11, '6': '.google.protobuf.Struct', '10': 'extraContext'},
    {'1': 'history', '3': 6, '4': 3, '5': 11, '6': '.agent.v1.ChatMessage', '10': 'history'},
    {'1': 'config', '3': 8, '4': 1, '5': 11, '6': '.agent.v1.ChatConfig', '10': 'config'},
    {'1': 'request_id', '3': 9, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'file_ids', '3': 10, '4': 3, '5': 9, '10': 'fileIds'},
    {'1': 'include_references', '3': 11, '4': 1, '5': 8, '10': 'includeReferences'},
    {'1': 'active_tools', '3': 12, '4': 3, '5': 9, '10': 'activeTools'},
  ],
  '8': [
    {'1': 'input'},
  ],
};

/// Descriptor for `ChatRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List chatRequestDescriptor = $convert.base64Decode(
    'CgtDaGF0UmVxdWVzdBIXCgd1c2VyX2lkGAEgASgJUgZ1c2VySWQSHQoKc2Vzc2lvbl9pZBgCIA'
    'EoCVIJc2Vzc2lvbklkEhoKB21lc3NhZ2UYAyABKAlIAFIHbWVzc2FnZRI3Cgt0b29sX3Jlc3Vs'
    'dBgHIAEoCzIULmFnZW50LnYxLlRvb2xSZXN1bHRIAFIKdG9vbFJlc3VsdBI4Cgx1c2VyX3Byb2'
    'ZpbGUYBCABKAsyFS5hZ2VudC52MS5Vc2VyUHJvZmlsZVILdXNlclByb2ZpbGUSPAoNZXh0cmFf'
    'Y29udGV4dBgFIAEoCzIXLmdvb2dsZS5wcm90b2J1Zi5TdHJ1Y3RSDGV4dHJhQ29udGV4dBIvCg'
    'doaXN0b3J5GAYgAygLMhUuYWdlbnQudjEuQ2hhdE1lc3NhZ2VSB2hpc3RvcnkSLAoGY29uZmln'
    'GAggASgLMhQuYWdlbnQudjEuQ2hhdENvbmZpZ1IGY29uZmlnEh0KCnJlcXVlc3RfaWQYCSABKA'
    'lSCXJlcXVlc3RJZBIZCghmaWxlX2lkcxgKIAMoCVIHZmlsZUlkcxItChJpbmNsdWRlX3JlZmVy'
    'ZW5jZXMYCyABKAhSEWluY2x1ZGVSZWZlcmVuY2VzEiEKDGFjdGl2ZV90b29scxgMIAMoCVILYW'
    'N0aXZlVG9vbHNCBwoFaW5wdXQ=');

@$core.Deprecated('Use userProfileDescriptor instead')
const UserProfile$json = {
  '1': 'UserProfile',
  '2': [
    {'1': 'nickname', '3': 1, '4': 1, '5': 9, '10': 'nickname'},
    {'1': 'timezone', '3': 2, '4': 1, '5': 9, '10': 'timezone'},
    {'1': 'language', '3': 3, '4': 1, '5': 9, '10': 'language'},
    {'1': 'is_pro', '3': 4, '4': 1, '5': 8, '10': 'isPro'},
    {'1': 'preferences', '3': 5, '4': 3, '5': 11, '6': '.agent.v1.UserProfile.PreferencesEntry', '10': 'preferences'},
    {'1': 'extra_context', '3': 6, '4': 1, '5': 9, '10': 'extraContext'},
    {'1': 'level', '3': 7, '4': 1, '5': 5, '10': 'level'},
    {'1': 'avatar_url', '3': 8, '4': 1, '5': 9, '10': 'avatarUrl'},
  ],
  '3': [UserProfile_PreferencesEntry$json],
};

@$core.Deprecated('Use userProfileDescriptor instead')
const UserProfile_PreferencesEntry$json = {
  '1': 'PreferencesEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `UserProfile`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List userProfileDescriptor = $convert.base64Decode(
    'CgtVc2VyUHJvZmlsZRIaCghuaWNrbmFtZRgBIAEoCVIIbmlja25hbWUSGgoIdGltZXpvbmUYAi'
    'ABKAlSCHRpbWV6b25lEhoKCGxhbmd1YWdlGAMgASgJUghsYW5ndWFnZRIVCgZpc19wcm8YBCAB'
    'KAhSBWlzUHJvEkgKC3ByZWZlcmVuY2VzGAUgAygLMiYuYWdlbnQudjEuVXNlclByb2ZpbGUuUH'
    'JlZmVyZW5jZXNFbnRyeVILcHJlZmVyZW5jZXMSIwoNZXh0cmFfY29udGV4dBgGIAEoCVIMZXh0'
    'cmFDb250ZXh0EhQKBWxldmVsGAcgASgFUgVsZXZlbBIdCgphdmF0YXJfdXJsGAggASgJUglhdm'
    'F0YXJVcmwaPgoQUHJlZmVyZW5jZXNFbnRyeRIQCgNrZXkYASABKAlSA2tleRIUCgV2YWx1ZRgC'
    'IAEoCVIFdmFsdWU6AjgB');

@$core.Deprecated('Use profileRequestDescriptor instead')
const ProfileRequest$json = {
  '1': 'ProfileRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
  ],
};

/// Descriptor for `ProfileRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List profileRequestDescriptor = $convert.base64Decode(
    'Cg5Qcm9maWxlUmVxdWVzdBIXCgd1c2VyX2lkGAEgASgJUgZ1c2VySWQ=');

@$core.Deprecated('Use weeklyReportRequestDescriptor instead')
const WeeklyReportRequest$json = {
  '1': 'WeeklyReportRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'week_id', '3': 2, '4': 1, '5': 9, '10': 'weekId'},
  ],
};

/// Descriptor for `WeeklyReportRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List weeklyReportRequestDescriptor = $convert.base64Decode(
    'ChNXZWVrbHlSZXBvcnRSZXF1ZXN0EhcKB3VzZXJfaWQYASABKAlSBnVzZXJJZBIXCgd3ZWVrX2'
    'lkGAIgASgJUgZ3ZWVrSWQ=');

@$core.Deprecated('Use weeklyReportDescriptor instead')
const WeeklyReport$json = {
  '1': 'WeeklyReport',
  '2': [
    {'1': 'summary', '3': 1, '4': 1, '5': 9, '10': 'summary'},
    {'1': 'tasks_completed', '3': 2, '4': 1, '5': 5, '10': 'tasksCompleted'},
  ],
};

/// Descriptor for `WeeklyReport`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List weeklyReportDescriptor = $convert.base64Decode(
    'CgxXZWVrbHlSZXBvcnQSGAoHc3VtbWFyeRgBIAEoCVIHc3VtbWFyeRInCg90YXNrc19jb21wbG'
    'V0ZWQYAiABKAVSDnRhc2tzQ29tcGxldGVk');

@$core.Deprecated('Use toolResultDescriptor instead')
const ToolResult$json = {
  '1': 'ToolResult',
  '2': [
    {'1': 'tool_call_id', '3': 1, '4': 1, '5': 9, '10': 'toolCallId'},
    {'1': 'tool_name', '3': 2, '4': 1, '5': 9, '10': 'toolName'},
    {'1': 'result_json', '3': 3, '4': 1, '5': 9, '10': 'resultJson'},
    {'1': 'is_error', '3': 4, '4': 1, '5': 8, '10': 'isError'},
    {'1': 'error_message', '3': 5, '4': 1, '5': 9, '10': 'errorMessage'},
  ],
};

/// Descriptor for `ToolResult`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List toolResultDescriptor = $convert.base64Decode(
    'CgpUb29sUmVzdWx0EiAKDHRvb2xfY2FsbF9pZBgBIAEoCVIKdG9vbENhbGxJZBIbCgl0b29sX2'
    '5hbWUYAiABKAlSCHRvb2xOYW1lEh8KC3Jlc3VsdF9qc29uGAMgASgJUgpyZXN1bHRKc29uEhkK'
    'CGlzX2Vycm9yGAQgASgIUgdpc0Vycm9yEiMKDWVycm9yX21lc3NhZ2UYBSABKAlSDGVycm9yTW'
    'Vzc2FnZQ==');

@$core.Deprecated('Use chatConfigDescriptor instead')
const ChatConfig$json = {
  '1': 'ChatConfig',
  '2': [
    {'1': 'model', '3': 1, '4': 1, '5': 9, '10': 'model'},
    {'1': 'temperature', '3': 2, '4': 1, '5': 2, '10': 'temperature'},
    {'1': 'max_tokens', '3': 3, '4': 1, '5': 5, '10': 'maxTokens'},
    {'1': 'tools_enabled', '3': 4, '4': 1, '5': 8, '10': 'toolsEnabled'},
  ],
};

/// Descriptor for `ChatConfig`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List chatConfigDescriptor = $convert.base64Decode(
    'CgpDaGF0Q29uZmlnEhQKBW1vZGVsGAEgASgJUgVtb2RlbBIgCgt0ZW1wZXJhdHVyZRgCIAEoAl'
    'ILdGVtcGVyYXR1cmUSHQoKbWF4X3Rva2VucxgDIAEoBVIJbWF4VG9rZW5zEiMKDXRvb2xzX2Vu'
    'YWJsZWQYBCABKAhSDHRvb2xzRW5hYmxlZA==');

@$core.Deprecated('Use chatMessageDescriptor instead')
const ChatMessage$json = {
  '1': 'ChatMessage',
  '2': [
    {'1': 'role', '3': 1, '4': 1, '5': 9, '10': 'role'},
    {'1': 'content', '3': 2, '4': 1, '5': 9, '10': 'content'},
    {'1': 'name', '3': 3, '4': 1, '5': 9, '10': 'name'},
    {'1': 'tool_call_id', '3': 4, '4': 1, '5': 9, '10': 'toolCallId'},
    {'1': 'metadata', '3': 5, '4': 3, '5': 11, '6': '.agent.v1.ChatMessage.MetadataEntry', '10': 'metadata'},
  ],
  '3': [ChatMessage_MetadataEntry$json],
};

@$core.Deprecated('Use chatMessageDescriptor instead')
const ChatMessage_MetadataEntry$json = {
  '1': 'MetadataEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `ChatMessage`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List chatMessageDescriptor = $convert.base64Decode(
    'CgtDaGF0TWVzc2FnZRISCgRyb2xlGAEgASgJUgRyb2xlEhgKB2NvbnRlbnQYAiABKAlSB2Nvbn'
    'RlbnQSEgoEbmFtZRgDIAEoCVIEbmFtZRIgCgx0b29sX2NhbGxfaWQYBCABKAlSCnRvb2xDYWxs'
    'SWQSPwoIbWV0YWRhdGEYBSADKAsyIy5hZ2VudC52MS5DaGF0TWVzc2FnZS5NZXRhZGF0YUVudH'
    'J5UghtZXRhZGF0YRo7Cg1NZXRhZGF0YUVudHJ5EhAKA2tleRgBIAEoCVIDa2V5EhQKBXZhbHVl'
    'GAIgASgJUgV2YWx1ZToCOAE=');

@$core.Deprecated('Use chatResponseDescriptor instead')
const ChatResponse$json = {
  '1': 'ChatResponse',
  '2': [
    {'1': 'response_id', '3': 1, '4': 1, '5': 9, '10': 'responseId'},
    {'1': 'created_at', '3': 2, '4': 1, '5': 3, '10': 'createdAt'},
    {'1': 'request_id', '3': 10, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'delta', '3': 3, '4': 1, '5': 9, '9': 0, '10': 'delta'},
    {'1': 'tool_call', '3': 4, '4': 1, '5': 11, '6': '.agent.v1.ToolCall', '9': 0, '10': 'toolCall'},
    {'1': 'status_update', '3': 5, '4': 1, '5': 11, '6': '.agent.v1.AgentStatus', '9': 0, '10': 'statusUpdate'},
    {'1': 'full_text', '3': 6, '4': 1, '5': 9, '9': 0, '10': 'fullText'},
    {'1': 'error', '3': 7, '4': 1, '5': 11, '6': '.agent.v1.Error', '9': 0, '10': 'error'},
    {'1': 'usage', '3': 8, '4': 1, '5': 11, '6': '.agent.v1.Usage', '9': 0, '10': 'usage'},
    {'1': 'citations', '3': 11, '4': 1, '5': 11, '6': '.agent.v1.CitationBlock', '9': 0, '10': 'citations'},
    {'1': 'tool_result', '3': 12, '4': 1, '5': 11, '6': '.agent.v1.ToolResultPayload', '9': 0, '10': 'toolResult'},
    {'1': 'intervention', '3': 14, '4': 1, '5': 11, '6': '.agent.v1.InterventionPayload', '9': 0, '10': 'intervention'},
    {'1': 'finish_reason', '3': 9, '4': 1, '5': 14, '6': '.agent.v1.FinishReason', '10': 'finishReason'},
    {'1': 'timestamp', '3': 13, '4': 1, '5': 3, '10': 'timestamp'},
  ],
  '8': [
    {'1': 'content'},
  ],
};

/// Descriptor for `ChatResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List chatResponseDescriptor = $convert.base64Decode(
    'CgxDaGF0UmVzcG9uc2USHwoLcmVzcG9uc2VfaWQYASABKAlSCnJlc3BvbnNlSWQSHQoKY3JlYX'
    'RlZF9hdBgCIAEoA1IJY3JlYXRlZEF0Eh0KCnJlcXVlc3RfaWQYCiABKAlSCXJlcXVlc3RJZBIW'
    'CgVkZWx0YRgDIAEoCUgAUgVkZWx0YRIxCgl0b29sX2NhbGwYBCABKAsyEi5hZ2VudC52MS5Ub2'
    '9sQ2FsbEgAUgh0b29sQ2FsbBI8Cg1zdGF0dXNfdXBkYXRlGAUgASgLMhUuYWdlbnQudjEuQWdl'
    'bnRTdGF0dXNIAFIMc3RhdHVzVXBkYXRlEh0KCWZ1bGxfdGV4dBgGIAEoCUgAUghmdWxsVGV4dB'
    'InCgVlcnJvchgHIAEoCzIPLmFnZW50LnYxLkVycm9ySABSBWVycm9yEicKBXVzYWdlGAggASgL'
    'Mg8uYWdlbnQudjEuVXNhZ2VIAFIFdXNhZ2USNwoJY2l0YXRpb25zGAsgASgLMhcuYWdlbnQudj'
    'EuQ2l0YXRpb25CbG9ja0gAUgljaXRhdGlvbnMSPgoLdG9vbF9yZXN1bHQYDCABKAsyGy5hZ2Vu'
    'dC52MS5Ub29sUmVzdWx0UGF5bG9hZEgAUgp0b29sUmVzdWx0EkMKDGludGVydmVudGlvbhgOIA'
    'EoCzIdLmFnZW50LnYxLkludGVydmVudGlvblBheWxvYWRIAFIMaW50ZXJ2ZW50aW9uEjsKDWZp'
    'bmlzaF9yZWFzb24YCSABKA4yFi5hZ2VudC52MS5GaW5pc2hSZWFzb25SDGZpbmlzaFJlYXNvbh'
    'IcCgl0aW1lc3RhbXAYDSABKANSCXRpbWVzdGFtcEIJCgdjb250ZW50');

@$core.Deprecated('Use citationBlockDescriptor instead')
const CitationBlock$json = {
  '1': 'CitationBlock',
  '2': [
    {'1': 'citations', '3': 1, '4': 3, '5': 11, '6': '.agent.v1.Citation', '10': 'citations'},
  ],
};

/// Descriptor for `CitationBlock`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List citationBlockDescriptor = $convert.base64Decode(
    'Cg1DaXRhdGlvbkJsb2NrEjAKCWNpdGF0aW9ucxgBIAMoCzISLmFnZW50LnYxLkNpdGF0aW9uUg'
    'ljaXRhdGlvbnM=');

@$core.Deprecated('Use citationDescriptor instead')
const Citation$json = {
  '1': 'Citation',
  '2': [
    {'1': 'id', '3': 1, '4': 1, '5': 9, '10': 'id'},
    {'1': 'title', '3': 2, '4': 1, '5': 9, '10': 'title'},
    {'1': 'content', '3': 3, '4': 1, '5': 9, '10': 'content'},
    {'1': 'source_type', '3': 4, '4': 1, '5': 9, '10': 'sourceType'},
    {'1': 'url', '3': 5, '4': 1, '5': 9, '10': 'url'},
    {'1': 'score', '3': 6, '4': 1, '5': 2, '10': 'score'},
    {'1': 'file_id', '3': 7, '4': 1, '5': 9, '10': 'fileId'},
    {'1': 'page_number', '3': 8, '4': 1, '5': 5, '10': 'pageNumber'},
    {'1': 'chunk_index', '3': 9, '4': 1, '5': 5, '10': 'chunkIndex'},
    {'1': 'section_title', '3': 10, '4': 1, '5': 9, '10': 'sectionTitle'},
  ],
};

/// Descriptor for `Citation`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List citationDescriptor = $convert.base64Decode(
    'CghDaXRhdGlvbhIOCgJpZBgBIAEoCVICaWQSFAoFdGl0bGUYAiABKAlSBXRpdGxlEhgKB2Nvbn'
    'RlbnQYAyABKAlSB2NvbnRlbnQSHwoLc291cmNlX3R5cGUYBCABKAlSCnNvdXJjZVR5cGUSEAoD'
    'dXJsGAUgASgJUgN1cmwSFAoFc2NvcmUYBiABKAJSBXNjb3JlEhcKB2ZpbGVfaWQYByABKAlSBm'
    'ZpbGVJZBIfCgtwYWdlX251bWJlchgIIAEoBVIKcGFnZU51bWJlchIfCgtjaHVua19pbmRleBgJ'
    'IAEoBVIKY2h1bmtJbmRleBIjCg1zZWN0aW9uX3RpdGxlGAogASgJUgxzZWN0aW9uVGl0bGU=');

@$core.Deprecated('Use toolCallDescriptor instead')
const ToolCall$json = {
  '1': 'ToolCall',
  '2': [
    {'1': 'id', '3': 1, '4': 1, '5': 9, '10': 'id'},
    {'1': 'name', '3': 2, '4': 1, '5': 9, '10': 'name'},
    {'1': 'arguments', '3': 3, '4': 1, '5': 9, '10': 'arguments'},
  ],
};

/// Descriptor for `ToolCall`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List toolCallDescriptor = $convert.base64Decode(
    'CghUb29sQ2FsbBIOCgJpZBgBIAEoCVICaWQSEgoEbmFtZRgCIAEoCVIEbmFtZRIcCglhcmd1bW'
    'VudHMYAyABKAlSCWFyZ3VtZW50cw==');

@$core.Deprecated('Use toolResultPayloadDescriptor instead')
const ToolResultPayload$json = {
  '1': 'ToolResultPayload',
  '2': [
    {'1': 'tool_name', '3': 1, '4': 1, '5': 9, '10': 'toolName'},
    {'1': 'success', '3': 2, '4': 1, '5': 8, '10': 'success'},
    {'1': 'data', '3': 3, '4': 1, '5': 11, '6': '.google.protobuf.Struct', '10': 'data'},
    {'1': 'error_message', '3': 4, '4': 1, '5': 9, '10': 'errorMessage'},
    {'1': 'suggestion', '3': 5, '4': 1, '5': 9, '10': 'suggestion'},
    {'1': 'widget_type', '3': 6, '4': 1, '5': 9, '10': 'widgetType'},
    {'1': 'widget_data', '3': 7, '4': 1, '5': 11, '6': '.google.protobuf.Struct', '10': 'widgetData'},
    {'1': 'tool_call_id', '3': 8, '4': 1, '5': 9, '10': 'toolCallId'},
  ],
};

/// Descriptor for `ToolResultPayload`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List toolResultPayloadDescriptor = $convert.base64Decode(
    'ChFUb29sUmVzdWx0UGF5bG9hZBIbCgl0b29sX25hbWUYASABKAlSCHRvb2xOYW1lEhgKB3N1Y2'
    'Nlc3MYAiABKAhSB3N1Y2Nlc3MSKwoEZGF0YRgDIAEoCzIXLmdvb2dsZS5wcm90b2J1Zi5TdHJ1'
    'Y3RSBGRhdGESIwoNZXJyb3JfbWVzc2FnZRgEIAEoCVIMZXJyb3JNZXNzYWdlEh4KCnN1Z2dlc3'
    'Rpb24YBSABKAlSCnN1Z2dlc3Rpb24SHwoLd2lkZ2V0X3R5cGUYBiABKAlSCndpZGdldFR5cGUS'
    'OAoLd2lkZ2V0X2RhdGEYByABKAsyFy5nb29nbGUucHJvdG9idWYuU3RydWN0Ugp3aWRnZXREYX'
    'RhEiAKDHRvb2xfY2FsbF9pZBgIIAEoCVIKdG9vbENhbGxJZA==');

@$core.Deprecated('Use evidenceRefDescriptor instead')
const EvidenceRef$json = {
  '1': 'EvidenceRef',
  '2': [
    {'1': 'type', '3': 1, '4': 1, '5': 9, '10': 'type'},
    {'1': 'id', '3': 2, '4': 1, '5': 9, '10': 'id'},
    {'1': 'schema_version', '3': 3, '4': 1, '5': 9, '10': 'schemaVersion'},
    {'1': 'user_deleted', '3': 4, '4': 1, '5': 8, '10': 'userDeleted'},
  ],
};

/// Descriptor for `EvidenceRef`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List evidenceRefDescriptor = $convert.base64Decode(
    'CgtFdmlkZW5jZVJlZhISCgR0eXBlGAEgASgJUgR0eXBlEg4KAmlkGAIgASgJUgJpZBIlCg5zY2'
    'hlbWFfdmVyc2lvbhgDIAEoCVINc2NoZW1hVmVyc2lvbhIhCgx1c2VyX2RlbGV0ZWQYBCABKAhS'
    'C3VzZXJEZWxldGVk');

@$core.Deprecated('Use coolDownPolicyDescriptor instead')
const CoolDownPolicy$json = {
  '1': 'CoolDownPolicy',
  '2': [
    {'1': 'policy', '3': 1, '4': 1, '5': 9, '10': 'policy'},
    {'1': 'until_ms', '3': 2, '4': 1, '5': 3, '10': 'untilMs'},
  ],
};

/// Descriptor for `CoolDownPolicy`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List coolDownPolicyDescriptor = $convert.base64Decode(
    'Cg5Db29sRG93blBvbGljeRIWCgZwb2xpY3kYASABKAlSBnBvbGljeRIZCgh1bnRpbF9tcxgCIA'
    'EoA1IHdW50aWxNcw==');

@$core.Deprecated('Use interventionReasonDescriptor instead')
const InterventionReason$json = {
  '1': 'InterventionReason',
  '2': [
    {'1': 'trigger_event_id', '3': 1, '4': 1, '5': 9, '10': 'triggerEventId'},
    {'1': 'explanation_text', '3': 2, '4': 1, '5': 9, '10': 'explanationText'},
    {'1': 'confidence', '3': 3, '4': 1, '5': 2, '10': 'confidence'},
    {'1': 'evidence_refs', '3': 4, '4': 3, '5': 11, '6': '.agent.v1.EvidenceRef', '10': 'evidenceRefs'},
    {'1': 'decision_trace', '3': 5, '4': 3, '5': 9, '10': 'decisionTrace'},
  ],
};

/// Descriptor for `InterventionReason`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List interventionReasonDescriptor = $convert.base64Decode(
    'ChJJbnRlcnZlbnRpb25SZWFzb24SKAoQdHJpZ2dlcl9ldmVudF9pZBgBIAEoCVIOdHJpZ2dlck'
    'V2ZW50SWQSKQoQZXhwbGFuYXRpb25fdGV4dBgCIAEoCVIPZXhwbGFuYXRpb25UZXh0Eh4KCmNv'
    'bmZpZGVuY2UYAyABKAJSCmNvbmZpZGVuY2USOgoNZXZpZGVuY2VfcmVmcxgEIAMoCzIVLmFnZW'
    '50LnYxLkV2aWRlbmNlUmVmUgxldmlkZW5jZVJlZnMSJQoOZGVjaXNpb25fdHJhY2UYBSADKAlS'
    'DWRlY2lzaW9uVHJhY2U=');

@$core.Deprecated('Use interventionRequestDescriptor instead')
const InterventionRequest$json = {
  '1': 'InterventionRequest',
  '2': [
    {'1': 'id', '3': 1, '4': 1, '5': 9, '10': 'id'},
    {'1': 'dedupe_key', '3': 2, '4': 1, '5': 9, '10': 'dedupeKey'},
    {'1': 'topic', '3': 3, '4': 1, '5': 9, '10': 'topic'},
    {'1': 'created_at_ms', '3': 4, '4': 1, '5': 3, '10': 'createdAtMs'},
    {'1': 'expires_at_ms', '3': 5, '4': 1, '5': 3, '10': 'expiresAtMs'},
    {'1': 'is_retractable', '3': 6, '4': 1, '5': 8, '10': 'isRetractable'},
    {'1': 'supersedes_id', '3': 7, '4': 1, '5': 9, '10': 'supersedesId'},
    {'1': 'schema_version', '3': 8, '4': 1, '5': 9, '10': 'schemaVersion'},
    {'1': 'policy_version', '3': 9, '4': 1, '5': 9, '10': 'policyVersion'},
    {'1': 'model_version', '3': 10, '4': 1, '5': 9, '10': 'modelVersion'},
    {'1': 'reason', '3': 11, '4': 1, '5': 11, '6': '.agent.v1.InterventionReason', '10': 'reason'},
    {'1': 'level', '3': 12, '4': 1, '5': 14, '6': '.agent.v1.InterventionLevel', '10': 'level'},
    {'1': 'on_reject', '3': 13, '4': 1, '5': 11, '6': '.agent.v1.CoolDownPolicy', '10': 'onReject'},
    {'1': 'content', '3': 14, '4': 1, '5': 11, '6': '.google.protobuf.Struct', '10': 'content'},
  ],
};

/// Descriptor for `InterventionRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List interventionRequestDescriptor = $convert.base64Decode(
    'ChNJbnRlcnZlbnRpb25SZXF1ZXN0Eg4KAmlkGAEgASgJUgJpZBIdCgpkZWR1cGVfa2V5GAIgAS'
    'gJUglkZWR1cGVLZXkSFAoFdG9waWMYAyABKAlSBXRvcGljEiIKDWNyZWF0ZWRfYXRfbXMYBCAB'
    'KANSC2NyZWF0ZWRBdE1zEiIKDWV4cGlyZXNfYXRfbXMYBSABKANSC2V4cGlyZXNBdE1zEiUKDm'
    'lzX3JldHJhY3RhYmxlGAYgASgIUg1pc1JldHJhY3RhYmxlEiMKDXN1cGVyc2VkZXNfaWQYByAB'
    'KAlSDHN1cGVyc2VkZXNJZBIlCg5zY2hlbWFfdmVyc2lvbhgIIAEoCVINc2NoZW1hVmVyc2lvbh'
    'IlCg5wb2xpY3lfdmVyc2lvbhgJIAEoCVINcG9saWN5VmVyc2lvbhIjCg1tb2RlbF92ZXJzaW9u'
    'GAogASgJUgxtb2RlbFZlcnNpb24SNAoGcmVhc29uGAsgASgLMhwuYWdlbnQudjEuSW50ZXJ2ZW'
    '50aW9uUmVhc29uUgZyZWFzb24SMQoFbGV2ZWwYDCABKA4yGy5hZ2VudC52MS5JbnRlcnZlbnRp'
    'b25MZXZlbFIFbGV2ZWwSNQoJb25fcmVqZWN0GA0gASgLMhguYWdlbnQudjEuQ29vbERvd25Qb2'
    'xpY3lSCG9uUmVqZWN0EjEKB2NvbnRlbnQYDiABKAsyFy5nb29nbGUucHJvdG9idWYuU3RydWN0'
    'Ugdjb250ZW50');

@$core.Deprecated('Use interventionPayloadDescriptor instead')
const InterventionPayload$json = {
  '1': 'InterventionPayload',
  '2': [
    {'1': 'request', '3': 1, '4': 1, '5': 11, '6': '.agent.v1.InterventionRequest', '10': 'request'},
  ],
};

/// Descriptor for `InterventionPayload`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List interventionPayloadDescriptor = $convert.base64Decode(
    'ChNJbnRlcnZlbnRpb25QYXlsb2FkEjcKB3JlcXVlc3QYASABKAsyHS5hZ2VudC52MS5JbnRlcn'
    'ZlbnRpb25SZXF1ZXN0UgdyZXF1ZXN0');

@$core.Deprecated('Use agentStatusDescriptor instead')
const AgentStatus$json = {
  '1': 'AgentStatus',
  '2': [
    {'1': 'state', '3': 1, '4': 1, '5': 14, '6': '.agent.v1.AgentStatus.State', '10': 'state'},
    {'1': 'details', '3': 2, '4': 1, '5': 9, '10': 'details'},
    {'1': 'current_agent_name', '3': 3, '4': 1, '5': 9, '10': 'currentAgentName'},
    {'1': 'active_agent', '3': 4, '4': 1, '5': 14, '6': '.agent.v1.AgentType', '10': 'activeAgent'},
  ],
  '4': [AgentStatus_State$json],
};

@$core.Deprecated('Use agentStatusDescriptor instead')
const AgentStatus_State$json = {
  '1': 'State',
  '2': [
    {'1': 'UNKNOWN', '2': 0},
    {'1': 'THINKING', '2': 1},
    {'1': 'SEARCHING', '2': 2},
    {'1': 'EXECUTING_TOOL', '2': 3},
    {'1': 'GENERATING', '2': 4},
  ],
};

/// Descriptor for `AgentStatus`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List agentStatusDescriptor = $convert.base64Decode(
    'CgtBZ2VudFN0YXR1cxIxCgVzdGF0ZRgBIAEoDjIbLmFnZW50LnYxLkFnZW50U3RhdHVzLlN0YX'
    'RlUgVzdGF0ZRIYCgdkZXRhaWxzGAIgASgJUgdkZXRhaWxzEiwKEmN1cnJlbnRfYWdlbnRfbmFt'
    'ZRgDIAEoCVIQY3VycmVudEFnZW50TmFtZRI2CgxhY3RpdmVfYWdlbnQYBCABKA4yEy5hZ2VudC'
    '52MS5BZ2VudFR5cGVSC2FjdGl2ZUFnZW50IlUKBVN0YXRlEgsKB1VOS05PV04QABIMCghUSElO'
    'S0lORxABEg0KCVNFQVJDSElORxACEhIKDkVYRUNVVElOR19UT09MEAMSDgoKR0VORVJBVElORx'
    'AE');

@$core.Deprecated('Use errorDescriptor instead')
const Error$json = {
  '1': 'Error',
  '2': [
    {'1': 'code', '3': 1, '4': 1, '5': 9, '10': 'code'},
    {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
    {'1': 'retryable', '3': 3, '4': 1, '5': 8, '10': 'retryable'},
    {'1': 'details', '3': 4, '4': 3, '5': 11, '6': '.agent.v1.Error.DetailsEntry', '10': 'details'},
  ],
  '3': [Error_DetailsEntry$json],
};

@$core.Deprecated('Use errorDescriptor instead')
const Error_DetailsEntry$json = {
  '1': 'DetailsEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `Error`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List errorDescriptor = $convert.base64Decode(
    'CgVFcnJvchISCgRjb2RlGAEgASgJUgRjb2RlEhgKB21lc3NhZ2UYAiABKAlSB21lc3NhZ2USHA'
    'oJcmV0cnlhYmxlGAMgASgIUglyZXRyeWFibGUSNgoHZGV0YWlscxgEIAMoCzIcLmFnZW50LnYx'
    'LkVycm9yLkRldGFpbHNFbnRyeVIHZGV0YWlscxo6CgxEZXRhaWxzRW50cnkSEAoDa2V5GAEgAS'
    'gJUgNrZXkSFAoFdmFsdWUYAiABKAlSBXZhbHVlOgI4AQ==');

@$core.Deprecated('Use usageDescriptor instead')
const Usage$json = {
  '1': 'Usage',
  '2': [
    {'1': 'prompt_tokens', '3': 1, '4': 1, '5': 5, '10': 'promptTokens'},
    {'1': 'completion_tokens', '3': 2, '4': 1, '5': 5, '10': 'completionTokens'},
    {'1': 'total_tokens', '3': 3, '4': 1, '5': 5, '10': 'totalTokens'},
    {'1': 'cost_micro_usd', '3': 4, '4': 1, '5': 3, '10': 'costMicroUsd'},
  ],
};

/// Descriptor for `Usage`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List usageDescriptor = $convert.base64Decode(
    'CgVVc2FnZRIjCg1wcm9tcHRfdG9rZW5zGAEgASgFUgxwcm9tcHRUb2tlbnMSKwoRY29tcGxldG'
    'lvbl90b2tlbnMYAiABKAVSEGNvbXBsZXRpb25Ub2tlbnMSIQoMdG90YWxfdG9rZW5zGAMgASgF'
    'Ugt0b3RhbFRva2VucxIkCg5jb3N0X21pY3JvX3VzZBgEIAEoA1IMY29zdE1pY3JvVXNk');

@$core.Deprecated('Use memoryQueryDescriptor instead')
const MemoryQuery$json = {
  '1': 'MemoryQuery',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'query_text', '3': 2, '4': 1, '5': 9, '10': 'queryText'},
    {'1': 'limit', '3': 3, '4': 1, '5': 5, '10': 'limit'},
    {'1': 'min_score', '3': 4, '4': 1, '5': 2, '10': 'minScore'},
    {'1': 'filter', '3': 5, '4': 1, '5': 11, '6': '.agent.v1.MemoryFilter', '10': 'filter'},
    {'1': 'hybrid_alpha', '3': 6, '4': 1, '5': 2, '10': 'hybridAlpha'},
  ],
};

/// Descriptor for `MemoryQuery`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List memoryQueryDescriptor = $convert.base64Decode(
    'CgtNZW1vcnlRdWVyeRIXCgd1c2VyX2lkGAEgASgJUgZ1c2VySWQSHQoKcXVlcnlfdGV4dBgCIA'
    'EoCVIJcXVlcnlUZXh0EhQKBWxpbWl0GAMgASgFUgVsaW1pdBIbCgltaW5fc2NvcmUYBCABKAJS'
    'CG1pblNjb3JlEi4KBmZpbHRlchgFIAEoCzIWLmFnZW50LnYxLk1lbW9yeUZpbHRlclIGZmlsdG'
    'VyEiEKDGh5YnJpZF9hbHBoYRgGIAEoAlILaHlicmlkQWxwaGE=');

@$core.Deprecated('Use memoryFilterDescriptor instead')
const MemoryFilter$json = {
  '1': 'MemoryFilter',
  '2': [
    {'1': 'tags', '3': 1, '4': 3, '5': 9, '10': 'tags'},
    {'1': 'start_time', '3': 2, '4': 1, '5': 11, '6': '.google.protobuf.Timestamp', '10': 'startTime'},
    {'1': 'end_time', '3': 3, '4': 1, '5': 11, '6': '.google.protobuf.Timestamp', '10': 'endTime'},
    {'1': 'source_types', '3': 4, '4': 3, '5': 9, '10': 'sourceTypes'},
  ],
};

/// Descriptor for `MemoryFilter`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List memoryFilterDescriptor = $convert.base64Decode(
    'CgxNZW1vcnlGaWx0ZXISEgoEdGFncxgBIAMoCVIEdGFncxI5CgpzdGFydF90aW1lGAIgASgLMh'
    'ouZ29vZ2xlLnByb3RvYnVmLlRpbWVzdGFtcFIJc3RhcnRUaW1lEjUKCGVuZF90aW1lGAMgASgL'
    'MhouZ29vZ2xlLnByb3RvYnVmLlRpbWVzdGFtcFIHZW5kVGltZRIhCgxzb3VyY2VfdHlwZXMYBC'
    'ADKAlSC3NvdXJjZVR5cGVz');

@$core.Deprecated('Use memoryResultDescriptor instead')
const MemoryResult$json = {
  '1': 'MemoryResult',
  '2': [
    {'1': 'items', '3': 1, '4': 3, '5': 11, '6': '.agent.v1.MemoryItem', '10': 'items'},
    {'1': 'total_found', '3': 2, '4': 1, '5': 5, '10': 'totalFound'},
  ],
};

/// Descriptor for `MemoryResult`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List memoryResultDescriptor = $convert.base64Decode(
    'CgxNZW1vcnlSZXN1bHQSKgoFaXRlbXMYASADKAsyFC5hZ2VudC52MS5NZW1vcnlJdGVtUgVpdG'
    'VtcxIfCgt0b3RhbF9mb3VuZBgCIAEoBVIKdG90YWxGb3VuZA==');

@$core.Deprecated('Use memoryItemDescriptor instead')
const MemoryItem$json = {
  '1': 'MemoryItem',
  '2': [
    {'1': 'id', '3': 1, '4': 1, '5': 9, '10': 'id'},
    {'1': 'content', '3': 2, '4': 1, '5': 9, '10': 'content'},
    {'1': 'score', '3': 3, '4': 1, '5': 2, '10': 'score'},
    {'1': 'created_at', '3': 4, '4': 1, '5': 11, '6': '.google.protobuf.Timestamp', '10': 'createdAt'},
    {'1': 'metadata', '3': 5, '4': 3, '5': 11, '6': '.agent.v1.MemoryItem.MetadataEntry', '10': 'metadata'},
  ],
  '3': [MemoryItem_MetadataEntry$json],
};

@$core.Deprecated('Use memoryItemDescriptor instead')
const MemoryItem_MetadataEntry$json = {
  '1': 'MetadataEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `MemoryItem`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List memoryItemDescriptor = $convert.base64Decode(
    'CgpNZW1vcnlJdGVtEg4KAmlkGAEgASgJUgJpZBIYCgdjb250ZW50GAIgASgJUgdjb250ZW50Eh'
    'QKBXNjb3JlGAMgASgCUgVzY29yZRI5CgpjcmVhdGVkX2F0GAQgASgLMhouZ29vZ2xlLnByb3Rv'
    'YnVmLlRpbWVzdGFtcFIJY3JlYXRlZEF0Ej4KCG1ldGFkYXRhGAUgAygLMiIuYWdlbnQudjEuTW'
    'Vtb3J5SXRlbS5NZXRhZGF0YUVudHJ5UghtZXRhZGF0YRo7Cg1NZXRhZGF0YUVudHJ5EhAKA2tl'
    'eRgBIAEoCVIDa2V5EhQKBXZhbHVlGAIgASgJUgV2YWx1ZToCOAE=');

const $core.Map<$core.String, $core.dynamic> AgentServiceBase$json = {
  '1': 'AgentService',
  '2': [
    {'1': 'StreamChat', '2': '.agent.v1.ChatRequest', '3': '.agent.v1.ChatResponse', '6': true},
    {'1': 'RetrieveMemory', '2': '.agent.v1.MemoryQuery', '3': '.agent.v1.MemoryResult'},
    {'1': 'GetUserProfile', '2': '.agent.v1.ProfileRequest', '3': '.agent.v1.UserProfile'},
    {'1': 'GetWeeklyReport', '2': '.agent.v1.WeeklyReportRequest', '3': '.agent.v1.WeeklyReport'},
  ],
};

@$core.Deprecated('Use agentServiceDescriptor instead')
const $core.Map<$core.String, $core.Map<$core.String, $core.dynamic>> AgentServiceBase$messageJson = {
  '.agent.v1.ChatRequest': ChatRequest$json,
  '.agent.v1.UserProfile': UserProfile$json,
  '.agent.v1.UserProfile.PreferencesEntry': UserProfile_PreferencesEntry$json,
  '.google.protobuf.Struct': $1.Struct$json,
  '.google.protobuf.Struct.FieldsEntry': $1.Struct_FieldsEntry$json,
  '.google.protobuf.Value': $1.Value$json,
  '.google.protobuf.ListValue': $1.ListValue$json,
  '.agent.v1.ChatMessage': ChatMessage$json,
  '.agent.v1.ChatMessage.MetadataEntry': ChatMessage_MetadataEntry$json,
  '.agent.v1.ToolResult': ToolResult$json,
  '.agent.v1.ChatConfig': ChatConfig$json,
  '.agent.v1.ChatResponse': ChatResponse$json,
  '.agent.v1.ToolCall': ToolCall$json,
  '.agent.v1.AgentStatus': AgentStatus$json,
  '.agent.v1.Error': Error$json,
  '.agent.v1.Error.DetailsEntry': Error_DetailsEntry$json,
  '.agent.v1.Usage': Usage$json,
  '.agent.v1.CitationBlock': CitationBlock$json,
  '.agent.v1.Citation': Citation$json,
  '.agent.v1.ToolResultPayload': ToolResultPayload$json,
  '.agent.v1.InterventionPayload': InterventionPayload$json,
  '.agent.v1.InterventionRequest': InterventionRequest$json,
  '.agent.v1.InterventionReason': InterventionReason$json,
  '.agent.v1.EvidenceRef': EvidenceRef$json,
  '.agent.v1.CoolDownPolicy': CoolDownPolicy$json,
  '.agent.v1.MemoryQuery': MemoryQuery$json,
  '.agent.v1.MemoryFilter': MemoryFilter$json,
  '.google.protobuf.Timestamp': $2.Timestamp$json,
  '.agent.v1.MemoryResult': MemoryResult$json,
  '.agent.v1.MemoryItem': MemoryItem$json,
  '.agent.v1.MemoryItem.MetadataEntry': MemoryItem_MetadataEntry$json,
  '.agent.v1.ProfileRequest': ProfileRequest$json,
  '.agent.v1.WeeklyReportRequest': WeeklyReportRequest$json,
  '.agent.v1.WeeklyReport': WeeklyReport$json,
};

/// Descriptor for `AgentService`. Decode as a `google.protobuf.ServiceDescriptorProto`.
final $typed_data.Uint8List agentServiceDescriptor = $convert.base64Decode(
    'CgxBZ2VudFNlcnZpY2USPQoKU3RyZWFtQ2hhdBIVLmFnZW50LnYxLkNoYXRSZXF1ZXN0GhYuYW'
    'dlbnQudjEuQ2hhdFJlc3BvbnNlMAESPwoOUmV0cmlldmVNZW1vcnkSFS5hZ2VudC52MS5NZW1v'
    'cnlRdWVyeRoWLmFnZW50LnYxLk1lbW9yeVJlc3VsdBJBCg5HZXRVc2VyUHJvZmlsZRIYLmFnZW'
    '50LnYxLlByb2ZpbGVSZXF1ZXN0GhUuYWdlbnQudjEuVXNlclByb2ZpbGUSSAoPR2V0V2Vla2x5'
    'UmVwb3J0Eh0uYWdlbnQudjEuV2Vla2x5UmVwb3J0UmVxdWVzdBoWLmFnZW50LnYxLldlZWtseV'
    'JlcG9ydA==');

