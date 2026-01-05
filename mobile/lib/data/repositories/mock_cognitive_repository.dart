import 'package:sparkle/data/models/behavior_pattern_model.dart';
import 'package:sparkle/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/data/repositories/i_cognitive_repository.dart';

class MockCognitiveRepository implements ICognitiveRepository {
  @override
  Future<CognitiveFragmentModel> createFragment(
      CognitiveFragmentCreate data,) async {
    await Future.delayed(const Duration(milliseconds: 500));
    return CognitiveFragmentModel(
      id: 'mock-frag-${DateTime.now().millisecondsSinceEpoch}',
      userId: 'user-1',
      sourceType: data.sourceType,
      content: data.content,
      taskId: data.taskId,
      createdAt: DateTime.now(),
      sentiment: 'neutral',
      tags: ['mock', 'new'],
    );
  }

  @override
  Future<List<CognitiveFragmentModel>> getFragments(
      {int limit = 20, int skip = 0,}) async {
    await Future.delayed(const Duration(milliseconds: 800));
    return [
      CognitiveFragmentModel(
        id: 'frag-1',
        userId: 'user-1',
        sourceType: 'reflection',
        content: '每次遇到难题就会想要刷手机，这似乎是一种逃避机制。',
        createdAt: DateTime.now().subtract(const Duration(hours: 2)),
        sentiment: 'negative',
        tags: ['procrastination', 'anxiety'],
      ),
      CognitiveFragmentModel(
        id: 'frag-2',
        userId: 'user-1',
        sourceType: 'task_note',
        content: '完成高数作业后感到非常有成就感，这种正反馈很重要。',
        taskId: 'task-123',
        createdAt: DateTime.now().subtract(const Duration(days: 1)),
        sentiment: 'positive',
        tags: ['achievement', 'math'],
      ),
      CognitiveFragmentModel(
        id: 'frag-3',
        userId: 'user-1',
        sourceType: 'daily_review',
        content: '今天原本计划背单词，但是被社团活动打断了，需要调整计划弹性。',
        createdAt: DateTime.now().subtract(const Duration(days: 2)),
        sentiment: 'neutral',
        tags: ['planning', 'interruption'],
      ),
    ];
  }

  @override
  Future<List<BehaviorPatternModel>> getBehaviorPatterns() async {
    await Future.delayed(const Duration(milliseconds: 1000));
    return [
      BehaviorPatternModel(
        id: 'pattern-1',
        userId: 'user-1',
        patternName: '畏难性拖延',
        patternType: 'emotional', // cognitive, emotional, execution
        description: '当面对难度较大或不确定的任务（如物理大作业）时，倾向于通过处理琐事（如整理桌面、回消息）来推迟开始时间。',
        solutionText: '尝试"5分钟起步法"：告诉自己只做5分钟，降低心理门槛。',
        evidenceIds: ['frag-1'],
        isArchived: false,
        createdAt: DateTime.now().subtract(const Duration(days: 5)),
        updatedAt: DateTime.now().subtract(const Duration(days: 1)),
      ),
      BehaviorPatternModel(
        id: 'pattern-2',
        userId: 'user-1',
        patternName: '深夜突击习惯',
        patternType: 'execution',
        description: '习惯在晚上10点后才开始处理最重要、最烧脑的学习任务，导致睡眠延迟和次日精力不足。',
        solutionText: '调整生物钟，尝试在早上头脑最清醒时攻克一道难题。',
        evidenceIds: [],
        isArchived: false,
        createdAt: DateTime.now().subtract(const Duration(days: 10)),
        updatedAt: DateTime.now().subtract(const Duration(days: 3)),
      ),
      BehaviorPatternModel(
        id: 'pattern-3',
        userId: 'user-1',
        patternName: '完美主义倾向',
        patternType: 'cognitive',
        description: '在做PPT或写报告时，过度纠结于排版和措辞，导致核心内容产出效率低下。',
        solutionText: '采用"草稿-迭代"模式，先完成内容框架，最后统一调整格式。',
        evidenceIds: [],
        isArchived: true, // 已克服
        createdAt: DateTime.now().subtract(const Duration(days: 30)),
        updatedAt: DateTime.now().subtract(const Duration(days: 15)),
      ),
    ];
  }
}
