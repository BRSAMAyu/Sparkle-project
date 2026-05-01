import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/websocket_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:uuid/uuid.dart';

// WebSocket connection state enum
enum WebSocketConnectionState {
  connecting,
  connected,
  disconnected,
}

// Token provider for WebSocket connections
final _wsTokenProvider = FutureProvider.autoDispose<String?>((ref) async {
  final authRepo = ref.watch(authRepositoryProvider);
  return authRepo.getAccessToken();
});

// Global Community Events Stream
final communityEventsStreamProvider =
    Provider.autoDispose<Stream<dynamic>>((ref) {
  // 🔧 Demo 模式下禁用 WebSocket，使用 Mock 数据
  if (DemoDataService.isDemoMode) {
    debugPrint('🎭 Demo Mode: Using mock community data, WebSocket disabled');
    return const Stream.empty();
  }

  final wsService = WebSocketService();
  final tokenAsync = ref.watch(_wsTokenProvider);

  final token = tokenAsync.valueOrNull;
  if (token == null) {
    return const Stream.empty();
  }

  final baseUrl = ApiEndpoints.baseUrl.replaceFirst(RegExp('^http'), 'ws');
  // 支持两种认证方式：headers用于移动端，query param用于Web端fallback
  final wsUrl = '$baseUrl/community/ws/connect?token=$token';
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

Map<String, dynamic>? _decodeCommunityWsPayload(dynamic data) {
  if (data is Map<String, dynamic>) {
    return data;
  }
  if (data is Map) {
    return Map<String, dynamic>.from(data);
  }
  if (data is String) {
    try {
      final decoded = jsonDecode(data);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
      if (decoded is Map) {
        return Map<String, dynamic>.from(decoded);
      }
    } catch (e) {
      debugPrint('Community WS payload decode failed: $e');
      return null;
    }
  }
  return null;
}

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
    _eventsSubscription = events.listen(_handleEvent);
  }
  final CommunityRepository _repository;
  late final StreamSubscription<dynamic> _eventsSubscription;

  void _handleEvent(dynamic data) {
    try {
      final json = data is String
          ? jsonDecode(data) as Map<String, dynamic>
          : data is Map
              ? Map<String, dynamic>.from(data)
              : null;
      if (json == null) return;
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
            initiatedByMe: f.initiatedByMe,
            accountability: f.accountability,
          );
        }
        return f;
      }).toList();

      state = AsyncValue.data(updatedFriends);
    });
  }

  Future<void> loadFriends() async {
    if (!mounted) return;
    state = const AsyncValue.loading();
    try {
      final friends = await _repository.getFriends();
      if (!mounted) return;
      state = AsyncValue.data(friends);
    } catch (e, st) {
      if (!mounted) return;
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadFriends();

  @override
  void dispose() {
    unawaited(_eventsSubscription.cancel());
    super.dispose();
  }

  /// 删除好友
  Future<void> deleteFriend(String friendshipId) async {
    await _repository.deleteFriend(friendshipId);
    // Remove from local state
    state.whenData((friends) {
      state = AsyncValue.data(
        friends.where((f) => f.id != friendshipId).toList(),
      );
    });
  }

  /// 拉黑用户（自动从好友列表移除）
  Future<void> blockUser(String userId, {String? reason}) async {
    await _repository.blockUser(userId, reason: reason);
    // Remove from local state if present
    state.whenData((friends) {
      state = AsyncValue.data(
        friends.where((f) => f.friend.id != userId).toList(),
      );
    });
  }
}

final pendingRequestsProvider = StateNotifierProvider<PendingRequestsNotifier,
    AsyncValue<List<FriendshipInfo>>>(
  (ref) => PendingRequestsNotifier(ref.watch(communityRepositoryProvider)),
);

class PendingRequestsNotifier
    extends StateNotifier<AsyncValue<List<FriendshipInfo>>> {
  PendingRequestsNotifier(this._repository)
      : super(const AsyncValue.loading()) {
    loadPendingRequests();
  }
  final CommunityRepository _repository;

  Future<void> loadPendingRequests() async {
    if (!mounted) return;
    state = const AsyncValue.loading();
    try {
      final requests = await _repository.getPendingRequests();
      if (!mounted) return;
      state = AsyncValue.data(requests);
    } catch (e, st) {
      if (!mounted) return;
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
      FriendRecommendationsNotifier(ref.watch(communityRepositoryProvider)),
);

final friendRecommendationStrategyProvider = StateProvider<FriendMatchStrategy>(
  (_) => FriendMatchStrategy.compatibility,
);

class FriendRecommendationsNotifier
    extends StateNotifier<AsyncValue<List<FriendRecommendation>>> {
  FriendRecommendationsNotifier(this._repository)
      : super(const AsyncValue.loading()) {
    loadRecommendations();
  }
  final CommunityRepository _repository;
  final Set<String> _viewed = {};
  FriendMatchStrategy _strategy = FriendMatchStrategy.compatibility;
  final FriendRecommendationTarget _target =
      FriendRecommendationTarget.accountability;

  Future<void> loadRecommendations() async {
    if (!mounted) return;
    state = const AsyncValue.loading();
    try {
      final recommendations = await _repository.getFriendRecommendations(
        strategy: _strategy,
        target: _target,
      );
      if (!mounted) return;
      state = AsyncValue.data(recommendations);
      try {
        await _recordViews(recommendations);
      } catch (e) {
        debugPrint('Friend recommendation view feedback failed: $e');
      }
    } catch (e, st) {
      if (!mounted) return;
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadRecommendations();

  Future<void> setStrategy(FriendMatchStrategy strategy) async {
    if (_strategy == strategy) return;
    _strategy = strategy;
    _viewed.clear();
    await loadRecommendations();
  }

  Future<void> sendRequest(FriendRecommendation recommendation) async {
    await _repository.sendFriendRequest(recommendation.user.id);
    await _sendFeedback(recommendation, action: 'friend_request');
    _removeRecommendation(recommendation.user.id);
  }

  Future<void> dismiss(FriendRecommendation recommendation) async {
    await _sendFeedback(recommendation, action: 'dismiss');
    _removeRecommendation(recommendation.user.id);
  }

  Future<void> recordAccountabilityInvite(
    FriendRecommendation recommendation,
  ) async {
    await _sendFeedback(recommendation, action: 'accountability_invite');
    _removeRecommendation(recommendation.user.id);
  }

  Future<void> _recordViews(List<FriendRecommendation> recommendations) async {
    for (final recommendation in recommendations) {
      if (!_viewed.add(recommendation.user.id)) {
        continue;
      }
      await _sendFeedback(recommendation, action: 'view');
    }
  }

  Future<void> _sendFeedback(
    FriendRecommendation recommendation, {
    required String action,
  }) async {
    await _repository.sendFriendRecommendationFeedback(
      targetUserId: recommendation.user.id,
      strategy: _strategy,
      target: _target,
      action: action,
      source: 'friends_discover',
      score: recommendation.matchScore,
    );
  }

  void _removeRecommendation(String userId) {
    state.whenData((items) {
      final updated = items.where((item) => item.user.id != userId).toList();
      state = AsyncValue.data(updated);
    });
  }
}

// 2.5 Group Recommendations Provider
final groupRecommendationsProvider = StateNotifierProvider<
    GroupRecommendationsNotifier, AsyncValue<List<GroupRecommendationItem>>>(
  (ref) => GroupRecommendationsNotifier(
    ref.watch(communityRepositoryProvider),
    source: 'list',
    limit: 8,
  ),
);

final groupDiscoverProvider = StateNotifierProvider<GroupDirectoryNotifier,
    AsyncValue<GroupDirectoryInfo>>(
  (ref) => GroupDirectoryNotifier(
    ref.watch(communityRepositoryProvider),
    ref,
  ),
);

final recommendationFeedbackPromptsProvider = StateNotifierProvider<
    RecommendationFeedbackPromptsNotifier,
    AsyncValue<List<RecommendationFeedbackPrompt>>>(
  (ref) => RecommendationFeedbackPromptsNotifier(
    ref.watch(communityRepositoryProvider),
  ),
);

final recommendationFeedbackInsightsProvider = StateNotifierProvider<
    RecommendationFeedbackInsightsNotifier,
    AsyncValue<List<RecommendationFeedbackInsight>>>(
  (ref) => RecommendationFeedbackInsightsNotifier(
    ref.watch(communityRepositoryProvider),
  ),
);

class RecommendationFeedbackPromptsNotifier
    extends StateNotifier<AsyncValue<List<RecommendationFeedbackPrompt>>> {
  RecommendationFeedbackPromptsNotifier(this._repository)
      : super(const AsyncValue.loading()) {
    loadPrompts();
  }

  final CommunityRepository _repository;

  Future<void> loadPrompts() async {
    if (!mounted) return;
    state = const AsyncValue.loading();
    try {
      final prompts = await _repository.getRecommendationFeedbackPrompts();
      if (!mounted) return;
      state = AsyncValue.data(prompts);
    } catch (e, st) {
      if (!mounted) return;
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadPrompts();
}

class RecommendationFeedbackInsightsNotifier
    extends StateNotifier<AsyncValue<List<RecommendationFeedbackInsight>>> {
  RecommendationFeedbackInsightsNotifier(this._repository)
      : super(const AsyncValue.loading()) {
    loadInsights();
  }

  final CommunityRepository _repository;

  Future<void> loadInsights() async {
    if (!mounted) return;
    state = const AsyncValue.loading();
    try {
      final insights = await _repository.getRecommendationFeedbackInsights();
      if (!mounted) return;
      state = AsyncValue.data(insights);
    } catch (e, st) {
      if (!mounted) return;
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadInsights();
}

class GroupRecommendationsNotifier
    extends StateNotifier<AsyncValue<List<GroupRecommendationItem>>> {
  GroupRecommendationsNotifier(
    this._repository, {
    required this.source,
    required this.limit,
  }) : super(const AsyncValue.loading()) {
    loadRecommendations();
  }
  final CommunityRepository _repository;
  final String source;
  final int limit;
  final Set<String> _viewed = {};

  Future<void> loadRecommendations({int cursor = 0}) async {
    if (!mounted) return;
    state = const AsyncValue.loading();
    try {
      final recommendations = await _repository.getGroupRecommendations(
        limit: limit,
        cursor: cursor,
      );
      if (!mounted) return;
      state = AsyncValue.data(recommendations);
      try {
        await _recordViews(recommendations);
      } catch (e) {
        debugPrint('Group recommendation view feedback failed: $e');
      }
    } catch (e, st) {
      if (!mounted) return;
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadRecommendations();

  Future<void> dismiss(String groupId) async {
    await _repository.sendGroupRecommendationFeedback(
      groupId: groupId,
      action: 'dismiss',
      source: source,
      reasonTypes: _reasonTypesFor(groupId),
    );
    state.whenData((items) {
      final updated = items.where((item) => item.group.id != groupId).toList();
      state = AsyncValue.data(updated);
    });
  }

  Future<void> join(String groupId) async {
    await _repository.joinGroup(groupId);
    await _repository.sendGroupRecommendationFeedback(
      groupId: groupId,
      action: 'join',
      source: source,
      reasonTypes: _reasonTypesFor(groupId),
    );
    await refresh();
  }

  Future<void> _recordViews(List<GroupRecommendationItem> items) async {
    final pending = <Future<void>>[];
    for (final item in items) {
      if (_viewed.contains(item.group.id)) continue;
      _viewed.add(item.group.id);
      pending.add(
        _repository.sendGroupRecommendationFeedback(
          groupId: item.group.id,
          action: 'view',
          source: source,
          reasonTypes: item.reasons.map((reason) => reason.type).toList(),
        ),
      );
    }
    if (pending.isNotEmpty) {
      await Future.wait(pending);
    }
  }

  List<String>? _reasonTypesFor(String groupId) {
    final items = state.valueOrNull;
    if (items == null) return null;
    for (final item in items) {
      if (item.group.id == groupId) {
        return item.reasons.map((reason) => reason.type).toList();
      }
    }
    return null;
  }
}

class GroupDirectoryNotifier
    extends StateNotifier<AsyncValue<GroupDirectoryInfo>> {
  GroupDirectoryNotifier(this._repository, this._ref)
      : super(const AsyncValue.loading()) {
    loadDirectory();
  }

  final CommunityRepository _repository;
  final Ref _ref;

  GroupDirectorySort _sortBy = GroupDirectorySort.hot;
  GroupType? _type;
  String _keyword = '';
  final Set<String> _selectedTags = <String>{};

  GroupDirectorySort get sortBy => _sortBy;
  GroupType? get type => _type;
  String get keyword => _keyword;
  Set<String> get selectedTags => _selectedTags;

  Future<void> loadDirectory() async {
    if (!mounted) return;
    final previous = state.valueOrNull;
    if (previous == null) {
      state = const AsyncValue.loading();
    }
    try {
      final directory = await _repository.getGroupDirectory(
        keyword: _keyword.isEmpty ? null : _keyword,
        type: _type,
        tags: _selectedTags.isEmpty ? null : _selectedTags.toList(),
        sortBy: _sortBy,
      );
      if (!mounted) return;
      state = AsyncValue.data(directory);
    } catch (e, st) {
      if (!mounted) return;
      if (previous != null) {
        debugPrint('Group directory refresh failed, keeping previous data: $e');
        state = AsyncValue.data(previous);
        return;
      }
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadDirectory();

  Future<void> setSortBy(GroupDirectorySort sortBy) async {
    if (_sortBy == sortBy) return;
    _sortBy = sortBy;
    await loadDirectory();
  }

  Future<void> setKeyword(String keyword) async {
    _keyword = keyword.trim();
    await loadDirectory();
  }

  Future<void> setType(GroupType? type) async {
    _type = type;
    await loadDirectory();
  }

  Future<void> toggleTag(String tag) async {
    if (_selectedTags.contains(tag)) {
      _selectedTags.remove(tag);
    } else {
      _selectedTags.add(tag);
    }
    await loadDirectory();
  }

  Future<void> clearFilters() async {
    _sortBy = GroupDirectorySort.hot;
    _type = null;
    _keyword = '';
    _selectedTags.clear();
    await loadDirectory();
  }

  Future<void> join(String groupId) async {
    await _repository.joinGroup(groupId);
    _ref.invalidate(myGroupsProvider);
    _ref.invalidate(groupRecommendationsProvider);
    await loadDirectory();
  }
}

// 3. User Search Provider
final userSearchProvider =
    StateNotifierProvider<UserSearchNotifier, AsyncValue<List<UserBrief>>>(
  (ref) => UserSearchNotifier(ref.watch(communityRepositoryProvider)),
);

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
  (ref) => MyGroupsNotifier(
    ref.watch(communityRepositoryProvider),
    ref,
  ),
);

final groupDetailProvider = StateNotifierProvider.family<GroupDetailNotifier,
    AsyncValue<GroupInfo>, String>(
  (ref, groupId) => GroupDetailNotifier(
    ref.watch(communityRepositoryProvider),
    groupId,
    ref,
  ),
);

class GroupDetailNotifier extends StateNotifier<AsyncValue<GroupInfo>> {
  GroupDetailNotifier(this._repository, this._groupId, this._ref)
      : super(const AsyncValue.loading()) {
    loadDetail();
  }
  final CommunityRepository _repository;
  final String _groupId;
  final Ref _ref;

  Future<void> loadDetail() async {
    final previous = state.valueOrNull;
    if (previous == null) {
      state = const AsyncValue.loading();
    }
    try {
      final detail = await _repository.getGroup(_groupId);
      state = AsyncValue.data(detail);
    } catch (e, st) {
      if (previous != null) {
        debugPrint('Group detail refresh failed, keeping previous data: $e');
        state = AsyncValue.data(previous);
        return;
      }
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadDetail();

  Future<void> joinGroup() async {
    try {
      await _repository.joinGroup(_groupId);
      _ref.invalidate(myGroupsProvider);
      _ref.invalidate(groupDiscoverProvider);
      _ref.invalidate(groupRecommendationsProvider);
      _ref.invalidate(groupMembersProvider(_groupId));
      await loadDetail();
    } catch (e) {
      rethrow;
    }
  }

  Future<void> leaveGroup() async {
    try {
      await _repository.leaveGroup(_groupId);
      _ref.invalidate(myGroupsProvider);
      _ref.invalidate(groupDiscoverProvider);
      _ref.invalidate(groupRecommendationsProvider);
      _ref.invalidate(groupMembersProvider(_groupId));
      await loadDetail();
    } catch (e) {
      rethrow;
    }
  }

  Future<CheckinResponse> checkin(int minutes, String? message) async {
    try {
      final response = await _repository.checkin(
        _groupId,
        todayDurationMinutes: minutes,
        message: message,
      );
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.checkin));
      _ref.invalidate(groupMembersProvider(_groupId));
      await loadDetail();
      return response;
    } catch (e) {
      rethrow;
    }
  }

  Future<void> updateAnnouncement(String? announcement) async {
    try {
      await _repository.updateAnnouncement(_groupId, announcement);
      await loadDetail();
    } catch (e) {
      rethrow;
    }
  }
}

class MyGroupsNotifier extends StateNotifier<AsyncValue<List<GroupListItem>>> {
  MyGroupsNotifier(this._repository, this._ref)
      : super(const AsyncValue.loading()) {
    loadGroups();
  }
  final CommunityRepository _repository;
  final Ref _ref;

  Future<void> loadGroups() async {
    if (!mounted) return;
    final previous = state.valueOrNull;
    if (previous == null) {
      state = const AsyncValue.loading();
    }
    try {
      final groups = await _repository.getMyGroups();
      if (!mounted) return;
      state = AsyncValue.data(groups);
    } catch (e, st) {
      if (!mounted) return;
      if (previous != null) {
        debugPrint('My groups refresh failed, keeping previous data: $e');
        state = AsyncValue.data(previous);
        return;
      }
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadGroups();

  Future<GroupInfo> createGroup(GroupCreate data) async {
    try {
      final group = await _repository.createGroup(data);
      _ref.invalidate(groupDiscoverProvider);
      _ref.invalidate(groupRecommendationsProvider);
      await loadGroups();
      return group;
    } catch (e) {
      rethrow;
    }
  }
}

// 4.5. Group Members Provider (Family)
final groupMembersProvider = StateNotifierProvider.family<GroupMembersNotifier,
    AsyncValue<List<GroupMemberInfo>>, String>(
  (ref, groupId) =>
      GroupMembersNotifier(ref.watch(communityRepositoryProvider), groupId),
);

class GroupMembersNotifier
    extends StateNotifier<AsyncValue<List<GroupMemberInfo>>> {
  GroupMembersNotifier(this._repository, this._groupId)
      : super(const AsyncValue.loading()) {
    loadMembers();
  }
  final CommunityRepository _repository;
  final String _groupId;

  Future<void> loadMembers() async {
    final previous = state.valueOrNull;
    if (previous == null) {
      state = const AsyncValue.loading();
    }
    try {
      final members = await _repository.getGroupMembers(_groupId);
      state = AsyncValue.data(members);
    } catch (e, st) {
      if (previous != null) {
        debugPrint('Group members refresh failed, keeping previous data: $e');
        state = AsyncValue.data(previous);
        return;
      }
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadMembers();

  Future<void> kickMember(String userId) async {
    try {
      await _repository.kickMember(_groupId, userId);
      await loadMembers();
    } catch (e) {
      rethrow;
    }
  }

  Future<void> promoteMember(String userId) async {
    try {
      await _repository.promoteMember(_groupId, userId);
      await loadMembers();
    } catch (e) {
      rethrow;
    }
  }

  Future<void> demoteMember(String userId) async {
    try {
      await _repository.demoteMember(_groupId, userId);
      await loadMembers();
    } catch (e) {
      rethrow;
    }
  }

  Future<void> transferOwnership(String userId) async {
    try {
      await _repository.transferOwnership(_groupId, userId);
      await loadMembers();
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
    this._repository,
    this._authRepository,
    this._groupId,
    this._ref,
  ) : super(const AsyncValue.loading()) {
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

  // WebSocket reconnection state
  WebSocketConnectionState _connectionState =
      WebSocketConnectionState.disconnected;
  WebSocketConnectionState get connectionState => _connectionState;
  int _retryCount = 0;
  static const int _maxRetries = 5;
  static const int _pageSize = 50;
  bool _isLoadingMore = false;
  bool _hasMoreMessages = true;
  StreamSubscription<dynamic>? _wsSubscription;

  bool get isLoadingMore => _isLoadingMore;
  bool get hasMoreMessages => _hasMoreMessages;

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

  Future<void> _connectWebSocket({bool isRetry = false}) async {
    if (_connectionState == WebSocketConnectionState.connecting) return;
    if (DemoDataService.isDemoMode) {
      _connectionState = WebSocketConnectionState.disconnected;
      return;
    }

    _connectionState = WebSocketConnectionState.connecting;
    final token = await _authRepository.getAccessToken();
    if (token == null) {
      _connectionState = WebSocketConnectionState.disconnected;
      return;
    }

    final baseUrl = ApiEndpoints.baseUrl.replaceFirst(RegExp('^http'), 'ws');
    // 安全修复：token不再放在URL中，改用headers
    final wsUrl = '$baseUrl/community/groups/$_groupId/ws';
    final headers = <String, dynamic>{
      'Authorization': 'Bearer $token',
    };

    try {
      // Cancel existing subscription if any
      await _wsSubscription?.cancel();

      _wsService.connect(wsUrl, headers: headers);
      _wsSubscription = _wsService.stream.listen(
        (data) {
          final jsonData = _decodeCommunityWsPayload(data);
          if (jsonData == null) {
            return;
          }

          try {
            if (jsonData['type'] == 'ack') {
              final nonce = jsonData['nonce'];
              if (nonce != null && _pendingNonces.contains(nonce)) {
                _pendingNonces.remove(nonce);
                unawaited(
                  _cacheService.removePendingGroupMessage(
                    _groupId,
                    nonce.toString(),
                  ),
                );
                state.whenData(
                  (messages) => state = AsyncValue.data([...messages]),
                );
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
                  messageId.toString(),
                  reactions as Map<String, dynamic>?,
                );
              }
              return;
            }

            if (jsonData['type'] == 'read_receipt') {
              final upToMessageId = jsonData['up_to_message_id']?.toString();
              final readerId = jsonData['reader_id']?.toString();
              final readerRaw = jsonData['reader'];
              final reader = readerRaw is Map<String, dynamic>
                  ? UserBrief.fromJson(readerRaw)
                  : readerRaw is Map
                      ? UserBrief.fromJson(
                          Map<String, dynamic>.from(readerRaw),
                        )
                      : null;
              if (upToMessageId != null &&
                  upToMessageId.isNotEmpty &&
                  readerId != null &&
                  readerId.isNotEmpty) {
                _handleReadReceipt(
                  upToMessageId: upToMessageId,
                  readerId: readerId,
                  reader: reader,
                );
              }
              return;
            }

            final message = MessageInfo.fromJson(jsonData);
            state.whenData((messages) {
              if (!messages.any((m) => m.id == message.id)) {
                state = AsyncValue.data([message, ...messages]);
                unawaited(
                  _markVisibleMessagesAsRead(upToMessageId: message.id),
                );

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
        },
        onError: (Object error) {
          debugPrint('WS Stream Error: $error');
          _handleConnectionError();
        },
        onDone: () {
          debugPrint('WS Stream Done');
          _handleConnectionError();
        },
      );

      // Connection successful
      _connectionState = WebSocketConnectionState.connected;
      _retryCount = 0;
    } catch (e) {
      debugPrint('WS Connect Error: $e');
      _handleConnectionError();
    }
  }

  void _handleConnectionError() {
    _connectionState = WebSocketConnectionState.disconnected;
    if (_retryCount < _maxRetries) {
      _retryCount++;
      final delay = Duration(
        seconds: 1 << _retryCount,
      ); // Exponential backoff: 2s, 4s, 8s, 16s, 32s
      debugPrint(
        'WS reconnecting in ${delay.inSeconds}s (attempt $_retryCount/$_maxRetries)',
      );
      Future.delayed(delay, () {
        if (mounted) {
          _connectWebSocket(isRetry: true);
        }
      });
    } else {
      debugPrint('WS max retries reached, giving up');
    }
  }

  Future<void> manualReconnect() async {
    _retryCount = 0;
    await _connectWebSocket();
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
          _groupId,
          payload['nonce']?.toString() ?? '',
        );
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
    _wsSubscription?.cancel();
    _wsService.disconnect();
    super.dispose();
  }

  Future<void> loadMessages() async {
    try {
      final messages = await _repository.getMessages(_groupId);
      _hasMoreMessages = messages.length >= _pageSize;
      state = AsyncValue.data(messages);
      await _cacheService.saveGroupMessages(_groupId, messages);
      if (messages.isNotEmpty) {
        await _markVisibleMessagesAsRead(upToMessageId: messages.first.id);
      }
    } catch (e, st) {
      if (!state.hasValue) {
        state = AsyncValue.error(e, st);
      }
    }
  }

  Future<void> refresh() => loadMessages();

  Future<void> loadOlderMessages() async {
    if (_isLoadingMore || !_hasMoreMessages) {
      return;
    }

    final currentMessages = state.valueOrNull ?? const <MessageInfo>[];
    if (currentMessages.isEmpty) {
      await loadMessages();
      return;
    }

    _isLoadingMore = true;
    try {
      final olderMessages = await _repository.getMessages(
        _groupId,
        beforeId: currentMessages.last.id,
      );
      if (olderMessages.isEmpty) {
        _hasMoreMessages = false;
        return;
      }

      final seenIds = currentMessages.map((message) => message.id).toSet();
      final deduped = olderMessages
          .where((message) => !seenIds.contains(message.id))
          .toList();
      if (deduped.isEmpty) {
        _hasMoreMessages = false;
        return;
      }

      _hasMoreMessages = olderMessages.length >= _pageSize;
      final merged = [...currentMessages, ...deduped];
      state = AsyncValue.data(merged);
      await _cacheService.saveGroupMessages(_groupId, merged);
    } catch (e) {
      debugPrint('Load older group messages failed: $e');
    } finally {
      _isLoadingMore = false;
    }
  }

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

  Future<void> _markVisibleMessagesAsRead({
    required String upToMessageId,
  }) async {
    final currentUserId = await _resolveCurrentUserId();
    if (currentUserId == null || currentUserId.isEmpty) {
      return;
    }
    final messages = state.valueOrNull ?? const <MessageInfo>[];
    MessageInfo? target;
    for (final message in messages) {
      if (message.id == upToMessageId) {
        target = message;
        break;
      }
    }
    if (target == null) {
      return;
    }
    final hasUnreadVisible = messages.any((message) {
      final isVisibleRange = !message.createdAt.isAfter(target!.createdAt);
      final isFromSomeoneElse = message.sender?.id != currentUserId;
      final isUnread =
          !(message.readBy ?? const <String>[]).contains(currentUserId);
      return isVisibleRange && isFromSomeoneElse && isUnread;
    });
    if (!hasUnreadVisible) {
      return;
    }
    try {
      await _repository.markGroupMessagesRead(
        _groupId,
        upToMessageId: upToMessageId,
      );
    } catch (e) {
      debugPrint('Mark group messages read failed: $e');
    }
  }

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
    String messageId,
    Map<String, dynamic>? reactions,
  ) {
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

  void _handleReadReceipt({
    required String upToMessageId,
    required String readerId,
    UserBrief? reader,
  }) {
    state.whenData((messages) {
      MessageInfo? target;
      for (final message in messages) {
        if (message.id == upToMessageId) {
          target = message;
          break;
        }
      }
      if (target == null) {
        return;
      }
      final targetCreatedAt = target.createdAt;
      final updated = messages.map((message) {
        if (message.sender?.id == readerId) {
          return message;
        }
        if (message.createdAt.isAfter(targetCreatedAt)) {
          return message;
        }
        final readBy = List<String>.from(message.readBy ?? const <String>[]);
        if (!readBy.contains(readerId)) {
          readBy.add(readerId);
        }
        final readByUsers =
            List<UserBrief>.from(message.readByUsers ?? const <UserBrief>[]);
        if (reader != null && !readByUsers.any((user) => user.id == readerId)) {
          readByUsers.add(reader);
        }
        return MessageInfo(
          id: message.id,
          messageType: message.messageType,
          sender: message.sender,
          content: message.content,
          contentData: message.contentData,
          replyToId: message.replyToId,
          threadRootId: message.threadRootId,
          mentionUserIds: message.mentionUserIds,
          reactions: message.reactions,
          createdAt: message.createdAt,
          updatedAt: message.updatedAt,
          isRevoked: message.isRevoked,
          revokedAt: message.revokedAt,
          editedAt: message.editedAt,
          readBy: readBy,
          quotedMessage: message.quotedMessage,
          readByUsers: readByUsers,
        );
      }).toList();
      state = AsyncValue.data(updated);
    });
  }

  Future<String?> _resolveCurrentUserId() async {
    final current = _ref.read(currentUserProvider)?.id;
    if (current != null && current.isNotEmpty) {
      return current;
    }
    return null;
  }
}

// 6. Group Search Provider
final groupSearchProvider =
    StateNotifierProvider<GroupSearchNotifier, AsyncValue<List<GroupListItem>>>(
  (ref) => GroupSearchNotifier(ref.watch(communityRepositoryProvider)),
);

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
      GroupTasksNotifier(ref.watch(communityRepositoryProvider), groupId),
);

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

  Future<void> createTask(GroupTaskCreate task) async {
    try {
      await _repository.createGroupTask(_groupId, task);
      await loadTasks();
    } catch (e) {
      rethrow;
    }
  }
}

// 8. Private Chat Provider (Family)
final privateChatProvider = StateNotifierProvider.family<PrivateChatNotifier,
    AsyncValue<List<PrivateMessageInfo>>, String>((ref, friendId) {
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
    this._repository,
    this._friendId,
    Stream<dynamic> events,
    this._ref,
  ) : super(const AsyncValue.loading()) {
    _initialize(events);
  }
  final CommunityRepository _repository;
  final String _friendId;
  final ChatCacheService _cacheService = ChatCacheService();
  final Ref _ref;
  String? _currentUserId;
  StreamSubscription<dynamic>? _eventsSubscription;

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
    if (!mounted) return;
    await _eventsSubscription?.cancel();
    _eventsSubscription = events.listen(_handleEvent);
  }

  void _handleEvent(dynamic data) {
    final jsonData = _decodeCommunityWsPayload(data);
    if (jsonData == null) {
      return;
    }

    try {
      if (jsonData['type'] == 'ack') {
        final nonce = jsonData['nonce'];
        if (nonce != null && _pendingNonces.contains(nonce)) {
          _pendingNonces.remove(nonce);
          unawaited(
            _cacheService.removePendingPrivateMessage(
              _friendId,
              nonce.toString(),
            ),
          );
          state.whenData((messages) => state = AsyncValue.data([...messages]));
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
        final l10n = I18nService.instance.l10n;
        _ref.read(unreadMessageCountProvider.notifier).increment();
        _ref.read(inAppNotificationProvider.notifier).show(
              NotificationMessage(
                id: groupMessage.id,
                senderName: groupMessage.sender?.displayName ??
                    l10n.communityGroupMemberFallback,
                senderAvatarUrl: groupMessage.sender?.avatarUrl,
                content: groupMessage.content ??
                    l10n.memorySettingsSocialPersonMention,
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
            messageId.toString(),
            reactions as Map<String, dynamic>?,
          );
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
        } catch (e) {
          debugPrint(
            'PrivateChatNotifier.handleEvent message parse failed: $e',
          );
        }
      }
    } catch (e) {
      debugPrint('WS Parse Error (Private): $e');
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
          _friendId,
          payload['nonce']?.toString() ?? '',
        );
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
    String messageId,
    Map<String, dynamic>? reactions,
  ) {
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
      (messages) => state = AsyncValue.data([tempMessage, ...messages]),
    );

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
        _friendId,
        pendingPayload,
      );
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

  @override
  void dispose() {
    unawaited(_eventsSubscription?.cancel());
    super.dispose();
  }

  Future<UserBrief> _buildCurrentUserBrief() async {
    final user = _ref.read(currentUserProvider);
    if (user == null) {
      var userId = 'guest';
      var nickname = '访客';
      try {
        final guestService = _ref.read(guestServiceProvider);
        userId = await guestService.getGuestId();
        nickname = guestService.getGuestNickname();
      } catch (e) {
        debugPrint('PrivateChatNotifier guest profile lookup failed: $e');
      }
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
    } catch (e) {
      debugPrint('PrivateChatNotifier guest id lookup failed: $e');
      return 'guest';
    }
  }
}

// 9. Current User Status Provider
final currentUserStatusProvider =
    StateNotifierProvider<CurrentUserStatusNotifier, UserStatus>(
  (ref) => CurrentUserStatusNotifier(ref.watch(communityRepositoryProvider)),
);

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

// 10. Blocked Users Provider (Phase 4)
final blockedUsersProvider = StateNotifierProvider<BlockedUsersNotifier,
    AsyncValue<List<BlockUserInfo>>>(
  (ref) => BlockedUsersNotifier(ref.watch(communityRepositoryProvider)),
);

class BlockedUsersNotifier
    extends StateNotifier<AsyncValue<List<BlockUserInfo>>> {
  BlockedUsersNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadBlockedUsers();
  }
  final CommunityRepository _repository;

  Future<void> loadBlockedUsers() async {
    state = const AsyncValue.loading();
    try {
      final blockedUsers = await _repository.getBlockedUsers();
      state = AsyncValue.data(blockedUsers);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadBlockedUsers();

  /// 解除拉黑
  Future<void> unblockUser(String userId) async {
    await _repository.unblockUser(userId);
    // Remove from local state
    state.whenData((users) {
      state = AsyncValue.data(
        users.where((u) => u.blockedUser.id != userId).toList(),
      );
    });
  }
}
