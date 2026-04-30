import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('task list prefers task and plan detail routes from entity card',
      (tester) async {
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => Scaffold(
            body: ActionCard(
              action: WidgetPayload(
                type: 'task_list',
                data: {
                  'plan_id': '00000000-0000-0000-0000-000000000111',
                  'plan_title': '冲刺计划',
                  'tasks': [
                    {
                      'id': '00000000-0000-0000-0000-000000000222',
                      'title': '完成主任务',
                      'status': 'PENDING',
                      'estimated_minutes': 25,
                      'entity_card': {
                        'entity_type': 'task',
                        'entity_id': '00000000-0000-0000-0000-000000000222',
                        'title': '完成主任务',
                        'primary_action': {
                          'id': 'open_task_execute',
                          'type': 'route',
                          'label': '打开任务',
                          'route':
                              '/tasks/00000000-0000-0000-0000-000000000222/execute',
                        },
                        'raw': {
                          'id': '00000000-0000-0000-0000-000000000222',
                          'title': '完成主任务',
                          'status': 'PENDING',
                          'estimated_minutes': 25,
                        },
                      },
                    },
                  ],
                  'entity_card': {
                    'entity_type': 'task_list',
                    'entity_id': 'tool-result-1',
                    'title': '任务计划',
                    'primary_action': {
                      'id': 'open_plan_board',
                      'type': 'route',
                      'label': '查看计划',
                      'route':
                          '/plans/00000000-0000-0000-0000-000000000111/kanban',
                    },
                    'linked_entities': {
                      'plan_id': '00000000-0000-0000-0000-000000000111',
                      'plan_title': '冲刺计划',
                    },
                  },
                },
              ),
            ),
          ),
        ),
        GoRoute(
          path: '/tasks/:id/execute',
          builder: (context, state) => Scaffold(
            body: Text('task-execute:${state.pathParameters['id']}'),
          ),
        ),
        GoRoute(
          path: '/plans/:id/kanban',
          builder: (context, state) => Scaffold(
            body: Text('plan-board:${state.pathParameters['id']}'),
          ),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      MaterialApp.router(
        routerConfig: router,
        theme: ThemeData.light().copyWith(
          extensions: [SparkleThemeExtension.light()],
        ),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
      ),
    );

    await tester.pumpAndSettle();
    await tester.tap(find.text('展开'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('打开'));
    await tester.pumpAndSettle();
    expect(
      find.text('task-execute:00000000-0000-0000-0000-000000000222'),
      findsOneWidget,
    );

    router.go('/');
    await tester.pumpAndSettle();
    await tester.tap(find.text('展开'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('查看计划'));
    await tester.pumpAndSettle();
    expect(
      find.text('plan-board:00000000-0000-0000-0000-000000000111'),
      findsOneWidget,
    );
  });

  testWidgets('plan card can navigate through custom detail route',
      (tester) async {
    String? receivedPlanId;
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => Scaffold(
            body: ActionCard(
              action: WidgetPayload(
                type: 'plan_card',
                data: {
                  'id': '00000000-0000-0000-0000-000000000333',
                  'title': '知识星图冲刺',
                  'type': 'sprint',
                  'description': '先锁定关键节点，再生成任务卡。',
                  'entity_card': {
                    'entity_type': 'plan',
                    'entity_id': '00000000-0000-0000-0000-000000000333',
                    'title': '知识星图冲刺',
                    'primary_action': {
                      'id': 'open_plan_workspace',
                      'type': 'route',
                      'label': '查看详情',
                      'route':
                          '/plans/00000000-0000-0000-0000-000000000333/workspace',
                    },
                  },
                },
              ),
              onPlanNavigation: (planId) => receivedPlanId = planId,
            ),
          ),
        ),
        GoRoute(
          path: '/plans/:id/workspace',
          builder: (context, state) => Scaffold(
            body: Text('plan-workspace:${state.pathParameters['id']}'),
          ),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      MaterialApp.router(
        routerConfig: router,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
      ),
    );

    await tester.pumpAndSettle();
    await tester.tap(find.text('展开'));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(PlanCard));
    await tester.pumpAndSettle();

    expect(
      find.text('plan-workspace:00000000-0000-0000-0000-000000000333'),
      findsOneWidget,
    );
    expect(receivedPlanId, '00000000-0000-0000-0000-000000000333');
  });
}
