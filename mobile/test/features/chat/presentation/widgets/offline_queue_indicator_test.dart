import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/chat/presentation/widgets/offline_queue_indicator.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('shows pending count while offline messages are queued',
      (tester) async {
    final semantics = tester.ensureSemantics();

    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: OfflineQueueIndicator(
            status: OfflineQueueIndicatorStatus.queued,
            pendingCount: 2,
          ),
        ),
      ),
    );

    expect(find.text('2 条消息等待发送'), findsOneWidget);
    expect(find.byIcon(Icons.wifi_off_rounded), findsOneWidget);
    expect(
      find.bySemanticsLabel(RegExp('离线队列中有 2 条消息等待发送')),
      findsOneWidget,
    );
    semantics.dispose();
  });

  testWidgets('shows sending progress when queue is flushing', (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: OfflineQueueIndicator(
            status: OfflineQueueIndicatorStatus.sending,
            pendingCount: 3,
          ),
        ),
      ),
    );

    expect(find.text('正在发送 3 条排队消息...'), findsOneWidget);
    // U-01 Step 3：发送中 spinner 已迁 owner LoadingIndicator，
    // 其内部仍渲染 CircularProgressIndicator。
    expect(find.byType(LoadingIndicator), findsOneWidget);
    expect(
      find.descendant(
        of: find.byType(LoadingIndicator),
        matching: find.byType(CircularProgressIndicator),
      ),
      findsOneWidget,
    );
  });

  testWidgets('shows completion state after all queued messages send',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: OfflineQueueIndicator(
            status: OfflineQueueIndicatorStatus.complete,
            pendingCount: 0,
          ),
        ),
      ),
    );

    expect(find.text('已全部发送'), findsOneWidget);
    expect(find.byIcon(Icons.check_circle_outline_rounded), findsOneWidget);
  });
}
