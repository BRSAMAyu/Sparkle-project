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
                            'id': 'open-theater',
                            'title': '先推演 行列式',
                            'summary': '先拆路径再决定顺序。',
                            'cta_label': '打开推演剧场',
                            'deep_link':
                                '/theater?topic=%E8%A1%8C%E5%88%97%E5%BC%8F',
                            'kind': 'theater',
                          },
                        ],
                        'trigger_summary': {
                          'mode': 'baseline_ready',
                          'title': '已建立第一版学习基线',
                          'summary': '当前报告会先聚焦最值得先收口的部分。',
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
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('推演剧场'), findsOneWidget);
      expect(find.text('学习仿真'), findsOneWidget);
      expect(find.text('查看学习报告'), findsOneWidget);
      expect(find.textContaining('两周掌握特征值'), findsOneWidget);
      expect(find.textContaining('矩阵特征值'), findsOneWidget);
      expect(find.text('继续在对话里'), findsWidgets);
      expect(find.text('排今天行动顺序'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets(
        'recent insights card shows top three items and deep-links to theater',
        (tester) async {
      final now = DateTime(2026, 3, 26, 10);
      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            builder: (context, state) => const Scaffold(
              body: RecentInsightsCard(),
            ),
          ),
          GoRoute(
            path: '/theater',
            builder: (context, state) => Text(
                'open-theater:${state.uri.queryParameters['topic'] ?? ''}'),
          ),
          GoRoute(
            path: '/learning-report',
            builder: (context, state) => const Text('open-report'),
          ),
          GoRoute(
            path: '/notification-center',
            builder: (context, state) => const Text('open-notification-center'),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            notificationCenterProvider.overrideWith(
              () => _StaticNotificationCenter(const NotificationCenterState()),
            ),
            systemUpdatesProvider.overrideWith(
              (ref) async => [
                {
                  'type': 'theater_route_adopted',
                  'title': '已采纳稳扎稳打',
                  'description': '已根据推演创建计划',
                  'metadata': {
                    'deep_link': '/theater?topic=%E7%89%B9%E5%BE%81%E5%80%BC',
                  },
                  'created_at': now.toIso8601String(),
                },
                {
                  'type': 'learning_report_ready',
                  'title': '学习分析报告',
                  'description': '你的报告已生成',
                  'metadata': {
                    'report_payload': {
                      'report_id': 'r-1',
                      'markdown': '# 报告',
                      'sections': <String>[],
                      'mastery': <Map<String, dynamic>>[],
                    },
                  },
                  'created_at': now
                      .subtract(const Duration(minutes: 1))
                      .toIso8601String(),
                },
                {
                  'type': 'theater_snapshot_saved',
                  'title': '剧场快照',
                  'description': '已保存快照',
                  'metadata': {
                    'deep_link': '/theater?topic=%E5%BF%AB%E7%85%A7',
                  },
                  'created_at': now
                      .subtract(const Duration(minutes: 2))
                      .toIso8601String(),
                },
                {
                  'type': 'theater_route_adopted',
                  'title': '更早的洞察',
                  'description': '不应显示在前三条里',
                  'metadata': {
                    'deep_link': '/theater?topic=%E6%97%A7%E6%B4%9E%E5%AF%9F',
                  },
                  'created_at': now
                      .subtract(const Duration(minutes: 3))
                      .toIso8601String(),
                },
              ],
            ),
          ],
          child: MaterialApp.router(
            routerConfig: router,
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('最近洞察'), findsOneWidget);
      expect(find.text('已采纳稳扎稳打'), findsOneWidget);
      expect(find.text('学习分析报告'), findsOneWidget);
      expect(find.text('2 条'), findsOneWidget);
      expect(find.text('更早的洞察'), findsNothing);
      expect(find.textContaining('已根据推演创建计划'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
