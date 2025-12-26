import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/data/repositories/community_repository.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:uuid/uuid.dart';

class MockCommunityRepository implements CommunityRepository {
  final ApiClient? _apiClient; // Not used in mock but kept for interface compatibility

  MockCommunityRepository([this._apiClient]);

  // ============ Mock Data Helper ============
  
  UserBrief _createUser(String name, int level, UserStatus status, {String? avatarSeed}) {
    return UserBrief(
      id: const Uuid().v4(),
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
    final alice = _createUser('Alice', 8, UserStatus.online);
    final bob = _createUser('Bob', 5, UserStatus.offline);
    final charlie = _createUser('Charlie', 12, UserStatus.online);
    final david = _createUser('David', 3, UserStatus.invisible);
    final eve = _createUser('Eve', 7, UserStatus.online);
    
    _mockUsers = [alice, bob, charlie, david, eve];

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
    final sprintGroup = GroupInfo(
      id: 'group_sprint_001',
      name: 'CET-6 30天冲刺',
      type: GroupType.sprint,
      focusTags: ['English', 'Exam'],
      memberCount: 45,
      totalFlamePower: 12500,
      todayCheckinCount: 32,
      totalTasksCompleted: 450,
      maxMembers: 50,
      isPublic: true,
      joinRequiresApproval: false,
      createdAt: DateTime.now().subtract(const Duration(days: 10)),
      updatedAt: DateTime.now(),
      description: '每天背单词 + 一套真题，不打卡会被踢出！',
      avatarUrl: 'https://api.dicebear.com/7.x/identicon/png?seed=cet6',
      deadline: DateTime.now().add(const Duration(days: 20)),
      sprintGoal: '全员过600分',
      daysRemaining: 20,
      myRole: GroupRole.member,
    );

    final techGroup = GroupInfo(
      id: 'group_tech_002',
      name: 'Flutter 学习小组',
      type: GroupType.squad,
      focusTags: ['Flutter', 'Dart', 'Mobile'],
      memberCount: 128,
      totalFlamePower: 34000,
      todayCheckinCount: 15,
      totalTasksCompleted: 1200,
      maxMembers: 200,
      isPublic: true,
      joinRequiresApproval: true,
      createdAt: DateTime.now().subtract(const Duration(days: 60)),
      updatedAt: DateTime.now(),
      description: '探讨 Flutter 技术，分享组件库。',
      avatarUrl: 'https://api.dicebear.com/7.x/identicon/png?seed=flutter',
      myRole: GroupRole.admin,
    );

    _mockGroups = [sprintGroup, techGroup];

    // Group Messages
    _mockGroupMessages = {
      sprintGroup.id: [
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          createdAt: DateTime.now().subtract(const Duration(minutes: 5)),
          updatedAt: DateTime.now(),
          sender: alice,
          content: '今天的阅读理解太难了😭',
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.checkin,
          createdAt: DateTime.now().subtract(const Duration(minutes: 10)),
          updatedAt: DateTime.now(),
          sender: charlie,
          content: '完成今日打卡！',
          contentData: {'flame_power': 25, 'streak': 8, 'today_duration': 60},
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.system,
          createdAt: DateTime.now().subtract(const Duration(hours: 1)),
          updatedAt: DateTime.now(),
          content: '欢迎新成员 Eve 加入群组！',
        ),
      ],
      techGroup.id: [
         MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          createdAt: DateTime.now().subtract(const Duration(hours: 2)),
          updatedAt: DateTime.now(),
          sender: bob,
          content: 'Riverpod 2.0 的新特性有人试过吗？',
        ),
      ],
    };

    // Private Messages
    _mockPrivateMessages = {
      alice.id: [
        PrivateMessageInfo(
          id: const Uuid().v4(),
          sender: alice,
          receiver: UserBrief(id: 'me', username: 'me'), // Mock 'me'
          messageType: MessageType.text,
          isRead: false,
          createdAt: DateTime.now().subtract(const Duration(minutes: 2)),
          updatedAt: DateTime.now(),
          content: '这周末要不要一起去图书馆？',
        ),
        PrivateMessageInfo(
          id: const Uuid().v4(),
          sender: UserBrief(id: 'me', username: 'me'), 
          receiver: alice,
          messageType: MessageType.text,
          isRead: true,
          createdAt: DateTime.now().subtract(const Duration(minutes: 10)),
          updatedAt: DateTime.now(),
          content: '好啊，几点？',
        ),
      ],
    };

    // Group Tasks
    _mockGroupTasks = {
      sprintGroup.id: [
        GroupTaskInfo(
          id: const Uuid().v4(),
          title: '完成 2019 年 6 月真题',
          tags: ['真题', '阅读'],
          estimatedMinutes: 120,
          difficulty: 4,
          totalClaims: 30,
          totalCompletions: 12,
          completionRate: 0.4,
          createdAt: DateTime.now().subtract(const Duration(days: 1)),
          updatedAt: DateTime.now(),
          dueDate: DateTime.now().add(const Duration(days: 1)),
          creator: charlie,
          isClaimedByMe: true,
          myCompletionStatus: false,
        ),
        GroupTaskInfo(
          id: const Uuid().v4(),
          title: '背诵 List 5 单词',
          tags: ['单词'],
          estimatedMinutes: 45,
          difficulty: 2,
          totalClaims: 40,
          totalCompletions: 38,
          completionRate: 0.95,
          createdAt: DateTime.now().subtract(const Duration(days: 2)),
          updatedAt: DateTime.now(),
          creator: alice,
          isClaimedByMe: true,
          myCompletionStatus: true,
        ),
      ]
    };
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
         user: frank,
         matchScore: 0.85,
         matchReasons: ['都在学习 Python', '活跃时间重叠'],
       ),
       FriendRecommendation(
         user: grace,
         matchScore: 0.72,
         matchReasons: ['同校校友'],
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
    return _mockPrivateMessages[friendId] ?? [];
  }

  @override
  Future<PrivateMessageInfo> sendPrivateMessage(PrivateMessageSend message) async {
    await Future.delayed(const Duration(milliseconds: 200));
    final newMsg = PrivateMessageInfo(
      id: const Uuid().v4(),
      sender: UserBrief(id: 'me', username: 'me'),
      receiver: UserBrief(id: message.targetUserId, username: 'receiver'), // Simplified
      messageType: message.messageType,
      content: message.content,
      contentData: message.contentData,
      isRead: false,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );
    
    // Add to mock store
    if (!_mockPrivateMessages.containsKey(message.targetUserId)) {
      _mockPrivateMessages[message.targetUserId] = [];
    }
    _mockPrivateMessages[message.targetUserId]!.insert(0, newMsg);
    
    return newMsg;
  }

  @override
  Future<List<UserBrief>> searchUsers(String keyword, {int limit = 20}) async {
    await Future.delayed(const Duration(seconds: 1));
    return _mockUsers.where((u) => u.username.contains(keyword.toLowerCase())).toList();
  }

  @override
  Future<void> updateStatus(UserStatus status) async {
     // Mock update
  }

  @override
  Future<GroupInfo> createGroup(GroupCreate group) async {
    await Future.delayed(const Duration(seconds: 1));
    return GroupInfo(
      id: const Uuid().v4(),
      name: group.name,
      type: group.type,
      focusTags: group.focusTags,
      memberCount: 1,
      totalFlamePower: 0,
      todayCheckinCount: 0,
      totalTasksCompleted: 0,
      maxMembers: group.maxMembers,
      isPublic: group.isPublic,
      joinRequiresApproval: group.joinRequiresApproval,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      myRole: GroupRole.owner,
      description: group.description,
      deadline: group.deadline,
    );
  }

  @override
  Future<GroupInfo> getGroup(String groupId) async {
    await Future.delayed(const Duration(milliseconds: 300));
    return _mockGroups.firstWhere(
      (g) => g.id == groupId, 
      orElse: () => _mockGroups[0] // Fallback
    );
  }

  @override
  Future<List<GroupListItem>> getMyGroups() async {
    await Future.delayed(const Duration(milliseconds: 600));
    return _mockGroups.map((g) => GroupListItem(
      id: g.id,
      name: g.name,
      type: g.type,
      memberCount: g.memberCount,
      totalFlamePower: g.totalFlamePower,
      focusTags: g.focusTags,
      deadline: g.deadline,
      daysRemaining: g.daysRemaining,
      myRole: g.myRole,
    )).toList();
  }

  @override
  Future<List<GroupListItem>> searchGroups({
    String? keyword,
    GroupType? type,
    List<String>? tags,
    int limit = 20,
  }) async {
     await Future.delayed(const Duration(seconds: 1));
     // Return some random groups
     return [
       GroupListItem(
         id: 'group_search_1',
         name: '考研政治交流',
         type: GroupType.squad,
         memberCount: 88,
         totalFlamePower: 5000,
         focusTags: ['考研', '政治'],
         myRole: null,
       )
     ];
  }

  @override
  Future<void> joinGroup(String groupId) async {
    await Future.delayed(const Duration(seconds: 1));
  }

  @override
  Future<void> leaveGroup(String groupId) async {
    await Future.delayed(const Duration(seconds: 1));
  }

  @override
  Future<List<MessageInfo>> getMessages(
    String groupId, {
    String? beforeId,
    int limit = 50,
  }) async {
    await Future.delayed(const Duration(milliseconds: 400));
    return _mockGroupMessages[groupId] ?? [];
  }

  @override
  Future<MessageInfo> sendMessage(
    String groupId, {
    required MessageType type,
    String? content,
    Map<String, dynamic>? contentData,
    String? replyToId,
    String? nonce,
  }) async {
    await Future.delayed(const Duration(milliseconds: 200));
    final newMsg = MessageInfo(
      id: const Uuid().v4(),
      messageType: type,
      content: content,
      contentData: contentData,
      replyToId: replyToId,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      sender: UserBrief(id: 'me', username: 'me', nickname: 'Me', avatarUrl: 'https://api.dicebear.com/7.x/avataaars/png?seed=me'),
    );
    
    if (!_mockGroupMessages.containsKey(groupId)) {
      _mockGroupMessages[groupId] = [];
    }
    _mockGroupMessages[groupId]!.insert(0, newMsg);
    
    return newMsg;
  }

  @override
  Future<CheckinResponse> checkin(
    String groupId, {
    required int todayDurationMinutes,
    String? message,
  }) async {
    await Future.delayed(const Duration(seconds: 1));
    return CheckinResponse(
      success: true,
      newStreak: 5,
      flameEarned: 15,
      rankInGroup: 3,
      groupCheckinCount: 33,
    );
  }

  @override
  Future<List<GroupTaskInfo>> getGroupTasks(String groupId) async {
    await Future.delayed(const Duration(milliseconds: 500));
    return _mockGroupTasks[groupId] ?? [];
  }

  @override
  Future<GroupTaskInfo> createGroupTask(String groupId, GroupTaskCreate task) async {
    await Future.delayed(const Duration(seconds: 1));
    final newTask = GroupTaskInfo(
      id: const Uuid().v4(),
      title: task.title,
      description: task.description,
      tags: task.tags,
      estimatedMinutes: task.estimatedMinutes,
      difficulty: task.difficulty,
      totalClaims: 0,
      totalCompletions: 0,
      completionRate: 0,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      dueDate: task.dueDate,
      creator: UserBrief(id: 'me', username: 'me'),
      isClaimedByMe: false,
    );
    
    if (!_mockGroupTasks.containsKey(groupId)) {
      _mockGroupTasks[groupId] = [];
    }
    _mockGroupTasks[groupId]!.insert(0, newTask);
    
    return newTask;
  }

  @override
  Future<void> claimTask(String taskId) async {
    await Future.delayed(const Duration(milliseconds: 500));
    // In a real mock, we'd update the task state here
  }

  @override
  Future<GroupFlameStatus> getFlameStatus(String groupId) async {
     await Future.delayed(const Duration(milliseconds: 800));
     // Mock flame status
     final group = await getGroup(groupId);
     
     final flames = List.generate(min(20, group.memberCount), (index) {
       return FlameStatus(
         userId: 'user_$index',
         flamePower: 10 + index * 5,
         flameColor: index % 3 == 0 ? '#FFD700' : '#FF6B35',
         flameSize: 0.5 + (index / 20.0),
         positionX: (index % 5 - 2) * 10.0,
         positionY: (index ~/ 5 - 2) * 10.0,
       );
     });

     return GroupFlameStatus(
       groupId: groupId,
       totalPower: group.totalFlamePower,
       flames: flames,
       bonfireLevel: 3,
     );
  }
  
  int min(int a, int b) => a < b ? a : b;
}
