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

@$core.Deprecated('Use feedbackTypeDescriptor instead')
const FeedbackType$json = {
  '1': 'FeedbackType',
  '2': [
    {'1': 'FEEDBACK_TYPE_UP', '2': 0},
    {'1': 'FEEDBACK_TYPE_DOWN', '2': 1},
  ],
};

/// Descriptor for `FeedbackType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List feedbackTypeDescriptor = $convert.base64Decode(
    'CgxGZWVkYmFja1R5cGUSFAoQRkVFREJBQ0tfVFlQRV9VUBAAEhYKEkZFRURCQUNLX1RZUEVfRE'
    '9XThAB');

@$core.Deprecated('Use feedbackReasonDescriptor instead')
const FeedbackReason$json = {
  '1': 'FeedbackReason',
  '2': [
    {'1': 'FEEDBACK_REASON_UNSPECIFIED', '2': 0},
    {'1': 'FEEDBACK_REASON_INACCURATE', '2': 1},
    {'1': 'FEEDBACK_REASON_INCOMPLETE', '2': 2},
    {'1': 'FEEDBACK_REASON_VERBOSE', '2': 3},
    {'1': 'FEEDBACK_REASON_FORMATTING', '2': 4},
    {'1': 'FEEDBACK_REASON_MISALIGNED', '2': 5},
    {'1': 'FEEDBACK_REASON_TOO_HARD', '2': 6},
    {'1': 'FEEDBACK_REASON_TOO_SIMPLE', '2': 7},
  ],
};

/// Descriptor for `FeedbackReason`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List feedbackReasonDescriptor = $convert.base64Decode(
    'Cg5GZWVkYmFja1JlYXNvbhIfChtGRUVEQkFDS19SRUFTT05fVU5TUEVDSUZJRUQQABIeChpGRU'
    'VEQkFDS19SRUFTT05fSU5BQ0NVUkFURRABEh4KGkZFRURCQUNLX1JFQVNPTl9JTkNPTVBMRVRF'
    'EAISGwoXRkVFREJBQ0tfUkVBU09OX1ZFUkJPU0UQAxIeChpGRUVEQkFDS19SRUFTT05fRk9STU'
    'FUVElORxAEEh4KGkZFRURCQUNLX1JFQVNPTl9NSVNBTElHTkVEEAUSHAoYRkVFREJBQ0tfUkVB'
    'U09OX1RPT19IQVJEEAYSHgoaRkVFREJBQ0tfUkVBU09OX1RPT19TSU1QTEUQBw==');

@$core.Deprecated('Use planReviewDecisionDescriptor instead')
const PlanReviewDecision$json = {
  '1': 'PlanReviewDecision',
  '2': [
    {'1': 'PLAN_REVIEW_DECISION_UNSPECIFIED', '2': 0},
    {'1': 'APPROVE', '2': 1},
    {'1': 'REJECT', '2': 2},
    {'1': 'MODIFY', '2': 3},
    {'1': 'ACKNOWLEDGE', '2': 4},
  ],
};

/// Descriptor for `PlanReviewDecision`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List planReviewDecisionDescriptor = $convert.base64Decode(
    'ChJQbGFuUmV2aWV3RGVjaXNpb24SJAogUExBTl9SRVZJRVdfREVDSVNJT05fVU5TUEVDSUZJRU'
    'QQABILCgdBUFBST1ZFEAESCgoGUkVKRUNUEAISCgoGTU9ESUZZEAMSDwoLQUNLTk9XTEVER0UQ'
    'BA==');

@$core.Deprecated('Use contentReviewFeedbackTypeDescriptor instead')
const ContentReviewFeedbackType$json = {
  '1': 'ContentReviewFeedbackType',
  '2': [
    {'1': 'SATISFIED', '2': 0},
    {'1': 'UNSATISFIED', '2': 1},
    {'1': 'MODIFIED', '2': 2},
    {'1': 'REPORTED_ERROR', '2': 3},
    {'1': 'SKIPPED', '2': 4},
  ],
};

/// Descriptor for `ContentReviewFeedbackType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List contentReviewFeedbackTypeDescriptor = $convert.base64Decode(
    'ChlDb250ZW50UmV2aWV3RmVlZGJhY2tUeXBlEg0KCVNBVElTRklFRBAAEg8KC1VOU0FUSVNGSU'
    'VEEAESDAoITU9ESUZJRUQQAhISCg5SRVBPUlRFRF9FUlJPUhADEgsKB1NLSVBQRUQQBA==');

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
    {'1': 'chat_mode', '3': 13, '4': 1, '5': 9, '10': 'chatMode'},
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
    'N0aXZlVG9vbHMSGwoJY2hhdF9tb2RlGA0gASgJUghjaGF0TW9kZUIHCgVpbnB1dA==');

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
    {'1': 'trace_id', '3': 15, '4': 1, '5': 9, '10': 'traceId'},
    {'1': 'workflow_id', '3': 16, '4': 1, '5': 9, '10': 'workflowId'},
    {'1': 'prompt_version', '3': 17, '4': 1, '5': 9, '10': 'promptVersion'},
    {'1': 'metadata', '3': 18, '4': 3, '5': 11, '6': '.agent.v1.ChatResponse.MetadataEntry', '10': 'metadata'},
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
  '3': [ChatResponse_MetadataEntry$json],
  '8': [
    {'1': 'content'},
  ],
};

@$core.Deprecated('Use chatResponseDescriptor instead')
const ChatResponse_MetadataEntry$json = {
  '1': 'MetadataEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `ChatResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List chatResponseDescriptor = $convert.base64Decode(
    'CgxDaGF0UmVzcG9uc2USHwoLcmVzcG9uc2VfaWQYASABKAlSCnJlc3BvbnNlSWQSHQoKY3JlYX'
    'RlZF9hdBgCIAEoA1IJY3JlYXRlZEF0Eh0KCnJlcXVlc3RfaWQYCiABKAlSCXJlcXVlc3RJZBIZ'
    'Cgh0cmFjZV9pZBgPIAEoCVIHdHJhY2VJZBIfCgt3b3JrZmxvd19pZBgQIAEoCVIKd29ya2Zsb3'
    'dJZBIlCg5wcm9tcHRfdmVyc2lvbhgRIAEoCVINcHJvbXB0VmVyc2lvbhJACghtZXRhZGF0YRgS'
    'IAMoCzIkLmFnZW50LnYxLkNoYXRSZXNwb25zZS5NZXRhZGF0YUVudHJ5UghtZXRhZGF0YRIWCg'
    'VkZWx0YRgDIAEoCUgAUgVkZWx0YRIxCgl0b29sX2NhbGwYBCABKAsyEi5hZ2VudC52MS5Ub29s'
    'Q2FsbEgAUgh0b29sQ2FsbBI8Cg1zdGF0dXNfdXBkYXRlGAUgASgLMhUuYWdlbnQudjEuQWdlbn'
    'RTdGF0dXNIAFIMc3RhdHVzVXBkYXRlEh0KCWZ1bGxfdGV4dBgGIAEoCUgAUghmdWxsVGV4dBIn'
    'CgVlcnJvchgHIAEoCzIPLmFnZW50LnYxLkVycm9ySABSBWVycm9yEicKBXVzYWdlGAggASgLMg'
    '8uYWdlbnQudjEuVXNhZ2VIAFIFdXNhZ2USNwoJY2l0YXRpb25zGAsgASgLMhcuYWdlbnQudjEu'
    'Q2l0YXRpb25CbG9ja0gAUgljaXRhdGlvbnMSPgoLdG9vbF9yZXN1bHQYDCABKAsyGy5hZ2VudC'
    '52MS5Ub29sUmVzdWx0UGF5bG9hZEgAUgp0b29sUmVzdWx0EkMKDGludGVydmVudGlvbhgOIAEo'
    'CzIdLmFnZW50LnYxLkludGVydmVudGlvblBheWxvYWRIAFIMaW50ZXJ2ZW50aW9uEjsKDWZpbm'
    'lzaF9yZWFzb24YCSABKA4yFi5hZ2VudC52MS5GaW5pc2hSZWFzb25SDGZpbmlzaFJlYXNvbhIc'
    'Cgl0aW1lc3RhbXAYDSABKANSCXRpbWVzdGFtcBo7Cg1NZXRhZGF0YUVudHJ5EhAKA2tleRgBIA'
    'EoCVIDa2V5EhQKBXZhbHVlGAIgASgJUgV2YWx1ZToCOAFCCQoHY29udGVudA==');

@$core.Deprecated('Use responseFeedbackRequestDescriptor instead')
const ResponseFeedbackRequest$json = {
  '1': 'ResponseFeedbackRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'response_id', '3': 2, '4': 1, '5': 9, '10': 'responseId'},
    {'1': 'trace_id', '3': 3, '4': 1, '5': 9, '10': 'traceId'},
    {'1': 'feedback_type', '3': 4, '4': 1, '5': 14, '6': '.agent.v1.FeedbackType', '10': 'feedbackType'},
    {'1': 'reasons', '3': 5, '4': 3, '5': 14, '6': '.agent.v1.FeedbackReason', '10': 'reasons'},
    {'1': 'free_text', '3': 6, '4': 1, '5': 9, '10': 'freeText'},
    {'1': 'workflow_id', '3': 7, '4': 1, '5': 9, '10': 'workflowId'},
    {'1': 'prompt_version', '3': 8, '4': 1, '5': 9, '10': 'promptVersion'},
    {'1': 'meta', '3': 9, '4': 3, '5': 11, '6': '.agent.v1.ResponseFeedbackRequest.MetaEntry', '10': 'meta'},
  ],
  '3': [ResponseFeedbackRequest_MetaEntry$json],
};

@$core.Deprecated('Use responseFeedbackRequestDescriptor instead')
const ResponseFeedbackRequest_MetaEntry$json = {
  '1': 'MetaEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `ResponseFeedbackRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List responseFeedbackRequestDescriptor = $convert.base64Decode(
    'ChdSZXNwb25zZUZlZWRiYWNrUmVxdWVzdBIXCgd1c2VyX2lkGAEgASgJUgZ1c2VySWQSHwoLcm'
    'VzcG9uc2VfaWQYAiABKAlSCnJlc3BvbnNlSWQSGQoIdHJhY2VfaWQYAyABKAlSB3RyYWNlSWQS'
    'OwoNZmVlZGJhY2tfdHlwZRgEIAEoDjIWLmFnZW50LnYxLkZlZWRiYWNrVHlwZVIMZmVlZGJhY2'
    'tUeXBlEjIKB3JlYXNvbnMYBSADKA4yGC5hZ2VudC52MS5GZWVkYmFja1JlYXNvblIHcmVhc29u'
    'cxIbCglmcmVlX3RleHQYBiABKAlSCGZyZWVUZXh0Eh8KC3dvcmtmbG93X2lkGAcgASgJUgp3b3'
    'JrZmxvd0lkEiUKDnByb21wdF92ZXJzaW9uGAggASgJUg1wcm9tcHRWZXJzaW9uEj8KBG1ldGEY'
    'CSADKAsyKy5hZ2VudC52MS5SZXNwb25zZUZlZWRiYWNrUmVxdWVzdC5NZXRhRW50cnlSBG1ldG'
    'EaNwoJTWV0YUVudHJ5EhAKA2tleRgBIAEoCVIDa2V5EhQKBXZhbHVlGAIgASgJUgV2YWx1ZToC'
    'OAE=');

@$core.Deprecated('Use responseFeedbackResponseDescriptor instead')
const ResponseFeedbackResponse$json = {
  '1': 'ResponseFeedbackResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
    {'1': 'response_id', '3': 3, '4': 1, '5': 9, '10': 'responseId'},
  ],
};

/// Descriptor for `ResponseFeedbackResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List responseFeedbackResponseDescriptor = $convert.base64Decode(
    'ChhSZXNwb25zZUZlZWRiYWNrUmVzcG9uc2USGAoHc3VjY2VzcxgBIAEoCFIHc3VjY2VzcxIYCg'
    'dtZXNzYWdlGAIgASgJUgdtZXNzYWdlEh8KC3Jlc3BvbnNlX2lkGAMgASgJUgpyZXNwb25zZUlk');

@$core.Deprecated('Use planReviewRequestDescriptor instead')
const PlanReviewRequest$json = {
  '1': 'PlanReviewRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'plan_id', '3': 2, '4': 1, '5': 9, '10': 'planId'},
    {'1': 'review_id', '3': 3, '4': 1, '5': 9, '10': 'reviewId'},
    {'1': 'decision', '3': 4, '4': 1, '5': 14, '6': '.agent.v1.PlanReviewDecision', '10': 'decision'},
    {'1': 'user_comment', '3': 5, '4': 1, '5': 9, '10': 'userComment'},
    {'1': 'trace_id', '3': 6, '4': 1, '5': 9, '10': 'traceId'},
    {'1': 'workflow_id', '3': 7, '4': 1, '5': 9, '10': 'workflowId'},
    {'1': 'prompt_version', '3': 8, '4': 1, '5': 9, '10': 'promptVersion'},
    {'1': 'meta', '3': 9, '4': 3, '5': 11, '6': '.agent.v1.PlanReviewRequest.MetaEntry', '10': 'meta'},
  ],
  '3': [PlanReviewRequest_MetaEntry$json],
};

@$core.Deprecated('Use planReviewRequestDescriptor instead')
const PlanReviewRequest_MetaEntry$json = {
  '1': 'MetaEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `PlanReviewRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List planReviewRequestDescriptor = $convert.base64Decode(
    'ChFQbGFuUmV2aWV3UmVxdWVzdBIXCgd1c2VyX2lkGAEgASgJUgZ1c2VySWQSFwoHcGxhbl9pZB'
    'gCIAEoCVIGcGxhbklkEhsKCXJldmlld19pZBgDIAEoCVIIcmV2aWV3SWQSOAoIZGVjaXNpb24Y'
    'BCABKA4yHC5hZ2VudC52MS5QbGFuUmV2aWV3RGVjaXNpb25SCGRlY2lzaW9uEiEKDHVzZXJfY2'
    '9tbWVudBgFIAEoCVILdXNlckNvbW1lbnQSGQoIdHJhY2VfaWQYBiABKAlSB3RyYWNlSWQSHwoL'
    'd29ya2Zsb3dfaWQYByABKAlSCndvcmtmbG93SWQSJQoOcHJvbXB0X3ZlcnNpb24YCCABKAlSDX'
    'Byb21wdFZlcnNpb24SOQoEbWV0YRgJIAMoCzIlLmFnZW50LnYxLlBsYW5SZXZpZXdSZXF1ZXN0'
    'Lk1ldGFFbnRyeVIEbWV0YRo3CglNZXRhRW50cnkSEAoDa2V5GAEgASgJUgNrZXkSFAoFdmFsdW'
    'UYAiABKAlSBXZhbHVlOgI4AQ==');

@$core.Deprecated('Use planReviewResponseDescriptor instead')
const PlanReviewResponse$json = {
  '1': 'PlanReviewResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
    {'1': 'review_id', '3': 3, '4': 1, '5': 9, '10': 'reviewId'},
    {'1': 'updated_plan_id', '3': 4, '4': 1, '5': 9, '10': 'updatedPlanId'},
  ],
};

/// Descriptor for `PlanReviewResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List planReviewResponseDescriptor = $convert.base64Decode(
    'ChJQbGFuUmV2aWV3UmVzcG9uc2USGAoHc3VjY2VzcxgBIAEoCFIHc3VjY2VzcxIYCgdtZXNzYW'
    'dlGAIgASgJUgdtZXNzYWdlEhsKCXJldmlld19pZBgDIAEoCVIIcmV2aWV3SWQSJgoPdXBkYXRl'
    'ZF9wbGFuX2lkGAQgASgJUg11cGRhdGVkUGxhbklk');

@$core.Deprecated('Use contentReviewFeedbackRequestDescriptor instead')
const ContentReviewFeedbackRequest$json = {
  '1': 'ContentReviewFeedbackRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'review_id', '3': 2, '4': 1, '5': 9, '10': 'reviewId'},
    {'1': 'response_id', '3': 3, '4': 1, '5': 9, '10': 'responseId'},
    {'1': 'feedback_type', '3': 4, '4': 1, '5': 14, '6': '.agent.v1.ContentReviewFeedbackType', '10': 'feedbackType'},
    {'1': 'rating', '3': 5, '4': 1, '5': 5, '10': 'rating'},
    {'1': 'comment', '3': 6, '4': 1, '5': 9, '10': 'comment'},
    {'1': 'issues_reported', '3': 7, '4': 3, '5': 9, '10': 'issuesReported'},
    {'1': 'session_id', '3': 8, '4': 1, '5': 9, '10': 'sessionId'},
    {'1': 'meta', '3': 9, '4': 3, '5': 11, '6': '.agent.v1.ContentReviewFeedbackRequest.MetaEntry', '10': 'meta'},
  ],
  '3': [ContentReviewFeedbackRequest_MetaEntry$json],
};

@$core.Deprecated('Use contentReviewFeedbackRequestDescriptor instead')
const ContentReviewFeedbackRequest_MetaEntry$json = {
  '1': 'MetaEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `ContentReviewFeedbackRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List contentReviewFeedbackRequestDescriptor = $convert.base64Decode(
    'ChxDb250ZW50UmV2aWV3RmVlZGJhY2tSZXF1ZXN0EhcKB3VzZXJfaWQYASABKAlSBnVzZXJJZB'
    'IbCglyZXZpZXdfaWQYAiABKAlSCHJldmlld0lkEh8KC3Jlc3BvbnNlX2lkGAMgASgJUgpyZXNw'
    'b25zZUlkEkgKDWZlZWRiYWNrX3R5cGUYBCABKA4yIy5hZ2VudC52MS5Db250ZW50UmV2aWV3Rm'
    'VlZGJhY2tUeXBlUgxmZWVkYmFja1R5cGUSFgoGcmF0aW5nGAUgASgFUgZyYXRpbmcSGAoHY29t'
    'bWVudBgGIAEoCVIHY29tbWVudBInCg9pc3N1ZXNfcmVwb3J0ZWQYByADKAlSDmlzc3Vlc1JlcG'
    '9ydGVkEh0KCnNlc3Npb25faWQYCCABKAlSCXNlc3Npb25JZBJECgRtZXRhGAkgAygLMjAuYWdl'
    'bnQudjEuQ29udGVudFJldmlld0ZlZWRiYWNrUmVxdWVzdC5NZXRhRW50cnlSBG1ldGEaNwoJTW'
    'V0YUVudHJ5EhAKA2tleRgBIAEoCVIDa2V5EhQKBXZhbHVlGAIgASgJUgV2YWx1ZToCOAE=');

@$core.Deprecated('Use contentReviewFeedbackResponseDescriptor instead')
const ContentReviewFeedbackResponse$json = {
  '1': 'ContentReviewFeedbackResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
    {'1': 'feedback_id', '3': 3, '4': 1, '5': 9, '10': 'feedbackId'},
  ],
};

/// Descriptor for `ContentReviewFeedbackResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List contentReviewFeedbackResponseDescriptor = $convert.base64Decode(
    'Ch1Db250ZW50UmV2aWV3RmVlZGJhY2tSZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZX'
    'NzEhgKB21lc3NhZ2UYAiABKAlSB21lc3NhZ2USHwoLZmVlZGJhY2tfaWQYAyABKAlSCmZlZWRi'
    'YWNrSWQ=');

@$core.Deprecated('Use reviewOverrideRequestDescriptor instead')
const ReviewOverrideRequest$json = {
  '1': 'ReviewOverrideRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'review_id', '3': 2, '4': 1, '5': 9, '10': 'reviewId'},
    {'1': 'original_decision', '3': 3, '4': 1, '5': 9, '10': 'originalDecision'},
    {'1': 'new_decision', '3': 4, '4': 1, '5': 9, '10': 'newDecision'},
    {'1': 'reason', '3': 5, '4': 1, '5': 9, '10': 'reason'},
    {'1': 'session_id', '3': 6, '4': 1, '5': 9, '10': 'sessionId'},
    {'1': 'meta', '3': 7, '4': 3, '5': 11, '6': '.agent.v1.ReviewOverrideRequest.MetaEntry', '10': 'meta'},
  ],
  '3': [ReviewOverrideRequest_MetaEntry$json],
};

@$core.Deprecated('Use reviewOverrideRequestDescriptor instead')
const ReviewOverrideRequest_MetaEntry$json = {
  '1': 'MetaEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `ReviewOverrideRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List reviewOverrideRequestDescriptor = $convert.base64Decode(
    'ChVSZXZpZXdPdmVycmlkZVJlcXVlc3QSFwoHdXNlcl9pZBgBIAEoCVIGdXNlcklkEhsKCXJldm'
    'lld19pZBgCIAEoCVIIcmV2aWV3SWQSKwoRb3JpZ2luYWxfZGVjaXNpb24YAyABKAlSEG9yaWdp'
    'bmFsRGVjaXNpb24SIQoMbmV3X2RlY2lzaW9uGAQgASgJUgtuZXdEZWNpc2lvbhIWCgZyZWFzb2'
    '4YBSABKAlSBnJlYXNvbhIdCgpzZXNzaW9uX2lkGAYgASgJUglzZXNzaW9uSWQSPQoEbWV0YRgH'
    'IAMoCzIpLmFnZW50LnYxLlJldmlld092ZXJyaWRlUmVxdWVzdC5NZXRhRW50cnlSBG1ldGEaNw'
    'oJTWV0YUVudHJ5EhAKA2tleRgBIAEoCVIDa2V5EhQKBXZhbHVlGAIgASgJUgV2YWx1ZToCOAE=');

@$core.Deprecated('Use reviewOverrideResponseDescriptor instead')
const ReviewOverrideResponse$json = {
  '1': 'ReviewOverrideResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
    {'1': 'override_id', '3': 3, '4': 1, '5': 9, '10': 'overrideId'},
  ],
};

/// Descriptor for `ReviewOverrideResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List reviewOverrideResponseDescriptor = $convert.base64Decode(
    'ChZSZXZpZXdPdmVycmlkZVJlc3BvbnNlEhgKB3N1Y2Nlc3MYASABKAhSB3N1Y2Nlc3MSGAoHbW'
    'Vzc2FnZRgCIAEoCVIHbWVzc2FnZRIfCgtvdmVycmlkZV9pZBgDIAEoCVIKb3ZlcnJpZGVJZA==');

@$core.Deprecated('Use reviewAppealRequestDescriptor instead')
const ReviewAppealRequest$json = {
  '1': 'ReviewAppealRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'review_id', '3': 2, '4': 1, '5': 9, '10': 'reviewId'},
    {'1': 'appeal_reason', '3': 3, '4': 1, '5': 9, '10': 'appealReason'},
    {'1': 'issues_with_review', '3': 4, '4': 3, '5': 9, '10': 'issuesWithReview'},
    {'1': 'session_id', '3': 5, '4': 1, '5': 9, '10': 'sessionId'},
    {'1': 'meta', '3': 6, '4': 3, '5': 11, '6': '.agent.v1.ReviewAppealRequest.MetaEntry', '10': 'meta'},
  ],
  '3': [ReviewAppealRequest_MetaEntry$json],
};

@$core.Deprecated('Use reviewAppealRequestDescriptor instead')
const ReviewAppealRequest_MetaEntry$json = {
  '1': 'MetaEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `ReviewAppealRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List reviewAppealRequestDescriptor = $convert.base64Decode(
    'ChNSZXZpZXdBcHBlYWxSZXF1ZXN0EhcKB3VzZXJfaWQYASABKAlSBnVzZXJJZBIbCglyZXZpZX'
    'dfaWQYAiABKAlSCHJldmlld0lkEiMKDWFwcGVhbF9yZWFzb24YAyABKAlSDGFwcGVhbFJlYXNv'
    'bhIsChJpc3N1ZXNfd2l0aF9yZXZpZXcYBCADKAlSEGlzc3Vlc1dpdGhSZXZpZXcSHQoKc2Vzc2'
    'lvbl9pZBgFIAEoCVIJc2Vzc2lvbklkEjsKBG1ldGEYBiADKAsyJy5hZ2VudC52MS5SZXZpZXdB'
    'cHBlYWxSZXF1ZXN0Lk1ldGFFbnRyeVIEbWV0YRo3CglNZXRhRW50cnkSEAoDa2V5GAEgASgJUg'
    'NrZXkSFAoFdmFsdWUYAiABKAlSBXZhbHVlOgI4AQ==');

@$core.Deprecated('Use reviewAppealResponseDescriptor instead')
const ReviewAppealResponse$json = {
  '1': 'ReviewAppealResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'appeal_id', '3': 2, '4': 1, '5': 9, '10': 'appealId'},
    {'1': 'status', '3': 3, '4': 1, '5': 9, '10': 'status'},
    {'1': 'message', '3': 4, '4': 1, '5': 9, '10': 'message'},
  ],
};

/// Descriptor for `ReviewAppealResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List reviewAppealResponseDescriptor = $convert.base64Decode(
    'ChRSZXZpZXdBcHBlYWxSZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZXNzEhsKCWFwcG'
    'VhbF9pZBgCIAEoCVIIYXBwZWFsSWQSFgoGc3RhdHVzGAMgASgJUgZzdGF0dXMSGAoHbWVzc2Fn'
    'ZRgEIAEoCVIHbWVzc2FnZQ==');

@$core.Deprecated('Use appealStatusRequestDescriptor instead')
const AppealStatusRequest$json = {
  '1': 'AppealStatusRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'appeal_id', '3': 2, '4': 1, '5': 9, '10': 'appealId'},
  ],
};

/// Descriptor for `AppealStatusRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List appealStatusRequestDescriptor = $convert.base64Decode(
    'ChNBcHBlYWxTdGF0dXNSZXF1ZXN0EhcKB3VzZXJfaWQYASABKAlSBnVzZXJJZBIbCglhcHBlYW'
    'xfaWQYAiABKAlSCGFwcGVhbElk');

@$core.Deprecated('Use appealStatusResponseDescriptor instead')
const AppealStatusResponse$json = {
  '1': 'AppealStatusResponse',
  '2': [
    {'1': 'appeal_id', '3': 1, '4': 1, '5': 9, '10': 'appealId'},
    {'1': 'review_id', '3': 2, '4': 1, '5': 9, '10': 'reviewId'},
    {'1': 'status', '3': 3, '4': 1, '5': 9, '10': 'status'},
    {'1': 'submitted_at', '3': 4, '4': 1, '5': 9, '10': 'submittedAt'},
    {'1': 'appeal_reason', '3': 5, '4': 1, '5': 9, '10': 'appealReason'},
    {'1': 'resolution', '3': 6, '4': 1, '5': 9, '10': 'resolution'},
    {'1': 'resolved_by', '3': 7, '4': 1, '5': 9, '10': 'resolvedBy'},
    {'1': 'resolved_at', '3': 8, '4': 1, '5': 9, '10': 'resolvedAt'},
    {'1': 'secondary_decision', '3': 9, '4': 1, '5': 9, '10': 'secondaryDecision'},
    {'1': 'secondary_score', '3': 10, '4': 1, '5': 1, '10': 'secondaryScore'},
  ],
};

/// Descriptor for `AppealStatusResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List appealStatusResponseDescriptor = $convert.base64Decode(
    'ChRBcHBlYWxTdGF0dXNSZXNwb25zZRIbCglhcHBlYWxfaWQYASABKAlSCGFwcGVhbElkEhsKCX'
    'Jldmlld19pZBgCIAEoCVIIcmV2aWV3SWQSFgoGc3RhdHVzGAMgASgJUgZzdGF0dXMSIQoMc3Vi'
    'bWl0dGVkX2F0GAQgASgJUgtzdWJtaXR0ZWRBdBIjCg1hcHBlYWxfcmVhc29uGAUgASgJUgxhcH'
    'BlYWxSZWFzb24SHgoKcmVzb2x1dGlvbhgGIAEoCVIKcmVzb2x1dGlvbhIfCgtyZXNvbHZlZF9i'
    'eRgHIAEoCVIKcmVzb2x2ZWRCeRIfCgtyZXNvbHZlZF9hdBgIIAEoCVIKcmVzb2x2ZWRBdBItCh'
    'JzZWNvbmRhcnlfZGVjaXNpb24YCSABKAlSEXNlY29uZGFyeURlY2lzaW9uEicKD3NlY29uZGFy'
    'eV9zY29yZRgKIAEoAVIOc2Vjb25kYXJ5U2NvcmU=');

@$core.Deprecated('Use reviewFeedbackRequestDescriptor instead')
const ReviewFeedbackRequest$json = {
  '1': 'ReviewFeedbackRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'review_id', '3': 2, '4': 1, '5': 9, '10': 'reviewId'},
    {'1': 'feedback_type', '3': 3, '4': 1, '5': 9, '10': 'feedbackType'},
    {'1': 'rating', '3': 4, '4': 1, '5': 5, '10': 'rating'},
    {'1': 'was_helpful', '3': 5, '4': 1, '5': 8, '10': 'wasHelpful'},
    {'1': 'was_accurate', '3': 6, '4': 1, '5': 8, '10': 'wasAccurate'},
    {'1': 'inaccurate_points', '3': 7, '4': 3, '5': 9, '10': 'inaccuratePoints'},
    {'1': 'specificity_level', '3': 8, '4': 1, '5': 9, '10': 'specificityLevel'},
    {'1': 'comments', '3': 9, '4': 1, '5': 9, '10': 'comments'},
    {'1': 'tags', '3': 10, '4': 3, '5': 9, '10': 'tags'},
  ],
};

/// Descriptor for `ReviewFeedbackRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List reviewFeedbackRequestDescriptor = $convert.base64Decode(
    'ChVSZXZpZXdGZWVkYmFja1JlcXVlc3QSFwoHdXNlcl9pZBgBIAEoCVIGdXNlcklkEhsKCXJldm'
    'lld19pZBgCIAEoCVIIcmV2aWV3SWQSIwoNZmVlZGJhY2tfdHlwZRgDIAEoCVIMZmVlZGJhY2tU'
    'eXBlEhYKBnJhdGluZxgEIAEoBVIGcmF0aW5nEh8KC3dhc19oZWxwZnVsGAUgASgIUgp3YXNIZW'
    'xwZnVsEiEKDHdhc19hY2N1cmF0ZRgGIAEoCFILd2FzQWNjdXJhdGUSKwoRaW5hY2N1cmF0ZV9w'
    'b2ludHMYByADKAlSEGluYWNjdXJhdGVQb2ludHMSKwoRc3BlY2lmaWNpdHlfbGV2ZWwYCCABKA'
    'lSEHNwZWNpZmljaXR5TGV2ZWwSGgoIY29tbWVudHMYCSABKAlSCGNvbW1lbnRzEhIKBHRhZ3MY'
    'CiADKAlSBHRhZ3M=');

@$core.Deprecated('Use reviewFeedbackResponseDescriptor instead')
const ReviewFeedbackResponse$json = {
  '1': 'ReviewFeedbackResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'feedback_id', '3': 2, '4': 1, '5': 9, '10': 'feedbackId'},
    {'1': 'message', '3': 3, '4': 1, '5': 9, '10': 'message'},
  ],
};

/// Descriptor for `ReviewFeedbackResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List reviewFeedbackResponseDescriptor = $convert.base64Decode(
    'ChZSZXZpZXdGZWVkYmFja1Jlc3BvbnNlEhgKB3N1Y2Nlc3MYASABKAhSB3N1Y2Nlc3MSHwoLZm'
    'VlZGJhY2tfaWQYAiABKAlSCmZlZWRiYWNrSWQSGAoHbWVzc2FnZRgDIAEoCVIHbWVzc2FnZQ==');

@$core.Deprecated('Use regenerationRequestDescriptor instead')
const RegenerationRequest$json = {
  '1': 'RegenerationRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'original_content_id', '3': 2, '4': 1, '5': 9, '10': 'originalContentId'},
    {'1': 'review_id', '3': 3, '4': 1, '5': 9, '10': 'reviewId'},
    {'1': 'regeneration_type', '3': 4, '4': 1, '5': 9, '10': 'regenerationType'},
    {'1': 'improvement_hints', '3': 5, '4': 3, '5': 9, '10': 'improvementHints'},
    {'1': 'focus_areas', '3': 6, '4': 3, '5': 9, '10': 'focusAreas'},
    {'1': 'custom_instructions', '3': 7, '4': 1, '5': 9, '10': 'customInstructions'},
  ],
};

/// Descriptor for `RegenerationRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List regenerationRequestDescriptor = $convert.base64Decode(
    'ChNSZWdlbmVyYXRpb25SZXF1ZXN0EhcKB3VzZXJfaWQYASABKAlSBnVzZXJJZBIuChNvcmlnaW'
    '5hbF9jb250ZW50X2lkGAIgASgJUhFvcmlnaW5hbENvbnRlbnRJZBIbCglyZXZpZXdfaWQYAyAB'
    'KAlSCHJldmlld0lkEisKEXJlZ2VuZXJhdGlvbl90eXBlGAQgASgJUhByZWdlbmVyYXRpb25UeX'
    'BlEisKEWltcHJvdmVtZW50X2hpbnRzGAUgAygJUhBpbXByb3ZlbWVudEhpbnRzEh8KC2ZvY3Vz'
    'X2FyZWFzGAYgAygJUgpmb2N1c0FyZWFzEi8KE2N1c3RvbV9pbnN0cnVjdGlvbnMYByABKAlSEm'
    'N1c3RvbUluc3RydWN0aW9ucw==');

@$core.Deprecated('Use regenerationResponseDescriptor instead')
const RegenerationResponse$json = {
  '1': 'RegenerationResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'request_id', '3': 2, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'new_content', '3': 3, '4': 1, '5': 9, '10': 'newContent'},
    {'1': 'new_content_id', '3': 4, '4': 1, '5': 9, '10': 'newContentId'},
    {'1': 'improvement_summary', '3': 5, '4': 1, '5': 9, '10': 'improvementSummary'},
    {'1': 'changes_made', '3': 6, '4': 3, '5': 9, '10': 'changesMade'},
    {'1': 'score_improvement', '3': 7, '4': 1, '5': 1, '10': 'scoreImprovement'},
    {'1': 'generation_time_ms', '3': 8, '4': 1, '5': 5, '10': 'generationTimeMs'},
  ],
};

/// Descriptor for `RegenerationResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List regenerationResponseDescriptor = $convert.base64Decode(
    'ChRSZWdlbmVyYXRpb25SZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZXNzEh0KCnJlcX'
    'Vlc3RfaWQYAiABKAlSCXJlcXVlc3RJZBIfCgtuZXdfY29udGVudBgDIAEoCVIKbmV3Q29udGVu'
    'dBIkCg5uZXdfY29udGVudF9pZBgEIAEoCVIMbmV3Q29udGVudElkEi8KE2ltcHJvdmVtZW50X3'
    'N1bW1hcnkYBSABKAlSEmltcHJvdmVtZW50U3VtbWFyeRIhCgxjaGFuZ2VzX21hZGUYBiADKAlS'
    'C2NoYW5nZXNNYWRlEisKEXNjb3JlX2ltcHJvdmVtZW50GAcgASgBUhBzY29yZUltcHJvdmVtZW'
    '50EiwKEmdlbmVyYXRpb25fdGltZV9tcxgIIAEoBVIQZ2VuZXJhdGlvblRpbWVNcw==');

@$core.Deprecated('Use feedbackStatisticsRequestDescriptor instead')
const FeedbackStatisticsRequest$json = {
  '1': 'FeedbackStatisticsRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'period_days', '3': 2, '4': 1, '5': 5, '10': 'periodDays'},
  ],
};

/// Descriptor for `FeedbackStatisticsRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List feedbackStatisticsRequestDescriptor = $convert.base64Decode(
    'ChlGZWVkYmFja1N0YXRpc3RpY3NSZXF1ZXN0EhcKB3VzZXJfaWQYASABKAlSBnVzZXJJZBIfCg'
    'twZXJpb2RfZGF5cxgCIAEoBVIKcGVyaW9kRGF5cw==');

@$core.Deprecated('Use feedbackStatisticsResponseDescriptor instead')
const FeedbackStatisticsResponse$json = {
  '1': 'FeedbackStatisticsResponse',
  '2': [
    {'1': 'total_feedbacks', '3': 1, '4': 1, '5': 5, '10': 'totalFeedbacks'},
    {'1': 'avg_rating', '3': 2, '4': 1, '5': 1, '10': 'avgRating'},
    {'1': 'helpful_rate', '3': 3, '4': 1, '5': 1, '10': 'helpfulRate'},
    {'1': 'accuracy_rate', '3': 4, '4': 1, '5': 1, '10': 'accuracyRate'},
    {'1': 'regeneration_requests', '3': 5, '4': 1, '5': 5, '10': 'regenerationRequests'},
    {'1': 'successful_regenerations', '3': 6, '4': 1, '5': 5, '10': 'successfulRegenerations'},
    {'1': 'period_days', '3': 7, '4': 1, '5': 5, '10': 'periodDays'},
  ],
};

/// Descriptor for `FeedbackStatisticsResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List feedbackStatisticsResponseDescriptor = $convert.base64Decode(
    'ChpGZWVkYmFja1N0YXRpc3RpY3NSZXNwb25zZRInCg90b3RhbF9mZWVkYmFja3MYASABKAVSDn'
    'RvdGFsRmVlZGJhY2tzEh0KCmF2Z19yYXRpbmcYAiABKAFSCWF2Z1JhdGluZxIhCgxoZWxwZnVs'
    'X3JhdGUYAyABKAFSC2hlbHBmdWxSYXRlEiMKDWFjY3VyYWN5X3JhdGUYBCABKAFSDGFjY3VyYW'
    'N5UmF0ZRIzChVyZWdlbmVyYXRpb25fcmVxdWVzdHMYBSABKAVSFHJlZ2VuZXJhdGlvblJlcXVl'
    'c3RzEjkKGHN1Y2Nlc3NmdWxfcmVnZW5lcmF0aW9ucxgGIAEoBVIXc3VjY2Vzc2Z1bFJlZ2VuZX'
    'JhdGlvbnMSHwoLcGVyaW9kX2RheXMYByABKAVSCnBlcmlvZERheXM=');

@$core.Deprecated('Use getArbitrationQueueRequestDescriptor instead')
const GetArbitrationQueueRequest$json = {
  '1': 'GetArbitrationQueueRequest',
  '2': [
    {'1': 'limit', '3': 1, '4': 1, '5': 5, '10': 'limit'},
    {'1': 'priority_filter', '3': 2, '4': 1, '5': 9, '10': 'priorityFilter'},
    {'1': 'status_filter', '3': 3, '4': 1, '5': 9, '10': 'statusFilter'},
  ],
};

/// Descriptor for `GetArbitrationQueueRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List getArbitrationQueueRequestDescriptor = $convert.base64Decode(
    'ChpHZXRBcmJpdHJhdGlvblF1ZXVlUmVxdWVzdBIUCgVsaW1pdBgBIAEoBVIFbGltaXQSJwoPcH'
    'Jpb3JpdHlfZmlsdGVyGAIgASgJUg5wcmlvcml0eUZpbHRlchIjCg1zdGF0dXNfZmlsdGVyGAMg'
    'ASgJUgxzdGF0dXNGaWx0ZXI=');

@$core.Deprecated('Use arbitrationCaseInfoDescriptor instead')
const ArbitrationCaseInfo$json = {
  '1': 'ArbitrationCaseInfo',
  '2': [
    {'1': 'case_id', '3': 1, '4': 1, '5': 9, '10': 'caseId'},
    {'1': 'appeal_id', '3': 2, '4': 1, '5': 9, '10': 'appealId'},
    {'1': 'review_id', '3': 3, '4': 1, '5': 9, '10': 'reviewId'},
    {'1': 'user_id', '3': 4, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'escalation_reason', '3': 5, '4': 1, '5': 9, '10': 'escalationReason'},
    {'1': 'priority', '3': 6, '4': 1, '5': 9, '10': 'priority'},
    {'1': 'created_at', '3': 7, '4': 1, '5': 9, '10': 'createdAt'},
    {'1': 'status', '3': 8, '4': 1, '5': 9, '10': 'status'},
    {'1': 'assigned_to', '3': 9, '4': 1, '5': 9, '10': 'assignedTo'},
    {'1': 'assigned_at', '3': 10, '4': 1, '5': 9, '10': 'assignedAt'},
    {'1': 'original_review_score', '3': 11, '4': 1, '5': 1, '10': 'originalReviewScore'},
    {'1': 'secondary_review_score', '3': 12, '4': 1, '5': 1, '10': 'secondaryReviewScore'},
    {'1': 'score_discrepancy', '3': 13, '4': 1, '5': 1, '10': 'scoreDiscrepancy'},
    {'1': 'resolution', '3': 14, '4': 1, '5': 9, '10': 'resolution'},
    {'1': 'final_decision', '3': 15, '4': 1, '5': 9, '10': 'finalDecision'},
    {'1': 'resolved_at', '3': 16, '4': 1, '5': 9, '10': 'resolvedAt'},
    {'1': 'resolved_by', '3': 17, '4': 1, '5': 9, '10': 'resolvedBy'},
    {'1': 'notes', '3': 18, '4': 3, '5': 9, '10': 'notes'},
  ],
};

/// Descriptor for `ArbitrationCaseInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List arbitrationCaseInfoDescriptor = $convert.base64Decode(
    'ChNBcmJpdHJhdGlvbkNhc2VJbmZvEhcKB2Nhc2VfaWQYASABKAlSBmNhc2VJZBIbCglhcHBlYW'
    'xfaWQYAiABKAlSCGFwcGVhbElkEhsKCXJldmlld19pZBgDIAEoCVIIcmV2aWV3SWQSFwoHdXNl'
    'cl9pZBgEIAEoCVIGdXNlcklkEisKEWVzY2FsYXRpb25fcmVhc29uGAUgASgJUhBlc2NhbGF0aW'
    '9uUmVhc29uEhoKCHByaW9yaXR5GAYgASgJUghwcmlvcml0eRIdCgpjcmVhdGVkX2F0GAcgASgJ'
    'UgljcmVhdGVkQXQSFgoGc3RhdHVzGAggASgJUgZzdGF0dXMSHwoLYXNzaWduZWRfdG8YCSABKA'
    'lSCmFzc2lnbmVkVG8SHwoLYXNzaWduZWRfYXQYCiABKAlSCmFzc2lnbmVkQXQSMgoVb3JpZ2lu'
    'YWxfcmV2aWV3X3Njb3JlGAsgASgBUhNvcmlnaW5hbFJldmlld1Njb3JlEjQKFnNlY29uZGFyeV'
    '9yZXZpZXdfc2NvcmUYDCABKAFSFHNlY29uZGFyeVJldmlld1Njb3JlEisKEXNjb3JlX2Rpc2Ny'
    'ZXBhbmN5GA0gASgBUhBzY29yZURpc2NyZXBhbmN5Eh4KCnJlc29sdXRpb24YDiABKAlSCnJlc2'
    '9sdXRpb24SJQoOZmluYWxfZGVjaXNpb24YDyABKAlSDWZpbmFsRGVjaXNpb24SHwoLcmVzb2x2'
    'ZWRfYXQYECABKAlSCnJlc29sdmVkQXQSHwoLcmVzb2x2ZWRfYnkYESABKAlSCnJlc29sdmVkQn'
    'kSFAoFbm90ZXMYEiADKAlSBW5vdGVz');

@$core.Deprecated('Use getArbitrationQueueResponseDescriptor instead')
const GetArbitrationQueueResponse$json = {
  '1': 'GetArbitrationQueueResponse',
  '2': [
    {'1': 'cases', '3': 1, '4': 3, '5': 11, '6': '.agent.v1.ArbitrationCaseInfo', '10': 'cases'},
    {'1': 'total_count', '3': 2, '4': 1, '5': 5, '10': 'totalCount'},
  ],
};

/// Descriptor for `GetArbitrationQueueResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List getArbitrationQueueResponseDescriptor = $convert.base64Decode(
    'ChtHZXRBcmJpdHJhdGlvblF1ZXVlUmVzcG9uc2USMwoFY2FzZXMYASADKAsyHS5hZ2VudC52MS'
    '5BcmJpdHJhdGlvbkNhc2VJbmZvUgVjYXNlcxIfCgt0b3RhbF9jb3VudBgCIAEoBVIKdG90YWxD'
    'b3VudA==');

@$core.Deprecated('Use assignArbitrationCaseRequestDescriptor instead')
const AssignArbitrationCaseRequest$json = {
  '1': 'AssignArbitrationCaseRequest',
  '2': [
    {'1': 'case_id', '3': 1, '4': 1, '5': 9, '10': 'caseId'},
    {'1': 'arbitrator_id', '3': 2, '4': 1, '5': 9, '10': 'arbitratorId'},
    {'1': 'arbitrator_role', '3': 3, '4': 1, '5': 9, '10': 'arbitratorRole'},
  ],
};

/// Descriptor for `AssignArbitrationCaseRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List assignArbitrationCaseRequestDescriptor = $convert.base64Decode(
    'ChxBc3NpZ25BcmJpdHJhdGlvbkNhc2VSZXF1ZXN0EhcKB2Nhc2VfaWQYASABKAlSBmNhc2VJZB'
    'IjCg1hcmJpdHJhdG9yX2lkGAIgASgJUgxhcmJpdHJhdG9ySWQSJwoPYXJiaXRyYXRvcl9yb2xl'
    'GAMgASgJUg5hcmJpdHJhdG9yUm9sZQ==');

@$core.Deprecated('Use assignArbitrationCaseResponseDescriptor instead')
const AssignArbitrationCaseResponse$json = {
  '1': 'AssignArbitrationCaseResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
  ],
};

/// Descriptor for `AssignArbitrationCaseResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List assignArbitrationCaseResponseDescriptor = $convert.base64Decode(
    'Ch1Bc3NpZ25BcmJpdHJhdGlvbkNhc2VSZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZX'
    'NzEhgKB21lc3NhZ2UYAiABKAlSB21lc3NhZ2U=');

@$core.Deprecated('Use submitArbitrationDecisionRequestDescriptor instead')
const SubmitArbitrationDecisionRequest$json = {
  '1': 'SubmitArbitrationDecisionRequest',
  '2': [
    {'1': 'case_id', '3': 1, '4': 1, '5': 9, '10': 'caseId'},
    {'1': 'decision', '3': 2, '4': 1, '5': 9, '10': 'decision'},
    {'1': 'explanation', '3': 3, '4': 1, '5': 9, '10': 'explanation'},
    {'1': 'arbitrator_id', '3': 4, '4': 1, '5': 9, '10': 'arbitratorId'},
    {'1': 'arbitrator_role', '3': 5, '4': 1, '5': 9, '10': 'arbitratorRole'},
    {'1': 'feedback_for_model', '3': 6, '4': 1, '5': 9, '10': 'feedbackForModel'},
  ],
};

/// Descriptor for `SubmitArbitrationDecisionRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List submitArbitrationDecisionRequestDescriptor = $convert.base64Decode(
    'CiBTdWJtaXRBcmJpdHJhdGlvbkRlY2lzaW9uUmVxdWVzdBIXCgdjYXNlX2lkGAEgASgJUgZjYX'
    'NlSWQSGgoIZGVjaXNpb24YAiABKAlSCGRlY2lzaW9uEiAKC2V4cGxhbmF0aW9uGAMgASgJUgtl'
    'eHBsYW5hdGlvbhIjCg1hcmJpdHJhdG9yX2lkGAQgASgJUgxhcmJpdHJhdG9ySWQSJwoPYXJiaX'
    'RyYXRvcl9yb2xlGAUgASgJUg5hcmJpdHJhdG9yUm9sZRIsChJmZWVkYmFja19mb3JfbW9kZWwY'
    'BiABKAlSEGZlZWRiYWNrRm9yTW9kZWw=');

@$core.Deprecated('Use submitArbitrationDecisionResponseDescriptor instead')
const SubmitArbitrationDecisionResponse$json = {
  '1': 'SubmitArbitrationDecisionResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'decision_id', '3': 2, '4': 1, '5': 9, '10': 'decisionId'},
    {'1': 'message', '3': 3, '4': 1, '5': 9, '10': 'message'},
  ],
};

/// Descriptor for `SubmitArbitrationDecisionResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List submitArbitrationDecisionResponseDescriptor = $convert.base64Decode(
    'CiFTdWJtaXRBcmJpdHJhdGlvbkRlY2lzaW9uUmVzcG9uc2USGAoHc3VjY2VzcxgBIAEoCFIHc3'
    'VjY2VzcxIfCgtkZWNpc2lvbl9pZBgCIAEoCVIKZGVjaXNpb25JZBIYCgdtZXNzYWdlGAMgASgJ'
    'UgdtZXNzYWdl');

@$core.Deprecated('Use getArbitrationQueueStatsRequestDescriptor instead')
const GetArbitrationQueueStatsRequest$json = {
  '1': 'GetArbitrationQueueStatsRequest',
};

/// Descriptor for `GetArbitrationQueueStatsRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List getArbitrationQueueStatsRequestDescriptor = $convert.base64Decode(
    'Ch9HZXRBcmJpdHJhdGlvblF1ZXVlU3RhdHNSZXF1ZXN0');

@$core.Deprecated('Use arbitrationQueueStatsInfoDescriptor instead')
const ArbitrationQueueStatsInfo$json = {
  '1': 'ArbitrationQueueStatsInfo',
  '2': [
    {'1': 'total_pending', '3': 1, '4': 1, '5': 5, '10': 'totalPending'},
    {'1': 'total_assigned', '3': 2, '4': 1, '5': 5, '10': 'totalAssigned'},
    {'1': 'total_in_review', '3': 3, '4': 1, '5': 5, '10': 'totalInReview'},
    {'1': 'total_resolved_today', '3': 4, '4': 1, '5': 5, '10': 'totalResolvedToday'},
    {'1': 'avg_resolution_time_hours', '3': 5, '4': 1, '5': 1, '10': 'avgResolutionTimeHours'},
    {'1': 'by_priority', '3': 6, '4': 3, '5': 11, '6': '.agent.v1.ArbitrationQueueStatsInfo.ByPriorityEntry', '10': 'byPriority'},
    {'1': 'by_reason', '3': 7, '4': 3, '5': 11, '6': '.agent.v1.ArbitrationQueueStatsInfo.ByReasonEntry', '10': 'byReason'},
  ],
  '3': [ArbitrationQueueStatsInfo_ByPriorityEntry$json, ArbitrationQueueStatsInfo_ByReasonEntry$json],
};

@$core.Deprecated('Use arbitrationQueueStatsInfoDescriptor instead')
const ArbitrationQueueStatsInfo_ByPriorityEntry$json = {
  '1': 'ByPriorityEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 5, '10': 'value'},
  ],
  '7': {'7': true},
};

@$core.Deprecated('Use arbitrationQueueStatsInfoDescriptor instead')
const ArbitrationQueueStatsInfo_ByReasonEntry$json = {
  '1': 'ByReasonEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 5, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `ArbitrationQueueStatsInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List arbitrationQueueStatsInfoDescriptor = $convert.base64Decode(
    'ChlBcmJpdHJhdGlvblF1ZXVlU3RhdHNJbmZvEiMKDXRvdGFsX3BlbmRpbmcYASABKAVSDHRvdG'
    'FsUGVuZGluZxIlCg50b3RhbF9hc3NpZ25lZBgCIAEoBVINdG90YWxBc3NpZ25lZBImCg90b3Rh'
    'bF9pbl9yZXZpZXcYAyABKAVSDXRvdGFsSW5SZXZpZXcSMAoUdG90YWxfcmVzb2x2ZWRfdG9kYX'
    'kYBCABKAVSEnRvdGFsUmVzb2x2ZWRUb2RheRI5ChlhdmdfcmVzb2x1dGlvbl90aW1lX2hvdXJz'
    'GAUgASgBUhZhdmdSZXNvbHV0aW9uVGltZUhvdXJzElQKC2J5X3ByaW9yaXR5GAYgAygLMjMuYW'
    'dlbnQudjEuQXJiaXRyYXRpb25RdWV1ZVN0YXRzSW5mby5CeVByaW9yaXR5RW50cnlSCmJ5UHJp'
    'b3JpdHkSTgoJYnlfcmVhc29uGAcgAygLMjEuYWdlbnQudjEuQXJiaXRyYXRpb25RdWV1ZVN0YX'
    'RzSW5mby5CeVJlYXNvbkVudHJ5UghieVJlYXNvbho9Cg9CeVByaW9yaXR5RW50cnkSEAoDa2V5'
    'GAEgASgJUgNrZXkSFAoFdmFsdWUYAiABKAVSBXZhbHVlOgI4ARo7Cg1CeVJlYXNvbkVudHJ5Eh'
    'AKA2tleRgBIAEoCVIDa2V5EhQKBXZhbHVlGAIgASgFUgV2YWx1ZToCOAE=');

@$core.Deprecated('Use getArbitrationQueueStatsResponseDescriptor instead')
const GetArbitrationQueueStatsResponse$json = {
  '1': 'GetArbitrationQueueStatsResponse',
  '2': [
    {'1': 'stats', '3': 1, '4': 1, '5': 11, '6': '.agent.v1.ArbitrationQueueStatsInfo', '10': 'stats'},
  ],
};

/// Descriptor for `GetArbitrationQueueStatsResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List getArbitrationQueueStatsResponseDescriptor = $convert.base64Decode(
    'CiBHZXRBcmJpdHJhdGlvblF1ZXVlU3RhdHNSZXNwb25zZRI5CgVzdGF0cxgBIAEoCzIjLmFnZW'
    '50LnYxLkFyYml0cmF0aW9uUXVldWVTdGF0c0luZm9SBXN0YXRz');

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

