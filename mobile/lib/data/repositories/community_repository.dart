import 'package:dio/dio.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class CommunityRepository {
  final ApiClient _apiClient;

  CommunityRepository(this._apiClient);

  // Error handler
  T _handleDioError<T>(DioException e, String functionName) {
    final errorMessage =
        e.response?.data?['detail'] ?? 'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  // ============ 好友系统 ============

  /// 获取好友列表
  Future<List<FriendshipInfo>> getFriends() async {
    try {
      final response = await _apiClient.get(ApiEndpoints.friends);
      final List<dynamic> data = response.data;
      return data.map((json) => FriendshipInfo.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getFriends');
    }
  }

  /// 发送好友请求
  Future<void> sendFriendRequest(String targetUserId, {String? message}) async {
    try {
      await _apiClient.post(ApiEndpoints.friendRequest, data: {
        'target_user_id': targetUserId,
        'message': message,
      },);
    } on DioException catch (e) {
      return _handleDioError(e, 'sendFriendRequest');
    }
  }

  /// 响应好友请求
  Future<void> respondToRequest(String friendshipId, bool accept) async {
    try {
      await _apiClient.post(ApiEndpoints.friendRespond, data: {
        'friendship_id': friendshipId,
        'accept': accept,
      },);
    } on DioException catch (e) {
      return _handleDioError(e, 'respondToRequest');
    }
  }

  /// 获取待处理的好友请求
  Future<List<FriendshipInfo>> getPendingRequests() async {
    try {
      final response = await _apiClient.get(ApiEndpoints.friendsPending);
      final List<dynamic> data = response.data;
      return data.map((json) => FriendshipInfo.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getPendingRequests');
    }
  }

  /// 获取好友推荐
  Future<List<FriendRecommendation>> getFriendRecommendations({int limit = 10}) async {
    try {
      final response = await _apiClient.get(
        ApiEndpoints.friendsRecommendations,
        queryParameters: {'limit': limit},
      );
      final List<dynamic> data = response.data;
      return data.map((json) => FriendRecommendation.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getFriendRecommendations');
    }
  }

  /// 获取私信
  Future<List<PrivateMessageInfo>> getPrivateMessages(
    String friendId, {
    String? beforeId,
    int limit = 50,
  }) async {
    try {
      final Map<String, dynamic> queryParams = {'limit': limit};
      if (beforeId != null) queryParams['before_id'] = beforeId;

      final response = await _apiClient.get(
        ApiEndpoints.privateMessages(friendId),
        queryParameters: queryParams,
      );
      final List<dynamic> data = response.data;
      return data.map((json) => PrivateMessageInfo.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getPrivateMessages');
    }
  }

  /// 发送私信
  Future<PrivateMessageInfo> sendPrivateMessage(PrivateMessageSend message) async {
    try {
      final response = await _apiClient.post(
        ApiEndpoints.sendPrivateMessage,
        data: message.toJson(),
      );
      return PrivateMessageInfo.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'sendPrivateMessage');
    }
  }

  /// 撤销私信
  Future<void> revokePrivateMessage(String messageId) async {
    try {
      await _apiClient.post(ApiEndpoints.revokePrivateMessage(messageId));
    } on DioException catch (e) {
      return _handleDioError(e, 'revokePrivateMessage');
    }
  }

  /// 搜索用户
  Future<List<UserBrief>> searchUsers(String keyword, {int limit = 20}) async {
    try {
      final response = await _apiClient.get(
        ApiEndpoints.searchUsers,
        queryParameters: {'keyword': keyword, 'limit': limit},
      );
      final List<dynamic> data = response.data;
      return data.map((json) => UserBrief.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'searchUsers');
    }
  }

  /// 更新在线状态
  Future<void> updateStatus(UserStatus status) async {
    try {
      await _apiClient.put(
        ApiEndpoints.userStatus,
        data: {'status': status.name},
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'updateStatus');
    }
  }

  // ============ 群组管理 ============

  /// 创建群组
  Future<GroupInfo> createGroup(GroupCreate group) async {
    try {
      final response = await _apiClient.post(
        ApiEndpoints.groups,
        data: group.toJson(),
      );
      return GroupInfo.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'createGroup');
    }
  }

  /// 获取群组详情
  Future<GroupInfo> getGroup(String groupId) async {
    try {
      final response = await _apiClient.get(ApiEndpoints.group(groupId));
      return GroupInfo.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'getGroup');
    }
  }

  /// 获取我的群组列表
  Future<List<GroupListItem>> getMyGroups() async {
    try {
      final response = await _apiClient.get(ApiEndpoints.groups);
      final List<dynamic> data = response.data;
      return data.map((json) => GroupListItem.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getMyGroups');
    }
  }

  /// 搜索公开群组
  Future<List<GroupListItem>> searchGroups({
    String? keyword,
    GroupType? type,
    List<String>? tags,
    int limit = 20,
  }) async {
    try {
      final Map<String, dynamic> queryParams = {'limit': limit};
      if (keyword != null) queryParams['keyword'] = keyword;
      if (type != null) queryParams['group_type'] = type.name;
      if (tags != null && tags.isNotEmpty) queryParams['tags'] = tags;

      final response = await _apiClient.get(
        ApiEndpoints.groupsSearch,
        queryParameters: queryParams,
      );
      final List<dynamic> data = response.data;
      return data.map((json) => GroupListItem.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'searchGroups');
    }
  }

  /// 加入群组
  Future<void> joinGroup(String groupId) async {
    try {
      await _apiClient.post(ApiEndpoints.groupJoin(groupId));
    } on DioException catch (e) {
      return _handleDioError(e, 'joinGroup');
    }
  }

  /// 退出群组
  Future<void> leaveGroup(String groupId) async {
    try {
      await _apiClient.post(ApiEndpoints.groupLeave(groupId));
    } on DioException catch (e) {
      return _handleDioError(e, 'leaveGroup');
    }
  }

  // ============ 群消息 ============

  /// 获取群消息
  Future<List<MessageInfo>> getMessages(
    String groupId, {
    String? beforeId,
    int limit = 50,
  }) async {
    try {
      final Map<String, dynamic> queryParams = {'limit': limit};
      if (beforeId != null) queryParams['before_id'] = beforeId;

      final response = await _apiClient.get(
        ApiEndpoints.groupMessages(groupId),
        queryParameters: queryParams,
      );
      final List<dynamic> data = response.data;
      return data.map((json) => MessageInfo.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getMessages');
    }
  }

  /// 发送消息
  Future<MessageInfo> sendMessage(
    String groupId, {
    required MessageType type,
    String? content,
    Map<String, dynamic>? contentData,
    String? replyToId,
    String? nonce,
  }) async {
    try {
      final response = await _apiClient.post(
        ApiEndpoints.groupMessages(groupId),
        data: {
          'message_type': type.name,
          'content': content,
          'content_data': contentData,
          'reply_to_id': replyToId,
          'nonce': nonce,
        },
      );
      return MessageInfo.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'sendMessage');
    }
  }

  // ============ 打卡 ============

  /// 群组打卡
  Future<CheckinResponse> checkin(
    String groupId, {
    required int todayDurationMinutes,
    String? message,
  }) async {
    try {
      final response = await _apiClient.post(
        ApiEndpoints.checkin,
        data: {
          'group_id': groupId,
          'today_duration_minutes': todayDurationMinutes,
          'message': message,
        },
      );
      return CheckinResponse.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'checkin');
    }
  }

  // ============ 群任务 ============

  /// 获取群任务列表
  Future<List<GroupTaskInfo>> getGroupTasks(String groupId) async {
    try {
      final response = await _apiClient.get(ApiEndpoints.groupTasks(groupId));
      final List<dynamic> data = response.data;
      return data.map((json) => GroupTaskInfo.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getGroupTasks');
    }
  }

  /// 创建群任务
  Future<GroupTaskInfo> createGroupTask(String groupId, GroupTaskCreate task) async {
    try {
      final response = await _apiClient.post(
        ApiEndpoints.groupTasks(groupId),
        data: task.toJson(),
      );
      return GroupTaskInfo.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'createGroupTask');
    }
  }

  /// 认领群任务
  Future<void> claimTask(String taskId) async {
    try {
      await _apiClient.post(ApiEndpoints.claimTask(taskId));
    } on DioException catch (e) {
      return _handleDioError(e, 'claimTask');
    }
  }

  // ============ 火堆状态 ============

  /// 获取群组火堆状态
  Future<GroupFlameStatus> getFlameStatus(String groupId) async {
    try {
      final response = await _apiClient.get(ApiEndpoints.groupFlame(groupId));
      return GroupFlameStatus.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'getFlameStatus');
    }
  }
}


