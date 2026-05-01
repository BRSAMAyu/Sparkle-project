import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';
import 'package:sparkle/features/cognitive/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/i_cognitive_repository.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class MockCognitiveRepository implements ICognitiveRepository {
  @override
  Future<CognitiveFragmentModel> createFragment(
    CognitiveFragmentCreate data,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 500));
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
  Future<List<CognitiveFragmentModel>> getFragments({
    int limit = 20,
    int skip = 0,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 800));
    final zh = I18nService.instance.isChinese;
    return [
      CognitiveFragmentModel(
        id: 'frag-1',
        userId: 'user-1',
        sourceType: 'reflection',
        content: zh ? '每次遇到难题就会想要刷手机，这似乎是一种逃避机制。' : 'When facing difficult problems, I want to scroll through my phone. This seems to be an escape mechanism.',
        createdAt: DateTime.now().subtract(const Duration(hours: 2)),
        sentiment: 'negative',
        tags: ['procrastination', 'anxiety'],
      ),
      CognitiveFragmentModel(
        id: 'frag-2',
        userId: 'user-1',
        sourceType: 'task_note',
        content: zh ? '完成高数作业后感到非常有成就感，这种正反馈很重要。' : 'Felt a great sense of achievement after completing advanced math homework. This positive feedback is important.',
        taskId: 'task-123',
        createdAt: DateTime.now().subtract(const Duration(days: 1)),
        sentiment: 'positive',
        tags: ['achievement', 'math'],
      ),
      CognitiveFragmentModel(
        id: 'frag-3',
        userId: 'user-1',
        sourceType: 'daily_review',
        content: zh ? '今天原本计划背单词，但是被社团活动打断了，需要调整计划弹性。' : 'Originally planned to memorize vocabulary today, but was interrupted by club activities. Need to adjust plan flexibility.',
        createdAt: DateTime.now().subtract(const Duration(days: 2)),
        sentiment: 'neutral',
        tags: ['planning', 'interruption'],
      ),
    ];
  }

  @override
  Future<List<BehaviorPatternModel>> getBehaviorPatterns() async {
    await Future<void>.delayed(const Duration(milliseconds: 1000));
    final zh = I18nService.instance.isChinese;
    return [
      BehaviorPatternModel(
        id: 'pattern-1',
        userId: 'user-1',
        patternName: zh ? '畏难性拖延' : 'Avoidance Procrastination',
        patternType: PatternType.emotional,
        description: zh ? '当面对难度较大或不确定的任务（如物理大作业）时，倾向于通过处理琐事（如整理桌面、回消息）来推迟开始时间。' : 'When facing difficult or uncertain tasks (like physics assignments), tend to delay by handling trivial tasks (like organizing desktop, replying to messages).',
        solutionText: zh ? '尝试"5分钟起步法"：告诉自己只做5分钟，降低心理门槛。' : 'Try the "5-minute start method": tell yourself you\'ll only do 5 minutes to lower the mental barrier.',
        evidenceIds: ['frag-1'],
        confidenceScore: 0.82,
        frequency: 6,
        isArchived: false,
        lastObservedAt: DateTime.now().subtract(const Duration(hours: 18)),
        createdAt: DateTime.now().subtract(const Duration(days: 5)),
        updatedAt: DateTime.now().subtract(const Duration(days: 1)),
      ),
      BehaviorPatternModel(
        id: 'pattern-2',
        userId: 'user-1',
        patternName: zh ? '深夜突击习惯' : 'Late Night Cramming Habit',
        patternType: PatternType.execution,
        description: zh ? '习惯在晚上10点后才开始处理最重要、最烧脑的学习任务，导致睡眠延迟和次日精力不足。' : 'Habit of starting the most important and brain-intensive study tasks after 10 PM, leading to delayed sleep and low energy the next day.',
        solutionText: zh ? '调整生物钟，尝试在早上头脑最清醒时攻克一道难题。' : 'Adjust your biological clock and try to tackle a difficult problem when your mind is clearest in the morning.',
        evidenceIds: [],
        confidenceScore: 0.74,
        frequency: 4,
        isArchived: false,
        lastObservedAt: DateTime.now().subtract(const Duration(days: 3)),
        createdAt: DateTime.now().subtract(const Duration(days: 10)),
        updatedAt: DateTime.now().subtract(const Duration(days: 3)),
      ),
      BehaviorPatternModel(
        id: 'pattern-3',
        userId: 'user-1',
        patternName: zh ? '完美主义倾向' : 'Perfectionist Tendency',
        patternType: PatternType.cognitive,
        description: zh ? '在做PPT或写报告时，过度纠结于排版和措辞，导致核心内容产出效率低下。' : 'When making PPTs or writing reports, overly focused on layout and wording, resulting in low efficiency of core content output.',
        solutionText: zh ? '采用"草稿-迭代"模式，先完成内容框架，最后统一调整格式。' : 'Adopt the "draft-iterate" mode: complete the content framework first, then adjust the format uniformly at the end.',
        evidenceIds: [],
        confidenceScore: 0.68,
        frequency: 9,
        isArchived: true,
        lastObservedAt: DateTime.now().subtract(const Duration(days: 18)),
        lastDecayAt: DateTime.now().subtract(const Duration(days: 7)),
        createdAt: DateTime.now().subtract(const Duration(days: 30)),
        updatedAt: DateTime.now().subtract(const Duration(days: 15)),
      ),
    ];
  }
}
