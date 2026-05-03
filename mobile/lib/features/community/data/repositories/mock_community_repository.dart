// ignore_for_file: cascade_invocations, prefer_expression_function_bodies, unnecessary_breaks, unnecessary_lambdas, prefer_null_aware_operators

import 'dart:async';

import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/models/community_models.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:uuid/uuid.dart';

class MockCommunityRepository implements CommunityRepository {
  MockCommunityRepository() : this._init();

  MockCommunityRepository._init() {
    // Create current user matching DemoDataService
    final me = _createUser(
      'Mika',
      15,
      UserStatus.online,
      id: currentUserId,
      avatarSeed: 'AI_Learner_02',
    );
    final alice = _createUser(
      'Lena',
      8,
      UserStatus.online,
      id: 'user_alice',
      avatarSeed: 'alice_seed',
    );
    final bob = _createUser(
      'Mori',
      5,
      UserStatus.offline,
      id: 'user_bob',
      avatarSeed: 'bob_seed',
    );
    final charlie = _createUser(
      'Nora',
      12,
      UserStatus.online,
      id: 'user_charlie',
      avatarSeed: 'charlie_seed',
    );
    final diana = _createUser(
      'Owen',
      9,
      UserStatus.online,
      id: 'user_diana',
      avatarSeed: 'diana_seed',
    );
    final eva = _createUser(
      'Rina',
      6,
      UserStatus.offline,
      id: 'user_eva',
      avatarSeed: 'eva_seed',
    );

    _mockUsers = [alice, bob, charlie, diana, eva, me];

    _mockFriends = [
      FriendshipInfo(
        id: const Uuid().v4(),
        friend: alice,
        status: FriendshipStatus.accepted,
        createdAt: DateTime.now().subtract(const Duration(days: 30)),
        updatedAt: DateTime.now(),
        accountability: AccountabilityFriendSummary(
          partnershipId: 'demo_core_partner',
          slotType: 'core',
          status: 'active',
          myRole: 'initiator',
          myCheckedInToday: false,
          partnerCheckedInToday: true,
          myStreakDays: 7,
          partnerStreakDays: 5,
          lastCheckinAt: DateTime.now().subtract(const Duration(hours: 2)),
          goalPreview: I18nService.instance.isChinese
              ? '每天同步一个主任务和一个轻复盘动作'
              : 'Sync one main task and one light review action daily',
        ),
      ),
      FriendshipInfo(
        id: const Uuid().v4(),
        friend: charlie,
        status: FriendshipStatus.accepted,
        createdAt: DateTime.now().subtract(const Duration(days: 15)),
        updatedAt: DateTime.now(),
        accountability: AccountabilityFriendSummary(
          partnershipId: 'demo_pending_partner',
          slotType: 'core',
          status: 'pending',
          myRole: 'partner',
          myCheckedInToday: false,
          partnerCheckedInToday: false,
          myStreakDays: 0,
          partnerStreakDays: 0,
          goalPreview: I18nService.instance.isChinese
              ? '一起把周末节律和复盘稳定下来'
              : 'Stabilize weekend rhythm and reviews together',
        ),
      ),
      FriendshipInfo(
        id: const Uuid().v4(),
        friend: diana,
        status: FriendshipStatus.accepted,
        createdAt: DateTime.now().subtract(const Duration(days: 7)),
        updatedAt: DateTime.now(),
      ),
    ];
    _mockPendingRequests = [
      FriendshipInfo(
        id: 'friend_request_user_eva',
        friend: eva,
        status: FriendshipStatus.pending,
        createdAt: DateTime.now().subtract(const Duration(hours: 8)),
        updatedAt: DateTime.now().subtract(const Duration(hours: 1)),
      ),
    ];

    // Restore Groups
    final zh = I18nService.instance.isChinese;
    final sprintGroup = GroupInfo(
      id: 'group_sprint_001',
      name: zh ? '晚间语言复盘屋' : 'Evening Language Review House',
      description: zh
          ? '下班下课后一起做精读、跟说和短复盘，适合想慢慢找回表达节奏的人。'
          : 'Do intensive reading, shadowing, and short reviews together after work/class. Suitable for those who want to gradually regain their expression rhythm.',
      type: GroupType.sprint,
      focusTags: ['Language', 'English', 'Speaking'],
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
      name: zh ? '理工理解力自习组' : 'STEM Comprehension Study Group',
      description: zh
          ? '一起复盘课堂概念、错题和公式，不求卷时长，先把理解说清楚。'
          : 'Review classroom concepts, errors, and formulas together. Not about grinding hours, but getting understanding clear.',
      type: GroupType.squad,
      focusTags: ['Academic', 'Math', 'Science'],
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
    final aiGroup = GroupInfo(
      id: 'group_ai_001',
      name: zh ? '作品集慢慢长出来' : 'Portfolio Growth Space',
      description: zh
          ? '给跨领域学习者一个稳定更新作品集、表达方向和互相看初稿的空间。'
          : 'A space for cross-disciplinary learners to steadily update portfolios, refine direction, and review each other\'s drafts.',
      type: GroupType.squad,
      focusTags: ['Career', 'Portfolio', 'Creative'],
      memberCount: 33,
      totalFlamePower: 7800,
      todayCheckinCount: 11,
      totalTasksCompleted: 210,
      maxMembers: 60,
      isPublic: true,
      joinRequiresApproval: true,
      createdAt: DateTime.now().subtract(const Duration(days: 35)),
      updatedAt: DateTime.now().subtract(const Duration(hours: 4)),
    );
    final mathGroup = GroupInfo(
      id: 'group_math_001',
      name: zh ? '周末恢复实验室' : 'Weekend Recovery Lab',
      description: zh
          ? '一起讨论睡眠、运动和如何避免周末散掉，帮自己把节律重新接上。'
          : 'Discuss sleep, exercise, and how to avoid weekend dispersion. Help yourself reconnect your rhythm.',
      type: GroupType.sprint,
      focusTags: ['Wellness', 'Recovery', 'Habit'],
      memberCount: 19,
      totalFlamePower: 2600,
      todayCheckinCount: 8,
      totalTasksCompleted: 96,
      maxMembers: 40,
      isPublic: true,
      joinRequiresApproval: false,
      createdAt: DateTime.now().subtract(const Duration(days: 6)),
      updatedAt: DateTime.now().subtract(const Duration(hours: 2)),
      deadline: DateTime.now().add(const Duration(days: 24)),
      sprintGoal: zh ? '一起完成周末节律重置' : 'Complete weekend rhythm reset together',
    );
    _mockGroups = [sprintGroup, studyGroup, aiGroup, mathGroup];

    // Group messages with multiple members
    _mockGroupMessages = {
      sprintGroup.id: [
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: alice,
          content: zh
              ? '今晚先从 10 分钟轻输出开始，谁也不用一上来就满电。'
              : 'Start with 10 minutes of light output tonight. No one needs to be fully charged right away.',
          createdAt: DateTime.now().subtract(const Duration(minutes: 30)),
          updatedAt: DateTime.now(),
          readBy: [alice.id, charlie.id, diana.id, bob.id, eva.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.planShare,
          sender: me,
          content: zh ? '把我的冲刺计划分享给大家' : 'Sharing my sprint plan with everyone',
          createdAt: DateTime.now().subtract(const Duration(minutes: 28)),
          updatedAt: DateTime.now(),
          contentData: {
            'resource_type': 'plan',
            'resource_title': zh ? '晚间语言复盘计划' : 'Evening Language Review Plan',
            'resource_summary': zh
                ? '精读 + 跟说 + 5 分钟短复盘'
                : 'Intensive reading + Shadowing + 5-min short review',
            'resource_meta': {
              'progress': 0.42,
              'target_date': DateTime.now()
                  .add(const Duration(days: 20))
                  .toIso8601String(),
              'subject': 'Language',
            },
            'comment': zh ? '需要的话一起进度对齐' : 'Align progress together if needed',
          },
          readBy: [alice.id, charlie.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: charlie,
          content: zh
              ? '今天终于开口录完一版英文自我介绍，虽然还磕巴，但没有逃掉。'
              : 'Finally recorded an English self-introduction today. Still stuttering a bit, but I didn\'t bail.',
          createdAt: DateTime.now().subtract(const Duration(minutes: 25)),
          updatedAt: DateTime.now(),
          readBy: [alice.id, diana.id, bob.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: me,
          content: zh
              ? '我今晚也先从低门槛版本开始，感觉这样更能坚持。'
              : 'I\'ll also start with the low-barrier version tonight. Feels more sustainable this way.',
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
          content: zh ? '完成今日语言打卡' : 'Completed today\'s language check-in',
          createdAt: DateTime.now().subtract(const Duration(minutes: 15)),
          updatedAt: DateTime.now(),
          contentData: {'flame_power': 120, 'today_duration': 60, 'streak': 7},
          readBy: [alice.id, charlie.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: alice,
          content: zh
              ? '厉害，连续把节奏接住最不容易。'
              : 'Impressive. Keeping the rhythm going consistently is the hardest part.',
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
          content: zh
              ? '有人愿意一起对一题统计学错题吗？我老是把”样本量不够”和”样本偏差”混在一起。'
              : 'Anyone want to work through a statistics error together? I keep mixing up “insufficient sample size” and “sampling bias”.',
          createdAt: DateTime.now().subtract(const Duration(hours: 2)),
          updatedAt: DateTime.now(),
          readBy: [alice.id, me.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.capsuleShare,
          sender: alice,
          content: zh ? '分享一个好奇心胶囊' : 'Sharing a curiosity capsule',
          createdAt:
              DateTime.now().subtract(const Duration(hours: 1, minutes: 40)),
          updatedAt: DateTime.now(),
          contentData: {
            'resource_type': 'curiosity_capsule',
            'resource_title': zh
                ? '为什么”回忆”比反复重读更能记住内容'
                : 'Why “retrieval” remembers content better than repeated rereading',
            'resource_summary': zh
                ? '主动检索比重复看起来更费力，但正因为费力才更能留下记忆...'
                : 'Active retrieval feels more effortful than repetition, but precisely because it\'s effortful, it sticks better...',
            'resource_meta': {
              'related_subject': zh ? '学习策略' : 'Learning Strategies'
            },
            'comment': zh
                ? '我觉得这条很适合理工错题回看时用'
                : 'I think this is great for reviewing STEM errors',
          },
          readBy: [charlie.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: me,
          content: zh
              ? '我最近的做法是先问”这个结论为什么不能代表总体”，这样就不容易只盯着数量了。'
              : 'My recent approach is to first ask “why can\'t this conclusion represent the population”—that way I don\'t fixate on sample size alone.',
          createdAt:
              DateTime.now().subtract(const Duration(hours: 1, minutes: 50)),
          updatedAt: DateTime.now(),
          readBy: [charlie.id, alice.id],
        ),
        MessageInfo(
          id: const Uuid().v4(),
          messageType: MessageType.text,
          sender: alice,
          content: zh
              ? '我刚好有一张”抽样偏差 vs 样本量”的对照图，整理完发群里。'
              : 'I happen to have a comparison chart of “sampling bias vs sample size”. Will share once I\'ve organized it.',
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
          content: zh
              ? '今晚只求先开口，不求一上来就完整。'
              : 'Tonight just aim to start speaking. Don\'t expect to be complete right away.',
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
          content: zh
              ? '收到，我先做 10 分钟跟说，再看看要不要补一小段复盘。'
              : 'Got it. I\'ll do 10 minutes of shadowing first, then see if I need to add a short review.',
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
          content: zh
              ? '需要的话我可以帮你听第一版录音，不用等你准备得很完美。'
              : 'If needed, I can listen to your first recording. No need to wait until it\'s perfect.',
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
          content: zh
              ? '明天下午一起去图书馆吗？我想把作品集首页的第一屏重写一下。'
              : 'Want to go to the library together tomorrow afternoon? I want to rewrite the first screen of my portfolio homepage.',
        ),
        PrivateMessageInfo(
          id: 'pm_charlie_2',
          sender: me,
          receiver: charlie,
          messageType: MessageType.prismShare,
          isRead: false,
          createdAt: DateTime.now().subtract(const Duration(minutes: 50)),
          updatedAt: DateTime.now(),
          content: zh ? '分享一个认知棱镜' : 'Sharing a cognitive prism',
          contentData: {
            'resource_type': 'cognitive_prism_pattern',
            'resource_title': zh ? '任务复杂度低估' : 'Task Complexity Underestimation',
            'resource_summary': zh
                ? '我经常低估任务复杂度，导致计划频繁延期...'
                : 'I often underestimate task complexity, leading to frequent plan delays...',
            'resource_meta': {'pattern_type': 'cognitive', 'frequency': 5},
            'comment': zh ? '想听听你的建议' : 'Would love your advice',
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
          content: zh
              ? '上次你提到的作品集结构，我帮你顺手整理成了一个提纲。'
              : 'The portfolio structure you mentioned last time—I\'ve organized it into an outline for you.',
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
          content: zh ? '分享一个认知碎片' : 'Sharing a cognitive fragment',
          contentData: {
            'resource_type': 'cognitive_fragment',
            'resource_title': zh ? '拖延的触发点' : 'Procrastination Triggers',
            'resource_summary': zh
                ? '我发现只要任务没有明确的下一步，就会开始刷手机...'
                : 'I found that whenever a task lacks clear next steps, I start scrolling my phone...',
            'resource_meta': {'source_type': 'capsule', 'severity': 2},
            'comment': zh
                ? '帮我看看有没有更好的拆解方式'
                : 'Help me see if there\'s a better way to break it down',
          },
        ),
      ],
    };

    _mockFeedbackPrompts = [
      RecommendationFeedbackPrompt(
        promptId: 'friend:user_alice:immediate:demo',
        itemType: RecommendationItemType.friend,
        itemId: 'user_alice',
        stage: RecommendationFeedbackStage.immediate,
        triggerAction: 'friend_match_view',
        title: zh
            ? '这位责任伙伴推荐对你来说够契合吗？'
            : 'Is this accountability partner recommendation a good fit for you?',
        subtitle: zh
            ? '给相似度、互补性和舒适度打个分，系统会据此微调你的匹配权重。'
            : 'Rate similarity, complementarity, and comfort. The system will fine-tune your matching weights accordingly.',
        dueAt: DateTime.now().subtract(const Duration(hours: 2)),
        strategy: 'compatibility',
        target: 'accountability',
        user: alice,
        reasonTags: const ['subject_overlap', 'preference_alignment'],
      ),
      RecommendationFeedbackPrompt(
        promptId: 'group:group_ai_001:immediate:demo',
        itemType: RecommendationItemType.group,
        itemId: 'group_ai_001',
        stage: RecommendationFeedbackStage.immediate,
        triggerAction: 'reco_view',
        title: zh
            ? '这个社群推荐真的对口吗？'
            : 'Is this community recommendation really on target?',
        subtitle: zh
            ? '从兴趣匹配、活跃度和氛围三个角度告诉我们感受。'
            : 'Tell us your feelings from three angles: interest match, activity, and atmosphere.',
        dueAt: DateTime.now().subtract(const Duration(minutes: 90)),
        group: _toGroupListItem(aiGroup),
        reasonTags: const ['tag_overlap', 'trending'],
      ),
    ];

    _mockFeedbackInsights = {
      RecommendationItemType.friend: RecommendationFeedbackInsight(
        itemType: RecommendationItemType.friend,
        recentFeedbackCount: 3,
        averageScores: const {
          'overall_score': 3.7,
          'similarity_score': 3.3,
          'comfort_score': 4.0,
        },
        topPositiveSignals: const ['trustworthy', 'good_similarity'],
        topNegativeSignals: const ['too_dissimilar'],
        userTuning: const {
          'feature_weights': {
            'subject_overlap': 1.08,
            'relationship_readiness': 1.04,
          },
          'strategy_bias': {
            'compatibility': 1.06,
          },
        },
        globalAdjustments: const {
          'subject_overlap': 1.02,
          'preference_alignment': 1.01,
        },
      ),
      RecommendationItemType.group: RecommendationFeedbackInsight(
        itemType: RecommendationItemType.group,
        recentFeedbackCount: 2,
        averageScores: const {
          'overall_score': 3.5,
          'interest_match_score': 3.0,
          'activity_score': 3.5,
        },
        topPositiveSignals: const ['good_interest_match'],
        topNegativeSignals: const ['want_more_tag_match'],
        userTuning: const {
          'feature_weights': {
            'tag_score': 1.1,
            'activity': 1.03,
          },
        },
        globalAdjustments: const {
          'tag_score': 1.03,
          'quality': 1.01,
        },
      ),
    };

    _mockReports = [];

    final zh = I18nService.instance.isChinese;
    final now = DateTime.now();
    _mockGroupTasks = {
      'group_sprint_001': [
        GroupTaskInfo(
          id: 'task_sprint_1',
          title: zh ? '完成每日算法练习' : 'Complete daily algorithm practice',
          description: zh ? 'LeetCode 3 题' : '3 LeetCode problems',
          tags: ['algorithms', 'daily'],
          estimatedMinutes: 45,
          difficulty: 3,
          totalClaims: 2,
          totalCompletions: 1,
          completionRate: 0.5,
          createdAt: now.subtract(const Duration(days: 2)),
          updatedAt: now,
          creator: alice,
          isClaimedByMe: true,
        ),
        GroupTaskInfo(
          id: 'task_sprint_2',
          title: zh ? '阅读系统设计文章' : 'Read system design article',
          tags: ['system-design'],
          estimatedMinutes: 30,
          difficulty: 2,
          totalClaims: 3,
          totalCompletions: 3,
          completionRate: 1.0,
          createdAt: now.subtract(const Duration(days: 5)),
          updatedAt: now.subtract(const Duration(days: 1)),
          creator: bob,
          myCompletionStatus: true,
        ),
        GroupTaskInfo(
          id: 'task_sprint_3',
          title: zh ? '复习动态规划' : 'Review dynamic programming',
          description: zh ? '重点：背包问题' : 'Focus: knapsack problems',
          tags: ['algorithms', 'dp'],
          estimatedMinutes: 60,
          difficulty: 4,
          totalClaims: 1,
          totalCompletions: 0,
          completionRate: 0.0,
          createdAt: now.subtract(const Duration(days: 1)),
          updatedAt: now.subtract(const Duration(days: 1)),
          creator: charlie,
        ),
      ],
      'group_study_001': [
        GroupTaskInfo(
          id: 'task_study_1',
          title: zh ? '完成第三章习题' : 'Complete Chapter 3 exercises',
          tags: ['study', 'chapter3'],
          estimatedMinutes: 90,
          difficulty: 3,
          totalClaims: 4,
          totalCompletions: 2,
          completionRate: 0.5,
          createdAt: now.subtract(const Duration(days: 3)),
          updatedAt: now,
          creator: diana,
          isClaimedByMe: true,
        ),
        GroupTaskInfo(
          id: 'task_study_2',
          title: zh ? '整理课堂笔记' : 'Organize lecture notes',
          tags: ['notes', 'review'],
          estimatedMinutes: 45,
          difficulty: 1,
          totalClaims: 2,
          totalCompletions: 2,
          completionRate: 1.0,
          createdAt: now.subtract(const Duration(days: 4)),
          updatedAt: now.subtract(const Duration(days: 2)),
          creator: me,
          myCompletionStatus: true,
        ),
      ],
      'group_ai_001': [
        GroupTaskInfo(
          id: 'task_ai_1',
          title: zh ? '实现 Transformer 注意力机制' : 'Implement Transformer attention',
          description: zh ? '从头实现多头注意力' : 'Multi-head attention from scratch',
          tags: ['transformer', 'attention', 'deep-learning'],
          estimatedMinutes: 120,
          difficulty: 5,
          totalClaims: 5,
          totalCompletions: 3,
          completionRate: 0.6,
          createdAt: now.subtract(const Duration(days: 7)),
          updatedAt: now.subtract(const Duration(days: 1)),
          creator: bob,
        ),
        GroupTaskInfo(
          id: 'task_ai_2',
          title: zh ? '训练一个简单 CNN' : 'Train a simple CNN',
          tags: ['cnn', 'computer-vision'],
          estimatedMinutes: 60,
          difficulty: 3,
          totalClaims: 3,
          totalCompletions: 2,
          completionRate: 0.67,
          createdAt: now.subtract(const Duration(days: 5)),
          updatedAt: now.subtract(const Duration(days: 2)),
          creator: alice,
          isClaimedByMe: true,
        ),
      ],
      'group_math_001': [
        GroupTaskInfo(
          id: 'task_math_1',
          title: zh ? '证明拉格朗日中值定理' : 'Prove Lagrange Mean Value Theorem',
          tags: ['calculus', 'proof'],
          estimatedMinutes: 60,
          difficulty: 4,
          totalClaims: 1,
          totalCompletions: 0,
          completionRate: 0.0,
          createdAt: now.subtract(const Duration(days: 2)),
          updatedAt: now.subtract(const Duration(days: 2)),
          creator: charlie,
          isClaimedByMe: true,
        ),
        GroupTaskInfo(
          id: 'task_math_2',
          title: zh ? '做 10 道积分练习题' : 'Do 10 integral practice problems',
          tags: ['calculus', 'practice'],
          estimatedMinutes: 45,
          difficulty: 2,
          totalClaims: 2,
          totalCompletions: 1,
          completionRate: 0.5,
          createdAt: now.subtract(const Duration(days: 3)),
          updatedAt: now,
          creator: diana,
        ),
        GroupTaskInfo(
          id: 'task_math_3',
          title: zh ? '总结微分方程解法' : 'Summarize differential equation methods',
          tags: ['differential-equations', 'summary'],
          estimatedMinutes: 30,
          difficulty: 3,
          totalClaims: 2,
          totalCompletions: 2,
          completionRate: 1.0,
          createdAt: now.subtract(const Duration(days: 6)),
          updatedAt: now.subtract(const Duration(days: 3)),
          creator: bob,
        ),
      ],
    };
  }
  factory MockCommunityRepository.instance() => _instance;

  // Demo user ID - matches DemoDataService.demoUser.id
  static const String currentUserId = 'CS_Sophomore_12345';

  UserBrief _createUser(
    String name,
    int level,
    UserStatus status, {
    String? avatarSeed,
    String? id,
  }) =>
      UserBrief(
        id: id ?? const Uuid().v4(),
        username: name.toLowerCase(),
        nickname: name,
        flameLevel: level,
        flameBrightness:
            (0.5 + (level / 40.0)).clamp(0.0, 1.0), // 🔧 修复：确保不超过1.0
        status: status,
      );

  late final List<UserBrief> _mockUsers;
  late final List<FriendshipInfo> _mockFriends;
  late final List<FriendshipInfo> _mockPendingRequests;
  late final List<GroupInfo> _mockGroups;
  late final Map<String, List<MessageInfo>> _mockGroupMessages;
  late final Map<String, List<PrivateMessageInfo>> _mockPrivateMessages;
  late final List<RecommendationFeedbackPrompt> _mockFeedbackPrompts;
  late final Map<RecommendationItemType, RecommendationFeedbackInsight>
      _mockFeedbackInsights;
  late final List<Map<String, dynamic>> _mockReports;
  late final Map<String, List<GroupTaskInfo>> _mockGroupTasks;

  static final MockCommunityRepository _instance =
      MockCommunityRepository._init();

  GroupListItem _toGroupListItem(GroupInfo group) => GroupListItem(
        id: group.id,
        name: group.name,
        description: group.description,
        type: group.type,
        memberCount: group.memberCount,
        totalFlamePower: group.totalFlamePower,
        todayCheckinCount: group.todayCheckinCount,
        focusTags: group.focusTags,
        deadline: group.deadline,
        daysRemaining: group.deadline == null
            ? null
            : group.deadline!.difference(DateTime.now()).inDays.clamp(0, 9999),
        isPublic: group.isPublic,
        joinRequiresApproval: group.joinRequiresApproval,
        activityScore: group.todayCheckinCount * 4 +
            group.memberCount +
            (group.totalFlamePower / 100),
        myRole: group.myRole,
      );

  @override
  Future<List<FriendshipInfo>> getFriends({
    int limit = 20,
    int offset = 0,
  }) async =>
      _mockFriends;

  @override
  Future<List<PrivateMessageInfo>> getPrivateMessages(
    String friendId, {
    String? beforeId,
    int limit = 50,
  }) async {
    final messages = List<PrivateMessageInfo>.from(
      _mockPrivateMessages[friendId] ?? [],
    );
    messages.sort((a, b) => b.createdAt.compareTo(a.createdAt));

    if (beforeId != null) {
      final index = messages.indexWhere((m) => m.id == beforeId);
      if (index >= 0) {
        final older = messages.sublist(index + 1);
        return older.take(limit).toList();
      }
    }
    return messages.take(limit).toList();
  }

  @override
  Future<PrivateMessageInfo> sendPrivateMessage(
    PrivateMessageSend message,
  ) async {
    final me = _mockUsers.firstWhere((u) => u.id == currentUserId);
    final target = _mockUsers.firstWhere(
      (u) => u.id == message.targetUserId,
      orElse: () => _createUser(
        'User',
        1,
        UserStatus.online,
        id: message.targetUserId,
      ),
    );

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
    String friendId,
    String keyword, {
    int limit = 50,
  }) async {
    final list = _mockPrivateMessages[friendId] ?? [];
    final lower = keyword.toLowerCase();
    return list
        .where((m) => (m.content ?? '').toLowerCase().contains(lower))
        .take(limit)
        .toList();
  }

  @override
  Future<List<GroupListItem>> getMyGroups() async =>
      _mockGroups.where((g) => g.myRole != null).map(_toGroupListItem).toList();

  @override
  Future<GroupInfo> getGroup(String groupId) async =>
      _mockGroups.firstWhere((g) => g.id == groupId);

  @override
  Future<List<MessageInfo>> getMessages(
    String groupId, {
    String? beforeId,
    int limit = 50,
  }) async {
    final messages = List<MessageInfo>.from(_mockGroupMessages[groupId] ?? []);
    messages.sort((a, b) => b.createdAt.compareTo(a.createdAt));

    if (beforeId != null) {
      final index = messages.indexWhere((m) => m.id == beforeId);
      if (index >= 0) {
        final older = messages.sublist(index + 1);
        return older.take(limit).toList();
      }
    }
    return messages.take(limit).toList();
  }

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
  Future<List<MessageInfo>> searchGroupMessages(
    String groupId,
    String keyword, {
    int limit = 50,
  }) async {
    final list = _mockGroupMessages[groupId] ?? [];
    final lower = keyword.toLowerCase();
    return list
        .where((m) => (m.content ?? '').toLowerCase().contains(lower))
        .take(limit)
        .toList();
  }

  @override
  Future<List<MessageInfo>> getThreadMessages(
    String groupId,
    String threadRootId, {
    int limit = 100,
  }) async {
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

  @override
  Future<int> markGroupMessagesRead(
    String groupId, {
    required String upToMessageId,
  }) async {
    final list = _mockGroupMessages[groupId];
    if (list == null || list.isEmpty) {
      return 0;
    }

    var updatedCount = 0;
    for (var i = 0; i < list.length; i++) {
      final message = list[i];
      final readBy = List<String>.from(message.readBy ?? const <String>[]);
      if (!readBy.contains(currentUserId)) {
        readBy.add(currentUserId);
        list[i] = MessageInfo(
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
          updatedAt: DateTime.now(),
          isRevoked: message.isRevoked,
          revokedAt: message.revokedAt,
          editedAt: message.editedAt,
          readBy: readBy,
          quotedMessage: message.quotedMessage,
          readByUsers: message.readByUsers,
        );
        updatedCount++;
      }
      if (message.id == upToMessageId) {
        break;
      }
    }
    return updatedCount;
  }

  // Other methods remain as minimal implementation
  @override
  Future<void> sendFriendRequest(
    String targetUserId, {
    String? message,
  }) async {}
  @override
  Future<void> respondToRequest(String friendshipId, bool accept) async {
    final index =
        _mockPendingRequests.indexWhere((item) => item.id == friendshipId);
    if (index < 0) return;
    final request = _mockPendingRequests.removeAt(index);
    if (accept) {
      _mockFriends = [
        FriendshipInfo(
          id: request.id,
          friend: request.friend,
          status: FriendshipStatus.accepted,
          createdAt: request.createdAt,
          updatedAt: DateTime.now(),
          initiatedByMe: request.initiatedByMe,
        ),
        ..._mockFriends,
      ];
    }
  }

  @override
  Future<List<FriendshipInfo>> getPendingRequests() async =>
      _mockPendingRequests;
  @override
  Future<List<FriendRecommendation>> getFriendRecommendations({
    int limit = 10,
    FriendMatchStrategy strategy = FriendMatchStrategy.compatibility,
    FriendRecommendationTarget target =
        FriendRecommendationTarget.accountability,
  }) async {
    final zh = I18nService.instance.isChinese;
    return (strategy == FriendMatchStrategy.complementary
            ? [
                FriendRecommendation(
                  user: _mockUsers.firstWhere((user) => user.id == 'user_bob'),
                  matchScore: 0.91,
                  matchReasons: zh
                      ? const [
                          'TA 的执行节奏更稳定，适合做监督型伙伴',
                          '你们都在准备语言与考试相关目标，互补关系更容易落地',
                        ]
                      : const [
                          'Their execution rhythm is steadier, making them a good accountability partner',
                          'You are both preparing language and exam-related goals, so the partnership can land more easily',
                        ],
                  strategy: strategy.name,
                  target: target.name,
                  summary: zh
                      ? '更适合做监督型责任伙伴，先建立好友关系会更顺畅。'
                      : 'Better suited as an accountability partner; starting as friends will be smoother.',
                  scoreBreakdown: const {
                    'support_strength': 0.28,
                    'subject_bridge': 0.18,
                    'stability': 0.14,
                  },
                ),
                FriendRecommendation(
                  user: _mockUsers.firstWhere((user) => user.id == 'user_eva'),
                  matchScore: 0.83,
                  matchReasons: zh
                      ? const [
                          'TA 的规划习惯更强，适合在关键节点提醒你',
                          '学习风格差异能带来新的推进方式',
                        ]
                      : const [
                          'Their planning habits are stronger, useful for reminders at key moments',
                          'Different learning styles can bring new ways to move forward',
                        ],
                  strategy: strategy.name,
                  target: target.name,
                  summary: zh
                      ? '适合作为互补型学习搭子。'
                      : 'Suitable as a complementary study partner.',
                  scoreBreakdown: const {
                    'support_strength': 0.25,
                    'diversity': 0.12,
                    'stability': 0.11,
                  },
                ),
              ]
            : [
                FriendRecommendation(
                  user:
                      _mockUsers.firstWhere((user) => user.id == 'user_alice'),
                  matchScore: 0.94,
                  matchReasons: zh
                      ? const [
                          '你们关注的学习主题高度重合',
                          '学习节奏和专注偏好比较接近',
                          '你们已经是好友，建立责任伙伴关系会更顺手',
                        ]
                      : const [
                          'Your learning topics highly overlap',
                          'Similar learning rhythm and focus preferences',
                          'Already friends—building an accountability partnership will be smoother',
                        ],
                  strategy: strategy.name,
                  target: target.name,
                  summary: zh
                      ? '契合度很高，适合直接发展成核心责任伙伴。'
                      : 'Highly compatible—suitable for developing directly into a core accountability partner.',
                  relationshipStatus: 'accepted',
                  isExistingFriend: true,
                  canInviteAccountability: true,
                  recommendedAction: 'invite_accountability',
                  scoreBreakdown: const {
                    'subject_overlap': 0.26,
                    'preference_alignment': 0.23,
                    'relationship_readiness': 0.05,
                  },
                ),
                FriendRecommendation(
                  user: _mockUsers
                      .firstWhere((user) => user.id == 'user_charlie'),
                  matchScore: 0.86,
                  matchReasons: zh
                      ? const [
                          '你们在相同社群里有共同经历',
                          '你们处理学习任务的方式比较契合',
                        ]
                      : const [
                          'Shared experiences in the same communities',
                          'Your approaches to learning tasks align well',
                        ],
                  strategy: strategy.name,
                  target: target.name,
                  summary: zh
                      ? '已有默契基础，适合深入协作。'
                      : 'Already have a rapport foundation—suitable for deeper collaboration.',
                  relationshipStatus: 'accepted',
                  isExistingFriend: true,
                  canInviteAccountability: true,
                  recommendedAction: 'invite_accountability',
                  scoreBreakdown: const {
                    'group_affinity': 0.14,
                    'cognitive_alignment': 0.09,
                    'stability': 0.07,
                  },
                ),
              ])
        .take(limit)
        .toList();
  }

  @override
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
    final zh = I18nService.instance.isChinese;
    if (promptId != null) {
      _mockFeedbackPrompts.removeWhere((prompt) => prompt.promptId == promptId);
    }
    _updateInsight(
      RecommendationItemType.friend,
      scores: {
        if (overallScore != null) 'overall_score': overallScore,
        if (relevanceScore != null) 'relevance_score': relevanceScore,
        if (explanationScore != null) 'explanation_score': explanationScore,
        if (actionabilityScore != null)
          'actionability_score': actionabilityScore,
        if (similarityScore != null) 'similarity_score': similarityScore,
        if (complementaryScore != null)
          'complementary_score': complementaryScore,
        if (comfortScore != null) 'comfort_score': comfortScore,
      },
      positiveSignals: selectedStrengths ?? const [],
      negativeSignals: [
        ...?selectedIssues,
        if ((freeText ?? '').contains(zh ? '不够相似' : 'not similar enough'))
          'too_dissimilar',
      ],
      featureBoosts: {
        'subject_overlap':
            similarityScore != null && similarityScore <= 2 ? 1.12 : 1.06,
        'relationship_readiness':
            comfortScore != null && comfortScore <= 2 ? 1.08 : 1.04,
      },
      strategyBoosts: {
        strategy.name: overallScore != null && overallScore >= 4 ? 1.08 : 1.04,
      },
    );
  }

  @override
  Future<List<UserBrief>> searchUsers(String keyword, {int limit = 20}) async =>
      [];
  @override
  Future<void> updateStatus(UserStatus status) async {}
  @override
  Future<GroupInfo> createGroup(GroupCreate group) async {
    final created = GroupInfo(
      id: const Uuid().v4(),
      name: group.name,
      description: group.description,
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
      deadline: group.deadline,
      sprintGoal: group.sprintGoal,
      myRole: GroupRole.owner,
    );
    _mockGroups.insert(0, created);
    _mockGroupMessages[created.id] = [];
    return created;
  }

  @override
  Future<List<GroupListItem>> searchGroups({
    String? keyword,
    GroupType? type,
    List<String>? tags,
    GroupDirectorySort sortBy = GroupDirectorySort.latest,
    int limit = 20,
    int offset = 0,
  }) async {
    final query = keyword?.trim().toLowerCase() ?? '';
    var groups = _mockGroups.where((group) {
      if (!(group.isPublic || group.myRole != null)) {
        return false;
      }
      if (type != null && group.type != type) {
        return false;
      }
      if (query.isNotEmpty) {
        final haystack =
            '${group.name} ${group.description ?? ''}'.toLowerCase();
        if (!haystack.contains(query)) {
          return false;
        }
      }
      if (tags != null && tags.isNotEmpty) {
        final normalized =
            group.focusTags.map((tag) => tag.toLowerCase()).toSet();
        for (final tag in tags) {
          if (!normalized.contains(tag.toLowerCase())) {
            return false;
          }
        }
      }
      return true;
    }).toList();

    switch (sortBy) {
      case GroupDirectorySort.hot:
        groups.sort((a, b) {
          final scoreA = a.todayCheckinCount * 4 +
              a.memberCount +
              (a.totalFlamePower / 100);
          final scoreB = b.todayCheckinCount * 4 +
              b.memberCount +
              (b.totalFlamePower / 100);
          return scoreB.compareTo(scoreA);
        });
        break;
      case GroupDirectorySort.latest:
        groups.sort((a, b) => b.createdAt.compareTo(a.createdAt));
        break;
      case GroupDirectorySort.random:
        groups = [...groups]..shuffle();
        break;
    }

    return groups.skip(offset).take(limit).map(_toGroupListItem).toList();
  }

  @override
  Future<GroupDirectoryInfo> getGroupDirectory({
    String? keyword,
    GroupType? type,
    List<String>? tags,
    GroupDirectorySort sortBy = GroupDirectorySort.hot,
    int limit = 20,
    int offset = 0,
  }) async {
    final groups = await searchGroups(
      keyword: keyword,
      type: type,
      tags: tags,
      sortBy: sortBy,
      limit: limit,
      offset: offset,
    );
    final tagCounts = <String, int>{};
    for (final group in _mockGroups.where((group) => group.isPublic)) {
      for (final tag in group.focusTags) {
        tagCounts[tag] = (tagCounts[tag] ?? 0) + 1;
      }
    }
    final recommendations = await getGroupRecommendations(limit: 6);
    return GroupDirectoryInfo(
      sortBy: sortBy,
      keyword: keyword,
      appliedTags: tags ?? const [],
      availableTags: tagCounts.keys.toList()
        ..sort((a, b) => (tagCounts[b] ?? 0).compareTo(tagCounts[a] ?? 0)),
      totalCount: (await searchGroups(
        keyword: keyword,
        type: type,
        tags: tags,
        sortBy: sortBy,
        limit: 999,
      ))
          .length,
      recommendations:
          keyword == null || keyword.isEmpty ? recommendations : const [],
      groups: groups,
    );
  }

  @override
  Future<void> joinGroup(String groupId) async {
    final index = _mockGroups.indexWhere((g) => g.id == groupId);
    if (index == -1) return;
    final group = _mockGroups[index];
    if (group.myRole != null) return;
    _mockGroups[index] = GroupInfo(
      id: group.id,
      name: group.name,
      description: group.description,
      avatarUrl: group.avatarUrl,
      type: group.type,
      focusTags: group.focusTags,
      memberCount: group.memberCount + 1,
      totalFlamePower: group.totalFlamePower,
      todayCheckinCount: group.todayCheckinCount,
      totalTasksCompleted: group.totalTasksCompleted,
      maxMembers: group.maxMembers,
      isPublic: group.isPublic,
      joinRequiresApproval: group.joinRequiresApproval,
      createdAt: group.createdAt,
      updatedAt: DateTime.now(),
      deadline: group.deadline,
      sprintGoal: group.sprintGoal,
      announcement: group.announcement,
      myRole: GroupRole.member,
    );
  }

  @override
  Future<void> leaveGroup(String groupId) async {
    final index = _mockGroups.indexWhere((g) => g.id == groupId);
    if (index == -1) return;
    final group = _mockGroups[index];
    if (group.myRole == null) return;
    _mockGroups[index] = GroupInfo(
      id: group.id,
      name: group.name,
      description: group.description,
      avatarUrl: group.avatarUrl,
      type: group.type,
      focusTags: group.focusTags,
      memberCount: group.memberCount > 0 ? group.memberCount - 1 : 0,
      totalFlamePower: group.totalFlamePower,
      todayCheckinCount: group.todayCheckinCount,
      totalTasksCompleted: group.totalTasksCompleted,
      maxMembers: group.maxMembers,
      isPublic: group.isPublic,
      joinRequiresApproval: group.joinRequiresApproval,
      createdAt: group.createdAt,
      updatedAt: DateTime.now(),
      deadline: group.deadline,
      sprintGoal: group.sprintGoal,
      announcement: group.announcement,
    );
  }

  @override
  Future<CheckinResponse> checkin(
    String groupId, {
    required int todayDurationMinutes,
    String? message,
  }) async =>
      CheckinResponse(
        success: true,
        newStreak: 1,
        flameEarned: 10,
        rankInGroup: 1,
        groupCheckinCount: 1,
      );
  @override
  Future<List<GroupTaskInfo>> getGroupTasks(String groupId) async =>
      List.from(_mockGroupTasks[groupId] ?? []);
  @override
  Future<GroupTaskInfo> createGroupTask(
    String groupId,
    GroupTaskCreate task,
  ) async {
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
    );
    _mockGroupTasks.putIfAbsent(groupId, () => []).add(newTask);
    return newTask;
  }
  @override
  Future<void> claimTask(String taskId) async {
    for (final tasks in _mockGroupTasks.values) {
      final idx = tasks.indexWhere((t) => t.id == taskId);
      if (idx != -1) {
        tasks[idx] = GroupTaskInfo(
          id: tasks[idx].id,
          title: tasks[idx].title,
          description: tasks[idx].description,
          tags: tasks[idx].tags,
          estimatedMinutes: tasks[idx].estimatedMinutes,
          difficulty: tasks[idx].difficulty,
          totalClaims: tasks[idx].totalClaims + 1,
          totalCompletions: tasks[idx].totalCompletions,
          completionRate: tasks[idx].completionRate,
          dueDate: tasks[idx].dueDate,
          creator: tasks[idx].creator,
          isClaimedByMe: true,
          myCompletionStatus: tasks[idx].myCompletionStatus,
          createdAt: tasks[idx].createdAt,
          updatedAt: DateTime.now(),
        );
        return;
      }
    }
  }
  @override
  Future<GroupFlameStatus> getFlameStatus(String groupId) async =>
      GroupFlameStatus(
        groupId: groupId,
        totalPower: 0,
        flames: [],
        bonfireLevel: 1,
      );

  // === CommunityRepository interface methods ===
  @override
  Future<List<Post>> getFeed(
      {int page = 1, int limit = 20, String? scope}) async {
    final zh = I18nService.instance.isChinese;
    final now = DateTime.now();
    return [
      Post(
        id: 'post_001',
        userId: _mockUsers[0].id,
        content: zh
            ? '今天用番茄工作法复习了第三章，25分钟一节真的很有效。之前总觉得学不完，拆成小块后反而多做了两节。'
            : 'Used Pomodoro to review chapter 3 today. 25-min blocks really work. I used to feel overwhelmed, but breaking it into chunks helped me do two extra sections.',
        createdAt: now.subtract(const Duration(hours: 2)),
        user: PostUser(id: _mockUsers[0].id, username: _mockUsers[0].nickname ?? _mockUsers[0].username),
        likeCount: 7,
        topic: zh ? '学习方法' : 'Study Methods',
      ),
      Post(
        id: 'post_002',
        userId: _mockUsers[2].id,
        content: zh
            ? '终于把线性代数的特征值分解搞懂了！关键是把矩阵看作变换而不是一堆数字。'
            : 'Finally understood eigendecomposition in linear algebra! The key was seeing matrices as transformations, not just arrays of numbers.',
        createdAt: now.subtract(const Duration(hours: 5)),
        user: PostUser(id: _mockUsers[2].id, username: _mockUsers[2].nickname ?? _mockUsers[2].username),
        likeCount: 12,
        topic: zh ? '数学突破' : 'Math Breakthrough',
      ),
      Post(
        id: 'post_003',
        userId: _mockUsers[1].id,
        content: zh
            ? '连续7天早起打卡了！虽然今天差点放弃，但想到责任伙伴在等我，就还是起来了。'
            : '7-day early rising streak! Almost gave up today, but knowing my accountability partner was waiting got me up.',
        createdAt: now.subtract(const Duration(hours: 8)),
        user: PostUser(id: _mockUsers[1].id, username: _mockUsers[1].nickname ?? _mockUsers[1].username),
        likeCount: 15,
        topic: zh ? '习惯养成' : 'Habit Building',
      ),
      Post(
        id: 'post_004',
        userId: _mockUsers[3].id,
        content: zh
            ? '分享一下我总结的错题复盘模板：1) 错因归类 2) 找到知识盲区 3) 出一道变式题验证。用了两周，同类错误减少了60%。'
            : 'Sharing my error review template: 1) Categorize error type 2) Find knowledge gap 3) Create a variant problem to verify. Used for 2 weeks, same-type errors down 60%.',
        createdAt: now.subtract(const Duration(days: 1)),
        user: PostUser(id: _mockUsers[3].id, username: _mockUsers[3].nickname ?? _mockUsers[3].username),
        likeCount: 23,
        topic: zh ? '错题复盘' : 'Error Review',
      ),
    ];
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

  @override
  Future<List<GroupRecommendationItem>> getGroupRecommendations({
    int limit = 20,
    int cursor = 0,
  }) async {
    final items = _mockGroups
        .where((group) => group.isPublic)
        .skip(cursor)
        .take(limit)
        .map(
          (group) => GroupRecommendationItem(
            group: _toGroupListItem(group),
            score: 0.6,
            reasons: [
              GroupRecommendationReason(
                type: 'trending',
                data: {'msg_7d': 42},
              ),
            ],
            requiresApproval: group.joinRequiresApproval,
          ),
        )
        .toList();
    return items;
  }

  @override
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
    final zh = I18nService.instance.isChinese;
    if (promptId != null) {
      _mockFeedbackPrompts.removeWhere((prompt) => prompt.promptId == promptId);
    }
    _updateInsight(
      RecommendationItemType.group,
      scores: {
        if (overallScore != null) 'overall_score': overallScore,
        if (relevanceScore != null) 'relevance_score': relevanceScore,
        if (explanationScore != null) 'explanation_score': explanationScore,
        if (actionabilityScore != null)
          'actionability_score': actionabilityScore,
        if (interestMatchScore != null)
          'interest_match_score': interestMatchScore,
        if (activityScore != null) 'activity_score': activityScore,
        if (atmosphereScore != null) 'atmosphere_score': atmosphereScore,
      },
      positiveSignals: selectedStrengths ?? const [],
      negativeSignals: [
        ...?selectedIssues,
        if ((freeText ?? '').contains(zh ? '标签不准' : 'inaccurate tags'))
          'want_more_tag_match',
      ],
      featureBoosts: {
        'tag_score':
            interestMatchScore != null && interestMatchScore <= 2 ? 1.12 : 1.06,
        'activity': activityScore != null && activityScore <= 2 ? 1.08 : 1.03,
      },
    );
  }

  @override
  Future<List<RecommendationFeedbackPrompt>> getRecommendationFeedbackPrompts({
    RecommendationItemType? itemType,
    int limit = 20,
  }) async {
    final prompts = itemType == null
        ? _mockFeedbackPrompts
        : _mockFeedbackPrompts
            .where((prompt) => prompt.itemType == itemType)
            .toList();
    return prompts.take(limit).toList();
  }

  @override
  Future<List<RecommendationFeedbackInsight>>
      getRecommendationFeedbackInsights({
    RecommendationItemType? itemType,
    int days = 30,
  }) async {
    if (itemType != null) {
      final insight = _mockFeedbackInsights[itemType];
      return insight == null ? const [] : [insight];
    }
    return _mockFeedbackInsights.values.toList();
  }

  @override
  Future<List<GroupMemberInfo>> getGroupMembers(String groupId) async {
    final group = _mockGroups.where((g) => g.id == groupId).firstOrNull;
    if (group == null) return [];
    final roles = [GroupRole.member, GroupRole.member, GroupRole.member, GroupRole.admin];
    final members = <GroupMemberInfo>[];
    for (int i = 0; i < _mockUsers.length && members.length < group.memberCount; i++) {
      final user = _mockUsers[i];
      final role = user.id == currentUserId ? (group.myRole ?? GroupRole.member) : roles[i % roles.length];
      members.add(GroupMemberInfo(
        user: user,
        role: role,
        flameContribution: 100 + i * 50,
        tasksCompleted: 5 + i * 3,
        checkinStreak: i < 3 ? 3 + i : 0,
        joinedAt: DateTime.now().subtract(Duration(days: 10 - i)),
        lastActiveAt: DateTime.now().subtract(Duration(hours: i)),
      ));
    }
    return members;
  }

  GroupInfo _rebuildGroup(GroupInfo group, {
    int? memberCount,
    GroupRole? myRole,
  }) {
    return GroupInfo(
      id: group.id,
      name: group.name,
      description: group.description,
      avatarUrl: group.avatarUrl,
      type: group.type,
      focusTags: group.focusTags,
      memberCount: memberCount ?? group.memberCount,
      totalFlamePower: group.totalFlamePower,
      todayCheckinCount: group.todayCheckinCount,
      totalTasksCompleted: group.totalTasksCompleted,
      maxMembers: group.maxMembers,
      isPublic: group.isPublic,
      joinRequiresApproval: group.joinRequiresApproval,
      createdAt: group.createdAt,
      updatedAt: DateTime.now(),
      deadline: group.deadline,
      sprintGoal: group.sprintGoal,
      announcement: group.announcement,
      myRole: myRole,
    );
  }

  @override
  Future<void> kickMember(String groupId, String userId) async {
    final index = _mockGroups.indexWhere((g) => g.id == groupId);
    if (index == -1) return;
    final group = _mockGroups[index];
    _mockGroups[index] = _rebuildGroup(
      group,
      memberCount: group.memberCount > 0 ? group.memberCount - 1 : 0,
      myRole: userId == currentUserId ? null : group.myRole,
    );
  }

  @override
  Future<void> promoteMember(String groupId, String userId) async {
    final index = _mockGroups.indexWhere((g) => g.id == groupId);
    if (index == -1) return;
    final group = _mockGroups[index];
    _mockGroups[index] = _rebuildGroup(
      group,
      myRole: userId == currentUserId ? GroupRole.admin : group.myRole,
    );
  }

  @override
  Future<void> demoteMember(String groupId, String userId) async {
    final index = _mockGroups.indexWhere((g) => g.id == groupId);
    if (index == -1) return;
    final group = _mockGroups[index];
    _mockGroups[index] = _rebuildGroup(
      group,
      myRole: userId == currentUserId ? GroupRole.member : group.myRole,
    );
  }

  @override
  Future<void> transferOwnership(String groupId, String userId) async {
    final index = _mockGroups.indexWhere((g) => g.id == groupId);
    if (index == -1) return;
    final group = _mockGroups[index];
    _mockGroups[index] = _rebuildGroup(
      group,
      myRole: userId == currentUserId ? GroupRole.owner : GroupRole.member,
    );
  }

  @override
  Future<UserBrief> getUserProfile(String userId) async =>
      UserBrief(id: userId, username: 'mock_user');

  void _updateInsight(
    RecommendationItemType itemType, {
    required Map<String, int> scores,
    required List<String> positiveSignals,
    required List<String> negativeSignals,
    required Map<String, double> featureBoosts,
    Map<String, double> strategyBoosts = const {},
  }) {
    final current = _mockFeedbackInsights[itemType];
    if (current == null) return;

    final currentCount = current.recentFeedbackCount;
    final nextCount = currentCount + 1;
    final mergedScores = <String, double>{...current.averageScores};
    scores.forEach((key, value) {
      final oldValue = current.averageScores[key] ?? value.toDouble();
      mergedScores[key] =
          ((oldValue * currentCount) + value.toDouble()) / nextCount;
    });

    final mergedUserTuning = <String, dynamic>{...current.userTuning};
    final currentFeatures = Map<String, dynamic>.from(
      mergedUserTuning['feature_weights'] as Map? ?? const {},
    );
    featureBoosts.forEach((key, value) {
      currentFeatures[key] = value;
    });
    mergedUserTuning['feature_weights'] = currentFeatures;
    if (strategyBoosts.isNotEmpty) {
      final currentStrategies = Map<String, dynamic>.from(
        mergedUserTuning['strategy_bias'] as Map? ?? const {},
      );
      strategyBoosts.forEach((key, value) {
        currentStrategies[key] = value;
      });
      mergedUserTuning['strategy_bias'] = currentStrategies;
    }

    _mockFeedbackInsights[itemType] = RecommendationFeedbackInsight(
      itemType: itemType,
      recentFeedbackCount: nextCount,
      averageScores: mergedScores,
      topPositiveSignals: _mergeSignals(
        current.topPositiveSignals,
        positiveSignals,
      ),
      topNegativeSignals: _mergeSignals(
        current.topNegativeSignals,
        negativeSignals,
      ),
      userTuning: mergedUserTuning,
      globalAdjustments: current.globalAdjustments,
    );
  }

  List<String> _mergeSignals(List<String> existing, List<String> incoming) {
    final merged = <String>[
      ...incoming.where((item) => item.trim().isNotEmpty),
      ...existing,
    ];
    final seen = <String>{};
    return merged.where((item) => seen.add(item)).take(5).toList();
  }

  @override
  Future<FriendProfileDetail> getFriendProfile(String userId) async =>
      FriendProfileDetail(
        user: UserBrief(
          id: userId,
          username: 'mock_user',
          nickname: 'Mock Partner',
        ),
        friendship: {
          'id': 'friendship_$userId',
          'status': 'accepted',
          'initiated_by_me': false,
          'created_at': DateTime.now().toIso8601String(),
        },
        accountability: userId == 'user_alice'
            ? const {
                'id': 'demo_core_partner',
                'partnership_id': 'demo_core_partner',
                'status': 'active',
                'slot_type': 'core',
              }
            : userId == 'user_charlie'
                ? const {
                    'id': 'demo_pending_partner',
                    'partnership_id': 'demo_pending_partner',
                    'status': 'pending',
                    'slot_type': 'core',
                  }
                : const {},
        relationshipSummary: {
          'partner_name': 'Mock Partner',
          'days_together': 12,
          'my_streak_days': 5,
          'partner_streak_days': 4,
        },
        achievementsSummary: const {
          'my_total_unlocked': 2,
          'partner_total_unlocked': 1,
        },
        leaderboardSummary: const {},
        quickActions: {
          'can_invite_accountability': false,
          'can_open_dashboard': userId == 'user_alice',
          'can_chat': true,
          'can_share': true,
        },
      );

  @override
  Future<void> updateAnnouncement(String groupId, String? announcement) async {
    return;
  }

  // ── Phase 1: Message Favorites ─────────────────────────────────────────────

  @override
  Future<void> addFavorite(
    String? groupMessageId,
    String? privateMessageId, {
    String? note,
    List<String>? tags,
  }) async {}

  @override
  Future<List<MessageFavoriteInfo>> getFavorites({
    String? tag,
    int limit = 20,
    int offset = 0,
  }) async =>
      [];

  @override
  Future<void> removeFavorite(String favoriteId) async {}

  // ── Phase 1: Message Forward ───────────────────────────────────────────────

  @override
  Future<void> forwardMessage(
    String messageId,
    String sourceType, {
    String? targetGroupId,
    String? targetUserId,
    String? comment,
  }) async {}

  // ── Phase 1: Message Report ────────────────────────────────────────────────

  @override
  Future<void> reportMessage(
    String messageId,
    ReportReason reason, {
    String? description,
  }) async {
    _mockReports.add({
      'messageId': messageId,
      'reason': reason,
      'description': description,
    });
  }

  // ── Phase 2a: Group Member Moderation ─────────────────────────────────────

  @override
  Future<void> muteMember(
    String groupId,
    String userId,
    int durationMinutes, {
    String? reason,
  }) async {}

  @override
  Future<void> unmuteMember(String groupId, String userId) async {}

  @override
  Future<void> warnMember(
    String groupId,
    String userId,
    String reason,
  ) async {}

  // ── Phase 2b: Group Moderation Settings ───────────────────────────────────

  @override
  Future<GroupModerationSettings> getModerationSettings(
    String groupId,
  ) async =>
      const GroupModerationSettings();

  @override
  Future<void> updateModerationSettings(
    String groupId,
    GroupModerationSettings settings,
  ) async {}

  // ── Phase 2d: Complete Task ────────────────────────────────────────────────

  @override
  Future<void> completeTask(String taskId) async {
    for (final tasks in _mockGroupTasks.values) {
      final idx = tasks.indexWhere((t) => t.id == taskId);
      if (idx != -1) {
        tasks[idx] = GroupTaskInfo(
          id: tasks[idx].id,
          title: tasks[idx].title,
          description: tasks[idx].description,
          tags: tasks[idx].tags,
          estimatedMinutes: tasks[idx].estimatedMinutes,
          difficulty: tasks[idx].difficulty,
          totalClaims: tasks[idx].totalClaims,
          totalCompletions: tasks[idx].totalCompletions + 1,
          completionRate: (tasks[idx].totalCompletions + 1) /
              (tasks[idx].totalClaims > 0 ? tasks[idx].totalClaims : 1),
          dueDate: tasks[idx].dueDate,
          creator: tasks[idx].creator,
          isClaimedByMe: tasks[idx].isClaimedByMe,
          myCompletionStatus: true,
          createdAt: tasks[idx].createdAt,
          updatedAt: DateTime.now(),
        );
        return;
      }
    }
  }

  // ── Phase 4: Friend Management ─────────────────────────────────────────────

  @override
  Future<void> deleteFriend(String friendshipId) async {
    _mockFriends.removeWhere((f) => f.id == friendshipId);
  }

  @override
  Future<void> blockUser(String targetUserId, {String? reason}) async {
    // Remove from friends if present
    _mockFriends.removeWhere((f) => f.friend.id == targetUserId);
  }

  @override
  Future<void> unblockUser(String userId) async {
    // Mock implementation - no-op
  }

  @override
  Future<List<BlockUserInfo>> getBlockedUsers({
    int limit = 50,
    int offset = 0,
  }) async {
    // Return empty list for mock
    return [];
  }

  // ── Privacy Settings ──────────────────────────────────────────────────────

  @override
  Future<UserPrivacySettings> getPrivacySettings() async =>
      UserPrivacySettings(searchableBy: SearchVisibility.everyone);

  @override
  Future<void> updatePrivacySettings(UserPrivacySettings settings) async {
    // Mock implementation - no-op
  }

  // ── Broadcast ──────────────────────────────────────────────────────────────

  @override
  Future<BroadcastMessageInfo> createBroadcast(
    BroadcastMessageCreate request,
  ) async =>
      BroadcastMessageInfo(
        id: const Uuid().v4(),
        senderId: currentUserId,
        content: request.content,
        contentData: request.contentData,
        targetGroupIds: request.targetGroupIds,
        deliveredCount: request.targetGroupIds.length,
        createdAt: DateTime.now(),
      );

  // ── Offline Queue ──────────────────────────────────────────────────────────

  @override
  Future<List<OfflineMessageInfo>> getPendingOfflineMessages() async => [];

  @override
  Future<List<OfflineMessageInfo>> getFailedOfflineMessages() async => [];

  @override
  Future<void> retryOfflineMessages(List<String> messageIds) async {
    // Mock implementation - no-op
  }

  // ── Encryption Keys ────────────────────────────────────────────────────────

  @override
  Future<EncryptionKeyInfo> registerEncryptionKey(
    EncryptionKeyCreate request,
  ) async =>
      EncryptionKeyInfo(
        id: const Uuid().v4(),
        userId: currentUserId,
        publicKey: request.publicKey,
        keyType: request.keyType,
        deviceId: request.deviceId,
        isActive: true,
        createdAt: DateTime.now(),
        expiresAt: request.expiresAt,
      );

  @override
  Future<List<EncryptionKeyInfo>> getUserPublicKeys(String userId) async => [];

  @override
  Future<void> revokeEncryptionKey(String keyId) async {
    // Mock implementation - no-op
  }

  // ── Group Files ────────────────────────────────────────────────────────────

  @override
  Future<List<GroupFileInfo>> getGroupFiles(
    String groupId, {
    String? category,
    int limit = 50,
    int offset = 0,
  }) async =>
      [];

  @override
  Future<GroupFileInfo> shareFileToGroup(
    String groupId,
    GroupFileShareRequest request,
  ) async =>
      GroupFileInfo(
        id: const Uuid().v4(),
        groupId: groupId,
        uploaderId: currentUserId,
        fileName: 'mock_file.pdf',
        fileSize: 1024,
        mimeType: 'application/pdf',
        fileUrl: 'https://example.com/mock_file.pdf',
        description: request.description,
        category: request.category,
        tags: request.tags,
        permissions: GroupFilePermissions(),
        createdAt: DateTime.now(),
      );

  @override
  Future<GroupFileInfo> updateGroupFilePermissions(
    String groupId,
    String fileId,
    GroupFilePermissionUpdate permissions,
  ) async =>
      GroupFileInfo(
        id: fileId,
        groupId: groupId,
        uploaderId: currentUserId,
        fileName: 'mock_file.pdf',
        fileSize: 1024,
        mimeType: 'application/pdf',
        fileUrl: 'https://example.com/mock_file.pdf',
        permissions: GroupFilePermissions(
          canView: permissions.canView ?? [],
          canDownload: permissions.canDownload ?? [],
          canDelete: permissions.canDelete ?? [],
        ),
        createdAt: DateTime.now(),
      );

  @override
  Future<List<GroupFileCategoryStat>> getGroupFileCategories(
    String groupId,
  ) async =>
      [];

  // ── Shared Resources ───────────────────────────────────────────────────────

  @override
  Future<SharedResourceInfo> shareResource(
          SharedResourceCreate request) async =>
      SharedResourceInfo(
        id: const Uuid().v4(),
        resourceType: request.resourceType,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
        taskId: request.resourceType == SharedResourceType.task
            ? request.resourceId
            : null,
        planId: request.resourceType == SharedResourceType.plan
            ? request.resourceId
            : null,
      );

  @override
  Future<List<SharedResourceInfo>> getGroupResources(
    String groupId, {
    SharedResourceType? type,
    int limit = 50,
    int offset = 0,
  }) async =>
      [];

  @override
  Future<void> adoptSharedResource(String shareId) async {
    // Mock implementation - no-op
  }

  // ── Message Reports Management ─────────────────────────────────────────────

  @override
  Future<List<MessageReportInfo>> getPendingReports(String groupId) async => [];

  @override
  Future<MessageReportInfo> reviewReport(
    String reportId,
    MessageReportReview review,
  ) async =>
      MessageReportInfo(
        id: reportId,
        reporterId: currentUserId,
        reason: ReportReason.other,
        status: review.status,
        createdAt: DateTime.now(),
        reviewedBy: currentUserId,
        reviewedAt: DateTime.now(),
        actionTaken: review.actionTaken,
      );

  // ── Group File Library Copy ────────────────────────────────────────────────

  @override
  Future<void> copyFileToMyLibrary(String groupId, String fileId) async {
    // Mock implementation - no-op
  }
}
