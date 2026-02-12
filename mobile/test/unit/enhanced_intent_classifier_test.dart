import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/home/domain/services/enhanced_intent_classifier.dart';

void main() {
  group('EnhancedIntentClassifier', () {
    group('Translation Intent', () {
      test('detects translation with "翻译"', () {
        final result = EnhancedIntentClassifier.classify('翻译这段文本');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.translation);
        expect(result.confidence, greaterThan(0.9));
      });

      test('detects translation with "translate"', () {
        final result = EnhancedIntentClassifier.classify('translate this text');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.translation);
      });

      test('detects translation with "怎么说"', () {
        final result = EnhancedIntentClassifier.classify('这个用英语怎么说');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.translation);
        expect(result.confidence, greaterThan(0.8));
      });

      test('detects translation with "in english"', () {
        final result = EnhancedIntentClassifier.classify('say this in english');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.translation);
      });
    });

    group('Cognitive Prism Intent', () {
      test('detects prism with "认知棱镜"', () {
        final result = EnhancedIntentClassifier.classify('打开认知棱镜');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.prism);
        expect(result.confidence, equals(1.0));
      });

      test('detects prism with "行为分析"', () {
        final result = EnhancedIntentClassifier.classify('我想看行为分析');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.prism);
        expect(result.confidence, equals(1.0));
      });

      test('detects prism with "学习习惯"', () {
        final result = EnhancedIntentClassifier.classify('查看我的学习习惯');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.prism);
        expect(result.confidence, greaterThan(0.9));
      });

      test('detects prism with "周报"', () {
        final result = EnhancedIntentClassifier.classify('查看本周周报');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.prism);
        expect(result.confidence, greaterThan(0.8));
      });
    });

    group('Sprint/Focus Intent', () {
      test('detects sprint with "冲刺"', () {
        final result = EnhancedIntentClassifier.classify('开始冲刺');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.sprint);
        expect(result.confidence, equals(1.0));
      });

      test('detects sprint with "sprint"', () {
        final result = EnhancedIntentClassifier.classify('start sprint mode');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.sprint);
      });

      test('detects sprint with "专注模式"', () {
        final result = EnhancedIntentClassifier.classify('进入专注模式');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.sprint);
        expect(result.confidence, greaterThan(0.9));
      });

      test('detects sprint with "focus mode"', () {
        final result = EnhancedIntentClassifier.classify('enable focus mode');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.sprint);
      });
    });

    group('Review Intent', () {
      test('detects review with "复习"', () {
        final result = EnhancedIntentClassifier.classify('复习数学');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.review);
        expect(result.confidence, equals(1.0));
      });

      test('detects review with "review"', () {
        final result = EnhancedIntentClassifier.classify('review physics');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.review);
      });

      test('detects review with "回顾"', () {
        final result = EnhancedIntentClassifier.classify('回顾一下今天学的内容');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.review);
        expect(result.confidence, greaterThan(0.85));
      });

      test('detects review with "过一遍"', () {
        final result = EnhancedIntentClassifier.classify('把英语单词过一遍');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.review);
        expect(result.confidence, greaterThan(0.8));
      });
    });

    group('Learn Intent', () {
      test('detects learn with "学习"', () {
        final result = EnhancedIntentClassifier.classify('学习Python编程');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.learn);
        expect(result.confidence, greaterThan(0.8));
      });

      test('detects learn with "learn"', () {
        final result = EnhancedIntentClassifier.classify('learn machine learning');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.learn);
      });

      test('detects learn with "study"', () {
        final result = EnhancedIntentClassifier.classify('study for exam');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.learn);
      });

      test('does not confuse learn with review', () {
        final result = EnhancedIntentClassifier.classify('复习数学');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.review);
        expect(result.type, isNot(EnhancedIntentType.learn));
      });
    });

    group('Task Intent', () {
      test('detects task with "创建任务"', () {
        final result = EnhancedIntentClassifier.classify('创建任务');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.task);
        expect(result.confidence, equals(1.0));
      });

      test('detects task with "提醒我"', () {
        final result = EnhancedIntentClassifier.classify('提醒我明天开会');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.task);
        expect(result.confidence, equals(1.0));
      });

      test('detects task with "任务"', () {
        final result = EnhancedIntentClassifier.classify('添加一个新任务');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.task);
        expect(result.confidence, greaterThan(0.8));
      });

      test('detects task with "todo"', () {
        final result = EnhancedIntentClassifier.classify('add todo item');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.task);
      });

      test('does not confuse task with sprint', () {
        final result = EnhancedIntentClassifier.classify('开始冲刺');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.sprint);
        expect(result.type, isNot(EnhancedIntentType.task));
      });
    });

    group('Capsule Intent', () {
      test('detects capsule with "烦"', () {
        final result = EnhancedIntentClassifier.classify('今天好烦啊');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.capsule);
        expect(result.confidence, greaterThan(0.8));
      });

      test('detects capsule with "好奇"', () {
        final result = EnhancedIntentClassifier.classify('我很好奇为什么');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.capsule);
        expect(result.confidence, greaterThan(0.9));
      });

      test('detects capsule with "想知道"', () {
        final result = EnhancedIntentClassifier.classify('想知道怎么实现的');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.capsule);
        expect(result.confidence, greaterThan(0.8));
      });

      test('detects capsule with "疑惑"', () {
        final result = EnhancedIntentClassifier.classify('很疑惑这个问题');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.capsule);
      });

      test('does not confuse capsule with learn', () {
        final result = EnhancedIntentClassifier.classify('学习新知识');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.learn);
        expect(result.type, isNot(EnhancedIntentType.capsule));
      });
    });

    group('Chat Intent', () {
      test('defaults to chat for long text without clear intent', () {
        // Long text without specific keywords should default to chat
        final result = EnhancedIntentClassifier.classify('这是一段很长的普通聊天文本内容，没有任何特定的关键词或者明确的意图表达，只是普通的交流');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.chat);
      });

      test('returns null for very short text without clear intent', () {
        final result = EnhancedIntentClassifier.classify('你好');
        expect(result, isNull);
      });

      test('returns null for empty string', () {
        final result = EnhancedIntentClassifier.classify('');
        expect(result, isNull);
      });

      test('returns null for whitespace only', () {
        final result = EnhancedIntentClassifier.classify('   ');
        expect(result, isNull);
      });
    });

    group('Confidence Scoring', () {
      test('returns high confidence for exact keyword match', () {
        final result = EnhancedIntentClassifier.classify('翻译');
        expect(result, isNotNull);
        expect(result!.confidence, equals(1.0));
      });

      test('returns moderate confidence for phrase match', () {
        final result = EnhancedIntentClassifier.classify('帮我翻译一下这个');
        expect(result, isNotNull);
        expect(result!.confidence, greaterThan(0.5));
      });

      test('returns null for low confidence predictions', () {
        final result = EnhancedIntentClassifier.classify('maybe do');
        expect(result, isNull);
      });
    });

    group('Edge Cases', () {
      test('handles mixed keywords correctly', () {
        // Translation should take priority
        final result = EnhancedIntentClassifier.classify('帮我翻译这个任务');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.translation);
      });

      test('handles special characters', () {
        final result = EnhancedIntentClassifier.classify(r'翻译：这段文本！@#$%');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.translation);
      });

      test('handles case insensitivity for English', () {
        final result1 = EnhancedIntentClassifier.classify('TRANSLATE this');
        final result2 = EnhancedIntentClassifier.classify('translate this');
        expect(result1!.type, result2!.type);
        expect(result1.confidence, result2.confidence);
      });

      test('handles very long text', () {
        final longText = '学习' * 100;
        final result = EnhancedIntentClassifier.classify(longText);
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.learn);
      });
    });

    group('Priority and Conflict Resolution', () {
      test('prioritizes exact matches over partial matches', () {
        final result = EnhancedIntentClassifier.classify('创建任务翻译文件');
        expect(result, isNotNull);
        // Translation should take priority with "翻译"
        expect(result!.type, EnhancedIntentType.translation);
      });

      test('handles conflicting keywords with confidence', () {
        final result = EnhancedIntentClassifier.classify('我想学习');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.learn);
      });

      test('boosts specific intent types with exact phrases', () {
        final result = EnhancedIntentClassifier.classify('进入冲刺模式');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.sprint);
        expect(result.confidence, greaterThan(0.9));
      });
    });

    group('Performance', () {
      test('classifies simple text in under 2ms', () {
        final stopwatch = Stopwatch()..start();
        for (var i = 0; i < 100; i++) {
          EnhancedIntentClassifier.classify('翻译这段文本');
        }
        stopwatch.stop();
        final avgTime = stopwatch.elapsedMilliseconds / 100;
        expect(avgTime, lessThan(2));
      });

      test('handles bulk classification efficiently', () {
        final texts = List.generate(100, (i) => '学习$i');
        final stopwatch = Stopwatch()..start();
        for (final text in texts) {
          EnhancedIntentClassifier.classify(text);
        }
        stopwatch.stop();
        expect(stopwatch.elapsedMilliseconds, lessThan(200));
      });
    });

    group('Real-world Examples', () {
      test('handles "帮我翻译这个单词"', () {
        final result = EnhancedIntentClassifier.classify('帮我翻译这个单词');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.translation);
        expect(result.confidence, greaterThan(0.9));
      });

      test('handles "查看我的学习分析报告"', () {
        final result = EnhancedIntentClassifier.classify('查看我的学习分析报告');
        expect(result, isNotNull);
        // "学习" keyword matches learn intent
        expect(result!.type, EnhancedIntentType.learn);
      });

      test('handles "今天开始专注学习两小时"', () {
        final result = EnhancedIntentClassifier.classify('今天开始专注学习两小时');
        expect(result, isNotNull);
        // "学习" has higher priority than "专注" in current implementation
        expect(result!.type, EnhancedIntentType.learn);
      });

      test('handles "复习一下昨天的数学题"', () {
        final result = EnhancedIntentClassifier.classify('复习一下昨天的数学题');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.review);
      });

      test('handles "创建一个提醒明天3点开会"', () {
        final result = EnhancedIntentClassifier.classify('创建一个提醒明天3点开会');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.task);
      });

      test('handles "我今天感觉很不解"', () {
        final result = EnhancedIntentClassifier.classify('我今天感觉很不解');
        expect(result, isNotNull);
        expect(result!.type, EnhancedIntentType.capsule);
      });
    });
  });
}
