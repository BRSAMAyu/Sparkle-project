import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/data/repositories/community_repository.dart';

// 1. Friends Provider
final friendsProvider = StateNotifierProvider<FriendsNotifier, AsyncValue<List<FriendshipInfo>>>((ref) {
  return FriendsNotifier(ref.watch(communityRepositoryProvider));
});

class FriendsNotifier extends StateNotifier<AsyncValue<List<FriendshipInfo>>> {
  final CommunityRepository _repository;

  FriendsNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadFriends();
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
      // Remove the processed request from the list
      state.whenData((requests) {
        state = AsyncValue.data(requests.where((r) => r.id != friendshipId).toList());
      });
    } catch (e) {
      rethrow;
    }
  }
}

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

  Future<void> sendRequest(String userId, {String? message}) async {
    try {
      await _repository.sendFriendRequest(userId, message: message);
      // Ideally update the UI to show "Sent"
    } catch (e) {
      rethrow;
    }
  }
}

// 2. My Groups Provider
final myGroupsProvider = StateNotifierProvider<MyGroupsNotifier, AsyncValue<List<GroupListItem>>>((ref) {
  return MyGroupsNotifier(ref.watch(communityRepositoryProvider));
});

class MyGroupsNotifier extends StateNotifier<AsyncValue<List<GroupListItem>>> {
  final CommunityRepository _repository;

  MyGroupsNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadMyGroups();
  }

  Future<void> loadMyGroups() async {
    state = const AsyncValue.loading();
    try {
      final groups = await _repository.getMyGroups();
      state = AsyncValue.data(groups);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadMyGroups();

  Future<GroupInfo> createGroup(GroupCreate data) async {
    try {
      final group = await _repository.createGroup(data);
      await loadMyGroups(); // Refresh list
      return group;
    } catch (e) {
      rethrow;
    }
  }
}

// 3. Group Detail Provider (Family)
final groupDetailProvider = StateNotifierProvider.family<GroupDetailNotifier, AsyncValue<GroupInfo>, String>((ref, groupId) {
  return GroupDetailNotifier(ref.watch(communityRepositoryProvider), groupId);
});

class GroupDetailNotifier extends StateNotifier<AsyncValue<GroupInfo>> {
  final CommunityRepository _repository;
  final String _groupId;

  GroupDetailNotifier(this._repository, this._groupId) : super(const AsyncValue.loading()) {
    loadGroup();
  }

  Future<void> loadGroup() async {
    state = const AsyncValue.loading();
    try {
      final group = await _repository.getGroup(_groupId);
      state = AsyncValue.data(group);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }
  
  Future<void> refresh() => loadGroup();

  Future<void> joinGroup() async {
    try {
      await _repository.joinGroup(_groupId);
      await loadGroup(); // Refresh after joining
    } catch (e) {
      // Handle error, maybe show toast via a side effect provider
      rethrow;
    }
  }

  Future<void> leaveGroup() async {
    try {
      await _repository.leaveGroup(_groupId);
      // Logic after leaving? Maybe navigate back.
    } catch (e) {
      rethrow;
    }
  }

  Future<CheckinResponse> checkin(int duration, String? message) async {
    try {
      final response = await _repository.checkin(_groupId, todayDurationMinutes: duration, message: message);
      await loadGroup(); // Refresh stats
      return response;
    } catch (e) {
      rethrow;
    }
  }
}

// 4. Group Chat Provider (Family)
final groupChatProvider = StateNotifierProvider.family<GroupChatNotifier, AsyncValue<List<MessageInfo>>, String>((ref, groupId) {
  return GroupChatNotifier(ref.watch(communityRepositoryProvider), groupId);
});

class GroupChatNotifier extends StateNotifier<AsyncValue<List<MessageInfo>>> {
  final CommunityRepository _repository;
  final String _groupId;

  GroupChatNotifier(this._repository, this._groupId) : super(const AsyncValue.loading()) {
    loadMessages();
  }

  Future<void> loadMessages() async {
    state = const AsyncValue.loading();
    try {
      final messages = await _repository.getMessages(_groupId);
      state = AsyncValue.data(messages);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() => loadMessages();

  Future<void> sendMessage({required String content, MessageType type = MessageType.text}) async {
    try {
      final message = await _repository.sendMessage(_groupId, type: type, content: content);
      
      // Optimistically update or re-fetch
      // For now, let's append if success
      state.whenData((messages) {
        state = AsyncValue.data([message, ...messages]);
      });
    } catch (e) {
      rethrow;
    }
  }
}

// 5. Group Search Provider
final groupSearchProvider = StateNotifierProvider<GroupSearchNotifier, AsyncValue<List<GroupListItem>>>((ref) {
  return GroupSearchNotifier(ref.watch(communityRepositoryProvider));
});

class GroupSearchNotifier extends StateNotifier<AsyncValue<List<GroupListItem>>> {
  final CommunityRepository _repository;

  GroupSearchNotifier(this._repository) : super(const AsyncValue.data([])); // Initially empty

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

// 6. Group Tasks Provider (Family)
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
      await loadTasks(); // Refresh to update status
    } catch (e) {
      rethrow;
    }
  }
}
