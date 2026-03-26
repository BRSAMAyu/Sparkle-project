// ignore_for_file: use_setters_to_change_properties, cascade_invocations

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/features/community/data/models/community_models.dart';
import 'package:sparkle/features/knowledge/data/models/knowledge_detail_model.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import 'package:uuid/uuid.dart';

class _DemoDomainProfile {
  const _DemoDomainProfile({
    required this.domainId,
    required this.displayName,
    required this.goalTheme,
    required this.taskTags,
    required this.contentTone,
    required this.priorityRole,
  });

  final String domainId;
  final String displayName;
  final String goalTheme;
  final List<String> taskTags;
  final String contentTone;
  final String priorityRole;
}

class _DemoTouchpointProfile {
  const _DemoTouchpointProfile({
    required this.touchpointId,
    required this.displayName,
    required this.storyline,
    required this.anchorTags,
    required this.signal,
  });

  final String touchpointId;
  final String displayName;
  final String storyline;
  final List<String> anchorTags;
  final String signal;
}

const List<_DemoDomainProfile> _demoDomainProfiles = [
  _DemoDomainProfile(
    domainId: 'Academic',
    displayName: '理工学业',
    goalTheme: '稳住课程理解，把抽象概念变成可复述的结构',
    taskTags: ['Academic', 'Math', 'Science', 'Coursework'],
    contentTone: 'structured',
    priorityRole: 'primary',
  ),
  _DemoDomainProfile(
    domainId: 'Language',
    displayName: '语言表达',
    goalTheme: '提升英语输入输出，让表达更自然、更有组织',
    taskTags: ['Language', 'English', 'Speaking', 'Writing'],
    contentTone: 'expressive',
    priorityRole: 'primary',
  ),
  _DemoDomainProfile(
    domainId: 'Creative',
    displayName: '艺术创作',
    goalTheme: '用摄影、写作和策展练习稳定输出审美判断',
    taskTags: ['Creative', 'Photography', 'Writing', 'Design'],
    contentTone: 'playful',
    priorityRole: 'secondary',
  ),
  _DemoDomainProfile(
    domainId: 'Humanities',
    displayName: '阅读反思',
    goalTheme: '通过阅读、记录和讨论建立更完整的理解框架',
    taskTags: ['Humanities', 'Reading', 'Reflection', 'Society'],
    contentTone: 'reflective',
    priorityRole: 'secondary',
  ),
  _DemoDomainProfile(
    domainId: 'Wellness',
    displayName: '健康节律',
    goalTheme: '先把睡眠、运动和恢复节律拉稳，再谈高强度冲刺',
    taskTags: ['Wellness', 'Exercise', 'Sleep', 'Recovery'],
    contentTone: 'grounding',
    priorityRole: 'support',
  ),
  _DemoDomainProfile(
    domainId: 'Career',
    displayName: '职业探索',
    goalTheme: '用作品集、表达训练和信息访谈连接长期方向',
    taskTags: ['Career', 'Portfolio', 'Interview', 'Planning'],
    contentTone: 'pragmatic',
    priorityRole: 'primary',
  ),
];

const List<_DemoTouchpointProfile> _demoTouchpointProfiles = [
  _DemoTouchpointProfile(
    touchpointId: 'Certification',
    displayName: '考证用户',
    storyline: '会把阶段考试、口语计时和错题回看揉进日常节奏里。',
    anchorTags: ['Exam Prep', 'Speaking', 'Review', 'Routine'],
    signal: '重视阶段目标和计时练习',
  ),
  _DemoTouchpointProfile(
    touchpointId: 'Creator',
    displayName: '内容创作者',
    storyline: '会在创作、选题、发布节奏和作品集整理之间来回切换。',
    anchorTags: ['Creative', 'Portfolio', 'Writing', 'Photography'],
    signal: '需要持续输出和素材整理',
  ),
  _DemoTouchpointProfile(
    touchpointId: 'CareerTransition',
    displayName: '求职转型用户',
    storyline: '会频繁梳理可迁移能力、信息访谈和作品集叙事。',
    anchorTags: ['Career', 'Portfolio', 'Interview', 'Planning'],
    signal: '在探索方向与构建叙事之间反复校准',
  ),
  _DemoTouchpointProfile(
    touchpointId: 'SportsRecovery',
    displayName: '运动恢复型用户',
    storyline: '更在意恢复、睡眠和负荷管理，不再只看打卡数量。',
    anchorTags: ['Wellness', 'Recovery', 'Sleep', 'Mobility'],
    signal: '会把恢复动作视为主任务的一部分',
  ),
];

class DemoDataService {
  factory DemoDataService() => _instance;
  DemoDataService._internal();
  static bool isDemoMode = false;

  static final DemoDataService _instance = DemoDataService._internal();

  final _uuid = const Uuid();
  final DateTime _snapshotAnchor = DateTime.now();

  String? _currentAvatarUrl;
  List<TaskModel>? _demoTasksCache;
  GalaxyGraphResponse? _demoGalaxyCache;
  List<PlanModel>? _demoPlansCache;
  List<ChatMessageModel>? _demoChatHistoryCache;
  Map<String, dynamic>? _demoDashboardCache;
  List<CuriosityCapsuleModel>? _demoCuriosityCapsulesCache;
  List<AchievementModel>? _demoAchievementsCache;
  List<Post>? _demoCommunityPostsCache;
  List<Map<String, dynamic>>? _demoFocusSessionsCache;
  List<Map<String, dynamic>>? _demoErrorRecordsCache;
  List<BehaviorPatternModel>? _demoBehaviorPatternsCache;
  List<Map<String, dynamic>>? _demoNotificationsCache;
  List<Map<String, dynamic>>? _demoFriendsCache;
  List<Map<String, dynamic>>? _demoAccountabilityPartnersCache;
  List<Map<String, dynamic>>? _demoGroupsCache;
  List<Map<String, dynamic>>? _demoGroupMessagesCache;
  List<Map<String, dynamic>>? _demoVisualElementsCache;
  List<Map<String, dynamic>>? _demoAchievementDetailsCache;
  List<Map<String, dynamic>>? _demoAccountabilityHeatmapCache;
  List<Map<String, dynamic>>? _demoCheckinsCache;

  static const String demoUserId = 'CS_Sophomore_12345';
  static const String demoUsername = 'AI_Learner_02';
  static const String demoAvatarSeed = 'AI_Learner_02';

  final Map<String, _DemoDomainProfile> _domainProfileById = {
    for (final profile in _demoDomainProfiles) profile.domainId: profile,
  };
  // --- User Data ---
  UserModel get demoUser => UserModel(
        id: demoUserId,
        username: demoUsername,
        email: 'learner@sparkle.ai',
        nickname: 'Mika',
        avatarUrl: _currentAvatarUrl ??
            'https://api.dicebear.com/9.x/avataaars/png?seed=$demoAvatarSeed',
        flameLevel: 15,
        flameBrightness: 0.85,
        depthPreference: 0.7,
        curiosityPreference: 0.8,
        isActive: true,
        createdAt: _snapshotAnchor.subtract(const Duration(days: 45)),
        updatedAt: _snapshotAnchor,
        pushPreferences: PushPreferences(),
      );

  void updateDemoAvatar(String url) {
    _currentAvatarUrl = url;
  }

  void resetDemoState() {
    _currentAvatarUrl = null;
    _demoTasksCache = null;
    _demoGalaxyCache = null;
    _demoPlansCache = null;
    _demoChatHistoryCache = null;
    _demoDashboardCache = null;
    _demoCuriosityCapsulesCache = null;
    _demoAchievementsCache = null;
    _demoCommunityPostsCache = null;
    _demoFocusSessionsCache = null;
    _demoErrorRecordsCache = null;
    _demoBehaviorPatternsCache = null;
    _demoNotificationsCache = null;
    _demoFriendsCache = null;
    _demoAccountabilityPartnersCache = null;
    _demoGroupsCache = null;
    _demoGroupMessagesCache = null;
    _demoVisualElementsCache = null;
    _demoAchievementDetailsCache = null;
    _demoAccountabilityHeatmapCache = null;
    _demoCheckinsCache = null;
  }

  DateTime get _now => _snapshotAnchor;

  String _nodeIdByName(List<GalaxyNodeModel> nodes, String name) =>
      nodes.firstWhere((node) => node.name == name).id;

  _DemoDomainProfile _domainProfile(String domainId) =>
      _domainProfileById[domainId]!;

  static const Map<String, List<String>> _nodeSemanticAliases = {
    '高等数学': ['Academic', 'Math', 'Calculus', 'Exam Prep'],
    '线性代数': ['Academic', 'Math', 'Linear Algebra'],
    '概率论与数理统计': ['Academic', 'Statistics', 'Problem Set'],
    '摄影艺术': ['Creative', 'Photography', 'Portfolio', 'Creator'],
    '设计思维': ['Creative', 'Career', 'Portfolio', 'Planning'],
    '文学鉴赏': ['Humanities', 'Reading', 'Writing'],
    '写作表达': ['Language', 'Writing', 'Creator'],
    '心理学导论': ['Humanities', 'Wellness', 'Reflection'],
    '管理学基础': ['Career', 'Planning', 'CareerTransition'],
    '经济学原理': ['Humanities', 'Career', 'Reading'],
    '生理学': ['Wellness', 'Recovery', 'SportsRecovery'],
    '营养学': ['Wellness', 'Recovery', 'Sleep'],
    '运动科学': ['Wellness', 'Exercise', 'Recovery', 'SportsRecovery'],
    '批判性思维': ['Humanities', 'Reading', 'Reflection'],
    '设计思维与创新': ['Creative', 'Career', 'Creator'],
    '学习方法论': ['Academic', 'Language', 'Review', 'Certification'],
    '程序设计基础': ['Academic', 'Career', 'Problem Solving'],
    '机器学习': ['Academic', 'Career', 'Project'],
  };

  TaskModel _buildDemoTask({
    required String title,
    required String domainId,
    required TaskType type,
    required TaskStatus status,
    required int estimatedMinutes,
    required int difficulty,
    required int energyCost,
    required int priority,
    required DateTime createdAt,
    required DateTime updatedAt,
    DateTime? dueDate,
    DateTime? startedAt,
    DateTime? completedAt,
    int? actualMinutes,
    String? userNote,
    List<String> extraTags = const [],
  }) {
    final profile = _domainProfile(domainId);
    return TaskModel(
      id: _uuid.v4(),
      userId: demoUserId,
      title: title,
      type: type,
      tags: [domainId, ...profile.taskTags, ...extraTags],
      estimatedMinutes: estimatedMinutes,
      difficulty: difficulty,
      energyCost: energyCost,
      status: status,
      priority: priority,
      dueDate: dueDate,
      startedAt: startedAt,
      completedAt: completedAt,
      actualMinutes: actualMinutes,
      userNote: userNote,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
  }

  Set<String> _semanticTokensForNode(GalaxyNodeModel node) {
    final tokens = <String>{
      node.name,
      ...?node.tags,
      ...?_nodeSemanticAliases[node.name],
    };
    final description = node.description ?? '';
    for (final token in [
      'Academic',
      'Language',
      'Creative',
      'Humanities',
      'Wellness',
      'Career',
      'Math',
      'Statistics',
      'Photography',
      'Writing',
      'Reading',
      'Recovery',
      'Portfolio',
      'Interview',
      'Exam Prep',
    ]) {
      if (description.toLowerCase().contains(token.toLowerCase())) {
        tokens.add(token);
      }
    }
    return tokens;
  }

  Set<String> _domainIdsForNode(GalaxyNodeModel node) {
    switch (node.sector) {
      case SectorEnum.cosmos:
        return {'Academic'};
      case SectorEnum.tech:
        return {'Academic', 'Career'};
      case SectorEnum.art:
        return {'Creative', 'Language'};
      case SectorEnum.civilization:
        return {'Humanities', 'Career'};
      case SectorEnum.life:
        return {'Wellness'};
      case SectorEnum.wisdom:
        return {'Humanities', 'Wellness', 'Language'};
      case SectorEnum.voidSector:
        return {'Humanities'};
    }
  }

  int _matchTextScore(String text, Iterable<String> keywords) {
    final lowerText = text.toLowerCase();
    var score = 0;
    for (final keyword in keywords) {
      if (lowerText.contains(keyword.toLowerCase())) {
        score += keyword.length > 6 ? 4 : 2;
      }
    }
    return score;
  }

  int _taskScoreForNode(
    TaskModel task,
    GalaxyNodeModel node,
    Set<String> nodeDomains,
    Set<String> semanticTokens,
  ) {
    var score = _matchTextScore(task.title, semanticTokens);
    score += _matchTextScore(task.tags.join(' '), semanticTokens);
    for (final domain in nodeDomains) {
      if (task.tags.contains(domain)) score += 5;
    }
    if (task.status == TaskStatus.inProgress) score += 3;
    if (task.status == TaskStatus.pending) score += 2;
    if (task.status == TaskStatus.completed) score += 1;
    if (task.dueDate != null &&
        task.dueDate!.isAfter(_now.subtract(const Duration(days: 1)))) {
      score += 1;
    }
    if (node.name.contains('写作') && task.tags.contains('Writing')) score += 4;
    if (node.name.contains('摄影') && task.tags.contains('Photography'))
      score += 4;
    if (node.name.contains('统计') && task.tags.contains('Statistics'))
      score += 4;
    if (node.name.contains('运动') && task.tags.contains('Recovery')) score += 4;
    return score;
  }

  int _planScoreForNode(
    PlanModel plan,
    GalaxyNodeModel node,
    Set<String> nodeDomains,
    Set<String> semanticTokens,
  ) {
    final planTasks = plan.tasks ?? const <TaskModel>[];
    final text =
        '${plan.name} ${plan.description ?? ''} ${plan.subject ?? ''} ${planTasks.map((task) => task.title).join(' ')}';
    var score = _matchTextScore(text, semanticTokens);
    for (final domain in nodeDomains) {
      if (planTasks.any((task) => task.tags.contains(domain))) score += 5;
    }
    if (plan.isActive) score += 3;
    if (plan.priority == PlanPriority.high) score += 1;
    if (node.name.contains('摄影') &&
        planTasks.any((task) => task.tags.contains('Photography'))) {
      score += 4;
    }
    if (node.name.contains('管理') &&
        planTasks.any((task) => task.tags.contains('Career'))) {
      score += 4;
    }
    return score;
  }

  // --- Task Data ---
  List<TaskModel> get demoTasks {
    if (_demoTasksCache != null) return _demoTasksCache!;
    final now = _now;
    final tasks = [
      _buildDemoTask(
        title: '理工课复盘 - 用自己的话讲清楚积分换元',
        domainId: 'Academic',
        type: TaskType.learning,
        status: TaskStatus.inProgress,
        estimatedMinutes: 75,
        difficulty: 4,
        energyCost: 4,
        priority: 3,
        dueDate: now,
        startedAt: now.subtract(const Duration(minutes: 35)),
        createdAt: now.subtract(const Duration(days: 1)),
        updatedAt: now,
        extraTags: const ['Calculus', 'Exam Prep'],
      ),
      _buildDemoTask(
        title: '理工练习 - 统计学抽样误差题组',
        domainId: 'Academic',
        type: TaskType.training,
        status: TaskStatus.pending,
        estimatedMinutes: 85,
        difficulty: 4,
        energyCost: 4,
        priority: 3,
        dueDate: now.add(const Duration(days: 2)),
        createdAt: now.subtract(const Duration(days: 2)),
        updatedAt: now.subtract(const Duration(hours: 9)),
        extraTags: const ['Statistics', 'Problem Set'],
      ),
      _buildDemoTask(
        title: '理工总结 - 线性代数错题回看',
        domainId: 'Academic',
        type: TaskType.reflection,
        status: TaskStatus.completed,
        estimatedMinutes: 50,
        difficulty: 2,
        energyCost: 2,
        priority: 2,
        dueDate: now.subtract(const Duration(days: 3)),
        completedAt: now.subtract(const Duration(days: 3)),
        actualMinutes: 55,
        createdAt: now.subtract(const Duration(days: 7)),
        updatedAt: now.subtract(const Duration(days: 3)),
        userNote: '把总是漏写条件的地方圈出来了，下次先审题再动笔。',
        extraTags: const ['Linear Algebra', 'Review'],
      ),
      _buildDemoTask(
        title: '语言输出 - 口语话题卡 2 轮跟说',
        domainId: 'Language',
        type: TaskType.training,
        status: TaskStatus.pending,
        estimatedMinutes: 35,
        difficulty: 2,
        energyCost: 1,
        priority: 2,
        dueDate: now.add(const Duration(days: 1)),
        createdAt: now.subtract(const Duration(days: 3)),
        updatedAt: now.subtract(const Duration(hours: 10)),
        extraTags: const ['Speaking', 'Shadowing'],
      ),
      _buildDemoTask(
        title: '语言输入 - 精读一篇城市更新英文评论',
        domainId: 'Language',
        type: TaskType.learning,
        status: TaskStatus.inProgress,
        estimatedMinutes: 45,
        difficulty: 3,
        energyCost: 2,
        priority: 2,
        dueDate: now.add(const Duration(days: 3)),
        startedAt: now.subtract(const Duration(minutes: 15)),
        createdAt: now.subtract(const Duration(days: 1)),
        updatedAt: now,
        extraTags: const ['Reading', 'Vocabulary'],
      ),
      _buildDemoTask(
        title: '语言表达 - 改写上周英语自我介绍',
        domainId: 'Language',
        type: TaskType.reflection,
        status: TaskStatus.completed,
        estimatedMinutes: 40,
        difficulty: 2,
        energyCost: 1,
        priority: 1,
        dueDate: now.subtract(const Duration(days: 4)),
        completedAt: now.subtract(const Duration(days: 4)),
        actualMinutes: 42,
        createdAt: now.subtract(const Duration(days: 6)),
        updatedAt: now.subtract(const Duration(days: 4)),
        userNote: '句子更短以后自然很多，不再一味追求复杂句。',
        extraTags: const ['Writing', 'Self Intro'],
      ),
      _buildDemoTask(
        title: '考证计时 - 口语 Part 2 计时练习',
        domainId: 'Language',
        type: TaskType.training,
        status: TaskStatus.pending,
        estimatedMinutes: 20,
        difficulty: 2,
        energyCost: 1,
        priority: 2,
        dueDate: now.add(const Duration(days: 2)),
        createdAt: now.subtract(const Duration(days: 2)),
        updatedAt: now.subtract(const Duration(hours: 5)),
        extraTags: const ['Certification', 'Exam Prep', 'Speaking'],
      ),
      _buildDemoTask(
        title: '创作输出 - 拍一组“傍晚通勤”主题照片',
        domainId: 'Creative',
        type: TaskType.training,
        status: TaskStatus.pending,
        estimatedMinutes: 60,
        difficulty: 2,
        energyCost: 2,
        priority: 1,
        dueDate: now.add(const Duration(days: 2)),
        createdAt: now.subtract(const Duration(days: 4)),
        updatedAt: now.subtract(const Duration(hours: 6)),
        extraTags: const ['Photography', 'Street'],
      ),
      _buildDemoTask(
        title: '创作整理 - 为作品集挑选 6 张最稳定的照片',
        domainId: 'Creative',
        type: TaskType.planning,
        status: TaskStatus.pending,
        estimatedMinutes: 55,
        difficulty: 3,
        energyCost: 2,
        priority: 2,
        dueDate: now.add(const Duration(days: 5)),
        createdAt: now.subtract(const Duration(days: 5)),
        updatedAt: now.subtract(const Duration(hours: 12)),
        extraTags: const ['Portfolio', 'Editing'],
      ),
      _buildDemoTask(
        title: '创作复盘 - 给旧文章补一个更清晰的开头',
        domainId: 'Creative',
        type: TaskType.reflection,
        status: TaskStatus.completed,
        estimatedMinutes: 30,
        difficulty: 2,
        energyCost: 1,
        priority: 1,
        dueDate: now.subtract(const Duration(days: 2)),
        completedAt: now.subtract(const Duration(days: 2)),
        actualMinutes: 33,
        createdAt: now.subtract(const Duration(days: 5)),
        updatedAt: now.subtract(const Duration(days: 2)),
        userNote: '删掉了太用力的形容词，画面感反而更清楚。',
        extraTags: const ['Writing', 'Editing'],
      ),
      _buildDemoTask(
        title: '创作者触点 - 整理一周选题碎片',
        domainId: 'Creative',
        type: TaskType.planning,
        status: TaskStatus.inProgress,
        estimatedMinutes: 35,
        difficulty: 2,
        energyCost: 1,
        priority: 1,
        dueDate: now.add(const Duration(days: 1)),
        startedAt: now.subtract(const Duration(minutes: 12)),
        createdAt: now.subtract(const Duration(days: 3)),
        updatedAt: now,
        extraTags: const ['Creator', 'Content Planning', 'Writing'],
      ),
      _buildDemoTask(
        title: '阅读反思 - 读《置身事内》并记 3 条问题',
        domainId: 'Humanities',
        type: TaskType.learning,
        status: TaskStatus.pending,
        estimatedMinutes: 70,
        difficulty: 3,
        energyCost: 2,
        priority: 2,
        dueDate: now.add(const Duration(days: 4)),
        createdAt: now.subtract(const Duration(days: 2)),
        updatedAt: now.subtract(const Duration(hours: 7)),
        extraTags: const ['Economy', 'Reading Notes'],
      ),
      _buildDemoTask(
        title: '阅读反思 - 整理本周的“我为什么会拖延”摘录',
        domainId: 'Humanities',
        type: TaskType.reflection,
        status: TaskStatus.inProgress,
        estimatedMinutes: 25,
        difficulty: 2,
        energyCost: 1,
        priority: 1,
        dueDate: now.add(const Duration(days: 1)),
        startedAt: now.subtract(const Duration(minutes: 10)),
        createdAt: now.subtract(const Duration(days: 1)),
        updatedAt: now,
        extraTags: const ['Reflection', 'Journal'],
      ),
      _buildDemoTask(
        title: '阅读反思 - 完成一篇短评《夜晚的潜水艇》',
        domainId: 'Humanities',
        type: TaskType.training,
        status: TaskStatus.completed,
        estimatedMinutes: 50,
        difficulty: 3,
        energyCost: 2,
        priority: 1,
        dueDate: now.subtract(const Duration(days: 5)),
        completedAt: now.subtract(const Duration(days: 5)),
        actualMinutes: 62,
        createdAt: now.subtract(const Duration(days: 8)),
        updatedAt: now.subtract(const Duration(days: 5)),
        userNote: '先写感受再补论证，比一开始就追求完整顺手很多。',
        extraTags: const ['Literature', 'Review'],
      ),
      _buildDemoTask(
        title: '健康节律 - 晚上 11:30 前关屏',
        domainId: 'Wellness',
        type: TaskType.planning,
        status: TaskStatus.pending,
        estimatedMinutes: 15,
        difficulty: 1,
        energyCost: 1,
        priority: 3,
        dueDate: now,
        createdAt: now.subtract(const Duration(days: 6)),
        updatedAt: now.subtract(const Duration(hours: 2)),
        extraTags: const ['Sleep', 'Routine'],
      ),
      _buildDemoTask(
        title: '健康节律 - 午后拉伸和 20 分钟散步',
        domainId: 'Wellness',
        type: TaskType.social,
        status: TaskStatus.completed,
        estimatedMinutes: 20,
        difficulty: 1,
        energyCost: 1,
        priority: 2,
        dueDate: now.subtract(const Duration(days: 1)),
        completedAt: now.subtract(const Duration(days: 1)),
        actualMinutes: 24,
        createdAt: now.subtract(const Duration(days: 1)),
        updatedAt: now.subtract(const Duration(days: 1)),
        extraTags: const ['Recovery', 'Walking'],
      ),
      _buildDemoTask(
        title: '健康节律 - 周末早餐后轻量瑜伽',
        domainId: 'Wellness',
        type: TaskType.training,
        status: TaskStatus.pending,
        estimatedMinutes: 25,
        difficulty: 1,
        energyCost: 1,
        priority: 1,
        dueDate: now.add(const Duration(days: 4)),
        createdAt: now.subtract(const Duration(days: 3)),
        updatedAt: now.subtract(const Duration(days: 1)),
        extraTags: const ['Mobility', 'Weekend'],
      ),
      _buildDemoTask(
        title: '运动恢复 - 下肢力量日后的拉伸记录',
        domainId: 'Wellness',
        type: TaskType.reflection,
        status: TaskStatus.completed,
        estimatedMinutes: 18,
        difficulty: 1,
        energyCost: 1,
        priority: 1,
        dueDate: now.subtract(const Duration(days: 2)),
        completedAt: now.subtract(const Duration(days: 2)),
        actualMinutes: 20,
        createdAt: now.subtract(const Duration(days: 2)),
        updatedAt: now.subtract(const Duration(days: 2)),
        userNote: '左腿后侧比想象中更紧，恢复日还是得留出来。',
        extraTags: const ['SportsRecovery', 'Recovery', 'Mobility'],
      ),
      _buildDemoTask(
        title: '职业探索 - 更新跨领域作品集首页',
        domainId: 'Career',
        type: TaskType.planning,
        status: TaskStatus.pending,
        estimatedMinutes: 80,
        difficulty: 3,
        energyCost: 3,
        priority: 3,
        dueDate: now.add(const Duration(days: 6)),
        createdAt: now.subtract(const Duration(days: 4)),
        updatedAt: now.subtract(const Duration(hours: 8)),
        extraTags: const ['Portfolio', 'Personal Brand'],
      ),
      _buildDemoTask(
        title: '职业探索 - 写一封信息访谈邀请邮件',
        domainId: 'Career',
        type: TaskType.training,
        status: TaskStatus.inProgress,
        estimatedMinutes: 40,
        difficulty: 3,
        energyCost: 2,
        priority: 2,
        dueDate: now.add(const Duration(days: 2)),
        startedAt: now.subtract(const Duration(minutes: 20)),
        createdAt: now.subtract(const Duration(days: 2)),
        updatedAt: now,
        extraTags: const ['Networking', 'Email'],
      ),
      _buildDemoTask(
        title: '职业探索 - 整理一次模拟面试后的追问清单',
        domainId: 'Career',
        type: TaskType.reflection,
        status: TaskStatus.completed,
        estimatedMinutes: 35,
        difficulty: 2,
        energyCost: 1,
        priority: 2,
        dueDate: now.subtract(const Duration(days: 2)),
        completedAt: now.subtract(const Duration(days: 2)),
        actualMinutes: 30,
        createdAt: now.subtract(const Duration(days: 4)),
        updatedAt: now.subtract(const Duration(days: 2)),
        userNote: '我对“为什么是你”回答得还不够具体，下次要带项目例子。',
        extraTags: const ['Interview', 'Reflection'],
      ),
      _buildDemoTask(
        title: '转型梳理 - 写出 3 条可迁移能力证据',
        domainId: 'Career',
        type: TaskType.reflection,
        status: TaskStatus.pending,
        estimatedMinutes: 30,
        difficulty: 3,
        energyCost: 2,
        priority: 2,
        dueDate: now.add(const Duration(days: 3)),
        createdAt: now.subtract(const Duration(days: 4)),
        updatedAt: now.subtract(const Duration(hours: 4)),
        extraTags: const ['CareerTransition', 'Portfolio', 'Reflection'],
      ),
    ];
    _demoTasksCache = tasks;
    return tasks;
  }

  // --- Galaxy Data ---
  GalaxyGraphResponse get demoGalaxy {
    if (_demoGalaxyCache != null) return _demoGalaxyCache!;
    final nodes = <GalaxyNodeModel>[];
    final edges = <GalaxyEdgeModel>[];
    var nodeId = 0;

    // 🌌 COSMOS 星域 - 自然科学基础
    final cosmosNodes = _createCosmosNodes(nodeId);
    nodes.addAll(cosmosNodes);
    nodeId += cosmosNodes.length;

    // 💻 TECH 星域 - 科技与工程
    final techNodes = _createTechNodes(nodeId);
    nodes.addAll(techNodes);
    nodeId += techNodes.length;

    // 🎨 ART 星域 - 艺术与人文
    final artNodes = _createArtNodes(nodeId);
    nodes.addAll(artNodes);
    nodeId += artNodes.length;

    // 🏛️ CIVILIZATION 星域 - 社会与文明
    final civilizationNodes = _createCivilizationNodes(nodeId);
    nodes.addAll(civilizationNodes);
    nodeId += civilizationNodes.length;

    // 🌱 LIFE 星域 - 生命科学
    final lifeNodes = _createLifeNodes(nodeId);
    nodes.addAll(lifeNodes);
    nodeId += lifeNodes.length;

    // 🧠 WISDOM 星域 - 智慧与思考
    final wisdomNodes = _createWisdomNodes(nodeId);
    nodes.addAll(wisdomNodes);

    // 创建跨领域连接
    edges.addAll(_createCrossFieldEdges(nodes));

    final galaxy = GalaxyGraphResponse(
      nodes: _withReplayUnlockOrder(nodes),
      edges: edges,
      userFlameIntensity: 0.85,
    );
    _demoGalaxyCache = galaxy;
    return galaxy;
  }

  // 🌌 COSMOS - 自然科学星域
  List<GalaxyNodeModel> _createCosmosNodes(int startId) {
    var id = startId;
    return [
      // 数学基础
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '高等数学',
        description: '微积分、极限、导数、积分等基础数学知识',
        importance: 5,
        sector: SectorEnum.cosmos,
        isUnlocked: true,
        masteryScore: 85,
        studyCount: 12,
        tags: ['数学', '基础'],
        baseColor: '#2196F3',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '线性代数',
        description: '矩阵、向量空间、线性变换',
        importance: 4,
        sector: SectorEnum.cosmos,
        isUnlocked: true,
        masteryScore: 70,
        studyCount: 8,
        tags: ['数学', '线性代数'],
        baseColor: '#2196F3',
        parentId: 'node_$startId',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '概率论与数理统计',
        description: '概率、随机变量、统计推断',
        importance: 4,
        sector: SectorEnum.cosmos,
        isUnlocked: true,
        masteryScore: 60,
        studyCount: 6,
        tags: ['数学', '统计'],
        baseColor: '#2196F3',
        parentId: 'node_$startId',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '离散数学',
        description: '集合论、图论、组合数学、数理逻辑',
        importance: 4,
        sector: SectorEnum.cosmos,
        isUnlocked: true,
        masteryScore: 55,
        studyCount: 5,
        tags: ['数学', '离散'],
        baseColor: '#2196F3',
        parentId: 'node_$startId',
      ),
      // 物理
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '大学物理',
        description: '力学、电磁学、热学、光学基础',
        importance: 4,
        sector: SectorEnum.cosmos,
        isUnlocked: true,
        masteryScore: 65,
        studyCount: 7,
        tags: ['物理', '基础'],
        baseColor: '#3F51B5',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '经典力学',
        description: '牛顿力学、动量、能量',
        importance: 3,
        sector: SectorEnum.cosmos,
        isUnlocked: true,
        masteryScore: 70,
        studyCount: 5,
        tags: ['物理', '力学'],
        baseColor: '#3F51B5',
        parentId: 'node_${startId + 4}',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '电磁学基础',
        description: '电场、磁场、电磁感应',
        importance: 3,
        sector: SectorEnum.cosmos,
        isUnlocked: true,
        masteryScore: 50,
        studyCount: 4,
        tags: ['物理', '电磁'],
        baseColor: '#3F51B5',
        parentId: 'node_${startId + 4}',
      ),
      // 化学
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '普通化学',
        description: '化学反应、元素周期表、化学键',
        importance: 3,
        sector: SectorEnum.cosmos,
        isUnlocked: true,
        masteryScore: 45,
        studyCount: 3,
        tags: ['化学', '基础'],
        baseColor: '#009688',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '有机化学',
        description: '有机物结构、反应机理',
        importance: 2,
        sector: SectorEnum.cosmos,
        isUnlocked: false,
        masteryScore: 0,
        tags: ['化学', '有机'],
        baseColor: '#009688',
        parentId: 'node_${startId + 7}',
      ),
    ];
  }

  // 💻 TECH - 科技星域
  List<GalaxyNodeModel> _createTechNodes(int startId) {
    var id = startId;
    return [
      // 编程基础
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '程序设计基础',
        description: '变量、控制流、函数、基本算法',
        importance: 5,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 90,
        studyCount: 15,
        tags: ['编程', '基础'],
        baseColor: '#4CAF50',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: 'Python编程',
        description: 'Python语法、数据结构、面向对象',
        importance: 4,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 80,
        studyCount: 10,
        tags: ['Python', '编程'],
        baseColor: '#4CAF50',
        parentId: 'node_$startId',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: 'C/C++编程',
        description: 'C语言基础、指针、C++面向对象',
        importance: 4,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 75,
        studyCount: 9,
        tags: ['C++', '编程'],
        baseColor: '#4CAF50',
        parentId: 'node_$startId',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: 'Java编程',
        description: 'Java语法、OOP、集合框架',
        importance: 4,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 70,
        studyCount: 8,
        tags: ['Java', '编程'],
        baseColor: '#4CAF50',
        parentId: 'node_$startId',
      ),
      // 数据结构与算法
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '数据结构',
        description: '线性表、栈、队列、树、图',
        importance: 5,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 85,
        studyCount: 12,
        tags: ['数据结构', '算法'],
        baseColor: '#8BC34A',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '算法设计与分析',
        description: '排序、搜索、动态规划、贪心算法',
        importance: 5,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 70,
        studyCount: 8,
        tags: ['算法', '优化'],
        baseColor: '#8BC34A',
        parentId: 'node_${startId + 4}',
      ),
      // 计算机系统
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '计算机组成原理',
        description: 'CPU、内存、I/O系统',
        importance: 4,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 65,
        studyCount: 7,
        tags: ['计算机系统', '硬件'],
        baseColor: '#FFC107',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '操作系统',
        description: '进程、内存管理、文件系统',
        importance: 5,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 60,
        studyCount: 6,
        tags: ['操作系统', 'OS'],
        baseColor: '#FFC107',
        parentId: 'node_${startId + 6}',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '计算机网络',
        description: 'TCP/IP、HTTP、网络协议',
        importance: 4,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 55,
        studyCount: 5,
        tags: ['网络', '协议'],
        baseColor: '#FF9800',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '数据库系统',
        description: 'SQL、关系模型、事务处理',
        importance: 4,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 70,
        studyCount: 8,
        tags: ['数据库', 'SQL'],
        baseColor: '#FF9800',
      ),
      // Web开发
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: 'Web前端开发',
        description: 'HTML、CSS、JavaScript基础',
        importance: 3,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 60,
        studyCount: 6,
        tags: ['Web', '前端'],
        baseColor: '#00BCD4',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: 'Web后端开发',
        description: 'RESTful API、服务器开发',
        importance: 3,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 50,
        studyCount: 4,
        tags: ['Web', '后端'],
        baseColor: '#00BCD4',
      ),
      // AI/ML
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '人工智能基础',
        description: '机器学习、神经网络入门',
        importance: 4,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 40,
        studyCount: 3,
        tags: ['AI', '机器学习'],
        baseColor: '#9C27B0',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '机器学习',
        description: '监督学习、非监督学习、模型评估',
        importance: 4,
        sector: SectorEnum.tech,
        isUnlocked: false,
        masteryScore: 0,
        tags: ['机器学习', 'ML'],
        baseColor: '#9C27B0',
        parentId: 'node_${startId + 12}',
      ),
    ];
  }

  // 🎨 ART - 艺术星域
  List<GalaxyNodeModel> _createArtNodes(int startId) {
    var id = startId;
    return [
      // 文学
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '中国文学',
        description: '古代文学、现代文学、诗词赏析',
        importance: 4,
        sector: SectorEnum.art,
        isUnlocked: true,
        masteryScore: 75,
        studyCount: 9,
        tags: ['文学', '中国'],
        baseColor: '#E91E63',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '外国文学',
        description: '西方文学、世界文学经典',
        importance: 3,
        sector: SectorEnum.art,
        isUnlocked: true,
        masteryScore: 60,
        studyCount: 6,
        tags: ['文学', '外国'],
        baseColor: '#E91E63',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '写作技巧',
        description: '议论文、说明文、创意写作',
        importance: 3,
        sector: SectorEnum.art,
        isUnlocked: true,
        masteryScore: 65,
        studyCount: 7,
        tags: ['写作', '技巧'],
        baseColor: '#E91E63',
      ),
      // 艺术
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '美术基础',
        description: '素描、色彩、构图',
        importance: 2,
        sector: SectorEnum.art,
        isUnlocked: true,
        masteryScore: 45,
        studyCount: 4,
        tags: ['美术', '绘画'],
        baseColor: '#F06292',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '音乐欣赏',
        description: '音乐史、乐理、作品欣赏',
        importance: 2,
        sector: SectorEnum.art,
        isUnlocked: true,
        masteryScore: 50,
        studyCount: 5,
        tags: ['音乐', '欣赏'],
        baseColor: '#F06292',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '设计思维',
        description: 'UI/UX设计、平面设计原理',
        importance: 3,
        sector: SectorEnum.art,
        isUnlocked: true,
        masteryScore: 55,
        studyCount: 5,
        tags: ['设计', 'UI'],
        baseColor: '#EC407A',
      ),
      // 传媒
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '摄影基础',
        description: '构图、光影、后期处理',
        importance: 2,
        sector: SectorEnum.art,
        isUnlocked: true,
        masteryScore: 60,
        studyCount: 6,
        tags: ['摄影', '艺术'],
        baseColor: '#F48FB1',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '影视制作',
        description: '视频拍摄、剪辑、叙事技巧',
        importance: 2,
        sector: SectorEnum.art,
        isUnlocked: false,
        masteryScore: 0,
        tags: ['影视', '制作'],
        baseColor: '#F48FB1',
        parentId: 'node_${startId + 6}',
      ),
    ];
  }

  // 🏛️ CIVILIZATION - 文明星域
  List<GalaxyNodeModel> _createCivilizationNodes(int startId) {
    var id = startId;
    return [
      // 历史
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '中国近现代史',
        description: '辛亥革命、新中国成立、改革开放',
        importance: 4,
        sector: SectorEnum.civilization,
        isUnlocked: true,
        masteryScore: 80,
        studyCount: 10,
        tags: ['历史', '中国'],
        baseColor: '#795548',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '世界历史',
        description: '文艺复兴、工业革命、两次世界大战',
        importance: 4,
        sector: SectorEnum.civilization,
        isUnlocked: true,
        masteryScore: 70,
        studyCount: 8,
        tags: ['历史', '世界'],
        baseColor: '#795548',
      ),
      // 政治经济
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '马克思主义基本原理',
        description: '唯物辩证法、政治经济学',
        importance: 4,
        sector: SectorEnum.civilization,
        isUnlocked: true,
        masteryScore: 75,
        studyCount: 9,
        tags: ['政治', '马克思主义'],
        baseColor: '#8D6E63',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '经济学原理',
        description: '微观经济、宏观经济、市场机制',
        importance: 4,
        sector: SectorEnum.civilization,
        isUnlocked: true,
        masteryScore: 60,
        studyCount: 6,
        tags: ['经济', '市场'],
        baseColor: '#A1887F',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '管理学基础',
        description: '组织管理、领导力、战略规划',
        importance: 3,
        sector: SectorEnum.civilization,
        isUnlocked: true,
        masteryScore: 55,
        studyCount: 5,
        tags: ['管理', '组织'],
        baseColor: '#A1887F',
      ),
      // 法律社会
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '法律基础',
        description: '宪法、民法、刑法基础知识',
        importance: 3,
        sector: SectorEnum.civilization,
        isUnlocked: true,
        masteryScore: 50,
        studyCount: 4,
        tags: ['法律', '权利'],
        baseColor: '#BCAAA4',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '社会学导论',
        description: '社会结构、群体行为、社会问题',
        importance: 3,
        sector: SectorEnum.civilization,
        isUnlocked: true,
        masteryScore: 45,
        studyCount: 3,
        tags: ['社会', '群体'],
        baseColor: '#BCAAA4',
      ),
    ];
  }

  // 🌱 LIFE - 生命星域
  List<GalaxyNodeModel> _createLifeNodes(int startId) {
    var id = startId;
    return [
      // 生物
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '普通生物学',
        description: '细胞、遗传、进化、生态',
        importance: 4,
        sector: SectorEnum.life,
        isUnlocked: true,
        masteryScore: 70,
        studyCount: 8,
        tags: ['生物', '基础'],
        baseColor: '#4CAF50',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '人体生理学',
        description: '循环系统、消化系统、神经系统',
        importance: 3,
        sector: SectorEnum.life,
        isUnlocked: true,
        masteryScore: 60,
        studyCount: 6,
        tags: ['生理', '人体'],
        baseColor: '#66BB6A',
        parentId: 'node_$startId',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '基因与遗传',
        description: 'DNA、基因表达、遗传规律',
        importance: 3,
        sector: SectorEnum.life,
        isUnlocked: true,
        masteryScore: 55,
        studyCount: 5,
        tags: ['遗传', '基因'],
        baseColor: '#66BB6A',
        parentId: 'node_$startId',
      ),
      // 医学健康
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '健康与养生',
        description: '营养、运动、睡眠、疾病预防',
        importance: 3,
        sector: SectorEnum.life,
        isUnlocked: true,
        masteryScore: 75,
        studyCount: 9,
        tags: ['健康', '养生'],
        baseColor: '#81C784',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '急救与安全',
        description: 'CPR、止血、常见急症处理',
        importance: 3,
        sector: SectorEnum.life,
        isUnlocked: true,
        masteryScore: 65,
        studyCount: 7,
        tags: ['急救', '安全'],
        baseColor: '#81C784',
      ),
      // 心理
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '心理学导论',
        description: '认知、情绪、人格、行为',
        importance: 4,
        sector: SectorEnum.life,
        isUnlocked: true,
        masteryScore: 70,
        studyCount: 8,
        tags: ['心理', '认知'],
        baseColor: '#AED581',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '发展心理学',
        description: '儿童、青少年、成人心理发展',
        importance: 3,
        sector: SectorEnum.life,
        isUnlocked: true,
        masteryScore: 50,
        studyCount: 4,
        tags: ['心理', '发展'],
        baseColor: '#AED581',
        parentId: 'node_${startId + 5}',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '社会心理学',
        description: '态度、说服、群体影响',
        importance: 3,
        sector: SectorEnum.life,
        isUnlocked: true,
        masteryScore: 45,
        studyCount: 3,
        tags: ['心理', '社会'],
        baseColor: '#AED581',
        parentId: 'node_${startId + 5}',
      ),
    ];
  }

  // 🧠 WISDOM - 智慧星域
  List<GalaxyNodeModel> _createWisdomNodes(int startId) {
    var id = startId;
    return [
      // 哲学
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '哲学导论',
        description: '形而上学、认识论、伦理学',
        importance: 4,
        sector: SectorEnum.wisdom,
        isUnlocked: true,
        masteryScore: 65,
        studyCount: 7,
        tags: ['哲学', '思考'],
        baseColor: '#673AB7',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '中国哲学',
        description: '儒家、道家、佛家思想',
        importance: 3,
        sector: SectorEnum.wisdom,
        isUnlocked: true,
        masteryScore: 60,
        studyCount: 6,
        tags: ['哲学', '中国'],
        baseColor: '#7E57C2',
        parentId: 'node_$startId',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '西方哲学',
        description: '古希腊哲学、近代哲学、现代哲学',
        importance: 3,
        sector: SectorEnum.wisdom,
        isUnlocked: true,
        masteryScore: 55,
        studyCount: 5,
        tags: ['哲学', '西方'],
        baseColor: '#7E57C2',
        parentId: 'node_$startId',
      ),
      // 思维方法
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '批判性思维',
        description: '逻辑推理、论证分析、谬误识别',
        importance: 5,
        sector: SectorEnum.wisdom,
        isUnlocked: true,
        masteryScore: 70,
        studyCount: 8,
        tags: ['思维', '逻辑'],
        baseColor: '#9575CD',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '创新思维',
        description: '发散思维、联想、头脑风暴',
        importance: 4,
        sector: SectorEnum.wisdom,
        isUnlocked: true,
        masteryScore: 60,
        studyCount: 6,
        tags: ['思维', '创新'],
        baseColor: '#9575CD',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '系统思维',
        description: '整体观、反馈循环、涌现特性',
        importance: 4,
        sector: SectorEnum.wisdom,
        isUnlocked: true,
        masteryScore: 50,
        studyCount: 4,
        tags: ['思维', '系统'],
        baseColor: '#9575CD',
      ),
      // 学习方法
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '学习科学',
        description: '记忆原理、遗忘曲线、刻意练习',
        importance: 5,
        sector: SectorEnum.wisdom,
        isUnlocked: true,
        masteryScore: 80,
        studyCount: 10,
        tags: ['学习', '科学'],
        baseColor: '#B39DDB',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '时间管理',
        description: '优先级、番茄工作法、GTD',
        importance: 4,
        sector: SectorEnum.wisdom,
        isUnlocked: true,
        masteryScore: 75,
        studyCount: 9,
        tags: ['管理', '时间'],
        baseColor: '#B39DDB',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '元认知',
        description: '自我监控、学习策略、反思',
        importance: 4,
        sector: SectorEnum.wisdom,
        isUnlocked: true,
        masteryScore: 65,
        studyCount: 7,
        tags: ['认知', '元认知'],
        baseColor: '#B39DDB',
      ),
      // 沟通表达
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '有效沟通',
        description: '倾听、表达、非暴力沟通',
        importance: 4,
        sector: SectorEnum.wisdom,
        isUnlocked: true,
        masteryScore: 70,
        studyCount: 8,
        tags: ['沟通', '表达'],
        baseColor: '#D1C4E9',
      ),
      GalaxyNodeModel(
        id: 'node_${id++}',
        name: '演讲技巧',
        description: '结构设计、肢体语言、克服紧张',
        importance: 3,
        sector: SectorEnum.wisdom,
        isUnlocked: true,
        masteryScore: 55,
        studyCount: 5,
        tags: ['演讲', '技巧'],
        baseColor: '#D1C4E9',
        parentId: 'node_${startId + 9}',
      ),
    ];
  }

  // 创建跨领域连接
  List<GalaxyEdgeModel> _createCrossFieldEdges(List<GalaxyNodeModel> nodes) {
    final edges = <GalaxyEdgeModel>[];
    var edgeId = 0;
    final nodeId = _nodeIdByName;

    // 数学 -> 算法（前置知识）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: nodeId(nodes, '高等数学'),
        targetId: nodeId(nodes, '算法设计与分析'),
        relationType: EdgeRelationType.prerequisite,
        strength: 0.9,
      ),
    );

    // 概率论 -> 机器学习（前置知识）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: nodeId(nodes, '概率论与数理统计'),
        targetId: nodeId(nodes, '机器学习'),
        relationType: EdgeRelationType.prerequisite,
        strength: 0.9,
      ),
    );

    // 线性代数 -> 机器学习（前置知识）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: nodeId(nodes, '线性代数'),
        targetId: nodeId(nodes, '机器学习'),
        relationType: EdgeRelationType.prerequisite,
        strength: 0.8,
      ),
    );

    // 心理学 -> 设计思维（相关知识）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: nodeId(nodes, '心理学导论'),
        targetId: nodeId(nodes, '设计思维'),
        strength: 0.7,
      ),
    );

    // 批判性思维 -> 编程（应用）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: nodeId(nodes, '批判性思维'),
        targetId: nodeId(nodes, '程序设计基础'),
        relationType: EdgeRelationType.application,
        strength: 0.6,
      ),
    );

    // 经济学 -> 管理学（衍生知识）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: nodeId(nodes, '经济学原理'),
        targetId: nodeId(nodes, '管理学基础'),
        relationType: EdgeRelationType.derived,
        strength: 0.8,
      ),
    );

    return edges;
  }

  /// Get demo node detail for a specific node ID
  KnowledgeDetailResponse getDemoNodeDetail(String nodeId) {
    // Find the node in our galaxy
    final galaxyNodes = demoGalaxy.nodes;
    final node = _findDemoNodeById(galaxyNodes, nodeId);
    if (node == null) {
      throw Exception('当前节点不存在或已被清理，请返回星图后重试');
    }

    // Get related nodes through edges
    final edges = demoGalaxy.edges;
    final relations = edges
        .where((e) => e.sourceId == nodeId || e.targetId == nodeId)
        .map((e) {
          final isSource = e.sourceId == nodeId;
          final relatedNodeId = isSource ? e.targetId : e.sourceId;
          final relatedNode = _findDemoNodeById(galaxyNodes, relatedNodeId);
          if (relatedNode == null ||
              !_isRenderableDemoNodeName(relatedNode.name)) {
            return null;
          }

          return NodeRelation(
            id: e.id,
            sourceNodeId: e.sourceId,
            targetNodeId: e.targetId,
            relationType: e.relationType.toString().split('.').last,
            strength: e.strength,
            sourceNodeName: isSource ? node.name : relatedNode.name,
            targetNodeName: isSource ? relatedNode.name : node.name,
          );
        })
        .whereType<NodeRelation>()
        .toList();

    // Determine sector code string
    final sectorCode = node.sector.toString().split('.').last.toUpperCase();
    final nodeDomains = _domainIdsForNode(node);
    final semanticTokens = _semanticTokensForNode(node);
    final relatedTasks = [...demoTasks]..sort(
        (a, b) => _taskScoreForNode(b, node, nodeDomains, semanticTokens)
            .compareTo(_taskScoreForNode(a, node, nodeDomains, semanticTokens)),
      );
    final relatedPlans = [...demoPlans]..sort(
        (a, b) => _planScoreForNode(b, node, nodeDomains, semanticTokens)
            .compareTo(_planScoreForNode(a, node, nodeDomains, semanticTokens)),
      );

    return KnowledgeDetailResponse(
      node: KnowledgeNodeDetail(
        id: node.id,
        name: node.name,
        nameEn: node.name,
        description: node.description ?? '${node.name}的详细介绍和知识点说明。',
        keywords: node.tags ?? [],
        importanceLevel: node.importance,
        sectorCode: sectorCode,
        isSeed: node.importance >= 4,
        sourceType: node.importance >= 4 ? 'seed' : 'llm_expanded',
        parentId: node.parentId,
        subjectId: node.sector.index + 1,
        subjectName: node.name,
        createdAt: DateTime.now().subtract(Duration(days: node.studyCount * 2)),
      ),
      relations: relations,
      relatedTasks: relatedTasks.take(3).toList(),
      relatedPlans: relatedPlans
          .take(3)
          .map(
            (p) => RelatedPlan(
              id: p.id,
              title: p.name,
              planType: p.type.toString().split('.').last,
              status: p.isActive ? 'active' : 'completed',
              targetDate: p.targetDate,
            ),
          )
          .toList(),
      userStats: KnowledgeUserStats(
        masteryScore: node.masteryScore.toDouble(),
        totalStudyMinutes: node.studyCount * 15,
        studyCount: node.studyCount,
        isUnlocked: node.isUnlocked,
        isFavorite: node.studyCount % 7 == 0,
        lastStudyAt: node.studyCount > 0
            ? _now.subtract(Duration(days: node.studyCount % 7))
            : null,
        nextReviewAt: node.masteryScore > 0 && node.masteryScore < 80
            ? _now.add(Duration(days: node.studyCount % 3 + 1))
            : null,
        decayPaused: node.studyCount % 10 == 0,
      ),
    );
  }

  List<GalaxyNodeModel> _withReplayUnlockOrder(List<GalaxyNodeModel> nodes) {
    final replayBase = DateTime(2026, 1, 3, 9);
    var unlockedOffset = 0;
    var lockedOffset = nodes.where((node) => node.isUnlocked).length;

    return nodes.map((node) {
      if (node.firstUnlockAt != null) {
        return node;
      }
      final offset = node.isUnlocked ? unlockedOffset++ : lockedOffset++;
      return node.copyWith(
        firstUnlockAt: replayBase.add(Duration(seconds: offset * 8)),
      );
    }).toList(growable: false);
  }

  bool _isRenderableDemoNodeName(String name) {
    final trimmed = name.trim();
    if (trimmed.isEmpty) {
      return false;
    }
    if (trimmed.contains('�')) {
      return false;
    }
    if (RegExp(r'^J\d', caseSensitive: false).hasMatch(trimmed)) {
      return false;
    }
    return !RegExp(r'^[?？·•\-_=\s]+$').hasMatch(trimmed);
  }

  GalaxyNodeModel? _findDemoNodeById(
    List<GalaxyNodeModel> nodes,
    String nodeId,
  ) {
    for (final node in nodes) {
      if (node.id == nodeId) {
        return node;
      }
    }
    return null;
  }

  // --- Plan Data ---
  List<PlanModel> get demoPlans => _demoPlansCache ??= _buildDemoPlans();

  List<PlanModel> _buildDemoPlans() {
    final now = DateTime.now();
    final growthCoreTasks = [
      _buildPlanTask(
        id: 'plan_growth_core_task_1',
        title: '把积分换元的典型题型整理成一页笔记',
        planId: 'plan_growth_1',
        createdAt: now.subtract(const Duration(days: 9)),
        updatedAt: now.subtract(const Duration(days: 2)),
        estimatedMinutes: 50,
        difficulty: 3,
        type: TaskType.learning,
        status: TaskStatus.completed,
        actualMinutes: 55,
        userNote: '这次先按“什么时候用”来分类，比按公式抄写更容易记住。',
        tags: const ['Academic', 'Calculus', 'Knowledge Map'],
      ),
      _buildPlanTask(
        id: 'plan_growth_core_task_2',
        title: '完成统计学抽样误差错题回看',
        planId: 'plan_growth_1',
        createdAt: now.subtract(const Duration(days: 5)),
        updatedAt: now.subtract(const Duration(hours: 12)),
        estimatedMinutes: 40,
        difficulty: 4,
        type: TaskType.training,
        status: TaskStatus.inProgress,
        dueDate: now.add(const Duration(days: 2)),
        tags: const ['Academic', 'Statistics', 'Error Review'],
      ),
      _buildPlanTask(
        id: 'plan_growth_core_task_3',
        title: '补齐本周课堂里没听稳的线性代数前置概念',
        planId: 'plan_growth_1',
        createdAt: now.subtract(const Duration(days: 2)),
        updatedAt: now.subtract(const Duration(hours: 6)),
        estimatedMinutes: 35,
        difficulty: 2,
        type: TaskType.learning,
        status: TaskStatus.pending,
        dueDate: now.add(const Duration(days: 4)),
        tags: const ['Academic', 'Linear Algebra', 'Prerequisites'],
      ),
    ];
    return [
      PlanModel(
        id: 'plan_sprint_1',
        userId: demoUserId,
        name: '本周复合学习节奏校准',
        type: PlanType.sprint,
        dailyAvailableMinutes: 120,
        masteryLevel: 0.6,
        progress: 0.68,
        isActive: true,
        createdAt: now.subtract(const Duration(days: 5)),
        updatedAt: now,
        targetDate: now.add(const Duration(days: 7)),
        description: '把白天的高认知任务、晚间语言复盘和睡前降速动作重新排顺。',
        totalEstimatedHours: 20,
        tasks: demoTasks
            .where(
              (task) =>
                  task.tags.contains('Academic') ||
                  task.tags.contains('Language') ||
                  task.tags.contains('Wellness'),
            )
            .take(4)
            .toList(),
      ),
      PlanModel(
        id: 'plan_growth_1',
        userId: demoUserId,
        name: '学业理解力主线',
        type: PlanType.growth,
        dailyAvailableMinutes: 60,
        masteryLevel: 0.48,
        progress: 0.45,
        isActive: true,
        createdAt: now.subtract(const Duration(days: 30)),
        updatedAt: now,
        targetDate: now.add(const Duration(days: 90)),
        description: '稳住理工课程的基础盘，把错题和课堂概念逐步串成可复述的结构。',
        totalEstimatedHours: 100,
        planStage: PlanStage.daily,
        priority: PlanPriority.high,
        tasks: growthCoreTasks,
      ),
      PlanModel(
        id: 'plan_growth_2',
        userId: demoUserId,
        name: '语言与表达升级',
        type: PlanType.growth,
        dailyAvailableMinutes: 45,
        masteryLevel: 0.42,
        progress: 0.34,
        isActive: true,
        createdAt: now.subtract(const Duration(days: 18)),
        updatedAt: now.subtract(const Duration(hours: 4)),
        targetDate: now.add(const Duration(days: 45)),
        description: '通过精读、跟说和短文改写，把语言输入转成更自然的输出。',
        totalEstimatedHours: 48,
        subject: '语言表达',
        planStage: PlanStage.daily,
        tasks: demoTasks
            .where((task) => task.tags.contains('Language'))
            .take(3)
            .toList(),
      ),
      PlanModel(
        id: 'plan_growth_archived',
        userId: demoUserId,
        name: '恢复与复盘习惯回炉',
        type: PlanType.growth,
        dailyAvailableMinutes: 35,
        masteryLevel: 0.8,
        progress: 1.0,
        isActive: false,
        createdAt: now.subtract(const Duration(days: 60)),
        updatedAt: now.subtract(const Duration(days: 15)),
        targetDate: now.subtract(const Duration(days: 3)),
        description: '已完成的睡眠与周复盘习惯回炉计划，可在历史记录中查看。',
        totalEstimatedHours: 24,
        subject: '健康节律',
        planStage: PlanStage.review,
        tasks: demoTasks
            .where(
              (task) =>
                  task.tags.contains('Wellness') ||
                  task.tags.contains('Humanities'),
            )
            .take(3)
            .toList(),
      ),
    ];
  }

  TaskModel _buildPlanTask({
    required String id,
    required String title,
    required String planId,
    required DateTime createdAt,
    required DateTime updatedAt,
    required int estimatedMinutes,
    required int difficulty,
    required TaskType type,
    required TaskStatus status,
    List<String> tags = const [],
    DateTime? dueDate,
    int? actualMinutes,
    String? userNote,
  }) =>
      TaskModel(
        id: id,
        userId: demoUser.id,
        planId: planId,
        title: title,
        type: type,
        tags: tags,
        estimatedMinutes: estimatedMinutes,
        difficulty: difficulty,
        energyCost: difficulty >= 4 ? 4 : 2,
        status: status,
        priority: difficulty >= 4 ? 3 : 2,
        createdAt: createdAt,
        updatedAt: updatedAt,
        dueDate: dueDate,
        actualMinutes: actualMinutes,
        userNote: userNote,
      );

  // --- Chat Data (保留真实LLM功能，只展示历史记录) ---
  List<ChatMessageModel> get demoChatHistory {
    if (_demoChatHistoryCache != null) return _demoChatHistoryCache!;
    final now = _now;
    _demoChatHistoryCache = [
      ChatMessageModel(
        id: 'msg_1',
        conversationId: 'demo_conv_1',
        role: MessageRole.user,
        content: '我最近白天能学进去，但一到晚上就很想逃避输出任务，尤其是英语口语和复盘。',
        createdAt: now.subtract(const Duration(hours: 2)),
      ),
      ChatMessageModel(
        id: 'msg_2',
        conversationId: 'demo_conv_1',
        role: MessageRole.assistant,
        content:
            '这更像是“白天把高能量都花掉了，晚上只剩下对输出的心理负担”。可以把晚上任务改成两段：先做 10 分钟低门槛跟说，再做 10 分钟复盘，而不是一口气要求自己讲完整段内容。',
        createdAt: now.subtract(const Duration(hours: 1, minutes: 59)),
      ),
      ChatMessageModel(
        id: 'msg_3',
        conversationId: 'demo_conv_1',
        role: MessageRole.user,
        content: '那我今晚是不是可以先做“口语话题卡 2 轮跟说”，再补一句中文反思？',
        createdAt: now.subtract(const Duration(minutes: 30)),
      ),
      ChatMessageModel(
        id: 'msg_4',
        conversationId: 'demo_conv_1',
        role: MessageRole.assistant,
        content: '可以，这样的组合很适合你当前的晚间状态。我已经按“低门槛开场 + 简短复盘”帮你重排了今晚动作。',
        createdAt: now.subtract(const Duration(minutes: 29)),
        toolResults: [
          ToolResultModel(
            success: true,
            toolName: 'generate_plan',
            data: {'status': 'completed'},
          ),
        ],
      ),
      ChatMessageModel(
        id: 'msg_5',
        conversationId: 'demo_conv_1',
        role: MessageRole.assistant,
        content: '''
今晚的顺序建议：

1. 先做 10 分钟跟说，目标只有“张嘴”
2. 再用 8 分钟写下今天最卡的一句表达
3. 最后补 5 分钟感受记录，判断是累还是怕出错

你现在不是缺努力，而是需要更温和的起步阻力。''',
        createdAt: now.subtract(const Duration(minutes: 28)),
      ),
      ChatMessageModel(
        id: 'msg_6',
        conversationId: 'demo_conv_2',
        role: MessageRole.user,
        content: '我想把一段英文自我介绍说得更自然，但一紧张就只会背稿子。',
        createdAt: now.subtract(const Duration(days: 1)),
      ),
      ChatMessageModel(
        id: 'msg_7',
        conversationId: 'demo_conv_2',
        role: MessageRole.assistant,
        content: '''
更自然的关键不是“背得更熟”，而是给每一句一个真实意图。

- 第一段只负责打招呼和定位自己
- 第二段只说最近在做什么
- 第三段补一个具体例子

你可以先用关键词提纲练习，而不是整段背诵。这样卡住时也更容易换种说法。''',
        createdAt: now.subtract(const Duration(days: 1)),
      ),
      ChatMessageModel(
        id: 'msg_8',
        conversationId: 'demo_conv_3',
        role: MessageRole.user,
        content: '我拍了几张傍晚通勤的照片，但总觉得画面很满，不知道问题出在哪。',
        createdAt: now.subtract(const Duration(days: 2)),
      ),
      ChatMessageModel(
        id: 'msg_9',
        conversationId: 'demo_conv_3',
        role: MessageRole.assistant,
        content: '''
先别急着追求“丰富”，你这组图更像是缺一个明确主角。

你可以试试这三个检查点：

- 画面里最亮的区域是不是你真正想强调的
- 边缘有没有抢戏的杂物
- 视线能不能在 2 秒内落到主题上

如果你愿意，我可以按你常拍的风格给你一套“通勤街景”取舍清单。''',
        createdAt: now.subtract(const Duration(days: 2)),
      ),
      ChatMessageModel(
        id: 'msg_10',
        conversationId: 'demo_conv_4',
        role: MessageRole.user,
        content: '为什么我周末一睡晚，整个周日都会觉得脑子很钝？',
        createdAt: now.subtract(const Duration(days: 3)),
      ),
      ChatMessageModel(
        id: 'msg_11',
        conversationId: 'demo_conv_4',
        role: MessageRole.assistant,
        content: '''
睡晚之后觉得“整天都钝”，通常不只是睡眠时长问题，而是节律被整体推迟了。

- 起床变晚，第一餐和出门时间也一起后移
- 白天活动量下降，大脑更难进入清醒状态
- 到了晚上又不够困，形成循环

所以周末更适合保留固定起床时间，把任务改轻，而不是彻底打乱节奏。''',
        createdAt: now.subtract(const Duration(days: 3)),
      ),
      ChatMessageModel(
        id: 'msg_12',
        conversationId: 'demo_conv_5',
        role: MessageRole.user,
        content: '我对以后做什么还没有完全确定，作品集是不是也可以先做成“过程型”的？',
        createdAt: now.subtract(const Duration(days: 4)),
      ),
      ChatMessageModel(
        id: 'msg_13',
        conversationId: 'demo_conv_5',
        role: MessageRole.assistant,
        content: '''
完全可以。对你这种跨领域用户来说，过程型作品集反而更真实。

建议首页先放三类内容：

- 课程或项目里解决过的问题
- 语言或写作里能体现表达能力的片段
- 你持续做过的创作与复盘痕迹

它不需要先证明“我已经定型”，而是先证明“我有连续成长的轨迹”。''',
        createdAt: now.subtract(const Duration(days: 3)),
      ),
    ];
    return _demoChatHistoryCache!;
  }

  // --- Dashboard Data ---
  Map<String, dynamic> get demoDashboard {
    if (_demoDashboardCache != null) return _demoDashboardCache!;
    final tasks = demoTasks;
    final sprint = demoPlans.firstWhere((plan) => plan.id == 'plan_sprint_1');
    final growth = demoPlans.firstWhere((plan) => plan.id == 'plan_growth_1');
    _demoDashboardCache = {
      'weather': {
        'type': 'sunny',
        'condition': 'Clear sky',
      },
      'flame': {
        'level': 15,
        'brightness': 85,
        'today_focus_minutes': 120,
        'tasks_completed':
            tasks.where((task) => task.status == TaskStatus.completed).length,
        'nudge_message': '你今天已经完成了理工复盘和语言热身，晚上更适合做轻一点的表达与整理。',
      },
      'sprint': {
        'id': sprint.id,
        'name': sprint.name,
        'progress': sprint.progress,
        'days_left': sprint.targetDate == null
            ? 0
            : sprint.targetDate!.difference(_now).inDays,
        'total_estimated_hours': sprint.totalEstimatedHours ?? 20.0,
      },
      'growth': {
        'id': growth.id,
        'name': growth.name,
        'progress': growth.progress,
        'mastery_level': growth.masteryLevel,
      },
      'audience_touchpoints': _demoTouchpointProfiles
          .map(
            (profile) => {
              'id': profile.touchpointId,
              'label': profile.displayName,
              'storyline': profile.storyline,
              'signal': profile.signal,
            },
          )
          .toList(),
      'next_actions': tasks
          .where((task) => task.status != TaskStatus.completed)
          .take(3)
          .map(
            (task) => {
              'id': task.id,
              'title': task.title,
              'estimated_minutes': task.estimatedMinutes,
              'priority': task.priority,
              'type': task.type.name,
            },
          )
          .toList(),
      'cognitive': {
        'weekly_pattern': 'Balanced Growth',
        'pattern_type': 'productive',
        'description': '你在下午 3-5 点适合推进高认知任务，晚上 8-9 点更适合语言复盘与阅读整理。',
        'solution_text': '下午处理理工与职业任务，晚上保留给语言、反思和轻量恢复动作。',
        'status': 'analyzed',
        'has_new_insight': true,
      },
    };
    return _demoDashboardCache!;
  }

  // --- 🎓 认知胶囊 Data ---
  List<CuriosityCapsuleModel> get demoCuriosityCapsules {
    if (_demoCuriosityCapsulesCache != null) {
      return _demoCuriosityCapsulesCache!;
    }
    final now = _now;
    _demoCuriosityCapsulesCache = [
      CuriosityCapsuleModel(
        id: 'capsule_1',
        title: '为什么“回忆”比反复重读更能记住内容？',
        content: '''
大脑更容易记住“被主动提取出来的信息”，而不是“看起来很熟的信息”。

当你合上笔记，尝试自己写出要点时，大脑会经历一次“检索”过程。这个过程本身就在强化记忆线路。

所以比起重复看 3 遍，更有效的做法通常是：

- 看一遍
- 合上资料回忆
- 对照缺口再补

这也是为什么你最近做“理工错题回看”时，自己先讲一遍题意会明显更稳。''',
        isRead: false,
        createdAt: now.subtract(const Duration(hours: 2)),
        relatedSubject: '学习策略',
        depthLevel: 'deep',
        generationMethod: 'knowledge_gap_analysis',
        qualityScore: 0.92,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_2',
        title: '为什么口语一紧张就会“只剩背稿感”？',
        content: '''
紧张时，大脑会优先抓住最熟的固定表达，所以整段话会显得像在“回放录音”。

想让表达更自然，关键不是再背一次整稿，而是把每一句拆成“意图卡片”：

- 这句是为了打招呼
- 这句是为了说明近况
- 这句是为了举例子

当你知道每句话在“做什么”，就更容易临场换词，而不是一停顿就整段断掉。''',
        isRead: true,
        createdAt: now.subtract(const Duration(hours: 5)),
        relatedSubject: '语言表达',
        depthLevel: 'deep',
        generationMethod: 'concept_clarification',
        qualityScore: 0.88,
        feedbackCount: 1,
        shareCount: 2,
        isFavorite: true,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_3',
        title: '摄影构图里，为什么“少一点”常常更高级？',
        content: '''
画面不耐看，很多时候不是信息太少，而是主题不够明确。

当观众在 2 秒内找不到主角，就会感到“乱”。删减的价值在于帮视线更快落到重点上。

你可以做一个简单测试：把每张照片边缘遮掉 10%，如果反而更聚焦，说明原图里有抢戏元素。''',
        isRead: true,
        createdAt: now.subtract(const Duration(days: 1)),
        relatedSubject: '摄影构图',
        depthLevel: 'medium',
        generationMethod: 'why_question',
        qualityScore: 0.85,
        shareCount: 1,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_4',
        title: '写作里为什么“删形容词”会让句子更有力？',
        content: '''
很多句子显得“用力”，不是因为内容不够，而是作者抢先替读者下了判断。

比如：

- “很震撼的晚霞” 不如 “晚霞把整条街照成铜色”

后者把感受交给画面，读者更容易自己进入情境。这也是你最近改旧文章时，删掉一些形容词后反而更顺的原因。''',
        isRead: false,
        createdAt: now.subtract(const Duration(days: 1, hours: 3)),
        relatedSubject: '写作表达',
        depthLevel: 'deep',
        generationMethod: 'learning_barrier_breakthrough',
        qualityScore: 0.90,
        isFavorite: true,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_5',
        title: '睡眠为什么会直接影响第二天的语言流畅度？',
        content: '''
语言输出需要调用词汇、语序、语气和工作记忆，这些都依赖大脑的清醒度。

睡眠不足时，你不一定完全不会，但会更容易：

- 找词慢
- 句子半途改口
- 一出错就更想停下来

这也是为什么晚睡之后，比起硬顶高压口语，不如先做精读或关键词跟说。''',
        isRead: true,
        createdAt: now.subtract(const Duration(days: 2)),
        relatedSubject: '健康节律',
        depthLevel: 'medium',
        generationMethod: 'design_rationale',
        qualityScore: 0.82,
        feedbackCount: 1,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_6',
        title: '为什么很多拖延其实是“下一步不够明确”？',
        content: '''
人通常不会无缘无故抗拒做事，而是在面对模糊任务时大脑自动选择了更轻松的替代项。

“更新作品集”很难开始，但“写首页第一段 80 字版本”就容易得多。

一旦下一步足够具体，阻力会显著下降。你最近职业探索任务推进慢，更多不是不重视，而是目标粒度还偏大。''',
        isRead: false,
        createdAt: now.subtract(const Duration(days: 2, hours: 12)),
        relatedSubject: '行动阻力',
        depthLevel: 'deep',
        generationMethod: 'concept_clarification',
        qualityScore: 0.87,
        shareCount: 1,
        isFavorite: true,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_7',
        title: '阅读时为什么“记了很多笔记”不等于真正理解？',
        content: '''
笔记只能证明你接触过材料，不能证明你已经形成了自己的判断。

真正的理解通常至少会留下三种痕迹：

- 能换种方式复述
- 能指出作者没说清的地方
- 能和自己的经历或别的学科连起来

所以你最近把阅读任务改成“记 3 条问题”是个很好的变化，它逼着你从被动记录转向主动判断。''',
        isRead: true,
        createdAt: now.subtract(const Duration(days: 3)),
        relatedSubject: '阅读理解',
        depthLevel: 'medium',
        generationMethod: 'cognitive_barrier_analysis',
        qualityScore: 0.89,
        feedbackCount: 2,
        shareCount: 3,
        isFavorite: true,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_8',
        title: '为什么跨学科学习更容易“看起来都学了，其实没沉淀”？',
        content: '''
跨学科学习最大的风险不是内容太多，而是每个领域都停留在“接触过”的表层。

避免“漂浮感”的方法是给每个领域留一个固定锚点：

- 理工靠错题和讲解
- 语言靠输出片段
- 创作靠成品挑选
- 人文靠问题和短评

这样一周结束时，你不只是“学过”，而是真的留下了可回看的痕迹。''',
        isRead: false,
        createdAt: now.subtract(const Duration(days: 3, hours: 8)),
        relatedSubject: '跨学科学习',
        depthLevel: 'deep',
        generationMethod: 'analogy_explanation',
        qualityScore: 0.91,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_9',
        title: '信息访谈里，什么问题最容易让对话真正深入？',
        content: '''
真正有效的问题往往不是“你平时做什么”，而是：

- 你是怎么进入这个方向的？
- 你最近一次明显感到成长的节点是什么？
- 如果回到学生阶段，你会更早开始补哪种能力？

它们会把对方从“职责描述”拉回到真实经验，也更适合你这种还在探索方向的人。''',
        isRead: true,
        createdAt: now.subtract(const Duration(days: 4)),
        relatedSubject: '职业探索',
        depthLevel: 'medium',
        generationMethod: 'mental_model_correction',
        qualityScore: 0.86,
        feedbackCount: 1,
        shareCount: 2,
        isFavorite: true,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_10',
        title: '为什么有时“先散步 15 分钟”比硬撑更能救回专注？',
        content: '''
当注意力已经黏住手机或疲劳感时，继续硬顶通常只会加深挫败感。

短暂散步的作用不是偷懒，而是把大脑从过载状态拉回一个更能重新启动的区间。

重点是回来以后不要直接挑战最难任务，而是先接一个 10 分钟的低门槛动作，让系统重新转起来。''',
        isRead: false,
        createdAt: now.subtract(const Duration(days: 4, hours: 15)),
        relatedSubject: '恢复策略',
        depthLevel: 'shallow',
        generationMethod: 'big_picture_connection',
        qualityScore: 0.80,
        shareCount: 1,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_11',
        title: '考证练习里，为什么“计时”会直接改变你的表达质量？',
        content: '''
很多人以为自己“内容不会”，其实真正卡住的是在时间压力下没有形成稳定节奏。

计时的价值不只是模拟考试，而是帮你发现：

- 哪一步花太久
- 哪种句式一紧张就会忘
- 什么长度才是你当前最稳的输出单位

所以对考证用户来说，计时不是最后才做的事，而是日常训练本身。''',
        isRead: false,
        createdAt: now.subtract(const Duration(days: 1, hours: 8)),
        relatedSubject: '考证训练',
        depthLevel: 'medium',
        generationMethod: 'touchpoint_adaptation',
        qualityScore: 0.84,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_12',
        title: '内容创作者为什么也需要“选题复盘”？',
        content: '''
创作不只是产出作品，也是在训练你判断“什么值得继续做”。

每周回看一次选题碎片，可以帮你看见：

- 哪些题目只是临时兴奋
- 哪些题目反复出现，说明真的在意
- 哪些内容最容易和作品集、表达、职业方向连起来

这样你累积的就不是零散灵感，而是一条慢慢成形的主线。''',
        isRead: true,
        createdAt: now.subtract(const Duration(days: 2, hours: 4)),
        relatedSubject: '内容创作',
        depthLevel: 'medium',
        generationMethod: 'touchpoint_adaptation',
        qualityScore: 0.86,
        isFavorite: true,
      ),
    ];
    return _demoCuriosityCapsulesCache!;
  }

  // --- 🏆 成就系统 Data ---
  List<AchievementModel> get demoAchievements {
    if (_demoAchievementsCache != null) return _demoAchievementsCache!;
    final now = _now;
    _demoAchievementsCache = [
      AchievementModel(
        id: 'ach_1',
        name: '初识星火',
        description: '完成第一个学习任务',
        type: AchievementType.milestone,
        rarity: AchievementRarity.common,
        iconUrl: '🎯',
        category: 'onboarding',
        createdAt: now.subtract(const Duration(days: 45)),
        updatedAt: now.subtract(const Duration(days: 45)),
        totalUnlocked: 1250,
      ),
      AchievementModel(
        id: 'ach_2',
        name: '连续学习7天',
        description: '坚持每天学习，连续7天不间断',
        type: AchievementType.streak,
        rarity: AchievementRarity.rare,
        iconUrl: '🔥',
        category: 'consistency',
        hint: '每天至少完成一个番茄钟',
        createdAt: now.subtract(const Duration(days: 30)),
        updatedAt: now.subtract(const Duration(days: 30)),
        totalUnlocked: 350,
      ),
      AchievementModel(
        id: 'ach_3',
        name: '知识探索者',
        description: '解锁50个知识节点',
        type: AchievementType.nodeExplore,
        rarity: AchievementRarity.rare,
        iconUrl: '🌟',
        category: 'knowledge',
        createdAt: now.subtract(const Duration(days: 25)),
        updatedAt: now.subtract(const Duration(days: 25)),
        totalUnlocked: 180,
      ),
      AchievementModel(
        id: 'ach_4',
        name: '深度聚焦',
        description: '单次专注时间达到2小时',
        type: AchievementType.studyTime,
        rarity: AchievementRarity.epic,
        iconUrl: '🎯',
        category: 'focus',
        visualEffectType: VisualEffectType.supernova,
        createdAt: now.subtract(const Duration(days: 20)),
        updatedAt: now.subtract(const Duration(days: 20)),
        totalUnlocked: 85,
      ),
      AchievementModel(
        id: 'ach_5',
        name: '冲刺达人',
        description: '完成第一个Sprint计划',
        type: AchievementType.sprint,
        rarity: AchievementRarity.rare,
        iconUrl: '🚀',
        category: 'planning',
        createdAt: now.subtract(const Duration(days: 15)),
        updatedAt: now.subtract(const Duration(days: 15)),
        totalUnlocked: 120,
      ),
      AchievementModel(
        id: 'ach_6',
        name: '社交之星',
        description: '在社群发布10条动态',
        type: AchievementType.social,
        rarity: AchievementRarity.common,
        iconUrl: '💬',
        category: 'community',
        createdAt: now.subtract(const Duration(days: 10)),
        updatedAt: now.subtract(const Duration(days: 10)),
        totalUnlocked: 450,
      ),
      AchievementModel(
        id: 'ach_7',
        name: '完美主义者',
        description: '单周任务完成率100%',
        type: AchievementType.taskComplete,
        rarity: AchievementRarity.epic,
        iconUrl: '✨',
        category: 'achievement',
        visualEffectType: VisualEffectType.gravityWave,
        createdAt: now.subtract(const Duration(days: 8)),
        updatedAt: now.subtract(const Duration(days: 8)),
        totalUnlocked: 45,
      ),
      AchievementModel(
        id: 'ach_8',
        name: '知识大师',
        description: '任意知识节点掌握度达到100%',
        type: AchievementType.mastery,
        rarity: AchievementRarity.epic,
        iconUrl: '👑',
        category: 'mastery',
        visualEffectType: VisualEffectType.nebulaTransform,
        createdAt: now.subtract(const Duration(days: 5)),
        updatedAt: now.subtract(const Duration(days: 5)),
        totalUnlocked: 62,
      ),
      AchievementModel(
        id: 'ach_9',
        name: '夜猫子',
        description: '在凌晨2点后仍在学习（隐藏成就）',
        type: AchievementType.hidden,
        rarity: AchievementRarity.legendary,
        iconUrl: '🦉',
        category: 'special',
        isHidden: true,
        hint: '深夜学习也要注意休息哦',
        visualEffectType: VisualEffectType.blackHole,
        createdAt: now.subtract(const Duration(days: 3)),
        updatedAt: now.subtract(const Duration(days: 3)),
        totalUnlocked: 12,
      ),
      AchievementModel(
        id: 'ach_10',
        name: '编程马拉松',
        description: '累计专注学习100小时',
        type: AchievementType.studyTime,
        rarity: AchievementRarity.legendary,
        iconUrl: '⚡',
        category: 'endurance',
        visualEffectType: VisualEffectType.dualStar,
        createdAt: now.subtract(const Duration(days: 1)),
        updatedAt: now.subtract(const Duration(days: 1)),
        totalUnlocked: 28,
      ),
    ];
    return _demoAchievementsCache!;
  }

  // --- 👥 社群动态 Data ---
  List<Post> get demoCommunityPosts {
    if (_demoCommunityPostsCache != null) return _demoCommunityPostsCache!;
    final now = _now;
    _demoCommunityPostsCache = [
      Post(
        id: 'post_1',
        userId: 'user_alice',
        content:
            '把“口语话题卡”拆成关键词以后真的顺很多，不再死背全文了。今天第一次能自然地补一句自己的例子，虽然还是会卡壳，但没那么怕开口了。',
        createdAt: now.subtract(const Duration(hours: 2)),
        user: const PostUser(
          id: 'user_alice',
          username: 'Alice_Words',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Alice',
        ),
        topic: '语言练习',
        likeCount: 15,
      ),
      Post(
        id: 'post_2',
        userId: 'user_bob',
        content:
            '今天用“边走边录音”的方式整理作品集开场白，居然比坐在桌前更敢说。感觉职业准备也不一定都得很正式，先把想法说出来也算前进。',
        createdAt: now.subtract(const Duration(hours: 5)),
        user: const PostUser(
          id: 'user_bob',
          username: 'Bob_Pathfinder',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Bob',
        ),
        topic: '职业探索',
        likeCount: 23,
      ),
      Post(
        id: 'post_3',
        userId: 'user_carol',
        content: '分享一个阅读办法：不要急着摘金句，先写下“我真正不同意作者的哪一句”。这样读完以后留下来的不是笔记堆，而是自己的判断。',
        createdAt: now.subtract(const Duration(hours: 8)),
        user: const PostUser(
          id: 'user_carol',
          username: 'Carol_Reader',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Carol',
        ),
        topic: '阅读反思',
        likeCount: 42,
      ),
      Post(
        id: 'post_4',
        userId: 'user_david',
        content: '周末总想睡到自然醒，结果起来以后整天都昏昏的。有没有人试过“固定起床时间 + 把周末任务减轻”的方法？想听真实反馈。',
        createdAt: now.subtract(const Duration(hours: 12)),
        user: const PostUser(
          id: 'user_david',
          username: 'David_Reset',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=David',
        ),
        topic: '节律求助',
        likeCount: 8,
      ),
      Post(
        id: 'post_5',
        userId: 'user_emma',
        content:
            '今天用 Sparkle 的认知棱镜看见一个挺真实的模式：下午适合理工大任务，晚上反而更适合读书和语言复盘。以前我总逼自己晚上冲刺，难怪总挫败。',
        createdAt: now.subtract(const Duration(days: 1)),
        user: const PostUser(
          id: 'user_emma',
          username: 'Emma_Rhythm',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Emma',
        ),
        topic: '学习心得',
        likeCount: 31,
      ),
      Post(
        id: 'post_6',
        userId: 'user_frank',
        content:
            '今天拍“傍晚通勤”终于不再什么都想塞进画面里了。我强迫自己每张只保留一个主角，结果照片干净了很多，删减真的是创作的一部分。',
        createdAt: now.subtract(const Duration(days: 1, hours: 6)),
        user: const PostUser(
          id: 'user_frank',
          username: 'Frank_Frame',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Frank',
        ),
        topic: '摄影练习',
        likeCount: 19,
      ),
      Post(
        id: 'post_7',
        userId: 'user_grace',
        content:
            '刚做完一次信息访谈，最有效的问题居然不是“你每天做什么”，而是“你是怎么走到现在这个方向的”。一下子就聊到了真正有用的经验。',
        createdAt: now.subtract(const Duration(days: 2)),
        user: const PostUser(
          id: 'user_grace',
          username: 'Grace_Career',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Grace',
        ),
        topic: '访谈技巧',
        likeCount: 56,
      ),
      Post(
        id: 'post_8',
        userId: 'user_henry',
        content: '数学课上最有用的改变不是多做题，而是每做完一题都补一句“这题为什么不是另一个方法”。这种区分感一建立，错题少了很多。',
        createdAt: now.subtract(const Duration(days: 2, hours: 10)),
        user: const PostUser(
          id: 'user_henry',
          username: 'Henry_Logic',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Henry',
        ),
        topic: '理工方法',
        likeCount: 38,
      ),
      Post(
        id: 'post_9',
        userId: 'user_iris',
        content:
            '试了“读完一章只记 3 个问题”的方式，发现自己终于不是在机械摘抄了。虽然写出来的问题有点笨，但它们真的能暴露我没想清的地方。',
        createdAt: now.subtract(const Duration(days: 3)),
        user: const PostUser(
          id: 'user_iris',
          username: 'Iris_Question',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Iris',
        ),
        topic: '阅读训练',
        likeCount: 27,
      ),
      Post(
        id: 'post_10',
        userId: 'user_jack',
        content:
            '今天把作品集首页改成“我最近在学什么、在做什么、在思考什么”三段，瞬间没有那么像硬凹人设了。对还没定方向的人来说，过程感真的比结论更诚实。',
        createdAt: now.subtract(const Duration(days: 3, hours: 15)),
        user: const PostUser(
          id: 'user_jack',
          username: 'Jack_Process',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Jack',
        ),
        topic: '作品集更新',
        likeCount: 45,
      ),
      Post(
        id: 'post_11',
        userId: 'user_kate',
        content: '这周开始把雅思口语改成“每天一张话题卡 + 2 分钟计时”，比以前一次练很久更能坚持。原来考证也不一定要一直靠意志力顶。',
        createdAt: now.subtract(const Duration(days: 1, hours: 2)),
        user: const PostUser(
          id: 'user_kate',
          username: 'Kate_Timer',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Kate',
        ),
        topic: '考证节奏',
        likeCount: 26,
      ),
      Post(
        id: 'post_12',
        userId: 'user_ryan',
        content:
            '转型期最有用的动作不是疯狂投递，而是先把“我做过什么、我能迁移什么、我想往哪去”写成能讲给别人听的版本。写出来以后，焦虑会小很多。',
        createdAt: now.subtract(const Duration(days: 2, hours: 3)),
        user: const PostUser(
          id: 'user_ryan',
          username: 'Ryan_Shift',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Ryan',
        ),
        topic: '转型复盘',
        likeCount: 34,
      ),
    ];
    return _demoCommunityPostsCache!;
  }

  // --- 🎯 专注会话历史 Data ---
  List<Map<String, dynamic>> get demoFocusSessions {
    if (_demoFocusSessionsCache != null) return _demoFocusSessionsCache!;
    final now = _now;
    _demoFocusSessionsCache = [
      {
        'id': 'session_1',
        'start_time': now.subtract(const Duration(hours: 2)).toIso8601String(),
        'end_time': now
            .subtract(const Duration(hours: 1, minutes: 30))
            .toIso8601String(),
        'duration_minutes': 30,
        'focus_type': 'pomodoro',
        'status': 'completed',
        'task_id': demoTasks.first.id,
        'white_noise_type': 'rain',
      },
      {
        'id': 'session_2',
        'start_time':
            now.subtract(const Duration(days: 1, hours: 3)).toIso8601String(),
        'end_time': now
            .subtract(const Duration(days: 1, hours: 1, minutes: 30))
            .toIso8601String(),
        'duration_minutes': 90,
        'focus_type': 'deep_work',
        'status': 'completed',
        'task_id': demoTasks[1].id,
        'white_noise_type': 'ocean',
      },
      {
        'id': 'session_3',
        'start_time':
            now.subtract(const Duration(days: 1, hours: 15)).toIso8601String(),
        'end_time': now
            .subtract(const Duration(days: 1, hours: 14, minutes: 35))
            .toIso8601String(),
        'duration_minutes': 25,
        'focus_type': 'pomodoro',
        'status': 'completed',
        'white_noise_type': 'forest',
      },
      {
        'id': 'session_4',
        'start_time':
            now.subtract(const Duration(days: 2, hours: 4)).toIso8601String(),
        'end_time':
            now.subtract(const Duration(days: 2, hours: 2)).toIso8601String(),
        'duration_minutes': 120,
        'focus_type': 'deep_work',
        'status': 'completed',
        'task_id': demoTasks[2].id,
      },
      {
        'id': 'session_5',
        'start_time':
            now.subtract(const Duration(days: 3, hours: 5)).toIso8601String(),
        'end_time': now
            .subtract(const Duration(days: 3, hours: 4, minutes: 20))
            .toIso8601String(),
        'duration_minutes': 40,
        'focus_type': 'pomodoro',
        'status': 'completed',
        'white_noise_type': 'cafe',
      },
    ];
    return _demoFocusSessionsCache!;
  }

  // --- 📝 错题本 Data ---
  List<Map<String, dynamic>> get demoErrorRecords {
    if (_demoErrorRecordsCache != null) return _demoErrorRecordsCache!;
    final now = _now;
    _demoErrorRecordsCache = [
      {
        'id': 'error_1',
        'question_text': '若函数 f(x)=x^2 e^x，求 f\'(x) 的结果。',
        'user_answer': '2x e^x',
        'correct_answer': 'f\'(x)=2x e^x + x^2 e^x',
        'subject': '高等数学',
        'mastery_level': 0.6,
        'review_count': 2,
        'created_at': now.subtract(const Duration(days: 5)).toIso8601String(),
        'updated_at': now.subtract(const Duration(days: 1)).toIso8601String(),
        'chapter': '乘积求导',
        'difficulty': 3,
        'next_review_at': now.add(const Duration(days: 2)).toIso8601String(),
        'ai_analysis_summary':
            '你漏掉了乘积法则中的第二项，说明求导规则本身会，但在书写时容易直接抓住第一个显眼部分。建议先写结构再代入。',
      },
      {
        'id': 'error_2',
        'question_text': '请将 “我最近在尝试建立更稳定的学习节奏” 翻译成更自然的英文。',
        'user_answer': 'I am trying build a more stable study rhythm recently.',
        'correct_answer':
            'I\'ve been trying to build a more stable study routine lately.',
        'subject': '英语表达',
        'mastery_level': 0.4,
        'review_count': 3,
        'created_at': now.subtract(const Duration(days: 7)).toIso8601String(),
        'updated_at': now.subtract(const Duration(days: 2)).toIso8601String(),
        'chapter': '日常表达',
        'difficulty': 3,
        'next_review_at': now.add(const Duration(days: 3)).toIso8601String(),
        'ai_analysis_summary':
            '主要问题在于动词搭配和时间副词位置。你想表达的是“最近一直在尝试”，用现在完成进行意味更自然。',
      },
      {
        'id': 'error_3',
        'question_text': '阅读一段非虚构文本时，作者为什么在第二段突然转向个人经历？',
        'user_answer': '因为作者想举个例子',
        'correct_answer': '作者借个人经历建立情感入口，把抽象议题转成可感知的具体场景。',
        'subject': '阅读理解',
        'mastery_level': 0.7,
        'review_count': 1,
        'created_at': now.subtract(const Duration(days: 3)).toIso8601String(),
        'updated_at': now.subtract(const Duration(days: 1)).toIso8601String(),
        'chapter': '论证结构',
        'difficulty': 2,
        'next_review_at': now.add(const Duration(days: 4)).toIso8601String(),
        'ai_analysis_summary':
            '你看到了“举例子”，但没有继续判断这个例子在全文结构中的作用。阅读题里要多问一步：它为什么在这里出现。',
      },
      {
        'id': 'error_4',
        'question_text': '如果一项调查样本主要来自同一个宿舍楼层，结论最可能受到什么影响？',
        'user_answer': '样本数量可能不够',
        'correct_answer': '更核心的问题是样本偏差，样本来源过于集中会影响代表性。',
        'subject': '统计学',
        'mastery_level': 0.52,
        'review_count': 2,
        'created_at': now.subtract(const Duration(days: 4)).toIso8601String(),
        'updated_at': now.subtract(const Duration(hours: 20)).toIso8601String(),
        'chapter': '抽样方法',
        'difficulty': 3,
        'next_review_at': now.add(const Duration(days: 2)).toIso8601String(),
        'ai_analysis_summary': '你先注意到了数量，却忽略了来源分布。以后遇到调查题，先判断“样本像不像总体”再看数量。',
      },
      {
        'id': 'error_5',
        'question_text': '为什么这张街拍照片看起来“很热闹但没有重点”？',
        'user_answer': '因为人太多',
        'correct_answer': '问题不只在于元素多，而在于没有明确主角，亮部和边缘杂物共同分散了视线。',
        'subject': '摄影构图',
        'mastery_level': 0.46,
        'review_count': 1,
        'created_at': now.subtract(const Duration(days: 6)).toIso8601String(),
        'updated_at': now.subtract(const Duration(days: 2)).toIso8601String(),
        'chapter': '主体与留白',
        'difficulty': 2,
        'next_review_at': now.add(const Duration(days: 5)).toIso8601String(),
        'ai_analysis_summary': '你已经能感受到“乱”，下一步要训练自己具体指出哪里在抢戏，尤其是边缘和高亮区域。',
      },
    ];
    return _demoErrorRecordsCache!;
  }

  // --- 🧠 行为模式 Data ---
  List<BehaviorPatternModel> get demoBehaviorPatterns {
    if (_demoBehaviorPatternsCache != null) return _demoBehaviorPatternsCache!;
    final now = _now;
    _demoBehaviorPatternsCache = [
      BehaviorPatternModel(
        id: 'pattern_1',
        userId: demoUserId,
        patternName: '下午效率高峰',
        patternType: 'productive',
        description: '你在下午3-5点的专注时长和复杂任务完成率明显高于其他时段',
        solutionText: '把理工学习、作品集重写和需要判断力的任务安排在下午，早上留给热身与整理。',
        evidenceIds: ['frag_1', 'frag_2', 'frag_3'],
        isArchived: false,
        createdAt: now.subtract(const Duration(days: 7)),
        updatedAt: now.subtract(const Duration(days: 1)),
      ),
      BehaviorPatternModel(
        id: 'pattern_2',
        userId: demoUserId,
        patternName: '晚间适合轻输出',
        patternType: 'productive',
        description: '晚上 8-9 点更适合语言跟说、阅读整理和短复盘，不适合直接冲高难任务。',
        solutionText: '给晚间任务设置更低起点，用 10-15 分钟动作代替“今晚必须高产”的压力。',
        isArchived: false,
        createdAt: now.subtract(const Duration(days: 10)),
        updatedAt: now.subtract(const Duration(days: 2)),
      ),
      BehaviorPatternModel(
        id: 'pattern_3',
        userId: demoUserId,
        patternName: '周末学习动力不足',
        patternType: 'barrier',
        description: '周末的学习时长仅为工作日的40%，任务完成率下降60%',
        solutionText: '保留固定起床时间，周末只安排轻量任务和恢复动作，再借助社群一起维持节奏。',
        isArchived: false,
        createdAt: now.subtract(const Duration(days: 14)),
        updatedAt: now.subtract(const Duration(days: 3)),
      ),
    ];
    return _demoBehaviorPatternsCache!;
  }

  // --- 📢 通知中心 Data ---
  List<Map<String, dynamic>> get demoNotifications {
    if (_demoNotificationsCache != null) return _demoNotificationsCache!;
    final now = _now;
    _demoNotificationsCache = [
      {
        'id': 'notif_1',
        'type': 'achievement',
        'title': '🏆 解锁新成就',
        'message': '恭喜你获得“连续学习7天”成就，节奏感正在慢慢稳定下来。',
        'created_at': now.subtract(const Duration(hours: 1)).toIso8601String(),
        'is_read': false,
      },
      {
        'id': 'notif_2',
        'type': 'task_reminder',
        'title': '⏰ 任务提醒',
        'message': '你有 1 个任务即将到期：理工课复盘 - 用自己的话讲清楚积分换元',
        'created_at': now.subtract(const Duration(hours: 3)).toIso8601String(),
        'is_read': false,
      },
      {
        'id': 'notif_3',
        'type': 'cognitive_insight',
        'title': '💡 新的学习洞察',
        'message': '发现你在下午适合理工与职业任务，晚上更适合语言复盘与阅读整理',
        'created_at': now.subtract(const Duration(hours: 6)).toIso8601String(),
        'is_read': true,
      },
      {
        'id': 'notif_4',
        'type': 'community',
        'title': '💬 社群动态',
        'message': 'Mori_Creative 在“作品集慢慢长出来”里回复了你的问题',
        'created_at': now.subtract(const Duration(days: 1)).toIso8601String(),
        'is_read': true,
      },
      {
        'id': 'notif_5',
        'type': 'plan_progress',
        'title': '🎯 计划进度',
        'message': '你的“本周复合学习节奏校准”计划已完成 68%，还剩 7 天。',
        'created_at': now.subtract(const Duration(days: 1)).toIso8601String(),
        'is_read': true,
      },
      {
        'id': 'notif_6',
        'type': 'capsule_ready',
        'title': '🎁 新认知胶囊',
        'message': '为你生成了一个关于“下一步不够明确为什么会拖延”的深度洞察',
        'created_at': now.subtract(const Duration(days: 2)).toIso8601String(),
        'is_read': true,
      },
      {
        'id': 'notif_7',
        'type': 'touchpoint',
        'title': '🧭 转型线索',
        'message': '你最近的作品集整理、信息访谈和可迁移能力记录正在形成一条更清晰的转型主线',
        'created_at':
            now.subtract(const Duration(days: 2, hours: 6)).toIso8601String(),
        'is_read': false,
      },
      {
        'id': 'notif_8',
        'type': 'wellness_nudge',
        'title': '🫁 恢复提醒',
        'message': '你连续两次在高认知任务后补了恢复动作，运动恢复型节奏正在慢慢稳定',
        'created_at': now.subtract(const Duration(days: 3)).toIso8601String(),
        'is_read': true,
      },
    ];
    return _demoNotificationsCache!;
  }

  // --- 👥 好友列表 Data ---
  List<Map<String, dynamic>> get demoFriends {
    if (_demoFriendsCache != null) return _demoFriendsCache!;
    _demoFriendsCache = [
      {
        'id': 'friend_1',
        'username': 'Lena_Words',
        'avatar_url': 'https://api.dicebear.com/9.x/avataaars/png?seed=Alice',
        'flame_level': 12,
        'is_online': true,
        'recent_activity': '刚完成一轮英语跟说练习',
      },
      {
        'id': 'friend_2',
        'username': 'Mori_Creative',
        'avatar_url': 'https://api.dicebear.com/9.x/avataaars/png?seed=Bob',
        'flame_level': 18,
        'is_online': false,
        'recent_activity': '2小时前在整理摄影作品集',
      },
      {
        'id': 'friend_3',
        'username': 'Nora_Reset',
        'avatar_url': 'https://api.dicebear.com/9.x/avataaars/png?seed=Carol',
        'flame_level': 15,
        'is_online': true,
        'recent_activity': '正在做晚间阅读整理',
      },
      {
        'id': 'friend_4',
        'username': 'Owen_Field',
        'avatar_url': 'https://api.dicebear.com/9.x/avataaars/png?seed=David',
        'flame_level': 10,
        'is_online': false,
        'recent_activity': '5小时前完成了统计学练习',
      },
      {
        'id': 'friend_5',
        'username': 'Rina_Path',
        'avatar_url': 'https://api.dicebear.com/9.x/avataaars/png?seed=Emma',
        'flame_level': 20,
        'is_online': true,
        'recent_activity': '30分钟前更新了作品集首页',
      },
    ];
    return _demoFriendsCache!;
  }

  // --- 🤝 责任伙伴 Data ---
  List<Map<String, dynamic>> get demoAccountabilityPartners {
    if (_demoAccountabilityPartnersCache != null) {
      return _demoAccountabilityPartnersCache!;
    }
    _demoAccountabilityPartnersCache = [
      {
        'id': 'partner_1',
        'partner_id': 'friend_1',
        'partner_name': 'Lena_Words',
        'partner_avatar':
            'https://api.dicebear.com/9.x/avataaars/png?seed=Alice',
        'status': 'active',
        'started_at': _now.subtract(const Duration(days: 14)).toIso8601String(),
        'my_streak': 7,
        'partner_streak': 5,
        'total_checkins': 12,
        'last_checkin':
            _now.subtract(const Duration(hours: 3)).toIso8601String(),
      },
      {
        'id': 'partner_2',
        'partner_id': 'friend_3',
        'partner_name': 'Nora_Reset',
        'partner_avatar':
            'https://api.dicebear.com/9.x/avataaars/png?seed=Carol',
        'status': 'active',
        'started_at': _now.subtract(const Duration(days: 7)).toIso8601String(),
        'my_streak': 3,
        'partner_streak': 4,
        'total_checkins': 8,
        'last_checkin':
            _now.subtract(const Duration(hours: 1)).toIso8601String(),
      },
    ];
    return _demoAccountabilityPartnersCache!;
  }

  // --- 🏘️ 群组 Data ---
  List<Map<String, dynamic>> get demoGroups {
    if (_demoGroupsCache != null) return _demoGroupsCache!;
    _demoGroupsCache = [
      {
        'id': 'group_1',
        'name': '晚间语言复盘屋',
        'description': '一起做精读、跟说和短复盘，适合下班下课后慢慢进入状态的人。',
        'avatar_url': 'https://api.dicebear.com/9.x/shapes/png?seed=algo',
        'member_count': 15,
        'is_member': true,
        'is_public': true,
        'created_at': _now.subtract(const Duration(days: 30)).toIso8601String(),
        'last_activity':
            _now.subtract(const Duration(hours: 1)).toIso8601String(),
      },
      {
        'id': 'group_2',
        'name': '作品集慢慢长出来',
        'description': '给跨领域学习者一个稳定更新作品集和表达职业方向的空间。',
        'avatar_url': 'https://api.dicebear.com/9.x/shapes/png?seed=flutter',
        'member_count': 42,
        'is_member': true,
        'is_public': true,
        'created_at': _now.subtract(const Duration(days: 60)).toIso8601String(),
        'last_activity':
            _now.subtract(const Duration(minutes: 30)).toIso8601String(),
      },
      {
        'id': 'group_3',
        'name': '周末恢复实验室',
        'description': '讨论睡眠、运动、恢复和如何避免周末一散就整周失控。',
        'avatar_url': 'https://api.dicebear.com/9.x/shapes/png?seed=ai',
        'member_count': 28,
        'is_member': false,
        'is_public': true,
        'created_at': _now.subtract(const Duration(days: 15)).toIso8601String(),
        'last_activity':
            _now.subtract(const Duration(hours: 2)).toIso8601String(),
      },
    ];
    return _demoGroupsCache!;
  }

  // --- 💬 群组消息 Data ---
  List<Map<String, dynamic>> get demoGroupMessages {
    if (_demoGroupMessagesCache != null) return _demoGroupMessagesCache!;
    _demoGroupMessagesCache = [
      {
        'id': 'msg_1',
        'group_id': 'group_1',
        'sender_id': 'friend_1',
        'sender_name': 'Lena_Words',
        'sender_avatar':
            'https://api.dicebear.com/9.x/avataaars/png?seed=Alice',
        'content': '有人今晚一起做 15 分钟英文跟说吗？我想先从天气和近况两个话题热身。',
        'created_at':
            _now.subtract(const Duration(minutes: 30)).toIso8601String(),
        'reactions': [
          {'emoji': '👍', 'count': 3},
        ],
      },
      {
        'id': 'msg_2',
        'group_id': 'group_1',
        'sender_id': 'friend_2',
        'sender_name': 'Mori_Creative',
        'sender_avatar': 'https://api.dicebear.com/9.x/avataaars/png?seed=Bob',
        'content': '我来，今天白天太耗脑了，晚上只想做一点轻输出，正合适。',
        'created_at':
            _now.subtract(const Duration(minutes: 25)).toIso8601String(),
        'reactions': [
          {'emoji': '💪', 'count': 2},
        ],
      },
      {
        'id': 'msg_3',
        'group_id': 'group_1',
        'sender_id': 'friend_3',
        'sender_name': 'Nora_Reset',
        'sender_avatar':
            'https://api.dicebear.com/9.x/avataaars/png?seed=Carol',
        'content': '加油，今天如果脑子有点钝也没关系，先张嘴比说得完美更重要。',
        'created_at':
            _now.subtract(const Duration(minutes: 20)).toIso8601String(),
        'reactions': <Map<String, dynamic>>[],
      },
    ];
    return _demoGroupMessagesCache!;
  }

  // --- 📊 责任伙伴打卡热力图 Data ---
  List<Map<String, dynamic>> get demoAccountabilityHeatmap {
    if (_demoAccountabilityHeatmapCache != null) {
      return _demoAccountabilityHeatmapCache!;
    }
    final now = _now;
    final heatmap = <Map<String, dynamic>>[];

    // 生成过去365天的模拟数据
    for (var i = 0; i < 365; i++) {
      final date = now.subtract(Duration(days: i));
      // 随机生成打卡强度 (0-4)
      final intensity =
          i < 30 ? (date.weekday % 3 == 0 ? 2 : 0) : (i % 7 == 0 ? 3 : (i % 3));
      heatmap.add({
        'date': date.toIso8601String().split('T')[0],
        'intensity': intensity,
        'checkins': intensity > 0
            ? <Map<String, dynamic>>[
                {'time': '09:00', 'content': '早起学习一小时！'},
                if (intensity > 2) {'time': '21:00', 'content': '晚上复习总结'},
              ]
            : <Map<String, dynamic>>[],
      });
    }
    _demoAccountabilityHeatmapCache = heatmap;
    return heatmap;
  }

  // --- 🔥 打卡记录 Data ---
  List<Map<String, dynamic>> get demoCheckins {
    if (_demoCheckinsCache != null) return _demoCheckinsCache!;
    _demoCheckinsCache = [
      {
        'id': 'checkin_1',
        'partnership_id': 'partner_1',
        'user_id': demoUserId,
        'content': '今天先完成了积分换元复盘，晚上又补了 12 分钟口语跟说，虽然都不长，但节奏比前几天稳很多。',
        'created_at': _now.subtract(const Duration(hours: 3)).toIso8601String(),
        'likes_count': 2,
        'encouragements': [
          {'user_id': 'friend_1', 'message': '这个节奏很真实，稳下来比一口气冲太猛更厉害。'},
        ],
      },
      {
        'id': 'checkin_2',
        'partnership_id': 'partner_1',
        'user_id': 'friend_1',
        'content': '我今天把英语自我介绍改短了一版，终于不像背模板了，晚上准备再录一次。',
        'created_at': _now.subtract(const Duration(hours: 5)).toIso8601String(),
        'likes_count': 3,
        'encouragements': <Map<String, dynamic>>[],
      },
    ];
    return _demoCheckinsCache!;
  }

  // --- 🎯 视觉元素 Data ---
  List<Map<String, dynamic>> get demoVisualElements {
    if (_demoVisualElementsCache != null) return _demoVisualElementsCache!;
    _demoVisualElementsCache = [
      {
        'id': 've_bg_1',
        'name': '星空背景',
        'description': '深邃的宇宙星空背景',
        'element_type': 'background',
        'rarity': 'common',
        'category': '宇宙',
        'is_unlocked': true,
        'is_equipped': true,
        'unlock_condition': '默认解锁',
        'preview_url':
            'https://images.unsplash.com/photo-1419248682-f54b?w=200',
      },
      {
        'id': 've_bg_2',
        'name': '极光背景',
        'description': '绚丽的北极光效果',
        'element_type': 'background',
        'rarity': 'rare',
        'category': '自然',
        'is_unlocked': true,
        'is_equipped': false,
        'unlock_condition': '连续学习7天',
        'preview_url': 'https://images.unsplash.com/photo-1486402638-b5b?w=200',
      },
      {
        'id': 've_bg_3',
        'name': '赛博朋克背景',
        'description': '霓虹灯与未来城市',
        'element_type': 'background',
        'rarity': 'epic',
        'category': '科幻',
        'is_unlocked': false,
        'is_equipped': false,
        'unlock_condition': '完成10个任务',
        'preview_url':
            'https://images.unsplash.com/photo-1550751827-f584?w=200',
      },
      {
        'id': 've_particle_1',
        'name': '萤火虫粒子',
        'description': '温暖的萤火虫飘动效果',
        'element_type': 'particle',
        'rarity': 'common',
        'category': '自然',
        'is_unlocked': true,
        'is_equipped': true,
        'unlock_condition': '默认解锁',
        'preview_url': null,
      },
      {
        'id': 've_particle_2',
        'name': '雪花粒子',
        'description': '轻柔的雪花飘落效果',
        'element_type': 'particle',
        'rarity': 'rare',
        'category': '自然',
        'is_unlocked': true,
        'is_equipped': false,
        'unlock_condition': '在冬季学习',
        'preview_url': null,
      },
      {
        'id': 've_effect_1',
        'name': '金色光环',
        'description': '完成任务时的金色光环效果',
        'element_type': 'effect',
        'rarity': 'epic',
        'category': '特效',
        'is_unlocked': false,
        'is_equipped': false,
        'unlock_condition': '连续打卡30天',
        'preview_url': null,
      },
    ];
    return _demoVisualElementsCache!;
  }

  // --- 🏆 成就系统扩展 Data ---
  List<Map<String, dynamic>> get demoAchievementDetails {
    if (_demoAchievementDetailsCache != null) {
      return _demoAchievementDetailsCache!;
    }
    _demoAchievementDetailsCache = [
      {
        'id': 'achv_1',
        'name': '初出茅庐',
        'description': '完成第一个任务',
        'type': 'milestone',
        'rarity': 'common',
        'icon_url': '🎯',
        'is_unlocked': true,
        'unlocked_at':
            DateTime.now().subtract(const Duration(days: 30)).toIso8601String(),
        'progress': {'current': 1, 'target': 1},
      },
      {
        'id': 'achv_2',
        'name': '持之以恒',
        'description': '连续学习7天',
        'type': 'streak',
        'rarity': 'rare',
        'icon_url': '🔥',
        'is_unlocked': true,
        'unlocked_at':
            DateTime.now().subtract(const Duration(days: 10)).toIso8601String(),
        'progress': {'current': 7, 'target': 7},
      },
      {
        'id': 'achv_3',
        'name': '知识星探',
        'description': '解锁50个知识节点',
        'type': 'node_explore',
        'rarity': 'epic',
        'icon_url': '🌟',
        'is_unlocked': false,
        'progress': {'current': 23, 'target': 50},
      },
      {
        'id': 'achv_4',
        'name': '完美主义',
        'description': '任务完成率达到95%',
        'type': 'mastery',
        'rarity': 'legendary',
        'icon_url': '💎',
        'is_unlocked': false,
        'progress': {'current': 78, 'target': 100},
      },
    ];
    return _demoAchievementDetailsCache!;
  }
}

/// Provider for DemoDataService
final demoDataServiceProvider =
    Provider<DemoDataService>((ref) => DemoDataService());
