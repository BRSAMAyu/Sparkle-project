import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/websocket_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:uuid/uuid.dart';

// Token provider for WebSocket connections
final _wsTokenProvider = FutureProvider.autoDispose<String?>((ref) async {
  final authRepo = ref.watch(authRepositoryProvider);
  return authRepo.getAccessToken();
});

// Global Community Events Stream
final communityEventsStreamProvider =
    Provider.autoDispose<Stream<dynamic>>((ref) {
  final wsService = WebSocketService();
  final tokenAsync = ref.watch(_wsTokenProvider);

  final token = tokenAsync.valueOrNull;
  if (token == null) {
    return const Stream.empty();
  }

  final baseUrl = ApiEndpoints.baseUrl.replaceFirst(RegExp('^http'), 'ws');
  // 安全修复：token不再放在URL中，改用headers
  final wsUrl = '$baseUrl/community/ws/connect';
  final headers = <String, dynamic>{
    'Authorization': 'Bearer $token',
  };

  try {
    wsService.connect(wsUrl, headers: headers);
  } catch (e) {
    debugPrint('WS Connect Error: $e');
    return const Stream.empty();
  }

  ref.onDispose(wsService.disconnect);

  return wsService.stream;
});

// 1. Friends Provider
final friendsProvider =
    StateNotifierProvider<FriendsNotifier, AsyncValue<List<FriendshipInfo>>>(
        (ref) {
  final stream = ref.watch(communityEventsStreamProvider);
  return FriendsNotifier(ref.watch(communityRepositoryProvider), stream);
});

class FriendsNotifier extends StateNotifier<AsyncValue<List<FriendshipInfo>>> {
  FriendsNotifier(this._repository, Stream<dynamic> events)
      : super(const AsyncValue.loading()) {
    loadFriends();
    events.listen(_handleEvent);
  }
  final CommunityRepository _repository;

  void _handleEvent(dynamic data) {
    if (data is String) {
      try {
        final json = jsonDecode(data);
        if (json['type'] == 'status_update') {
          _updateFriendStatus(
            json['user_id'] as String,
            json['status'] as String,
          );
        }
      } catch (e) {
        debugPrint('Event Error: $e');
      }
    }
  }

  void _updateFriendStatus(String userId, String statusStr) {
    state.whenData((friends) {
      final newStatus = UserStatus.values.firstWhere(
        (e) => e.name == statusStr,
        orElse: () => UserStatus.offline,
      );

      final updatedFriends = friends.map((f) {
        if (f.friend.id == userId) {
          return FriendshipInfo(
            id: f.id,
            friend: UserBrief(
              id: f.friend.id,
              username: f.friend.username,
              nickname: f.friend.nickname,
              avatarUrl: f.friend.avatarUrl,
              flameLevel: f.friend.flameLevel,
              flameBrightness: f.friend.flameBrightness,
              status: newStatus,
            ),
            status: f.status,
            createdAt: f.createdAt,
            updatedAt: f.updatedAt,
            matchReason: f.matchReason,
          );
        }
        return f;
      }).toList();

      state = AsyncValue.data(updatedFriends);
    });
  }

  Future<void> loadFriends() async {
    state = const AsyncValue.loading();
    try {
      final friends = await _repository.getFriends();
      state = AsyncValue.data(friends);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadFriends();
}

final pendingRequestsProvider = StateNotifierProvider<PendingRequestsNotifier,
        AsyncValue<List<FriendshipInfo>>>(
    (ref) => PendingRequestsNotifier(ref.watch(communityRepositoryProvider)),);

class PendingRequestsNotifier
    extends StateNotifier<AsyncValue<List<FriendshipInfo>>> {
  PendingRequestsNotifier(this._repository)
      : super(const AsyncValue.loading()) {
    loadPendingRequests();
  }
  final CommunityRepository _repository;

  Future<void> loadPendingRequests() async {
    state = const AsyncValue.loading();
    try {
      final requests = await _repository.getPendingRequests();
      state = AsyncValue.data(requests);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadPendingRequests();

  Future<void> respondToRequest(String friendshipId, bool accept) async {
    try {
      await _repository.respondToRequest(friendshipId, accept);
      await loadPendingRequests();
    } catch (e) {
      rethrow;
    }
  }
}

// 2. Recommendations Provider
final friendRecommendationsProvider = StateNotifierProvider<
        FriendRecommendationsNotifier, AsyncValue<List<FriendRecommendation>>>(
    (ref) =>
        FriendRecommendationsNotifier(ref.watch(communityRepositoryProvider)),);

class FriendRecommendationsNotifier
    extends StateNotifier<AsyncValue<List<FriendRecommendation>>> {
  FriendRecommendationsNotifier(this._repository)
      : super(const AsyncValue.loading()) {
    loadRecommendations();
  }
  final CommunityRepository _repository;

  Future<void> loadRecommendations() async {
    state = const AsyncValue.loading();
    try {
      final recommendations = await _repository.getFriendRecommendations();
      state = AsyncValue.data(recommendations);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadRecommendations();

  Future<void> sendRequest(String targetUserId) async {
    try {
      await _repository.sendFriendRequest(targetUserId);
    } catch (e) {
      rethrow;
    }
  }
}

// 3. User Search Provider
final userSearchProvider =
    StateNotifierProvider<UserSearchNotifier, AsyncValue<List<UserBrief>>>(
        (ref) => UserSearchNotifier(ref.watch(communityRepositoryProvider)),);

class UserSearchNotifier extends StateNotifier<AsyncValue<List<UserBrief>>> {
  UserSearchNotifier(this._repository) : super(const AsyncValue.data([]));
  final CommunityRepository _repository;

  Future<void> search(String keyword) async {
    if (keyword.isEmpty) {
      state = const AsyncValue.data([]);
      return;
    }
    state = const AsyncValue.loading();
    try {
      final results = await _repository.searchUsers(keyword);
      state = AsyncValue.data(results);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }
}

// 4. My Groups Provider
final myGroupsProvider =
    StateNotifierProvider<MyGroupsNotifier, AsyncValue<List<GroupListItem>>>(
        (ref) => MyGroupsNotifier(ref.watch(communityRepositoryProvider)),);

final groupDetailProvider = StateNotifierProvider.family<GroupDetailNotifier,
        AsyncValue<GroupInfo>, String>(
    (ref, groupId) =>
        GroupDetailNotifier(ref.watch(communityRepositoryProvider), groupId),);

class GroupDetailNotifier extends StateNotifier<AsyncValue<GroupInfo>> {
  GroupDetailNotifier(this._repository, this._groupId)
      : super(const AsyncValue.loading()) {
    loadDetail();
  }
  final CommunityRepository _repository;
  final String _groupId;

  Future<void> loadDetail() async {
    state = const AsyncValue.loading();
    try {
      final detail = await _repository.getGroup(_groupId);
      state = AsyncValue.data(detail);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadDetail();

  Future<void> joinGroup() async {
    try {
      await _repository.joinGroup(_groupId);
      await loadDetail();
    } catch (e) {
      rethrow;
    }
  }

  Future<void> leaveGroup() async {
    try {
      await _repository.leaveGroup(_groupId);
      await loadDetail();
    } catch (e) {
      rethrow;
    }
  }

  Future<CheckinResponse> checkin(int minutes, String? message) async {
    try {
      final response = await _repository.checkin(_groupId,
          todayDurationMinutes: minutes, message: message,);
      await loadDetail();
      return response;
    } catch (e) {
      rethrow;
    }
  }
}

class MyGroupsNotifier extends StateNotifier<AsyncValue<List<GroupListItem>>> {
  MyGroupsNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadGroups();
  }
  final CommunityRepository _repository;

  Future<void> loadGroups() async {
    state = const AsyncValue.loading();
    try {
      final groups = await _repository.getMyGroups();
      state = AsyncValue.data(groups);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadGroups();

  Future<GroupInfo> createGroup(GroupCreate data) async {
    try {
      final group = await _repository.createGroup(data);
      await loadGroups();
      return group;
    } catch (e) {
      rethrow;
    }
  }
}

// 5. Group Chat Provider (Family)
final groupChatProvider = StateNotifierProvider.family<GroupChatNotifier,
    AsyncValue<List<MessageInfo>>, String>(
  (ref, groupId) => GroupChatNotifier(
    ref.watch(communityRepositoryProvider),
    ref.watch(authRepositoryProvider),
    groupId,
    ref,
  ),
);

class GroupChatNotifier extends StateNotifier<AsyncValue<List<MessageInfo>>> {
  GroupChatNotifier(
      this._repository, this._authRepository, this._groupId, this._ref,)
      : super(const AsyncValue.loading()) {
    _initialize();
  }
  final CommunityRepository _repository;
  final AuthRepository _authRepository;
  final String _groupId;
  final Ref _ref;
  final WebSocketService _wsService = WebSocketService();
  final ChatCacheService _cacheService = ChatCacheService();

  final Set<String> _pendingNonces = {};
  Set<String> get pendingNonces => _pendingNonces;

  MessageInfo? _quotedMessage;
  MessageInfo? get quotedMessage => _quotedMessage;

  String? _currentUserId;

  Future<void> _initialize() async {
    // Get current user ID for filtering notifications
    // In a real implementation, you'd decode the token to get user ID
    // For now, we'll leave it null and show all notifications
    await _authRepository.getAccessToken();
    _currentUserId = _ref.read(currentUserProvider)?.id;

    final cached = await _cacheService.getCachedGroupMessages(_groupId);
    if (cached.isNotEmpty && mounted) {
      state = AsyncValue.data(cached);
    }
    await loadMessages();
    await _retryPendingGroupMessages();
    await _connectWebSocket();
  }

  Future<void> _connectWebSocket() async {
    final token = await _authRepository.getAccessToken();
    if (token == null) return;

    final baseUrl = ApiEndpoints.baseUrl.replaceFirst(RegExp('^http'), 'ws');
    // 安全修复：token不再放在URL中，改用headers
    final wsUrl = '$baseUrl/community/groups/$_groupId/ws';
    final headers = <String, dynamic>{
      'Authorization': 'Bearer $token',
    };

    try {
      _wsService.connect(wsUrl, headers: headers);
      _wsService.stream.listen((data) {
        if (data is String) {
          try {
            final jsonData = jsonDecode(data) as Map<String, dynamic>;

            if (jsonData['type'] == 'ack') {
              final nonce = jsonData['nonce'];
              if (nonce != null && _pendingNonces.contains(nonce)) {
                _pendingNonces.remove(nonce);
                Future(() => _cacheService.removePendingGroupMessage(
                    _groupId, nonce.toString(),),);
                state.whenData(
                    (messages) => state = AsyncValue.data([...messages]),);
              }
              return;
            }

            if (jsonData['type'] == 'message_edit' &&
                jsonData['message'] != null) {
              final message = MessageInfo.fromJson(
                jsonData['message'] as Map<String, dynamic>,
              );
              _handleEditedEvent(message);
              return;
            }

            if (jsonData['type'] == 'message_revoke' ||
                jsonData['type'] == 'revoked') {
              final messageId = jsonData['message_id'];
              if (messageId != null) {
                _handleRevokedEvent(messageId.toString());
              }
              return;
            }

            if (jsonData['type'] == 'reaction_update') {
              final messageId = jsonData['message_id'];
              final reactions = jsonData['reactions'];
              if (messageId != null) {
                _handleReactionUpdate(
                    messageId.toString(), reactions as Map<String, dynamic>?,);
              }
              return;
            }

            final message = MessageInfo.fromJson(jsonData);
            state.whenData((messages) {
              if (!messages.any((m) => m.id == message.id)) {
                state = AsyncValue.data([message, ...messages]);

                // Trigger in-app notification for incoming group messages
                // Only notify if message is from someone else
                if (message.sender != null &&
                    message.sender!.id != _currentUserId) {
                  _ref.read(unreadMessageCountProvider.notifier).increment();
                  _ref.read(inAppNotificationProvider.notifier).show(
                        NotificationMessage(
                          id: message.id,
                          senderName: message.sender!.displayName,
                          senderAvatarUrl: message.sender!.avatarUrl,
                          content: message.content ?? '',
                          timestamp: message.createdAt,
                          type: NotificationType.groupMessage,
                          targetId: _groupId,
                        ),
                      );
                }
              }
            });
          } catch (e) {
            debugPrint('WS Parse Error: $e');
          }
        }
      });
    } catch (e) {
      debugPrint('WS Connect Error: $e');
    }
  }

  Future<void> _retryPendingGroupMessages() async {
    final pending = await _cacheService.getPendingGroupMessages(_groupId);
    if (pending.isEmpty) return;
    for (final payload in pending) {
      try {
        final typeName =
            payload['message_type']?.toString() ?? MessageType.text.name;
        final messageType = MessageType.values.firstWhere(
          (e) => e.name == typeName,
          orElse: () => MessageType.text,
        );
        final message = await _repository.sendMessage(
          _groupId,
          type: messageType,
          content: payload['content']?.toString(),
          contentData: payload['content_data'] as Map<String, dynamic>?,
          replyToId: payload['reply_to_id']?.toString(),
          threadRootId: payload['thread_root_id']?.toString(),
          mentionUserIds: (payload['mention_user_ids'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList(),
          nonce: payload['nonce']?.toString(),
        );
        await _cacheService.removePendingGroupMessage(
            _groupId, payload['nonce']?.toString() ?? '',);
        state.whenData((messages) {
          if (!messages.any((m) => m.id == message.id)) {
            state = AsyncValue.data([message, ...messages]);
          }
        });
      } catch (e) {
        debugPrint('Retry pending group message failed: $e');
      }
    }
  }

  @override
  void dispose() {
    _wsService.disconnect();
    super.dispose();
  }

  Future<void> loadMessages() async {
    try {
      final messages = await _repository.getMessages(_groupId);
      state = AsyncValue.data(messages);
      await _cacheService.saveGroupMessages(_groupId, messages);
    } catch (e, st) {
      if (!state.hasValue) {
        state = AsyncValue.error(e, st);
      }
    }
  }

  Future<void> refresh() => loadMessages();

  void setQuote(MessageInfo? message) {
    _quotedMessage = message;
  }

  Future<void> sendMessage({
    required String content,
    MessageType type = MessageType.text,
    String? replyToId,
    String? threadRootId,
    List<String>? mentionUserIds,
  }) async {
    final nonce = const Uuid().v4();
    _pendingNonces.add(nonce);
    state.whenData((messages) => state = AsyncValue.data([...messages]));

    final pendingPayload = {
      'message_type': type.name,
      'content': content,
      'content_data': null,
      'reply_to_id': replyToId,
      'thread_root_id': threadRootId,
      'mention_user_ids': mentionUserIds,
      'nonce': nonce,
    };

    try {
      final message = await _repository.sendMessage(
        _groupId,
        type: type,
        content: content,
        nonce: nonce,
        replyToId: replyToId,
        threadRootId: threadRootId,
        mentionUserIds: mentionUserIds,
      );

      state.whenData((messages) {
        if (!messages.any((m) => m.id == message.id)) {
          state = AsyncValue.data([message, ...messages]);
        }
      });
      _quotedMessage = null; // Clear quote after sending
      await _cacheService.removePendingGroupMessage(_groupId, nonce);
      _pendingNonces.remove(nonce);
    } catch (e) {
      _pendingNonces.remove(nonce);
      await _cacheService.enqueuePendingGroupMessage(_groupId, pendingPayload);
      state.whenData((messages) => state = AsyncValue.data([...messages]));
      rethrow;
    }
  }

  Future<void> revokeMessage(String messageId) async {
    try {
      await _repository.revokeGroupMessage(_groupId, messageId);
      _handleRevokedEvent(messageId);
    } catch (e) {
      rethrow;
    }
  }

  Future<void> editMessage(String messageId, String content) async {
    try {
      final message = await _repository.editGroupMessage(
        _groupId,
        messageId,
        content: content,
      );
      _handleEditedEvent(message);
    } catch (e) {
      rethrow;
    }
  }

  Future<void> toggleReaction(String messageId, String emoji) async {
    final userId = await _resolveCurrentUserId();
    if (userId == null || userId.isEmpty) return;
    final messages = state.valueOrNull ?? [];
    if (messages.isEmpty) return;
    final targetIndex = messages.indexWhere((m) => m.id == messageId);
    if (targetIndex == -1) return;
    final target = messages[targetIndex];
    final currentReactions = Map<String, dynamic>.from(target.reactions ?? {});
    final users = List<String>.from(
      (currentReactions[emoji] as Iterable<dynamic>?) ?? const <String>[],
    );
    final isAdd = !users.contains(userId);
    try {
      final message = await _repository.updateGroupReaction(
        _groupId,
        messageId,
        emoji: emoji,
        userId: userId,
        isAdd: isAdd,
      );
      _handleReactionUpdate(message.id, message.reactions);
    } catch (e) {
      rethrow;
    }
  }

  Future<List<MessageInfo>> searchMessages(String keyword) async =>
      _repository.searchGroupMessages(_groupId, keyword);

  Future<List<MessageInfo>> getThreadMessages(String threadRootId) async =>
      _repository.getThreadMessages(_groupId, threadRootId);

  void _handleRevokedEvent(String messageId) {
    state.whenData((messages) {
      final index = messages.indexWhere((m) => m.id == messageId);
      if (index != -1) {
        final updated = [...messages];
        final original = updated[index];
        updated[index] = MessageInfo(
          id: original.id,
          content: original.content,
          messageType: original.messageType,
          sender: original.sender,
          createdAt: original.createdAt,
          updatedAt: original.updatedAt,
          isRevoked: true,
          revokedAt: DateTime.now(),
          editedAt: original.editedAt,
          contentData: original.contentData,
          readBy: original.readBy,
          replyToId: original.replyToId,
          threadRootId: original.threadRootId,
          mentionUserIds: original.mentionUserIds,
          reactions: original.reactions,
          readByUsers: original.readByUsers,
          quotedMessage: original.quotedMessage,
        );
        state = AsyncValue.data(updated);
      }
    });
  }

  void _handleEditedEvent(MessageInfo message) {
    state.whenData((messages) {
      final index = messages.indexWhere((m) => m.id == message.id);
      if (index != -1) {
        final updated = [...messages];
        updated[index] = message;
        state = AsyncValue.data(updated);
      } else {
        state = AsyncValue.data([message, ...messages]);
      }
    });
  }

  void _handleReactionUpdate(
      String messageId, Map<String, dynamic>? reactions,) {
    state.whenData((messages) {
      final index = messages.indexWhere((m) => m.id == messageId);
      if (index != -1) {
        final original = messages[index];
        final updated = [...messages];
        updated[index] = MessageInfo(
          id: original.id,
          messageType: original.messageType,
          sender: original.sender,
          content: original.content,
          contentData: original.contentData,
          replyToId: original.replyToId,
          threadRootId: original.threadRootId,
          mentionUserIds: original.mentionUserIds,
          reactions: reactions ?? original.reactions,
          createdAt: original.createdAt,
          updatedAt: DateTime.now(),
          isRevoked: original.isRevoked,
          revokedAt: original.revokedAt,
          editedAt: original.editedAt,
          readBy: original.readBy,
          quotedMessage: original.quotedMessage,
          readByUsers: original.readByUsers,
        );
        state = AsyncValue.data(updated);
      }
    });
  }

  Future<String?> _resolveCurrentUserId() async {
    final current = _ref.read(currentUserProvider)?.id;
    if (current != null && current.isNotEmpty) {
      return current;
    }
    try {
      final guestService = _ref.read(guestServiceProvider);
      return await guestService.getGuestId();
    } catch (_) {
      return 'guest';
    }
  }
}

// 6. Group Search Provider
final groupSearchProvider =
    StateNotifierProvider<GroupSearchNotifier, AsyncValue<List<GroupListItem>>>(
        (ref) => GroupSearchNotifier(ref.watch(communityRepositoryProvider)),);

class GroupSearchNotifier
    extends StateNotifier<AsyncValue<List<GroupListItem>>> {
  GroupSearchNotifier(this._repository) : super(const AsyncValue.data([]));
  final CommunityRepository _repository;

  Future<void> search(String keyword) async {
    state = const AsyncValue.loading();
    try {
      final groups = await _repository.searchGroups(keyword: keyword);
      state = AsyncValue.data(groups);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }
}

// 7. Group Tasks Provider (Family)
final groupTasksProvider = StateNotifierProvider.family<GroupTasksNotifier,
        AsyncValue<List<GroupTaskInfo>>, String>(
    (ref, groupId) =>
        GroupTasksNotifier(ref.watch(communityRepositoryProvider), groupId),);

class GroupTasksNotifier
    extends StateNotifier<AsyncValue<List<GroupTaskInfo>>> {
  GroupTasksNotifier(this._repository, this._groupId)
      : super(const AsyncValue.loading()) {
    loadTasks();
  }
  final CommunityRepository _repository;
  final String _groupId;

  Future<void> loadTasks() async {
    state = const AsyncValue.loading();
    try {
      final tasks = await _repository.getGroupTasks(_groupId);
      state = AsyncValue.data(tasks);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadTasks();

  Future<void> claimTask(String taskId) async {
    try {
      await _repository.claimTask(taskId);
      await loadTasks();
    } catch (e) {
      rethrow;
    }
  }
}

// 8. Private Chat Provider (Family)
final privateChatProvider = StateNotifierProvider.autoDispose
    .family<PrivateChatNotifier, AsyncValue<List<PrivateMessageInfo>>, String>(
        (ref, friendId) {
  final stream = ref.watch(communityEventsStreamProvider);
  return PrivateChatNotifier(
    ref.watch(communityRepositoryProvider),
    friendId,
    stream,
    ref,
  );
});

class PrivateChatNotifier
    extends StateNotifier<AsyncValue<List<PrivateMessageInfo>>> {
  PrivateChatNotifier(
      this._repository, this._friendId, Stream<dynamic> events, this._ref,)
      : super(const AsyncValue.loading()) {
    _initialize(events);
  }
  final CommunityRepository _repository;
  final String _friendId;
  final ChatCacheService _cacheService = ChatCacheService();
  final Ref _ref;
  String? _currentUserId;

  final Set<String> _pendingNonces = {};
  Set<String> get pendingNonces => _pendingNonces;

  PrivateMessageInfo? _quotedMessage;
  PrivateMessageInfo? get quotedMessage => _quotedMessage;

  Future<void> _initialize(Stream<dynamic> events) async {
    final cached = await _cacheService.getCachedPrivateMessages(_friendId);
    if (cached.isNotEmpty && mounted) {
      state = AsyncValue.data(cached);
    }
    await loadMessages();
    await _retryPendingPrivateMessages();
    events.listen(_handleEvent);
  }

  void _handleEvent(dynamic data) {
    if (data is String) {
      try {
            final jsonData = jsonDecode(data) as Map<String, dynamic>;

        if (jsonData['type'] == 'ack') {
          final nonce = jsonData['nonce'];
          if (nonce != null && _pendingNonces.contains(nonce)) {
            _pendingNonces.remove(nonce);
            Future(() => _cacheService.removePendingPrivateMessage(
                _friendId, nonce.toString(),),);
            state
                .whenData((messages) => state = AsyncValue.data([...messages]));
          }
          return;
        }

        if (jsonData['type'] == 'message_edit' && jsonData['message'] != null) {
          final message = PrivateMessageInfo.fromJson(
            jsonData['message'] as Map<String, dynamic>,
          );
          _handleEditedEvent(message);
          return;
        }

        if (jsonData['type'] == 'mention' && jsonData['message'] != null) {
          final groupMessage = MessageInfo.fromJson(
            jsonData['message'] as Map<String, dynamic>,
          );
          _ref.read(unreadMessageCountProvider.notifier).increment();
          _ref.read(inAppNotificationProvider.notifier).show(
                NotificationMessage(
                  id: groupMessage.id,
                  senderName: groupMessage.sender?.displayName ?? '群成员',
                  senderAvatarUrl: groupMessage.sender?.avatarUrl,
                  content: groupMessage.content ?? '提及了你',
                  timestamp: groupMessage.createdAt,
                  type: NotificationType.mention,
                  targetId: jsonData['group_id']?.toString(),
                ),
              );
          return;
        }

        if (jsonData['type'] == 'message_revoke' ||
            jsonData['type'] == 'revoked') {
          final messageId = jsonData['message_id'];
          if (messageId != null) {
            _handleRevokedEvent(messageId.toString());
          }
          return;
        }

        if (jsonData['type'] == 'reaction_update') {
          final messageId = jsonData['message_id'];
          final reactions = jsonData['reactions'];
          if (messageId != null) {
            _handleReactionUpdate(
                messageId.toString(), reactions as Map<String, dynamic>?,);
          }
          return;
        }

        if (jsonData['sender'] != null && jsonData['receiver'] != null) {
          try {
            final message = PrivateMessageInfo.fromJson(jsonData);
            if (message.sender.id == _friendId ||
                message.receiver.id == _friendId) {
              state.whenData((messages) {
                if (!messages.any((m) => m.id == message.id)) {
                  final updated = [message, ...messages];
                  state = AsyncValue.data(updated);

                  // Trigger in-app notification for incoming messages
                  if (message.sender.id == _friendId) {
                    _ref.read(unreadMessageCountProvider.notifier).increment();
                    _ref.read(inAppNotificationProvider.notifier).show(
                          NotificationMessage(
                            id: message.id,
                            senderName: message.sender.displayName,
                            senderAvatarUrl: message.sender.avatarUrl,
                            content: message.content ?? '',
                            timestamp: message.createdAt,
                            type: NotificationType.privateMessage,
                            targetId: _friendId,
                          ),
                        );
                  }
                }
              });
            }
          } catch (_) {}
        }
      } catch (e) {
        debugPrint('WS Parse Error (Private): $e');
      }
    }
  }

  Future<void> _retryPendingPrivateMessages() async {
    final pending = await _cacheService.getPendingPrivateMessages(_friendId);
    if (pending.isEmpty) return;
    for (final payload in pending) {
      try {
        final typeName =
            payload['message_type']?.toString() ?? MessageType.text.name;
        final messageType = MessageType.values.firstWhere(
          (e) => e.name == typeName,
          orElse: () => MessageType.text,
        );
        final message = await _repository.sendPrivateMessage(
          PrivateMessageSend(
            targetUserId: _friendId,
            content: payload['content']?.toString(),
            messageType: messageType,
            contentData: payload['content_data'] as Map<String, dynamic>?,
            replyToId: payload['reply_to_id']?.toString(),
            threadRootId: payload['thread_root_id']?.toString(),
            mentionUserIds: (payload['mention_user_ids'] as List<dynamic>?)
                ?.map((e) => e.toString())
                .toList(),
            nonce: payload['nonce']?.toString(),
          ),
        );
        await _cacheService.removePendingPrivateMessage(
            _friendId, payload['nonce']?.toString() ?? '',);
        state.whenData((messages) {
          final tempId = 'local_${payload['nonce'] ?? ''}';
          final filtered = messages.where((m) => m.id != tempId).toList();
          if (!filtered.any((m) => m.id == message.id)) {
            state = AsyncValue.data([message, ...filtered]);
          } else {
            state = AsyncValue.data(filtered);
          }
        });
      } catch (e) {
        debugPrint('Retry pending private message failed: $e');
      }
    }
  }

  void _handleRevokedEvent(String messageId) {
    state.whenData((messages) {
      final index = messages.indexWhere((m) => m.id == messageId);
      if (index != -1) {
        final updated = [...messages];
        updated[index] =
            updated[index].copyWith(isRevoked: true, revokedAt: DateTime.now());
        state = AsyncValue.data(updated);
      }
    });
  }

  void _handleEditedEvent(PrivateMessageInfo message) {
    state.whenData((messages) {
      final isRelated =
          message.sender.id == _friendId || message.receiver.id == _friendId;
      if (!isRelated) return;
      final index = messages.indexWhere((m) => m.id == message.id);
      if (index != -1) {
        final updated = [...messages];
        updated[index] = message;
        state = AsyncValue.data(updated);
      } else {
        state = AsyncValue.data([message, ...messages]);
      }
    });
  }

  void _handleReactionUpdate(
      String messageId, Map<String, dynamic>? reactions,) {
    state.whenData((messages) {
      final index = messages.indexWhere((m) => m.id == messageId);
      if (index != -1) {
        final updated = [...messages];
        updated[index] = updated[index].copyWith(
          reactions: reactions ?? updated[index].reactions,
          updatedAt: DateTime.now(),
        );
        state = AsyncValue.data(updated);
      }
    });
  }

  Future<void> loadMessages() async {
    try {
      final messages = await _repository.getPrivateMessages(_friendId);
      state = AsyncValue.data(messages);
      await _cacheService.savePrivateMessages(_friendId, messages);
    } catch (e, st) {
      if (!state.hasValue) {
        state = AsyncValue.error(e, st);
      }
    }
  }

  void setQuote(PrivateMessageInfo? message) {
    _quotedMessage = message;
    // We trigger a state update to the same list to notify listeners of notifier itself
    // Actually, simple getter is fine if we call it from UI, but for reactive UI
    // we might need a separate StateProvider for quotedMessage.
    // Let's keep it simple for now as it's passed back to ChatInput.
  }

  Future<void> sendMessage({
    required String content,
    MessageType type = MessageType.text,
    String? replyToId,
    String? threadRootId,
    List<String>? mentionUserIds,
  }) async {
    final nonce = const Uuid().v4();
    _pendingNonces.add(nonce);

    final pendingPayload = {
      'message_type': type.name,
      'content': content,
      'content_data': null,
      'reply_to_id': replyToId,
      'thread_root_id': threadRootId,
      'mention_user_ids': mentionUserIds,
      'nonce': nonce,
    };

    final tempId = 'local_$nonce';
    final sender = await _buildCurrentUserBrief();
    final receiver = _buildFriendBrief();
    final tempMessage = PrivateMessageInfo(
      id: tempId,
      sender: sender,
      receiver: receiver,
      messageType: type,
      content: content,
      replyToId: replyToId,
      threadRootId: threadRootId,
      mentionUserIds: mentionUserIds,
      isRead: true,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      isSending: true,
    );

    state.whenData(
        (messages) => state = AsyncValue.data([tempMessage, ...messages]),);

    try {
      final message = await _repository.sendPrivateMessage(
        PrivateMessageSend(
          targetUserId: _friendId,
          content: content,
          messageType: type,
          nonce: nonce,
          replyToId: replyToId,
          threadRootId: threadRootId,
          mentionUserIds: mentionUserIds,
        ),
      );

      state.whenData((messages) {
        final filtered = messages.where((m) => m.id != tempId).toList();
        if (!filtered.any((m) => m.id == message.id)) {
          state = AsyncValue.data([message, ...filtered]);
        } else {
          state = AsyncValue.data(filtered);
        }
      });
      _quotedMessage = null; // Clear quote after sending
      await _cacheService.removePendingPrivateMessage(_friendId, nonce);
      _pendingNonces.remove(nonce);
    } catch (e) {
      _pendingNonces.remove(nonce);
      await _cacheService.enqueuePendingPrivateMessage(
          _friendId, pendingPayload,);
      state.whenData((messages) {
        final updated = messages.map((m) {
          if (m.id == tempId) {
            return m.copyWith(isSending: false, hasError: true);
          }
          return m;
        }).toList();
        state = AsyncValue.data(updated);
      });
      rethrow;
    }
  }

  Future<void> revokeMessage(String messageId) async {
    try {
      await _repository.revokePrivateMessage(messageId);
      _handleRevokedEvent(messageId);
    } catch (e) {
      rethrow;
    }
  }

  Future<void> editMessage(String messageId, String content) async {
    try {
      final message =
          await _repository.editPrivateMessage(messageId, content: content);
      _handleEditedEvent(message);
    } catch (e) {
      rethrow;
    }
  }

  Future<void> toggleReaction(String messageId, String emoji) async {
    final userId = await _resolveCurrentUserId();
    if (userId == null || userId.isEmpty) return;
    final messages = state.valueOrNull ?? [];
    if (messages.isEmpty) return;
    final targetIndex = messages.indexWhere((m) => m.id == messageId);
    if (targetIndex == -1) return;
    final target = messages[targetIndex];
    final currentReactions = Map<String, dynamic>.from(target.reactions ?? {});
    final users = List<String>.from(
      (currentReactions[emoji] as Iterable<dynamic>?) ?? const <String>[],
    );
    final isAdd = !users.contains(userId);
    try {
      final message = await _repository.updatePrivateReaction(
        messageId,
        emoji: emoji,
        userId: userId,
        isAdd: isAdd,
      );
      _handleReactionUpdate(message.id, message.reactions);
    } catch (e) {
      rethrow;
    }
  }

  Future<List<PrivateMessageInfo>> searchMessages(String keyword) async =>
      _repository.searchPrivateMessages(_friendId, keyword);

  Future<UserBrief> _buildCurrentUserBrief() async {
    final user = _ref.read(currentUserProvider);
    if (user == null) {
      var userId = 'guest';
      var nickname = '访客';
      try {
        final guestService = _ref.read(guestServiceProvider);
        userId = await guestService.getGuestId();
        nickname = guestService.getGuestNickname();
      } catch (_) {}
      return UserBrief(
        id: userId,
        username: nickname,
        nickname: nickname,
        flameBrightness: 0.4,
        status: UserStatus.online,
      );
    }
    return UserBrief(
      id: user.id,
      username: user.username,
      nickname: user.nickname,
      avatarUrl: user.avatarUrl,
      flameLevel: user.flameLevel,
      flameBrightness: user.flameBrightness,
      status: user.status,
    );
  }

  UserBrief _buildFriendBrief() {
    final existing = state.valueOrNull?.firstWhere(
      (m) => m.sender.id == _friendId || m.receiver.id == _friendId,
      orElse: () => PrivateMessageInfo(
        id: 'placeholder',
        sender: UserBrief(id: _friendId, username: 'Friend'),
        receiver: UserBrief(id: _friendId, username: 'Friend'),
        messageType: MessageType.text,
        isRead: true,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      ),
    );
    if (existing is PrivateMessageInfo) {
      if (existing.sender.id == _friendId) {
        return existing.sender;
      }
      return existing.receiver;
    }
    return UserBrief(id: _friendId, username: 'Friend');
  }

  Future<String?> _resolveCurrentUserId() async {
    final current = _currentUserId ?? _ref.read(currentUserProvider)?.id;
    if (current != null && current.isNotEmpty) {
      return current;
    }
    try {
      final guestService = _ref.read(guestServiceProvider);
      return await guestService.getGuestId();
    } catch (_) {
      return 'guest';
    }
  }
}

// 9. Current User Status Provider
final currentUserStatusProvider =
    StateNotifierProvider<CurrentUserStatusNotifier, UserStatus>((ref) =>
        CurrentUserStatusNotifier(ref.watch(communityRepositoryProvider)),);

class CurrentUserStatusNotifier extends StateNotifier<UserStatus> {
  CurrentUserStatusNotifier(this._repository) : super(UserStatus.online);
  final CommunityRepository _repository;

  Future<void> updateStatus(UserStatus newStatus) async {
    try {
      state = newStatus;
      await _repository.updateStatus(newStatus);
    } catch (e) {
      debugPrint('Update Status Failed: $e');
    }
  }
}
