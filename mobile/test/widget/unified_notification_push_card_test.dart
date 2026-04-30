import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/unified_notification_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('push notification card shows stage18 actions',
      (WidgetTester tester) async {
    var dismissTapped = false;
    var disableTapped = false;

    final notification = UnifiedNotification.fromJson({
      'id': 'push-1',
      'source_type': 'push',
      'title': '主动提醒',
      'content': '你之前答应过的事情还没有收尾。',
      'type': 'aurora_push',
      'priority': 'high',
      'is_read': false,
      'created_at': DateTime(2026, 4, 20, 10).toIso8601String(),
      'metadata': {
        'category': 'commitment_follow_up',
        'evidence_token': 'commitment:abc',
        'retractable_until': DateTime(2026, 4, 21, 10).toIso8601String(),
      },
    });

    await tester.pumpWidget(
      testMaterialApp(home: Scaffold(
          body: UnifiedNotificationCard(
            notification: notification,
            onRead: () {},
            onDelete: () {},
            onPushDismiss: () => dismissTapped = true,
            onPushDisableCategory: () => disableTapped = true,
          ),
        ),),
    );

    expect(find.text('这次不用了'), findsOneWidget);
    expect(find.text('不再提醒这类'), findsOneWidget);

    await tester.tap(find.text('这次不用了'));
    await tester.pumpAndSettle();
    expect(dismissTapped, isTrue);

    await tester.tap(find.text('不再提醒这类'));
    await tester.pumpAndSettle();
    expect(disableTapped, isTrue);
  });
}
