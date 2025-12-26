import 'dart:math';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/data/repositories/community_repository.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:uuid/uuid.dart';

class MockCommunityRepository implements CommunityRepository {
  final ApiClient? _apiClient; // Not used in mock but kept for interface compatibility

  MockCommunityRepository([this._apiClient]);

  // ============ Mock Data Helper ============
  
  UserBrief _createUser(String name, int level, UserStatus status, {String? avatarSeed, String? id}) {
    return UserBrief(
      id: id ?? const Uuid().v4(),
      username: name.toLowerCase(),
      nickname: name,
      avatarUrl: 'https://api.dicebear.com/7.x/avataaars/png?seed=${avatarSeed ?? name}',
      flameLevel: level,
      flameBrightness: 0.5 + (level / 20.0),
      status: status,
    );
  }

  // ============ Mock Data Store ============
  
  late final List<UserBrief> _mockUsers;
  late final List<FriendshipInfo> _mockFriends;
  late final List<GroupInfo> _mockGroups;
  late final Map<String, List<MessageInfo>> _mockGroupMessages;
  late final Map<String, List<PrivateMessageInfo>> _mockPrivateMessages;
  late final Map<String, List<GroupTaskInfo>> _mockGroupTasks;

  MockCommunityRepository._init() : _apiClient = null {
    // Users
    final alice = _createUser('Alice', 8, UserStatus.online, id: 'user_alice');
    final bob = _createUser('Bob', 5, UserStatus.offline, id: 'user_bob');
    final charlie = _createUser('Charlie', 12, UserStatus.online, id: 'user_charlie');
    final david = _createUser('David', 3, UserStatus.invisible, id: 'user_david');
    final eve = _createUser('Eve', 7, UserStatus.online, id: 'user_eve');
    final me = _createUser('Me', 10, UserStatus.online, id: 'me');
    
    _mockUsers = [alice, bob, charlie, david, eve, me];

    // Friends
    _mockFriends = [
      FriendshipInfo(
        id: const Uuid().v4(),
        friend: alice,
        status: FriendshipStatus.accepted,
        createdAt: DateTime.now().subtract(const Duration(days: 30)),
        updatedAt: DateTime.now(),
        matchReason: {'common_tags': ['Flutter', 'AI']},
      ),
      FriendshipInfo(
        id: const Uuid().v4(),
        friend: charlie,
        status: FriendshipStatus.accepted,
        createdAt: DateTime.now().subtract(const Duration(days: 15)),
        updatedAt: DateTime.now(),
      ),
       FriendshipInfo(
        id: const Uuid().v4(),
        friend: bob,
        status: FriendshipStatus.accepted,
        createdAt: DateTime.now().subtract(const Duration(days: 5)),
        updatedAt: DateTime.now(),
      ),
    ];

    // Groups
    _mockGroups = [];
    _mockGroupMessages = {};

    // Private Messages with Read Receipts and Revocation
    _mockPrivateMessages = {
      alice.id: [
        PrivateMessageInfo(
          id: const Uuid().v4(),
          sender: alice,
          receiver: me,
          messageType: MessageType.text,
          isRead: true,
          readAt: DateTime.now().subtract(const Duration(minutes: 1)),
          createdAt: DateTime.now().subtract(const Duration(minutes: 2)),
          updatedAt: DateTime.now(),
          content: '这周末要不要一起去图书馆？',
        ),
        PrivateMessageInfo(
          id: const Uuid().v4(),
          sender: me, 
          receiver: alice,
          messageType: MessageType.text,
          isRead: true,
          readAt: DateTime.now().subtract(const Duration(minutes: 5)),
          createdAt: DateTime.now().subtract(const Duration(minutes: 10)),
          updatedAt: DateTime.now(),
          content: '好啊，几点？',
        ),
        PrivateMessageInfo(
          id: 'revoke_test_1',
          sender: alice, 
          receiver: me,
          messageType: MessageType.text,
          isRead: false,
          isRevoked: true, // Mock revoked message
          createdAt: DateTime.now().subtract(const Duration(minutes: 1)),
          updatedAt: DateTime.now(),
          content: '这是一条被撤回的消息',
        ),
      ],
    };

    _mockGroupTasks = {};
  }

  static final MockCommunityRepository _instance = MockCommunityRepository._init();
  factory MockCommunityRepository.instance() => _instance;

  // ============ Override Methods ============

  @override
  Future<List<FriendshipInfo>> getFriends() async {
    await Future.delayed(const Duration(milliseconds: 500));
    return _mockFriends;
  }

  @override
  Future<void> sendFriendRequest(String targetUserId, {String? message}) async {
    await Future.delayed(const Duration(seconds: 1));
  }

  @override
  Future<void> respondToRequest(String friendshipId, bool accept) async {
    await Future.delayed(const Duration(seconds: 1));
  }

  @override
  Future<List<FriendshipInfo>> getPendingRequests() async {
    await Future.delayed(const Duration(milliseconds: 300));
    final dave = _createUser('Dave', 2, UserStatus.online);
    return [
      FriendshipInfo(
        id: const Uuid().v4(),
        friend: dave,
        status: FriendshipStatus.pending,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
        initiatedByMe: false,
        matchReason: {'common_interest': 'Music'},
      )
    ];
  }

  @override
  Future<List<FriendRecommendation>> getFriendRecommendations({int limit = 10}) async {
     await Future.delayed(const Duration(milliseconds: 400));
     final frank = _createUser('Frank', 4, UserStatus.offline);
     final grace = _createUser('Grace', 9, UserStatus.online);
     
     return [
       FriendRecommendation(
         user: frank, matchScore: 0.85, matchReasons: ['都在学习 Python', '活跃时间重叠'],
       ),
       FriendRecommendation(
         user: grace, matchScore: 0.72, matchReasons: ['同校校友'],
       ),
     ];
  }

  @override
  Future<List<PrivateMessageInfo>> getPrivateMessages(
    String friendId, {
    String? beforeId,
    int limit = 50,
  }) async {
    await Future.delayed(const Duration(milliseconds: 300));
    final messages = _mockPrivateMessages[friendId] ?? [];
    messages.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return messages;
  }

  @override
  Future<PrivateMessageInfo> sendPrivateMessage(PrivateMessageSend message) async {
    await Future.delayed(const Duration(milliseconds: 800));
    
    final me = _mockUsers.firstWhere((u) => u.id == 'me');
    final target = _mockUsers.firstWhere((u) => u.id == message.targetUserId, orElse: () => _createUser('Recipient', 1, UserStatus.online, id: message.targetUserId));

    // Handle quote
    PrivateMessageInfo? quoted;
    if (message.replyToId != null) {
      final friendMessages = _mockPrivateMessages[message.targetUserId];
      if (friendMessages != null) {
        quoted = friendMessages.firstWhere((m) => m.id == message.replyToId);
      }
    }

    final newMsg = PrivateMessageInfo(
      id: const Uuid().v4(),
      sender: me,
      receiver: target,
      messageType: message.messageType,
      content: message.content,
      contentData: message.contentData,
      isRead: false,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      replyToId: message.replyToId,
      quotedMessage: quoted,
    );
    
    if (!_mockPrivateMessages.containsKey(message.targetUserId)) {
      _mockPrivateMessages[message.targetUserId] = [];
    }
    _mockPrivateMessages[message.targetUserId]!.insert(0, newMsg);
    
    return newMsg;
  }

  @override
  Future<void> revokePrivateMessage(String messageId) async {
    await Future.delayed(const Duration(milliseconds: 500));
    // Simulate server side revocation: find message in any store and mark revoked
    for (var list in _mockPrivateMessages.values) {
      final index = list.indexWhere((m) => m.id == messageId);
      if (index != -1) {
        list[index] = list[index].copyWith(isRevoked: true);
        return;
      }
    }
  }

  @override
  Future<List<UserBrief>> searchUsers(String keyword, {int limit = 20}) async {
    await Future.delayed(const Duration(seconds: 1));
    return _mockUsers.where((u) => u.username.contains(keyword.toLowerCase())).toList();
  }

  @override
  Future<void> updateStatus(UserStatus status) async {}

  @override
  Future<GroupInfo> createGroup(GroupCreate group) async {
    await Future.delayed(const Duration(seconds: 1));
    return GroupInfo(
      id: const Uuid().v4(), name: group.name, type: group.type, focusTags: group.focusTags,
      memberCount: 1, totalFlamePower: 0, todayCheckinCount: 0, totalTasksCompleted: 0,
      maxMembers: group.maxMembers, isPublic: group.isPublic, joinRequiresApproval: group.joinRequiresApproval,
      createdAt: DateTime.now(), updatedAt: DateTime.now(), myRole: GroupRole.owner,
      description: group.description, deadline: group.deadline,
    );
  }

  @override
  Future<GroupInfo> getGroup(String groupId) async {
    await Future.delayed(const Duration(milliseconds: 300));
    return GroupInfo(
      id: groupId, name: 'Mock Group', type: GroupType.squad, focusTags: [], 
      memberCount: 1, totalFlamePower: 0, todayCheckinCount: 0, totalTasksCompleted: 0, 
      maxMembers: 50, isPublic: true, joinRequiresApproval: false, 
      createdAt: DateTime.now(), updatedAt: DateTime.now()
    );
  }

  @override
  Future<List<GroupListItem>> getMyGroups() async {
    await Future.delayed(const Duration(milliseconds: 600));
    return [];
  }

  @override
  Future<List<GroupListItem>> searchGroups({String? keyword, GroupType? type, List<String>? tags, int limit = 20,}) async {
     await Future.delayed(const Duration(seconds: 1));
     return [];
  }

  @override
  Future<void> joinGroup(String groupId) async { await Future.delayed(const Duration(seconds: 1)); }

  @override
  Future<void> leaveGroup(String groupId) async { await Future.delayed(const Duration(seconds: 1)); }

  @override
  Future<List<MessageInfo>> getMessages(String groupId, {String? beforeId, int limit = 50,}) async {
    await Future.delayed(const Duration(milliseconds: 400));
    return _mockGroupMessages[groupId] ?? [];
  }

  @override
  Future<MessageInfo> sendMessage(String groupId, {required MessageType type, String? content, Map<String, dynamic>? contentData, String? replyToId, String? nonce,}) async {
    await Future.delayed(const Duration(milliseconds: 200));
    final newMsg = MessageInfo(
      id: const Uuid().v4(), messageType: type, content: content, contentData: contentData,
      replyToId: replyToId, createdAt: DateTime.now(), updatedAt: DateTime.now(),
      sender: _mockUsers.firstWhere((u) => u.id == 'me'),
    );
    if (!_mockGroupMessages.containsKey(groupId)) _mockGroupMessages[groupId] = [];
    _mockGroupMessages[groupId]!.insert(0, newMsg);
    return newMsg;
  }

  @override
  Future<CheckinResponse> checkin(String groupId, {required int todayDurationMinutes, String? message,}) async {
    await Future.delayed(const Duration(seconds: 1));
    return CheckinResponse(success: true, newStreak: 5, flameEarned: 15, rankInGroup: 3, groupCheckinCount: 33,);
  }

  @override
  Future<List<GroupTaskInfo>> getGroupTasks(String groupId) async {
    await Future.delayed(const Duration(milliseconds: 500));
    return _mockGroupTasks[groupId] ?? [];
  }

  @override
  Future<GroupTaskInfo> createGroupTask(String groupId, GroupTaskCreate task) async {
    await Future.delayed(const Duration(seconds: 1));
    return GroupTaskInfo(
      id: const Uuid().v4(), title: task.title, tags: task.tags, estimatedMinutes: task.estimatedMinutes,
      difficulty: task.difficulty, totalClaims: 0, totalCompletions: 0, completionRate: 0,
      createdAt: DateTime.now(), updatedAt: DateTime.now(),
      creator: _mockUsers.firstWhere((u) => u.id == 'me'),
    );
  }

  @override
  Future<void> claimTask(String taskId) async { await Future.delayed(const Duration(milliseconds: 500)); }

  @override
  Future<GroupFlameStatus> getFlameStatus(String groupId) async {
     await Future.delayed(const Duration(milliseconds: 800));
     return GroupFlameStatus(groupId: groupId, totalPower: 0, flames: [], bonfireLevel: 1,);
  }
}
