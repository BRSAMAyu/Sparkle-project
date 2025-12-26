import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/websocket_service.dart';
import 'package:sparkle/core/services/chat_cache_service.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/data/repositories/community_repository.dart';
import 'package:sparkle/data/repositories/mock_community_repository.dart';
import 'package:sparkle/data/repositories/auth_repository.dart';

// Mock Community Repository Provider
final communityRepositoryProvider = Provider<CommunityRepository>((ref) {
  return MockCommunityRepository.instance();
});

// Token provider for WebSocket connections
final _wsTokenProvider = FutureProvider.autoDispose<String?>((ref) async {
  final authRepo = ref.watch(authRepositoryProvider);
  return authRepo.getAccessToken();
});

// Global Community Events Stream
final communityEventsStreamProvider = Provider.autoDispose<Stream<dynamic>>((ref) {
  final wsService = WebSocketService();
  final tokenAsync = ref.watch(_wsTokenProvider);

  final token = tokenAsync.valueOrNull;
  if (token == null) {
    // Return empty stream if no token yet
    return const Stream.empty();
  }

  final baseUrl = ApiEndpoints.baseUrl.replaceFirst(RegExp(r'^http'), 'ws');
  final wsUrl = '$baseUrl/community/ws/connect?token=$token';

  try {
    wsService.connect(wsUrl);
  } catch (e) {
    debugPrint('WS Connect Error: $e');
    return const Stream.empty();
  }

  ref.onDispose(() {
    wsService.disconnect();
  });

  return wsService.stream;
});

// 1. Friends Provider
final friendsProvider = StateNotifierProvider<FriendsNotifier, AsyncValue<List<FriendshipInfo>>>((ref) {
  final stream = ref.watch(communityEventsStreamProvider);
  return FriendsNotifier(ref.watch(communityRepositoryProvider), stream);
});

class FriendsNotifier extends StateNotifier<AsyncValue<List<FriendshipInfo>>> {
  final CommunityRepository _repository;

  FriendsNotifier(this._repository, Stream<dynamic> events) : super(const AsyncValue.loading()) {
    loadFriends();
    events.listen(_handleEvent);
  }

  void _handleEvent(dynamic data) {
    if (data is String) {
      try {
        final json = jsonDecode(data);
        if (json['type'] == 'status_update') {
           _updateFriendStatus(json['user_id'], json['status']);
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

final pendingRequestsProvider = StateNotifierProvider<PendingRequestsNotifier, AsyncValue<List<FriendshipInfo>>>((ref) {
  return PendingRequestsNotifier(ref.watch(communityRepositoryProvider));
});

class PendingRequestsNotifier extends StateNotifier<AsyncValue<List<FriendshipInfo>>> {
  final CommunityRepository _repository;

  PendingRequestsNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadPendingRequests();
  }

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
final friendRecommendationsProvider = StateNotifierProvider<FriendRecommendationsNotifier, AsyncValue<List<FriendRecommendation>>>((ref) {
  return FriendRecommendationsNotifier(ref.watch(communityRepositoryProvider));
});

class FriendRecommendationsNotifier extends StateNotifier<AsyncValue<List<FriendRecommendation>>> {
  final CommunityRepository _repository;

  FriendRecommendationsNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadRecommendations();
  }

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
final userSearchProvider = StateNotifierProvider<UserSearchNotifier, AsyncValue<List<UserBrief>>>((ref) {
  return UserSearchNotifier(ref.watch(communityRepositoryProvider));
});

class UserSearchNotifier extends StateNotifier<AsyncValue<List<UserBrief>>> {
  final CommunityRepository _repository;

  UserSearchNotifier(this._repository) : super(const AsyncValue.data([]));

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
final myGroupsProvider = StateNotifierProvider<MyGroupsNotifier, AsyncValue<List<GroupListItem>>>((ref) {
  return MyGroupsNotifier(ref.watch(communityRepositoryProvider));
});

final groupDetailProvider = StateNotifierProvider.family<GroupDetailNotifier, AsyncValue<GroupInfo>, String>((ref, groupId) {
  return GroupDetailNotifier(ref.watch(communityRepositoryProvider), groupId);
});

class GroupDetailNotifier extends StateNotifier<AsyncValue<GroupInfo>> {
  final CommunityRepository _repository;
  final String _groupId;

  GroupDetailNotifier(this._repository, this._groupId) : super(const AsyncValue.loading()) {
    loadDetail();
  }

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
      final response = await _repository.checkin(_groupId, todayDurationMinutes: minutes, message: message);
      await loadDetail();
      return response;
    } catch (e) {
      rethrow;
    }
  }
}

class MyGroupsNotifier extends StateNotifier<AsyncValue<List<GroupListItem>>> {
  final CommunityRepository _repository;

  MyGroupsNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadGroups();
  }

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
final groupChatProvider = StateNotifierProvider.family<GroupChatNotifier, AsyncValue<List<MessageInfo>>, String>((ref, groupId) {
  return GroupChatNotifier(
    ref.watch(communityRepositoryProvider),
    ref.watch(authRepositoryProvider),
    groupId,
  );
});

class GroupChatNotifier extends StateNotifier<AsyncValue<List<MessageInfo>>> {
  final CommunityRepository _repository;
  final AuthRepository _authRepository;
  final String _groupId;
  final WebSocketService _wsService = WebSocketService();
  final ChatCacheService _cacheService = ChatCacheService();
  
  final Set<String> _pendingNonces = {};
  Set<String> get pendingNonces => _pendingNonces;

  GroupChatNotifier(this._repository, this._authRepository, this._groupId) : super(const AsyncValue.loading()) {
    _initialize();
  }

  Future<void> _initialize() async {
    final cached = await _cacheService.getCachedGroupMessages(_groupId);
    if (cached.isNotEmpty && mounted) {
      state = AsyncValue.data(cached);
    }
    await loadMessages();
    await _connectWebSocket();
  }

  Future<void> _connectWebSocket() async {
    final token = await _authRepository.getAccessToken();
    if (token == null) return;

    final baseUrl = ApiEndpoints.baseUrl.replaceFirst(RegExp(r'^http'), 'ws');
    final wsUrl = '$baseUrl/community/groups/$_groupId/ws?token=$token';

    try {
      _wsService.connect(wsUrl);
      _wsService.stream.listen((data) {
        if (data is String) {
          try {
            final jsonData = jsonDecode(data);
            
            if (jsonData['type'] == 'ack') {
              final nonce = jsonData['nonce'];
              if (nonce != null && _pendingNonces.contains(nonce)) {
                _pendingNonces.remove(nonce);
                state.whenData((messages) => state = AsyncValue.data([...messages]));
              }
              return;
            }

            final message = MessageInfo.fromJson(jsonData);
            state.whenData((messages) {
              if (!messages.any((m) => m.id == message.id)) {
                state = AsyncValue.data([message, ...messages]);
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

  Future<void> sendMessage({required String content, MessageType type = MessageType.text}) async {
    final nonce = const Uuid().v4();
    _pendingNonces.add(nonce);
    state.whenData((messages) => state = AsyncValue.data([...messages]));

    try {
      final message = await _repository.sendMessage(
        _groupId, 
        type: type, 
        content: content,
        nonce: nonce,
      );
      
      state.whenData((messages) {
        if (!messages.any((m) => m.id == message.id)) {
          state = AsyncValue.data([message, ...messages]);
        }
      });
    } catch (e) {
      _pendingNonces.remove(nonce);
      state.whenData((messages) => state = AsyncValue.data([...messages]));
      rethrow;
    }
  }
}

// 6. Group Search Provider
final groupSearchProvider = StateNotifierProvider<GroupSearchNotifier, AsyncValue<List<GroupListItem>>>((ref) {
  return GroupSearchNotifier(ref.watch(communityRepositoryProvider));
});

class GroupSearchNotifier extends StateNotifier<AsyncValue<List<GroupListItem>>> {
  final CommunityRepository _repository;

  GroupSearchNotifier(this._repository) : super(const AsyncValue.data([]));

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
final groupTasksProvider = StateNotifierProvider.family<GroupTasksNotifier, AsyncValue<List<GroupTaskInfo>>, String>((ref, groupId) {
  return GroupTasksNotifier(ref.watch(communityRepositoryProvider), groupId);
});

class GroupTasksNotifier extends StateNotifier<AsyncValue<List<GroupTaskInfo>>> {
  final CommunityRepository _repository;
  final String _groupId;

  GroupTasksNotifier(this._repository, this._groupId) : super(const AsyncValue.loading()) {
    loadTasks();
  }

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
final privateChatProvider = StateNotifierProvider.autoDispose.family<PrivateChatNotifier, AsyncValue<List<PrivateMessageInfo>>, String>((ref, friendId) {
  final stream = ref.watch(communityEventsStreamProvider);
  return PrivateChatNotifier(
    ref.watch(communityRepositoryProvider),
    friendId,
    stream,
  );
});

class PrivateChatNotifier extends StateNotifier<AsyncValue<List<PrivateMessageInfo>>> {
  final CommunityRepository _repository;
  final String _friendId;
  final ChatCacheService _cacheService = ChatCacheService();
  
  final Set<String> _pendingNonces = {};
  Set<String> get pendingNonces => _pendingNonces;

  PrivateChatNotifier(this._repository, this._friendId, Stream<dynamic> events) : super(const AsyncValue.loading()) {
    _initialize(events);
  }

  Future<void> _initialize(Stream<dynamic> events) async {
    final cached = await _cacheService.getCachedPrivateMessages(_friendId);
    if (cached.isNotEmpty && mounted) {
      state = AsyncValue.data(cached);
    }
    await loadMessages();
    events.listen(_handleEvent);
  }

  void _handleEvent(dynamic data) {
    if (data is String) {
      try {
        final jsonData = jsonDecode(data);
        
        if (jsonData['type'] == 'ack') {
          final nonce = jsonData['nonce'];
          if (nonce != null && _pendingNonces.contains(nonce)) {
            _pendingNonces.remove(nonce);
            state.whenData((messages) => state = AsyncValue.data([...messages]));
          }
          return;
        }

        if (jsonData['sender'] != null && jsonData['receiver'] != null) {
           try {
             final message = PrivateMessageInfo.fromJson(jsonData);
             if (message.sender.id == _friendId || message.receiver.id == _friendId) {
               state.whenData((messages) {
                 if (!messages.any((m) => m.id == message.id)) {
                   final updated = [message, ...messages];
                   state = AsyncValue.data(updated);
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

  Future<void> sendMessage({required String content, MessageType type = MessageType.text}) async {
    final nonce = const Uuid().v4();
    _pendingNonces.add(nonce);
    state.whenData((messages) => state = AsyncValue.data([...messages]));

    try {
      final message = await _repository.sendPrivateMessage(
        PrivateMessageSend(
          targetUserId: _friendId,
          content: content,
          messageType: type,
          nonce: nonce,
        ),
      );
      
      state.whenData((messages) {
        if (!messages.any((m) => m.id == message.id)) {
          state = AsyncValue.data([message, ...messages]);
        }
      });
    } catch (e) {
      _pendingNonces.remove(nonce);
      state.whenData((messages) => state = AsyncValue.data([...messages]));
      rethrow;
    }
  }
}

// 9. Current User Status Provider
final currentUserStatusProvider = StateNotifierProvider<CurrentUserStatusNotifier, UserStatus>((ref) {
  return CurrentUserStatusNotifier(ref.watch(communityRepositoryProvider));
});

class CurrentUserStatusNotifier extends StateNotifier<UserStatus> {
  final CommunityRepository _repository;
  CurrentUserStatusNotifier(this._repository) : super(UserStatus.online);

  Future<void> updateStatus(UserStatus newStatus) async {
    try {
      state = newStatus;
      await _repository.updateStatus(newStatus);
    } catch (e) {
      debugPrint('Update Status Failed: $e');
    }
  }
}
