#!/usr/bin/env dart
/// Interactive Intent Classifier Test Runner
///
/// Run this script to interactively test the enhanced intent classifier:
///   dart test/interactive_intent_test.dart
///
/// Or in Flutter:
///   flutter test test/interactive_intent_test.dart

import 'package:sparkle/features/home/domain/services/enhanced_intent_classifier.dart';

void main() {
  // Test cases
  final testCases = [
    // Translation
    _TestCase('翻译这个单词', EnhancedIntentType.translation, 1.0, '精确匹配'),
    _TestCase('in English怎么说', EnhancedIntentType.translation, 0.85, '短语匹配'),
    _TestCase('这是什么意思', EnhancedIntentType.translation, 0.9, '短语匹配'),

    // Prism
    _TestCase('我的学习习惯', EnhancedIntentType.prism, 0.95, '短语匹配'),
    _TestCase('查看行为分析', EnhancedIntentType.prism, 1.0, '精确关键词'),
    _TestCase('生成周报', EnhancedIntentType.prism, 0.85, '短语匹配'),

    // Sprint
    _TestCase('进入冲刺模式', EnhancedIntentType.sprint, 1.0, '精确匹配'),
    _TestCase('开始专注', EnhancedIntentType.sprint, 0.88, '关键词匹配'),
    _TestCase('专注模式学习', EnhancedIntentType.sprint, 0.95, '组合模式'),

    // Learn
    _TestCase('学习英语', EnhancedIntentType.learn, 0.9, '精确匹配'),
    _TestCase('study math', EnhancedIntentType.learn, 0.9, '精确匹配'),

    // Review
    _TestCase('复习数学', EnhancedIntentType.review, 1.0, '精确匹配'),
    _TestCase('review一下', EnhancedIntentType.review, 1.0, '短语匹配'),
    _TestCase('过一遍昨天的题', EnhancedIntentType.review, 0.85, '短语匹配'),

    // Task
    _TestCase('创建任务', EnhancedIntentType.task, 1.0, '精确关键词'),
    _TestCase('提醒我明天3点', EnhancedIntentType.task, 1.0, '组合模式'),
    _TestCase('创建一个提醒', EnhancedIntentType.task, 1.0, '精确短语'),

    // Capsule
    _TestCase('我很烦', EnhancedIntentType.capsule, 0.9, '关键词匹配'),
    _TestCase('好奇想知道', EnhancedIntentType.capsule, 0.95, '组合模式'),
    _TestCase('疑惑不解', EnhancedIntentType.capsule, 0.85, '短语匹配'),

    // Edge cases
    _TestCase('', null, 0.0, '空字符串'),
    _TestCase('   ', null, 0.0, '纯空格'),
    _TestCase('a', null, 0.0, '单字符'),
    _TestCase('你好呀', null, 0.0, '简短问候'),
  ];

  var passed = 0;
  var failed = 0;

  for (var i = 0; i < testCases.length; i++) {
    final testCase = testCases[i];
    final result = EnhancedIntentClassifier.classify(testCase.input);

    bool testPassed;
    if (testCase.expectedType == null) {
      testPassed = result == null;
    } else {
      testPassed = result?.type == testCase.expectedType &&
                   (result!.confidence - testCase.expectedConfidence).abs() < 0.15;
    }

    if (testPassed) {
      passed++;
      final typeStr = result?.type.name ?? 'null';
      final confStr = result?.confidence.toStringAsFixed(2) ?? '0.00';
      print('✓ [$i] ${testCase.input.padRight(25)} → $typeStr (conf: $confStr) | ${testCase.description}');
    } else {
      failed++;
      final expectedStr = testCase.expectedType?.name ?? 'null';
      final gotStr = result?.type.name ?? 'null';
      final gotConf = result?.confidence.toStringAsFixed(2) ?? '0.00';
      print('✗ [$i] ${testCase.input.padRight(25)} → FAILED | expected: $expectedStr (${testCase.expectedConfidence}) | got: $gotStr ($gotConf) | ${testCase.description}');
    }
  }

  print('');
  print('─' * 60);
  print('测试结果汇总:');
  print('  通过: $passed');
  print('  失败: $failed');
  print('  总数: ${testCases.length}');
  print('  通过率: ${(passed / testCases.length * 100).toStringAsFixed(1)}%');
  print('─' * 60);

  if (failed == 0) {
    print('');
    print('🎉 所有测试通过！增强意图分类器工作正常。');
  }

  print('');
  print('💡 提示: 你可以修改此文件添加更多测试用例');
}

class _TestCase {

  _TestCase(this.input, this.expectedType, this.expectedConfidence, this.description);
  final String input;
  final EnhancedIntentType? expectedType;
  final double expectedConfidence;
  final String description;
}
