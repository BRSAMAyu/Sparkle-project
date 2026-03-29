import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/features/insights/data/models/learning_path_node.dart';
import 'package:sparkle/features/insights/data/models/learning_path_plan_response.dart';
import 'package:sparkle/features/insights/data/repositories/learning_path_repository.dart';
import 'package:sparkle/features/insights/presentation/providers/learning_path_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/learning_path_dialog.dart';
import 'package:sparkle/features/visual_elements/data/repositories/visual_element_repository.dart';
import 'package:sparkle/features/visual_elements/presentation/providers/visual_elements_provider.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

class _FakeApiClient extends Fake implements ApiClient {}

class _FakeAppEventStreamService extends Fake implements AppEventStreamService {}

class _VisualFallbackRepository extends VisualElementRepository {
  _VisualFallbackRepository() : super(_FakeApiClient());

  @override
  Future<VisualElementListResponse> getVisualElements({
    VisualElementType? type,
    VisualElementRarity? rarity,
    String? category,
    bool unlockedOnly = false,
  }) async {
    final items = <VisualElementModel>[
      VisualElementModel(
        id: 'bg-default',
        name: 'Default Background',
        elementType: VisualElementType.background,
        rarity: VisualElementRarity.common,
        unlockSource: VisualElementUnlockSource.system,
        isDefault: true,
        sortOrder: 1,
        isUnlocked: true,
      ),
      VisualElementModel(
        id: 'particle-default',
        name: 'Default Particle',
        elementType: VisualElementType.particle,
        rarity: VisualElementRarity.common,
        unlockSource: VisualElementUnlockSource.system,
        isDefault: true,
        sortOrder: 2,
      ),
      VisualElementModel(
        id: 'effect-default',
        name: 'Default Effect',
        elementType: VisualElementType.effect,
        rarity: VisualElementRarity.common,
        unlockSource: VisualElementUnlockSource.system,
        isDefault: true,
        sortOrder: 3,
      ),
      VisualElementModel(
        id: 'bundle-default',
        name: 'Default Bundle',
        elementType: VisualElementType.bundle,
        rarity: VisualElementRarity.common,
        unlockSource: VisualElementUnlockSource.system,
        isDefault: true,
        sortOrder: 4,
        config: const {
          'background_id': 'bg-default',
          'particle_id': 'particle-default',
          'effect_id': 'effect-default',
        },
      ),
    ];

    final filtered = unlockedOnly
        ? items.where((item) => item.isUnlocked).toList(growable: false)
        : items;
    return VisualElementListResponse(
      items: filtered,
      total: filtered.length,
    );
  }

  @override
  Future<VisualElementListResponse> getUnlockedElements({
    VisualElementType? type,
  }) async {
    throw Exception('unlocked endpoint unavailable');
  }

  @override
  Future<UserVisualConfig> getUserConfig() async {
    throw Exception('config endpoint unavailable');
  }
}

class _LearningPathDialogRepository extends LearningPathRepository {
  _LearningPathDialogRepository()
      : super(_FakeApiClient(), _FakeAppEventStreamService());

  @override
  Future<List<LearningPathNode>> getLearningPath(String targetNodeId) async =>
      <LearningPathNode>[
        LearningPathNode(
          id: 'foundation',
          name: '基础概念',
          status: 'mastered',
        ),
        LearningPathNode(
          id: 'bridge',
          name: '桥接知识',
          status: 'unlocked',
        ),
        LearningPathNode(
          id: targetNodeId,
          name: '目标节点',
          status: 'locked',
          isTarget: true,
        ),
        LearningPathNode(
          id: 'related-a',
          name: '关联拓展 A',
          status: 'unlocked',
          isOptional: true,
          relationType: 'related',
          sourceType: 'candidate',
        ),
        LearningPathNode(
          id: 'related-b',
          name: '关联拓展 B',
          status: 'locked',
          isOptional: true,
          relationType: 'recommended',
          sourceType: 'candidate',
        ),
      ];

  @override
  Future<LearningPathPlanResponse> generateLearningPlan(
    String targetNodeId, {
    List<String> selectedRelatedNodeIds = const [],
  }) async =>
      LearningPathPlanResponse(
        planId: 'plan-1',
        planSummary: 'summary',
        tasks: const <LearningPathTaskSummary>[],
      );

  @override
  Future<LearningPathTaskPathResponse> generateTaskPath(
    String targetNodeId, {
    List<String> selectedRelatedNodeIds = const [],
  }) async =>
      LearningPathTaskPathResponse(
        mode: 'task_path',
        targetNodeId: targetNodeId,
        targetName: '目标节点',
        planSummary: 'summary',
        tasks: const <LearningPathTaskSummary>[],
      );

  @override
  Future<FullPlanResponse> generateFullPathPlan(
    String targetNodeId, {
    List<String> selectedRelatedNodeIds = const [],
  }) async =>
      FullPlanResponse(
        planId: 'full-plan-1',
        planSummary: 'summary',
        parentTaskId: 'task-parent',
        subtaskCount: 0,
      );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('visual elements fallback keeps defaults available when secondary calls fail',
      () async {
    final notifier = VisualElementsNotifier(_VisualFallbackRepository());

    await notifier.loadAll();

    expect(notifier.state.error, isNull);
    expect(notifier.state.allElements, hasLength(4));
    expect(notifier.state.unlockedElements.map((item) => item.id), ['bg-default']);
    expect(notifier.state.config?.equippedBackground?.id, 'bg-default');
    expect(
      notifier.state.config?.equippedParticle?.id,
      'particle-default',
    );
    expect(
      notifier.state.config?.equippedEffect?.id,
      'effect-default',
    );
  });

  testWidgets('learning path dialog remains scrollable and action buttons visible on compact screens',
      (tester) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(390, 640);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          learningPathRepositoryProvider.overrideWithValue(
            _LearningPathDialogRepository(),
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: Center(
              child: LearningPathDialog(
                targetNodeId: 'target-node',
                targetNodeName: '目标节点',
              ),
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('主干路径'), findsOneWidget);
    expect(find.text('推荐拓展节点'), findsOneWidget);
    expect(find.text('快速生成任务路径'), findsOneWidget);
    expect(find.text('生成完整计划'), findsOneWidget);
    expect(find.byType(SingleChildScrollView), findsWidgets);

    await tester.drag(find.byType(SingleChildScrollView).first, const Offset(0, -120));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
  });
}
