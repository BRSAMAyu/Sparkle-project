import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/data/repositories/community_repository.dart';
import 'package:sparkle/domain/community/community_models.dart';
import 'package:uuid/uuid.dart';

class MockCommunityRepository implements CommunityRepository {

  MockCommunityRepository([this._apiClient]);

  MockCommunityRepository._init() : _apiClient = null {
    // Create current user matching DemoDataService
    final me = _createUser('AI_Learner_02', 15, UserStatus.online, id: currentUserId, avatarSeed: 'AI_Learner_02');
    final alice = _createUser('Alice', 8, UserStatus.online, id: 'user_alice', avatarSeed: 'alice_seed');
    final bob = _createUser('Bob', 5, UserStatus.offline, id: 'user_bob', avatarSeed: 'bob_seed');
    final charlie = _createUser('Charlie', 12, UserStatus.online, id: 'user_charlie', avatarSeed: 'charlie_seed');
    final diana = _createUser('Diana', 9, UserStatus.online, id: 'user_diana', avatarSeed: 'diana_seed');
    final eva = _createUser('Eva', 6, UserStatus.offline, id: 'user_eva', avatarSeed: 'eva_seed');

    _mockUsers = [alice, bob, charlie, diana, eva, me];

    _mockFriends = [
      FriendshipInfo(
        id: const Uuid().v4(), friend: alice, status: FriendshipStatus.accepted,
        createdAt: DateTime.now().subtract(const Duration(days: 30)), updatedAt: DateTime.now(),
      ),
      FriendshipInfo(
        id: const Uuid().v4(), friend: charlie, status: FriendshipStatus.accepted,
        createdAt: DateTime.now().subtract(const Duration(days: 15)), updatedAt: DateTime.now(),
      ),
      FriendshipInfo(
        id: const Uuid().v4(), friend: diana, status: FriendshipStatus.accepted,
        createdAt: DateTime.now().subtract(const Duration(days: 7)), updatedAt: DateTime.now(),
      ),
    ];

    // Restore Groups
    final sprintGroup = GroupInfo(
      id: 'group_sprint_001', name: 'CET-6 30天冲刺', type: GroupType.sprint, focusTags: ['English'],
      memberCount: 45, totalFlamePower: 12500, todayCheckinCount: 32, totalTasksCompleted: 450,
      maxMembers: 50, isPublic: true, joinRequiresApproval: false,
      createdAt: DateTime.now().subtract(const Duration(days: 10)), updatedAt: DateTime.now(),
      myRole: GroupRole.member,
    );

    final studyGroup = GroupInfo(
      id: 'group_study_001', name: '数据结构互助组', type: GroupType.squad, focusTags: ['CS', 'Data Structure'],
      memberCount: 28, totalFlamePower: 5600, todayCheckinCount: 15, totalTasksCompleted: 180,
      maxMembers: 50, isPublic: true, joinRequiresApproval: false,
      createdAt: DateTime.now().subtract(const Duration(days: 20)), updatedAt: DateTime.now(),
      myRole: GroupRole.admin,
    );
    _mockGroups = [sprintGroup, studyGroup];

    // Group messages with multiple members
    _mockGroupMessages = {
      sprintGroup.id: [
        MessageInfo(
          id: const Uuid().v4(), messageType: MessageType.text, sender: alice,
          content: '冲冲冲！', createdAt: DateTime.now().subtract(const Duration(minutes: 30)), updatedAt: DateTime.now(),
          readBy: [alice.id, charlie.id, diana.id, bob.id, eva.id],
        ),
        MessageInfo(
          id: const Uuid().v4(), messageType: MessageType.text, sender: charlie,
          content: '今天做完了阅读理解，感觉题目变简单了', createdAt: DateTime.now().subtract(const Duration(minutes: 25)), updatedAt: DateTime.now(),
          readBy: [alice.id, diana.id, bob.id],
        ),
        MessageInfo(
          id: const Uuid().v4(), messageType: MessageType.text, sender: me,
          content: '我也感觉进步了，大家一起加油！', createdAt: DateTime.now().subtract(const Duration(minutes: 20)), updatedAt: DateTime.now(),
          readBy: [alice.id, charlie.id, diana.id, bob.id, eva.id, 'user_frank', 'user_grace'],
        ),
        MessageInfo(
          id: const Uuid().v4(), messageType: MessageType.checkin, sender: diana,
          content: '完成今日单词打卡', createdAt: DateTime.now().subtract(const Duration(minutes: 15)), updatedAt: DateTime.now(),
          contentData: {'flame_power': 120, 'today_duration': 60, 'streak': 7},
          readBy: [alice.id, charlie.id],
        ),
        MessageInfo(
          id: const Uuid().v4(), messageType: MessageType.text, sender: alice,
          content: '厉害！连续7天了', createdAt: DateTime.now().subtract(const Duration(minutes: 10)), updatedAt: DateTime.now(),
          readBy: [diana.id],
        ),
      ],
      studyGroup.id: [
        MessageInfo(
          id: const Uuid().v4(), messageType: MessageType.text, sender: charlie,
          content: '有人能解释一下红黑树的平衡操作吗？', createdAt: DateTime.now().subtract(const Duration(hours: 2)), updatedAt: DateTime.now(),
          readBy: [alice.id, me.id],
        ),
        MessageInfo(
          id: const Uuid().v4(), messageType: MessageType.text, sender: me,
          content: '红黑树的平衡主要通过旋转和变色来维护，左旋和右旋是基本操作', createdAt: DateTime.now().subtract(const Duration(hours: 1, minutes: 50)), updatedAt: DateTime.now(),
          readBy: [charlie.id, alice.id],
        ),
        MessageInfo(
          id: const Uuid().v4(), messageType: MessageType.text, sender: alice,
          content: '我找到一个不错的视频教程，分享给大家', createdAt: DateTime.now().subtract(const Duration(hours: 1)), updatedAt: DateTime.now(),
          readBy: [charlie.id, me.id, diana.id],
        ),
      ],
    };

    // Private messages with quote support
    _mockPrivateMessages = {
      alice.id: [
        PrivateMessageInfo(
          id: 'pm_alice_1', sender: alice, receiver: me, messageType: MessageType.text,
          isRead: true, readAt: DateTime.now().subtract(const Duration(minutes: 8)),
          createdAt: DateTime.now().subtract(const Duration(minutes: 10)), updatedAt: DateTime.now(),
          content: '今天也要加油学习呀！',
        ),
        PrivateMessageInfo(
          id: 'pm_alice_2', sender: me, receiver: alice, messageType: MessageType.text,
          isRead: true, readAt: DateTime.now().subtract(const Duration(minutes: 5)),
          createdAt: DateTime.now().subtract(const Duration(minutes: 8)), updatedAt: DateTime.now(),
          content: '好的，我正在复习数据结构',
        ),
        PrivateMessageInfo(
          id: 'pm_alice_3', sender: alice, receiver: me, messageType: MessageType.text,
          isRead: true, readAt: DateTime.now().subtract(const Duration(minutes: 3)),
          createdAt: DateTime.now().subtract(const Duration(minutes: 5)), updatedAt: DateTime.now(),
          content: '需要帮忙可以找我哦',
        ),
      ],
      charlie.id: [
        PrivateMessageInfo(
          id: 'pm_charlie_1', sender: charlie, receiver: me, messageType: MessageType.text,
          isRead: false, createdAt: DateTime.now().subtract(const Duration(hours: 1)), updatedAt: DateTime.now(),
          content: '明天一起去图书馆吗？',
        ),
      ],
      diana.id: [
        PrivateMessageInfo(
          id: 'pm_diana_1', sender: diana, receiver: me, messageType: MessageType.text,
          isRead: true, readAt: DateTime.now().subtract(const Duration(days: 1)),
          createdAt: DateTime.now().subtract(const Duration(days: 1)), updatedAt: DateTime.now(),
          content: '上次的笔记整理好了',
        ),
      ],
    };
    _mockGroupTasks = {};
  }
  factory MockCommunityRepository.instance() => _instance;
  final ApiClient? _apiClient;

  // Demo user ID - matches DemoDataService.demoUser.id
  static const String currentUserId = 'CS_Sophomore_12345';

  UserBrief _createUser(String name, int level, UserStatus status, {String? avatarSeed, String? id}) => UserBrief(
      id: id ?? const Uuid().v4(),
      username: name.toLowerCase(),
      nickname: name,
      avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=${avatarSeed ?? name}',
      flameLevel: level,
      flameBrightness: 0.5 + (level / 20.0),
      status: status,
    );

  late final List<UserBrief> _mockUsers;
  late final List<FriendshipInfo> _mockFriends;
  late final List<GroupInfo> _mockGroups;
  late final Map<String, List<MessageInfo>> _mockGroupMessages;
  late final Map<String, List<PrivateMessageInfo>> _mockPrivateMessages;
  late final Map<String, List<GroupTaskInfo>> _mockGroupTasks;

  static final MockCommunityRepository _instance = MockCommunityRepository._init();

  @override
  Future<List<FriendshipInfo>> getFriends() async => _mockFriends;

  @override
  Future<List<PrivateMessageInfo>> getPrivateMessages(String friendId, {String? beforeId, int limit = 50}) async {
    final messages = _mockPrivateMessages[friendId] ?? [];
    messages.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return messages;
  }

  @override
  Future<PrivateMessageInfo> sendPrivateMessage(PrivateMessageSend message) async {
    final me = _mockUsers.firstWhere((u) => u.id == currentUserId);
    final target = _mockUsers.firstWhere((u) => u.id == message.targetUserId, orElse: () => _createUser('User', 1, UserStatus.online, id: message.targetUserId));

    // Find quoted message if replyToId is set
    PrivateMessageInfo? quotedMessage;
    if (message.replyToId != null) {
      final messages = _mockPrivateMessages[message.targetUserId];
      if (messages != null) {
        try {
          quotedMessage = messages.firstWhere((m) => m.id == message.replyToId);
        } catch (_) {}
      }
    }

    final newMsg = PrivateMessageInfo(
      id: const Uuid().v4(), sender: me, receiver: target, messageType: message.messageType,
      content: message.content, isRead: false, createdAt: DateTime.now(), updatedAt: DateTime.now(),
      replyToId: message.replyToId,
      quotedMessage: quotedMessage,
    );

    if (!_mockPrivateMessages.containsKey(message.targetUserId)) _mockPrivateMessages[message.targetUserId] = [];
    _mockPrivateMessages[message.targetUserId]!.insert(0, newMsg);

    // Auto-read by "other person" for demo
    Future.delayed(const Duration(seconds: 2), () {
      final index = _mockPrivateMessages[message.targetUserId]!.indexWhere((m) => m.id == newMsg.id);
      if (index != -1) {
        _mockPrivateMessages[message.targetUserId]![index] = _mockPrivateMessages[message.targetUserId]![index].copyWith(
          isRead: true, readAt: DateTime.now(),
        );
      }
    });

    return newMsg;
  }

  @override
  Future<void> revokePrivateMessage(String messageId) async {
    for (final list in _mockPrivateMessages.values) {
      final index = list.indexWhere((m) => m.id == messageId);
      if (index != -1) {
        list[index] = list[index].copyWith(isRevoked: true);
        return;
      }
    }
  }

  @override
  Future<List<GroupListItem>> getMyGroups() async => _mockGroups.map((g) => GroupListItem(
      id: g.id, name: g.name, type: g.type, memberCount: g.memberCount, 
      totalFlamePower: g.totalFlamePower, focusTags: g.focusTags, myRole: g.myRole,
    ),).toList();

  @override
  Future<GroupInfo> getGroup(String groupId) async => _mockGroups.firstWhere((g) => g.id == groupId);

  @override
  Future<List<MessageInfo>> getMessages(String groupId, {String? beforeId, int limit = 50}) async => _mockGroupMessages[groupId] ?? [];

  @override
  Future<MessageInfo> sendMessage(String groupId, {required MessageType type, String? content, Map<String, dynamic>? contentData, String? replyToId, String? nonce}) async {
    // Simulate network delay
    await Future.delayed(const Duration(milliseconds: 300));

    final currentUser = _mockUsers.firstWhere((u) => u.id == currentUserId);
    final newMsg = MessageInfo(
      id: const Uuid().v4(),
      messageType: type,
      content: content,
      contentData: contentData,
      replyToId: replyToId,
      sender: currentUser,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );

    // Add to the beginning of the list (reverse chronological order)
    if (_mockGroupMessages[groupId] != null) {
      _mockGroupMessages[groupId]!.insert(0, newMsg);
    } else {
      _mockGroupMessages[groupId] = [newMsg];
    }

    return newMsg;
  }

  // Other methods remain as minimal implementation
  @override
  Future<void> sendFriendRequest(String targetUserId, {String? message}) async {}
  @override
  Future<void> respondToRequest(String friendshipId, bool accept) async {}
  @override
  Future<List<FriendshipInfo>> getPendingRequests() async => [];
  @override
  Future<List<FriendRecommendation>> getFriendRecommendations({int limit = 10}) async => [];
  @override
  Future<List<UserBrief>> searchUsers(String keyword, {int limit = 20}) async => [];
  @override
  Future<void> updateStatus(UserStatus status) async {}
  @override
  Future<GroupInfo> createGroup(GroupCreate group) async => _mockGroups[0];
  @override
  Future<List<GroupListItem>> searchGroups({String? keyword, GroupType? type, List<String>? tags, int limit = 20}) async => [];
  @override
  Future<void> joinGroup(String groupId) async {}
  @override
  Future<void> leaveGroup(String groupId) async {}
  @override
  Future<CheckinResponse> checkin(String groupId, {required int todayDurationMinutes, String? message}) async => CheckinResponse(success: true, newStreak: 1, flameEarned: 10, rankInGroup: 1, groupCheckinCount: 1);
  @override
  Future<List<GroupTaskInfo>> getGroupTasks(String groupId) async => [];
  @override
  Future<GroupTaskInfo> createGroupTask(String groupId, GroupTaskCreate task) async => GroupTaskInfo(id: '', title: '', tags: [], estimatedMinutes: 0, difficulty: 1, totalClaims: 0, totalCompletions: 0, completionRate: 0, createdAt: DateTime.now(), updatedAt: DateTime.now());
  @override
  Future<void> claimTask(String taskId) async {}
  @override
  Future<GroupFlameStatus> getFlameStatus(String groupId) async => GroupFlameStatus(groupId: groupId, totalPower: 0, flames: [], bonfireLevel: 1);

  // === CommunityRepository interface methods ===
  @override
  Future<List<Post>> getFeed({int page = 1, int limit = 20}) async {
    // Return empty list for mock - feed would be handled by community_providers
    return [];
  }

  @override
  Future<String> createPost(CreatePostRequest request) async {
    // Return a mock post ID
    return const Uuid().v4();
  }

  @override
  Future<void> likePost(String postId, String userId) async {
    // Mock implementation - do nothing
    return;
  }
}