import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_inline_signals.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/data/repositories/notification_center_repository.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/unified_notification_card.dart';
import '../shared/i18n_test_helper.dart';

class _FakeApiClient extends Fake implements ApiClient {}

UnifiedNotification _auroraNotification() => UnifiedNotification.fromJson({
      'id': 'claim-1',
      'source_type': 'aurora_confirm',
      'title': '我注意到你最近在晚上复习',
      'content': '我有一个判断需要你确认。',
      'type': 'aurora_confirm',
      'priority': 'high',
      'is_read': false,
      'created_at': DateTime(2026, 9, 20, 10).toIso8601String(),
      'metadata': {
        'kind': 'aurora_confirm',
        'needs_confirmation': true,
        'confidence': 0.72,
        'confidence_label': '72%',
        'evidence_summary': '证据：最近 3 天任务都排在晚上。',
      },
    });

void main() {
  setUp(setUpI18nForTesting);

  group('UnifiedNotification aurora_confirm model', () {
    test('parses aurora source type and card metadata', () {
      final notification = _auroraNotification();

      expect(notification.isAuroraConfirm, isTrue);
      expect(notification.canRespondAuroraConfirm, isTrue);
      expect(notification.auroraConfidenceLabel, '72%');
      expect(
        notification.auroraEvidenceSummary,
        '证据：最近 3 天任务都排在晚上。',
      );
      expect(notification.auroraNeedsConfirmation, isTrue);
      expect(notification.icon, '✨');
    });

    test('non-aurora notifications keep their source type', () {
      final notification = UnifiedNotification.fromJson({
        'id': 'n-1',
        'source_type': 'system',
        'title': '系统',
        'content': '内容',
        'priority': 'low',
        'is_read': false,
        'created_at': DateTime(2026, 9, 20, 10).toIso8601String(),
      });

      expect(notification.isAuroraConfirm, isFalse);
      expect(notification.sourceType, 'system');
    });
  });

  testWidgets('aurora confirm card renders respond actions',
      (WidgetTester tester) async {
    var confirmTapped = false;
    var incorrectTapped = false;
    var muteTapped = false;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: UnifiedNotificationCard(
            notification: _auroraNotification(),
            onRead: () {},
            onDelete: () {},
            onAuroraConfirm: () => confirmTapped = true,
            onAuroraIncorrect: () => incorrectTapped = true,
            onAuroraMute: () => muteTapped = true,
          ),
        ),
      ),
    );

    expect(find.text('确认'), findsOneWidget);
    expect(find.text('不准确'), findsOneWidget);
    expect(find.text('暂不确认'), findsOneWidget);
    expect(find.text('72%'), findsOneWidget);
    expect(find.text('Aurora 确认'), findsOneWidget);

    await tester.tap(find.text('确认'));
    await tester.pumpAndSettle();
    expect(confirmTapped, isTrue);

    await tester.tap(find.text('不准确'));
    await tester.pumpAndSettle();
    expect(incorrectTapped, isTrue);

    await tester.tap(find.text('暂不确认'));
    await tester.pumpAndSettle();
    expect(muteTapped, isTrue);
  });

  test('respondToAuroraCard delegates and removes the item locally', () async {
    final sentActions = <String>[];
    final repository = _FakeRepository(sentActions);

    final container = ProviderContainer(
      overrides: [
        notificationCenterRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);

    final notifier = container.read(notificationCenterProvider.notifier);
    await notifier.loadNotifications();

    final before = container.read(notificationCenterProvider).notifications;
    expect(before, hasLength(1));
    expect(before.single.isAuroraConfirm, isTrue);

    await notifier.respondToAuroraCard(before.single, 'confirm');

    expect(sentActions, ['confirm']);
    expect(container.read(notificationCenterProvider).notifications, isEmpty);
  });

  group('ChatInboxEntryIcon badge count (B4-INBOX)', () {
    testWidgets('shows pending confirm count when actionable',
        (WidgetTester tester) async {
      final notifier = _FakeAuroraNotifier(
        _snapshot(status: 'needs_confirm', pendingCount: 3),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            auroraStatusProvider.overrideWith((ref) => notifier),
            apiClientProvider.overrideWithValue(_FakeApiClient()),
          ],
          child: testMaterialApp(
            home: const Scaffold(
              body: ChatInboxEntryIcon(conversationId: 'conv-b4'),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.text('3'), findsOneWidget);
    });

    testWidgets('falls back to plain dot when count is zero but actionable',
        (WidgetTester tester) async {
      final notifier = _FakeAuroraNotifier(
        _snapshot(status: 'risk_found', pendingCount: 0),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            auroraStatusProvider.overrideWith((ref) => notifier),
            apiClientProvider.overrideWithValue(_FakeApiClient()),
          ],
          child: testMaterialApp(
            home: const Scaffold(
              body: ChatInboxEntryIcon(conversationId: 'conv-b4'),
            ),
          ),
        ),
      );
      await tester.pump();

      final badge = tester.widget<Badge>(find.byType(Badge));
      expect(badge.isLabelVisible, isTrue);
      expect(badge.label, isNull);
    });

    testWidgets('badge hidden when snapshot is not actionable',
        (WidgetTester tester) async {
      final notifier = _FakeAuroraNotifier(
        _snapshot(status: 'calibrated', pendingCount: 0),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            auroraStatusProvider.overrideWith((ref) => notifier),
            apiClientProvider.overrideWithValue(_FakeApiClient()),
          ],
          child: testMaterialApp(
            home: const Scaffold(
              body: ChatInboxEntryIcon(conversationId: 'conv-b4'),
            ),
          ),
        ),
      );
      await tester.pump();

      final badge = tester.widget<Badge>(find.byType(Badge));
      expect(badge.isLabelVisible, isFalse);
    });
  });
}

class _FakeRepository extends NotificationCenterRepository {
  _FakeRepository(this.sentActions) : super(_FakeApiClient());

  final List<String> sentActions;

  @override
  Future<List<UnifiedNotification>> getNotifications({
    int skip = 0,
    int limit = 50,
    bool unreadOnly = false,
    String? sourceType,
  }) async {
    if (sourceType != null && sourceType != 'aurora_confirm') {
      return const [];
    }
    return [_auroraNotification()];
  }

  @override
  Future<void> sendAuroraConfirmAction(
    String cardId,
    String action, {
    String? reason,
  }) async {
    sentActions.add(action);
  }
}

class _FakeAuroraNotifier extends AuroraStatusNotifier {
  _FakeAuroraNotifier(AuroraControlSurfaceSnapshot snapshot)
      : super(_FakeApiClient()) {
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
  required String status,
  required int pendingCount,
}) =>
    AuroraControlSurfaceSnapshot(
      auroraActive: true,
      runtimeEnabled: true,
      overallStatus: status,
      energyLevel: 'L2',
      summary: 'Aurora 有一个判断需要你确认。',
      readyCount: 3,
      activeCount: 4,
      totalCount: 4,
      conversationId: 'conv-b4',
      requestedConversationId: 'conv-b4',
      sceneAlignment: 'matched',
      timeContext: AuroraTimeContext.fromJson(null),
      surface: 'aurora_modeling',
      updatedAt: DateTime(2026, 9, 20),
      facets: const [],
      wakeEligibility: const AuroraWakeEligibility(
        canUserWake: true,
        userQuotaRemaining: 1,
        cooldownStatus: 'available',
        cooldownRemainingMin: 0,
        wakeReasons: [],
        recommendedSessionType: 'strategy_recalibration',
        estimatedDurationSec: 240,
        suggestedScope: 'status_band',
        fallbackIfUnavailable: 'quick_calibration',
      ),
      predictedReplyOptions: const [],
      fetchedAt: DateTime(2026, 9, 20),
      pendingConfirmCount: pendingCount,
    );
