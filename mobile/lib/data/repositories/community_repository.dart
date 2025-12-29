import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/domain/community/community_models.dart';

final communityRepositoryProvider = Provider<CommunityRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CommunityRepository(apiClient);
});

class CommunityRepository {
  CommunityRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<List<Post>> getFeed({int page = 1, int limit = 20}) async {
    final response = await _apiClient.get(
      ApiEndpoints.communityFeed,
      queryParameters: {'page': page, 'limit': limit},
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = response.data;
      return data.map((e) => Post.fromJson(e)).toList();
    }
    throw Exception('Failed to load feed');
  }

  Future<String> createPost(CreatePostRequest request) async {
    final response = await _apiClient.post(
      ApiEndpoints.communityPosts,
      data: request.toJson(),
    );

    if (response.statusCode == 201) {
      return response.data['id'];
    }
    throw Exception('Failed to create post');
  }

  Future<void> likePost(String postId, String userId) async {
    await _apiClient.post(
      ApiEndpoints.communityPostLike(postId),
      data: {'user_id': userId},
    );
  }

  Future<List<FriendshipInfo>> getFriends({int limit = 50, int offset = 0}) async {
    final response = await _apiClient.get(
      ApiEndpoints.friends,
      queryParameters: {'limit': limit, 'offset': offset},
    );
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => FriendshipInfo.fromJson(e)).toList();
    }
    throw Exception('Failed to load friends');
  }

  Future<List<FriendshipInfo>> getPendingRequests() async {
    final response = await _apiClient.get(ApiEndpoints.friendsPending);
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => FriendshipInfo.fromJson(e)).toList();
    }
    throw Exception('Failed to load pending requests');
  }

  Future<List<FriendRecommendation>> getFriendRecommendations({int limit = 10}) async {
    final response = await _apiClient.get(
      ApiEndpoints.friendsRecommendations,
      queryParameters: {'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => FriendRecommendation.fromJson(e)).toList();
    }
    throw Exception('Failed to load recommendations');
  }

  Future<void> sendFriendRequest(String targetUserId, {String? message}) async {
    await _apiClient.post(
      ApiEndpoints.friendRequest,
      data: {
        'target_user_id': targetUserId,
        if (message != null && message.isNotEmpty) 'message': message,
      },
    );
  }

  Future<void> respondToRequest(String friendshipId, bool accept) async {
    await _apiClient.post(
      ApiEndpoints.friendRespond,
      data: {
        'friendship_id': friendshipId,
        'accept': accept,
      },
    );
  }

  Future<List<UserBrief>> searchUsers(String keyword, {int limit = 20}) async {
    final response = await _apiClient.get(
      ApiEndpoints.searchUsers,
      queryParameters: {'keyword': keyword, 'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => UserBrief.fromJson(e)).toList();
    }
    throw Exception('Failed to search users');
  }

  Future<List<GroupListItem>> getMyGroups() async {
    final response = await _apiClient.get(ApiEndpoints.groups);
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => GroupListItem.fromJson(e)).toList();
    }
    throw Exception('Failed to load groups');
  }

  Future<GroupInfo> getGroup(String groupId) async {
    final response = await _apiClient.get(ApiEndpoints.group(groupId));
    if (response.statusCode == 200) {
      return GroupInfo.fromJson(response.data);
    }
    throw Exception('Failed to load group');
  }

  Future<GroupInfo> createGroup(GroupCreate group) async {
    final response = await _apiClient.post(
      ApiEndpoints.groups,
      data: group.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return GroupInfo.fromJson(response.data);
    }
    throw Exception('Failed to create group');
  }

  Future<void> joinGroup(String groupId) async {
    await _apiClient.post(ApiEndpoints.groupJoin(groupId));
  }

  Future<void> leaveGroup(String groupId) async {
    await _apiClient.post(ApiEndpoints.groupLeave(groupId));
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
    final response = await _apiClient.get(
      ApiEndpoints.groupsSearch,
      queryParameters: query,
    );
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => GroupListItem.fromJson(e)).toList();
    }
    throw Exception('Failed to search groups');
  }

  Future<List<MessageInfo>> getMessages(String groupId, {String? beforeId, int limit = 50}) async {
    final response = await _apiClient.get(
      ApiEndpoints.groupMessages(groupId),
      queryParameters: {
        if (beforeId != null) 'before_id': beforeId,
        'limit': limit,
      },
    );
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => MessageInfo.fromJson(e)).toList();
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
    final response = await _apiClient.post(
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
      return MessageInfo.fromJson(response.data);
    }
    throw Exception('Failed to send group message');
  }

  Future<void> revokeGroupMessage(String groupId, String messageId) async {
    await _apiClient.post(ApiEndpoints.groupMessageRevoke(groupId, messageId));
  }

  Future<MessageInfo> editGroupMessage(
    String groupId,
    String messageId, {
    String? content,
    Map<String, dynamic>? contentData,
    List<String>? mentionUserIds,
  }) async {
    final response = await _apiClient.patch(
      ApiEndpoints.groupMessageEdit(groupId, messageId),
      data: {
        if (content != null) 'content': content,
        if (contentData != null) 'content_data': contentData,
        if (mentionUserIds != null) 'mention_user_ids': mentionUserIds,
      },
    );
    if (response.statusCode == 200) {
      return MessageInfo.fromJson(response.data);
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
    final response = await _apiClient.post(
      ApiEndpoints.groupMessageReactions(groupId, messageId),
      data: {
        'emoji': emoji,
        'action': isAdd ? 'add' : 'remove',
      },
    );
    if (response.statusCode == 200) {
      return MessageInfo.fromJson(response.data);
    }
    throw Exception('Failed to update group reaction');
  }

  Future<List<MessageInfo>> searchGroupMessages(String groupId, String keyword, {int limit = 50}) async {
    final response = await _apiClient.get(
      ApiEndpoints.groupMessagesSearch(groupId),
      queryParameters: {'keyword': keyword, 'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => MessageInfo.fromJson(e)).toList();
    }
    throw Exception('Failed to search group messages');
  }

  Future<List<MessageInfo>> getThreadMessages(String groupId, String threadRootId, {int limit = 100}) async {
    final response = await _apiClient.get(
      ApiEndpoints.groupThreadMessages(groupId, threadRootId),
      queryParameters: {'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => MessageInfo.fromJson(e)).toList();
    }
    throw Exception('Failed to load thread messages');
  }

  Future<List<PrivateMessageInfo>> getPrivateMessages(String friendId, {String? beforeId, int limit = 50}) async {
    final response = await _apiClient.get(
      ApiEndpoints.privateMessages(friendId),
      queryParameters: {
        if (beforeId != null) 'before_id': beforeId,
        'limit': limit,
      },
    );
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => PrivateMessageInfo.fromJson(e)).toList();
    }
    throw Exception('Failed to load private messages');
  }

  Future<PrivateMessageInfo> sendPrivateMessage(PrivateMessageSend message) async {
    final response = await _apiClient.post(
      ApiEndpoints.sendPrivateMessage,
      data: message.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return PrivateMessageInfo.fromJson(response.data);
    }
    throw Exception('Failed to send private message');
  }

  Future<void> revokePrivateMessage(String messageId) async {
    await _apiClient.post(ApiEndpoints.revokePrivateMessage(messageId));
  }

  Future<PrivateMessageInfo> editPrivateMessage(
    String messageId, {
    String? content,
    Map<String, dynamic>? contentData,
    List<String>? mentionUserIds,
  }) async {
    final response = await _apiClient.patch(
      ApiEndpoints.editPrivateMessage(messageId),
      data: {
        if (content != null) 'content': content,
        if (contentData != null) 'content_data': contentData,
        if (mentionUserIds != null) 'mention_user_ids': mentionUserIds,
      },
    );
    if (response.statusCode == 200) {
      return PrivateMessageInfo.fromJson(response.data);
    }
    throw Exception('Failed to edit private message');
  }

  Future<PrivateMessageInfo> updatePrivateReaction(
    String messageId, {
    required String emoji,
    required String userId,
    required bool isAdd,
  }) async {
    final response = await _apiClient.post(
      ApiEndpoints.privateMessageReactions(messageId),
      data: {
        'emoji': emoji,
        'action': isAdd ? 'add' : 'remove',
      },
    );
    if (response.statusCode == 200) {
      return PrivateMessageInfo.fromJson(response.data);
    }
    throw Exception('Failed to update private reaction');
  }

  Future<List<PrivateMessageInfo>> searchPrivateMessages(String friendId, String keyword, {int limit = 50}) async {
    final response = await _apiClient.get(
      ApiEndpoints.privateMessagesSearch(friendId),
      queryParameters: {'keyword': keyword, 'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => PrivateMessageInfo.fromJson(e)).toList();
    }
    throw Exception('Failed to search private messages');
  }

  Future<CheckinResponse> checkin(
    String groupId, {
    required int todayDurationMinutes,
    String? message,
  }) async {
    final response = await _apiClient.post(
      ApiEndpoints.checkin,
      data: {
        'group_id': groupId,
        'today_duration_minutes': todayDurationMinutes,
        if (message != null && message.isNotEmpty) 'message': message,
      },
    );
    if (response.statusCode == 200) {
      return CheckinResponse.fromJson(response.data);
    }
    throw Exception('Failed to check in');
  }

  Future<List<GroupTaskInfo>> getGroupTasks(String groupId) async {
    final response = await _apiClient.get(ApiEndpoints.groupTasks(groupId));
    if (response.statusCode == 200) {
      final data = response.data as List<dynamic>;
      return data.map((e) => GroupTaskInfo.fromJson(e)).toList();
    }
    throw Exception('Failed to load group tasks');
  }

  Future<GroupTaskInfo> createGroupTask(String groupId, GroupTaskCreate task) async {
    final response = await _apiClient.post(
      ApiEndpoints.groupTasks(groupId),
      data: task.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return GroupTaskInfo.fromJson(response.data);
    }
    throw Exception('Failed to create group task');
  }

  Future<void> claimTask(String taskId) async {
    await _apiClient.post(ApiEndpoints.claimTask(taskId));
  }

  Future<GroupFlameStatus> getFlameStatus(String groupId) async {
    final response = await _apiClient.get(ApiEndpoints.groupFlame(groupId));
    if (response.statusCode == 200) {
      return GroupFlameStatus.fromJson(response.data);
    }
    throw Exception('Failed to load flame status');
  }

  Future<void> updateStatus(UserStatus status) async {
    await _apiClient.put(
      ApiEndpoints.userStatus,
      data: {'status': status.name},
    );
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
}
