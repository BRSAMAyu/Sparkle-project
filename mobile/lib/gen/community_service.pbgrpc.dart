// This is a generated file - do not edit.
//
// Generated from community_service.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:async' as $async;
import 'dart:core' as $core;

import 'package:grpc/service_api.dart' as $grpc;
import 'package:protobuf/protobuf.dart' as $pb;
import 'package:protobuf/well_known_types/google/protobuf/empty.pb.dart' as $1;

import 'community_service.pb.dart' as $0;

export 'community_service.pb.dart';

@$pb.GrpcServiceName('sparkle.community.CommunityService')
class CommunityServiceClient extends $grpc.Client {
  /// The hostname for this service.
  static const $core.String defaultHost = '';

  /// OAuth scopes needed for the client.
  static const $core.List<$core.String> oauthScopes = [
    '',
  ];

  CommunityServiceClient(super.channel, {super.options, super.interceptors});

  /// 好友系统
  $grpc.ResponseFuture<$0.FriendshipInfo> sendFriendRequest(
    $0.FriendRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$sendFriendRequest, request, options: options);
  }

  $grpc.ResponseFuture<$0.FriendshipInfo> respondToFriendRequest(
    $0.FriendResponse request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$respondToFriendRequest, request,
        options: options);
  }

  $grpc.ResponseStream<$0.FriendshipInfo> getFriends(
    $1.Empty request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(
        _$getFriends, $async.Stream.fromIterable([request]),
        options: options);
  }

  $grpc.ResponseStream<$0.FriendshipInfo> getPendingFriendRequests(
    $1.Empty request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(
        _$getPendingFriendRequests, $async.Stream.fromIterable([request]),
        options: options);
  }

  $grpc.ResponseFuture<$0.BlockUserInfo> blockUser(
    $0.BlockUserRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$blockUser, request, options: options);
  }

  $grpc.ResponseFuture<$1.Empty> unblockUser(
    $0.UUID request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$unblockUser, request, options: options);
  }

  $grpc.ResponseStream<$0.BlockUserInfo> getBlockedUsers(
    $1.Empty request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(
        _$getBlockedUsers, $async.Stream.fromIterable([request]),
        options: options);
  }

  /// 用户搜索
  $grpc.ResponseStream<$0.UserBrief> searchUsers(
    $0.SearchUsersRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(
        _$searchUsers, $async.Stream.fromIterable([request]),
        options: options);
  }

  $grpc.ResponseFuture<$1.Empty> updatePrivacySettings(
    $0.UserPrivacySettings request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$updatePrivacySettings, request, options: options);
  }

  $grpc.ResponseFuture<$0.UserPrivacySettings> getPrivacySettings(
    $1.Empty request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$getPrivacySettings, request, options: options);
  }

  /// 群组系统
  $grpc.ResponseFuture<$0.GroupInfo> createGroup(
    $0.GroupCreate request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$createGroup, request, options: options);
  }

  $grpc.ResponseFuture<$0.GroupInfo> getGroup(
    $0.UUID request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$getGroup, request, options: options);
  }

  $grpc.ResponseFuture<$0.GroupMemberInfo> joinGroup(
    $0.JoinGroupRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$joinGroup, request, options: options);
  }

  $grpc.ResponseFuture<$1.Empty> leaveGroup(
    $0.UUID request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$leaveGroup, request, options: options);
  }

  $grpc.ResponseStream<$0.GroupInfo> getMyGroups(
    $1.Empty request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(
        _$getMyGroups, $async.Stream.fromIterable([request]),
        options: options);
  }

  $grpc.ResponseStream<$0.GroupInfo> searchGroups(
    $0.SearchGroupsRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(
        _$searchGroups, $async.Stream.fromIterable([request]),
        options: options);
  }

  $grpc.ResponseStream<$0.GroupMemberInfo> getGroupMembers(
    $0.UUID request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(
        _$getGroupMembers, $async.Stream.fromIterable([request]),
        options: options);
  }

  /// 群消息系统
  $grpc.ResponseFuture<$0.MessageInfo> sendGroupMessage(
    $0.SendGroupMessageRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$sendGroupMessage, request, options: options);
  }

  $grpc.ResponseStream<$0.MessageInfo> getGroupMessages(
    $0.GetGroupMessagesRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(
        _$getGroupMessages, $async.Stream.fromIterable([request]),
        options: options);
  }

  $grpc.ResponseStream<$0.MessageInfo> streamGroupMessages(
    $0.StreamGroupMessagesRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(
        _$streamGroupMessages, $async.Stream.fromIterable([request]),
        options: options);
  }

  $grpc.ResponseFuture<$0.MessageInfo> revokeGroupMessage(
    $0.RevokeMessageRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$revokeGroupMessage, request, options: options);
  }

  $grpc.ResponseFuture<$0.MarkMessagesReadResponse> markMessagesRead(
    $0.MarkMessagesReadRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$markMessagesRead, request, options: options);
  }

  /// 私聊系统
  $grpc.ResponseFuture<$0.PrivateMessageInfo> sendPrivateMessage(
    $0.PrivateMessageSend request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$sendPrivateMessage, request, options: options);
  }

  $grpc.ResponseStream<$0.PrivateMessageInfo> getPrivateMessages(
    $0.GetPrivateMessagesRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(
        _$getPrivateMessages, $async.Stream.fromIterable([request]),
        options: options);
  }

  $grpc.ResponseFuture<$0.PrivateMessageInfo> revokePrivateMessage(
    $0.RevokeMessageRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$revokePrivateMessage, request, options: options);
  }

  /// 打卡系统
  $grpc.ResponseFuture<$0.CheckinResponse> checkin(
    $0.CheckinRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$checkin, request, options: options);
  }

  // method descriptors

  static final _$sendFriendRequest =
      $grpc.ClientMethod<$0.FriendRequest, $0.FriendshipInfo>(
          '/sparkle.community.CommunityService/SendFriendRequest',
          ($0.FriendRequest value) => value.writeToBuffer(),
          $0.FriendshipInfo.fromBuffer);
  static final _$respondToFriendRequest =
      $grpc.ClientMethod<$0.FriendResponse, $0.FriendshipInfo>(
          '/sparkle.community.CommunityService/RespondToFriendRequest',
          ($0.FriendResponse value) => value.writeToBuffer(),
          $0.FriendshipInfo.fromBuffer);
  static final _$getFriends = $grpc.ClientMethod<$1.Empty, $0.FriendshipInfo>(
      '/sparkle.community.CommunityService/GetFriends',
      ($1.Empty value) => value.writeToBuffer(),
      $0.FriendshipInfo.fromBuffer);
  static final _$getPendingFriendRequests =
      $grpc.ClientMethod<$1.Empty, $0.FriendshipInfo>(
          '/sparkle.community.CommunityService/GetPendingFriendRequests',
          ($1.Empty value) => value.writeToBuffer(),
          $0.FriendshipInfo.fromBuffer);
  static final _$blockUser =
      $grpc.ClientMethod<$0.BlockUserRequest, $0.BlockUserInfo>(
          '/sparkle.community.CommunityService/BlockUser',
          ($0.BlockUserRequest value) => value.writeToBuffer(),
          $0.BlockUserInfo.fromBuffer);
  static final _$unblockUser = $grpc.ClientMethod<$0.UUID, $1.Empty>(
      '/sparkle.community.CommunityService/UnblockUser',
      ($0.UUID value) => value.writeToBuffer(),
      $1.Empty.fromBuffer);
  static final _$getBlockedUsers =
      $grpc.ClientMethod<$1.Empty, $0.BlockUserInfo>(
          '/sparkle.community.CommunityService/GetBlockedUsers',
          ($1.Empty value) => value.writeToBuffer(),
          $0.BlockUserInfo.fromBuffer);
  static final _$searchUsers =
      $grpc.ClientMethod<$0.SearchUsersRequest, $0.UserBrief>(
          '/sparkle.community.CommunityService/SearchUsers',
          ($0.SearchUsersRequest value) => value.writeToBuffer(),
          $0.UserBrief.fromBuffer);
  static final _$updatePrivacySettings =
      $grpc.ClientMethod<$0.UserPrivacySettings, $1.Empty>(
          '/sparkle.community.CommunityService/UpdatePrivacySettings',
          ($0.UserPrivacySettings value) => value.writeToBuffer(),
          $1.Empty.fromBuffer);
  static final _$getPrivacySettings =
      $grpc.ClientMethod<$1.Empty, $0.UserPrivacySettings>(
          '/sparkle.community.CommunityService/GetPrivacySettings',
          ($1.Empty value) => value.writeToBuffer(),
          $0.UserPrivacySettings.fromBuffer);
  static final _$createGroup = $grpc.ClientMethod<$0.GroupCreate, $0.GroupInfo>(
      '/sparkle.community.CommunityService/CreateGroup',
      ($0.GroupCreate value) => value.writeToBuffer(),
      $0.GroupInfo.fromBuffer);
  static final _$getGroup = $grpc.ClientMethod<$0.UUID, $0.GroupInfo>(
      '/sparkle.community.CommunityService/GetGroup',
      ($0.UUID value) => value.writeToBuffer(),
      $0.GroupInfo.fromBuffer);
  static final _$joinGroup =
      $grpc.ClientMethod<$0.JoinGroupRequest, $0.GroupMemberInfo>(
          '/sparkle.community.CommunityService/JoinGroup',
          ($0.JoinGroupRequest value) => value.writeToBuffer(),
          $0.GroupMemberInfo.fromBuffer);
  static final _$leaveGroup = $grpc.ClientMethod<$0.UUID, $1.Empty>(
      '/sparkle.community.CommunityService/LeaveGroup',
      ($0.UUID value) => value.writeToBuffer(),
      $1.Empty.fromBuffer);
  static final _$getMyGroups = $grpc.ClientMethod<$1.Empty, $0.GroupInfo>(
      '/sparkle.community.CommunityService/GetMyGroups',
      ($1.Empty value) => value.writeToBuffer(),
      $0.GroupInfo.fromBuffer);
  static final _$searchGroups =
      $grpc.ClientMethod<$0.SearchGroupsRequest, $0.GroupInfo>(
          '/sparkle.community.CommunityService/SearchGroups',
          ($0.SearchGroupsRequest value) => value.writeToBuffer(),
          $0.GroupInfo.fromBuffer);
  static final _$getGroupMembers =
      $grpc.ClientMethod<$0.UUID, $0.GroupMemberInfo>(
          '/sparkle.community.CommunityService/GetGroupMembers',
          ($0.UUID value) => value.writeToBuffer(),
          $0.GroupMemberInfo.fromBuffer);
  static final _$sendGroupMessage =
      $grpc.ClientMethod<$0.SendGroupMessageRequest, $0.MessageInfo>(
          '/sparkle.community.CommunityService/SendGroupMessage',
          ($0.SendGroupMessageRequest value) => value.writeToBuffer(),
          $0.MessageInfo.fromBuffer);
  static final _$getGroupMessages =
      $grpc.ClientMethod<$0.GetGroupMessagesRequest, $0.MessageInfo>(
          '/sparkle.community.CommunityService/GetGroupMessages',
          ($0.GetGroupMessagesRequest value) => value.writeToBuffer(),
          $0.MessageInfo.fromBuffer);
  static final _$streamGroupMessages =
      $grpc.ClientMethod<$0.StreamGroupMessagesRequest, $0.MessageInfo>(
          '/sparkle.community.CommunityService/StreamGroupMessages',
          ($0.StreamGroupMessagesRequest value) => value.writeToBuffer(),
          $0.MessageInfo.fromBuffer);
  static final _$revokeGroupMessage =
      $grpc.ClientMethod<$0.RevokeMessageRequest, $0.MessageInfo>(
          '/sparkle.community.CommunityService/RevokeGroupMessage',
          ($0.RevokeMessageRequest value) => value.writeToBuffer(),
          $0.MessageInfo.fromBuffer);
  static final _$markMessagesRead = $grpc.ClientMethod<
          $0.MarkMessagesReadRequest, $0.MarkMessagesReadResponse>(
      '/sparkle.community.CommunityService/MarkMessagesRead',
      ($0.MarkMessagesReadRequest value) => value.writeToBuffer(),
      $0.MarkMessagesReadResponse.fromBuffer);
  static final _$sendPrivateMessage =
      $grpc.ClientMethod<$0.PrivateMessageSend, $0.PrivateMessageInfo>(
          '/sparkle.community.CommunityService/SendPrivateMessage',
          ($0.PrivateMessageSend value) => value.writeToBuffer(),
          $0.PrivateMessageInfo.fromBuffer);
  static final _$getPrivateMessages =
      $grpc.ClientMethod<$0.GetPrivateMessagesRequest, $0.PrivateMessageInfo>(
          '/sparkle.community.CommunityService/GetPrivateMessages',
          ($0.GetPrivateMessagesRequest value) => value.writeToBuffer(),
          $0.PrivateMessageInfo.fromBuffer);
  static final _$revokePrivateMessage =
      $grpc.ClientMethod<$0.RevokeMessageRequest, $0.PrivateMessageInfo>(
          '/sparkle.community.CommunityService/RevokePrivateMessage',
          ($0.RevokeMessageRequest value) => value.writeToBuffer(),
          $0.PrivateMessageInfo.fromBuffer);
  static final _$checkin =
      $grpc.ClientMethod<$0.CheckinRequest, $0.CheckinResponse>(
          '/sparkle.community.CommunityService/Checkin',
          ($0.CheckinRequest value) => value.writeToBuffer(),
          $0.CheckinResponse.fromBuffer);
}

@$pb.GrpcServiceName('sparkle.community.CommunityService')
abstract class CommunityServiceBase extends $grpc.Service {
  $core.String get $name => 'sparkle.community.CommunityService';

  CommunityServiceBase() {
    $addMethod($grpc.ServiceMethod<$0.FriendRequest, $0.FriendshipInfo>(
        'SendFriendRequest',
        sendFriendRequest_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.FriendRequest.fromBuffer(value),
        ($0.FriendshipInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.FriendResponse, $0.FriendshipInfo>(
        'RespondToFriendRequest',
        respondToFriendRequest_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.FriendResponse.fromBuffer(value),
        ($0.FriendshipInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$1.Empty, $0.FriendshipInfo>(
        'GetFriends',
        getFriends_Pre,
        false,
        true,
        ($core.List<$core.int> value) => $1.Empty.fromBuffer(value),
        ($0.FriendshipInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$1.Empty, $0.FriendshipInfo>(
        'GetPendingFriendRequests',
        getPendingFriendRequests_Pre,
        false,
        true,
        ($core.List<$core.int> value) => $1.Empty.fromBuffer(value),
        ($0.FriendshipInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.BlockUserRequest, $0.BlockUserInfo>(
        'BlockUser',
        blockUser_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.BlockUserRequest.fromBuffer(value),
        ($0.BlockUserInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.UUID, $1.Empty>(
        'UnblockUser',
        unblockUser_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.UUID.fromBuffer(value),
        ($1.Empty value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$1.Empty, $0.BlockUserInfo>(
        'GetBlockedUsers',
        getBlockedUsers_Pre,
        false,
        true,
        ($core.List<$core.int> value) => $1.Empty.fromBuffer(value),
        ($0.BlockUserInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.SearchUsersRequest, $0.UserBrief>(
        'SearchUsers',
        searchUsers_Pre,
        false,
        true,
        ($core.List<$core.int> value) =>
            $0.SearchUsersRequest.fromBuffer(value),
        ($0.UserBrief value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.UserPrivacySettings, $1.Empty>(
        'UpdatePrivacySettings',
        updatePrivacySettings_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.UserPrivacySettings.fromBuffer(value),
        ($1.Empty value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$1.Empty, $0.UserPrivacySettings>(
        'GetPrivacySettings',
        getPrivacySettings_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $1.Empty.fromBuffer(value),
        ($0.UserPrivacySettings value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.GroupCreate, $0.GroupInfo>(
        'CreateGroup',
        createGroup_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.GroupCreate.fromBuffer(value),
        ($0.GroupInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.UUID, $0.GroupInfo>(
        'GetGroup',
        getGroup_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.UUID.fromBuffer(value),
        ($0.GroupInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.JoinGroupRequest, $0.GroupMemberInfo>(
        'JoinGroup',
        joinGroup_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.JoinGroupRequest.fromBuffer(value),
        ($0.GroupMemberInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.UUID, $1.Empty>(
        'LeaveGroup',
        leaveGroup_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.UUID.fromBuffer(value),
        ($1.Empty value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$1.Empty, $0.GroupInfo>(
        'GetMyGroups',
        getMyGroups_Pre,
        false,
        true,
        ($core.List<$core.int> value) => $1.Empty.fromBuffer(value),
        ($0.GroupInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.SearchGroupsRequest, $0.GroupInfo>(
        'SearchGroups',
        searchGroups_Pre,
        false,
        true,
        ($core.List<$core.int> value) =>
            $0.SearchGroupsRequest.fromBuffer(value),
        ($0.GroupInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.UUID, $0.GroupMemberInfo>(
        'GetGroupMembers',
        getGroupMembers_Pre,
        false,
        true,
        ($core.List<$core.int> value) => $0.UUID.fromBuffer(value),
        ($0.GroupMemberInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.SendGroupMessageRequest, $0.MessageInfo>(
        'SendGroupMessage',
        sendGroupMessage_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.SendGroupMessageRequest.fromBuffer(value),
        ($0.MessageInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.GetGroupMessagesRequest, $0.MessageInfo>(
        'GetGroupMessages',
        getGroupMessages_Pre,
        false,
        true,
        ($core.List<$core.int> value) =>
            $0.GetGroupMessagesRequest.fromBuffer(value),
        ($0.MessageInfo value) => value.writeToBuffer()));
    $addMethod(
        $grpc.ServiceMethod<$0.StreamGroupMessagesRequest, $0.MessageInfo>(
            'StreamGroupMessages',
            streamGroupMessages_Pre,
            false,
            true,
            ($core.List<$core.int> value) =>
                $0.StreamGroupMessagesRequest.fromBuffer(value),
            ($0.MessageInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.RevokeMessageRequest, $0.MessageInfo>(
        'RevokeGroupMessage',
        revokeGroupMessage_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.RevokeMessageRequest.fromBuffer(value),
        ($0.MessageInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.MarkMessagesReadRequest,
            $0.MarkMessagesReadResponse>(
        'MarkMessagesRead',
        markMessagesRead_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.MarkMessagesReadRequest.fromBuffer(value),
        ($0.MarkMessagesReadResponse value) => value.writeToBuffer()));
    $addMethod(
        $grpc.ServiceMethod<$0.PrivateMessageSend, $0.PrivateMessageInfo>(
            'SendPrivateMessage',
            sendPrivateMessage_Pre,
            false,
            false,
            ($core.List<$core.int> value) =>
                $0.PrivateMessageSend.fromBuffer(value),
            ($0.PrivateMessageInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.GetPrivateMessagesRequest,
            $0.PrivateMessageInfo>(
        'GetPrivateMessages',
        getPrivateMessages_Pre,
        false,
        true,
        ($core.List<$core.int> value) =>
            $0.GetPrivateMessagesRequest.fromBuffer(value),
        ($0.PrivateMessageInfo value) => value.writeToBuffer()));
    $addMethod(
        $grpc.ServiceMethod<$0.RevokeMessageRequest, $0.PrivateMessageInfo>(
            'RevokePrivateMessage',
            revokePrivateMessage_Pre,
            false,
            false,
            ($core.List<$core.int> value) =>
                $0.RevokeMessageRequest.fromBuffer(value),
            ($0.PrivateMessageInfo value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.CheckinRequest, $0.CheckinResponse>(
        'Checkin',
        checkin_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.CheckinRequest.fromBuffer(value),
        ($0.CheckinResponse value) => value.writeToBuffer()));
  }

  $async.Future<$0.FriendshipInfo> sendFriendRequest_Pre(
      $grpc.ServiceCall $call, $async.Future<$0.FriendRequest> $request) async {
    return sendFriendRequest($call, await $request);
  }

  $async.Future<$0.FriendshipInfo> sendFriendRequest(
      $grpc.ServiceCall call, $0.FriendRequest request);

  $async.Future<$0.FriendshipInfo> respondToFriendRequest_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.FriendResponse> $request) async {
    return respondToFriendRequest($call, await $request);
  }

  $async.Future<$0.FriendshipInfo> respondToFriendRequest(
      $grpc.ServiceCall call, $0.FriendResponse request);

  $async.Stream<$0.FriendshipInfo> getFriends_Pre(
      $grpc.ServiceCall $call, $async.Future<$1.Empty> $request) async* {
    yield* getFriends($call, await $request);
  }

  $async.Stream<$0.FriendshipInfo> getFriends(
      $grpc.ServiceCall call, $1.Empty request);

  $async.Stream<$0.FriendshipInfo> getPendingFriendRequests_Pre(
      $grpc.ServiceCall $call, $async.Future<$1.Empty> $request) async* {
    yield* getPendingFriendRequests($call, await $request);
  }

  $async.Stream<$0.FriendshipInfo> getPendingFriendRequests(
      $grpc.ServiceCall call, $1.Empty request);

  $async.Future<$0.BlockUserInfo> blockUser_Pre($grpc.ServiceCall $call,
      $async.Future<$0.BlockUserRequest> $request) async {
    return blockUser($call, await $request);
  }

  $async.Future<$0.BlockUserInfo> blockUser(
      $grpc.ServiceCall call, $0.BlockUserRequest request);

  $async.Future<$1.Empty> unblockUser_Pre(
      $grpc.ServiceCall $call, $async.Future<$0.UUID> $request) async {
    return unblockUser($call, await $request);
  }

  $async.Future<$1.Empty> unblockUser($grpc.ServiceCall call, $0.UUID request);

  $async.Stream<$0.BlockUserInfo> getBlockedUsers_Pre(
      $grpc.ServiceCall $call, $async.Future<$1.Empty> $request) async* {
    yield* getBlockedUsers($call, await $request);
  }

  $async.Stream<$0.BlockUserInfo> getBlockedUsers(
      $grpc.ServiceCall call, $1.Empty request);

  $async.Stream<$0.UserBrief> searchUsers_Pre($grpc.ServiceCall $call,
      $async.Future<$0.SearchUsersRequest> $request) async* {
    yield* searchUsers($call, await $request);
  }

  $async.Stream<$0.UserBrief> searchUsers(
      $grpc.ServiceCall call, $0.SearchUsersRequest request);

  $async.Future<$1.Empty> updatePrivacySettings_Pre($grpc.ServiceCall $call,
      $async.Future<$0.UserPrivacySettings> $request) async {
    return updatePrivacySettings($call, await $request);
  }

  $async.Future<$1.Empty> updatePrivacySettings(
      $grpc.ServiceCall call, $0.UserPrivacySettings request);

  $async.Future<$0.UserPrivacySettings> getPrivacySettings_Pre(
      $grpc.ServiceCall $call, $async.Future<$1.Empty> $request) async {
    return getPrivacySettings($call, await $request);
  }

  $async.Future<$0.UserPrivacySettings> getPrivacySettings(
      $grpc.ServiceCall call, $1.Empty request);

  $async.Future<$0.GroupInfo> createGroup_Pre(
      $grpc.ServiceCall $call, $async.Future<$0.GroupCreate> $request) async {
    return createGroup($call, await $request);
  }

  $async.Future<$0.GroupInfo> createGroup(
      $grpc.ServiceCall call, $0.GroupCreate request);

  $async.Future<$0.GroupInfo> getGroup_Pre(
      $grpc.ServiceCall $call, $async.Future<$0.UUID> $request) async {
    return getGroup($call, await $request);
  }

  $async.Future<$0.GroupInfo> getGroup($grpc.ServiceCall call, $0.UUID request);

  $async.Future<$0.GroupMemberInfo> joinGroup_Pre($grpc.ServiceCall $call,
      $async.Future<$0.JoinGroupRequest> $request) async {
    return joinGroup($call, await $request);
  }

  $async.Future<$0.GroupMemberInfo> joinGroup(
      $grpc.ServiceCall call, $0.JoinGroupRequest request);

  $async.Future<$1.Empty> leaveGroup_Pre(
      $grpc.ServiceCall $call, $async.Future<$0.UUID> $request) async {
    return leaveGroup($call, await $request);
  }

  $async.Future<$1.Empty> leaveGroup($grpc.ServiceCall call, $0.UUID request);

  $async.Stream<$0.GroupInfo> getMyGroups_Pre(
      $grpc.ServiceCall $call, $async.Future<$1.Empty> $request) async* {
    yield* getMyGroups($call, await $request);
  }

  $async.Stream<$0.GroupInfo> getMyGroups(
      $grpc.ServiceCall call, $1.Empty request);

  $async.Stream<$0.GroupInfo> searchGroups_Pre($grpc.ServiceCall $call,
      $async.Future<$0.SearchGroupsRequest> $request) async* {
    yield* searchGroups($call, await $request);
  }

  $async.Stream<$0.GroupInfo> searchGroups(
      $grpc.ServiceCall call, $0.SearchGroupsRequest request);

  $async.Stream<$0.GroupMemberInfo> getGroupMembers_Pre(
      $grpc.ServiceCall $call, $async.Future<$0.UUID> $request) async* {
    yield* getGroupMembers($call, await $request);
  }

  $async.Stream<$0.GroupMemberInfo> getGroupMembers(
      $grpc.ServiceCall call, $0.UUID request);

  $async.Future<$0.MessageInfo> sendGroupMessage_Pre($grpc.ServiceCall $call,
      $async.Future<$0.SendGroupMessageRequest> $request) async {
    return sendGroupMessage($call, await $request);
  }

  $async.Future<$0.MessageInfo> sendGroupMessage(
      $grpc.ServiceCall call, $0.SendGroupMessageRequest request);

  $async.Stream<$0.MessageInfo> getGroupMessages_Pre($grpc.ServiceCall $call,
      $async.Future<$0.GetGroupMessagesRequest> $request) async* {
    yield* getGroupMessages($call, await $request);
  }

  $async.Stream<$0.MessageInfo> getGroupMessages(
      $grpc.ServiceCall call, $0.GetGroupMessagesRequest request);

  $async.Stream<$0.MessageInfo> streamGroupMessages_Pre($grpc.ServiceCall $call,
      $async.Future<$0.StreamGroupMessagesRequest> $request) async* {
    yield* streamGroupMessages($call, await $request);
  }

  $async.Stream<$0.MessageInfo> streamGroupMessages(
      $grpc.ServiceCall call, $0.StreamGroupMessagesRequest request);

  $async.Future<$0.MessageInfo> revokeGroupMessage_Pre($grpc.ServiceCall $call,
      $async.Future<$0.RevokeMessageRequest> $request) async {
    return revokeGroupMessage($call, await $request);
  }

  $async.Future<$0.MessageInfo> revokeGroupMessage(
      $grpc.ServiceCall call, $0.RevokeMessageRequest request);

  $async.Future<$0.MarkMessagesReadResponse> markMessagesRead_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.MarkMessagesReadRequest> $request) async {
    return markMessagesRead($call, await $request);
  }

  $async.Future<$0.MarkMessagesReadResponse> markMessagesRead(
      $grpc.ServiceCall call, $0.MarkMessagesReadRequest request);

  $async.Future<$0.PrivateMessageInfo> sendPrivateMessage_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.PrivateMessageSend> $request) async {
    return sendPrivateMessage($call, await $request);
  }

  $async.Future<$0.PrivateMessageInfo> sendPrivateMessage(
      $grpc.ServiceCall call, $0.PrivateMessageSend request);

  $async.Stream<$0.PrivateMessageInfo> getPrivateMessages_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.GetPrivateMessagesRequest> $request) async* {
    yield* getPrivateMessages($call, await $request);
  }

  $async.Stream<$0.PrivateMessageInfo> getPrivateMessages(
      $grpc.ServiceCall call, $0.GetPrivateMessagesRequest request);

  $async.Future<$0.PrivateMessageInfo> revokePrivateMessage_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.RevokeMessageRequest> $request) async {
    return revokePrivateMessage($call, await $request);
  }

  $async.Future<$0.PrivateMessageInfo> revokePrivateMessage(
      $grpc.ServiceCall call, $0.RevokeMessageRequest request);

  $async.Future<$0.CheckinResponse> checkin_Pre($grpc.ServiceCall $call,
      $async.Future<$0.CheckinRequest> $request) async {
    return checkin($call, await $request);
  }

  $async.Future<$0.CheckinResponse> checkin(
      $grpc.ServiceCall call, $0.CheckinRequest request);
}
