import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/home/presentation/widgets/recent_insights_card.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

class _StaticNotificationCenter extends NotificationCenter {
  _StaticNotificationCenter(this._initialState);

  final NotificationCenterState _initialState;

  @override
  NotificationCenterState build() => _initialState;

  @override
  Future<void> loadNotifications(
      {bool unreadOnly = false, String? sourceType}) async {}
}

void main() {

  setUp(setUpI18nForTesting);
  group('MiroFish wiring finish', () {
    testWidgets(
        'chat bubble renders inline mirofish bridge cards and chat follow-ups',
        (tester) async {
      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            builder: (context, state) => Scaffold(
              body: SingleChildScrollView(
                child: ChatBubble(
                  message: ChatMessageModel(
                    conversationId: 'c1',
                    role: MessageRole.assistant,
                    content: '这是一次多专家协作结果。',
                    agentCollaboration: {
                      'prediction_preview': {
                        'topic': '两周掌握特征值',
                        'paths': [
                          {
                            'title': '稳扎稳打',
                            'estimated_mastery': 78,
                          },
                        ],
                      },
                      'simulation_preview': {
                        'topic': '矩阵特征值',
                        'scenario_key': 'study_group',
                        'round_preview': [
                          {'summary': '先梳理前置概念'},
                        ],
                      },
                      'report_preview': {
                        'report_id': 'report-1',
                        'summary': '优先关注行列式，再决定是否直接推进特征值。',
                        'highlights': ['行列式', '特征值'],
                        'action_cards': [
                          {
                            'id': 'attack-weakest',
                            'title': '专项攻克：行列式',
                            'summary': '当前掌握度较低，建议用 25 分钟做一组针对性练习。',
                            'cta_label': '开始练习',
                            'deep_link': '/galaxy/node/node-1',
                            'kind': 'immediate_action',
                          },
                        ],
                        'trigger_summary': {
                          'mode': 'baseline_ready',
                          'title': '以下是基于聊天推断的方向，需要你确认',
                          'summary': '当前报告会先聚焦最值得先收口的部分。',
                          'data_status': 'partial',
                        },
                      },
                      'deep_link':
                          '/theater?topic=%E4%B8%A4%E5%91%A8%E6%8E%8C%E6%8F%A1%E7%89%B9%E5%BE%81%E5%80%BC',
                      'simulation_deep_link':
                          '/simulation?topic=%E7%9F%A9%E9%98%B5%E7%89%B9%E5%BE%81%E5%80%BC&scenario_key=study_group',
                      'report_deep_link': '/learning-report',
                    },
                  ),
                  currentUserId: 'me',
                  isLatestAssistantMessage: true,
                ),
              ),
            ),
          ),
          GoRoute(
            path: '/theater',
            builder: (context, state) =>
                Text('theater:${state.uri.queryParameters['topic']}'),
          ),
          GoRoute(
            path: '/simulation',
            builder: (context, state) =>
                Text('simulation:${state.uri.queryParameters['scenario_key']}'),
          ),
          GoRoute(
            path: '/learning-report',
            builder: (context, state) => const Text('report'),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: router,
            locale: const Locale('zh'),
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
          ),
        ),
      );

      await tester.pumpAndSettle();

      // The prediction / simulation / report cards are wrapped in
      // CollapsibleWidgetWrapper chips. Expand them first.
      await tester.tap(find.text('查看推演详情'));
      await tester.pump(const Duration(milliseconds: 300));

      await tester.tap(find.text('查看模拟详情'));
      await tester.pump(const Duration(milliseconds: 300));

      await tester.tap(find.text('查看学习报告'));
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('推演剧场'), findsOneWidget);
      expect(find.text('学习仿真'), findsOneWidget);
      expect(find.text('查看学习报告'), findsWidgets);
      expect(find.textContaining('两周掌握特征值'), findsOneWidget);
      expect(find.textContaining('矩阵特征值'), findsOneWidget);
      expect(find.text('继续在对话里'), findsWidgets);
      expect(find.text('排今天行动顺序'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

  });
}
