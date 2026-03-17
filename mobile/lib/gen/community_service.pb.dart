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
import 'package:protobuf/well_known_types/google/protobuf/timestamp.pb.dart'
    as $2;

import 'community_service.pbenum.dart';

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

export 'community_service.pbenum.dart';

class UUID extends $pb.GeneratedMessage {
  factory UUID({
    $core.String? value,
  }) {
    final result = create();
    if (value != null) result.value = value;
    return result;
  }

  UUID._();

  factory UUID.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory UUID.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'UUID',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'value')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UUID clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UUID copyWith(void Function(UUID) updates) =>
      super.copyWith((message) => updates(message as UUID)) as UUID;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UUID create() => UUID._();
  @$core.override
  UUID createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static UUID getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<UUID>(create);
  static UUID? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get value => $_getSZ(0);
  @$pb.TagNumber(1)
  set value($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasValue() => $_has(0);
  @$pb.TagNumber(1)
  void clearValue() => $_clearField(1);
}

class UserBrief extends $pb.GeneratedMessage {
  factory UserBrief({
    UUID? id,
    $core.String? username,
    $core.String? nickname,
    $core.String? avatarUrl,
    $core.int? flameLevel,
    $core.double? flameBrightness,
    $core.String? status,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (username != null) result.username = username;
    if (nickname != null) result.nickname = nickname;
    if (avatarUrl != null) result.avatarUrl = avatarUrl;
    if (flameLevel != null) result.flameLevel = flameLevel;
    if (flameBrightness != null) result.flameBrightness = flameBrightness;
    if (status != null) result.status = status;
    return result;
  }

  UserBrief._();

  factory UserBrief.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory UserBrief.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'UserBrief',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'id', subBuilder: UUID.create)
    ..aOS(2, _omitFieldNames ? '' : 'username')
    ..aOS(3, _omitFieldNames ? '' : 'nickname')
    ..aOS(4, _omitFieldNames ? '' : 'avatarUrl')
    ..aI(5, _omitFieldNames ? '' : 'flameLevel')
    ..aD(6, _omitFieldNames ? '' : 'flameBrightness',
        fieldType: $pb.PbFieldType.OF)
    ..aOS(7, _omitFieldNames ? '' : 'status')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UserBrief clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UserBrief copyWith(void Function(UserBrief) updates) =>
      super.copyWith((message) => updates(message as UserBrief)) as UserBrief;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UserBrief create() => UserBrief._();
  @$core.override
  UserBrief createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static UserBrief getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<UserBrief>(create);
  static UserBrief? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get id => $_getN(0);
  @$pb.TagNumber(1)
  set id(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureId() => $_ensure(0);

  @$pb.TagNumber(2)
  $core.String get username => $_getSZ(1);
  @$pb.TagNumber(2)
  set username($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasUsername() => $_has(1);
  @$pb.TagNumber(2)
  void clearUsername() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get nickname => $_getSZ(2);
  @$pb.TagNumber(3)
  set nickname($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasNickname() => $_has(2);
  @$pb.TagNumber(3)
  void clearNickname() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get avatarUrl => $_getSZ(3);
  @$pb.TagNumber(4)
  set avatarUrl($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasAvatarUrl() => $_has(3);
  @$pb.TagNumber(4)
  void clearAvatarUrl() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.int get flameLevel => $_getIZ(4);
  @$pb.TagNumber(5)
  set flameLevel($core.int value) => $_setSignedInt32(4, value);
  @$pb.TagNumber(5)
  $core.bool hasFlameLevel() => $_has(4);
  @$pb.TagNumber(5)
  void clearFlameLevel() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.double get flameBrightness => $_getN(5);
  @$pb.TagNumber(6)
  set flameBrightness($core.double value) => $_setFloat(5, value);
  @$pb.TagNumber(6)
  $core.bool hasFlameBrightness() => $_has(5);
  @$pb.TagNumber(6)
  void clearFlameBrightness() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.String get status => $_getSZ(6);
  @$pb.TagNumber(7)
  set status($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasStatus() => $_has(6);
  @$pb.TagNumber(7)
  void clearStatus() => $_clearField(7);
}

class FriendRequest extends $pb.GeneratedMessage {
  factory FriendRequest({
    UUID? targetUserId,
    $core.String? message,
  }) {
    final result = create();
    if (targetUserId != null) result.targetUserId = targetUserId;
    if (message != null) result.message = message;
    return result;
  }

  FriendRequest._();

  factory FriendRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory FriendRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'FriendRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'targetUserId',
        subBuilder: UUID.create)
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  FriendRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  FriendRequest copyWith(void Function(FriendRequest) updates) =>
      super.copyWith((message) => updates(message as FriendRequest))
          as FriendRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static FriendRequest create() => FriendRequest._();
  @$core.override
  FriendRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static FriendRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<FriendRequest>(create);
  static FriendRequest? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get targetUserId => $_getN(0);
  @$pb.TagNumber(1)
  set targetUserId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasTargetUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearTargetUserId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureTargetUserId() => $_ensure(0);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => $_clearField(2);
}

class FriendResponse extends $pb.GeneratedMessage {
  factory FriendResponse({
    UUID? friendshipId,
    $core.bool? accept,
  }) {
    final result = create();
    if (friendshipId != null) result.friendshipId = friendshipId;
    if (accept != null) result.accept = accept;
    return result;
  }

  FriendResponse._();

  factory FriendResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory FriendResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'FriendResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'friendshipId',
        subBuilder: UUID.create)
    ..aOB(2, _omitFieldNames ? '' : 'accept')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  FriendResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  FriendResponse copyWith(void Function(FriendResponse) updates) =>
      super.copyWith((message) => updates(message as FriendResponse))
          as FriendResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static FriendResponse create() => FriendResponse._();
  @$core.override
  FriendResponse createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static FriendResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<FriendResponse>(create);
  static FriendResponse? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get friendshipId => $_getN(0);
  @$pb.TagNumber(1)
  set friendshipId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasFriendshipId() => $_has(0);
  @$pb.TagNumber(1)
  void clearFriendshipId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureFriendshipId() => $_ensure(0);

  @$pb.TagNumber(2)
  $core.bool get accept => $_getBF(1);
  @$pb.TagNumber(2)
  set accept($core.bool value) => $_setBool(1, value);
  @$pb.TagNumber(2)
  $core.bool hasAccept() => $_has(1);
  @$pb.TagNumber(2)
  void clearAccept() => $_clearField(2);
}

class FriendshipInfo extends $pb.GeneratedMessage {
  factory FriendshipInfo({
    UserBrief? friend,
    FriendshipStatus? status,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? matchReason,
    $core.bool? initiatedByMe,
  }) {
    final result = create();
    if (friend != null) result.friend = friend;
    if (status != null) result.status = status;
    if (matchReason != null) result.matchReason.addEntries(matchReason);
    if (initiatedByMe != null) result.initiatedByMe = initiatedByMe;
    return result;
  }

  FriendshipInfo._();

  factory FriendshipInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory FriendshipInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'FriendshipInfo',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UserBrief>(1, _omitFieldNames ? '' : 'friend',
        subBuilder: UserBrief.create)
    ..aE<FriendshipStatus>(2, _omitFieldNames ? '' : 'status',
        enumValues: FriendshipStatus.values)
    ..m<$core.String, $core.String>(3, _omitFieldNames ? '' : 'matchReason',
        entryClassName: 'FriendshipInfo.MatchReasonEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('sparkle.community'))
    ..aOB(4, _omitFieldNames ? '' : 'initiatedByMe')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  FriendshipInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  FriendshipInfo copyWith(void Function(FriendshipInfo) updates) =>
      super.copyWith((message) => updates(message as FriendshipInfo))
          as FriendshipInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static FriendshipInfo create() => FriendshipInfo._();
  @$core.override
  FriendshipInfo createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static FriendshipInfo getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<FriendshipInfo>(create);
  static FriendshipInfo? _defaultInstance;

  @$pb.TagNumber(1)
  UserBrief get friend => $_getN(0);
  @$pb.TagNumber(1)
  set friend(UserBrief value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasFriend() => $_has(0);
  @$pb.TagNumber(1)
  void clearFriend() => $_clearField(1);
  @$pb.TagNumber(1)
  UserBrief ensureFriend() => $_ensure(0);

  @$pb.TagNumber(2)
  FriendshipStatus get status => $_getN(1);
  @$pb.TagNumber(2)
  set status(FriendshipStatus value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasStatus() => $_has(1);
  @$pb.TagNumber(2)
  void clearStatus() => $_clearField(2);

  @$pb.TagNumber(3)
  $pb.PbMap<$core.String, $core.String> get matchReason => $_getMap(2);

  @$pb.TagNumber(4)
  $core.bool get initiatedByMe => $_getBF(3);
  @$pb.TagNumber(4)
  set initiatedByMe($core.bool value) => $_setBool(3, value);
  @$pb.TagNumber(4)
  $core.bool hasInitiatedByMe() => $_has(3);
  @$pb.TagNumber(4)
  void clearInitiatedByMe() => $_clearField(4);
}

class BlockUserRequest extends $pb.GeneratedMessage {
  factory BlockUserRequest({
    UUID? targetUserId,
    $core.String? reason,
  }) {
    final result = create();
    if (targetUserId != null) result.targetUserId = targetUserId;
    if (reason != null) result.reason = reason;
    return result;
  }

  BlockUserRequest._();

  factory BlockUserRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory BlockUserRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'BlockUserRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'targetUserId',
        subBuilder: UUID.create)
    ..aOS(2, _omitFieldNames ? '' : 'reason')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockUserRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockUserRequest copyWith(void Function(BlockUserRequest) updates) =>
      super.copyWith((message) => updates(message as BlockUserRequest))
          as BlockUserRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static BlockUserRequest create() => BlockUserRequest._();
  @$core.override
  BlockUserRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static BlockUserRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<BlockUserRequest>(create);
  static BlockUserRequest? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get targetUserId => $_getN(0);
  @$pb.TagNumber(1)
  set targetUserId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasTargetUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearTargetUserId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureTargetUserId() => $_ensure(0);

  @$pb.TagNumber(2)
  $core.String get reason => $_getSZ(1);
  @$pb.TagNumber(2)
  set reason($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasReason() => $_has(1);
  @$pb.TagNumber(2)
  void clearReason() => $_clearField(2);
}

class BlockUserInfo extends $pb.GeneratedMessage {
  factory BlockUserInfo({
    UserBrief? blockedUser,
    $core.String? reason,
    $2.Timestamp? createdAt,
  }) {
    final result = create();
    if (blockedUser != null) result.blockedUser = blockedUser;
    if (reason != null) result.reason = reason;
    if (createdAt != null) result.createdAt = createdAt;
    return result;
  }

  BlockUserInfo._();

  factory BlockUserInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory BlockUserInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'BlockUserInfo',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UserBrief>(1, _omitFieldNames ? '' : 'blockedUser',
        subBuilder: UserBrief.create)
    ..aOS(2, _omitFieldNames ? '' : 'reason')
    ..aOM<$2.Timestamp>(3, _omitFieldNames ? '' : 'createdAt',
        subBuilder: $2.Timestamp.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockUserInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockUserInfo copyWith(void Function(BlockUserInfo) updates) =>
      super.copyWith((message) => updates(message as BlockUserInfo))
          as BlockUserInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static BlockUserInfo create() => BlockUserInfo._();
  @$core.override
  BlockUserInfo createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static BlockUserInfo getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<BlockUserInfo>(create);
  static BlockUserInfo? _defaultInstance;

  @$pb.TagNumber(1)
  UserBrief get blockedUser => $_getN(0);
  @$pb.TagNumber(1)
  set blockedUser(UserBrief value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasBlockedUser() => $_has(0);
  @$pb.TagNumber(1)
  void clearBlockedUser() => $_clearField(1);
  @$pb.TagNumber(1)
  UserBrief ensureBlockedUser() => $_ensure(0);

  @$pb.TagNumber(2)
  $core.String get reason => $_getSZ(1);
  @$pb.TagNumber(2)
  set reason($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasReason() => $_has(1);
  @$pb.TagNumber(2)
  void clearReason() => $_clearField(2);

  @$pb.TagNumber(3)
  $2.Timestamp get createdAt => $_getN(2);
  @$pb.TagNumber(3)
  set createdAt($2.Timestamp value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasCreatedAt() => $_has(2);
  @$pb.TagNumber(3)
  void clearCreatedAt() => $_clearField(3);
  @$pb.TagNumber(3)
  $2.Timestamp ensureCreatedAt() => $_ensure(2);
}

class GroupCreate extends $pb.GeneratedMessage {
  factory GroupCreate({
    $core.String? name,
    $core.String? description,
    GroupType? type,
    $core.Iterable<$core.String>? focusTags,
    $2.Timestamp? deadline,
    $core.String? sprintGoal,
    $core.int? maxMembers,
    $core.bool? isPublic,
    $core.bool? joinRequiresApproval,
  }) {
    final result = create();
    if (name != null) result.name = name;
    if (description != null) result.description = description;
    if (type != null) result.type = type;
    if (focusTags != null) result.focusTags.addAll(focusTags);
    if (deadline != null) result.deadline = deadline;
    if (sprintGoal != null) result.sprintGoal = sprintGoal;
    if (maxMembers != null) result.maxMembers = maxMembers;
    if (isPublic != null) result.isPublic = isPublic;
    if (joinRequiresApproval != null)
      result.joinRequiresApproval = joinRequiresApproval;
    return result;
  }

  GroupCreate._();

  factory GroupCreate.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory GroupCreate.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'GroupCreate',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'name')
    ..aOS(2, _omitFieldNames ? '' : 'description')
    ..aE<GroupType>(3, _omitFieldNames ? '' : 'type',
        enumValues: GroupType.values)
    ..pPS(4, _omitFieldNames ? '' : 'focusTags')
    ..aOM<$2.Timestamp>(5, _omitFieldNames ? '' : 'deadline',
        subBuilder: $2.Timestamp.create)
    ..aOS(6, _omitFieldNames ? '' : 'sprintGoal')
    ..aI(7, _omitFieldNames ? '' : 'maxMembers')
    ..aOB(8, _omitFieldNames ? '' : 'isPublic')
    ..aOB(9, _omitFieldNames ? '' : 'joinRequiresApproval')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GroupCreate clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GroupCreate copyWith(void Function(GroupCreate) updates) =>
      super.copyWith((message) => updates(message as GroupCreate))
          as GroupCreate;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GroupCreate create() => GroupCreate._();
  @$core.override
  GroupCreate createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static GroupCreate getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<GroupCreate>(create);
  static GroupCreate? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get name => $_getSZ(0);
  @$pb.TagNumber(1)
  set name($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasName() => $_has(0);
  @$pb.TagNumber(1)
  void clearName() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get description => $_getSZ(1);
  @$pb.TagNumber(2)
  set description($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasDescription() => $_has(1);
  @$pb.TagNumber(2)
  void clearDescription() => $_clearField(2);

  @$pb.TagNumber(3)
  GroupType get type => $_getN(2);
  @$pb.TagNumber(3)
  set type(GroupType value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasType() => $_has(2);
  @$pb.TagNumber(3)
  void clearType() => $_clearField(3);

  @$pb.TagNumber(4)
  $pb.PbList<$core.String> get focusTags => $_getList(3);

  @$pb.TagNumber(5)
  $2.Timestamp get deadline => $_getN(4);
  @$pb.TagNumber(5)
  set deadline($2.Timestamp value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasDeadline() => $_has(4);
  @$pb.TagNumber(5)
  void clearDeadline() => $_clearField(5);
  @$pb.TagNumber(5)
  $2.Timestamp ensureDeadline() => $_ensure(4);

  @$pb.TagNumber(6)
  $core.String get sprintGoal => $_getSZ(5);
  @$pb.TagNumber(6)
  set sprintGoal($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasSprintGoal() => $_has(5);
  @$pb.TagNumber(6)
  void clearSprintGoal() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.int get maxMembers => $_getIZ(6);
  @$pb.TagNumber(7)
  set maxMembers($core.int value) => $_setSignedInt32(6, value);
  @$pb.TagNumber(7)
  $core.bool hasMaxMembers() => $_has(6);
  @$pb.TagNumber(7)
  void clearMaxMembers() => $_clearField(7);

  @$pb.TagNumber(8)
  $core.bool get isPublic => $_getBF(7);
  @$pb.TagNumber(8)
  set isPublic($core.bool value) => $_setBool(7, value);
  @$pb.TagNumber(8)
  $core.bool hasIsPublic() => $_has(7);
  @$pb.TagNumber(8)
  void clearIsPublic() => $_clearField(8);

  @$pb.TagNumber(9)
  $core.bool get joinRequiresApproval => $_getBF(8);
  @$pb.TagNumber(9)
  set joinRequiresApproval($core.bool value) => $_setBool(8, value);
  @$pb.TagNumber(9)
  $core.bool hasJoinRequiresApproval() => $_has(8);
  @$pb.TagNumber(9)
  void clearJoinRequiresApproval() => $_clearField(9);
}

class GroupInfo extends $pb.GeneratedMessage {
  factory GroupInfo({
    UUID? id,
    $core.String? name,
    $core.String? description,
    $core.String? avatarUrl,
    GroupType? type,
    $core.Iterable<$core.String>? focusTags,
    $2.Timestamp? deadline,
    $core.String? sprintGoal,
    $core.int? daysRemaining,
    $core.int? memberCount,
    $core.int? totalFlamePower,
    $core.int? todayCheckinCount,
    $core.int? totalTasksCompleted,
    $core.int? maxMembers,
    $core.bool? isPublic,
    $core.bool? joinRequiresApproval,
    GroupRole? myRole,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (name != null) result.name = name;
    if (description != null) result.description = description;
    if (avatarUrl != null) result.avatarUrl = avatarUrl;
    if (type != null) result.type = type;
    if (focusTags != null) result.focusTags.addAll(focusTags);
    if (deadline != null) result.deadline = deadline;
    if (sprintGoal != null) result.sprintGoal = sprintGoal;
    if (daysRemaining != null) result.daysRemaining = daysRemaining;
    if (memberCount != null) result.memberCount = memberCount;
    if (totalFlamePower != null) result.totalFlamePower = totalFlamePower;
    if (todayCheckinCount != null) result.todayCheckinCount = todayCheckinCount;
    if (totalTasksCompleted != null)
      result.totalTasksCompleted = totalTasksCompleted;
    if (maxMembers != null) result.maxMembers = maxMembers;
    if (isPublic != null) result.isPublic = isPublic;
    if (joinRequiresApproval != null)
      result.joinRequiresApproval = joinRequiresApproval;
    if (myRole != null) result.myRole = myRole;
    return result;
  }

  GroupInfo._();

  factory GroupInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory GroupInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'GroupInfo',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'id', subBuilder: UUID.create)
    ..aOS(2, _omitFieldNames ? '' : 'name')
    ..aOS(3, _omitFieldNames ? '' : 'description')
    ..aOS(4, _omitFieldNames ? '' : 'avatarUrl')
    ..aE<GroupType>(5, _omitFieldNames ? '' : 'type',
        enumValues: GroupType.values)
    ..pPS(6, _omitFieldNames ? '' : 'focusTags')
    ..aOM<$2.Timestamp>(7, _omitFieldNames ? '' : 'deadline',
        subBuilder: $2.Timestamp.create)
    ..aOS(8, _omitFieldNames ? '' : 'sprintGoal')
    ..aI(9, _omitFieldNames ? '' : 'daysRemaining')
    ..aI(10, _omitFieldNames ? '' : 'memberCount')
    ..aI(11, _omitFieldNames ? '' : 'totalFlamePower')
    ..aI(12, _omitFieldNames ? '' : 'todayCheckinCount')
    ..aI(13, _omitFieldNames ? '' : 'totalTasksCompleted')
    ..aI(14, _omitFieldNames ? '' : 'maxMembers')
    ..aOB(15, _omitFieldNames ? '' : 'isPublic')
    ..aOB(16, _omitFieldNames ? '' : 'joinRequiresApproval')
    ..aE<GroupRole>(17, _omitFieldNames ? '' : 'myRole',
        enumValues: GroupRole.values)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GroupInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GroupInfo copyWith(void Function(GroupInfo) updates) =>
      super.copyWith((message) => updates(message as GroupInfo)) as GroupInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GroupInfo create() => GroupInfo._();
  @$core.override
  GroupInfo createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static GroupInfo getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<GroupInfo>(create);
  static GroupInfo? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get id => $_getN(0);
  @$pb.TagNumber(1)
  set id(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureId() => $_ensure(0);

  @$pb.TagNumber(2)
  $core.String get name => $_getSZ(1);
  @$pb.TagNumber(2)
  set name($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasName() => $_has(1);
  @$pb.TagNumber(2)
  void clearName() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get description => $_getSZ(2);
  @$pb.TagNumber(3)
  set description($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasDescription() => $_has(2);
  @$pb.TagNumber(3)
  void clearDescription() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get avatarUrl => $_getSZ(3);
  @$pb.TagNumber(4)
  set avatarUrl($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasAvatarUrl() => $_has(3);
  @$pb.TagNumber(4)
  void clearAvatarUrl() => $_clearField(4);

  @$pb.TagNumber(5)
  GroupType get type => $_getN(4);
  @$pb.TagNumber(5)
  set type(GroupType value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasType() => $_has(4);
  @$pb.TagNumber(5)
  void clearType() => $_clearField(5);

  @$pb.TagNumber(6)
  $pb.PbList<$core.String> get focusTags => $_getList(5);

  @$pb.TagNumber(7)
  $2.Timestamp get deadline => $_getN(6);
  @$pb.TagNumber(7)
  set deadline($2.Timestamp value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasDeadline() => $_has(6);
  @$pb.TagNumber(7)
  void clearDeadline() => $_clearField(7);
  @$pb.TagNumber(7)
  $2.Timestamp ensureDeadline() => $_ensure(6);

  @$pb.TagNumber(8)
  $core.String get sprintGoal => $_getSZ(7);
  @$pb.TagNumber(8)
  set sprintGoal($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasSprintGoal() => $_has(7);
  @$pb.TagNumber(8)
  void clearSprintGoal() => $_clearField(8);

  @$pb.TagNumber(9)
  $core.int get daysRemaining => $_getIZ(8);
  @$pb.TagNumber(9)
  set daysRemaining($core.int value) => $_setSignedInt32(8, value);
  @$pb.TagNumber(9)
  $core.bool hasDaysRemaining() => $_has(8);
  @$pb.TagNumber(9)
  void clearDaysRemaining() => $_clearField(9);

  @$pb.TagNumber(10)
  $core.int get memberCount => $_getIZ(9);
  @$pb.TagNumber(10)
  set memberCount($core.int value) => $_setSignedInt32(9, value);
  @$pb.TagNumber(10)
  $core.bool hasMemberCount() => $_has(9);
  @$pb.TagNumber(10)
  void clearMemberCount() => $_clearField(10);

  @$pb.TagNumber(11)
  $core.int get totalFlamePower => $_getIZ(10);
  @$pb.TagNumber(11)
  set totalFlamePower($core.int value) => $_setSignedInt32(10, value);
  @$pb.TagNumber(11)
  $core.bool hasTotalFlamePower() => $_has(10);
  @$pb.TagNumber(11)
  void clearTotalFlamePower() => $_clearField(11);

  @$pb.TagNumber(12)
  $core.int get todayCheckinCount => $_getIZ(11);
  @$pb.TagNumber(12)
  set todayCheckinCount($core.int value) => $_setSignedInt32(11, value);
  @$pb.TagNumber(12)
  $core.bool hasTodayCheckinCount() => $_has(11);
  @$pb.TagNumber(12)
  void clearTodayCheckinCount() => $_clearField(12);

  @$pb.TagNumber(13)
  $core.int get totalTasksCompleted => $_getIZ(12);
  @$pb.TagNumber(13)
  set totalTasksCompleted($core.int value) => $_setSignedInt32(12, value);
  @$pb.TagNumber(13)
  $core.bool hasTotalTasksCompleted() => $_has(12);
  @$pb.TagNumber(13)
  void clearTotalTasksCompleted() => $_clearField(13);

  @$pb.TagNumber(14)
  $core.int get maxMembers => $_getIZ(13);
  @$pb.TagNumber(14)
  set maxMembers($core.int value) => $_setSignedInt32(13, value);
  @$pb.TagNumber(14)
  $core.bool hasMaxMembers() => $_has(13);
  @$pb.TagNumber(14)
  void clearMaxMembers() => $_clearField(14);

  @$pb.TagNumber(15)
  $core.bool get isPublic => $_getBF(14);
  @$pb.TagNumber(15)
  set isPublic($core.bool value) => $_setBool(14, value);
  @$pb.TagNumber(15)
  $core.bool hasIsPublic() => $_has(14);
  @$pb.TagNumber(15)
  void clearIsPublic() => $_clearField(15);

  @$pb.TagNumber(16)
  $core.bool get joinRequiresApproval => $_getBF(15);
  @$pb.TagNumber(16)
  set joinRequiresApproval($core.bool value) => $_setBool(15, value);
  @$pb.TagNumber(16)
  $core.bool hasJoinRequiresApproval() => $_has(15);
  @$pb.TagNumber(16)
  void clearJoinRequiresApproval() => $_clearField(16);

  @$pb.TagNumber(17)
  GroupRole get myRole => $_getN(16);
  @$pb.TagNumber(17)
  set myRole(GroupRole value) => $_setField(17, value);
  @$pb.TagNumber(17)
  $core.bool hasMyRole() => $_has(16);
  @$pb.TagNumber(17)
  void clearMyRole() => $_clearField(17);
}

class GroupMemberInfo extends $pb.GeneratedMessage {
  factory GroupMemberInfo({
    UserBrief? user,
    GroupRole? role,
    $core.int? flameContribution,
    $core.int? tasksCompleted,
    $core.int? checkinStreak,
    $2.Timestamp? joinedAt,
    $2.Timestamp? lastActiveAt,
  }) {
    final result = create();
    if (user != null) result.user = user;
    if (role != null) result.role = role;
    if (flameContribution != null) result.flameContribution = flameContribution;
    if (tasksCompleted != null) result.tasksCompleted = tasksCompleted;
    if (checkinStreak != null) result.checkinStreak = checkinStreak;
    if (joinedAt != null) result.joinedAt = joinedAt;
    if (lastActiveAt != null) result.lastActiveAt = lastActiveAt;
    return result;
  }

  GroupMemberInfo._();

  factory GroupMemberInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory GroupMemberInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'GroupMemberInfo',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UserBrief>(1, _omitFieldNames ? '' : 'user',
        subBuilder: UserBrief.create)
    ..aE<GroupRole>(2, _omitFieldNames ? '' : 'role',
        enumValues: GroupRole.values)
    ..aI(3, _omitFieldNames ? '' : 'flameContribution')
    ..aI(4, _omitFieldNames ? '' : 'tasksCompleted')
    ..aI(5, _omitFieldNames ? '' : 'checkinStreak')
    ..aOM<$2.Timestamp>(6, _omitFieldNames ? '' : 'joinedAt',
        subBuilder: $2.Timestamp.create)
    ..aOM<$2.Timestamp>(7, _omitFieldNames ? '' : 'lastActiveAt',
        subBuilder: $2.Timestamp.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GroupMemberInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GroupMemberInfo copyWith(void Function(GroupMemberInfo) updates) =>
      super.copyWith((message) => updates(message as GroupMemberInfo))
          as GroupMemberInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GroupMemberInfo create() => GroupMemberInfo._();
  @$core.override
  GroupMemberInfo createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static GroupMemberInfo getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<GroupMemberInfo>(create);
  static GroupMemberInfo? _defaultInstance;

  @$pb.TagNumber(1)
  UserBrief get user => $_getN(0);
  @$pb.TagNumber(1)
  set user(UserBrief value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasUser() => $_has(0);
  @$pb.TagNumber(1)
  void clearUser() => $_clearField(1);
  @$pb.TagNumber(1)
  UserBrief ensureUser() => $_ensure(0);

  @$pb.TagNumber(2)
  GroupRole get role => $_getN(1);
  @$pb.TagNumber(2)
  set role(GroupRole value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasRole() => $_has(1);
  @$pb.TagNumber(2)
  void clearRole() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get flameContribution => $_getIZ(2);
  @$pb.TagNumber(3)
  set flameContribution($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasFlameContribution() => $_has(2);
  @$pb.TagNumber(3)
  void clearFlameContribution() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.int get tasksCompleted => $_getIZ(3);
  @$pb.TagNumber(4)
  set tasksCompleted($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasTasksCompleted() => $_has(3);
  @$pb.TagNumber(4)
  void clearTasksCompleted() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.int get checkinStreak => $_getIZ(4);
  @$pb.TagNumber(5)
  set checkinStreak($core.int value) => $_setSignedInt32(4, value);
  @$pb.TagNumber(5)
  $core.bool hasCheckinStreak() => $_has(4);
  @$pb.TagNumber(5)
  void clearCheckinStreak() => $_clearField(5);

  @$pb.TagNumber(6)
  $2.Timestamp get joinedAt => $_getN(5);
  @$pb.TagNumber(6)
  set joinedAt($2.Timestamp value) => $_setField(6, value);
  @$pb.TagNumber(6)
  $core.bool hasJoinedAt() => $_has(5);
  @$pb.TagNumber(6)
  void clearJoinedAt() => $_clearField(6);
  @$pb.TagNumber(6)
  $2.Timestamp ensureJoinedAt() => $_ensure(5);

  @$pb.TagNumber(7)
  $2.Timestamp get lastActiveAt => $_getN(6);
  @$pb.TagNumber(7)
  set lastActiveAt($2.Timestamp value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasLastActiveAt() => $_has(6);
  @$pb.TagNumber(7)
  void clearLastActiveAt() => $_clearField(7);
  @$pb.TagNumber(7)
  $2.Timestamp ensureLastActiveAt() => $_ensure(6);
}

class MessageSend extends $pb.GeneratedMessage {
  factory MessageSend({
    MessageType? messageType,
    $core.String? content,
    $core.String? contentData,
    UUID? replyToId,
    UUID? threadRootId,
    $core.Iterable<UUID>? mentionUserIds,
    $core.String? nonce,
  }) {
    final result = create();
    if (messageType != null) result.messageType = messageType;
    if (content != null) result.content = content;
    if (contentData != null) result.contentData = contentData;
    if (replyToId != null) result.replyToId = replyToId;
    if (threadRootId != null) result.threadRootId = threadRootId;
    if (mentionUserIds != null) result.mentionUserIds.addAll(mentionUserIds);
    if (nonce != null) result.nonce = nonce;
    return result;
  }

  MessageSend._();

  factory MessageSend.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory MessageSend.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MessageSend',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aE<MessageType>(1, _omitFieldNames ? '' : 'messageType',
        enumValues: MessageType.values)
    ..aOS(2, _omitFieldNames ? '' : 'content')
    ..aOS(3, _omitFieldNames ? '' : 'contentData')
    ..aOM<UUID>(4, _omitFieldNames ? '' : 'replyToId', subBuilder: UUID.create)
    ..aOM<UUID>(5, _omitFieldNames ? '' : 'threadRootId',
        subBuilder: UUID.create)
    ..pPM<UUID>(6, _omitFieldNames ? '' : 'mentionUserIds',
        subBuilder: UUID.create)
    ..aOS(7, _omitFieldNames ? '' : 'nonce')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MessageSend clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MessageSend copyWith(void Function(MessageSend) updates) =>
      super.copyWith((message) => updates(message as MessageSend))
          as MessageSend;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MessageSend create() => MessageSend._();
  @$core.override
  MessageSend createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static MessageSend getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MessageSend>(create);
  static MessageSend? _defaultInstance;

  @$pb.TagNumber(1)
  MessageType get messageType => $_getN(0);
  @$pb.TagNumber(1)
  set messageType(MessageType value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasMessageType() => $_has(0);
  @$pb.TagNumber(1)
  void clearMessageType() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get content => $_getSZ(1);
  @$pb.TagNumber(2)
  set content($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasContent() => $_has(1);
  @$pb.TagNumber(2)
  void clearContent() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get contentData => $_getSZ(2);
  @$pb.TagNumber(3)
  set contentData($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasContentData() => $_has(2);
  @$pb.TagNumber(3)
  void clearContentData() => $_clearField(3);

  @$pb.TagNumber(4)
  UUID get replyToId => $_getN(3);
  @$pb.TagNumber(4)
  set replyToId(UUID value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasReplyToId() => $_has(3);
  @$pb.TagNumber(4)
  void clearReplyToId() => $_clearField(4);
  @$pb.TagNumber(4)
  UUID ensureReplyToId() => $_ensure(3);

  @$pb.TagNumber(5)
  UUID get threadRootId => $_getN(4);
  @$pb.TagNumber(5)
  set threadRootId(UUID value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasThreadRootId() => $_has(4);
  @$pb.TagNumber(5)
  void clearThreadRootId() => $_clearField(5);
  @$pb.TagNumber(5)
  UUID ensureThreadRootId() => $_ensure(4);

  @$pb.TagNumber(6)
  $pb.PbList<UUID> get mentionUserIds => $_getList(5);

  @$pb.TagNumber(7)
  $core.String get nonce => $_getSZ(6);
  @$pb.TagNumber(7)
  set nonce($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasNonce() => $_has(6);
  @$pb.TagNumber(7)
  void clearNonce() => $_clearField(7);
}

class MessageInfo extends $pb.GeneratedMessage {
  factory MessageInfo({
    UUID? id,
    UserBrief? sender,
    MessageType? messageType,
    $core.String? content,
    $core.String? contentData,
    UUID? replyToId,
    UUID? threadRootId,
    $core.Iterable<UUID>? mentionUserIds,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? reactions,
    $core.bool? isRevoked,
    $2.Timestamp? revokedAt,
    $2.Timestamp? editedAt,
    $2.Timestamp? createdAt,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (sender != null) result.sender = sender;
    if (messageType != null) result.messageType = messageType;
    if (content != null) result.content = content;
    if (contentData != null) result.contentData = contentData;
    if (replyToId != null) result.replyToId = replyToId;
    if (threadRootId != null) result.threadRootId = threadRootId;
    if (mentionUserIds != null) result.mentionUserIds.addAll(mentionUserIds);
    if (reactions != null) result.reactions.addEntries(reactions);
    if (isRevoked != null) result.isRevoked = isRevoked;
    if (revokedAt != null) result.revokedAt = revokedAt;
    if (editedAt != null) result.editedAt = editedAt;
    if (createdAt != null) result.createdAt = createdAt;
    return result;
  }

  MessageInfo._();

  factory MessageInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory MessageInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MessageInfo',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'id', subBuilder: UUID.create)
    ..aOM<UserBrief>(2, _omitFieldNames ? '' : 'sender',
        subBuilder: UserBrief.create)
    ..aE<MessageType>(3, _omitFieldNames ? '' : 'messageType',
        enumValues: MessageType.values)
    ..aOS(4, _omitFieldNames ? '' : 'content')
    ..aOS(5, _omitFieldNames ? '' : 'contentData')
    ..aOM<UUID>(6, _omitFieldNames ? '' : 'replyToId', subBuilder: UUID.create)
    ..aOM<UUID>(7, _omitFieldNames ? '' : 'threadRootId',
        subBuilder: UUID.create)
    ..pPM<UUID>(8, _omitFieldNames ? '' : 'mentionUserIds',
        subBuilder: UUID.create)
    ..m<$core.String, $core.String>(9, _omitFieldNames ? '' : 'reactions',
        entryClassName: 'MessageInfo.ReactionsEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('sparkle.community'))
    ..aOB(10, _omitFieldNames ? '' : 'isRevoked')
    ..aOM<$2.Timestamp>(11, _omitFieldNames ? '' : 'revokedAt',
        subBuilder: $2.Timestamp.create)
    ..aOM<$2.Timestamp>(12, _omitFieldNames ? '' : 'editedAt',
        subBuilder: $2.Timestamp.create)
    ..aOM<$2.Timestamp>(13, _omitFieldNames ? '' : 'createdAt',
        subBuilder: $2.Timestamp.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MessageInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MessageInfo copyWith(void Function(MessageInfo) updates) =>
      super.copyWith((message) => updates(message as MessageInfo))
          as MessageInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MessageInfo create() => MessageInfo._();
  @$core.override
  MessageInfo createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static MessageInfo getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MessageInfo>(create);
  static MessageInfo? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get id => $_getN(0);
  @$pb.TagNumber(1)
  set id(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureId() => $_ensure(0);

  @$pb.TagNumber(2)
  UserBrief get sender => $_getN(1);
  @$pb.TagNumber(2)
  set sender(UserBrief value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasSender() => $_has(1);
  @$pb.TagNumber(2)
  void clearSender() => $_clearField(2);
  @$pb.TagNumber(2)
  UserBrief ensureSender() => $_ensure(1);

  @$pb.TagNumber(3)
  MessageType get messageType => $_getN(2);
  @$pb.TagNumber(3)
  set messageType(MessageType value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasMessageType() => $_has(2);
  @$pb.TagNumber(3)
  void clearMessageType() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get content => $_getSZ(3);
  @$pb.TagNumber(4)
  set content($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasContent() => $_has(3);
  @$pb.TagNumber(4)
  void clearContent() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get contentData => $_getSZ(4);
  @$pb.TagNumber(5)
  set contentData($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasContentData() => $_has(4);
  @$pb.TagNumber(5)
  void clearContentData() => $_clearField(5);

  @$pb.TagNumber(6)
  UUID get replyToId => $_getN(5);
  @$pb.TagNumber(6)
  set replyToId(UUID value) => $_setField(6, value);
  @$pb.TagNumber(6)
  $core.bool hasReplyToId() => $_has(5);
  @$pb.TagNumber(6)
  void clearReplyToId() => $_clearField(6);
  @$pb.TagNumber(6)
  UUID ensureReplyToId() => $_ensure(5);

  @$pb.TagNumber(7)
  UUID get threadRootId => $_getN(6);
  @$pb.TagNumber(7)
  set threadRootId(UUID value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasThreadRootId() => $_has(6);
  @$pb.TagNumber(7)
  void clearThreadRootId() => $_clearField(7);
  @$pb.TagNumber(7)
  UUID ensureThreadRootId() => $_ensure(6);

  @$pb.TagNumber(8)
  $pb.PbList<UUID> get mentionUserIds => $_getList(7);

  @$pb.TagNumber(9)
  $pb.PbMap<$core.String, $core.String> get reactions => $_getMap(8);

  @$pb.TagNumber(10)
  $core.bool get isRevoked => $_getBF(9);
  @$pb.TagNumber(10)
  set isRevoked($core.bool value) => $_setBool(9, value);
  @$pb.TagNumber(10)
  $core.bool hasIsRevoked() => $_has(9);
  @$pb.TagNumber(10)
  void clearIsRevoked() => $_clearField(10);

  @$pb.TagNumber(11)
  $2.Timestamp get revokedAt => $_getN(10);
  @$pb.TagNumber(11)
  set revokedAt($2.Timestamp value) => $_setField(11, value);
  @$pb.TagNumber(11)
  $core.bool hasRevokedAt() => $_has(10);
  @$pb.TagNumber(11)
  void clearRevokedAt() => $_clearField(11);
  @$pb.TagNumber(11)
  $2.Timestamp ensureRevokedAt() => $_ensure(10);

  @$pb.TagNumber(12)
  $2.Timestamp get editedAt => $_getN(11);
  @$pb.TagNumber(12)
  set editedAt($2.Timestamp value) => $_setField(12, value);
  @$pb.TagNumber(12)
  $core.bool hasEditedAt() => $_has(11);
  @$pb.TagNumber(12)
  void clearEditedAt() => $_clearField(12);
  @$pb.TagNumber(12)
  $2.Timestamp ensureEditedAt() => $_ensure(11);

  @$pb.TagNumber(13)
  $2.Timestamp get createdAt => $_getN(12);
  @$pb.TagNumber(13)
  set createdAt($2.Timestamp value) => $_setField(13, value);
  @$pb.TagNumber(13)
  $core.bool hasCreatedAt() => $_has(12);
  @$pb.TagNumber(13)
  void clearCreatedAt() => $_clearField(13);
  @$pb.TagNumber(13)
  $2.Timestamp ensureCreatedAt() => $_ensure(12);
}

class PrivateMessageSend extends $pb.GeneratedMessage {
  factory PrivateMessageSend({
    UUID? targetUserId,
    MessageType? messageType,
    $core.String? content,
    $core.String? contentData,
    UUID? replyToId,
    UUID? threadRootId,
    $core.Iterable<UUID>? mentionUserIds,
    $core.String? nonce,
  }) {
    final result = create();
    if (targetUserId != null) result.targetUserId = targetUserId;
    if (messageType != null) result.messageType = messageType;
    if (content != null) result.content = content;
    if (contentData != null) result.contentData = contentData;
    if (replyToId != null) result.replyToId = replyToId;
    if (threadRootId != null) result.threadRootId = threadRootId;
    if (mentionUserIds != null) result.mentionUserIds.addAll(mentionUserIds);
    if (nonce != null) result.nonce = nonce;
    return result;
  }

  PrivateMessageSend._();

  factory PrivateMessageSend.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory PrivateMessageSend.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'PrivateMessageSend',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'targetUserId',
        subBuilder: UUID.create)
    ..aE<MessageType>(2, _omitFieldNames ? '' : 'messageType',
        enumValues: MessageType.values)
    ..aOS(3, _omitFieldNames ? '' : 'content')
    ..aOS(4, _omitFieldNames ? '' : 'contentData')
    ..aOM<UUID>(5, _omitFieldNames ? '' : 'replyToId', subBuilder: UUID.create)
    ..aOM<UUID>(6, _omitFieldNames ? '' : 'threadRootId',
        subBuilder: UUID.create)
    ..pPM<UUID>(7, _omitFieldNames ? '' : 'mentionUserIds',
        subBuilder: UUID.create)
    ..aOS(8, _omitFieldNames ? '' : 'nonce')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  PrivateMessageSend clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  PrivateMessageSend copyWith(void Function(PrivateMessageSend) updates) =>
      super.copyWith((message) => updates(message as PrivateMessageSend))
          as PrivateMessageSend;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static PrivateMessageSend create() => PrivateMessageSend._();
  @$core.override
  PrivateMessageSend createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static PrivateMessageSend getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<PrivateMessageSend>(create);
  static PrivateMessageSend? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get targetUserId => $_getN(0);
  @$pb.TagNumber(1)
  set targetUserId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasTargetUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearTargetUserId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureTargetUserId() => $_ensure(0);

  @$pb.TagNumber(2)
  MessageType get messageType => $_getN(1);
  @$pb.TagNumber(2)
  set messageType(MessageType value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasMessageType() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessageType() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get content => $_getSZ(2);
  @$pb.TagNumber(3)
  set content($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasContent() => $_has(2);
  @$pb.TagNumber(3)
  void clearContent() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get contentData => $_getSZ(3);
  @$pb.TagNumber(4)
  set contentData($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasContentData() => $_has(3);
  @$pb.TagNumber(4)
  void clearContentData() => $_clearField(4);

  @$pb.TagNumber(5)
  UUID get replyToId => $_getN(4);
  @$pb.TagNumber(5)
  set replyToId(UUID value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasReplyToId() => $_has(4);
  @$pb.TagNumber(5)
  void clearReplyToId() => $_clearField(5);
  @$pb.TagNumber(5)
  UUID ensureReplyToId() => $_ensure(4);

  @$pb.TagNumber(6)
  UUID get threadRootId => $_getN(5);
  @$pb.TagNumber(6)
  set threadRootId(UUID value) => $_setField(6, value);
  @$pb.TagNumber(6)
  $core.bool hasThreadRootId() => $_has(5);
  @$pb.TagNumber(6)
  void clearThreadRootId() => $_clearField(6);
  @$pb.TagNumber(6)
  UUID ensureThreadRootId() => $_ensure(5);

  @$pb.TagNumber(7)
  $pb.PbList<UUID> get mentionUserIds => $_getList(6);

  @$pb.TagNumber(8)
  $core.String get nonce => $_getSZ(7);
  @$pb.TagNumber(8)
  set nonce($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasNonce() => $_has(7);
  @$pb.TagNumber(8)
  void clearNonce() => $_clearField(8);
}

class PrivateMessageInfo extends $pb.GeneratedMessage {
  factory PrivateMessageInfo({
    UUID? id,
    UserBrief? sender,
    UserBrief? receiver,
    MessageType? messageType,
    $core.String? content,
    $core.String? contentData,
    UUID? replyToId,
    UUID? threadRootId,
    $core.Iterable<UUID>? mentionUserIds,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? reactions,
    $core.bool? isRevoked,
    $2.Timestamp? revokedAt,
    $2.Timestamp? editedAt,
    $core.bool? isRead,
    $2.Timestamp? readAt,
    $2.Timestamp? createdAt,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (sender != null) result.sender = sender;
    if (receiver != null) result.receiver = receiver;
    if (messageType != null) result.messageType = messageType;
    if (content != null) result.content = content;
    if (contentData != null) result.contentData = contentData;
    if (replyToId != null) result.replyToId = replyToId;
    if (threadRootId != null) result.threadRootId = threadRootId;
    if (mentionUserIds != null) result.mentionUserIds.addAll(mentionUserIds);
    if (reactions != null) result.reactions.addEntries(reactions);
    if (isRevoked != null) result.isRevoked = isRevoked;
    if (revokedAt != null) result.revokedAt = revokedAt;
    if (editedAt != null) result.editedAt = editedAt;
    if (isRead != null) result.isRead = isRead;
    if (readAt != null) result.readAt = readAt;
    if (createdAt != null) result.createdAt = createdAt;
    return result;
  }

  PrivateMessageInfo._();

  factory PrivateMessageInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory PrivateMessageInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'PrivateMessageInfo',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'id', subBuilder: UUID.create)
    ..aOM<UserBrief>(2, _omitFieldNames ? '' : 'sender',
        subBuilder: UserBrief.create)
    ..aOM<UserBrief>(3, _omitFieldNames ? '' : 'receiver',
        subBuilder: UserBrief.create)
    ..aE<MessageType>(4, _omitFieldNames ? '' : 'messageType',
        enumValues: MessageType.values)
    ..aOS(5, _omitFieldNames ? '' : 'content')
    ..aOS(6, _omitFieldNames ? '' : 'contentData')
    ..aOM<UUID>(7, _omitFieldNames ? '' : 'replyToId', subBuilder: UUID.create)
    ..aOM<UUID>(8, _omitFieldNames ? '' : 'threadRootId',
        subBuilder: UUID.create)
    ..pPM<UUID>(9, _omitFieldNames ? '' : 'mentionUserIds',
        subBuilder: UUID.create)
    ..m<$core.String, $core.String>(10, _omitFieldNames ? '' : 'reactions',
        entryClassName: 'PrivateMessageInfo.ReactionsEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('sparkle.community'))
    ..aOB(11, _omitFieldNames ? '' : 'isRevoked')
    ..aOM<$2.Timestamp>(12, _omitFieldNames ? '' : 'revokedAt',
        subBuilder: $2.Timestamp.create)
    ..aOM<$2.Timestamp>(13, _omitFieldNames ? '' : 'editedAt',
        subBuilder: $2.Timestamp.create)
    ..aOB(14, _omitFieldNames ? '' : 'isRead')
    ..aOM<$2.Timestamp>(15, _omitFieldNames ? '' : 'readAt',
        subBuilder: $2.Timestamp.create)
    ..aOM<$2.Timestamp>(16, _omitFieldNames ? '' : 'createdAt',
        subBuilder: $2.Timestamp.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  PrivateMessageInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  PrivateMessageInfo copyWith(void Function(PrivateMessageInfo) updates) =>
      super.copyWith((message) => updates(message as PrivateMessageInfo))
          as PrivateMessageInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static PrivateMessageInfo create() => PrivateMessageInfo._();
  @$core.override
  PrivateMessageInfo createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static PrivateMessageInfo getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<PrivateMessageInfo>(create);
  static PrivateMessageInfo? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get id => $_getN(0);
  @$pb.TagNumber(1)
  set id(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureId() => $_ensure(0);

  @$pb.TagNumber(2)
  UserBrief get sender => $_getN(1);
  @$pb.TagNumber(2)
  set sender(UserBrief value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasSender() => $_has(1);
  @$pb.TagNumber(2)
  void clearSender() => $_clearField(2);
  @$pb.TagNumber(2)
  UserBrief ensureSender() => $_ensure(1);

  @$pb.TagNumber(3)
  UserBrief get receiver => $_getN(2);
  @$pb.TagNumber(3)
  set receiver(UserBrief value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasReceiver() => $_has(2);
  @$pb.TagNumber(3)
  void clearReceiver() => $_clearField(3);
  @$pb.TagNumber(3)
  UserBrief ensureReceiver() => $_ensure(2);

  @$pb.TagNumber(4)
  MessageType get messageType => $_getN(3);
  @$pb.TagNumber(4)
  set messageType(MessageType value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasMessageType() => $_has(3);
  @$pb.TagNumber(4)
  void clearMessageType() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get content => $_getSZ(4);
  @$pb.TagNumber(5)
  set content($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasContent() => $_has(4);
  @$pb.TagNumber(5)
  void clearContent() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.String get contentData => $_getSZ(5);
  @$pb.TagNumber(6)
  set contentData($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasContentData() => $_has(5);
  @$pb.TagNumber(6)
  void clearContentData() => $_clearField(6);

  @$pb.TagNumber(7)
  UUID get replyToId => $_getN(6);
  @$pb.TagNumber(7)
  set replyToId(UUID value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasReplyToId() => $_has(6);
  @$pb.TagNumber(7)
  void clearReplyToId() => $_clearField(7);
  @$pb.TagNumber(7)
  UUID ensureReplyToId() => $_ensure(6);

  @$pb.TagNumber(8)
  UUID get threadRootId => $_getN(7);
  @$pb.TagNumber(8)
  set threadRootId(UUID value) => $_setField(8, value);
  @$pb.TagNumber(8)
  $core.bool hasThreadRootId() => $_has(7);
  @$pb.TagNumber(8)
  void clearThreadRootId() => $_clearField(8);
  @$pb.TagNumber(8)
  UUID ensureThreadRootId() => $_ensure(7);

  @$pb.TagNumber(9)
  $pb.PbList<UUID> get mentionUserIds => $_getList(8);

  @$pb.TagNumber(10)
  $pb.PbMap<$core.String, $core.String> get reactions => $_getMap(9);

  @$pb.TagNumber(11)
  $core.bool get isRevoked => $_getBF(10);
  @$pb.TagNumber(11)
  set isRevoked($core.bool value) => $_setBool(10, value);
  @$pb.TagNumber(11)
  $core.bool hasIsRevoked() => $_has(10);
  @$pb.TagNumber(11)
  void clearIsRevoked() => $_clearField(11);

  @$pb.TagNumber(12)
  $2.Timestamp get revokedAt => $_getN(11);
  @$pb.TagNumber(12)
  set revokedAt($2.Timestamp value) => $_setField(12, value);
  @$pb.TagNumber(12)
  $core.bool hasRevokedAt() => $_has(11);
  @$pb.TagNumber(12)
  void clearRevokedAt() => $_clearField(12);
  @$pb.TagNumber(12)
  $2.Timestamp ensureRevokedAt() => $_ensure(11);

  @$pb.TagNumber(13)
  $2.Timestamp get editedAt => $_getN(12);
  @$pb.TagNumber(13)
  set editedAt($2.Timestamp value) => $_setField(13, value);
  @$pb.TagNumber(13)
  $core.bool hasEditedAt() => $_has(12);
  @$pb.TagNumber(13)
  void clearEditedAt() => $_clearField(13);
  @$pb.TagNumber(13)
  $2.Timestamp ensureEditedAt() => $_ensure(12);

  @$pb.TagNumber(14)
  $core.bool get isRead => $_getBF(13);
  @$pb.TagNumber(14)
  set isRead($core.bool value) => $_setBool(13, value);
  @$pb.TagNumber(14)
  $core.bool hasIsRead() => $_has(13);
  @$pb.TagNumber(14)
  void clearIsRead() => $_clearField(14);

  @$pb.TagNumber(15)
  $2.Timestamp get readAt => $_getN(14);
  @$pb.TagNumber(15)
  set readAt($2.Timestamp value) => $_setField(15, value);
  @$pb.TagNumber(15)
  $core.bool hasReadAt() => $_has(14);
  @$pb.TagNumber(15)
  void clearReadAt() => $_clearField(15);
  @$pb.TagNumber(15)
  $2.Timestamp ensureReadAt() => $_ensure(14);

  @$pb.TagNumber(16)
  $2.Timestamp get createdAt => $_getN(15);
  @$pb.TagNumber(16)
  set createdAt($2.Timestamp value) => $_setField(16, value);
  @$pb.TagNumber(16)
  $core.bool hasCreatedAt() => $_has(15);
  @$pb.TagNumber(16)
  void clearCreatedAt() => $_clearField(16);
  @$pb.TagNumber(16)
  $2.Timestamp ensureCreatedAt() => $_ensure(15);
}

class CheckinRequest extends $pb.GeneratedMessage {
  factory CheckinRequest({
    UUID? groupId,
    $core.String? message,
    $core.int? todayDurationMinutes,
  }) {
    final result = create();
    if (groupId != null) result.groupId = groupId;
    if (message != null) result.message = message;
    if (todayDurationMinutes != null)
      result.todayDurationMinutes = todayDurationMinutes;
    return result;
  }

  CheckinRequest._();

  factory CheckinRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory CheckinRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'CheckinRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'groupId', subBuilder: UUID.create)
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aI(3, _omitFieldNames ? '' : 'todayDurationMinutes')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CheckinRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CheckinRequest copyWith(void Function(CheckinRequest) updates) =>
      super.copyWith((message) => updates(message as CheckinRequest))
          as CheckinRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CheckinRequest create() => CheckinRequest._();
  @$core.override
  CheckinRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static CheckinRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<CheckinRequest>(create);
  static CheckinRequest? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get groupId => $_getN(0);
  @$pb.TagNumber(1)
  set groupId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasGroupId() => $_has(0);
  @$pb.TagNumber(1)
  void clearGroupId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureGroupId() => $_ensure(0);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get todayDurationMinutes => $_getIZ(2);
  @$pb.TagNumber(3)
  set todayDurationMinutes($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTodayDurationMinutes() => $_has(2);
  @$pb.TagNumber(3)
  void clearTodayDurationMinutes() => $_clearField(3);
}

class CheckinResponse extends $pb.GeneratedMessage {
  factory CheckinResponse({
    $core.bool? success,
    $core.int? newStreak,
    $core.int? flameEarned,
    $core.int? rankInGroup,
    $core.int? groupCheckinCount,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (newStreak != null) result.newStreak = newStreak;
    if (flameEarned != null) result.flameEarned = flameEarned;
    if (rankInGroup != null) result.rankInGroup = rankInGroup;
    if (groupCheckinCount != null) result.groupCheckinCount = groupCheckinCount;
    return result;
  }

  CheckinResponse._();

  factory CheckinResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory CheckinResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'CheckinResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aI(2, _omitFieldNames ? '' : 'newStreak')
    ..aI(3, _omitFieldNames ? '' : 'flameEarned')
    ..aI(4, _omitFieldNames ? '' : 'rankInGroup')
    ..aI(5, _omitFieldNames ? '' : 'groupCheckinCount')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CheckinResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CheckinResponse copyWith(void Function(CheckinResponse) updates) =>
      super.copyWith((message) => updates(message as CheckinResponse))
          as CheckinResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CheckinResponse create() => CheckinResponse._();
  @$core.override
  CheckinResponse createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static CheckinResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<CheckinResponse>(create);
  static CheckinResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.int get newStreak => $_getIZ(1);
  @$pb.TagNumber(2)
  set newStreak($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasNewStreak() => $_has(1);
  @$pb.TagNumber(2)
  void clearNewStreak() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get flameEarned => $_getIZ(2);
  @$pb.TagNumber(3)
  set flameEarned($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasFlameEarned() => $_has(2);
  @$pb.TagNumber(3)
  void clearFlameEarned() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.int get rankInGroup => $_getIZ(3);
  @$pb.TagNumber(4)
  set rankInGroup($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasRankInGroup() => $_has(3);
  @$pb.TagNumber(4)
  void clearRankInGroup() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.int get groupCheckinCount => $_getIZ(4);
  @$pb.TagNumber(5)
  set groupCheckinCount($core.int value) => $_setSignedInt32(4, value);
  @$pb.TagNumber(5)
  $core.bool hasGroupCheckinCount() => $_has(4);
  @$pb.TagNumber(5)
  void clearGroupCheckinCount() => $_clearField(5);
}

class UserPrivacySettings extends $pb.GeneratedMessage {
  factory UserPrivacySettings({
    SearchVisibility? searchableBy,
  }) {
    final result = create();
    if (searchableBy != null) result.searchableBy = searchableBy;
    return result;
  }

  UserPrivacySettings._();

  factory UserPrivacySettings.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory UserPrivacySettings.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'UserPrivacySettings',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aE<SearchVisibility>(1, _omitFieldNames ? '' : 'searchableBy',
        enumValues: SearchVisibility.values)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UserPrivacySettings clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UserPrivacySettings copyWith(void Function(UserPrivacySettings) updates) =>
      super.copyWith((message) => updates(message as UserPrivacySettings))
          as UserPrivacySettings;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UserPrivacySettings create() => UserPrivacySettings._();
  @$core.override
  UserPrivacySettings createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static UserPrivacySettings getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<UserPrivacySettings>(create);
  static UserPrivacySettings? _defaultInstance;

  @$pb.TagNumber(1)
  SearchVisibility get searchableBy => $_getN(0);
  @$pb.TagNumber(1)
  set searchableBy(SearchVisibility value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasSearchableBy() => $_has(0);
  @$pb.TagNumber(1)
  void clearSearchableBy() => $_clearField(1);
}

class SearchUsersRequest extends $pb.GeneratedMessage {
  factory SearchUsersRequest({
    $core.String? keyword,
    $core.int? limit,
  }) {
    final result = create();
    if (keyword != null) result.keyword = keyword;
    if (limit != null) result.limit = limit;
    return result;
  }

  SearchUsersRequest._();

  factory SearchUsersRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory SearchUsersRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'SearchUsersRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'keyword')
    ..aI(2, _omitFieldNames ? '' : 'limit')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SearchUsersRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SearchUsersRequest copyWith(void Function(SearchUsersRequest) updates) =>
      super.copyWith((message) => updates(message as SearchUsersRequest))
          as SearchUsersRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static SearchUsersRequest create() => SearchUsersRequest._();
  @$core.override
  SearchUsersRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static SearchUsersRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<SearchUsersRequest>(create);
  static SearchUsersRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get keyword => $_getSZ(0);
  @$pb.TagNumber(1)
  set keyword($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasKeyword() => $_has(0);
  @$pb.TagNumber(1)
  void clearKeyword() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.int get limit => $_getIZ(1);
  @$pb.TagNumber(2)
  set limit($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasLimit() => $_has(1);
  @$pb.TagNumber(2)
  void clearLimit() => $_clearField(2);
}

class SearchGroupsRequest extends $pb.GeneratedMessage {
  factory SearchGroupsRequest({
    $core.String? keyword,
    GroupType? type,
    $core.int? limit,
  }) {
    final result = create();
    if (keyword != null) result.keyword = keyword;
    if (type != null) result.type = type;
    if (limit != null) result.limit = limit;
    return result;
  }

  SearchGroupsRequest._();

  factory SearchGroupsRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory SearchGroupsRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'SearchGroupsRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'keyword')
    ..aE<GroupType>(2, _omitFieldNames ? '' : 'type',
        enumValues: GroupType.values)
    ..aI(3, _omitFieldNames ? '' : 'limit')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SearchGroupsRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SearchGroupsRequest copyWith(void Function(SearchGroupsRequest) updates) =>
      super.copyWith((message) => updates(message as SearchGroupsRequest))
          as SearchGroupsRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static SearchGroupsRequest create() => SearchGroupsRequest._();
  @$core.override
  SearchGroupsRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static SearchGroupsRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<SearchGroupsRequest>(create);
  static SearchGroupsRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get keyword => $_getSZ(0);
  @$pb.TagNumber(1)
  set keyword($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasKeyword() => $_has(0);
  @$pb.TagNumber(1)
  void clearKeyword() => $_clearField(1);

  @$pb.TagNumber(2)
  GroupType get type => $_getN(1);
  @$pb.TagNumber(2)
  set type(GroupType value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasType() => $_has(1);
  @$pb.TagNumber(2)
  void clearType() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get limit => $_getIZ(2);
  @$pb.TagNumber(3)
  set limit($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasLimit() => $_has(2);
  @$pb.TagNumber(3)
  void clearLimit() => $_clearField(3);
}

class JoinGroupRequest extends $pb.GeneratedMessage {
  factory JoinGroupRequest({
    UUID? groupId,
    $core.String? message,
  }) {
    final result = create();
    if (groupId != null) result.groupId = groupId;
    if (message != null) result.message = message;
    return result;
  }

  JoinGroupRequest._();

  factory JoinGroupRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory JoinGroupRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'JoinGroupRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'groupId', subBuilder: UUID.create)
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  JoinGroupRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  JoinGroupRequest copyWith(void Function(JoinGroupRequest) updates) =>
      super.copyWith((message) => updates(message as JoinGroupRequest))
          as JoinGroupRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static JoinGroupRequest create() => JoinGroupRequest._();
  @$core.override
  JoinGroupRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static JoinGroupRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<JoinGroupRequest>(create);
  static JoinGroupRequest? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get groupId => $_getN(0);
  @$pb.TagNumber(1)
  set groupId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasGroupId() => $_has(0);
  @$pb.TagNumber(1)
  void clearGroupId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureGroupId() => $_ensure(0);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => $_clearField(2);
}

class SendGroupMessageRequest extends $pb.GeneratedMessage {
  factory SendGroupMessageRequest({
    UUID? groupId,
    MessageSend? message,
  }) {
    final result = create();
    if (groupId != null) result.groupId = groupId;
    if (message != null) result.message = message;
    return result;
  }

  SendGroupMessageRequest._();

  factory SendGroupMessageRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory SendGroupMessageRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'SendGroupMessageRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'groupId', subBuilder: UUID.create)
    ..aOM<MessageSend>(2, _omitFieldNames ? '' : 'message',
        subBuilder: MessageSend.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SendGroupMessageRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SendGroupMessageRequest copyWith(
          void Function(SendGroupMessageRequest) updates) =>
      super.copyWith((message) => updates(message as SendGroupMessageRequest))
          as SendGroupMessageRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static SendGroupMessageRequest create() => SendGroupMessageRequest._();
  @$core.override
  SendGroupMessageRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static SendGroupMessageRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<SendGroupMessageRequest>(create);
  static SendGroupMessageRequest? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get groupId => $_getN(0);
  @$pb.TagNumber(1)
  set groupId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasGroupId() => $_has(0);
  @$pb.TagNumber(1)
  void clearGroupId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureGroupId() => $_ensure(0);

  @$pb.TagNumber(2)
  MessageSend get message => $_getN(1);
  @$pb.TagNumber(2)
  set message(MessageSend value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => $_clearField(2);
  @$pb.TagNumber(2)
  MessageSend ensureMessage() => $_ensure(1);
}

class GetGroupMessagesRequest extends $pb.GeneratedMessage {
  factory GetGroupMessagesRequest({
    UUID? groupId,
    UUID? beforeId,
    $core.int? limit,
  }) {
    final result = create();
    if (groupId != null) result.groupId = groupId;
    if (beforeId != null) result.beforeId = beforeId;
    if (limit != null) result.limit = limit;
    return result;
  }

  GetGroupMessagesRequest._();

  factory GetGroupMessagesRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory GetGroupMessagesRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'GetGroupMessagesRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'groupId', subBuilder: UUID.create)
    ..aOM<UUID>(2, _omitFieldNames ? '' : 'beforeId', subBuilder: UUID.create)
    ..aI(3, _omitFieldNames ? '' : 'limit')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GetGroupMessagesRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GetGroupMessagesRequest copyWith(
          void Function(GetGroupMessagesRequest) updates) =>
      super.copyWith((message) => updates(message as GetGroupMessagesRequest))
          as GetGroupMessagesRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GetGroupMessagesRequest create() => GetGroupMessagesRequest._();
  @$core.override
  GetGroupMessagesRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static GetGroupMessagesRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<GetGroupMessagesRequest>(create);
  static GetGroupMessagesRequest? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get groupId => $_getN(0);
  @$pb.TagNumber(1)
  set groupId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasGroupId() => $_has(0);
  @$pb.TagNumber(1)
  void clearGroupId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureGroupId() => $_ensure(0);

  @$pb.TagNumber(2)
  UUID get beforeId => $_getN(1);
  @$pb.TagNumber(2)
  set beforeId(UUID value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasBeforeId() => $_has(1);
  @$pb.TagNumber(2)
  void clearBeforeId() => $_clearField(2);
  @$pb.TagNumber(2)
  UUID ensureBeforeId() => $_ensure(1);

  @$pb.TagNumber(3)
  $core.int get limit => $_getIZ(2);
  @$pb.TagNumber(3)
  set limit($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasLimit() => $_has(2);
  @$pb.TagNumber(3)
  void clearLimit() => $_clearField(3);
}

class StreamGroupMessagesRequest extends $pb.GeneratedMessage {
  factory StreamGroupMessagesRequest({
    UUID? groupId,
    UUID? afterId,
  }) {
    final result = create();
    if (groupId != null) result.groupId = groupId;
    if (afterId != null) result.afterId = afterId;
    return result;
  }

  StreamGroupMessagesRequest._();

  factory StreamGroupMessagesRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory StreamGroupMessagesRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'StreamGroupMessagesRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'groupId', subBuilder: UUID.create)
    ..aOM<UUID>(2, _omitFieldNames ? '' : 'afterId', subBuilder: UUID.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StreamGroupMessagesRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StreamGroupMessagesRequest copyWith(
          void Function(StreamGroupMessagesRequest) updates) =>
      super.copyWith(
              (message) => updates(message as StreamGroupMessagesRequest))
          as StreamGroupMessagesRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static StreamGroupMessagesRequest create() => StreamGroupMessagesRequest._();
  @$core.override
  StreamGroupMessagesRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static StreamGroupMessagesRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<StreamGroupMessagesRequest>(create);
  static StreamGroupMessagesRequest? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get groupId => $_getN(0);
  @$pb.TagNumber(1)
  set groupId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasGroupId() => $_has(0);
  @$pb.TagNumber(1)
  void clearGroupId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureGroupId() => $_ensure(0);

  @$pb.TagNumber(2)
  UUID get afterId => $_getN(1);
  @$pb.TagNumber(2)
  set afterId(UUID value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasAfterId() => $_has(1);
  @$pb.TagNumber(2)
  void clearAfterId() => $_clearField(2);
  @$pb.TagNumber(2)
  UUID ensureAfterId() => $_ensure(1);
}

class RevokeMessageRequest extends $pb.GeneratedMessage {
  factory RevokeMessageRequest({
    UUID? messageId,
    UUID? groupId,
  }) {
    final result = create();
    if (messageId != null) result.messageId = messageId;
    if (groupId != null) result.groupId = groupId;
    return result;
  }

  RevokeMessageRequest._();

  factory RevokeMessageRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory RevokeMessageRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'RevokeMessageRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'messageId', subBuilder: UUID.create)
    ..aOM<UUID>(2, _omitFieldNames ? '' : 'groupId', subBuilder: UUID.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  RevokeMessageRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  RevokeMessageRequest copyWith(void Function(RevokeMessageRequest) updates) =>
      super.copyWith((message) => updates(message as RevokeMessageRequest))
          as RevokeMessageRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static RevokeMessageRequest create() => RevokeMessageRequest._();
  @$core.override
  RevokeMessageRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static RevokeMessageRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<RevokeMessageRequest>(create);
  static RevokeMessageRequest? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get messageId => $_getN(0);
  @$pb.TagNumber(1)
  set messageId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasMessageId() => $_has(0);
  @$pb.TagNumber(1)
  void clearMessageId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureMessageId() => $_ensure(0);

  @$pb.TagNumber(2)
  UUID get groupId => $_getN(1);
  @$pb.TagNumber(2)
  set groupId(UUID value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasGroupId() => $_has(1);
  @$pb.TagNumber(2)
  void clearGroupId() => $_clearField(2);
  @$pb.TagNumber(2)
  UUID ensureGroupId() => $_ensure(1);
}

class MarkMessagesReadRequest extends $pb.GeneratedMessage {
  factory MarkMessagesReadRequest({
    UUID? groupId,
    UUID? upToMessageId,
  }) {
    final result = create();
    if (groupId != null) result.groupId = groupId;
    if (upToMessageId != null) result.upToMessageId = upToMessageId;
    return result;
  }

  MarkMessagesReadRequest._();

  factory MarkMessagesReadRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory MarkMessagesReadRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MarkMessagesReadRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'groupId', subBuilder: UUID.create)
    ..aOM<UUID>(2, _omitFieldNames ? '' : 'upToMessageId',
        subBuilder: UUID.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MarkMessagesReadRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MarkMessagesReadRequest copyWith(
          void Function(MarkMessagesReadRequest) updates) =>
      super.copyWith((message) => updates(message as MarkMessagesReadRequest))
          as MarkMessagesReadRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MarkMessagesReadRequest create() => MarkMessagesReadRequest._();
  @$core.override
  MarkMessagesReadRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static MarkMessagesReadRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MarkMessagesReadRequest>(create);
  static MarkMessagesReadRequest? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get groupId => $_getN(0);
  @$pb.TagNumber(1)
  set groupId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasGroupId() => $_has(0);
  @$pb.TagNumber(1)
  void clearGroupId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureGroupId() => $_ensure(0);

  @$pb.TagNumber(2)
  UUID get upToMessageId => $_getN(1);
  @$pb.TagNumber(2)
  set upToMessageId(UUID value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasUpToMessageId() => $_has(1);
  @$pb.TagNumber(2)
  void clearUpToMessageId() => $_clearField(2);
  @$pb.TagNumber(2)
  UUID ensureUpToMessageId() => $_ensure(1);
}

class MarkMessagesReadResponse extends $pb.GeneratedMessage {
  factory MarkMessagesReadResponse({
    $core.int? updatedCount,
    UUID? upToMessageId,
  }) {
    final result = create();
    if (updatedCount != null) result.updatedCount = updatedCount;
    if (upToMessageId != null) result.upToMessageId = upToMessageId;
    return result;
  }

  MarkMessagesReadResponse._();

  factory MarkMessagesReadResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory MarkMessagesReadResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MarkMessagesReadResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aI(1, _omitFieldNames ? '' : 'updatedCount')
    ..aOM<UUID>(2, _omitFieldNames ? '' : 'upToMessageId',
        subBuilder: UUID.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MarkMessagesReadResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MarkMessagesReadResponse copyWith(
          void Function(MarkMessagesReadResponse) updates) =>
      super.copyWith((message) => updates(message as MarkMessagesReadResponse))
          as MarkMessagesReadResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MarkMessagesReadResponse create() => MarkMessagesReadResponse._();
  @$core.override
  MarkMessagesReadResponse createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static MarkMessagesReadResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MarkMessagesReadResponse>(create);
  static MarkMessagesReadResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get updatedCount => $_getIZ(0);
  @$pb.TagNumber(1)
  set updatedCount($core.int value) => $_setSignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUpdatedCount() => $_has(0);
  @$pb.TagNumber(1)
  void clearUpdatedCount() => $_clearField(1);

  @$pb.TagNumber(2)
  UUID get upToMessageId => $_getN(1);
  @$pb.TagNumber(2)
  set upToMessageId(UUID value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasUpToMessageId() => $_has(1);
  @$pb.TagNumber(2)
  void clearUpToMessageId() => $_clearField(2);
  @$pb.TagNumber(2)
  UUID ensureUpToMessageId() => $_ensure(1);
}

class GetPrivateMessagesRequest extends $pb.GeneratedMessage {
  factory GetPrivateMessagesRequest({
    UUID? friendId,
    UUID? beforeId,
    $core.int? limit,
  }) {
    final result = create();
    if (friendId != null) result.friendId = friendId;
    if (beforeId != null) result.beforeId = beforeId;
    if (limit != null) result.limit = limit;
    return result;
  }

  GetPrivateMessagesRequest._();

  factory GetPrivateMessagesRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory GetPrivateMessagesRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'GetPrivateMessagesRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.community'),
      createEmptyInstance: create)
    ..aOM<UUID>(1, _omitFieldNames ? '' : 'friendId', subBuilder: UUID.create)
    ..aOM<UUID>(2, _omitFieldNames ? '' : 'beforeId', subBuilder: UUID.create)
    ..aI(3, _omitFieldNames ? '' : 'limit')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GetPrivateMessagesRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GetPrivateMessagesRequest copyWith(
          void Function(GetPrivateMessagesRequest) updates) =>
      super.copyWith((message) => updates(message as GetPrivateMessagesRequest))
          as GetPrivateMessagesRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GetPrivateMessagesRequest create() => GetPrivateMessagesRequest._();
  @$core.override
  GetPrivateMessagesRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static GetPrivateMessagesRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<GetPrivateMessagesRequest>(create);
  static GetPrivateMessagesRequest? _defaultInstance;

  @$pb.TagNumber(1)
  UUID get friendId => $_getN(0);
  @$pb.TagNumber(1)
  set friendId(UUID value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasFriendId() => $_has(0);
  @$pb.TagNumber(1)
  void clearFriendId() => $_clearField(1);
  @$pb.TagNumber(1)
  UUID ensureFriendId() => $_ensure(0);

  @$pb.TagNumber(2)
  UUID get beforeId => $_getN(1);
  @$pb.TagNumber(2)
  set beforeId(UUID value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasBeforeId() => $_has(1);
  @$pb.TagNumber(2)
  void clearBeforeId() => $_clearField(2);
  @$pb.TagNumber(2)
  UUID ensureBeforeId() => $_ensure(1);

  @$pb.TagNumber(3)
  $core.int get limit => $_getIZ(2);
  @$pb.TagNumber(3)
  set limit($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasLimit() => $_has(2);
  @$pb.TagNumber(3)
  void clearLimit() => $_clearField(3);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
