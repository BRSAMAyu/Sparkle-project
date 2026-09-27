/// V3-FIX-376 · B-04-L-01 pin — demo 模式下理解快照不得以错误态裸露。
///
/// B-04 视觉 ledger B 级项 L-01：demo 首屏主叙事句下方渲染
/// 「ⓘ 加载失败 轻触重试」（understandingSnapshotProvider 无 demo 分支，
/// demo 首屏直打真网端点失败）。demo 契约 = demo 数据永不失败：
/// 本测试钉住 demo 分支返回内建空快照（卡片/面板均有既有空态渲染），
/// provider 级降级，错误态不再可达。
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/experience/presentation/widgets/understanding_snapshot_card.dart';
import 'package:sparkle/features/home/presentation/providers/understanding_snapshot_provider.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  testWidgets('demo 模式：理解快照解析为空快照而非错误态', (tester) async {
    DemoDataService.isDemoMode = true;
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final snapshot = await container.read(understandingSnapshotProvider.future);

    expect(snapshot, isNotNull,
        reason: 'demo 契约：理解快照不因无后端而失败（B-04-L-01）',);
    expect(snapshot!.isEmpty, isTrue,
        reason: 'demo 占位 = 内建空快照，由卡片/面板的既有空态渲染承载',);
    expect(snapshot.claims, isEmpty);
  });

  testWidgets('demo 模式：UnderstandingSnapshotCard 不渲染 CompactErrorCard',
      (tester) async {
    DemoDataService.isDemoMode = true;
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: Scaffold(body: UnderstandingSnapshotCard())),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.byType(CompactErrorCard),
      findsNothing,
      reason: 'demo 首屏不得裸露「加载失败 轻触重试」（V3-FIX-376）',
    );
  });
}
