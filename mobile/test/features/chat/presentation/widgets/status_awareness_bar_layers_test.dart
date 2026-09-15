import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/context_decision_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/aurora_status_layer_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/status_awareness_bar.dart';

import '../../../../shared/i18n_test_helper.dart';

class _FakeApiClient extends Fake implements ApiClient {
  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      Response<T>(requestOptions: RequestOptions(path: path));
}

class _LayerStatusNotifier extends AuroraStatusNotifier {
  _LayerStatusNotifier(AuroraControlSurfaceSnapshot snapshot)
      : super(_FakeApiClient()) {
    state = snapshot;
  }

  void setSnapshot(AuroraControlSurfaceSnapshot snapshot) {
    state = snapshot;
  }

  @override
  Future<void> refresh({String? conversationId}) async {}

  @override
  void startPeriodicRefresh({String? conversationId}) {}

  @override
  void stopPeriodicRefresh() {}
}

AuroraControlSurfaceSnapshot _snapshot({
  String status = 'risk_found',
  String summary = 'Aurora 发现当前推进节奏可能需要调整。',
}) {
  return AuroraControlSurfaceSnapshot(
    auroraActive: true,
    runtimeEnabled: true,
    overallStatus: status,
    energyLevel: 'L2',
    summary: summary,
    readyCount: 3,
    activeCount: 4,
    totalCount: 4,
    conversationId: 'conv-b3',
    requestedConversationId: 'conv-b3',
    sceneAlignment: 'matched',
    timeContext: AuroraTimeContext.fromJson(null),
    surface: 'aurora_modeling',
    updatedAt: DateTime(2026, 5),
    facets: const [
      AuroraFacetSnapshot(
        key: 'user_model',
        label: '用户建模',
        status: 'ready',
        summary: '当前最突出的用户瓶颈是“高数复习晚上容易拖延”。',
        confidence: 0.82,
        freshnessSeconds: 40,
        signalCount: 3,
        signals: ['最近 3 天任务都超时了', '薄弱点: 极限计算'],
        meta: {},
      ),
      AuroraFacetSnapshot(
        key: 'self_model',
        label: '自我建模',
        status: 'recalibrating',
        summary: '我对当前节奏判断的把握约为 72%。',
        confidence: 0.72,
        freshnessSeconds: 50,
        signalCount: 2,
        signals: ['任务完成率 42%', '策略命中率 58%'],
        meta: {},
      ),
      AuroraFacetSnapshot(
        key: 'goal_model',
        label: '目标建模',
        status: 'ready',
        summary: '当前目标锚点是“把高数极限题稳住”。',
        confidence: 0.76,
        freshnessSeconds: 60,
        signalCount: 3,
        signals: ['目标: 高数极限题', '时间: 7 天'],
        meta: {},
      ),
      AuroraFacetSnapshot(
        key: 'scene_model',
        label: '情景建模',
        status: 'partial',
        summary: '当前情景里连续出现超时信号。',
        confidence: 0.68,
        freshnessSeconds: 20,
        signalCount: 2,
        signals: ['晚上复习时段被压缩'],
        meta: {},
      ),
    ],
    wakeEligibility: const AuroraWakeEligibility(
      canUserWake: true,
      userQuotaRemaining: 1,
      cooldownStatus: 'available',
      cooldownRemainingMin: 0,
      wakeReasons: ['strategy_confidence_drop'],
      recommendedSessionType: 'strategy_recalibration',
      estimatedDurationSec: 240,
      suggestedScope: 'status_band',
      fallbackIfUnavailable: 'quick_calibration',
    ),
    predictedReplyOptions: const [],
    fetchedAt: DateTime(2026, 5),
    statusEvidenceChain: const ['最近 3 天任务都超时了', '晚上复习时段被压缩'],
    memoryReferences: const ['你之前提到高数复习压力会在晚上变重'],
    nextStepSuggestion: '先把下一步压缩成 10 分钟极限题复盘。',
    selfEvaluation: const AuroraSelfEvaluation(
      confidence: 0.72,
      why: '我主要根据连续超时和晚上时段压缩来判断。',
      risk: '这个判断可能把临时忙碌误判成长期卡点。',
    ),
  );
}

Future<_LayerStatusNotifier> _pumpStatusBar(
  WidgetTester tester,
  AuroraControlSurfaceSnapshot snapshot,
) async {
  final notifier = _LayerStatusNotifier(snapshot);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        auroraStatusProvider.overrideWith((ref) => notifier),
        apiClientProvider.overrideWithValue(_FakeApiClient()),
        lastContextDecisionProvider.overrideWithValue(null),
      ],
      child: testMaterialApp(
        home: const Scaffold(
          body: StatusAwarenessBar(conversationId: 'conv-b3'),
        ),
      ),
    ),
  );
  await tester.pump();
  return notifier;
}

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('layer 1 renders a short natural label', (tester) async {
    await _pumpStatusBar(tester, _snapshot());

    expect(find.text('可能卡住'), findsOneWidget);
    expect(find.textContaining('risk_found'), findsNothing);
    expect(find.text('Aurora 发现策略风险'), findsNothing);
  });

  testWidgets('layer 2 shows evidence and correction choices', (tester) async {
    await _pumpStatusBar(tester, _snapshot());

    await tester.tap(find.text('可能卡住'));
    await tester.pumpAndSettle();

    expect(find.textContaining('最近 3 天任务都超时了'), findsWidgets);
    expect(find.text('时间不够'), findsOneWidget);
    expect(find.text('内容太难'), findsOneWidget);
    expect(find.text('最近状态不好'), findsOneWidget);
    expect(find.text('都不是'), findsOneWidget);

    final correctionButton = find.byKey(
        const ValueKey<String>('aurora-status-correction-time_not_enough'));
    await tester.ensureVisible(correctionButton);
    await tester.tap(correctionButton);
    await tester.pumpAndSettle();

    expect(find.text('已记录，下轮会按这个校准。'), findsOneWidget);
  });

  testWidgets('layer 3 renders four collapsible deep cards', (tester) async {
    await _pumpStatusBar(tester, _snapshot());

    await tester.tap(find.text('可能卡住'));
    await tester.pumpAndSettle();
    final detailsButton =
        find.byKey(const ValueKey<String>('aurora-status-action-查看 Aurora 详情'));
    await tester.ensureVisible(detailsButton);
    await tester.tap(detailsButton);
    await tester.pumpAndSettle();

    expect(find.byType(AuroraStatusLayerCard), findsNWidgets(4));
    expect(find.text('当前状态'), findsOneWidget);
    expect(find.text('记忆引用'), findsOneWidget);
    expect(find.text('下一步建议'), findsOneWidget);
    expect(find.text('Aurora 自评'), findsOneWidget);
    expect(find.textContaining('你之前提到高数复习压力'), findsWidgets);
    expect(find.textContaining('10 分钟极限题复盘'), findsWidgets);
  });

  testWidgets('status switches through animated label and container',
      (tester) async {
    final notifier = await _pumpStatusBar(tester, _snapshot());

    expect(find.byType(AnimatedSwitcher), findsOneWidget);
    expect(find.byType(AnimatedContainer), findsWidgets);
    expect(find.text('可能卡住'), findsOneWidget);

    notifier.setSnapshot(_snapshot(
      status: 'calibrated',
      summary: 'Aurora 认为当前节奏稳定。',
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 350));

    expect(find.text('节奏不错'), findsOneWidget);
  });
}
