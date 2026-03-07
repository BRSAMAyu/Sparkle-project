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
            onWidgetAction: (actionType, payload) {
              if (actionType == 'prompt') {
                receivedPrompt = payload['prompt']?.toString();
              }
            },
          ),
        ),
      ),
    );

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
            onWidgetAction: (actionType, payload) {
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
}
