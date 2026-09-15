import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/unified_notification_card.dart';
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
      testMaterialApp(
        home: Scaffold(
          body: UnifiedNotificationCard(
            notification: notification,
            onRead: () {},
            onDelete: () {},
            onPushDismiss: () => dismissTapped = true,
            onPushDisableCategory: () => disableTapped = true,
          ),
        ),
      ),
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

  testWidgets('recall notification card expands value reasons and feedback',
      (WidgetTester tester) async {
    var inaccurateTapped = false;

    final notification = UnifiedNotification.fromJson({
      'id': 'recall-1',
      'source_type': 'push',
      'title': '任务等你开始',
      'content': '今天的第一个任务还没开始，要不要先看一眼？',
      'type': 'recall_notification',
      'priority': 'medium',
      'is_read': false,
      'created_at': DateTime(2026, 5, 2, 10).toIso8601String(),
      'metadata': {
        'reasoning': '今天的计划中有待办任务。',
        'value_reason': '启动第一张任务卡能帮计划产生反馈。',
        'effort_estimate': '预计先投入 5 分钟。',
        'deadline_pressure_label': '今日节奏待启动',
        'recall_score': 0.84,
      },
    });

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: UnifiedNotificationCard(
            notification: notification,
            onRead: () {},
            onDelete: () {},
            onRecallInaccurate: () => inaccurateTapped = true,
          ),
        ),
      ),
    );

    expect(find.text('为什么提醒你'), findsOneWidget);

    await tester.tap(find.text('为什么提醒你'));
    await tester.pumpAndSettle();

    expect(find.text('对目标的价值'), findsOneWidget);
    expect(find.text('启动第一张任务卡能帮计划产生反馈。'), findsOneWidget);
    expect(find.text('预计先投入 5 分钟。'), findsOneWidget);
    expect(find.text('84%'), findsOneWidget);

    await tester.tap(find.text('这个提醒不准确'));
    await tester.pumpAndSettle();
    expect(inaccurateTapped, isTrue);
  });
}
