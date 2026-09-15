library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/unified_notification_card.dart';

import '../shared/i18n_test_helper.dart';

const bool _enableNotificationGoldens = bool.fromEnvironment(
  'ENABLE_NOTIFICATION_GOLDEN',
);

void main() {
  setUp(setUpI18nForTesting);

  testGoldens(
    'recall notification value disclosure',
    (tester) async {
      final notification = UnifiedNotification.fromJson({
        'id': 'recall-golden',
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

      await tester.pumpWidgetBuilder(
        SizedBox(
          width: 390,
          child: UnifiedNotificationCard(
            notification: notification,
            onRead: () {},
            onDelete: () {},
            onRecallInaccurate: () {},
          ),
        ),
        wrapper: (child) => testMaterialApp(
          home: Scaffold(
            body: Padding(
              padding: const EdgeInsets.all(16),
              child: child,
            ),
          ),
        ),
        surfaceSize: const Size(390, 360),
      );

      await tester.tap(find.text('为什么提醒你'));
      await tester.pumpAndSettle();

      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('notification_recall_card.png'),
      );
    },
    skip: !_enableNotificationGoldens,
  );
}
