import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';

void main() {
  testWidgets('next actions widget triggers prompt callback', (tester) async {
    String? receivedPrompt;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActionCard(
            action: WidgetPayload(
              type: 'next_actions',
              data: {
                'title': '先把计划落地到这几步',
                'actions': [
                  {'label': '继续追问细节', 'type': 'prompt', 'prompt': '继续追问细节'},
                ],
                'retry_options': [
                  {'label': '补充材料', 'type': 'prompt', 'prompt': '补充材料'},
                ],
                'recovery_message': '如果当前节奏太重，我可以继续帮你压缩。',
              },
            ),
            onWidgetAction: (actionType, payload) async {
              if (actionType == 'prompt') {
                receivedPrompt = payload['prompt']?.toString();
              }
            },
          ),
        ),
      ),
    );

    await tester.tap(find.text('展开'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('继续追问细节'));
    await tester.pump();

    expect(receivedPrompt, '继续追问细节');
    expect(find.text('先把计划落地到这几步'), findsOneWidget);
    expect(find.text('如果当前节奏太重，我可以继续帮你压缩。'), findsOneWidget);
    expect(find.text('如果这轮还不够，可以这样继续：'), findsOneWidget);
  });

  testWidgets('source summary renders evidence cards', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActionCard(
            action: WidgetPayload(
              type: 'source_summary',
              data: {
                'headline': '我会先给综合判断，再把依据、反例和风险摊开。',
                'confidence_band': 'high',
                'completion_state': 'done',
                'why_this_answer': '这轮优先按观点、依据和风险组织了回答。',
                'evidence_summary': '这轮回答带有可展开的依据来源。',
                'citations': [
                  {'title': '线性代数讲义', 'section_title': '特征值'},
                ],
              },
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('展开'));
    await tester.pumpAndSettle();
    expect(find.text('可信度高'), findsOneWidget);
    expect(find.text('本轮已完成'), findsOneWidget);
    expect(find.text('为什么这样回答'), findsOneWidget);
    expect(find.text('这轮回答带有可展开的依据来源。'), findsOneWidget);
    expect(find.text('线性代数讲义'), findsOneWidget);
    expect(find.text('特征值'), findsOneWidget);
  });

  testWidgets('blocked input request renders recovery path', (tester) async {
    String? receivedPrompt;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActionCard(
            action: WidgetPayload(
              type: 'blocked_input_request',
              data: {
                'title': '要定位错因，我还需要题目证据',
                'recovery_message': '没有题目、步骤或截图，我没法把根因钉准。',
                'reason': '这轮优先按错因、证据和修复动作组织了回答。',
                'retry_options': ['补充题目', '上传材料'],
              },
            ),
            onWidgetAction: (actionType, payload) async {
              receivedPrompt = payload['prompt']?.toString();
            },
          ),
        ),
      ),
    );

    expect(find.text('要定位错因，我还需要题目证据'), findsOneWidget);
    expect(find.text('没有题目、步骤或截图，我没法把根因钉准。'), findsOneWidget);

    await tester.tap(find.text('补充题目'));
    await tester.pump();

    expect(receivedPrompt, '补充题目');
  });

  testWidgets('evolution card renders expandable adaptation details', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActionCard(
            action: WidgetPayload(
              type: 'evolution_card',
              data: {
                'headline': '系统正在根据你的反馈继续调整',
                'summary': '我发现你最近的任务偏难了，帮你调轻了一些。',
                'adaptation_records': [
                  {
                    'what_changed': '把任务难度偏移调整为 -0.1',
                    'why': '最近 3 次反馈都觉得太难',
                    'expected_effect': '降低任务启动门槛',
                  },
                ],
              },
            ),
          ),
        ),
      ),
    );

    expect(find.text('系统正在根据你的反馈继续调整'), findsOneWidget);
    expect(find.text('我发现你最近的任务偏难了，帮你调轻了一些。'), findsOneWidget);

    await tester.tap(find.text('了解详情'));
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('把任务难度偏移调整为 -0.1'), findsOneWidget);
    expect(find.text('为什么：最近 3 次反馈都觉得太难'), findsOneWidget);
    expect(find.text('预期效果：降低任务启动门槛'), findsOneWidget);
  });

  testWidgets('progress card renders highlights and comparisons', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActionCard(
            action: WidgetPayload(
              type: 'progress_card',
              data: {
                'highlights': [
                  '你这周完成了 8 个任务，比上周多 3 个。',
                  '线性代数掌握度提升了 15%。',
                ],
                'streak_info': {
                  'current_streak': 12,
                  'max_streak': 12,
                },
                'comparisons': {
                  'tasks_completed': {
                    'current': 8,
                    'previous': 5,
                  },
                },
              },
            ),
          ),
        ),
      ),
    );

    expect(find.textContaining('你这周完成了 8 个任务'), findsOneWidget);
    expect(find.textContaining('当前连胜 12 天'), findsOneWidget);

    await tester.tap(find.text('查看对比数据'));
    await tester.pump(const Duration(milliseconds: 250));

    expect(find.text('Tasks Completed'), findsOneWidget);
    expect(find.text('8 / 上期 5'), findsOneWidget);
  });

  testWidgets('reflection card submits and enters completed state', (
    tester,
  ) async {
    String? selectedOption;
    String? freeText;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActionCard(
            action: WidgetPayload(
              type: 'reflection_card',
              data: {
                'feedback_id': 'fb_1',
                'question': '你觉得难在哪里？',
                'options': ['概念没理解', '题量太大'],
              },
            ),
            onWidgetAction: (actionType, payload) async {
              selectedOption = payload['selected_option']?.toString();
              freeText = payload['free_text']?.toString();
            },
          ),
        ),
      ),
    );

    await tester.tap(find.text('概念没理解'));
    await tester.enterText(find.byType(TextField), '矩阵变换看不懂');
    await tester.tap(find.text('提交反馈'));
    await tester.pump(const Duration(milliseconds: 250));

    expect(selectedOption, '概念没理解');
    expect(freeText, '矩阵变换看不懂');
    expect(find.text('谢谢你的反馈，我会据此优化后续计划。'), findsOneWidget);
  });
}
