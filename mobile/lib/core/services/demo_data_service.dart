import 'dart:math';

import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/data/models/knowledge_detail_model.dart';
import 'package:sparkle/data/models/plan_model.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/data/models/user_model.dart';
import 'package:uuid/uuid.dart';

class DemoDataService {
  factory DemoDataService() => _instance;
  DemoDataService._internal();
  static bool isDemoMode = false;

  static final DemoDataService _instance = DemoDataService._internal();

  final _uuid = const Uuid();
  final _random = Random();

  String? _currentAvatarUrl;

  // --- User Data ---
  UserModel get demoUser => UserModel(
    id: 'CS_Sophomore_12345',
    username: 'AI_Learner_02',
    email: 'learner@sparkle.ai',
    nickname: 'AI_Learner_02',
    avatarUrl: _currentAvatarUrl ?? 'https://api.dicebear.com/9.x/avataaars/png?seed=AI_Learner_02',
    flameLevel: 15,
    flameBrightness: 0.85,
    depthPreference: 0.7,
    curiosityPreference: 0.8,
    isActive: true,
    createdAt: DateTime.now().subtract(const Duration(days: 45)),
    updatedAt: DateTime.now(),
    pushPreferences: PushPreferences(
      
    ),
  );

  void updateDemoAvatar(String url) {
    _currentAvatarUrl = url;
  }

  // --- Task Data ---
  List<TaskModel> get demoTasks {
    final now = DateTime.now();
    return [
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '数据结构 - 链表实现',
        type: TaskType.learning,
        tags: ['CS', 'Data Structures', 'C++'],
        estimatedMinutes: 120,
        difficulty: 3,
        energyCost: 3,
        status: TaskStatus.pending,
        priority: 3, // High
        dueDate: now.add(const Duration(days: 45)), 
        createdAt: now.subtract(const Duration(days: 2)),
        updatedAt: now,
      ),
       TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '离散数学 - 图论基础',
        type: TaskType.learning,
        tags: ['Math', 'Graph Theory'],
        estimatedMinutes: 90,
        difficulty: 4,
        energyCost: 4,
        status: TaskStatus.inProgress,
        priority: 2, // Medium
        dueDate: now.add(const Duration(days: 7)),
        createdAt: now.subtract(const Duration(days: 5)),
        updatedAt: now,
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '计算机系统 - CPU调度算法',
        type: TaskType.learning,
        tags: ['CS', 'OS'],
        estimatedMinutes: 60,
        difficulty: 3,
        energyCost: 2,
        status: TaskStatus.completed,
        priority: 1, // Low
        dueDate: now.subtract(const Duration(days: 3)),
        completedAt: now.subtract(const Duration(days: 3)),
        actualMinutes: 55,
        createdAt: now.subtract(const Duration(days: 10)),
        updatedAt: now.subtract(const Duration(days: 3)),
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '数字电路 - 逻辑门实验',
        type: TaskType.training,
        tags: ['Hardware', 'Lab'],
        estimatedMinutes: 180,
        difficulty: 2,
        energyCost: 3,
        status: TaskStatus.pending,
        priority: 2,
        dueDate: now.add(const Duration(days: 3)),
        createdAt: now,
        updatedAt: now,
      ),
      TaskModel(
        id: _uuid.v4(),
        userId: 'CS_Sophomore_12345',
        title: '摄影技巧 - 光影构图学习',
        type: TaskType.learning, 
        tags: ['Hobby', 'Photography'],
        estimatedMinutes: 45,
        difficulty: 1,
        energyCost: 1,
        status: TaskStatus.completed,
        priority: 1,
        dueDate: now.subtract(const Duration(days: 1)),
        completedAt: now.subtract(const Duration(days: 1)),
        actualMinutes: 50,
        createdAt: now.subtract(const Duration(days: 4)),
        updatedAt: now,
      ),
    ];
  }

  // --- Galaxy Data ---
  GalaxyGraphResponse get demoGalaxy {
    final nodes = <GalaxyNodeModel>[];
    
    // Core Subjects & Colors
    final subjects = ['数据结构', '离散数学', '计算机系统', '数字电路', '摄影', '文学'];
    final subjectColors = {
      '数据结构': '#4CAF50', // Green
      '离散数学': '#2196F3', // Blue
      '计算机系统': '#FFC107', // Amber
      '数字电路': '#9C27B0', // Purple
      '摄影': '#E91E63', // Pink
      '文学': '#795548', // Brown
    };

    // Generate ~500 nodes
    for (var i = 0; i < 500; i++) {
      final subject = subjects[i % subjects.length];
      final isCore = i < 20; 
      final status = _determineNodeStatus(i);
      final isUnlocked = status != NodeStatus.locked;
      final mastery = status == NodeStatus.mastered ? 100 : (status == NodeStatus.unlocked ? 30 : 0);
      
      String? parentId;
      if (!isCore) {
          parentId = 'node_${i % 20}'; 
      }

      nodes.add(GalaxyNodeModel(
        id: 'node_$i',
        name: isCore ? subject : '$subject - 知识点 ${i+1}',
        importance: isCore ? 5 : _random.nextInt(3) + 1,
        sector: SectorEnum.values[i % SectorEnum.values.length],
        isUnlocked: isUnlocked,
        masteryScore: mastery,
        baseColor: subjectColors[subject],
        parentId: parentId,
      ),);
    }

    return GalaxyGraphResponse(
        nodes: nodes, 
        userFlameIntensity: 0.85,
    );
  }

  // Helper enum for logic (internal use)
  NodeStatus _determineNodeStatus(int index) {
    if (index > 350) return NodeStatus.locked;
    if (index < 50) return NodeStatus.mastered;
    if (index < 130) return NodeStatus.review;
    return NodeStatus.unlocked;
  }

  /// Get demo node detail for a specific node ID
  KnowledgeDetailResponse getDemoNodeDetail(String nodeId) {
    // Parse node index from ID
    final indexStr = nodeId.replaceAll('node_', '');
    final index = int.tryParse(indexStr) ?? 0;

    final subjects = ['数据结构', '离散数学', '计算机系统', '数字电路', '摄影', '文学'];
    final subject = subjects[index % subjects.length];
    final isCore = index < 20;
    final status = _determineNodeStatus(index);

    // Determine sector based on index
    final sectorValues = ['COSMOS', 'TECH', 'ART', 'CIVILIZATION', 'LIFE', 'WISDOM', 'VOID'];
    final sectorCode = sectorValues[index % sectorValues.length];

    return KnowledgeDetailResponse(
      node: KnowledgeNodeDetail(
        id: nodeId,
        name: isCore ? subject : '$subject - 知识点 ${index + 1}',
        nameEn: isCore ? subject : '$subject - Point ${index + 1}',
        description: '这是关于$subject的知识点描述。该知识点涵盖了核心概念和应用场景，帮助你更好地理解和掌握相关内容。',
        keywords: [subject, '计算机科学', '基础知识'],
        importanceLevel: isCore ? 5 : _random.nextInt(3) + 1,
        sectorCode: sectorCode,
        isSeed: isCore,
        sourceType: isCore ? 'seed' : 'llm_expanded',
        parentId: isCore ? null : 'node_${index % 20}',
        subjectId: index % subjects.length + 1,
        subjectName: subject,
        createdAt: DateTime.now().subtract(Duration(days: index)),
      ),
      relations: [
        if (index > 0)
          NodeRelation(
            id: 'rel_${index}_prev',
            sourceNodeId: 'node_${index - 1}',
            targetNodeId: nodeId,
            relationType: 'prerequisite',
            strength: 0.8,
            sourceNodeName: '$subject - 知识点 $index',
            targetNodeName: isCore ? subject : '$subject - 知识点 ${index + 1}',
          ),
        if (index < 499)
          NodeRelation(
            id: 'rel_${index}_next',
            sourceNodeId: nodeId,
            targetNodeId: 'node_${index + 1}',
            relationType: 'related',
            strength: 0.6,
            sourceNodeName: isCore ? subject : '$subject - 知识点 ${index + 1}',
            targetNodeName: '$subject - 知识点 ${index + 2}',
          ),
      ],
      relatedTasks: demoTasks.take(2).toList(),
      relatedPlans: demoPlans.map((p) => RelatedPlan(
        id: p.id,
        title: p.name,
        planType: p.type.toString().split('.').last,
        status: p.isActive ? 'active' : 'completed',
        targetDate: p.targetDate,
      ),).toList(),
      userStats: KnowledgeUserStats(
        masteryScore: status == NodeStatus.mastered ? 95.0 :
                      status == NodeStatus.review ? 60.0 :
                      status == NodeStatus.unlocked ? 30.0 : 0.0,
        totalStudyMinutes: (index % 10 + 1) * 15,
        studyCount: index % 5 + 1,
        isUnlocked: status != NodeStatus.locked,
        isFavorite: index % 7 == 0,
        lastStudyAt: DateTime.now().subtract(Duration(days: index % 7)),
        nextReviewAt: status == NodeStatus.review
            ? DateTime.now().add(Duration(days: index % 3 + 1))
            : null,
        decayPaused: index % 10 == 0,
      ),
    );
  }

  // --- Plan Data ---
  List<PlanModel> get demoPlans {
    final now = DateTime.now();
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
      ),
    ];
  }

  // --- Chat Data ---
  List<ChatMessageModel> get demoChatHistory => [
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
        content: '理解你的感受。这种焦虑和自责其实是恶性循环的一部分。我们试着接纳这种情绪，而不是对抗它.\n\n根据你的学习记录，你这周已经在《离散数学》上投入了7.5小时，这非常棒。也许你可以试着先做一个简单的任务来找回状态？',
        createdAt: DateTime.now().subtract(const Duration(hours: 1, minutes: 59)),
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
        content: '没问题。根据你的学习进度，建议先复习 **单链表的插入与删除** 操作.\n\n正在为您生成数据结构学习计划...', 
        createdAt: DateTime.now().subtract(const Duration(minutes: 29)),
        toolResults: [
           ToolResultModel(success: true, toolName: 'generate_plan', data: {'status': 'completed'}),
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

你可以试着手写一下 `reverseList` 函数吗？''',
        createdAt: DateTime.now().subtract(const Duration(minutes: 28)),
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
}

enum NodeStatus { locked, unlocked, review, mastered }