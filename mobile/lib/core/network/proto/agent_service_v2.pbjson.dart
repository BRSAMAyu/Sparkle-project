//
//  Generated code. Do not modify.
//  source: agent_service_v2.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

@$core.Deprecated('Use chatRequestV2Descriptor instead')
const ChatRequestV2$json = {
  '1': 'ChatRequestV2',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
    {'1': 'session_id', '3': 3, '4': 1, '5': 9, '10': 'sessionId'},
    {'1': 'active_tools', '3': 4, '4': 3, '5': 9, '10': 'activeTools'},
  ],
};

/// Descriptor for `ChatRequestV2`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List chatRequestV2Descriptor = $convert.base64Decode(
    'Cg1DaGF0UmVxdWVzdFYyEhcKB3VzZXJfaWQYASABKAlSBnVzZXJJZBIYCgdtZXNzYWdlGAIgAS'
    'gJUgdtZXNzYWdlEh0KCnNlc3Npb25faWQYAyABKAlSCXNlc3Npb25JZBIhCgxhY3RpdmVfdG9v'
    'bHMYBCADKAlSC2FjdGl2ZVRvb2xz');

@$core.Deprecated('Use chatResponseV2Descriptor instead')
const ChatResponseV2$json = {
  '1': 'ChatResponseV2',
  '2': [
    {'1': 'content', '3': 1, '4': 1, '5': 9, '10': 'content'},
    {'1': 'type', '3': 2, '4': 1, '5': 9, '10': 'type'},
    {'1': 'timestamp', '3': 3, '4': 1, '5': 3, '10': 'timestamp'},
  ],
};

/// Descriptor for `ChatResponseV2`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List chatResponseV2Descriptor = $convert.base64Decode(
    'Cg5DaGF0UmVzcG9uc2VWMhIYCgdjb250ZW50GAEgASgJUgdjb250ZW50EhIKBHR5cGUYAiABKA'
    'lSBHR5cGUSHAoJdGltZXN0YW1wGAMgASgDUgl0aW1lc3RhbXA=');

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

@$core.Deprecated('Use profileRequestV2Descriptor instead')
const ProfileRequestV2$json = {
  '1': 'ProfileRequestV2',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
  ],
};

/// Descriptor for `ProfileRequestV2`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List profileRequestV2Descriptor = $convert.base64Decode(
    'ChBQcm9maWxlUmVxdWVzdFYyEhcKB3VzZXJfaWQYASABKAlSBnVzZXJJZA==');

@$core.Deprecated('Use profileResponseV2Descriptor instead')
const ProfileResponseV2$json = {
  '1': 'ProfileResponseV2',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'nickname', '3': 2, '4': 1, '5': 9, '10': 'nickname'},
    {'1': 'level', '3': 3, '4': 1, '5': 5, '10': 'level'},
    {'1': 'avatar_url', '3': 4, '4': 1, '5': 9, '10': 'avatarUrl'},
  ],
};

/// Descriptor for `ProfileResponseV2`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List profileResponseV2Descriptor = $convert.base64Decode(
    'ChFQcm9maWxlUmVzcG9uc2VWMhIXCgd1c2VyX2lkGAEgASgJUgZ1c2VySWQSGgoIbmlja25hbW'
    'UYAiABKAlSCG5pY2tuYW1lEhQKBWxldmVsGAMgASgFUgVsZXZlbBIdCgphdmF0YXJfdXJsGAQg'
    'ASgJUglhdmF0YXJVcmw=');

const $core.Map<$core.String, $core.dynamic> AgentServiceV2ServiceBase$json = {
  '1': 'AgentServiceV2',
  '2': [
    {'1': 'StreamChat', '2': '.sparkle.agent.v2.ChatRequestV2', '3': '.sparkle.agent.v2.ChatResponseV2', '6': true},
    {'1': 'GetUserProfile', '2': '.sparkle.agent.v2.ProfileRequestV2', '3': '.sparkle.agent.v2.ProfileResponseV2'},
    {'1': 'GetWeeklyReport', '2': '.sparkle.agent.v2.WeeklyReportRequest', '3': '.sparkle.agent.v2.WeeklyReport'},
  ],
};

@$core.Deprecated('Use agentServiceV2ServiceDescriptor instead')
const $core.Map<$core.String, $core.Map<$core.String, $core.dynamic>> AgentServiceV2ServiceBase$messageJson = {
  '.sparkle.agent.v2.ChatRequestV2': ChatRequestV2$json,
  '.sparkle.agent.v2.ChatResponseV2': ChatResponseV2$json,
  '.sparkle.agent.v2.ProfileRequestV2': ProfileRequestV2$json,
  '.sparkle.agent.v2.ProfileResponseV2': ProfileResponseV2$json,
  '.sparkle.agent.v2.WeeklyReportRequest': WeeklyReportRequest$json,
  '.sparkle.agent.v2.WeeklyReport': WeeklyReport$json,
};

/// Descriptor for `AgentServiceV2`. Decode as a `google.protobuf.ServiceDescriptorProto`.
final $typed_data.Uint8List agentServiceV2ServiceDescriptor = $convert.base64Decode(
    'Cg5BZ2VudFNlcnZpY2VWMhJRCgpTdHJlYW1DaGF0Eh8uc3BhcmtsZS5hZ2VudC52Mi5DaGF0Um'
    'VxdWVzdFYyGiAuc3BhcmtsZS5hZ2VudC52Mi5DaGF0UmVzcG9uc2VWMjABElkKDkdldFVzZXJQ'
    'cm9maWxlEiIuc3BhcmtsZS5hZ2VudC52Mi5Qcm9maWxlUmVxdWVzdFYyGiMuc3BhcmtsZS5hZ2'
    'VudC52Mi5Qcm9maWxlUmVzcG9uc2VWMhJYCg9HZXRXZWVrbHlSZXBvcnQSJS5zcGFya2xlLmFn'
    'ZW50LnYyLldlZWtseVJlcG9ydFJlcXVlc3QaHi5zcGFya2xlLmFnZW50LnYyLldlZWtseVJlcG'
    '9ydA==');

