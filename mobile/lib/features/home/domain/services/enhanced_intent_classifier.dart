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
  static IntentClassification? classify(String text) {
    if (text.isEmpty) return null;

    final lower = text.toLowerCase();
    var maxScore = 0.0;
    EnhancedIntentType? bestType;

    // === 优先级1: 特殊模式（高置信度关键词）===

    // Translation (翻译)
    if (_containsAny(lower, ['翻译', 'translate', '翻译成', '怎么说', 'in english', 'in chinese', '是什么意思'])) {
      final score = _calculateScore(lower, {
        '翻译': 1.0,
        'translate': 1.0,
        '翻译成': 0.95,
        '是什么意思': 0.9,
        '怎么说': 0.85,
        'in english': 0.85,
        'in chinese': 0.85,
      });
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.translation;
      }
    }

    // Cognitive Prism (认知棱镜)
    if (_containsAny(lower, ['认知棱镜', '行为分析', '学习习惯', '我的画像', '周报', '学习分析'])) {
      final score = _calculateScore(lower, {
        '认知棱镜': 1.0,
        '行为分析': 1.0,
        '学习习惯': 0.95,
        '我的画像': 0.9,
        '周报': 0.85,
        '学习分析': 0.85,
      });
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.prism;
      }
    }

    // Sprint/Focus Mode (冲刺/专注)
    if (_containsAny(lower, ['冲刺', 'sprint', '专注模式', 'focus mode', '突击', '进入冲刺', '开始专注', '专注'])) {
      final score = _calculateScore(lower, {
        '冲刺': 1.0,
        'sprint': 1.0,
        '专注模式': 0.95,
        'focus mode': 0.95,
        '突击': 0.9,
        '专注': 0.88,
      });
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.sprint;
      }
    }

    // === 优先级2: 学习相关 ===

    // Review (复习)
    if (_containsAny(lower, ['复习', 'review', '回顾', '过一遍'])) {
      final score = _calculateScore(lower, {
        '复习': 1.0,
        'review': 1.0,
        '回顾': 0.9,
        '过一遍': 0.85,
      });
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.review;
      }
    }

    // Learn (学习)
    if (_containsAny(lower, ['学习', 'learn', 'study', '学一下', '了解一下'])) {
      // 排除与其他意图的组合，但允许与"专注"共存（优先级已经在sprint中处理）
      if (!lower.contains('复习') && !lower.contains('翻译') && !lower.contains('冲刺') && !lower.contains('专注模式')) {
        final score = _calculateScore(lower, {
          '学习': 0.9,
          'learn': 0.9,
          'study': 0.9,
          '学一下': 0.85,
        });
        if (score > maxScore) {
          maxScore = score;
          bestType = EnhancedIntentType.learn;
        }
      }
    }

    // === 优先级3: 任务管理 ===

    // Task/创建
    if (_containsAny(lower, ['任务', 'task', '提醒', 'remind', '创建', 'create', '新建', '做', 'todo', '创建一个'])) {
      // 排除干扰词
      if (!lower.contains('冲刺') && !lower.contains('翻译')) {
        final score = _calculateScore(lower, {
          '创建任务': 1.0,
          '新建任务': 1.0,
          '提醒我': 1.0,
          '创建一个提醒': 1.0,
          '任务': 0.85,
          'todo': 0.85,
          '创建一个': 0.8,
          '做': 0.5,  // 降低单独"做"的权重
        });
        if (score > maxScore) {
          maxScore = score;
          bestType = EnhancedIntentType.task;
        }
      }
    }

    // === 优先级4: 认知胶囊（情感表达）===

    // Capsule (好奇心胶囊)
    if (_containsAny(lower, ['烦', '感觉', '觉得', '好奇', '想知道', '疑惑', '不明白'])) {
      // 排除与其他意图的组合
      if (!lower.contains('学习') && !lower.contains('复习') && !lower.contains('翻译')) {
        final score = _calculateScore(lower, {
          '烦': 0.9,
          '感觉': 0.7,
          '觉得': 0.6,  // 降低权重，因为"我觉得"太常见
          '好奇': 0.95,
          '想知道': 0.85,
          '疑惑': 0.85,
        });
        if (score > maxScore) {
          maxScore = score;
          bestType = EnhancedIntentType.capsule;
        }
      }
    }

    // === 优先级5: 默认聊天 ===

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
