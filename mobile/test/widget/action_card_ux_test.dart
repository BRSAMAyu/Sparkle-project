import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

void main() {
  testWidgets('next actions widget triggers prompt callback', (tester) async {
    String? receivedPrompt;

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
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
    expect(find.text('点击重试'), findsOneWidget);  // l10n.chatNextActionsRetryHint
  });

  testWidgets('source summary renders evidence cards', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
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
    expect(find.text('高'), findsOneWidget);  // confidence_band: 'high' maps to l10n.chatConfidenceHigh
    expect(find.text('补全完成'), findsOneWidget);  // completion_state: 'done' maps to l10n.chatCompletionDone
    expect(find.text('这轮回答带有可展开的依据来源。'), findsOneWidget);
    expect(find.text('线性代数讲义'), findsOneWidget);
    expect(find.text('特征值'), findsOneWidget);
  });

  testWidgets('blocked input request renders recovery path', (tester) async {
    String? receivedPrompt;

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
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
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
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

    await tester.tap(find.text('了解更多'));  // l10n.commonLearnMore
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('把任务难度偏移调整为 -0.1'), findsOneWidget);
    expect(find.text('最近 3 次反馈都觉得太难'), findsOneWidget);  // chatEvolutionWhy just returns the arg
    expect(find.text('降低任务启动门槛'), findsOneWidget);  // chatEvolutionExpectedEffect just returns the arg
  });

  testWidgets('progress card renders highlights and comparisons', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
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
    // chatStreakSummary returns "{arg0} {arg1}" which is "12 12"
    expect(find.textContaining('12'), findsWidgets);

    await tester.tap(find.text('查看对比数据'));
    await tester.pump(const Duration(milliseconds: 250));

    // The comparison format is "current previous" per l10n.chatComparisonCurrentPrevious
    expect(find.textContaining('8'), findsWidgets);
  });

  testWidgets('reflection card submits and enters completed state', (
    tester,
  ) async {
    String? selectedOption;
    String? freeText;

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
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
    expect(find.text('感谢您的反馈！'), findsOneWidget);  // chatFeedbackThanks
  });
}
