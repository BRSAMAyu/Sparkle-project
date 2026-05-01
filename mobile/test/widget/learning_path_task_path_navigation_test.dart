import 'package:flutter/material.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/insights/data/models/learning_path_node.dart';
import 'package:sparkle/features/insights/data/models/learning_path_plan_response.dart';
import 'package:sparkle/features/insights/data/repositories/learning_path_repository.dart';
import 'package:sparkle/features/insights/presentation/providers/learning_path_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/learning_path_dialog.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';
import '../shared/i18n_test_helper.dart';

class _FakeApiClient extends Fake implements ApiClient {}

class _FakeEventStream extends Fake implements AppEventStreamService {}

class _TaskPathRepository extends LearningPathRepository {
  _TaskPathRepository() : super(_FakeApiClient(), _FakeEventStream());

  @override
  Future<List<LearningPathNode>> getLearningPath(String targetNodeId) async =>
      <LearningPathNode>[
        LearningPathNode(
          id: targetNodeId,
          name: '目标节点',
          status: 'locked',
          isTarget: true,
        ),
      ];

  @override
  Future<LearningPathTaskPathResponse> generateTaskPath(
    String targetNodeId, {
    List<String> selectedRelatedNodeIds = const [],
  }) async =>
      LearningPathTaskPathResponse(
        mode: 'task_path',
        targetNodeId: targetNodeId,
        targetName: '目标节点',
        planSummary: '已整理成可执行任务卡',
        tasks: <LearningPathTaskSummary>[
          LearningPathTaskSummary(
            id: 'task-1',
            title: '第一张任务卡',
            type: 'learning',
            estimatedMinutes: 25,
            status: 'pending',
          ),
        ],
        taskListEntityCard: EntityCardPayload.fromRaw(
          {
            'entity_card': {
              'entity_type': 'task_list',
              'title': '任务路径',
              'primary_action': {
                'id': 'open_tasks',
                'type': 'route',
                'label': '查看任务',
                'route': '/tasks',
              },
            },
          },
          fallbackType: 'task_list',
        ),
      );
}

class _LearningPathDialogLauncher extends StatelessWidget {
  const _LearningPathDialogLauncher();

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(
          child: ElevatedButton(
            onPressed: () {
              showDialog<void>(
                context: context,
                builder: (dialogContext) => const Dialog(
                  child: LearningPathDialog(
                    targetNodeId: 'node-1',
                    targetNodeName: '目标节点',
                  ),
                ),
              );
            },
            child: const Text('open-dialog'),
          ),
        ),
      );
}

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('task path generation returns user to task system',
      (tester) async {
    final router = GoRouter(
      navigatorKey: navigatorKey,
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => const _LearningPathDialogLauncher(),
        ),
        GoRoute(
          path: '/tasks',
          builder: (context, state) => const Scaffold(body: Text('tasks-home')),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          learningPathRepositoryProvider
              .overrideWithValue(_TaskPathRepository()),
        ],
        child: MaterialApp.router(
          routerConfig: router,
        locale: const Locale('zh'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
              ),
      ),
    );

    await tester.pumpAndSettle();
    await tester.tap(find.text('open-dialog'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('快速生成任务路径'));
    await tester.pumpAndSettle();

    expect(find.text('tasks-home'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
