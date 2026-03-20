// ignore_for_file: use_setters_to_change_properties

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

class DemoDataService {
  factory DemoDataService() => _instance;
  DemoDataService._internal();
  static bool isDemoMode = false;

  static final DemoDataService _instance = DemoDataService._internal();

  final _uuid = const Uuid();

  String? _currentAvatarUrl;
  List<PlanModel>? _demoPlansCache;

  // --- User Data ---
  UserModel get demoUser => UserModel(
        id: 'CS_Sophomore_12345',
        username: 'AI_Learner_02',
        email: 'learner@sparkle.ai',
        nickname: 'AI_Learner_02',
        avatarUrl: _currentAvatarUrl ??
            'https://api.dicebear.com/9.x/avataaars/png?seed=AI_Learner_02',
        flameLevel: 15,
        flameBrightness: 0.85,
        depthPreference: 0.7,
        curiosityPreference: 0.8,
        isActive: true,
        createdAt: DateTime.now().subtract(const Duration(days: 45)),
        updatedAt: DateTime.now(),
        pushPreferences: PushPreferences(),
      );

  void updateDemoAvatar(String url) {
    _currentAvatarUrl = url;
  }

  void resetDemoState() {
    _currentAvatarUrl = null;
    _demoPlansCache = null;
  }

  // --- Task Data ---
  List<TaskModel> get demoTasks {
    final now = DateTime.now();
    return [
      // 🔥 Today's High Priority
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '数据结构 - 二叉树遍历算法',
        type: TaskType.learning,
        tags: ['CS', 'Data Structures', 'Tree'],
        estimatedMinutes: 90,
        difficulty: 4,
        energyCost: 4,
        status: TaskStatus.inProgress,
        priority: 3,
        dueDate: now,
        startedAt: now.subtract(const Duration(minutes: 30)),
        createdAt: now.subtract(const Duration(days: 1)),
        updatedAt: now,
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '操作系统 - 死锁处理机制',
        type: TaskType.learning,
        tags: ['OS', 'Concurrency'],
        estimatedMinutes: 75,
        difficulty: 4,
        energyCost: 3,
        status: TaskStatus.pending,
        priority: 3,
        dueDate: now,
        createdAt: now.subtract(const Duration(hours: 6)),
        updatedAt: now,
      ),

      // 📚 This Week
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '离散数学 - 图论着色问题',
        type: TaskType.learning,
        tags: ['Math', 'Graph Theory'],
        estimatedMinutes: 120,
        difficulty: 4,
        energyCost: 4,
        status: TaskStatus.pending,
        priority: 3,
        dueDate: now.add(const Duration(days: 2)),
        createdAt: now.subtract(const Duration(days: 3)),
        updatedAt: now,
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '计算机网络 - TCP协议分析',
        type: TaskType.learning,
        tags: ['Network', 'Protocol'],
        estimatedMinutes: 90,
        difficulty: 3,
        energyCost: 3,
        status: TaskStatus.pending,
        priority: 2,
        dueDate: now.add(const Duration(days: 3)),
        createdAt: now.subtract(const Duration(days: 2)),
        updatedAt: now,
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: 'Python爬虫 - BeautifulSoup实战',
        type: TaskType.training,
        tags: ['Python', 'Web Scraping'],
        estimatedMinutes: 120,
        difficulty: 2,
        energyCost: 2,
        status: TaskStatus.pending,
        priority: 2,
        dueDate: now.add(const Duration(days: 4)),
        createdAt: now.subtract(const Duration(days: 1)),
        updatedAt: now,
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '数据库系统 - 事务隔离级别',
        type: TaskType.learning,
        tags: ['Database', 'Transaction'],
        estimatedMinutes: 60,
        difficulty: 3,
        energyCost: 2,
        status: TaskStatus.pending,
        priority: 2,
        dueDate: now.add(const Duration(days: 5)),
        createdAt: now.subtract(const Duration(days: 1)),
        updatedAt: now,
      ),

      // 🎯 Mid-term Sprint
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '算法设计 - 动态规划专题',
        type: TaskType.learning,
        tags: ['Algorithm', 'DP'],
        estimatedMinutes: 150,
        difficulty: 5,
        energyCost: 4,
        status: TaskStatus.pending,
        priority: 3,
        dueDate: now.add(const Duration(days: 7)),
        createdAt: now.subtract(const Duration(days: 5)),
        updatedAt: now,
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '机器学习 - 线性回归实现',
        type: TaskType.training,
        tags: ['ML', 'Python'],
        estimatedMinutes: 180,
        difficulty: 4,
        energyCost: 4,
        status: TaskStatus.pending,
        priority: 2,
        dueDate: now.add(const Duration(days: 10)),
        createdAt: now.subtract(const Duration(days: 7)),
        updatedAt: now,
      ),

      // ✅ Recently Completed
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '数据结构 - 链表实现与操作',
        type: TaskType.learning,
        tags: ['CS', 'Data Structures', 'LinkedList'],
        estimatedMinutes: 120,
        difficulty: 3,
        energyCost: 3,
        status: TaskStatus.completed,
        priority: 3,
        dueDate: now.subtract(const Duration(days: 1)),
        completedAt: now.subtract(const Duration(days: 1)),
        actualMinutes: 135,
        userNote: '完成了单链表和双链表的所有操作，理解加深了！',
        createdAt: now.subtract(const Duration(days: 5)),
        updatedAt: now.subtract(const Duration(days: 1)),
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '计算机系统 - CPU调度算法模拟',
        type: TaskType.training,
        tags: ['OS', 'Scheduling'],
        estimatedMinutes: 90,
        difficulty: 3,
        energyCost: 3,
        status: TaskStatus.completed,
        priority: 2,
        dueDate: now.subtract(const Duration(days: 2)),
        completedAt: now.subtract(const Duration(days: 2)),
        actualMinutes: 85,
        createdAt: now.subtract(const Duration(days: 6)),
        updatedAt: now.subtract(const Duration(days: 2)),
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '线性代数 - 矩阵运算练习',
        type: TaskType.training,
        tags: ['Math', 'Linear Algebra'],
        estimatedMinutes: 60,
        difficulty: 2,
        energyCost: 2,
        status: TaskStatus.completed,
        priority: 2,
        dueDate: now.subtract(const Duration(days: 3)),
        completedAt: now.subtract(const Duration(days: 3)),
        actualMinutes: 55,
        createdAt: now.subtract(const Duration(days: 8)),
        updatedAt: now.subtract(const Duration(days: 3)),
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: 'Web前端 - React组件开发',
        type: TaskType.training,
        tags: ['Web', 'React', 'Frontend'],
        estimatedMinutes: 120,
        difficulty: 3,
        energyCost: 2,
        status: TaskStatus.completed,
        priority: 2,
        dueDate: now.subtract(const Duration(days: 5)),
        completedAt: now.subtract(const Duration(days: 5)),
        actualMinutes: 140,
        userNote: '实现了Todo List组件，学会了useState和useEffect',
        createdAt: now.subtract(const Duration(days: 10)),
        updatedAt: now.subtract(const Duration(days: 5)),
      ),

      // 🎨 Personal Growth
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '摄影技巧 - 夜景拍摄实践',
        type: TaskType.learning,
        tags: ['Photography', 'Hobby'],
        estimatedMinutes: 60,
        difficulty: 2,
        energyCost: 1,
        status: TaskStatus.completed,
        priority: 1,
        dueDate: now.subtract(const Duration(days: 4)),
        completedAt: now.subtract(const Duration(days: 4)),
        actualMinutes: 70,
        createdAt: now.subtract(const Duration(days: 7)),
        updatedAt: now.subtract(const Duration(days: 4)),
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '英语口语 - TED演讲学习',
        type: TaskType.learning,
        tags: ['English', 'Speaking'],
        estimatedMinutes: 45,
        difficulty: 2,
        energyCost: 1,
        status: TaskStatus.pending,
        priority: 1,
        dueDate: now.add(const Duration(days: 6)),
        createdAt: now.subtract(const Duration(days: 2)),
        updatedAt: now,
      ),

      // 📖 Reading & Reflection
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '《深度工作》阅读与反思',
        type: TaskType.reflection,
        tags: ['Reading', 'Self-improvement'],
        estimatedMinutes: 90,
        difficulty: 2,
        energyCost: 2,
        status: TaskStatus.pending,
        priority: 1,
        dueDate: now.add(const Duration(days: 14)),
        createdAt: now.subtract(const Duration(days: 3)),
        updatedAt: now,
      ),

      // 🏃 Health & Exercise
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '晨跑 - 5公里',
        type: TaskType.social,
        tags: ['Exercise', 'Health'],
        estimatedMinutes: 30,
        difficulty: 1,
        energyCost: 2,
        status: TaskStatus.completed,
        priority: 2,
        dueDate: now.subtract(const Duration(days: 1)),
        completedAt: now.subtract(const Duration(days: 1)),
        actualMinutes: 28,
        createdAt: now.subtract(const Duration(days: 1)),
        updatedAt: now.subtract(const Duration(days: 1)),
      ),

      // 🎯 Future Planning
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '实习简历更新与投递',
        type: TaskType.planning,
        tags: ['Career', 'Job Search'],
        estimatedMinutes: 120,
        difficulty: 3,
        energyCost: 3,
        status: TaskStatus.pending,
        priority: 3,
        dueDate: now.add(const Duration(days: 15)),
        createdAt: now.subtract(const Duration(days: 10)),
        updatedAt: now,
      ),
    ];
  }

  // --- Galaxy Data ---
  GalaxyGraphResponse get demoGalaxy {
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

    return GalaxyGraphResponse(
      nodes: nodes,
      edges: edges,
      userFlameIntensity: 0.85,
    );
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

    // 数学 -> 算法（前置知识）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: 'node_0', // 高等数学
        targetId: 'node_13', // 算法设计
        relationType: EdgeRelationType.prerequisite,
        strength: 0.9,
      ),
    );

    // 概率论 -> 机器学习（前置知识）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: 'node_2', // 概率论
        targetId: 'node_21', // 机器学习
        relationType: EdgeRelationType.prerequisite,
        strength: 0.9,
      ),
    );

    // 线性代数 -> 机器学习（前置知识）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: 'node_1', // 线性代数
        targetId: 'node_21', // 机器学习
        relationType: EdgeRelationType.prerequisite,
        strength: 0.8,
      ),
    );

    // 心理学 -> 设计思维（相关知识）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: 'node_${23 + 5}', // 心理学导论
        targetId: 'node_27', // 设计思维
        strength: 0.7,
      ),
    );

    // 批判性思维 -> 编程（应用）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: 'node_${30 + 3}', // 批判性思维
        targetId: 'node_9', // 程序设计
        relationType: EdgeRelationType.application,
        strength: 0.6,
      ),
    );

    // 经济学 -> 管理学（衍生知识）
    edges.add(
      GalaxyEdgeModel(
        id: 'edge_${edgeId++}',
        sourceId: 'node_${23 + 3}', // 经济学
        targetId: 'node_${23 + 4}', // 管理学
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
    final node = galaxyNodes.firstWhere(
      (n) => n.id == nodeId,
      orElse: () => galaxyNodes.first,
    );

    // Get related nodes through edges
    final edges = demoGalaxy.edges;
    final relations = edges
        .where((e) => e.sourceId == nodeId || e.targetId == nodeId)
        .map((e) {
      final isSource = e.sourceId == nodeId;
      final relatedNodeId = isSource ? e.targetId : e.sourceId;
      final relatedNode = galaxyNodes.firstWhere(
        (n) => n.id == relatedNodeId,
        orElse: () => node,
      );

      return NodeRelation(
        id: e.id,
        sourceNodeId: e.sourceId,
        targetNodeId: e.targetId,
        relationType: e.relationType.toString().split('.').last,
        strength: e.strength,
        sourceNodeName: isSource ? node.name : relatedNode.name,
        targetNodeName: isSource ? relatedNode.name : node.name,
      );
    }).toList();

    // Determine sector code string
    final sectorCode = node.sector.toString().split('.').last.toUpperCase();

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
      relatedTasks: demoTasks.take(2).toList(),
      relatedPlans: demoPlans
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
            ? DateTime.now().subtract(Duration(days: node.studyCount % 7))
            : null,
        nextReviewAt: node.masteryScore > 0 && node.masteryScore < 80
            ? DateTime.now().add(Duration(days: node.studyCount % 3 + 1))
            : null,
        decayPaused: node.studyCount % 10 == 0,
      ),
    );
  }

  // --- Plan Data ---
  List<PlanModel> get demoPlans => _demoPlansCache ??= _buildDemoPlans();

  List<PlanModel> _buildDemoPlans() {
    final now = DateTime.now();
    final growthCoreTasks = [
      _buildPlanTask(
        id: 'plan_growth_core_task_1',
        title: '梳理计算机组成原理知识地图',
        planId: 'plan_growth_1',
        createdAt: now.subtract(const Duration(days: 9)),
        updatedAt: now.subtract(const Duration(days: 2)),
        estimatedMinutes: 50,
        difficulty: 3,
        type: TaskType.learning,
        status: TaskStatus.completed,
        actualMinutes: 55,
        userNote: '把 CPU、内存层次和总线的关联重新串起来了。',
        tags: const ['Architecture', 'Knowledge Map'],
      ),
      _buildPlanTask(
        id: 'plan_growth_core_task_2',
        title: '完成操作系统并发专题错题回看',
        planId: 'plan_growth_1',
        createdAt: now.subtract(const Duration(days: 5)),
        updatedAt: now.subtract(const Duration(hours: 12)),
        estimatedMinutes: 40,
        difficulty: 4,
        type: TaskType.training,
        status: TaskStatus.inProgress,
        dueDate: now.add(const Duration(days: 2)),
        tags: const ['OS', 'Concurrency'],
      ),
      _buildPlanTask(
        id: 'plan_growth_core_task_3',
        title: '补齐网络层与传输层前置概念',
        planId: 'plan_growth_1',
        createdAt: now.subtract(const Duration(days: 2)),
        updatedAt: now.subtract(const Duration(hours: 6)),
        estimatedMinutes: 35,
        difficulty: 2,
        type: TaskType.learning,
        status: TaskStatus.pending,
        dueDate: now.add(const Duration(days: 4)),
        tags: const ['Network', 'Prerequisites'],
      ),
    ];
    final archivedGrowthTasks = [
      _buildPlanTask(
        id: 'plan_growth_archived_task_1',
        title: '完成数据库索引策略练习',
        planId: 'plan_growth_archived',
        createdAt: now.subtract(const Duration(days: 40)),
        updatedAt: now.subtract(const Duration(days: 20)),
        estimatedMinutes: 35,
        difficulty: 2,
        type: TaskType.training,
        status: TaskStatus.completed,
        actualMinutes: 32,
        tags: const ['Database', 'Index'],
      ),
    ];
    final emergingGrowthTasks = [
      _buildPlanTask(
        id: 'plan_growth_emerging_task_1',
        title: '建立 Python 自动化复盘脚本',
        planId: 'plan_growth_2',
        createdAt: now.subtract(const Duration(days: 6)),
        updatedAt: now.subtract(const Duration(days: 1)),
        estimatedMinutes: 45,
        difficulty: 2,
        type: TaskType.training,
        status: TaskStatus.inProgress,
        dueDate: now.add(const Duration(days: 3)),
        tags: const ['Python', 'Automation'],
      ),
      _buildPlanTask(
        id: 'plan_growth_emerging_task_2',
        title: '把错题本高频模式沉淀成学习清单',
        planId: 'plan_growth_2',
        createdAt: now.subtract(const Duration(days: 3)),
        updatedAt: now.subtract(const Duration(hours: 8)),
        estimatedMinutes: 30,
        difficulty: 3,
        type: TaskType.learning,
        status: TaskStatus.pending,
        dueDate: now.add(const Duration(days: 5)),
        tags: const ['Review', 'Error Book'],
      ),
    ];
    return [
      PlanModel(
        id: 'plan_sprint_1',
        userId: 'CS_Sophomore_12345',
        name: '数据结构期中冲刺',
        type: PlanType.sprint,
        dailyAvailableMinutes: 120,
        masteryLevel: 0.6,
        progress: 0.7, // 70%
        isActive: true,
        createdAt: now.subtract(const Duration(days: 5)),
        updatedAt: now,
        targetDate: now.add(const Duration(days: 7)),
        description: '集中攻克链表、栈、队列和二叉树，准备期中考试。',
        totalEstimatedHours: 20,
        tasks: demoTasks
            .where((task) =>
                task.title.contains('数据结构') || task.title.contains('算法设计'))
            .take(3)
            .toList(),
      ),
      PlanModel(
        id: 'plan_growth_1',
        userId: 'CS_Sophomore_12345',
        name: '计算机科学基础巩固',
        type: PlanType.growth,
        dailyAvailableMinutes: 60,
        masteryLevel: 0.3,
        progress: 0.45, // 45%
        isActive: true,
        createdAt: now.subtract(const Duration(days: 30)),
        updatedAt: now,
        targetDate: now.add(const Duration(days: 90)), // 3 months
        description: '系统性复习CS基础四大件，构建完整的知识体系。',
        totalEstimatedHours: 100,
        planStage: PlanStage.daily,
        priority: PlanPriority.high,
        tasks: growthCoreTasks,
      ),
      PlanModel(
        id: 'plan_growth_2',
        userId: 'CS_Sophomore_12345',
        name: '学习效率与自动化升级',
        type: PlanType.growth,
        dailyAvailableMinutes: 45,
        masteryLevel: 0.38,
        progress: 0.22,
        isActive: true,
        createdAt: now.subtract(const Duration(days: 18)),
        updatedAt: now.subtract(const Duration(hours: 4)),
        targetDate: now.add(const Duration(days: 45)),
        description: '围绕复盘、自动化和错题反馈，持续优化学习效率。',
        totalEstimatedHours: 48,
        subject: '学习方法',
        planStage: PlanStage.daily,
        priority: PlanPriority.normal,
        tasks: emergingGrowthTasks,
      ),
      PlanModel(
        id: 'plan_growth_archived',
        userId: 'CS_Sophomore_12345',
        name: '数据库基础补强',
        type: PlanType.growth,
        dailyAvailableMinutes: 35,
        masteryLevel: 0.8,
        progress: 1.0,
        isActive: false,
        createdAt: now.subtract(const Duration(days: 60)),
        updatedAt: now.subtract(const Duration(days: 15)),
        targetDate: now.subtract(const Duration(days: 3)),
        description: '已完成的数据库基础回炉计划，可在历史记录中查看。',
        totalEstimatedHours: 24,
        subject: '数据库系统',
        planStage: PlanStage.review,
        priority: PlanPriority.normal,
        tasks: archivedGrowthTasks,
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
  List<ChatMessageModel> get demoChatHistory => [
        // 最近的对话
        ChatMessageModel(
          id: 'msg_1',
          conversationId: 'demo_conv_1',
          role: MessageRole.user,
          content: '我觉得最近学习效率有点低，总是忍不住想玩手机，怎么办？',
          createdAt: DateTime.now().subtract(const Duration(hours: 2)),
        ),
        ChatMessageModel(
          id: 'msg_2',
          conversationId: 'demo_conv_1',
          role: MessageRole.assistant,
          content:
              '理解你的感受。这种焦虑和自责其实是恶性循环的一部分。我们试着接纳这种情绪，而不是对抗它。\n\n根据你的学习记录，你这周已经在《离散数学》上投入了7.5小时，这非常棒👍 也许你可以试着先做一个简单的任务来找回状态？',
          createdAt:
              DateTime.now().subtract(const Duration(hours: 1, minutes: 59)),
        ),
        ChatMessageModel(
          id: 'msg_3',
          conversationId: 'demo_conv_1',
          role: MessageRole.user,
          content: '确实，那我先复习一下链表吧，但是我有点忘了怎么实现了。',
          createdAt: DateTime.now().subtract(const Duration(minutes: 30)),
        ),
        ChatMessageModel(
          id: 'msg_4',
          conversationId: 'demo_conv_1',
          role: MessageRole.assistant,
          content: '没问题。根据你的学习进度，建议先复习 **单链表的插入与删除** 操作。\n\n正在为您生成数据结构学习计划...',
          createdAt: DateTime.now().subtract(const Duration(minutes: 29)),
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
这是一个简单的链表节点定义（C++），你可以作为参考：

```cpp
struct ListNode {
    int val;
    ListNode *next;
    ListNode(int x) : val(x), next(NULL) {}
};
```

关键操作包括：
- **插入节点**：调整next指针
- **删除节点**：跳过目标节点
- **反转链表**：迭代或递归改变方向

你想先尝试哪个操作？''',
          createdAt: DateTime.now().subtract(const Duration(minutes: 28)),
        ),
        // 之前的对话
        ChatMessageModel(
          id: 'msg_6',
          conversationId: 'demo_conv_2',
          role: MessageRole.user,
          content: '动态规划的状态转移方程怎么想出来的？感觉每次都想不到😣',
          createdAt: DateTime.now().subtract(const Duration(days: 1)),
        ),
        ChatMessageModel(
          id: 'msg_7',
          conversationId: 'demo_conv_2',
          role: MessageRole.assistant,
          content: '''
动态规划的核心思路是：

1. **定义状态**：dp[i]表示什么
2. **找递推关系**：当前状态如何从之前的状态得来
3. **确定边界**：最简单的情况是什么

以爬楼梯为例：
- 状态：dp[i] = 到达第i阶的方法数
- 递推：dp[i] = dp[i-1] + dp[i-2]（从i-1爬1阶或从i-2爬2阶）
- 边界：dp[1]=1, dp[2]=2

多做几道题，你会发现套路！要不要试试背包问题？''',
          createdAt: DateTime.now().subtract(const Duration(days: 1)),
        ),
        ChatMessageModel(
          id: 'msg_8',
          conversationId: 'demo_conv_3',
          role: MessageRole.user,
          content: '推荐一些计算机网络的学习资源？想系统学一下',
          createdAt: DateTime.now().subtract(const Duration(days: 2)),
        ),
        ChatMessageModel(
          id: 'msg_9',
          conversationId: 'demo_conv_3',
          role: MessageRole.assistant,
          content: '''
推荐以下资源组合：

📚 **书籍**：
- 《计算机网络：自顶向下方法》- 经典入门
- 《TCP/IP详解 卷1》- 深入协议细节

🎥 **视频课程**：
- 斯坦福CS144 - 实践性强
- 中科大郑烇老师 - 讲解清晰

💻 **实践项目**：
- Wireshark抓包分析
- 实现一个简单的HTTP服务器

建议：先看书+视频理解原理，然后通过抓包和编程加深理解。你想从哪个方向开始？''',
          createdAt: DateTime.now().subtract(const Duration(days: 2)),
        ),
        ChatMessageModel(
          id: 'msg_10',
          conversationId: 'demo_conv_4',
          role: MessageRole.user,
          content: '感觉学了很多知识但都很零散，怎么建立知识体系？',
          createdAt: DateTime.now().subtract(const Duration(days: 3)),
        ),
        ChatMessageModel(
          id: 'msg_11',
          conversationId: 'demo_conv_4',
          role: MessageRole.assistant,
          content: '''
建立知识体系的三个层次：

🌳 **1. 知识树（结构化）**
- 用思维导图画出知识点层级
- 明确前置关系：先学A才能学B

🔗 **2. 知识网（关联化）**
- 找跨领域联系：数学→算法→工程
- 用类比连接：线程像工厂的工人

⚡ **3. 知识流（应用化）**
- 通过项目串联知识点
- 费曼学习法：教是最好的学

Sparkle的知识星图功能就是帮你可视化这个体系！看过星图视图了吗？可以看到你的知识点之间的连接关系。''',
          createdAt: DateTime.now().subtract(const Duration(days: 3)),
        ),
      ];

  // --- Dashboard Data ---
  Map<String, dynamic> get demoDashboard => {
        'weather': {
          'type': 'sunny',
          'condition': 'Clear sky',
        },
        'flame': {
          'level': 15,
          'brightness': 85,
          'today_focus_minutes': 120,
          'tasks_completed': 3,
          'nudge_message': '你今天已经在《数据结构》上投入了2小时，非常棒！休息一下吧。',
        },
        'sprint': {
          'id': 'plan_sprint_1',
          'name': '数据结构期中冲刺',
          'progress': 0.7,
          'days_left': 7,
          'total_estimated_hours': 20.0,
        },
        'growth': {
          'id': 'plan_growth_1',
          'name': 'CS基础巩固',
          'progress': 0.45,
          'mastery_level': 0.3,
        },
        'next_actions': [
          {
            'id': 'task_1',
            'title': '数据结构 - 链表实现',
            'estimated_minutes': 120,
            'priority': 3,
            'type': 'learning',
          },
          {
            'id': 'task_2',
            'title': '离散数学 - 图论基础',
            'estimated_minutes': 90,
            'priority': 2,
            'type': 'learning',
          },
        ],
        'cognitive': {
          'weekly_pattern': 'Deep Work',
          'pattern_type': 'productive',
          'description': 'You are in a flow state this week.',
          'solution_text': 'Keep it up!',
          'status': 'analyzed',
          'has_new_insight': true,
        },
      };

  // --- 🎓 认知胶囊 Data ---
  List<CuriosityCapsuleModel> get demoCuriosityCapsules {
    final now = DateTime.now();
    return [
      CuriosityCapsuleModel(
        id: 'capsule_1',
        title: '为什么二叉树的遍历有三种方式？',
        content: '''
二叉树的三种遍历方式（前序、中序、后序）源于访问节点的不同时机。

**前序遍历**（根→左→右）：适合复制树结构
**中序遍历**（左→根→右）：对BST可得到有序序列
**后序遍历**（左→右→根）：适合释放内存、计算表达式树

这种设计体现了递归思想的优雅性，每种遍历都有其特定的应用场景。你最近在学习数据结构时遇到的困惑，正是深入理解这些概念的机会！''',
        isRead: false,
        createdAt: now.subtract(const Duration(hours: 2)),
        relatedSubject: '数据结构',
        depthLevel: 'deep',
        generationMethod: 'knowledge_gap_analysis',
        qualityScore: 0.92,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_2',
        title: '进程和线程的本质区别是什么？',
        content: '''
很多人觉得进程和线程只是"资源分配"vs"调度单位"的区别，但本质上：

**进程** = 资源容器 + 执行轨迹
**线程** = 共享资源 + 独立执行轨迹

比喻：进程像一个工厂，线程像工厂里的工人。工人们共享工厂的设备（内存），但各自有自己的工作流程（栈、寄存器）。

这解释了为什么线程切换比进程快（不需要切换"工厂"），以及为什么线程间通信更简单（共享内存）。''',
        isRead: true,
        createdAt: now.subtract(const Duration(hours: 5)),
        relatedSubject: '操作系统',
        depthLevel: 'deep',
        generationMethod: 'concept_clarification',
        qualityScore: 0.88,
        feedbackCount: 1,
        shareCount: 2,
        isFavorite: true,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_3',
        title: 'TCP为什么需要三次握手？',
        content: '''
三次握手不仅仅是"建立连接"，更重要的是**同步序列号**和**确认双方的收发能力**。

1️⃣ 客户端 → 服务器：证明客户端能发送
2️⃣ 服务器 → 客户端：证明服务器能接收+能发送
3️⃣ 客户端 → 服务器：证明客户端能接收

两次握手无法验证客户端的接收能力，四次又显得冗余。这是一个经典的"恰到好处"的设计！''',
        isRead: true,
        createdAt: now.subtract(const Duration(days: 1)),
        relatedSubject: '计算机网络',
        depthLevel: 'medium',
        generationMethod: 'why_question',
        qualityScore: 0.85,
        shareCount: 1,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_4',
        title: '动态规划的"状态转移"到底在转移什么？',
        content: '''
动态规划的精髓在于**把大问题拆成小问题，并记住小问题的答案**。

"状态转移"实际上是在表达：
- **当前状态** = f(**之前的某些状态**)

比如爬楼梯问题：
- dp[i] = dp[i-1] + dp[i-2]
- 意思是"到第i阶的方法数" = "先到i-1阶再爬1阶" + "先到i-2阶再爬2阶"

关键是找到"当前状态"和"之前状态"的数学关系。你做过的那道背包问题，本质上也是在转移"放或不放"的决策结果。''',
        isRead: false,
        createdAt: now.subtract(const Duration(days: 1, hours: 3)),
        relatedSubject: '算法设计',
        depthLevel: 'deep',
        generationMethod: 'learning_barrier_breakthrough',
        qualityScore: 0.90,
        isFavorite: true,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_5',
        title: '为什么Python的字符串是不可变的？',
        content: '''
Python字符串不可变(immutable)的设计有三个重要原因：

1. **性能优化**: 不可变对象可以被缓存和重用（字符串驻留）
2. **线程安全**: 多线程共享时无需加锁
3. **哈希键**: 可以作为字典的键（可哈希要求不可变）

这也是为什么字符串拼接在循环中效率低（每次都创建新对象），应该用join()或列表积累。设计哲学：**用少量的不便换来更多的安全性和性能**。''',
        isRead: true,
        createdAt: now.subtract(const Duration(days: 2)),
        relatedSubject: 'Python编程',
        depthLevel: 'medium',
        generationMethod: 'design_rationale',
        qualityScore: 0.82,
        feedbackCount: 1,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_6',
        title: '数据库的ACID到底保证了什么？',
        content: '''
ACID不是四个独立的特性，而是事务可靠性的四个维度：

**A**tomicity(原子性): 要么全做，要么全不做
**C**onsistency(一致性): 从一个合法状态到另一个合法状态
**I**solation(隔离性): 事务间互不干扰
**D**urability(持久性): 提交后永久保存

有趣的是，Consistency更像是目标，AID是实现手段。你学的"事务隔离级别"就是在调整I的强度，牺牲隔离性换取性能。''',
        isRead: false,
        createdAt: now.subtract(const Duration(days: 2, hours: 12)),
        relatedSubject: '数据库系统',
        depthLevel: 'deep',
        generationMethod: 'concept_clarification',
        qualityScore: 0.87,
        shareCount: 1,
        isFavorite: true,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_7',
        title: '递归为什么让人感觉"绕"？',
        content: '''
递归让人困惑的根本原因是：**人类习惯顺序思维，而递归是逆向构造**。

写递归的思路：
1. 先写最简单的情况（base case）
2. 假设子问题已解决
3. 用子问题的解构造当前问题的解

比如阶乘：
```
factorial(n) = n * factorial(n-1)  // 假设factorial(n-1)已知
factorial(1) = 1  // base case
```

关键是**信任递归会正确处理子问题**，不要试图在脑子里展开整个调用栈。这种"向下分解，向上组合"的思想，在树的遍历中体现得淋漓尽致。''',
        isRead: true,
        createdAt: now.subtract(const Duration(days: 3)),
        relatedSubject: '算法思维',
        depthLevel: 'medium',
        generationMethod: 'cognitive_barrier_analysis',
        qualityScore: 0.89,
        feedbackCount: 2,
        shareCount: 3,
        isFavorite: true,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_8',
        title: '机器学习中的"过拟合"是怎么发生的？',
        content: '''
过拟合的本质是**模型记住了数据的噪声，而不是学会了数据的规律**。

想象你为考试背答案：
- 欠拟合 = 只背了大纲，题目变化就不会了
- 刚刚好 = 理解了原理，能举一反三
- 过拟合 = 把题目和答案都死记硬背，新题目完全不会

防止过拟合的方法：
• 增加数据量（让模型见更多例子）
• 正则化（惩罚过于复杂的模型）
• Dropout（随机"忘记"一些神经元）
• 早停（train loss还在降但val loss开始升时停止）

记住：**简单的模型往往更robust**。''',
        isRead: false,
        createdAt: now.subtract(const Duration(days: 3, hours: 8)),
        relatedSubject: '机器学习',
        depthLevel: 'deep',
        generationMethod: 'analogy_explanation',
        qualityScore: 0.91,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_9',
        title: 'Git的分支到底是什么？',
        content: '''
很多人把Git分支想象成"复制了一份代码"，其实不是！

**分支只是一个指向commit的指针**。

当你创建分支时，Git只是创建了一个新指针，指向当前commit。所有commits形成一个DAG（有向无环图），分支就是这个图上的"命名指针"。

```
main  →  [A] → [B] → [C]
                ↑
              feature
```

切换分支 = 移动HEAD指针
合并分支 = 让两个指针指向同一个新commit

这就是为什么Git的分支操作如此快速（O(1)），因为只是在移动指针！理解这一点，merge、rebase、cherry-pick都变得清晰了。''',
        isRead: true,
        createdAt: now.subtract(const Duration(days: 4)),
        relatedSubject: '版本控制',
        depthLevel: 'medium',
        generationMethod: 'mental_model_correction',
        qualityScore: 0.86,
        feedbackCount: 1,
        shareCount: 2,
        isFavorite: true,
      ),
      CuriosityCapsuleModel(
        id: 'capsule_10',
        title: '为什么说"程序 = 数据结构 + 算法"？',
        content: '''
这句话揭示了编程的本质：

**数据结构** = 如何组织信息
**算法** = 如何处理信息

比如社交网络：
- 数据结构：用图表示用户关系
- 算法：BFS找朋友推荐、PageRank计算影响力

再比如导航系统：
- 数据结构：用图表示路网
- 算法：Dijkstra找最短路径

选对数据结构，算法就简单了；选错数据结构，再好的算法也救不了。这就是为什么数据结构是编程的基石！

你最近做的链表题，就是在训练"根据问题选择合适数据结构"的直觉。''',
        isRead: false,
        createdAt: now.subtract(const Duration(days: 4, hours: 15)),
        relatedSubject: '计算机科学',
        depthLevel: 'shallow',
        generationMethod: 'big_picture_connection',
        qualityScore: 0.80,
        shareCount: 1,
      ),
    ];
  }

  // --- 🏆 成就系统 Data ---
  List<AchievementModel> get demoAchievements {
    final now = DateTime.now();
    return [
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
  }

  // --- 👥 社群动态 Data ---
  List<Post> get demoCommunityPosts {
    final now = DateTime.now();
    return [
      Post(
        id: 'post_1',
        userId: 'user_alice',
        content:
            '今天终于搞懂了快速排序的partition过程！感觉打开了新世界的大门🎉 分享一下我的理解：选一个pivot，比它小的放左边，大的放右边，然后递归处理两边。关键是理解"分治"的思想！',
        createdAt: now.subtract(const Duration(hours: 2)),
        user: const PostUser(
          id: 'user_alice',
          username: 'Alice_Codes',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Alice',
        ),
        topic: '算法学习',
        likeCount: 15,
      ),
      Post(
        id: 'post_2',
        userId: 'user_bob',
        content: '刚完成了一个React项目，感觉组件化开发真的很香！推荐大家学习时多动手实践，理论+实战效果最好💪',
        createdAt: now.subtract(const Duration(hours: 5)),
        user: const PostUser(
          id: 'user_bob',
          username: 'Bob_Dev',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Bob',
        ),
        topic: 'Web开发',
        likeCount: 23,
      ),
      Post(
        id: 'post_3',
        userId: 'user_carol',
        content:
            '分享一个学习技巧：用费曼学习法复习知识点效果超好！试着把今天学的内容讲给室友听，结果发现自己还有很多不懂的地方😅 教是最好的学！',
        createdAt: now.subtract(const Duration(hours: 8)),
        user: const PostUser(
          id: 'user_carol',
          username: 'Carol_学习',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Carol',
        ),
        topic: '学习方法',
        likeCount: 42,
      ),
      Post(
        id: 'post_4',
        userId: 'user_david',
        content: '数据库事务这块真的太抽象了...有没有大佬能通俗地解释一下ACID？尤其是隔离性的几个级别🤔',
        createdAt: now.subtract(const Duration(hours: 12)),
        user: const PostUser(
          id: 'user_david',
          username: 'David_求知',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=David',
        ),
        topic: '求助',
        likeCount: 8,
      ),
      Post(
        id: 'post_5',
        userId: 'user_emma',
        content:
            '今天用Sparkle的认知棱镜发现了自己的学习模式：我在下午3-5点效率最高！以后要把难题放在这个时间段解决✨ 数据驱动真的有用！',
        createdAt: now.subtract(const Duration(days: 1)),
        user: const PostUser(
          id: 'user_emma',
          username: 'Emma_效率',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Emma',
        ),
        topic: '学习心得',
        likeCount: 31,
      ),
      Post(
        id: 'post_6',
        userId: 'user_frank',
        content: '刷LeetCode第30天打卡！从一开始的痛苦到现在的享受，真的是一个转变的过程。推荐大家从简单题开始，循序渐进💪',
        createdAt: now.subtract(const Duration(days: 1, hours: 6)),
        user: const PostUser(
          id: 'user_frank',
          username: 'Frank_刷题',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Frank',
        ),
        topic: '算法刷题',
        likeCount: 19,
      ),
      Post(
        id: 'post_7',
        userId: 'user_grace',
        content:
            '分享一个Git技巧：用git stash暂存当前修改，切换分支处理紧急bug，然后git stash pop恢复。再也不用到处commit了！',
        createdAt: now.subtract(const Duration(days: 2)),
        user: const PostUser(
          id: 'user_grace',
          username: 'Grace_技巧',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Grace',
        ),
        topic: '工具分享',
        likeCount: 56,
      ),
      Post(
        id: 'post_8',
        userId: 'user_henry',
        content: '机器学习入门推荐Andrew Ng的课程！讲得真的很清楚，而且有配套作业。现在已经能自己实现线性回归了🎓',
        createdAt: now.subtract(const Duration(days: 2, hours: 10)),
        user: const PostUser(
          id: 'user_henry',
          username: 'Henry_ML',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Henry',
        ),
        topic: '课程推荐',
        likeCount: 38,
      ),
      Post(
        id: 'post_9',
        userId: 'user_iris',
        content: '今天在图书馆学习了6个小时，虽然累但很充实！配合番茄工作法，效率真的提升了不少🍅 大家也试试看！',
        createdAt: now.subtract(const Duration(days: 3)),
        user: const PostUser(
          id: 'user_iris',
          username: 'Iris_奋斗',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Iris',
        ),
        topic: '学习日常',
        likeCount: 27,
      ),
      Post(
        id: 'post_10',
        userId: 'user_jack',
        content: '终于完成了数据结构的期中项目！实现了一个完整的AVL树，debug了两天😭 但看到测试全过的那一刻，真的太爽了！',
        createdAt: now.subtract(const Duration(days: 3, hours: 15)),
        user: const PostUser(
          id: 'user_jack',
          username: 'Jack_代码',
          avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=Jack',
        ),
        topic: '项目分享',
        likeCount: 45,
      ),
    ];
  }

  // --- 🎯 专注会话历史 Data ---
  List<Map<String, dynamic>> get demoFocusSessions {
    final now = DateTime.now();
    return [
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
  }

  // --- 📝 错题本 Data ---
  List<Map<String, dynamic>> get demoErrorRecords {
    final now = DateTime.now();
    return [
      {
        'id': 'error_1',
        'question_text': '使用快速排序算法对数组[5,2,8,1,9]进行升序排序，第一趟partition后的结果是？',
        'user_answer': '[2,1,5,8,9]',
        'correct_answer': '[2,1,5,8,9]（以5为pivot）或[1,2,5,9,8]（取决于实现）',
        'subject': '数据结构',
        'mastery_level': 0.6,
        'review_count': 2,
        'created_at': now.subtract(const Duration(days: 5)).toIso8601String(),
        'updated_at': now.subtract(const Duration(days: 1)).toIso8601String(),
        'chapter': '排序算法',
        'difficulty': 3,
        'next_review_at': now.add(const Duration(days: 2)).toIso8601String(),
        'ai_analysis_summary':
            '你对partition过程的理解基本正确，但需要注意不同实现方式（Lomuto vs Hoare）会影响结果。建议画图模拟完整过程。',
      },
      {
        'id': 'error_2',
        'question_text': 'TCP三次握手过程中，如果第三次握手丢失会怎样？',
        'user_answer': '连接建立失败，需要重新开始',
        'correct_answer': '服务器会认为连接未建立，但客户端认为已建立。客户端发送数据时，服务器会回复RST。',
        'subject': '计算机网络',
        'mastery_level': 0.4,
        'review_count': 3,
        'created_at': now.subtract(const Duration(days: 7)).toIso8601String(),
        'updated_at': now.subtract(const Duration(days: 2)).toIso8601String(),
        'chapter': 'TCP协议',
        'difficulty': 4,
        'next_review_at': now.add(const Duration(days: 3)).toIso8601String(),
        'ai_analysis_summary':
            '这是一个经典的边界情况问题。关键是理解TCP的状态机：客户端进入ESTABLISHED，服务器仍在SYN_RCVD。',
      },
      {
        'id': 'error_3',
        'question_text': '进程和线程的主要区别是什么？',
        'user_answer': '进程是程序的运行实例，线程是进程内的执行单元',
        'correct_answer': '除了调度和资源分配外，更重要的是地址空间独立性：进程独立，线程共享。',
        'subject': '操作系统',
        'mastery_level': 0.7,
        'review_count': 1,
        'created_at': now.subtract(const Duration(days: 3)).toIso8601String(),
        'updated_at': now.subtract(const Duration(days: 1)).toIso8601String(),
        'chapter': '进程管理',
        'difficulty': 2,
        'next_review_at': now.add(const Duration(days: 4)).toIso8601String(),
        'ai_analysis_summary': '你的答案正确但不够深入。建议从"资源"和"调度"两个维度对比，理解为什么线程切换更快。',
      },
    ];
  }

  // --- 🧠 行为模式 Data ---
  List<BehaviorPatternModel> get demoBehaviorPatterns {
    final now = DateTime.now();
    return [
      BehaviorPatternModel(
        id: 'pattern_1',
        userId: 'CS_Sophomore_12345',
        patternName: '下午效率高峰',
        patternType: 'productive',
        description: '你在下午3-5点的专注时长和任务完成率明显高于其他时段',
        solutionText: '建议将高难度任务（如算法题、系统设计）安排在下午时段，早上用于复习和预习',
        evidenceIds: ['frag_1', 'frag_2', 'frag_3'],
        isArchived: false,
        createdAt: now.subtract(const Duration(days: 7)),
        updatedAt: now.subtract(const Duration(days: 1)),
      ),
      BehaviorPatternModel(
        id: 'pattern_2',
        userId: 'CS_Sophomore_12345',
        patternName: '番茄工作法适配良好',
        patternType: 'productive',
        description: '使用番茄工作法时，你的平均专注时长提升32%，任务完成率提升45%',
        solutionText: '继续保持使用番茄工作法，可以尝试在休息时间做一些拉伸运动',
        isArchived: false,
        createdAt: now.subtract(const Duration(days: 10)),
        updatedAt: now.subtract(const Duration(days: 2)),
      ),
      BehaviorPatternModel(
        id: 'pattern_3',
        userId: 'CS_Sophomore_12345',
        patternName: '周末学习动力不足',
        patternType: 'barrier',
        description: '周末的学习时长仅为工作日的40%，任务完成率下降60%',
        solutionText: '建议周末早上安排1-2小时的轻量学习任务，利用社群功能与同学互相督促',
        isArchived: false,
        createdAt: now.subtract(const Duration(days: 14)),
        updatedAt: now.subtract(const Duration(days: 3)),
      ),
    ];
  }

  // --- 📢 通知中心 Data ---
  List<Map<String, dynamic>> get demoNotifications {
    final now = DateTime.now();
    return [
      {
        'id': 'notif_1',
        'type': 'achievement',
        'title': '🏆 解锁新成就',
        'message': '恭喜你获得"连续学习7天"成就！',
        'created_at': now.subtract(const Duration(hours: 1)).toIso8601String(),
        'is_read': false,
      },
      {
        'id': 'notif_2',
        'type': 'task_reminder',
        'title': '⏰ 任务提醒',
        'message': '你有1个任务即将到期：数据结构 - 二叉树遍历算法',
        'created_at': now.subtract(const Duration(hours: 3)).toIso8601String(),
        'is_read': false,
      },
      {
        'id': 'notif_3',
        'type': 'cognitive_insight',
        'title': '💡 新的学习洞察',
        'message': '发现你在下午3-5点效率最高，已为你生成优化建议',
        'created_at': now.subtract(const Duration(hours: 6)).toIso8601String(),
        'is_read': true,
      },
      {
        'id': 'notif_4',
        'type': 'community',
        'title': '💬 社群动态',
        'message': 'Alice_Codes 回复了你的帖子',
        'created_at': now.subtract(const Duration(days: 1)).toIso8601String(),
        'is_read': true,
      },
      {
        'id': 'notif_5',
        'type': 'plan_progress',
        'title': '🎯 计划进度',
        'message': '你的"数据结构期中冲刺"计划已完成70%，还剩7天！',
        'created_at': now.subtract(const Duration(days: 1)).toIso8601String(),
        'is_read': true,
      },
      {
        'id': 'notif_6',
        'type': 'capsule_ready',
        'title': '🎁 新认知胶囊',
        'message': '为你生成了一个关于"递归思维"的深度洞察',
        'created_at': now.subtract(const Duration(days: 2)).toIso8601String(),
        'is_read': true,
      },
    ];
  }

  // --- 👥 好友列表 Data ---
  List<Map<String, dynamic>> get demoFriends => [
        {
          'id': 'friend_1',
          'username': 'Alice_Codes',
          'avatar_url': 'https://api.dicebear.com/9.x/avataaars/png?seed=Alice',
          'flame_level': 12,
          'is_online': true,
          'recent_activity': '刚刚完成了一个React项目',
        },
        {
          'id': 'friend_2',
          'username': 'Bob_Dev',
          'avatar_url': 'https://api.dicebear.com/9.x/avataaars/png?seed=Bob',
          'flame_level': 18,
          'is_online': false,
          'recent_activity': '2小时前学习了算法',
        },
        {
          'id': 'friend_3',
          'username': 'Carol_学习',
          'avatar_url': 'https://api.dicebear.com/9.x/avataaars/png?seed=Carol',
          'flame_level': 15,
          'is_online': true,
          'recent_activity': '正在专注学习中',
        },
        {
          'id': 'friend_4',
          'username': 'David_求知',
          'avatar_url': 'https://api.dicebear.com/9.x/avataaars/png?seed=David',
          'flame_level': 10,
          'is_online': false,
          'recent_activity': '5小时前完成了数据库任务',
        },
        {
          'id': 'friend_5',
          'username': 'Emma_效率',
          'avatar_url': 'https://api.dicebear.com/9.x/avataaars/png?seed=Emma',
          'flame_level': 20,
          'is_online': true,
          'recent_activity': '30分钟前获得新成就',
        },
      ];

  // --- 🤝 责任伙伴 Data ---
  List<Map<String, dynamic>> get demoAccountabilityPartners => [
        {
          'id': 'partner_1',
          'partner_id': 'friend_1',
          'partner_name': 'Alice_Codes',
          'partner_avatar':
              'https://api.dicebear.com/9.x/avataaars/png?seed=Alice',
          'status': 'active',
          'started_at': DateTime.now()
              .subtract(const Duration(days: 14))
              .toIso8601String(),
          'my_streak': 7,
          'partner_streak': 5,
          'total_checkins': 12,
          'last_checkin': DateTime.now()
              .subtract(const Duration(hours: 3))
              .toIso8601String(),
        },
        {
          'id': 'partner_2',
          'partner_id': 'friend_3',
          'partner_name': 'Carol_学习',
          'partner_avatar':
              'https://api.dicebear.com/9.x/avataaars/png?seed=Carol',
          'status': 'active',
          'started_at': DateTime.now()
              .subtract(const Duration(days: 7))
              .toIso8601String(),
          'my_streak': 3,
          'partner_streak': 4,
          'total_checkins': 8,
          'last_checkin': DateTime.now()
              .subtract(const Duration(hours: 1))
              .toIso8601String(),
        },
      ];

  // --- 🏘️ 群组 Data ---
  List<Map<String, dynamic>> get demoGroups => [
        {
          'id': 'group_1',
          'name': '算法刷题小分队',
          'description': '每天一起刷算法题，互相监督共同进步',
          'avatar_url': 'https://api.dicebear.com/9.x/shapes/png?seed=algo',
          'member_count': 15,
          'is_member': true,
          'is_public': true,
          'created_at': DateTime.now()
              .subtract(const Duration(days: 30))
              .toIso8601String(),
          'last_activity': DateTime.now()
              .subtract(const Duration(hours: 1))
              .toIso8601String(),
        },
        {
          'id': 'group_2',
          'name': 'Flutter开发者联盟',
          'description': 'Flutter/Dart技术交流群，分享开发经验和最佳实践',
          'avatar_url': 'https://api.dicebear.com/9.x/shapes/png?seed=flutter',
          'member_count': 42,
          'is_member': true,
          'is_public': true,
          'created_at': DateTime.now()
              .subtract(const Duration(days: 60))
              .toIso8601String(),
          'last_activity': DateTime.now()
              .subtract(const Duration(minutes: 30))
              .toIso8601String(),
        },
        {
          'id': 'group_3',
          'name': 'AI学习小组',
          'description': '人工智能和机器学习爱好者社区',
          'avatar_url': 'https://api.dicebear.com/9.x/shapes/png?seed=ai',
          'member_count': 28,
          'is_member': false,
          'is_public': true,
          'created_at': DateTime.now()
              .subtract(const Duration(days: 15))
              .toIso8601String(),
          'last_activity': DateTime.now()
              .subtract(const Duration(hours: 2))
              .toIso8601String(),
        },
      ];

  // --- 💬 群组消息 Data ---
  List<Map<String, dynamic>> get demoGroupMessages => [
        {
          'id': 'msg_1',
          'group_id': 'group_1',
          'sender_id': 'friend_1',
          'sender_name': 'Alice_Codes',
          'sender_avatar':
              'https://api.dicebear.com/9.x/avataaars/png?seed=Alice',
          'content': '今天有人一起刷动态规划吗？',
          'created_at': DateTime.now()
              .subtract(const Duration(minutes: 30))
              .toIso8601String(),
          'reactions': [
            {'emoji': '👍', 'count': 3}
          ],
        },
        {
          'id': 'msg_2',
          'group_id': 'group_1',
          'sender_id': 'friend_2',
          'sender_name': 'Bob_Dev',
          'sender_avatar':
              'https://api.dicebear.com/9.x/avataaars/png?seed=Bob',
          'content': '我来！正好要做背包问题的练习',
          'created_at': DateTime.now()
              .subtract(const Duration(minutes: 25))
              .toIso8601String(),
          'reactions': [
            {'emoji': '💪', 'count': 2}
          ],
        },
        {
          'id': 'msg_3',
          'group_id': 'group_1',
          'sender_id': 'friend_3',
          'sender_name': 'Carol_学习',
          'sender_avatar':
              'https://api.dicebear.com/9.x/avataaars/png?seed=Carol',
          'content': '加油！动态规划确实需要多练 💯',
          'created_at': DateTime.now()
              .subtract(const Duration(minutes: 20))
              .toIso8601String(),
          'reactions': [],
        },
      ];

  // --- 📊 责任伙伴打卡热力图 Data ---
  List<Map<String, dynamic>> get demoAccountabilityHeatmap {
    final now = DateTime.now();
    final List<Map<String, dynamic>> heatmap = [];

    // 生成过去365天的模拟数据
    for (int i = 0; i < 365; i++) {
      final date = now.subtract(Duration(days: i));
      // 随机生成打卡强度 (0-4)
      final intensity =
          i < 30 ? (date.weekday % 3 == 0 ? 2 : 0) : (i % 7 == 0 ? 3 : (i % 3));
      heatmap.add({
        'date': date.toIso8601String().split('T')[0],
        'intensity': intensity,
        'checkins': intensity > 0
            ? [
                {'time': '09:00', 'content': '早起学习一小时！'},
                if (intensity > 2) {'time': '21:00', 'content': '晚上复习总结'},
              ]
            : [],
      });
    }
    return heatmap;
  }

  // --- 🔥 打卡记录 Data ---
  List<Map<String, dynamic>> get demoCheckins => [
        {
          'id': 'checkin_1',
          'partnership_id': 'partner_1',
          'user_id': 'CS_Sophomore_12345',
          'content': '今天完成了算法 chapter 3 的学习，理解了递归的核心思想！',
          'created_at': DateTime.now()
              .subtract(const Duration(hours: 3))
              .toIso8601String(),
          'likes_count': 2,
          'encouragements': [
            {'user_id': 'friend_1', 'message': '太棒了！递归确实需要多练习 💪'},
          ],
        },
        {
          'id': 'checkin_2',
          'partnership_id': 'partner_1',
          'user_id': 'friend_1',
          'content': '早起完成了 React Hooks 的复习，感觉理解更深了',
          'created_at': DateTime.now()
              .subtract(const Duration(hours: 5))
              .toIso8601String(),
          'likes_count': 3,
          'encouragements': [],
        },
      ];

  // --- 🎯 视觉元素 Data ---
  List<Map<String, dynamic>> get demoVisualElements => [
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
          'preview_url':
              'https://images.unsplash.com/photo-1486402638-b5b?w=200',
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

  // --- 🏆 成就系统扩展 Data ---
  List<Map<String, dynamic>> get demoAchievementDetails => [
        {
          'id': 'achv_1',
          'name': '初出茅庐',
          'description': '完成第一个任务',
          'type': 'milestone',
          'rarity': 'common',
          'icon_url': '🎯',
          'is_unlocked': true,
          'unlocked_at': DateTime.now()
              .subtract(const Duration(days: 30))
              .toIso8601String(),
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
          'unlocked_at': DateTime.now()
              .subtract(const Duration(days: 10))
              .toIso8601String(),
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
}

/// Provider for DemoDataService
final demoDataServiceProvider =
    Provider<DemoDataService>((ref) => DemoDataService());
