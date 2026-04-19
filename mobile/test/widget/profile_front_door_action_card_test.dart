import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

void main() {
  testWidgets('profile front door card renders claims and evidence classes', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: Scaffold(
          body: SingleChildScrollView(
            child: ActionCard(
              action: WidgetPayload(
                type: 'profile_front_door',
                data: {
                  'summary': '我目前最稳定的一条判断是「成就反馈响应 = supportive」。',
                  'claims': [
                    {
                      'id': 'achievement_motivation_response',
                      'label': '成就反馈响应',
                      'value': 'supportive',
                      'summary': '最近的成就反馈更容易带动你继续推进。',
                      'confidence_label': '86%',
                      'evidence_label': '编译结论',
                      'source': 'achievement_signals',
                      'freshness': 'fresh',
                      'correction_hint': '可直接在聊天里纠正',
                    },
                  ],
                  'predictions': [
                    {
                      'id': 'overload_risk',
                      'label': 'overload_risk',
                      'summary': '最近任务切换偏频繁，过载风险上升。',
                      'evidence_label': '推断/预测',
                      'recommended_action': '先缩窄下一步范围',
                    },
                  ],
                  'unknowns': [
                    {
                      'id': 'uncertainty:peak_focus_hours',
                      'description': '高效时段还不够稳定。',
                    },
                  ],
                  'calibration': {
                    'summary': '校准姿态：supported；最近有 1 条用户纠正；因此我会更保守地表达结论',
                  },
                  'binding_note': '当前前门展示的是 canonical 结论 + 来源标记。',
                },
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('展开'));
    await tester.pumpAndSettle();

    expect(find.text('成就反馈响应'), findsOneWidget);
    expect(find.text('supportive'), findsOneWidget);
    expect(find.text('编译结论'), findsOneWidget);
    expect(find.text('推断/预测'), findsOneWidget);
    expect(find.textContaining('高效时段还不够稳定'), findsOneWidget);
    expect(find.textContaining('校准姿态'), findsOneWidget);
  });

  testWidgets('profile front door card forwards correction prompt actions', (
    tester,
  ) async {
    String? capturedPrompt;

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: Scaffold(
          body: SingleChildScrollView(
            child: ActionCard(
              action: WidgetPayload(
                type: 'profile_front_door',
                data: {
                  'summary': '这是当前画像前门。',
                  'claims': [
                    {
                      'id': 'achievement_motivation_response',
                      'label': '成就反馈响应',
                      'value': 'progress_praise',
                      'summary': '最近的成就反馈更容易带动你继续推进。',
                      'confidence_label': '86%',
                      'evidence_label': '编译结论',
                      'source': 'achievement_signals',
                      'freshness': 'fresh',
                      'correction_hint': '可直接在聊天里纠正',
                      'actions': [
                        {
                          'label': '这条不对',
                          'type': 'prompt',
                          'prompt':
                              '请把画像里的「成就反馈响应」这条标记为不对（target_id=achievement_motivation_response，action=wrong），并基于更新后的 canonical 画像重新告诉我你现在怎么看我。',
                        },
                      ],
                    },
                  ],
                },
              ),
              onWidgetAction: (actionType, payload) async {
                if (actionType == 'prompt') {
                  capturedPrompt = payload['prompt']?.toString();
                }
              },
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('展开'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('这条不对'));
    await tester.pump();

    expect(
        capturedPrompt, contains('target_id=achievement_motivation_response'));
    expect(capturedPrompt, contains('action=wrong'));
  });
}
