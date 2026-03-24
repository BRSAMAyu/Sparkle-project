// This is a generated file - do not edit.
//
// Generated from community_service.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

class FriendshipStatus extends $pb.ProtobufEnum {
  static const FriendshipStatus FRIENDSHIP_STATUS_UNSPECIFIED =
      FriendshipStatus._(
          0, _omitEnumNames ? '' : 'FRIENDSHIP_STATUS_UNSPECIFIED');
  static const FriendshipStatus PENDING =
      FriendshipStatus._(1, _omitEnumNames ? '' : 'PENDING');
  static const FriendshipStatus ACCEPTED =
      FriendshipStatus._(2, _omitEnumNames ? '' : 'ACCEPTED');
  static const FriendshipStatus BLOCKED =
      FriendshipStatus._(3, _omitEnumNames ? '' : 'BLOCKED');

  static const $core.List<FriendshipStatus> values = <FriendshipStatus>[
    FRIENDSHIP_STATUS_UNSPECIFIED,
    PENDING,
    ACCEPTED,
    BLOCKED,
  ];

  static final $core.List<FriendshipStatus?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 3);
  static FriendshipStatus? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const FriendshipStatus._(super.value, super.name);
}

class GroupType extends $pb.ProtobufEnum {
  static const GroupType GROUP_TYPE_UNSPECIFIED =
      GroupType._(0, _omitEnumNames ? '' : 'GROUP_TYPE_UNSPECIFIED');
  static const GroupType SQUAD = GroupType._(1, _omitEnumNames ? '' : 'SQUAD');
  static const GroupType SPRINT =
      GroupType._(2, _omitEnumNames ? '' : 'SPRINT');
  static const GroupType OFFICIAL =
      GroupType._(3, _omitEnumNames ? '' : 'OFFICIAL');

  static const $core.List<GroupType> values = <GroupType>[
    GROUP_TYPE_UNSPECIFIED,
    SQUAD,
    SPRINT,
    OFFICIAL,
  ];

  static final $core.List<GroupType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 3);
  static GroupType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const GroupType._(super.value, super.name);
}

class GroupRole extends $pb.ProtobufEnum {
  static const GroupRole GROUP_ROLE_UNSPECIFIED =
      GroupRole._(0, _omitEnumNames ? '' : 'GROUP_ROLE_UNSPECIFIED');
  static const GroupRole OWNER = GroupRole._(1, _omitEnumNames ? '' : 'OWNER');
  static const GroupRole ADMIN = GroupRole._(2, _omitEnumNames ? '' : 'ADMIN');
  static const GroupRole MEMBER =
      GroupRole._(3, _omitEnumNames ? '' : 'MEMBER');

  static const $core.List<GroupRole> values = <GroupRole>[
    GROUP_ROLE_UNSPECIFIED,
    OWNER,
    ADMIN,
    MEMBER,
  ];

  static final $core.List<GroupRole?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 3);
  static GroupRole? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const GroupRole._(super.value, super.name);
}

class MessageType extends $pb.ProtobufEnum {
  static const MessageType MESSAGE_TYPE_UNSPECIFIED =
      MessageType._(0, _omitEnumNames ? '' : 'MESSAGE_TYPE_UNSPECIFIED');
  static const MessageType TEXT =
      MessageType._(1, _omitEnumNames ? '' : 'TEXT');
  static const MessageType TASK_SHARE =
      MessageType._(2, _omitEnumNames ? '' : 'TASK_SHARE');
  static const MessageType PLAN_SHARE =
      MessageType._(3, _omitEnumNames ? '' : 'PLAN_SHARE');
  static const MessageType FRAGMENT_SHARE =
      MessageType._(4, _omitEnumNames ? '' : 'FRAGMENT_SHARE');
  static const MessageType CAPSULE_SHARE =
      MessageType._(5, _omitEnumNames ? '' : 'CAPSULE_SHARE');
  static const MessageType PRISM_SHARE =
      MessageType._(6, _omitEnumNames ? '' : 'PRISM_SHARE');
  static const MessageType FILE_SHARE =
      MessageType._(7, _omitEnumNames ? '' : 'FILE_SHARE');
  static const MessageType PROGRESS =
      MessageType._(8, _omitEnumNames ? '' : 'PROGRESS');
  static const MessageType ACHIEVEMENT =
      MessageType._(9, _omitEnumNames ? '' : 'ACHIEVEMENT');
  static const MessageType CHECKIN =
      MessageType._(10, _omitEnumNames ? '' : 'CHECKIN');
  static const MessageType SYSTEM =
      MessageType._(11, _omitEnumNames ? '' : 'SYSTEM');
  static const MessageType BROADCAST =
      MessageType._(12, _omitEnumNames ? '' : 'BROADCAST');

  static const $core.List<MessageType> values = <MessageType>[
    MESSAGE_TYPE_UNSPECIFIED,
    TEXT,
    TASK_SHARE,
    PLAN_SHARE,
    FRAGMENT_SHARE,
    CAPSULE_SHARE,
    PRISM_SHARE,
    FILE_SHARE,
    PROGRESS,
    ACHIEVEMENT,
    CHECKIN,
    SYSTEM,
    BROADCAST,
  ];

  static final $core.List<MessageType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 12);
  static MessageType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const MessageType._(super.value, super.name);
}

class SearchVisibility extends $pb.ProtobufEnum {
  static const SearchVisibility SEARCH_VISIBILITY_UNSPECIFIED =
      SearchVisibility._(
          0, _omitEnumNames ? '' : 'SEARCH_VISIBILITY_UNSPECIFIED');
  static const SearchVisibility EVERYONE =
      SearchVisibility._(1, _omitEnumNames ? '' : 'EVERYONE');
  static const SearchVisibility FRIENDS =
      SearchVisibility._(2, _omitEnumNames ? '' : 'FRIENDS');
  static const SearchVisibility NOBODY =
      SearchVisibility._(3, _omitEnumNames ? '' : 'NOBODY');

  static const $core.List<SearchVisibility> values = <SearchVisibility>[
    SEARCH_VISIBILITY_UNSPECIFIED,
    EVERYONE,
    FRIENDS,
    NOBODY,
  ];

  static final $core.List<SearchVisibility?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 3);
  static SearchVisibility? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const SearchVisibility._(super.value, super.name);
}

const $core.bool _omitEnumNames =
    $core.bool.fromEnvironment('protobuf.omit_enum_names');
