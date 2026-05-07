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

  Future<List<Post>> getFeed({
    int page = 1,
    int limit = 20,
    String? scope,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.communityFeed,
      queryParameters: {
        'page': page,
        'limit': limit,
        if (scope != null) 'scope': scope,
      },
    );

    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'getFeed');
      return data
          .map((e) => Post.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load community feed');
  }

  Future<String> createPost(CreatePostRequest request) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.communityPosts,
      data: request.toJson(),
    );

    if (response.statusCode == 201) {
      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'createPost');
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

  Future<void> deletePost(String postId) async {
    await _apiClient.delete<dynamic>(
      ApiEndpoints.communityPostDelete(postId),
    );
  }

  Future<List<FriendshipInfo>> getFriends({
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.friends,
      queryParameters: {'limit': limit, 'offset': offset},
    );
    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'getFriends');
      return data
          .map((e) => FriendshipInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load friends');
  }

  Future<List<FriendshipInfo>> getPendingRequests() async {
    final response = await _apiClient.get<dynamic>(ApiEndpoints.friendsPending);
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data,
          action: 'getPendingRequests',);
      return data
          .map((e) => FriendshipInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load pending requests');
  }

  Future<List<FriendRecommendation>> getFriendRecommendations({
    int limit = 10,
    FriendMatchStrategy strategy = FriendMatchStrategy.compatibility,
    FriendRecommendationTarget target =
        FriendRecommendationTarget.accountability,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.friendsRecommendations,
      queryParameters: {
        'limit': limit,
        'strategy': strategy.name,
        'target': target.name,
      },
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data,
          action: 'getFriendRecommendations',);
      return data
          .map((e) => FriendRecommendation.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load recommendations');
  }

  Future<void> sendFriendRecommendationFeedback({
    required String targetUserId,
    required FriendMatchStrategy strategy,
    required FriendRecommendationTarget target,
    required String action,
    required String source,
    double? score,
    String? promptId,
    RecommendationFeedbackStage? stage,
    int? questionnaireVersion,
    int? overallScore,
    int? relevanceScore,
    int? explanationScore,
    int? actionabilityScore,
    int? similarityScore,
    int? complementaryScore,
    int? comfortScore,
    List<String>? selectedIssues,
    List<String>? selectedStrengths,
    String? freeText,
  }) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.friendsRecommendationsFeedback,
      data: {
        'target_user_id': targetUserId,
        'strategy': strategy.name,
        'target': target.name,
        'action': action,
        'source': source,
        if (score != null) 'score': score,
        if (promptId != null) 'prompt_id': promptId,
        if (stage != null) 'stage': stage.name == 'followUp'
            ? 'follow_up'
            : stage.name == 'immediate'
                ? 'immediate'
                : 'outcome',
        if (questionnaireVersion != null)
          'questionnaire_version': questionnaireVersion,
        if (overallScore != null) 'overall_score': overallScore,
        if (relevanceScore != null) 'relevance_score': relevanceScore,
        if (explanationScore != null) 'explanation_score': explanationScore,
        if (actionabilityScore != null)
          'actionability_score': actionabilityScore,
        if (similarityScore != null) 'similarity_score': similarityScore,
        if (complementaryScore != null)
          'complementary_score': complementaryScore,
        if (comfortScore != null) 'comfort_score': comfortScore,
        if (selectedIssues != null) 'selected_issues': selectedIssues,
        if (selectedStrengths != null) 'selected_strengths': selectedStrengths,
        if (freeText != null && freeText.trim().isNotEmpty)
          'free_text': freeText.trim(),
      },
    );
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
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'searchUsers');
      return data
          .map((e) => UserBrief.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to search users');
  }

  Future<List<GroupListItem>> getMyGroups() async {
    final response = await _apiClient.get<dynamic>(ApiEndpoints.groups);
    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'getMyGroups');
      return data
          .map((e) => GroupListItem.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load groups');
  }

  Future<GroupInfo> getGroup(String groupId) async {
    final response = await _apiClient.get<dynamic>(ApiEndpoints.group(groupId));
    if (response.statusCode == 200) {
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'getGroup');
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
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'createGroup');
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
    GroupDirectorySort sortBy = GroupDirectorySort.latest,
    int limit = 20,
    int offset = 0,
  }) async {
    final query = <String, dynamic>{
      if (keyword != null && keyword.isNotEmpty) 'keyword': keyword,
      if (type != null) 'group_type': type.name,
      if (tags != null && tags.isNotEmpty) 'tags': tags,
      'sort_by': sortBy.name,
      'limit': limit,
      'offset': offset,
    };
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupsSearch,
      queryParameters: query,
    );
    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'searchGroups');
      return data
          .map((e) => GroupListItem.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to search groups');
  }

  Future<GroupDirectoryInfo> getGroupDirectory({
    String? keyword,
    GroupType? type,
    List<String>? tags,
    GroupDirectorySort sortBy = GroupDirectorySort.hot,
    int limit = 20,
    int offset = 0,
  }) async {
    final query = <String, dynamic>{
      if (keyword != null && keyword.isNotEmpty) 'keyword': keyword,
      if (type != null) 'group_type': type.name,
      if (tags != null && tags.isNotEmpty) 'tags': tags,
      'sort_by': sortBy.name,
      'limit': limit,
      'offset': offset,
    };
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupsDirectory,
      queryParameters: query,
    );
    if (response.statusCode == 200) {
      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'getGroupDirectory',);
      return GroupDirectoryInfo.fromJson(payload);
    }
    throw Exception('Failed to load group directory');
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
          .map(
            (e) => GroupRecommendationItem.fromJson(
              e as Map<String, dynamic>,
            ),
          )
          .toList();
    }
    throw Exception('Failed to load group recommendations');
  }

  Future<void> sendGroupRecommendationFeedback({
    required String groupId,
    required String action,
    required String source,
    List<String>? reasonTypes,
    String? promptId,
    RecommendationFeedbackStage? stage,
    int? questionnaireVersion,
    int? overallScore,
    int? relevanceScore,
    int? explanationScore,
    int? actionabilityScore,
    int? interestMatchScore,
    int? activityScore,
    int? atmosphereScore,
    List<String>? selectedIssues,
    List<String>? selectedStrengths,
    String? freeText,
  }) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.groupsRecommendationsFeedback,
      data: {
        'group_id': groupId,
        'action': action,
        'source': source,
        if (reasonTypes != null) 'reason_types': reasonTypes,
        if (promptId != null) 'prompt_id': promptId,
        if (stage != null) 'stage': stage.name == 'followUp'
            ? 'follow_up'
            : stage.name == 'immediate'
                ? 'immediate'
                : 'outcome',
        if (questionnaireVersion != null)
          'questionnaire_version': questionnaireVersion,
        if (overallScore != null) 'overall_score': overallScore,
        if (relevanceScore != null) 'relevance_score': relevanceScore,
        if (explanationScore != null) 'explanation_score': explanationScore,
        if (actionabilityScore != null)
          'actionability_score': actionabilityScore,
        if (interestMatchScore != null)
          'interest_match_score': interestMatchScore,
        if (activityScore != null) 'activity_score': activityScore,
        if (atmosphereScore != null) 'atmosphere_score': atmosphereScore,
        if (selectedIssues != null) 'selected_issues': selectedIssues,
        if (selectedStrengths != null) 'selected_strengths': selectedStrengths,
        if (freeText != null && freeText.trim().isNotEmpty)
          'free_text': freeText.trim(),
      },
    );
  }

  Future<List<RecommendationFeedbackPrompt>> getRecommendationFeedbackPrompts({
    RecommendationItemType? itemType,
    int limit = 20,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.recommendationsFeedbackPrompts,
      queryParameters: {
        if (itemType != null) 'item_type': itemType.name,
        'limit': limit,
      },
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getRecommendationFeedbackPrompts',
      );
      return data
          .map(
            (e) => RecommendationFeedbackPrompt.fromJson(
              e as Map<String, dynamic>,
            ),
          )
          .toList();
    }
    throw Exception('Failed to load recommendation feedback prompts');
  }

  Future<List<RecommendationFeedbackInsight>>
      getRecommendationFeedbackInsights({
    RecommendationItemType? itemType,
    int days = 30,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.recommendationsFeedbackInsights,
      queryParameters: {
        if (itemType != null) 'item_type': itemType.name,
        'days': days,
      },
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getRecommendationFeedbackInsights',
      );
      return data
          .map(
            (e) => RecommendationFeedbackInsight.fromJson(
              e as Map<String, dynamic>,
            ),
          )
          .toList();
    }
    throw Exception('Failed to load recommendation feedback insights');
  }

  Future<List<GroupMemberInfo>> getGroupMembers(String groupId) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupMembers(groupId),
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data,
          action: 'getGroupMembers',);
      return data
          .map((e) => GroupMemberInfo.fromJson(e as Map<String, dynamic>))
          .toList();
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

  Future<FriendProfileDetail> getFriendProfile(String userId) async {
    try {
      final response =
          await _apiClient.get<dynamic>(ApiEndpoints.friendProfile(userId));
      if (response.statusCode == 200) {
        final data = ApiResponseParser.unwrapMap(
          response.data,
          action: 'getFriendProfile',
        );
        return FriendProfileDetail.fromJson(data);
      }
    } catch (_) {
      // Fall through to a lightweight public profile so the page remains usable
      // even when friendship detail payloads temporarily fail.
    }

    final brief = await getUserProfile(userId);
    return FriendProfileDetail(
      user: brief,
      friendship: const <String, dynamic>{},
      quickActions: const {
        'can_invite_accountability': false,
        'can_open_dashboard': false,
        'can_chat': true,
        'can_share': false,
      },
    );
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

  Future<List<MessageInfo>> getMessages(
    String groupId, {
    String? beforeId,
    int limit = 50,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupMessages(groupId),
      queryParameters: {
        if (beforeId != null) 'before_id': beforeId,
        'limit': limit,
      },
    );
    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'getMessages');
      return data
          .map((e) => MessageInfo.fromJson(e as Map<String, dynamic>))
          .toList();
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
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'sendMessage');
      return MessageInfo.fromJson(payload);
    }
    throw Exception('Failed to send group message');
  }

  Future<void> revokeGroupMessage(String groupId, String messageId) async {
    await _apiClient
        .post<dynamic>(ApiEndpoints.groupMessageRevoke(groupId, messageId));
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
      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'editGroupMessage',);
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
      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'updateGroupReaction',);
      return MessageInfo.fromJson(payload);
    }
    throw Exception('Failed to update group reaction');
  }

  Future<List<MessageInfo>> searchGroupMessages(
    String groupId,
    String keyword, {
    int limit = 50,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupMessagesSearch(groupId),
      queryParameters: {'keyword': keyword, 'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data,
          action: 'searchGroupMessages',);
      return data
          .map((e) => MessageInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to search group messages');
  }

  Future<List<MessageInfo>> getThreadMessages(
    String groupId,
    String threadRootId, {
    int limit = 100,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupThreadMessages(groupId, threadRootId),
      queryParameters: {'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data,
          action: 'getThreadMessages',);
      return data
          .map((e) => MessageInfo.fromJson(e as Map<String, dynamic>))
          .toList();
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

  Future<List<PrivateMessageInfo>> getPrivateMessages(
    String friendId, {
    String? beforeId,
    int limit = 50,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.privateMessages(friendId),
      queryParameters: {
        if (beforeId != null) 'before_id': beforeId,
        'limit': limit,
      },
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data,
          action: 'getPrivateMessages',);
      return data
          .map((e) => PrivateMessageInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load private messages');
  }

  Future<PrivateMessageInfo> sendPrivateMessage(
    PrivateMessageSend message,
  ) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.sendPrivateMessage,
      data: message.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'sendPrivateMessage',);
      return PrivateMessageInfo.fromJson(payload);
    }
    throw Exception('Failed to send private message');
  }

  Future<void> revokePrivateMessage(String messageId) async {
    await _apiClient
        .post<dynamic>(ApiEndpoints.revokePrivateMessage(messageId));
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
      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'editPrivateMessage',);
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
      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'updatePrivateReaction',);
      return PrivateMessageInfo.fromJson(payload);
    }
    throw Exception('Failed to update private reaction');
  }

  Future<List<PrivateMessageInfo>> searchPrivateMessages(
    String friendId,
    String keyword, {
    int limit = 50,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.privateMessagesSearch(friendId),
      queryParameters: {'keyword': keyword, 'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(response.data,
          action: 'searchPrivateMessages',);
      return data
          .map((e) => PrivateMessageInfo.fromJson(e as Map<String, dynamic>))
          .toList();
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
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'checkin');
      return CheckinResponse.fromJson(payload);
    }
    throw Exception('Failed to check in');
  }

  Future<List<GroupTaskInfo>> getGroupTasks(String groupId) async {
    final response =
        await _apiClient.get<dynamic>(ApiEndpoints.groupTasks(groupId));
    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'getGroupTasks');
      return data
          .map((e) => GroupTaskInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load group tasks');
  }

  Future<GroupTaskInfo> createGroupTask(
    String groupId,
    GroupTaskCreate task,
  ) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.groupTasks(groupId),
      data: task.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'createGroupTask');
      return GroupTaskInfo.fromJson(payload);
    }
    throw Exception('Failed to create group task');
  }

  Future<void> claimTask(String taskId) async {
    await _apiClient.post<dynamic>(ApiEndpoints.claimTask(taskId));
  }

  Future<GroupFlameStatus> getFlameStatus(String groupId) async {
    final response =
        await _apiClient.get<dynamic>(ApiEndpoints.groupFlame(groupId));
    if (response.statusCode == 200) {
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'getFlameStatus');
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
        if (tag != null && tag.trim().isNotEmpty) 'tags': <String>[tag.trim()],
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
        response.data,
        action: 'getModerationSettings',
      );
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
      case ReportReason.inappropriate:
        return 'inappropriate';
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

  // ── Privacy Settings ──────────────────────────────────────────────────────

  /// 获取隐私设置
  Future<UserPrivacySettings> getPrivacySettings() async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.userPrivacy,
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getPrivacySettings',
      );
      return UserPrivacySettings.fromJson(data);
    }
    throw Exception('Failed to load privacy settings');
  }

  /// 更新隐私设置
  Future<void> updatePrivacySettings(UserPrivacySettings settings) async {
    await _apiClient.put<dynamic>(
      ApiEndpoints.userPrivacy,
      data: settings.toJson(),
    );
  }

  // ── Broadcast ──────────────────────────────────────────────────────────────

  /// 发送跨群广播消息
  Future<BroadcastMessageInfo> createBroadcast(
    BroadcastMessageCreate request,
  ) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.broadcast,
      data: request.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'createBroadcast',
      );
      return BroadcastMessageInfo.fromJson(data);
    }
    throw Exception('Failed to create broadcast');
  }

  // ── Offline Queue ──────────────────────────────────────────────────────────

  /// 获取待发送的离线消息
  Future<List<OfflineMessageInfo>> getPendingOfflineMessages() async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.offlineQueuePending,
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getPendingOfflineMessages',
      );
      return data
          .map((e) => OfflineMessageInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load pending offline messages');
  }

  /// 获取发送失败的离线消息
  Future<List<OfflineMessageInfo>> getFailedOfflineMessages() async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.offlineQueueFailed,
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getFailedOfflineMessages',
      );
      return data
          .map((e) => OfflineMessageInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load failed offline messages');
  }

  /// 重试发送失败的离线消息
  Future<void> retryOfflineMessages(List<String> messageIds) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.offlineQueueRetry,
      data: {'message_ids': messageIds},
    );
  }

  // ── Encryption Keys ────────────────────────────────────────────────────────

  /// 注册加密公钥
  Future<EncryptionKeyInfo> registerEncryptionKey(
    EncryptionKeyCreate request,
  ) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.encryptionKeys,
      data: request.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'registerEncryptionKey',
      );
      return EncryptionKeyInfo.fromJson(data);
    }
    throw Exception('Failed to register encryption key');
  }

  /// 获取用户公钥列表
  Future<List<EncryptionKeyInfo>> getUserPublicKeys(String userId) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.userPublicKey(userId),
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getUserPublicKeys',
      );
      return data
          .map((e) => EncryptionKeyInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load user public keys');
  }

  /// 撤销加密密钥
  Future<void> revokeEncryptionKey(String keyId) async {
    await _apiClient.delete<dynamic>(ApiEndpoints.encryptionKey(keyId));
  }

  // ── Group Files ────────────────────────────────────────────────────────────

  /// 获取群文件列表
  Future<List<GroupFileInfo>> getGroupFiles(
    String groupId, {
    String? category,
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupFiles(groupId),
      queryParameters: {
        if (category != null) 'category': category,
        'limit': limit,
        'offset': offset,
      },
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getGroupFiles',
      );
      return data
          .map((e) => GroupFileInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load group files');
  }

  /// 分享文件到群组
  Future<GroupFileInfo> shareFileToGroup(
    String groupId,
    GroupFileShareRequest request,
  ) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.groupFileShare(groupId, request.fileId),
      data: request.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'shareFileToGroup',
      );
      return GroupFileInfo.fromJson(data);
    }
    throw Exception('Failed to share file to group');
  }

  /// 更新群文件权限
  Future<GroupFileInfo> updateGroupFilePermissions(
    String groupId,
    String fileId,
    GroupFilePermissionUpdate permissions,
  ) async {
    final response = await _apiClient.put<dynamic>(
      ApiEndpoints.groupFilePermissions(groupId, fileId),
      data: permissions.toJson(),
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'updateGroupFilePermissions',
      );
      return GroupFileInfo.fromJson(data);
    }
    throw Exception('Failed to update file permissions');
  }

  /// 获取群文件分类统计
  Future<List<GroupFileCategoryStat>> getGroupFileCategories(
    String groupId,
  ) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupFileCategories(groupId),
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getGroupFileCategories',
      );
      return data
          .map((e) => GroupFileCategoryStat.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load file categories');
  }

  // ── Shared Resources ───────────────────────────────────────────────────────

  /// 分享资源到群组
  Future<SharedResourceInfo> shareResource(SharedResourceCreate request) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.communityShare,
      data: request.toJson(),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'shareResource',
      );
      return SharedResourceInfo.fromJson(data);
    }
    throw Exception('Failed to share resource');
  }

  /// 获取群组共享资源
  Future<List<SharedResourceInfo>> getGroupResources(
    String groupId, {
    SharedResourceType? type,
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupResources(groupId),
      queryParameters: {
        if (type != null) 'resource_type': type.name,
        'limit': limit,
        'offset': offset,
      },
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getGroupResources',
      );
      return data
          .map((e) => SharedResourceInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load group resources');
  }

  /// 采纳共享资源
  Future<void> adoptSharedResource(String shareId) async {
    await _apiClient.post<dynamic>(
      ApiEndpoints.adoptSharedResource(shareId),
    );
  }

  // ── Message Reports Management ─────────────────────────────────────────────

  /// 获取群组待处理举报
  Future<List<MessageReportInfo>> getPendingReports(String groupId) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.groupReports(groupId),
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getPendingReports',
      );
      return data
          .map((e) => MessageReportInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load pending reports');
  }

  /// 审核举报
  Future<MessageReportInfo> reviewReport(
    String reportId,
    MessageReportReview review,
  ) async {
    final response = await _apiClient.put<dynamic>(
      ApiEndpoints.messageReportReview(reportId),
      data: review.toJson(),
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'reviewReport',
      );
      return MessageReportInfo.fromJson(data);
    }
    throw Exception('Failed to review report');
  }

  // ── Group File Library Copy ───────────────────────────────────────────────

  /// 将群文件保存到个人文件库
  /// TODO: endpoint POST /api/v1/community/groups/{groupId}/files/{fileId}/copy-to-library
  /// is not yet implemented on the backend — add backend support when ready.
  Future<void> copyFileToMyLibrary(String groupId, String fileId) async {
    await _apiClient.post<dynamic>(
      '/api/v1/community/groups/$groupId/files/$fileId/copy-to-library',
    );
  }
}
