import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/context_receipt_bar.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  testWidgets('receipt actions emit corrective prompts', (tester) async {
    String? selectedPrompt;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ContextReceiptBar(
            rawMetadata: const {
              'context_receipt': {
                'used_count': 1,
                'excluded_count': 0,
                'used_names': <String>['线性代数课件'],
                'excluded_names': <String>[],
                'decision_reason': '已优先引用课件',
                'retrieval_mode': 'courseware',
              },
            },
            onActionSelected: (prompt) => selectedPrompt = prompt,
          ),
        ),
      ),
    );

    await tester.tap(find.text('已优先引用课件'));
    await tester.pumpAndSettle();

    expect(find.text('按课件重讲'), findsOneWidget);
    expect(find.text('排除此资料'), findsOneWidget);
    expect(find.text('换成历年真题'), findsOneWidget);

    await tester.tap(find.text('排除此资料'));
    await tester.pumpAndSettle();

    expect(selectedPrompt, contains('线性代数课件'));
    expect(selectedPrompt, contains('排除'));
    expect(find.text('排除此资料'), findsNothing);
  });

  testWidgets('social context receipt shows privacy detail and opt out action',
      (tester) async {
    String? selectedPrompt;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ContextReceiptBar(
            rawMetadata: const {
              'social_context_receipt': {
                'type': 'social_context_receipt',
                'used_count': 1,
                'used_names': <String>['学习伙伴动态'],
                'excluded_names': <String>[],
                'decision_reason': '参考了学习伙伴的动态',
                'privacy_boundary': '只使用匿名角色标签，不展示伙伴姓名、原文或联系方式。',
                'retrieval_mode': 'social_context',
              },
            },
            onActionSelected: (prompt) => selectedPrompt = prompt,
          ),
        ),
      ),
    );

    expect(find.text('参考了学习伙伴的动态'), findsOneWidget);

    await tester.tap(find.text('参考了学习伙伴的动态'));
    await tester.pumpAndSettle();

    expect(find.text('社群参考详情'), findsOneWidget);
    expect(find.text('只使用匿名角色标签，不展示伙伴姓名、原文或联系方式。'), findsOneWidget);
    expect(find.text('不需要参考他的进度'), findsOneWidget);

    await tester.tap(find.text('不需要参考他的进度'));
    await tester.pumpAndSettle();

    expect(selectedPrompt, contains('不要参考学习伙伴的进度'));
  });

  testWidgets('receipt sheet shows tool context sources', (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: ContextReceiptBar(
            rawMetadata: {
              'context_receipt': {
                'used_count': 0,
                'excluded_count': 0,
                'tool_count': 1,
                'used_tools': <Map<String, String>>[
                  {
                    'name': '计算器',
                    'summary': '完成一次complex复杂度计算',
                    'privacy_note': '只保存安全摘要，不保存原始内容。',
                  },
                ],
                'decision_reason': 'Aurora 已参考你刚刚的工具动作。',
              },
            },
          ),
        ),
      ),
    );

    await tester.tap(find.text('Aurora 已参考你刚刚的工具动作。'));
    await tester.pumpAndSettle();

    expect(find.text('使用的工具上下文（1）'), findsOneWidget);
    expect(find.text('计算器'), findsOneWidget);
    expect(find.text('完成一次complex复杂度计算'), findsOneWidget);
    expect(find.text('只保存安全摘要，不保存原始内容。'), findsOneWidget);
  });

  testWidgets('unified aurora receipts render all four quiet chips',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: ContextReceiptBar(
            rawMetadata: {
              'aurora_receipts': [
                {
                  'receipt_type': 'aurora_experience_receipt',
                  'summary': '这轮改成更短的推进方式。',
                  'what_changed': <String>['降低解释密度'],
                },
                {
                  'receipt_type': 'memory_reference_receipt',
                  'summary': '引用了 1 条相关记忆',
                  'referenced_memories': [
                    {'id': 'mem-1', 'content': '明天考高数'},
                  ],
                },
                {
                  'receipt_type': 'source_context_receipt',
                  'summary': '已优先引用课件',
                  'used_count': 1,
                  'used_names': <String>['线性代数课件'],
                },
                {
                  'receipt_type': 'next_action_changed_by_aurora',
                  'summary': '已把下一步拆小。',
                  'correctable': true,
                  'correction_options': <String>['这个判断不准确'],
                },
              ],
            },
          ),
        ),
      ),
    );

    expect(find.text('这轮改成更短的推进方式。'), findsOneWidget);
    expect(find.text('引用了 1 条相关记忆'), findsOneWidget);
    expect(find.text('已优先引用课件'), findsOneWidget);
    expect(find.text('已把下一步拆小。'), findsOneWidget);
  });

  testWidgets('receipt display preferences can hide one receipt class',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: ContextReceiptBar(
            enabledReceiptTypes: {'memory_reference_receipt'},
            rawMetadata: {
              'memory_reference_receipt': {
                'used_count': 1,
                'decision_reason': '引用了 1 条相关记忆',
                'referenced_memories': [
                  {'id': 'mem-1', 'content': '明天考高数'},
                ],
              },
              'context_receipt': {
                'used_count': 1,
                'used_names': <String>['线性代数课件'],
                'decision_reason': '已优先引用课件',
              },
            },
          ),
        ),
      ),
    );

    expect(find.text('引用了 1 条相关记忆'), findsOneWidget);
    expect(find.text('已优先引用课件'), findsNothing);
  });

  testWidgets('next action receipt correction emits corrective prompt',
      (tester) async {
    String? selectedPrompt;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ContextReceiptBar(
            rawMetadata: const {
              'spine_receipt': {
                'receipt_id': 'rcpt-1',
                'summary': '已把下一步拆小。',
                'correctable': true,
                'correction_options': <String>['这个判断不准确'],
              },
            },
            onActionSelected: (prompt) => selectedPrompt = prompt,
          ),
        ),
      ),
    );

    await tester.tap(find.text('已把下一步拆小。'));
    await tester.pumpAndSettle();

    expect(find.text('行动调整'), findsOneWidget);
    expect(find.text('这个判断不准确'), findsOneWidget);

    await tester.tap(find.text('这个判断不准确'));
    await tester.pumpAndSettle();

    expect(selectedPrompt, contains('这个判断不准确'));
    expect(selectedPrompt, contains('重新判断'));
  });
}
