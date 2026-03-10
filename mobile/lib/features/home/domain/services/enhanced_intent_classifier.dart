/// Enhanced intent classifier with better coverage
///
/// Matches backend intent types:
/// - chat, create, update, delete, query
/// - learn, review, translation, prism, sprint
enum EnhancedIntentType {
  chat,
  task,
  capsule,
  translation,
  prism,
  sprint,
  learn,
  review,
}

class IntentClassification {
  const IntentClassification({
    required this.type,
    required this.confidence,
  });

  final EnhancedIntentType type;
  final double confidence; // 0.0 - 1.0
}

class EnhancedIntentClassifier {
  const EnhancedIntentClassifier._();

  /// Classify user input with confidence scoring
  /// Returns null if no clear intent detected
  ///
  /// Supports both Chinese and English keywords for bilingual intent detection.
  static IntentClassification? classify(String text) {
    if (text.isEmpty) return null;

    final lower = text.toLowerCase();
    var maxScore = 0.0;
    EnhancedIntentType? bestType;

    // === Priority 1: Special modes (high confidence keywords) ===

    // Translation (翻译)
    if (_containsAny(lower, [
      // Chinese
      '翻译', '翻译成', '怎么说', '是什么意思', '什么意思',
      // English
      'translate', 'translation', 'how do you say', 'what does this mean',
      'in english', 'in chinese', 'to english', 'to chinese',
    ])) {
      final score = _calculateScore(lower, {
        '翻译': 1.0,
        'translate': 1.0,
        'translation': 0.95,
        '翻译成': 0.95,
        '是什么意思': 0.9,
        'what does this mean': 0.9,
        '怎么说': 0.85,
        'how do you say': 0.85,
        'in english': 0.85,
        'in chinese': 0.85,
        'to english': 0.85,
        'to chinese': 0.85,
      });
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.translation;
      }
    }

    // Cognitive Prism (认知棱镜)
    if (_containsAny(lower, [
      // Chinese
      '认知棱镜', '行为分析', '学习习惯', '我的画像', '周报', '学习分析',
      // English
      'cognitive prism', 'behavior analysis', 'learning habit', 'my profile',
      'weekly report', 'learning analysis', 'persona', 'insight',
    ])) {
      final score = _calculateScore(lower, {
        '认知棱镜': 1.0,
        'cognitive prism': 1.0,
        '行为分析': 1.0,
        'behavior analysis': 1.0,
        '学习习惯': 0.95,
        'learning habit': 0.95,
        '我的画像': 0.9,
        'my profile': 0.9,
        'persona': 0.9,
        '周报': 0.85,
        'weekly report': 0.85,
        '学习分析': 0.85,
        'learning analysis': 0.85,
        'insight': 0.8,
      });
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.prism;
      }
    }

    // Sprint/Focus Mode (冲刺/专注)
    if (_containsAny(lower, [
      // Chinese
      '冲刺', '专注模式', '突击', '进入冲刺', '开始专注', '专注',
      // English
      'sprint', 'focus mode', 'deep focus', 'start sprint', 'enter focus',
      'pomodoro', 'focus session', 'deep work',
    ])) {
      final score = _calculateScore(lower, {
        '冲刺': 1.0,
        'sprint': 1.0,
        '专注模式': 0.95,
        'focus mode': 0.95,
        'deep focus': 0.95,
        '突击': 0.9,
        '专注': 0.88,
        'start sprint': 0.9,
        'enter focus': 0.9,
        'pomodoro': 0.85,
        'focus session': 0.85,
        'deep work': 0.85,
      });
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.sprint;
      }
    }

    // === Priority 2: Learning related ===

    // Review (复习)
    if (_containsAny(lower, [
      // Chinese
      '复习', '回顾', '过一遍', '温习',
      // English
      'review', 'go over', 'revise', 'refresh', 'recap',
    ])) {
      final score = _calculateScore(lower, {
        '复习': 1.0,
        'review': 1.0,
        '回顾': 0.9,
        'go over': 0.9,
        '过一遍': 0.85,
        '温习': 0.9,
        'revise': 0.85,
        'refresh': 0.85,
        'recap': 0.85,
      });
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.review;
      }
    }

    // Learn (学习)
    if (_containsAny(lower, [
      // Chinese
      '学习', '学一下', '了解一下', '学学',
      // English
      'learn', 'study', 'teach me', 'explain', 'show me how',
    ])) {
      // Exclude combinations with other intents
      if (!lower.contains('复习') && !lower.contains('翻译') && !lower.contains('冲刺') && !lower.contains('专注模式') &&
          !lower.contains('review') && !lower.contains('translate') && !lower.contains('sprint')) {
        final score = _calculateScore(lower, {
          '学习': 0.9,
          'learn': 0.9,
          'study': 0.9,
          '学一下': 0.85,
          'teach me': 0.85,
          'explain': 0.8,
          'show me how': 0.8,
        });
        if (score > maxScore) {
          maxScore = score;
          bestType = EnhancedIntentType.learn;
        }
      }
    }

    // === Priority 3: Task management ===

    // Task/创建
    if (_containsAny(lower, [
      // Chinese
      '任务', '提醒', '创建', '新建', '做', '创建一个', '添加任务',
      // English
      'task', 'todo', 'remind', 'create', 'new task', 'add task', 'reminder',
      'schedule', 'set a reminder',
    ])) {
      // Exclude interference words
      if (!lower.contains('冲刺') && !lower.contains('翻译') && !lower.contains('sprint') && !lower.contains('translate')) {
        final score = _calculateScore(lower, {
          '创建任务': 1.0,
          'create task': 1.0,
          'new task': 1.0,
          '新建任务': 1.0,
          '提醒我': 1.0,
          'remind me': 1.0,
          'set a reminder': 1.0,
          '创建一个提醒': 1.0,
          '任务': 0.85,
          'task': 0.85,
          'todo': 0.85,
          'reminder': 0.85,
          '创建一个': 0.8,
          '做': 0.5,  // Lower weight for standalone "做"
        });
        if (score > maxScore) {
          maxScore = score;
          bestType = EnhancedIntentType.task;
        }
      }
    }

    // === Priority 4: Cognitive capsule (emotional expressions) ===

    // Capsule (好奇心胶囊)
    if (_containsAny(lower, [
      // Chinese
      '烦', '感觉', '觉得', '好奇', '想知道', '疑惑', '不明白', '困惑',
      // English
      'curious', 'wonder', 'confused', 'frustrated', 'annoyed', 'not sure',
      "don't understand", "can't figure out", 'feeling', 'wondering',
    ])) {
      // Exclude combinations with other intents
      if (!lower.contains('学习') && !lower.contains('复习') && !lower.contains('翻译') &&
          !lower.contains('learn') && !lower.contains('review') && !lower.contains('translate')) {
        final score = _calculateScore(lower, {
          '烦': 0.9,
          'frustrated': 0.9,
          'annoyed': 0.9,
          '感觉': 0.7,
          'feeling': 0.7,
          '觉得': 0.6,  // Lower weight, "我觉得" is too common
          '好奇': 0.95,
          'curious': 0.95,
          '想知道': 0.85,
          'wonder': 0.85,
          'wondering': 0.85,
          '疑惑': 0.85,
          'confused': 0.85,
          '困惑': 0.85,
          "don't understand": 0.85,
          "can't figure out": 0.85,
          '不明白': 0.85,
          'not sure': 0.8,
        });
        if (score > maxScore) {
          maxScore = score;
          bestType = EnhancedIntentType.capsule;
        }
      }
    }

    // === Priority 5: Default chat ===

    // Long text tends to be chat
    if (text.length > 15 && maxScore < 0.5) {
      bestType = EnhancedIntentType.chat;
      maxScore = 0.5; // Set to 0.5 to meet the minimum threshold
    }

    // Return result only if confidence is high enough
    if (bestType != null && maxScore >= 0.5) {
      return IntentClassification(
        type: bestType,
        confidence: maxScore,
      );
    }

    return null;  // No clear intent detected
  }

  /// Calculate score based on keyword matches
  static double _calculateScore(String text, Map<String, double> keywords) {
    var score = 0.0;
    for (final entry in keywords.entries) {
      if (text.contains(entry.key)) {
        score = score > entry.value ? score : entry.value;
      }
    }
    return score;
  }

  /// Check if text contains any of the keywords
  static bool _containsAny(String text, List<String> keywords) => keywords.any((keyword) => text.contains(keyword));
}
