import 'dart:async';

import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/data/repositories/community_repository.dart';
import 'package:sparkle/domain/community/community_models.dart';
import 'package:uuid/uuid.dart';

class MockCommunityRepository implements CommunityRepository {
  MockCommunityRepository();

  MockCommunityRepository._init() {
    // Create current user matching DemoDataService
    final me = _createUser('AI_Learner_02', 15, UserStatus.online,
        id: currentUserId, avatarSeed: 'AI_Learner_02',);
    final alice = _createUser('Alice', 8, UserStatus.online,
        id: 'user_alice', avatarSeed: 'alice_seed',);
    final bob = _createUser('Bob', 5, UserStatus.offline,
        id: 'user_bob', avatarSeed: 'bob_seed',);
    final charlie = _createUser('Charlie', 12, UserStatus.online,
        id: 'user_charlie', avatarSeed: 'charlie_seed',);
    final diana = _createUser('Diana', 9, UserStatus.online,
        id: 'user_diana', avatarSeed: 'diana_seed',);
    final eva = _createUser('Eva', 6, UserStatus.offline,
        id: 'user_eva', avatarSeed: 'eva_seed',);

    _mockUsers = [alice, bob, charlie, diana, eva, me];

    _mockFriends = [
      FriendshipInfo(
        id: const Uuid().v4(),
        friend: alice,
        status: FriendshipStatus.accepted,
        createdAt: DateTime.now().subtract(const Duration(days: 30)),
        updatedAt: DateTime.now(),
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
        friend: diana,
        status: FriendshipStatus.accepted,
        createdAt: DateTime.now().subtract(const Duration(days: 7)),
        updatedAt: DateTime.now(),
      ),
    ];

    // Restore Groups
    final sprintGroup = GroupInfo(
      id: 'group_sprint_001',
      name: 'CET-6 30天冲刺',
      type: GroupType.sprint,
      focusTags: ['English'],
      memberCount: 45,
      totalFlamePower: 12500,
      todayCheckinCount: 32,
      totalTasksCompleted: 450,
      maxMembers: 50,
      isPublic: true,
      joinRequiresApproval: false,
      createdAt: DateTime.now().subtract(const Duration(days: 10)),
      updatedAt: DateTime.now(),
      myRole: GroupRole.member,
    );

    final studyGroup = GroupInfo(
      id: 'group_study_001',
      name: '数据结构互助组',
      type: GroupType.squad,
      focusTags: ['CS', 'Data Structure'],
      memberCount: 28,
      totalFlamePower: 5600,
      todayCheckinCount: 15,
      totalTasksCompleted: 180,
      maxMembers: 50,
      isPublic: true,
      joinRequiresApproval: false,
      createdAt: DateTime.now().subtract(const Duration(days: 20)),
      updatedAt: DateTime.now(),
      myRole: GroupRole.admin,
    );
    _mockGroups = [sprintGroup, studyGroup];

    // Group messages with multiple members
    _mockGroupMessages = {
      sprintGroup.id: [
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: alice,
          content: '冲冲冲！',
          createdAt: DateTime.now().subtract(const Duration(minutes: 30)),
          updatedAt: DateTime.now(),
          readBy: [alice.id, charlie.id, diana.id, bob.id, eva.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.planShare,
          sender: me,
          content: '把我的冲刺计划分享给大家',
          createdAt: DateTime.now().subtract(const Duration(minutes: 28)),
          updatedAt: DateTime.now(),
          contentData: {
            'resource_type': 'plan',
            'resource_title': 'CET-6 冲刺计划',
            'resource_summary': '每日阅读+听力+背词节奏',
            'resource_meta': {
              'progress': 0.42,
              'target_date': DateTime.now()
                  .add(const Duration(days: 20))
                  .toIso8601String(),
              'subject': 'English',
            },
            'comment': '需要的话一起进度对齐',
          },
          readBy: [alice.id, charlie.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: charlie,
          content: '今天做完了阅读理解，感觉题目变简单了',
          createdAt: DateTime.now().subtract(const Duration(minutes: 25)),
          updatedAt: DateTime.now(),
          readBy: [alice.id, diana.id, bob.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: me,
          content: '我也感觉进步了，大家一起加油！',
          createdAt: DateTime.now().subtract(const Duration(minutes: 20)),
          updatedAt: DateTime.now(),
          readBy: [
            alice.id,
            charlie.id,
            diana.id,
            bob.id,
            eva.id,
            'user_frank',
            'user_grace',
          ],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.checkin,
          sender: diana,
          content: '完成今日单词打卡',
          createdAt: DateTime.now().subtract(const Duration(minutes: 15)),
          updatedAt: DateTime.now(),
          contentData: {'flame_power': 120, 'today_duration': 60, 'streak': 7},
          readBy: [alice.id, charlie.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: alice,
          content: '厉害！连续7天了',
          createdAt: DateTime.now().subtract(const Duration(minutes: 10)),
          updatedAt: DateTime.now(),
          readBy: [diana.id],
        ),
      ],
      studyGroup.id: [
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: charlie,
          content: '有人能解释一下红黑树的平衡操作吗？',
          createdAt: DateTime.now().subtract(const Duration(hours: 2)),
          updatedAt: DateTime.now(),
          readBy: [alice.id, me.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.capsuleShare,
          sender: alice,
          content: '分享一个好奇心胶囊',
          createdAt:
              DateTime.now().subtract(const Duration(hours: 1, minutes: 40)),
          updatedAt: DateTime.now(),
          contentData: {
            'resource_type': 'curiosity_capsule',
            'resource_title': '图灵测试为什么仍然有趣',
            'resource_summary': '从哲学到工程，图灵测试仍是理解智能边界的一扇窗...',
            'resource_meta': {'related_subject': 'AI'},
            'comment': '这段可以当作读书会材料',
          },
          readBy: [charlie.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: me,
          content: '红黑树的平衡主要通过旋转和变色来维护，左旋和右旋是基本操作',
          createdAt:
              DateTime.now().subtract(const Duration(hours: 1, minutes: 50)),
          updatedAt: DateTime.now(),
          readBy: [charlie.id, alice.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: alice,
          content: '我找到一个不错的视频教程，分享给大家',
          createdAt: DateTime.now().subtract(const Duration(hours: 1)),
          updatedAt: DateTime.now(),
          readBy: [charlie.id, me.id, diana.id],
        ),
      ],
    };

    // Private messages with quote support
    _mockPrivateMessages = {
      alice.id: [
        PrivateMessageInfo(
          id: 'pm_alice_1',
          sender: alice,
          receiver: me,
          messageType: MessageType.text,
          isRead: true,
          readAt: DateTime.now().subtract(const Duration(minutes: 8)),
          createdAt: DateTime.now().subtract(const Duration(minutes: 10)),
          updatedAt: DateTime.now(),
          content: '今天也要加油学习呀！',
        ),
        PrivateMessageInfo(
          id: 'pm_alice_2',
          sender: me,
          receiver: alice,
          messageType: MessageType.text,
          isRead: true,
          readAt: DateTime.now().subtract(const Duration(minutes: 5)),
          createdAt: DateTime.now().subtract(const Duration(minutes: 8)),
          updatedAt: DateTime.now(),
          content: '好的，我正在复习数据结构',
        ),
        PrivateMessageInfo(
          id: 'pm_alice_3',
          sender: alice,
          receiver: me,
          messageType: MessageType.text,
          isRead: true,
          readAt: DateTime.now().subtract(const Duration(minutes: 3)),
          createdAt: DateTime.now().subtract(const Duration(minutes: 5)),
          updatedAt: DateTime.now(),
          content: '需要帮忙可以找我哦',
        ),
      ],
      charlie.id: [
        PrivateMessageInfo(
          id: 'pm_charlie_1',
          sender: charlie,
          receiver: me,
          messageType: MessageType.text,
          isRead: false,
          createdAt: DateTime.now().subtract(const Duration(hours: 1)),
          updatedAt: DateTime.now(),
          content: '明天一起去图书馆吗？',
        ),
        PrivateMessageInfo(
          id: 'pm_charlie_2',
          sender: me,
          receiver: charlie,
          messageType: MessageType.prismShare,
          isRead: false,
          createdAt: DateTime.now().subtract(const Duration(minutes: 50)),
          updatedAt: DateTime.now(),
          content: '分享一个认知棱镜',
          contentData: {
            'resource_type': 'cognitive_prism_pattern',
            'resource_title': '计划谬误',
            'resource_summary': '我经常低估任务复杂度，导致计划频繁延期...',
            'resource_meta': {'pattern_type': 'cognitive', 'frequency': 5},
            'comment': '想听听你的建议',
          },
        ),
      ],
      diana.id: [
        PrivateMessageInfo(
          id: 'pm_diana_1',
          sender: diana,
          receiver: me,
          messageType: MessageType.text,
          isRead: true,
          readAt: DateTime.now().subtract(const Duration(days: 1)),
          createdAt: DateTime.now().subtract(const Duration(days: 1)),
          updatedAt: DateTime.now(),
          content: '上次的笔记整理好了',
        ),
        PrivateMessageInfo(
          id: 'pm_diana_2',
          sender: me,
          receiver: diana,
          messageType: MessageType.fragmentShare,
          isRead: true,
          readAt: DateTime.now().subtract(const Duration(hours: 4)),
          createdAt: DateTime.now().subtract(const Duration(hours: 6)),
          updatedAt: DateTime.now(),
          content: '分享一个认知碎片',
          contentData: {
            'resource_type': 'cognitive_fragment',
            'resource_title': '拖延的触发点',
            'resource_summary': '我发现只要任务没有明确的下一步，就会开始刷手机...',
            'resource_meta': {'source_type': 'capsule', 'severity': 2},
            'comment': '帮我看看有没有更好的拆解方式',
          },
        ),
      ],
    };
  }
  factory MockCommunityRepository.instance() => _instance;

  // Demo user ID - matches DemoDataService.demoUser.id
  static const String currentUserId = 'CS_Sophomore_12345';

  UserBrief _createUser(String name, int level, UserStatus status,
          {String? avatarSeed, String? id,}) =>
      UserBrief(
        id: id ?? const Uuid().v4(),
        username: name.toLowerCase(),
        nickname: name,
        avatarUrl:
            'https://api.dicebear.com/9.x/avataaars/png?seed=${avatarSeed ?? name}',
        flameLevel: level,
        flameBrightness: 0.5 + (level / 20.0),
        status: status,
      );

  late final List<UserBrief> _mockUsers;
  late final List<FriendshipInfo> _mockFriends;
  late final List<GroupInfo> _mockGroups;
  late final Map<String, List<MessageInfo>> _mockGroupMessages;
  late final Map<String, List<PrivateMessageInfo>> _mockPrivateMessages;

  static final MockCommunityRepository _instance =
      MockCommunityRepository._init();

  @override
  Future<List<FriendshipInfo>> getFriends(
          {int limit = 20, int offset = 0,}) async =>
      _mockFriends;

  @override
  Future<List<PrivateMessageInfo>> getPrivateMessages(String friendId,
      {String? beforeId, int limit = 50,}) async {
    final messages = _mockPrivateMessages[friendId] ?? [];
    messages.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return messages;
  }

  @override
  Future<PrivateMessageInfo> sendPrivateMessage(
      PrivateMessageSend message,) async {
    final me = _mockUsers.firstWhere((u) => u.id == currentUserId);
    final target = _mockUsers.firstWhere((u) => u.id == message.targetUserId,
        orElse: () => _createUser('User', 1, UserStatus.online,
            id: message.targetUserId,),);

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
      id: const Uuid().v4(),
      sender: me,
      receiver: target,
      messageType: message.messageType,
      content: message.content,
      isRead: false,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      replyToId: message.replyToId,
      threadRootId: message.threadRootId,
      mentionUserIds: message.mentionUserIds,
      quotedMessage: quotedMessage,
    );

    if (!_mockPrivateMessages.containsKey(message.targetUserId)) {
      _mockPrivateMessages[message.targetUserId] = [];
    }
    _mockPrivateMessages[message.targetUserId]!.insert(0, newMsg);

    // Auto-read by "other person" for demo
    unawaited(
      Future<void>.delayed(
        const Duration(seconds: 2),
        () {
          final index = _mockPrivateMessages[message.targetUserId]!
              .indexWhere((m) => m.id == newMsg.id);
          if (index != -1) {
            _mockPrivateMessages[message.targetUserId]![index] =
                _mockPrivateMessages[message.targetUserId]![index].copyWith(
              isRead: true,
              readAt: DateTime.now(),
            );
          }
        },
      ),
    );

    return newMsg;
  }

  @override
  Future<void> revokePrivateMessage(String messageId) async {
    for (final list in _mockPrivateMessages.values) {
      final index = list.indexWhere((m) => m.id == messageId);
      if (index != -1) {
        list[index] =
            list[index].copyWith(isRevoked: true, revokedAt: DateTime.now());
        return;
      }
    }
  }

  @override
  Future<PrivateMessageInfo> editPrivateMessage(
    String messageId, {
    String? content,
    Map<String, dynamic>? contentData,
    List<String>? mentionUserIds,
  }) async {
    for (final list in _mockPrivateMessages.values) {
      final index = list.indexWhere((m) => m.id == messageId);
      if (index != -1) {
        final updated = list[index].copyWith(
          content: content ?? list[index].content,
          contentData: contentData ?? list[index].contentData,
          mentionUserIds: mentionUserIds ?? list[index].mentionUserIds,
          editedAt: DateTime.now(),
          updatedAt: DateTime.now(),
        );
        list[index] = updated;
        return updated;
      }
    }
    throw Exception('Message not found');
  }

  @override
  Future<PrivateMessageInfo> updatePrivateReaction(
    String messageId, {
    required String emoji,
    required String userId,
    required bool isAdd,
  }) async {
    for (final list in _mockPrivateMessages.values) {
      final index = list.indexWhere((m) => m.id == messageId);
      if (index != -1) {
        final original = list[index];
        final reactions = Map<String, dynamic>.from(original.reactions ?? {});
        final users = List<String>.from(
          (reactions[emoji] as List<dynamic>?) ?? const <String>[],
        );
        if (isAdd) {
          if (!users.contains(userId)) {
            users.add(userId);
          }
        } else {
          users.remove(userId);
        }
        if (users.isEmpty) {
          reactions.remove(emoji);
        } else {
          reactions[emoji] = users;
        }
        final updated = original.copyWith(
          reactions: reactions,
          updatedAt: DateTime.now(),
        );
        list[index] = updated;
        return updated;
      }
    }
    throw Exception('Message not found');
  }

  @override
  Future<List<PrivateMessageInfo>> searchPrivateMessages(
      String friendId, String keyword,
      {int limit = 50,}) async {
    final list = _mockPrivateMessages[friendId] ?? [];
    final lower = keyword.toLowerCase();
    return list
        .where((m) => (m.content ?? '').toLowerCase().contains(lower))
        .take(limit)
        .toList();
  }

  @override
  Future<List<GroupListItem>> getMyGroups() async => _mockGroups
      .map(
        (g) => GroupListItem(
          id: g.id,
          name: g.name,
          type: g.type,
          memberCount: g.memberCount,
          totalFlamePower: g.totalFlamePower,
          focusTags: g.focusTags,
          myRole: g.myRole,
        ),
      )
      .toList();

  @override
  Future<GroupInfo> getGroup(String groupId) async =>
      _mockGroups.firstWhere((g) => g.id == groupId);

  @override
  Future<List<MessageInfo>> getMessages(String groupId,
          {String? beforeId, int limit = 50,}) async =>
      _mockGroupMessages[groupId] ?? [];

  @override
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
    // Simulate network delay
    await Future<void>.delayed(const Duration(milliseconds: 300));

    final currentUser = _mockUsers.firstWhere((u) => u.id == currentUserId);
    final newMsg = MessageInfo(
      id: const Uuid().v4(),
      messageType: type,
      content: content,
      contentData: contentData,
      replyToId: replyToId,
      threadRootId: threadRootId,
      mentionUserIds: mentionUserIds,
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

  @override
  Future<MessageInfo> editGroupMessage(
    String groupId,
    String messageId, {
    String? content,
    Map<String, dynamic>? contentData,
    List<String>? mentionUserIds,
  }) async {
    final list = _mockGroupMessages[groupId] ?? [];
    final index = list.indexWhere((m) => m.id == messageId);
    if (index == -1) {
      throw Exception('Message not found');
    }
    final original = list[index];
    final updated = MessageInfo(
      id: original.id,
      messageType: original.messageType,
      sender: original.sender,
      content: content ?? original.content,
      contentData: contentData ?? original.contentData,
      replyToId: original.replyToId,
      threadRootId: original.threadRootId,
      mentionUserIds: mentionUserIds ?? original.mentionUserIds,
      reactions: original.reactions,
      createdAt: original.createdAt,
      updatedAt: DateTime.now(),
      isRevoked: original.isRevoked,
      revokedAt: original.revokedAt,
      editedAt: DateTime.now(),
      readBy: original.readBy,
      quotedMessage: original.quotedMessage,
      readByUsers: original.readByUsers,
    );
    list[index] = updated;
    return updated;
  }

  @override
  Future<void> revokeGroupMessage(String groupId, String messageId) async {
    final list = _mockGroupMessages[groupId] ?? [];
    final index = list.indexWhere((m) => m.id == messageId);
    if (index == -1) return;
    final original = list[index];
    list[index] = MessageInfo(
      id: original.id,
      messageType: original.messageType,
      sender: original.sender,
      content: original.content,
      contentData: original.contentData,
      replyToId: original.replyToId,
      threadRootId: original.threadRootId,
      mentionUserIds: original.mentionUserIds,
      reactions: original.reactions,
      createdAt: original.createdAt,
      updatedAt: DateTime.now(),
      isRevoked: true,
      revokedAt: DateTime.now(),
      editedAt: original.editedAt,
      readBy: original.readBy,
      quotedMessage: original.quotedMessage,
      readByUsers: original.readByUsers,
    );
  }

  @override
  Future<MessageInfo> updateGroupReaction(
    String groupId,
    String messageId, {
    required String emoji,
    required String userId,
    required bool isAdd,
  }) async {
    final list = _mockGroupMessages[groupId] ?? [];
    final index = list.indexWhere((m) => m.id == messageId);
    if (index == -1) {
      throw Exception('Message not found');
    }
    final original = list[index];
    final reactions = Map<String, dynamic>.from(original.reactions ?? {});
    final users = List<String>.from(
      (reactions[emoji] as List<dynamic>?) ?? const <String>[],
    );
    if (isAdd) {
      if (!users.contains(userId)) {
        users.add(userId);
      }
    } else {
      users.remove(userId);
    }
    if (users.isEmpty) {
      reactions.remove(emoji);
    } else {
      reactions[emoji] = users;
    }
    final updated = MessageInfo(
      id: original.id,
      messageType: original.messageType,
      sender: original.sender,
      content: original.content,
      contentData: original.contentData,
      replyToId: original.replyToId,
      threadRootId: original.threadRootId,
      mentionUserIds: original.mentionUserIds,
      reactions: reactions,
      createdAt: original.createdAt,
      updatedAt: DateTime.now(),
      isRevoked: original.isRevoked,
      revokedAt: original.revokedAt,
      editedAt: original.editedAt,
      readBy: original.readBy,
      quotedMessage: original.quotedMessage,
      readByUsers: original.readByUsers,
    );
    list[index] = updated;
    return updated;
  }

  @override
  Future<List<MessageInfo>> searchGroupMessages(String groupId, String keyword,
      {int limit = 50,}) async {
    final list = _mockGroupMessages[groupId] ?? [];
    final lower = keyword.toLowerCase();
    return list
        .where((m) => (m.content ?? '').toLowerCase().contains(lower))
        .take(limit)
        .toList();
  }

  @override
  Future<List<MessageInfo>> getThreadMessages(
      String groupId, String threadRootId,
      {int limit = 100,}) async {
    final list = _mockGroupMessages[groupId] ?? [];
    MessageInfo? root;
    for (final msg in list) {
      if (msg.id == threadRootId) {
        root = msg;
        break;
      }
    }
    final replies = list.where((m) => m.threadRootId == threadRootId).toList()
      ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
    final combined = root != null ? [root, ...replies] : replies;
    return combined.take(limit).toList();
  }

  // Other methods remain as minimal implementation
  @override
  Future<void> sendFriendRequest(String targetUserId,
      {String? message,}) async {}
  @override
  Future<void> respondToRequest(String friendshipId, bool accept) async {}
  @override
  Future<List<FriendshipInfo>> getPendingRequests() async => [];
  @override
  Future<List<FriendRecommendation>> getFriendRecommendations(
          {int limit = 10,}) async =>
      [];
  @override
  Future<List<UserBrief>> searchUsers(String keyword, {int limit = 20}) async =>
      [];
  @override
  Future<void> updateStatus(UserStatus status) async {}
  @override
  Future<GroupInfo> createGroup(GroupCreate group) async => _mockGroups[0];
  @override
  Future<List<GroupListItem>> searchGroups(
          {String? keyword,
          GroupType? type,
          List<String>? tags,
          int limit = 20,}) async =>
      [];
  @override
  Future<void> joinGroup(String groupId) async {}
  @override
  Future<void> leaveGroup(String groupId) async {}
  @override
  Future<CheckinResponse> checkin(String groupId,
          {required int todayDurationMinutes, String? message,}) async =>
      CheckinResponse(
          success: true,
          newStreak: 1,
          flameEarned: 10,
          rankInGroup: 1,
          groupCheckinCount: 1,);
  @override
  Future<List<GroupTaskInfo>> getGroupTasks(String groupId) async => [];
  @override
  Future<GroupTaskInfo> createGroupTask(
          String groupId, GroupTaskCreate task,) async =>
      GroupTaskInfo(
          id: '',
          title: '',
          tags: [],
          estimatedMinutes: 0,
          difficulty: 1,
          totalClaims: 0,
          totalCompletions: 0,
          completionRate: 0,
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),);
  @override
  Future<void> claimTask(String taskId) async {}
  @override
  Future<GroupFlameStatus> getFlameStatus(String groupId) async =>
      GroupFlameStatus(
          groupId: groupId, totalPower: 0, flames: [], bonfireLevel: 1,);

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
