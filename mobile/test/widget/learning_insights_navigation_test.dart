import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/home/presentation/widgets/insight_hub_card.dart';
import 'package:sparkle/features/insights/data/models/weekly_growth_narrative.dart';
import 'package:sparkle/features/insights/presentation/providers/weekly_growth_narrative_provider.dart';
import 'package:sparkle/features/insights/presentation/screens/learning_insights_overview_screen.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import '../shared/i18n_test_helper.dart';

/// U-07 导航减负契约钉：
/// 1. 首页洞察枢纽卡只保留「学习报告」单一 CONTEXTUAL 快捷动作 +
///    总览入口；theater/simulation（LABS, hidden by default）的快捷卡
///    与 LABS 类型通知聚合不再出现在 CORE 首页面。
/// 2. 洞察总览屏只剩 CORE/CONTEXTUAL 模块卡；simulation/theater 模块
///    卡与 deep-link 面板摘除。
void main() {

  setUp(setUpI18nForTesting);
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  group('learning insights navigation', () {
    testWidgets('insight hub keeps only the contextual report shortcut',
        (tester) async {
      final router = GoRouter(
        initialLocation: '/',
        routes: <RouteBase>[
          GoRoute(
            path: '/',
            builder: (context, state) => const Scaffold(body: InsightHubCard()),
          ),
          GoRoute(
            path: '/learning/insights',
            builder: (context, state) => const Text('overview-none'),
          ),
          GoRoute(
            path: '/theater',
            builder: (context, state) => const Text('open-theater'),
          ),
          GoRoute(
            path: '/simulation',
            builder: (context, state) => const Text('simulation-direct'),
          ),
          GoRoute(
            path: '/learning-report',
            builder: (context, state) => const Text('report-direct'),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            // LABS 类型通知（theater_*/simulation_session_ready）即便到达
            // 系统更新流，也不得渲染成首页洞察行。
            systemUpdatesProvider.overrideWith(
              (ref) async => <Map<String, dynamic>>[
                <String, dynamic>{
                  'type': 'theater_route_adopted',
                  'description': '已根据推演创建计划',
                  'metadata': <String, dynamic>{
                    'title': '稳扎稳打',
                    'deep_link':
                        '/theater?topic=%E7%BA%BF%E6%80%A7%E4%BB%A3%E6%95%B0&target_node_id=node-1',
                  },
                },
                <String, dynamic>{
                  'type': 'simulation_session_ready',
                  'description': '仿真会话已就绪',
                  'metadata': <String, dynamic>{},
                },
                <String, dynamic>{
                  'type': 'learning_report_ready',
                  'metadata': <String, dynamic>{
                    'report_payload': <String, dynamic>{
                      'report_id': 'r-1',
                      'markdown': '# 报告',
                      'sections': <String>['summary'],
                      'mastery': <Map<String, dynamic>>[
                        <String, dynamic>{
                          'node_name': '特征值',
                          'mastery_score': 72,
                        },
                      ],
                    },
                  },
                },
              ],
            ),
            weeklyGrowthNarrativeProvider.overrideWith(
              (ref) async => WeeklyGrowthNarrative.placeholder(),
            ),
          ],
          child: MaterialApp.router(
            locale: const Locale('zh'),
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: AppLocalizations.supportedLocales,
            routerConfig: router,
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('学习洞察'), findsOneWidget);
      expect(find.text('学习报告'), findsOneWidget);
      // LABS 快捷动作与 LABS 通知行不再出现在洞察枢纽卡。
      expect(find.text('推演剧场'), findsNothing);
      expect(find.text('学习仿真'), findsNothing);
      expect(find.textContaining('theater'), findsNothing);
      expect(find.textContaining('simulation'), findsNothing);

      await tester.tap(find.text('学习报告'));
      await tester.pumpAndSettle();

      expect(find.text('report-direct'), findsOneWidget);
    });

    testWidgets(
        'overview keeps report module, drops simulation/theater modules',
        (tester) async {
      final router = GoRouter(
        initialLocation: '/learning/insights?initialPanel=report',
        routes: <RouteBase>[
          GoRoute(
            path: '/learning/insights',
            builder: (context, state) => LearningInsightsOverviewScreen(
              initialPanel: state.uri.queryParameters['initialPanel'],
            ),
          ),
          GoRoute(
            path: '/theater',
            builder: (context, state) => const Scaffold(
              body: Center(child: Text('theater-screen')),
            ),
          ),
          GoRoute(
            path: '/simulation',
            builder: (context, state) => const Scaffold(
              body: Center(child: Text('simulation-screen')),
            ),
          ),
          GoRoute(
            path: '/learning-report',
            builder: (context, state) => const Scaffold(
              body: Center(child: Text('report-screen')),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            systemUpdatesProvider.overrideWith(
              (ref) async => <Map<String, dynamic>>[
                <String, dynamic>{
                  'type': 'theater_route_adopted',
                  'description': '已根据推演创建计划',
                  'metadata': <String, dynamic>{
                    'title': '线性代数',
                  },
                },
                <String, dynamic>{
                  'type': 'learning_report_ready',
                  'metadata': <String, dynamic>{
                    'report_payload': <String, dynamic>{
                      'report_id': 'r-1',
                      'markdown': '# 报告',
                      'sections': <String>['summary'],
                      'mastery': <Map<String, dynamic>>[
                        <String, dynamic>{
                          'node_name': '特征值',
                          'mastery_score': 72,
                        },
                      ],
                    },
                  },
                },
              ],
            ),
            weeklyGrowthNarrativeProvider.overrideWith(
              (ref) async => WeeklyGrowthNarrative.placeholder(),
            ),
          ],
          child: MaterialApp.router(
            locale: const Locale('zh'),
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: AppLocalizations.supportedLocales,
            routerConfig: router,
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.byType(LearningInsightsOverviewScreen), findsOneWidget);
      // 面板聚焦徽章只剩 Report 形制；Simulation/Theater 面板已摘除。
      expect(find.textContaining('Report · '), findsOneWidget);
      expect(find.textContaining('Simulation · '), findsNothing);
      expect(find.textContaining('Theater · '), findsNothing);

      // LABS 模块卡不再渲染。
      expect(find.text('学习仿真'), findsNothing);
      expect(find.text('推演剧场'), findsNothing);

      // 报告模块按钮 → 报告屏，返回回到总览（context CTA 返回语义）。
      final reportButton = find.text('查看报告');
      await tester.ensureVisible(reportButton);
      await tester.pumpAndSettle();
      await tester.tap(reportButton);
      await tester.pumpAndSettle();
      expect(find.text('report-screen'), findsOneWidget);

      router.pop();
      await tester.pumpAndSettle();

      expect(find.byType(LearningInsightsOverviewScreen), findsOneWidget);
    });
  });
}
