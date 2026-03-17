// This is a generated file - do not edit.
//
// Generated from community_service.proto.

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

@$core.Deprecated('Use friendshipStatusDescriptor instead')
const FriendshipStatus$json = {
  '1': 'FriendshipStatus',
  '2': [
    {'1': 'FRIENDSHIP_STATUS_UNSPECIFIED', '2': 0},
    {'1': 'PENDING', '2': 1},
    {'1': 'ACCEPTED', '2': 2},
    {'1': 'BLOCKED', '2': 3},
  ],
};

/// Descriptor for `FriendshipStatus`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List friendshipStatusDescriptor = $convert.base64Decode(
    'ChBGcmllbmRzaGlwU3RhdHVzEiEKHUZSSUVORFNISVBfU1RBVFVTX1VOU1BFQ0lGSUVEEAASCw'
    'oHUEVORElORxABEgwKCEFDQ0VQVEVEEAISCwoHQkxPQ0tFRBAD');

@$core.Deprecated('Use groupTypeDescriptor instead')
const GroupType$json = {
  '1': 'GroupType',
  '2': [
    {'1': 'GROUP_TYPE_UNSPECIFIED', '2': 0},
    {'1': 'SQUAD', '2': 1},
    {'1': 'SPRINT', '2': 2},
    {'1': 'OFFICIAL', '2': 3},
  ],
};

/// Descriptor for `GroupType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List groupTypeDescriptor = $convert.base64Decode(
    'CglHcm91cFR5cGUSGgoWR1JPVVBfVFlQRV9VTlNQRUNJRklFRBAAEgkKBVNRVUFEEAESCgoGU1'
    'BSSU5UEAISDAoIT0ZGSUNJQUwQAw==');

@$core.Deprecated('Use groupRoleDescriptor instead')
const GroupRole$json = {
  '1': 'GroupRole',
  '2': [
    {'1': 'GROUP_ROLE_UNSPECIFIED', '2': 0},
    {'1': 'OWNER', '2': 1},
    {'1': 'ADMIN', '2': 2},
    {'1': 'MEMBER', '2': 3},
  ],
};

/// Descriptor for `GroupRole`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List groupRoleDescriptor = $convert.base64Decode(
    'CglHcm91cFJvbGUSGgoWR1JPVVBfUk9MRV9VTlNQRUNJRklFRBAAEgkKBU9XTkVSEAESCQoFQU'
    'RNSU4QAhIKCgZNRU1CRVIQAw==');

@$core.Deprecated('Use messageTypeDescriptor instead')
const MessageType$json = {
  '1': 'MessageType',
  '2': [
    {'1': 'MESSAGE_TYPE_UNSPECIFIED', '2': 0},
    {'1': 'TEXT', '2': 1},
    {'1': 'TASK_SHARE', '2': 2},
    {'1': 'PLAN_SHARE', '2': 3},
    {'1': 'FRAGMENT_SHARE', '2': 4},
    {'1': 'CAPSULE_SHARE', '2': 5},
    {'1': 'PRISM_SHARE', '2': 6},
    {'1': 'FILE_SHARE', '2': 7},
    {'1': 'PROGRESS', '2': 8},
    {'1': 'ACHIEVEMENT', '2': 9},
    {'1': 'CHECKIN', '2': 10},
    {'1': 'SYSTEM', '2': 11},
    {'1': 'BROADCAST', '2': 12},
  ],
};

/// Descriptor for `MessageType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List messageTypeDescriptor = $convert.base64Decode(
    'CgtNZXNzYWdlVHlwZRIcChhNRVNTQUdFX1RZUEVfVU5TUEVDSUZJRUQQABIICgRURVhUEAESDg'
    'oKVEFTS19TSEFSRRACEg4KClBMQU5fU0hBUkUQAxISCg5GUkFHTUVOVF9TSEFSRRAEEhEKDUNB'
    'UFNVTEVfU0hBUkUQBRIPCgtQUklTTV9TSEFSRRAGEg4KCkZJTEVfU0hBUkUQBxIMCghQUk9HUk'
    'VTUxAIEg8KC0FDSElFVkVNRU5UEAkSCwoHQ0hFQ0tJThAKEgoKBlNZU1RFTRALEg0KCUJST0FE'
    'Q0FTVBAM');

@$core.Deprecated('Use searchVisibilityDescriptor instead')
const SearchVisibility$json = {
  '1': 'SearchVisibility',
  '2': [
    {'1': 'SEARCH_VISIBILITY_UNSPECIFIED', '2': 0},
    {'1': 'EVERYONE', '2': 1},
    {'1': 'FRIENDS', '2': 2},
    {'1': 'NOBODY', '2': 3},
  ],
};

/// Descriptor for `SearchVisibility`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List searchVisibilityDescriptor = $convert.base64Decode(
    'ChBTZWFyY2hWaXNpYmlsaXR5EiEKHVNFQVJDSF9WSVNJQklMSVRZX1VOU1BFQ0lGSUVEEAASDA'
    'oIRVZFUllPTkUQARILCgdGUklFTkRTEAISCgoGTk9CT0RZEAM=');

@$core.Deprecated('Use uUIDDescriptor instead')
const UUID$json = {
  '1': 'UUID',
  '2': [
    {'1': 'value', '3': 1, '4': 1, '5': 9, '10': 'value'},
  ],
};

/// Descriptor for `UUID`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List uUIDDescriptor =
    $convert.base64Decode('CgRVVUlEEhQKBXZhbHVlGAEgASgJUgV2YWx1ZQ==');

@$core.Deprecated('Use userBriefDescriptor instead')
const UserBrief$json = {
  '1': 'UserBrief',
  '2': [
    {
      '1': 'id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'id'
    },
    {'1': 'username', '3': 2, '4': 1, '5': 9, '10': 'username'},
    {'1': 'nickname', '3': 3, '4': 1, '5': 9, '10': 'nickname'},
    {'1': 'avatar_url', '3': 4, '4': 1, '5': 9, '10': 'avatarUrl'},
    {'1': 'flame_level', '3': 5, '4': 1, '5': 5, '10': 'flameLevel'},
    {'1': 'flame_brightness', '3': 6, '4': 1, '5': 2, '10': 'flameBrightness'},
    {'1': 'status', '3': 7, '4': 1, '5': 9, '10': 'status'},
  ],
};

/// Descriptor for `UserBrief`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List userBriefDescriptor = $convert.base64Decode(
    'CglVc2VyQnJpZWYSJwoCaWQYASABKAsyFy5zcGFya2xlLmNvbW11bml0eS5VVUlEUgJpZBIaCg'
    'h1c2VybmFtZRgCIAEoCVIIdXNlcm5hbWUSGgoIbmlja25hbWUYAyABKAlSCG5pY2tuYW1lEh0K'
    'CmF2YXRhcl91cmwYBCABKAlSCWF2YXRhclVybBIfCgtmbGFtZV9sZXZlbBgFIAEoBVIKZmxhbW'
    'VMZXZlbBIpChBmbGFtZV9icmlnaHRuZXNzGAYgASgCUg9mbGFtZUJyaWdodG5lc3MSFgoGc3Rh'
    'dHVzGAcgASgJUgZzdGF0dXM=');

@$core.Deprecated('Use friendRequestDescriptor instead')
const FriendRequest$json = {
  '1': 'FriendRequest',
  '2': [
    {
      '1': 'target_user_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'targetUserId'
    },
    {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
  ],
};

/// Descriptor for `FriendRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List friendRequestDescriptor = $convert.base64Decode(
    'Cg1GcmllbmRSZXF1ZXN0Ej0KDnRhcmdldF91c2VyX2lkGAEgASgLMhcuc3BhcmtsZS5jb21tdW'
    '5pdHkuVVVJRFIMdGFyZ2V0VXNlcklkEhgKB21lc3NhZ2UYAiABKAlSB21lc3NhZ2U=');

@$core.Deprecated('Use friendResponseDescriptor instead')
const FriendResponse$json = {
  '1': 'FriendResponse',
  '2': [
    {
      '1': 'friendship_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'friendshipId'
    },
    {'1': 'accept', '3': 2, '4': 1, '5': 8, '10': 'accept'},
  ],
};

/// Descriptor for `FriendResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List friendResponseDescriptor = $convert.base64Decode(
    'Cg5GcmllbmRSZXNwb25zZRI8Cg1mcmllbmRzaGlwX2lkGAEgASgLMhcuc3BhcmtsZS5jb21tdW'
    '5pdHkuVVVJRFIMZnJpZW5kc2hpcElkEhYKBmFjY2VwdBgCIAEoCFIGYWNjZXB0');

@$core.Deprecated('Use friendshipInfoDescriptor instead')
const FriendshipInfo$json = {
  '1': 'FriendshipInfo',
  '2': [
    {
      '1': 'friend',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UserBrief',
      '10': 'friend'
    },
    {
      '1': 'status',
      '3': 2,
      '4': 1,
      '5': 14,
      '6': '.sparkle.community.FriendshipStatus',
      '10': 'status'
    },
    {
      '1': 'match_reason',
      '3': 3,
      '4': 3,
      '5': 11,
      '6': '.sparkle.community.FriendshipInfo.MatchReasonEntry',
      '10': 'matchReason'
    },
    {'1': 'initiated_by_me', '3': 4, '4': 1, '5': 8, '10': 'initiatedByMe'},
  ],
  '3': [FriendshipInfo_MatchReasonEntry$json],
};

@$core.Deprecated('Use friendshipInfoDescriptor instead')
const FriendshipInfo_MatchReasonEntry$json = {
  '1': 'MatchReasonEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `FriendshipInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List friendshipInfoDescriptor = $convert.base64Decode(
    'Cg5GcmllbmRzaGlwSW5mbxI0CgZmcmllbmQYASABKAsyHC5zcGFya2xlLmNvbW11bml0eS5Vc2'
    'VyQnJpZWZSBmZyaWVuZBI7CgZzdGF0dXMYAiABKA4yIy5zcGFya2xlLmNvbW11bml0eS5Gcmll'
    'bmRzaGlwU3RhdHVzUgZzdGF0dXMSVQoMbWF0Y2hfcmVhc29uGAMgAygLMjIuc3BhcmtsZS5jb2'
    '1tdW5pdHkuRnJpZW5kc2hpcEluZm8uTWF0Y2hSZWFzb25FbnRyeVILbWF0Y2hSZWFzb24SJgoP'
    'aW5pdGlhdGVkX2J5X21lGAQgASgIUg1pbml0aWF0ZWRCeU1lGj4KEE1hdGNoUmVhc29uRW50cn'
    'kSEAoDa2V5GAEgASgJUgNrZXkSFAoFdmFsdWUYAiABKAlSBXZhbHVlOgI4AQ==');

@$core.Deprecated('Use blockUserRequestDescriptor instead')
const BlockUserRequest$json = {
  '1': 'BlockUserRequest',
  '2': [
    {
      '1': 'target_user_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'targetUserId'
    },
    {'1': 'reason', '3': 2, '4': 1, '5': 9, '10': 'reason'},
  ],
};

/// Descriptor for `BlockUserRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List blockUserRequestDescriptor = $convert.base64Decode(
    'ChBCbG9ja1VzZXJSZXF1ZXN0Ej0KDnRhcmdldF91c2VyX2lkGAEgASgLMhcuc3BhcmtsZS5jb2'
    '1tdW5pdHkuVVVJRFIMdGFyZ2V0VXNlcklkEhYKBnJlYXNvbhgCIAEoCVIGcmVhc29u');

@$core.Deprecated('Use blockUserInfoDescriptor instead')
const BlockUserInfo$json = {
  '1': 'BlockUserInfo',
  '2': [
    {
      '1': 'blocked_user',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UserBrief',
      '10': 'blockedUser'
    },
    {'1': 'reason', '3': 2, '4': 1, '5': 9, '10': 'reason'},
    {
      '1': 'created_at',
      '3': 3,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'createdAt'
    },
  ],
};

/// Descriptor for `BlockUserInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List blockUserInfoDescriptor = $convert.base64Decode(
    'Cg1CbG9ja1VzZXJJbmZvEj8KDGJsb2NrZWRfdXNlchgBIAEoCzIcLnNwYXJrbGUuY29tbXVuaX'
    'R5LlVzZXJCcmllZlILYmxvY2tlZFVzZXISFgoGcmVhc29uGAIgASgJUgZyZWFzb24SOQoKY3Jl'
    'YXRlZF9hdBgDIAEoCzIaLmdvb2dsZS5wcm90b2J1Zi5UaW1lc3RhbXBSCWNyZWF0ZWRBdA==');

@$core.Deprecated('Use groupCreateDescriptor instead')
const GroupCreate$json = {
  '1': 'GroupCreate',
  '2': [
    {'1': 'name', '3': 1, '4': 1, '5': 9, '10': 'name'},
    {'1': 'description', '3': 2, '4': 1, '5': 9, '10': 'description'},
    {
      '1': 'type',
      '3': 3,
      '4': 1,
      '5': 14,
      '6': '.sparkle.community.GroupType',
      '10': 'type'
    },
    {'1': 'focus_tags', '3': 4, '4': 3, '5': 9, '10': 'focusTags'},
    {
      '1': 'deadline',
      '3': 5,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'deadline'
    },
    {'1': 'sprint_goal', '3': 6, '4': 1, '5': 9, '10': 'sprintGoal'},
    {'1': 'max_members', '3': 7, '4': 1, '5': 5, '10': 'maxMembers'},
    {'1': 'is_public', '3': 8, '4': 1, '5': 8, '10': 'isPublic'},
    {
      '1': 'join_requires_approval',
      '3': 9,
      '4': 1,
      '5': 8,
      '10': 'joinRequiresApproval'
    },
  ],
};

/// Descriptor for `GroupCreate`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List groupCreateDescriptor = $convert.base64Decode(
    'CgtHcm91cENyZWF0ZRISCgRuYW1lGAEgASgJUgRuYW1lEiAKC2Rlc2NyaXB0aW9uGAIgASgJUg'
    'tkZXNjcmlwdGlvbhIwCgR0eXBlGAMgASgOMhwuc3BhcmtsZS5jb21tdW5pdHkuR3JvdXBUeXBl'
    'UgR0eXBlEh0KCmZvY3VzX3RhZ3MYBCADKAlSCWZvY3VzVGFncxI2CghkZWFkbGluZRgFIAEoCz'
    'IaLmdvb2dsZS5wcm90b2J1Zi5UaW1lc3RhbXBSCGRlYWRsaW5lEh8KC3NwcmludF9nb2FsGAYg'
    'ASgJUgpzcHJpbnRHb2FsEh8KC21heF9tZW1iZXJzGAcgASgFUgptYXhNZW1iZXJzEhsKCWlzX3'
    'B1YmxpYxgIIAEoCFIIaXNQdWJsaWMSNAoWam9pbl9yZXF1aXJlc19hcHByb3ZhbBgJIAEoCFIU'
    'am9pblJlcXVpcmVzQXBwcm92YWw=');

@$core.Deprecated('Use groupInfoDescriptor instead')
const GroupInfo$json = {
  '1': 'GroupInfo',
  '2': [
    {
      '1': 'id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'id'
    },
    {'1': 'name', '3': 2, '4': 1, '5': 9, '10': 'name'},
    {'1': 'description', '3': 3, '4': 1, '5': 9, '10': 'description'},
    {'1': 'avatar_url', '3': 4, '4': 1, '5': 9, '10': 'avatarUrl'},
    {
      '1': 'type',
      '3': 5,
      '4': 1,
      '5': 14,
      '6': '.sparkle.community.GroupType',
      '10': 'type'
    },
    {'1': 'focus_tags', '3': 6, '4': 3, '5': 9, '10': 'focusTags'},
    {
      '1': 'deadline',
      '3': 7,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'deadline'
    },
    {'1': 'sprint_goal', '3': 8, '4': 1, '5': 9, '10': 'sprintGoal'},
    {'1': 'days_remaining', '3': 9, '4': 1, '5': 5, '10': 'daysRemaining'},
    {'1': 'member_count', '3': 10, '4': 1, '5': 5, '10': 'memberCount'},
    {
      '1': 'total_flame_power',
      '3': 11,
      '4': 1,
      '5': 5,
      '10': 'totalFlamePower'
    },
    {
      '1': 'today_checkin_count',
      '3': 12,
      '4': 1,
      '5': 5,
      '10': 'todayCheckinCount'
    },
    {
      '1': 'total_tasks_completed',
      '3': 13,
      '4': 1,
      '5': 5,
      '10': 'totalTasksCompleted'
    },
    {'1': 'max_members', '3': 14, '4': 1, '5': 5, '10': 'maxMembers'},
    {'1': 'is_public', '3': 15, '4': 1, '5': 8, '10': 'isPublic'},
    {
      '1': 'join_requires_approval',
      '3': 16,
      '4': 1,
      '5': 8,
      '10': 'joinRequiresApproval'
    },
    {
      '1': 'my_role',
      '3': 17,
      '4': 1,
      '5': 14,
      '6': '.sparkle.community.GroupRole',
      '10': 'myRole'
    },
  ],
};

/// Descriptor for `GroupInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List groupInfoDescriptor = $convert.base64Decode(
    'CglHcm91cEluZm8SJwoCaWQYASABKAsyFy5zcGFya2xlLmNvbW11bml0eS5VVUlEUgJpZBISCg'
    'RuYW1lGAIgASgJUgRuYW1lEiAKC2Rlc2NyaXB0aW9uGAMgASgJUgtkZXNjcmlwdGlvbhIdCgph'
    'dmF0YXJfdXJsGAQgASgJUglhdmF0YXJVcmwSMAoEdHlwZRgFIAEoDjIcLnNwYXJrbGUuY29tbX'
    'VuaXR5Lkdyb3VwVHlwZVIEdHlwZRIdCgpmb2N1c190YWdzGAYgAygJUglmb2N1c1RhZ3MSNgoI'
    'ZGVhZGxpbmUYByABKAsyGi5nb29nbGUucHJvdG9idWYuVGltZXN0YW1wUghkZWFkbGluZRIfCg'
    'tzcHJpbnRfZ29hbBgIIAEoCVIKc3ByaW50R29hbBIlCg5kYXlzX3JlbWFpbmluZxgJIAEoBVIN'
    'ZGF5c1JlbWFpbmluZxIhCgxtZW1iZXJfY291bnQYCiABKAVSC21lbWJlckNvdW50EioKEXRvdG'
    'FsX2ZsYW1lX3Bvd2VyGAsgASgFUg90b3RhbEZsYW1lUG93ZXISLgoTdG9kYXlfY2hlY2tpbl9j'
    'b3VudBgMIAEoBVIRdG9kYXlDaGVja2luQ291bnQSMgoVdG90YWxfdGFza3NfY29tcGxldGVkGA'
    '0gASgFUhN0b3RhbFRhc2tzQ29tcGxldGVkEh8KC21heF9tZW1iZXJzGA4gASgFUgptYXhNZW1i'
    'ZXJzEhsKCWlzX3B1YmxpYxgPIAEoCFIIaXNQdWJsaWMSNAoWam9pbl9yZXF1aXJlc19hcHByb3'
    'ZhbBgQIAEoCFIUam9pblJlcXVpcmVzQXBwcm92YWwSNQoHbXlfcm9sZRgRIAEoDjIcLnNwYXJr'
    'bGUuY29tbXVuaXR5Lkdyb3VwUm9sZVIGbXlSb2xl');

@$core.Deprecated('Use groupMemberInfoDescriptor instead')
const GroupMemberInfo$json = {
  '1': 'GroupMemberInfo',
  '2': [
    {
      '1': 'user',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UserBrief',
      '10': 'user'
    },
    {
      '1': 'role',
      '3': 2,
      '4': 1,
      '5': 14,
      '6': '.sparkle.community.GroupRole',
      '10': 'role'
    },
    {
      '1': 'flame_contribution',
      '3': 3,
      '4': 1,
      '5': 5,
      '10': 'flameContribution'
    },
    {'1': 'tasks_completed', '3': 4, '4': 1, '5': 5, '10': 'tasksCompleted'},
    {'1': 'checkin_streak', '3': 5, '4': 1, '5': 5, '10': 'checkinStreak'},
    {
      '1': 'joined_at',
      '3': 6,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'joinedAt'
    },
    {
      '1': 'last_active_at',
      '3': 7,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'lastActiveAt'
    },
  ],
};

/// Descriptor for `GroupMemberInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List groupMemberInfoDescriptor = $convert.base64Decode(
    'Cg9Hcm91cE1lbWJlckluZm8SMAoEdXNlchgBIAEoCzIcLnNwYXJrbGUuY29tbXVuaXR5LlVzZX'
    'JCcmllZlIEdXNlchIwCgRyb2xlGAIgASgOMhwuc3BhcmtsZS5jb21tdW5pdHkuR3JvdXBSb2xl'
    'UgRyb2xlEi0KEmZsYW1lX2NvbnRyaWJ1dGlvbhgDIAEoBVIRZmxhbWVDb250cmlidXRpb24SJw'
    'oPdGFza3NfY29tcGxldGVkGAQgASgFUg50YXNrc0NvbXBsZXRlZBIlCg5jaGVja2luX3N0cmVh'
    'axgFIAEoBVINY2hlY2tpblN0cmVhaxI3Cglqb2luZWRfYXQYBiABKAsyGi5nb29nbGUucHJvdG'
    '9idWYuVGltZXN0YW1wUghqb2luZWRBdBJACg5sYXN0X2FjdGl2ZV9hdBgHIAEoCzIaLmdvb2ds'
    'ZS5wcm90b2J1Zi5UaW1lc3RhbXBSDGxhc3RBY3RpdmVBdA==');

@$core.Deprecated('Use messageSendDescriptor instead')
const MessageSend$json = {
  '1': 'MessageSend',
  '2': [
    {
      '1': 'message_type',
      '3': 1,
      '4': 1,
      '5': 14,
      '6': '.sparkle.community.MessageType',
      '10': 'messageType'
    },
    {'1': 'content', '3': 2, '4': 1, '5': 9, '10': 'content'},
    {'1': 'content_data', '3': 3, '4': 1, '5': 9, '10': 'contentData'},
    {
      '1': 'reply_to_id',
      '3': 4,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'replyToId'
    },
    {
      '1': 'thread_root_id',
      '3': 5,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'threadRootId'
    },
    {
      '1': 'mention_user_ids',
      '3': 6,
      '4': 3,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'mentionUserIds'
    },
    {'1': 'nonce', '3': 7, '4': 1, '5': 9, '10': 'nonce'},
  ],
};

/// Descriptor for `MessageSend`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List messageSendDescriptor = $convert.base64Decode(
    'CgtNZXNzYWdlU2VuZBJBCgxtZXNzYWdlX3R5cGUYASABKA4yHi5zcGFya2xlLmNvbW11bml0eS'
    '5NZXNzYWdlVHlwZVILbWVzc2FnZVR5cGUSGAoHY29udGVudBgCIAEoCVIHY29udGVudBIhCgxj'
    'b250ZW50X2RhdGEYAyABKAlSC2NvbnRlbnREYXRhEjcKC3JlcGx5X3RvX2lkGAQgASgLMhcuc3'
    'BhcmtsZS5jb21tdW5pdHkuVVVJRFIJcmVwbHlUb0lkEj0KDnRocmVhZF9yb290X2lkGAUgASgL'
    'Mhcuc3BhcmtsZS5jb21tdW5pdHkuVVVJRFIMdGhyZWFkUm9vdElkEkEKEG1lbnRpb25fdXNlcl'
    '9pZHMYBiADKAsyFy5zcGFya2xlLmNvbW11bml0eS5VVUlEUg5tZW50aW9uVXNlcklkcxIUCgVu'
    'b25jZRgHIAEoCVIFbm9uY2U=');

@$core.Deprecated('Use messageInfoDescriptor instead')
const MessageInfo$json = {
  '1': 'MessageInfo',
  '2': [
    {
      '1': 'id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'id'
    },
    {
      '1': 'sender',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UserBrief',
      '10': 'sender'
    },
    {
      '1': 'message_type',
      '3': 3,
      '4': 1,
      '5': 14,
      '6': '.sparkle.community.MessageType',
      '10': 'messageType'
    },
    {'1': 'content', '3': 4, '4': 1, '5': 9, '10': 'content'},
    {'1': 'content_data', '3': 5, '4': 1, '5': 9, '10': 'contentData'},
    {
      '1': 'reply_to_id',
      '3': 6,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'replyToId'
    },
    {
      '1': 'thread_root_id',
      '3': 7,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'threadRootId'
    },
    {
      '1': 'mention_user_ids',
      '3': 8,
      '4': 3,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'mentionUserIds'
    },
    {
      '1': 'reactions',
      '3': 9,
      '4': 3,
      '5': 11,
      '6': '.sparkle.community.MessageInfo.ReactionsEntry',
      '10': 'reactions'
    },
    {'1': 'is_revoked', '3': 10, '4': 1, '5': 8, '10': 'isRevoked'},
    {
      '1': 'revoked_at',
      '3': 11,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'revokedAt'
    },
    {
      '1': 'edited_at',
      '3': 12,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'editedAt'
    },
    {
      '1': 'created_at',
      '3': 13,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'createdAt'
    },
  ],
  '3': [MessageInfo_ReactionsEntry$json],
};

@$core.Deprecated('Use messageInfoDescriptor instead')
const MessageInfo_ReactionsEntry$json = {
  '1': 'ReactionsEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `MessageInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List messageInfoDescriptor = $convert.base64Decode(
    'CgtNZXNzYWdlSW5mbxInCgJpZBgBIAEoCzIXLnNwYXJrbGUuY29tbXVuaXR5LlVVSURSAmlkEj'
    'QKBnNlbmRlchgCIAEoCzIcLnNwYXJrbGUuY29tbXVuaXR5LlVzZXJCcmllZlIGc2VuZGVyEkEK'
    'DG1lc3NhZ2VfdHlwZRgDIAEoDjIeLnNwYXJrbGUuY29tbXVuaXR5Lk1lc3NhZ2VUeXBlUgttZX'
    'NzYWdlVHlwZRIYCgdjb250ZW50GAQgASgJUgdjb250ZW50EiEKDGNvbnRlbnRfZGF0YRgFIAEo'
    'CVILY29udGVudERhdGESNwoLcmVwbHlfdG9faWQYBiABKAsyFy5zcGFya2xlLmNvbW11bml0eS'
    '5VVUlEUglyZXBseVRvSWQSPQoOdGhyZWFkX3Jvb3RfaWQYByABKAsyFy5zcGFya2xlLmNvbW11'
    'bml0eS5VVUlEUgx0aHJlYWRSb290SWQSQQoQbWVudGlvbl91c2VyX2lkcxgIIAMoCzIXLnNwYX'
    'JrbGUuY29tbXVuaXR5LlVVSURSDm1lbnRpb25Vc2VySWRzEksKCXJlYWN0aW9ucxgJIAMoCzIt'
    'LnNwYXJrbGUuY29tbXVuaXR5Lk1lc3NhZ2VJbmZvLlJlYWN0aW9uc0VudHJ5UglyZWFjdGlvbn'
    'MSHQoKaXNfcmV2b2tlZBgKIAEoCFIJaXNSZXZva2VkEjkKCnJldm9rZWRfYXQYCyABKAsyGi5n'
    'b29nbGUucHJvdG9idWYuVGltZXN0YW1wUglyZXZva2VkQXQSNwoJZWRpdGVkX2F0GAwgASgLMh'
    'ouZ29vZ2xlLnByb3RvYnVmLlRpbWVzdGFtcFIIZWRpdGVkQXQSOQoKY3JlYXRlZF9hdBgNIAEo'
    'CzIaLmdvb2dsZS5wcm90b2J1Zi5UaW1lc3RhbXBSCWNyZWF0ZWRBdBo8Cg5SZWFjdGlvbnNFbn'
    'RyeRIQCgNrZXkYASABKAlSA2tleRIUCgV2YWx1ZRgCIAEoCVIFdmFsdWU6AjgB');

@$core.Deprecated('Use privateMessageSendDescriptor instead')
const PrivateMessageSend$json = {
  '1': 'PrivateMessageSend',
  '2': [
    {
      '1': 'target_user_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'targetUserId'
    },
    {
      '1': 'message_type',
      '3': 2,
      '4': 1,
      '5': 14,
      '6': '.sparkle.community.MessageType',
      '10': 'messageType'
    },
    {'1': 'content', '3': 3, '4': 1, '5': 9, '10': 'content'},
    {'1': 'content_data', '3': 4, '4': 1, '5': 9, '10': 'contentData'},
    {
      '1': 'reply_to_id',
      '3': 5,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'replyToId'
    },
    {
      '1': 'thread_root_id',
      '3': 6,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'threadRootId'
    },
    {
      '1': 'mention_user_ids',
      '3': 7,
      '4': 3,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'mentionUserIds'
    },
    {'1': 'nonce', '3': 8, '4': 1, '5': 9, '10': 'nonce'},
  ],
};

/// Descriptor for `PrivateMessageSend`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List privateMessageSendDescriptor = $convert.base64Decode(
    'ChJQcml2YXRlTWVzc2FnZVNlbmQSPQoOdGFyZ2V0X3VzZXJfaWQYASABKAsyFy5zcGFya2xlLm'
    'NvbW11bml0eS5VVUlEUgx0YXJnZXRVc2VySWQSQQoMbWVzc2FnZV90eXBlGAIgASgOMh4uc3Bh'
    'cmtsZS5jb21tdW5pdHkuTWVzc2FnZVR5cGVSC21lc3NhZ2VUeXBlEhgKB2NvbnRlbnQYAyABKA'
    'lSB2NvbnRlbnQSIQoMY29udGVudF9kYXRhGAQgASgJUgtjb250ZW50RGF0YRI3CgtyZXBseV90'
    'b19pZBgFIAEoCzIXLnNwYXJrbGUuY29tbXVuaXR5LlVVSURSCXJlcGx5VG9JZBI9Cg50aHJlYW'
    'Rfcm9vdF9pZBgGIAEoCzIXLnNwYXJrbGUuY29tbXVuaXR5LlVVSURSDHRocmVhZFJvb3RJZBJB'
    'ChBtZW50aW9uX3VzZXJfaWRzGAcgAygLMhcuc3BhcmtsZS5jb21tdW5pdHkuVVVJRFIObWVudG'
    'lvblVzZXJJZHMSFAoFbm9uY2UYCCABKAlSBW5vbmNl');

@$core.Deprecated('Use privateMessageInfoDescriptor instead')
const PrivateMessageInfo$json = {
  '1': 'PrivateMessageInfo',
  '2': [
    {
      '1': 'id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'id'
    },
    {
      '1': 'sender',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UserBrief',
      '10': 'sender'
    },
    {
      '1': 'receiver',
      '3': 3,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UserBrief',
      '10': 'receiver'
    },
    {
      '1': 'message_type',
      '3': 4,
      '4': 1,
      '5': 14,
      '6': '.sparkle.community.MessageType',
      '10': 'messageType'
    },
    {'1': 'content', '3': 5, '4': 1, '5': 9, '10': 'content'},
    {'1': 'content_data', '3': 6, '4': 1, '5': 9, '10': 'contentData'},
    {
      '1': 'reply_to_id',
      '3': 7,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'replyToId'
    },
    {
      '1': 'thread_root_id',
      '3': 8,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'threadRootId'
    },
    {
      '1': 'mention_user_ids',
      '3': 9,
      '4': 3,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'mentionUserIds'
    },
    {
      '1': 'reactions',
      '3': 10,
      '4': 3,
      '5': 11,
      '6': '.sparkle.community.PrivateMessageInfo.ReactionsEntry',
      '10': 'reactions'
    },
    {'1': 'is_revoked', '3': 11, '4': 1, '5': 8, '10': 'isRevoked'},
    {
      '1': 'revoked_at',
      '3': 12,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'revokedAt'
    },
    {
      '1': 'edited_at',
      '3': 13,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'editedAt'
    },
    {'1': 'is_read', '3': 14, '4': 1, '5': 8, '10': 'isRead'},
    {
      '1': 'read_at',
      '3': 15,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'readAt'
    },
    {
      '1': 'created_at',
      '3': 16,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'createdAt'
    },
  ],
  '3': [PrivateMessageInfo_ReactionsEntry$json],
};

@$core.Deprecated('Use privateMessageInfoDescriptor instead')
const PrivateMessageInfo_ReactionsEntry$json = {
  '1': 'ReactionsEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `PrivateMessageInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List privateMessageInfoDescriptor = $convert.base64Decode(
    'ChJQcml2YXRlTWVzc2FnZUluZm8SJwoCaWQYASABKAsyFy5zcGFya2xlLmNvbW11bml0eS5VVU'
    'lEUgJpZBI0CgZzZW5kZXIYAiABKAsyHC5zcGFya2xlLmNvbW11bml0eS5Vc2VyQnJpZWZSBnNl'
    'bmRlchI4CghyZWNlaXZlchgDIAEoCzIcLnNwYXJrbGUuY29tbXVuaXR5LlVzZXJCcmllZlIIcm'
    'VjZWl2ZXISQQoMbWVzc2FnZV90eXBlGAQgASgOMh4uc3BhcmtsZS5jb21tdW5pdHkuTWVzc2Fn'
    'ZVR5cGVSC21lc3NhZ2VUeXBlEhgKB2NvbnRlbnQYBSABKAlSB2NvbnRlbnQSIQoMY29udGVudF'
    '9kYXRhGAYgASgJUgtjb250ZW50RGF0YRI3CgtyZXBseV90b19pZBgHIAEoCzIXLnNwYXJrbGUu'
    'Y29tbXVuaXR5LlVVSURSCXJlcGx5VG9JZBI9Cg50aHJlYWRfcm9vdF9pZBgIIAEoCzIXLnNwYX'
    'JrbGUuY29tbXVuaXR5LlVVSURSDHRocmVhZFJvb3RJZBJBChBtZW50aW9uX3VzZXJfaWRzGAkg'
    'AygLMhcuc3BhcmtsZS5jb21tdW5pdHkuVVVJRFIObWVudGlvblVzZXJJZHMSUgoJcmVhY3Rpb2'
    '5zGAogAygLMjQuc3BhcmtsZS5jb21tdW5pdHkuUHJpdmF0ZU1lc3NhZ2VJbmZvLlJlYWN0aW9u'
    'c0VudHJ5UglyZWFjdGlvbnMSHQoKaXNfcmV2b2tlZBgLIAEoCFIJaXNSZXZva2VkEjkKCnJldm'
    '9rZWRfYXQYDCABKAsyGi5nb29nbGUucHJvdG9idWYuVGltZXN0YW1wUglyZXZva2VkQXQSNwoJ'
    'ZWRpdGVkX2F0GA0gASgLMhouZ29vZ2xlLnByb3RvYnVmLlRpbWVzdGFtcFIIZWRpdGVkQXQSFw'
    'oHaXNfcmVhZBgOIAEoCFIGaXNSZWFkEjMKB3JlYWRfYXQYDyABKAsyGi5nb29nbGUucHJvdG9i'
    'dWYuVGltZXN0YW1wUgZyZWFkQXQSOQoKY3JlYXRlZF9hdBgQIAEoCzIaLmdvb2dsZS5wcm90b2'
    'J1Zi5UaW1lc3RhbXBSCWNyZWF0ZWRBdBo8Cg5SZWFjdGlvbnNFbnRyeRIQCgNrZXkYASABKAlS'
    'A2tleRIUCgV2YWx1ZRgCIAEoCVIFdmFsdWU6AjgB');

@$core.Deprecated('Use checkinRequestDescriptor instead')
const CheckinRequest$json = {
  '1': 'CheckinRequest',
  '2': [
    {
      '1': 'group_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'groupId'
    },
    {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
    {
      '1': 'today_duration_minutes',
      '3': 3,
      '4': 1,
      '5': 5,
      '10': 'todayDurationMinutes'
    },
  ],
};

/// Descriptor for `CheckinRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List checkinRequestDescriptor = $convert.base64Decode(
    'Cg5DaGVja2luUmVxdWVzdBIyCghncm91cF9pZBgBIAEoCzIXLnNwYXJrbGUuY29tbXVuaXR5Ll'
    'VVSURSB2dyb3VwSWQSGAoHbWVzc2FnZRgCIAEoCVIHbWVzc2FnZRI0ChZ0b2RheV9kdXJhdGlv'
    'bl9taW51dGVzGAMgASgFUhR0b2RheUR1cmF0aW9uTWludXRlcw==');

@$core.Deprecated('Use checkinResponseDescriptor instead')
const CheckinResponse$json = {
  '1': 'CheckinResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'new_streak', '3': 2, '4': 1, '5': 5, '10': 'newStreak'},
    {'1': 'flame_earned', '3': 3, '4': 1, '5': 5, '10': 'flameEarned'},
    {'1': 'rank_in_group', '3': 4, '4': 1, '5': 5, '10': 'rankInGroup'},
    {
      '1': 'group_checkin_count',
      '3': 5,
      '4': 1,
      '5': 5,
      '10': 'groupCheckinCount'
    },
  ],
};

/// Descriptor for `CheckinResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List checkinResponseDescriptor = $convert.base64Decode(
    'Cg9DaGVja2luUmVzcG9uc2USGAoHc3VjY2VzcxgBIAEoCFIHc3VjY2VzcxIdCgpuZXdfc3RyZW'
    'FrGAIgASgFUgluZXdTdHJlYWsSIQoMZmxhbWVfZWFybmVkGAMgASgFUgtmbGFtZUVhcm5lZBIi'
    'Cg1yYW5rX2luX2dyb3VwGAQgASgFUgtyYW5rSW5Hcm91cBIuChNncm91cF9jaGVja2luX2NvdW'
    '50GAUgASgFUhFncm91cENoZWNraW5Db3VudA==');

@$core.Deprecated('Use userPrivacySettingsDescriptor instead')
const UserPrivacySettings$json = {
  '1': 'UserPrivacySettings',
  '2': [
    {
      '1': 'searchable_by',
      '3': 1,
      '4': 1,
      '5': 14,
      '6': '.sparkle.community.SearchVisibility',
      '10': 'searchableBy'
    },
  ],
};

/// Descriptor for `UserPrivacySettings`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List userPrivacySettingsDescriptor = $convert.base64Decode(
    'ChNVc2VyUHJpdmFjeVNldHRpbmdzEkgKDXNlYXJjaGFibGVfYnkYASABKA4yIy5zcGFya2xlLm'
    'NvbW11bml0eS5TZWFyY2hWaXNpYmlsaXR5UgxzZWFyY2hhYmxlQnk=');

@$core.Deprecated('Use searchUsersRequestDescriptor instead')
const SearchUsersRequest$json = {
  '1': 'SearchUsersRequest',
  '2': [
    {'1': 'keyword', '3': 1, '4': 1, '5': 9, '10': 'keyword'},
    {'1': 'limit', '3': 2, '4': 1, '5': 5, '10': 'limit'},
  ],
};

/// Descriptor for `SearchUsersRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List searchUsersRequestDescriptor = $convert.base64Decode(
    'ChJTZWFyY2hVc2Vyc1JlcXVlc3QSGAoHa2V5d29yZBgBIAEoCVIHa2V5d29yZBIUCgVsaW1pdB'
    'gCIAEoBVIFbGltaXQ=');

@$core.Deprecated('Use searchGroupsRequestDescriptor instead')
const SearchGroupsRequest$json = {
  '1': 'SearchGroupsRequest',
  '2': [
    {'1': 'keyword', '3': 1, '4': 1, '5': 9, '10': 'keyword'},
    {
      '1': 'type',
      '3': 2,
      '4': 1,
      '5': 14,
      '6': '.sparkle.community.GroupType',
      '10': 'type'
    },
    {'1': 'limit', '3': 3, '4': 1, '5': 5, '10': 'limit'},
  ],
};

/// Descriptor for `SearchGroupsRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List searchGroupsRequestDescriptor = $convert.base64Decode(
    'ChNTZWFyY2hHcm91cHNSZXF1ZXN0EhgKB2tleXdvcmQYASABKAlSB2tleXdvcmQSMAoEdHlwZR'
    'gCIAEoDjIcLnNwYXJrbGUuY29tbXVuaXR5Lkdyb3VwVHlwZVIEdHlwZRIUCgVsaW1pdBgDIAEo'
    'BVIFbGltaXQ=');

@$core.Deprecated('Use joinGroupRequestDescriptor instead')
const JoinGroupRequest$json = {
  '1': 'JoinGroupRequest',
  '2': [
    {
      '1': 'group_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'groupId'
    },
    {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
  ],
};

/// Descriptor for `JoinGroupRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List joinGroupRequestDescriptor = $convert.base64Decode(
    'ChBKb2luR3JvdXBSZXF1ZXN0EjIKCGdyb3VwX2lkGAEgASgLMhcuc3BhcmtsZS5jb21tdW5pdH'
    'kuVVVJRFIHZ3JvdXBJZBIYCgdtZXNzYWdlGAIgASgJUgdtZXNzYWdl');

@$core.Deprecated('Use sendGroupMessageRequestDescriptor instead')
const SendGroupMessageRequest$json = {
  '1': 'SendGroupMessageRequest',
  '2': [
    {
      '1': 'group_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'groupId'
    },
    {
      '1': 'message',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.MessageSend',
      '10': 'message'
    },
  ],
};

/// Descriptor for `SendGroupMessageRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List sendGroupMessageRequestDescriptor = $convert.base64Decode(
    'ChdTZW5kR3JvdXBNZXNzYWdlUmVxdWVzdBIyCghncm91cF9pZBgBIAEoCzIXLnNwYXJrbGUuY2'
    '9tbXVuaXR5LlVVSURSB2dyb3VwSWQSOAoHbWVzc2FnZRgCIAEoCzIeLnNwYXJrbGUuY29tbXVu'
    'aXR5Lk1lc3NhZ2VTZW5kUgdtZXNzYWdl');

@$core.Deprecated('Use getGroupMessagesRequestDescriptor instead')
const GetGroupMessagesRequest$json = {
  '1': 'GetGroupMessagesRequest',
  '2': [
    {
      '1': 'group_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'groupId'
    },
    {
      '1': 'before_id',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'beforeId'
    },
    {'1': 'limit', '3': 3, '4': 1, '5': 5, '10': 'limit'},
  ],
};

/// Descriptor for `GetGroupMessagesRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List getGroupMessagesRequestDescriptor = $convert.base64Decode(
    'ChdHZXRHcm91cE1lc3NhZ2VzUmVxdWVzdBIyCghncm91cF9pZBgBIAEoCzIXLnNwYXJrbGUuY2'
    '9tbXVuaXR5LlVVSURSB2dyb3VwSWQSNAoJYmVmb3JlX2lkGAIgASgLMhcuc3BhcmtsZS5jb21t'
    'dW5pdHkuVVVJRFIIYmVmb3JlSWQSFAoFbGltaXQYAyABKAVSBWxpbWl0');

@$core.Deprecated('Use streamGroupMessagesRequestDescriptor instead')
const StreamGroupMessagesRequest$json = {
  '1': 'StreamGroupMessagesRequest',
  '2': [
    {
      '1': 'group_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'groupId'
    },
    {
      '1': 'after_id',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'afterId'
    },
  ],
};

/// Descriptor for `StreamGroupMessagesRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List streamGroupMessagesRequestDescriptor =
    $convert.base64Decode(
        'ChpTdHJlYW1Hcm91cE1lc3NhZ2VzUmVxdWVzdBIyCghncm91cF9pZBgBIAEoCzIXLnNwYXJrbG'
        'UuY29tbXVuaXR5LlVVSURSB2dyb3VwSWQSMgoIYWZ0ZXJfaWQYAiABKAsyFy5zcGFya2xlLmNv'
        'bW11bml0eS5VVUlEUgdhZnRlcklk');

@$core.Deprecated('Use revokeMessageRequestDescriptor instead')
const RevokeMessageRequest$json = {
  '1': 'RevokeMessageRequest',
  '2': [
    {
      '1': 'message_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'messageId'
    },
    {
      '1': 'group_id',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'groupId'
    },
  ],
};

/// Descriptor for `RevokeMessageRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List revokeMessageRequestDescriptor = $convert.base64Decode(
    'ChRSZXZva2VNZXNzYWdlUmVxdWVzdBI2CgptZXNzYWdlX2lkGAEgASgLMhcuc3BhcmtsZS5jb2'
    '1tdW5pdHkuVVVJRFIJbWVzc2FnZUlkEjIKCGdyb3VwX2lkGAIgASgLMhcuc3BhcmtsZS5jb21t'
    'dW5pdHkuVVVJRFIHZ3JvdXBJZA==');

@$core.Deprecated('Use markMessagesReadRequestDescriptor instead')
const MarkMessagesReadRequest$json = {
  '1': 'MarkMessagesReadRequest',
  '2': [
    {
      '1': 'group_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'groupId'
    },
    {
      '1': 'up_to_message_id',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'upToMessageId'
    },
  ],
};

/// Descriptor for `MarkMessagesReadRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List markMessagesReadRequestDescriptor = $convert.base64Decode(
    'ChdNYXJrTWVzc2FnZXNSZWFkUmVxdWVzdBIyCghncm91cF9pZBgBIAEoCzIXLnNwYXJrbGUuY2'
    '9tbXVuaXR5LlVVSURSB2dyb3VwSWQSQAoQdXBfdG9fbWVzc2FnZV9pZBgCIAEoCzIXLnNwYXJr'
    'bGUuY29tbXVuaXR5LlVVSURSDXVwVG9NZXNzYWdlSWQ=');

@$core.Deprecated('Use markMessagesReadResponseDescriptor instead')
const MarkMessagesReadResponse$json = {
  '1': 'MarkMessagesReadResponse',
  '2': [
    {'1': 'updated_count', '3': 1, '4': 1, '5': 5, '10': 'updatedCount'},
    {
      '1': 'up_to_message_id',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'upToMessageId'
    },
  ],
};

/// Descriptor for `MarkMessagesReadResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List markMessagesReadResponseDescriptor = $convert.base64Decode(
    'ChhNYXJrTWVzc2FnZXNSZWFkUmVzcG9uc2USIwoNdXBkYXRlZF9jb3VudBgBIAEoBVIMdXBkYX'
    'RlZENvdW50EkAKEHVwX3RvX21lc3NhZ2VfaWQYAiABKAsyFy5zcGFya2xlLmNvbW11bml0eS5V'
    'VUlEUg11cFRvTWVzc2FnZUlk');

@$core.Deprecated('Use getPrivateMessagesRequestDescriptor instead')
const GetPrivateMessagesRequest$json = {
  '1': 'GetPrivateMessagesRequest',
  '2': [
    {
      '1': 'friend_id',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'friendId'
    },
    {
      '1': 'before_id',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.sparkle.community.UUID',
      '10': 'beforeId'
    },
    {'1': 'limit', '3': 3, '4': 1, '5': 5, '10': 'limit'},
  ],
};

/// Descriptor for `GetPrivateMessagesRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List getPrivateMessagesRequestDescriptor = $convert.base64Decode(
    'ChlHZXRQcml2YXRlTWVzc2FnZXNSZXF1ZXN0EjQKCWZyaWVuZF9pZBgBIAEoCzIXLnNwYXJrbG'
    'UuY29tbXVuaXR5LlVVSURSCGZyaWVuZElkEjQKCWJlZm9yZV9pZBgCIAEoCzIXLnNwYXJrbGUu'
    'Y29tbXVuaXR5LlVVSURSCGJlZm9yZUlkEhQKBWxpbWl0GAMgASgFUgVsaW1pdA==');
