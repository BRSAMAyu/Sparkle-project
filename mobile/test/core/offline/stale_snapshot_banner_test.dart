import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/offline/widgets/stale_snapshot_banner.dart';

import '../../shared/i18n_test_helper.dart';

/// N34/N36（A-SPEC6）验收：本地快照读必带「截至 X」时点标记（stale 徽标）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('挂 stale 徽标：可见 + 语义标签带时点（zh 口径）', (tester) async {
    setUpI18nForTesting();

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: StaleSnapshotBanner(
              fetchedAt: DateTime(2026, 9, 21, 22, 30),),
        ),
      ),
    );
    await tester.pump();

    // N36 口径：文案=「离线数据 · 截至 {time}」，时点真源为 fetchedAt
    //（时间经 Formatters.formatDateTime 本地化格式化，只断言稳定片段）。
    expect(find.byType(StaleSnapshotBanner), findsOneWidget);
    expect(find.textContaining('离线数据 · 截至'), findsOneWidget);
    expect(find.textContaining('22:30'), findsOneWidget);
  });
}
