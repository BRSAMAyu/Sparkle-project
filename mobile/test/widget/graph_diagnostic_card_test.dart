import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('graph diagnostic card renders weak nodes and forwards actions', (
    tester,
  ) async {
    String? routedTo;
    String? prompted;

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: Scaffold(
          body: SingleChildScrollView(
            child: ActionCard(
              action: WidgetPayload(
                type: 'graph_diagnostic',
                data: {
                  'summary': '当前最弱的是热力学第二定律。',
                  'weak_nodes': [
                    {
                      'node_id': 'node-1',
                      'node_name': '热力学第二定律',
                      'mastery': 41.0,
                      'why': '掌握度已经落到明显偏低区间。',
                      'prerequisite_names': ['热机效率'],
                      'downstream_names': ['熵增方向判断'],
                      'route': '/galaxy/node/node-1',
                      'prompt': '带我看看这个点为什么会卡住。',
                    },
                  ],
                  'recommended_next_review': [
                    {
                      'node_name': '热力学第二定律',
                      'mastery': 41.0,
                    },
                  ],
                  'binding_note': '这个诊断面只消费现有 graph / mastery 数据。',
                },
              ),
              onWidgetAction: (actionType, payload) async {
                if (actionType == 'route') {
                  routedTo = payload['route']?.toString();
                }
                if (actionType == 'prompt') {
                  prompted = payload['prompt']?.toString();
                }
              },
            ),
          ),
        ),
      ),
    );

    expect(find.text('最弱点'), findsOneWidget);
    expect(find.text('热力学第二定律'), findsAtLeastNWidgets(1));
    expect(find.textContaining('前置相关'), findsOneWidget);
    expect(find.textContaining('受影响后续'), findsOneWidget);

    await tester.tap(find.text('去星图看'));
    await tester.pump();
    await tester.tap(find.text('继续解释'));
    await tester.pump();

    expect(routedTo, '/galaxy/node/node-1');
    expect(prompted, '带我看看这个点为什么会卡住。');
  });
}
