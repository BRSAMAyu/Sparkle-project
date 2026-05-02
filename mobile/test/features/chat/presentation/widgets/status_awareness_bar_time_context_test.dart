import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/context_decision_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/status_awareness_bar.dart';

import '../../../../shared/i18n_test_helper.dart';

class _FakeApiClient extends Fake implements ApiClient {}

class _TimeContextNotifier extends AuroraStatusNotifier {
  _TimeContextNotifier({
    AuroraTaskHealth taskHealth = const AuroraTaskHealth.empty(),
  }) : super(_FakeApiClient()) {
    state = AuroraControlSurfaceSnapshot(
      auroraActive: true,
      runtimeEnabled: true,
      overallStatus: 'calibrated',
      energyLevel: 'L1',
      summary: 'Aurora 已对齐当前计划。',
      readyCount: 4,
      activeCount: 4,
      totalCount: 4,
      conversationId: 'conv-time',
      requestedConversationId: 'conv-time',
      sceneAlignment: 'matched',
      timeContext: AuroraTimeContext.fromJson(const {
        'visible': true,
        'kind': 'time_conflict',
        'severity': 'warning',
        'label': '时间可能不够',
        'subtitle': '高数考试',
        'action': 'quick_adjust',
        'conflict': {'type': 'plan_deadline'},
      }),
      lastCorrectionEffect: const AuroraCorrectionEffect(
        visible: false,
        semanticValue: '',
        action: '',
        affectedStateKeys: [],
        updatedAt: null,
      ),
      taskHealth: taskHealth,
      surface: 'aurora_planning',
      updatedAt: DateTime(2026, 5),
      facets: const [],
      wakeEligibility: const AuroraWakeEligibility(
        canUserWake: false,
        userQuotaRemaining: 0,
        cooldownStatus: 'available',
        cooldownRemainingMin: 0,
        wakeReasons: [],
        recommendedSessionType: 'strategy_recalibration',
        estimatedDurationSec: 240,
        suggestedScope: '',
        fallbackIfUnavailable: 'quick_calibration',
      ),
      predictedReplyOptions: const [],
      fetchedAt: DateTime(2026, 5),
    );
  }

  @override
  Future<void> refresh({String? conversationId}) async {}

  @override
  void startPeriodicRefresh({String? conversationId}) {}

  @override
  void stopPeriodicRefresh() {}
}

void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(<String, Object>{
      'sensory_feedback.aurora_linkage_enabled': false,
    });
  });
  tearDown(tearDownI18n);

  testWidgets('status bar displays calendar time conflict context',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          auroraStatusProvider.overrideWith((ref) => _TimeContextNotifier()),
          lastContextDecisionProvider.overrideWithValue(null),
        ],
        child: testMaterialApp(
          home: const Scaffold(
            body: StatusAwarenessBar(conversationId: 'conv-time'),
          ),
        ),
      ),
    );

    await tester.pump();

    expect(find.textContaining('时间可能不够'), findsWidgets);
    expect(find.textContaining('高数考试'), findsWidgets);
  });

  testWidgets('status bar displays task health intervention context',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          auroraStatusProvider.overrideWith(
            (ref) => _TimeContextNotifier(
              taskHealth: AuroraTaskHealth.fromJson(const {
                'visible': true,
                'status': 'needs_attention',
                'severity': 'warning',
                'label': '最近 3 张任务中有 3 张卡住',
                'subtitle': '需要关注',
                'trend_label': '需要关注',
                'total_count': 3,
                'issue_count': 3,
              }),
            ),
          ),
          lastContextDecisionProvider.overrideWithValue(null),
        ],
        child: testMaterialApp(
          home: const Scaffold(
            body: StatusAwarenessBar(conversationId: 'conv-time'),
          ),
        ),
      ),
    );

    await tester.pump();

    expect(find.textContaining('最近 3 张任务中有 3 张卡住'), findsWidgets);
    expect(find.textContaining('需要关注'), findsWidgets);
  });

  testWidgets('status row uses stagger motion for Aurora state changes',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          auroraStatusProvider.overrideWith((ref) => _TimeContextNotifier()),
        ],
        child: testMaterialApp(
          home: const Scaffold(
            body: StatusAwarenessBar(conversationId: 'conv-time'),
          ),
        ),
      ),
    );

    await tester.pump();

    expect(find.byType(SparkleStaggerItem), findsOneWidget);
  });
}
