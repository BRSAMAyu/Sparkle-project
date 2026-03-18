import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/models/community_models.dart';
import 'package:sparkle/features/community/data/repositories/mock_community_repository.dart';

final communityRepositoryProvider = Provider<CommunityRepository>((ref) {
  // 🔧 Demo 模式下使用 Mock Repository
  if (DemoDataService.isDemoMode) {
    return MockCommunityRepository();
  }

  final apiClient = ref.watch(apiClientProvider);
  return CommunityRepository(apiClient);
});

class CommunityRepository {
  CommunityRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<List<Post>> getFeed({int page = 1, int limit = 20}) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.communityFeed,
        queryParameters: {'page': page, 'limit': limit},
      );

      if (response.statusCode == 200) {
        final data = ApiResponseParser.unwrapList(response.data, action: 'getFeed');
        return data.map((e) => Post.fromJson(e as Map<String, dynamic>)).toList();
      }
      return [];
    } catch (e) {
      // Feed endpoint not yet implemented on backend — return empty list gracefully
      return [];
    }
  }

  Future<String> createPost(CreatePostRequest request) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.communityPosts,
      data: request.toJson(),
    );

    if (response.statusCode == 201) {
      final data = ApiResponseParser.unwrapMap(response.data, action: 'createPost');
      return data['id'] as String;
    }
    throw Exception('Failed to create post');
  }

  Future<void> likePost(String postId, String userId) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.communityPostLike(postId),
      data: {'user_id': userId},
    );
  }

  Future<List<FriendshipInfo>> getFriends(
      {int limit = 50, int offset = 0,}) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.friends,
      queryParameters: {'limit': limit, 'offset': offset},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'getFriends');
      return data
          .map((e) => FriendshipInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load friends');
  }

  Future<List<FriendshipInfo>> getPendingRequests() async {
    final response = await _apiClient.get<dynamic>(ApiEndpoints.friendsPending);
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'getPendingRequests');
      return data
          .map((e) => FriendshipInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load pending requests');
  }

  Future<List<FriendRecommendation>> getFriendRecommendations(
      {int limit = 10,}) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.friendsRecommendations,
      queryParameters: {'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'getFriendRecommendations');
      return data
          .map((e) => FriendRecommendation.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load recommendations');
  }

  Future<void> sendFriendRequest(String targetUserId, {String? message}) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.friendRequest,
      data: {
        'target_user_id': targetUserId,
        if (message != null && message.isNotEmpty) 'message': message,
      },
    );
  }

  Future<void> respondToRequest(String friendshipId, bool accept) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.friendRespond,
      data: {
        'friendship_id': friendshipId,
        'accept': accept,
      },
    );
  }

  Future<List<UserBrief>> searchUsers(String keyword, {int limit = 20}) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.searchUsers,
      queryParameters: {'keyword': keyword, 'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'searchUsers');
      return data
          .map((e) => UserBrief.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to search users');
  }

  Future<List<GroupListItem>> getMyGroups() async {
    final response = await _apiClient.get<dynamic>(ApiEndpoints.groups);
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'getMyGroups');
      return data
          .map((e) => GroupListItem.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load groups');
  }

  Future<GroupInfo> getGroup(String groupId) async {
    final response = await _apiClient.get<dynamic>(ApiEndpoints.group(groupId));
    if (response.statusCode == 200) {
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getGroup');
      return GroupInfo.fromJson(payload);
    }
    throw Exception('Failed to load group');
  }

  Future<GroupInfo> createGroup(GroupCreate group) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.groups,
      data: group.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'createGroup');
      return GroupInfo.fromJson(payload);
    }
    throw Exception('Failed to create group');
  }

  Future<void> joinGroup(String groupId) async {
    await _apiClient.post<dynamic>(ApiEndpoints.groupJoin(groupId));
  }

  Future<void> leaveGroup(String groupId) async {
    await _apiClient.post<dynamic>(ApiEndpoints.groupLeave(groupId));
  }

  Future<List<GroupListItem>> searchGroups({
    String? keyword,
    GroupType? type,
    List<String>? tags,
    int limit = 20,
  }) async {
    final query = <String, dynamic>{
      if (keyword != null && keyword.isNotEmpty) 'keyword': keyword,
      if (type != null) 'group_type': type.name,
      if (tags != null && tags.isNotEmpty) 'tags': tags,
      'limit': limit,
    };
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupsSearch,
      queryParameters: query,
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'searchGroups');
      return data.map((e) => GroupListItem.fromJson(e as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to search groups');
  }

  Future<List<GroupRecommendationItem>> getGroupRecommendations({
    int limit = 20,
    int cursor = 0,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupsRecommendations,
      queryParameters: {'limit': limit, 'cursor': cursor},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getGroupRecommendations',
      );
      return data
          .map((e) => GroupRecommendationItem.fromJson(
              e as Map<String, dynamic>,),)
          .toList();
    }
    throw Exception('Failed to load group recommendations');
  }

  Future<void> sendGroupRecommendationFeedback({
    required String groupId,
    required String action,
    required String source,
    List<String>? reasonTypes,
  }) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.groupsRecommendationsFeedback,
      data: {
        'group_id': groupId,
        'action': action,
        'source': source,
        if (reasonTypes != null) 'reason_types': reasonTypes,
      },
    );
  }

  Future<List<GroupMemberInfo>> getGroupMembers(String groupId) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupMembers(groupId),
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'getGroupMembers');
      return data.map((e) => GroupMemberInfo.fromJson(e as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to load group members');
  }

  Future<void> kickMember(String groupId, String userId) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.groupMemberKick(groupId, userId),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to kick member');
    }
  }

  Future<void> promoteMember(String groupId, String userId) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.groupMemberPromote(groupId, userId),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to promote member');
    }
  }

  Future<void> demoteMember(String groupId, String userId) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.groupMemberDemote(groupId, userId),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to demote member');
    }
  }

  Future<void> transferOwnership(String groupId, String userId) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.groupTransferOwnership(groupId, userId),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to transfer ownership');
    }
  }

  Future<UserBrief> getUserProfile(String userId) async {
    final response = await _apiClient.get<dynamic>(ApiEndpoints.user(userId));
    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'getUserProfile');
      return UserBrief.fromJson(data);
    }
    throw Exception('Failed to load user profile');
  }

  Future<void> updateAnnouncement(String groupId, String? announcement) async {
    final response = await _apiClient.put<dynamic>(
      ApiEndpoints.groupAnnouncement(groupId),
      data: {'announcement': announcement},
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to update announcement');
    }
  }

  Future<List<MessageInfo>> getMessages(String groupId,
      {String? beforeId, int limit = 50,}) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupMessages(groupId),
      queryParameters: {
        if (beforeId != null) 'before_id': beforeId,
        'limit': limit,
      },
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'getMessages');
      return data.map((e) => MessageInfo.fromJson(e as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to load group messages');
  }

  Future<MessageInfo> sendMessage(
    String groupId, {
    required MessageType type,
    String? content,
    Map<String, dynamic>? contentData,
    String? replyToId,
    String? threadRootId,
    List<String>? mentionUserIds,
    String? nonce,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.groupMessages(groupId),
      data: {
        'message_type': _messageTypeToApi(type),
        if (content != null) 'content': content,
        if (contentData != null) 'content_data': contentData,
        if (replyToId != null) 'reply_to_id': replyToId,
        if (threadRootId != null) 'thread_root_id': threadRootId,
        if (mentionUserIds != null) 'mention_user_ids': mentionUserIds,
        if (nonce != null) 'nonce': nonce,
      },
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'sendMessage');
      return MessageInfo.fromJson(payload);
    }
    throw Exception('Failed to send group message');
  }

  Future<void> revokeGroupMessage(String groupId, String messageId) async {
    await _apiClient.post<dynamic>(ApiEndpoints.groupMessageRevoke(groupId, messageId));
  }

  Future<MessageInfo> editGroupMessage(
    String groupId,
    String messageId, {
    String? content,
    Map<String, dynamic>? contentData,
    List<String>? mentionUserIds,
  }) async {
    final response = await _apiClient.patch<dynamic>(
      ApiEndpoints.groupMessageEdit(groupId, messageId),
      data: {
        if (content != null) 'content': content,
        if (contentData != null) 'content_data': contentData,
        if (mentionUserIds != null) 'mention_user_ids': mentionUserIds,
      },
    );
    if (response.statusCode == 200) {
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'editGroupMessage');
      return MessageInfo.fromJson(payload);
    }
    throw Exception('Failed to edit group message');
  }

  Future<MessageInfo> updateGroupReaction(
    String groupId,
    String messageId, {
    required String emoji,
    required String userId,
    required bool isAdd,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.groupMessageReactions(groupId, messageId),
      data: {
        'emoji': emoji,
        'action': isAdd ? 'add' : 'remove',
      },
    );
    if (response.statusCode == 200) {
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'updateGroupReaction');
      return MessageInfo.fromJson(payload);
    }
    throw Exception('Failed to update group reaction');
  }

  Future<List<MessageInfo>> searchGroupMessages(String groupId, String keyword,
      {int limit = 50,}) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupMessagesSearch(groupId),
      queryParameters: {'keyword': keyword, 'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'searchGroupMessages');
      return data.map((e) => MessageInfo.fromJson(e as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to search group messages');
  }

  Future<List<MessageInfo>> getThreadMessages(
      String groupId, String threadRootId,
      {int limit = 100,}) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupThreadMessages(groupId, threadRootId),
      queryParameters: {'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'getThreadMessages');
      return data.map((e) => MessageInfo.fromJson(e as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to load thread messages');
  }

  Future<int> markGroupMessagesRead(
    String groupId, {
    required String upToMessageId,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.groupMessagesRead(groupId),
      data: {'up_to_message_id': upToMessageId},
    );
    if (response.statusCode == 200) {
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'markGroupMessagesRead',
      );
      return payload['updated_count'] as int? ?? 0;
    }
    throw Exception('Failed to mark group messages as read');
  }

  Future<List<PrivateMessageInfo>> getPrivateMessages(String friendId,
      {String? beforeId, int limit = 50,}) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.privateMessages(friendId),
      queryParameters: {
        if (beforeId != null) 'before_id': beforeId,
        'limit': limit,
      },
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'getPrivateMessages');
      return data.map((e) => PrivateMessageInfo.fromJson(e as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to load private messages');
  }

  Future<PrivateMessageInfo> sendPrivateMessage(
      PrivateMessageSend message,) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.sendPrivateMessage,
      data: message.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'sendPrivateMessage');
      return PrivateMessageInfo.fromJson(payload);
    }
    throw Exception('Failed to send private message');
  }

  Future<void> revokePrivateMessage(String messageId) async {
    await _apiClient.post<dynamic>(ApiEndpoints.revokePrivateMessage(messageId));
  }

  Future<PrivateMessageInfo> editPrivateMessage(
    String messageId, {
    String? content,
    Map<String, dynamic>? contentData,
    List<String>? mentionUserIds,
  }) async {
    final response = await _apiClient.patch<dynamic>(
      ApiEndpoints.editPrivateMessage(messageId),
      data: {
        if (content != null) 'content': content,
        if (contentData != null) 'content_data': contentData,
        if (mentionUserIds != null) 'mention_user_ids': mentionUserIds,
      },
    );
    if (response.statusCode == 200) {
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'editPrivateMessage');
      return PrivateMessageInfo.fromJson(payload);
    }
    throw Exception('Failed to edit private message');
  }

  Future<PrivateMessageInfo> updatePrivateReaction(
    String messageId, {
    required String emoji,
    required String userId,
    required bool isAdd,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.privateMessageReactions(messageId),
      data: {
        'emoji': emoji,
        'action': isAdd ? 'add' : 'remove',
      },
    );
    if (response.statusCode == 200) {
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'updatePrivateReaction');
      return PrivateMessageInfo.fromJson(payload);
    }
    throw Exception('Failed to update private reaction');
  }

  Future<List<PrivateMessageInfo>> searchPrivateMessages(
      String friendId, String keyword,
      {int limit = 50,}) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.privateMessagesSearch(friendId),
      queryParameters: {'keyword': keyword, 'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'searchPrivateMessages');
      return data.map((e) => PrivateMessageInfo.fromJson(e as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to search private messages');
  }

  Future<CheckinResponse> checkin(
    String groupId, {
    required int todayDurationMinutes,
    String? message,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.checkin,
      data: {
        'group_id': groupId,
        'today_duration_minutes': todayDurationMinutes,
        if (message != null && message.isNotEmpty) 'message': message,
      },
    );
    if (response.statusCode == 200) {
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'checkin');
      return CheckinResponse.fromJson(payload);
    }
    throw Exception('Failed to check in');
  }

  Future<List<GroupTaskInfo>> getGroupTasks(String groupId) async {
    final response = await _apiClient.get<dynamic>(ApiEndpoints.groupTasks(groupId));
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data, action: 'getGroupTasks');
      return data.map((e) => GroupTaskInfo.fromJson(e as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to load group tasks');
  }

  Future<GroupTaskInfo> createGroupTask(
      String groupId, GroupTaskCreate task,) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.groupTasks(groupId),
      data: task.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'createGroupTask');
      return GroupTaskInfo.fromJson(payload);
    }
    throw Exception('Failed to create group task');
  }

  Future<void> claimTask(String taskId) async {
    await _apiClient.post<dynamic>(ApiEndpoints.claimTask(taskId));
  }

  Future<GroupFlameStatus> getFlameStatus(String groupId) async {
    final response = await _apiClient.get<dynamic>(ApiEndpoints.groupFlame(groupId));
    if (response.statusCode == 200) {
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getFlameStatus');
      return GroupFlameStatus.fromJson(payload);
    }
    throw Exception('Failed to load flame status');
  }

  Future<void> updateStatus(UserStatus status) async {
    await _apiClient.put<dynamic>(
      ApiEndpoints.userStatus,
      data: {'status': status.name},
    );
  }

  // ── Message Favorites (Phase 1a) ──────────────────────────────────────────

  Future<void> addFavorite(
    String? groupMessageId,
    String? privateMessageId, {
    String? note,
    List<String>? tags,
  }) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.messageFavorites,
      data: {
        if (groupMessageId != null) 'group_message_id': groupMessageId,
        if (privateMessageId != null) 'private_message_id': privateMessageId,
        if (note != null && note.isNotEmpty) 'note': note,
        if (tags != null && tags.isNotEmpty) 'tags': tags,
      },
    );
  }

  Future<List<MessageFavoriteInfo>> getFavorites({
    String? tag,
    int limit = 20,
    int offset = 0,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.messageFavorites,
      queryParameters: {
        if (tag != null) 'tag': tag,
        'limit': limit,
        'offset': offset,
      },
    );
    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'getFavorites');
      return data
          .map((e) => MessageFavoriteInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load favorites');
  }

  Future<void> removeFavorite(String favoriteId) async {
    await _apiClient.delete<dynamic>(ApiEndpoints.messageFavorite(favoriteId));
  }

  // ── Message Forward (Phase 1b) ─────────────────────────────────────────────

  Future<void> forwardMessage(
    String messageId,
    String sourceType, {
    String? targetGroupId,
    String? targetUserId,
    String? comment,
  }) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.messageForward,
      data: {
        'source_message_id': messageId,
        'source_type': sourceType,
        if (targetGroupId != null) 'target_group_id': targetGroupId,
        if (targetUserId != null) 'target_user_id': targetUserId,
        if (comment != null && comment.isNotEmpty) 'comment': comment,
      },
    );
  }

  // ── Message Report (Phase 1c) ──────────────────────────────────────────────

  Future<void> reportMessage(
    String messageId,
    ReportReason reason, {
    String? description,
  }) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.messageReports,
      data: {
        'message_id': messageId,
        'reason': _reportReasonToApi(reason),
        if (description != null && description.isNotEmpty)
          'description': description,
      },
    );
  }

  // ── Group Member Moderation (Phase 2a) ────────────────────────────────────

  Future<void> muteMember(
    String groupId,
    String userId,
    int durationMinutes, {
    String? reason,
  }) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.groupMemberMute(groupId, userId),
      data: {
        'duration_minutes': durationMinutes,
        if (reason != null && reason.isNotEmpty) 'reason': reason,
      },
    );
  }

  Future<void> unmuteMember(String groupId, String userId) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.groupMemberUnmute(groupId, userId),
    );
  }

  Future<void> warnMember(
    String groupId,
    String userId,
    String reason,
  ) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.groupMemberWarn(groupId, userId),
      data: {'reason': reason},
    );
  }

  // ── Group Moderation Settings (Phase 2b) ──────────────────────────────────

  Future<GroupModerationSettings> getModerationSettings(String groupId) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupModerationSettings(groupId),
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapMap(
          response.data, action: 'getModerationSettings',);
      return GroupModerationSettings.fromJson(data);
    }
    throw Exception('Failed to load moderation settings');
  }

  Future<void> updateModerationSettings(
    String groupId,
    GroupModerationSettings settings,
  ) async {
    await _apiClient.put<dynamic>(
      ApiEndpoints.groupModerationSettings(groupId),
      data: settings.toJson(),
    );
  }

  // ── Complete Task (Phase 2d) ───────────────────────────────────────────────

  Future<void> completeTask(String taskId) async {
    await _apiClient.post<dynamic>('/community/tasks/$taskId/complete');
  }

  String _reportReasonToApi(ReportReason reason) {
    switch (reason) {
      case ReportReason.spam:
        return 'spam';
      case ReportReason.harassment:
        return 'harassment';
      case ReportReason.violence:
        return 'violence';
      case ReportReason.hateSpeech:
        return 'hate_speech';
      case ReportReason.misinformation:
        return 'misinformation';
      case ReportReason.other:
        return 'other';
    }
  }

  String _messageTypeToApi(MessageType type) {
    switch (type) {
      case MessageType.text:
        return 'text';
      case MessageType.taskShare:
        return 'task_share';
      case MessageType.planShare:
        return 'plan_share';
      case MessageType.fragmentShare:
        return 'fragment_share';
      case MessageType.capsuleShare:
        return 'capsule_share';
      case MessageType.prismShare:
        return 'prism_share';
      case MessageType.fileShare:
        return 'file_share';
      case MessageType.progress:
        return 'progress';
      case MessageType.achievement:
        return 'achievement';
      case MessageType.checkin:
        return 'checkin';
      case MessageType.system:
        return 'system';
    }
  }

  // ── Friend Management (Phase 4) ────────────────────────────────────────────

  /// 删除好友
  Future<void> deleteFriend(String friendshipId) async {
    await _apiClient.delete<dynamic>(ApiEndpoints.friendDelete(friendshipId));
  }

  /// 拉黑用户
  Future<void> blockUser(String targetUserId, {String? reason}) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.userBlock,
      data: {
        'target_user_id': targetUserId,
        if (reason != null && reason.isNotEmpty) 'reason': reason,
      },
    );
  }

  /// 取消拉黑
  Future<void> unblockUser(String userId) async {
    await _apiClient.delete<dynamic>(ApiEndpoints.userUnblock(userId));
  }

  /// 获取黑名单列表
  Future<List<BlockUserInfo>> getBlockedUsers({
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.friendsBlocked,
      queryParameters: {'limit': limit, 'offset': offset},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getBlockedUsers',
      );
      return data
          .map((e) => BlockUserInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load blocked users');
  }
}
