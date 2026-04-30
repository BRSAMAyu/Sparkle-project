import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/unified_notification_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  test('accountability overview parses in-app hints', () {
    final overview = AccountabilityOverviewInfo.fromJson({
      'slot_type': 'core',
      'in_app_hints': [
        {
          'id': 'hint-1',
          'type': 'accountability_encouragement_received',
          'message': '小李正在看着你，加油',
          'sender_name': '小李',
          'sender_id': 'user-2',
          'partnership_id': 'partner-1',
          'source_notification_id': 'notif-1',
          'created_at': DateTime(2026, 4, 25, 8).toIso8601String(),
        },
      ],
    });

    expect(overview.inAppHints, hasLength(1));
    expect(overview.inAppHints.first.message, '小李正在看着你，加油');
    expect(overview.inAppHints.first.senderName, '小李');
  });

  testWidgets('struggle alert card exposes one-tap encouragement action', (
    tester,
  ) async {
    var encourageTapped = false;

    final notification = UnifiedNotification.fromJson({
      'id': 'signal-1',
      'source_type': 'system',
      'title': '责任伙伴轻提醒',
      'content': '小明已经 2 天没有完成学习任务了，也许可以发一条鼓励。',
      'type': 'accountability_struggle_alert',
      'priority': 'medium',
      'is_read': false,
      'created_at': DateTime(2026, 4, 25, 9).toIso8601String(),
      'metadata': {
        'kind': 'accountability_struggle_alert',
        'target_name': '小明',
        'encouragement_status': 'pending',
        'primary_action': {
          'label': '发个鼓励',
        },
      },
    });

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: Scaffold(
          body: UnifiedNotificationCard(
            notification: notification,
            onRead: () {},
            onDelete: () {},
            onAccountabilityEncourage: () => encourageTapped = true,
          ),
        ),
      ),
    );

    expect(notification.isAccountabilityStruggleAlert, isTrue);
    expect(notification.canSendAccountabilityEncouragement, isTrue);
    expect(find.text('发个鼓励'), findsOneWidget);

    await tester.tap(find.text('发个鼓励'));
    await tester.pumpAndSettle();

    expect(encourageTapped, isTrue);
  });

  testWidgets('struggle alert card shows sent state after encouragement', (
    tester,
  ) async {
    final notification = UnifiedNotification.fromJson({
      'id': 'signal-2',
      'source_type': 'system',
      'title': '责任伙伴轻提醒',
      'content': '小明已经 2 天没有完成学习任务了，也许可以发一条鼓励。',
      'type': 'accountability_struggle_alert',
      'priority': 'medium',
      'is_read': true,
      'created_at': DateTime(2026, 4, 25, 9).toIso8601String(),
      'metadata': {
        'kind': 'accountability_struggle_alert',
        'target_name': '小明',
        'encouragement_status': 'sent',
      },
    });

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: Scaffold(
          body: UnifiedNotificationCard(
            notification: notification,
            onRead: () {},
            onDelete: () {},
          ),
        ),
      ),
    );

    expect(notification.canSendAccountabilityEncouragement, isFalse);
    expect(find.text('已鼓励'), findsOneWidget);
  });
}
