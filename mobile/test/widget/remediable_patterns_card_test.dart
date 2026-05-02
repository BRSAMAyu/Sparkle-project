import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/error_book/data/models/remediable_pattern.dart';
import 'package:sparkle/features/error_book/presentation/widgets/remediable_patterns_card.dart';

import '../shared/i18n_test_helper.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(setUpI18nForTesting);
  setUpAll(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('renders remediable pattern and accepts generated template',
      (tester) async {
    var accepted = false;
    final pattern = RemediablePattern(
      id: 'pattern-1',
      knowledgeNodeName: '二次函数顶点',
      errorType: 'calculation_error',
      errorTypeLabel: '计算过程',
      subjectCode: 'math',
      chapter: '二次函数',
      errorCount: 4,
      confidence: 0.87,
      averageMastery: 0.38,
      suggestedDurationMinutes: 32,
      rootCauseSummary: '代入后没有验算符号。',
      representativeErrorId: 'error-1',
      errorIds: const ['error-1', 'error-2', 'error-3', 'error-4'],
      lastSeenAt: DateTime(2026, 5, 1, 12),
    );
    const template = RemedialTaskTemplate(
      patternId: 'pattern-1',
      title: '补救练习：二次函数顶点 · 计算过程',
      objective: '修复重复出现的计算错因。',
      estimatedMinutes: 32,
      difficulty: 3,
      errorType: 'calculation_error',
      successCriteria: const ['能解释错因', '能做对 1 道同类题'],
      minimumOutput: '完成 1 张错因对照卡',
      structuredSteps: const [
        StructuredRemediationStep(
          order: 1,
          title: '定位错因',
          instruction: '标出错误一步。',
          durationMinutes: 5,
          checkpoint: '能指出错误开始的位置。',
        ),
      ],
      guideJson: const {},
      taskPayload: const {},
    );

    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: Scaffold(
            body: RemediablePatternsCard(
              patterns: [pattern],
              onGenerateTemplate: (_) async => template,
              onAcceptTemplate: (_, __) async {
                accepted = true;
              },
            ),
          ),
        ),
      ),
    );

    expect(find.text('可补救错因'), findsOneWidget);
    expect(find.text('二次函数顶点'), findsOneWidget);
    expect(find.text('4 道错题'), findsOneWidget);

    await tester.tap(find.text('生成补救任务'));
    await tester.pumpAndSettle();

    expect(find.text('补救练习：二次函数顶点 · 计算过程'), findsOneWidget);
    expect(find.text('完成 1 张错因对照卡'), findsOneWidget);

    await tester.tap(find.text('接受并加入今日计划'));
    await tester.pumpAndSettle();

    expect(accepted, isTrue);
    expect(find.text('补救任务已加入今日计划'), findsOneWidget);
  });
}
